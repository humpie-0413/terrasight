"""Contract tests for the FIRMS v2 connector.

Locks the `EventPoint` shape produced by `FirmsConnector.normalize()`
against the pydantic contract mirror in `pipelines.contracts`.

Run:
    python -m pytest pipelines/tests/test_firms_contract.py -v
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipelines.connectors.base import ConnectorResult
from pipelines.connectors.firms import FirmsConnector, detect_error_body
from pipelines.contracts import EventPoint

FIXTURES = Path(__file__).parent / "fixtures" / "firms"


# ---------------------------------------------------------------------------
# D3 requirement 1: load sample-normalized.json and validate every row
# against the pydantic EventPoint model.
# ---------------------------------------------------------------------------


def test_sample_normalized_rows_match_eventpoint_contract() -> None:
    payload = json.loads((FIXTURES / "sample-normalized.json").read_text(encoding="utf-8"))
    rows = payload["data"]
    assert len(rows) == 10, "fixture should have exactly 10 rows"
    for i, row in enumerate(rows):
        ev = EventPoint.model_validate(row)
        assert ev.type == "wildfire", f"row {i}: type must be wildfire"
        assert -90.0 <= ev.lat <= 90.0, f"row {i}: lat out of range"
        assert -180.0 <= ev.lon <= 180.0, f"row {i}: lon must be -180..180"
        assert ev.observedAt.endswith("Z"), f"row {i}: observedAt must be ISO-8601 UTC"
        assert "FRP" in ev.label, f"row {i}: label must include FRP"
        # properties is a dict and must carry the documented sub-fields
        assert "confidence_raw" in ev.properties
        assert "daynight" in ev.properties


# ---------------------------------------------------------------------------
# D3 requirement 2: empty CSV → ConnectorResult(status='ok', values=[]).
# ---------------------------------------------------------------------------


def test_empty_feed_normalizes_to_ok_empty_list() -> None:
    payload = json.loads((FIXTURES / "empty-feed.json").read_text(encoding="utf-8"))
    raw_csv = payload["raw_csv"]
    result = FirmsConnector().normalize(raw_csv)
    assert isinstance(result, ConnectorResult)
    assert result.status == "ok"
    assert result.values == []
    assert result.tag == "near-real-time"
    assert result.source == "NASA FIRMS"


# ---------------------------------------------------------------------------
# D3 requirement 3: auth-error body → ConnectorResult(status='error', ...)
# without raising.
# ---------------------------------------------------------------------------


def test_auth_error_body_normalizes_to_error_status() -> None:
    payload = json.loads((FIXTURES / "auth-error.json").read_text(encoding="utf-8"))
    raw_body = payload["raw_body"]
    # First: the standalone detector should flag it.
    assert detect_error_body(raw_body) == "Invalid MAP_KEY"
    # And normalize() must not raise; it must return status="error".
    result = FirmsConnector().normalize(raw_body)
    assert result.status == "error"
    assert result.values == []
    assert any("Invalid MAP_KEY" in n for n in result.notes)


# ---------------------------------------------------------------------------
# Extra guardrails — normalization of a tiny synthetic CSV feeding through
# the pipeline end-to-end, so we catch drift in label format, id hashing,
# and time-padding in one place.
# ---------------------------------------------------------------------------


SYNTHETIC_CSV = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,"
    "satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
    "-15.2341,-47.8812,347.12,0.42,0.38,2026-04-16,130,N,VIIRS,n,2.0NRT,308.45,42.7,N\n"
    "34.8823,-118.4412,322.60,0.39,0.36,2026-04-16,1022,N,VIIRS,l,2.0NRT,298.30,8.4,D\n"
)


def test_synthetic_csv_normalizes_to_eventpoints() -> None:
    result = FirmsConnector().normalize(SYNTHETIC_CSV)
    assert result.status == "ok"
    assert len(result.values) == 2

    # Row 0 — acq_time=130 must be zero-padded to 0130 → 01:30Z
    row0 = result.values[0]
    assert row0["observedAt"] == "2026-04-16T01:30:00Z", (
        "acq_time='130' must pad to HH:MM='01:30'"
    )
    assert row0["type"] == "wildfire"
    assert row0["severity"] == pytest.approx(42.7)
    assert row0["label"] == "FRP 42.7 MW \u00b7 nominal"
    assert row0["properties"]["confidence_raw"] == "n"
    # Validate against the pydantic EventPoint to double-lock the contract.
    EventPoint.model_validate(row0)

    row1 = result.values[1]
    assert row1["observedAt"] == "2026-04-16T10:22:00Z"
    assert row1["label"] == "FRP 8.4 MW \u00b7 low"
    EventPoint.model_validate(row1)


def test_stable_id_is_deterministic_across_runs() -> None:
    """Hashing lat|lon|acq_date|acq_time must be stable so dedupe works
    across Worker cache windows."""
    ids_a = [e["id"] for e in FirmsConnector().normalize(SYNTHETIC_CSV).values]
    ids_b = [e["id"] for e in FirmsConnector().normalize(SYNTHETIC_CSV).values]
    assert ids_a == ids_b
    assert len(set(ids_a)) == 2  # distinct fires → distinct ids
