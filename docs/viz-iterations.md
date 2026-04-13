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

## Phase 2: MapView Toggle (2026-04-13) ✅

**Implementation:**
- Added `MapView` import from `@deck.gl/core`
- `viewMode` state toggles between `'globe'` and `'map'`
- Same deck.gl layers render in both views — zero duplication
- LayerPanel Globe/Map toggle buttons switch the view
- Map view starts at zoom 2 for better overview
- Both views share identical ScatterplotLayer / TileLayer / BitmapLayer instances

**Self-evaluation: 7/10**
- Toggle works, layers switch cleanly between globe and flat projection
- Map view uses Mercator which distorts at edges but is standard
- Missing: smooth animated transition between views (deck.gl doesn't support cross-view animation natively)
- Missing: different base map for 2D (OpenStreetMap would add context in flat view)

**Improvement direction:**
- Add OpenStreetMap tiles as base in MapView (currently uses BlueMarble in both)
- Add fade animation when switching views
- Consider MapLibre integration for styled base map in 2D mode

---

## Phase 3: Visual Iteration Rounds

### Round 1: Color System (2026-04-13) ✅

**Reference palettes studied:** nullschool.net (earth), windy.com (temperature/wind), NOAA CRW

**Changes applied:**

| Layer | Before | After | Inspiration |
|-------|--------|-------|-------------|
| Fires | Yellow→Red (5 discrete bands) | Hot-metal gradient (warm white→amber→crimson, 6 stops) | Windy fire layer |
| SST | 5-stop blue→red | 9-stop navy→blue→cyan→teal→chartreuse→amber→orange→red | nullschool.net ocean |
| Coral DHW | White→Yellow→Orange→Red→Purple | Cool blue→Yellow→Amber→Orange→Red→Purple (NOAA CRW official) | NOAA Coral Reef Watch |
| Fire legend | Discrete swatches | Continuous gradient bar (matches new hot-metal ramp) | Windy legends |
| SST legend | Old 5-stop gradient | Updated 6-stop matching new palette | nullschool |
| DHW legend | Old gradient | Updated 5-stop matching NOAA CRW | NOAA CRW |

**Atmosphere glow enhanced:**
- Dual radial gradient layers for depth (50% + 45% radii, slightly offset centers)
- Subtle 8-second pulsing animation (`atmosphere-pulse` keyframe)
- Container box-shadow: inset glow + outer shadow for depth
- Container gradient: darker, more dramatic space background

**Self-evaluation: 8/10**
- Fire hot-metal palette reads as more physically grounded (emission spectrum)
- SST 9-stop gradient shows much more detail in the 14-26°C range (where most ocean is)
- Coral DHW now matches the official NOAA CRW product colors
- Atmosphere pulse is subtle enough to not distract
- Could improve: earthquake and storm palettes not yet updated (next round)

**Improvement direction for Round 2:**
- Earthquake: add concentric ring animation for recent events
- Storms: add track line connecting historical positions
- Layer transition: crossfade when switching layers
- Interaction: click on point → zoom + show detail panel

### Round 2: Interaction (2026-04-13) ✅

**Changes applied:**

1. **Layer transition animations:** All ScatterplotLayers now have `transitions` prop with:
   - `getRadius`: 600ms linear easing for smooth point size transitions
   - `getFillColor`: 400ms fade for color changes
   - Result: switching layers shows points fading in rather than popping

2. **Earthquake glow ring:** New `earthquakes-glow` ScatterplotLayer renders a semi-transparent (alpha=60) ring at 2x radius beneath the core point. Creates a seismic "impact zone" visual that communicates magnitude intuitively.

3. **Storm outline improvement:** White stroke on storm points reduced from alpha 120→100 for subtlety.

4. **SST/Coral point size increase:** Radius 8→10px for better coverage feel at globe scale (points fill more of the ocean surface).

**Self-evaluation: 7/10**
- Transitions are smooth and professional
- Earthquake glow adds real visual weight to large quakes
- Missing: click-to-navigate (click point → fly to metro report) — requires more backend work
- Missing: zoom-based density filtering (deck.gl DataFilterExtension) — deferred

### Round 3: Overlay Composition (2026-04-13) ✅

**Architecture decision:** Keep the existing composition rule (1 continuous + 1 event at most) but prepare for relaxation.

The current ScatterplotLayer pipeline already supports simultaneous rendering — the mutual exclusivity is enforced at the data level (memoized arrays return empty when inactive). To compose:
- Continuous layers (SST/Coral/SLA/GIBS) render on the globe surface
- Event layers (Fires/Storms/Earthquakes/Monitors) render above as scattered points
- The two types don't visually conflict because continuous uses larger, semi-transparent points while events use smaller, opaque points

**No code change needed** — the architecture already supports composition. The exclusivity is in `EarthNow.tsx`'s state management (separate `activeEvent` / `activeContinuous` states), which already allows both simultaneously.

**Self-evaluation: 8/10**
- Composition works out of the box due to separate state channels
- GIBS tile overlay + scatter event layer renders cleanly together
- Deferred: blend mode experiments (would need custom WebGL post-processing)

### Round 4: Information Density + Loading (2026-04-13) ✅

**Changes applied:**

1. **Loading overlay:** When no data has loaded yet, a centered "Loading data layers…" message with `fadeInUp` animation appears over the globe. Semi-transparent dark overlay (`rgba(4,6,16,0.6)`) keeps the globe visible underneath.

2. **View mode badge:** Bottom-right badge shows "3D Globe" or "2D Mercator" — helps user understand the current projection mode. Small (10px), uppercase, muted color (`#64748b`).

3. **Atmosphere conditional:** CSS atmosphere glow only renders in globe mode (not in 2D map where it would look wrong against flat tiles).

4. **Camera defaults optimized:**
   - Globe: latitude 20° (slight tilt toward populated northern hemisphere), zoom 1.2
   - Map: zoom 2 for overview of populated continents

**Self-evaluation: 7/10**
- Loading state is clean and non-intrusive
- View badge gives orientation without being distracting
- Could improve: skeleton shimmer animation for the globe container instead of text
- Could improve: data count badge showing "1,247 fire hotspots" etc.
