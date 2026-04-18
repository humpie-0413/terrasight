"""EPA RCRA Biennial Report connector — Envirofacts REST.

Source:  https://www.epa.gov/hwgenerators
Base:    https://data.epa.gov/efservice/
Table:   BR_REPORTING
Cadence: biennial (every 2 years — most recent report_cycle = 2023)
Tag:     observed (self-reported under RCRA)
Auth:    none
Geo:     US facilities, state-filtered

=============================================================================
IMPLEMENTATION NOTES (verified 2026-04-12)

Primary table: `BR_REPORTING` (RCRA Biennial Report)
    Verified working URL:
        https://data.epa.gov/efservice/BR_REPORTING/activity_location/TX/rows/0:10/JSON
    Column names (confirmed from probe):
      - handler_id            (str)   -- EPA handler ID
      - handler_name          (str)   -- facility / handler name
      - activity_location     (str)   -- 2-letter state code (USE for filtering)
      - location_city         (str)
      - location_state        (str)
      - county_name           (str)
      - generation_tons       (str)   -- STRING, needs float coercion
      - report_cycle          (int)   -- biennial reporting year (NOT "year")
      - primary_naics         (str)
      - description           (str)   -- waste description
      - source_code           (str)
      - form_code             (str)
      - management_method     (str)
      - management_category   (str)   -- e.g., "LANDFILL", "FUEL BLENDING"

=============================================================================
LANDMINES

1. **No lat/lon.** BR_REPORTING has NO latitude/longitude columns.
   lat and lon on RcraHandler are always None from this table.
   Cross-referencing with a geocoded RCRA handler table would require
   a second hop — deferred.

2. **Rows are per-waste-stream, not per-facility.** A single
   handler_id can appear many times (once per waste form/page). The
   connector returns raw rows without aggregation so the caller can
   decide how to roll up.

3. **State filter column.** Use `activity_location` (NOT `state` or
   `location_state`). The `state` column also works but
   `activity_location` was tested and confirmed first.

4. **generation_tons is a string.** Envirofacts returns numeric
   fields as strings — must coerce with _coerce_float.

5. **report_cycle, not year.** The biennial year column is named
   `report_cycle`, not `year`. Filtering uses
   `/report_cycle/{year}`.

6. **Dead host.** Legacy `iaspub.epa.gov/enviro/efservice/` is gone.
   Use `data.epa.gov/efservice/` only.

7. **Mandatory pagination slug + JSON token.** Always append
   `/rows/{first}:{last}/JSON` or you get XML or a timeout.

8. **Accept header.** Set `Accept: application/json`.

9. **Server-side 500 on large states without report_cycle.**
   Querying `activity_location/TX/rows/0:N/JSON` without a
   `report_cycle` filter returns HTTP 500 — the Envirofacts
   server-side query times out on states with many rows. Always
   include `/report_cycle/{year}` in the URL. The connector
   defaults to DEFAULT_REPORT_CYCLE (2023) when year is None.

=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

EFSERVICE_BASE = "https://data.epa.gov/efservice"
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# 2023 is the most recent biennial report cycle as of 2026-04-12.
DEFAULT_REPORT_CYCLE = 2023


@dataclass
class RcraHandler:
    name: str                      # handler_name
    handler_id: str | None         # handler_id (EPA ID)
    lat: float | None              # always None — BR_REPORTING has no coords
    lon: float | None              # always None — BR_REPORTING has no coords
    city: str | None
    state: str | None
    county: str | None
    waste_generated_tons: float | None  # generation_tons
    reporting_year: int | None     # report_cycle
    naics_code: str | None         # primary_naics


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class RcraConnector(BaseConnector):
    """EPA RCRA Biennial Report Envirofacts REST connector."""

    name = "rcra"
    source = "EPA RCRA Biennial Report"
    source_url = "https://www.epa.gov/hwgenerators"
    cadence = "biennial"
    tag = "observed"

    async def fetch(
        self,
        state: str = "TX",
        limit: int = 100,
        year: int | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        """Fetch BR_REPORTING rows filtered by state and report_cycle.

        Uses `activity_location` for the state filter and `report_cycle`
        for the biennial year filter.

        IMPORTANT: report_cycle is ALWAYS applied (defaults to 2023).
        Without it, Envirofacts returns HTTP 500 for large states (e.g.
        TX) because the server-side query times out. See landmine #9.
        """
        state_code = (state or "TX").upper()
        target_year = int(year) if year is not None else DEFAULT_REPORT_CYCLE
        row_end = max(1, min(limit, 500)) - 1

        # Build URL segments.  Always include report_cycle to avoid
        # server-side 500 on large states.
        url = (
            f"{EFSERVICE_BASE}/BR_REPORTING"
            f"/activity_location/{state_code}"
            f"/report_cycle/{target_year}"
            f"/rows/0:{row_end}/JSON"
        )

        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT, follow_redirects=True
        ) as client:
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise RuntimeError(
                    f"RCRA BR_REPORTING fetch failed "
                    f"({state_code}, year={target_year}): {exc}"
                ) from exc
            try:
                rows = resp.json()
            except ValueError as exc:
                raise RuntimeError(
                    f"RCRA BR_REPORTING returned non-JSON payload: {exc}"
                ) from exc
            if isinstance(rows, dict) and isinstance(
                rows.get("Results"), list
            ):
                rows = rows["Results"]
            if not isinstance(rows, list):
                raise RuntimeError(
                    "RCRA BR_REPORTING returned unexpected payload shape "
                    f"(type={type(rows).__name__})."
                )

        return {
            "state": state_code,
            "year": target_year,
            "rows": rows,
        }

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        rows_raw = raw.get("rows") or []

        out: list[RcraHandler] = []
        for row in rows_raw:
            if not isinstance(row, dict):
                continue

            # BR_REPORTING has no lat/lon columns.
            lat = None
            lon = None

            generation = _coerce_float(row.get("generation_tons"))
            report_cycle = _coerce_int(row.get("report_cycle"))

            name = str(row.get("handler_name") or "Unknown handler").strip()
            handler_id = str(row.get("handler_id") or "").strip() or None
            city = str(row.get("location_city") or "").strip() or None
            state = str(
                row.get("activity_location")
                or row.get("location_state")
                or ""
            ).strip() or None
            county = str(row.get("county_name") or "").strip() or None
            naics = str(row.get("primary_naics") or "").strip() or None

            out.append(
                RcraHandler(
                    name=name,
                    handler_id=handler_id,
                    lat=lat,
                    lon=lon,
                    city=city,
                    state=state,
                    county=county,
                    waste_generated_tons=generation,
                    reporting_year=int(report_cycle) if report_cycle is not None else None,
                    naics_code=naics,
                )
            )

        return ConnectorResult(
            values=out,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="US facilities, state-filtered",
            license="Public domain (US EPA)",
            notes=[
                (
                    "RCRA Biennial Report: large-quantity hazardous waste "
                    "generators self-report every 2 years."
                ),
                (
                    "Waste quantity units vary by row; tons_generated may "
                    "be approximated."
                ),
                (
                    "Rows are per-waste-stream, not per-facility. A single "
                    "handler_id may appear multiple times with different "
                    "waste descriptions."
                ),
                (
                    "BR_REPORTING has no latitude/longitude columns. "
                    "Coordinates are always None."
                ),
            ],
        )
