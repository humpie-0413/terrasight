"""NASA FIRMS (Fire Information for Resource Management System) connector.

Source:  https://firms.modaps.eosdis.nasa.gov/
Cadence: near-real-time (~3h)
Tag:     observed
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class FirmsConnector(BaseConnector):
    name = "firms"
    source = "NASA FIRMS"
    source_url = "https://firms.modaps.eosdis.nasa.gov/"
    cadence = "NRT ~3h"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
