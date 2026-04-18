"""Disaster declarations API — OpenFEMA disaster history.

Endpoints (mounted at /api/disasters in main.py):
  GET /declarations?state=TX&years=5&limit=100

Graceful degradation contract (per CLAUDE.md rule 5):
  - Never raises HTTPException for upstream errors; returns a dict with
    `status: "error"` and a `message` field instead.
  - Always exposes `source`, `source_url`, `cadence`, `tag` so the
    frontend can still render trust metadata when the dataset is empty.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Query

from backend.connectors.openfema import OpenfemaConnector

router = APIRouter()


@router.get("/declarations")
async def get_declarations(
    state: str | None = Query(None, description="U.S. state name or 2-letter code (e.g. 'TX' or 'Texas')"),
    years: int = Query(5, ge=1, le=50, description="Look back N years from today"),
    limit: int = Query(100, ge=1, le=1000, description="Max declarations to return"),
) -> dict[str, Any]:
    """FEMA disaster declarations for a state over a time window."""
    connector = OpenfemaConnector()
    try:
        raw = await connector.fetch(state=state, years=years, limit=limit)
        result = connector.normalize(raw)
    except Exception as exc:  # noqa: BLE001 — graceful degradation, no 5xx
        return {
            "source": connector.source,
            "source_url": connector.source_url,
            "cadence": connector.cadence,
            "tag": connector.tag,
            "configured": True,
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
            "count": 0,
            "declarations": [],
        }

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "configured": True,
        "status": "ok",
        "count": len(result.values),
        "state": state,
        "years": years,
        "declarations": [asdict(d) for d in result.values],
        "notes": result.notes,
    }
