"""US Drought Monitor (USDM) connector.

Endpoints:
  National: https://usdmdataservices.unl.edu/api/USStatistics/GetDroughtSeverityStatisticsByAreaPercent
  State:    https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent
Docs:     https://droughtmonitor.unl.edu/DmData/DataDownload/WebServiceInfo.aspx
Cadence:  weekly (Thursday)
Tag:      observed
Auth:     none
Geo:      CONUS

=============================================================================
Response format: JSON array of objects (requires Accept: application/json).
Each object has camelCase keys:
  - mapDate (ISO datetime string, e.g. "2023-06-27T00:00:00")
  - none (% area in no drought)
  - d0 (% abnormally dry), d1 (moderate), d2 (severe),
    d3 (extreme), d4 (exceptional drought)
  - validStart, validEnd (ISO datetime strings)
  - For USStatistics: areaOfInterest ("CONUS")
  - For StateStatistics: stateAbbreviation ("TX", etc.)

Params:
  - aoi: "US" for national (USStatistics), or a 2-digit state FIPS code
    (StateStatistics)
  - startdate, enddate: MM/DD/YYYY format
  - statisticsType: 1 (by area), 2 (by population)

=============================================================================
LANDMINE: Date format is MM/DD/YYYY, NOT ISO-8601.
  The API returns an empty array silently if dates use YYYY-MM-DD or any
  other format. Always use strftime("%m/%d/%Y").

LANDMINE: The default response Content-Type is text/csv with empty body.
  You MUST send Accept: application/json header to get JSON responses.

LANDMINE: National data uses USStatistics endpoint, not StateStatistics
  with aoi=US. StateStatistics with aoi=US returns [].

LANDMINE: Field names are camelCase (mapDate, validStart, d0, none) —
  NOT PascalCase (MapDate, ValidStart, D0, None) as some older docs show.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

_BASE = "https://usdmdataservices.unl.edu/api"
_SUFFIX = "/GetDroughtSeverityStatisticsByAreaPercent"
_US_ENDPOINT = f"{_BASE}/USStatistics{_SUFFIX}"
_STATE_ENDPOINT = f"{_BASE}/StateStatistics{_SUFFIX}"


@dataclass
class DroughtStats:
    map_date: str
    fips: str
    none_pct: float
    d0_pct: float
    d1_pct: float
    d2_pct: float
    d3_pct: float
    d4_pct: float
    valid_start: str
    valid_end: str


class UsdmConnector(BaseConnector):
    name = "usdm"
    source = "US Drought Monitor (UNL/USDA/NOAA)"
    source_url = "https://droughtmonitor.unl.edu/"
    cadence = "weekly (Thursday)"
    tag = "observed"

    async def fetch(
        self,
        aoi: str = "US",
        weeks: int = 4,
        **_: Any,
    ) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        enddate = now.strftime("%m/%d/%Y")
        startdate = (now - timedelta(days=weeks * 7)).strftime("%m/%d/%Y")

        # National data uses USStatistics; state data uses StateStatistics.
        is_national = aoi.upper() == "US"
        endpoint = _US_ENDPOINT if is_national else _STATE_ENDPOINT

        params: dict[str, str] = {
            "aoi": aoi,
            "startdate": startdate,
            "enddate": enddate,
            "statisticsType": "1",
        }
        timeout = httpx.Timeout(30.0, connect=10.0)
        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: list[dict[str, Any]]) -> ConnectorResult:
        stats: list[DroughtStats] = []
        for row in raw:
            try:
                none_pct = float(row.get("none") or 0.0)
                d0 = float(row.get("d0") or 0.0)
                d1 = float(row.get("d1") or 0.0)
                d2 = float(row.get("d2") or 0.0)
                d3 = float(row.get("d3") or 0.0)
                d4 = float(row.get("d4") or 0.0)
            except (TypeError, ValueError):
                continue
            # Identify the area: national returns areaOfInterest, state
            # returns stateAbbreviation.
            fips = str(
                row.get("stateAbbreviation")
                or row.get("areaOfInterest")
                or row.get("fips")
                or ""
            )
            stats.append(
                DroughtStats(
                    map_date=str(row.get("mapDate") or ""),
                    fips=fips,
                    none_pct=none_pct,
                    d0_pct=d0,
                    d1_pct=d1,
                    d2_pct=d2,
                    d3_pct=d3,
                    d4_pct=d4,
                    valid_start=str(row.get("validStart") or ""),
                    valid_end=str(row.get("validEnd") or ""),
                )
            )
        return ConnectorResult(
            values=stats,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="CONUS",
            license="Public domain",
            notes=[
                "US Drought Monitor drought severity by area percent.",
                "D0=abnormally dry, D1=moderate, D2=severe, D3=extreme, D4=exceptional.",
                "Date params must be MM/DD/YYYY — API silently returns [] for other formats.",
                "Must send Accept: application/json — default response is empty text/csv.",
                "National data uses USStatistics endpoint; state data uses StateStatistics.",
            ],
        )
