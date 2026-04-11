# TerraSight — Progress Log

**최종 업데이트:** 2026-04-12 (Phase D.1 완료)

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
| Git commits | **47+** (Phase D.1 pending commit) |
| Backend connectors | **29개** (14 기존 + 14 글로벌 + 5 Phase D.1 EPA 규제/사이트) |
| API endpoints | **32개** (+5: releases/tri · releases/ghgrp · sites/superfund · sites/brownfields · drinking-water/sdwis) |
| Atlas 라이브 데이터셋 | **16개** (+5: tri · ghgrp · superfund · brownfields · sdwis) |
| Frontend components / pages | **~32개** |
| Local Reports metros | **50개** ✅ |
| Globe 레이어 | **13개** (5카테고리 어코디언) |
| Climate Trends 카드 | **5개** (CO₂ · Temp · Sea Ice · CH₄ · Sea Level) |
| Born-in 인터랙티브 | ✅ **완성** (연도 입력 → 3지표 비교) |
| Atlas 카테고리 | **8개** |
| SEO 랭킹 페이지 | **2개** |
| SEO 가이드 페이지 | **4개** |
| 번들 사이즈 | **599 KB gzipped** (600 KB 가드레일 이내) |
| 배포 스택 | Cloudflare Pages + Render (Docker) |

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

## 다음 단계 후보

### 높음
- **AdSense 신청** — 50개 리포트 + 6개 SEO 페이지로 조건 충족
- **CMEMS P1** — `copernicusmarine` 추가, Globe SLA 레이어 활성화

### 중간
- **추가 랭킹:** `/rankings/coral-bleaching`, `/rankings/ghg-emissions`
- **추가 가이드:** "Understanding Coral Bleaching", "Reading Storm Data"
- **Bundle 코드 스플리팅** — 현재 599 KB gzip (600 KB 가드레일 직전)

### 낮음
- **Story Panel 프리셋 확장** (1개 → 5~10개)
- **디자인 폴리시** (hover/애니메이션, 모바일 최적화)
