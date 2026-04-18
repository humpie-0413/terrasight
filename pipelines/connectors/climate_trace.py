"""Climate TRACE GHG emissions connector.

Source:  https://climatetrace.org/
Cadence: Annual data, updated approximately 6 months after the reference year
         (e.g., 2022 emissions published mid-2023).
Tag:     derived  (ML + satellite-derived asset-level estimates; v2 mapping — v1 `estimated` retired 2026-04-17)
Auth:    None required — public API, no API key needed.

=============================================================================
Verified endpoints (2026-04-11 spike against https://api.climatetrace.org/v6/):

  GET /v6/definitions/sectors
    Returns JSON array of sector name strings.
    Verified: HTTP 200, no auth.
    Sectors: mineral-extraction, waste, transportation, buildings, manufacturing,
             fossil-fuel-operations, agriculture, power, fluorinated-gases,
             forestry-and-land-use

  GET /v6/definitions/countries
    Returns JSON array of {alpha3, alpha2, name, continent} objects.
    252 countries in the database.

  GET /v6/country/emissions
    Query params (all optional):
      since (int, 2000-2050, default 2010) — start year inclusive
      to    (int, 2000-2050, default 2020) — end year inclusive
      countries (str)   — comma-separated alpha3 codes; omit for world aggregate
      sector (str)      — single sector name to filter
      continents (str)  — comma-separated continent names
      groups (str)      — comma-separated group names
    Response:
      - With `countries` param: JSON array, one entry per country
        {country, continent, rank, previousRank, assetCount,
         emissions: {co2, ch4, n2o, co2e_100yr, co2e_20yr},
         worldEmissions: {...}, emissionsChange: {...}}
      - Without `countries` param: JSON dict with country="all" (world aggregate)
    Emission values are in METRIC TONS (not gigatons, not megatons).
    co2e_100yr uses 100-year GWP (IPCC AR6).

  GET /v6/assets/emissions
    Returns sector-level breakdowns per country.
    Query params: since, to, countries, sector, limit (default unset).
    Response: dict keyed by country alpha3, each value is an array of
      {AssetCount, Emissions (metric tons co2e_100yr), Year, Month, Gas,
       Country, Sector}
    NOTE: Gas field is always "co2e_100yr" in observed responses.
    This endpoint is used to build the sector breakdown within CountryEmissions.

LANDMINES:
  - The query parameter for country filtering is `countries` (PLURAL, csv string),
    NOT `country`. Using `country` silently returns world aggregate.
  - Emission values are in metric TONS — divide by 1e6 for megatons,
    by 1e9 for gigatons.
  - /v6/country/emissions without `countries` always returns world aggregate
    (country="all"), regardless of other filters.
  - The `sector` param on /v6/country/emissions does NOT appear to split
    the response by sector; it filters to a single sector total.
    Use /v6/assets/emissions for sector breakdowns.
  - `continent` field in country/emissions response is the string "null"
    (not JSON null) when countries param is used. Do not parse as None.
  - The API has no rate limit documented, but avoid hammering it with
    per-country requests across all 252 countries in a single call.
  - emissionsChange values are currently all 0 (change tracking not yet live).
=============================================================================
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

BASE_URL = "https://api.climatetrace.org/v6"

# Known sectors from /v6/definitions/sectors (verified 2026-04-11)
KNOWN_SECTORS: list[str] = [
    "mineral-extraction",
    "waste",
    "transportation",
    "buildings",
    "manufacturing",
    "fossil-fuel-operations",
    "agriculture",
    "power",
    "fluorinated-gases",
    "forestry-and-land-use",
]


@dataclass
class CountryEmissions:
    """Annual GHG emissions summary for one country, optionally with sector breakdown."""

    country_iso: str     # ISO alpha-3, e.g. "USA", "CHN", "IND"
    country_name: str    # Display name from definitions/countries (or alpha3 if unknown)
    year: int            # Reference year (since == to in a single-year query)
    rank: int | None     # Global emissions rank (1 = largest emitter)

    # Total emissions in metric tons CO2-equivalent (100-year GWP, IPCC AR6)
    total_co2e_mt: float

    # Individual gas breakdown (metric tons)
    co2_mt: float
    ch4_mt: float
    n2o_mt: float

    # 20-year GWP equivalent for methane-heavy sectors (metric tons CO2e)
    total_co2e_20yr_mt: float

    # Sector breakdown: sector_name → metric tons CO2e (100yr)
    # Populated only when fetch_sectors=True in the fetch() call.
    sectors: dict[str, float] = field(default_factory=dict)


def _country_name_map(definitions: list[dict[str, Any]]) -> dict[str, str]:
    """Build alpha3 → display name lookup from /definitions/countries response."""
    return {entry["alpha3"]: entry.get("name", entry["alpha3"]) for entry in definitions}


def _parse_country_entry(
    entry: dict[str, Any],
    year: int,
    name_map: dict[str, str],
) -> CountryEmissions:
    """Convert a single /country/emissions array element to CountryEmissions."""
    iso = entry.get("country", "")
    emissions = entry.get("emissions", {})
    return CountryEmissions(
        country_iso=iso,
        country_name=name_map.get(iso, iso),
        year=year,
        rank=entry.get("rank"),
        total_co2e_mt=float(emissions.get("co2e_100yr") or 0.0),
        co2_mt=float(emissions.get("co2") or 0.0),
        ch4_mt=float(emissions.get("ch4") or 0.0),
        n2o_mt=float(emissions.get("n2o") or 0.0),
        total_co2e_20yr_mt=float(emissions.get("co2e_20yr") or 0.0),
    )


class ClimateTraceConnector(BaseConnector):
    """Connector for Climate TRACE country-level GHG emissions data.

    Fetches annual emissions by country using the Climate TRACE v6 API.
    No API key is required.

    fetch() returns a dict with:
      "country_data"   — list of raw country emission dicts from /country/emissions
      "sector_data"    — dict of country→sector breakdown from /assets/emissions
                         (only populated when fetch_sectors=True)
      "name_map"       — alpha3→name mapping from /definitions/countries
      "year"           — the queried year
      "countries"      — the queried country list (None if world aggregate)

    normalize() converts this into a ConnectorResult with list[CountryEmissions].
    """

    name = "climate_trace"
    source = "Climate TRACE"
    source_url = "https://climatetrace.org/"
    cadence = "annual (~6-month publication lag after reference year)"
    tag = "derived"

    async def fetch(
        self,
        year: int = 2022,
        countries: list[str] | str | None = None,
        fetch_sectors: bool = True,
        **_: Any,
    ) -> dict[str, Any]:
        """Fetch country-level emissions from Climate TRACE API.

        Args:
            year: Reference year for emissions data (2015-2022 are well-covered).
            countries: ISO alpha-3 code(s) to query.  Can be:
                       - None/empty → world aggregate (single dict, country="all")
                       - str        → one country, e.g. "USA"
                       - list[str]  → multiple countries, e.g. ["USA","CHN","IND"]
                       To get top emitters, pass a pre-selected list.
            fetch_sectors: If True, also call /assets/emissions for sector breakdown.
                           Set False to reduce latency when sector data is not needed.
        """
        # Normalise countries arg
        if isinstance(countries, str) and countries:
            countries_str: str | None = countries
            countries_list: list[str] | None = [countries]
        elif isinstance(countries, list) and countries:
            countries_str = ",".join(countries)
            countries_list = countries
        else:
            countries_str = None
            countries_list = None

        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Fire country/emissions and definitions/countries in parallel
            params: dict[str, Any] = {"since": year, "to": year}
            if countries_str:
                params["countries"] = countries_str

            emissions_task = client.get(f"{BASE_URL}/country/emissions", params=params)
            names_task = client.get(f"{BASE_URL}/definitions/countries")

            emissions_resp, names_resp = await asyncio.gather(emissions_task, names_task)
            emissions_resp.raise_for_status()
            names_resp.raise_for_status()

            country_data = emissions_resp.json()
            name_map = _country_name_map(names_resp.json())

            # Optionally fetch sector breakdown for the requested countries
            sector_data: dict[str, Any] = {}
            if fetch_sectors and countries_list:
                sector_params: dict[str, Any] = {
                    "since": year,
                    "to": year,
                    "countries": ",".join(countries_list),
                }
                sector_resp = await client.get(
                    f"{BASE_URL}/assets/emissions", params=sector_params
                )
                if sector_resp.status_code == 200:
                    sector_data = sector_resp.json()

        return {
            "country_data": country_data,
            "sector_data": sector_data,
            "name_map": name_map,
            "year": year,
            "countries": countries_list,
        }

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        """Parse Climate TRACE fetch() payload into a ConnectorResult.

        ``raw["country_data"]`` is either:
          - a list  → per-country entries (when countries param was set)
          - a dict  → world aggregate    (when countries param was omitted)
        """
        year = raw.get("year", 0)
        name_map: dict[str, str] = raw.get("name_map", {})
        sector_data: dict[str, Any] = raw.get("sector_data", {})
        country_data = raw.get("country_data", [])

        # Normalise to list regardless of whether API returned list or dict
        if isinstance(country_data, dict):
            entries = [country_data]  # world aggregate
        else:
            entries = country_data

        results: list[CountryEmissions] = []
        for entry in entries:
            ce = _parse_country_entry(entry, year, name_map)

            # Attach sector breakdown if available
            iso = ce.country_iso
            if iso in sector_data:
                for item in sector_data[iso]:
                    sector_name = item.get("Sector", "unknown")
                    emissions_val = float(item.get("Emissions") or 0.0)
                    if sector_name and emissions_val > 0:
                        ce.sectors[sector_name] = ce.sectors.get(sector_name, 0.0) + emissions_val

            results.append(ce)

        # Sort by total emissions descending (most relevant first)
        results.sort(key=lambda c: c.total_co2e_mt, reverse=True)

        return ConnectorResult(
            values=results,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global (country-level)",
            license="Creative Commons Attribution 4.0 International (CC BY 4.0)",
            notes=[
                "Emissions values are in metric tons CO2-equivalent (100-year GWP, IPCC AR6).",
                "Divide by 1e6 for megatons, 1e9 for gigatons.",
                "Data is ML + satellite-derived asset-level estimates — not direct measurement.",
                "Annual data; publication lags reference year by approximately 6 months.",
                f"Reference year: {year}. Coverage: 2015-2022 is well-populated.",
                "Sector breakdown requires a separate /assets/emissions call per country.",
                "emissionsChange fields from the API are all 0 (feature not yet live).",
                "Parameter 'countries' must be alpha-3 codes (ISO 3166-1); see "
                "/v6/definitions/countries for the full list of 252 supported codes.",
            ],
        )
