"""Fact Rankings API.

Per CLAUDE.md: each ranking must disclose source & criterion.
- EPA violations ranking → ECHO (slug: epa-violations)
"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from backend.connectors.echo import EchoConnector
from backend.connectors.airnow import AirNowConnector
from backend.connectors.tri import TriConnector
from backend.connectors.ghgrp import GhgrpConnector
from backend.connectors.superfund import SuperfundConnector
from backend.connectors.sdwis import SdwisConnector
from backend.config import get_settings

router = APIRouter()

CBSA_MAPPING_PATH = Path(__file__).resolve().parents[2] / "data" / "cbsa_mapping.json"


def _load_cbsa_mapping() -> dict[str, dict[str, Any]]:
    if not CBSA_MAPPING_PATH.exists():
        return {}
    raw = json.loads(CBSA_MAPPING_PATH.read_text(encoding="utf-8"))
    return {v["slug"]: v for k, v in raw.items() if not k.startswith("_")}


async def _echo_for_metro(cbsa: dict[str, Any]) -> dict[str, Any]:
    """Fetch ECHO summary for one metro, return a ranking row."""
    bbox = cbsa["bbox"]
    connector = EchoConnector()
    try:
        raw = await asyncio.wait_for(
            connector.fetch(
                west=bbox["west"],
                south=bbox["south"],
                east=bbox["east"],
                north=bbox["north"],
                response_set=100,
            ),
            timeout=60,
        )
        result = connector.normalize(raw)
        vals = result.values
        sampled = vals.sampled_facilities
        in_vio = vals.in_violation
        rate = round(in_vio / sampled * 100, 1) if sampled else 0.0
        return {
            "slug": cbsa["slug"],
            "name": cbsa["name"],
            "state": cbsa.get("state"),
            "sampled_facilities": sampled,
            "in_violation": in_vio,
            "violation_rate_pct": rate,
            "status": "ok",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "slug": cbsa["slug"],
            "name": cbsa["name"],
            "state": cbsa.get("state"),
            "sampled_facilities": None,
            "in_violation": None,
            "violation_rate_pct": None,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }


@router.get("/epa-violations")
async def epa_violations_ranking() -> dict[str, Any]:
    """Return all metros sorted by ECHO in-violation count (descending).

    Source: EPA ECHO — regulatory compliance data.
    Each metro uses a bbox sample of up to 500 active facilities (p_act=Y).
    Violation = FacSNCFlg='Y' or FacComplianceStatus contains 'violation'.
    """
    mapping = _load_cbsa_mapping()
    tasks = [_echo_for_metro(cbsa) for cbsa in mapping.values()]
    rows: list[dict[str, Any]] = await asyncio.gather(*tasks)

    # Sort: successful rows by in_violation desc, then error rows at end.
    ok_rows = sorted(
        [r for r in rows if r["status"] == "ok"],
        key=lambda r: r["in_violation"] or 0,
        reverse=True,
    )
    err_rows = [r for r in rows if r["status"] != "ok"]

    return {
        "slug": "epa-violations",
        "title": "U.S. Metros — EPA Facility Violations",
        "criterion": "Facilities in violation per EPA ECHO (FacSNCFlg=Y or compliance status contains 'violation')",
        "note": "Sample = up to 500 active facilities per metro bounding box (p_act=Y). Not a complete census.",
        "retrieved_date": date.today().isoformat(),
        "source": "EPA ECHO",
        "source_url": "https://echo.epa.gov/",
        "tag": "regulatory",
        "rows": ok_rows + err_rows,
    }


async def _pm25_for_metro(cbsa: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Fetch current PM2.5 AQI for one metro via AirNow."""
    zip_code = (cbsa.get("airnow") or {}).get("sample_zip")
    if not zip_code:
        return {
            "slug": cbsa["slug"], "name": cbsa["name"], "state": cbsa.get("state"),
            "pm25_aqi": None, "pm25_category": None, "reporting_area": None,
            "observed_at": None, "status": "no_zip",
        }
    connector = AirNowConnector(api_key=api_key)
    try:
        raw = await asyncio.wait_for(connector.fetch(zip_code=zip_code), timeout=30)
        result = connector.normalize(raw)
        pm25 = [r for r in result.values if r.pollutant == "PM2.5"]
        if not pm25:
            return {
                "slug": cbsa["slug"], "name": cbsa["name"], "state": cbsa.get("state"),
                "pm25_aqi": None, "pm25_category": None, "reporting_area": None,
                "observed_at": None, "status": "no_data",
            }
        r = pm25[0]
        return {
            "slug": cbsa["slug"], "name": cbsa["name"], "state": cbsa.get("state"),
            "pm25_aqi": r.aqi, "pm25_category": r.category,
            "reporting_area": r.reporting_area, "observed_at": r.observed_at,
            "status": "ok",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "slug": cbsa["slug"], "name": cbsa["name"], "state": cbsa.get("state"),
            "pm25_aqi": None, "pm25_category": None, "reporting_area": None,
            "observed_at": None, "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }


@router.get("/pm25")
async def pm25_ranking() -> dict[str, Any]:
    """Return all metros sorted by current PM2.5 AQI (descending).

    Source: AirNow (EPA, USFS, NPS, NOAA) — real-time monitoring stations.
    Requires AIRNOW_API_KEY. Returns not_configured if key is absent.
    """
    settings = get_settings()
    if not settings.airnow_api_key:
        return {
            "slug": "pm25",
            "title": "U.S. Metros by Current PM2.5 Levels",
            "status": "not_configured",
            "message": (
                "AIRNOW_API_KEY is not set. Register at https://docs.airnowapi.org/ "
                "and add AIRNOW_API_KEY to your environment variables."
            ),
            "rows": [],
        }
    mapping = _load_cbsa_mapping()
    tasks = [_pm25_for_metro(cbsa, settings.airnow_api_key) for cbsa in mapping.values()]
    rows: list[dict[str, Any]] = await asyncio.gather(*tasks)

    ok_rows = sorted(
        [r for r in rows if r["status"] == "ok"],
        key=lambda r: r["pm25_aqi"] or 0,
        reverse=True,
    )
    other_rows = [r for r in rows if r["status"] != "ok"]

    return {
        "slug": "pm25",
        "title": "U.S. Metros by Current PM2.5 Levels",
        "criterion": "Current PM2.5 AQI from AirNow real-time monitoring stations",
        "note": (
            "PM2.5 values reflect the most recent hourly observation for each metro's "
            "representative ZIP code. Reporting area boundaries ≠ CBSA boundaries."
        ),
        "retrieved_date": date.today().isoformat(),
        "source": "AirNow (EPA, USFS, NPS, NOAA)",
        "source_url": "https://www.airnow.gov/",
        "tag": "observed",
        "rows": ok_rows + other_rows,
    }


# ---------------------------------------------------------------------------
# Shared helpers for state-level fan-out rankings (TRI, GHGRP, SDWIS).
# ---------------------------------------------------------------------------


def _unique_states_from_cbsas(cbsas: list[dict[str, Any]]) -> list[str]:
    """Return the sorted unique set of state codes from a list of CBSA dicts."""
    seen: set[str] = set()
    for cbsa in cbsas:
        st = (cbsa.get("state") or "").strip().upper()
        if st:
            seen.add(st)
    return sorted(seen)


async def _fetch_tri_for_state(state: str) -> tuple[str, int]:
    """Return (state, facility_count) — raises on failure."""
    connector = TriConnector()
    result = await asyncio.wait_for(
        connector.run(state=state, limit=500),
        timeout=90,
    )
    return state, len(result.values)


async def _fetch_ghgrp_for_state(state: str) -> tuple[str, int, float | None]:
    """Return (state, facility_count, total_co2e_tonnes) — raises on failure."""
    connector = GhgrpConnector()
    result = await asyncio.wait_for(
        connector.run(state=state, limit=500),
        timeout=90,
    )
    facilities = result.values
    total_co2e: float | None = None
    for f in facilities:
        val = getattr(f, "total_co2e_tonnes", None)
        if val is None:
            continue
        total_co2e = (total_co2e or 0.0) + float(val)
    if total_co2e is not None:
        total_co2e = round(total_co2e, 2)
    return state, len(facilities), total_co2e


async def _fetch_sdwis_for_state(
    state: str,
) -> tuple[str, int, int, int]:
    """Return (state, system_count, violation_count, systems_with_violations).

    Uses the connector's state-level fallback path (zip_prefix_list=None), which
    pulls a single 500-row slice of water_system rows joined with violations.
    Raises on failure so the caller can attribute an error to all metros in
    that state.
    """
    connector = SdwisConnector()
    result = await asyncio.wait_for(
        connector.run(state=state, zip_prefix_list=None, limit=500),
        timeout=120,
    )
    systems = result.values
    system_count = len(systems)
    violation_count = 0
    systems_with_violations = 0
    for s in systems:
        vc = int(getattr(s, "violation_count", 0) or 0)
        violation_count += vc
        if vc > 0:
            systems_with_violations += 1
    return state, system_count, violation_count, systems_with_violations


# ---------------------------------------------------------------------------
# /tri-releases — state-level fan-out
# ---------------------------------------------------------------------------


@router.get("/tri-releases")
async def tri_releases_ranking() -> dict[str, Any]:
    """Rank metros by TRI facility count (state-level attribution).

    Per-metro zip_prefix queries would be prohibitively slow against
    Envirofacts, so we resolve each metro's state, query the state once,
    and attribute the state total to every metro within it.
    """
    mapping = _load_cbsa_mapping()
    cbsas = list(mapping.values())
    states = _unique_states_from_cbsas(cbsas)

    tasks = [_fetch_tri_for_state(st) for st in states]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    state_counts: dict[str, int] = {}
    state_errors: dict[str, str] = {}
    for st, res in zip(states, results, strict=True):
        if isinstance(res, Exception):
            state_errors[st] = f"{type(res).__name__}: {res}"
        else:
            _, count = res
            state_counts[st] = count

    rows: list[dict[str, Any]] = []
    for cbsa in cbsas:
        state = (cbsa.get("state") or "").strip().upper()
        if not state:
            rows.append({
                "slug": cbsa["slug"],
                "name": cbsa["name"],
                "state": cbsa.get("state"),
                "facility_count": None,
                "status": "error",
                "error": "No state in CBSA mapping",
            })
            continue
        if state in state_errors:
            rows.append({
                "slug": cbsa["slug"],
                "name": cbsa["name"],
                "state": state,
                "facility_count": None,
                "status": "error",
                "error": state_errors[state],
            })
            continue
        rows.append({
            "slug": cbsa["slug"],
            "name": cbsa["name"],
            "state": state,
            "facility_count": state_counts.get(state, 0),
            "status": "ok",
        })

    ok_rows = sorted(
        [r for r in rows if r["status"] == "ok"],
        key=lambda r: r["facility_count"] or 0,
        reverse=True,
    )
    err_rows = [r for r in rows if r["status"] != "ok"]

    return {
        "slug": "tri-releases",
        "title": "U.S. Metros \u2014 TRI Facility Count",
        "criterion": (
            "Number of EPA Toxics Release Inventory reporting facilities, "
            "aggregated at state level"
        ),
        "note": (
            "TRI facilities self-report annual releases of toxic chemicals "
            "under EPCRA \u00a7313. Only facilities above reporting thresholds "
            "are included. State-level totals are attributed to every metro "
            "in that state."
        ),
        "retrieved_date": date.today().isoformat(),
        "source": "EPA TRI (Toxics Release Inventory)",
        "source_url": "https://www.epa.gov/toxics-release-inventory-tri-program",
        "tag": "observed",
        "rows": ok_rows + err_rows,
    }


# ---------------------------------------------------------------------------
# /ghg-emissions — state-level fan-out
# ---------------------------------------------------------------------------


@router.get("/ghg-emissions")
async def ghg_emissions_ranking() -> dict[str, Any]:
    """Rank metros by total facility CO2e (GHGRP), state-level attribution."""
    mapping = _load_cbsa_mapping()
    cbsas = list(mapping.values())
    states = _unique_states_from_cbsas(cbsas)

    tasks = [_fetch_ghgrp_for_state(st) for st in states]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    state_facility_counts: dict[str, int] = {}
    state_total_co2e: dict[str, float | None] = {}
    state_errors: dict[str, str] = {}
    for st, res in zip(states, results, strict=True):
        if isinstance(res, Exception):
            state_errors[st] = f"{type(res).__name__}: {res}"
        else:
            _, count, total_co2e = res
            state_facility_counts[st] = count
            state_total_co2e[st] = total_co2e

    rows: list[dict[str, Any]] = []
    for cbsa in cbsas:
        state = (cbsa.get("state") or "").strip().upper()
        if not state:
            rows.append({
                "slug": cbsa["slug"],
                "name": cbsa["name"],
                "state": cbsa.get("state"),
                "facility_count": None,
                "total_co2e_tonnes": None,
                "status": "error",
                "error": "No state in CBSA mapping",
            })
            continue
        if state in state_errors:
            rows.append({
                "slug": cbsa["slug"],
                "name": cbsa["name"],
                "state": state,
                "facility_count": None,
                "total_co2e_tonnes": None,
                "status": "error",
                "error": state_errors[state],
            })
            continue
        rows.append({
            "slug": cbsa["slug"],
            "name": cbsa["name"],
            "state": state,
            "facility_count": state_facility_counts.get(state, 0),
            "total_co2e_tonnes": state_total_co2e.get(state),
            "status": "ok",
        })

    ok_rows = sorted(
        [r for r in rows if r["status"] == "ok"],
        key=lambda r: r["total_co2e_tonnes"] or 0.0,
        reverse=True,
    )
    err_rows = [r for r in rows if r["status"] != "ok"]

    return {
        "slug": "ghg-emissions",
        "title": "U.S. Metros \u2014 Facility GHG Emissions (GHGRP)",
        "criterion": (
            "Total reported CO\u2082-equivalent tonnes from GHGRP facilities, "
            "aggregated at state level"
        ),
        "note": (
            "GHGRP covers large emitters (>25,000 tCO\u2082e/year). "
            "Self-reported under the EPA GHG Reporting Rule. State-level "
            "totals are attributed to every metro in that state."
        ),
        "retrieved_date": date.today().isoformat(),
        "source": "EPA GHGRP / FLIGHT",
        "source_url": "https://www.epa.gov/ghgreporting",
        "tag": "observed",
        "rows": ok_rows + err_rows,
    }


# ---------------------------------------------------------------------------
# /superfund — per-metro bbox fan-out (fast)
# ---------------------------------------------------------------------------


async def _superfund_for_metro(cbsa: dict[str, Any]) -> dict[str, Any]:
    """Fetch Superfund site count for one metro via bbox query."""
    bbox = cbsa.get("bbox") or {}
    connector = SuperfundConnector()
    try:
        result = await asyncio.wait_for(
            connector.run(
                west=bbox["west"],
                south=bbox["south"],
                east=bbox["east"],
                north=bbox["north"],
                limit=500,
            ),
            timeout=60,
        )
        sites = result.values
        site_count = len(sites)
        npl_final_count = sum(
            1 for s in sites if (getattr(s, "npl_status", None) or "").upper() == "F"
        )
        return {
            "slug": cbsa["slug"],
            "name": cbsa["name"],
            "state": cbsa.get("state"),
            "site_count": site_count,
            "npl_final_count": npl_final_count,
            "status": "ok",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "slug": cbsa["slug"],
            "name": cbsa["name"],
            "state": cbsa.get("state"),
            "site_count": None,
            "npl_final_count": None,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }


@router.get("/superfund")
async def superfund_ranking() -> dict[str, Any]:
    """Rank metros by Superfund site count within each metro bbox."""
    mapping = _load_cbsa_mapping()
    tasks = [_superfund_for_metro(cbsa) for cbsa in mapping.values()]
    rows: list[dict[str, Any]] = await asyncio.gather(*tasks)

    ok_rows = sorted(
        [r for r in rows if r["status"] == "ok"],
        key=lambda r: r["site_count"] or 0,
        reverse=True,
    )
    err_rows = [r for r in rows if r["status"] != "ok"]

    return {
        "slug": "superfund",
        "title": "U.S. Metros \u2014 Superfund NPL Sites",
        "criterion": (
            "Count of EPA Superfund sites within each metro's bounding box"
        ),
        "note": (
            "Includes Final, Proposed, Deleted and Removed NPL sites. "
            "Bounding box may extend slightly beyond the core CBSA polygon."
        ),
        "retrieved_date": date.today().isoformat(),
        "source": "EPA SEMS / Superfund NPL",
        "source_url": "https://www.epa.gov/superfund",
        "tag": "observed",
        "rows": ok_rows + err_rows,
    }


# ---------------------------------------------------------------------------
# /drinking-water-violations — state-level fan-out
# ---------------------------------------------------------------------------


@router.get("/drinking-water-violations")
async def drinking_water_violations_ranking() -> dict[str, Any]:
    """Rank metros by SDWIS violation count, state-level attribution."""
    mapping = _load_cbsa_mapping()
    cbsas = list(mapping.values())
    states = _unique_states_from_cbsas(cbsas)

    tasks = [_fetch_sdwis_for_state(st) for st in states]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    state_system_count: dict[str, int] = {}
    state_violation_count: dict[str, int] = {}
    state_systems_with_vios: dict[str, int] = {}
    state_errors: dict[str, str] = {}
    for st, res in zip(states, results, strict=True):
        if isinstance(res, Exception):
            state_errors[st] = f"{type(res).__name__}: {res}"
        else:
            _, sys_c, viol_c, sys_with_v = res
            state_system_count[st] = sys_c
            state_violation_count[st] = viol_c
            state_systems_with_vios[st] = sys_with_v

    rows: list[dict[str, Any]] = []
    for cbsa in cbsas:
        state = (cbsa.get("state") or "").strip().upper()
        if not state:
            rows.append({
                "slug": cbsa["slug"],
                "name": cbsa["name"],
                "state": cbsa.get("state"),
                "system_count": None,
                "violation_count": None,
                "systems_with_violations": None,
                "violation_rate_pct": None,
                "status": "error",
                "error": "No state in CBSA mapping",
            })
            continue
        if state in state_errors:
            rows.append({
                "slug": cbsa["slug"],
                "name": cbsa["name"],
                "state": state,
                "system_count": None,
                "violation_count": None,
                "systems_with_violations": None,
                "violation_rate_pct": None,
                "status": "error",
                "error": state_errors[state],
            })
            continue
        sys_c = state_system_count.get(state, 0)
        viol_c = state_violation_count.get(state, 0)
        sys_with_v = state_systems_with_vios.get(state, 0)
        rate: float | None = None
        if sys_c:
            rate = round(sys_with_v / sys_c * 100, 1)
        rows.append({
            "slug": cbsa["slug"],
            "name": cbsa["name"],
            "state": state,
            "system_count": sys_c,
            "violation_count": viol_c,
            "systems_with_violations": sys_with_v,
            "violation_rate_pct": rate,
            "status": "ok",
        })

    ok_rows = sorted(
        [r for r in rows if r["status"] == "ok"],
        key=lambda r: r["violation_count"] or 0,
        reverse=True,
    )
    err_rows = [r for r in rows if r["status"] != "ok"]

    return {
        "slug": "drinking-water-violations",
        "title": "U.S. Metros \u2014 SDWIS Drinking Water Violations",
        "criterion": (
            "Active SDWIS violations reported by public water systems, "
            "aggregated at state level"
        ),
        "note": (
            "A regulatory violation does NOT necessarily indicate unsafe "
            "water at the tap. SDWIS data are on a quarterly refresh cycle. "
            "State-level totals are attributed to every metro in that state."
        ),
        "retrieved_date": date.today().isoformat(),
        "source": "EPA SDWIS (Safe Drinking Water Information System)",
        "source_url": (
            "https://www.epa.gov/ground-water-and-drinking-water/"
            "safe-drinking-water-information-system-sdwis-federal-reporting"
        ),
        "tag": "observed",
        "rows": ok_rows + err_rows,
    }


# ---------------------------------------------------------------------------
# Catch-all stub — MUST remain the last route to avoid shadowing named slugs.
# ---------------------------------------------------------------------------


@router.get("/{ranking_slug}")
async def get_ranking(ranking_slug: str) -> dict[str, Any]:
    """Stub for future ranking slugs."""
    return {
        "slug": ranking_slug,
        "title": f"Ranking: {ranking_slug}",
        "source": None,
        "criterion": None,
        "rows": [],
        "status": "not_implemented",
    }
