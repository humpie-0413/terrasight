"""Water Quality Portal (WQP) beta API + USGS modernized endpoints.

Source:  https://www.waterqualitydata.us/
Cadence: discrete samples (dates vary)
Tag:     observed

CRITICAL (CLAUDE.md guardrail):
- WQP UI export is WQX 2.2 ONLY, and is MISSING USGS data after 2024-03-11.
- MUST hit WQP beta API + USGS modernized endpoints directly, NOT UI export.

Display rule: always show "Discrete samples — dates vary".
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class WqpConnector(BaseConnector):
    name = "wqp"
    source = "Water Quality Portal (beta API) + USGS modernized"
    source_url = "https://www.waterqualitydata.us/"
    cadence = "discrete samples — dates vary"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
