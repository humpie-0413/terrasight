"""Earth Now API — globe layers + this month's climate story."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.config import get_settings
from backend.connectors.firms import FirmsConnector, top_by_frp
from backend.connectors.oisst import OisstConnector, summarize as sst_summary
from backend.connectors.openaq import OpenAqConnector

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
            "default": False,
        },
        {
            "id": "cams-smoke",
            "title": "Smoke",
            "kind": "continuous",
            "tag": "forecast",
            "cadence": "6-12h",
            "default": False,
            "disabled": True,
            "disabled_reason": (
                "CAMS (Copernicus Atmosphere Monitoring Service) forecast "
                "smoke layer requires a Copernicus ADS account. Deferred to P1."
            ),
        },
        {
            "id": "openaq",
            "title": "Air monitors",
            "kind": "continuous",
            "tag": "observed",
            "cadence": "varies",
            "default": False,
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


@router.get("/sst")
async def get_sst() -> dict[str, Any]:
    """NOAA OISST v2.1 daily global SST, downsampled for globe rendering.

    Returns ~1,700 ocean grid points at ~5° spacing with lat/lon/sst_c.
    Continuous-field layer (mutually exclusive with other continuous
    layers on the Earth Now globe).
    """
    connector = OisstConnector()
    try:
        raw = await connector.fetch()
        result = connector.normalize(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch OISST ERDDAP feed: {exc}",
        ) from exc

    stats = sst_summary(result.values)
    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "count": stats["count"],
        "stats": stats,
        "configured": True,
        "points": [
            {"lat": p.lat, "lon": p.lon, "sst_c": round(p.sst_c, 2)}
            for p in result.values
        ],
        "notes": result.notes,
    }


@router.get("/air-monitors")
async def get_air_monitors(
    limit: int = Query(1000, ge=1, le=1000),
) -> dict[str, Any]:
    """OpenAQ v3 global PM2.5 stations with latest value per station.

    Returns stations with lat/lon/pm25/location_name. Graceful
    degradation when OPENAQ_API_KEY is missing — empty list plus
    registration instructions, so the globe toggle can render as
    disabled without erroring.
    """
    settings = get_settings()
    connector = OpenAqConnector(api_key=settings.openaq_api_key)

    if not settings.openaq_api_key:
        return {
            "source": connector.source,
            "source_url": connector.source_url,
            "cadence": connector.cadence,
            "tag": connector.tag,
            "count": 0,
            "configured": False,
            "message": (
                "OPENAQ_API_KEY is not configured. Register at "
                "https://explore.openaq.org/ and set OPENAQ_API_KEY "
                "in the project-root .env."
            ),
            "monitors": [],
        }

    try:
        raw = await connector.fetch(limit=limit)
        result = connector.normalize(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch OpenAQ feed: {exc}",
        ) from exc

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "count": len(result.values),
        "configured": True,
        "monitors": [
            {
                "lat": m.lat,
                "lon": m.lon,
                "pm25": m.pm25,
                "location_name": m.location_name,
                "datetime_utc": m.datetime_utc,
                "country": m.country,
            }
            for m in result.values
        ],
        "notes": result.notes,
    }


@router.get("/storms")
async def get_storms() -> dict[str, Any]:
    """NOAA IBTrACS active tropical storms — latest track point per storm."""
    from backend.connectors.ibtracs import IbtracsCsvConnector

    connector = IbtracsCsvConnector()
    try:
        raw = await connector.fetch(source="ACTIVE")
        result = connector.normalize(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch IBTrACS feed: {exc}"
        ) from exc

    storms_out = []
    for storm in result.values:
        pt = storm.latest_point
        if pt is None:
            continue
        storms_out.append(
            {
                "sid": storm.sid,
                "name": storm.name,
                "basin": storm.basin,
                "season": storm.season,
                "lat": pt.lat,
                "lon": pt.lon,
                "wind_kt": pt.wind_kt,
                "pres_hpa": pt.pres_hpa,
                "sshs": pt.sshs,
                "iso_time": pt.iso_time,
            }
        )

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "count": len(storms_out),
        "configured": True,
        "storms": storms_out,
    }


@router.get("/coral")
async def get_coral() -> dict[str, Any]:
    """NOAA Coral Reef Watch daily bleaching heat stress grid."""
    from backend.connectors.coral_reef_watch import CoralReefWatchConnector

    connector = CoralReefWatchConnector()
    try:
        raw = await connector.fetch()
        result = connector.normalize(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch Coral Reef Watch feed: {exc}"
        ) from exc

    if isinstance(result.values, dict):
        return {
            "source": result.source,
            "source_url": result.source_url,
            "cadence": result.cadence,
            "tag": result.tag,
            "count": 0,
            "configured": True,
            "status": "error",
            "message": result.values.get("message", "Unknown error from Coral Reef Watch."),
            "points": [],
        }

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "count": len(result.values),
        "configured": True,
        "status": "ok",
        "points": [
            {
                "lat": p.lat,
                "lon": p.lon,
                "bleaching_alert": p.bleaching_alert,
                "dhw": round(p.dhw, 2),
                "sst_c": round(p.sst_c, 2),
                "sst_anomaly_c": round(p.sst_anomaly_c, 2),
            }
            for p in result.values
        ],
    }


@router.get("/sea-level-anomaly")
async def get_sea_level_anomaly() -> dict[str, Any]:
    """Copernicus Marine CMEMS daily SLA — not_configured if no credentials."""
    from backend.connectors.cmems import CmemsConnector

    settings = get_settings()

    if not settings.cmems_username:
        connector = CmemsConnector()
        return {
            "source": connector.source,
            "source_url": connector.source_url,
            "cadence": connector.cadence,
            "tag": connector.tag,
            "count": 0,
            "configured": False,
            "status": "not_configured",
            "message": (
                "CMEMS credentials are required but not set. "
                "Register for free at https://marine.copernicus.eu/ and set "
                "CMEMS_USERNAME and CMEMS_PASSWORD in the project-root .env."
            ),
            "points": [],
        }

    connector = CmemsConnector(
        username=settings.cmems_username,
        password=settings.cmems_password,
    )
    try:
        raw = await connector.fetch()
        result = connector.normalize(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch CMEMS SLA feed: {exc}"
        ) from exc

    if isinstance(result.values, dict):
        return {
            "source": result.source,
            "source_url": result.source_url,
            "cadence": result.cadence,
            "tag": result.tag,
            "count": 0,
            "configured": True,
            "status": result.values.get("status", "error"),
            "message": result.values.get("message", "Unknown error from CMEMS."),
            "points": [],
        }

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "count": len(result.values),
        "configured": True,
        "status": "ok",
        "points": [
            {
                "lat": p.lat,
                "lon": p.lon,
                "sla_m": p.sla_m,
            }
            for p in result.values
        ],
    }


@router.get("/story")
async def get_story() -> dict:
    """This month's climate story (preset-driven editorial).

    MVP ships one hard-coded preset ("2026 Wildfire Season"). The
    full preset bank with 5-10 seasonal/event templates will land
    in a later pass (see CLAUDE.md Story Panel section).
    """
    return {
        "preset_id": "2026-wildfire-season",
        "title": "2026 Wildfire Season",
        "body": (
            "NASA FIRMS is tracking active fire hotspots across western "
            "North America. Dense smoke plumes are already affecting "
            "air quality in several metros — check your local report."
        ),
        "globe_hint": {
            "layer_on": "firms",
            "camera": {"lat": 40, "lng": -120, "altitude": 1.6},
        },
        "report_link": "/reports/los-angeles-long-beach-anaheim",
    }
