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

## Next
- Register for FIRMS MAP_KEY + OPENAQ_API_KEY (both free) so the
  Fires and Air Monitors layers actually carry data. Ocean Heat
  works right now without any key.
- Preset bank (5-10 templates for Story Panel): wildfire, hurricane,
  heatwave, flood, sea ice minimum — replace the hardcoded preset
  in `/api/earth-now/story`.
- Register for AirNow, Copernicus ADS, EPA AQS (3 more keys) for
  Local Reports.
- Born-in Interactive (P1) — uses all three trend connectors.
