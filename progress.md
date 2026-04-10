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

## Next
- Begin Earth Now globe skeleton (Cesium or Globe.gl + GIBS base imagery)
- NASA FIRMS connector for globe Fires layer (free MAP_KEY)
- OISST ERDDAP WMS integration for globe Ocean Heat layer
- Register for 5 API keys (AirNow, OpenAQ v3, Copernicus ADS, EPA AQS, NASA FIRMS)
- Born-in Interactive (P1) — uses all three trend connectors, so unblocked
