"""Contract test for UsgsConnector — validates the EventPoint shape, the
mag-null filter, the ms-epoch -> ISO-8601 conversion, and the severity
class distribution.

Fixtures live in `pipelines/tests/fixtures/usgs/`.
Run: `python -m pytest pipelines/tests/test_usgs_contract.py -v`.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pipelines.connectors.base import ConnectorResult
from pipelines.connectors.usgs import UsgsConnector
from pipelines.contracts import EventPoint

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "usgs"
ALL_DAY_FIXTURE = FIXTURE_DIR / "earthquakes-all-day.json"
EMPTY_FIXTURE = FIXTURE_DIR / "empty-feed.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_normalize_all_day_filters_null_mag_and_shapes_match_eventpoint() -> None:
    raw = _load(ALL_DAY_FIXTURE)
    assert len(raw["features"]) == 15, (
        "Fixture invariant: exactly 15 features expected in the trimmed "
        "fixture; if this changes, update the test expectation."
    )

    result = UsgsConnector().normalize(raw)

    # ConnectorResult: ok status, envelope metadata correct.
    assert isinstance(result, ConnectorResult)
    assert result.status == "ok"
    assert result.source == "USGS Earthquake"
    assert result.tag == "observed"
    assert result.cadence == "5 min"
    assert result.spatial_scope == "global"
    assert result.license == "public domain"

    # The 1 mag=null feature must be filtered out -> 14 normalized rows.
    assert len(result.values) == 14, (
        "Expected 14 rows after filtering the 1 mag=null synthesized "
        f"feature; got {len(result.values)}"
    )

    # Every row must validate against the shared EventPoint schema.
    for row in result.values:
        EventPoint.model_validate(row)

    # The mag=null feature's id must NOT appear in the output.
    output_ids = {row["id"] for row in result.values}
    assert "test_null_mag_01" not in output_ids


def test_observed_at_is_iso8601_not_epoch_ms() -> None:
    raw = _load(ALL_DAY_FIXTURE)
    result = UsgsConnector().normalize(raw)

    for row in result.values:
        ts = row["observedAt"]
        assert isinstance(ts, str)
        # ISO-8601 UTC string. The connector writes "Z" suffix.
        # datetime.fromisoformat accepts "Z" in Python 3.11+.
        parsed = datetime.fromisoformat(ts)
        assert parsed.year >= 2020, (
            f"observedAt parsed to year {parsed.year}; almost certainly "
            "an epoch-ms value leaked through (landmine #1)."
        )
        assert parsed.year <= 2100


def test_severity_class_is_one_of_the_four_known_classes() -> None:
    raw = _load(ALL_DAY_FIXTURE)
    result = UsgsConnector().normalize(raw)

    known = {"major", "moderate", "light", "micro"}
    classes: dict[str, int] = {}
    for row in result.values:
        sc = row["properties"]["severity_class"]
        assert sc in known, f"Unexpected severity_class: {sc!r}"
        classes[sc] = classes.get(sc, 0) + 1

    # Fixture-determined distribution. If the fixture is reshuffled, these
    # counts need updating — but there must always be at least one major
    # (mag >= 6) and at least one moderate (4.5 <= mag < 6) by design.
    assert classes.get("major", 0) >= 1, (
        "Fixture must contain at least one feature with mag >= 6."
    )
    assert classes.get("moderate", 0) >= 1, (
        "Fixture must contain at least one feature with 4.5 <= mag < 6."
    )


def test_coordinates_order_lon_lat_not_lat_lon() -> None:
    """Landmine #2 regression: GeoJSON coords are [lon, lat, depth].

    In the fixture the first real feature is `us6000sqta` (mag 5.4,
    northern Mid-Atlantic Ridge). Mid-Atlantic Ridge implies longitude
    near 0 and latitude between -60 and 60. If lat/lon were swapped we
    would see lat closer to 0 and lon in the high ranges.
    """
    raw = _load(ALL_DAY_FIXTURE)
    result = UsgsConnector().normalize(raw)

    first = next(row for row in result.values if row["id"] == "us6000sqta")
    assert -90.0 <= first["lat"] <= 90.0
    assert -180.0 <= first["lon"] <= 180.0


def test_label_is_truncated_to_80_chars() -> None:
    raw = _load(ALL_DAY_FIXTURE)
    result = UsgsConnector().normalize(raw)
    for row in result.values:
        assert len(row["label"]) <= 80


def test_tsunami_flag_preserved_as_int() -> None:
    raw = _load(ALL_DAY_FIXTURE)
    result = UsgsConnector().normalize(raw)
    tsu_row = next(row for row in result.values if row["id"] == "test_tsunami_01")
    assert tsu_row["properties"]["tsunami"] == 1


def test_empty_feed_returns_ok_with_empty_values() -> None:
    raw = _load(EMPTY_FIXTURE)
    result = UsgsConnector().normalize(raw)
    assert result.status == "ok"
    assert result.values == []
