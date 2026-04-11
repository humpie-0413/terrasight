# EarthPulse / TerraSight — Progress Log

## 1차 MVP 완료 (2026-04-11)

### 라이브 URL
| 서비스 | URL |
|--------|-----|
| Frontend (CF Pages) | https://terrasight.pages.dev |
| Backend (Render) | https://terrasight-api-o959.onrender.com |
| GitHub | https://github.com/humpie-0413/terrasight |

### 핵심 수치
| 항목 | 수치 |
|------|------|
| Git commits | 37 |
| Backend connectors | 28개 (14 기존 + 14 신규) |
| API endpoints | 24개 |
| Frontend components / pages | ~28개 |
| Local Reports metros | 50 / 50 목표 ✅ |
| Bundle size | **598 KB gzipped** (< 600 KB 가드레일) |
| Globe 레이어 | **13개** (5 카테고리 어코디언) |
| Trends 카드 | **5개** (CO₂ · Temp · Sea Ice · CH₄ · Sea Level) |
| 배포 스택 | Cloudflare Pages + Render (Docker) |

---

## 완료 항목 요약

### Phase 0 — Scaffold (`a95ea56`)
- React + Vite + TypeScript 프런트 skeleton (15 컴포넌트, 5 페이지, hooks/utils/types)
- FastAPI 백엔드 skeleton (14 커넥터 stub, 5 API 라우터)
- 프로젝트 구조: `frontend/`, `backend/`, `data/`, `docs/`

### Phase 1 — API Spike (`7414e6b`, `ad3175b`)
14개 P0 소스 검증. 최종 결과: **9 GO / 5 주의 / 0 블로커**

| 소스 | 결과 | 주요 사항 |
|------|------|-----------|
| NOAA GML CO₂ | ✅ | 직접 파일 다운로드, 인증 불필요 |
| NOAAGlobalTemp CDR | ✅ | CtaG 대체 (공개 REST API 없음) |
| NSIDC Sea Ice | ✅ | CSV, noaadata.apps.nsidc.org |
| NOAA OISST | ✅ | ERDDAP griddap (CoastWatch) |
| U.S. Climate Normals | ✅ | NCEI 1991-2020 per-station CSV |
| AirNow | ✅ | 무료 키, 500 req/hr |
| OpenAQ v3 | ✅ | v1/v2 은퇴 2025-01-31; v3 키 필요 |
| NASA FIRMS | ✅ | 무료 MAP_KEY, 5,000 트랜잭션/10분 |
| NASA GIBS | ✅ | 공개 WMTS, 인증 불필요 |
| EPA ECHO | ✅ | echodata.epa.gov (ofmpub 차단됨) |
| USGS modernized | ✅ | OGC API, api.waterdata.usgs.gov |
| WQP | ✅ | `/wqx3/` beta 필수 (legacy 폐기) |
| EPA AQS | ⚠️ | 이메일+키, 10 req/min — P1 |
| CAMS (ADS) | ⚠️ | Copernicus 계정 필요 — P1 보류 |

### Phase 2 — Climate Trends Strip (`f69988b`, `ddf8735`)
3개 카드 모두 라이브.

| 카드 | 커넥터 | 최신값 (검증일) |
|------|--------|-----------------|
| CO₂ | `noaa_gml.py` — Mauna Loa 직접 다운로드 | 429.35 ppm (2026-02) |
| Global Temp | `noaa_ctag.py` — NOAAGlobalTemp CDR v6.1 ASCII | +0.53 °C vs 1991-2020 (2026-02) |
| Arctic Sea Ice | `nsidc.py` — G02135 v4.0 daily CSV, 5-day mean | 13.98 M km² (2026-04-09) |

- 팬아웃 엔드포인트 `GET /api/trends` — 3개 커넥터 병렬 실행, 한 개 실패해도 나머지 정상 반환
- `TrendsStrip.tsx` — MetaLine(cadence · badge · source)이 수치 위에 표시

### Phase 3 — Earth Now Globe (`00a1ae1`, `0b85e37`)
글로브 + 4개 레이어 + Story Panel.

**라이브러리:** `react-globe.gl` (Cesium 대신 — 번들 3-5 MB 절감)

| 레이어 | 커넥터 | 상태 |
|--------|--------|------|
| Base (BlueMarble) | NASA GIBS WMS GetMap | ✅ 항상 ON |
| Fires | `firms.py` — VIIRS Area API, top 1,500 by FRP | ✅ 기본 ON |
| Ocean Heat | `oisst.py` — ERDDAP griddap stride 20, 1,684 points | ✅ |
| Air Monitors | `openaq.py` — v3 PM2.5 locations, AQI 색상 밴드 | ✅ (키 필요) |
| Smoke | `cams.py` | ⚪ P1 보류 (Copernicus 계정 없음) |

- `Globe.tsx` — `forwardRef` + `flyTo()` 명령 핸들 (Story Panel 연동)
- `StoryPanel.tsx` — "2026 Wildfire Season" 프리셋, "Explore on Globe" + "Read Local Report →"
- 레이어 규칙: 연속 필드 1개 + 이벤트 오버레이 1개

### Phase 4 — Local Reports (`e925798`, `7265819`, `f430f89`, `0342dd9`)
10개 metro, 6블록 구조 라이브.

**커넥터 (Block별):**
| 커넥터 | 블록 | 검증 수치 |
|--------|------|-----------|
| `airnow.py` | Block 1 현재 AQI | Houston AQI 63 · Moderate · PM2.5 |
| `climate_normals.py` | Block 2 기준선 | Houston 71.1°F / 55.6 in (1991-2020) |
| `echo.py` | Block 3 시설 | 500 샘플, FacSNCFlg + ComplianceStatus |
| `usgs.py` | Block 4 수문 | Houston 51 NRT 사이트 |
| `wqp.py` | Block 4 수질 | Houston 31,549 이산 샘플 |

**ECHO 주요 변경사항 (이전 ofmpub → echodata):**
- Two-hop API: `get_facilities` → QueryID → `get_qid`
- `p_act=Y` 필수 (LA bbox → 363k rows → queryset 한계 초과)
- `FacLong` 없음 (지도 P1 보류), `CurrVioFlag` 없음 → `FacSNCFlg` 사용

**10개 Metro (data/cbsa_mapping.json):**
| CBSA | 이름 | 인구 | 기후 | NOAA 스테이션 |
|------|------|------|------|---------------|
| 26420 | Houston-The Woodlands-Sugar Land | 7.3M | Cfa | USW00012918 |
| 31080 | Los Angeles-Long Beach-Anaheim | 13.2M | Csb | USW00023174 |
| 35620 | New York-Newark-Jersey City | 19.8M | Cfa | USW00094728 |
| 16980 | Chicago-Naperville-Elgin | 9.5M | Dfa | USW00094846 |
| 19100 | Dallas-Fort Worth-Arlington | 7.8M | Cfa | USW00003927 |
| 38060 | Phoenix-Mesa-Chandler | 5.1M | BWh | USW00023183 |
| 37980 | Philadelphia-Camden-Wilmington | 6.2M | Cfa | USW00013739 |
| 41700 | San Antonio-New Braunfels | 2.6M | Cfa | USW00012921 |
| 41740 | San Diego-Chula Vista-Carlsbad | 3.3M | Csb | USW00023188 |
| 41940 | San Jose-Sunnyvale-Santa Clara | 2.0M | Csb | USW00023293 |

**Backend endpoints:**
- `GET /api/reports/` — metro 목록
- `GET /api/reports/search?q=` — ZIP prefix + 이름 매칭
- `GET /api/reports/{cbsa_slug}` — 6블록 리포트 (5개 커넥터 병렬)

**Frontend:**
- `ReportPage.tsx` — 6블록 + MetaLine + graceful degradation + AdSense 슬롯
- 홈 LocalReportsSection: 상위 4개 카드 + "View all N →" + 랭킹/가이드 링크

### Phase 5 — Atlas + Navigation (`02de1c2`)
- `atlas_catalog.json` — 8개 카테고리 × 2-5 데이터셋, 14개 live
- `Atlas.tsx` (/atlas) — 카테고리 카드, trust badge 샘플
- `AtlasCategory.tsx` (/atlas/:slug) — 데이터셋 목록, MetaLine, 404 처리
- `AtlasGrid.tsx` — 홈 진입 카드 (emoji, count, live badge)
- `Header.tsx` — sticky, scrollTo() 앵커, 모바일 햄버거

### Phase 6 — SEO 콘텐츠 (`0342dd9`)
- `GET /api/rankings/epa-violations` — 10개 metro ECHO 병렬 호출, 위반순 정렬
- `Ranking.tsx` (/rankings/epa-violations) — 로딩 안내 + 위반 테이블 + ECHO 면책
- `Guide.tsx` (/guides/how-to-read-aqi) — AQI 6단계 + 색상 스와치 + 오염물질 테이블

### Phase 7 — 배포 + 인프라 (`8d03752`, `46d1c52`)
- `Dockerfile` — python:3.12-slim, 비루트 유저, `$PORT`
- `render.yaml` — Render blueprint (docker runtime, free plan)
- `frontend/public/_headers` — CF Pages 보안 헤더 + 정적 에셋 캐싱
- `frontend/public/_redirects` — SPA fallback
- `docs/deploy.md` — 3가지 옵션 비교 + 단계별 가이드
- **CORS 버그 수정:** pydantic-settings `list[str]` 필드가 plain URL 파싱 실패
  → `str` 타입으로 변경, `main.py`에서 `_parse_origins()` 직접 파싱

### 토큰 최적화 (`085ffe7`)
- `.claudeignore` 추가 (node_modules, dist, __pycache__ 등)
- CLAUDE.md: 299 → 123줄 (다이어트)
- 분산 docs: `connectors.md`, `report-spec.md`, `guardrails.md`, `api-spike-results.md`

---

## 알려진 랜드마인 (docs/guardrails.md 상세 기록)

| 소스 | 함정 | 해결책 |
|------|------|--------|
| EPA ECHO | `ofmpub.epa.gov` 차단 | `echodata.epa.gov` 사용 |
| EPA ECHO | `echo13_rest_services` 404 | `echo_rest_services` 사용 |
| EPA ECHO | 단일 요청으로 시설 목록 안 나옴 | Two-hop: get_facilities → get_qid |
| EPA ECHO | LA같은 대도시 bbox → queryset 초과 | `p_act=Y` 파라미터 필수 |
| EPA ECHO | `FacLong` 없음 | 위도만 사용; 지도 기능 P1 보류 |
| WQP | legacy `/data/` — USGS 2024-03-11 이후 데이터 없음 | `/wqx3/` beta 필수 |
| WQP | `providers=NWIS,STORET` comma-join → 0 rows | repeated params 사용 |
| pydantic-settings | `list[str]` 필드 — plain URL → json.loads 실패 | `str` 타입 + 직접 파싱 |

---

## Phase 8 — 2차 작업: Metro 확장 + SEO 콘텐츠 (2026-04-11) ✅

### 8.1 Metro 40개 추가 (총 50개)
- `data/cbsa_mapping.json` → 10 → **50개** CBSA 추가 완료
- 4개 병렬 에이전트로 NOAA 스테이션 ID, AirNow ZIP, ZIP prefix, bbox 조사
- **추가된 40개:** Atlanta, Austin, Baltimore, Birmingham, Boston, Buffalo,
  Cincinnati, Cleveland, Columbus OH, Denver, Detroit, Hartford, Indianapolis,
  Jacksonville, Kansas City, Las Vegas, Louisville, Memphis, Miami, Milwaukee,
  Minneapolis, Nashville, New Orleans, Oklahoma City, Orlando, Pittsburgh,
  Portland OR, Providence, Raleigh, Richmond, Riverside, Sacramento, St. Louis,
  Salt Lake City, San Francisco, Seattle, Tampa, Tucson, Virginia Beach, Washington DC
- ZIP prefix 중복 제거: Riverside ["922"-"925"] / Richmond ["230","232","238"] / Virginia Beach ["233"-"237"]

### 8.2 PM2.5 랭킹
- `GET /api/rankings/pm25` — AirNow ZIP 기반, 50개 metro 병렬, pm25_aqi 내림차순
- `AIRNOW_API_KEY` 미설정 시 `not_configured` graceful response
- `PM25Ranking.tsx` — AQI 카테고리 색상 배지, 테이블 표시
- App.tsx: `/rankings/pm25` 전용 라우트 (catch-all 앞에 위치)

### 8.3 교육 가이드 3개
- `/guides/understanding-epa-compliance` — ECHO SNC 기준, 위반 유형, 면책
- `/guides/water-quality-samples` — WQP 이산 샘플, 파라미터 테이블, 검출 한계
- `/guides/climate-normals` — 1991-2020 기준, 기온 vs 강수, 공학 응용

### 8.4 홈 업데이트
- 랭킹/가이드 빠른 링크 6개: EPA Violations, PM2.5, AQI 가이드, EPA Compliance, Water Quality, Climate Normals

---

---

## Phase A — 글로벌 데이터 커넥터 14개 추가 (`a5e897d`, 2026-04-11) ✅

커넥터 총 **28개** (14 기존 + 14 신규). 전체 신규 목록:

### A.1 GIBS Layer Catalog
- `backend/connectors/gibs.py` — `LAYER_CATALOG` dict 추가

| 레이어 키 | GIBS Layer ID | 주기 | 상태 |
|-----------|---------------|------|------|
| `modis_aod` | `MODIS_Terra_Aerosol` | daily | ✅ live |
| `pm25` | `MERRA2_Dust_Surface_Mass_Concentration_PM25_Monthly` | monthly | ✅ live (먼지 성분만) |
| `oco2_xco2` | `OCO-2_Carbon_Dioxide_Total_Column_Average` | daily (swath) | ✅ live |
| `modis_flood` | `MODIS_Combined_Flood_2-Day` | daily | ✅ live |
| `tropomi_ch4` | — | — | ❌ GIBS 미지원 → Copernicus GES DISC 대안 |

- `backend/api/layers.py` — `GET /api/layers/catalog` (WMTS tile_url_template 포함)
- `backend/main.py` — `/api/layers` 라우터 등록

### A.2 해양/기후 커넥터 4개

| 커넥터 | 소스 | 인증 | 태그 |
|--------|------|------|------|
| `noaa_gml_ch4.py` | NOAA GML CH₄ monthly global | 없음 | observed |
| `noaa_sea_level.py` | NOAA NESDIS GMSL (`_free_all_66.csv`) | 없음 | observed |
| `coral_reef_watch.py` | CRW ERDDAP `NOAA_DHW` (BAA, DHW, SST) | 없음 | near-real-time |
| `cmems.py` | Copernicus Marine SLA L4 NRT | `CMEMS_USERNAME/PASSWORD` | observed |

### A.3 육지/생태 커넥터 2개

| 커넥터 | 소스 | 인증 | 태그 |
|--------|------|------|------|
| `global_forest_watch.py` | GFW Data API / Hansen UMD | `GFW_API_KEY` (무료, 1년 만료) | derived |
| `jrc_drought.py` | JRC EDO WMS (drought.emergency.copernicus.eu) | 없음 | derived |

JRC: REST API 없음 — WMS/WCS 타일 URL 카탈로그(`status: tiles_only`)로 구현

### A.4 기상/배출 커넥터 2개

| 커넥터 | 소스 | 인증 | 태그 |
|--------|------|------|------|
| `ibtracs.py` | NOAA IBTrACS v04r01 ACTIVE + LAST3YEARS CSV | 없음 | observed |
| `climate_trace.py` | Climate TRACE API v6 (국가별 연간 GHG) | 없음 | estimated |

### 주요 랜드마인 (docs/connectors.md 상세)
- NOAA Sea Level 구 URL `_txj1j2_90.csv` → 사망, `_free_all_66.csv` 사용
- GFW: POST-only query (GET → 405), 컬럼명 이중 언더스코어
- JRC: 도메인 이전 `edo.jrc.ec.europa.eu` → `drought.emergency.copernicus.eu` (2024-04-03)
- IBTrACS: 파일명 `last3years` (소문자, `LAST3YR` → 404), 2-헤더-행 CSV
- Climate TRACE: 파라미터 `countries` (복수), 단위 metric tons (기가톤 아님)

---

## Phase 9 — Land/Ecology Connectors (2026-04-11) ✅

### 9.1 Global Forest Watch connector (`backend/connectors/global_forest_watch.py`)
- **Endpoint:** `POST https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/{version}/query/json`
- **Auth:** `x-api-key` header required — free account at globalforestwatch.org; keys expire after 1 year
- **Data:** Annual global tree cover loss (ha) aggregated worldwide; version auto-detected from `/dataset/umd_tree_cover_loss` metadata
- **Graceful degradation:** returns `status: not_configured` when `api_key` is absent or HTTP 401/403 received
- **Tag:** `derived` | **Cadence:** annual | **License:** CC BY 4.0
- **Landmines:** (1) POST-only query endpoint — GET `?sql=` returns 405; (2) country-level queries require posting a polygon geometry; (3) `area__ha` column name uses double underscores; (4) dataset version must be exact string from metadata list ("v1.12", not "1.12")

### 9.2 JRC Global Drought Observatory connector (`backend/connectors/jrc_drought.py`)
- **API type:** WMS (tiles) + WCS (GeoTIFF rasters) only — NO public JSON/REST tabular API as of 2026-04-11
- **WMS endpoint:** `https://drought.emergency.copernicus.eu/api/wms?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1`
- **WCS endpoint:** `https://drought.emergency.copernicus.eu/api/wcs?map=DO_WCS&...`
- **Available layers:** spaST/spaLT (SPI ERA5), spcST/spcLT (SPI CHIRPS), spgTS (SPI GPCC), smian/smang/smand (Soil Moisture), fpanv (fAPAR), cdiad (CDI Europe), twsan (GRACE TWS), rdria (Drought/Agriculture risk)
- **Returns:** `DroughtLayer` objects with WMS tile URL templates and WCS GeoTIFF URL templates; `status: tiles_only` in notes
- **Fallback:** hardcoded `_KNOWN_LAYERS` used if WMS GetCapabilities fetch fails
- **Tag:** `derived` | **Cadence:** dekadal (most layers), monthly (SPI-LT, GRACE) | **License:** CC BY 4.0
- **Landmines:** (1) Domain migrated from `edo.jrc.ec.europa.eu` to `drought.emergency.copernicus.eu` on 2024-04-03; (2) SPI GPCC (`spgTS`) requires `SELECTED_TIMESCALE` param ("01","03","06","09","12"); (3) `cdiad` is Europe-only; (4) pixel-to-tabular stats need rasterio/GDAL

---

## Phase B — Globe UI 레이어 확장 + Trends 캐러셀 (2026-04-11) ✅

브랜치: `feature/phase-b-globe-ui` | 커밋 9개

### B.1 Climate Trends 5-카드 캐러셀 (`cafee8b`, `0ae83cf`)
- `TrendsStrip.tsx` — 3카드 grid → **5카드 horizontal scroll-snap carousel**
  - CH₄ (ppb, NOAA GML, sparkColor amber `#d97706`)
  - Sea Level Rise (mm, NOAA NESDIS GMSL, sparkColor blue `#2563eb`)
- `backend/api/trends.py` — 3개 → **5개 fan-out** (`_ch4_payload`, `_sea_level_payload`)
  - 개별 디버그 엔드포인트: `GET /api/trends/ch4`, `GET /api/trends/sea-level`

### B.2 TrustTag 확장 (`b743dd6`)
- `trustTags.ts` — `Derived`, `NearRealTime`, `ForecastModel` 값 추가 (기존 `Forecast` 버그 수정)

### B.3 Backend 새 earth-now 엔드포인트 (`a468233`)
- `backend/api/earth_now.py`:
  - `GET /api/earth-now/storms` — IBTrACS 활성 열대폭풍 (storm당 최신 1포인트)
  - `GET /api/earth-now/coral` — CRW 산호 표백 열 응력 그리드 (DHW, BAA)
  - `GET /api/earth-now/sea-level-anomaly` — CMEMS SLA L4 NRT (인증 없으면 `not_configured` 반환)

### B.4 Globe.tsx Phase B 리라이트 (`c1ea188`)

**5-카테고리 어코디언 레이어 패널 (top-right 고정 오버레이):**

| 카테고리 | 레이어 |
|----------|--------|
| 🌫 Atmosphere | PM2.5 MERRA-2 (gibs-pm25) · AOD MODIS (gibs-aod) · Air Monitors (monitors) |
| 🔥 Fire & Land | Active Fires (fires) · Deforestation (disabled) · Drought (disabled P1) |
| 🌊 Ocean | SST Anomaly (ocean-heat) · Coral Bleaching (coral) · Sea Level (cmems-sla) |
| 🌿 GHG | CO₂ Column OCO-2 (gibs-oco2) · CH₄ TROPOMI (disabled P1) |
| ⚡ Hazards | Tropical Storms (storms) · Flood Map (gibs-flood) |

**GIBS 캔버스 컴포지트 (`useGibsTexture` hook):**
- GIBS WMS GetMap 투명 PNG → BlueMarble 오프스크린 캔버스에 합성 (globalAlpha=0.72)
- `canvas.toDataURL() → globeImageUrl` → 3D 구체 함께 회전
- 날짜 자동 선택: today → yesterday → day-2 → 이달 1일 → 지난달 1일 (월별 레이어 폴백)

**새 데이터 레이어 렌더링:**
- `pointsData` — fires (FRP 로그 스케일) or storms (windKt 색상 밴드)
- `hexBinPointsData` — SST (sstColor) or coral DHW (dhwColor)
- `labelsData` — air monitors (pm25Color) or CMEMS SLA dots (slaColor)

**새 색상 헬퍼:** `dhwColor` (DHW 0→16 ramp), `slaColor` (±0.3 m blue/white/red), `stormColor` (windKt 밴드)

**Home.tsx 정리 (`71838e3`, `eb2645e`):**
- 레이어 상태: `firesOn+continuousLayer` → `activeEvent + activeContinuous`
- 버그 수정: `openaq → 'air-monitors'`가 ActiveContinuous 멤버 아님 → `setActiveEvent('monitors')` 수정

---

## Phase C.0 — 데이터 전수조사 + 미구현 해결 (`b28831d`, 2026-04-11) ✅

### 전수조사 결과 (28개 데이터 소스)

| 상태 | 개수 |
|------|------|
| ✅ 작동 (인증 불필요) | 18개 |
| 🔑 API 키 부족 (graceful degradation) | 6개 |
| ⏸ 비활성화 P1 | 2개 |
| ❌ 미구현 (코드 없음) | 2개 → 1개 (CH₄ UI 정리) |

### 미구현 2개 처리

**NOAA CtaG City Series** (Block 2):
- 검증: `/access/monitoring/climate-at-a-glance/city/time-series/` — HTTP 404 all URL patterns
- 결론: CtaG city는 JavaScript UI 전용, 공개 REST/CSV API 없음
- 조치: `noaa_ctag.py` 도큐스트링에 발견 사항 기록, Climate Normals 영구 fallback 유지

**TROPOMI CH₄**:
- 기존 `available=false` 마킹 유지
- 사용자 노출 텍스트: `"TROPOMI CH₄ not in GIBS..."` → **`"Satellite data coming soon"`**
- GHG 카테고리는 OCO-2 CO₂ 레이어로 비어있지 않음 ✅

### config.py 보완
- `gfw_api_key: str | None = None` 추가 → .env에서 `GFW_API_KEY` 값 인식 가능

### 라이브 엔드포인트 상태 (2026-04-11 기준)

| 엔드포인트 | 상태 |
|-----------|------|
| `/api/earth-now/air-monitors` | ✅ **47개 실시간 PM2.5** (OPENAQ_API_KEY 등록 완료) |
| `/api/earth-now/sea-level-anomaly` | ⚠️ CMEMS THREDDS HTML 리다이렉트 — ToU 동의 필요 |
| `/api/earth-now/fires` | ✅ **live** (FIRMS_MAP_KEY 등록 완료) |
| `/api/earth-now/storms` | ✅ IBTrACS live |
| `/api/earth-now/coral` | ✅ NOAA CRW live |
| `/api/earth-now/sst` | ✅ NOAA OISST live |
| `/api/trends` | ✅ 5개 지표 모두 live |
| `/api/layers/catalog` | ✅ 6 GIBS layers (tropomi_ch4 available=False) |

---

## Phase C — 다음 단계 ← 현재 위치

### C.0 선택지 (사용자 결정 필요)
- **Phase C-디자인**: 디자인 폴리시 (카드 hover/애니메이션, 다크모드, 모바일 최적화)
- **Phase C-콘텐츠**: 추가 랭킹 + 가이드 (산호/IBTrACS/GHG), 가이드 SEO 확장
- **두 가지 병행** 가능

### C.1 인프라 (높음)
1. **AIRNOW_API_KEY** → PM2.5 랭킹 실제 데이터 활성화
2. **GFW_API_KEY** → 산림 손실 데이터 활성화
3. **CMEMS_USERNAME/PASSWORD** → 해수면 이상 Globe 레이어 활성화
4. **AdSense 신청** — 콘텐츠 충분 (50개 리포트 + 5개 SEO 페이지)
5. **커스텀 도메인** — CF Pages + Render 양쪽 설정

### C.2 콘텐츠/랭킹 (중간)
- `/rankings/deforestation` — GFW 연간 산림 손실 국가별 랭킹
- `/rankings/coral-bleaching` — CRW 산호 표백 경보 레벨 지도
- `/rankings/ghg-emissions` — Climate TRACE 국가별 GHG 배출 랭킹
- 가이드: "Understanding Coral Bleaching Alerts", "Reading IBTrACS Storm Data"

### C.3 SEO/인터랙티브 (낮음)
- Born-in Interactive 완성 (CO₂ / 기온 / 해빙 then vs now)
- Story Panel 프리셋 확장 (현재 1개 → 5~10개)
- CAMS Smoke 레이어 (Copernicus 계정 승인 후)
- Drought 레이어 (JRC WMS → Phase P1)

---

## Phase C.1 — API 키 등록 + 버그 수정 (`abbf159`, `0a14c54`, 2026-04-11) ✅

### 등록 완료 API 키 (.env + Render 환경변수)
- `AIRNOW_API_KEY` ✅, `FIRMS_MAP_KEY` ✅, `OPENAQ_API_KEY` ✅
- `CMEMS_USERNAME/PASSWORD` ✅, `GFW_API_KEY` ✅

### OpenAQ v3 API 마이그레이션 버그 수정 (`abbf159`)
- **발견**: `/v3/locations?parameters_id=2` → sensors에 `latest: null` (v3 마이그레이션 후 데이터 없음)
- **수정**: `/v3/parameters/2/latest` 엔드포인트로 전환 → **25,000개 실시간 PM2.5 스테이션**
- 결과: `count: 0` → **`count: 47`** (limit=100 기준, 실제 ~25k)

### CMEMS SLA 상태
- **현상**: THREDDS OPeNDAP → HTML 페이지 반환 (Cloudflare WAF 또는 ToU 미동의)
- **로컬**: HTTP 403 / error code: 1010 (Cloudflare가 Python 요청 차단)
- **Render 서버**: 200 HTML → parse 실패
- **조치**: `cmems.py`에 HTML 감지 추가 → 명확한 에러 메시지 (`0a14c54`)
- **해결책**: https://data.marine.copernicus.eu/ 로그인 → SEALEVEL_GLO_PHY_L4_NRT_008_046 Terms of Use 동의

---

## 블로커

| 항목 | 내용 | 해결 방법 |
|------|------|-----------|
| Render Free tier 슬립 | 15분 비활성 → 30초 cold start | UptimeRobot 핑 or Starter $7/월 전환 |
| CAMS Smoke | Copernicus ADS 계정 수동 승인 | 신청 완료 후 대기 |
| EPA AQS | 이메일 + 키 등록 필요 (10 req/min) | 등록 후 `epa_aqs_email/key` .env 추가 |
| FIRMS / OpenAQ | 키 미등록 → 해당 레이어 비활성 | 무료 등록 필요 |
| GFW API key | 연간 갱신 필요 (무료) | globalforestwatch.org 계정 생성 |
| CMEMS 계정 | 가입 후 `CMEMS_USERNAME/PASSWORD` | marine.copernicus.eu 무료 등록 |
| TROPOMI CH4 GIBS | GIBS 미지원 — `available=False` 마킹 | Copernicus GES DISC `S5P_L2__CH4____HiR` 대안 |
