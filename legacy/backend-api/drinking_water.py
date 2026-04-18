"""Drinking Water API router — EPA SDWIS.

Exposes:
  GET /sdwis — public water system metadata + violation aggregates,
  filterable by US state and optional zip prefix list.

Graceful degradation: connector failures never 5xx — errors are
surfaced as `status="error"` with an empty `systems` list.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from backend.connectors.sdwis import SdwisConnector

router = APIRouter()


def _serialize_system(d: Any) -> dict[str, Any]:
    return {
        "pwsid": d.pwsid,
        "name": d.name,
        "city": d.city,
        "state": d.state,
        "zip_code": d.zip_code,
        "pws_type": d.pws_type,
        "population_served": d.population_served,
        "primary_source": d.primary_source,
        "violation_count": d.violation_count,
        "latest_violation_date": d.latest_violation_date,
    }


@router.get("/sdwis")
async def get_sdwis(
    state: str = Query("TX", description="2-letter US state code (SDWIS primacy agency)"),
    zip_prefix: str | None = Query(
        None,
        description=(
            "Comma-separated list of zip prefixes to narrow the state-level "
            "result to a metro, e.g. '770,771,772,773,774,775,776,777,778,779' "
            "for Houston-The Woodlands-Sugar Land."
        ),
    ),
    limit: int = Query(100, ge=1, le=500, description="Max normalized systems to return"),
) -> dict[str, Any]:
    """Return SDWIS public water systems + violation aggregates for a state.

    The joined `water_system + violation` pull is aggregated per-PWSID
    in Python so each returned record has `violation_count` and
    `latest_violation_date`. Metro scoping uses zip prefixes because
    PWSIDs do not map cleanly to CBSAs.
    """
    prefixes = (
        [p.strip() for p in zip_prefix.split(",") if p.strip()]
        if zip_prefix
        else None
    )
    connector = SdwisConnector()

    try:
        raw = await connector.fetch(
            state=state,
            zip_prefix_list=prefixes,
            limit=limit,
        )
        result = connector.normalize(raw)
    except Exception as exc:  # noqa: BLE001 — graceful degradation
        return {
            "source": connector.source,
            "source_url": connector.source_url,
            "cadence": connector.cadence,
            "tag": connector.tag,
            "spatial_scope": "US Public Water Systems",
            "license": "Public domain (US EPA)",
            "count": 0,
            "configured": True,
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
            "systems": [],
            "notes": [
                (
                    "SDWIS violations are regulatory compliance records. "
                    "A violation does NOT necessarily indicate unsafe water "
                    "at the tap."
                ),
            ],
        }

    systems_out = [_serialize_system(d) for d in result.values]
    systems_with_violations = sum(1 for d in result.values if d.violation_count > 0)

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "count": len(systems_out),
        "systems_with_violations": systems_with_violations,
        "configured": True,
        "status": "ok",
        "state": state.upper(),
        "zip_prefixes": prefixes,
        "systems": systems_out,
        "notes": result.notes,
    }
