"""Contaminated / remediation sites API — Superfund (NPL) and Brownfields (ACRES).

Both endpoints accept a WGS84 bbox (west/south/east/north) and return points
suitable for overlay on a Local Environmental Report metro map.

Graceful degradation rule (CLAUDE.md #5): connector failures return
`status="error"` with a message — never HTTPException / 5xx.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from backend.connectors.brownfields import BrownfieldsConnector
from backend.connectors.superfund import SuperfundConnector

router = APIRouter()


@router.get("/superfund")
async def get_superfund(
    west: float = Query(..., description="Western longitude of bbox (WGS84)"),
    south: float = Query(..., description="Southern latitude of bbox (WGS84)"),
    east: float = Query(..., description="Eastern longitude of bbox (WGS84)"),
    north: float = Query(..., description="Northern latitude of bbox (WGS84)"),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    """EPA Superfund (SEMS / NPL) sites intersecting the given bbox.

    Returns centroid lat/lon (Superfund boundaries are polygons), site name,
    EPA ID, NPL status code, and mailing address fields.
    """
    connector = SuperfundConnector()
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
            "sites": [],
        }

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "configured": True,
        "status": "ok",
        "count": len(result.values),
        "sites": [
            {
                "name": s.name,
                "site_id": s.site_id,
                "lat": s.lat,
                "lon": s.lon,
                "city": s.city,
                "state": s.state,
                "npl_status": s.npl_status,
                "address": s.address,
            }
            for s in result.values
        ],
        "notes": result.notes,
    }


@router.get("/brownfields")
async def get_brownfields(
    west: float = Query(..., description="Western longitude of bbox (WGS84)"),
    south: float = Query(..., description="Southern latitude of bbox (WGS84)"),
    east: float = Query(..., description="Eastern longitude of bbox (WGS84)"),
    north: float = Query(..., description="Northern latitude of bbox (WGS84)"),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    """EPA Brownfields (ACRES) sites intersecting the given bbox.

    Returns point lat/lon, primary name, program system id, and city/state.
    cleanup_status is always None — the attribute is not exposed by the
    spatial point layer (see connector notes).
    """
    connector = BrownfieldsConnector()
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
            "sites": [],
        }

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "configured": True,
        "status": "ok",
        "count": len(result.values),
        "sites": [
            {
                "name": s.name,
                "site_id": s.site_id,
                "lat": s.lat,
                "lon": s.lon,
                "city": s.city,
                "state": s.state,
                "cleanup_status": s.cleanup_status,
            }
            for s in result.values
        ],
        "notes": result.notes,
    }
