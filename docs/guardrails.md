# Guardrails & Verification Checklist

Non-negotiable rules and the checks to run before declaring any feature
"done". CLAUDE.md links here — keep this file short and actionable.

## Absolute rules

1. **Never claim "Live" loosely.** Separate "Now" and "Trends" in the
   UI, and always print the update cadence next to the value.
2. **U.S.-first.** Local Reports ship for U.S. metros first. The Atlas
   is global, but revenue and SEO effort are U.S.-aligned.
3. **Reports have interpretation.** No purely templated auto-generated
   report pages. Every report must offer a unique editorial or
   analytical angle.
4. **No environmental "scores".** We ship *reports*, not composite
   scores. Only transparent screenings are allowed; never claim a
   number is a holistic environmental grade.
5. **Source separation for current vs trend.** Even when two signals
   cover the same topic, current and trend must cite different
   sources (AirNow vs AirData / AQS; USGS continuous vs WQP discrete).
6. **Mandatory disclaimers (non-removable):**
   - ECHO: "Regulatory compliance ≠ environmental exposure or health
     risk."
   - WQP: "Discrete samples — dates vary."
   - AirNow: "Reporting area ≠ CBSA boundary."
7. **Google policy compliance.** Avoid scaled content abuse.
   People-first content. No AdSense inside data tables or charts.

## Layer composition rule (Earth Now globe)

At most **one continuous field + one event overlay** active at the
same time. Layer groups in `frontend/src/components/earth-now/GlobeDeck.tsx`
enforce this client-side via the category pill system. Examples:

- ✅ Ocean Heat (continuous) + Fires (event)
- ✅ Air Monitors (continuous) + Fires (event)
- ❌ Ocean Heat + Air Monitors (both continuous)

## Trust-tag vocabulary (always attach one)

`observed` 🟢 / `near-real-time` 🟡 / `forecast` 🟠 / `derived` 🔵 /
`estimated` ⚪. Enforced by the `TrustTag` `Literal` in
`backend/connectors/base.py`.

## Trust signal placement

The MetaLine (cadence · trust badge · source) renders **before** the
numerical value. From CLAUDE.md: "메타정보가 숫자보다 먼저 보여야 함".
Applies to every indicator, card, and block.

---

## Verification checklist (before marking a feature done)

Run these in order.

### Backend

- [ ] New / modified connectors use `ConnectorResult` with a valid
      `tag` value (compile-time enforced).
- [ ] Connector has a module docstring explaining endpoint quirks —
      especially anything learned the hard way during implementation
      (see `docs/connectors.md` for the landmines we already know).
- [ ] `python -c "from backend.main import app"` imports cleanly.
- [ ] For each new connector: a standalone smoke test that fetches
      real data (or returns `configured: false` gracefully).
- [ ] Orchestrator endpoints wrap connector failures — a single
      connector outage MUST NOT 5xx the whole route.

### Frontend

- [ ] `npm run build` succeeds with zero TypeScript errors.
- [ ] Bundle stays under 600 KB gzipped (currently ~580 KB).
- [ ] Every new data surface renders a `MetaLine` before any numbers.
- [ ] Loading / error / `not_configured` / `pending` states are
      handled distinctly — no blank screens on partial failure.
- [ ] Mandatory disclaimers from the Absolute Rules section appear
      verbatim on the relevant blocks (ECHO / WQP / AirNow).

### Data correctness

- [ ] Cross-check at least one value in the payload against the
      upstream source (e.g. the AirNow website, the NCEI file you
      fetched from) to catch unit or schema drift.
- [ ] Preserve any URL / endpoint quirk notes in the connector
      docstring so the next person hitting the same landmine finds
      the answer in the code they already have open.

---

## Known landmines (do not re-discover)

| Landmine | Where | Fix |
|---|---|---|
| ECHO `ofmpub.epa.gov` → blocked | `connectors/echo.py` | Use `https://echodata.epa.gov/echo/` |
| ECHO blocks default httpx User-Agent as "robotic query" | `connectors/echo.py` | Must send descriptive UA header; default `python-httpx/...` triggers API block |
| ECHO `echo13_rest_services` → 404 on echodata | `connectors/echo.py` | Use `echo_rest_services` (no `13`) |
| ECHO single-hop returns no Facilities | `connectors/echo.py` | Two-hop required: `get_facilities` → QueryID → `get_qid` paginated |
| ECHO `FacLong` absent from QID response | `connectors/echo.py` | Only `FacLat` available; facility map deferred |
| ECHO `CurrVioFlag`/`Over3yrsFormalActions` absent | `connectors/echo.py` | Use `FacSNCFlg` + `FacComplianceStatus` instead |
| ECHO bbox query → "Queryset Limit exceeded" for large metros | `connectors/echo.py` | Add `p_act=Y` (active facilities only) — reduces rows from 363k to ~50k |
| WQP `/data/` missing USGS post-2024-03-11 | `connectors/wqp.py` | Use `/wqx3/` beta |
| WQP `/wqx3/Result/search` 500 without profile | `connectors/wqp.py` | `dataProfile=basicPhysChem` |
| WQP `providers=NWIS,STORET` → zero rows | `connectors/wqp.py` | Repeat the param: `providers=NWIS&providers=STORET` |
| WQX 3.0 column renames | `connectors/wqp.py` | `Location_Identifier`, `Result_Characteristic`, `Result_Measure`, `Result_MeasureUnit` |
| USGS feature has no `site_name` | `connectors/usgs.py` | Fall back to `monitoring_location_id`; optional second hop to `/collections/monitoring-locations` |
| NSIDC CSV column contains commas | `connectors/nsidc.py` | Parse via `csv` module, not `.split(",")` |
| CtaG has no REST API | `connectors/noaa_ctag.py` | Pivot to NOAAGlobalTemp CDR v6.1 ASCII |
| `USW00012918` is Houston Hobby, not IAH | `data/cbsa_mapping.json` | Already corrected — watch for similar mislabels on other stations |
| Envirofacts `iaspub.epa.gov/enviro/efservice/` dead | `connectors/tri.py`, `ghgrp.py`, `sdwis.py` | Use `data.epa.gov/efservice/` only |
| Envirofacts mandatory pagination slug | `connectors/tri.py`, `ghgrp.py`, `sdwis.py` | Append `/rows/{first}:{last}/JSON` — required, not optional |
| Envirofacts latency non-linear | `connectors/sdwis.py` | Shard requests to ≤500 rows/slice, fan out with `asyncio.gather` |
| TRI `fac_latitude`/`fac_longitude` often garbage (0, null, DMS-packed) | `connectors/tri.py` | `_pick_coord()` walks candidate keys; rejects 0 and out-of-range floats |
| TRI has no annual release total column | `connectors/tri.py` | `total_release_lb` left `None` — `one_time_release_qty` is one-time-event, not annual aggregate |
| GHGRP emissions table not state-filterable | `connectors/ghgrp.py` | `pub_facts_sector_ghg_emission` has no state col; fetch year-windowed slice and aggregate by `facility_id` |
| SDWIS `violation/state_code/TX` returns wrong state silently | `connectors/sdwis.py` | Use joined path `water_system/state_code/{ST}/violation/...` |
| SDWIS `zip_code/BEGINNING/77/` is the correct metro-narrowing operator | `connectors/sdwis.py` | 500-row cap per prefix — fan out in parallel |
| SDWIS joined rows duplicate `(pwsid, violation_id)` | `connectors/sdwis.py` | De-dupe on `violation_id` during aggregation |
| Superfund FeatureServer returns polygons, not points | `connectors/superfund.py` | Compute centroid via simple vertex averaging; skip shapely |
| ArcGIS bbox query needs `inSR=4326` explicitly | `connectors/superfund.py`, `brownfields.py` | Omitting defaults to Web Mercator → empty for WGS84 envelopes |
| Brownfields `cleanup_status` not on spatial layer | `connectors/brownfields.py` | `EMEF/efpoints/MapServer/5` only has identification fields; cleanup status needs ACRES second-hop join |
| GFW world bbox → 504 timeout | `connectors/global_forest_watch.py` | Use regional bbox (CONUS) instead of world-spanning geometry |
| GFW v1.13 → 401 "restricted dataset or version" | `connectors/global_forest_watch.py` | Pin to v1.11; test before bumping version |
| GFW `Origin` header mandatory for key validation | `connectors/global_forest_watch.py` | Must send `Origin: https://terrasight.pages.dev` matching registered domain |
| GFW query requires `geometry` field (since ~2026-04) | `connectors/global_forest_watch.py` | Without geometry → 422 "Raster tile set queries require a geometry" |
| CRW ERDDAP host mismatch — **RESOLVED 2026-04-17** | `connectors/coral_reef_watch.py` | `pae-paha.pacioos.hawaii.edu` → HTTP 500 (dead). `coastwatch.pfeg.noaa.gov` has no DHW dataset. **Correct host: `oceanwatch.pifsc.noaa.gov`**, datasetID `CRW_dhw_v1_0`, variable `degree_heating_week`. Lon 0-360, no zlev dim. See `data/fixtures/crw-dhw/metadata.json`. |
| NESDIS `star.nesdis.noaa.gov` intermittent TCP refusal | `connectors/noaa_sea_level.py` | Connector handles gracefully but `/api/trends/sea-level` returns 502 during outages |
| RCRA BR_REPORTING state-only query → HTTP 500 on large states (TX, CA) | `connectors/rcra.py` | Always include `/report_cycle/{year}` filter (default 2023) — server-side timeout otherwise |
| RCRA BR_REPORTING has no lat/lon columns | `connectors/rcra.py` | Coordinates always None; geocoding via second table deferred |
| RCRA BR_REPORTING rows = per-waste-stream, not per-facility | `connectors/rcra.py` | Single `handler_id` can have many rows; aggregation is caller's responsibility |
| RCRA `report_cycle` not `year` | `connectors/rcra.py` | Biennial year column is `report_cycle`, not `year`; filter URL uses `/report_cycle/{N}` |
| PFAS FeatureServer layer 0 does not exist (400) | `connectors/pfas.py` | Default to layer 1 (`PAT_Unregulated_Contaminant_Monitoring`); layer 0 returns 400 Bad Request |
| PFAS State field has leading space | `connectors/pfas.py` | `" TX"` — must `.strip()` (handled by `_first_match`) |
| PFAS rows are per-sample, not per-site | `connectors/pfas.py` | Same `F_PWS_ID` appears for each contaminant/date; de-duplication is caller's responsibility |
| ArcGIS bbox query needs `inSR=4326` explicitly | `connectors/pfas.py` | Same landmine as Superfund/Brownfields — omitting defaults to Web Mercator |
| NWS API requires `User-Agent` header | `connectors/nws_alerts.py` | Without UA, api.weather.gov returns HTTP 403; use descriptive UA string |
| NWS alerts are national, not metro-scoped | `api/reports.py` | `_run_nws_alerts()` fetches all alerts and filters by `area_desc` containing state or core city name; no bbox/zone param used |
| USDM requires `Accept: application/json` header | `connectors/usdm.py` | Without it, API returns text/csv with empty body → JSON parse error |
| USDM uses separate endpoints for national vs state | `connectors/usdm.py` | `USStatistics` for `aoi=US`, `StateStatistics` for state FIPS codes |
| USDM field names are camelCase, not PascalCase | `connectors/usdm.py` | `mapDate`, `none`, `d0` (not `MapDate`, `None`, `D0` as some docs suggest) |
| OpenFEMA `state` field requires 2-letter abbreviation | `connectors/openfema.py` | Full state names (e.g. `Texas`) return 0 results; use `TX` |
| CO-OPS mdapi stations with lat=0/lng=0 | `connectors/coops.py` | Filter out bogus coordinates; some stations are decommissioned |
| CO-OPS datagetter `v` field is string | `connectors/coops.py` | Water level value returned as string `"1.234"`, not float; empty string = missing data |
| Open-Meteo Marine land points return null | `connectors/open_meteo_marine.py` | Grid covers all lon/lat; land points have null velocity/direction — must filter |
| Open-Meteo Marine direction is "going to" | `connectors/open_meteo_marine.py` | Oceanographic convention (not meteorological "coming from"); frontend should not flip |
| ERDDAP griddap lon 0-360 convention (OISST + CRW) | `connectors/oisst.py`, `connectors/coral_reef_watch.py` | Both `ncdcOisst21NrtAgg` and `CRW_dhw_v1_0` use 0-360 lon. Convert user lon: `lon_erddap = lon_user < 0 ? lon_user + 360 : lon_user`. Using raw negative lon returns HTTP 404. |
| OISST land/near-coast cells return JSON `null` | `connectors/oisst.py`, Worker `/api/sst-point` | Coastal clicks will snap to nearest 0.25° cell but may still hit null if land-masked. Worker must check for null SST and return `{ status: "no_data", reason: "land_or_ice" }` — not an error. |
| OISST griddap requires `zlev=(0.0)` in every point query | `connectors/oisst.py` | Omitting the zlev dimension from a 4-D griddap variable yields HTTP 400. Format: `sst[(last)][(0.0)][(lat)][(lon)]` |
| GIBS `VIIRS_SNPP_DayNightBand_ENCC` is FROZEN at 2023-07-07 | Globe imagery layers | Any current-date request returns HTTP 400. Use `VIIRS_SNPP_DayNightBand` (live 2012-01-19→present) or `VIIRS_NOAA20_DayNightBand`. Never use `_ENCC` in new code. |
| GIBS TileMatrixSet varies per layer (no global default) | Globe imagery | BlueMarble=`500m`/JPG, SST=`1km`/PNG, AOD=`2km`/PNG, Cloud=`2km`/PNG, Night Lights=`1km`/PNG. Hardcode per-layer in LayerManifest, never inherit a global default. |
| GIBS date format: `YYYY-MM-DD` only (no ISO datetime) | Globe imagery | `2026-04-17T00:00:00Z` yields HTTP 400. Use bare date. |
| GIBS static layers use literal `"default"` as date segment | Globe imagery | BlueMarble path: `…/default/default/500m/…`. Cesium `WebMapTileServiceImageryProvider` should have `clock` undefined for static layers. |
| CesiumJS 1.140 `WebMapTileServiceImageryProvider.fromUrl()` is async | Globe init | Prefer the sync constructor with `urlTemplate` (REST form) to bypass GetCapabilities fetch. `fromUrl()` requires `await`. |
| FIRMS invalid MAP_KEY returns HTTP 400 (not 401/403) | Worker `/api/fires` | Error handler must map 400 → `{ status: "not_configured" }`. |
| FIRMS global bbox fan-out = quota drain | Worker `/api/fires` | Single `-180,-90,180,90` call consumes 100+ transactions. Split into ~9 regional sub-bboxes or use `/country/` API for global coverage. |
| FIRMS CSV column drift — VIIRS vs MODIS | Worker `/api/fires` | VIIRS: `bright_ti4`/`bright_ti5`. MODIS: `brightness`/`bright_t31`. MVP uses VIIRS_SNPP_NRT only. |
| FIRMS `acq_time` needs zero-padding | Worker `/api/fires` | "130" must become "0130" before parsing into `HH:MM`. |
| USGS `properties.time` is Unix **milliseconds**, not seconds | Worker `/api/earthquakes` | `new Date(p.time)` works directly in JS — never divide by 1000. |
| USGS `properties.mag` can be null (quarry blasts, non-earthquakes) | Worker `/api/earthquakes` | Normalize as `p.mag ?? 0`; skip Globe rendering if null. |
| USGS `properties.tsunami` can be null | Worker `/api/earthquakes` | Always `p.tsunami ?? 0`. Show warning badge only when `=== 1`. |
| USGS `geometry.coordinates[2]` is depth km, positive-down | Worker `/api/earthquakes` | Label popup "Depth: X km" — never negate. Spec convention. |
| NOMADS GFS 10-day rolling window returns 404 | Phase 4+ GFS pipeline | URLs older than ~10 days 404 silently. Never hardcode dates; fall back to prior cycle on 404. |
| GFS `pgrb2.0p25.f000` full file = 477 MB | Phase 4+ GFS pipeline | Never download the full file. Use `filter_gfs_0p25.pl` with explicit `var_TMP=on&var_UGRD=on&…`; filtered 5-var payload ~4 MB. |
| GFS longitude range is 0–359.75° (not -180..180) | Phase 4+ GFS pipeline | Roll with `np.roll()` or `xr.assign_coords()` before plotting with cartopy, or tiles will be east-shifted by 180°. |
| `cfgrib` requires `libeccodes-dev` C library | Phase 4+ GFS pipeline | `apt-get install -y libeccodes-dev` in GH Actions job step. Import fails at runtime (not install time). |
| ADS vs CDS URLs are distinct in `~/.cdsapirc` | Phase 4+ CAMS/ERA5 | ADS = `https://ads.atmosphere.copernicus.eu/api`. CDS = `https://cds.climate.copernicus.eu/api`. Mixing them yields silent 403. Same `cdsapi` package, different server. |
| ERA5 `~/.cdsapirc` format changed 2024: single PAT, no `UID:API_KEY` colon | Phase 4+ ERA5 | Old `key: 12345:abc...` format silently 403s. Use single personal access token. |
| CAMS/ERA5 per-dataset ToU must be accepted in browser | Phase 4+ CAMS/ERA5 | `cdsapi` returns cryptic `Access restricted` with no explanation if ToU not accepted. Do this manually once per dataset. |
| CAMS PM2.5 = composite variable `particulate_matter_d_less_than_2p5_um` | Phase 4+ CAMS | Never manually sum organic + sulfate + BC + dust; use the pre-computed composite. `cfgrib` shortName is `pm2p5`. |
| ERA5 multi-month hourly requests trigger MARS tape retrieval (hours–days) | Phase 4+ ERA5 | Request one month at a time for monthly-means jobs. Always set `timeout=` in `cdsapi.Client()` to avoid a 6h runner hang. |
| `pipelines/contracts::Cadence` literal lacks `near-real-time` | `pipelines/connectors/gibs.py`, LayerManifest authoring | Encode NRT latency via `trustTag='near-real-time'` + a `caveats[]` entry — never try to stuff NRT into the `cadence` field (enum is `daily\|monthly\|3h\|5min\|static` only). |
| FIRMS VIIRS `confidence` column is string enum `n\|l\|h`, not numeric 0–100 like MODIS | `pipelines/connectors/firms.py`, Worker `/api/fires` | Map `n\|l\|h` → `nominal\|low\|high` for the human-readable `label`; keep the raw one-char code under `properties.confidence_raw`. |
| FIRMS empty/quiet feed = **header-only CSV** (not HTTP 204, not 404) | `pipelines/connectors/firms.py`, Worker `/api/fires` | Treat a header-only body as `status: 'ok'` with empty `data: []`. Do NOT retry — the feed really is empty for this window. |
| FIRMS `frp` column can be empty string on legacy MODIS rows | `pipelines/connectors/firms.py`, Worker `/api/fires` | Use a `_safe_float` helper that defaults to `0.0` on empty / non-numeric. Keep the row — the fire is still real even when FRP is missing. |
| FIRMS CSV cells have trailing whitespace (e.g. `satellite="N "`) | `pipelines/connectors/firms.py`, Worker `/api/fires` | Always `.strip()` string cells before downstream use. Applies to both Python and TS parsers. |
| USGS `properties.type` can be non-earthquake — quarry blast, rockburst, sonic boom | `pipelines/connectors/usgs.py`, Worker `/api/earthquakes` | The frozen EventPoint `type` stays `"earthquake"`; preserve the USGS value under `properties.event_type` so the UI can tag atypical events without breaking the contract. |
| Cloudflare `caches.default.match()` is **Request-keyed**, not string-keyed | Worker routes (`fires.ts`, `earthquakes.ts`, `sst-point.ts`) | A `caches.default.match('somekey')` string-miss compiles and silently never hits. Always build a `new Request(normalizedUrl, { method: 'GET' })`; fold the cache key into the URL's search string so identity is stable and inspectable. |

Any new landmine discovered during implementation must be added
**to this table and to the relevant connector docstring** before the
feature is marked done. The goal is zero re-learned lessons.

## Step 7 frontend landmines

| Landmine | Where | Fix |
|---|---|---|
| Rankings metric slug — underscore in schema vs hyphen in URL | `apps/web/src/components/reports/CityComparison.astro`, future `pages/rankings/*` | The `RankingMetric` enum in `@terrasight/schemas` uses underscore ids (`air_quality_pm25`). Step 8 ranking routes live at hyphenated paths (`/rankings/air-quality-pm25`). CityComparison.astro owns the translation via `SLUG_MAP`; Step 8 route filenames must match or links 404. |
| `related_cities` block data shape drift — `peer_slugs` vs `peers` | `apps/web/src/components/reports/RelatedCities.astro` | Step 5 composer emits `block.data.peer_slugs: string[]`. Spec'd shape is `block.data.peers: Array<{ slug, city, region, reason? }>`. Component accepts both; slug-only list is resolved via `reports-index.json` mirror. |
| Rankings JSON mirror — manual copy required | `apps/web/src/data/rankings/*.json` | Astro/Vite cannot reliably `import.meta.glob` across the workspace root, so rankings JSON is mirrored under `apps/web/src/data/rankings/`. Re-copy from `C:/0_project/terrasight/data/rankings/*.json` whenever the pipeline regenerates. Step 7 follow-up will automate via a build hook. |
| Astro `.astro` can't export TypeScript types | `apps/web/src/components/reports/AdSlot.types.ts` | Types referenced at build time across packages must live in sibling `.ts` files; `AdSlot.astro` imports `AdSlotName` from `./AdSlot.types`, barrel re-exports the type from the `.ts` file. |

## Step 10 QA landmines

| Landmine | Where | Fix |
|---|---|---|
| Footer links to non-existent guide slugs (`/guides/methodology`, `/guides/trust-legend`) | `apps/web/src/components/SiteFooter.astro` | Actual guide stubs ship as `how-to-read-a-report` and `what-is-a-trust-tag` (Step 8). Any component referencing guide routes must grep against `apps/web/src/pages/guides/*.astro`, not against the Step 8 IA doc draft names. Fixed 2026-04-18 — footer now points at the real stubs. |
| `grep -c '<loc>'` on Astro sitemap undercounts | QA verification | `@astrojs/sitemap` emits all `<loc>` tags on a single line, so `grep -c` (line count) returns 1 regardless of URL count. Always use `grep -oE '<loc>[^<]+</loc>' <file> \| wc -l` for the true count. Same trap applies to `data-ad-slot=` count in minified report HTML. |
| Peer-metro links 404 when pipeline ships < full CBSA set | `apps/web/src/components/reports/RelatedCities.astro`, `apps/web/src/components/reports/CityComparison.astro` | Step 5 composer resolves peer slugs from the full `data/cbsa_mapping.json` (50 CBSAs), but only 3 sample reports are built. Sidebar links to non-built peers 404. Filter `peer_slugs` at render time against `reports-index.json`, or post-filter in `build_reports.py`. Defer to Step 11 when full 50-CBSA set ships. |
| Home page canonical not emitted even when `PUBLIC_SITE_URL` set | `apps/web/src/pages/index.astro` | Home calls `<Layout title=... description=...>` without the `seo` prop, so `BaseLayout.astro` falls back to the minimal-OG path that skips canonical. Pass `seo={{ title, description, path: '/' }}` to route through `buildPageMeta()` and emit canonical when env var is set. |
| `wrangler dev` on Windows appears to "exit 0" via run_in_background but keeps listening | Step 10 QA protocol | `wrangler 3.114.17` detaches its server PID from the shell task, so the task notification may claim completion while the server is actually still up on `127.0.0.1:8787`. Always verify with `netstat -ano \| grep :8787` and kill the listener PIDs explicitly at teardown. |

