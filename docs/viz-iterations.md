# TerraSight — Visualization Iteration Log

**Created:** 2026-04-13

---

## Phase 1: deck.gl Migration (2026-04-13)

### 1a. deck.gl Installation

- Installed: `@deck.gl/core@9.2.11`, `@deck.gl/react@9.2.11`, `@deck.gl/layers@9.2.11`, `@deck.gl/geo-layers@9.2.11`, `@math.gl/core`
- Removed: `react-globe.gl` (which brought `three.js`, `three-globe`, `globe.gl`)

### 1b. GlobeView + BlueMarble + ScatterplotLayer (Fires)

**Implementation:**
- New component: `GlobeDeck.tsx` (replaces Globe.tsx)
- `_GlobeView` from deck.gl provides 3D globe projection
- `TileLayer` + `BitmapLayer` for BlueMarble WMTS tiles (native tile loading, no canvas composite)
- `ScatterplotLayer` for fires with FRP-based color/radius (GPU-instanced, supports 100K+ points)
- CSS atmosphere glow via radial gradient overlay
- Container: dark radial gradient background (`#0a0e27` → `#040610`)

**Self-evaluation: 7/10**
- Globe renders correctly with BlueMarble tiles
- Fire points render with color ramp
- Atmosphere glow is subtle but effective via CSS
- Missing: the old react-globe.gl had a built-in 3D atmosphere shader; CSS approximation is flatter
- Missing: auto-rotation (deck.gl GlobeView doesn't support autoRotate natively)

**Improvement direction:**
- Consider adding a second radial gradient layer for more depth
- Investigate deck.gl postProcessEffect for bloom/glow
- Add subtle CSS animation to the atmosphere glow (pulse)

### 1c. Full Layer Migration

**All layers migrated to ScatterplotLayer:**

| Layer | Old (react-globe.gl) | New (deck.gl) | Change |
|-------|---------------------|---------------|--------|
| Fires | pointsData (per-mesh) | ScatterplotLayer (GPU instanced) | 100x perf |
| Storms | pointsData (per-mesh) | ScatterplotLayer + stroke | Better visuals |
| Earthquakes | pointsData (per-mesh) | ScatterplotLayer + stroke | Better visuals |
| Air Monitors | labelsData (DOM labels) | ScatterplotLayer | Much faster |
| SST | hexBinPointsData | ScatterplotLayer | Simpler, direct color |
| Coral | hexBinPointsData | ScatterplotLayer | Simpler, direct color |
| SLA | labelsData | ScatterplotLayer | Consistent rendering |
| GIBS overlays | Manual canvas composite | TileLayer + BitmapLayer | Native! No CORS hack |

**Key improvements:**
- GIBS tiles load natively via TileLayer — eliminated the `loadImageViaFetch()` + canvas composite pipeline
- All data layers use GPU-instanced ScatterplotLayer — no per-point three.js meshes
- Tooltips now use React-rendered overlay (no dangerouslySetInnerHTML needed for positioning)

### 1d. Layer Panel + Legend Reconnection

- Layer panel ported with identical accordion structure
- Added Globe ↔ Map view mode toggle buttons (prepared for Phase 2)
- Legend ported with all color ramps (fires, PM2.5 AQI, earthquakes, storms, SST, DHW)
- MetaLine overlay preserved (top-left)

### Bundle Impact

| Chunk | Before (react-globe.gl) | After (deck.gl) | Change |
|-------|------------------------|-----------------|--------|
| Globe vendor (gz) | 519.83 KB | **226.98 KB** | **-293 KB (-56%)** |
| Globe component (gz) | 7.35 KB | 6.78 KB | -0.6 KB |
| Main index (gz) | 54.58 KB | 56.30 KB | +1.7 KB |
| **Total globe payload** | **527.18 KB** | **233.76 KB** | **-293 KB (-56%)** |

**three.js removed entirely from the dependency tree.**

---

## Phase 2: MapView Toggle (pending)

Will add 2D flat map view using the same deck.gl layers with MapView instead of GlobeView.

---

## Phase 3: Visual Iteration Rounds (pending)

### Round 1: Color System
- Reference: nullschool.net, windy.com
- 3 candidate palettes per layer → select best

### Round 2: Interaction
- Layer transition fade
- Click → metro report link
- Zoom-based density adjustment

### Round 3: Overlay Composition
- Simultaneous continuous + event display
- Blend mode experiments

### Round 4: Information Density + Loading
- Camera position optimization
- Skeleton → data transition animation
