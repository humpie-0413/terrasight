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
