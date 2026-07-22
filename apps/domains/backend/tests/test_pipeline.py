"""Tests anchored to the concrete numbers in the TZ (§3-§8)."""

from __future__ import annotations

import math

from app.ahrefs import parsing
from app.ahrefs.config import merge_with_defaults, validate_config
from app.ahrefs.metrics import DomainRecord
from app.ahrefs.pipeline import analyze, evaluate
from app.ahrefs.scoring import norm
from app.config_defaults import default_config

CFG = default_config()


def row(**over) -> dict:
    """Build a minimal Ahrefs-shaped row; override any field by header name."""
    base = {
        "#": "1", "Target": "example.com/", "Domain Rating": "0",
        "Ref. domains / All": "0", "Ref. domains / Followed": "0",
        "Backlinks / All": "0", "Organic / Traffic": "0",
        "Ref. IPs / IPs": "0", "Ref. IPs / Subnets": "0",
        "Outgoing links / All time": "0", "Organic / Top Countries": "",
    }
    base.update(over)
    return base


# --- §3 parsing ------------------------------------------------------------

def test_to_number_empty_is_zero():
    assert parsing.to_number("") == 0.0
    assert parsing.to_number(None) == 0.0
    assert parsing.to_number("4.5") == 4.5
    assert parsing.to_number("garbage") == 0.0


def test_parse_top_countries():
    assert parsing.parse_top_countries("(mx, 4704)") == ("mx", 4704)
    assert parsing.parse_top_countries("") == (None, None)
    assert parsing.parse_top_countries("(MX, 10)") == ("mx", 10)


def test_parse_tld_examples():
    assert parsing.parse_tld("handfie.com/") == "com"
    assert parsing.parse_tld("diariodelsur.com.co/") == "com.co"
    assert parsing.parse_tld("transparencia.utea.edu.pe/") == "utea.edu.pe"


# --- §4 derived metrics ----------------------------------------------------

def test_derived_metrics_and_zero_division():
    rec = DomainRecord.from_row(row(**{
        "Ref. domains / All": "100", "Ref. domains / Followed": "40",
        "Backlinks / All": "120", "Ref. IPs / IPs": "50",
        "Ref. IPs / Subnets": "30", "Outgoing links / All time": "200",
    }))
    assert rec.fol_share == 40 / 100
    assert rec.bl_rd == 120 / 100
    assert rec.subnet_div == 30 / 50
    assert rec.burn == 200 / 100

    zero = DomainRecord.from_row(row())  # rd_all=0, ips=0
    assert zero.fol_share == 0 and zero.bl_rd == 0
    assert zero.subnet_div == 0 and zero.burn == 0


# --- §5 reject -------------------------------------------------------------

def test_reject_dead():
    r = evaluate(DomainRecord.from_row(row(**{"Domain Rating": "0",
                 "Ref. domains / Followed": "0"})), CFG)
    assert r.tier == "Rejected" and r.reject_reason == "dead"


def test_reject_spam_blast():
    r = evaluate(DomainRecord.from_row(row(**{
        "Domain Rating": "5", "Ref. domains / Followed": "0",
        "Ref. domains / All": "250", "Backlinks / All": "250",
    })), CFG)
    assert r.tier == "Rejected" and r.reject_reason == "spam_blast"


def test_reject_dr_floor():
    # Correction 1а: DR=0 with ~30 followed ref.domains escapes dead/thin,
    # but dr_floor (DR < 0.5) rejects it.
    r = evaluate(DomainRecord.from_row(row(**{
        "Domain Rating": "0", "Ref. domains / Followed": "30",
        "Ref. domains / All": "300", "Backlinks / All": "330",
    })), CFG)
    assert r.tier == "Rejected" and r.reject_reason == "dr_floor"


def test_spam_floor_reject_optional():
    # Off by default -> a DR 1.5 spammy domain passes reject.
    base = row(**{"Domain Rating": "1.5", "Ref. domains / All": "200",
                  "Ref. domains / Followed": "10", "Backlinks / All": "240",
                  "Organic / Traffic": "0"})
    assert evaluate(DomainRecord.from_row(base), CFG).reject_reason is None
    # Enabled -> rejected (fol_share=0.05<0.15, bl_rd=1.2<=1.3, org=0).
    cfg = merge_with_defaults({"reject": {"spam_floor_reject": {"enabled": True}}})
    r = evaluate(DomainRecord.from_row(base), cfg)
    assert r.tier == "Rejected" and r.reject_reason == "spam_floor_reject"


def test_reject_thin():
    r = evaluate(DomainRecord.from_row(row(**{
        "Domain Rating": "1", "Ref. domains / Followed": "1",
        "Ref. domains / All": "5", "Backlinks / All": "3",
    })), CFG)
    assert r.tier == "Rejected" and r.reject_reason == "thin"


def test_reject_burn_hacked():
    r = evaluate(DomainRecord.from_row(row(**{
        "Domain Rating": "5", "Ref. domains / Followed": "5",
        "Ref. domains / All": "10", "Backlinks / All": "10",
        "Outgoing links / All time": "20000", "Organic / Traffic": "0",
    })), CFG)
    assert r.tier == "Rejected" and r.reject_reason == "burn_hacked"


# --- §6 score --------------------------------------------------------------

def test_norm_bounds():
    assert norm(0, 40) == 0.0
    assert 0.99 <= norm(40, 40) <= 1.0
    assert norm(10_000_000, 2000) == 1.0  # clipped, no overflow


def test_score_within_bounds_strong_domain():
    r = evaluate(DomainRecord.from_row(row(**{
        "Domain Rating": "40", "Ref. domains / All": "300",
        "Ref. domains / Followed": "300", "Backlinks / All": "300",
        "Ref. IPs / Subnets": "400", "Ref. IPs / IPs": "400",
        "Organic / Traffic": "2000",
    })), CFG)
    assert r.score is not None and 0 <= r.score <= 100
    assert r.tier == "A"


# --- §7 tiers + CJK override ----------------------------------------------

def test_cjk_forces_review():
    r = evaluate(DomainRecord.from_row(row(**{
        "Domain Rating": "35", "Ref. domains / All": "60",
        "Ref. domains / Followed": "50", "Backlinks / All": "100",
        "Ref. IPs / IPs": "40", "Ref. IPs / Subnets": "35",
        "Organic / Top Countries": "(jp, 5000)",
    })), CFG)
    assert r.flags.cjk is True
    assert r.tier == "Review"
    assert r.tier_override_reason == "cjk"


def test_cjk_action_reject():
    cfg = merge_with_defaults({"flags": {"cjk": {"action": "reject"}}})
    r = evaluate(DomainRecord.from_row(row(**{
        "Domain Rating": "35", "Ref. domains / All": "60",
        "Ref. domains / Followed": "50", "Backlinks / All": "100",
        "Organic / Top Countries": "(cn, 5000)",
    })), cfg)
    assert r.tier == "Rejected" and r.tier_override_reason == "cjk"


# --- §8 flags --------------------------------------------------------------

def test_flag_spam_floor():
    r = evaluate(DomainRecord.from_row(row(**{
        "Domain Rating": "3", "Ref. domains / All": "250",
        "Ref. domains / Followed": "50", "Backlinks / All": "300",
        "Organic / Traffic": "0",
    })), CFG)
    # rd_all=250 in [200,320]; fol_share=0.2<0.35; org=0 -> spam_floor
    assert r.flags.spam_floor is True


def test_flag_geo_review_only_with_allowlist():
    base = row(**{"Domain Rating": "20", "Ref. domains / All": "50",
                  "Ref. domains / Followed": "30", "Backlinks / All": "60",
                  "Organic / Top Countries": "(br, 1000)"})
    r0 = evaluate(DomainRecord.from_row(base), CFG)
    assert r0.flags.geo_review is False  # empty allowlist -> no flag
    cfg = merge_with_defaults({"flags": {"geo": {"allowlist": ["au"]}}})
    r1 = evaluate(DomainRecord.from_row(base), cfg)
    assert r1.flags.geo_review is True   # br not in [au]


# --- §9 config validation --------------------------------------------------

def test_validate_warns_negative_weight_and_nonmonotone_tiers():
    cfg = merge_with_defaults({
        "score": {"weights": {"dr": -1}},
        "tiers": {"A_min": 10, "B_min": 40, "C_min": 28},
    })
    warnings = validate_config(cfg)
    assert any("weights.dr" in w for w in warnings)
    assert any("монотонны" in w for w in warnings)


# --- §10 summary + sort ----------------------------------------------------

def test_analyze_summary_and_sort():
    recs = [
        DomainRecord.from_row(row(Target="a.com/", **{
            "Domain Rating": "40", "Ref. domains / All": "300",
            "Ref. domains / Followed": "300", "Backlinks / All": "300",
            "Ref. IPs / Subnets": "400", "Ref. IPs / IPs": "400",
            "Organic / Traffic": "2000"})),
        DomainRecord.from_row(row(Target="dead.com/", **{
            "Domain Rating": "0", "Ref. domains / Followed": "0"})),
    ]
    rows, summary = analyze(recs, CFG)
    assert rows[-1].tier == "Rejected"          # Rejected sorts last
    assert summary["analyzed"] == 2
    assert summary["tiers"]["Rejected"]["count"] == 1
    assert summary["reject_reasons"]["dead"]["count"] == 1
