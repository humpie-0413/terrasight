"""EPA ECHO (Enforcement and Compliance History Online) connector.

Source:  https://echo.epa.gov/tools/web-services
Cadence: live feed
Tag:     regulatory (NOT environmental exposure)
Geo:     facility coordinates → aggregated to CBSA

MANDATORY disclaimer wherever this data is shown:
"Regulatory compliance ≠ environmental exposure or health risk."
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class EchoConnector(BaseConnector):
    name = "echo"
    source = "EPA ECHO"
    source_url = "https://echo.epa.gov/"
    cadence = "live feed"
    tag = "observed"  # enforcement records are observed facts

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
