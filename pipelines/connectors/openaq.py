"""OpenAQ v3 connector — global air monitor stations (home globe only).

Source:  https://docs.openaq.org/
Cadence: varies (varies per station, typically hourly)
Tag:     observed (aggregated)
Geo:     global
Auth:    X-API-Key header (free registration at https://explore.openaq.org/)

Note: Home globe labels this "Air monitors", NOT "AQI" (AQI is Local Reports only).

=============================================================================
Implementation notes (updated 2026-04-11 — API migration finding):

Endpoint: GET /v3/parameters/2/latest?limit=1000
- parameter_id 2 = PM2.5 in OpenAQ v3
- Returns flat array of {datetime, value, coordinates, sensorsId, locationsId}
- Found: ~25,000 real-time PM2.5 readings globally

MIGRATION NOTE: The original endpoint GET /v3/locations?parameters_id=2
was verified to return sensors with `latest: null` for all stations —
OpenAQ v3 did not carry over latest-reading data into the locations
response. The correct endpoint is /v3/parameters/{id}/latest which
returns actual measurement values.

location_name and country are not available in this endpoint response
(would require a second hop to /v3/locations/{locationsId}). We
synthesize a name from the locationsId to avoid the N+1 call.

Rate limits: 60 req/min, 2000 req/hr, 401 without key, 429 when exceeded.

Graceful degradation:
  If OPENAQ_API_KEY is missing, the endpoint returns `configured: false`
  with registration instructions and an empty station list — the globe
  toggle stays visible but disabled.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

OPENAQ_BASE = "https://api.openaq.org/v3"
PM25_PARAMETER_ID = 2  # PM2.5 in OpenAQ v3 parameter taxonomy


@dataclass
class AirMonitor:
    lat: float
    lon: float
    pm25: float       # µg/m³
    location_name: str
    datetime_utc: str
    country: str | None


class OpenAqConnector(BaseConnector):
    name = "openaq"
    source = "OpenAQ"
    source_url = "https://openaq.org/"
    cadence = "varies (typically hourly)"
    tag = "observed"

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    async def fetch(
        self,
        parameters_id: int = PM25_PARAMETER_ID,
        limit: int = 1000,
        **_: Any,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError(
                "OPENAQ_API_KEY is not configured. Register at "
                "https://explore.openaq.org/ and set OPENAQ_API_KEY in .env."
            )
        # Use /v3/parameters/{id}/latest — the only endpoint that returns
        # actual current measurement values (~25k stations globally).
        url = f"{OPENAQ_BASE}/parameters/{parameters_id}/latest"
        params: dict[str, Any] = {"limit": limit}
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        # /v3/parameters/{id}/latest response: flat list of measurement records.
        # Each record: {datetime:{utc,local}, value, coordinates:{latitude,longitude},
        #               sensorsId, locationsId}
        monitors: list[AirMonitor] = []
        for record in raw.get("results", []):
            coords = record.get("coordinates") or {}
            lat = coords.get("latitude")
            lon = coords.get("longitude")
            if lat is None or lon is None:
                continue

            value = record.get("value")
            if value is None:
                continue
            try:
                pm25_value = float(value)
            except (TypeError, ValueError):
                continue
            # OpenAQ occasionally returns negative or sentinel values (9999).
            if pm25_value < 0 or pm25_value > 1000:
                continue

            dt = record.get("datetime") or {}
            pm25_time = dt.get("utc") or ""

            location_id = record.get("locationsId")
            location_name = f"Monitor #{location_id}" if location_id else "PM2.5 Monitor"

            monitors.append(
                AirMonitor(
                    lat=float(lat),
                    lon=float(lon),
                    pm25=pm25_value,
                    location_name=location_name,
                    datetime_utc=pm25_time,
                    country=None,
                )
            )

        return ConnectorResult(
            values=monitors,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global",
            license="CC BY 4.0 (OpenAQ)",
            notes=[
                "PM2.5 (parameter id 2) latest per-station values.",
                "Home globe label: 'Air monitors' — not AQI (AQI is Local Reports).",
                "Some stations may be stale; a datetime_min filter is not "
                "supported on /v3/locations.",
            ],
        )
