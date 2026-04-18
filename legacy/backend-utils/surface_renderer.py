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


def render_gridded_surface_png(
    points: Sequence[tuple[float, float, float]],
    width: int = 3600,
    height: int = 1800,
    colormap: str = "RdYlBu_r",
    sigma: float = 1.5,
    vmin: float = -2.0,
    vmax: float = 32.0,
) -> bytes:
    """Render pre-gridded lat/lon/value data as an equirectangular RGBA PNG.

    Unlike render_density_png() which does KDE on sparse scattered points,
    this function is designed for data that is ALREADY on a regular grid
    (like OISST 0.25 deg). Empty cells remain transparent (land/ice), and
    Gaussian smoothing only fills tiny sub-pixel gaps between ocean cells.

    Args:
        points: [(lat, lon, value), ...] — lat in -90..90, lon in -180..180.
                Expected to be a regular grid with NaN/missing cells already
                removed (only ocean cells present).
        width:  output image width (3600 = 0.1 deg per pixel)
        height: output image height (1800 = 0.1 deg per pixel)
        colormap: matplotlib colormap name (diverging recommended for SST)
        sigma: Gaussian smoothing in grid cells (small — just fills gaps)
        vmin/vmax: fixed value range for colormapping

    Returns:
        PNG image bytes (RGBA).
    """
    from scipy.ndimage import gaussian_filter

    # Initialize with NaN so we can distinguish "no data" from "zero value"
    grid = np.full((height, width), np.nan, dtype=np.float64)
    has_data = np.zeros((height, width), dtype=np.bool_)

    lat_scale = height / 180.0
    lon_scale = width / 360.0

    for lat, lon, val in points:
        y = int((90.0 - lat) * lat_scale)
        x = int((lon + 180.0) * lon_scale)
        y = max(0, min(height - 1, y))
        x = max(0, min(width - 1, x))
        grid[y, x] = val
        has_data[y, x] = True

    # Light Gaussian smoothing to fill tiny gaps between grid cells.
    # Replace NaN with 0 for the filter, then re-mask.
    grid_filled = np.where(has_data, grid, 0.0)
    weight = has_data.astype(np.float64)

    if sigma > 0:
        smoothed_vals = gaussian_filter(grid_filled, sigma=sigma)
        smoothed_weight = gaussian_filter(weight, sigma=sigma)
        # Threshold adapts to data density — ensures sparse grids still produce
        # continuous coverage. max_weight * 0.05 works for both dense (OISST ~43K pts)
        # and sparse (Open-Meteo ~2,600 pts at 5° spacing).
        max_w = float(smoothed_weight.max()) if smoothed_weight.max() > 0 else 1.0
        threshold = max_w * 0.05
        valid = smoothed_weight > threshold
        grid_out = np.where(valid, smoothed_vals / smoothed_weight, np.nan)
    else:
        grid_out = np.where(has_data, grid, np.nan)

    # Normalize to 0..1 using fixed vmin/vmax
    norm = np.clip((grid_out - vmin) / (vmax - vmin), 0.0, 1.0)

    # Apply colormap
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.cm as cm

    cmap = cm.get_cmap(colormap)
    rgba = cmap(norm)  # (H, W, 4) float 0..1

    # Set alpha: transparent where no data (NaN), opaque where data exists
    ocean_mask = ~np.isnan(grid_out)
    rgba[..., 3] = np.where(ocean_mask, 0.9, 0.0)

    # Convert to uint8 PNG
    img_uint8 = (rgba * 255).astype(np.uint8)

    from PIL import Image as PILImage
    img = PILImage.fromarray(img_uint8, "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_advected_sst_frames(
    sst_points: Sequence[tuple[float, float, float]],
    flow_points: Sequence[tuple[float, float, float, float]],
    num_frames: int = 8,
    width: int = 1800,
    height: int = 900,
    colormap: str = "RdYlBu_r",
    vmin: float = -2.0,
    vmax: float = 32.0,
) -> list[bytes]:
    """Render SST advected by ocean currents into multiple PNG frames.

    Semi-Lagrangian advection: for each frame, shift the SST grid
    by the flow field. Creates the visual effect of SST moving with currents.
    """
    from scipy.ndimage import gaussian_filter, map_coordinates

    lat_scale = height / 180.0
    lon_scale = width / 360.0

    # Build SST grid
    sst_grid = np.full((height, width), np.nan, dtype=np.float64)
    has_data = np.zeros((height, width), dtype=np.bool_)
    for lat, lon, val in sst_points:
        y = max(0, min(height - 1, int((90.0 - lat) * lat_scale)))
        x = max(0, min(width - 1, int((lon + 180.0) * lon_scale)))
        sst_grid[y, x] = val
        has_data[y, x] = True

    # Smooth SST to fill gaps
    gf = np.where(has_data, sst_grid, 0.0)
    wt = has_data.astype(np.float64)
    sg = gaussian_filter(gf, sigma=2.0)
    sw = gaussian_filter(wt, sigma=2.0)
    mw = float(sw.max()) if sw.max() > 0 else 1.0
    ocean = sw > mw * 0.05
    sst_smooth = np.where(ocean, sg / sw, np.nan)

    # Build flow field (pixels/frame)
    u_px = np.zeros((height, width), dtype=np.float64)
    v_px = np.zeros((height, width), dtype=np.float64)
    for lat, lon, vel, dirn in flow_points:
        y = max(0, min(height - 1, int((90.0 - lat) * lat_scale)))
        x = max(0, min(width - 1, int((lon + 180.0) * lon_scale)))
        spd = vel * 0.009 * 0.5  # degrees per frame-step
        rad = dirn * np.pi / 180
        u_px[y, x] = spd * np.sin(rad) * lon_scale
        v_px[y, x] = -spd * np.cos(rad) * lat_scale

    u_px = gaussian_filter(u_px, sigma=8.0)
    v_px = gaussian_filter(v_px, sigma=8.0)

    # Default circulation where no flow data
    for row in range(height):
        lat = 90.0 - row / lat_scale
        a = abs(lat)
        dflt = -0.3 if a < 30 else (0.2 if a < 60 else -0.1)
        mask = (u_px[row, :] == 0) & ocean[row, :]
        u_px[row, mask] = dflt

    # Generate frames
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.cm as cm
    from PIL import Image as PILImage

    cmap = cm.get_cmap(colormap)
    yy, xx = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
    frames: list[bytes] = []
    cur = sst_smooth.copy()
    sst_fill = np.where(ocean, cur, 0.0)

    for _ in range(num_frames):
        src_y = np.clip(yy - v_px, 0, height - 1)
        src_x = (xx - u_px) % width
        advected = map_coordinates(sst_fill, [src_y, src_x], order=1, mode='wrap')
        cur = np.where(ocean, advected, np.nan)
        sst_fill = np.where(ocean, cur, 0.0)

        norm = np.clip((cur - vmin) / (vmax - vmin), 0.0, 1.0)
        rgba = cmap(norm)
        rgba[..., 3] = np.where(ocean, 0.9, 0.0)
        img = PILImage.fromarray((rgba * 255).astype(np.uint8), "RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        frames.append(buf.getvalue())

    return frames