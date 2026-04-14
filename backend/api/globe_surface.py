"""Globe Surface API — self-rendered continuous surface PNGs.

Each endpoint fetches raw gridded data from an upstream source,
renders it to an equirectangular RGBA PNG via surface_renderer,
caches the result on disk, and returns the PNG binary.

Every surface PNG is designed to be loaded as a single BitmapLayer
on the deck.gl globe with bounds=[-180, -90, 180, 90].
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from backend.connectors.oisst import OisstConnector
from backend.utils import surface_cache
from backend.utils.surface_renderer import render_gridded_surface_png

router = APIRouter()

SST_CACHE_KEY = "globe_surface_sst"
SST_CACHE_TTL = 21600  # 6 hours


@router.get("/sst.png")
async def sst_surface_png() -> Response:
    """Full-resolution OISST sea surface temperature as a continuous PNG.

    Fetches the native 0.25 deg OISST grid (stride=2, ~65K ocean cells),
    renders via render_gridded_surface_png(), caches for 6 hours.
    Uses stride=2 (0.5 deg effective) to keep memory under 512 MB on Render.

    Returns equirectangular RGBA PNG (3600x1800).
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

    # Fetch full grid from ERDDAP
    # stride=2 -> 0.5 deg effective resolution -> ~65K ocean points
    connector = OisstConnector()
    try:
        raw = await connector.fetch(stride=2)
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

    # Render to PNG
    png_bytes = render_gridded_surface_png(
        points,
        width=3600,
        height=1800,
        colormap="RdYlBu_r",
        sigma=1.5,
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
