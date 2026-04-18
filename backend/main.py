"""EarthPulse / Terrasight — Render maintenance stub (v2 transition).

This FastAPI app is intentionally minimal. Heavy connectors, schedulers, and
raster pipelines moved to `pipelines/` (GitHub Actions batch) and
`apps/worker/` (Cloudflare Worker proxy). See
`docs/architecture/architecture-v2.md` and `docs/architecture/repo-layout.md`.

Only 4 endpoints remain, each a thin httpx passthrough — enough to keep
the legacy Render deployment alive while the v2 Worker rolls out.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY")
USGS_FEED = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
)
ERDDAP_OISST = (
    "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg.json"
)


def _parse_origins(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("["):
        return json.loads(raw)
    return [o.strip() for o in raw.split(",") if o.strip()]


cors_origins = _parse_origins(os.getenv("CORS_ORIGINS", "http://localhost:5173"))

app = FastAPI(
    title="Terrasight API (maintenance)",
    version="0.2.0-maint",
    description=(
        "Maintenance stub during v2 migration. "
        "New traffic should target the Cloudflare Worker at /api/*."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "terrasight-maint", "mode": "maintenance"}


@app.get("/fires")
async def fires(days: int = Query(1, ge=1, le=10)) -> dict[str, Any]:
    """FIRMS VIIRS_SNPP_NRT active fires — thin passthrough."""
    if not FIRMS_MAP_KEY:
        return {
            "status": "not_configured",
            "source": "NASA FIRMS",
            "message": "FIRMS_MAP_KEY not set on this deployment.",
            "fires": [],
        }
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/world/{days}"
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            lines = r.text.strip().split("\n")
            if len(lines) < 2:
                return {"status": "ok", "source": "NASA FIRMS", "count": 0, "fires": []}
            header = lines[0].split(",")
            idx = {name: header.index(name) for name in header}
            fires_out: list[dict[str, Any]] = []
            for line in lines[1:]:
                cols = line.split(",")
                try:
                    fires_out.append(
                        {
                            "lat": float(cols[idx["latitude"]]),
                            "lon": float(cols[idx["longitude"]]),
                            "brightness": float(cols[idx["bright_ti4"]]),
                            "frp": float(cols[idx["frp"]]),
                            "confidence": cols[idx["confidence"]],
                            "acq_date": cols[idx["acq_date"]],
                            "acq_time": cols[idx["acq_time"]],
                            "daynight": cols[idx["daynight"]],
                        }
                    )
                except (ValueError, KeyError, IndexError):
                    continue
            return {
                "status": "ok",
                "source": "NASA FIRMS",
                "source_url": "https://firms.modaps.eosdis.nasa.gov/api/area/",
                "cadence": "NRT ~3h",
                "tag": "near-real-time",
                "count": len(fires_out),
                "fires": fires_out,
            }
    except httpx.HTTPError as exc:
        return {"status": "error", "source": "NASA FIRMS", "message": str(exc), "fires": []}


@app.get("/quakes")
async def quakes() -> dict[str, Any]:
    """USGS earthquakes (past 24h) — thin GeoJSON passthrough."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(USGS_FEED)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        return {"status": "error", "source": "USGS", "message": str(exc), "quakes": []}

    quakes_out: list[dict[str, Any]] = []
    for feat in data.get("features", []):
        props = feat.get("properties", {}) or {}
        geom = feat.get("geometry", {}) or {}
        coords = geom.get("coordinates", []) or []
        if len(coords) < 2:
            continue
        quakes_out.append(
            {
                "id": feat.get("id"),
                "lat": coords[1],
                "lon": coords[0],
                "depth_km": coords[2] if len(coords) > 2 else None,
                "mag": props.get("mag"),
                "place": props.get("place"),
                "time_ms": props.get("time"),
                "url": props.get("url"),
            }
        )
    return {
        "status": "ok",
        "source": "USGS Earthquake",
        "source_url": USGS_FEED,
        "cadence": "5 min",
        "tag": "observed",
        "count": len(quakes_out),
        "quakes": quakes_out,
    }


@app.get("/sst-point")
async def sst_point(
    lat: float = Query(..., ge=-89.875, le=89.875),
    lon: float = Query(..., ge=-179.875, le=179.875),
) -> dict[str, Any]:
    """NOAA OISST v2.1 single-point SST via ERDDAP griddap."""
    # ERDDAP expects lon in [0, 360) for this dataset; wrap if needed.
    lon_erddap = lon + 360 if lon < 0 else lon
    url = (
        f"{ERDDAP_OISST}?sst[last][0][({lat})][({lon_erddap})]"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        return {"status": "error", "source": "NOAA OISST", "message": str(exc)}

    try:
        table = data["table"]
        rows = table.get("rows", [])
        if not rows:
            return {"status": "ok", "source": "NOAA OISST", "sst_c": None}
        col_names = table.get("columnNames", [])
        sst_idx = col_names.index("sst")
        time_idx = col_names.index("time")
        row = rows[0]
        return {
            "status": "ok",
            "source": "NOAA OISST v2.1",
            "source_url": ERDDAP_OISST,
            "cadence": "daily",
            "tag": "observed",
            "lat": lat,
            "lon": lon,
            "sst_c": row[sst_idx],
            "observed_at": row[time_idx],
        }
    except (KeyError, ValueError, IndexError) as exc:
        return {"status": "error", "source": "NOAA OISST", "message": f"unexpected payload: {exc}"}
