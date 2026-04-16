# TerraSight Globe — 구상안 및 현황 (2026-04-16)

## 비전

전지구 환경 데이터를 실시간으로 3D 지구본 위에 시각화하는 포털.
earth.nullschool.net 수준의 연속 표면 + 데이터 인터랙션.

---

## 현재 구현된 것 vs 실제 동작 상태

### Globe 엔진
| 항목 | 상태 | 비고 |
|------|------|------|
| CesiumJS Globe 렌더링 | ✅ 동작 | Cesium Ion 위성 기본 이미지 표시 |
| 3D/2D 전환 | ✅ 동작 | morphTo3D/morphTo2D |
| 자동 회전 | ✅ 동작 | 8초 idle 후 |
| 카테고리 탭 UI | ✅ 동작 | 8개 탭 (LayerBar) |
| 범례 표시 | ✅ 동작 | 카테고리별 색상 바 |
| 투명 헤더 | ✅ 동작 | Globe 위 floating |

### 데이터 레이어 — 실제 동작 여부
| 레이어 | 코드 있음 | 실제 동작 | 실패 원인 |
|--------|---------|---------|---------|
| **SST (해수 온도)** | ✅ | ❌ 안 보임 | advection 렌더링이 Render 512MB 초과 (OISST 43K pts × 8 frames × numpy/scipy) |
| **SST 클릭 온도 조회** | ✅ | ✅ 동작 | ERDDAP 직접 쿼리, 가벼움 |
| **해류 파티클** | ✅ | ❌ 미확인 | Ocean currents API 타임아웃 (Open-Meteo rate limit) |
| **PM2.5** | ✅ | ❌ 안 보임 | Open-Meteo 타임아웃 / rate limit |
| **Temperature** | ✅ | ❌ 안 보임 | Open-Meteo 타임아웃 |
| **Precipitation** | ✅ | ❌ 안 보임 | Open-Meteo 타임아웃 |
| **NO₂** | ✅ | ❌ 안 보임 | Open-Meteo 타임아웃 |
| **Wildfires** | ✅ | ✅ 동작 | NASA FIRMS (자체 API 키) |
| **Earthquakes** | ✅ | ✅ 동작 | USGS (무인증, 안정) |
| **CO₂ (OCO-2)** | ✅ | ❌ 미확인 | GIBS WMS → SingleTile async 전환 후 미검증 |

### 근본 문제 3가지

1. **Render Free Tier 메모리 한계 (512MB)**
   - SST advection: 43K pts × 8 frames × numpy array = ~400MB+ peak → 502
   - 자체 렌더링 PNG (pm25, temp 등)도 비슷한 문제

2. **Open-Meteo 무료 API rate limit**
   - 시간당 5,000 호출, 일일 10,000 호출
   - 전지구 5° 격자 = 2,664 포인트 × 3 배치 = 3 API 호출/레이어
   - 5개 레이어 × 3 = 15 호출/갱신 → 정상 범위지만
   - 개발 중 연구 에이전트가 수백 호출 → rate limit 소진
   - 캐시 6시간이지만 Render cold start 시 캐시 소실

3. **CesiumJS 1.140 비동기 API**
   - `SingleTileImageryProvider`가 `await fromUrl()` 필요
   - 코드에 적용했지만 실제 배포 환경에서 검증 부족

---

## 구상안: 실제로 동작하게 만드는 방법

### Phase 1: "확실히 되는 것만" (즉시)

| 레이어 | 방법 | 왜 되는지 |
|--------|------|---------|
| **SST** | GIBS WMS 단일 이미지 (정적, 애니메이션 없음) | GIBS는 무인증, 안정, land mask 내장. advection 제거. |
| **Wildfires** | 현행 유지 (FIRMS API) | 이미 동작 중 |
| **Earthquakes** | 현행 유지 (USGS API) | 이미 동작 중 |
| **CO₂** | GIBS WMS 단일 이미지 | GIBS 무인증 |

**제거 대상:**
- PM2.5, Temperature, Precipitation, NO₂ (Open-Meteo 의존 → 불안정)
- SST advection (메모리 초과)
- 해류 파티클 (데이터 없이 과학모델만 가능하지만 우선순위 낮음)

**결과:** Globe에 SST + Fires + Earthquakes + CO₂ = 4개 레이어 확실히 동작.

### Phase 2: "GIBS 최대 활용" (1주)

GIBS에서 무인증으로 가져올 수 있는 모든 레이어 추가:

| GIBS 레이어 | 카테고리 | 해상도 | 갱신 |
|------------|---------|--------|------|
| GHRSST_L4_MUR_Sea_Surface_Temperature | Ocean | 1km | Daily |
| MODIS_Terra_Aerosol_Optical_Depth_3km | Air Quality | 3km | Daily |
| MODIS_Combined_Flood_2-Day | Floods | 250m | 2-Day |
| OCO2_L2_CO2_Total_Column_Day | CO₂ | 2km | Daily |
| MERRA2_2m_Temperature_Monthly | Temperature | ~50km | Monthly |
| MODIS_Aqua_Cloud_Fraction_Day | Clouds | 1km | Daily |
| VIIRS_SNPP_DayNightBand_ENCC | Night Lights | 500m | Daily |

**장점:**
- 전부 무인증
- land mask 내장 (해양 레이어)
- CesiumJS WMS SingleTile로 안정적 로드
- 백엔드 렌더링 불필요 → Render 메모리 이슈 없음

**단점:**
- NASA의 colormap 사용 (커스텀 불가)
- 실시간이 아닌 1-2일 지연
- 격자 해상도가 제품마다 다름

### Phase 3: "고급 시각화" (2-4주)

**해류 파티클 (earth.nullschool 스타일)**

선택지:
| 방법 | 노력 | 품질 |
|------|------|------|
| A. OSCAR ERDDAP (2018년까지) + climatological 해류 모델 | 중 | 중 |
| B. Copernicus Marine (CMEMS) 해류 데이터 | 대 (인증 필요) | 고 |
| C. 순수 과학 모델 기반 (위도별 무역풍/편서풍/ACC) | 소 | 낮음 |

권장: **C로 시작, B로 업그레이드** (CMEMS 계정 등록 후)

**SST 애니메이션**

선택지:
| 방법 | 노력 | 품질 |
|------|------|------|
| A. GIBS 7일 날짜 순환 (현재 시도 중) | 소 | 낮음 (변화 미미) |
| B. advection 프레임 (현재 시도, 메모리 초과) | 대 | 고 |
| C. WebGL 커스텀 셰이더 | 매우 대 | 매우 고 |
| D. 프레임을 외부 서버에서 사전 생성 | 중 | 고 |

권장: **D** — AWS Lambda 또는 GitHub Actions에서 cron으로 8 프레임 생성 → S3/R2에 업로드 → 프런트에서 로드

### Phase 4: "독자적 데이터 파이프라인" (1-2달)

Open-Meteo 대신 원천 데이터:
- **CAMS (Copernicus ADS)**: PM2.5, NO₂, O₃ — 계정 등록 필요
- **ERA5 (Copernicus CDS)**: 기온, 풍속, 강수 — 계정 등록 필요
- **GFS (NOAA NOMADS)**: 기온, 풍속 — 무인증, GRIB2 포맷

파이프라인:
```
GFS GRIB2 → cfgrib + xarray → numpy grid → surface_renderer PNG → S3/R2
(cron job, 외부 서버에서 실행)
```

---

## 기술 아키텍처 정리

```
┌─────────────────────────────────────────────────┐
│                  Frontend                        │
│  CesiumJS Globe + React UI                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │ Imagery  │ │ Points   │ │ Particle     │    │
│  │ Layers   │ │ DataSrc  │ │ Canvas       │    │
│  │ (SST,AQ) │ │ (Fire,EQ)│ │ (Currents)   │    │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘    │
│       │             │              │             │
└───────┼─────────────┼──────────────┼─────────────┘
        │             │              │
  ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
  │ GIBS WMS  │ │ Backend   │ │ Backend   │
  │ (NASA)    │ │ API       │ │ API       │
  │ 무인증     │ │ /fires    │ │ /currents │
  │ 안정      │ │ /quakes   │ │ (Open-Met)│
  └───────────┘ │ /sst-pt   │ └───────────┘
                └───────────┘
```

### Phase 1 아키텍처 (즉시 실행)

- SST/AQ/CO₂: **GIBS WMS → SingleTileImageryProvider** (백엔드 불필요)
- Fires: **Backend → FIRMS API** (이미 동작)
- Earthquakes: **Backend → USGS API** (이미 동작)
- SST 클릭: **Backend → OISST ERDDAP** (이미 동작)
- 파티클: 과학 모델 기반 (API 데이터 없이)

---

## 우선순위 로드맵

| 순서 | 작업 | 예상 시간 | 효과 |
|------|------|---------|------|
| 1 | SST를 GIBS WMS 정적 이미지로 롤백 | 30분 | Globe에 SST 즉시 표시 |
| 2 | 불안정 레이어 제거 (PM2.5/Temp/Precip/NO₂) | 30분 | 빈 화면 없앰 |
| 3 | GIBS 추가 레이어 (AOD, Night Lights, Clouds) | 2시간 | 데이터 다양성 |
| 4 | 해류 파티클 (과학 모델 기반, API 없이) | 2시간 | 비주얼 임팩트 |
| 5 | CMEMS 계정 등록 + 해류 실제 데이터 | 1일 | 과학적 정확성 |
| 6 | 외부 서버 SST advection 프레임 생성 | 2일 | 움직이는 SST |
| 7 | CAMS/ERA5 원천 데이터 연동 | 1주 | 자체 데이터 파이프라인 |

---

## 핵심 교훈

1. **Render Free Tier (512MB)에서 numpy/scipy 렌더링은 위험**
   - 43K pts × float64 × 8 frames = 메모리 초과
   - 해결: 렌더링을 외부로 이동하거나 GIBS 사전렌더 이미지 사용

2. **Open-Meteo 무료 API는 프로덕션에 부적합**
   - rate limit + cold start 캐시 소실 = 불안정
   - 해결: GIBS (무제한) 또는 원천 데이터 (CDS/NOMADS)

3. **GIBS가 가장 안정적인 데이터 소스**
   - 무인증, 무제한, land mask 내장, 다양한 제품
   - 단점: NASA colormap 고정, 1-2일 지연

4. **CesiumJS 비동기 API 주의**
   - v1.104+ 이후 모든 Provider가 async
   - `await fromUrl()` 패턴 필수
