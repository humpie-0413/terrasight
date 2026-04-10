"""NASA GIBS / Worldview imagery tile connector.

Source:  https://nasa-gibs.github.io/gibs-api-docs/
Cadence: varies
Tag:     observed / NRT
Note: Base layer = Natural Earth. Used as globe base imagery.
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class GibsConnector(BaseConnector):
    name = "gibs"
    source = "NASA GIBS"
    source_url = "https://nasa-gibs.github.io/gibs-api-docs/"
    cadence = "varies"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
