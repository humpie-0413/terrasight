"""EPA ECHO (Enforcement and Compliance History Online) connector.

REST services base: http://ofmpub.epa.gov/echo/
Docs:               https://echo.epa.gov/tools/web-services
Cadence:            live feed
Tag:                observed (enforcement records are observed regulatory facts)
Geo:                facility coordinates → aggregated to CBSA

=============================================================================
⚠️ HTTP ONLY — NOT HTTPS.
2026-04-10 API spike verified: https://ofmpub.epa.gov → 404.
Use http://ofmpub.epa.gov/echo/... exactly. Do not upgrade the scheme.
=============================================================================

Endpoint: echo13_rest_services.get_facilities

Bounding-box parameters: p_c1lon, p_c1lat (west/south), p_c2lon, p_c2lat
(east/north). Output=JSON returns a first response with a QueryID + Totals +
the first N facilities. For count-only Block 3 aggregation we only need the
first response.

Useful qcolumns (per ECHO DFR REST services PDF):
  1  FacSourceID             — facility identifier
  3  FacName                 — facility name
  4  FacStreet + FacCity     — address
  5  FacState + FacZip       — location
  12 FacLat / FacLong        — coordinates
  19 CurrVioFlag             — currently in violation
  22 Over3yrsFormalActions   — formal enforcement actions in past 3 yrs
  23 Over3yrsEnfAmt          — enforcement penalties past 3 yrs ($)

Facility-level violation flags live on each facility object in the first
response — no second QID hop needed for counts.

MANDATORY disclaimer wherever this data is shown:
  "Regulatory compliance ≠ environmental exposure or health risk."
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

# NOTE: HTTP, not HTTPS. HTTPS returns 404. See module docstring.
BASE_URL = "http://ofmpub.epa.gov"
FACILITIES_PATH = "/echo/echo13_rest_services.get_facilities"


@dataclass
class FacilitySummary:
    name: str
    source_id: str
    lat: float | None
    lon: float | None
    in_violation: bool
    formal_actions_3yr: int
    penalties_3yr_usd: float


@dataclass
class EchoSummary:
    total_facilities: int
    in_violation: int
    formal_actions_3yr: int
    penalties_3yr_usd: float
    top_violations: list[FacilitySummary]


class EchoConnector(BaseConnector):
    name = "echo"
    source = "EPA ECHO"
    source_url = "https://echo.epa.gov/"
    cadence = "live feed"
    tag = "observed"

    async def fetch(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
        response_set: int = 10,
        **_: Any,
    ) -> dict[str, Any]:
        params = {
            "output": "JSON",
            "p_c1lon": west,
            "p_c1lat": south,
            "p_c2lon": east,
            "p_c2lat": north,
            # qcolumns: FacName, FacStreet, FacState, FacLat/Long, CurrVioFlag,
            # Over3yrsFormalActions, Over3yrsEnfAmt.
            "qcolumns": "3,4,5,12,19,22,23",
            "responseset": response_set,
        }
        # ECHO is HTTP-only and reportedly slow. 60s is a reasonable ceiling.
        timeout = httpx.Timeout(60.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                BASE_URL + FACILITIES_PATH, params=params
            )
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        results_obj = raw.get("Results") or {}
        facilities = results_obj.get("Facilities") or []
        query_rows = int(results_obj.get("QueryRows") or len(facilities))

        facility_summaries: list[FacilitySummary] = []
        in_violation = 0
        formal_actions_total = 0
        penalties_total = 0.0

        for f in facilities:
            curr_vio = str(f.get("CurrVioFlag") or "").upper() == "Y"
            try:
                actions = int(f.get("Over3yrsFormalActions") or 0)
            except (TypeError, ValueError):
                actions = 0
            try:
                penalties = float(
                    str(f.get("Over3yrsEnfAmt") or "0").replace(",", "")
                )
            except (TypeError, ValueError):
                penalties = 0.0

            if curr_vio:
                in_violation += 1
            formal_actions_total += actions
            penalties_total += penalties

            lat: float | None
            lon: float | None
            try:
                lat = float(f.get("FacLat")) if f.get("FacLat") else None
            except (TypeError, ValueError):
                lat = None
            try:
                lon = float(f.get("FacLong")) if f.get("FacLong") else None
            except (TypeError, ValueError):
                lon = None

            facility_summaries.append(
                FacilitySummary(
                    name=str(f.get("FacName") or "Unknown facility"),
                    source_id=str(f.get("FacSourceID") or ""),
                    lat=lat,
                    lon=lon,
                    in_violation=curr_vio,
                    formal_actions_3yr=actions,
                    penalties_3yr_usd=penalties,
                )
            )

        # "Top violations" = currently-in-violation first, then by action count.
        top = sorted(
            facility_summaries,
            key=lambda fs: (
                1 if fs.in_violation else 0,
                fs.formal_actions_3yr,
                fs.penalties_3yr_usd,
            ),
            reverse=True,
        )[:10]

        summary = EchoSummary(
            total_facilities=query_rows,
            in_violation=in_violation,
            formal_actions_3yr=formal_actions_total,
            penalties_3yr_usd=penalties_total,
            top_violations=top,
        )

        return ConnectorResult(
            values=summary,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Facility coordinates within CBSA bounding box",
            license="Public domain (US EPA ECHO)",
            notes=[
                "Regulatory compliance ≠ environmental exposure or health risk.",
                "Violation and enforcement counts reflect the sampled "
                "response_set, not necessarily every facility in the CBSA.",
                "ECHO is HTTP-only; some deployment regions may be blocked "
                "and degrade gracefully.",
            ],
        )
