# Phase B — Globe UI Layer Expansion & Trends Carousel Design

**Date:** 2026-04-11
**Status:** Approved

---

## Overview

Two parallel improvements to the home page:

1. **Globe layer panel** — refactor 4 flat toggles → 5-category accordion panel exposing all 28 datasets
2. **Climate Trends carousel** — expand 3-card grid → 5-card horizontal scroll-snap carousel (add CH₄, Sea Level)

---

## 1. Globe Layer Panel

### 1.1 Interaction model

**Side accordion panel (Option B)** — fixed overlay in top-right corner of the globe div.

- A header row "🗂 Layers" always visible
- 5 category rows, each expands inline when clicked (one open at a time)
- Within each category: a list of layer buttons; clicking activates a layer
- Active layer shows filled highlight color; inactive = dim

### 1.2 Category → layer mapping

| Category | Emoji | Layers | Layer type |
|---|---|---|---|
| Atmosphere | 🌫 | PM2.5 (MERRA-2 GIBS) · AOD (MODIS GIBS) · Air Monitors (OpenAQ) | GIBS tile · GIBS tile · points |
| Fire & Land | 🔥 | Active Fires (FIRMS) · Deforestation (GFW ❌) · Drought (JRC WMS) | points · disabled · GIBS/WMS tile |
| Ocean | 🌊 | SST Anomaly (OISST) · Coral Bleaching (CRW) · Sea Level (CMEMS) | hexbin · hexbin · points |
| Greenhouse Gas | 🌿 | CO₂ Column (OCO-2 GIBS) · Methane (GIBS ❌) | GIBS tile · disabled |
| Hazards | ⚡ | Tropical Storms (IBTrACS) · Flood Map (MODIS GIBS) | points · GIBS tile |

### 1.3 Layer composition rules (maintained)

- **Continuous field**: at most 1 active (GIBS raster layers, hexbin data)
- **Event overlay**: at most 1 active (points layers — fires, storms, monitors)
- Selecting a second continuous field auto-deactivates the previous one
- Both slots can be ON simultaneously

### 1.4 GIBS raster rendering

GIBS tile layers are rendered by fetching a **WMS GetMap equirectangular image** (2048×1024 PNG with transparency) and compositing it onto the BlueMarble base via an offscreen canvas. The resulting data URL is passed to `globeImageUrl`, so the raster rotates correctly with the 3D globe.

```
fetch GIBS WMS GetMap (transparent PNG, today's date auto-selected)
  ↓
draw BlueMarble on offscreen canvas (2048×1024)
  ↓
draw GIBS layer on top (globalAlpha = 0.7)
  ↓
canvas.toDataURL() → globeImageUrl prop
```

**Date handling:** Always fetch today's date (or subtract 1 day on 404 for daily layers, subtract 1 month for monthly layers). No user-facing date picker in Phase B.

### 1.5 State model changes

Current `Globe` props:
```ts
firesOn: boolean
continuousLayer: 'ocean-heat' | 'smoke' | 'air-monitors' | null
```

New props:
```ts
activeEvent: EventLayerKey | null        // fires | storms | monitors
activeContinuous: ContinuousLayerKey | null  // ocean-heat | sst | coral | gibs-aod | gibs-pm25 | gibs-oco2 | gibs-flood | drought
onLayerChange: (type: 'event' | 'continuous', key: string | null) => void
```

`Home.tsx` owns state (unchanged pattern); `Globe` is controlled.

### 1.6 Disabled layers

- **CH₄ GIBS** (`tropomi_ch4`): `available=false` in `LAYER_CATALOG` → button rendered dimmed + tooltip "TROPOMI CH₄ not in GIBS — Copernicus GES DISC (P1)"
- **Smoke (CAMS)**: same as current — dimmed + tooltip
- **Deforestation (GFW)**: current connector returns global aggregate (no lat/lon) → disabled + tooltip "Country-level points require polygon query (P1)"
- **CMEMS Sea Level**: `not_configured` if no credentials → dimmed + tooltip

### 1.7 TrustBadge + MetaLine per layer

The accordion panel renders `TrustBadge` inline next to each layer name. The top-left header `MetaLine` (existing) updates to reflect whichever layer is active.

---

## 2. Climate Trends Carousel

### 2.1 Card order

`co2` → `temp` → `sea-ice` → `ch4` → `sea-level`

### 2.2 Layout

- `display: flex; overflow-x: auto; scroll-snap-type: x mandatory`
- Each card: `min-width: 200px; scroll-snap-align: start`
- No pagination arrows in Phase B (scroll gesture sufficient)
- Responsive: on wide screens all 5 cards visible; on narrow screens scroll reveals cards 4–5

### 2.3 New backend indicators

**CH₄** (`id: "ch4"`):
- Connector: `noaa_gml_ch4.py` (already exists, `ch4_mm_gl.txt`)
- Latest value: global monthly mean in ppb
- Sparkline: last 12 months
- Unit: ppb · tag: observed · cadence: monthly

**Sea Level** (`id: "sea-level"`):
- Connector: `noaa_sea_level.py` (already exists, `_free_all_66.csv`)
- Latest value: most recent GMSL in mm (vs 1993 baseline)
- Sparkline: last 24 points (one per ~10-day cycle)
- Unit: mm · tag: observed · cadence: ~10-day

### 2.4 Backend changes

`backend/api/trends.py`:
- Add `_ch4_payload()` and `_sea_level_payload()` async functions
- `get_trends()` fan-out extended to 5 connectors
- Individual `/api/trends/ch4` and `/api/trends/sea-level` debug endpoints

`frontend/src/components/climate-trends/TrendsStrip.tsx`:
- `ORDER` array extended: `['co2', 'temp', 'sea-ice', 'ch4', 'sea-level']`
- `TrendIndicator['id']` union extended
- `STATIC_META` entries added for new cards
- `sectionStyle` changed from `grid` to `flex + overflow-x: auto`

---

## 3. Files Changed

| File | Change |
|---|---|
| `frontend/src/components/earth-now/Globe.tsx` | Refactor layer props + accordion panel UI |
| `frontend/src/pages/Home.tsx` | Update layer state management |
| `frontend/src/components/climate-trends/TrendsStrip.tsx` | 5-card carousel |
| `backend/api/trends.py` | Add CH₄ + sea-level payload + endpoints |

No new files needed. All connectors already exist.

---

## 4. Out of Scope (Phase B)

- Date picker for GIBS layers
- Carousel navigation arrows
- Born-in Interactive
- Story Panel preset expansion
- CAMS smoke layer (Copernicus account required)
