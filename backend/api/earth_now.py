"""Earth Now API — globe layers + this month's climate story."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.config import get_settings
from backend.connectors.firms import FirmsConnector, top_by_frp

router = APIRouter()


@router.get("/layers")
async def list_layers() -> list[dict]:
    """Return available globe layers with trust metadata."""
    return [
        {
            "id": "gibs-natural-earth",
            "title": "Natural Earth",
            "kind": "base",
            "tag": "observed",
            "default": True,
        },
        {
            "id": "firms",
            "title": "Fires",
            "kind": "event",
            "tag": "observed",
            "cadence": "NRT ~3h",
            "default": True,
        },
        {
            "id": "oisst",
            "title": "Ocean Heat",
            "kind": "continuous",
            "tag": "observed",
            "cadence": "daily",
        },
        {
            "id": "cams-smoke",
            "title": "Smoke",
            "kind": "continuous",
            "tag": "forecast",
            "cadence": "6-12h",
        },
        {
            "id": "openaq",
            "title": "Air monitors",
            "kind": "event",
            "tag": "observed",
            "cadence": "varies",
        },
    ]


@router.get("/fires")
async def get_fires(
    days: int = Query(1, ge=1, le=10),
    limit: int = Query(1500, ge=1, le=10000),
) -> dict[str, Any]:
    """NASA FIRMS global VIIRS_SNPP_NRT active fires for the past `days`.

    Returns the top-N hotspots by fire radiative power, suitable for
    direct point overlay on the Earth Now globe. The full feed runs
    tens of thousands of points per day and is too dense at globe scale.
    """
    settings = get_settings()
    connector = FirmsConnector(map_key=settings.firms_map_key)

    if not settings.firms_map_key:
        return {
            "source": connector.source,
            "source_url": connector.source_url,
            "cadence": connector.cadence,
            "tag": connector.tag,
            "count": 0,
            "configured": False,
            "message": (
                "FIRMS_MAP_KEY is not configured. Register at "
                "https://firms.modaps.eosdis.nasa.gov/api/map_key/ "
                "and set FIRMS_MAP_KEY in the project-root .env."
            ),
            "fires": [],
        }

    try:
        raw = await connector.fetch(days=days)
        result = connector.normalize(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch FIRMS feed: {exc}"
        ) from exc

    top = top_by_frp(result.values, limit=limit)
    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "count": len(top),
        "total_24h": len(result.values),
        "configured": True,
        "fires": [
            {
                "lat": h.lat,
                "lon": h.lon,
                "brightness": h.brightness,
                "frp": h.frp,
                "confidence": h.confidence,
                "acq_date": h.acq_date,
                "acq_time": h.acq_time,
                "daynight": h.daynight,
            }
            for h in top
        ],
        "notes": result.notes,
    }


@router.get("/story")
async def get_story() -> dict:
    """This month's climate story (preset-driven editorial)."""
    # TODO: load from editorial preset bank (5-10 presets)
    return {
        "title": None,
        "body": None,
        "preset_id": None,
        "globe_hint": None,
        "report_link": None,
    }
