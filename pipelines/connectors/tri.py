"""EPA TRI (Toxics Release Inventory) connector — Envirofacts REST.

Source:  https://www.epa.gov/toxics-release-inventory-tri-program
Docs:    https://www.epa.gov/enviro/envirofacts-data-service-api
Base:    https://data.epa.gov/efservice/
Cadence: annual (reporting year N published mid-year N+1)
Tag:     observed (self-reported regulatory submissions under EPCRA Section 313)
Auth:    none
Geo:     US facilities, state-filtered

=============================================================================
IMPLEMENTATION NOTES (verified 2026-04-12)

Endpoint pattern:
    {BASE}/{TABLE}/{COL}/{VAL}/{first}:{last}/{format}

Example (verified working):
    https://data.epa.gov/efservice/tri_facility/state_abbr/TX/rows/0:10/JSON

Primary table: `tri_facility`
    Columns we use:
      - facility_name    (str)
      - epa_registry_id  (str)
      - city_name        (str)
      - county_name      (str)
      - state_abbr       (str)
      - fac_latitude     (float)   -- often 0/null
      - fac_longitude    (float)   -- often 0/null
      - pref_latitude    (float)   -- fallback (often None)
      - pref_longitude   (float)   -- fallback (often None)

Enrichment table: `tri_reporting_form`
    - Keyed by `tri_facility_id` + `reporting_year`
    - Provides `cas_chem_name` and `tri_chem_id` per chemical per facility
    - `one_time_release_qty` is a ONE-TIME-event field, NOT an annual total
      — do not treat it as the annual release total.

=============================================================================
LANDMINES (add to docs/guardrails.md)

1. **Dead host.** The legacy `iaspub.epa.gov/enviro/efservice/` host is
   gone — use `data.epa.gov/efservice/` only.

2. **Mandatory pagination slug.** The trailing `/rows/{first}:{last}/`
   segment is REQUIRED. Without it, Envirofacts often times out or
   returns the full table.

3. **Format token required.** Append `/JSON` to the URL; default is
   XML which breaks json parsing.

4. **Accept header.** Some Envirofacts tables 500 without an explicit
   `Accept: application/json` header; always set it.

5. **Bad coordinates.** Many `tri_facility` rows carry `fac_latitude=0`,
   `fac_longitude=0`, None, or DMS-packed integers like 330450/964037
   (instead of decimal degrees). Skip facilities whose lat/lon cannot
   be coerced to a sane `-90..90` / `-180..180` decimal degree pair.

6. **Annual release totals are NOT in `tri_reporting_form`.** The
   `one_time_release_qty` field covers one-time events. A proper annual
   aggregate requires joining `tri_release_qty` across media types,
   which is a multi-hop query beyond the scope of this connector.
   We expose `total_release_lb = None` and leave the annual aggregation
   to future work / upstream TRI Basic Plus data files.

7. **Self-reported threshold.** Facilities below the EPCRA reporting
   threshold are invisible. This is expected; the normalize() `notes`
   list MUST carry the "absence is not zero" disclaimer.

=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

EFSERVICE_BASE = "https://data.epa.gov/efservice"
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


@dataclass
class TriFacility:
    name: str
    registry_id: str
    lat: float | None
    lon: float | None
    city: str | None
    county: str | None
    state: str | None
    year: int | None
    total_release_lb: float | None
    chemicals: list[str] = field(default_factory=list)


def _coerce_coord(value: Any, is_lat: bool) -> float | None:
    """Coerce an Envirofacts coordinate field into decimal degrees.

    TRI facility coordinates come back in several broken forms:
      - `0` / `0.0` (placeholder)
      - `None` / missing
      - DMS-packed integers like `330450` (33deg04'50" -- needs decoding)

    This helper returns a decimal-degree float ONLY when the value
    lands in a plausible range. Anything suspect -> None.
    """
    if value is None:
        return None
    try:
        fval = float(value)
    except (TypeError, ValueError):
        return None
    if fval == 0.0:
        return None
    # Decimal degree sanity check. DMS-packed ints like 330450 fall
    # outside these ranges and are correctly discarded.
    if is_lat:
        if -90.0 <= fval <= 90.0:
            return fval
        return None
    if -180.0 <= fval <= 180.0:
        return fval
    return None


def _pick_coord(row: dict[str, Any], lat_keys: list[str], lon_keys: list[str]) -> tuple[float | None, float | None]:
    """Walk multiple candidate keys and return the first valid lat/lon pair."""
    lat: float | None = None
    lon: float | None = None
    for k in lat_keys:
        lat = _coerce_coord(row.get(k), is_lat=True)
        if lat is not None:
            break
    for k in lon_keys:
        lon = _coerce_coord(row.get(k), is_lat=False)
        if lon is not None:
            break
    return lat, lon


class TriConnector(BaseConnector):
    """EPA TRI Envirofacts REST connector (facility list, state-filtered)."""

    name = "tri"
    source = "EPA TRI (Toxics Release Inventory)"
    source_url = "https://www.epa.gov/toxics-release-inventory-tri-program"
    cadence = "annual"
    tag = "observed"

    async def fetch(
        self,
        state: str = "TX",
        limit: int = 100,
        year: int | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        """Fetch TRI facilities for a given state.

        Hop 1: GET tri_facility rows filtered by state_abbr.
        Hop 2 (best-effort): GET tri_reporting_form rows for the same state
        limited to the requested reporting_year so we can attach a small
        sample of chemical names per facility. Failures here are
        swallowed — facility list still renders.
        """
        state_code = (state or "TX").upper()
        row_end = max(1, min(limit, 500)) - 1

        facility_url = (
            f"{EFSERVICE_BASE}/tri_facility/state_abbr/{state_code}"
            f"/rows/0:{row_end}/JSON"
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
                    f"TRI tri_facility fetch failed ({state_code}): {exc}"
                ) from exc
            try:
                facilities = r_fac.json()
            except ValueError as exc:
                raise RuntimeError(
                    f"TRI tri_facility returned non-JSON payload: {exc}"
                ) from exc
            if not isinstance(facilities, list):
                # Envirofacts returns {"Results": [...]} in some cases.
                if isinstance(facilities, dict) and isinstance(
                    facilities.get("Results"), list
                ):
                    facilities = facilities["Results"]
                else:
                    raise RuntimeError(
                        "TRI tri_facility returned unexpected payload shape "
                        f"(type={type(facilities).__name__})."
                    )

            # Best-effort chemicals enrichment. Keep the row cap small —
            # tri_reporting_form is huge; we just want a light sample to
            # attach chemical names where possible.
            chemicals_by_facility: dict[str, list[str]] = {}
            if year is not None:
                form_url = (
                    f"{EFSERVICE_BASE}/tri_reporting_form/reporting_year/{int(year)}"
                    f"/rows/0:499/JSON"
                )
                try:
                    r_form = await client.get(form_url, headers=headers)
                    r_form.raise_for_status()
                    forms = r_form.json()
                    if isinstance(forms, dict) and isinstance(forms.get("Results"), list):
                        forms = forms["Results"]
                    if isinstance(forms, list):
                        for form in forms:
                            fid = str(form.get("tri_facility_id") or "").strip()
                            chem = (form.get("cas_chem_name") or "").strip()
                            if not fid or not chem or chem.upper() == "NA":
                                continue
                            bucket = chemicals_by_facility.setdefault(fid, [])
                            if chem not in bucket and len(bucket) < 5:
                                bucket.append(chem)
                except httpx.HTTPError:
                    # Enrichment is optional — swallow.
                    chemicals_by_facility = {}

        return {
            "state": state_code,
            "year": year,
            "facilities": facilities,
            "chemicals_by_facility": chemicals_by_facility,
        }

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        facilities_raw = raw.get("facilities") or []
        chemicals_by_facility = raw.get("chemicals_by_facility") or {}
        year = raw.get("year")

        out: list[TriFacility] = []
        for row in facilities_raw:
            if not isinstance(row, dict):
                continue

            lat, lon = _pick_coord(
                row,
                lat_keys=["fac_latitude", "pref_latitude"],
                lon_keys=["fac_longitude", "pref_longitude"],
            )

            registry_id = str(
                row.get("epa_registry_id") or row.get("tri_facility_id") or ""
            ).strip()
            tri_id = str(row.get("tri_facility_id") or "").strip()
            chems = chemicals_by_facility.get(tri_id, []) if tri_id else []

            name = str(row.get("facility_name") or "Unknown facility").strip()
            city = str(row.get("city_name") or "").strip() or None
            county = str(row.get("county_name") or "").strip() or None
            state = str(row.get("state_abbr") or "").strip() or None

            out.append(
                TriFacility(
                    name=name,
                    registry_id=registry_id,
                    lat=lat,
                    lon=lon,
                    city=city,
                    county=county,
                    state=state,
                    year=int(year) if year is not None else None,
                    # Annual aggregate release totals live in a second,
                    # heavier join (tri_release_qty across media types).
                    # Left None for now — see connector docstring landmine #6.
                    total_release_lb=None,
                    chemicals=chems,
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
                    "TRI releases are self-reported by facilities above "
                    "reporting thresholds; absence from the list does not "
                    "mean zero emissions."
                ),
                (
                    "Facility coordinates come from Envirofacts tri_facility; "
                    "rows with 0/null/invalid lat/lon are dropped from "
                    "map-ready outputs but may still appear in counts."
                ),
                (
                    "Annual total_release_lb is not populated in this "
                    "connector — it requires a separate join across "
                    "tri_release_qty media types (landmine in docstring)."
                ),
            ],
        )
