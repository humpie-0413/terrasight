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

## Next
- Register for FIRMS MAP_KEY (free, instant) so fire hotspots actually
  render. Every other piece is already in place.
- OISST ERDDAP WMS integration for globe Ocean Heat layer (continuous
  field counterpart to Fires per CLAUDE.md "1 continuous + 1 event" rule).
- Register for AirNow, OpenAQ v3, Copernicus ADS, EPA AQS (4 more keys).
- Born-in Interactive (P1) — uses all three trend connectors.
