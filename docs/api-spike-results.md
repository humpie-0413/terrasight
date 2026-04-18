# API Spike Results — Phase 1-2 (2026-04-10)

Verified accessibility of all 14 P0 data sources. Each section documents the exact
endpoint, auth requirement, sample call, format, rate limit, cadence, GO/⚠️/❌ status,
and fallback.

## Summary

| # | Source | Status | Auth | Blocker |
|---|---|---|---|---|
| 1 | NOAA GML Mauna Loa (CO2) | ✅ GO | None | — |
| 2 | NOAA Climate at a Glance | ⚠️ | None | No public REST API — UI export / scrape only |
| 3 | NSIDC Sea Ice Index | ✅ GO | None | — |
| 4 | NOAA OISST | ✅ GO (via ERDDAP) | None | THREDDS dead — pivoted to NOAA CoastWatch ERDDAP |
| 5 | U.S. Climate Normals 1991-2020 | ✅ GO | None | — |
| 6 | AirNow | ✅ GO | Free API key | — |
| 7 | OpenAQ v3 | ✅ GO | Free API key | v1/v2 retired 2025-01-31 |
| 8 | CAMS (Copernicus ADS) | ⚠️ | Free CDS token | Registration + cdsapi Python client required |
| 9 | USGS modernized Water Data API | ✅ GO | None | OGC API Features; legacy sunsets 2027 Q1 |
| 10 | Water Quality Portal (WQP) | ⚠️ | None | MUST use `/wqx3/` beta for post-2024-03-11 USGS data |
| 11 | EPA ECHO | ✅ GO | None | HTTP only (HTTPS 404) |
| 12 | EPA AirData / AQS | ⚠️ | Email + key (free) | 10 req/min enforced |
| 13 | NASA FIRMS | ✅ GO | Free MAP_KEY | 5000 trans / 10-min window |
| 14 | NASA GIBS | ✅ GO | None | — |

**Overall: 9 GO, 5 ⚠️ (solvable with registration or workaround), 0 ❌ — OISST blocker resolved via ERDDAP pivot (2026-04-10).**

---

## 1. NOAA GML Mauna Loa CO2

- **Endpoint:** `https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt` (monthly); `https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_daily_mlo.txt` (daily). Also: `co2_weekly_mlo.txt`, `co2_annmean_mlo.txt`, `co2_gr_mlo.txt`.
- **Auth:** None — public direct file download.
- **Sample call:** `curl -s https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt`
- **Response format:** Plain text, whitespace-separated columns (year, month, decimal_date, average, interpolated, trend, days).
- **Rate limit:** None documented.
- **Update frequency:** Daily file refreshed daily (~1-day latency); monthly finalized after QC; most recent year marked preliminary until calibration finalization.
- **Status:** ✅ GO
- **Notes:** Record 1958-present. Contact Xin Lan (xin.lan@noaa.gov). File headers include attribution/use terms. Last file timestamp observed 2026-04-09.
- **Fallback:** Scripps Institution `scrippsco2.ucsd.edu` (original source, pre-1974 reference record).

## 2. NOAA Climate at a Glance (CtaG)

- **Endpoint:** `https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/` (interactive web UI). Underlying dataset hosted on Google Cloud Storage at `https://storage.googleapis.com/noaa-ncei-ipg/datasets/cag/data/` but not publicly indexed. No formal REST/JSON API documented.
- **Auth:** None for web UI.
- **Sample call:** No direct curl. UI export: navigate to global/city time-series page → click Download → CSV. Programmatic alternative: scrape HTML + underlying JSON requests via Playwright/headless browser.
- **Response format:** CSV (UI export); chart data loaded via opaque client-side fetch.
- **Rate limit:** Standard web server (no API gateway).
- **Update frequency:** Monthly (preliminary, subject to revision).
- **Status:** ⚠️ 주의사항 있음 — no public REST API. UI-driven workflow only.
- **Notes:** For both global temperature anomaly (since 1880) AND city-level time series, there is **no documented programmatic API**. Options: (a) headless-browser scraping of `ncei.noaa.gov/access/monitoring/climate-at-a-glance/us-city/{slug}/time-series`, (b) parse the chart JS fetch calls, (c) ingest raw NOAAGlobalTemp CDR NetCDF files directly (`https://www.ncei.noaa.gov/products/climate-data-records/global-temperature`). Recommendation: for Climate Trends strip, use NOAAGlobalTemp CDR NetCDF scheduled ingest; for Local Reports Block 2 city series, accept scrape or schedule manual monthly pull.
- **Fallback:** (1) NOAAGlobalTemp CDR NetCDF (primary programmatic fallback). (2) Berkeley Earth monthly land/ocean anomaly (alternative provenance). (3) HadCRUT5 (UK Met Office) as independent anomaly series.

## 3. NSIDC Sea Ice Index

- **Endpoint:** `https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv` (Arctic); `.../south/.../S_seaice_extent_daily_v4.0.csv` (Antarctic). Monthly aggregates: `N_seaice_extent_monthly_v4.0.csv`.
- **Auth:** None (public HTTPS).
- **Sample call:** `curl -s "https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv" | head -20`
- **Response format:** CSV — Year, Month, Day, Extent (million km²), Missing, Source Data.
- **Rate limit:** None documented (direct file serving).
- **Update frequency:** Daily — verified latest 2026-04-09 at 13.850 M km² Arctic. 5-day running mean must be computed client-side.
- **Status:** ✅ GO
- **Notes:** Dataset G02135 v4.0 (AMSR2 passive microwave). NSIDC support level recently downgraded to "Basic" due to funding; files still update daily as of verification. Record starts 1979-10.
- **Fallback:** Monthly file at same base path (reduced cadence). For independent cross-check, JAXA AMSR2 sea ice product at University of Bremen (`https://seaice.uni-bremen.de/data/amsr2/`).

## 4. NOAA OISST (Optimum Interpolation SST) — **RESOLVED 2026-04-10**

### Resolution summary
Original NCEI THREDDS endpoint dead. Pivoted to **NOAA CoastWatch ERDDAP**, verified
live with real SST data returned for 2026-04-08. No auth, URL-based slicing.
Connector (`backend/connectors/oisst.py`) updated accordingly.

### Primary (ERDDAP, ✅ GO)
- **Endpoint:** `https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg` (NRT, 1-day latency); `.../ncdcOisst21Agg` (final, ~2-week delay). WMS tile endpoint: `https://coastwatch.pfeg.noaa.gov/erddap/wms/ncdcOisst21NrtAgg/request`.
- **Auth:** None.
- **Sample call (verified 2026-04-10, returned 4 SST rows for 2026-04-08):**
  ```bash
  curl "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg.csv?sst%5B(last)%5D%5B(0.0)%5D%5B(0):(0.25)%5D%5B(0):(0.25)%5D"
  ```
  Output:
  ```csv
  time,zlev,latitude,longitude,sst
  UTC,m,degrees_north,degrees_east,degree_C
  2026-04-08T12:00:00Z,0.0,0.125,0.125,30.19
  2026-04-08T12:00:00Z,0.0,0.125,0.375,30.07
  2026-04-08T12:00:00Z,0.0,0.375,0.125,30.16
  2026-04-08T12:00:00Z,0.0,0.375,0.375,30.06
  ```
  Griddap URL syntax: `[start:stride:stop]` per dimension → `sst[time][zlev][lat][lon]`. `(last)` = latest timestep.
- **Response format:** CSV / JSON / NetCDF / PNG (griddap); WMS tiles (separate endpoint).
- **Rate limit:** Not formally published. ERDDAP is a community infrastructure — polite-use expected.
- **Update frequency:** Daily NRT (1-day latency); final version ~14 days after. Verified latest timestamp 2026-04-08 at spike time.
- **Status:** ✅ GO
- **Notes:** Variables on griddap: `sst`, `anom`, `err`, `ice`. Dataset `ncdcOisst21NrtAgg` for NRT (Earth Now globe freshness), `ncdcOisst21Agg` for historical analysis. WMS path is ready for direct tile overlay on globe without backend roundtrip.
- **Fallback:** (1) NASA PODAAC **GHRSST AVHRR_OI-NCEI-L4-GLOB-v2.1** (same underlying product, different distributor) — CMR collection `C2036881712-POCLOUD`. Requires NASA Earthdata Login. Use `earthaccess` Python library. (2) Original NCEI THREDDS (once restored).

### Dead endpoints (for the record)
- ❌ `https://www.ncei.noaa.gov/thredds/dodsC/model-oisst-daily/` — OPeNDAP "Unrecognized request"
- ❌ `https://www.ncei.noaa.gov/thredds-ocean/fileServer/oisst-daily/oisst-avhrr/oisst-avhrr-YYYYMMDD.nc` — 404

## 5. U.S. Climate Normals 1991-2020

- **Endpoint:** `https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/access/{STATION_ID}.csv` (station-level). Directory index at `https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/`. Also: `/normals-annualseasonal/1991-2020/`, `/normals-daily/1991-2020/`, `/normals-hourly/1991-2020/`.
- **Auth:** None.
- **Sample call:** `curl -s "https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/access/USW00012839.csv" | head -15` (USW00012839 = LAX). Verified live: ~40 KB, 77 monthly normals fields.
- **Response format:** CSV — STATION, DATE, LATITUDE, LONGITUDE, ELEVATION, NAME, then MLY-TAVG-NORMAL, MLY-TMAX-NORMAL, MLY-TMIN-NORMAL, precipitation, frost days, etc. with measurement/completeness flags.
- **Rate limit:** None documented.
- **Update frequency:** Fixed 30-year baseline (1991–2020). Next cycle 2021–2050 not yet published.
- **Status:** ✅ GO
- **Notes:** ~15,000 US stations. File naming by ICAO/NCEI station code. For Local Reports Block 2, need city→nearest-station mapping table. Tag as **derived** (30-yr statistical mean, not raw observation).
- **Fallback:** (1) Gridded monthly normals NetCDF (~275 MB, spatially continuous) at same base directory. (2) NCEI CDO Web Tool `https://www.ncei.noaa.gov/cdo-web/tools/normals` for interactive lookups.

## 6. AirNow

- **Endpoint:** `https://www.airnowapi.org/aq/observation/zipCode/current/` and `/aq/observation/latLong/current/`. Docs: `https://docs.airnowapi.org/`.
- **Auth:** Free API key, registration at `https://docs.airnowapi.org/`. Key passed as `API_KEY` query parameter.
- **Sample call:** `curl -s "https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode=25404&distance=5&API_KEY=YOUR_KEY"`
- **Response format:** JSON array — `DateObserved`, `ReportingArea`, `StateCode`, `Latitude`, `Longitude`, `ParameterName` ('O3'/'PM2.5'/...), `AQI`, `CategoryName`, `CategoryNumber`. Empty array when no data.
- **Rate limit:** 500 req/hour per endpoint per key (separate quotas for hourly/daily × zip/latlong).
- **Update frequency:** Hourly.
- **Status:** ✅ GO
- **Notes:** ⚠️ **Reporting area ≠ city boundary** — mandatory UI disclaimer in Local Reports Block 1. Current AQI = peak pollutant in reporting area.
- **Fallback:** EPA AQS (historical/annual, different cadence). OpenAQ v3 (global, different coverage).

## 7. OpenAQ v3

- **Endpoint:** `https://api.openaq.org/v3/locations`, `/v3/measurements`, `/v3/locations/{id}`. Base: `https://api.openaq.org/v3/`.
- **Auth:** API key required. Registration `https://explore.openaq.org/register`. Passed as header: `X-API-Key: YOUR_KEY`.
- **Sample call:** `curl -s -H "X-API-Key: YOUR_KEY" "https://api.openaq.org/v3/locations?limit=5"`
- **Response format:** JSON — metadata (citation, license, timestamp) + results array with location IDs, coordinates, sensors, measurement history.
- **Rate limit:** Free tier: 60 req/min, 2,000 req/hour. 429 on excess. Headers: `x-ratelimit-remaining`, `x-ratelimit-reset`.
- **Update frequency:** Varies per contributing station (aggregator model).
- **Status:** ✅ GO
- **Notes:** ⚠️ **v1 and v2 retired 2025-01-31** (return 410 Gone). Must use v3. Strongest coverage: PM2.5, PM10, SO2, NO2, CO, O3. Per CLAUDE.md, home globe labels this "**Air monitors**" (NOT "AQI") — global aggregation, not for US Local Reports.
- **Fallback:** EPA AQS (US-authoritative), AirNow (current).

## 8. CAMS (Copernicus Atmosphere Monitoring Service)

- **Endpoint:** `https://ads.atmosphere.copernicus.eu/api` (Atmosphere Data Store / CDS API). Primary dataset: `cams-global-atmospheric-composition-forecasts`.
- **Auth:** Required. Free ADS account + personal access token from profile. Config file `$HOME/.cdsapirc`:
  ```
  url: https://ads.atmosphere.copernicus.eu/api
  key: <PERSONAL-ACCESS-TOKEN>
  ```
  Dataset ToS must be accepted on web UI before first retrieval.
- **Sample call:**
  ```python
  import cdsapi
  c = cdsapi.Client()
  c.retrieve('cams-global-atmospheric-composition-forecasts', {
      'date': '2026-04-10',
      'variable': 'total_aerosol_optical_depth_550nm',
      'time': '00:00',
      'format': 'netcdf'
  }, 'download.nc')
  ```
  (Requires `cdsapi>=0.7.7` Python client and configured `.cdsapirc`.)
- **Response format:** GRIB2 (preferred) or GRIB1; NetCDF alternative (experimental, not recommended for production).
- **Rate limit:** Not formally published. Free, but queuing behind concurrent jobs can add latency.
- **Update frequency:** 5-day forecast issued daily; ~6-12h lag from 00/12 UTC model runs.
- **Status:** ⚠️ 주의사항 있음 — free but requires registration, ToS acceptance per-dataset, and Python cdsapi client. No direct curl/REST path.
- **Notes:** CAMS system upgrade scheduled 2026-05-12 — monitor release notes. For Earth Now **"Smoke" layer**, consider WMS/tile service instead of data download path: ECMWF / ADS also publishes WMS tiles. Investigate WMS alternative to avoid running Python cdsapi inside the FastAPI backend.
- **Fallback:** (1) WMS tile service from ADS if available for the smoke product. (2) NASA VIIRS FRP from FIRMS as smoke-source proxy (already in stack). (3) NASA MERRA-2 aerosols via GES DISC (reanalysis, different provenance).

## 9. USGS Modernized Water Data API

- **Endpoint:** `https://api.waterdata.usgs.gov/ogcapi/v0/collections/{collection-id}/items`. Collections: `continuous` (15-min instantaneous), `daily` (daily means), `monitoring-locations` (sites), `time-series-metadata`. Legacy `waterservices.usgs.gov` sunsets **2027 Q1** — must NOT be used for new code.
- **Auth:** None required for basic use; optional free API key at `https://api.waterdata.usgs.gov/signup/` unlocks higher request rates. Response header: `X-Api-Umbrella-Request-Id`.
- **Sample call:**
  ```bash
  # Continuous instantaneous values (streamflow at Potomac @ Washington DC)
  curl "https://api.waterdata.usgs.gov/ogcapi/v0/collections/continuous/items?limit=2&monitoring_location_id=USGS-01646500"

  # Daily values
  curl "https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items?limit=2&monitoring_location_id=USGS-01646500&datetime=2026-04-01/2026-04-10"

  # Sites within bbox
  curl "https://api.waterdata.usgs.gov/ogcapi/v0/collections/monitoring-locations/items?bbox=-77.05,38.75,-77.00,38.80&limit=2"
  ```
- **Response format:** GeoJSON (default). Alternatives via `f=`: `csv`, `jsonld`, `html`.
- **Rate limit:** Not explicitly documented; API key enables higher throughput.
- **Update frequency:** `continuous` = 15-min (near-real-time). `daily` = daily rollups.
- **Status:** ✅ GO
- **Notes:** OGC API Features standard. Response is one feature per observation (not grouped per time series) — differs from legacy WaterML2; normalize in connector. `gwlevels` and SensorThings APIs decommissioned fall 2025. 3-year rolling window on `continuous` collection — older data must come from `daily`. Tag as **observed** for sensor data; cadence-wise the continuous collection qualifies for **near-real-time** trust tag.
- **Fallback:** Legacy `waterservices.usgs.gov` until 2027 Q1 — **only for emergency validation cross-checks, not production**.

## 10. Water Quality Portal (WQP) beta — WQX 3.0

- **Endpoint:** **BETA WQX 3.0 (REQUIRED):** `https://www.waterqualitydata.us/wqx3/Result/search`, `.../wqx3/Station/search`, `.../wqx3/Activity/search`, `.../wqx3/ActivityMetric/search`. **Legacy WQX 2.2** (`/data/...`) is broken for USGS samples post-2024-03-11.
- **Auth:** None (free, public).
- **Sample call:**
  ```bash
  # Results via BETA WQX 3.0 (includes USGS data post-2024-03-11)
  curl "https://www.waterqualitydata.us/wqx3/Result/search?bBox=-77.05,38.75,-77.00,38.80&providers=NWIS&limit=5&mimeType=csv"

  # Stations
  curl "https://www.waterqualitydata.us/wqx3/Station/search?bBox=-77.05,38.75,-77.00,38.80&providers=NWIS&limit=5&mimeType=json"
  ```
- **Response format:** CSV (`mimeType=csv`), JSON (`mimeType=json`), GeoJSON (`mimeType=geojson`), XML (default WQX), XLSX, KML/KMZ.
- **Rate limit:** Not formally documented. Reasonable-use expected.
- **Update frequency:** EPA/state (STORET/WQX) refreshed weekly (Thursday evening). USGS (NWIS) samples post-2024-03-11 **only on `/wqx3/` beta** — not on legacy `/data/`.
- **Status:** ⚠️ 주의사항 있음 — **CRITICAL GUARDRAIL (matches CLAUDE.md)**
- **Notes (extended — project depends on this):**
  - On **2024-03-11**, WQP standard UI export (`/data/...`) transitioned to **WQX 2.2 only**, BLOCKING all USGS discrete water-quality data added/modified after that date. This is a known, documented breakage.
  - Our code MUST use the `/wqx3/` beta endpoints, NOT `/data/`.
  - Column names differ between WQX 2.2 and 3.0 — the backend connector must be written against the 3.0 schema.
  - Query params: `providers=NWIS` (USGS) / `STORET` (EPA/state), `bBox` or `countycode`/`statecode`, `characteristicName` (analyte filter e.g. "Nitrate", "Dissolved oxygen"), `startDateLo`/`startDateHi`.
  - Tag discrete samples as **observed** with cadence "discrete — dates vary" (CLAUDE.md mandatory UI label).
  - Endpoints confirmed: `/Result/search`, `/Station/search`, `/Activity/search`, `/ActivityMetric/search`.
- **Fallback:** (1) USGS **Samples Data API** (modernized, USGS-only) as documented in the R `dataRetrieval` package — redundant path for USGS data. (2) For pre-2024-03-11 historical-only queries, legacy `/data/` still works. (3) Legacy `waterservices.usgs.gov/qwdata` is **decommissioned** — do not use.

## 11. EPA ECHO

- **Endpoint:** `http://ofmpub.epa.gov/echo/` — REST services: `get_facilities`, `get_qid`, `get_facility_info`, `get_download`, `get_map`, `get_enforcement_case_search`. Swagger/docs at `https://echo.epa.gov/tools/web-services`.
- **Auth:** None (public REST).
- **Sample call:**
  ```bash
  curl "http://ofmpub.epa.gov/echo/echo13_rest_services.get_facilities?p_st=CA&output=json&p_limit=5"
  ```
- **Response format:** JSON (default) / CSV / JSONP. Fields: facility name, location, permit status, violation history, enforcement actions, penalties.
- **Rate limit:** Not publicly documented; EPA applies throttling on excessive concurrent/successive queries. Watch for 429/503.
- **Update frequency:** Live feed — updated as cases enter ICIS and prosecution databases.
- **Status:** ✅ GO
- **Notes:** ⚠️ **HTTP only** — `https://ofmpub.epa.gov` returns 404. Must use `http://`. Pagination via QID pattern: `get_facilities` returns summary + QID (valid ~30 min) → iterate with `get_qid`. Bbox: `p_c1lon`, `p_c1lat`, `p_c2lon`, `p_c2lat`. For CBSA aggregation, query by bbox of CBSA boundary or by county FIPS. **MANDATORY UI disclaimer (CLAUDE.md):** "regulatory compliance ≠ environmental exposure or health risk".
- **Fallback:** ECHO Data Downloads (pre-exported CSVs) at `https://echo.epa.gov/tools/data-downloads`. R package `echor` if server-side R is available.

## 12. EPA AirData / AQS

- **Endpoint:** `https://aqs.epa.gov/data/api/` — key services `/annualData/byCounty`, `/annualData/byCBSA`, `/site/bySite`, `/list/parametersByClass`. Docs: `https://aqs.epa.gov/aqsweb/documents/data_api.html`.
- **Auth:** Required — email + API key. Signup: `https://aqs.epa.gov/data/api/signup?email=your@email.com` (verification email delivers key). Credentials passed as query params.
- **Sample call:**
  ```bash
  curl "https://aqs.epa.gov/data/api/annualData/byCounty?email=you@example.com&key=YOUR_KEY&param=88101&state=06&county=001&bdate=20250101&edate=20251231"
  ```
- **Response format:** JSON — `Header` + `Data` structure. Annual summary: AQI, PM2.5, Ozone, sample counts, validity.
- **Rate limit:** **10 req/min** enforced. Recommend 5-sec pause between calls. Single query max 1,000,000 rows. Suspension for abuse.
- **Update frequency:** Annual batch (PM2.5 annual avg certified ~March; preliminary within season).
- **Status:** ⚠️ 주의사항 있음 — functional but requires registration + strict rate limit.
- **Notes:** Parameter codes: **PM2.5 FRM/FEM = 88101**, **PM2.5 non-FRM = 88502**, **Ozone = 44201**. Max 5 params per request. `bdate`/`edate` must be same calendar year. County-level uses state+county FIPS. For CBSA-level, use `/annualData/byCBSA` with CBSA code. This is the ANNUAL source (CLAUDE.md: "Current vs Trend source separation" — pair with AirNow for current).
- **Fallback:** EPA AirData web portal CSV downloads at `https://aqs.epa.gov/aqsweb/airdata/download_files.html` (pre-generated annual summary files — good candidate for batch ingest avoiding the 10 req/min wall).

## 13. NASA FIRMS

- **Endpoint:** `https://firms.modaps.eosdis.nasa.gov/api/area/{FORMAT}/{MAP_KEY}/{SOURCE}/{AREA_COORDS}/{DAY_RANGE}[/{DATE}]`. Sources: `MODIS_NRT`, `MODIS_SP`, `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT`, `LANDSAT_NRT`. Alt country API: `/api/country/...`. US/Canada NRT via USFS endpoint `/usfs/api/area/...`.
- **Auth:** Free **MAP_KEY** registration: `https://firms.modaps.eosdis.nasa.gov/api/map_key/`. 32-char alphanumeric delivered via email. Key passed as URL path segment.
- **Sample call:**
  ```bash
  # VIIRS NRT, 3-day lookback, South America bbox, CSV
  curl "https://firms.modaps.eosdis.nasa.gov/api/area/csv/YOUR_MAP_KEY/VIIRS_SNPP_NRT/-100,-50,100,50/3"
  ```
- **Response format:** CSV (default) or JSON or KML. Row fields: latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, **frp** (Fire Radiative Power), daynight.
- **Rate limit:** **5000 transactions per 10-minute rolling window** per MAP_KEY. Large areas or 7-day global queries consume multiple transactions. Higher quotas on request.
- **Update frequency:** NRT (~3h latency from satellite overpass). SP (standard) product ~2-week processing delay.
- **Status:** ✅ GO
- **Notes:** Endpoint verified live (invalid-key test returns proper error response). Coords format: `west,south,east,north`. DAY_RANGE: 1–5 days. Optional historical `DATE`: `YYYY-MM-DD`. Default globe layer — pair with GIBS for VIIRS true-color base.
- **Fallback:** FIRMS Web Map `https://firms.modaps.eosdis.nasa.gov/map/` (interactive, manual exports). WMS/WFS at `https://firms.modaps.eosdis.nasa.gov/mapserver/` (tiles, no MAP_KEY required — good for globe overlay pre-render).

## 14. NASA GIBS

- **Endpoint:** WMTS base: `https://gibs.earthdata.nasa.gov/wmts/epsg{EPSG}/best/` (EPSG ∈ {4326, 3857, 3413, 3031}). Tile URL (REST): `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/{LayerIdentifier}/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.{ext}`. Capabilities: `.../wmts.cgi?request=GetCapabilities` or `.../1.0.0/WMTSCapabilities.xml`.
- **Auth:** None (public, CDN-backed).
- **Sample call:**
  ```bash
  # GetCapabilities to enumerate layers
  curl "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi?request=GetCapabilities"

  # Sample tile — MODIS Terra True Color
  curl -o tile.jpg "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2026-04-09/250m/0/0/0.jpg"
  ```
- **Response format:** JPEG / PNG / WebP tiles (binary). Metadata: WMTS XML.
- **Rate limit:** None documented. Globally CDN-cached.
- **Update frequency:** Varies per layer. Blue Marble monthly; MODIS Terra/Aqua daily; aerosol/AOD ~6-12h.
- **Status:** ✅ GO
- **Notes:** ⚠️ **No layer literally named "Natural Earth"** — closest analog in GIBS is `BlueMarble_ShadedRelief_Bathymetry` (MODIS composite with relief + bathy). True-color daily: `MODIS_Terra_CorrectedReflectance_TrueColor`. Tile matrix set names depend on projection (e.g. `250m`, `500m`, `1km`, or `GoogleMapsCompatible_Level{0-28}` for EPSG:3857). Must match the target layer's supported matrix (check GetCapabilities). For EarthPulse home globe base, use Blue Marble layer and relabel UI as "Natural Earth".
- **Fallback:** (1) NASA Worldview at `https://worldview.earthdata.nasa.gov/` (interactive, same layers). (2) Mapbox/Maptiler as commercial basemap (requires key). (3) OpenStreetMap tiles as last-resort basemap.

---

## Step 2 Spike — Event Layers: FIRMS Wildfires + USGS Earthquakes (2026-04-17)

### Summary Table (7 axes)

| Axis | FIRMS VIIRS SNPP NRT | USGS Earthquakes |
|---|---|---|
| **Auth** | Free MAP_KEY (email reg) — URL path segment | None |
| **Rate limit** | 5,000 transactions / 10-min window per key | No documented limit; feeds are static GeoJSON files, CDN-served |
| **Spatial coverage** | Global (bbox param: `west,south,east,north`) | Global |
| **Cadence** | NRT ~3 h from satellite overpass | `all_day`: regenerated ~1 min; `all_week`: ~5 min; `all_month`: ~15 min |
| **Latency** | ~3 h from overpass; DAY_RANGE 1–5 | Near-instantaneous (static file, CDN) |
| **Payload size** | Varies by bbox/days; global 1-day ~500 KB–2 MB CSV | `all_day.geojson` ~180 KB (271 features on 2026-04-17 spike) |
| **Client-direct?** | **No** — MAP_KEY must be hidden in Worker | **No** — must go through Worker for bbox filtering and cache |

**MAP_KEY registration:** `https://firms.modaps.eosdis.nasa.gov/api/map_key/`
**Env var for Worker:** `FIRMS_MAP_KEY`

---

### USGS Live Spike Results (2026-04-17)

- **Endpoint verified:** `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson`
- **HTTP status:** 200
- **Feature count:** 271
- **Magnitude range:** -0.9 → 4.7 (all_day includes micro-quakes; use `4.5` or `significant` feeds for Globe default)
- **Timestamp format:** `properties.time` — **Unix ms epoch** (divide by 1000 for ISO)
- **Depth:** `geometry.coordinates[2]` in **km** (positive = below surface)
- **Tsunami flag:** `properties.tsunami` — integer (0 = no, 1 = possible). Can be `null` for minor events — null-safe required.
- **Alert:** `properties.alert` — `"green"/"yellow"/"orange"/"red"` or `null` for non-significant events.
- **API version:** 2.3.0
- **Response size:** ~180 KB (271 features)

Sample feature (index 0, 2026-04-17):
```
id: "aka2026hnobgm"
mag: 1.0, place: "65 km WNW of Happy Valley, Alaska"
time: 1776429393935 (ms) → 2026-04-17T18:16:33.935Z
geometry.coordinates: [-152.85, 60.137, 17.7]  → [lon, lat, depth_km]
tsunami: 0, alert: null, magType: "ml"
```

---

### FIRMS Key-Less Probe (2026-04-17)

- **Invalid MAP_KEY response:** HTTP **400** (not 401/403 — see Landmine #1)
- Response body: plain text error message from FIRMS API
- Key format: 32-char alphanumeric (delivered via email on registration)
- Worker must inject key from env var `FIRMS_MAP_KEY`; never expose to client

---

### EventPoint Normalization

#### USGS GeoJSON → EventPoint (TypeScript)

```typescript
import type { EventPoint } from '@/packages/schemas/events';

export function normalizeUsgsFeature(f: GeoJsonFeature): EventPoint {
  const p = f.properties;
  const [lon, lat, depthKm] = f.geometry.coordinates;
  return {
    id: `usgs-${f.id}`,
    type: 'earthquake',
    lat,
    lon,
    observedAt: new Date(p.time).toISOString(),   // ms epoch → ISO
    severity: p.mag ?? 0,
    label: p.title,
    properties: {
      mag: p.mag,
      place: p.place,
      depth_km: depthKm,
      tsunami: p.tsunami ?? 0,          // null-safe — default 0
      alert: p.alert ?? null,
      magType: p.magType,
      sig: p.sig,
      status: p.status,
      net: p.net,
      time: p.time,
      updated: p.updated,
    },
  };
}
```

#### FIRMS CSV → EventPoint (TypeScript)

```typescript
// VIIRS SNPP NRT CSV columns (ordered):
// latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,
// satellite,confidence,version,bright_ti5,frp,daynight

export function normalizeFirmsRow(row: Record<string, string>, idx: number): EventPoint {
  const lat = parseFloat(row.latitude);
  const lon = parseFloat(row.longitude);
  const frp = parseFloat(row.frp) || 0;
  // acq_date="2026-04-16", acq_time="0130" → "2026-04-16T01:30:00Z"
  const hhmm = row.acq_time.padStart(4, '0');
  const observedAt = `${row.acq_date}T${hhmm.slice(0, 2)}:${hhmm.slice(2)}:00Z`;
  return {
    id: `firms-viirs-${row.acq_date.replace(/-/g, '')}-${row.acq_time}-${idx}`,
    type: 'wildfire',
    lat,
    lon,
    observedAt,
    severity: frp,
    label: `Active fire — FRP ${frp} MW`,
    properties: {
      bright_ti4: parseFloat(row.bright_ti4),
      bright_ti5: parseFloat(row.bright_ti5),
      scan: parseFloat(row.scan),
      track: parseFloat(row.track),
      acq_date: row.acq_date,
      acq_time: row.acq_time,
      satellite: row.satellite,    // "N"=NOAA-20/21, "S"=Suomi-NPP
      confidence: row.confidence,  // "low"|"nominal"|"high"
      version: row.version,
      frp,
      daynight: row.daynight,      // "D"|"N"
    },
  };
}
```

---

### Worker API Endpoint Design

#### `GET /api/fires?bbox=w,s,e,n&days=1`

```
Worker injects FIRMS_MAP_KEY → proxies:
  GET https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/{bbox}/{days}
Returns: JSON EventPoint[] (CSV parsed and normalized server-side)
Cache: 10 min (CF Cache-Control: max-age=600)
Params:
  bbox  required  "west,south,east,north"  e.g. "-180,-90,180,90"
  days  optional  1-5, default 1
```

Worker splits large global bbox into sub-regions if needed (see Landmine #3).

#### `GET /api/earthquakes?period=day&magnitude=all`

```
Worker proxies:
  GET https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{magnitude}_{period}.geojson
Returns: JSON EventPoint[] (normalized from GeoJSON)
Cache: 5 min (CF Cache-Control: max-age=300)
Params:
  period     optional  hour|day|week|month  default "day"
  magnitude  optional  significant|4.5|2.5|1.0|all  default "all"
Globe default: magnitude=4.5&period=day (reduce noise)
```

---

### Cache TTL Recommendation

| Source | TTL | Rationale |
|---|---|---|
| FIRMS | **10 min** | NRT cadence ~3h; 10-min cache cuts Worker transactions 6× per hour while staying far within 3h window |
| USGS | **5 min** | Static GeoJSON regenerated ~1 min; 5 min gives reasonable freshness without hammering CDN |

---

### Landmines

1. **FIRMS returns HTTP 400 (not 401/403) for invalid MAP_KEY.** Worker error handler must treat 400 as auth failure and return `{ status: "not_configured" }` — don't surface raw FIRMS 400 to client.

2. **USGS `properties.time` is Unix ms (not seconds).** Must divide by 1000 before passing to `new Date()` — or use `new Date(p.time)` directly (JS Date accepts ms). Do not do `new Date(p.time / 1000)` which would give ~1970.

3. **FIRMS bbox fan-out for global coverage.** The FIRMS API limits very large bboxes to a set number of transactions. A single `-180,-90,180,90` request may use 100+ transactions. For global coverage, either (a) use the country API endpoint instead of bbox, or (b) split into ~9 regional sub-bboxes and merge.

4. **FIRMS CSV column drift between VIIRS and MODIS.** MODIS CSV has `brightness` / `bright_t31` instead of `bright_ti4` / `bright_ti5`. The normalization function must branch on `instrument` or `satellite` to avoid undefined column reads. Default Worker layer uses VIIRS_SNPP_NRT only.

5. **USGS `properties.mag` can be `null` for quarry blasts / other events.** Normalize as `severity: p.mag ?? 0` and skip display if `mag === null`.

6. **USGS `properties.tsunami` is integer 0/1 but can be `null` for older or non-network events.** Always null-coalesce: `tsunami: p.tsunami ?? 0`.

7. **USGS `geometry.coordinates[2]` is depth in km positive-down.** Do NOT negate — 17.7 means 17.7 km deep, not elevation. Label popup as "Depth: X km".

8. **FIRMS `acq_time` is HHMM with no separator, zero-padded to 4 digits.** Time "130" must be padded to "0130" before parsing. Use `.padStart(4, '0')`.

---

### Popup Data Contracts

**Fire popup fields:**
- `lat`, `lon`
- `frp` (Fire Radiative Power in MW)
- `confidence` ("low" / "nominal" / "high")
- `acq_date` + `acq_time` (acquisition datetime)
- `satellite` ("N" = NOAA-20/21, "S" = Suomi-NPP, "T" = Terra-MODIS, "A" = Aqua-MODIS)
- `daynight` ("D" = daytime, "N" = nighttime)

**Earthquake popup fields:**
- `mag` + `magType`
- `depth_km` (from `geometry.coordinates[2]`)
- `place`
- `observedAt` (ISO 8601)
- `tsunami` (0 = no / 1 = possible — display warning badge if `tsunami === 1`)
- `alert` (PAGER color if not null)

---

## Integration Actions (immediate)

1. ~~**❌ OISST blocker**~~ **✅ RESOLVED 2026-04-10** — pivoted to NOAA CoastWatch ERDDAP. Connector updated. See OISST section for details.
2. **⚠️ NOAA CtaG** — no API: pivot Climate Trends strip to **NOAAGlobalTemp CDR NetCDF** directly; defer city-series Local-Report path to a secondary spike.
3. **⚠️ WQP** — hard-code `/wqx3/` beta endpoints in `wqp.py` connector; add unit test to detect accidental use of `/data/...`.
4. **⚠️ CAMS** — investigate ADS WMS tile path BEFORE committing to cdsapi inside FastAPI.
5. **Registration checklist (5 free accounts needed):** AirNow, OpenAQ v3, Copernicus ADS, EPA AQS, NASA FIRMS.
6. **Production URL corrections to apply now:**
   - `connectors/usgs.py`: confirm `api.waterdata.usgs.gov/ogcapi/v0/...` as base.
   - `connectors/wqp.py`: set base to `waterqualitydata.us/wqx3/` and leave a comment about the 2024-03-11 breakage.
   - `connectors/echo.py`: use `http://` not `https://`.
   - `connectors/gibs.py`: default layer = `BlueMarble_ShadedRelief_Bathymetry`, UI label "Natural Earth".
