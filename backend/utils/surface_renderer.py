"""Shared equirectangular PNG renderer for density / surface layers.

Used by fire-density and ocean-surface endpoints to produce
BitmapLayer-ready images for the deck.gl globe.
"""
from __future__ import annotations

import io
from typing import Sequence

import numpy as np


def render_density_png(
    points: Sequence[tuple[float, float, float]],
    width: int = 4320,
    height: int = 2160,
    colormap: str = "hot",
    sigma: float = 2.0,
    alpha_min: float = 0.0,
    vmin: float | None = None,
    vmax: float | None = None,
) -> bytes:
    """Render point data onto an equirectangular RGBA PNG.

    Args:
        points: [(lat, lon, value), ...] — lat in -90..90, lon in -180..180
        width:  output image width  (4320 ≈ 5-arcmin cells)
        height: output image height (2160 ≈ 5-arcmin cells)
        colormap: matplotlib colormap name
        sigma: Gaussian smoothing kernel size in grid cells
        alpha_min: minimum alpha for non-zero cells (0..1)
        vmin/vmax: clamp value range before colormapping

    Returns:
        PNG image bytes (RGBA).
    """
    from scipy.ndimage import gaussian_filter

    grid = np.zeros((height, width), dtype=np.float64)

    lat_scale = height / 180.0
    lon_scale = width / 360.0

    for lat, lon, val in points:
        y = int((90.0 - lat) * lat_scale)
        x = int((lon + 180.0) * lon_scale)
        y = max(0, min(height - 1, y))
        x = max(0, min(width - 1, x))
        grid[y, x] += val

    if sigma > 0:
        grid = gaussian_filter(grid, sigma=sigma)

    # Normalize
    lo = vmin if vmin is not None else 0.0
    hi = vmax if vmax is not None else float(grid.max()) if grid.max() > 0 else 1.0
    if hi <= lo:
        hi = lo + 1.0
    norm = np.clip((grid - lo) / (hi - lo), 0.0, 1.0)

    # Apply colormap
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.cm as cm

    cmap = cm.get_cmap(colormap)
    rgba = cmap(norm)  # (H, W, 4) float 0..1

    # Set alpha: zero where no data, scaled elsewhere
    mask = grid > 0
    alpha = np.where(mask, np.clip(norm * (1.0 - alpha_min) + alpha_min, alpha_min, 1.0), 0.0)
    rgba[..., 3] = alpha

    # Convert to uint8 PNG
    img_uint8 = (rgba * 255).astype(np.uint8)

    from PIL import Image
    img = Image.fromarray(img_uint8, "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
