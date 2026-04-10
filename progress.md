# EarthPulse / TerraSight — Progress Log

## 2026-04-10

### Phase 0 — Scaffold
- Initialized project structure (frontend + backend scaffolding)
- Created git repository (commit `a95ea56`)
- React + Vite + TypeScript frontend skeleton (15 components, 5 pages, hooks/utils/types)
- FastAPI backend skeleton with 14 connector stubs + 5 API routers

### Phase 1-2 — API Spike (COMPLETE)
Verified accessibility of all 14 P0 data sources via 4 parallel Explore agents.
Full report in `docs/api-spike-results.md`.

**Final score: 9 ✅ GO / 5 ⚠️ / 0 ❌** (OISST blocker resolved — see below)

| Source | Status | Notes |
|---|---|---|
| NOAA GML (CO2) | ✅ | Direct file download, no auth |
| NOAA CtaG | ⚠️ | No public REST API — pivot to NOAAGlobalTemp CDR NetCDF |
| NSIDC Sea Ice | ✅ | CSV at noaadata.apps.nsidc.org |
| NOAA OISST | ✅ | **Resolved** — NOAA CoastWatch ERDDAP griddap (NRT + final) |
| U.S. Climate Normals | ✅ | Station CSVs at ncei.noaa.gov/data/normals-monthly/1991-2020 |
| AirNow | ✅ | Free key, 500 req/hr per endpoint |
| OpenAQ v3 | ✅ | Free key (v1/v2 retired 2025-01-31), 2000 req/hr |
| CAMS (ADS) | ⚠️ | Registration + cdsapi Python client; investigate WMS tile alt |
| USGS modernized | ✅ | OGC API Features at api.waterdata.usgs.gov/ogcapi/v0 |
| WQP | ⚠️ | **Must use `/wqx3/` beta** (legacy `/data/` broken for USGS post-2024-03-11) |
| EPA ECHO | ✅ | HTTP only (HTTPS 404) — use `http://ofmpub.epa.gov/echo/` |
| EPA AQS | ⚠️ | Email + key, 10 req/min enforced |
| NASA FIRMS | ✅ | Free MAP_KEY, 5000 trans/10min |
| NASA GIBS | ✅ | Public WMTS, no auth, default base = `BlueMarble_ShadedRelief_Bathymetry` |

### Integration actions identified
1. ✅ **OISST blocker RESOLVED** — pivoted to NOAA CoastWatch ERDDAP
   (`ncdcOisst21NrtAgg`, verified curl returned real SST for 2026-04-08).
   PODAAC GHRSST kept as fallback.
2. ⚠️ **CtaG pivot** — use NOAAGlobalTemp CDR NetCDF for Climate Trends strip
3. ⚠️ **WQP hard-code** `/wqx3/` endpoints in `wqp.py`, add test preventing `/data/` regression
4. ⚠️ **CAMS** — investigate ADS WMS tile path before committing to cdsapi inside FastAPI
5. ✅ **URL corrections applied** to `connectors/{usgs,wqp,echo,gibs}.py`
6. Registration needed: AirNow, OpenAQ v3, Copernicus ADS, EPA AQS, NASA FIRMS (5 free accounts)

### Phase 3 — First Vertical Slice (COMPLETE)
End-to-end data flow proven for the NOAA GML CO₂ Climate Trends card:

- `backend/connectors/noaa_gml.py` — async httpx fetch of
  `co2_mm_mlo.txt`, parser skips `#` comments, returns list of
  `Co2Point(year, month, decimal_date, value_ppm)` wrapped in a
  `ConnectorResult`. Spike returned 816 points from 1958-03 to 2026-02.
- `backend/api/trends.py` — `GET /api/trends/co2` returns latest monthly
  mean + 12-month trailing series. Latest verified: **429.35 ppm (2026-02)**.
- `frontend/src/components/climate-trends/TrendsStrip.tsx` — CO₂ card wired
  via `useApi<Co2Response>('/trends/co2')`:
  - MetaLine renders "Monthly · 🟢observed · NOAA GML Mauna Loa" ABOVE the value
  - Big number + `ppm` unit + "as of YYYY-MM"
  - Inline SVG 12-month sparkline (no chart library — keeps bundle lean)

### Phase 4 — Climate Trends Strip COMPLETE (3/3 cards live)

- `backend/connectors/nsidc.py` — fetches NSIDC G02135 v4.0 daily Arctic
  CSV (`N_seaice_extent_daily_v4.0.csv`), parses via `csv` module (the
  Source Data column is comma-laden). Helpers:
  - `five_day_mean()` — trailing 5-day running mean for headline value
  - `monthly_means()` — daily → calendar-month aggregation for sparkline
  - Verified: 15,682 points 1978-10-26 → 2026-04-09; latest 5-day mean
    **13.98 M km²**.
- `backend/connectors/noaa_ctag.py` — pivoted away from CtaG (no public
  REST API) to **NOAAGlobalTemp CDR v6.1** ASCII time series. Discovers
  latest `aravg.mon.land_ocean.90S.90N.v6.1.0.YYYYMM.asc` via directory
  index scrape, parses year/month/anomaly columns. Anomalies are °C vs
  1991-2020 baseline. Verified: 2,114 points 1850-01 → 2026-02; latest
  **+0.53 °C (2026-02)**.
- `backend/api/trends.py` — refactored:
  - New fan-out endpoint `GET /api/trends` runs all three connectors in
    parallel via `asyncio.gather(..., return_exceptions=True)`; a failure
    in one indicator degrades gracefully without blocking the others.
  - Individual `/co2`, `/temperature`, `/sea-ice` endpoints retained for
    deep-link and debugging use.
  - Payload includes `baseline: "1991-2020"` for temperature, `window:
    "5-day mean"` for sea ice latest.
- `frontend/.../TrendsStrip.tsx` — rewritten around a single
  `useApi<TrendsResponse>('/trends')` call. Deterministic CO₂ → Temp →
  Sea Ice card ordering independent of backend ordering. Temperature
  shows signed values (`+0.53`). Each card gets its own sparkline color
  (teal / red / blue). Static per-card metadata table lets the MetaLine
  paint trust signals during the initial loading state.

### Phase 5 — Earth Now Globe MVP (COMPLETE)

Visible globe + one live event overlay on the home page.

**Library decision: `react-globe.gl`** (chosen over Cesium)
- Single package install (51 deps), no static-asset copying. Cesium would
  require `vite-plugin-cesium` + Workers/Assets/ThirdParty mirrored into
  `public/` — painful on Windows Git Bash.
- Declarative `pointsData` overlay — Cesium would need Entity plumbing.
- Bundle: full frontend builds to 2 MB / **576 KB gzipped** including
  three.js + globe.gl. Cesium's minimum is ~3-5 MB.
- Accepted tradeoff: no WMTS tile streaming. Fine for a static BlueMarble
  base; revisit if we later need daily-updating tiled layers (MODIS true
  color etc.).

**Backend:**
- `backend/connectors/firms.py` — httpx fetch of the NASA FIRMS Area API
  `api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAYS}`. Parses the VIIRS CSV
  into `FireHotspot(lat, lon, brightness, frp, confidence, acq_date,
  acq_time, daynight)`. Helper `top_by_frp(limit=1500)` caps the feed
  because the full global 24h VIIRS stream is 30k+ points (too dense
  at globe scale and too heavy for the browser).
- `backend/api/earth_now.py` — `GET /api/earth-now/fires` endpoint.
  Reads `FIRMS_MAP_KEY` from `get_settings()`. **If the key is missing,
  the endpoint returns `configured: false` with instructions** rather
  than a 5xx — the globe still renders with an empty overlay and a
  status line telling the user to register.
- `backend/config.py` — already had `firms_map_key: str | None`.
  Pydantic-settings reads it from the `FIRMS_MAP_KEY` env var.
- `.env.example` added at project root with placeholder values for
  `FIRMS_MAP_KEY`, `AIRNOW_API_KEY`, `OPENAQ_API_KEY`.

**Frontend:**
- `frontend/src/components/earth-now/Globe.tsx` — full rewrite:
  - Base texture: NASA GIBS WMS GetMap single equirectangular JPEG
    (2048×1024 BlueMarble_ShadedRelief_Bathymetry). Verified 2026-04-10:
    returns `image/jpeg` with `Access-Control-Allow-Origin: *`.
  - `ResizeObserver` drives responsive width/height matching parent.
  - Auto-rotate enabled via `controls().autoRotate = true`
    (speed 0.35) with initial camera at lat 15, lng 0, altitude 2.3.
  - Fires overlay pulled from `/api/earth-now/fires` via `useApi`,
    rendered as `pointsData` with:
    - `pointRadius` = log-scaled FRP (keeps one huge wildfire from
      dominating the view)
    - `pointAltitude` = log-scaled FRP (slight lift off surface)
    - `pointColor` = `#ff3d00`
    - `pointLabel` = custom HTML tooltip showing FRP, confidence,
      date/time, day/night flag, and coordinates
  - Trust metadata (`MetaLine`) overlaid top-left: "NRT ~3h · 🟢observed ·
    NASA FIRMS / NASA GIBS".
  - Top-right layer toggle button `[🔥 Fires (N)]`. Default ON.
  - Bottom status line shows loading or "FIRMS_MAP_KEY not configured"
    warning when the backend reports the key is missing.
- `frontend/src/vite-env.d.ts` added — standard Vite+TS triple-slash
  reference was missing from the initial scaffold, blocking `npm run
  build` via a pre-existing `import.meta.env` type error in `useApi.ts`.
  Added to unblock builds.
- `frontend/package.json` — added `react-globe.gl@^2.37.1`.
- `frontend/src/pages/Home.tsx` — already wires `<Globe />` in the hero
  section; no changes needed.

**Verified:**
- `npm run build` succeeds, 478 modules, 2 MB total / 576 KB gzipped.
- `python -m` smoke test of `/api/earth-now/fires` without a key
  returns `configured: false` with the registration instructions and
  an empty `fires: []` list — degrades gracefully.

### Phase 6 — Earth Now Complete (SST + Air Monitors + Story Panel)

Three new layers + Story Panel interactivity.

**Backend:**
- `backend/connectors/oisst.py` — real implementation. Uses ERDDAP
  griddap CSV at stride 20 (`sst[(last)][(0.0)][...]:20:...`),
  two-header-row parser, filters `NaN` land cells, converts 0-360
  longitude to -180..180 for the globe. Verified 2026-04-10:
  latest timestep **2026-04-08T12:00Z**, **1,684 ocean points**,
  range **-1.80 °C → +31.13 °C**, mean 14.52 °C. ~2 s response.
- `backend/connectors/openaq.py` — real implementation. Uses OpenAQ
  v3 `/locations?parameters_id=2&limit=1000` (PM2.5). Single call
  returns station name + coords + latest sensor reading inline —
  no second hop to `/measurements` or `/latest`. X-API-Key header.
  Gracefully raises when the key is missing; the API layer catches
  that and returns `configured: false`.
- `backend/api/earth_now.py` — three new endpoints:
  - `GET /api/earth-now/sst` — ~1,700 point payload with min/max/mean
    stats for the client-side color ramp.
  - `GET /api/earth-now/air-monitors` — stations list, `configured:
    false` fallback when the key is missing (mirrors FIRMS pattern).
  - `GET /api/earth-now/story` — hardcoded "2026 Wildfire Season"
    preset with `globe_hint.camera` (lat 40, lng -120, alt 1.6) and
    `report_link: /reports/los-angeles-long-beach-anaheim`. Full
    preset bank (5-10 templates) deferred to a later pass.
- `/api/earth-now/layers` extended with `oisst`, `cams-smoke`
  (marked `disabled: true` with explanatory `disabled_reason`), and
  `openaq`.

**CAMS decision:**
CAMS has no public WMS tile endpoint without a Copernicus ADS
account (verified via parallel research agent: ECMWF open data
decommissioned non-S2S/TIGGE datasets in 2023; Sentinel Hub public
WMS requires per-instance UUIDs; OpenCharts is PNG-only). NASA GIBS
MODIS `MODIS_Combined_Value_Added_AOD` would work as an observed
aerosol proxy but that's a substitution, not CAMS — deferred to a
follow-up. For now the Smoke toggle is rendered **disabled** with a
tooltip: "CAMS forecast — Copernicus ADS account required (P1)".

**Frontend:**
- `frontend/src/components/earth-now/Globe.tsx` — full rewrite as a
  `forwardRef` controlled component. Layer state is lifted to
  `Home.tsx` so the Story Panel can command both the active layer
  and the camera position:
  - Props: `firesOn`, `onToggleFires`, `continuousLayer`,
    `onSetContinuousLayer`.
  - Imperative handle: `flyTo(lat, lng, altitude)` — pauses
    auto-rotate and animates the camera over 1.5 s.
  - Fetches fires + SST + air-monitors on mount (~500 KB total).
  - **Fires** → `pointsData`, red, log-scaled FRP radius / altitude
    (unchanged).
  - **Ocean Heat** → `hexBinPointsData` with `hexBinResolution={3}`,
    `weight = sst_c`, and a 5-stop cold→warm color ramp (deep blue
    -2 °C → teal 5 → pale green 15 → orange 22 → red 30+). Hex
    hover tooltip shows mean °C and cell count.
  - **Air Monitors** → `labelsData` with `labelDotRadius` and EPA
    PM2.5 AQI color bands (green/yellow/orange/red/purple).
    Hover tooltip shows station name, PM2.5, and timestamp.
  - Layer toggles (top-right): Fires is an independent event
    overlay; Ocean Heat / Smoke / Air Monitors are the mutually-
    exclusive continuous-field group (Smoke disabled with tooltip).
  - Active-layer `MetaLine` in the header (top-left) updates to
    show the current continuous layer's source + badge, or falls
    back to FIRMS/GIBS when none is active.
- `frontend/src/components/earth-now/StoryPanel.tsx` — full rewrite.
  Loads `/api/earth-now/story`, renders title + body, and renders
  **Explore on Globe** + **Read Local Report →** buttons. The first
  calls the parent's `onExploreOnGlobe` with the preset's
  `layer_on` id and camera target. Panel also renders a
  **Data Status** legend (🟢 observed / 🟡 NRT / 🟠 forecast /
  🔵 derived / ⚪ estimated) — the trust-tag vocabulary from
  CLAUDE.md, visible to the user on every visit.
- `frontend/src/pages/Home.tsx` — holds `firesOn`, `continuousLayer`,
  and a `globeRef: RefObject<GlobeHandle>`. The `handleExploreOnGlobe`
  handler maps preset layer ids (`firms` / `oisst` / `openaq`) to
  the right state setter and then calls `globeRef.current?.flyTo(...)`.
  Two-column hero: `minmax(0, 2fr) minmax(280px, 1fr)`.

**Verified:**
- Backend smoke test: `/sst` returns 1,684 points + stats,
  `/air-monitors` returns `configured: false` + instructions without
  a key, `/story` returns the 2026 wildfire preset with camera
  hint. All three endpoints wired through `APIRouter`.
- `npm run build` succeeds, 478 modules, ~578 KB gzipped. Clean
  `tsc --noEmit`.

## 2026-04-11 — Phase 7 Local Reports + Token Optimization

**Phase 2 connectors (Local Reports backend):**
- `usgs.py` — modernized OGC API `/collections/daily/items`,
  parameter_code=00060. Houston: 51 streamflow sites. Feature has
  no `site_name` — falls back to `monitoring_location_id`.
- `wqp.py` — WQX 3.0 beta `/wqx3/Result/search`. 3 landmines fixed:
  (a) `dataProfile=basicPhysChem` required (else HTTP 500),
  (b) WQX 3.0 column renames (`Location_Identifier`,
  `Result_Characteristic`, `Result_Measure`, `Result_MeasureUnit`),
  (c) `providers=NWIS,STORET` comma-joined silently matches zero
  rows — must emit as repeated params. Houston: 31,549 samples /
  448 stations / 272 analytes over past year.
- `climate_normals.py` — per-station 1991-2020 CSVs from NCEI.
  Houston `USW00012918` = **Houston Hobby AP** (cbsa_mapping label
  corrected). Annual mean 71.1°F, precip 55.6 in.

**Report API orchestrator** (`backend/api/reports.py`):
- `GET /api/reports/{cbsa_slug}` loads `data/cbsa_mapping.json`,
  fans out 5 connectors in parallel via
  `asyncio.gather(..., return_exceptions=True)`, wraps each as a
  block with `status: ok | error | not_configured | pending`.
  Single-connector failure never 5xxs the whole report.
- Emits Block 0 key-signal mini-cards + methodology source table
  + mandatory CLAUDE.md disclaimers (ECHO compliance, WQP discrete,
  AirNow reporting area).

**Current block statuses (Houston smoke test):**
- ✅ Climate Normals — baseline 71.1°F
- ✅ USGS — 51 streamflow sites
- ✅ WQP — 31,549 discrete samples
- ❌ ECHO — ConnectTimeout (HTTP-only `ofmpub.epa.gov` blocked from
  current dev network; graceful-degraded as error block). **Needs
  re-investigation** — possibly corporate firewall, possibly
  endpoint change, possibly proxy required.
- ⚪ AirNow — `not_configured`, AIRNOW_API_KEY unset. **Register at
  https://docs.airnowapi.org/ and add to .env**.

**Frontend** (`frontend/src/components/local-reports/ReportPage.tsx`):
- Full 6-block rewrite: metro header + key signals, Air Quality,
  Climate Locally (12-row normals table), Facilities (top
  violations table + 4 stat cards), Water (USGS NRT + WQP discrete
  sub-blocks), Methodology source table, Related Content stub.
- MetaLine on every healthy block (cadence · trust badge · source
  above the value). Graceful notices for error / not_configured /
  pending. AdSense slots between Blocks 1-2 and 3-4.
- `npm run build` clean, 478 modules, 581 KB gzipped.

**Token optimization:**
- `.claudeignore` added (node_modules, dist, __pycache__, etc.)
- CLAUDE.md diet: **299 → 123 lines**. Extracted content to:
  - `docs/connectors.md` — per-source catalog + endpoint quirks
  - `docs/report-spec.md` — 6-block spec + AdSense rules
  - `docs/guardrails.md` — rules + verification checklist +
    known-landmine table
- New Operating Rules section in CLAUDE.md: no re-reading context
  files, parallel tool calls, sub-agent delegation, write down
  landmines, mandatory graceful degradation.

**Commits:**
- `085ffe7` chore: token optimization (CLAUDE.md diet + docs split)
- `e925798` feat: Local Reports MVP — Houston vertical slice

## 2026-04-11 — ECHO fix + AirNow wiring

### ECHO connector migrated to echodata.epa.gov (`7265819`)

**Root cause of ConnectTimeout:** `ofmpub.epa.gov` is blocked on most
networks. New host: `echodata.epa.gov` (HTTPS works).

**API behavioral changes vs old echo13:**
- Two hops required: `get_facilities` → QueryID → `get_qid` paginated
- `FacLong` absent from QID response (lat-only; map deferred)
- `CurrVioFlag`, `Over3yrsFormalActions`, `Over3yrsEnfAmt` absent
- Violation detection now: `FacSNCFlg == 'Y'` OR `FacComplianceStatus`
  contains "violation" (not "no violation")
- `QueryRows` in both hops = global unconstrained count; use
  `CAARows`/`CWARows` from first hop for program-level geo estimate
- `responseset=100` + up to 5 pages → 500 facility sample per call

**Houston smoke test:** 500 facilities sampled · 2 in violation ·
1,329 CAA-regulated · 26,272 CWA-regulated (index counts)

**AirNow status:** connector already fully implemented
(`connectors/airnow.py`). Returns `not_configured` until
`AIRNOW_API_KEY` is set in `.env`. Block 1 will light up automatically
once the key is added — no code change needed.

**Full Houston report blocks after fix:**
- ✅ air_quality — not_configured (key absent, graceful)
- ✅ climate_locally — ok (normals 71.1°F baseline)
- ✅ facilities — ok (500 sampled, 2 in violation)
- ✅ water — ok (USGS 50 NRT sites + WQP discrete)
- ✅ methodology — ok
- ⚪ related — pending (P1)

**New landmines added to guardrails.md:**
- `ofmpub.epa.gov` → blocked; use `echodata.epa.gov`
- `echo13_rest_services` → gone; use `echo_rest_services`
- Two-hop required; `FacLong` absent; `CurrVioFlag` absent

## 2026-04-11 — AirNow activated

- `AIRNOW_API_KEY` set in `.env` → Block 1 Air Quality now **ok**
- Houston live reading: **AQI 63 · Moderate · PM2.5**
  Reporting area: Houston-Galveston-Brazoria, TX
- All 5 data blocks now ok (related = P1 pending as expected)

## 2026-04-11 — LA metro + Home Local Reports section (`f430f89`)

**Second metro added: Los Angeles-Long Beach-Anaheim (CBSA 31080)**
- bbox, AirNow ZIP 90001, NOAA USW00023174 (LAX)
- LA smoke test: all 5 blocks ok · AQI 44 Good · 500 sampled · 8 in violation · 56 NRT sites

**ECHO p_act=Y fix:**
- LA bbox without p_act → 363k rows → ECHO queryset-limit error
- p_act=Y (active facilities only) → QueryID obtained for any metro
- Now applied to all ECHO queries; Houston unaffected (22k vs 71k rows, CAARows consistent)
- Landmine added to guardrails.md

**New backend endpoints:**
- `GET /api/reports/` — metro list (slug, name, state, pop, climate_zone)
- `GET /api/reports/search?q=` — ZIP prefix + metro name substring match
  - 77002 → Houston, 90001 → LA, "Houston" → Houston, "99999" → null+message

**Home page:**
- LocalReportsSection with metro cards (fetched from `/api/reports/`) + ZIP/city search → navigate
- Story Panel "Read Local Report →" already pointed to LA (no change needed)

**ReportPage 404:**
- Detects HTTP 404 → "Metro not found" message + "Back to home" link

## 2026-04-11 — Atlas + Navigation + BornIn placeholder (`02de1c2`)

**Atlas static catalog (`frontend/src/data/atlas_catalog.json`):**
- 8 categories × 2–5 datasets each
- Fields: id, name, source, url, update_frequency, trust_tag, description,
  spatial_coverage, license, status (`live` | `planned`)
- 14 P0 sources marked `live`; remainder `planned`

**New pages:**
- `frontend/src/pages/Atlas.tsx` — `/atlas` main page, 8 category cards with
  icon, title, dataset count, live count, 2 sample trust badge pills
- `frontend/src/pages/AtlasCategory.tsx` — `/atlas/:categorySlug` dataset
  listing; MetaLine above each dataset; Live/Planned pill; external source link;
  404 handling for unknown slugs

**Updated components:**
- `AtlasGrid.tsx` — now imports from `atlas_catalog.json`; shows emoji icon,
  dataset count, "N live" badge, "View all →" link to `/atlas`
- `Header.tsx` — full rewrite: sticky (z-index 100), scrollTo() helper for
  Earth Now / Climate Trends / Local Reports anchors, Atlas → `/atlas` Link,
  mobile hamburger toggle
- `BornIn.tsx` — styled placeholder (blue gradient), disabled input + button,
  "Coming soon (P1)" label, data record start dates
- `App.tsx` — added `import Atlas` + `<Route path="/atlas" …>` before
  `:categorySlug`

**Build verified:** 480 modules · 587.70 KB gzipped · 0 TS errors ✅

## 2026-04-11 — 10-metro expansion + Rankings + AQI Guide (`0342dd9`)

**Metro expansion to 10 (data/cbsa_mapping.json):**
| CBSA | Name | Pop | Climate | NOAA Station | Normals verified |
|------|------|-----|---------|--------------|-----------------|
| 35620 | New York-Newark-Jersey City | 19.8M | Cfa | USW00094728 (JFK) | 55.8°F / 49.5in |
| 16980 | Chicago-Naperville-Elgin | 9.5M | Dfa | USW00094846 (O'Hare) | 51.3°F / 37.9in |
| 19100 | Dallas-Fort Worth-Arlington | 7.8M | Cfa | USW00003927 (DFW) | 66.6°F / 37.0in |
| 38060 | Phoenix-Mesa-Chandler | 5.1M | BWh | USW00023183 (Sky Harbor) | 75.6°F / 7.2in |
| 37980 | Philadelphia-Camden-Wilmington | 6.2M | Cfa | USW00013739 (PHL) | 56.3°F / 44.1in |
| 41700 | San Antonio-New Braunfels | 2.6M | Cfa | USW00012921 (SAT) | 69.6°F / 32.4in |
| 41740 | San Diego-Chula Vista-Carlsbad | 3.3M | Csb | USW00023188 (SAN) | 64.7°F / 9.8in |
| 41940 | San Jose-Sunnyvale-Santa Clara | 2.0M | Csb | USW00023293 (SJC) | 60.7°F / 13.5in |

ECHO smoke: NY=500 sampled/7 violations, Chicago=500 sampled/5 violations ✅

**Rankings API (backend/api/rankings.py):**
- `GET /api/rankings/epa-violations` — parallel asyncio.gather across all 10 metros
- Returns rows sorted by in_violation desc; per-row status ok/error for graceful degradation
- 60s per-metro timeout via asyncio.wait_for; error rows appended at end

**Ranking page (frontend/src/pages/Ranking.tsx):**
- `/rankings/epa-violations` — loading notice (30-60s expected), table with
  metro name/state, sampled count, in-violation count, violation rate %, report link
- ECHO disclaimer footer + source/retrieved_date attribution

**AQI Guide (frontend/src/pages/Guide.tsx):**
- `/guides/how-to-read-aqi` — static content
- 6 AQI categories with color swatches, descriptions, action recommendations
- Criteria pollutant table (PM2.5, PM10, O₃, NO₂, SO₂, CO)
- Sensitive groups section, data sources, related links

**Home page updates:**
- LocalReportsSection: shows top 4 metro cards + "View all N metros →" link
- Rankings quick-link card (📊 EPA Violations Ranking)
- Guides quick-link card (📖 How to Read an AQI Report)

**Header:** Rankings link updated from /rankings/pm25 → /rankings/epa-violations

**Build:** 480 modules · 591.62 KB gzipped · 0 TS errors ✅

## 2026-04-11 — Production deployment setup (`8d03752`)

**Build check:**
- 0 `console.log` in frontend + backend ✅
- 591.63 KB gzipped — within 600 KB guardrail ✅
- Fixed: `Home.tsx` `handleSearch` used hardcoded `/api` — now uses `VITE_API_BASE ?? '/api'`

**Deployment option comparison (3 options evaluated):**
| Option | Frontend | Backend | Free BW | Cold Start | Notes |
|--------|----------|---------|---------|------------|-------|
| A | Vercel | Render | 100 GB | ~30s | Simple but bandwidth cap |
| B ✅ | CF Pages | Render | Unlimited | ~30s | Best for SEO long-tail |
| C | CF Pages | Fly.io | Unlimited | <5s | Lowest cost always-on |

**Chosen: Option B (CF Pages + Render)**
Reason: CF Pages unlimited bandwidth is critical for SEO-driven local reports;
Render is zero-config Python; free tier works for MVP; $7/mo for always-on.

**Files created:**
- `Dockerfile` — python:3.12-slim, non-root user, `$PORT` env var
- `render.yaml` — Render blueprint (docker runtime, free plan, env var stubs)
- `frontend/public/_headers` — CF Pages security headers + asset caching rules
- `frontend/public/_redirects` — SPA fallback (`/* → /index.html 200`)
- `docs/deploy.md` — option table, step-by-step setup, env var reference

**`.env.example` updated** — all 5 API services documented:
1. FIRMS_MAP_KEY (P0)
2. AIRNOW_API_KEY (P0)
3. OPENAQ_API_KEY (P0)
4. EPA_AQS_EMAIL + EPA_AQS_KEY (P1)
5. CAMS_ADS_KEY (P1)

**`backend/config.py` updated:**
- `debug=False` default (was `True`)
- `CORS_ORIGINS` env-configurable
- Added `epa_aqs_email`, `epa_aqs_key`, `cams_ads_key` fields

## Next
- CtaG city monthly time series (Block 2, P1 pending).
- Preset bank for Story Panel, Born-in Interactive (both P1).
- ECHO `FacLong` absent → facility map on Block 3 deferred.
- Born-in Interactive full implementation (P1).
- Add PM2.5 annual ranking once EPA AQS key is registered.
