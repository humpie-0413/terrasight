"""EPA AirData / AQS connector — ANNUAL trend + rankings (county/CBSA).

Source:  https://aqs.epa.gov/aqsweb/documents/data_api.html
Cadence: annual (pre-generated summary files + AQS API)
Tag:     observed
Geo:     county / CBSA

Used for: Local Reports Block 1 "annual trend", PM2.5 rankings.
Separate from AirNow (current AQI at reporting-area level).
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class AirDataConnector(BaseConnector):
    name = "airdata"
    source = "EPA AirData / AQS"
    source_url = "https://www.epa.gov/outdoor-air-quality-data"
    cadence = "annual"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
