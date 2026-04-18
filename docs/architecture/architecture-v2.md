# TerraSight v2 — Architecture

**작성일:** 2026-04-17
**상태:** 승인 (Phase: v2 Architecture Reset)
**선행 문서:** `docs/project-blueprint.md`, `docs/globe-vision.md`, `docs/terrasight_v2_architecture_and_prompts.md`

---

## 1. Why v2 — 구조적 문제 10줄 요약

1. Render Free Tier 512MB 에서 numpy/scipy 래스터 렌더링이 상시 실패 (SST advection 피크 400MB+).
2. Open-Meteo 무료 API의 rate limit + Render cold start 캐시 소실로 PM2.5/Temp/Precip/NO₂ 4개 레이어가 빈 화면.
3. 자체 PNG 렌더링 파이프라인은 cold start 시 첫 요청이 10~30초 지연 → UX 붕괴.
4. Globe 12개 레이어 유지 전제가 유지보수 부하를 과잉 생산 (실제 동작은 4~5개).
5. Report API 가 요청 시점 다중 커넥터 fan-out → 하나만 느려도 전체 Report 블록 타임아웃.
6. Frontend 가 CesiumJS + deck.gl 양립 번들 (232KB vendor) 로 홈 라우트 초기 로딩 부담.
7. CLAUDE.md/progress.md 가 비대 → 세션마다 컨텍스트 부담 + 실제 운영 규칙 불분명.
8. "compliance ≠ exposure" disclaimer 등 절대 규칙이 코드 수준에서 강제되지 않음.
9. GIBS 중심 전략 선언했지만 실제 레이어는 Open-Meteo 로 구현되는 불일치.
10. 수익화 블록(AdSense 슬롯)이 정적 생성 전제 없이 동적 페이지에 삽입 → Google 정책 리스크.

---

## 2. v2 핵심 전환

| From (v1) | To (v2) |
|---|---|
| Render 상시 FastAPI 런타임 | GitHub Actions 배치 + Cloudflare Workers 경량 프록시 |
| 요청 시점 래스터 PNG 생성 | GIBS imagery 브라우저 직접 로드 |
| Report API fan-out | 빌드타임 `report.json` 정적 생성 |
| Open-Meteo 의존 MVP 레이어 | GIBS/FIRMS/USGS/ERDDAP 중심 MVP |
| React SPA (Vite) | Astro SSG + React island |
| 12-layer Globe 전제 | **Globe Lite** 6-layer MVP |
| Atlas 인터랙티브 탐색기 | **Atlas Lite** 데이터셋 레지스트리 + 방법론 허브 |
| Report 14 블록 동적 | **Reports Static** 핵심 8 블록 + 선택 확장 |

---

## 3. 유지 / 제거 / 보류 분류

### 유지 (Keep)
- 3-Tier 퍼널 (Globe → Atlas → Reports)
- GIBS-first 데이터 전략
- Trust Tag 체계 (`observed` / `near-real-time` / `forecast` / `derived` / `compliance`)
- 8개 Atlas 카테고리 (환경공학 교과 분류)
- 50개 U.S. CBSA metros (Reports 타겟)
- Climate Trends 6 cards (정적 JSON 소비)
- Wildfires (FIRMS) · Earthquakes (USGS) — 이미 안정
- SST click-to-value (ERDDAP point query)
- CesiumJS Globe 엔진 (v1 후반기 마이그레이션 완료)
- Mandatory disclaimers (ECHO / WQP / AirNow)
- `docs/guardrails.md` Absolute Rules 7개

### 제거 (Remove)
- Render Free 상시 FastAPI 런타임에서 래스터/PNG 생성
- 자체 PNG 렌더링 파이프라인 (`backend/utils/surface_renderer.py` 계열)
- Strip-based BitmapLayer 워크어라운드 (v1 Phase 4/5)
- SST advection 프레임 생성 (메모리 초과)
- Open-Meteo 의존 프로덕션 레이어: PM2.5, Temperature, Precipitation, NO₂
- Open-Meteo Marine 기반 해류 파티클 (MVP 제외, Phase 4 후속)
- Report API 요청 시점 fan-out (`GET /api/reports/{slug}`)
- 12-레이어 fullset 유지 전제
- React SPA 홈 (Vite) → Astro SSG 로 교체

### 보류 (Defer, Phase 4+)
- CAMS Global (Copernicus ADS 계정 필요)
- ERA5 (Copernicus CDS 계정 필요)
- GFS 배치 파이프라인 (GRIB2 디코딩)
- OCO-2 Total Column CO₂ (3~5% 커버리지, 맥락 라벨 필요)
- MERRA-2 월평균 (현재 날씨로 오인 방지 라벨 필요)
- Flood detection (GIBS 불안정)
- Storm tracks (활성 폭풍 없을 때 표시 로직)
- Wind/Current particle animation (외부 서버 렌더링 후속)
- External SST advection frames (GitHub Actions cron → R2)
- PFAS · Coast · Hazard history · City comparison · Related cities — Report 선택 확장 블록

---

## 4. Three-Tier 재정의

### Tier 1 — Globe Lite
**목적:** 예쁜 데모가 아니라 "항상 뜨는" 전지구 관측 포털.

- 6 MVP 레이어 (상세: `docs/architecture/mvp-scope-v2.md`)
- Layer composition rule: **1 continuous field + 1 event overlay 동시 최대**
- 클릭 조회: SST 만 우선 (ERDDAP point query)
- 이벤트 팝업: 산불 · 지진
- 나머지 표면 레이어는 값 조회 대신 설명 + Trust Tag 중심
- Globe island 는 `/globe` 라우트에서만 hydration — 홈 `index.astro` 는 SSG HTML + Trends 카드

### Tier 2 — Atlas Lite
**목적:** 데이터셋 레지스트리 + 방법론 허브 (깊은 인터랙티브 탐색기 아님).

- `/atlas` → 카테고리 카드
- `/atlas/[category]` → 데이터셋 목록
- `/atlas/datasets/[slug]` → 데이터셋 상세
- 각 데이터셋 필수 필드: 측정 대상 · 관측/모델/규제 구분 · 범위 · 갱신 주기 · 해상도 · 라이선스 · 한계 · 연결 Globe 레이어 · 연결 Report 블록

### Tier 3 — Reports Static
**목적:** 수익화 중심축. 모든 Report 는 **빌드타임 JSON 소비** 정적 생성.

- 핵심 8 블록 + 선택 확장 블록 (상세: `mvp-scope-v2.md`)
- 페이지 요청 시 서버 계산 **금지**
- 광고 슬롯은 블록 사이 정적 슬롯으로 관리
- 블록별 Trust Tag · citations · updatedAt · caveats 필수

---

## 5. 기술 스택

### Frontend / Site
- **Astro** + **React (island)** + **TypeScript**
- Globe: `/globe` 라우트의 React island (CesiumJS)
- Reports / Atlas / Guides / Rankings: Astro SSG
- 스타일: Tailwind 또는 CSS Modules 중 택1 (통일)

### Edge API (경량 프록시)
- **Cloudflare Workers** (Hono)
- 역할: FIRMS / USGS / ERDDAP point query 프록시 + 캐시
- **금지:** 래스터 렌더링 / numpy 계산 / Report 조립

### Storage
- **Cloudflare R2**
- 빌드 산출 JSON · 프리렌더 프레임 · 정적 데이터

### Build / Jobs
- **GitHub Actions** 스케줄러
- **Python 3.11** 데이터 파이프라인
- 커넥터 → normalize → report.json → R2/repo publish

### 런타임 금지
- Render Free 상시 백엔드
- 요청 시점 numpy/scipy 이미지 렌더링
- Worker 안에서의 무거운 조합/계산

---

## 6. Monorepo 구조

```text
terrasight/
├─ apps/
│  ├─ web/                    # Astro site
│  │  ├─ src/
│  │  │  ├─ pages/
│  │  │  │  ├─ index.astro
│  │  │  │  ├─ globe.astro
│  │  │  │  ├─ atlas/
│  │  │  │  ├─ reports/
│  │  │  │  ├─ guides/
│  │  │  │  └─ rankings/
│  │  │  ├─ components/
│  │  │  ├─ islands/          # Globe 등 hydration 대상만
│  │  │  ├─ layouts/
│  │  │  └─ lib/
│  │  └─ public/
│  └─ worker/                 # Cloudflare Worker API (Hono)
│     ├─ src/
│     │  ├─ routes/
│     │  │  ├─ fires.ts
│     │  │  ├─ earthquakes.ts
│     │  │  └─ sst-point.ts
│     │  ├─ services/
│     │  ├─ cache/
│     │  └─ index.ts
│     └─ wrangler.jsonc
├─ packages/
│  ├─ schemas/                # zod/json schema (공유 계약)
│  ├─ ui/                     # shared presentational components
│  └─ config/                 # ts/eslint/prettier 공유
├─ pipelines/
│  ├─ connectors/             # Python source adapters
│  ├─ jobs/                   # build/snapshot jobs
│  ├─ transforms/             # normalize / derive metrics
│  ├─ publish/                # R2 publish helpers
│  └─ tests/
├─ data/
│  ├─ fixtures/
│  ├─ manifests/
│  ├─ reports/
│  └─ rankings/
├─ docs/
│  ├─ architecture/
│  ├─ datasets/
│  ├─ reports/
│  ├─ review/
│  └─ prompts/
├─ .claude/
│  ├─ agents/
│  ├─ skills/
│  └─ settings.json
├─ CLAUDE.md
├─ progress.md
├─ package.json
├─ pnpm-workspace.yaml
└─ pyproject.toml
```

---

## 7. 런타임 경계

```text
사용자 브라우저
   │
   ├─ /                → Astro SSG 홈 (Climate Trends 정적 카드)
   ├─ /globe           → React island (CesiumJS, client:visible)
   ├─ /atlas/...       → Astro SSG + dataset JSON
   ├─ /reports/...     → Astro SSG + report.json (getStaticPaths)
   ├─ /rankings/...    → Astro SSG + rankings JSON
   └─ /guides/...      → Astro SSG
   │
   ├─ GIBS imagery     → 브라우저 직접 로드 (Worker 경유 금지)
   └─ Worker API       → 경량 프록시만
         ├─ /api/fires              (FIRMS, 10min cache)
         ├─ /api/earthquakes        (USGS, 5min cache)
         └─ /api/sst-point          (ERDDAP, 1h cache)

GitHub Actions (cron)
   │
   ├─ Python connectors 실행
   ├─ normalize / validate (zod/pydantic)
   ├─ report.json 생성
   ├─ rankings JSON 생성
   └─ R2 publish or repo commit (apps/web/public 데이터)
```

### 경계 원칙
- GIBS 레이어 = 브라우저 직접 (Worker 경유 금지)
- 이벤트 데이터 = Worker 프록시/캐시
- Report/Atlas = 빌드타임 산출물 (요청 시점 계산 금지)
- 무거운 계산 = GitHub Actions 전용

---

## 8. 데이터 계약 (Contracts)

정식 스펙은 `packages/schemas/` 에 zod 로 정의. 타입 프리뷰:

```ts
// TrustTag
export type TrustTag =
  | 'observed'
  | 'near-real-time'
  | 'forecast'
  | 'derived'
  | 'compliance';

// LayerManifest (Globe)
export interface LayerManifest {
  id: string;
  title: string;
  category: 'ocean' | 'atmosphere' | 'hazards' | 'human-footprint';
  kind: 'imagery' | 'event';
  source: string;
  trustTag: TrustTag;
  coverage: 'global' | 'land-only' | 'ocean-only' | 'swath';
  cadence: string;
  enabled: boolean;
  legend?: { min?: number; max?: number; units?: string; note?: string };
  imagery?: { type: 'gibs-wms' | 'gibs-wmts'; layerId: string; dateMode: 'latest' | 'fixed' };
  eventApi?: { path: string; ttlSeconds: number };
  caveats: string[];
}

// EventPoint (Worker API 응답)
export interface EventPoint {
  id: string;
  type: 'fire' | 'earthquake';
  lat: number;
  lon: number;
  observedAt: string;
  severity?: number;
  label: string;
  properties: Record<string, string | number | boolean | null>;
}

// DatasetRegistryItem (Atlas)
export interface DatasetRegistryItem {
  slug: string;
  title: string;
  category: string;
  summary: string;
  sourceType: 'satellite' | 'model' | 'regulatory' | 'inventory';
  trustTag: TrustTag;
  geographicCoverage: string;
  cadence: string;
  resolution: string;
  license: string;
  sourceUrl: string;
  caveats: string[];
  linkedLayers: string[];
  linkedReportBlocks: string[];
}

// CityReport (Reports)
export interface CityReport {
  slug: string;
  city: string;
  region: string;
  country: string;
  updatedAt: string;
  summary: { headline: string; bullets: string[] };
  blocks: Array<{
    id: string;
    title: string;
    trustTags: TrustTag[];
    body: string;
    metrics?: Array<{ label: string; value: string; note?: string }>;
    citations: string[];
  }>;
}

// Graceful degradation 공통 status
export type BlockStatus = 'ok' | 'error' | 'not_configured' | 'pending';
```

---

## 9. 핵심 원칙 (Non-Negotiable)

1. **No Render runtime rasterization** — 요청 시점 numpy/scipy PNG 생성 금지.
2. **No Open-Meteo dependency in production MVP** — 참고용으로만 문서화.
3. **All reports must be statically generated** — 빌드타임 `report.json` 소비.
4. **GIBS-first for global layers** — 새 표면 레이어는 GIBS 우선 검토.
5. **Trust tags required** — 모든 dataset / report block / map layer.
6. **Graceful status** — 모든 block/endpoint 는 `ok | error | not_configured | pending` 반환.
7. **No composite environmental scores** — 투명한 개별 지표만.
8. **Mandatory disclaimers** — ECHO / WQP / AirNow 문구는 제거 불가.
9. **Layer composition rule** — 1 continuous + 1 event 동시 최대.
10. **Don't paste docs into CLAUDE.md** — CLAUDE.md 는 1~2 screen 유지.

---

## 10. Definition of Done (Phase 단위)

- [ ] 코드
- [ ] 스키마 validation 통과 (zod/pydantic 양쪽)
- [ ] 테스트 (fixture 기반 contract test 포함)
- [ ] 문서 (architecture/datasets/reports 중 해당)
- [ ] landmine 이 발견되었다면 `docs/guardrails.md` + 커넥터 docstring 에 기록
- [ ] `CLAUDE.md` 업데이트 (핵심 규칙 변경 시에만)
- [ ] `progress.md` 업데이트 (필수)

---

## 11. 관련 문서

- MVP 레이어/블록 상세: `docs/architecture/mvp-scope-v2.md`
- 데이터 소스 정책: `docs/architecture/data-source-policy.md`
- 단계별 실행 프롬프트: `docs/terrasight-v2-step-prompts.md`
- Legacy (참고용): `docs/terrasight_v2_architecture_and_prompts.md`, `docs/globe-vision.md`, `docs/project-blueprint.md`
