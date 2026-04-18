"""EPA GHGRP / FLIGHT connector — Envirofacts REST.

Source:  https://www.epa.gov/ghgreporting
Docs:    https://www.epa.gov/enviro/greenhouse-gas-restful-data-service
Base:    https://data.epa.gov/efservice/
Cadence: annual (reporting year N published in fall of N+1)
Tag:     observed (self-reported under 40 CFR Part 98)
Auth:    none
Geo:     US facilities, state-filtered

=============================================================================
IMPLEMENTATION NOTES (verified 2026-04-12)

Primary table: `pub_dim_facility` (GHGRP FLIGHT facility dimension)
    Verified working URL:
        https://data.epa.gov/efservice/pub_dim_facility/state/TX/rows/0:10/JSON
    Column names (confirmed):
      - facility_id               (int)
      - facility_name             (str)
      - latitude                  (float)   -- decimal degrees, clean
      - longitude                 (float)   -- decimal degrees, clean
      - city                      (str)
      - state                     (str)
      - year                      (int)     -- reporting year
      - reported_industry_types   (str)     -- "Direct Emitter", etc.
      - facility_types            (str)
      - naics_code                (str)

Emissions table: `pub_facts_sector_ghg_emission`
    Columns:
      - facility_id        (int)
      - year               (int)
      - sector_id          (int)    -- NOT a descriptive name
      - subsector_id       (int)
      - gas_id             (int)
      - co2e_emission      (float)  -- metric tonnes CO2e

Because pub_facts_sector_ghg_emission is keyed by sector/subsector/gas
and has NO descriptive sector names, we aggregate co2e_emission by
facility_id + year to produce a single facility-level total. This
matches how FLIGHT's public-facing charts present it.

=============================================================================
LANDMINES

1. **Dead host.** Legacy `iaspub.epa.gov/enviro/efservice/` is gone.
   Use `data.epa.gov/efservice/` only.

2. **Mandatory pagination slug + JSON token.** Same as TRI — always
   append `/rows/{first}:{last}/JSON` or you get XML or a timeout.

3. **Accept header.** Set `Accept: application/json`.

4. **Suppressed emissions.** Some facilities have `co2e_emission`
   set to None due to CBI suppression rules. These are left as None
   in the output — do not coerce to 0.

5. **25,000 tCO2e/yr threshold.** GHGRP covers emitters at or above
   this annual CO2e threshold (40 CFR Part 98). Facilities below the
   threshold do not report — this is a reporting floor, not a gap.

6. **No descriptive sector name.** The `sector_id` integer has no
   lookup exposed on this endpoint. We expose `reported_industry_types`
   from pub_dim_facility instead, which is a short categorical code
   (e.g., "C" for Direct Emitter). Expanding to friendly names would
   need a static lookup table — deferred.

=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

EFSERVICE_BASE = "https://data.epa.gov/efservice"
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# 2023 reporting year was the latest available as of 2026-04-12.
DEFAULT_YEAR = 2023


@dataclass
class GhgrpFacility:
    name: str
    facility_id: int | None
    lat: float | None
    lon: float | None
    city: str | None
    state: str | None
    year: int | None
    total_co2e_tonnes: float | None
    industry_type: str | None


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


class GhgrpConnector(BaseConnector):
    """EPA GHGRP FLIGHT Envirofacts REST connector."""

    name = "ghgrp"
    source = "EPA GHGRP (FLIGHT)"
    source_url = "https://www.epa.gov/ghgreporting"
    cadence = "annual"
    tag = "observed"

    async def fetch(
        self,
        state: str = "TX",
        limit: int = 100,
        year: int | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        """Fetch GHGRP facility dimension rows + aggregate CO2e emissions.

        Hop 1 (required): pub_dim_facility filtered by state (and year).
        Hop 2 (best-effort): pub_facts_sector_ghg_emission for the same
        year, aggregated by facility_id to attach per-facility totals.
        """
        state_code = (state or "TX").upper()
        target_year = int(year) if year is not None else DEFAULT_YEAR
        row_end = max(1, min(limit, 500)) - 1

        facility_url = (
            f"{EFSERVICE_BASE}/pub_dim_facility/state/{state_code}"
            f"/year/{target_year}/rows/0:{row_end}/JSON"
        )

        # Emissions table is not state-filterable (no state column on
        # pub_facts_sector_ghg_emission). We fetch a fixed window for
        # the target year and aggregate; facilities that don't match
        # simply get None for their total.
        emissions_url = (
            f"{EFSERVICE_BASE}/pub_facts_sector_ghg_emission/year/{target_year}"
            f"/rows/0:499/JSON"
        )

        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT, follow_redirects=True
        ) as client:
            try:
                r_fac = await client.get(facility_url, headers=headers)
                r_fac.raise_for_status()
            except httpx.HTTPError as exc:
                raise RuntimeError(
                    f"GHGRP pub_dim_facility fetch failed "
                    f"({state_code}, {target_year}): {exc}"
                ) from exc
            try:
                facilities = r_fac.json()
            except ValueError as exc:
                raise RuntimeError(
                    f"GHGRP pub_dim_facility returned non-JSON payload: {exc}"
                ) from exc
            if isinstance(facilities, dict) and isinstance(
                facilities.get("Results"), list
            ):
                facilities = facilities["Results"]
            if not isinstance(facilities, list):
                raise RuntimeError(
                    "GHGRP pub_dim_facility returned unexpected payload shape "
                    f"(type={type(facilities).__name__})."
                )

            # Best-effort emissions fetch.
            emissions_by_facility: dict[int, float] = {}
            try:
                r_em = await client.get(emissions_url, headers=headers)
                r_em.raise_for_status()
                emissions = r_em.json()
                if isinstance(emissions, dict) and isinstance(
                    emissions.get("Results"), list
                ):
                    emissions = emissions["Results"]
                if isinstance(emissions, list):
                    for row in emissions:
                        if not isinstance(row, dict):
                            continue
                        fid = _coerce_int(row.get("facility_id"))
                        co2e = _coerce_float(row.get("co2e_emission"))
                        if fid is None or co2e is None:
                            continue
                        emissions_by_facility[fid] = (
                            emissions_by_facility.get(fid, 0.0) + co2e
                        )
            except httpx.HTTPError:
                emissions_by_facility = {}

        return {
            "state": state_code,
            "year": target_year,
            "facilities": facilities,
            "emissions_by_facility": emissions_by_facility,
        }

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        facilities_raw = raw.get("facilities") or []
        emissions_by_facility: dict[int, float] = raw.get("emissions_by_facility") or {}
        year_default = raw.get("year")

        out: list[GhgrpFacility] = []
        for row in facilities_raw:
            if not isinstance(row, dict):
                continue

            fid = _coerce_int(row.get("facility_id"))
            lat = _coerce_float(row.get("latitude"))
            lon = _coerce_float(row.get("longitude"))
            # Sanity-check coordinates.
            if lat is not None and not (-90.0 <= lat <= 90.0):
                lat = None
            if lon is not None and not (-180.0 <= lon <= 180.0):
                lon = None

            total_co2e: float | None = None
            if fid is not None and fid in emissions_by_facility:
                total_co2e = round(emissions_by_facility[fid], 2)

            name = str(row.get("facility_name") or "Unknown facility").strip()
            city = str(row.get("city") or "").strip() or None
            state = str(row.get("state") or "").strip() or None
            year = _coerce_int(row.get("year")) or year_default
            industry = str(
                row.get("reported_industry_types")
                or row.get("facility_types")
                or ""
            ).strip() or None

            out.append(
                GhgrpFacility(
                    name=name,
                    facility_id=fid,
                    lat=lat,
                    lon=lon,
                    city=city,
                    state=state,
                    year=int(year) if year is not None else None,
                    total_co2e_tonnes=total_co2e,
                    industry_type=industry,
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
                    "GHGRP emissions are self-reported under 40 CFR Part 98. "
                    "Covers facilities emitting \u226525,000 tCO\u2082e/yr."
                ),
                (
                    "Per-facility total_co2e_tonnes is aggregated from "
                    "pub_facts_sector_ghg_emission (best-effort); some "
                    "facilities return None due to CBI suppression or "
                    "because their records fell outside the paginated window."
                ),
                (
                    "industry_type uses the short reported_industry_types "
                    "code from pub_dim_facility (e.g., 'C' = Direct Emitter)."
                ),
            ],
        )
