"""Copernicus CAMS (Atmosphere Monitoring Service) connector.

Source:  https://atmosphere.copernicus.eu/
Cadence: 6-12h
Tag:     forecast/model
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class CamsConnector(BaseConnector):
    name = "cams"
    source = "Copernicus CAMS"
    source_url = "https://atmosphere.copernicus.eu/"
    cadence = "6-12h"
    tag = "forecast"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
