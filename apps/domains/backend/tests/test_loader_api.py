"""Loader (§2, §11) and API smoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.ahrefs import loader
from app.main import app

HEADER = [
    "#", "Target", "Domain Rating", "Ref. domains / All",
    "Ref. domains / Followed", "Backlinks / All", "Organic / Top Countries",
]


def _utf8_comma() -> bytes:
    lines = [
        ",".join(HEADER),
        '1,handfie.com/,40,300,300,300,"(mx, 4704)"',
        '2,dead.com/,0,0,0,0,',
        '2,dead.com/,0,0,0,0,',  # duplicate Target
    ]
    return ("\n".join(lines)).encode("utf-8")


def _utf16_tab() -> bytes:
    lines = [
        "\t".join(HEADER),
        "1\thandfie.com/\t40\t300\t300\t300\t(mx, 4704)",
        "2\tdead.com/\t0\t0\t0\t0\t",
    ]
    return ("\n".join(lines)).encode("utf-16")


def test_loader_utf8_comma_dedup():
    res = loader.parse_file(_utf8_comma())
    assert len(res.records) == 2          # duplicate removed
    assert res.duplicates_removed == 1
    assert res.records[0].cc == "mx"


def test_loader_utf16_tab():
    res = loader.parse_file(_utf16_tab())
    assert len(res.records) == 2
    assert res.records[0].target == "handfie.com/"


def test_loader_missing_required_column_errors():
    bad = "Target,Domain Rating\nx.com/,10\n".encode("utf-8")
    with pytest.raises(loader.LoadError):
        loader.parse_file(bad)


def test_api_upload_analyze_export_bridge():
    client = TestClient(app)
    assert client.get("/api/health").json()["status"] == "ok"

    up = client.post(
        "/api/ahrefs/datasets",
        files={"file": ("export.csv", _utf8_comma(), "text/csv")},
    )
    assert up.status_code == 200
    ds_id = up.json()["dataset_id"]
    assert up.json()["duplicates_removed"] == 1

    an = client.post(f"/api/ahrefs/datasets/{ds_id}/analyze", json={"config": None})
    body = an.json()
    assert body["summary"]["analyzed"] == 2
    assert len(body["rows"]) == 2

    ex = client.post(
        f"/api/ahrefs/datasets/{ds_id}/export",
        json={"format": "csv", "include_raw": False},
    )
    assert ex.status_code == 200
    assert ex.text.splitlines()[0].startswith("Target,tier,score")

    br = client.post(f"/api/ahrefs/datasets/{ds_id}/targets?tiers=A,B,C", json={})
    assert "handfie.com/" in br.json()["targets"]


def test_config_default_and_validate():
    client = TestClient(app)
    assert "reject" in client.get("/api/config/default").json()["config"]
    v = client.post("/api/config/validate", json={"config": {"tiers": {"A_min": 1, "B_min": 9, "C_min": 5}}})
    assert v.json()["warnings"]
