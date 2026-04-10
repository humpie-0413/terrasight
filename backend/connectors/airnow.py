"""AirNow connector — CURRENT AQI (reporting area granularity).

Source:  https://docs.airnowapi.org/
Cadence: hourly
Tag:     observed
Geo:     reporting area (≠ city boundary — must be disclosed in UI)

Used for: Local Reports Block 1 "current", Earth Now overlay (future).

=============================================================================
Verified endpoint (2026-04-10 local reports spike):
  ✅ https://www.airnowapi.org/aq/observation/zipCode/current/

Query params:
  format=application/json   (required)
  zipCode=77002             (required)
  distance=25               (optional, miles radius — default 25)
  API_KEY=<key>             (required)

Response: list of per-pollutant observations for the requested ZIP.
Each element carries DateObserved, HourObserved, ReportingArea, StateCode,
Latitude, Longitude, ParameterName ("O3" / "PM2.5" / "PM10"), AQI, Category.

The connector picks the WORST observation (max AQI) and returns it — that
matches how AirNow itself summarizes a reporting area.

Rate limit: ~500 requests/hour per key per endpoint (community-documented).
Graceful degradation: when AIRNOW_API_KEY is missing, fetch() raises and
the API layer returns `configured: false` with registration instructions
instead of a 5xx.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

AIRNOW_ZIP_URL = "https://www.airnowapi.org/aq/observation/zipCode/current/"


@dataclass
class AirNowReading:
    aqi: int
    category: str
    category_number: int
    pollutant: str          # "O3", "PM2.5", "PM10"
    reporting_area: str     # e.g. "Houston"
    state_code: str
    lat: float
    lon: float
    observed_at: str        # "YYYY-MM-DD HH:00 TZ"


class AirNowConnector(BaseConnector):
    name = "airnow"
    source = "AirNow"
    source_url = "https://www.airnow.gov/"
    cadence = "hourly"
    tag = "observed"

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    async def fetch(
        self,
        zip_code: str,
        distance: int = 25,
        **_: Any,
    ) -> list[dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError(
                "AIRNOW_API_KEY is not configured. Register at "
                "https://docs.airnowapi.org/ and set AIRNOW_API_KEY in .env."
            )
        params = {
            "format": "application/json",
            "zipCode": zip_code,
            "distance": distance,
            "API_KEY": self.api_key,
        }
        timeout = httpx.Timeout(20.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(AIRNOW_ZIP_URL, params=params)
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: list[dict[str, Any]]) -> ConnectorResult:
        readings: list[AirNowReading] = []
        for obs in raw or []:
            try:
                aqi = int(obs.get("AQI") or -1)
            except (TypeError, ValueError):
                continue
            if aqi < 0:
                continue
            category = obs.get("Category") or {}
            readings.append(
                AirNowReading(
                    aqi=aqi,
                    category=str(category.get("Name") or ""),
                    category_number=int(category.get("Number") or 0),
                    pollutant=str(obs.get("ParameterName") or ""),
                    reporting_area=str(obs.get("ReportingArea") or ""),
                    state_code=str(obs.get("StateCode") or ""),
                    lat=float(obs.get("Latitude") or 0.0),
                    lon=float(obs.get("Longitude") or 0.0),
                    observed_at=(
                        f"{str(obs.get('DateObserved') or '').strip()} "
                        f"{str(obs.get('HourObserved') or '').rjust(2, '0')}:00 "
                        f"{obs.get('LocalTimeZone') or ''}"
                    ).strip(),
                )
            )

        return ConnectorResult(
            values=readings,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Reporting area (≠ city boundary)",
            license="Public (AirNow, US EPA)",
            notes=[
                "AQI reflects the reporting area, not a neighborhood.",
                "Readings come from the station(s) closest to the ZIP code.",
                "The 'current' value is typically the worst pollutant of the hour.",
            ],
        )


def worst_reading(readings: list[AirNowReading]) -> AirNowReading | None:
    """Return the pollutant with the highest AQI (the 'headline' value)."""
    if not readings:
        return None
    return max(readings, key=lambda r: r.aqi)
