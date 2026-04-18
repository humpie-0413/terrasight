# TerraSight v2 — 현재 개발환경 기준 전체 아키텍처 및 Claude CLI 작업 프롬프트

## 1. 전제와 리셋 결정

현재 TerraSight는 3-Tier 퍼널, GIBS 우선 전략, Globe/Atlas/Reports 구조 자체는 좋지만, 실제 운용은 Render Free 512MB와 Open-Meteo 의존 때문에 실시간 래스터 렌더링이 계속 실패하는 상태다. 따라서 v2는 **"실시간 백엔드 렌더링 중심"에서 "정적/배치 중심 + 경량 API" 구조로 재설계**한다.

### 유지할 것
- 3-Tier 퍼널: Globe → Atlas → Reports
- GIBS 우선 데이터 전략
- Trust Tag
- 전지구 공통 코어 + 지역별 확장 모듈
- Local Reports 중심의 SEO/수익화

### 버릴 것 / 후순위로 미룰 것
- Render 상시 FastAPI 런타임에서 PNG/래스터 생성
- Open-Meteo 기반 프로덕션 핵심 레이어
- 12개 Globe 레이어를 당장 모두 유지해야 한다는 전제
- SST advection / 실시간 해류 파티클을 MVP 핵심으로 두는 접근
- Atlas를 초기부터 무거운 인터랙티브 탐색기로 만드는 방향

---

## 2. TerraSight v2 제품 아키텍처

## Tier 1 — Globe Lite
목표는 “예쁜 데모”가 아니라 **항상 뜨는 전지구 관측 포털**이다.

### MVP 레이어 (6개)
1. Sea Surface Temperature (GIBS)
2. Aerosol Optical Depth / Haze (GIBS)
3. Clouds (GIBS)
4. Night Lights (GIBS)
5. Wildfires (FIRMS)
6. Earthquakes (USGS)

### 클릭/호버 정책
- 클릭 조회: SST만 우선 지원
- 이벤트 팝업: 산불, 지진
- 나머지 표면 레이어는 일단 값 조회보다 “관측 레이어 + 설명 + Trust Tag” 중심

### 보류 레이어
- PM2.5 (Open-Meteo 프로덕션 제외)
- Temperature / Precipitation (원천 파이프라인 전까지 제외)
- Currents / Wind particle (후속)
- OCO-2 / Flood / MERRA2는 2차 추가 후보

---

## Tier 2 — Atlas Lite
초기 Atlas는 **데이터셋 레지스트리 + 방법론 허브**로 운영한다.

### Atlas Lite 페이지 구성
- /atlas
- /atlas/[category]
- /atlas/datasets/[slug]

### 각 데이터셋 페이지 필수 필드
- 무엇을 측정하는가
- 관측/모델/규제 여부
- 전지구/지역 범위
- 갱신 주기
- 해상도
- 라이선스/출처
- 한계와 주의점
- 연결되는 Globe 레이어
- 연결되는 Report 블록

---

## Tier 3 — Local Reports Static
수익화 중심축은 Reports다. 모든 Report는 **정적 생성(SSG)** 으로 만든다.

### 초기 리포트 범위
- 50개 도시를 유지하되, 페이지 구조는 14개 블록 고정 대신 **핵심 8개 블록 + 선택 확장 블록**으로 재설계

### 핵심 8개 블록
1. 대기질
2. 기후/열환경
3. 재해 노출
4. 음용수/수질
5. 산업시설·배출
6. 오염부지·정화
7. 인구 노출/환경정의
8. 방법론 + 데이터 신뢰 설명

### 선택 확장 블록
- PFAS
- 해안
- 세부 재해 이력
- 도시 비교
- 관련 도시

### 정적 생성 원칙
- 모든 Report는 빌드 시점 JSON을 소비
- 페이지 요청 시 서버 계산 금지
- 광고 삽입 위치는 블록 사이 정적 슬롯으로 관리

---

## 3. 권장 기술 아키텍처 (현재 개발환경 최적화)

## 권장 스택
### Frontend / Site
- **Astro** + **React** + **TypeScript**
- Globe는 React island로만 hydration
- Reports / Atlas / Guides / Rankings는 Astro SSG
- 스타일링은 CSS variables + CSS modules 또는 Tailwind 중 한 가지로 통일

### Edge API
- **Cloudflare Workers**
- 필요 시 Hono 사용
- 역할: FIRMS / USGS / ERDDAP point query 경량 프록시 및 캐시

### Storage
- **Cloudflare R2**
- 빌드 산출 JSON / 프리렌더 프레임 / 정적 데이터 보관

### Build / Jobs
- **GitHub Actions** 스케줄러
- **Python 3.11** 데이터 파이프라인
- 커넥터, 정규화, Report JSON 생성, Rankings JSON 생성

### Runtime 금지
- Render Free 상시 백엔드
- 요청 시점 numpy/scipy 이미지 렌더링

---

## 4. 모노레포 구조

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
│  │  │  ├─ islands/
│  │  │  ├─ layouts/
│  │  │  └─ lib/
│  │  └─ public/
│  └─ worker/                 # Cloudflare Worker API
│     ├─ src/
│     │  ├─ routes/
│     │  ├─ services/
│     │  ├─ cache/
│     │  └─ index.ts
│     └─ wrangler.jsonc
├─ packages/
│  ├─ schemas/                # zod/json schema shared contracts
│  ├─ ui/                     # shared presentational components
│  └─ config/                 # shared ts/eslint/prettier config
├─ pipelines/
│  ├─ connectors/             # Python source adapters
│  ├─ jobs/                   # build jobs / snapshot jobs
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

## 5. 런타임 아키텍처

```text
사용자 브라우저
   │
   ├─ /                → Astro SSG 홈
   ├─ /globe           → React/Cesium island
   ├─ /atlas/...       → Astro SSG + dataset JSON
   └─ /reports/...     → Astro SSG + report JSON
   │
   ├─ GIBS imagery 직접 로드
   └─ Worker API 호출
         ├─ /api/fires
         ├─ /api/earthquakes
         └─ /api/sst-point

GitHub Actions / Local CLI
   │
   ├─ Python connectors 실행
   ├─ normalize / validate
   ├─ report JSON 생성
   ├─ rankings JSON 생성
   └─ R2 또는 repo data/에 publish
```

### 핵심 원칙
- GIBS 레이어는 브라우저에서 직접 소비
- 이벤트 데이터만 Worker가 프록시/캐시
- Report와 Atlas는 정적 페이지
- 무거운 계산은 빌드나 스케줄 잡으로만 수행

---

## 6. 데이터 소스 정책

## 프로덕션 허용
### 1순위
- NASA GIBS
- NASA FIRMS
- USGS
- NOAA ERDDAP (point query 수준)

### 2순위
- EPA / NOAA / USGS / 기타 정부 무인증 또는 무료 계정 데이터

### 3순위 (후속 배치 파이프라인)
- CAMS
- ERA5
- GFS

## 프로덕션 핵심에서 제외
- Open-Meteo 의존 레이어
- 요청 시점 래스터 생성

### 데이터 표기 규칙
- PM2.5 대신 AOD일 경우 반드시 “에어로졸 프록시”로 표기
- OCO-2는 “Total Column CO₂”로 표기
- 월평균 MERRA2는 “현재 날씨”처럼 보이게 하지 말 것

---

## 7. 핵심 데이터 계약 (Data Contracts)

## TrustTag
```ts
export type TrustTag =
  | 'observed'
  | 'near-real-time'
  | 'forecast'
  | 'derived'
  | 'compliance';
```

## LayerManifest
```ts
{
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
```

## EventPoint
```ts
{
  id: string;
  type: 'fire' | 'earthquake';
  lat: number;
  lon: number;
  observedAt: string;
  severity?: number;
  label: string;
  properties: Record<string, string | number | boolean | null>;
}
```

## DatasetRegistryItem
```ts
{
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
```

## CityReport
```ts
{
  slug: string;
  city: string;
  region: string;
  country: string;
  updatedAt: string;
  summary: {
    headline: string;
    bullets: string[];
  };
  blocks: Array<{
    id: string;
    title: string;
    trustTags: TrustTag[];
    body: string;
    metrics?: Array<{ label: string; value: string; note?: string }>;
    citations: string[];
  }>;
}
```

---

## 8. 개발 운영 아키텍처 (VSCode + Claude CLI)

## 기본 운영 원칙
1. 모든 세션 시작 시 `@CLAUDE.md`와 `@progress.md`를 먼저 읽는다.
2. 큰 계획은 `/ultraplan`으로 먼저 승인받는다.
3. 병렬 탐색/조사는 `dispatching-parallel-agents`를 사용한다.
4. 반복 구현은 `subagent-driven-development`를 사용한다.
5. 완료 직전에는 `verification-before-completion`을 반드시 수행한다.
6. 디버깅은 `systematic-debugging`로 원인까지 추적한다.
7. **모든 작업 종료 시 CLAUDE.md와 progress.md를 갱신한다.**

## 스코프 운영
- **ECC**: user scope 기본
- **Harness**: project scope 기본
- **.claude/agents/** 와 **.claude/skills/** 는 repo에 커밋
- **CLAUDE.md는 짧고 강한 규칙만 유지**, 세부 절차는 skills로 이동

## .claude/settings.json
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

---

## 9. 모델 선택 기준 (이번 프로젝트용)

## 무조건 Claude Opus
- 전체 아키텍처 설계
- Repo 구조 변경
- 데이터 계약 설계
- Worker/API 구현
- Globe 핵심 로직
- Report 생성 파이프라인
- 근본 원인 디버깅
- 최종 검증/리뷰

## Claude Sonnet 허용
- 반복적 콘텐츠 입력
- 단순 스타일 수정
- 테스트 케이스 추가
- 문서 정리
- 이미 정의된 패턴을 그대로 늘리는 작업

### 실무 규칙
- **프로덕션 코드에 영향을 주는 핵심 구현은 Opus가 기본**
- Sonnet은 “보조 확장”이나 “반복 작업”에만 제한적으로 사용

---

## 10. CLAUDE.md 권장 구조

```md
# TerraSight

## Product Scope
- Globe Lite / Atlas Lite / Reports Static

## Non-Negotiable Rules
- No Render runtime rasterization
- No Open-Meteo dependency in production MVP
- All reports must be statically generated
- GIBS-first for global layers
- Trust tags required on all datasets and report blocks

## Architecture Decisions
- Current approved stack
- Runtime boundaries
- Data source priorities

## Definition of Done
- code
- tests
- docs
- CLAUDE.md updated
- progress.md updated

## Current Phase
- active phase name
- primary deliverables
```

### CLAUDE.md 관리 규칙
- 1~2 screen 안에 핵심 규칙 유지
- 길어지는 절차는 `.claude/skills/`로 이동
- 아키텍처 결정만 누적

---

## 11. progress.md 권장 구조

```md
# Progress

## Current Phase
- name:
- goal:

## Last Completed
- ...

## In Progress
- ...

## Next Actions
- ...

## Decisions
- ...

## Blockers / Risks
- ...

## Files Changed
- ...

## Verification
- tests:
- manual:
- review:
```

### progress.md 관리 규칙
- 작업 단위가 끝날 때마다 갱신
- 무엇을 했는지보다 **다음 사람이 바로 이어받을 수 있는 상태**를 남길 것

---

## 12. Phase별 Claude CLI 프롬프트

아래 프롬프트는 그대로 붙여넣어도 되도록 작성했다.

---

### Prompt A — 기반 설계 / v2 아키텍처 재정의

```text
모델: Claude Opus
스킬: writing-plans, brainstorming, claude-md-management
에이전트: 단일

작업 목표:
TerraSight를 현재 Render 중심 실시간 백엔드 구조에서 Cloudflare Pages + Worker + R2 + Python 배치 파이프라인 구조로 재설계하라.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 를 읽어라.
2. docs/project-blueprint.md 와 현재 Globe 상태 문서를 읽고, 유지할 것 / 제거할 것 / 보류할 것을 분류하라.
3. 구조적 문제를 10줄 이내로 요약하라.

산출물:
- docs/architecture/architecture-v2.md
- docs/architecture/mvp-scope-v2.md
- docs/architecture/data-source-policy.md
- CLAUDE.md 업데이트
- progress.md 업데이트

설계 요구사항:
- Globe Lite / Atlas Lite / Reports Static 구조를 명확히 정의할 것
- Render runtime rasterization 제거
- Open-Meteo를 MVP 프로덕션 핵심에서 제외
- GIBS/FIRMS/USGS 중심으로 재정의
- Cloudflare Pages/Workers/R2/GitHub Actions 역할을 분리
- 모노레포 구조와 데이터 계약 초안을 포함

수락 기준:
- 문서만 읽어도 새 팀원이 구현 방향을 이해할 수 있어야 한다
- 금지사항과 허용사항이 분명해야 한다
- CLAUDE.md에는 핵심 규칙만 남기고 길어지지 않게 유지할 것
- 마지막에 progress.md의 Current Phase, Decisions, Next Actions를 최신화할 것
```

---

### Prompt B — API Spike / 데이터 소스 검증 병렬 조사

```text
모델: 오케스트레이터 Claude Opus / 병렬 서브에이전트 Claude Sonnet
스킬: dispatching-parallel-agents, writing-plans, claude-md-management
에이전트: 4 병렬

작업 목표:
TerraSight v2 MVP에서 사용할 데이터 소스를 병렬로 검증하고, 각 소스의 인증 여부 / 전지구 커버리지 / 응답 형식 / 캐시 전략 / 프로덕션 적합성을 문서화하라.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 읽기
2. architecture-v2 문서가 있으면 먼저 읽기
3. 검증 기준표를 먼저 만들기: auth, rate limit, coverage, cadence, latency, payload size, client-direct 가능 여부

병렬 분담:
- Agent 1: GIBS imagery 계열
- Agent 2: FIRMS / USGS 이벤트 계열
- Agent 3: NOAA ERDDAP point query 및 해양 계열
- Agent 4: CAMS / ERA5 / GFS 후속 파이프라인 적합성 조사

산출물:
- docs/datasets/source-spike-matrix.md
- docs/datasets/gibs-approved-layers.md
- docs/datasets/runtime-vs-batch-sources.md
- 필요 시 샘플 응답 fixture 저장
- CLAUDE.md 업데이트
- progress.md 업데이트

중요 규칙:
- MVP 승인 / 보류 / 금지 소스를 명확히 구분하라
- Open-Meteo는 참고용으로만 정리하고 승인 목록에 넣지 마라
- 각 소스마다 Trust Tag 후보와 caveat를 적어라

수락 기준:
- 구현 전에 어떤 데이터가 프로덕션 승인인지 명확해야 한다
- MVP용 레이어 6개에 필요한 소스가 확정되어야 한다
- 마지막에 progress.md에 승인/보류 목록과 다음 구현 대상을 남겨라
```

---

### Prompt C — 프로젝트 세팅 / 모노레포 및 배포 베이스 구축

```text
모델: Claude Opus
스킬: executing-plans, claude-md-management
에이전트: 단일 순차

작업 목표:
기존 TerraSight repo를 v2 모노레포 구조로 정리하고, Astro web / Cloudflare Worker / shared schemas / Python pipelines의 뼈대를 구축하라.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 읽기
2. 현재 repo 구조를 스캔하고 유지/이동/삭제 후보를 분류하라
3. 변경 계획을 먼저 제시한 뒤 적용하라

구현 범위:
- apps/web 생성 또는 마이그레이션
- apps/worker 생성
- packages/schemas 생성
- pipelines 디렉토리 생성
- pnpm workspace / pyproject 설정
- lint / format / test 기본 명령 통일
- .claude/settings.json 점검
- docs/architecture에 현재 repo 구조 문서화

산출물:
- 실제 디렉토리 구조 반영
- 최소 실행 가능한 web / worker / pipeline scaffold
- README 또는 docs/setup/local-dev.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 로컬에서 web, worker, pipeline 명령이 각각 실행 가능해야 한다
- 새 구조가 문서와 실제 repo에서 일치해야 한다
- 변경 파일 목록과 남은 마이그레이션 항목을 progress.md에 남겨라
```

---

### Prompt D — 커넥터 개발 / v2 승인 소스 구현

```text
모델: 오케스트레이터 Claude Opus / 병렬 서브에이전트 Claude Opus
스킬: subagent-driven-development, dispatching-parallel-agents, claude-md-management
에이전트: 3~4 병렬

작업 목표:
승인된 v2 데이터 소스를 기준으로 Python connectors와 Worker service layer를 구현하라. 우선순위는 GIBS manifest, FIRMS, USGS, NOAA ERDDAP point query다.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 읽기
2. source-spike-matrix와 architecture-v2 문서 읽기
3. 공통 응답 스키마와 에러 정책을 먼저 확정하라

병렬 분담 예시:
- Agent 1: GIBS layer manifest / legend / metadata 정리
- Agent 2: FIRMS connector + cache strategy + fixtures
- Agent 3: USGS connector + severity mapping + fixtures
- Agent 4: NOAA ERDDAP SST point query connector + validation

구현 규칙:
- 모든 커넥터는 fixture 기반 테스트를 가져야 한다
- 공통 schema validation을 통과해야 한다
- raw 응답을 UI에 직접 노출하지 말고 normalized contract로 변환할 것
- retries, timeouts, cache TTL을 명시할 것

산출물:
- pipelines/connectors/*
- apps/worker/src/services/*
- packages/schemas/*
- tests/fixtures 및 계약 테스트
- docs/datasets/normalized-contracts.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 각 커넥터가 독립 테스트 가능해야 한다
- Worker에서 소비 가능한 normalized shape가 고정되어야 한다
- progress.md에 어떤 소스가 구현 완료인지 남겨라
```

---

### Prompt E — Report API 대신 Report Build Pipeline 구현

```text
모델: Claude Opus
스킬: executing-plans, systematic-debugging, claude-md-management
에이전트: 단일 순차

작업 목표:
기존 Report API 중심 구조를 폐기하고, 도시별 report.json을 생성하는 배치 파이프라인으로 대체하라.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 읽기
2. 현재 Report 관련 코드와 데이터 흐름을 파악하라
3. 어떤 부분을 런타임에서 빌드타임으로 옮길지 표로 정리하라

구현 범위:
- CityReport schema 정의
- metro/city source registry 정의
- report builder job 구현
- block composer 구현
- rankings JSON 생성기 구현
- sample city 3개로 end-to-end 생성 검증

필수 정책:
- 모든 Report는 정적 생성 전제로 설계
- 블록별 Trust Tag 필수
- citations / updatedAt / caveats 포함
- 데이터가 없는 블록은 숨기거나 “데이터 없음” 정책을 일관되게 적용

산출물:
- pipelines/jobs/build_reports.py
- data/reports/*.json
- data/rankings/*.json
- docs/reports/report-schema.md
- docs/reports/report-block-policy.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 샘플 도시 3개 report.json 생성 가능
- schema validation 통과
- 앞으로 50개 도시 확장이 가능한 구조여야 한다
- progress.md에 샘플 생성 결과와 남은 도시 확장 계획을 남겨라
```

---

### Prompt F — 홈/Globe 프런트 구현

```text
모델: 오케스트레이터 Claude Opus / 병렬 서브에이전트 Claude Opus
스킬: subagent-driven-development, frontend-design, claude-md-management
에이전트: 2~3 병렬

작업 목표:
Astro 홈과 React/Cesium Globe를 v2 구조로 구현하라. 홈은 SEO 친화적 랜딩, Globe는 /globe 라우트의 client island로 분리하라.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 읽기
2. architecture-v2와 approved layer manifest를 읽기
3. 홈과 Globe의 역할을 분리한 UI 정보구조를 먼저 제안하라

병렬 분담 예시:
- Agent 1: Globe island, layer switching, event popups
- Agent 2: 홈 랜딩, trend strip, featured reports, atlas links
- Agent 3: legend / trust tag / mobile fallback UX

구현 규칙:
- 홈은 정적 페이지 우선
- Globe는 무거운 Cesium 번들을 홈에서 즉시 로드하지 말 것
- GIBS imagery direct load
- 이벤트 데이터는 Worker API 경유
- layer/legend/trust tag 설명은 항상 UI에 노출

산출물:
- apps/web/src/pages/index.astro
- apps/web/src/pages/globe.astro
- apps/web/src/islands/GlobeApp.tsx
- apps/web/src/components/*
- docs/architecture/frontend-routing.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 홈은 SEO-friendly HTML로 렌더링
- Globe는 6개 MVP 레이어를 안정적으로 표시
- 이벤트 팝업과 기본 legend가 동작
- progress.md에 실제 동작 확인 항목을 남겨라
```

---

### Prompt G — Report 프런트 구현

```text
모델: 오케스트레이터 Claude Opus / 병렬 서브에이전트 Claude Opus
스킬: subagent-driven-development, frontend-design, claude-md-management
에이전트: 2~3 병렬

작업 목표:
정적 생성된 CityReport JSON을 소비하는 Report 페이지를 구현하라. 우선 3개 샘플 도시로 시작하고, 50개 확장 가능 구조로 만들어라.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 읽기
2. CityReport schema와 report-block-policy 문서를 읽기
3. 블록 렌더링 규칙과 없는 데이터 처리 규칙을 먼저 정리하라

병렬 분담 예시:
- Agent 1: report layout / hero / summary / methodology
- Agent 2: block renderer / metrics / citations / trust tags
- Agent 3: related cities / ranking snippets / ad slot placeholders

구현 규칙:
- 모든 블록은 Trust Tag와 updatedAt 맥락을 보여줄 것
- thin content를 피하도록 block minimum content 기준을 적용할 것
- 구조화 데이터(가능하면 Article / Dataset / Breadcrumb)를 고려할 것
- 광고 슬롯은 레이아웃을 깨지 않는 placeholder로 먼저 구현

산출물:
- apps/web/src/pages/reports/[...slug].astro
- report components
- sample static paths
- docs/reports/report-page-ux.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 샘플 도시 3개가 정적으로 렌더링되어야 한다
- 블록 누락/빈 값 정책이 일관적이어야 한다
- progress.md에 어떤 블록이 구현됐는지 남겨라
```

---

### Prompt H — SEO / 수익화 구조 구현

```text
모델: Claude Opus
스킬: writing-plans, brainstorming, executing-plans, claude-md-management
에이전트: 단일

작업 목표:
TerraSight v2의 SEO 및 수익화 구조를 정적 사이트 기준으로 설계하고 구현하라. Reports, Rankings, Guides, internal linking, metadata, sitemap, ad slot policy를 정리하라.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 읽기
2. 현재 route 구조와 샘플 page 상태를 점검하라
3. 검색 유입 관점에서 landing hierarchy를 먼저 설계하라

구현 범위:
- route taxonomy 정리
- metadata / OG / canonical 정책
- sitemap / robots 정책
- rankings page scaffold
- guides page scaffold
- report↔atlas↔globe internal linking 규칙
- ad slot placement rules 문서화

산출물:
- docs/architecture/seo-ia.md
- apps/web metadata helpers
- rankings / guides page scaffold
- docs/revenue/adsense-placement-policy.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 어떤 페이지가 유입용, 체류용, 수익용인지 명확해야 한다
- internal linking 전략이 구현과 문서에서 일치해야 한다
- progress.md에 남은 콘텐츠 생산 목록을 적어라
```

---

### Prompt I — Reviewer 검증

```text
모델: Claude Opus
스킬: verification-before-completion, claude-md-management
에이전트: 단일

작업 목표:
현재 브랜치의 구현을 CLAUDE.md 규칙, architecture-v2, data contracts와 대조 검증하라. 특히 Trust Tag 누락, 금지 소스 사용, 런타임 계산 회귀를 집중 검사하라.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 읽기
2. 문서 기준의 must / must-not 체크리스트를 먼저 작성하라
3. 변경 파일 범위를 기준으로 검증 대상을 좁혀라

검증 항목:
- Render runtime 의존이 남아 있는가
- Open-Meteo가 프로덕션 핵심 경로에 남아 있는가
- Report가 정적 생성 전제로 설계됐는가
- 모든 dataset/report block에 Trust Tag가 있는가
- schema와 실제 payload가 일치하는가
- 홈과 Globe 역할이 분리됐는가

산출물:
- docs/review/review-checklist.md 또는 review memo
- 수정 필요 항목 목록
- 필요한 경우 작은 수정 커밋
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- pass / fail가 명확해야 한다
- 규칙 위반이 있으면 반드시 파일 단위로 지적해야 한다
- progress.md에 남은 리스크와 release blocker를 남겨라
```

---

### Prompt J — QA / E2E / 회귀 점검

```text
모델: Claude Sonnet (실패 원인 추적이 필요하면 Claude Opus로 재실행)
스킬: executing-plans, systematic-debugging, claude-md-management
에이전트: 단일

작업 목표:
TerraSight v2 MVP의 핵심 경로를 테스트하고, 실패 시 원인을 재현 가능한 형태로 기록하라.

반드시 먼저 할 일:
1. @CLAUDE.md @progress.md 읽기
2. MVP 핵심 사용자 경로를 먼저 정의하라
3. 테스트 우선순위를 home → globe → report → atlas 순으로 두어라

테스트 범위:
- 홈 렌더링
- /globe 진입 및 기본 레이어 로드
- fires / earthquakes API 응답
- sst point query
- sample report 3개 정적 렌더링
- atlas dataset 페이지 렌더링
- metadata / sitemap / broken links

산출물:
- test results summary
- 재현 단계가 있는 bug list
- Playwright/Vitest/Pytest 보강이 필요하면 추가
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- MVP 핵심 경로의 pass/fail가 정리되어야 한다
- 실패는 반드시 재현 단계와 원인 가설을 포함해야 한다
- progress.md에 남은 버그와 출시 가능 여부를 남겨라
```

---

## 13. 권장 실행 순서

1. Prompt A — 기반 설계
2. Prompt B — API Spike
3. Prompt C — 프로젝트 세팅
4. Prompt D — 커넥터 개발
5. Prompt E — Report Build Pipeline
6. Prompt F — 홈/Globe 프런트
7. Prompt G — Report 프런트
8. Prompt H — SEO/수익화
9. Prompt I — Reviewer 검증
10. Prompt J — QA/E2E

---

## 14. 최종 운영 원칙 한 줄 요약

**TerraSight v2는 "무거운 실시간 분석 앱"이 아니라, "전지구 환경 관측 포털 + 정적 지역 리포트 + 신뢰도 중심 데이터 허브"로 운영한다.**
