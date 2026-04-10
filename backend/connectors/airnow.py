"""AirNow connector — CURRENT AQI (reporting area granularity).

Source:  https://docs.airnowapi.org/
Cadence: hourly
Tag:     observed
Geo:     reporting area (≠ city boundary — must be disclosed in UI)

Used for: Earth Now current AQI overlay, Local Reports Block 1 "current".
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class AirNowConnector(BaseConnector):
    name = "airnow"
    source = "AirNow"
    source_url = "https://www.airnow.gov/"
    cadence = "hourly"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
