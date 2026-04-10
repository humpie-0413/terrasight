"""OpenAQ connector — global air quality monitors (home globe only).

Source:  https://docs.openaq.org/
Cadence: varies
Tag:     observed (aggregated)
Geo:     global

Note: Home globe labels this "Air monitors", NOT "AQI".
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class OpenAqConnector(BaseConnector):
    name = "openaq"
    source = "OpenAQ"
    source_url = "https://openaq.org/"
    cadence = "varies"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
