"""Water Quality Portal (WQP) beta — WQX 3.0 endpoints.

Source:  https://www.waterqualitydata.us/wqx3/ (BETA, WQX 3.0 — USE THIS)
Legacy:  https://www.waterqualitydata.us/data/ (WQX 2.2 — DO NOT USE for USGS)
Cadence: discrete samples (dates vary)
Tag:     observed

=============================================================================
CRITICAL GUARDRAIL (CLAUDE.md + 2026-04-10 API spike, Agent 3):

On 2024-03-11, the WQP legacy endpoint `/data/` transitioned to WQX 2.2 ONLY,
and is MISSING all USGS discrete water-quality samples added or modified
after that date. This is a KNOWN, DOCUMENTED breakage.

We MUST use the `/wqx3/` beta endpoints, NOT `/data/`.
Column names differ between WQX 2.2 and 3.0 — parser must target 3.0 schema.
=============================================================================

Verified endpoints (2026-04-10 spike):
- /wqx3/Result/search          — sample measurements
- /wqx3/Station/search         — monitoring locations
- /wqx3/Activity/search        — field sampling events
- /wqx3/ActivityMetric/search  — metric summaries

Query params: providers=NWIS|STORET, bBox or countycode/statecode,
characteristicName (analyte filter), startDateLo/startDateHi, mimeType.

Display rule: always show "Discrete samples — dates vary".
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

BASE_URL = "https://www.waterqualitydata.us/wqx3/"
RESULT_SEARCH_PATH = "Result/search"

# WQX 3.0 CSV column names (verified 2026-04-11 via live curl against
# /wqx3/Result/search?dataProfile=basicPhysChem&mimeType=csv).
# NOTE: dataProfile=basicPhysChem is REQUIRED — without it the endpoint
# returns HTTP 500.
COL_STATION_ID = "Location_Identifier"
COL_STATION_NAME = "Location_Name"
COL_CHARACTERISTIC = "Result_Characteristic"
COL_RESULT_VALUE = "Result_Measure"
COL_RESULT_UNIT = "Result_MeasureUnit"
COL_ACTIVITY_DATE = "Activity_StartDate"
COL_PROVIDER = "ProviderName"


@dataclass
class WaterQualitySample:
    station_id: str
    station_name: str
    characteristic: str
    result_value: float | None
    result_unit: str
    activity_start_date: str
    provider: str


@dataclass
class WqpSummary:
    sample_count: int
    station_count: int
    characteristics: list[str]
    recent_samples: list[WaterQualitySample] = field(default_factory=list)
    earliest_sample_date: str | None = None
    latest_sample_date: str | None = None


class WqpConnector(BaseConnector):
    name = "wqp"
    source = "Water Quality Portal (WQX 3.0 beta)"
    source_url = BASE_URL
    cadence = "discrete samples — dates vary"
    tag = "observed"

    async def fetch(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
        lookback_days: int = 365,
        **_: Any,
    ) -> str:
        today = date.today()
        start = today - timedelta(days=lookback_days)

        # Use a list of tuples so httpx emits `providers=NWIS&providers=STORET`
        # (repeated param). Passing "NWIS,STORET" as a single comma-joined
        # string silently matches zero rows — the WQP API treats the comma
        # as a literal character, not a delimiter. (Verified 2026-04-11.)
        params: list[tuple[str, str]] = [
            # bBox is sent as a single comma-joined string of floats.
            ("bBox", f"{west},{south},{east},{north}"),
            # NWIS = USGS, STORET = EPA/state partners.
            ("providers", "NWIS"),
            ("providers", "STORET"),
            # WQP expects MM-DD-YYYY dates, NOT ISO.
            ("startDateLo", start.strftime("%m-%d-%Y")),
            ("startDateHi", today.strftime("%m-%d-%Y")),
            # basicPhysChem is the default profile for physical/chemical
            # samples. Omitting dataProfile yields HTTP 500 on Result/search.
            ("dataProfile", "basicPhysChem"),
            ("mimeType", "csv"),
        ]

        timeout = httpx.Timeout(60.0, connect=15.0)
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True
        ) as client:
            response = await client.get(
                BASE_URL + RESULT_SEARCH_PATH, params=params
            )
            response.raise_for_status()
            return response.text

    def normalize(self, raw: str) -> ConnectorResult:
        samples: list[WaterQualitySample] = []
        station_ids: set[str] = set()
        characteristics: set[str] = set()
        earliest: str | None = None
        latest: str | None = None
        sample_count = 0

        if raw and raw.strip():
            reader = csv.DictReader(io.StringIO(raw))
            for row in reader:
                try:
                    station_id = (row.get(COL_STATION_ID) or "").strip()
                    station_name = (row.get(COL_STATION_NAME) or "").strip()
                    characteristic = (row.get(COL_CHARACTERISTIC) or "").strip()
                    unit = (row.get(COL_RESULT_UNIT) or "").strip()
                    activity_date = (row.get(COL_ACTIVITY_DATE) or "").strip()
                    provider = (row.get(COL_PROVIDER) or "").strip()
                    raw_value = (row.get(COL_RESULT_VALUE) or "").strip()
                except (AttributeError, TypeError):
                    # Completely malformed row — skip defensively.
                    continue

                if not characteristic and not station_id:
                    # Blank/garbage row.
                    continue

                sample_count += 1
                if station_id:
                    station_ids.add(station_id)
                if characteristic:
                    characteristics.add(characteristic)

                # Date range tracking (ISO-like "YYYY-MM-DD" strings sort
                # lexicographically).
                if activity_date:
                    if earliest is None or activity_date < earliest:
                        earliest = activity_date
                    if latest is None or activity_date > latest:
                        latest = activity_date

                # Defensive float parse.
                result_value: float | None
                if raw_value == "" or raw_value.lower() in {"nd", "na", "n/a"}:
                    result_value = None
                else:
                    try:
                        result_value = float(raw_value)
                    except (TypeError, ValueError):
                        result_value = None

                samples.append(
                    WaterQualitySample(
                        station_id=station_id or "Unknown",
                        station_name=station_name or "Unknown station",
                        characteristic=characteristic or "Unknown",
                        result_value=result_value,
                        result_unit=unit,
                        activity_start_date=activity_date,
                        provider=provider,
                    )
                )

        # Sort all samples by date descending; empty dates sink to the end.
        samples.sort(
            key=lambda s: s.activity_start_date or "",
            reverse=True,
        )
        recent_samples = samples[:50]

        summary = WqpSummary(
            sample_count=sample_count,
            station_count=len(station_ids),
            characteristics=sorted(characteristics),
            recent_samples=recent_samples,
            earliest_sample_date=earliest,
            latest_sample_date=latest,
        )

        return ConnectorResult(
            values=summary,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Monitoring stations within CBSA bounding box",
            license="Public (USGS NWIS + EPA STORET)",
            notes=[
                "Discrete samples — dates vary.",
                "WQX 3.0 beta endpoint; USGS post-2024-03-11 data requires "
                "this path.",
                "Not suitable for real-time trend detection.",
            ],
        )
