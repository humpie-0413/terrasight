"""Global layer catalog API.

GET /api/layers/catalog -> full layer metadata (GIBS + future sources)

Each entry includes:
- key          : catalog key (e.g. "modis_aod")
- id           : exact GIBS layer identifier (None if unavailable)
- title        : human-readable display name
- description  : short description of what the layer shows
- tag          : trust tag (observed / near-real-time / derived / estimated / forecast)
- cadence      : temporal cadence (daily / monthly / static)
- tile_matrix_set : WMTS TileMatrixSet identifier (e.g. "2km", "500m", "250m")
- format       : MIME type of tiles (e.g. "image/png", "image/jpeg")
- temporal     : whether the layer has a time dimension
- spatial_scope: geographic coverage
- notes        : list of caveats / landmines
- available    : False if layer is not yet in GIBS (use unavailable_reason)
- unavailable_reason : explanation when available=False
- tile_url_template  : ready-to-use REST tile URL template (omitted if unavailable)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.connectors.gibs import LAYER_CATALOG, WMTS_BASE_4326

router = APIRouter()


@router.get("/catalog")
async def layers_catalog() -> dict[str, Any]:
    """Return all known layer IDs, trust tags, and WMTS tile URL templates.

    The ``tile_url_template`` field uses literal placeholders that callers
    must substitute:
      - ``{Time}``        ISO-8601 date string (YYYY-MM-DD).  Omitted for
                          static layers (temporal=False).
      - ``{TileMatrixSet}`` replaced with the layer's ``tile_matrix_set`` value.
      - ``{TileMatrix}``  zoom level integer.
      - ``{TileRow}``     tile row.
      - ``{TileCol}``     tile column.
    """
    layers = []
    for key, meta in LAYER_CATALOG.items():
        entry: dict[str, Any] = {"key": key, **meta}

        if meta.get("available", True) and meta.get("id"):
            layer_id = meta["id"]
            ext = meta.get("format", "image/png").split("/")[-1]
            # Normalise extension: "jpeg" -> "jpg" for REST URLs
            if ext == "jpeg":
                ext = "jpg"

            if meta.get("temporal", True):
                tile_url_template = (
                    f"{WMTS_BASE_4326}/{layer_id}/default"
                    "/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}"
                    f".{ext}"
                )
            else:
                # Static layers have no Time segment in their REST URL
                tile_url_template = (
                    f"{WMTS_BASE_4326}/{layer_id}/default"
                    "/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}"
                    f".{ext}"
                )

            entry["tile_url_template"] = tile_url_template

        layers.append(entry)

    return {
        "source": "NASA GIBS",
        "wmts_base": WMTS_BASE_4326,
        "capabilities_url": f"{WMTS_BASE_4326}/wmts.cgi?request=GetCapabilities",
        "total": len(layers),
        "layers": layers,
    }
