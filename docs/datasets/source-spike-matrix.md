# TerraSight v2 — Source Spike Matrix

**작성일:** 2026-04-17
**상태:** 승인 (Phase: v2 Architecture Reset — Step 2 완료)
**목적:** v2 MVP 및 Phase 4+ 배치 파이프라인에 편입될 모든 데이터 소스를 7개 축 (auth · rate-limit · coverage · cadence · latency · payload · client-direct) 으로 고정한다.

**Related docs:**
- 정책: `docs/architecture/data-source-policy.md`
- 레이어 최종안: `docs/datasets/gibs-approved-layers.md`
- 런타임/배치 경계: `docs/datasets/runtime-vs-batch-sources.md`
- v1 spike 원본: `docs/api-spike-results.md`
- Landmines: `docs/guardrails.md`

---

## 1. Tier 1 — Production Runtime (MVP)

### 1.1 Browser-direct (GIBS imagery)

| Source / Layer | Auth | Rate-limit | Coverage | Cadence | Latency | Payload | Client-direct | Status |
|---|---|---|---|---|---|---|---|---|
| `BlueMarble_ShadedRelief_Bathymetry` | 없음 | CDN 무제한 | global | monthly (static) | n/a | JPG tile ~20KB | ✅ yes | ✅ GO |
| `GHRSST_L4_MUR_Sea_Surface_Temperature` | 없음 | CDN 무제한 | ocean-only | daily | 1-day lag | PNG tile ~30-80KB | ✅ yes | ✅ GO |
| `MODIS_Terra_Aerosol` | 없음 | CDN 무제한 | global | daily | same-day | PNG tile ~30KB | ✅ yes | ✅ GO (**라벨: 에어로졸 프록시**) |
| `MODIS_Aqua_Cloud_Fraction_Day` | 없음 | CDN 무제한 | global (day-only) | daily | same-day | PNG tile ~20KB | ✅ yes | ✅ GO |
| `VIIRS_SNPP_DayNightBand` | 없음 | CDN 무제한 | global | daily | 1-day lag | PNG tile ~40KB | ✅ yes | ✅ GO (**`_ENCC` 금지 — 2023-07-07 FROZEN**) |

**공통:**
- `TileMatrixSet` 은 레이어별로 다름 (`500m`/`1km`/`2km`). 하드코딩 금지, 레이어 매니페스트에서 읽는다.
- 날짜 포맷은 `YYYY-MM-DD` 만 허용. ISO 8601 `T00:00:00Z` 불가.
- CesiumJS 1.140 에서 `WebMapTileServiceImageryProvider.fromUrl()` 비동기. REST 템플릿 형태 권장.

### 1.2 Worker-proxied events

| Source | Auth | Rate-limit | Coverage | Cadence | Latency | Payload | Client-direct | Status |
|---|---|---|---|---|---|---|---|---|
| FIRMS VIIRS_SNPP_NRT | MAP_KEY (free) | 5000 tx / 10min / key | global (bbox) | ~3h | ~3h from overpass | CSV 500KB–2MB / 전역 1일 | ❌ (키 숨김) | ✅ GO |
| USGS Earthquakes (summary feed) | 없음 | 없음 | global | ~1-5 min 재생성 | 거의 실시간 | GeoJSON ~180KB (all_day, 271 feat) | ❌ (bbox/caching) | ✅ GO |
| NOAA OISST (ERDDAP point) | 없음 | 없음 (polite) | ocean 0.25° | daily | 1-day (NRT) / 14d (final) | JSON ~1KB/point | ❌ (lon 변환) | ✅ GO |
| CRW DHW (ERDDAP point) | 없음 | 없음 (polite) | global 0.05° | daily | 1-day | JSON ~1KB/point | ❌ (lon 변환) | ✅ GO (**host 수정 완료 — 아래 참조**) |

**공통:**
- ERDDAP longitude 는 0-360°. `lon_erddap = user_lon < 0 ? user_lon + 360 : user_lon`.
- OISST 는 `zlev=(0.0)` 차원 필수. DHW 는 zlev 없음.
- Worker 는 프록시 + 캐시만. 조합/계산 금지.

**Worker endpoint 최종:**
```
GET /api/fires?bbox=w,s,e,n&days=1        — cache 10min
GET /api/earthquakes?period=day&magnitude=all — cache 5min
GET /api/sst-point?lat=..&lon=..          — cache 1h
GET /api/dhw-point?lat=..&lon=..          — cache 6h (선택, Atlas 용)
```

---

## 2. Tier 2 — Reports Static (빌드타임 fan-out)

모두 **GitHub Actions 빌드 잡**에서 호출 → `data/reports/<slug>.json` 저장 → Astro `getStaticPaths` 가 읽음.
v1 spike 결과 유효 (2026-03/04 verified) — v2 에서 재확인 불필요.

| Source | Auth | Notes (v1 spike) | Status |
|---|---|---|---|
| AirNow | 무료 API key | 10 req/min | ✅ GO |
| EPA AQS / AirData | 무료 API key | 10 req/min | ✅ GO |
| NOAA Climate Normals (NCEI) | 없음 | 1991-2020 | ✅ GO |
| NWS Alerts | 없음 (UA 필수) | zone / county 필터 | ✅ GO |
| USDM (Drought) | 없음 (`Accept: application/json`) | weekly | ✅ GO |
| OpenFEMA | 없음 | state 코드 2자 | ✅ GO |
| SDWIS (Envirofacts) | 없음 | mandatory pagination | ✅ GO |
| WQP wqx3 | 없음 | `/wqx3/` beta, `providers` 반복 | ✅ GO |
| EPA ECHO | 없음 (UA 필수) | two-hop | ✅ GO |
| EPA GHGRP | 없음 | Envirofacts pagination | ✅ GO |
| EPA TRI | 없음 | 좌표 신뢰도 낮음 | ✅ GO |
| EPA Superfund | 없음 | FeatureServer polygon → centroid | ✅ GO |
| EPA Brownfields | 없음 | ArcGIS `inSR=4326` | ✅ GO |
| EPA RCRA (BR_REPORTING) | 없음 | year filter 필수 | ✅ GO |
| PFAS (State PAT) | 없음 | layer 1, `" TX"` strip | ✅ GO (선택) |
| NOAA CO-OPS | 없음 | mdapi lat=0 필터 | ✅ GO (선택) |
| NOAA GML (CO₂ / CH₄) | 없음 | Mauna Loa, Barrow | ✅ GO |
| NOAAGlobalTemp CDR | 없음 | monthly anomaly | ✅ GO |
| NSIDC G02135 | 없음 | CSV comma 이슈 | ✅ GO |
| NOAA NESDIS GMSL | 없음 | star.nesdis 간헐 502 | ✅ GO (재시도 필수) |
| CRW ERDDAP (DHW) | 없음 | **정확한 host: `oceanwatch.pifsc.noaa.gov`** | ✅ GO (수정됨) |
| Climate TRACE | 없음 | ≥ 10 MB dump | ✅ GO |
| Global Forest Watch | API key | Origin 헤더 필수 | ✅ GO |

---

## 3. Tier 3 — Phase 4+ Batch Pipeline (GitHub Actions cron → R2)

| Source | Auth | Rate-limit | Coverage | Cadence | Latency | Payload | Client-direct | Status |
|---|---|---|---|---|---|---|---|---|
| **CAMS Global (ADS)** | PAT + per-dataset ToU | 큐 5-30min (최대 2h+) | global 0.4° | 2×/day (00, 12 UTC) | ~6h | ~0.5MB/timestep GRIB2; daily 8-step ~4MB | ❌ 배치 | ✅ Phase 4 |
| **ERA5 (CDS)** | PAT + per-dataset ToU | 큐 2-10min (disk) / hrs-days (MARS) | global 0.25° | monthly (days ~5) | ERA5T 5d / ERA5 3mo | ~1MB/var GRIB; 4-var monthly ~6MB | ❌ 배치 | ✅ Phase 4 |
| **GFS (NOMADS)** | 없음 | 제한 없음 (polite) | global 0.25° | 4×/day (00/06/12/18) | ~3.5-4h | 전체 f000 **477MB**; filter 서비스 사용 시 5-var ~4MB | ❌ 배치 | ✅ Phase 4 (**1순위**) |

**Phase 4+ 구현 순서 (우선 낮은 → 높은):**
1. **GFS** — 무인증, 큐 없음, 4×/day. `filter_gfs_0p25.pl` 서브셋 서비스 사용 필수 (풀 파일 477MB).
2. **CAMS** — PM2.5 / NO₂ 는 GFS 와 겹치지 않음. PM2.5 는 composite variable `particulate_matter_d_less_than_2p5_um` (수동 합산 금지).
3. **ERA5** — 월평균만. 실시간 대시보드 가치 낮음. Climatology / anomaly 오버레이 용.

**공통 런타임:**
- GitHub Actions `ubuntu-latest` (7GB RAM, 6h max). 모든 잡 예상 소요 5-55 min, 메모리 800MB 피크 → 헤드룸 충분.
- `cfgrib` (GFS) 는 `libeccodes-dev` apt install 필수.
- 렌더링: `xarray` + `matplotlib` + `cartopy` → PNG → R2 업로드.
- ERA5 / CAMS cdsapi 설정 파일 (`~/.cdsapirc`) 의 URL 은 **반드시 다르다** (ADS 와 CDS 는 별도 서버).

---

## 4. 🔴 Excluded (프로덕션 제외)

| Excluded | 이유 | 대체 |
|---|---|---|
| Open-Meteo (모든 엔드포인트) | Rate limit + cold-start 캐시 소실 | CAMS 배치 (PM2.5/NO₂), GFS 배치 (Temp/Wind) |
| Runtime numpy/scipy PNG 렌더 | Render Free 512MB 초과 | GIBS 직접 로드 / GH Actions 배치 |
| Runtime Report fan-out | 커넥터 하나 실패로 block 타임아웃 | 빌드타임 정적 `report.json` |
| Cesium Ion 상업 플랜 | 무료 쿼터로 충분 | BlueMarble + GIBS |

---

## 5. Trust Tag 할당 (재확인)

| Layer / Source | Tag | 근거 |
|---|---|---|
| BlueMarble, SST, AOD, Clouds, Night Lights, OISST | `observed` / `near-real-time` | 직접 관측 또는 위성 복사도 |
| FIRMS | `near-real-time` | ~3h cadence, satellite overpass |
| USGS Earthquakes | `observed` | instrument detection |
| CRW DHW | `derived` | 관측값에서 계산 (accumulated stress) |
| CAMS | `near-real-time` (~6h) / `forecast` (미래 stride) | 분석 + 예측 혼합 |
| ERA5 | `derived` | reanalysis = 관측 + 모델 |
| GFS | `forecast` | 모델 예측 |
| AirNow | `near-real-time` | hourly |
| AQS, Climate Normals, ECHO, GHGRP, TRI | `observed` / `derived` / `compliance` | per-source |

---

## 6. 변경 이력

| 날짜 | 변경 | 근거 |
|---|---|---|
| 2026-04-17 | `VIIRS_SNPP_DayNightBand_ENCC` → `VIIRS_SNPP_DayNightBand` (FROZEN 2023-07-07) | Agent 1 probe 결과 |
| 2026-04-17 | CRW DHW host: `pae-paha.pacioos.hawaii.edu` → `oceanwatch.pifsc.noaa.gov/erddap`, datasetID `CRW_dhw_v1_0` | Agent 3 live probe |
| 2026-04-17 | GFS filter 서비스 (`filter_gfs_0p25.pl`) 의무화 | Agent 4: 풀 파일 477MB → 필터 5-var 4MB |
| 2026-04-17 | ERA5 cdsapirc 신형 PAT 포맷 (`key: UID:API_KEY` colon 폐기) | Agent 4: 2024+ 변경 |
