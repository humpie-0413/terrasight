"""NOAA National Weather Service active alerts connector.

Endpoint: https://api.weather.gov/alerts/active
Docs:     https://www.weather.gov/documentation/services-web-api
Cadence:  near-real-time
Tag:      observed
Auth:     none (but User-Agent header is REQUIRED)
Geo:      U.S. + territories

=============================================================================
Response format: GeoJSON-LD FeatureCollection (application/geo+json).

Each feature has:
  - properties.event ("Tornado Warning", "Heat Advisory", etc.)
  - properties.severity ("Extreme"/"Severe"/"Moderate"/"Minor"/"Unknown")
  - properties.certainty, properties.urgency
  - properties.headline, properties.areaDesc
  - properties.onset (ISO datetime), properties.expires (ISO datetime)
  - properties.senderName
  - geometry: Polygon or null (null when zone-based, not geometry-based)

Params supported: status (actual|exercise|system|test|draft),
  message_type (alert|update|cancel), severity, certainty, urgency,
  area (state code), zone, point, region, etc.

=============================================================================
LANDMINE: NWS API REQUIRES a User-Agent header with contact information.
  Without it the server returns HTTP 403 Forbidden. Same UA pattern as the
  ECHO connector.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

ENDPOINT = "https://api.weather.gov/alerts/active"

_UA = "TerraSight/1.0 (environmental data portal; contact: terrasight.pages.dev)"


@dataclass
class WeatherAlert:
    event: str
    severity: str
    certainty: str
    urgency: str
    headline: str
    area_desc: str
    onset: str  # ISO datetime
    expires: str  # ISO datetime
    sender: str


class NwsAlertsConnector(BaseConnector):
    name = "nws_alerts"
    source = "NOAA National Weather Service"
    source_url = "https://www.weather.gov/"
    cadence = "near-real-time"
    tag = "observed"

    async def fetch(
        self,
        status: str = "actual",
        severity: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        params: dict[str, str] = {
            "status": status,
            "message_type": "alert",
        }
        if severity is not None:
            params["severity"] = severity
        timeout = httpx.Timeout(30.0, connect=10.0)
        headers = {"User-Agent": _UA}
        async with httpx.AsyncClient(
            timeout=timeout, headers=headers
        ) as client:
            response = await client.get(ENDPOINT, params=params)
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        features = raw.get("features") or []
        alerts: list[WeatherAlert] = []
        for f in features:
            props = f.get("properties") or {}
            alerts.append(
                WeatherAlert(
                    event=str(props.get("event") or "Unknown"),
                    severity=str(props.get("severity") or "Unknown"),
                    certainty=str(props.get("certainty") or "Unknown"),
                    urgency=str(props.get("urgency") or "Unknown"),
                    headline=str(props.get("headline") or ""),
                    area_desc=str(props.get("areaDesc") or ""),
                    onset=str(props.get("onset") or ""),
                    expires=str(props.get("expires") or ""),
                    sender=str(props.get("senderName") or ""),
                )
            )
        return ConnectorResult(
            values=alerts,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="U.S. + territories",
            license="Public domain (NOAA)",
            notes=[
                "NWS active alerts (status=actual, message_type=alert).",
                "Geometry may be null for zone-based alerts.",
                "NWS API requires User-Agent header with contact info.",
            ],
        )
