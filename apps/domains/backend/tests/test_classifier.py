"""Tests for Part 2 (name classifier): normalization, buckets, schema, engine."""

from __future__ import annotations

import asyncio

from app.classifier.buckets import assign_bucket
from app.classifier.engine import RunManager
from app.classifier.normalize import is_valid_domain, normalize_domain, parse_input
from app.classifier.schema import Classification, parse_response
from app.classifier.store import ClassifierStore


# --- FR-1..FR-4 normalization ---------------------------------------------

def test_normalize_domain():
    assert normalize_domain("HTTPS://WWW.Example.com/path?x=1") == "example.com"
    assert normalize_domain("http://foo.bar.net.") == "foo.bar.net"
    assert normalize_domain("  Site.COM  ") == "site.com"


def test_validation_and_parse_input():
    p = parse_input("good.com\nwww.good.com\nnot a domain\nhttps://bad-casino.net\n\n")
    # good.com deduped with its www. form
    assert "good.com" in p.domains
    assert p.duplicates == 1
    assert "not a domain".replace(" ", "") not in p.domains
    assert len(p.invalid) == 1          # "not a domain" -> invalid
    assert "bad-casino.net" in p.domains


def test_is_valid_domain():
    assert is_valid_domain("example.com")
    assert is_valid_domain("sub.example.co.uk")
    assert not is_valid_domain("nodot")
    assert not is_valid_domain("bad_underscore.com")


# --- §6 bucket rules -------------------------------------------------------

def c(**kw) -> Classification:
    base = dict(domain="x.com", verdict="good", category="clean",
                name_language="en", is_english_name=True, confidence=0.9)
    base.update(kw)
    return Classification(**base)


def test_bucket_rules_by_verdict_only():
    # Correction 1: language and confidence NO LONGER affect the bucket.
    # error -> review
    assert assign_bucket(c(verdict="error")) == "review"
    # needs_review -> review
    assert assign_bucket(c(needs_review=True)) == "review"
    # bad -> bad (any language)
    assert assign_bucket(c(verdict="bad", is_english_name=False)) == "bad"
    # clean foreign name -> GOOD (was review before the correction)
    assert assign_bucket(c(is_english_name=False)) == "good"
    # low confidence clean -> GOOD (confidence no longer gates)
    assert assign_bucket(c(confidence=0.0)) == "good"
    # clean english -> good
    assert assign_bucket(c()) == "good"


# --- FR-9/FR-10 schema parsing --------------------------------------------

def test_parse_response_tolerates_fences_and_maps_domains():
    content = """```json
    [
      {"domain":"a.com","verdict":"good","category":"clean","is_english_name":true,"confidence":0.9},
      {"domain":"casino-x.net","verdict":"bad","category":"gambling","is_english_name":true,"confidence":0.97,"matched_terms":["casino"]}
    ]
    ```"""
    res = parse_response(content, ["a.com", "casino-x.net"])
    assert res["a.com"].verdict == "good"
    assert res["casino-x.net"].category == "gambling"


def test_parse_response_missing_domain_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_response('[{"domain":"a.com","verdict":"good","category":"clean","is_english_name":true,"confidence":0.9}]',
                       ["a.com", "b.com"])


# --- engine end-to-end (offline MockProvider) -----------------------------

def test_engine_full_run_with_mock(tmp_path):
    store = ClassifierStore(str(tmp_path / "c.db"))
    store.save_settings({"provider": "mock", "batch_size": 2, "concurrency": 2})

    text = "\n".join([
        "cleansite.com",           # good
        "bestcasino.net",          # bad (gambling)
        "medienverbesserer.com",   # foreign but CLEAN name -> good now
        "not a domain",            # invalid -> review (error)
        "pornhub-clone.com",       # bad (adult)
    ])

    async def go():
        mgr = RunManager()
        run_id = mgr.start(store, text, ignore_cache=True)
        await mgr._tasks[run_id]   # await the scheduled task to completion
        return run_id

    run_id = asyncio.run(go())

    run = store.get_run(run_id)
    assert run["status"] == "done"
    assert run["total"] == 5 and run["processed"] == 5
    assert run["bad"] == 2
    assert run["review"] == 1      # only the invalid domain
    assert run["good"] == 2        # clean english + clean foreign name

    results = store.get_results(run_id)
    by = {r["domain"]: r for r in results}
    assert by["bestcasino.net"]["bucket"] == "bad"
    assert by["bestcasino.net"]["category"] == "gambling"
    # Correction 2: a clean foreign name is Good, not Review.
    assert by["medienverbesserer.com"]["bucket"] == "good"


def test_engine_cache_reuse(tmp_path):
    store = ClassifierStore(str(tmp_path / "c.db"))
    store.save_settings({"provider": "mock", "batch_size": 10})

    async def run_once():
        mgr = RunManager()
        rid = mgr.start(store, "cleansite.com", ignore_cache=False)
        await mgr._tasks[rid]
        return rid

    asyncio.run(run_once())          # populates cache
    rid2 = asyncio.run(run_once())   # should hit cache
    logs = " ".join(l["message"] for l in store.get_logs(rid2))
    assert "Кэш" in logs
