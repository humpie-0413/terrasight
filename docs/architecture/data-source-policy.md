# TerraSight v2 — Data Source Policy

**작성일:** 2026-04-17
**상태:** 승인 (Phase: v2 Architecture Reset)
**목적:** 어떤 데이터 소스가 프로덕션 승인 / 보류 / 금지인지 단일 기준으로 고정한다.

---

## 1. 등급 체계

### 🟢 1순위 — 프로덕션 승인 (MVP)
무인증 또는 공개 키 · 안정 · 글로벌 커버리지.

| Source | Layers/Blocks | TrustTag | Auth | Rate Limit | Landmines |
|--------|---------------|----------|------|-----------|-----------|
| NASA GIBS | SST · AOD · Clouds · Night Lights · (OCO-2 보류) · (CO₂ 보류) | observed | 없음 | 실질 무제한 | CesiumJS 1.140 `await fromUrl()` 비동기 주의 |
| NASA FIRMS | Wildfires | near-real-time | MAP_KEY (무료) | 소량 | bbox fan-out, 3h cadence |
| USGS | Earthquakes, Hydrology (OGC API) | observed / near-real-time | 없음 | 소량 | feature 에 `site_name` 누락 → `monitoring_location_id` fallback |
| NOAA ERDDAP | SST point query (OISST) | observed | 없음 | 소량 | griddap URL 구조, stride 지정 필수 |

### 🟡 2순위 — 프로덕션 승인 (Reports)
정부 무인증 또는 무료 계정 데이터. 각 소스의 landmine 은 `docs/guardrails.md` 참조.

| Source | Reports Block | TrustTag | Auth |
|--------|---------------|----------|------|
| AirNow | `air` (Now) | near-real-time | 무료 키 |
| EPA AQS / AirData | `air` (Trend) | observed | 무료 키, 10 req/min |
| NOAA Climate Normals (NCEI) | `climate` | derived | 없음 |
| NWS Alerts | `hazards` | near-real-time | 없음 (UA 헤더 필수) |
| USDM (Drought) | `hazards` | observed | 없음 (`Accept: application/json` 필수) |
| OpenFEMA | `hazards` | compliance | 없음 (state 코드 2자) |
| SDWIS (Envirofacts) | `water` | compliance | 없음 (mandatory pagination) |
| WQP (Water Quality Portal) | `water` | observed | 없음 (`/wqx3/` beta, `providers` 반복) |
| EPA ECHO | `facilities` | compliance | 없음 (echodata.epa.gov, UA 필수, two-hop) |
| EPA GHGRP | `facilities` | compliance | 없음 (Envirofacts pagination) |
| EPA TRI | `facilities`, `sites` | compliance | 없음 (좌표 신뢰도 낮음) |
| EPA Superfund | `sites` | compliance | 없음 (FeatureServer polygon → centroid) |
| EPA Brownfields | `sites` | compliance | 없음 (ArcGIS `inSR=4326`) |
| EPA RCRA (BR_REPORTING) | `sites` | compliance | 없음 (year filter 필수) |
| PFAS (State PAT) | `pfas` (선택) | observed | 없음 (layer 1, `" TX"` strip) |
| NOAA CO-OPS | `coastal` (선택) | observed | 없음 (mdapi lat=0 필터) |
| NOAA GML (CO₂ / CH₄) | Climate Trends | observed | 없음 |
| NOAAGlobalTemp CDR | Climate Trends | derived | 없음 |
| NSIDC G02135 | Climate Trends | observed | 없음 (CSV comma 이슈) |
| NOAA NESDIS GMSL | Climate Trends | derived | 없음 (star.nesdis 간헐적 502) |
| CRW ERDDAP (DHW) | Atlas: Coast & Ocean | derived | 없음 (URL 미스매치 버그 주의) |
| Climate TRACE | `facilities` | derived | 없음 |
| Global Forest Watch | Atlas: Soil/Land | observed | API key (Origin 헤더 필수) |

### 🟠 3순위 — 후속 배치 파이프라인 (Phase 4+)
무료 계정 필요 또는 GRIB2 파이프라인 구축 필요. **GitHub Actions cron 에서만** 호출.

| Source | Target Use | Auth | Notes |
|--------|-----------|------|-------|
| CAMS Global (Copernicus ADS) | PM2.5 · NO₂ · O₃ 격자 | ADS 계정 + cdsapi | netCDF → PNG → R2 |
| ERA5 (Copernicus CDS) | Temperature · Wind · Precip | CDS 계정 + cdsapi | 월별 대용량 |
| GFS (NOAA NOMADS) | Temperature · Wind forecasts | 없음 | GRIB2 → cfgrib + xarray |
| CMEMS (Copernicus Marine) | 해류 · SLA | CMEMS 계정 | 파티클 프레임 외부 렌더링 |

---

## 2. 🔴 프로덕션 제외 (MVP 이후에도 유지)

| Excluded | 이유 | 대체 |
|----------|------|------|
| **Open-Meteo** (모든 엔드포인트) | Rate limit + cold start 캐시 소실로 프로덕션 불안정. 참고용으로만 유지. | 1순위 소스 우선, 후속 배치 파이프라인으로 대체 |
| **요청 시점 numpy/scipy PNG 렌더링** | Render Free 512MB 초과, cold start 10~30s | GIBS 직접 로드 또는 배치 렌더 → R2 |
| **요청 시점 Report 조립 (fan-out)** | 커넥터 하나 실패로 전체 블록 타임아웃 | 빌드타임 `report.json` 정적 생성 |
| **Cesium Ion 상업 플랜 의존** | 무료 쿼터로 충분, 결제 의존 피함 | 기본 위성 이미지만 사용 |

---

## 3. Trust Tag 매핑 규칙

| Tag | 정의 | 적용 예 |
|-----|------|--------|
| `observed` | 직접 관측 (계기 측정, 위성 복사도) | AirNow, USGS, GIBS SST |
| `near-real-time` | 수 시간 내 처리된 관측 | FIRMS, NWS Alerts |
| `forecast` | 모델 예측 출력 | GFS, ERA5 reanalysis 는 아님 |
| `derived` | 관측값에서 계산 | Climate Normals, DHW, 이상치 |
| `compliance` | 규제 보고 데이터 | ECHO, SDWIS, TRI, Superfund |

### Tag 충돌 시 우선순위
- 관측이 규제보고에 병합된 경우 → `observed` 우선 (예: AQS)
- 모델이 관측으로 보정된 경우 → `derived`
- "실시간"이란 단어를 쓰려면 cadence < 3h 여야 함

---

## 4. 캐시 TTL 정책 (Cloudflare Worker)

| Endpoint | TTL | 근거 |
|----------|-----|------|
| `/api/fires` (FIRMS) | 10 min | FIRMS 자체 갱신 3h, 단 bbox 다양성 대응 |
| `/api/earthquakes` (USGS) | 5 min | 이벤트 발생 즉각성 |
| `/api/sst-point` (ERDDAP) | 1 h | OISST daily 갱신 |
| GIBS imagery | 브라우저 캐시만 (Worker 경유 금지) | 직접 로드 |

**규칙:** Worker 는 프록시 + 캐시만. 조합/계산 금지.

---

## 5. 표기 규칙 (라벨 · 단위 · 주의문)

### 오해 방지 라벨 (강제)
| 데이터 | 표시 라벨 | 금지 표현 |
|--------|----------|----------|
| GIBS AOD | "에어로졸 프록시 / Aerosol Proxy" | "PM2.5", "미세먼지" (직접 측정 아님) |
| OCO-2 | "Total Column CO₂" + "궤도 관측 구역" | "전지구 CO₂" (3~5% 커버리지) |
| MERRA-2 월평균 | "월평균 / Monthly" + cadence 표기 | "현재" |
| VIIRS DNB | "인간 활동 프록시" | "전력 소비량" |
| EPA ECHO | "규제 준수 지표" + "compliance ≠ exposure" disclaimer | "환경 위험도" |
| WQP 샘플 | "Discrete samples — dates vary" | "실시간 수질" |
| AirNow | "Reporting area ≠ CBSA" | "CBSA 공기질" |

### 단위
- 온도: °C (Fahrenheit 보조 표시 허용)
- 대기질: µg/m³ (AQI 점수는 AirNow 출처만)
- CO₂: ppm
- 해수면: mm
- 길이/거리: km

### Mandatory Disclaimers (non-removable)
- **ECHO:** "Regulatory compliance ≠ environmental exposure or health risk."
- **WQP:** "Discrete samples — dates vary."
- **AirNow:** "Reporting area ≠ CBSA boundary."

---

## 6. Graceful Degradation (필수)

### 응답 status 필드 (공통)
```ts
type BlockStatus = 'ok' | 'error' | 'not_configured' | 'pending';
```

### 커넥터 계약
- 인증 키 부재 → `status: 'not_configured'` + 설명
- 업스트림 타임아웃/502 → `status: 'error'` + retryable 플래그
- 미구현 기능 → `status: 'pending'`
- 성공 → `status: 'ok'` + 데이터

### UI 계약
- `not_configured` → 설정 안내 (admin 만 볼 수 있게 hidden 가능)
- `error` → 재시도 버튼 + 원인 요약
- `pending` → "곧 공개" 뱃지
- `ok` 이외 모든 상태에서 **layout collapse 금지**

### 절대 금지
- Report 페이지가 5xx 를 사용자에게 노출
- 빈 Globe 레이어가 placeholder 없이 검은 화면
- 광고 슬롯이 데이터 미도착으로 겹치기

---

## 7. 신규 소스 추가 절차

1. `docs/datasets/source-spike-matrix.md` 에 auth · rate · coverage · cadence · latency · payload · client-direct 7개 축으로 기록
2. Trust Tag 후보 + caveat 초안
3. `packages/schemas/` 에 normalized contract 추가
4. `pipelines/connectors/` 에 커넥터 + fixture
5. 계약 테스트 (`pipelines/tests/test_<name>_contract.py`)
6. landmine 발견 시 **즉시** `docs/guardrails.md` + 커넥터 docstring 에 기록
7. `progress.md` 업데이트

---

## 8. 관련 문서

- 아키텍처: `docs/architecture/architecture-v2.md`
- MVP 범위: `docs/architecture/mvp-scope-v2.md`
- 기존 landmines: `docs/guardrails.md`
- Spike 결과 (v1): `docs/api-spike-results.md`
