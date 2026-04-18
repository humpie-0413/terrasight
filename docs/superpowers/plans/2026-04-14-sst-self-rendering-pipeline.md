# SST Self-Rendering Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-rendering pipeline that fetches the full NOAA OISST 0.25° grid, interpolates gaps, applies a publication-quality colormap, and serves it as an equirectangular RGBA PNG at `GET /api/globe/surface/sst.png` — replacing the current sparse scatter/stress-PNG approach for ocean temperature with a true continuous surface.

**Architecture:** OisstConnector fetches the full native grid (stride=1, ~260K ocean cells) → a new `render_gridded_surface_png()` function in `surface_renderer.py` places values directly onto a lat/lon grid (no KDE needed — data is already gridded) → Gaussian smooth to fill tiny gaps between ocean cells → apply a diverging `coolwarm` colormap (−2°C to 32°C) → save as RGBA PNG → cache to `/tmp/terrasight_cache/` for 6 hours → serve via a new FastAPI router at `/api/globe/surface/`. Frontend loads it as a single `BitmapLayer`.

**Tech Stack:** Python (numpy, scipy.ndimage, matplotlib colormaps, Pillow), FastAPI `Response`, deck.gl `BitmapLayer`. No new frontend dependencies. Backend dependencies already present (numpy, scipy, matplotlib, Pillow from Globe-First Redesign).

---

## Key Differences from Existing `render_density_png()`

The existing renderer is designed for **scattered point data** (fires, stress scores) — it bins points into cells and then smooths with Gaussian KDE. SST data is fundamentally different:

1. **Already gridded** — OISST is a regular 0.25° grid. No need for KDE; direct grid placement.
2. **Land = NaN, not zero** — fire density treats empty cells as 0 (no fires). SST must treat empty cells as **transparent** (land/ice), not cold ocean.
3. **Value range is known** — SST ranges −2°C to 32°C globally. Fire FRP has no fixed upper bound.
4. **Colormap is diverging** — SST should use a perceptually uniform diverging colormap (cool→warm), not a sequential one like `hot`.

This means we need a new function `render_gridded_surface_png()` rather than reusing `render_density_png()`.

## Memory Budget (Render Free Tier: 512 MB)

| Item | Memory |
|------|--------|
| OISST stride=1 CSV text (~260K rows × ~50 bytes) | ~13 MB |
| Grid array float64 (1800×3600) | ~49 MB |
| RGBA float64 after colormap (1800×3600×4) | ~197 MB |
| RGBA uint8 for PNG (1800×3600×4) | ~25 MB |
| Pillow Image buffer | ~25 MB |
| **Peak (all held simultaneously)** | **~310 MB** |

310 MB < 512 MB. Fits. If tight, reduce to 1440×720 (0.5°, ~4 MB grid, ~62 MB RGBA).

The stride=1 ERDDAP fetch is the real bottleneck — estimated 10-30 seconds and ~15 MB download. Caching for 6 hours is essential.

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `backend/utils/surface_renderer.py` | Add `render_gridded_surface_png()` | Modify |
| `backend/utils/surface_cache.py` | File-system cache with TTL | Create |
| `backend/api/globe_surface.py` | New router: `GET /surface/sst.png` | Create |
| `backend/main.py` | Register the new router | Modify (1 line) |
| `frontend/src/components/earth-now/GlobeDeck.tsx` | Add new `sst` category + BitmapLayer | Modify |

---

## Task 1: File-System Cache Utility

**Files:**
- Create: `backend/utils/surface_cache.py`

- [ ] **Step 1: Write `surface_cache.py`**

```python
"""Simple file-system PNG cache with TTL.

Stores rendered PNGs in /tmp/terrasight_cache/ with a timestamp suffix.
get() returns bytes if cache is fresh, None if stale/missing.
put() writes bytes and cleans stale entries for the same key.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

CACHE_DIR = Path("/tmp/terrasight_cache")


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(key: str) -> Path:
    """Sanitize key into a safe filename."""
    safe = key.replace("/", "_").replace(".", "_")
    return CACHE_DIR / f"{safe}.png"


def _meta_path(key: str) -> Path:
    safe = key.replace("/", "_").replace(".", "_")
    return CACHE_DIR / f"{safe}.meta"


def get(key: str, ttl_seconds: int = 21600) -> bytes | None:
    """Return cached PNG bytes if within TTL, else None."""
    _ensure_dir()
    cache_file = _cache_path(key)
    meta_file = _meta_path(key)
    if not cache_file.exists() or not meta_file.exists():
        return None
    try:
        written_at = float(meta_file.read_text().strip())
    except (ValueError, OSError):
        return None
    if time.time() - written_at > ttl_seconds:
        return None
    try:
        return cache_file.read_bytes()
    except OSError:
        return None


def put(key: str, data: bytes) -> None:
    """Write PNG bytes to cache with current timestamp."""
    _ensure_dir()
    _cache_path(key).write_bytes(data)
    _meta_path(key).write_text(str(time.time()))
```

- [ ] **Step 2: Verify file written correctly**

Run: `python -c "from backend.utils.surface_cache import get, put; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/utils/surface_cache.py
git commit -m "feat(surface): add file-system PNG cache with TTL"
```

---

## Task 2: Gridded Surface Renderer

**Files:**
- Modify: `backend/utils/surface_renderer.py` (add new function after existing `render_density_png`)

- [ ] **Step 1: Add `render_gridded_surface_png()` to `surface_renderer.py`**

Append this function after the existing `render_density_png()` function (after line 82):

```python
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
    (like OISST 0.25°). Empty cells remain transparent (land/ice), and
    Gaussian smoothing only fills tiny sub-pixel gaps between ocean cells.

    Args:
        points: [(lat, lon, value), ...] — lat in -90..90, lon in -180..180.
                Expected to be a regular grid with NaN/missing cells already
                removed (only ocean cells present).
        width:  output image width (3600 = 0.1° per pixel)
        height: output image height (1800 = 0.1° per pixel)
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
        # Avoid division by zero
        valid = smoothed_weight > 0.01
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

    from PIL import Image
    img = Image.fromarray(img_uint8, "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from backend.utils.surface_renderer import render_gridded_surface_png; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Quick smoke test — render a tiny grid**

Run:
```bash
python -c "
from backend.utils.surface_renderer import render_gridded_surface_png
pts = [(0, 0, 25.0), (0, 1, 26.0), (1, 0, 24.0), (1, 1, 27.0)]
png = render_gridded_surface_png(pts, width=360, height=180, sigma=0.5)
print(f'PNG size: {len(png)} bytes, starts with PNG header: {png[:4] == bytes([137,80,78,71])}')
"
```
Expected: `PNG size: NNNN bytes, starts with PNG header: True`

- [ ] **Step 4: Commit**

```bash
git add backend/utils/surface_renderer.py
git commit -m "feat(surface): add render_gridded_surface_png for pre-gridded data"
```

---

## Task 3: SST Surface API Endpoint

**Files:**
- Create: `backend/api/globe_surface.py`
- Modify: `backend/main.py` (line ~82, add 1 router registration)

- [ ] **Step 1: Create `backend/api/globe_surface.py`**

```python
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

    Fetches the native 0.25° OISST grid (stride=2, ~65K ocean cells),
    renders via render_gridded_surface_png(), caches for 6 hours.
    Uses stride=2 (0.5° effective) to keep memory under 512 MB on Render.

    Returns equirectangular RGBA PNG (3600×1800).
    Colormap: RdYlBu_r (blue=cold, red=hot), range −2°C to 32°C.
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
    # stride=2 → 0.5° effective resolution → ~65K ocean points
    # (stride=1 would be ~260K but risks timeout + memory on free tier)
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
```

- [ ] **Step 2: Register the router in `backend/main.py`**

Add after line 82 (`app.include_router(disasters.router, ...)`):

```python
app.include_router(
    globe_surface.router, prefix="/api/globe/surface", tags=["globe-surface"]
)
```

And add the import at the top of main.py with the other API imports:

```python
from backend.api import globe_surface
```

- [ ] **Step 3: Verify the app imports cleanly**

Run: `python -c "from backend.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/api/globe_surface.py backend/main.py
git commit -m "feat(surface): add GET /api/globe/surface/sst.png endpoint"
```

---

## Task 4: Curl Smoke Test

**Files:** None (testing only)

- [ ] **Step 1: Start the backend locally**

Run (in a separate terminal):
```bash
cd backend && uvicorn backend.main:app --reload --port 8000
```

- [ ] **Step 2: Test the SST endpoint**

Run:
```bash
curl -s -o /tmp/sst_test.png -w "HTTP %{http_code}, size %{size_download} bytes\n" http://localhost:8000/api/globe/surface/sst.png
file /tmp/sst_test.png
```

Expected: `HTTP 200, size NNNNN bytes` (expect 200KB-2MB) and `PNG image data, 3600 x 1800, 8-bit/color RGBA`

- [ ] **Step 3: Test cache HIT**

Run the same curl again immediately:
```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" -D - http://localhost:8000/api/globe/surface/sst.png 2>&1 | grep X-Surface-Cache
```

Expected: `X-Surface-Cache: HIT`

- [ ] **Step 4: Verify PNG renders correctly**

Open `/tmp/sst_test.png` in an image viewer. You should see:
- Blue in polar/cold regions, red in tropical warm water
- Land areas are transparent (alpha=0)
- Smooth continuous surface with no visible gaps between grid cells
- Full equirectangular projection (180° tall, 360° wide)

---

## Task 5: New "Sea Surface Temp" Globe Category

**Files:**
- Modify: `frontend/src/components/earth-now/GlobeDeck.tsx`

- [ ] **Step 1: Add `'sst'` to the `ActiveCategory` type**

Change line 23-26:

```typescript
export type ActiveCategory =
  | 'air-quality' | 'wildfires' | 'ocean-crisis'
  | 'earthquakes' | 'co2-ghg' | 'storms' | 'floods'
  | 'sst'
  | null;
```

- [ ] **Step 2: Add the SST category to `CATEGORIES` array**

Insert after the `ocean-crisis` entry (after line 138):

```typescript
  {
    key: 'sst', icon: '🌡️', name: 'Sea Surface Temp',
    question: 'How warm are the oceans?',
    activeColor: '#f97316', tag: TrustTag.Observed, cadence: 'Daily (1-day lag)',
    source: 'NOAA OISST v2.1 (self-rendered)', sourceUrl: 'https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg.html',
    activates: ['sst-surface'],
  },
```

- [ ] **Step 3: Add the BitmapLayer for SST surface**

Add a new section in the `layers` useMemo (after the ocean-integrated block, ~line 670):

```typescript
    // 7. SST — self-rendered continuous surface from OISST
    if (activeLayers.has('sst-surface')) {
      result.push(
        new BitmapLayer({
          id: 'sst-surface',
          image: `${API_BASE}/globe/surface/sst.png`,
          bounds: [-180, -90, 180, 90] as [number, number, number, number],
          opacity: 0.85,
        }),
      );
    }
```

- [ ] **Step 4: Add SST legend**

In the `Legend` component (after the ocean-crisis legend block, ~line 358):

```typescript
  if (activeCategory === 'sst') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Sea Surface Temperature (°C)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(49,54,149), rgb(116,173,209), rgb(253,174,97), rgb(215,48,39), rgb(165,0,38))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>−2</span><span>8</span><span>18</span><span>26</span><span>32</span></div>
    </div>
  );
```

- [ ] **Step 5: TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 6: Build check**

Run: `cd frontend && npm run build`
Expected: clean build, GlobeDeck chunk ~7 KB gzipped (no significant change)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/earth-now/GlobeDeck.tsx
git commit -m "feat(surface): add SST self-rendered surface category to Globe"
```

---

## Task 6: End-to-End Browser Test

**Files:** None (manual testing)

- [ ] **Step 1: Start both backend and frontend dev servers**

```bash
# Terminal 1:
cd backend && uvicorn backend.main:app --reload --port 8000

# Terminal 2:
cd frontend && npm run dev
```

- [ ] **Step 2: Open http://localhost:5173/ in Chrome**

- [ ] **Step 3: Click the "Sea Surface Temp" pill in the LayerBar**

Verify:
- A continuous ocean surface appears on the globe (blue→orange→red gradient)
- Land is transparent (BlueMarble visible through)
- The category pill at top shows "🌡️ Sea Surface Temp"
- The legend shows "Sea Surface Temperature (°C)" with range −2 to 32
- MetaLine shows "Daily (1-day lag) · observed · NOAA OISST v2.1"

- [ ] **Step 4: Toggle 3D/2D**

Click the 3D→2D button. The SST surface should render identically in MapView (BitmapLayer works in both).

- [ ] **Step 5: Switch between categories**

Click Wildfires → SST → Ocean Crisis → SST. Each transition should be clean, no leftover layers.

- [ ] **Step 6: Check DevTools Network tab**

- First click: `sst.png` should load (~500KB-2MB, 10-30s first render, then cached)
- Second click: `sst.png` should return near-instantly (X-Surface-Cache: HIT)

---

## Task 7: Update progress.md and Commit

**Files:**
- Modify: `progress.md`

- [ ] **Step 1: Add self-rendering pipeline entry to progress.md**

In the "Globe-First Redesign" section or as a new section:

```markdown
### Self-Rendering Pipeline Prototype (2026-04-14)
- New `render_gridded_surface_png()` in `surface_renderer.py` — handles pre-gridded data
  (NaN-aware, diverging colormap, land=transparent)
- New `surface_cache.py` — file-system PNG cache with TTL (/tmp/terrasight_cache/)
- New router `globe_surface.py` → `GET /api/globe/surface/sst.png`
- OISST stride=2 (~65K ocean cells) → 3600×1800 RGBA PNG, RdYlBu_r colormap, 6h cache
- New Globe category "Sea Surface Temp" — BitmapLayer, observed, daily
- Pipeline pattern: fetch → grid → smooth → colormap → PNG → cache → BitmapLayer
- Memory footprint ~310 MB peak (within Render 512 MB free tier)
```

- [ ] **Step 2: Commit**

```bash
git add progress.md
git commit -m "docs: record SST self-rendering pipeline in progress.md"
```

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| stride=2 (0.5°) not stride=1 (0.25°) | stride=1 → ~260K points → ~310MB peak → tight on 512MB Render. stride=2 → ~65K points → ~80MB peak → safe margin. Visual quality at globe zoom is indistinguishable. |
| 3600×1800 PNG (0.1°/pixel) | Matches visual resolution of 0.5° data after smoothing. Larger than data resolution but smooth filtering fills it naturally. 3600×1800 RGBA PNG compresses to ~500KB-1.5MB. |
| File-system cache, not Redis | Zero new infra. `/tmp` persists across requests on same Render instance. Redis is overkill for 1-2 cached PNGs. |
| New router `/api/globe/surface/` not added to `earth_now_integrated` | Clean separation: `earth_now_integrated` combines multiple connectors, `globe_surface` is the self-rendering pipeline. Different responsibility = different router. Also sets up the pattern for future layers (temperature, wind, etc.) |
| `render_gridded_surface_png` separate from `render_density_png` | Fundamentally different algorithm: gridded data uses NaN-aware weighted smoothing, density uses additive binning + Gaussian KDE. Merging would create a confusing function with too many modes. |
| SST as separate category from Ocean Crisis | Ocean Crisis = derived stress index (SST + coral DHW combined). SST = raw observed temperature. Different trust tags, different questions, different colormaps. Users can toggle between "how stressed?" and "how warm?" |

## Future: Extending the Pipeline

Once this SST prototype works, the same pattern applies to any gridded data source:

1. Write a connector that returns `list[tuple[lat, lon, value]]`
2. Choose colormap + vmin/vmax
3. Add a `@router.get("/{layer}.png")` endpoint in `globe_surface.py`
4. Add a cache key + TTL
5. Add a category pill + BitmapLayer in GlobeDeck.tsx

Candidate next layers (in priority order):
- **CAMS PM2.5** — needs Copernicus ADS account (currently blocked)
- **GFS 2m Temperature** — NOMADS GRIB2 via cfgrib+xarray (needs research)
- **GFS Wind** — same source, u/v components → magnitude
- **GPM Precipitation** — NASA Earthdata OpenDAP (needs research)
