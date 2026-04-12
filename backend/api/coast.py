"""Coastal tides & conditions API — NOAA CO-OPS water levels and temperatures.

Endpoints (mounted at /api/coast in main.py):
  GET /tides?west=-95.5&south=29.0&east=-94.5&north=29.8&limit=20

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

from backend.connectors.coops import CoopsConnector

router = APIRouter()


@router.get("/tides")
async def get_tides(
    west: float = Query(..., description="Western longitude of bbox (WGS84)"),
    south: float = Query(..., description="Southern latitude of bbox (WGS84)"),
    east: float = Query(..., description="Eastern longitude of bbox (WGS84)"),
    north: float = Query(..., description="Northern latitude of bbox (WGS84)"),
    limit: int = Query(20, ge=1, le=50, description="Max stations to return"),
) -> dict[str, Any]:
    """NOAA CO-OPS tide stations with latest water level and temperature."""
    connector = CoopsConnector()
    try:
        raw = await connector.fetch(
            west=west, south=south, east=east, north=north, limit=limit
        )
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
            "stations": [],
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
        "stations": [asdict(s) for s in result.values],
        "notes": result.notes,
    }
