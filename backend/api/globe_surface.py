"""Globe Surface API — self-rendered continuous surface PNGs.

Each endpoint fetches raw gridded data from an upstream source,
renders it to an equirectangular RGBA PNG via surface_renderer,
caches the result on disk, and returns the PNG binary.

Every surface PNG is designed to be loaded as a single BitmapLayer
on the deck.gl globe with bounds=[-180, -90, 180, 90].
"""
from __future__ import annotations

import io

from fastapi import APIRouter, Query
from fastapi.responses import Response

from backend.connectors.oisst import OisstConnector
from backend.connectors.open_meteo_aq import OpenMeteoAqConnector
from backend.connectors.open_meteo_weather import OpenMeteoWeatherConnector
from backend.utils import surface_cache
from backend.utils.surface_renderer import render_gridded_surface_png

router = APIRouter()

SST_CACHE_KEY = "globe_surface_sst"
SST_CACHE_TTL = 21600  # 6 hours

PM25_CACHE_KEY = "globe_surface_pm25"
PM25_CACHE_TTL = 21600  # 6 hours

NO2_CACHE_KEY = "globe_surface_no2"
NO2_CACHE_TTL = 21600  # 6 hours

TEMP_CACHE_KEY = "globe_surface_temperature"
TEMP_CACHE_TTL = 21600  # 6 hours

PRECIP_CACHE_KEY = "globe_surface_precipitation"
PRECIP_CACHE_TTL = 21600  # 6 hours


@router.get("/sst.png")
async def sst_surface_png() -> Response:
    """OISST sea surface temperature as a continuous PNG.

    Fetches the 0.25 deg OISST grid (stride=4, ~43K ocean cells),
    renders via render_gridded_surface_png(), caches for 6 hours.
    Uses stride=4 (1 deg effective) to stay under 512 MB on Render free tier.

    Returns equirectangular RGBA PNG (1800x900).
    Colormap: RdYlBu_r (blue=cold, red=hot), range -2C to 32C.
    """
    # Check cache first
    cached = surface_cache.get(SST_CACHE_KEY, ttl_seconds=SST_CACHE_TTL)
    if cached:
        return Response(
            content=cached,
            media_type="image/png",
            headers={
                "Cache-Control": f"public, max-age={SST_CACHE_TTL}",
                "X-Surface-Cache": "HIT",
            },
        )

    # Fetch grid from ERDDAP
    # stride=4 -> 1 deg effective resolution -> ~43K ocean points
    # (stride=2 peaks at 852 MB — exceeds Render 512 MB free tier)
    connector = OisstConnector()
    try:
        raw = await connector.fetch(stride=4)
        result = connector.normalize(raw)
    except Exception:
        return Response(
            content=b"",
            media_type="image/png",
            status_code=502,
            headers={"X-Surface-Error": "OISST fetch failed"},
        )

    if not result.values:
        return Response(content=b"", media_type="image/png", status_code=204)

    # Build (lat, lon, sst_c) tuples
    points = [(p.lat, p.lon, p.sst_c) for p in result.values]

    # Render to PNG — 1800x900 keeps peak memory ~200 MB
    png_bytes = render_gridded_surface_png(
        points,
        width=1800,
        height=900,
        colormap="RdYlBu_r",
        sigma=2.0,
        vmin=-2.0,
        vmax=32.0,
    )

    # Cache
    surface_cache.put(SST_CACHE_KEY, png_bytes)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": f"public, max-age={SST_CACHE_TTL}",
            "X-Surface-Cache": "MISS",
        },
    )


@router.get("/pm25.png")
async def pm25_surface_png() -> Response:
    """Global PM2.5 concentration as a continuous surface PNG.

    Fetches current PM2.5 from Open-Meteo (CAMS Global) on a 5-degree grid
    (~2,600 points via 3 POST requests), renders with AQI-inspired colormap.
    Cached for 1 hour.

    Returns equirectangular RGBA PNG (1800x900).
    Colormap: RdYlGn_r (green=clean, red=polluted), range 0-75 ug/m3.
    """
    cached = surface_cache.get(PM25_CACHE_KEY, ttl_seconds=PM25_CACHE_TTL)
    if cached:
        return Response(
            content=cached,
            media_type="image/png",
            headers={
                "Cache-Control": f"public, max-age={PM25_CACHE_TTL}",
                "X-Surface-Cache": "HIT",
            },
        )

    connector = OpenMeteoAqConnector()
    try:
        raw = await connector.fetch(variable="pm2_5")
        result = connector.normalize(raw, variable="pm2_5")
    except Exception:
        return Response(
            content=b"",
            media_type="image/png",
            status_code=502,
            headers={"X-Surface-Error": "Open-Meteo AQ fetch failed"},
        )

    if not result.values:
        return Response(content=b"", media_type="image/png", status_code=204)

    points = [(p.lat, p.lon, p.pm25) for p in result.values]

    # sigma=15: 5° grid on 1800px-wide image = 25px per cell, need ~15px blur radius
    png_bytes = render_gridded_surface_png(
        points,
        width=1800,
        height=900,
        colormap="RdYlGn_r",
        sigma=15.0,
        vmin=0.0,
        vmax=75.0,
    )

    surface_cache.put(PM25_CACHE_KEY, png_bytes)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": f"public, max-age={PM25_CACHE_TTL}",
            "X-Surface-Cache": "MISS",
        },
    )


@router.get("/no2.png")
async def no2_surface_png() -> Response:
    """Global NO₂ concentration as a continuous surface PNG.

    Open-Meteo CAMS Global nitrogen_dioxide on 5-degree grid.
    Colormap: YlOrRd (yellow=low, red=high), range 0-80 ug/m3.
    """
    cached = surface_cache.get(NO2_CACHE_KEY, ttl_seconds=NO2_CACHE_TTL)
    if cached:
        return Response(
            content=cached,
            media_type="image/png",
            headers={
                "Cache-Control": f"public, max-age={NO2_CACHE_TTL}",
                "X-Surface-Cache": "HIT",
            },
        )

    connector = OpenMeteoAqConnector()
    try:
        raw = await connector.fetch(variable="nitrogen_dioxide")
        result = connector.normalize(raw, variable="nitrogen_dioxide")
    except Exception:
        return Response(
            content=b"",
            media_type="image/png",
            status_code=502,
            headers={"X-Surface-Error": "Open-Meteo AQ fetch failed"},
        )

    if not result.values:
        return Response(content=b"", media_type="image/png", status_code=204)

    points = [(p.lat, p.lon, p.pm25) for p in result.values]

    png_bytes = render_gridded_surface_png(
        points,
        width=1800,
        height=900,
        colormap="YlOrRd",
        sigma=15.0,
        vmin=0.0,
        vmax=80.0,
    )

    surface_cache.put(NO2_CACHE_KEY, png_bytes)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": f"public, max-age={NO2_CACHE_TTL}",
            "X-Surface-Cache": "MISS",
        },
    )


@router.get("/temperature.png")
async def temperature_surface_png() -> Response:
    """Global 2m temperature as a continuous surface PNG.

    Open-Meteo GFS temperature_2m on 5-degree grid.
    Colormap: RdYlBu_r (blue=cold, red=hot), range -40C to 50C.
    """
    cached = surface_cache.get(TEMP_CACHE_KEY, ttl_seconds=TEMP_CACHE_TTL)
    if cached:
        return Response(
            content=cached,
            media_type="image/png",
            headers={
                "Cache-Control": f"public, max-age={TEMP_CACHE_TTL}",
                "X-Surface-Cache": "HIT",
            },
        )

    connector = OpenMeteoWeatherConnector()
    try:
        raw = await connector.fetch(variable="temperature_2m")
        result = connector.normalize(raw, variable="temperature_2m")
    except Exception:
        return Response(
            content=b"",
            media_type="image/png",
            status_code=502,
            headers={"X-Surface-Error": "Open-Meteo Weather fetch failed"},
        )

    if not result.values:
        return Response(content=b"", media_type="image/png", status_code=204)

    points = [(p.lat, p.lon, p.value) for p in result.values]

    png_bytes = render_gridded_surface_png(
        points,
        width=1800,
        height=900,
        colormap="RdYlBu_r",
        sigma=15.0,
        vmin=-40.0,
        vmax=50.0,
    )

    surface_cache.put(TEMP_CACHE_KEY, png_bytes)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": f"public, max-age={TEMP_CACHE_TTL}",
            "X-Surface-Cache": "MISS",
        },
    )


@router.get("/precipitation.png")
async def precipitation_surface_png() -> Response:
    """Global precipitation as a continuous surface PNG.

    Open-Meteo GFS precipitation on 5-degree grid.
    Colormap: Blues (white=0, dark blue=heavy), range 0-20 mm.
    """
    cached = surface_cache.get(PRECIP_CACHE_KEY, ttl_seconds=PRECIP_CACHE_TTL)
    if cached:
        return Response(
            content=cached,
            media_type="image/png",
            headers={
                "Cache-Control": f"public, max-age={PRECIP_CACHE_TTL}",
                "X-Surface-Cache": "HIT",
            },
        )

    connector = OpenMeteoWeatherConnector()
    try:
        raw = await connector.fetch(variable="precipitation")
        result = connector.normalize(raw, variable="precipitation")
    except Exception:
        return Response(
            content=b"",
            media_type="image/png",
            status_code=502,
            headers={"X-Surface-Error": "Open-Meteo Weather fetch failed"},
        )

    if not result.values:
        return Response(content=b"", media_type="image/png", status_code=204)

    points = [(p.lat, p.lon, p.value) for p in result.values]

    png_bytes = render_gridded_surface_png(
        points,
        width=1800,
        height=900,
        colormap="Blues",
        sigma=15.0,
        vmin=0.0,
        vmax=20.0,
    )

    surface_cache.put(PRECIP_CACHE_KEY, png_bytes)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": f"public, max-age={PRECIP_CACHE_TTL}",
            "X-Surface-Cache": "MISS",
        },
    )


# ---------------------------------------------------------------------------
# Tile endpoint — crops cached full PNG into small tiles for GlobeView
# ---------------------------------------------------------------------------

# Map layer names to their cache keys
_LAYER_CACHE = {
    "sst": SST_CACHE_KEY,
    "pm25": PM25_CACHE_KEY,
    "no2": NO2_CACHE_KEY,
    "temperature": TEMP_CACHE_KEY,
    "precipitation": PRECIP_CACHE_KEY,
}


@router.get("/tile/{layer}")
async def surface_tile(
    layer: str,
    west: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    north: float = Query(...),
) -> Response:
    """Crop a region from a cached full-globe PNG and return it as a tile.

    Used by TileLayer on the frontend to break a single equirectangular
    PNG into small tiles, avoiding the polygon distortion that occurs
    when draping a single large BitmapLayer on GlobeView.

    Query params: west, south, east, north (degrees).
    """
    cache_key = _LAYER_CACHE.get(layer)
    if not cache_key:
        return Response(content=b"", media_type="image/png", status_code=404)

    # Get the full cached PNG — use generous TTL since full PNG
    # endpoints handle their own refresh cycle
    full_png = surface_cache.get(cache_key, ttl_seconds=43200)
    if not full_png:
        return Response(content=b"", media_type="image/png", status_code=204)

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(full_png))
        w, h = img.size  # e.g. 1800x900

        # Convert geo bounds to pixel coords
        # Image is equirectangular: x=0 at lon=-180, y=0 at lat=90
        px_left = int((west + 180) / 360 * w)
        px_right = int((east + 180) / 360 * w)
        px_top = int((90 - north) / 180 * h)
        px_bottom = int((90 - south) / 180 * h)

        # Clamp
        px_left = max(0, min(w, px_left))
        px_right = max(0, min(w, px_right))
        px_top = max(0, min(h, px_top))
        px_bottom = max(0, min(h, px_bottom))

        if px_right <= px_left or px_bottom <= px_top:
            return Response(content=b"", media_type="image/png", status_code=204)

        tile = img.crop((px_left, px_top, px_right, px_bottom))
        buf = io.BytesIO()
        tile.save(buf, format="PNG")
        tile_bytes = buf.getvalue()
    except Exception:
        return Response(content=b"", media_type="image/png", status_code=500)

    return Response(
        content=tile_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
