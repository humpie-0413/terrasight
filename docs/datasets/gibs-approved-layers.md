# TerraSight v2 — GIBS Approved Layers (MVP)

**작성일:** 2026-04-17
**상태:** 승인 (Phase: v2 Architecture Reset — Step 2 완료)
**목적:** MVP Globe 에서 **브라우저-다이렉트**로 로드되는 NASA GIBS 레이어를 단일 소스 오브 트루스로 고정한다. 레이어 추가/교체는 이 파일을 먼저 수정하고 커밋한다.

---

## 1. 공통 규칙

### 1.1 WMTS URL Template (REST 형태, KVP 금지)

```
https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/{LayerId}/default/{Date}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.{ext}
```

- 프로젝션: `epsg4326` (WGS84).
- 카탈로그: `best`. 다른 카탈로그 (`std`, `nrt`) 는 MVP 에서 사용하지 않는다.
- 날짜 포맷: `YYYY-MM-DD`. `T00:00:00Z` 같은 ISO datetime 사용 시 **HTTP 400**.
- `TileMatrixSet` 은 **레이어마다 다르다**. 하드코딩 금지 → 매니페스트에서 읽는다.
- 확장자: JPEG (BlueMarble) / PNG (관측 레이어) 중 해당 레이어 스펙 준수.

### 1.2 정적 레이어 vs 일간 레이어

- BlueMarble 계열은 `default/default/{TileMatrixSet}/...` — 날짜 자리에 **`default`** 리터럴 사용.
- 일간 레이어는 `default/{YYYY-MM-DD}/{TileMatrixSet}/...` — **오늘 / 어제 / 그제** 순으로 availableDate fallback 구현.

### 1.3 CesiumJS 1.140 Integration Rules

- `WebMapTileServiceImageryProvider.fromUrl()` 는 비동기 — **await 필수**.
- 대신 `new WebMapTileServiceImageryProvider({ urlTemplate, tileMatrixSetID, ... })` 동기 생성자 사용 권장 (GetCapabilities 호출 회피).
- GIBS REST 템플릿은 GetCapabilities 없이 직접 호출 가능 → 초기화 경로 단축.
- 정적 레이어는 `clock` undefined 로 설정.

### 1.4 Layer Composition Rule (CLAUDE.md)

> 한 번에 **1 continuous + 1 event** 동시 최대.

4개 GIBS imagery 레이어 중 **동시 ON 은 1개**. 나머지는 토글 시 먼저 disable.
BlueMarble 은 기본 레이어 — 카운트 제외.

---

## 2. 승인된 MVP Imagery 레이어 (4 + BlueMarble)

### 2.1 BlueMarble (베이스)

```ts
const BlueMarble: LayerManifest = {
  id: 'BlueMarble_ShadedRelief_Bathymetry',
  title: 'Natural Earth',                     // UI 라벨 고정 (Blue Marble 금지 — 상표 이슈)
  category: 'imagery',
  kind: 'continuous',
  source: 'NASA GIBS / Blue Marble',
  trustTag: 'observed',
  coverage: 'global',
  cadence: 'monthly',
  enabled: true,                              // 기본 ON (베이스)
  caveats: [
    'Monthly composite — not real-time.',
    'UI label must read "Natural Earth", not "Blue Marble" (브랜드 혼동 방지).',
  ],
  imagery: {
    type: 'wmts',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/BlueMarble_ShadedRelief_Bathymetry/default/default/500m/{TileMatrix}/{TileRow}/{TileCol}.jpg',
    tileMatrixSet: '500m',
    availableDates: 'static',
  },
};
```

### 2.2 Sea Surface Temperature (SST)

```ts
const SST: LayerManifest = {
  id: 'GHRSST_L4_MUR_Sea_Surface_Temperature',
  title: 'Sea Surface Temperature (SST)',
  category: 'imagery',
  kind: 'continuous',
  source: 'NASA JPL MUR GHRSST L4 via GIBS',
  trustTag: 'near-real-time',
  coverage: 'ocean-only',
  cadence: 'daily',
  enabled: false,                             // 탭 클릭 시 ON, 다른 continuous 자동 OFF
  legend: { unit: '°C', min: -2, max: 35, colormap: 'GHRSST_L4_MUR_Sea_Surface_Temperature' },
  caveats: [
    '1-day latency (NRT).',
    'Polar regions interpolated.',
    'Click 시 실제 값은 Worker `/api/sst-point` 에서 OISST 로 조회 (GIBS 타일 RGB 역변환 금지).',
  ],
  imagery: {
    type: 'wmts',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/GHRSST_L4_MUR_Sea_Surface_Temperature/default/{Time}/1km/{TileMatrix}/{TileRow}/{TileCol}.png',
    tileMatrixSet: '1km',
    availableDates: 'daily 2002-06-01 to present',
  },
};
```

### 2.3 Aerosol (AOD) — **"에어로졸 프록시"**

```ts
const AOD: LayerManifest = {
  id: 'MODIS_Terra_Aerosol',
  title: 'Aerosol Proxy (AOD)',               // PM2.5 라벨 절대 금지
  category: 'imagery',
  kind: 'continuous',
  source: 'MODIS Terra — NASA GSFC via GIBS',
  trustTag: 'near-real-time',
  coverage: 'global',
  cadence: 'daily',
  enabled: false,
  legend: { unit: 'AOD (unitless)', min: 0, max: 1, colormap: 'MODIS_Terra_Aerosol' },
  caveats: [
    'AOD = column-integrated aerosol optical depth. 컬럼 합산 값.',
    'PM2.5, 미세먼지, 대기질 점수 등 다른 해석 금지.',
    'Land + ocean 결합 제품.',
    'Click 동작: 값 조회 없이 "에어로졸 프록시 — PM2.5 아님" 설명 카드만 표시.',
  ],
  imagery: {
    type: 'wmts',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_Aerosol/default/{Time}/2km/{TileMatrix}/{TileRow}/{TileCol}.png',
    tileMatrixSet: '2km',
    availableDates: 'daily 2000-02-24 to present',
  },
};
```

### 2.4 Clouds

```ts
const Clouds: LayerManifest = {
  id: 'MODIS_Aqua_Cloud_Fraction_Day',
  title: 'Cloud Fraction (Day)',
  category: 'imagery',
  kind: 'continuous',
  source: 'MODIS Aqua — NASA GSFC via GIBS',
  trustTag: 'near-real-time',
  coverage: 'global',
  cadence: 'daily',
  enabled: false,
  legend: { unit: 'fraction (0–1)', min: 0, max: 1, colormap: 'MODIS_Aqua_Cloud_Fraction_Day' },
  caveats: [
    'Day-only pass (Aqua 오전/오후 궤도). 야간 커버리지 없음.',
    'Click 동작: 설명 카드만.',
  ],
  imagery: {
    type: 'wmts',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Aqua_Cloud_Fraction_Day/default/{Time}/2km/{TileMatrix}/{TileRow}/{TileCol}.png',
    tileMatrixSet: '2km',
    availableDates: 'daily 2002-07-04 to present',
  },
};
```

### 2.5 Night Lights — **`_ENCC` 절대 사용 금지**

```ts
const NightLights: LayerManifest = {
  id: 'VIIRS_SNPP_DayNightBand',              // ⚠️ NOT _ENCC (frozen at 2023-07-07)
  title: 'Night Lights',
  category: 'imagery',
  kind: 'continuous',
  source: 'VIIRS Suomi NPP Day/Night Band via GIBS',
  trustTag: 'near-real-time',
  coverage: 'global',
  cadence: 'daily',
  enabled: false,
  caveats: [
    '"인간 활동 프록시" 로 라벨. 전력 소비량 직접 측정 아님.',
    'Raw radiance — 대기 보정 없음. 해양/빙하 상의 강한 반사(glare) 존재.',
    '`VIIRS_SNPP_DayNightBand_ENCC` 는 2023-07-07 이후 FROZEN → 400 에러. 사용 금지.',
    'NOAA-20 대체: `VIIRS_NOAA20_DayNightBand` 동일 스펙.',
  ],
  imagery: {
    type: 'wmts',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/VIIRS_SNPP_DayNightBand/default/{Time}/1km/{TileMatrix}/{TileRow}/{TileCol}.png',
    tileMatrixSet: '1km',
    availableDates: 'daily 2012-01-19 to present',
  },
};
```

---

## 3. 클릭 정책 (UI contract)

| Layer | Click Behavior |
|---|---|
| BlueMarble | 동작 없음 |
| SST | Worker `/api/sst-point` → OISST 실제 °C 표시 (Popup: temperatureC + observedAt + trustTag) |
| AOD | 설명 카드 — "에어로졸 프록시. PM2.5 아님." |
| Clouds | 설명 카드 — "낮 시간 관측. 야간 커버리지 없음." |
| Night Lights | 설명 카드 — "인간 활동 프록시. 전력 소비량 직접 측정 아님." |

이벤트 레이어 (FIRMS / USGS) 의 클릭 정책은 `docs/datasets/source-spike-matrix.md` Worker endpoint 섹션 참조.

---

## 4. 검증 프로토콜 (새 레이어 추가 시)

1. `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi?SERVICE=WMTS&request=GetCapabilities` 에서 현재 LayerIdentifier 확인.
2. `TileMatrixSet` 필드 + valid date range 기록.
3. `curl -I {urlTemplate with zoom=0}` 으로 200 + content-type 확인.
4. Date fallback 구현: 오늘 → 어제 → 그제 (3 tries 이후 disable).
5. `data/fixtures/gibs/<layerId>.json` 에 HEAD probe 결과 저장.
6. 본 파일에 LayerManifest 추가.
7. CesiumJS 통합 후 실 브라우저에서 타일 로드 확인.
8. 라벨/caveat/trustTag 확정 후 `packages/schemas/` 에 반영.

---

## 5. 변경 이력

| 날짜 | 변경 | 근거 |
|---|---|---|
| 2026-04-17 | 최초 작성 (5 레이어 승인) | Step 2 Agent 1 live probe |
| 2026-04-17 | `VIIRS_SNPP_DayNightBand_ENCC` → `VIIRS_SNPP_DayNightBand` | ENCC frozen 2023-07-07 |
