"""OpenAQ v3 connector — global air monitor stations (home globe only).

Source:  https://docs.openaq.org/
Cadence: varies (varies per station, typically hourly)
Tag:     observed (aggregated)
Geo:     global
Auth:    X-API-Key header (free registration at https://explore.openaq.org/)

Note: Home globe labels this "Air monitors", NOT "AQI" (AQI is Local Reports only).

=============================================================================
Implementation notes (verified 2026-04-10 via API docs subagent):

Endpoint: GET /v3/locations?parameters_id=2&limit=1000
- parameters_id=2 → PM2.5 in OpenAQ v3
- Returns Location objects with `sensors[].latest.{datetime, value}`,
  `coordinates.{latitude, longitude}`, and human-readable `name`.
- One request gives us {name, lat, lon, pm25_latest} without a second
  hop to `/v3/measurements` or `/v3/latest`. Trade-off: no `datetime_min`
  filter, so we may see a handful of stale stations — acceptable for a
  globe overview.

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
        url = f"{OPENAQ_BASE}/locations"
        params = {
            "parameters_id": parameters_id,
            "limit": limit,
        }
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
        monitors: list[AirMonitor] = []
        for loc in raw.get("results", []):
            coords = loc.get("coordinates") or {}
            lat = coords.get("latitude")
            lon = coords.get("longitude")
            if lat is None or lon is None:
                continue

            # Pick the PM2.5 sensor's latest reading from `sensors[]`.
            pm25_value: float | None = None
            pm25_time: str = ""
            for sensor in loc.get("sensors") or []:
                param = sensor.get("parameter") or {}
                if param.get("id") != PM25_PARAMETER_ID:
                    continue
                latest = sensor.get("latest") or {}
                value = latest.get("value")
                if value is None:
                    continue
                try:
                    pm25_value = float(value)
                except (TypeError, ValueError):
                    continue
                dt = latest.get("datetime") or {}
                pm25_time = dt.get("utc") or ""
                break

            if pm25_value is None:
                continue
            # OpenAQ occasionally returns negative values from sensor glitches.
            if pm25_value < 0:
                continue

            country = None
            country_obj = loc.get("country") or {}
            if isinstance(country_obj, dict):
                country = country_obj.get("name") or country_obj.get("code")

            monitors.append(
                AirMonitor(
                    lat=float(lat),
                    lon=float(lon),
                    pm25=pm25_value,
                    location_name=str(loc.get("name") or "Unknown station"),
                    datetime_utc=pm25_time,
                    country=country,
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
