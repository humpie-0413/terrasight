"""Hazards API — earthquakes, NWS alerts, and US drought statistics.

Endpoints (mount at /api/hazards in main.py):
  GET /earthquakes?min_magnitude=4&limit=500&days=30
  GET /alerts?severity=Severe
  GET /drought?aoi=US&weeks=4

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

from backend.connectors.earthquake import EarthquakeConnector
from backend.connectors.nws_alerts import NwsAlertsConnector
from backend.connectors.usdm import UsdmConnector

router = APIRouter()


def _error_response(connector: Any, message: str, key: str) -> dict[str, Any]:
    return {
        "source": connector.source,
        "source_url": connector.source_url,
        "cadence": connector.cadence,
        "tag": connector.tag,
        "count": 0,
        "configured": True,
        "status": "error",
        "message": message,
        key: [],
    }


@router.get("/earthquakes")
async def get_earthquakes(
    min_magnitude: float = Query(4.0, ge=0, le=10, description="Minimum magnitude"),
    limit: int = Query(500, ge=1, le=5000, description="Max events to return"),
    days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
) -> dict[str, Any]:
    """USGS ComCat earthquakes — global, near-real-time."""
    connector = EarthquakeConnector()
    try:
        raw = await connector.fetch(
            min_magnitude=min_magnitude, limit=limit, days=days
        )
        result = connector.normalize(raw)
    except Exception as exc:
        return _error_response(connector, str(exc), key="earthquakes")

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "count": len(result.values),
        "configured": True,
        "status": "ok",
        "earthquakes": [asdict(e) for e in result.values],
        "notes": result.notes,
    }


@router.get("/alerts")
async def get_alerts(
    severity: str | None = Query(
        None, description="Filter by severity (Extreme, Severe, Moderate, Minor)"
    ),
) -> dict[str, Any]:
    """NWS active weather alerts — U.S. + territories."""
    connector = NwsAlertsConnector()
    try:
        raw = await connector.fetch(severity=severity)
        result = connector.normalize(raw)
    except Exception as exc:
        return _error_response(connector, str(exc), key="alerts")

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "count": len(result.values),
        "configured": True,
        "status": "ok",
        "alerts": [asdict(a) for a in result.values],
        "notes": result.notes,
    }


@router.get("/drought")
async def get_drought(
    aoi: str = Query("US", description="Area of interest (US or state FIPS code)"),
    weeks: int = Query(4, ge=1, le=52, description="Look-back window in weeks"),
) -> dict[str, Any]:
    """US Drought Monitor severity statistics by area percent."""
    connector = UsdmConnector()
    try:
        raw = await connector.fetch(aoi=aoi, weeks=weeks)
        result = connector.normalize(raw)
    except Exception as exc:
        return _error_response(connector, str(exc), key="drought")

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "count": len(result.values),
        "configured": True,
        "status": "ok",
        "drought": [asdict(d) for d in result.values],
        "notes": result.notes,
    }
