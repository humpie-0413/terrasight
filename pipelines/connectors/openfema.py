"""OpenFEMA Disaster Declarations connector — U.S. disaster history.

Endpoint: https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries
Docs:     https://www.fema.gov/about/openfema/data-sets
Cadence:  continuous
Tag:      observed
Auth:     none
Geo:      U.S. states and territories

=============================================================================
Implementation notes:

Uses OData-style query parameters ($filter, $select, $orderby, $top, $skip).

Filter construction:
  - Always include declarationDate gt '{start_date}' (ISO 8601).
  - If a state is provided, add: and state eq '{state}'.
  - State values use the full state name (e.g., 'Texas') for the
    state field in older docs, but the API field `state` actually
    stores the 2-letter abbreviation in the v2 summaries endpoint.
    Both 'TX' and 'Texas' have been tested — use the 2-letter code.

Response structure:
  {"DisasterDeclarationsSummaries": [...], "metadata": {"count": N}}

Landmines:
  - OData filter strings are sensitive to whitespace and quoting.
    Single-quote string values: state eq 'TX'.
  - The v2 API `state` field stores the 2-letter abbreviation (e.g.,
    'TX'), NOT the full state name. Passing 'Texas' returns 0 results.
    Callers should always use 2-letter codes.
  - The API sometimes returns `femaDeclarationString` instead of or
    in addition to `disasterNumber`. Always check for both fields
    and prefer `disasterNumber` when present.
  - Some declarations have null incidentEndDate (event still ongoing
    or end date not recorded). Handle gracefully.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

ENDPOINT = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"

SELECT_FIELDS = (
    "disasterNumber,state,declarationType,declarationDate,"
    "fyDeclared,incidentType,declarationTitle,"
    "incidentBeginDate,incidentEndDate,designatedArea"
)


@dataclass
class DisasterDeclaration:
    disaster_number: int
    state: str
    declaration_type: str
    declaration_date: str
    incident_type: str
    title: str
    incident_begin: str
    incident_end: str
    designated_area: str


class OpenfemaConnector(BaseConnector):
    name = "openfema"
    source = "FEMA"
    source_url = "https://www.fema.gov/disaster/declarations"
    cadence = "continuous"
    tag = "observed"

    async def fetch(
        self,
        state: str | None = None,
        years: int = 5,
        limit: int = 100,
        **_: Any,
    ) -> dict[str, Any]:
        """Fetch disaster declarations from OpenFEMA v2 API."""
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=365 * years)).strftime(
            "%Y-%m-%dT00:00:00.000z"
        )

        # Build OData filter
        odata_filter = f"declarationDate gt '{start_date}'"
        if state:
            odata_filter += f" and state eq '{state}'"

        params: dict[str, Any] = {
            "$filter": odata_filter,
            "$select": SELECT_FIELDS,
            "$orderby": "declarationDate desc",
            "$top": limit,
            "$inlinecount": "allpages",
        }

        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(ENDPOINT, params=params)
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        summaries = raw.get("DisasterDeclarationsSummaries") or []
        declarations: list[DisasterDeclaration] = []
        for d in summaries:
            # Prefer disasterNumber, fall back to femaDeclarationString
            disaster_number = d.get("disasterNumber")
            if disaster_number is None:
                fema_str = d.get("femaDeclarationString", "")
                # Try to extract number from e.g. "DR-4332-TX"
                try:
                    disaster_number = int(
                        "".join(c for c in fema_str.split("-")[1] if c.isdigit())
                    )
                except (IndexError, ValueError):
                    disaster_number = 0

            declarations.append(
                DisasterDeclaration(
                    disaster_number=int(disaster_number),
                    state=str(d.get("state", "")),
                    declaration_type=str(d.get("declarationType", "")),
                    declaration_date=str(d.get("declarationDate", "")),
                    incident_type=str(d.get("incidentType", "")),
                    title=str(d.get("declarationTitle", "")),
                    incident_begin=str(d.get("incidentBeginDate") or ""),
                    incident_end=str(d.get("incidentEndDate") or ""),
                    designated_area=str(d.get("designatedArea", "")),
                )
            )

        return ConnectorResult(
            values=declarations,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="U.S. states and territories",
            license="Public domain (FEMA)",
            notes=[
                "OpenFEMA v2 DisasterDeclarationsSummaries endpoint.",
                "DR = Major Disaster, EM = Emergency, FM = Fire Management.",
                "incidentEndDate may be empty for ongoing events.",
                "State filter uses 2-letter code (e.g., 'TX').",
            ],
        )
