"""Global Forest Watch — Tree Cover Loss connector.

Source:  https://www.globalforestwatch.org/
Data:    Hansen/UMD/Google/USGS/NASA Global Forest Change
Cadence: annual (new vintage released each April/May)
Tag:     derived (satellite-based classification; Hansen et al.)
Auth:    API key required — free account at https://www.globalforestwatch.org/
         Register, then POST /auth/apikey to obtain key.
         Key must be passed as HTTP header: x-api-key

=============================================================================
Verified endpoints (2026-04-11):

  ✅ https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss
       — dataset metadata; no auth required; lists versions v1.8 … v1.13
  ⚠️  https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/v1.12/query/json
       — returns HTTP 403 without x-api-key (graceful degradation implemented)
  ✅  https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/v1.12/fields
       — field list; no auth required; used to confirm column names

  Dataset version strategy: fetch /dataset/umd_tree_cover_loss, parse
  `data.versions` list, use the latest version string.

=============================================================================
Landmines:
  1. The SQL alias for the area column is `area__ha` (two underscores).
     The field list confirms: `umd_tree_cover_loss__ha` is the pixel-sum
     field, and `umd_tree_cover_loss__year` is the year dimension.
  2. The query endpoint requires POST with JSON body `{"sql": "..."}`.
     GET with `?sql=` params returns HTTP 405 for some versions.
  3. No `iso` rollup is exposed in the public query endpoint without a
     geometry payload — to get country-level stats you must POST a country
     polygon (WKT or GeoJSON) as the `geometry` field alongside the SQL.
     This connector therefore aggregates globally (no geometry filter).
  4. `umd_tree_cover_loss__ha` is gated behind the `>=30%` canopy-cover
     threshold filter by default in the GFW dashboard. When querying via
     API without a threshold filter, numbers are summed across all densities.
     The `notes` field documents this.
  5. Version string in the URL must match exactly (e.g. "v1.12", not "1.12").
     The metadata endpoint returns a list of strings; always take the last one.
  6. API keys expire after 1 year; connector returns `not_configured` when
     the key is absent or when the API returns 401/403.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BASE = "https://data-api.globalforestwatch.org"
_DATASET_META_URL = f"{_BASE}/dataset/umd_tree_cover_loss"
# Query URL is constructed at runtime once the latest version is known.
_QUERY_PATH = "/dataset/umd_tree_cover_loss/{version}/query/json"

# Global aggregate: sum loss (ha) per year, no geometry filter.
_SQL = (
    "SELECT umd_tree_cover_loss__year, SUM(area__ha) AS tree_cover_loss_ha "
    "FROM results "
    "GROUP BY umd_tree_cover_loss__year "
    "ORDER BY umd_tree_cover_loss__year"
)

# Sentinel returned when no API key is available.
_NOT_CONFIGURED: dict[str, Any] = {
    "status": "not_configured",
    "message": (
        "GFW Data API key missing. Register a free account at "
        "https://www.globalforestwatch.org/ and create an API key via "
        "POST /auth/apikey (see "
        "https://www.globalforestwatch.org/help/developers/guides/"
        "create-and-use-an-api-key/). "
        "Pass the key as GFW_API_KEY environment variable."
    ),
}


# ---------------------------------------------------------------------------
# Typed result dataclass
# ---------------------------------------------------------------------------
@dataclass
class ForestLossPoint:
    """Annual global tree cover loss.

    Spatial scope: global aggregate (no country breakdown — country-level
    queries require posting country polygon geometries to the API).
    """

    year: int
    iso_country: str  # "WLD" for world aggregate
    country_name: str
    tree_cover_loss_ha: float
    gross_emissions_co2e_mt: float | None = None  # not in umd_tree_cover_loss


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------
class GlobalForestWatchConnector(BaseConnector):
    """Fetch annual global tree cover loss from the GFW Data API.

    The GFW Data API requires an x-api-key header obtained by creating a
    free account on globalforestwatch.org. Without a key the connector
    returns ``status: not_configured`` rather than raising an exception.
    """

    name = "global_forest_watch"
    source = "Global Forest Watch (Hansen/UMD)"
    source_url = "https://www.globalforestwatch.org/"
    cadence = "annual"
    tag = "derived"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["x-api-key"] = self.api_key
        return h

    async def _get_latest_version(self, client: httpx.AsyncClient) -> str:
        """Fetch dataset metadata and return the latest version string."""
        r = await client.get(_DATASET_META_URL, headers=self._headers())
        r.raise_for_status()
        data = r.json()
        versions: list[str] = data.get("data", {}).get("versions", [])
        if not versions:
            raise ValueError("GFW metadata returned no versions list")
        # versions are strings like "v1.8", "v1.12" — sort lexicographically
        # after splitting the numeric part to avoid "v1.9" > "v1.12".
        def _ver_key(v: str) -> tuple[int, ...]:
            parts = v.lstrip("v").split(".")
            try:
                return tuple(int(p) for p in parts)
            except ValueError:
                return (0,)

        return sorted(versions, key=_ver_key)[-1]

    # ------------------------------------------------------------------
    # BaseConnector implementation
    # ------------------------------------------------------------------

    async def fetch(self, **params: Any) -> Any:
        """Query the GFW Data API for annual global tree cover loss.

        Returns a dict with ``status`` key:
        - ``not_configured`` — API key absent
        - ``ok`` — ``data`` list present
        - ``error`` — HTTP or parse failure; ``message`` describes it
        """
        if not self.api_key:
            return _NOT_CONFIGURED

        timeout = httpx.Timeout(60.0, connect=15.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                version = await self._get_latest_version(client)
                url = _BASE + _QUERY_PATH.format(version=version)
                payload = {"sql": _SQL}
                r = await client.post(url, headers=self._headers(), json=payload)
                if r.status_code in (401, 403):
                    return {
                        "status": "not_configured",
                        "message": (
                            f"GFW API returned HTTP {r.status_code}. "
                            "Check that your x-api-key is valid and not expired "
                            "(keys expire after 1 year)."
                        ),
                    }
                r.raise_for_status()
                return {"status": "ok", "version": version, "data": r.json()}
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "message": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "message": str(exc)}

    def normalize(self, raw: Any) -> ConnectorResult:
        """Convert GFW API JSON into a list of ForestLossPoint.

        Handles ``not_configured`` and ``error`` sentinel payloads gracefully
        by returning an empty values list with the status embedded in notes.
        """
        status = raw.get("status", "error") if isinstance(raw, dict) else "error"
        notes_base: list[str] = [
            "Global aggregate only — country-level queries require posting "
            "country polygon geometries to the API.",
            "Loss is summed across all canopy-cover density thresholds. "
            "GFW dashboard default is ≥30 % canopy cover.",
            "Derived from Hansen/UMD/Google/USGS/NASA Global Forest Change; "
            "accuracy ~88 % globally (varies by biome).",
            "License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).",
        ]

        if status != "ok":
            message = raw.get("message", "Unknown error") if isinstance(raw, dict) else str(raw)
            return ConnectorResult(
                values=[],
                source=self.source,
                source_url=self.source_url,
                cadence=self.cadence,
                tag=self.tag,
                spatial_scope="Global",
                license="CC BY 4.0",
                notes=[f"status:{status} — {message}"] + notes_base,
            )

        rows: list[dict[str, Any]] = (
            raw.get("data", {}).get("data", [])
            if isinstance(raw.get("data"), dict)
            else []
        )

        points: list[ForestLossPoint] = []
        for row in rows:
            try:
                year = int(row["umd_tree_cover_loss__year"])
                loss_ha = float(row.get("tree_cover_loss_ha") or row.get("area__ha") or 0.0)
            except (KeyError, TypeError, ValueError):
                continue
            points.append(
                ForestLossPoint(
                    year=year,
                    iso_country="WLD",
                    country_name="World",
                    tree_cover_loss_ha=loss_ha,
                    gross_emissions_co2e_mt=None,
                )
            )

        version_note = f"Dataset version: {raw.get('version', 'unknown')}."
        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global",
            license="CC BY 4.0",
            notes=[version_note] + notes_base,
        )
