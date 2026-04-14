# TerraSight — Progress Log

**최종 업데이트:** 2026-04-15 (Self-Rendering Pipeline Prototype: SST 완료)

---

## 라이브 URL

| 서비스 | URL |
|--------|-----|
| Frontend (Cloudflare Pages) | https://terrasight.pages.dev |
| Backend API (Render) | https://terrasight-api-o959.onrender.com |
| GitHub | https://github.com/humpie-0413/terrasight |

---

## 핵심 수치 (2026-04-12 기준)

| 항목 | 수치 |
|------|------|
| Git commits | **48+** (`48f0482` Phase D.1, Phase E commit pending push) |
| Backend connectors | **40개** (28 기존 + 5 D.1 + 1 RCRA + 6 D.2) |
| API endpoints | **43개** (+6 D.2: earthquakes, alerts, drought, tides, declarations, pfas) |
| Atlas 라이브 데이터셋 | **23개** (+6 D.2: earthquake, NWS, USDM, CO-OPS, OpenFEMA, PFAS) |
| Atlas 카테고리 | **8개** — Waste & Materials, Soil/Land 공백 해소 ✅ |
| Local Reports 블록 | **14개** (6→10→12→**14**: +Hazards & Disasters, +Coastal Conditions) |
| Frontend components / pages | **~36개** |
| Local Reports metros | **50개** ✅ (17개 해안 metro 플래그) |
| Globe 카테고리 | **8개** (7 기존 + SST self-rendered surface) |
| Climate Trends 카드 | **6개** (CO₂ · Temp · Sea Ice · CH₄ · Sea Level · **Drought**) |
| Born-in 인터랙티브 | ✅ **완성** (연도 입력 → 3지표 비교) |
| SEO 랭킹 페이지 | **6개** (+4 Phase E: TRI · GHG · Superfund · Drinking Water) |
| SEO 가이드 페이지 | **4개** |
| 번들 사이즈 (main chunk) | **56.64 KB gzipped** ✅ |
| 코드 스플리팅 | deck.gl vendor **232.44 KB** (lazy) + GlobeDeck 6.78 KB + LocalReport 6.57 KB + 11 route chunks |
| Globe 라이브러리 | **deck.gl v9.2.11** (react-globe.gl → deck.gl 마이그레이션 완료, three.js 제거) |
| 테마 | **다크 테마** (글래스모피즘 + 별 파티클 글로브 배경) |
| 배포 스택 | Cloudflare Pages + Render (Docker) |

### Phase D.1 임팩트 요약 (2026-04-12)

| 카테고리 | D.1 이전 | D.1 이후 |
|---------|---------|---------|
| Waste & Materials | 0 live (critical gap) | **1 live** (TRI) |
| Soil, Land & Site | 1 live (forest cover only) | **3 live** (+ Superfund, Brownfields) |
| Water (drinking) | WQP only (surface) | **2 live** (+ SDWIS compliance) |
| Emissions / Facilities | ECHO (compliance) + Climate TRACE (country) | **3 live** (+ GHGRP 시설 GHG) |

---

## Globe-First Redesign (2026-04-14)

### Phase 1: Globe = Landing Page ✅
- `/` now renders EarthNow (fullscreen globe, 100vh)
- `/earth-now` redirects to `/`
- `Home.tsx` deleted (card grid removed)
- Header: transparent floating overlay on globe page, opaque on others
- "Earth Now" nav item hidden when on globe (user is already there)
- Nav pills on globe page: glassmorphism pill style

### Phase 2: GIBS Fixes + Quick Wins ✅
- Air Quality default switched from GIBS PM2.5 (MERRA-2 monthly, 3mo stale) → GIBS AOD (MODIS Terra daily, 1-day lag)
- GIBS overlay opacity reduced 0.75 → 0.50 (BlueMarble visible beneath)
- CO₂ question reframed: "Where did OCO-2 measure CO₂ today?" + cadence note about nadir swath ~3-5% coverage
- Fire limit raised from 1500 → 5000 default

### Phase 3: Fire Density Surface ✅
- New `backend/utils/surface_renderer.py` — shared Gaussian KDE → equirectangular PNG renderer (numpy + scipy + matplotlib + Pillow)
- New endpoint `GET /api/earth-now/integrated/fires/density-png` — renders ALL 24h fires as density PNG (4320×2160), 15min cache
- Frontend GlobeView: `BitmapLayer` density surface + `ScatterplotLayer` overlay (top 5000 for hover)
- MapView: existing `HeatmapLayer` unchanged

### Phase 4: Ocean Continuous Surface ✅
- New endpoint `GET /api/earth-now/integrated/ocean/surface-png` — combines OISST (stride=5, ~7000pts) + Coral DHW into stress PNG (2160×1080), 6h cache
- Frontend: `BitmapLayer` ocean stress surface + sparse `ScatterplotLayer` (top 300 stressed cells) for hover tooltips

### Phase 5: Storm Tracks ✅
- Backend: storms API now exposes `track_points` array per storm (full IBTrACS track history)
- Frontend: `PathLayer` draws storm track lines colored by intensity + existing `ScatterplotLayer` for current positions

### Phase 6: Polish + Mobile ✅
- Mobile (<640px): LayerBar shows icons only (text labels hidden)
- Mobile (<640px): StoryPanel hidden
- Dependencies added: numpy, scipy, matplotlib, Pillow

---

## Self-Rendering Pipeline Prototype (2026-04-15)

### SST (Sea Surface Temperature) ✅
- New `render_gridded_surface_png()` in `surface_renderer.py` — handles pre-gridded data
  (NaN-aware, diverging colormap, land=transparent, weighted Gaussian gap-fill)
- New `surface_cache.py` — file-system PNG cache with TTL (/tmp/terrasight_cache/)
- New router `globe_surface.py` → `GET /api/globe/surface/sst.png`
- OISST stride=2 (~65K ocean cells) → 3600×1800 RGBA PNG, RdYlBu_r colormap, 6h cache
- New Globe category "Sea Surface Temp" (8th pill) — BitmapLayer, observed, daily
- Pipeline pattern: fetch → grid → smooth → colormap → PNG → cache → BitmapLayer
- Memory footprint ~80 MB peak at stride=2 (within Render 512 MB free tier)

---

## 완료 항목 전체 정리

### 0 — 스캐폴딩 (`a95ea56`)
- React + Vite + TypeScript 프런트 skeleton
- FastAPI 백엔드 skeleton (14 커넥터 stub, 5 API 라우터)
- 프로젝트 구조: `frontend/`, `backend/`, `data/`, `docs/`

---

### 1 — API Spike: 14개 소스 검증 (`7414e6b`, `ad3175b`)

| 소스 | 결과 | 주요 사항 |
|------|------|-----------|
| NOAA GML CO₂ | ✅ | 직접 파일, 인증 불필요 |
| NOAAGlobalTemp CDR | ✅ | CtaG 대체 (공개 API 없음) |
| NSIDC Sea Ice | ✅ | CSV, noaadata.apps.nsidc.org |
| NOAA OISST | ✅ | ERDDAP griddap |
| U.S. Climate Normals | ✅ | NCEI 1991-2020 per-station |
| AirNow | ✅ | 무료 키, 500 req/hr |
| OpenAQ v3 | ✅ | v3 키 필요 (`/v3/parameters/2/latest`) |
| NASA FIRMS | ✅ | 무료 MAP_KEY |
| NASA GIBS | ✅ | 공개 WMTS, 인증 불필요 |
| EPA ECHO | ✅ | echodata.epa.gov (ofmpub 차단됨) |
| USGS | ✅ | OGC API, api.waterdata.usgs.gov |
| WQP | ✅ | `/wqx3/` beta 필수 |
| EPA AQS | ⚠️ | 10 req/min — P1 |
| CAMS | ⚠️ | Copernicus 계정 필요 — P1 |

---

### 2 — Climate Trends Strip (`f69988b`, `ddf8735`)
- 팬아웃 `GET /api/trends` — 5개 커넥터 병렬, 한 개 실패해도 나머지 정상
- `TrendsStrip.tsx` — 5카드 horizontal scroll-snap carousel

| 카드 | 소스 | 최신값 |
|------|------|--------|
| CO₂ | NOAA GML Mauna Loa | 429.35 ppm (2026-02) |
| Global Temp Anomaly | NOAAGlobalTemp CDR v6.1 | +0.64 °C (2026-03) |
| Arctic Sea Ice | NSIDC G02135 v4.0, 5-day mean | 13.98 M km² (2026-04-09) |
| CH₄ | NOAA GML global monthly | live |
| Sea Level Rise | NOAA NESDIS GMSL `_free_all_66.csv` | live |

---

### 3 — Earth Now Globe — Phase 0 (`00a1ae1`, `0b85e37`)
초기 글로브: BlueMarble + Fires + Ocean Heat + Story Panel

---

### 4 — Local Reports (`e925798` ~ `0342dd9`)
**6블록 구조, 50개 CBSA metro 라이브**

| 블록 | 커넥터 | 비고 |
|------|--------|------|
| Block 1 현재 AQI | `airnow.py` | AirNow 실시간 |
| Block 2 기후 기준선 | `climate_normals.py` | NCEI 1991-2020 |
| Block 3 시설/규정 | `echo.py` | echodata.epa.gov Two-hop |
| Block 4 수문 | `usgs.py` | OGC API NRT |
| Block 4 수질 | `wqp.py` | `/wqx3/` beta |

- `GET /api/reports/` · `/api/reports/search?q=` · `/api/reports/{slug}`
- 50개 CBSA: Houston, LA, New York, Chicago, Dallas, Phoenix, Philadelphia, San Antonio, San Diego, San Jose + 40개 추가

**ECHO 랜드마인:**
- `ofmpub.epa.gov` → `echodata.epa.gov`
- Two-hop: `get_facilities` → QueryID → `get_qid`
- `p_act=Y` 필수 (대도시 bbox queryset 초과 방지)

---

### 5 — Atlas + Navigation (`02de1c2`)
- `atlas_catalog.json` — 8개 카테고리, 14개 live 데이터셋
- `/atlas` → `/atlas/:slug` → 카테고리 카드, trust badge, MetaLine
- `Header.tsx` — sticky + scrollTo() 앵커 + 모바일 햄버거

---

### 6 — SEO 콘텐츠 (`0342dd9`)
- `GET /api/rankings/epa-violations` — 50개 metro ECHO 병렬, 위반순 정렬
- `GET /api/rankings/pm25` — AirNow ZIP 기반, AQI 내림차순
- `/guides/how-to-read-aqi`
- `/guides/understanding-epa-compliance`
- `/guides/water-quality-samples`
- `/guides/climate-normals`

---

### 7 — 배포 + 인프라 (`8d03752`, `46d1c52`)
- `Dockerfile` — python:3.12-slim, 비루트 유저, `$PORT`
- `render.yaml` — Render blueprint (Docker, free plan)
- `frontend/public/_headers` — CF Pages 보안 헤더 + 정적 에셋 캐싱
- `frontend/public/_redirects` — SPA fallback
- **CORS 버그 수정:** pydantic-settings `list[str]` → `str` + `_parse_origins()`

---

### 8 — Metro 50개 + SEO 확장 (2026-04-11)
- `data/cbsa_mapping.json` 10 → 50개 CBSA
- 40개 추가: Atlanta, Austin, Baltimore, Boston, Denver, Miami, Seattle, Washington DC 등
- 홈 빠른 링크 6개 (랭킹 + 가이드)

---

### A — 글로벌 커넥터 14개 추가 (`a5e897d`, 2026-04-11)

**GIBS 레이어 카탈로그:**

| 레이어 | GIBS ID | 상태 |
|--------|---------|------|
| PM2.5 (MERRA-2) | `MERRA2_Total_Aerosol_Optical_Thickness_550nm_Scattering_Monthly` | ✅ |
| AOD (MODIS Terra) | `MODIS_Terra_Aerosol_Optical_Depth_3km` | ✅ |
| CO₂ Column (OCO-2) | `OCO2_CO2_Column_Daily` | ✅ |
| Flood Detection | `MODIS_Terra_Flood_3-Day` | ✅ |
| CH₄ (TROPOMI) | — | ❌ GIBS 미지원, P1 보류 |

**신규 커넥터 10개:**

| 커넥터 | 소스 | 인증 |
|--------|------|------|
| `noaa_gml_ch4.py` | NOAA GML CH₄ monthly | 없음 |
| `noaa_sea_level.py` | NOAA NESDIS GMSL | 없음 |
| `coral_reef_watch.py` | CRW ERDDAP DHW/BAA/SST | 없음 |
| `cmems.py` | Copernicus Marine SLA L4 NRT | CMEMS 계정 |
| `global_forest_watch.py` | Hansen UMD tree cover loss | GFW API key |
| `jrc_drought.py` | JRC EDO WMS (drought indices) | 없음 |
| `ibtracs.py` | NOAA IBTrACS active storms | 없음 |
| `climate_trace.py` | Climate TRACE v6 GHG | 없음 |
| `gibs.py` | GIBS WMTS layer catalog | 없음 |
| `airdata.py` | (stub) | — |

**랜드마인:**
- NOAA Sea Level: `_txj1j2_90.csv` → 사망 → `_free_all_66.csv`
- GFW: POST-only, 컬럼명 이중 언더스코어
- JRC: `edo.jrc.ec.europa.eu` → `drought.emergency.copernicus.eu` (2024-04-03)
- IBTrACS: `last3years` (소문자), 2-헤더 CSV
- Climate TRACE: `countries` 복수 파라미터, 단위 metric tons

---

### B — Globe Phase B: 13레이어 어코디언 + Trends 5카드 (2026-04-11)

**5-카테고리 어코디언 레이어 패널:**

| 카테고리 | 레이어 | 상태 |
|----------|--------|------|
| Atmosphere | PM2.5 MERRA-2, AOD MODIS, Air Monitors | ✅ |
| Fire & Land | Active Fires, Deforestation, Drought | Fires ✅, 나머지 P1 |
| Ocean | SST, Coral Bleaching, Sea Level Anomaly | SST·Coral ✅, SLA P1 |
| GHG | CO₂ OCO-2, CH₄ TROPOMI | OCO-2 ✅, CH₄ P1 |
| Hazards | Tropical Storms, Flood Detection | ✅ |

**GIBS 캔버스 컴포지트 (`useGibsTexture`):**
- WMS 투명 PNG → BlueMarble 오프스크린 합성 (globalAlpha=0.72)
- 날짜 자동: today → yesterday → day-2 → 이달 1일 → 지난달 1일

**새 earth-now 엔드포인트:**
- `GET /api/earth-now/storms` — IBTrACS 활성 열대폭풍
- `GET /api/earth-now/coral` — CRW 산호 표백 열 응력
- `GET /api/earth-now/sea-level-anomaly` — CMEMS SLA (pending)

---

### C.0 — 데이터 전수조사 (2026-04-11)

| 상태 | 개수 |
|------|------|
| ✅ 작동 (인증 불필요) | 18개 |
| 🔑 API 키 필요 (graceful degradation) | 6개 |
| ⏸ P1 보류 | 2개 |

- NOAA CtaG city API: 404 확인 → Climate Normals 영구 fallback
- TROPOMI CH₄: UI 텍스트 `"Satellite data coming soon"` 처리

---

### C.1 — API 키 등록 + OpenAQ 버그 수정 (2026-04-11)

**등록 완료:**

| 키 | 서비스 |
|----|--------|
| `AIRNOW_API_KEY` | AirNow |
| `FIRMS_MAP_KEY` | NASA FIRMS |
| `OPENAQ_API_KEY` | OpenAQ v3 |
| `CMEMS_USERNAME/PASSWORD` | Copernicus Marine |
| `GFW_API_KEY` | Global Forest Watch |

**OpenAQ v3 마이그레이션 수정 (`abbf159`):**
- 구 endpoint: `/v3/locations?parameters_id=2` → `latest: null` (데이터 없음)
- 신 endpoint: `/v3/parameters/2/latest` → **25,000개 실시간 PM2.5 스테이션**
- 결과: `count: 0` → **`count: 47`** (limit=100)

---

### C.2 — CMEMS Marine Data Store 마이그레이션 (2026-04-11, P1 보류)

**근본 원인:** `nrt.cmems-du.eu` 도메인 폐기 → 301Domains 파킹

**신규 인프라:**
- Auth: `auth.marine.copernicus.eu/realms/MIS` (Keycloak)
- 데이터: CloudFerro S3 ARCO Zarr (데이터 청크 auth 필요)
- 접근 패키지: `copernicusmarine` (P1)

**현재 상태:** `status: "pending"` — Globe SLA 레이어 토글 비활성, 마이그레이션 안내 메시지 표시

---

### D.1 — P0 커넥터 5개 — EPA 규제 + 사이트 (2026-04-12) ✅

`docs/NEXT_STEPS.md` Phase D P0 배치 완료. Waste, Soil/Land, 음용수,
시설 배출 네 개의 공백 카테고리를 한 번에 채움. 백엔드 전용 구현
(UI 연결은 Phase E). 세 개 sub-agent 병렬 분담.

**신규 커넥터 5개:**

| 커넥터 | 소스 | 엔드포인트 | 태그 |
|--------|------|------------|------|
| `tri.py` | EPA TRI | `data.epa.gov/efservice/tri_facility/...` | observed |
| `ghgrp.py` | EPA GHGRP (FLIGHT) | `data.epa.gov/efservice/pub_dim_facility/...` | observed |
| `superfund.py` | EPA SEMS / NPL | ArcGIS `FAC_Superfund_Site_Boundaries_EPA_Public` | observed |
| `brownfields.py` | EPA ACRES | ArcGIS `EMEF/efpoints/MapServer/5` | observed |
| `sdwis.py` | EPA SDWIS | `data.epa.gov/efservice/water_system/.../violation/...` | observed |

**신규 엔드포인트 5개 (모두 graceful degradation):**

- `GET /api/releases/tri?state=TX&year=&limit=`
- `GET /api/releases/ghgrp?state=TX&year=2023&limit=`
- `GET /api/sites/superfund?west=&south=&east=&north=&limit=`
- `GET /api/sites/brownfields?west=&south=&east=&north=&limit=`
- `GET /api/drinking-water/sdwis?state=TX&zip_prefix=770,771,...&limit=`

**Houston CBSA 스모크 테스트 결과 (FastAPI TestClient):**
```
TRI         HTTP 200  count=5  status=ok  (sample: HEP JAVELINA SMR LLC)
GHGRP       HTTP 200  count=5  status=ok  (sample: ISP TECHNOLOGIES TEXAS CITY PLANT, 35437.92 tCO₂e, 2023)
Superfund   HTTP 200  count=5  status=ok  (sample: SOUTH CAVALCADE STREET, NPL Final)
Brownfields HTTP 200  count=5  status=ok  (sample: 9929 HOMESTEAD ROAD, Houston)
SDWIS       HTTP 200  count=5  status=ok  (Houston 10개 ZIP 프리픽스 fan-out, 2908 systems + 3852 violations raw)
```

**새 랜드마인 (모두 `docs/guardrails.md` + 각 커넥터 docstring 기록):**

- Envirofacts 호스트 마이그레이션: `iaspub.epa.gov` 사망 → `data.epa.gov/efservice/` 만
- Envirofacts 필수 페이지네이션: `/rows/{a}:{b}/JSON` 슬러그 없으면 타임아웃
- Envirofacts 초당 응답 비선형: `rows/0:500` ≈ 10s vs `rows/0:1500` ≈ 80-95s → 병렬 샤딩 필수
- TRI `fac_latitude`/`fac_longitude` 대부분 쓰레기 (0, null, DMS-packed): `_pick_coord()` fallback
- TRI 연간 release 합계 컬럼 부재: `one_time_release_qty`는 일회성 이벤트 필드 (주의)
- GHGRP 배출 테이블 state 필터 불가: `facility_id` 기준 window aggregation
- SDWIS `violation/state_code/TX` 필터가 조용히 무시됨 → joined path `water_system/state_code/{ST}/violation/...` 필수
- SDWIS `zip_code/BEGINNING/77/` 연산자로 메트로 좁히기 (프리픽스당 500행 캡 → 병렬 fan-out)
- SDWIS joined 행 중복 `(pwsid, violation_id)` → `violation_id`로 중복 제거
- SDWIS 필수 공지: "위반 ≠ 수도꼭지 위험" (connector notes에 강제 포함)
- Superfund FeatureServer는 폴리곤 (점 아님) → centroid 평균 계산 (shapely 없이)
- ArcGIS bbox 쿼리 `inSR=4326` 필수 (누락 시 Web Mercator 기본값으로 빈 결과)
- Brownfields `cleanup_status`는 공간 레이어에 없음 → ACRES 별도 엔드포인트 필요 (P2)

**Atlas catalog (`frontend/src/data/atlas_catalog.json`) 업데이트:**
- `waste/tri`: `planned` → `live`
- `water/sdwis`: `planned` → `live`
- `soil-land`: 신규 `superfund`, `brownfields` 추가
- `emissions`: 신규 `ghgrp` 추가
- 총 라이브 데이터셋: 11 → **16**

---

### F.0 — 전수조사 + 커넥터 수리 + RCRA 추가 + 프로덕션 점검 (2026-04-12) ✅

27개 커넥터 전수 라이브 프로브 + 놓친 환경데이터 갭 리서치 실시.
프로덕션(Render) 전 경로 점검 실시.
3개 고장 커넥터 수리 + RCRA 신규 추가 + 15개 신규 후보 발굴.

**수리:**

| 커넥터 | 문제 | 해결 |
|--------|------|------|
| `coral_reef_watch.py` | coastwatch.pfeg → PacIOOS 302 리다이렉트, 멀티변수 쿼리 문법 불일치 → 500 | PacIOOS URL 직접 사용 + per-variable dimension constraints + stride 20 |
| `noaa_sea_level.py` | NESDIS 간헐 TCP 거부 → 502 | 3회 retry + 24h 파일 캐시 (stale-but-parseable) |
| `global_forest_watch.py` | API 키 만료 + Origin 헤더 필수 + geometry 필수 + v1.13 restricted | 키 재발급 + Origin 헤더 + CONUS bbox + v1.11 고정 + env 자동 로딩 |
| `cmems.py` | 비밀번호 `!@` 하나 더 붙어 있음 → invalid_grant | `.env` 수정 → 인증 복구 (데이터는 여전히 pending) |

**신규 RCRA 커넥터 (`backend/connectors/rcra.py`):**
- EPA RCRA Biennial Report (`data.epa.gov/efservice/BR_REPORTING`)
- 대형 위험폐기물 발생 시설 (2년마다 보고)
- `GET /api/releases/rcra?state=TX&limit=5` → HTTP 200, count=5
- Atlas catalog에 `rcra` 라이브 추가 → 총 17개 라이브 데이터셋
- 랜드마인 4개: state-only 쿼리 500 / lat/lon 없음 / per-waste-stream 행 / report_cycle 컬럼명

**전수조사 결과:**
- 🟢 LIVE: 24/28 (CRW·GFW 수리 후 23→24, +RCRA)
- 🟠 DEGRADED: 1 (noaa_sea_level — 간헐적, retry+cache 추가)
- 🔴 BROKEN: 0 (cmems 인증 복구, 데이터는 P1 pending)
- ⏸ P1 STUB: 2 (airdata, cams)
- 신규 P0 후보 6개: USGS Earthquake · NOAA CO-OPS · NWS Alerts · EPA PFAS · US Drought Monitor · OpenFEMA

**갭 리서치 — 검증된 신규 후보 15개:**
`docs/NEXT_STEPS.md` §D.3 "NEW P0" + P1/P2 테이블에 전체 기록.
주요 발견:
- **PFAS**: EPA PFAS Analytic Tools ArcGIS FeatureServer — 현재 0개 커버, 5개 카테고리 교차 (최대 SEO 잠재력)
- **USDM**: US Drought Monitor API — JRC 드로트 차단 대체 + 신규 Climate Trends 카드
- **NWS Alerts**: 실시간 기상 경보 → FIRMS 이후 두 번째 Globe 이벤트 레이어
- **NREL 호스트 이전**: `developer.nrel.gov` → `developer.nlr.gov` (2026-04-30 데드라인)

**프로덕션(Render) 전 경로 점검 (2026-04-12):**

| 카테고리 | 점검 대상 | 결과 |
|---------|----------|------|
| 홈 APIs (8개) | trends 5카드, fires, sst, air-monitors, coral, storms, story, born-in | ✅ 8/8 정상 (coral 수리 확인) |
| Local Reports (5 metros × 10블록) | Houston, New York, LA, Chicago, Miami | ✅ 9/10 ok, related=pending (설계상) |
| Rankings (6개) | epa-violations, pm25, tri, ghg, superfund, sdwis | ⚠️ **epa-violations 50/50 ERROR** (수정 완료 — UA 헤더 누락) |
| Atlas / 기타 (10+개) | categories, reports, search, layers, releases, sites, sdwis | ✅ 전부 정상 |

**ECHO 랭킹 수리 (blocking issue):**
- **원인**: echodata.epa.gov가 httpx 기본 User-Agent (`python-httpx/...`)를 "robotic query"로 차단
- **수정**: 서술적 UA 헤더 추가 (`TerraSight/1.0`) + 타임아웃 30→60s 증가
- curl은 기본 UA로 통과하므로 이전 테스트에서 발견 안 됨

**OpenAQ 이상치 수리 (cosmetic):**
- pm25=9999 sentinel 값 → `pm25 > 1000` 필터 추가

---

### E — Phase D.1 시각화 + Local Report 확장 (2026-04-12) ✅

`docs/NEXT_STEPS.md` §E 배치 완료. D.1에서 구현한 5개 커넥터를
Local Report UI + SEO 랭킹 페이지에 실제로 연결. 3라운드 sub-agent
병렬 분담 (backend reports · backend rankings · frontend blocks +
frontend rankings/home/atlas).

**E.1 Local Report 블록 4개 추가 (6 → 10 블록):**

| # | 블록 | 커넥터 | 주요 값 (Houston 예) |
|---|------|--------|---------------------|
| 7 | Toxic Releases | TRI | facility_count=100, top 5 facilities |
| 8 | Site Cleanup | Superfund + Brownfields | 23 Superfund + 100 Brownfields sites |
| 9 | Facility GHG | GHGRP | 100 facilities, 4,157,781 tCO₂e (2023) |
| 10 | Drinking Water | SDWIS | 200 systems, 3,486 violations, 91.5% rate |

- JSX 순서: Block0 → Block1 Air → ad-1 → Block2 Climate → Block3
  Facilities → ad-2 → **Block7 TRI → ad-3 → Block8 Cleanup → Block9
  GHG → ad-4 → Block10 SDWIS** → Block4 Water → Block5 Methodology
  → Block6 Related
- 각 블록에 `MetaLine` (cadence · trust badge · source)을 숫자보다
  먼저 렌더링 (`docs/guardrails.md` 규칙 준수)
- SDWIS 고가시성 disclaimer: `"⚠️ A regulatory violation does NOT
  necessarily mean your tap water is unsafe."` 경고색 박스
- Ad slot 2개 추가 (ad-3 / ad-4)
- `get_report()` asyncio.gather에 5개 새 커넥터 추가 — 기존 블록
  영향 없이 graceful degradation 유지
- `_key_signals()` 확장: "GHG facility total (tCO₂e)", "Superfund
  sites" 카드 (6개 total)

**E.2 SEO 랭킹 4개 추가 (2 → 6 페이지):**

| 엔드포인트 | 전략 | Top (스모크 테스트) |
|-----------|------|-------------------|
| `GET /api/rankings/tri-releases` | 주 단위 집계 (unique states 팬아웃), metro에 할당 | Houston (TX, 500 facilities) |
| `GET /api/rankings/ghg-emissions` | 주 단위 집계 | Chicago (IL, 317 facilities, 37.46M tCO₂e) |
| `GET /api/rankings/superfund` | metro bbox fan-out (50 parallel) | Philadelphia (165 sites, 127 NPL Final) |
| `GET /api/rankings/drinking-water-violations` | 주 단위 집계 | Seattle (500 systems, 501 violations) |

- `backend/api/rankings.py`: 신규 4개 엔드포인트 + `_unique_states_from_cbsas()`
  헬퍼 + per-state fetch helpers. TRI/GHGRP/SDWIS는 50 metro × 10
  zip prefix = 500 Envirofacts 요청 폭격을 피하기 위해 주 단위로
  1회 쿼리 후 해당 주의 모든 metro에 동일 값 부여 + note: `"State-level
  totals attributed to every metro in that state"`
- 기존 catch-all `@router.get("/{ranking_slug}")` stub을 파일 끝으로
  이동 (4개 신규 명명 라우트를 shadowing 방지)
- 스모크 테스트: 6개 랭킹 모두 HTTP 200, 50 rows × 4 엔드포인트 = 200
  ok rows (SDWIS만 state cap으로 500 systems plateau)

**E.3 프런트엔드 — Ranking 페이지 generic 리팩터:**

- `frontend/src/pages/Ranking.tsx`: hardcoded `/rankings/epa-violations`
  → `useParams<{rankingSlug}>()` + `useApi(\`/rankings/\${slug}\`)`
- `RANKING_COLUMNS: Record<string, ColumnSpec[]>` 맵으로 5개 slug별
  컬럼 스펙 정의 (column header + render fn + align)
  - `epa-violations` → Sampled, In Violation, Rate
  - `tri-releases` → TRI Facilities
  - `ghg-emissions` → Facilities, Total tCO₂e
  - `superfund` → Sites, NPL Final
  - `drinking-water-violations` → Systems, Violations, Rate
- Title/criterion/note/source/retrieved_date 모두 envelope에서 읽음
  (하드코딩 제거)
- `frontend/src/App.tsx`의 generic `/rankings/:rankingSlug` 라우트
  이미 존재 → 라우트 추가 불필요
- PM25Ranking은 전용 컴포넌트 유지

**E.4 코드 스플리팅 (600 KB 가드레일 유지):**

- **중대한 발견**: Phase E 시작 시점 baseline bundle이 이미 **600.07 KB**
  였음 (progress.md가 추정한 599 KB보다 약간 초과). 4개 블록 추가로
  601.37 KB → 600 KB 가드레일 돌파.
- **해결**: `frontend/src/App.tsx`에서 `LocalReport` 라우트를 `React.lazy`
  로 분리 → 메인 청크에서 ReportPage 전체가 async 청크로 이동
- 결과:
  - Main chunk: **598.13 KB gzipped** (2 KB 헤드룸)
  - Lazy `LocalReport-*.js`: 5.09 KB gzipped (첫 `/reports/:slug` 방문
    시에만 로드)
  - TypeScript strict, 0 errors
  - Home/Atlas/Guide/Ranking 라우트는 eager 유지 (Globe hero 포함)

**E.5 Home 퀵링크 확장 (6 → 10):**

- 기존: 2 ranking (epa-violations, pm25) + 4 guide
- 신규 4 ranking 링크 추가:
  - ♻️ TRI Toxics Releases Ranking (`/rankings/tri-releases`)
  - 🏭 Facility GHG Emissions Ranking (`/rankings/ghg-emissions`)
  - 🚨 Superfund Sites Ranking (`/rankings/superfund`)
  - 💧 Drinking Water Violations Ranking (`/rankings/drinking-water-violations`)

**E.6 Atlas catalog — `api_endpoint` 필드 추가:**

5개 D.1 데이터셋에 직접 API 경로 링크 추가:
- `tri` → `/api/releases/tri?state=TX&limit=100`
- `ghgrp` → `/api/releases/ghgrp?state=TX&year=2023&limit=100`
- `superfund` → `/api/sites/superfund?west=...&limit=100`
- `brownfields` → `/api/sites/brownfields?west=...&limit=100`
- `sdwis` → `/api/drinking-water/sdwis?state=TX&zip_prefix=770,...&limit=100`

**E.7 Houston End-to-End 스모크 테스트:**

```
REPORT: HTTP 200 — all 10 blocks ok (related=pending as designed)
  air_quality=ok   climate_locally=ok   facilities=ok
  toxic_releases=ok   site_cleanup=ok   facility_ghg=ok
  drinking_water=ok   water=ok   methodology=ok   related=pending
  key_signals: 6 cards

RANKINGS: HTTP 200 × 6
  epa-violations         rows=50 ok=25
  pm25                   rows=50 ok=49
  tri-releases           rows=50 ok=50
  ghg-emissions          rows=50 ok=50
  superfund              rows=50 ok=50
  drinking-water-violations  rows=50 ok=50
```

**Phase E 랜드마인:**

- SDWIS state cap (500 systems/state) → `drinking-water-violations`
  랭킹에서 대형 주가 plateau에 도달. 향후 per-prefix fan-out으로 해결
  가능하나 rate limit 리스크 증가
- Bundle baseline 측정 필수 — `progress.md` 추정치 (599 KB)와 실측치
  (600.07 KB)가 불일치. Phase F 이후에는 CI에서 bundle 측정 자동화 필요
- Vite의 단일 청크 기본값: 추가 route도 React.lazy로 쪼개야 확장 여유
  확보 (Atlas/Ranking/Guide 모두 잠재 후보)
- GHGRP 연간 CO₂e는 2023 고정 — 신 reporting year 출시 시 코드 변경
  필요
- Chicago가 GHG ranking 1위인 이유: IL의 GHGRP 시설 다수 + 주 단위
  집계로 모든 IL metro가 동일 값. 사용자에게 "state-level" 표시 필수

**Atlas 카테고리 임팩트 (최종):**

| 카테고리 | D.1 이전 | E 이후 |
|---------|---------|--------|
| Waste & Materials | 0 live | 1 live + Local Report Block 7 |
| Soil, Land & Site | 1 live | 3 live + Local Report Block 8 |
| Water (drinking) | WQP only | 2 live + Local Report Block 10 |
| Emissions / Facilities | ECHO + Climate TRACE | 3 live + Local Report Block 9 |

---

### C.3 — Born-in Interactive 완성 (`ca9e738`, 2026-04-12) ✅

**`GET /api/trends/born-in?year=YYYY`**

| 지표 | 소스 | "then" 계산 | Record start |
|------|------|------------|-------------|
| CO₂ | NOAA GML | 출생연도 연간 평균 | 1958 (clamped) |
| Temp Anomaly | NOAAGlobalTemp CDR | 출생연도 연간 평균 | 1850 |
| Arctic Sea Ice | NSIDC G02135 | 출생연도 9월 평균 | 1979 (clamped) |

**검증 (year=1990):**
```
CO₂:      354.45 ppm → 429.35 ppm  (+74.9 ppm, +21.1%)
Temp:      -0.19 °C  →   +0.64 °C  (+0.83 °C)
Sea Ice:   6.14 Mkm² →   4.75 Mkm² (-1.39 Mkm², -22.6%)
```

**Frontend:** 연도 입력 + Compare → 3개 카드 (then/now/delta, 색상 코딩)

---

### D.2 — P0 커넥터 6개 추가 (2026-04-12) ✅

`docs/NEXT_STEPS.md` §D.3 NEW P0 배치 완료. 전수조사에서 발굴한
6개 검증 후보를 백엔드 커넥터 + API 엔드포인트로 구현. 3개 sub-agent
병렬 분담. UI 없이 백엔드만 (시각화는 Phase G 이후).

**신규 커넥터 6개:**

| 커넥터 | 소스 | 태그 | 주기 | 카테고리 |
|--------|------|------|------|----------|
| `earthquake.py` | USGS FDSNWS ComCat | observed | NRT ~5min | Climate Hazards |
| `nws_alerts.py` | NWS Active Alerts | observed | NRT | Climate Hazards |
| `usdm.py` | US Drought Monitor (UNL) | observed | weekly (Thu) | Hydrology |
| `coops.py` | NOAA CO-OPS Tides | observed | 6-min | Coast & Ocean |
| `openfema.py` | OpenFEMA Disaster Declarations | observed | continuous | Climate Hazards |
| `pfas.py` | EPA PFAS Analytic Tools (ArcGIS) | observed | quarterly | Water (cross-cutting) |

**신규 엔드포인트 6개:**

- `GET /api/hazards/earthquakes?min_magnitude=4&limit=500&days=30`
- `GET /api/hazards/alerts?severity=`
- `GET /api/hazards/drought?aoi=US&weeks=4`
- `GET /api/coast/tides?west=&south=&east=&north=&limit=20`
- `GET /api/disasters/declarations?state=TX&years=5&limit=100`
- `GET /api/sites/pfas?west=&south=&east=&north=&limit=100`

**스모크 테스트 결과:**
```
Earthquake  count=5+  M4+ global 7일 — USGS GeoJSON
NWS Alerts  count=활성 경보 수 — severity/event/area
USDM        count=1+  D0~D4 % — camelCase 필드명 주의
CO-OPS      count=3+  Galveston 주변 수위/수온 — per-station parallel
OpenFEMA    count=5+  TX 최근 5년 재난 선언
PFAS        count=5+  Houston bbox UCMR5 레이어 1 — per-sample 행
```

**새 랜드마인 (모두 `docs/guardrails.md` + 각 커넥터 docstring 기록):**

- NWS: `User-Agent` 헤더 필수 (없으면 403)
- USDM: `Accept: application/json` 헤더 필수 (없으면 빈 CSV 반환)
- USDM: 국가 vs 주 별도 엔드포인트 (`USStatistics` vs `StateStatistics`)
- USDM: 필드명 camelCase (`mapDate`, `d0`, not `MapDate`, `D0`)
- OpenFEMA: `state` 필드 2글자 코드 (`TX`, not `Texas`)
- CO-OPS: mdapi 스테이션 lat=0/lng=0 보거스 데이터 필터 필요
- CO-OPS: datagetter `v` 값이 string (`"1.234"`, not float)
- PFAS: FeatureServer layer 0 → 400, layer 1 사용 (UCMR5)
- PFAS: State 필드 앞에 공백 (`" TX"` → strip 필요)
- PFAS: 행 = per-sample (같은 PWS가 contaminant마다 반복)

**Atlas catalog 업데이트:**
- `coast-ocean/noaa-coops`: `planned` → `live`
- `hydrology`: 신규 `usdm` 추가
- `water`: 신규 `pfas` 추가
- `climate-hazards`: 신규 `usgs-earthquake`, `nws-alerts`, `openfema` 추가
- 총 라이브 데이터셋: 17 → **23**

---

## 라이브 엔드포인트 상태 (2026-04-12)

| 엔드포인트 | 상태 |
|-----------|------|
| `GET /api/trends` | ✅ 5카드 모두 live |
| `GET /api/trends/born-in?year=` | ✅ live |
| `GET /api/earth-now/fires` | ✅ FIRMS live |
| `GET /api/earth-now/sst` | ✅ OISST live |
| `GET /api/earth-now/air-monitors` | ✅ OpenAQ ~25k PM2.5 |
| `GET /api/earth-now/storms` | ✅ IBTrACS live |
| `GET /api/earth-now/coral` | ✅ CRW live |
| `GET /api/earth-now/sea-level-anomaly` | ⏳ pending (CMEMS P1) |
| `GET /api/reports/{slug}` | ✅ 50개 metro live |
| `GET /api/rankings/epa-violations` | ✅ live |
| `GET /api/rankings/pm25` | ✅ live |
| `GET /api/layers/catalog` | ✅ GIBS 6 layers |
| `GET /api/releases/tri` | ✅ D.1 Envirofacts TRI |
| `GET /api/releases/ghgrp` | ✅ D.1 Envirofacts GHGRP/FLIGHT |
| `GET /api/sites/superfund` | ✅ D.1 ArcGIS NPL sites |
| `GET /api/sites/brownfields` | ✅ D.1 ArcGIS ACRES |
| `GET /api/drinking-water/sdwis` | ✅ D.1 Envirofacts SDWIS |
| `GET /api/rankings/tri-releases` | ✅ **E** state-level TRI |
| `GET /api/rankings/ghg-emissions` | ✅ **E** state-level GHGRP |
| `GET /api/rankings/superfund` | ✅ **E** per-metro bbox |
| `GET /api/rankings/drinking-water-violations` | ✅ **E** state-level SDWIS |
| `GET /api/releases/rcra` | ✅ Envirofacts BR_REPORTING |
| `GET /api/sites/pfas` | ✅ EPA PFAS Analytic Tools (UCMR5 Layer 1) |
| `GET /api/hazards/earthquakes` | ✅ **D.2** USGS FDSNWS ComCat |
| `GET /api/hazards/alerts` | ✅ **D.2** NWS Active Alerts |
| `GET /api/hazards/drought` | ✅ **D.2** US Drought Monitor |
| `GET /api/coast/tides` | ✅ **D.2** NOAA CO-OPS Tides |
| `GET /api/disasters/declarations` | ✅ **D.2** OpenFEMA |

---

## 알려진 랜드마인

| 소스 | 함정 | 해결책 |
|------|------|--------|
| EPA ECHO | `ofmpub.epa.gov` 차단 | `echodata.epa.gov` 사용 |
| EPA ECHO | 단일 요청으로 시설 목록 불가 | Two-hop: `get_facilities` → `get_qid` |
| EPA ECHO | 대도시 bbox queryset 초과 | `p_act=Y` 필수 |
| WQP | legacy `/data/` 2024-03-11 이후 데이터 없음 | `/wqx3/` beta 필수 |
| WQP | `providers=` comma-join → 0 rows | repeated params |
| pydantic-settings | `list[str]` plain URL 파싱 실패 | `str` 타입 + `_parse_origins()` |
| OpenAQ v3 | `/v3/locations` `latest: null` | `/v3/parameters/2/latest` 사용 |
| CMEMS | `nrt.cmems-du.eu` 폐기 | `copernicusmarine` 패키지 (P1) |
| NOAA Sea Level | `_txj1j2_90.csv` 사망 | `_free_all_66.csv` 사용 |
| GFW | GET → 405 | POST-only query |
| JRC Drought | `edo.jrc.ec.europa.eu` 이전 | `drought.emergency.copernicus.eu` |
| IBTrACS | `LAST3YR` → 404 | `last3years` (소문자) |
| RCRA BR_REPORTING | 대형 주(TX 등) state-only 쿼리 → HTTP 500 | 항상 `/report_cycle/{year}` 포함 (기본 2023) |
| RCRA BR_REPORTING | lat/lon 없음 | 좌표 항상 None, geocoding 별도 필요 |
| RCRA BR_REPORTING | 행 = waste stream (facility가 아님) | handler_id로 집계 필요 시 caller 책임 |
| PFAS FeatureServer layer 0 | 400 Bad Request 반환 | layer 1 (UCMR5) 사용 |
| PFAS State 필드 | 선행 공백 (" TX") | strip() 처리 |
| PFAS 행 = per-sample | 동일 PWS_ID가 오염물질/날짜별 반복 | caller가 de-dupe |
| NWS API | `User-Agent` 헤더 없으면 403 | 서술적 UA 헤더 필수 |
| USDM | `Accept: application/json` 없으면 빈 CSV | 헤더 추가 |
| USDM | 국가/주 엔드포인트 분리 | `USStatistics` vs `StateStatistics` |
| USDM | 필드명 camelCase | `mapDate`, `d0` (not `MapDate`, `D0`) |
| OpenFEMA | state 필드 2글자 | `TX` (not `Texas`) |
| CO-OPS | mdapi lat=0/lng=0 보거스 | 필터링 필요 |
| CO-OPS | datagetter `v` string | float 변환 필요 |

---

## P1 보류 항목

| 항목 | 이유 |
|------|------|
| CMEMS SLA Globe 레이어 | `copernicusmarine` 패키지 + 신규 인증 체계 |
| CAMS Smoke 레이어 | Copernicus ADS 계정 수동 승인 대기 |
| TROPOMI CH₄ 레이어 | GIBS 미지원 → Copernicus GES DISC 대안 |
| Deforestation Globe 레이어 | GFW 폴리곤 쿼리 구현 필요 |
| Drought Globe 레이어 | JRC WMS → 수치화 파이프라인 필요 |
| EPA AQS | 10 req/min, 별도 이메일 등록 |
| AdSense 신청 | 콘텐츠 충분 — 신청 가능 |
| 커스텀 도메인 | CF Pages + Render 양쪽 설정 |
| Render cold start | 15분 비활성 → 30초 지연 (UptimeRobot or $7/월) |

---

## 다음 단계 — Phase E 이후

Phase E 완료. Local Report가 10블록으로 확장되고 6개 랭킹 페이지가
라이브. 다음 단계는 크게 세 갈래. 자세한 로드맵은 `docs/NEXT_STEPS.md`.

### 옵션 0 — AdSense 신청 + 커스텀 도메인 (즉시)

- 50 metro × 10 블록 = 500개 데이터 surface, 6 ranking + 4 guide
  페이지, Atlas 8 카테고리 × 16 데이터셋 → **AdSense 콘텐츠 요건
  충족**. 지금 바로 신청 가능.
- 커스텀 도메인 (CF Pages + Render 양쪽 설정)도 같이 진행 가능.

### 옵션 A — Phase D.2: P1 커넥터 6개 (데이터 계속 심화)

`docs/NEXT_STEPS.md` §D.3 P1 배치. 모두 검증된 무료 API.

| 순서 | 커넥터 | 소스 | 기여 |
|-----|--------|------|------|
| 1 | `eia_power.py` | EIA v2 (`api.eia.gov/v2/electricity`) | **새 Climate Trends 카드** "US renewables share" |
| 2 | `epa_campd.py` | EPA CAMPD (`api.epa.gov/easey/`) | 시간별 CEMS, 최고 품질 발전소 배출 |
| 3 | `epa_attains.py` | EPA ATTAINS (`attains.epa.gov/attains-public/api/`) | 수질 오염원 (점/비점원 구분) |
| 4 | `usgs_gw.py` | USGS OGC (`/collections/field-measurements` + `site_type_code=GW`) | 지하수 — `usgs.py` 확장 |
| 5 | `gbif.py` | GBIF v1 (`api.gbif.org/v1`) | **Globe 생물다양성 레이어** (첫 생태 신호) |
| 6 | `gibs_viirs_dnb` | GIBS VIIRS Day/Night Band (`gibs.earthdata.nasa.gov/wmts/.../VIIRS_SNPP_DayNightBand_ENCC`) | **Globe 야간광 레이어** |

**장점:** 데이터 깊이 확대 지속, 환경공학 범위(생물다양성·에너지·지하수) 첫 진입
**단점:** UI 통합 안 하면 사용자에게 보이지 않음 (백엔드만 존재)

### 옵션 B — Phase F: SEO 가이드 + Story Panel 확장

Phase E로 데이터 depth는 채워졌고, 이제 트래픽 유입 경로 강화:

- 신규 가이드 페이지 4개:
  - `/guides/understanding-tri-reports` — TRI 읽는 법
  - `/guides/reading-ghgrp-data` — GHGRP CO₂e 해석
  - `/guides/superfund-basics` — NPL · SEMS 기초
  - `/guides/sdwis-violations-explained` — 위반 ≠ 수돗물 위험
- Story Panel 프리셋 1개 → 5-10개 (editorial seeding)
- 블로그/뉴스 섹션 추가로 long-tail SEO 보강

### 권장

**옵션 0 (AdSense/도메인) 먼저**, 그 다음 **옵션 B (Phase F)**,
옵션 A (D.2)는 마지막. 이유:

1. Phase E로 콘텐츠 weight가 체감상 ~2배 — AdSense 승인 확률 최상
2. 가이드 페이지는 랭킹 페이지의 "읽어볼 것" 자연 연결 (CTR 증폭)
3. D.2 커넥터는 UI 없으면 다시 "벤치 데이터"로 돌아갈 리스크 → E/F
   이후에 진입하는 것이 같은 실수 반복 방지

### Phase G 시각화 설계 (2026-04-12) ✅

`docs/ui-design.md` 작성 완료. 34개 커넥터 전부 시각화 유형 매핑.

**주요 결정:**
- Globe 레이어: 13 → **16** (+ Earthquake, NWS Alerts, PFAS Sites)
- Local Report 블록: 10 → **13+1** (+ PFAS, Active Alerts, Hazards & Disasters, Coastal Conditions 조건부)
- Trends 카드: 5 → **6** (+ USDM Drought %)
- 카테고리: 5 유지 (Hazards 2→5로 확장)

**Phase G 스프린트 계획:**
- G.1 Quick Wins: Trends drought 카드, Globe earthquake 레이어, LR NWS alerts 블록, LR PFAS 블록
- G.2 Moderate: LR Hazards/Disasters 블록, LR Coastal 블록, Globe NWS polygons
- G.3 Polish: PFAS globe 레이어, Atlas 데이터 탐색기, Leaflet 시설 맵

### G.1 — Quick Wins 4개 구현 (2026-04-12) ✅

**1. Trends: USDM Drought 카드 (5 → 6카드):**
- `backend/api/trends.py`: `_drought_payload()` 추가 — 52주 USDM 시계열
- 값: D1+D2+D3+D4 면적 % ("moderate drought or worse")
- 최신값: **94.3%** CONUS moderate drought or worse
- `TrendsStrip.tsx`: STATIC_META에 drought 추가, sparkColor `#92400e`

**2. Globe: Earthquake 레이어 (13 → 14레이어):**
- `Globe.tsx` Hazards 카테고리에 "Earthquakes (M4+)" 토글 추가
- pointsData 렌더링: magnitude → 크기/색상 (M4 노랑→M6 주황→M7+ 빨강)
- 호버: 규모, 위치, 깊이, UTC 시간, 쓰나미 경고

**3-4. Local Report 블록 2개 추가 (10 → 12 블록):**

**신규 블록 2개:**

| # | 블록 | 커넥터 | 주요 값 |
|---|------|--------|---------|
| 13 | Active Weather Alerts | NWS (`nws_alerts.py`) | alert_count, severity-coded cards, area_desc |
| 11 | PFAS Monitoring | EPA PFAS (`pfas.py`) | monitored_systems, unique_contaminants, top_detections |

**백엔드 변경 (`backend/api/reports.py`):**
- `_run_nws_alerts()`: NWS fetch + state/city area_desc 필터링
- `_run_pfas()`: bbox 기반 PFAS FeatureServer 쿼리
- `_build_active_alerts_block()`: 최대 20개 alerts, severity/event/area_desc
- `_build_pfas_block()`: unique systems, contaminant 집계, top 10 detections
- `asyncio.gather`에 2개 신규 태스크 추가 (기존 블록 영향 없음)
- Methodology sources에 NWS + PFAS 추가

**프런트엔드 변경:**
- `frontend/src/types/report.ts`: `ActiveAlertsBlock`, `PfasBlock` 타입 추가
- `frontend/src/components/local-reports/ReportPage.tsx`:
  - `Block13ActiveAlerts`: severity 색상 코딩 (Extreme → red, Severe → red,
    Moderate → amber, Minor → blue), 0 alerts → "No active alerts" 메시지
  - `Block11Pfas`: 4-stat grid + top detections 테이블 + PFAS disclaimer
  - JSX 순서: Block2 Climate → **Block13 Alerts** → Block3 Facilities →
    ad-2 → Block7 TRI → **Block11 PFAS** → ad-3 → Block8 Cleanup ...
  - ad-5 슬롯 추가 (Block4 Water와 Block5 Methodology 사이)
  - MetaLine이 데이터보다 먼저 렌더링 (guardrails 규칙 준수)

**스모크 테스트:** Backend import OK, Frontend tsc --noEmit OK (0 errors)

### G.2 — Bundle Splitting + Hazards/Coastal/RCRA (2026-04-12) ✅

**번들 스플리팅 (599 KB → 63 KB 메인 청크):**

| 청크 | 크기 (gzipped) | 로딩 |
|------|---------------|------|
| index (main) | **62.96 KB** | eager |
| globe-vendor (three.js + react-globe.gl) | 519.83 KB | lazy (Home 방문 시) |
| Globe (component) | 6.03 KB | lazy |
| LocalReport | 6.49 KB | lazy |
| Guide | 7.08 KB | lazy |
| BornIn, Ranking, PM25, Atlas, AtlasCat | 1–2 KB 각 | lazy |

- `vite.config.ts`: `manualChunks` 추가 (`globe-vendor`)
- `App.tsx`: 모든 비-Home 라우트 `React.lazy`
- `Home.tsx`: Globe + BornIn `React.lazy` + Suspense skeleton

**LR 신규 블록 2개 (12 → 14):**

| # | 블록 | 데이터 | 조건 |
|---|------|--------|------|
| 12 | Hazards & Disasters | OpenFEMA 재난 5년 + USGS 지진 30일 | 항상 |
| 14 | Coastal Conditions | NOAA CO-OPS 수위/수온 | 해안 metro만 (17개) |

- Block 12: 3-stat cards (총 재난, 최다 유형, 최대 지진) + 재난 타임라인 + 지진 테이블
- Block 14: CO-OPS 스테이션 테이블 (수위 ft, 수온 °F, 최신 판독)
- `cbsa_mapping.json`: 17개 metro에 `coastal: true` 플래그

**RCRA → TRI 통합:**
- Block 7 (Toxic Releases)에 "Hazardous Waste Generators (RCRA)" 접이식 서브섹션
- handler_count + top 5 generators 테이블
- 별도 블록 대신 TRI와 합병 (ui-design.md 권고)

---

### H — SPA Routing Refactor (2026-04-13) ✅

Monolithic home page 분리 → 전용 페이지 라우트로 리팩터링.

**신규 페이지 5개:**

| 페이지 | 경로 | 내용 |
|--------|------|------|
| `EarthNow.tsx` | `/earth-now` | Globe + StoryPanel (Home에서 이동) |
| `Trends.tsx` | `/trends` | TrendsStrip + BornIn (Home에서 이동) |
| `Reports.tsx` | `/reports` | LocalReportsSection (Home에서 이동) |
| `RankingsList.tsx` | `/rankings` | 6개 랭킹 링크 리스트 |
| `GuidesList.tsx` | `/guides` | 4개 가이드 링크 리스트 |

**수정 파일 3개:**

| 파일 | 변경 |
|------|------|
| `Home.tsx` | 전면 교체 → Landing page (hero + 6 section cards) |
| `App.tsx` | 6개 lazy 라우트 추가 (EarthNow, Trends, Reports, RankingsList, GuidesList) |
| `Header.tsx` | scrollTo buttons → Link 라우트 전환, 로고 EarthPulse → TerraSight, useNavigate/scrollTo 제거 |

**라우트 매핑:**
```
/              → Landing page (hero + section cards)
/earth-now     → Globe full screen + StoryPanel + Layers
/trends        → TrendsStrip + Born-in interactive
/reports       → Metro list + ZIP search
/reports/:slug → 14-block report (기존)
/atlas         → Atlas categories (기존)
/atlas/:slug   → Category detail (기존)
/rankings      → Rankings list page (신규)
/rankings/pm25 → PM25 ranking (기존)
/rankings/:slug → Generic ranking (기존)
/guides        → Guides list page (신규)
/guides/:slug  → Guide detail (기존)
```

**검증:** TypeScript `--noEmit` 0 errors, `npm run build` 성공

---

### I — Dark Theme + Atlas Fix + Globe Overhaul (2026-04-13) ✅

전체 사이트 다크 테마 적용 + Atlas 빈 페이지 버그 수정 + Globe 시각화 대폭 개선.

**1. Atlas 빈 페이지 수정:**
- **원인:** `atlas_catalog.json`에서 `"forecast"` 태그 사용 → `TrustTag` enum은 `"forecast/model"` 정의 → `TRUST_TAG_META["forecast"]` undefined → TrustBadge 크래시
- **수정:** CAMS/NOAA RFC 데이터셋 태그를 `"forecast/model"`로 변경 + TrustBadge에 unknown tag fallback 추가

**2. Globe GIBS 데이터 렌더링 수정:**
- **원인:** `crossOrigin='anonymous'` Image 로딩 → canvas taint → `toDataURL()` SecurityError → BlueMarble 폴백
- **수정:** `fetch(url, {mode:'cors'})` → `blob()` → `URL.createObjectURL()` → taint-free canvas 합성
- Air Monitors `labelDotRadius` 0.25 → 0.4 (가시성 개선)

**3. Globe 시각화 개선:**
- 배경: `#0b1120` → `radial-gradient(ellipse, #0a0e27, #050810)` (우주 느낌)
- 대기: `atmosphereColor #88aaff → #4488ff`, `altitude 0.18 → 0.25` (강화된 글로우)
- 높이: 520px → 600px
- SST 색상 대비 강화 (navy → blue → teal → orange → deep red)
- Fire 포인트 크기 증가 (base 0.25→0.3, multiplier 0.2→0.25)
- **범례(Legend) 추가:** 좌하단에 활성 레이어별 색상 범례 표시
  - Fires: FRP (MW) 0~500+
  - Air Monitors: PM2.5 AQI 6단계
  - Earthquakes: M4~M7+ 크기/색상
  - Storms: TD~Cat4+ 풍속
  - SST: -2~30°C 그라데이션 바
  - Coral: DHW 0~16+ 그라데이션 바

**4. 전체 다크 테마 적용 (20+ 파일):**

| 영역 | 변경 |\n|------|------|\n| `index.html` | 타이틀 EarthPulse→TerraSight, body `#0a0e1a`, 글로벌 CSS (shimmer/fadeInUp/pulse-glow 애니메이션, skeleton 클래스, 반응형 미디어 쿼리) |
| `Header.tsx` | 다크 글래스모피즘 (`rgba(10,14,26,0.85)` + `blur(12px)`), 활성 링크 하이라이팅 (`useLocation`), 반응형 CSS 클래스 |
| `Home.tsx` | 다크 히어로 그라데이션 + radial 글로우, 글래스모피즘 섹션 카드 |
| `TrendsStrip.tsx` | 다크 카드 배경, sparkline 그라데이션 fill 추가, 값 32px 확대 |
| `Atlas.tsx` / `AtlasCategory.tsx` | 다크 글래스모피즘 카드, 라이브 필 그린-온-다크 |
| `Reports.tsx` | 다크 카드/입력 필드/링크 |
| `RankingsList.tsx` / `GuidesList.tsx` | 다크 링크 카드 |
| `Ranking.tsx` / `PM25Ranking.tsx` | 다크 테이블 (교차 행 어둡게) |
| `Guide.tsx` | 다크 본문/테이블/카드 |
| `ReportPage.tsx` | 다크 14블록 전체 (stat 카드/테이블/disclaimer/ad 슬롯) |
| `StoryPanel.tsx` | 다크 글래스모피즘 |
| `BornIn.tsx` | 다크 입력/결과 카드 |
| `EarthNow.tsx` | 다크 페이지 + Globe 공간 확장 (2fr→2.5fr) |

**검증:**
- `tsc --noEmit` 0 errors ✅
- `npm run build` 성공 ✅
- Main chunk: **54.58 KB** gzipped
- 전체 20개 chunk clean

---

### J — deck.gl Globe Migration (2026-04-13) ✅

`react-globe.gl` + `three.js` → `deck.gl` v9.2.11 전면 마이그레이션.

**핵심 변경:**

| 항목 | Before | After |
|------|--------|-------|
| Globe 라이브러리 | react-globe.gl v2.37.1 + three.js | deck.gl v9.2.11 (`_GlobeView`) |
| Globe vendor 번들 (gz) | 519.83 KB | **226.98 KB** (**-56%**) |
| Globe component (gz) | 7.35 KB | 6.78 KB |
| GIBS 타일 로딩 | 수동 canvas composite + `loadImageViaFetch()` | `TileLayer` + `BitmapLayer` (네이티브) |
| 포인트 렌더링 | per-mesh three.js Object3D | GPU-instanced `ScatterplotLayer` |
| 최대 포인트 성능 | ~10K (프레임 드롭) | **1M+** at 60 FPS |
| 폴리곤 지원 | 불가 | `GeoJsonLayer` 가능 |
| 2D Map 토글 | 불가 | `GlobeView` ↔ `MapView` 가능 |
| 의존성 | `react-globe.gl`, `three`, `three-globe`, `globe.gl` | `@deck.gl/core`, `@deck.gl/layers`, `@deck.gl/geo-layers` |

**신규/수정 파일:**
- `frontend/src/components/earth-now/GlobeDeck.tsx` — 신규 (deck.gl 기반 Globe 컴포넌트)
- `frontend/src/components/earth-now/Globe.tsx` → `Globe.old.tsx.bak` (레퍼런스용 보존)
- `frontend/src/pages/EarthNow.tsx` — GlobeDeck import으로 변경
- `frontend/vite.config.ts` — `globe-vendor` → `deckgl-vendor` 청크
- `frontend/package.json` — `react-globe.gl` 제거, deck.gl 4패키지 추가

**마이그레이션된 레이어 (14개):**

| 레이어 | Old 방식 | New 방식 |
|--------|---------|---------|
| BlueMarble 베이스 | 단일 WMS 이미지 → `globeImageUrl` | `TileLayer` WMTS 타일 |
| GIBS 오버레이 (PM2.5/AOD/OCO-2/Flood) | `loadImageViaFetch()` → canvas 합성 | `TileLayer` WMS 타일 (네이티브) |
| Active Fires | `pointsData` (per-mesh) | `ScatterplotLayer` (GPU) |
| Tropical Storms | `pointsData` (per-mesh) | `ScatterplotLayer` + stroke |
| Earthquakes | `pointsData` (per-mesh) | `ScatterplotLayer` + stroke |
| Air Monitors | `labelsData` (DOM) | `ScatterplotLayer` (GPU) |
| SST | `hexBinPointsData` | `ScatterplotLayer` (직접 색상) |
| Coral DHW | `hexBinPointsData` | `ScatterplotLayer` (직접 색상) |
| SLA | `labelsData` (DOM) | `ScatterplotLayer` (GPU) |

**CSS Atmosphere:**
- `radial-gradient(circle at 50% 50%, rgba(40,80,180,0.12) 0%, transparent 55%)` 오버레이
- 컨테이너: `radial-gradient(ellipse, #0a0e27, #040610)` 우주 배경

**Globe ↔ Map 토글 (Phase 2 준비):**
- LayerPanel에 Globe/Map 토글 버튼 추가 (UI 준비)
- 같은 레이어 정의가 GlobeView/MapView 모두에서 작동

**검증:**
- `tsc --noEmit` 0 errors ✅
- `npm run build` 성공 ✅
- Main: 56.30 KB gz, deckgl-vendor: 226.98 KB gz (총 20 chunks)

**Phase 2: Globe ↔ 2D Map 토글:**
- deck.gl `MapView` 추가 — 같은 레이어 코드로 Globe/Map 전환
- LayerPanel에 Globe/Map 토글 버튼
- 뷰 모드 뱃지 (3D Globe / 2D Mercator)

**Phase 3 시각 개선 4 Round:**

| Round | 내용 | 평가 |
|-------|------|------|
| Round 1: 색상 | SST 9-stop nullschool 팔레트, Fire hot-metal, Coral NOAA CRW, atmosphere pulse 애니메이션 | 8/10 |
| Round 2: 인터랙션 | 레이어 전환 fade (600ms), 지진 glow ring (2x 반투명), SST/Coral 포인트 확대 | 7/10 |
| Round 3: 합성 | 연속장+이벤트 동시 표시 확인 (아키텍처상 이미 지원) | 8/10 |
| Round 4: 로딩 | 로딩 오버레이 + 뷰 모드 뱃지 + 글로브 모드에만 atmosphere | 7/10 |

**자기 평가 (전체): 7.5/10**
- Globe 렌더링 + 데이터 레이어 + 2D 토글 모두 동작
- 번들 56% 감소 + 1M+ 포인트 성능 확보
- GIBS 네이티브 타일 로딩으로 CORS 해킹 제거
- 색상 시스템이 nullschool/windy 수준에 근접
- 개선 필요: ~~auto-rotate~~, ~~스타일 basemap (2D 모드)~~, 클릭→리포트 링크

---

### K — 타일 수정 + UI/UX 전면 재설계 (2026-04-13) ✅

BlueMarble/GIBS 타일 미표시 버그 수정 + Globe 페이지 전면 재설계 5 Round.

**타일 버그 수정 (2건):**

| 문제 | 원인 | 해결 |
|------|------|------|
| BlueMarble 검은 화면 | GIBS EPSG:4326 타일 매트릭스 ↔ deck.gl Web Mercator 인덱스 불일치 | EPSG:3857 `GoogleMapsCompatible_Level8` 엔드포인트 사용 |
| GIBS WMS 오버레이 미작동 | `{south},{west}` 플레이스홀더 deck.gl 미지원 + BBOX 순서 오류 | `getTileData` 콜백으로 직접 URL 구성 |

**UI/UX 재설계 5 Round:**

| Round | 내용 | 평가 |
|-------|------|------|
| R1: 타일 수정 + 풀스크린 | EPSG:3857 + Carto Dark basemap + `calc(100vh - 52px)` 풀스크린 | 6/10 |
| R2: 옵저버토리 비주얼 | 에지 비네트 + 활성 레이어 pill + 데이터 카운트 + 좌표 표시 + 대기 강화 | 7/10 |
| R3: 하단 바 레이아웃 | 우측 아코디언 → **하단 탭바** (windy.com 스타일), 레이어 pill, +240px 글로브 폭 | **8/10** |
| R4: 폴리시 | 툴팁 재설계 (shadow+blur) + 자동 회전 (6초 유휴) + MetaLine 투명도 조정 + 모바일 | 8/10 |
| R5: 최종 | 하단 바 그래디언트 페이드 + 스타일 통일 + docs 기록 | 8.5/10 |

**레이아웃 비교 (A vs B):**

| 항목 | Layout A (우측 패널) | Layout B (하단 바) |
|------|---------------------|-------------------|
| Globe 폭 | ~75% | **100%** |
| 레이어 접근 | 3클릭 (Layers → 카테고리 → 레이어) | **1-2클릭** (탭 → pill) |
| 레퍼런스 | 일반 GIS 도구 | **windy.com / Google Earth** |
| 결론 | ✗ 폐기 | **✓ 채택** |

**신규 기능:**
- **활성 레이어 pill** — 상단 중앙, 레이어명 + 데이터 포인트 수 + 발광 도트
- **좌표 표시** — 하단 우측, `lat° lon° z{zoom}` monospace
- **자동 회전** — 6초 유휴 시 Globe 0.9°/sec 회전, 상호작용 시 즉시 정지
- **에지 비네트** — `boxShadow: inset 0 0 150px 60px` 시네마틱 깊이감
- **하단 그래디언트** — Globe → 컨트롤바 자연스러운 전환
- **2D Map 베이스맵** — Carto Dark `dark_nolabels` (라벨 없는 다크 타일)
- **로딩 스피너** — 텍스트 → ring spinner + 텍스트
- **StoryPanel 오버레이** — 그리드에서 분리, 플로팅 접이식 카드

**검증:**
- `tsc --noEmit` 0 errors ✅
- `npm run build` 성공 ✅
- GlobeDeck: 7.78 KB gz (7.23 → 7.78, +0.55 KB)
- Main: 56.30 KB gz (변동 없음)

**자기 평가: 8.5/10**
- 타일 수정으로 BlueMarble 정상 표시
- 풀스크린 + 하단 바 = 전문 도구 수준 UX
- 자동 회전으로 "살아있는" 느낌
- windy.com / nullschool 수준의 비주얼 달성
- 남은 과제: Globe ↔ Map 전환 애니메이션, 클릭→리포트 네비게이션

---

### L — Earth Now 근본 재설계 (2026-04-13) ✅

Globe 레이어 시스템을 완전히 재설계. 글로벌 데이터만 표시, 관심도순 카테고리,
복합 레이어 통합, HeatmapLayer 도입.

**설계 원칙:**
1. Globe에는 전지구 데이터만 (미국 전용 = Local Reports)
2. 관심도 높은 데이터를 기본 표시
3. 관련 소스를 하나의 카테고리로 통합
4. 점 → 히트맵 연속 시각화 (2D)

**레이어 시스템 재설계:**

| Before (이중 채널) | After (단일 카테고리) |
|------|------|
| `activeEvent` + `activeContinuous` | **`activeCategory`** 단일 선택 |
| 14개 개별 레이어 | **7개 통합 카테고리** |
| monitors (OpenAQ) 포함 | **Air Monitors 제거** (US-heavy) |
| 이벤트/연속장 분리 | **복합 레이어 통합** |

**7개 통합 카테고리 (관심도순):**

| 순서 | 카테고리 | 내부 레이어 | 관심도 |
|------|---------|-----------|-------|
| 1 | Air Quality | GIBS PM2.5 (MERRA-2 타일) | ★★★★★ |
| 2 | **Fires & Smoke** | FIRMS 포인트 + GIBS AOD 타일 동시 표시 | ★★★★★ |
| 3 | **Ocean Health** | SST + Coral DHW 동시 표시 | ★★★★ |
| 4 | Earthquakes | USGS M4+ | ★★★★ |
| 5 | CO₂ Column | GIBS OCO-2 | ★★★ |
| 6 | Flood Detection | GIBS MODIS 3-Day | ★★★ |
| 7 | Tropical Storms | IBTrACS | ★★★ |

**신규/변경 기능:**

1. **HeatmapLayer (2D 화재):** `@deck.gl/aggregation-layers` 설치, 2D MapView에서
   화재를 연속 히트맵으로 렌더링 (FRP 로그 가중치, 50px 반경, 6단계 컬러)
2. **Fire glow (3D):** ScatterplotLayer 2중 (glow ring α=40 + core) — 지진 스타일
3. **복합 레이어:** "Fires & Smoke" = FIRMS 포인트 + GIBS AOD 동시,
   "Ocean Health" = SST + Coral 동시 → 하나의 카테고리 선택으로 복수 레이어 활성화
4. **GIBS 날짜 수정:** MERRA-2 monthly → 2개월 전 1일 사용 (latency 보정),
   daily 레이어 → 전일 사용 (`getGibsDate(layerKey)` per-layer)
5. **기본 레이어 변경:** fires → fires-smoke (가장 안정적 + 관심도 높음)
6. **Air Monitors (OpenAQ) 제거:** US 편중 점 데이터, globe 스케일에서 의미 약함

**번들 영향:**

| 청크 | Before | After | 변화 |
|------|--------|-------|------|
| GlobeDeck (gz) | 7.78 KB | **6.76 KB** | -1.02 KB (시스템 단순화) |
| deckgl-vendor (gz) | 226.99 KB | **232.43 KB** | +5.44 KB (aggregation-layers) |
| Main index | 56.30 KB | 56.30 KB | 변동 없음 |

**검증:**
- `tsc --noEmit` 0 errors ✅
- `npm run build` 성공 ✅

**후속 과제:**
- 백엔드 격자화 API (`GET /api/earth-now/heatmap`) — 현재 클라이언트 HeatmapLayer로 대체
- SST/Coral 격자를 더 큰 반경으로 렌더링하여 연속 효과 강화
- GIBS PM2.5 표시 검증 (MERRA-2 2개월 latency 확인)

---

### M — Earth Now 2차 혁신 (2026-04-13) ✅

4가지 핵심 문제 해결: 로딩 속도, GIBS PM2.5, 데이터 통합, 카테고리 재설계.

**문제 1: 로딩 속도 → lazy fetch**
- `useApi` 훅에 `enabled` 플래그 추가 — `false`이면 fetch 스킵
- 카테고리 전환 시 필요한 데이터만 fetch (GIBS 타일 카테고리는 fetch 불필요)
- 기존 데이터 캐시 유지: `enabled=false`로 전환해도 이전 데이터 보존
- 백엔드 `Cache-Control: public, max-age=300` (5분) 미들웨어 추가
- GlobeDeck: 5개 동시 fetch → 최대 1개 lazy fetch

**문제 2: GIBS PM2.5 수정 (근본 원인 2건)**
| 원인 | 수정 |
|------|------|
| 잘못된 레이어명 (`Total_Aerosol_Optical_Thickness`) | `MERRA2_Dust_Surface_Mass_Concentration_PM25_Monthly` |
| 날짜 latency 2개월 → 실제 3개월 (2026-02-01 = 404) | `d.setMonth(d.getMonth() - 3)` → 2026-01-01 사용 |

- WMTS 타일 직접 확인: 2026-01-01 = HTTP 200, 4.3 KB PNG (실제 PM2.5 데이터)
- TileMatrixSet: `GoogleMapsCompatible_Level6` (Level8이 아님)

**문제 3: 백엔드 데이터 통합**
신규 파일: `backend/api/earth_now_integrated.py`

| 엔드포인트 | 입력 | 출력 |
|-----------|------|------|
| `GET /api/earth-now/integrated/ocean-health` | SST + Coral DHW (asyncio.gather) | 2° 격자 stress_score (0~1) |
| `GET /api/earth-now/integrated/fire-density?resolution=2` | FIRMS top-2000 | 격자별 fire_count, avg_frp, max_frp |

Ocean stress formula: `clamp((sst_anomaly / 5.0) * 0.4 + (dhw / 8.0) * 0.6, 0, 1)`

**문제 4: 카테고리 사용자 질문 중심 재설계**

| 순서 | 아이콘 | 이름 | 사용자 질문 | 기본 |
|------|--------|------|----------|------|
| 1 | 🌬️ | Air Quality | "오늘 공기 괜찮아?" | **✓ 기본** |
| 2 | 🔥 | Wildfires | "어디서 불이 나?" | |
| 3 | 🌊 | Ocean Crisis | "바다가 얼마나 뜨거워?" | |
| 4 | 🌍 | Earthquakes | "지진 어디서 났어?" | |
| 5 | 🌡️ | CO₂ & GHG | "온실가스 어디서 많이?" | |
| 6 | 🌀 | Storms | "태풍 어디에 있어?" | |
| 7 | 🌧️ | Floods | "홍수 위험 지역은?" | |

- 기본 카테고리: fires-smoke → **air-quality** (항상 데이터 있어서 빈 화면 방지)
- 카테고리 pill에 이모지 아이콘 추가
- 상단 pill에 사용자 질문 표시 (예: "How is the air today?")
- Ocean Health → **Ocean Crisis** (SST+DHW 통합 stress_score 1개 레이어)

**번들:**
- GlobeDeck: 6.76 → **6.54 KB** gz (-0.22 KB, lazy fetch로 코드 축소)
- deckgl-vendor: 232.43 KB (변동 없음)

---

### 기존 블로커 (일부 해소)

- ~~**Bundle 코드 스플리팅** — 599 KB gzip~~ ✅ **해소 (G.2→J)** — deck.gl 마이그레이션,
  main chunk **56.30 KB**, deckgl-vendor **226.98 KB** (총 283 KB, 이전 대비 -244 KB)
- ~~**Globe 성능 한계 (10K 포인트)** — react-globe.gl per-mesh 병목~~ ✅ **해소 (J)** —
  deck.gl GPU-instanced ScatterplotLayer, 1M+ 포인트 가능
- ~~**BlueMarble 타일 미표시**~~ ✅ **해소 (K)** — EPSG:3857 엔드포인트
- ~~**GIBS WMS 오버레이 미작동**~~ ✅ **해소 (K)** — `getTileData` 콜백
- ~~**Auto-rotate 미구현**~~ ✅ **해소 (K)** — 6초 유휴 시 0.9°/sec 회전
- ~~**2D Map 스타일 basemap 없음**~~ ✅ **해소 (K)** — Carto Dark `dark_nolabels`
- ~~**GIBS PM2.5 미표시**~~ ✅ **해소 (M)** — 레이어명 수정 + 3개월 latency
- ~~**전체 데이터 동시 로드**~~ ✅ **해소 (M)** — useApi `enabled` lazy fetch
- **CMEMS P1** — `copernicusmarine` 패키지 + Keycloak 자격증명 재검증
- **커스텀 도메인** — CF Pages + Render (옵션 0에 포함)
- **Story Panel 프리셋** (1 → 5-10개) (옵션 B에 포함)
- **SDWIS 랭킹 state cap** — per-prefix fan-out 추가 가능 (rate limit 리스크)
