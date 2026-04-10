"""Water Quality Portal (WQP) beta — WQX 3.0 endpoints.

Source:  https://www.waterqualitydata.us/wqx3/ (BETA, WQX 3.0 — USE THIS)
Legacy:  https://www.waterqualitydata.us/data/ (WQX 2.2 — DO NOT USE for USGS)
Cadence: discrete samples (dates vary)
Tag:     observed

=============================================================================
CRITICAL GUARDRAIL (CLAUDE.md + 2026-04-10 API spike, Agent 3):

On 2024-03-11, the WQP legacy endpoint `/data/` transitioned to WQX 2.2 ONLY,
and is MISSING all USGS discrete water-quality samples added or modified
after that date. This is a KNOWN, DOCUMENTED breakage.

We MUST use the `/wqx3/` beta endpoints, NOT `/data/`.
Column names differ between WQX 2.2 and 3.0 — parser must target 3.0 schema.
=============================================================================

Verified endpoints (2026-04-10 spike):
- /wqx3/Result/search          — sample measurements
- /wqx3/Station/search         — monitoring locations
- /wqx3/Activity/search        — field sampling events
- /wqx3/ActivityMetric/search  — metric summaries

Query params: providers=NWIS|STORET, bBox or countycode/statecode,
characteristicName (analyte filter), startDateLo/startDateHi, mimeType.

Display rule: always show "Discrete samples — dates vary".
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult

BASE_URL = "https://www.waterqualitydata.us/wqx3/"


class WqpConnector(BaseConnector):
    name = "wqp"
    source = "Water Quality Portal (WQX 3.0 beta)"
    source_url = BASE_URL
    cadence = "discrete samples — dates vary"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
