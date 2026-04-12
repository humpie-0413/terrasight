"""USGS FDSNWS ComCat earthquake connector.

Endpoint: https://earthquake.usgs.gov/fdsnws/event/1/query
Docs:     https://earthquake.usgs.gov/fdsnws/event/1/
Cadence:  near-real-time (~5 min)
Tag:      observed
Auth:     none
Geo:      Global

=============================================================================
Response format: GeoJSON FeatureCollection.
Each feature has:
  - properties.mag, properties.place, properties.time (epoch ms),
    properties.url, properties.type, properties.tsunami (0|1)
  - geometry.coordinates [lon, lat, depth_km]

The endpoint supports `format=geojson`, `limit`, `minmagnitude`, `orderby`,
`starttime` (ISO 8601), and `endtime` (ISO 8601).

No auth required. Rate limits are generous but undocumented; the API
returns HTTP 503 under heavy load — retry with backoff if needed.

Landmine: `starttime` and `endtime` must be ISO-8601 (YYYY-MM-DD).
  Using other date formats returns HTTP 400.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"


@dataclass
class Earthquake:
    lat: float
    lon: float
    depth_km: float
    magnitude: float
    place: str
    time_utc: str  # ISO 8601
    event_url: str
    tsunami: bool


class EarthquakeConnector(BaseConnector):
    name = "earthquake"
    source = "USGS Earthquake Hazards Program"
    source_url = "https://earthquake.usgs.gov/"
    cadence = "near-real-time (~5 min)"
    tag = "observed"

    async def fetch(
        self,
        min_magnitude: float = 4.0,
        limit: int = 500,
        days: int = 30,
        **_: Any,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        starttime = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        params = {
            "format": "geojson",
            "limit": limit,
            "minmagnitude": min_magnitude,
            "orderby": "time",
            "starttime": starttime,
        }
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(ENDPOINT, params=params)
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        features = raw.get("features") or []
        earthquakes: list[Earthquake] = []
        for f in features:
            props = f.get("properties") or {}
            coords = (f.get("geometry") or {}).get("coordinates") or [0, 0, 0]
            try:
                lon = float(coords[0])
                lat = float(coords[1])
                depth_km = float(coords[2]) if len(coords) > 2 else 0.0
                magnitude = float(props.get("mag") or 0.0)
            except (TypeError, ValueError):
                continue
            time_epoch_ms = props.get("time")
            if time_epoch_ms is not None:
                time_utc = datetime.fromtimestamp(
                    time_epoch_ms / 1000, tz=timezone.utc
                ).isoformat()
            else:
                time_utc = ""
            earthquakes.append(
                Earthquake(
                    lat=lat,
                    lon=lon,
                    depth_km=depth_km,
                    magnitude=magnitude,
                    place=str(props.get("place") or "Unknown"),
                    time_utc=time_utc,
                    event_url=str(props.get("url") or ""),
                    tsunami=bool(props.get("tsunami")),
                )
            )
        return ConnectorResult(
            values=earthquakes,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global",
            license="Public domain (USGS)",
            notes=[
                "USGS ComCat earthquake catalog via FDSNWS event/1 API.",
                "Ordered by time descending; magnitude and depth from authoritative origin.",
                "Tsunami flag indicates whether the event triggered a tsunami alert (0/1).",
            ],
        )
