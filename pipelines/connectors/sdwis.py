"""EPA SDWIS (Safe Drinking Water Information System) connector.

Source:  https://data.epa.gov/efservice/
Docs:    https://www.epa.gov/enviro/sdwis-overview
Cadence: quarterly (states report to EPA on a quarterly cycle)
Tag:     observed (regulatory violation records are observed facts)
Geo:     Public Water Systems (PWS), geolocated via city_name / zip_code

=============================================================================
ENVIROFACTS REST PATTERN (verified live 2026-04-12)

Base URL:
  https://data.epa.gov/efservice/

The old host `iaspub.epa.gov/enviro/efservice/` is DEAD. Only
`data.epa.gov/efservice/` works.

URL layout:
  {BASE}/{TABLE}/{COL}/{OP}/{VAL}/{first}:{last}/{FORMAT}
  …where OP can be omitted (defaults to equality), or can be
  `BEGINNING`, `CONTAINING`, `>`, `<`, etc.

- Mandatory pagination: the trailing `{first}:{last}` slice is required.
- Format token: append `/JSON` or `/CSV` as the final path segment.
- No auth required.

Useful tables (verified 2026-04-12):
  water_system  — PWS metadata (pwsid, pws_name, city_name, state_code,
                  zip_code, pws_type_code, population_served_count,
                  primary_source_code, pws_activity_code, …)
  violation     — SDWIS violation records (pwsid, violation_id,
                  violation_category_code, is_health_based_ind,
                  compl_per_begin_date, compl_per_end_date, …)

=============================================================================
LANDMINES (all hit & fixed 2026-04-12):

1. `violation` table's own `state_code` filter is SILENTLY IGNORED.
   A query like `/efservice/violation/state_code/TX/rows/0:5/JSON`
   returns Connecticut rows (pwsid 010106001). The filter is a no-op.
   FIX: use the joined pattern
   `/efservice/water_system/state_code/TX/violation/rows/…/JSON`
   which DOES constrain the violation rows to TX-only correctly (the
   response includes `state_code=TX` on every row).

2. Envirofacts is S-L-O-W as the requested slice grows.
   - `rows/0:500`  ≈ 10 s
   - `rows/0:1500` ≈ 80-95 s
   - `rows/0:2500` ≈ 145 s  (often exceeds a 120 s timeout)
   - `rows/0:9999` typically never returns inside a reasonable budget.
   The latency scales super-linearly with slice size, so we keep
   per-request slices small (500) and fan out in parallel instead.

3. `BEGINNING` is a real Envirofacts operator on `zip_code` and
   returns correctly-constrained rows. Verified live.

4. Parallel per-prefix fetching is the right pattern for metro pulls.
   We build one URL per zip prefix and gather them via `asyncio.gather`.
   Houston (10 prefixes × 500 rows) completes in ~37 s — 4× faster
   than a single large slice — and keeps each individual request well
   within the timeout envelope. This doubles as a built-in "shard"
   that lets us identify per-prefix completeness.

5. If a per-prefix slice hits the 501-row cap, we flag that prefix
   as `truncated` in the raw payload. Callers may choose to bump the
   cap, but for MVP Houston-level reporting this is acceptable
   because CWS + significant population systems are usually in the
   first window.

6. PWSID → CBSA is not a clean mapping — a single water system can
   span counties or lie partly outside a metro. For Houston we
   filter by zip_code prefix (770–779).

7. `zip_code` values may include a `-####` suffix (ZIP+4). We compare
   the first 3 chars only.

8. The joined query may repeat (pwsid, violation_id) rows — de-dupe
   by `violation_id` when aggregating.

9. `population_served_count` can be a string, int, or None — coerce.

10. Dates come back as "YYYY-MM-DD HH:MM:SS" strings (or None). We
    compare lexicographically to find the latest.

11. `Accept: application/json` header is set explicitly to avoid any
    content-negotiation fallback to HTML.

12. When no zip prefixes are supplied we fall back to a single
    state-level pull with a hard cap of 500 rows. This is a loss of
    completeness on purpose — a callers wanting full state coverage
    should iterate zip prefixes or city_name facets themselves.

13. MANDATORY disclaimer on every render:
    "SDWIS violations are regulatory compliance records. A violation
     does NOT necessarily indicate unsafe water at the tap."
=============================================================================
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Iterable

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

BASE_URL = "https://data.epa.gov/efservice"

# Per-request row slice (see landmine #2). 500 is the sweet spot where
# individual requests return in ~10 s and can safely fan out in parallel.
SLICE_SIZE = 500

# Fallback slice when no zip prefixes are supplied — we can only afford
# one request, so cap to 500 (see landmine #12).
STATE_FALLBACK_SLICE = 500


@dataclass
class DrinkingWaterSystem:
    pwsid: str
    name: str
    city: str | None
    state: str | None
    pws_type: str | None
    population_served: int | None
    primary_source: str | None
    violation_count: int
    latest_violation_date: str | None
    zip_code: str | None = None


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _zip3(value: Any) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    if len(s) < 3:
        return None
    return s[:3]




class SdwisConnector(BaseConnector):
    name = "sdwis"
    source = "EPA SDWIS (Safe Drinking Water Information System)"
    source_url = (
        "https://www.epa.gov/ground-water-and-drinking-water/"
        "safe-drinking-water-information-system-sdwis-federal-reporting"
    )
    cadence = "quarterly"
    tag = "observed"

    async def fetch(
        self,
        state: str = "TX",
        zip_prefix_list: Iterable[str] | None = None,
        limit: int = 100,
        **_: Any,
    ) -> dict[str, Any]:
        """Fetch SDWIS water systems + violations for a state.

        Returns a dict: {
            "systems": [...],
            "violations": [...],
            "limit": int,
            "truncated_prefixes": [...],
        }

        The `limit` governs how many normalized systems the caller wants
        back — it is applied during `normalize`, not here.

        `zip_prefix_list` (e.g. ["770", "771", ..., "779"]) triggers
        parallel per-prefix fetching against the Envirofacts REST API,
        one HTTP request per (table × prefix). See landmines #2 and #4
        in the module docstring for why this pattern exists.

        With no zip prefixes we fall back to a single state-wide pull
        with a hard 500-row cap (see landmine #12).
        """
        state = state.upper().strip()

        prefixes = (
            sorted({p.strip() for p in zip_prefix_list if p and p.strip()})
            if zip_prefix_list
            else None
        )

        headers = {"Accept": "application/json"}
        # Per-request timeout. Individual prefix pulls are usually <15 s
        # but a few hot ones (e.g. Houston 770) can take 30 s.
        timeout = httpx.Timeout(60.0, connect=15.0)

        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers=headers
        ) as client:
            if not prefixes:
                return await self._fetch_state_only(client, state, limit)

            # Build one task per (table × prefix) and gather in parallel.
            sys_tasks = [
                self._fetch_slice(
                    client,
                    f"{BASE_URL}/water_system/state_code/{state}"
                    f"/zip_code/BEGINNING/{p}/rows/0:{SLICE_SIZE}/JSON",
                    tag=f"sys:{p}",
                )
                for p in prefixes
            ]
            viol_tasks = [
                self._fetch_slice(
                    client,
                    f"{BASE_URL}/water_system/state_code/{state}"
                    f"/zip_code/BEGINNING/{p}/violation/rows/0:{SLICE_SIZE}/JSON",
                    tag=f"viol:{p}",
                )
                for p in prefixes
            ]
            all_results = await asyncio.gather(
                *sys_tasks, *viol_tasks, return_exceptions=True
            )

        n = len(prefixes)
        sys_results = all_results[:n]
        viol_results = all_results[n:]

        systems_flat: list[dict[str, Any]] = []
        violations_flat: list[dict[str, Any]] = []
        truncated_prefixes: list[str] = []

        # Merge systems + note any prefix that hit the slice cap.
        for prefix, res in zip(prefixes, sys_results, strict=True):
            if isinstance(res, Exception):
                # Skip the prefix but don't fail the whole call.
                continue
            systems_flat.extend(res)
            # SLICE_SIZE=500 → rows/0:500 returns 501 when truncated.
            if len(res) >= SLICE_SIZE + 1:
                truncated_prefixes.append(prefix)

        for res in viol_results:
            if isinstance(res, Exception):
                continue
            violations_flat.extend(res)

        # Python-side refinement: limit to the exact 3-digit prefixes.
        prefixes_set = set(prefixes)
        refined_systems = [
            s for s in systems_flat if _zip3(s.get("zip_code")) in prefixes_set
        ]

        return {
            "systems": refined_systems,
            "violations": violations_flat,
            "limit": limit,
            "truncated_prefixes": truncated_prefixes,
        }

    @staticmethod
    async def _fetch_slice(
        client: httpx.AsyncClient, url: str, tag: str = ""
    ) -> list[dict[str, Any]]:
        """Fetch a single Envirofacts URL and return a list of records.

        Raises if the response isn't HTTP 200 or a JSON list.
        """
        resp = await client.get(url)
        resp.raise_for_status()
        payload = resp.json()
        if payload is None:
            return []
        if not isinstance(payload, list):
            raise RuntimeError(
                f"SDWIS {tag} response was not a list: {type(payload).__name__}"
            )
        return payload

    async def _fetch_state_only(
        self, client: httpx.AsyncClient, state: str, limit: int
    ) -> dict[str, Any]:
        """Fallback: single state-level pull when no zip prefixes given."""
        systems_url = (
            f"{BASE_URL}/water_system/state_code/{state}"
            f"/rows/0:{STATE_FALLBACK_SLICE}/JSON"
        )
        violations_url = (
            f"{BASE_URL}/water_system/state_code/{state}/violation"
            f"/rows/0:{STATE_FALLBACK_SLICE}/JSON"
        )
        sys_task = self._fetch_slice(client, systems_url, tag="sys:state")
        viol_task = self._fetch_slice(client, violations_url, tag="viol:state")
        systems_raw, violations_raw = await asyncio.gather(sys_task, viol_task)
        return {
            "systems": systems_raw,
            "violations": violations_raw,
            "limit": limit,
            "truncated_prefixes": [],
        }

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        systems_raw = raw.get("systems") or []
        violations_raw = raw.get("violations") or []
        limit = int(raw.get("limit") or 100)
        truncated_prefixes = raw.get("truncated_prefixes") or []

        # Aggregate violations by PWSID.  De-dupe on violation_id in case
        # the joined query repeats rows (landmine #5).
        seen_violation_ids: dict[str, set[str]] = {}
        latest_by_pwsid: dict[str, str] = {}

        for v in violations_raw:
            pwsid = str(v.get("pwsid") or "").strip()
            if not pwsid:
                continue
            vid = str(v.get("violation_id") or "").strip()

            bucket = seen_violation_ids.setdefault(pwsid, set())
            if vid:
                if vid in bucket:
                    continue
                bucket.add(vid)
            else:
                # Fallback key — avoid double counting unkeyed rows.
                synth = f"{v.get('compl_per_begin_date')}|{v.get('violation_code')}"
                if synth in bucket:
                    continue
                bucket.add(synth)

            begin = v.get("compl_per_begin_date")
            if begin:
                begin_s = str(begin)[:10]  # "YYYY-MM-DD"
                current = latest_by_pwsid.get(pwsid)
                if current is None or begin_s > current:
                    latest_by_pwsid[pwsid] = begin_s

        pwsid_violation_counts = {k: len(v) for k, v in seen_violation_ids.items()}

        values: list[DrinkingWaterSystem] = []
        for s in systems_raw:
            pwsid = str(s.get("pwsid") or "").strip()
            if not pwsid:
                continue
            name = str(s.get("pws_name") or "Unknown system").strip()
            city = s.get("city_name") or None
            state = s.get("state_code") or None
            pws_type = s.get("pws_type_code") or None
            population = _coerce_int(s.get("population_served_count"))
            primary_source = s.get("primary_source_code") or None
            zip_code = s.get("zip_code") or None

            count = pwsid_violation_counts.get(pwsid, 0)
            latest = latest_by_pwsid.get(pwsid)

            values.append(
                DrinkingWaterSystem(
                    pwsid=pwsid,
                    name=name,
                    city=str(city) if city else None,
                    state=str(state) if state else None,
                    pws_type=str(pws_type) if pws_type else None,
                    population_served=population,
                    primary_source=str(primary_source) if primary_source else None,
                    violation_count=count,
                    latest_violation_date=latest,
                    zip_code=str(zip_code) if zip_code else None,
                )
            )

        # Sort: most-violated first, then largest population served.
        values.sort(
            key=lambda d: (
                -d.violation_count,
                -(d.population_served or 0),
                d.pwsid,
            )
        )
        values = values[:limit]

        notes = [
            (
                "SDWIS violations are regulatory compliance records. "
                "A violation does NOT necessarily indicate unsafe water "
                "at the tap."
            ),
            "SDWIS quarterly refresh; preliminary data may be revised.",
            (
                "Envirofacts `violation` table `state_code` filter is a "
                "no-op; this connector uses the joined "
                "`water_system/state_code/{ST}/violation` path instead."
            ),
            (
                "PWSIDs are mapped to metros by zip_code prefix, which "
                "is approximate — some systems cross metro boundaries."
            ),
        ]
        if truncated_prefixes:
            notes.append(
                "Some zip-prefix slices hit the per-request row cap and may "
                "under-count: " + ", ".join(truncated_prefixes)
            )

        return ConnectorResult(
            values=values,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="US Public Water Systems",
            license="Public domain (US EPA)",
            notes=notes,
        )
