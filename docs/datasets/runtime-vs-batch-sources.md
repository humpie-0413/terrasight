# TerraSight v2 — Runtime vs Batch Source Boundary

**작성일:** 2026-04-17
**상태:** 승인 (Phase: v2 Architecture Reset — Step 2 완료)
**목적:** 모든 데이터 소스가 "브라우저-다이렉트", "Worker 경유", "GitHub Actions 배치" 중 정확히 하나의 경로로 들어오도록 경계를 고정한다. **경로 혼용 금지.**

---

## 1. 세 가지 실행 경로

```
┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
│  Browser direct     │         │  Cloudflare Worker  │         │  GitHub Actions     │
│  (GIBS WMTS)        │   →     │  (proxy + cache)    │   →     │  (batch cron)       │
│                     │         │                     │         │                     │
│  - WMTS 타일         │         │  - FIRMS (MAP_KEY)  │         │  - CAMS → PNG → R2  │
│  - 무인증 CDN        │         │  - USGS (bbox)      │         │  - ERA5 → PNG → R2  │
│                     │         │  - OISST point      │         │  - GFS  → PNG → R2  │
│                     │         │  - DHW point        │         │                     │
└─────────────────────┘         └─────────────────────┘         └─────────────────────┘
         ↓                                ↓                                ↓
    모든 CesiumJS                     HTTPS JSON                       정적 PNG
    imagery 레이어                    (EventPoint[] 등)                  R2 + 브라우저 캐시
```

---

## 2. 경로별 규칙

### 2.1 Browser Direct — GIBS WMTS 만 허용

- **허용:** GIBS 타일 REST 템플릿 (`gibs.earthdata.nasa.gov/wmts/epsg4326/best/...`)
- **금지:** 원본 API key 가 필요한 어떤 소스도 브라우저에서 직접 호출 금지.
- **금지:** CORS 제한이 있는 government API 직접 호출 (AirNow, EPA 등) — Worker 경유.
- **금지:** 요청 시점 CSV/GeoJSON 파싱 후 Globe 렌더 — 페이로드 크면 Worker 에서 정규화.

**승인 레이어:** `docs/datasets/gibs-approved-layers.md` 참조 (5개).

### 2.2 Cloudflare Worker — Proxy + Cache Only

- **허용:** 키 주입, bbox/params 처리, 응답 정규화 (EventPoint / 단일값), 캐시 TTL.
- **금지:** 계산, 집계, 조합, 이미지 렌더링, 파일 저장.
- **금지:** 동시에 여러 소스 fan-out (예: `/api/report/houston` — 이건 빌드타임 잡).

**승인 엔드포인트:**

| Endpoint | Upstream | Cache | Response |
|---|---|---|---|
| `GET /api/fires?bbox=w,s,e,n&days=1` | FIRMS VIIRS_SNPP_NRT | 10 min | EventPoint[] |
| `GET /api/earthquakes?period=day&magnitude=all` | USGS summary feed | 5 min | EventPoint[] |
| `GET /api/sst-point?lat=..&lon=..` | NOAA OISST (ERDDAP) | 1 h | `{ temperatureC, observedAt, trustTag, source }` |
| `GET /api/dhw-point?lat=..&lon=..` (선택) | CRW DHW (ERDDAP) | 6 h | `{ dhw, observedAt, trustTag, source }` |

**Worker Graceful Degradation:**
- 키 부재 → `{ status: 'not_configured' }` (200)
- 업스트림 5xx / 타임아웃 → `{ status: 'error', retryable: true }` (200)
- bbox 미지정 / 잘못된 format → `{ status: 'error', message }` (400)

### 2.3 GitHub Actions — Batch → R2

- **목적:** Open-Meteo 의존 제거 후 "현재 값" 이 필요한 모든 필드는 배치에서 PNG 프레임으로 렌더.
- **실행:** `ubuntu-latest` runner (7 GB RAM, 6h max), Python 3.11+.
- **산출물:** PNG (1440×720 또는 900×450), R2 업로드, 브라우저가 CDN 으로 fetch.
- **금지:** 런타임에서 numpy/scipy 로 PNG 렌더 (Render 512MB 초과 사례 재발 방지).

**승인 파이프라인 (Phase 4+):**

| Pipeline | Cron | Output Path | Est. duration |
|---|---|---|---|
| GFS (temp/wind/precip) | `30 4,10,16,22 * * *` | `r2://terrasight-frames/gfs/<var>/<YYYY>/<MM>/<DD>/global-<HH>00.png` | 5–10 min |
| CAMS (pm25/no2/o3) | `0 8 * * *` | `r2://terrasight-frames/cams/<var>/<YYYY>/<MM>/<DD>/global-<HH>00.png` | 25–55 min |
| ERA5 (monthly climatology) | `0 6 5 * *` | `r2://terrasight-frames/era5/<var>/<YYYY>/<MM>/global-monthly.png` | 10–20 min |

**예상 월 R2 스토리지:**
- GFS: 4 runs/day × 5 vars × 30d × 300KB ≈ 180 MB/month
- CAMS: 1 run/day × 3 vars × 30d × 400KB ≈ 36 MB/month
- ERA5: 1 run/month × 4 vars × 400KB ≈ 1.6 MB/month
- **합계 ~218 MB/month** — R2 Free 10GB 내 완전 여유.

---

## 3. 왜 혼용하면 안 되는가

| 잘못된 패턴 | 왜 폭주하는가 |
|---|---|
| 브라우저에서 FIRMS 직접 호출 | MAP_KEY 노출 → 쿼터 소진 / abuse |
| Worker 가 report 전체 fan-out | 커넥터 1 실패 → block 전체 5xx → layout collapse |
| Worker 가 GeoTIFF 디코딩 | CPU 초과 → 128 MB memory → 크래시 |
| 런타임 numpy PNG 렌더 | v1 에서 이미 발생한 장애 — Render 512MB 초과 → 502 |
| 배치 결과를 Worker 가 재조합 | 정적 JSON 의 신뢰 타임스탬프 무효화 |

**기본 원칙:** 데이터가 어디서 "조합" 되는가로 경로가 결정된다.

- 단일 값, 사용자 좌표 즉답 → Worker
- 사전 정의된 정적 산출물 (Report 블록, 배치 프레임) → GitHub Actions
- 프록시 없이 안전한 CDN 타일 → Browser

---

## 4. 데이터 소스 배정 표

| Source | Path | 이유 |
|---|---|---|
| GIBS imagery (BlueMarble/SST/AOD/Clouds/NightLights) | Browser | 무인증 CDN, 타일 렌더는 클라이언트에서 |
| FIRMS | Worker | MAP_KEY 숨김 + bbox fan-out 제어 + 캐시 |
| USGS Earthquakes | Worker | bbox 필터 + 캐시 (CORS OK 지만 정규화 필요) |
| OISST point | Worker | longitude 변환 + zlev 핸들 + null-land |
| CRW DHW point | Worker | 동상 |
| AirNow | GitHub Actions (report build) | CBSA 단위 사전 계산, 런타임 fan-out 금지 |
| AQS / ECHO / SDWIS / WQP / 기타 Reports 소스 | GitHub Actions | 동상 |
| CAMS PM2.5 / NO₂ / O₃ | GitHub Actions → PNG → R2 | 계정 + 큐 + 렌더 |
| ERA5 월평균 | GitHub Actions → PNG → R2 | 동상 |
| GFS Temp / Wind / Precip | GitHub Actions → PNG → R2 | GRIB2 파싱 필요 |
| Open-Meteo | — | 🔴 제외 (참고용 링크만) |

---

## 5. 빌드타임 Report fan-out 재확인

MVP 에서 Report 는 **완전 정적**:
- GitHub Actions 에서 `pipelines/run-report-build.py` 실행.
- 각 CBSA 별로 필요한 모든 커넥터 호출 → 8 core blocks (optional extension blocks) 조립.
- 결과: `data/reports/<slug>.json` → Astro `getStaticPaths` → HTML 생성.
- 런타임 (브라우저/Worker) 은 report 조립 책임 없음.

커넥터 1개가 실패해도 **해당 블록만 `status: 'error'`** 로 마킹, 다른 블록은 정상 렌더.

---

## 6. 경로 전환 트리거 (언제 배치 → Worker 로 승격하는가)

- Worker 로 승격: 응답이 정적이 아니고 사용자 좌표/시간에 따라 달라지며 단일 값 또는 작은 배열 (< 100 KB) 일 때.
- 배치로 강등: 응답이 격자 (raster) 이거나, 사용자마다 같거나, 렌더링이 CPU-heavy 일 때.

이 결정은 본 파일에 먼저 반영하고 커밋 후 구현한다.

---

## 7. 변경 이력

| 날짜 | 변경 | 근거 |
|---|---|---|
| 2026-04-17 | 최초 작성 (Browser / Worker / Batch 3 경로 확정) | Step 2 agent 결과 종합 |
