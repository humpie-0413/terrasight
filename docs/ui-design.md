# TerraSight — Data Visualization Design

**Created:** 2026-04-12
**Purpose:** Map all 34 connectors to optimal visualization types, restructure
Globe layers / Local Report blocks / Trends cards, and set implementation
priority for Phase G (the next UI sprint).

---

## Part 1: Data → Visualization Mapping (all 34 connectors)

### Legend

| Code | Visualization Type | Rendering Tech | Where |
|------|-------------------|----------------|-------|
| **GT** | GIBS Tile Overlay | canvas composite → globeImageUrl | Globe |
| **PS** | Point Scatter | pointsData (size/color by value) | Globe |
| **HX** | HexBin Heatmap | hexBinPointsData | Globe |
| **PG** | Polygon / Area | GeoJSON polygons overlay | Globe |
| **SK** | Sparkline Card | custom SVG 220×48 path | Trends strip |
| **SC** | Stat Cards | 2–4 metric cards in CSS grid | Local Report |
| **TBL** | Data Table | HTML `<table>`, 13px, striped | Local Report / Atlas |
| **MK** | Map Markers | Leaflet/Mapbox point markers | Local Report (future) |
| **GA** | Gauge / Meter | SVG arc or bar with threshold | Local Report |
| **BA** | Bar Chart | custom SVG or Recharts (if added) | Local Report / Atlas |
| **TL** | Timeline | chronological event list | Local Report |

### Full Mapping

| # | Connector | Data Shape | Primary Viz | Secondary Viz | Surface |
|---|-----------|-----------|-------------|---------------|---------|
| | **— Climate Trends (global time series) —** | | | | |
| 1 | `noaa_gml.py` (CO₂) | monthly scalar + history | **SK** | — | Trends, Born-in |
| 2 | `noaa_ctag.py` (Temp Anomaly) | monthly scalar + history | **SK** | — | Trends, Born-in |
| 3 | `nsidc.py` (Sea Ice) | daily scalar + history | **SK** | — | Trends, Born-in |
| 4 | `noaa_gml_ch4.py` (CH₄) | monthly scalar + history | **SK** | — | Trends |
| 5 | `noaa_sea_level.py` (GMSL) | ~10-day scalar + history | **SK** | — | Trends |
| 6 | `usdm.py` (Drought %) | weekly D0–D4 % areas | **SK** | PG (state choropleth) | Trends (new), Globe (future) |
| | **— Globe: Continuous Fields —** | | | | |
| 7 | `gibs.py` (PM2.5 MERRA-2) | global raster tile | **GT** | — | Globe |
| 8 | `gibs.py` (AOD MODIS) | global raster tile | **GT** | — | Globe |
| 9 | `gibs.py` (CO₂ OCO-2) | global raster tile | **GT** | — | Globe |
| 10 | `gibs.py` (Flood Detection) | global raster tile | **GT** | — | Globe |
| 11 | `gibs.py` (CH₄ TROPOMI) | global raster tile (P1) | **GT** | — | Globe |
| 12 | `oisst.py` (SST) | lat/lon/sst grid ~1700 pts | **HX** | — | Globe |
| 13 | `coral_reef_watch.py` (DHW) | lat/lon/dhw grid | **HX** | — | Globe |
| 14 | `cmems.py` (SLA) | lat/lon/sla grid (pending) | **HX** | — | Globe |
| 15 | `jrc_drought.py` (EDO) | WMS tiles (Europe only) | **GT** | — | Globe (P1) |
| 16 | `global_forest_watch.py` (Tree Loss) | annual aggregate (CONUS) | — | TBL | Atlas only (no globe viz) |
| | **— Globe: Event Overlays —** | | | | |
| 17 | `firms.py` (Fires) | lat/lon/frp points ~1500 | **PS** | — | Globe |
| 18 | `ibtracs.py` (Storms) | lat/lon/wind track points | **PS** | — | Globe |
| 19 | `earthquake.py` (Earthquakes) | lat/lon/mag/depth points | **PS** | — | Globe (new) |
| 20 | `openaq.py` (Air Monitors) | lat/lon/pm25 points ~1000 | **PS** | — | Globe |
| 21 | `nws_alerts.py` (Weather Alerts) | GeoJSON polygons + severity | **PG** | TL | Globe (new), LR |
| | **— Local Report: Facility / Site Data —** | | | | |
| 22 | `airnow.py` (Current AQI) | AQI + pollutant readings | **GA** | TBL | LR Block 1 |
| 23 | `climate_normals.py` (Baselines) | 12-month normals per station | **TBL** | — | LR Block 2 |
| 24 | `echo.py` (ECHO Compliance) | violation count + facility list | **SC** | TBL | LR Block 3 |
| 25 | `tri.py` (Toxic Releases) | facility list + chemicals | **SC** | TBL, MK | LR Block 7 |
| 26 | `superfund.py` (NPL Sites) | site list + NPL status | **TBL** | MK | LR Block 8a |
| 27 | `brownfields.py` (ACRES) | site list + city | **TBL** | MK | LR Block 8b |
| 28 | `ghgrp.py` (Facility GHG) | facility list + tCO₂e | **SC** | TBL, MK | LR Block 9 |
| 29 | `sdwis.py` (Drinking Water) | system count + violations | **SC** | TBL | LR Block 10 |
| 30 | `pfas.py` (PFAS Monitoring) | per-sample contaminant data | **SC** | TBL, MK | LR Block 10 (sub) or new |
| 31 | `rcra.py` (Hazardous Waste) | handler list + waste tons | **SC** | TBL | LR (future block) |
| 32 | `coops.py` (Tides) | station water level + temp | **SC** | TBL, MK | LR (conditional coastal) |
| | **— Local Report: Hazards / History —** | | | | |
| 33 | `openfema.py` (Disasters) | declaration list + incident type | **TL** | TBL | LR (new block) |
| | **— Stubs / Pending —** | | | | |
| 34 | `usgs.py` (Streamflow NRT) | site list + discharge values | **SC** | TBL | LR Block 4a |
| 35 | `wqp.py` (Water Quality) | discrete sample list | **SC** | TBL | LR Block 4b |
| 36 | `climate_trace.py` (Country GHG) | country-level annual emissions | **BA** | TBL | Atlas only |
| 37 | `airdata.py` (stub) | — | — | — | P1 |
| 38 | `cams.py` (stub) | — | — | — | P1 |

> **Note:** `gibs.py` is a single file serving 5+ GIBS tile layers (rows 7–11).
> Row numbers 34+ exceed file count because GIBS is one file for many layers.

### Visualization Type Summary

| Type | Count | Data Sources |
|------|-------|-------------|
| Sparkline Card (SK) | 6 | CO₂, Temp, Sea Ice, CH₄, Sea Level, **Drought (new)** |
| GIBS Tile (GT) | 5–6 | PM2.5, AOD, OCO-2, Flood, CH₄ (P1), JRC (P1) |
| Point Scatter (PS) | 4 | Fires, Storms, **Earthquakes (new)**, Air Monitors |
| HexBin (HX) | 3 | SST, Coral, SLA |
| Polygon (PG) | 1 | **NWS Alerts (new)** |
| Stat Cards (SC) | 11 | AirNow, ECHO, TRI, GHGRP, SDWIS, PFAS, RCRA, CO-OPS, USGS, WQP + 1 |
| Data Table (TBL) | 14 | Nearly every LR block has a detail table |
| Gauge (GA) | 1 | AirNow AQI (could expand to drought %) |
| Timeline (TL) | 1 | OpenFEMA disasters |
| Map Markers (MK) | 6 | TRI, Superfund, Brownfields, GHGRP, PFAS, CO-OPS (future Leaflet) |
| Bar Chart (BA) | 1 | Climate TRACE country comparison |

---

## Part 2: Globe Layer Restructuring

### Current State: 13 layers in 5 categories

```
Atmosphere (3):  PM2.5, AOD, Air Monitors
Fire & Land (3): Fires, Deforestation (P1), Drought (P1)
Ocean (3):       SST, Coral, SLA
GHG (2):         CO₂ OCO-2, CH₄ (P1)
Hazards (2):     Storms, Floods
```

### Proposed: 16 layers in 6 categories

```
Atmosphere (3):      PM2.5, AOD, Air Monitors          — unchanged
Fire & Land (3):     Fires, Deforestation (P1), Drought (P1)  — unchanged
Ocean (3):           SST, Coral, SLA                    — unchanged
GHG (2):             CO₂ OCO-2, CH₄ (P1)               — unchanged
Hazards (5):         Storms, Floods, Earthquakes (NEW), Weather Alerts (NEW), PFAS Sites (NEW)
                     ↑ expanded from 2 → 5
```

**Why not a 6th category?** Earthquakes and Weather Alerts are natural fits
for Hazards. PFAS Sites could go in a "Contamination" category but the
density is too low at globe scale — it works better as a filterable event
layer inside Hazards. Keeping 5 categories avoids accordion clutter.

### New Layer Specs

| Layer key | Label | Type | Rendering | Color | Data Source |
|-----------|-------|------|-----------|-------|-------------|
| `earthquakes` | Earthquakes (M4+) | event | **PS** pointsData | magnitude-scaled: M4 yellow → M6 orange → M7+ red | `/api/hazards/earthquakes` |
| `nws-alerts` | Weather Alerts | event | **PG** polygonsData | severity: Minor=blue, Moderate=yellow, Severe=orange, Extreme=red | `/api/hazards/alerts` |
| `pfas-sites` | PFAS Monitoring | event | **PS** pointsData (labeled) | uniform purple #7c3aed | `/api/sites/pfas` (bbox=global or CONUS) |

### Composition Rule Update

Current rule: **1 continuous + 1 event** at most.

New rule stays the same. The three new layers are all **event** type, so
they are mutually exclusive with Fires, Storms, and Air Monitors. This
is correct — showing Earthquakes + Fires simultaneously would be too
cluttered.

### Implementation Notes

- **Earthquakes**: Drop-in to existing `pointsData` pipeline. Use
  `magnitude` for point altitude/radius (same log-scale as FIRMS FRP).
  Color ramp: M4 `#eab308` → M5 `#f97316` → M6 `#ef4444` → M7+ `#991b1b`.

- **NWS Alerts**: Requires **new rendering path** — `polygonsData` on
  react-globe.gl. The library supports `polygonsData` prop with
  `polygonCapColor` / `polygonSideColor`. Each alert polygon gets colored
  by severity. This is the only layer that needs a new rendering type.
  **Moderate effort.**

- **PFAS Sites**: Low density (~5–20 sites per metro bbox, ~few hundred
  nationally). Use `labelsData` path (like Air Monitors) with purple dots.
  May be better as Atlas/LR-only if global density is too low to be
  meaningful at globe zoom.

### Globe Layer Count Trajectory

| Phase | Layers | Change |
|-------|--------|--------|
| Phase B (current) | 13 (3 disabled) | — |
| Phase G (proposed) | 16 (3 disabled + 3 new) | +3 new event layers |
| Phase G active | 13 | Same active count (P1 layers still disabled) |

---

## Part 3: Local Report Block Restructuring

### Current: 10 blocks

```
Block 0:  Metro Header (key signals)
Block 1:  Air Quality (AirNow)
Block 2:  Climate Locally (Climate Normals)
Block 3:  Facilities (ECHO)
Block 7:  Toxic Releases (TRI)
Block 8:  Site Cleanup (Superfund + Brownfields)
Block 9:  Facility GHG (GHGRP)
Block 10: Drinking Water (SDWIS)
Block 4:  Water Snapshot (USGS + WQP)
Block 5:  Methodology
Block 6:  Related (pending)
```

### Proposed: 13 blocks (+ 1 conditional)

New blocks to add:

| # | Block Name | Data Source(s) | Viz Pattern | Condition |
|---|-----------|---------------|-------------|-----------|
| 11 | **PFAS Monitoring** | `pfas.py` | SC (unique contaminants, sample count) + TBL (top detections) | Always (high public interest) |
| 12 | **Hazards & Disasters** | `openfema.py` + `earthquake.py` | TL (disaster timeline) + SC (total count, most recent) | Always |
| 13 | **Active Alerts** | `nws_alerts.py` | Alert cards: severity badge + event + area + expires | Always |
| 14 | **Coastal Conditions** | `coops.py` | SC (nearest station water level + temp) + TBL (stations) | **Conditional: coastal metros only** |

### Block Ordering (proposed JSX)

```
Block 0:  Metro Header + Key Signals
Block 1:  Air Quality (AirNow)
          [ad-1]
Block 2:  Climate Locally (Normals)
Block 13: Active Alerts (NWS)          ← NEW — high urgency, near top
Block 3:  Facilities (ECHO)
          [ad-2]
Block 7:  Toxic Releases (TRI)
Block 11: PFAS Monitoring              ← NEW — pairs with TRI/water
          [ad-3]
Block 8:  Site Cleanup (Superfund + Brownfields)
Block 9:  Facility GHG (GHGRP)
          [ad-4]
Block 10: Drinking Water (SDWIS)
Block 4:  Water Snapshot (USGS + WQP)
Block 14: Coastal Conditions (CO-OPS)  ← NEW — conditional
          [ad-5]
Block 12: Hazards & Disasters (OpenFEMA + Earthquake)  ← NEW — historical
Block 5:  Methodology
Block 6:  Related (pending)
```

### Conditional Block Logic (Block 14: Coastal)

Not all 50 metros are coastal. Criteria: CBSA bounding box intersects
coastline. Approximate list of coastal metros (18 of 50):

```
Houston, Los Angeles, New York, San Diego, San Francisco, Miami,
Tampa, Seattle, Boston, Philadelphia, San Jose, Virginia Beach,
Jacksonville, New Orleans, Honolulu, Portland (OR), Baltimore,
Providence
```

Implementation: Add a `coastal: true` flag to `cbsa_mapping.json` entries.
Block 14 renders only if `coastal && coops_status === "ok"`.

### PFAS Block Design (Block 11)

```
┌─ MetaLine: quarterly · observed · EPA PFAS Analytic Tools ─┐
│                                                             │
│  PFAS Monitoring in Houston-The Woodlands-Sugar Land        │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 12       │ │ 5        │ │ PFBA     │ │ 47       │      │
│  │ Monitored│ │ Unique   │ │ Most     │ │ Total    │      │
│  │ Systems  │ │ Contam.  │ │ Frequent │ │ Samples  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  System        | Contaminant | Result  | Unit   | Date     │
│  ─────────────────────────────────────────────────────────  │
│  City of Lake  | PFBA        | 12.3    | ng/L   | 2024-Q3  │
│  Jackson       |             |         |        |          │
│  ...                                                        │
│                                                             │
│  ⚠️ PFAS results are screening-level monitoring data.       │
│  Detection does not imply a health risk at reported levels. │
└─────────────────────────────────────────────────────────────┘
```

### Active Alerts Block Design (Block 13)

```
┌─ MetaLine: near-real-time · observed · NOAA NWS ───────────┐
│                                                              │
│  Active Weather Alerts                                       │
│                                                              │
│  🔴 Severe Thunderstorm Warning                              │
│     Harris County, Galveston County                          │
│     Expires: 2026-04-12 18:00 UTC                           │
│                                                              │
│  🟡 Heat Advisory                                            │
│     Houston Metro Area                                       │
│     Expires: 2026-04-13 01:00 UTC                           │
│                                                              │
│  ─── or ───                                                  │
│  ✅ No active weather alerts for this area.                  │
└──────────────────────────────────────────────────────────────┘
```

### Hazards & Disasters Block Design (Block 12)

```
┌─ MetaLine: continuous · observed · FEMA / USGS ─────────────┐
│                                                              │
│  Hazards & Disaster History                                  │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ 23       │ │ Hurricane│ │ M3.2     │                    │
│  │ Federal  │ │ Most     │ │ Largest  │                    │
│  │ Disasters│ │ Common   │ │ Quake    │                    │
│  │ (5 yrs)  │ │ Type     │ │ (30 days)│                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
│                                                              │
│  Recent Disaster Declarations                                │
│  Date       | Type       | Title              | Area        │
│  ──────────────────────────────────────────────────────────  │
│  2026-03-15 | Fire       | CORNER POCKET FIRE | TX          │
│  2024-07-08 | Hurricane  | HURRICANE BERYL    | Harris Co   │
│  ...                                                         │
└──────────────────────────────────────────────────────────────┘
```

### Bundle Size Impact

Current main chunk: **598.13 KB** gzipped (2 KB headroom to 600 KB).

LocalReport is already lazy-loaded. Adding 4 blocks to the lazy chunk:
- Each block: ~2–3 KB source → ~0.5–1 KB gzipped
- 4 blocks: ~2–4 KB added to the lazy chunk (not the main chunk)
- **Main chunk stays at ~598 KB.** Lazy chunk grows from 5.09 → ~9 KB.

No code-splitting concern.

---

## Part 4: Trends Card Expansion

### Current: 5 cards

| Card | Source | Spark Color |
|------|--------|------------|
| CO₂ | NOAA GML Mauna Loa | `#0f766e` (teal) |
| Global Temp Anomaly | NOAAGlobalTemp CDR | `#b91c1c` (red) |
| Arctic Sea Ice | NSIDC G02135 | `#1d4ed8` (blue) |
| CH₄ | NOAA GML global | `#d97706` (amber) |
| Sea Level Rise | NOAA NESDIS GMSL | `#2563eb` (royal blue) |

### Proposed: 6 cards (+1)

| Card | Source | Spark Color | Value | Rationale |
|------|--------|------------|-------|-----------|
| **% CONUS in Drought** | US Drought Monitor | `#92400e` (brown) | `D1+D2+D3+D4` area % | Weekly signal, high relevance, data already live |

### Why Only +1

- **Data availability**: Only USDM has a clean scalar time series ready today.
- **UX**: 6 cards still fit in a scroll-snap strip. 7+ needs a second row
  or pagination, which breaks the "at a glance" pattern.
- **Future candidates** (need new connectors first):
  - US Renewable Energy Share (EIA — P1 connector)
  - Global Fire Area (FIRMS aggregate — derivable but not yet)
  - US Water Quality Trend (WQP aggregate — derivable but slow)

### Implementation

Backend: Add `drought` indicator to `GET /api/trends` response.
The USDM connector already has the weekly data. Aggregate:
`drought_pct = 100 - none_pct` (i.e., any drought D0+).
Or use `d1_pct + d2_pct + d3_pct + d4_pct` for "moderate drought or worse".

Frontend: Add entry to `STATIC_META` in `TrendsStrip.tsx` with
sparkColor `#92400e`. The sparkline renders the weekly drought %
over the trailing 52 weeks.

---

## Part 5: Implementation Priority — Difficulty × Impact Matrix

### Scoring

**Difficulty**: 1 (trivial, <30 min) → 5 (hard, multi-day)
**Impact**: 1 (niche) → 5 (high visibility, SEO, revenue)
**Priority** = Impact / Difficulty (higher = do first)

### Matrix

| Task | Difficulty | Impact | Priority | Sprint Slot |
|------|-----------|--------|----------|-------------|
| **Trends: +USDM drought card** | 1 | 4 | **4.0** | G.1 |
| **Globe: +Earthquake layer** | 1 | 3 | **3.0** | G.1 |
| **LR: +Active Alerts block (NWS)** | 2 | 4 | **2.0** | G.1 |
| **LR: +PFAS block** | 2 | 4 | **2.0** | G.1 |
| **LR: +Hazards block (OpenFEMA+EQ)** | 2 | 3 | **1.5** | G.2 |
| **LR: +Coastal block (CO-OPS)** | 3 | 2 | **0.7** | G.2 |
| **Globe: +NWS Alerts polygons** | 4 | 3 | **0.75** | G.2 |
| **Globe: +PFAS sites layer** | 2 | 1 | **0.5** | G.3 (optional) |
| **Atlas: data explorer tables** | 3 | 2 | **0.7** | G.3 |
| **LR: Leaflet maps for sites** | 4 | 3 | **0.75** | G.3 |

### Recommended Phase G Sprint Plan

#### G.1 — Quick Wins (1 sprint, ~4 high-priority items)

1. **Trends: USDM Drought card** — Backend: add `drought` to `/api/trends`.
   Frontend: add to `STATIC_META`, sparkline renders weekly %. Trivial.

2. **Globe: Earthquake layer** — Add `earthquakes` to CATEGORIES array
   in Globe.tsx. Fetch from `/api/hazards/earthquakes`. Render as
   pointsData with magnitude-scaled radius/color. Drop-in pattern.

3. **LR: Active Alerts block (Block 13)** — Backend: add NWS alerts to
   `get_report()` with metro bbox filtering. Frontend: alert cards with
   severity badge, event name, area, expiry. Handle "no active alerts"
   state gracefully.

4. **LR: PFAS Monitoring block (Block 11)** — Backend: add PFAS to
   `get_report()` with metro bbox. Frontend: 4 stat cards (systems,
   contaminants, most frequent, samples) + detection table. Disclaimer
   about screening-level data.

**Estimated scope**: 4 items × 1–2 hours each = half-day sprint.

#### G.2 — Moderate Additions (next sprint)

5. **LR: Hazards & Disasters block (Block 12)** — Combine OpenFEMA
   disaster timeline + earthquake history for the metro area. 3 stat cards
   + timeline table.

6. **LR: Coastal Conditions block (Block 14)** — CO-OPS water level +
   temp for nearest stations. Conditional rendering (coastal metros only).
   Requires `coastal` flag in `cbsa_mapping.json`.

7. **Globe: NWS Alerts polygon layer** — New rendering path using
   `polygonsData`. Severity-colored polygons. Needs geometry from NWS API
   (some alerts have null geometry — skip those).

#### G.3 — Polish (following sprint, optional)

8. **Globe: PFAS sites layer** — Low-density point overlay. May decide to
   skip if density is too low at globe scale.

9. **Atlas data explorer** — Interactive tables for each live dataset.
   Filter/sort/search. Progressive enhancement.

10. **LR: Leaflet facility maps** — Embed Leaflet map in Site Cleanup,
    TRI, GHGRP, PFAS blocks showing facility/site markers. Significant
    bundle addition (~40 KB gzipped for Leaflet) — needs code-splitting.

---

## Appendix: Data Sources Not Yet Visualized

These connectors produce data that is currently API-only (no UI surface):

| Connector | Current Surface | Proposed Surface |
|-----------|----------------|-----------------|
| `rcra.py` | API only | LR block (future, pairs with TRI) |
| `climate_trace.py` | API only | Atlas bar chart (country comparison) |
| `global_forest_watch.py` | API only | Atlas table + possible Trends card |
| `jrc_drought.py` | Globe (P1 disabled) | Activate when USDM proves concept |

## Appendix: RCRA Block Decision

RCRA (hazardous waste generators) was intentionally omitted from the
proposed block list because:
1. It shares significant overlap with TRI (both are facility-level waste reporting)
2. It has no coordinates (lat/lon always None) — no map overlay possible
3. Biennial data means the "current" value is always 1–2 years stale

**Recommendation**: Merge RCRA summary stats into the existing TRI block
(Block 7) as a sub-section ("Hazardous Waste Generators") rather than a
separate block. This avoids block inflation while surfacing the data.
