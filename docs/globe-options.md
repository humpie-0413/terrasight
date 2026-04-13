# Globe & Map Library Options — TerraSight

**Created:** 2026-04-13
**Purpose:** Evaluate alternatives to react-globe.gl for the Earth Now visualization, considering rendering quality, bundle size, data density support, and 2D map toggle feasibility.

---

## Current State

| Metric | Value |
|--------|-------|
| Library | `react-globe.gl` v2.37.1 (wraps `three-globe` + `three.js`) |
| Globe vendor chunk (gz) | **519.83 KB** |
| Globe component chunk (gz) | 7.35 KB |
| Main index chunk (gz) | 54.58 KB |
| Rendering | WebGL 1/2 via three.js |
| Max tested points | ~1,500 (FIRMS fires) — performance degrades >5K |
| GIBS integration | Manual: fetch WMS PNG → canvas composite → `globeImageUrl` texture |
| Data layers | 14 layers across 5 categories (points, hex bins, labels, GIBS texture) |
| Known issues | No native heatmap, no tile layer, no vector tiles, no clustering |

---

## Option A: Optimize react-globe.gl (Minimal Change)

**Keep current library, maximize what it can do.**

### Optimizations Available

| Optimization | Impact | Effort |
|-------------|--------|--------|
| 8K BlueMarble texture (8192×4096) | Sharper globe surface | Trivial — change `WIDTH=8192&HEIGHT=4096` in URL |
| `pointsMerge={true}` | 10x point performance (single draw call) | Trivial — but disables hover/click per-point |
| `MeshPhongMaterial` → custom `ShaderMaterial` | Atmosphere glow, rim lighting | Medium — requires three.js shader knowledge |
| Inertia / damping on controls | Smoother rotation | Trivial — `controls.enableDamping = true` |
| Worker-based GIBS composite | Unblock main thread during tile load | Medium |

### Limits (Cannot Fix)

- **Performance ceiling at ~10K points** — each point = separate three.js mesh without `pointsMerge`
- **No native heatmap** — cannot render density maps
- **No tile layer protocol** — GIBS must go through manual canvas composite
- **No 2D map view** — library is 3D globe only
- **No polygon rendering** — cannot show NWS alert zones as filled polygons
- **Bundle: 519 KB gz** — entire three.js bundled, not tree-shakeable

### Verdict

Good for quick polish (8K texture, atmosphere, inertia). **Dead end** for Phase 2 (2D toggle) and data density growth.

---

## Option B: deck.gl GlobeView + MapView

**Replace react-globe.gl with deck.gl. Same layer code serves both 3D globe and 2D map.**

### Architecture

```
deck.gl core (tree-shakeable)
├── GlobeView  → 3D globe (like current)
├── MapView    → 2D flat map (new)
├── ScatterplotLayer  → fires, earthquakes, air monitors, storms
├── GeoJsonLayer      → NWS alert polygons, PFAS sites
├── H3HexagonLayer    → SST, coral DHW hex bins
├── TileLayer         → GIBS WMS raster tiles (native!)
└── BitmapLayer       → BlueMarble base texture
```

### Bundle Size

| Component | Gzipped |
|-----------|---------|
| `@deck.gl/core` | ~145 KB |
| `@deck.gl/layers` (Scatterplot, GeoJson, Bitmap) | ~28 KB |
| `@deck.gl/geo-layers` (H3, GreatCircle, Tile) | ~20 KB |
| `@deck.gl/react` | ~4 KB |
| **Total deck.gl** | **~197 KB gz** |
| **Savings vs current** | **-322 KB gz** (519 → 197) |

### Pros

- **1M+ points at 60 FPS** — GPU-instanced rendering, no per-point mesh
- **Tree-shakeable** — only import layers you use
- **GlobeView ↔ MapView toggle** — same layer definitions, just switch view
- **Native TileLayer** — GIBS WMS tiles load as standard raster source (no manual canvas composite)
- **H3HexagonLayer** — native hex bin aggregation (replaces react-globe.gl hex bins)
- **GeoJsonLayer** — NWS alert polygons render natively
- **Mature ecosystem** — vis.gl (Uber), 14K GitHub stars, 189K weekly downloads
- **WebGL2** — better anti-aliasing, texture handling

### Cons

- **No atmosphere glow** — deck.gl globe has no built-in atmosphere effect (needs custom post-processing or CSS glow)
- **GlobeView: no pitch/bearing** — always north-up, looking at center
- **HeatmapLayer NOT supported in GlobeView** — works in MapView only (2D)
- **No "pretty globe" out of box** — you compose the look from layers; react-globe.gl had aesthetic defaults
- **Migration: medium-high** — completely different API; all 1,500 lines of Globe.tsx rewritten
- **react-globe.gl features lost**: label rendering, hex bin merge, point transition animations

### Key Question

Can we get the atmosphere glow? **Yes**, via:
1. CSS `box-shadow` / radial gradient behind the globe container
2. Custom deck.gl effect (post-processing bloom)
3. Three.js atmosphere mesh rendered underneath (hybrid approach)

### Verdict

**Best balance of capability and bundle size.** Solves every current limitation (performance, 2D toggle, polygons, tiles). The atmosphere gap is solvable. Migration is significant but one-time.

---

## Option C: MapLibre GL JS v5 + deck.gl Overlay

**MapLibre handles globe rendering + base map + raster tiles. deck.gl handles data layers on top.**

### Architecture

```
MapLibre GL JS v5 (globe projection)
├── Globe rendering with atmosphere
├── Raster source → GIBS WMS tiles (native!)
├── Style spec → base map theming
└── deck.gl MapboxOverlay
    ├── ScatterplotLayer → fires, quakes, monitors
    ├── GeoJsonLayer → NWS alert polygons
    ├── H3HexagonLayer → SST, coral
    └── HeatmapLayer → density (2D view)
```

### Bundle Size

| Component | Gzipped |
|-----------|---------|
| `maplibre-gl` (selective) | ~210 KB |
| `maplibre-gl` (full) | ~750 KB |
| `react-map-gl` | ~57 KB |
| deck.gl layers | ~197 KB |
| **Total (selective MapLibre)** | **~464 KB gz** |
| **Total (full MapLibre)** | **~1,004 KB gz** |

### Pros

- **Globe v5 with atmosphere** — built-in globe projection with atmosphere effect
- **Native WMS/raster tiles** — GIBS tiles load as standard raster source
- **Style spec** — full Mapbox-compatible styling (dark basemap, custom colors)
- **Vector tiles** — can load OpenMapTiles for a styled base map
- **Smooth globe ↔ Mercator transition** — automatic at zoom ~12
- **deck.gl overlay is production-ready** — `MapboxOverlay` works on MapLibre v5 globe

### Cons

- **Larger bundle than deck.gl alone** — 464 KB vs 197 KB (selective) or 1 MB (full)
- **Two libraries to manage** — MapLibre + deck.gl coordination
- **MapLibre globe is newer** (v5, Jan 2025) — fewer examples than Cesium/deck.gl
- **Not tree-shakeable** — MapLibre ships as monolithic bundle
- **Globe projection limitations** — tile warping at high latitudes, higher tile request volume

### Verdict

**Best visual quality for globe** (styled basemap + atmosphere), but **~2.4x the bundle** of deck.gl alone. Worth it only if we need a styled basemap (OpenStreetMap roads/borders) visible on the globe. For a BlueMarble + data overlay use case, deck.gl alone is lighter.

---

## Option D: CesiumJS + resium

**Full 3D virtual globe with terrain, 3D tiles, and native WMS/WMTS.**

### Bundle Size

| Component | Gzipped |
|-----------|---------|
| `cesium` (not tree-shakeable) | **~715 KB** |
| `resium` (React wrapper) | ~5 KB |
| Static assets (workers, CSS, images) | +2 MB on disk |
| **Total** | **~720 KB gz** (+ static assets) |

### Pros

- **Highest visual fidelity** — 3D terrain, dynamic lighting, sky box
- **Native WMS/WMTS** — `WebMapTileServiceImageryProvider` works with GIBS out of the box
- **Time-dynamic data** — CZML animations, timeline scrubbing
- **3D Tiles** — building models, point clouds

### Cons

- **720 KB gz** — 3.7x larger than deck.gl, 1.4x larger than current
- **Not tree-shakeable** — monolithic bundle
- **Webpack/Vite config pain** — static asset copying, web worker handling, craco-cesium unmaintained
- **resium TypeScript issues** — breakage with Cesium >=1.117 + React >=18.3 + TS >=5.5
- **Overkill** — we don't need 3D terrain, building models, or CZML

### Verdict

**Overkill for TerraSight.** Best for flight simulators, military GIS, city planning. The bundle penalty and build complexity don't justify features we won't use.

---

## Option E: Leaflet (2D Only, for Local Reports)

**Lightweight 2D map for Tier 3 (Local Reports facility maps).**

| Metric | Value |
|--------|-------|
| Bundle | **42 KB gz** (JS) + 3.5 KB (CSS) |
| Heatmap plugin | `Leaflet.heat` ~2 KB |
| Marker clustering | `Leaflet.markercluster` ~9 KB |
| WMS support | Native `L.tileLayer.wms()` |
| 3D / globe | **No** |

**Not a globe replacement.** Ideal for facility maps in Local Reports (Superfund sites, TRI facilities, PFAS locations). Could coexist with any globe solution.

---

## Decision Matrix

| Criterion (weight) | A: Optimize r-g.gl | B: deck.gl | C: MapLibre+deck.gl | D: Cesium | E: Leaflet |
|---------------------|:--:|:--:|:--:|:--:|:--:|
| **Bundle size (25%)** | ★★☆ (520 KB) | ★★★★★ (197 KB) | ★★★☆ (464 KB) | ★★☆ (720 KB) | ★★★★★ (42 KB) |
| **Rendering quality (20%)** | ★★★☆ | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★☆ |
| **10K+ point perf (15%)** | ★☆ | ★★★★★ | ★★★★★ | ★★★★☆ | ★★☆ |
| **2D map toggle (15%)** | ☆ (impossible) | ★★★★★ | ★★★★★ | ★★★☆ | ★★★★★ (2D only) |
| **GIBS/WMS native (10%)** | ☆ (manual) | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★☆ |
| **Migration effort (10%)** | ★★★★★ (none) | ★★★☆ | ★★★☆ | ★★☆ | ★★★★★ (2D only) |
| **Polygon support (5%)** | ☆ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ |
| **Weighted total** | 2.2 | **4.4** | 4.3 | 3.4 | 4.0 (2D) |

---

## Recommendation

### Primary: **Option B — deck.gl GlobeView** (for Earth Now globe)

| Why | Detail |
|-----|--------|
| Bundle | 197 KB gz — **saves 322 KB** vs current (62% reduction) |
| Performance | 1M+ points at 60 FPS — eliminates the 10K ceiling |
| 2D toggle | Same layers work in GlobeView and MapView — Phase 2 free |
| GIBS | TileLayer loads WMS raster tiles natively — no manual canvas composite |
| Polygons | GeoJsonLayer for NWS alert zones — Phase G.2 unblocked |
| H3 hexbins | Native H3HexagonLayer — better SST/coral rendering |
| Tree-shakeable | Import only what you use |

**Atmosphere gap mitigation:** CSS radial gradient behind globe container (already implemented in current design) + optional post-processing bloom effect.

### Secondary: **Option E — Leaflet** (for Local Reports maps, Phase G.3)

42 KB gz add for facility/site marker maps in Tier 3. Independent from the globe choice.

### Rejected

- **Option A** — dead end for 2D toggle and data density
- **Option C** — 2.4x heavier than deck.gl alone; styled basemap not needed for BlueMarble + data viz
- **Option D** — overkill, build complexity, TypeScript issues

---

## Implementation Sketch (if deck.gl chosen)

### Migration path

1. **Phase 1a**: Install `@deck.gl/core`, `@deck.gl/react`, `@deck.gl/layers`, `@deck.gl/geo-layers`
2. **Phase 1b**: New `GlobeView.tsx` with BitmapLayer (BlueMarble) + ScatterplotLayer (fires)
3. **Phase 1c**: Migrate remaining layers (SST hexbin, coral, storms, earthquakes, air monitors, GIBS tiles)
4. **Phase 1d**: Layer panel + legend (reuse existing React components)
5. **Phase 2**: Add MapView toggle (same layers, different view)
6. Remove `react-globe.gl` and `three` dependencies

### Risk

The biggest risk is **visual regression** — react-globe.gl's globe looks "pretty" by default. deck.gl requires intentional composition of:
- BitmapLayer for the globe texture
- CSS atmosphere glow
- Proper lighting configuration
- Camera animation (deck.gl `viewState` transitions)

This is solvable but requires iterative visual tuning (Phase 3 rounds).
