# TerraSight v2 — MVP Scope

**작성일:** 2026-04-17
**상태:** 승인 (Phase: v2 Architecture Reset)
**목적:** Globe Lite 6 레이어 + Reports Static 핵심 8 블록을 고정해 범위 폭주를 방지한다.

---

## 1. MVP 정의

**MVP = "항상 뜨는" 전지구 관측 포털 + 3개 샘플 도시 정적 Report + 8개 Atlas 카테고리 레지스트리.**

MVP 는 수익화 전제가 아니라 **출시 가능한 하한선**이다. 출시 이후 Phase 4+ 에서 레이어와 블록을 확장한다.

---

## 2. Tier 1 — Globe Lite: MVP 6 레이어

> Layer composition rule: 한 번에 **1 continuous + 1 event** 동시 최대.

| # | Layer | Source | Kind | TrustTag | Coverage | Cadence | Click/Hover |
|---|-------|--------|------|----------|----------|---------|-------------|
| 1 | Sea Surface Temperature | GIBS GHRSST MUR L4 | imagery | observed | ocean-only | daily | ✅ ERDDAP point query |
| 2 | Aerosol Optical Depth / Haze | GIBS MODIS Terra AOD 3km | imagery | observed | land+ocean | daily | 설명만 |
| 3 | Clouds | GIBS MODIS Aqua Cloud Fraction | imagery | observed | global | daily | 설명만 |
| 4 | Night Lights | GIBS VIIRS DNB ENCC | imagery | observed | land+coast | daily | 설명만 |
| 5 | Wildfires | FIRMS (Worker API) | event | near-real-time | global | 3h | ✅ popup (FRP, confidence) |
| 6 | Earthquakes | USGS (Worker API) | event | observed | global | 5min | ✅ popup (magnitude, depth) |

### Globe UI 요구
- 하단 카테고리 탭 6개 (imagery 4 + event 2)
- 좌하단 공통 스타일 범례 (단위 · 값 범위 · 반투명 다크 배경)
- Trust Tag 뱃지를 레이어 이름 옆에 노출
- AOD 는 반드시 **"에어로졸 프록시"** 로 라벨 (PM2.5 로 오독 방지)
- Night Lights 는 **"인간 활동 프록시"** 로 라벨 (전력 소비 직접 측정 아님)

### 클릭 조회 정책
| Layer | Click Behavior |
|-------|----------------|
| SST | ERDDAP point query → 실제 온도 °C 표시 |
| AOD / Clouds / Night Lights | 값 조회 없이 "이 레이어가 무엇인지" 설명 카드 |
| Wildfires | Entity popup (lat/lon, FRP, confidence, observedAt) |
| Earthquakes | Entity popup (magnitude, depth, place, observedAt) |

---

## 3. Tier 2 — Atlas Lite: 8 카테고리 (Phase 1 범위 유지)

| # | Category | Phase 1 Live Datasets | Goal |
|---|----------|-----------------------|------|
| 1 | Air & Atmosphere | AirNow, AirData (AQS), GIBS AOD | 4 |
| 2 | Water Quality, Drinking Water & Wastewater | WQP, SDWIS | 3 |
| 3 | Hydrology & Floods | USGS OGC | 2 |
| 4 | Coast & Ocean | OISST, CRW DHW, CO-OPS | 3 |
| 5 | Soil, Land & Site Condition | Superfund, Brownfields, GFW | 3 |
| 6 | Waste & Materials | TRI, RCRA | 2 |
| 7 | Emissions, Energy & Facilities | ECHO, GHGRP, Climate TRACE | 3 |
| 8 | Climate, Hazards & Exposure | NOAA Climate Normals, NWS Alerts, USDM, OpenFEMA, PFAS | 5 |

> 상세 데이터셋 레지스트리 스키마는 `packages/schemas/dataset.ts` 의 `DatasetRegistryItem`.

### Atlas 페이지 필수 필드
- 측정 대상 (variable)
- sourceType (`satellite` / `model` / `regulatory` / `inventory`)
- TrustTag
- geographicCoverage · cadence · resolution · license · sourceUrl
- caveats[] — 최소 1개 이상
- linkedLayers[] — 연결된 Globe Layer id
- linkedReportBlocks[] — 연결된 Report block id

---

## 4. Tier 3 — Reports Static: 핵심 8 블록 + 선택 확장

### 4.1 핵심 8 블록 (모든 Report 에 고정)

| # | Block ID | Title | 주 데이터 소스 | TrustTag | Mandatory Disclaimer |
|---|----------|-------|---------------|----------|---------------------|
| 1 | `air` | 대기질 | AirNow (Now) + AQS (Trend) | near-real-time + observed | AirNow: "Reporting area ≠ CBSA" |
| 2 | `climate` | 기후 · 열환경 | NOAA Climate Normals 1991-2020 | derived | — |
| 3 | `hazards` | 재해 노출 | NWS Alerts + USDM + OpenFEMA | near-real-time + derived | — |
| 4 | `water` | 음용수 · 수질 | SDWIS (compliance) + WQP (samples) | compliance + observed | WQP: "Discrete samples — dates vary" |
| 5 | `facilities` | 산업시설 · 배출 | ECHO + GHGRP + TRI | compliance + observed | ECHO: "compliance ≠ exposure" |
| 6 | `sites` | 오염부지 · 정화 | Superfund + Brownfields + RCRA | compliance | — |
| 7 | `equity` | 인구 노출 · 환경정의 | EJScreen(예정) + census | derived | EJScreen disclaimer 예정 |
| 8 | `methodology` | 방법론 · 데이터 신뢰 | (메타블록) | — | 전체 출처 · 계산식 · 한계 명시 |

### 4.2 선택 확장 블록 (도시별 on/off, 빌드 시점 결정)

| Block ID | Condition | Notes |
|----------|-----------|-------|
| `pfas` | 주 PWS 가 PFAS 보고 데이터 존재 | PFAS 커넥터 출력 기반 |
| `coastal` | `is_coastal_metro=true` (CBSA 메타) | CO-OPS 수위 · 해안 해발고도 |
| `hazard-history` | 과거 10년 major declaration ≥ 3 | OpenFEMA 이력 상세 |
| `comparison` | always (related metros) | 동일 region 또는 유사 인구 |
| `related` | always | 동일 주 또는 인접 CBSA 링크 |

### 4.3 Report 데이터 없음 정책
- 블록 핵심 지표가 없으면 **블록 숨김** (getStaticPaths 단계에서 필터링)
- 부차 지표가 없으면 **"데이터 없음 — 출처/시기"** 문구 고정
- thin content 방지: 각 블록 최소 콘텐츠 기준 60자 이상 서술 필수

### 4.4 MVP Report 샘플 (검증용 3 도시)
- New York–Newark–Jersey City, NY-NJ-PA (대규모 · 해안)
- Houston–The Woodlands–Sugar Land, TX (산업 · 재해)
- Los Angeles–Long Beach–Anaheim, CA (대기질 · 해안)

샘플 3 도시가 모두 schema validation 통과하고 정적 렌더링되면 MVP 출시 가능. 이후 50 CBSA 확장은 동일 파이프라인 반복.

---

## 5. MVP 에서 제외된 것 (그리고 왜)

| Excluded | 이유 | 복귀 조건 |
|----------|------|-----------|
| PM2.5 (Open-Meteo) | API rate limit + cold start 캐시 소실 | CAMS 직접 파이프라인 가동 후 |
| Temperature (Open-Meteo) | 동상 | GFS GRIB2 배치 파이프라인 |
| Precipitation (Open-Meteo) | 동상 | GFS 배치 |
| NO₂ (Open-Meteo) | 동상 | CAMS 배치 |
| 실시간 해류 파티클 | Open-Meteo Marine 의존 | CMEMS 계정 + 배치 프레임 |
| Wind particle | 데이터 파이프라인 미구축 | GFS 배치 |
| SST advection frames | Render 메모리 초과 | GitHub Actions 외부 렌더링 → R2 |
| Flood detection (GIBS) | GIBS 제품 자체 불안정 | 대체 제품 검토 |
| Storm tracks | 활성 폭풍 없을 때 빈 UI | "현재 활성 폭풍 N개" 조건부 노출 정책 확립 후 |
| OCO-2 Total Column CO₂ | 궤도 swath 3~5% 커버리지 오해 | 명시적 "궤도 관측 구역" 라벨 UX 확정 후 |
| Atlas 인터랙티브 탐색기 | MVP 범위 폭주 | Reports/Globe 안정화 후 |
| Report PFAS / Coast / Hazard history | 선택 확장 블록 | 도시별 조건부 — MVP 에서는 off |
| Report City comparison / Related | UX 설계 미정 | v2 UX 라운드 후 |

---

## 6. MVP 수락 기준 (Go/No-Go)

- [ ] Globe Lite 6 레이어 모두 브라우저 로드 성공
- [ ] Worker API 3 엔드포인트 (fires / earthquakes / sst-point) 응답 200
- [ ] 샘플 3 도시 Report `getStaticPaths` 로 정적 렌더링 성공
- [ ] 8 Atlas 카테고리 페이지 모두 렌더 가능 (빈 데이터셋 0 개)
- [ ] 모든 블록에 Trust Tag + updatedAt + citations 존재
- [ ] Mandatory disclaimers (ECHO/WQP/AirNow) 관련 블록에 누락 없이 렌더
- [ ] `packages/schemas/` zod 검증 전수 통과
- [ ] `apps/web` main bundle < 200KB gzipped (홈 라우트)
- [ ] sitemap.xml · robots.txt 정상
- [ ] Lighthouse SEO score > 90 (홈 + Report 샘플)

---

## 7. 관련 문서

- 아키텍처: `docs/architecture/architecture-v2.md`
- 데이터 소스 정책: `docs/architecture/data-source-policy.md`
- Report 스키마 (작성 예정 Step 5): `docs/reports/report-schema.md`
- Report 블록 정책 (작성 예정 Step 5): `docs/reports/report-block-policy.md`
