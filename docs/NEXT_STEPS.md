# TerraSight — Next Steps Plan

**Last updated:** 2026-04-14
**Companion to:** `progress.md` (backwards-looking reference) · this doc is
forwards-looking. `progress.md` logs what has been shipped; this file
plans what comes next.

---

## Executive summary

TerraSight's Phase 0 → C.3 are shipped: 3-tier funnel (Climate Trends
strip → Globe → Local Reports) is live, 50 metros, 5 trend cards, 13
Globe layers, Born-in interactive. The three biggest open questions
going into the next quarter are:

1. **Data depth** — the Atlas's 8 categories are unevenly populated.
   Waste & Materials has *zero* live datasets. Soil/Land has only
   forest cover. Water has surface samples but no drinking-water
   compliance. Fixing this is **Phase D**.
2. **Monetization** — AdSense application is gated on content, which
   is now sufficient. Custom domain + SEO polish are **Phase E**.
3. **Unblocking** — CMEMS SLA, CAMS smoke, TROPOMI CH₄, Deforestation
   and Drought Globe layers are all stuck on API migrations or
   package integrations. These are the **Blocker Cleanup** track.

This document is organised around those three tracks. Phase D is the
main body; Phase E and Blocker Cleanup are summarised near the end.

---

## Current coverage audit — 8 atlas categories vs existing connectors

Mapping the 24 live connector files in `backend/connectors/` to the
8 Atlas categories. `✅ live` means the connector currently returns
real data in production. `🔑 key` means a free API key is wired.
`⏸ P1` means a known blocker exists (see `progress.md` §C.2 and
"P1 보류 항목").

| # | Category | Live connectors | Gap severity |
|---|----------|-----------------|--------------|
| 1 | Air & Atmosphere | `airnow` ✅🔑, `openaq` ✅🔑, `noaa_gml` (CO₂) ✅, `noaa_gml_ch4` ✅, `climate_trace` ✅, `cams` ⏸ | **medium** — has trends + point monitors but no regulatory TMS / facility-level emissions / HAPs |
| 2 | Water Quality, Drinking Water & Wastewater | `wqp` ✅ (surface samples only) | **HIGH** — SDWIS drinking water compliance totally missing, no groundwater dedicated endpoint, no NPS |
| 3 | Hydrology & Floods | `usgs` ✅, `jrc_drought` ✅, `gibs` (flood layer) ✅ | **low** — core coverage OK; groundwater is technically hydrology too |
| 4 | Coast & Ocean | `oisst` ✅, `coral_reef_watch` ✅, `nsidc` ✅, `ibtracs` ✅, `noaa_sea_level` ✅, `cmems` ⏸ | **low** — rich; only SLA blocked |
| 5 | Soil, Land & Site Condition | `global_forest_watch` 🔑 (tree cover only) | **HIGH** — no Superfund, no Brownfields, no UST, no soil data |
| 6 | Waste & Materials | — | **CRITICAL** — zero connectors |
| 7 | Emissions, Energy & Facilities | `echo` ✅ (compliance only), `climate_trace` ✅ (country-level GHG) | **HIGH** — no GHGRP/FLIGHT facility-level, no CAMPD CEMS, no EIA energy mix |
| 8 | Climate, Hazards & Exposure | `firms` ✅🔑, `noaa_ctag` ✅, `climate_normals` ✅, `gibs` ✅ | **low** — core coverage OK |

**Summary:** categories 2, 5, 6, 7 are where Phase D must put its
energy. Environmental-engineering students expect Waste, Superfund
and facility-level emissions to be first-class citizens, and right
now they are either empty or hidden inside ECHO's compliance data.

---

## Phase D — 데이터 완전 확보

### D.0 Scope

Add data sources that close the four critical/high gaps above, with
preference for:

1. **Verified-live** free REST APIs (no paid tiers)
2. **US-first** (matches audience + Local Report funnel)
3. **Compliance or observed** trust tags (fits TerraSight's brand
   of explicit trust tagging)
4. Slots into at least one of: Local Report block / Atlas entry /
   Globe layer / Climate Trends card.

Connectors that would require research-grade bulk ingestion (no
public REST, only periodic static files) are deferred to Phase E
or later.

### D.1 Candidate data sources — spec cards

Each card uses the same template. API confirmation dates are
**2026-04-12** unless noted. Source URLs are the public docs that
back each claim.

---

#### D.1.1 — EPA TRI (Toxics Release Inventory)

- **API exists?** ✅ yes — confirmed live
- **Best endpoint:** `https://data.epa.gov/efservice/{table}/{col}/{op}/{val}/{first}:{last}/{format}`
  Useful tables: `tri.tri_facility`, `tri.tri_reporting_form`,
  `tri.tri_release_qty`, `tri.tri_transfer_qty`, `tri.tri_chem_info`
- **Auth:** none
- **Response format:** XML (default) / JSON / CSV / Excel (trailing path token)
- **Update cadence:** annual (reporting deadline July 1 prior year; National Analysis dataset ~October)
- **Geographic scope:** US facilities, lat/lon included
- **Trust tag:** `compliance` (self-reported under EPCRA §313)
- **Blockers:** paging is **mandatory** — large queries without `/1:N` slug time out. Self-reporting bias below thresholds. Some facilities mis-geocoded.
- **Recommended usage:** **Local Report Waste block** (top releasers in CBSA by chemical/medium) + **Atlas entry** + **Globe layer** (facility points at high zoom)
- **Effort:** trivial-to-moderate (REST is easy; table joins + multi-year de-dup is the work)
- **Priority:** **P0** — closes the "Waste & Materials" category single-handedly, drives SEO long-tail ("top polluters in Houston")
- **Docs:** https://www.epa.gov/enviro/envirofacts-data-service-api ·
  https://www.epa.gov/enviro/tri-overview

---

#### D.1.2 — EPA GHGRP / FLIGHT (facility-level GHG emissions)

- **API exists?** ✅ partial — FLIGHT is a web UI, but the underlying GHGRP tables are exposed via Envirofacts
- **Best endpoint:** `https://data.epa.gov/efservice/{TABLE}/ROWS/{first}:{last}/{format}` against GHGRP tables (e.g. `PUB_DIM_FACILITY`, `PUB_FACTS_SECTOR_GHG_EMISSION`). Browse names at `https://enviro.epa.gov/envirofacts/metadata/search/ghg`
- **Auth:** none
- **Response format:** XML default, JSON/CSV/Excel selectable
- **Update cadence:** annual (most recent reporting year 2023 as of pull)
- **Geographic scope:** US, facility-level (lat/lon, state, county)
- **Trust tag:** `compliance` (self-reported under GHGRP rule)
- **Blockers:** positional `ROWS/0:N` syntax (not query strings); efservice throttles large pages — chunk in 10k rows; uppercase program names safer.
- **Recommended usage:** **Local Report Emissions block** (top metro GHG emitters) + **Atlas entry** + optional **Globe layer** (facility points sized by tCO₂e)
- **Effort:** moderate (table discovery + paging + facility-dim × emissions-fact join)
- **Priority:** **P0** — natural pair with TRI; completes the "facilities" story the ECHO connector started but can't finish (ECHO reports compliance, not quantities)
- **Docs:** https://www.epa.gov/enviro/greenhouse-gas-restful-data-service

---

#### D.1.3 — EPA CAMPD (Clean Air Markets Power Sector CEMS)

- **API exists?** ✅ yes — confirmed live
- **Best endpoint:** `https://api.epa.gov/easey/` — service families:
  `/streaming-services/emissions/...` (quarterly CEMS: CO₂, SO₂, NOₓ, gross load, heat input)
  · `/camd-services/...` · `/facilities-mgmt/...` · `/emissions-mgmt/...`
  Bulk CSV/Parquet also at `https://campd.epa.gov/data/bulk-data-files`
- **Auth:** free api.data.gov key
- **Response format:** JSON REST (+ CSV/Parquet bulk)
- **Update cadence:** quarterly bulk uploads of hourly CEMS data (~45–60 day lag)
- **Geographic scope:** US regulated power sector (Acid Rain / CSAPR / MATS programs) — does NOT cover general manufacturing CEMS
- **Trust tag:** `compliance` (certified per 40 CFR Part 75 — arguably `observed_qc` for hourly values)
- **Blockers:** 1000 req/hr default, 500 rows/page, 15-min request timeout. Quarterly lag. Power-sector only.
- **Recommended usage:** **Local Report Emissions block** (top coal/gas plants in metro with hourly emissions trends) + **Atlas entry** + **Globe layer** (power plants)
- **Effort:** moderate (Swagger is documented but pagination + CBSA attribution is real work)
- **Priority:** **P1** (P0 if power-sector story is central) — highest-fidelity facility data in the entire EPA portfolio
- **Docs:** https://www.epa.gov/power-sector/cam-api-portal ·
  https://github.com/US-EPA-CAMD/easey-emissions-api

---

#### D.1.4 — EPA Superfund (SEMS / NPL)

- **API exists?** ✅ yes
- **Best endpoint (easy path):** ArcGIS FeatureServer
  `https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/FAC_Superfund_Site_Boundaries_EPA_Public/FeatureServer/0/query`
  (polygons) and `FRS_SEMS_NPL` variant (points). Standard `query?where=...&outFields=*&f=geojson`
- **Best endpoint (Envirofacts):** `https://data.epa.gov/efservice/sems.envirofacts_site/.../JSON`
  joined to `sems.envirofacts_contaminants` via `site_id/equals/fk_site_id`
- **Auth:** none
- **Response format:** GeoJSON (ArcGIS) / JSON / CSV / Parquet (Envirofacts)
- **Update cadence:** SEMS continuously, ArcGIS ~monthly, NPL semi-annual
- **Geographic scope:** US 50 states + territories
- **Trust tag:** `compliance`
- **Blockers:** Envirofacts host moved (`iaspub.epa.gov` → `data.epa.gov`); uppercase program names; must append `/rows/0:N/` and `/JSON`. Mandatory disclaimer "Data do not represent EPA's official position."
- **Recommended usage:** **Local Report Soil/Land block** ("Superfund sites in this CBSA" — count, NPL status, contaminants) + **Atlas entry** + optional **Globe layer** (low-zoom point cloud)
- **Effort:** trivial via ArcGIS FeatureServer; moderate via Envirofacts (contaminant joins)
- **Priority:** **P0** — completes Category 5
- **Docs:** https://www.epa.gov/enviro/sems-overview ·
  https://catalog.data.gov/dataset/epa-facility-registry-service-frs-sems_npl8

---

#### D.1.5 — EPA Brownfields (ACRES)

- **API exists?** ✅ partial — Envirofacts tables + ArcGIS feature layer
- **Best endpoint (easy path):** `https://geopub.epa.gov/arcgis/rest/services/EMEF/efpoints/MapServer/5`
  — Layer ID 5 is Brownfields, query returns GeoJSON with lat/lon + site metadata
- **Best endpoint (Envirofacts):** `https://data.epa.gov/efservice/acres.{table}/rows/0:N/JSON` via metadata browser at `https://enviro.epa.gov/enviro/ef_metadata_html.ef_metadata_table?p_topic=ACRES`
- **Auth:** none
- **Response format:** GeoJSON (ArcGIS) / JSON/CSV/XML/Parquet (Envirofacts)
- **Update cadence:** monthly-ish (grantees report into ACRES continuously)
- **Geographic scope:** US
- **Trust tag:** `compliance`
- **Blockers:** Envirofacts can return 500 on direct probes; ArcGIS route more reliable.
- **Recommended usage:** **Local Report Soil/Land block** ("Brownfields in this metro" with count + map markers) + **Atlas entry**
- **Effort:** trivial via ArcGIS; moderate via Envirofacts
- **Priority:** **P0** — pairs with Superfund to finish Category 5
- **Docs:** https://www.epa.gov/enviro/envirofacts-data-service-api ·
  https://catalog.data.gov/dataset/acres-brownfields-properties

---

#### D.1.6 — EPA SDWIS (Safe Drinking Water Information System)

- **API exists?** ✅ yes
- **Best endpoint:** Envirofacts efservice with SDWIS tables:
  - `https://data.epa.gov/efservice/VIOLATION/ROWS/0:1000/JSON`
  - `https://data.epa.gov/efservice/WATER_SYSTEM/STATE_CODE/{ST}/JSON`
  - Joined: `.../WATER_SYSTEM/STATE_CODE/{ST}/VIOLATION/JSON`
  - Bulk alt: `https://echo.epa.gov/tools/data-downloads/sdwa-download-summary`
- **Auth:** none
- **Response format:** XML default, JSON/CSV/Excel as path token
- **Update cadence:** quarterly (states report into SDWIS/FED on quarterly cycle)
- **Geographic scope:** US, Public Water System (PWS) level — service area is not a precise polygon
- **Trust tag:** `compliance`
- **Blockers:** positional `ROWS/` paging, 10k row page cap, joins are positional. **Critical disclaimer** — violations ≠ unsafe water at the tap. **PWSID-to-CBSA crosswalk is the hard part** — many systems cross county lines.
- **Recommended usage:** **Local Report Water block** (active drinking water violations + system count for metro) + **Atlas entry**
- **Effort:** moderate (crosswalk is the real work; raw API is easy)
- **Priority:** **P0** — WQP already covers surface water; SDWIS is the drinking-water half of Category 2 and it is currently empty
- **Docs:** https://www.epa.gov/enviro/sdwis-overview

---

#### D.1.7 — EIA Electricity Open Data (renewable generation mix)

- **API exists?** ✅ yes
- **Best endpoint:** `https://api.eia.gov/v2/electricity/electricity-power-operational-data/data/` with `frequency=monthly&data[0]=generation&facets[fueltypeid][]=SUN&facets[fueltypeid][]=WND&facets[fueltypeid][]=HYC&facets[fueltypeid][]=GEO&facets[fueltypeid][]=WWW&facets[location][]={STATE}`
- **Auth:** free key at `eia.gov/opendata`
- **Response format:** JSON (XML also available)
- **Update cadence:** monthly (~2 month lag) + annual
- **Geographic scope:** US national / state / sector
- **Trust tag:** `observed_qc` (utility-reported, EIA-validated)
- **Blockers:** ~5000 rows/response, ~5000 req/hour soft cap. v2 facet hierarchy is confusing — use `eia.gov/opendata/browser/` dashboard to discover facets.
- **Recommended usage:** **New Climate Trends card** ("US renewables share") + **Local Report Emissions block** (state-level renewable mix panel) + **Atlas entry**
- **Effort:** trivial-to-moderate
- **Priority:** **P0** — first additional Climate Trends card in 6 months; SEO lift ("renewable energy by state")
- **Docs:** https://www.eia.gov/opendata/documentation.php

---

#### D.1.8 — EPA ATTAINS (impaired waters / nonpoint sources)

- **API exists?** ✅ yes
- **Best endpoint:** `https://attains.epa.gov/attains-public/api/` with `/assessmentUnits`, `/assessments`, `/actions`, `/huc12summary`, `/sources`, `/domains`, `/parameters`
- **Bulk alt:** `https://owapps.epa.gov/expertquery/api-documentation` — same data, JSON/CSV/XLSX/Parquet
- **Auth:** none
- **Response format:** JSON
- **Update cadence:** continuous (states), biennial Integrated Reports
- **Geographic scope:** US + tribes
- **Trust tag:** `compliance` (impaired waters list is regulatory)
- **Blockers:** slow on multi-state queries — page by `assessmentUnitIdentifier` or HUC. "Source of impairment" taxonomy is free-text at state level — must map via the `/domains` endpoint to attribute to nonpoint vs point source.
- **Recommended usage:** **Local Report Water block** (impaired waters list + NPS vs point source breakdown by HUC12 for the metro) + **Atlas entry**
- **Effort:** moderate (schema is verbose but stable)
- **Priority:** **P1** — complements SDWIS (SDWIS = compliance, ATTAINS = ambient water quality)
- **Docs:** https://www.epa.gov/waterdata/how-access-and-use-attains-web-services

---

#### D.1.9 — USGS Groundwater (extension of existing `usgs.py`)

- **API exists?** ✅ yes
- **Best endpoint:** `https://api.waterdata.usgs.gov/ogcapi/v0/collections/field-measurements/items` and `/collections/daily/items` with `site_type_code=GW`. Legacy `/nwis/gwlevels` being decommissioned Nov 2025 — must migrate.
- **Auth:** none (optional key for higher rate limits)
- **Response format:** GeoJSON / JSON
- **Update cadence:** daily to near-real-time
- **Geographic scope:** US
- **Trust tag:** `observed_qc`
- **Blockers:** `/nwis/gwlevels` sunset is the main migration pressure; groundwater sites must be filtered via `site_type_code=GW`.
- **Recommended usage:** **Atlas entry** + **Local Report Hydrology block** (groundwater levels adjacent to surface streamflow)
- **Effort:** moderate (extends `usgs.py`; mostly adds a `siteType=GW` switch and the field-measurements collection)
- **Priority:** **P1** — Water category second-half
- **Docs:** https://api.waterdata.usgs.gov/docs/ogcapi/

---

#### D.1.10 — GBIF (Global Biodiversity)

- **API exists?** ✅ yes
- **Best endpoint:** `https://api.gbif.org/v1/occurrence/search?taxonKey={k}&country={iso}&hasCoordinate=true&hasGeospatialIssue=false` and density tiles at `https://api.gbif.org/v2/map/occurrence/density/{z}/{x}/{y}@1x.png?...`
- **Auth:** none for read
- **Response format:** JSON (search), PNG / vector tiles (density)
- **Update cadence:** continuous (millions of occurrences/month)
- **Geographic scope:** global, point-level
- **Trust tag:** `observed` (citizen science + museum records; quality varies by dataset)
- **Blockers:** search API caps offset+limit at 100k — use async download for bulk. Must filter `hasGeospatialIssue=false`.
- **Recommended usage:** **Globe layer** (density tiles under a new "Biodiversity" category in the accordion) + **Atlas entry**
- **Effort:** trivial for tiles, moderate for filtered search
- **Priority:** **P1** — gives Terrasight its first biodiversity datapoint; pairs well with existing Coral Reef Watch ocean story
- **Docs:** https://techdocs.gbif.org/en/openapi/v1/occurrence · https://techdocs.gbif.org/en/openapi/v1/maps

---

#### D.1.11 — NASA GIBS VIIRS DNB (light pollution)

- **API exists?** ✅ yes
- **Best endpoint:** `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_DayNightBand_ENCC/default/{Time}/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png`
- **Alt (calibrated):** EOG monthly composites `https://eogdata.mines.edu/products/vnl/` (GeoTIFF)
- **Auth:** none (GIBS)
- **Response format:** PNG/JPEG tiles
- **Update cadence:** daily
- **Geographic scope:** global
- **Trust tag:** `observed`
- **Blockers:** Raw ENCC is "nighttime imagery", not calibrated radiance — acceptable for visualization but NOT for quantitative metrics (for that, ingest EOG VNL composites).
- **Recommended usage:** **Globe layer** (under new Atmosphere → Night Lights sub-layer or new "Human Footprint" category)
- **Effort:** trivial (drop-in under existing `gibs.py` catalog)
- **Priority:** **P1** — low-effort, high-impact visual
- **Docs:** https://www.earthdata.nasa.gov/news/blog/announcing-viirs-nighttime-imagery-day-night-band

---

#### D.1.12 — NRC Power Reactor Status (US nuclear)

- **API exists?** ✅ partial — no JSON REST but a reliable pipe-delimited file
- **Best endpoint:** `https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/PowerReactorStatusForLast365Days.txt` (pipe-delimited, daily power-level % for every operating US reactor)
- **Alt:** NRC datasets hub `https://www.nrc.gov/reading-rm/doc-collections/datasets/index`
- **Auth:** none
- **Response format:** pipe-delimited text
- **Update cadence:** daily
- **Geographic scope:** US
- **Trust tag:** `compliance` (metadata) / `observed` (daily power levels)
- **Blockers:** no REST, must parse text. Decommissioned plants drop out.
- **Recommended usage:** **Atlas entry** + **Local Report Waste block** (nearest reactor + 365-day operating record) + **Globe layer** (reactor points colored by current status)
- **Effort:** moderate (text parser + daily refresh + facility geocoding)
- **Priority:** **P2** — novel but narrow coverage
- **Docs:** https://www.nrc.gov/data/index

---

#### D.1.13 — UST Finder (Leaking Underground Storage Tanks)

- **API exists?** ✅ yes (ArcGIS feature service; snapshot data)
- **Best endpoint:** ArcGIS Online item `88d551abd342485582c5ca4aac6ac0d6` — resolved FeatureServer exposes facilities, tanks, confirmed releases
- **Auth:** none
- **Response format:** JSON / GeoJSON
- **Update cadence:** snapshot (2018–2021 vintage; refresh cadence unclear 2026)
- **Geographic scope:** US
- **Trust tag:** `compliance`
- **Blockers:** **snapshot, not live** — cannot be marketed as current; refresh cadence uncertain.
- **Recommended usage:** **Atlas entry** only (honest about snapshot) + **Local Report Soil/Land block** (LUST counts)
- **Effort:** trivial
- **Priority:** **P2** — nice to have, but must warn about staleness
- **Docs:** https://www.epa.gov/ust/ust-finder

---

### D.2 Not viable — honest rejections

Sources explicitly investigated and rejected. Keep this list so we
don't re-waste cycles researching them.

| Dataset | Reason rejected | What to do instead |
|---------|-----------------|-------------------|
| **Indoor Air Quality (IAQ)** | No federal API. EPA explicitly states no nationwide IAQ monitoring network exists. PurpleAir has a paid points system after the 1M free trial (~30 days). Indoor sensors are a small fraction of PurpleAir network and not validated for indoor use. | Atlas placeholder card that honestly explains the gap and links to EPA IAQ page. **Do NOT ship as a connector.** |
| **Medical Waste** | No federal aggregator — authority lapsed when the Medical Waste Tracking Act of 1988 expired in 1991. State regulators publish PDFs only. EPA I-WASTE DST has a developers page but no reachable REST endpoints. | Atlas explainer card that points at state regulators. |
| **AirToxScreen / NATA (HAPs)** | Download-only. Excel/MDB/CSV bulk files released on a ~4-year lag (2020 data released May 2024). No API. | Defer to P2 as a bulk ingest pipeline if EJ/toxics story becomes central. |
| **IUCN Red List** | **Commercial use prohibited** in v4 license. Free key but manual approval. Incompatible with an AdSense-funded site unless we buy an IBAT license. | Use **GBIF** for biodiversity instead (which has open licensing). |
| **Desalination plants (global)** | No free live API. DesalData is a paid subscription. EMODnet covers EU only. Academic datasets (Jones 2019, Ai 2022) are static CSV snapshots. | Static CSV import for Atlas only, if the story matters. Not a connector. |
| **EJScreen** | EPA removed the tool from its website on **2025-02-05**. Only community-mirrored data (PEDP, `pedp-ejscreen.azurewebsites.net` and `screening-tools.com/epa-ejscreen`) exists, as static bulk files. Sustainability uncertain. | Defer to P2 as a bulk-import → Postgres query path; flag explicitly as "via PEDP mirror, EPA discontinued". Politically sensitive — think twice. |
| **Noise pollution (FAA / NPS)** | FAA ATADS has no REST (web form only). NPS Natural Sounds has no public API. | Use BTS ArcGIS noise map (biennial raster) as Atlas-only add-on. Not a connector priority. |
| **Soil contamination monitoring (federal live)** | No federal dataset distinct from Superfund. USDA NRCS SDA covers soil *properties*, not contaminants. | Use SEMS contaminant data from Superfund card D.1.4 instead. |

---

### D.3 Prioritised roadmap

Ordered by funnel-impact × effort × risk.

#### P0 — "Close the critical gaps" ✅ DONE (Phase D.1 + Phase E)

All five shipped. Plus RCRA (Phase F.0). TRI · GHGRP · Superfund ·
Brownfields · SDWIS live with 10-block Local Reports and 6 ranking
pages. See `progress.md` for the full post-E status.

| # | Connector | Status |
|---|-----------|--------|
| 1 | `tri.py` | ✅ live |
| 2 | `superfund.py` | ✅ live |
| 3 | `brownfields.py` | ✅ live |
| 4 | `sdwis.py` | ✅ live |
| 5 | `ghgrp.py` | ✅ live |
| 6 | `rcra.py` (added F.0) | ✅ live |

#### NEW P0 — Verified candidates from 2026-04-12 audit

All probe-verified with live HTTP 200 responses. These fill the
highest-impact gaps remaining after Phase D.1 + E.

| # | Connector | Source | Fills gap | Effort | Slot |
|---|-----------|--------|-----------|--------|------|
| A | `usgs_earthquake.py` | USGS FDSNWS ComCat | Cat 8 Hazards — **zero seismic coverage** | trivial | Globe event layer + LR Hazards block + Atlas |
| B | `noaa_coops.py` | NOAA CO-OPS Tides & Currents | Cat 4 Coast — **zero in-situ coastal obs** | trivial | LR Coast block + Globe + Atlas |
| C | `nws_alerts.py` | NWS api.weather.gov | Cat 8 Hazards — **new Trends card** + Globe event polygons | trivial→mod | Trends card + LR Hazards + Globe |
| D | `epa_pfas.py` | EPA PFAS Analytic Tools (ArcGIS FS) | Cat 1/2/5/6/7 **cross-cutting — zero PFAS** | moderate | LR Water+Waste + Atlas + Globe |
| E | `usdm.py` | US Drought Monitor (UNL) | Cat 3/8 — **new Trends card** "% CONUS in drought" + replaces blocked JRC | trivial | Trends card + LR Hydrology + Globe + Atlas |
| F | `fema_disasters.py` | OpenFEMA Disaster Declarations | Cat 8 — historical disaster timeline | trivial | LR Hazards + Atlas + Rankings |

**API details:**
- **USGS Earthquake:** `earthquake.usgs.gov/fdsnws/event/1/query?format=geojson` — no auth, real-time, GeoJSON
- **NOAA CO-OPS:** `api.tidesandcurrents.noaa.gov/api/prod/datagetter` — no auth, 6-min cadence, ~200 US stations
- **NWS Alerts:** `api.weather.gov/alerts/active` — no auth, requires `User-Agent` header, real-time GeoJSON-LD
- **EPA PFAS:** ArcGIS FeatureServer `services.arcgis.com/cJ9YHowT8TU7DUyn/.../PFAS_Analytic_Tools_Layers/FeatureServer/` — no auth, quarterly, ~8 layers (UCMR5 drinking water, TRI PFAS, Superfund PFAS, DoD sites)
- **US Drought Monitor:** `usdmdataservices.unl.edu/api/{Scope}Statistics/GetDroughtSeverityStatisticsByAreaPercent` — no auth, weekly (Thursday), CSV/JSON
- **OpenFEMA:** `fema.gov/api/open/v2/DisasterDeclarationsSummaries` — no auth, OData, continuous

**⚠️ NREL host migration landmine (2026-04-30 deadline):**
`developer.nrel.gov` → `developer.nlr.gov`. Affects planned `eia_power.py`
(NSRDB solar), any AFDC (EV charging) connector, and any existing docs
referencing the old host. **Pin to new host in all new code.**

#### P1 — "Breadth and trends" (following sprint)

| # | Connector | Adds | Priority rationale |
|---|-----------|------|-------------------|
| 6 | `eia_power.py` | New Trends card ("US renewables share") + LR Energy block | First Trends card addition in months; fresh hook |
| 7 | `epa_campd.py` | LR Emissions block (hourly CEMS) + Globe facility layer | Highest-fidelity data in EPA; power-sector story |
| 8 | `epa_attains.py` | LR Water block (impaired waters + NPS) | Completes water triangle: WQP (samples) + SDWIS (compliance) + ATTAINS (ambient) |
| 9 | `usgs_gw.py` (extension) | LR Hydrology block groundwater; Atlas | Small effort, big coverage win |
| 10 | `gbif.py` | Globe biodiversity layer + Atlas | First-ever biodiversity signal |
| 11 | `gibs_viirs_dnb.py` (layer add) | Globe "Night Lights" layer | Trivial; visual novelty |
| 12 | `nrcs_sda.py` | USDA NRCS Soil Data Access (SSURGO) — soil properties per CBSA | Cat 5 actual soil data |
| 13 | `nlcd.py` | MRLC NLCD Geoserver WMS — US land cover classes | Globe layer + Cat 5 |
| 14 | `nrel_solar.py` | NREL NSRDB — solar resource potential | Cat 7 Energy; pairs with EIA | ⚠️ use `developer.nlr.gov` |
| 15 | `nrel_afdc.py` | NREL AFDC — EV charging stations | Cat 7 Energy; SEO "EV chargers in Houston" | ⚠️ use `developer.nlr.gov` |
| 16 | `cdc_epht.py` | CDC EPHT Tracking Network — heat ED visits, PFAS, lead | Cat 8 exposure bridge |

#### P2 — "Research-grade and specialty"

| # | Connector | Why P2 |
|---|-----------|--------|
| 17 | `nrc_reactors.py` | Niche audience; text parser |
| 18 | `epa_ust.py` (UST Finder) | Snapshot data, not live |
| 19 | `airtoxscreen_bulk.py` | No API; heavy bulk pipeline; 4-year lag |
| 20 | `ejscreen_pedp.py` | EPA-discontinued; politically sensitive |
| 21 | `inaturalist.py` | Overlaps GBIF; only for real-time biodiversity pings |
| 22 | `noaa_swpc.py` | Space weather — off-core |

---

### D.4 Per-connector implementation checklist

Before merging any Phase D connector, verify it meets TerraSight's
`CLAUDE.md` contract:

- [ ] `backend/connectors/<name>.py` inherits `BaseConnector`
- [ ] `normalize()` returns a typed `ConnectorResult` with `source`, `source_url`, `cadence`, `tag`, `spatial_scope`, `license`, `notes`
- [ ] Fetch logic has graceful degradation — missing keys / down endpoints return `status: not_configured` or `status: error`, never raise 5xx
- [ ] All URL quirks and landmines documented in the module docstring AND added to `docs/guardrails.md`'s landmine table
- [ ] Atlas catalog JSON (`atlas_catalog.json`) gets a new entry with trust tag, source, cadence, license, limitations
- [ ] If the connector feeds a Local Report block, update `docs/report-spec.md` with the new block spec and the mandatory disclaimer (e.g. SDWIS "compliance ≠ exposure")
- [ ] `progress.md` gets a new "Phase D.x — <connector>" section
- [ ] Frontend `useApi.ts` types updated; card/block renders with trust badge + source
- [ ] Bundle size guard: still under 600 KB gzipped (currently 599)

---

## Phase E — ✅ DONE (2026-04-12)

- ✅ 4 new Local Report blocks (6 → 10): TRI, Site Cleanup, GHGRP, SDWIS
- ✅ 4 new SEO ranking pages (2 → 6)
- ✅ Ranking.tsx refactored to generic via `:rankingSlug`
- ✅ Home quick links expanded (6 → 10)
- ✅ Atlas `api_endpoint` field added to 5 datasets
- ✅ Bundle code splitting: LocalReport lazy route (main chunk 598 KB gzipped)

## Globe-First Redesign — ✅ DONE (2026-04-14)

Globe is now the landing page (`/`). Home.tsx card grid deleted.
Transparent header on globe, opaque on other pages.
Fire density PNG + ocean stress PNG continuous surfaces.
Storm track PathLayer. Air quality switched to daily AOD.
GIBS opacity halved. Mobile responsive (icons-only pills <640px).
New backend dependencies: numpy, scipy, matplotlib, Pillow.

## Phase F — Monetization + Growth (next)

- **AdSense application** — 50 metros × 14 blocks = 700 data surfaces, 6 rankings + 4 guides + Atlas 8 categories × 23 datasets → content requirement exceeded. Apply now.
- **Custom domain** — Cloudflare Pages + Render both sides.
- **SEO guides** — `/guides/understanding-tri-reports`, `/guides/reading-ghgrp-data`, `/guides/superfund-basics`, `/guides/sdwis-violations-explained`
- **Story Panel preset expansion** — current count is 1; target 5–10.

## Blocker Cleanup

Items from `progress.md`'s "P1 보류 항목" table that should be
closed out rather than left in limbo:

| Blocker | Closeout plan |
|---------|---------------|
| **CMEMS SLA** (`cmems.py`) | Credentials fixed (2026-04-12). Still needs `copernicusmarine` package in `requirements.txt` (pinned) and `fetch()` rewrite using `copernicusmarine.open_dataset(...).subset()`. Activate Globe SLA layer toggle. |
| **CAMS smoke** | Copernicus ADS account: wait for manual approval; no code action required until approval lands. |
| **TROPOMI CH₄** | Not on GIBS. Alternative: Copernicus GES DISC Giovanni or Sentinel-5P L3 subset via `copernicusmarine`/Earth Engine. Defer until CMEMS is resolved (same auth stack). |
| **GFW Deforestation Globe** | GFW key re-issued (2026-04-12). Connector fixed: Origin header + geometry mandatory + pinned v1.11. Returns CONUS loss data (24 years). Globe layer still needs tile precomputation. |
| **Drought Globe layer** | JRC WMS is global only. **US Drought Monitor (USDM)** is now a verified NEW P0 candidate — weekly, free, CSV API, replaces JRC for US coverage. See D.3 NEW P0 table. |
| **EPA AQS** (10 req/min) | Low priority — AirNow already covers real-time; AQS is historical. Add as Atlas-only reference. |
| **Render cold start** | UptimeRobot free ping every 5 min is the $0 fix; alternatively $7/month Render paid tier. |

---

## Research notes — where each claim came from

All D.1 cards were verified on **2026-04-12** by three parallel
research passes on public API docs. Key sources:

- EPA Envirofacts — https://www.epa.gov/enviro/envirofacts-data-service-api
- EPA CAMPD portal — https://www.epa.gov/power-sector/cam-api-portal
- EPA ATTAINS — https://www.epa.gov/waterdata/how-access-and-use-attains-web-services
- EPA SEMS/Superfund — https://www.epa.gov/enviro/sems-overview
- EPA SDWIS — https://www.epa.gov/enviro/sdwis-overview
- EIA Open Data — https://www.eia.gov/opendata/documentation.php
- USGS Water Data OGC — https://api.waterdata.usgs.gov/docs/ogcapi/
- GBIF TechDocs — https://techdocs.gbif.org/en/openapi/v1/occurrence
- NASA GIBS VIIRS DNB — https://www.earthdata.nasa.gov/news/blog/announcing-viirs-nighttime-imagery-day-night-band
- NRC Reactor Status — https://www.nrc.gov/data/index
- EPA UST Finder — https://www.epa.gov/ust/ust-finder
- PurpleAir API — https://api.purpleair.com/ (IAQ rejection basis)
- IUCN Red List API — https://api.iucnredlist.org/help (commercial-use restriction)
- EJScreen removal — https://envirodatagov.org/epa-removes-ejscreen-from-its-website/
