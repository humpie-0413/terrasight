# Data Sources & Connector Catalog

Detailed per-source reference for every P0/P1/P2 dataset in EarthPulse.
Connector implementations live in `backend/connectors/`; this file is the
source of truth for cadence, trust tag, and update rhythm.

## Trust-tag vocabulary (5 levels)

| Tag | Color | Meaning |
|---|---|---|
| observed | 🟢 | Direct instrument measurement |
| near-real-time | 🟡 | Processed within a few hours |
| forecast/model | 🟠 | CAMS, GFS etc. — model output |
| derived | 🔵 | Calculated from observed values |
| estimated | ⚪ | Statistical / ML inference |

Every data surface in the UI must attach one of these tags. The
`backend/connectors/base.py::ConnectorResult.tag` field enforces this
at the type level (`Literal["observed", ...]`).

---

## P0 — MVP spine

### Earth Now (globe layers)

| Source | Purpose | Cadence | Tag |
|---|---|---|---|
| NASA GIBS / Worldview | Base imagery | varies | observed / NRT |
| NASA FIRMS | Wildfires / thermal anomalies | NRT ~3h | observed |
| AirNow | Current AQI (reports) | hourly | observed |
| OpenAQ v3 | Global air monitors (home globe) | varies | observed |
| NOAA OISST | Daily SST | daily | observed |
| CAMS | Smoke / atmospheric composition | 6–12h | forecast/model |

### Climate Trends (3 cards)

| Card | Source | Cadence | Tag | Record start |
|---|---|---|---|---|
| CO₂ concentration | NOAA GML Mauna Loa | daily + monthly | observed | 1958 |
| Global temp anomaly | NOAA CtaG (via NOAAGlobalTemp CDR v6.1) | monthly | NRT / preliminary | 1850 |
| Arctic sea ice | NSIDC Sea Ice Index (G02135 v4.0, 5-day mean) | daily | observed | 1978 |

### Local Reports

| Source | Purpose | Cadence | Tag |
|---|---|---|---|
| AirNow | Current AQI | hourly | observed |
| EPA AirData / AQS | Annual AQI, PM2.5 | annual | observed |
| NOAA CtaG | City temperature time series | monthly | observed |
| U.S. Climate Normals 1991-2020 | Reference baseline | 30-yr | derived |
| EPA ECHO | Facilities / violations / enforcement | live feed | regulatory |
| USGS modernized OGC API | Continuous hydrology | 15-min | observed |
| WQP `/wqx3/` beta | Discrete water-quality samples | discrete | observed |

### Story Panel

Preset-driven editorial — 5 to 10 seasonal / event templates sitting on
top of Earth Now layers. Currently one hardcoded preset ("2026 Wildfire
Season") at `/api/earth-now/story`.

---

## P1 — Differentiators

- Worldview additional imagery layers
- ECHO fact rankings (EPA violations)
- AirData PM2.5 annual rankings
- Born-in Interactive (CO₂ / temp / sea ice then vs now)
- Educational guide series

## P2 — Expansion

- Soil / Land (SoilGrids)
- Waste & Materials (hazardous waste, TRI)
- Climate TRACE emissions facility map
- Global Local Report expansion
- Custom aggregate environmental indicators

---

## Verified endpoint quirks (from the 2026-04-10 API spike)

These are the landmines; every connector touching the listed source must
handle them exactly as described.

### EPA ECHO
- **HTTP only** — `https://ofmpub.epa.gov/...` returns 404. Use
  `http://ofmpub.epa.gov/echo/echo13_rest_services.get_facilities`.
- Bounding-box params: `p_c1lon`, `p_c1lat` (W/S) / `p_c2lon`, `p_c2lat`
  (E/N). `Output=JSON` + `responseset=N` returns the first response with
  QueryID, Totals, and the first N facilities.
- Facility-level violation flags (`CurrVioFlag`, `Over3yrsFormalActions`,
  `Over3yrsEnfAmt`) live on each facility object in the first response —
  no QID second-hop needed for counts.
- Some deployment networks block `ofmpub.epa.gov`; the connector must
  surface a timeout as a block-level error and the orchestrator must
  degrade the report gracefully.

### USGS modernized Water Data
- Base: `https://api.waterdata.usgs.gov/ogcapi/v0/`. Legacy
  `waterservices.usgs.gov/` is scheduled for 2027 Q1 decommission.
- Use `/collections/daily/items?bbox=W,S,E,N&parameter_code=00060&datetime=<start>/<end>`.
- Feature property names observed live: `monitoring_location_id`, `time`
  (YYYY-MM-DD), `value` (string), `unit_of_measure`, `parameter_code`,
  `statistic_id`, `approval_status`.
- **Feature payload has no site_name** — a second lookup against
  `/collections/monitoring-locations/items` is required for
  human-readable labels; we fall back to the USGS site ID for now.
- Features are NOT time-sorted; `datetime` interval is essential and we
  dedupe per `monitoring_location_id` in `normalize()`.

### WQP (Water Quality Portal)
- **Use `/wqx3/` beta endpoints, NOT `/data/`.** The legacy
  `/data/` path serves WQX 2.2 only and is missing all USGS data added
  or modified after 2024-03-11.
- `/wqx3/Result/search` returns **HTTP 500** without
  `dataProfile=basicPhysChem`. Always include it.
- WQX 3.0 column renames (critical — the 2.2 names silently fall
  through as `None`):
  - `Location_Identifier` (was `MonitoringLocationIdentifier`)
  - `Result_Characteristic` (was `CharacteristicName`)
  - `Result_Measure` (was `ResultMeasureValue`)
  - `Result_MeasureUnit` (was `ResultMeasure/MeasureUnitCode`)
  - `Activity_StartDate`, `ProviderName`, `Location_Name` unchanged
- **`providers=NWIS,STORET` (comma-joined) matches zero rows.** WQP
  treats the comma as a literal character. Emit `providers=NWIS` and
  `providers=STORET` as separate repeated params via an httpx list of
  tuples.
- Dates use `MM-DD-YYYY`, not ISO.

### U.S. Climate Normals 1991-2020
- Per-station CSVs at `https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/access/{STATION_ID}.csv`.
- Each file has exactly 12 monthly rows (`DATE = "01".."12"`) and ~260
  columns. We extract `STATION`, `NAME`, `LATITUDE`, `LONGITUDE`,
  `ELEVATION`, plus `MLY-TAVG-NORMAL`, `MLY-TMAX-NORMAL`,
  `MLY-TMIN-NORMAL`, `MLY-PRCP-NORMAL`.
- Missing-value sentinels: `-9999`, `-7777`, blank. Numeric cells are
  space-padded; strip before parsing.
- `USW00012918` is Houston **Hobby** AP, not Intercontinental.

### NOAA GML Mauna Loa
- Direct file: `co2_mm_mlo.txt`. Comment lines prefixed with `#`. No
  auth.

### NOAAGlobalTemp CDR (CtaG pivot)
- CtaG UI has no public REST API. Pivot to
  `ncei.noaa.gov/data/noaa-global-surface-temperature/v6.1/access/timeseries/aravg.mon.land_ocean.90S.90N.v6.1.0.YYYYMM.asc`.
- Filename embeds data-month; scrape the directory index to discover
  the latest file.
- Anomalies are °C relative to the **1991-2020** climatology (many
  other products use 1961-1990 — do not cross-compare magnitudes).

### NSIDC Sea Ice
- `N_seaice_extent_daily_v4.0.csv` at `noaadata.apps.nsidc.org`. The
  "Source Data" column contains commas — parse via `csv` module, not
  naive `.split(",")`.

### NOAA OISST
- PODAAC GHRSST is a fallback. Primary is **NOAA CoastWatch ERDDAP
  griddap CSV** at `ncdcOisst21NrtAgg`, stride 20, two header rows,
  filter NaN land cells, convert 0–360 lon to -180..180.

### NASA FIRMS
- Area API: `api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAYS}`. Full
  global 24h VIIRS is 30k+ points — cap to top N by FRP before
  sending to the browser.

### OpenAQ v3
- v1/v2 retired 2025-01-31. Use `/locations?parameters_id=2&limit=1000`
  for PM2.5 — the single call returns station + coords + latest reading
  inline, no second hop to `/measurements`.
- `X-API-Key` header, ~2000 req/hr.

### AirNow
- Verified: `https://www.airnowapi.org/aq/observation/zipCode/current/`.
  `format=application/json`, `zipCode`, `distance` (miles, default 25),
  `API_KEY`. ~500 req/hr/endpoint.
- Response is one observation per pollutant; the connector picks the
  worst (max AQI) as the headline, matching how AirNow itself
  summarizes a reporting area.

### CAMS
- No public WMS tile endpoint without a Copernicus ADS account. The
  Smoke toggle on the globe ships **disabled** with a tooltip; full
  cdsapi integration is deferred to P1. MODIS AOD from NASA GIBS is a
  possible substitute but not CAMS.

### NASA GIBS (base imagery)
- Public WMTS + WMS, no auth. Default home base:
  `BlueMarble_ShadedRelief_Bathymetry`. `Access-Control-Allow-Origin: *`.

---

---

## Phase A — Global data connectors (2026-04-11)

### GIBS Layer Catalog (`backend/connectors/gibs.py`)

| Catalog key | GIBS Layer ID | TileMatrixSet | Cadence | Available |
|---|---|---|---|---|
| `blue_marble` | `BlueMarble_ShadedRelief_Bathymetry` | 500m | static | ✅ |
| `modis_aod` | `MODIS_Terra_Aerosol` | 2km | daily | ✅ |
| `pm25` | `MERRA2_Dust_Surface_Mass_Concentration_PM25_Monthly` | 2km | monthly | ✅ |
| `oco2_xco2` | `OCO-2_Carbon_Dioxide_Total_Column_Average` | 500m | daily (sparse swath) | ✅ |
| `modis_flood` | `MODIS_Combined_Flood_2-Day` | 250m | daily | ✅ |
| `tropomi_ch4` | — | — | — | ❌ Not in GIBS — use Copernicus GES DISC `S5P_L2__CH4____HiR` |

Landmines:
- `pm25` layer is **dust fraction only** (MERRA-2), not total PM2.5
- `pm25` time param must be `YYYY-MM-DD`, not `YYYY-MM`
- OCO-2 has sparse daily swath — large blank regions are normal
- `blue_marble` has no `{Time}` segment (static layer) — `layers.py` handles this

### Ocean/Climate Connectors

| Connector | Source | Endpoint | Auth | Tag | Cadence |
|---|---|---|---|---|---|
| `noaa_gml_ch4.py` | NOAA GML CH₄ | `gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_mm_gl.txt` | None | observed | monthly |
| `noaa_sea_level.py` | NOAA NESDIS GMSL | `star.nesdis.noaa.gov/.../slr_sla_gbl_free_all_66.csv` | None | observed | ~10-day |
| `coral_reef_watch.py` | NOAA CRW via ERDDAP | `coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW` | None | near-real-time | daily |
| `cmems.py` | Copernicus Marine CMEMS | THREDDS OPeNDAP, product `SEALEVEL_GLO_PHY_L4_NRT_008_046` | `CMEMS_USERNAME` + `CMEMS_PASSWORD` | observed | daily |

Landmines:
- **NOAA Sea Level** old URL `_txj1j2_90.csv` → ECONNREFUSED. Use `_free_all_66.csv`
- **CRW**: ERDDAP dataset ID `NOAA_DHW`; auto-retries previous day if latest 404
- **CMEMS**: Free registration at marine.copernicus.eu — `not_configured` fallback if absent

### Land/Ecology Connectors

| Connector | Source | Endpoint | Auth | Tag | Cadence |
|---|---|---|---|---|---|
| `global_forest_watch.py` | GFW / Hansen UMD | `POST data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/{ver}/query/json` | `GFW_API_KEY` (free, expires 1yr) | derived | annual |
| `jrc_drought.py` | EU JRC / Copernicus EDO | `drought.emergency.copernicus.eu/api/wms` (WMS only) | None | derived | dekadal |

Landmines:
- **GFW**: POST-only query (GET `?sql=` → 405); column name uses double underscores (`umd_tree_cover_loss__year`)
- **GFW**: Country-level stats require polygon geometry — global aggregate only without geometry
- **JRC**: Domain migrated from `edo.jrc.ec.europa.eu` to `drought.emergency.copernicus.eu` (2024-04-03)
- **JRC**: SPI GPCC layer (`spgTS`) requires `SELECTED_TIMESCALE` param ("01","03","06","09","12")
- **JRC**: CDI layer (`cdiad`) is Europe-only, not global
- **JRC**: No JSON/REST API — WMS/WCS tiles only (`status: tiles_only` in response)

### Weather/Emissions Connectors

| Connector | Source | Endpoint | Auth | Tag | Cadence |
|---|---|---|---|---|---|
| `ibtracs.py` | NOAA IBTrACS v04r01 | NCEI CSV (ACTIVE + LAST3YEARS) | None | observed | NRT ~6h (active) |
| `climate_trace.py` | Climate TRACE | `api.climatetrace.org/v6/countries/emissions` | None | estimated | annual |

Landmines:
- **IBTrACS**: Filename is `ibtracs.last3years...` (lowercase) — `LAST3YR` → 404
- **IBTrACS**: CSV has 2 header rows — row 1 is units, must skip before DictReader
- **IBTrACS**: LAST3YEARS file is ~8.8MB; use 120s timeout
- **Climate TRACE**: Query param is `countries` (plural, comma CSV) — `country` (singular) silently returns world aggregate
- **Climate TRACE**: Values are metric tons (not gigatons) — divide by 1e9 for display
- **Climate TRACE**: `continent` field returns string `"null"` (not JSON null) when `countries` param is used

---

## API key registration (free)

| Source | Env var | Register |
|---|---|---|
| NASA FIRMS | `FIRMS_MAP_KEY` | https://firms.modaps.eosdis.nasa.gov/api/map_key/ |
| OpenAQ v3 | `OPENAQ_API_KEY` | https://explore.openaq.org/ |
| AirNow | `AIRNOW_API_KEY` | https://docs.airnowapi.org/ |
| EPA AQS | `AQS_EMAIL` + `AQS_KEY` | https://aqs.epa.gov/aqsweb/documents/data_api.html |
| Copernicus ADS (CAMS) | ADS account + cdsapi | https://ads.atmosphere.copernicus.eu/ |
| CMEMS (Sea Level) | `CMEMS_USERNAME` + `CMEMS_PASSWORD` | https://marine.copernicus.eu/ |
| Global Forest Watch | `GFW_API_KEY` | https://www.globalforestwatch.org/ (free, 1yr expiry) |

ECHO, NSIDC, NOAA GML/CtaG/Normals, USGS, WQP, NASA GIBS, IBTrACS, Climate TRACE,
NOAA Sea Level, NOAA Coral Reef Watch, JRC Drought all require **no key**.

---

## Live endpoint status (verified 2026-04-11)

| Endpoint | Key available? | Status | Notes |
|---|---|---|---|
| `GET /api/earth-now/air-monitors` | ❌ OPENAQ_API_KEY missing | `not_configured` | Graceful degradation OK |
| `GET /api/earth-now/sea-level-anomaly` | ❌ CMEMS credentials missing | `not_configured` | Graceful degradation OK |
| `GET /api/earth-now/fires` | ❌ FIRMS_MAP_KEY missing | `not_configured` | Graceful degradation OK |
| `GET /api/earth-now/storms` | No key needed | ✅ live | IBTrACS |
| `GET /api/earth-now/coral` | No key needed | ✅ live | NOAA CRW |
| `GET /api/earth-now/sst` | No key needed | ✅ live | NOAA OISST |
| `GET /api/trends` | No key needed | ✅ live | 5 indicators |
| `GET /api/layers/catalog` | No key needed | ✅ 6 layers | GIBS only; tropomi_ch4 available=False |
| GFW deforestation | ❌ No endpoint yet | — | Connector exists; needs `/api/earth-now/deforestation` route |

### CtaG city-level time series (Block 2 finding)

Verified 2026-04-11: NOAA Climate at a Glance has **no public REST/CSV API for
city-level time series**. All URL patterns (USW station ID, state+code) return
HTTP 404. The CtaG city interface is JavaScript-rendered only. Block 2 uses
**Climate Normals** (`climate_normals.py`) as the permanent baseline fallback.

### GFW API key config

`GFW_API_KEY` added to `backend/config.py` (`gfw_api_key` field) 2026-04-11.
To activate: set `GFW_API_KEY=...` in `.env` and add a `/api/earth-now/deforestation`
endpoint that calls `GlobalForestWatchConnector(api_key=settings.gfw_api_key)`.

---

## Phase D.1 — EPA regulatory + site datasets (2026-04-12)

Five new connectors that close the Waste, Soil/Land, Water (drinking), and
Facility Emissions gaps identified in `docs/NEXT_STEPS.md` §D.1. All served
by EPA services, no auth required for any of them. Trust tag: `observed`
(self-reported under statute or EPA-curated, but regulator-recorded facts).

| Connector | Source | Endpoint | Auth | Cadence |
|---|---|---|---|---|
| `tri.py` | EPA TRI | `data.epa.gov/efservice/tri_facility/...` + `tri_reporting_form` | None | annual |
| `ghgrp.py` | EPA GHGRP (FLIGHT) | `data.epa.gov/efservice/pub_dim_facility/...` + `pub_facts_sector_ghg_emission` | None | annual |
| `superfund.py` | EPA SEMS / NPL | ArcGIS FeatureServer `FAC_Superfund_Site_Boundaries_EPA_Public/FeatureServer/0/query` | None | monthly |
| `brownfields.py` | EPA ACRES | ArcGIS MapServer `EMEF/efpoints/MapServer/5/query` | None | monthly |
| `sdwis.py` | EPA SDWIS | `data.epa.gov/efservice/water_system/state_code/{ST}/violation/...` | None | quarterly |

Live endpoints (registered in `backend/main.py`):

- `GET /api/releases/tri?state=TX&year=&limit=` — facility rows with chemicals and self-reported releases
- `GET /api/releases/ghgrp?state=TX&year=2023&limit=` — facility rows with total CO₂e
- `GET /api/sites/superfund?west=&south=&east=&north=&limit=` — NPL / SEMS sites in bbox, polygon centroids
- `GET /api/sites/brownfields?west=&south=&east=&north=&limit=` — Brownfields points in bbox
- `GET /api/drinking-water/sdwis?state=TX&zip_prefix=770,771,...&limit=` — PWS with aggregated violation counts

Landmines:

- **Envirofacts host migrated** — `iaspub.epa.gov/enviro/efservice/` is dead; use `data.epa.gov/efservice/` only
- **Envirofacts mandatory pagination** — trailing `/rows/{first}:{last}/JSON` slug is required or queries time out; append `/JSON` to force JSON (default is XML)
- **Envirofacts latency scales super-linearly** — `rows/0:500` ≈ 10s, `rows/0:1500` ≈ 80–95s. Fan out per-slice with `asyncio.gather` instead of one giant slice
- **TRI `fac_latitude`/`fac_longitude` are frequently garbage** — zeros, nulls, or DMS-packed integers. `_pick_coord()` fallback walks candidate keys, rejects 0 and out-of-range values
- **TRI has no single "annual release total" column** — `one_time_release_qty` is a one-time-event field, NOT the annual total. True aggregate requires a second join across `tri_release_qty` media types; `total_release_lb` is left `None` until that's wired
- **GHGRP emissions table is not state-filterable** — `pub_facts_sector_ghg_emission` has no `state` column; fetch a year-windowed slice and aggregate by `facility_id`
- **SDWIS `violation` table `state_code` filter is silently ignored** — querying `violation/state_code/TX/...` returns CT rows with no warning. Use the joined path `water_system/state_code/{ST}/violation/...` instead
- **SDWIS `zip_code` operator `BEGINNING`** is the correct way to narrow water systems to a metro (e.g. `zip_code/BEGINNING/77/...`); per-prefix 500-row cap is real — fan out in parallel per prefix
- **SDWIS joined rows may duplicate `(pwsid, violation_id)`** — de-dupe on `violation_id` during aggregation or violation counts inflate
- **SDWIS mandatory disclaimer** — "SDWIS violations are regulatory compliance records. A violation does NOT necessarily indicate unsafe water at the tap." Must appear in `result.notes`
- **Superfund FeatureServer returns polygons** — the `FAC_Superfund_Site_Boundaries_EPA_Public` layer is MultiPolygon/Polygon; compute centroid via simple vertex averaging (no shapely dependency)
- **Superfund bbox query needs `inSR=4326` explicitly** — omitting it defaults to Web Mercator and returns empty for WGS84 envelopes
- **Brownfields `cleanup_status` lives on a separate ACRES endpoint** — the EMEF efpoints MapServer Layer 5 only exposes facility identification fields; cleanup status needs a second-hop join via `pgm_sys_id`, deferred for now
- **Brownfields layer ID 5** is current under `EMEF/efpoints/MapServer`; if it moves, inspect parent MapServer with `?f=json` to rediscover the layer index

---

## Phase D.2 — P0 hazards, coast, drought, PFAS (2026-04-12)

Six new connectors closing the remaining critical gaps: seismic hazards,
weather alerts, drought, coastal observations, disaster history, and PFAS.

| Connector | Source | Endpoint | Auth | Tag | Cadence |
|---|---|---|---|---|---|
| `earthquake.py` | USGS FDSNWS ComCat | `earthquake.usgs.gov/fdsnws/event/1/query` | None | observed | NRT ~5 min |
| `nws_alerts.py` | NWS Active Alerts | `api.weather.gov/alerts/active` | None (UA required) | observed | NRT |
| `usdm.py` | US Drought Monitor | `usdmdataservices.unl.edu/api/USStatistics/...` | None | observed | weekly (Thu) |
| `coops.py` | NOAA CO-OPS | `api.tidesandcurrents.noaa.gov/api/prod/datagetter` | None | observed | 6-min |
| `openfema.py` | OpenFEMA | `fema.gov/api/open/v2/DisasterDeclarationsSummaries` | None | observed | continuous |
| `pfas.py` | EPA PFAS Analytic Tools | ArcGIS FeatureServer `PFAS_Analytic_Tools_Layers/FeatureServer/1` | None | observed | quarterly |

Live endpoints:

- `GET /api/hazards/earthquakes?min_magnitude=4&limit=500&days=30`
- `GET /api/hazards/alerts?severity=`
- `GET /api/hazards/drought?aoi=US&weeks=4`
- `GET /api/coast/tides?west=&south=&east=&north=&limit=20`
- `GET /api/disasters/declarations?state=TX&years=5&limit=100`
- `GET /api/sites/pfas?west=&south=&east=&north=&limit=100`

Landmines:

- **NWS API requires User-Agent** — api.weather.gov returns 403 without it
- **USDM requires Accept: application/json** — without it returns empty CSV body
- **USDM separate endpoints for national vs state** — `USStatistics` vs `StateStatistics`
- **USDM field names are camelCase** — `mapDate`, `d0` (not `MapDate`, `D0`)
- **OpenFEMA state field uses 2-letter codes** — full state names return 0 results
- **CO-OPS mdapi has bogus lat=0/lng=0 stations** — filter during bbox narrowing
- **CO-OPS datagetter value is string** — `"v": "1.234"` not float; empty = missing
- **PFAS FeatureServer layer 0 → 400** — use layer 1 (UCMR5 drinking water)
- **PFAS State field has leading space** — `" TX"` — must strip
- **PFAS rows are per-sample** — same PWS repeats for each contaminant/date
