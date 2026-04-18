# TerraSight v2 — 단계별 Claude CLI 프롬프트

**작성일:** 2026-04-17
**기반 문서:** `docs/terrasight_v2_architecture_and_prompts.md`
**목적:** v2 재설계(Globe Lite + Atlas Lite + Reports Static)를 Claude CLI에서 단계별로 실행하기 위한 복붙용 프롬프트 묶음. 현재 repo(`CLAUDE.md`의 7개 운영 규칙)와 정합되도록 각 Step에 준수 사항을 명시했다.

---

## 0. 공통 운영 규칙 (모든 Step 앞에 자동 적용)

모든 프롬프트에는 다음 규칙이 **암묵적으로 포함**되어 있다. 각 Step에서 반복 서술하지 않되, 작업 중 항상 준수한다.

### 0.1 세션 시작 체크리스트
1. `@CLAUDE.md` 를 먼저 읽는다. (이미 현재 컨텍스트에 있으면 다시 읽지 않는다 — Rule 1)
2. `@progress.md` 를 읽고 현재 Phase와 Next Actions를 확인한다.
3. 관련된 `docs/*.md`만 선별적으로 읽는다 (전체 스캔 금지).

### 0.2 CLAUDE.md 7개 운영 규칙 (Claude가 반드시 지킬 것)
1. **이미 읽은 파일을 다시 읽지 않는다.** 대화 컨텍스트에 존재하면 재-Read 금지.
2. **독립적인 도구 호출은 병렬로 묶는다.** 데이터 의존성이 없는 Read/Glob/Grep은 한 메시지에서 다중 호출.
3. **광범위한 탐색은 sub-agent에 위임한다.** `Explore` / `general-purpose` / `ecc:*` 전문 에이전트 사용. 2개 이상 독립 커넥터 구현이면 `dispatching-parallel-agents` 적용.
4. **발견한 landmine은 즉시 기록한다.** URL quirk, 스키마 변경, 파라미터 함정 → 해당 커넥터 docstring + `docs/guardrails.md` landmine 표에 기록 후 완료 처리.
5. **Graceful degradation은 필수.** 커넥터 실패 / API 키 부재 / 미완성 기능은 5xx나 빈 UI가 아니라 구조화된 `status` 필드(`ok` / `error` / `not_configured` / `pending`) 반환.
6. **작업 종료 시 `progress.md` 갱신 필수.** 완료 항목, 변경 수치, Next Actions, Blockers — 생략 불가.
7. **95% 확신 전에는 수정 금지.** 계획/진단에 모호함이 있으면 편집 전에 명확화 질문부터.

### 0.3 모델 선택 기준
| 작업 유형 | 기본 모델 |
|----------|---------|
| 아키텍처 설계 / Repo 구조 변경 / 데이터 계약 / Worker 코어 / Globe 핵심 로직 / Report pipeline / 근본원인 디버깅 / 최종 리뷰 | **Claude Opus** |
| 반복 콘텐츠 입력 / 스타일 수정 / 테스트 케이스 확장 / 문서 정리 / 기존 패턴 복제 | **Claude Sonnet** |

> **프로덕션 코드에 영향을 주는 핵심 구현은 Opus 기본.** Sonnet은 보조 확장/반복 작업에만 제한적으로 사용.

### 0.4 데이터 소스 정책 (v2)
- **프로덕션 허용(1순위):** NASA GIBS, NASA FIRMS, USGS, NOAA ERDDAP(point query)
- **프로덕션 허용(2순위):** EPA / NOAA / USGS / 기타 정부 무인증 데이터
- **배치 파이프라인(3순위):** CAMS / ERA5 / GFS
- **프로덕션 제외:** Open-Meteo 의존 레이어, 요청 시점 래스터 생성

### 0.5 표기 규칙
- PM2.5 대신 AOD을 쓸 때 반드시 **"에어로졸 프록시"** 로 표기
- OCO-2는 **"Total Column CO₂"**
- MERRA-2 월평균은 "현재 날씨"로 보이지 않게

---

## 1. 실행 순서 (권장)

```
Step 1 (Prompt A)  기반 설계 / v2 아키텍처 재정의
Step 2 (Prompt B)  API Spike / 데이터 소스 검증 (병렬)
Step 3 (Prompt C)  프로젝트 세팅 / 모노레포 구축
Step 4 (Prompt D)  커넥터 개발 (병렬)
Step 5 (Prompt E)  Report Build Pipeline
Step 6 (Prompt F)  홈 / Globe 프런트
Step 7 (Prompt G)  Report 프런트
Step 8 (Prompt H)  SEO / 수익화 구조
Step 9 (Prompt I)  Reviewer 검증
Step 10 (Prompt J) QA / E2E / 회귀 점검
```

앞 Step의 산출물(문서/스키마)이 뒤 Step의 입력이므로 **건너뛰기 금지**. 단 Step 9/10은 매 Step 완료 시마다 부분 적용 가능.

---

## Step 1 — 기반 설계 / v2 아키텍처 재정의

**모델:** Claude Opus
**스킬:** `superpowers:writing-plans` · `superpowers:brainstorming` · `claude-md-management:revise-claude-md`
**에이전트:** 단일

### 작업 목표
TerraSight를 현재 Render 상시 FastAPI + Open-Meteo 의존 구조에서 **Cloudflare Pages + Worker + R2 + Python 배치 파이프라인** 구조로 재설계한다.

### 프롬프트 (그대로 붙여넣기)
```text
/model opus

@CLAUDE.md 와 @progress.md 읽어.
그 다음 @docs/project-blueprint.md 와 @docs/globe-vision.md 를 읽고,
TerraSight v2 아키텍처를 재정의해줘.

작업 원칙:
- CLAUDE.md 7개 운영 규칙을 준수할 것 (특히 Rule 2 병렬 호출, Rule 7 95% 확신).
- 관련 없는 파일은 Read 하지 말 것. 
- 문서가 길어지면 세부 절차는 .claude/skills/ 로 빼고 CLAUDE.md는 1~2 screen 유지.

수행 절차:
1. project-blueprint.md 와 globe-vision.md 를 기준으로
   [유지 / 제거 / 보류] 3분류 표를 만들어.
2. 현재 구조적 문제를 10줄 이내로 요약.
3. v2 아키텍처 결정 사항을 문서로 확정.

산출물:
- docs/architecture/architecture-v2.md
  → Globe Lite / Atlas Lite / Reports Static 구조 정의
- docs/architecture/mvp-scope-v2.md
  → MVP 6개 Globe 레이어 + 8개 Report 핵심 블록 고정
- docs/architecture/data-source-policy.md
  → 1/2/3순위 소스와 프로덕션 제외 소스 명확화
- CLAUDE.md 업데이트 (Non-Negotiable Rules 섹션 추가)
- progress.md 업데이트 (Current Phase = "v2 Architecture Reset")

필수 금지/허용:
- Render 상시 런타임 rasterization 제거
- Open-Meteo 를 MVP 프로덕션 핵심에서 제외
- GIBS / FIRMS / USGS / NOAA ERDDAP 중심으로 재정의
- Cloudflare Pages / Workers / R2 / GitHub Actions 역할 분리
- 모노레포 구조(apps/, packages/, pipelines/)와 데이터 계약 초안 포함

수락 기준:
- 문서만 읽어도 새 팀원이 구현 방향을 이해 가능
- 금지사항과 허용사항 명확
- CLAUDE.md 는 짧고 강한 규칙만 유지
- progress.md 의 Current Phase / Decisions / Next Actions 갱신 완료

작업 종료 시 landmine 이 있으면 docs/guardrails.md 에 추가.
```

### 산출물 체크
- [ ] `docs/architecture/architecture-v2.md`
- [ ] `docs/architecture/mvp-scope-v2.md`
- [ ] `docs/architecture/data-source-policy.md`
- [ ] `CLAUDE.md` (Non-Negotiable Rules 반영)
- [ ] `progress.md` (Current Phase = v2 Architecture Reset)

---

## Step 2 — API Spike / 데이터 소스 검증 (병렬 조사)

**모델:** 오케스트레이터 Opus / 서브에이전트 Sonnet
**스킬:** `superpowers:dispatching-parallel-agents` · `superpowers:writing-plans`
**에이전트:** 4개 병렬

### 작업 목표
v2 MVP에서 사용할 데이터 소스를 **병렬 검증**하고, auth · rate limit · coverage · cadence · latency · payload size · client-direct 가능 여부를 문서화한다.

### 프롬프트
```text
/model opus

@CLAUDE.md 와 @progress.md 와 @docs/architecture/architecture-v2.md 와 @docs/api-spike-results.md 읽어.

작업 원칙:
- Rule 3 준수: 4개 병렬 서브에이전트로 분할 (dispatching-parallel-agents).
- Rule 2 준수: 각 에이전트 안에서도 curl 프로브를 병렬로.
- 각 소스마다 샘플 응답을 fixtures/ 에 남길 것.

선행 작업:
1. 검증 기준표를 먼저 만들어:
   auth · rate limit · coverage · cadence · latency · payload size · client-direct · 필요 헤더
2. 기준표를 서브에이전트 4개에 공통 배포.

병렬 분담:
- Agent 1: GIBS imagery (BlueMarble, SST, AOD, Clouds, Night Lights)
- Agent 2: FIRMS(산불) / USGS(지진) 이벤트 계열
- Agent 3: NOAA ERDDAP point query 및 해양 계열(OISST, CRW DHW)
- Agent 4: CAMS / ERA5 / GFS 후속 배치 파이프라인 적합성 조사

각 에이전트 산출물:
- 테이블 한 줄 per layer + 샘플 응답 + caveat
- Trust Tag 후보(observed / near-real-time / forecast / derived / compliance)

통합 산출물:
- docs/datasets/source-spike-matrix.md
- docs/datasets/gibs-approved-layers.md (6개 MVP 레이어 확정)
- docs/datasets/runtime-vs-batch-sources.md
- data/fixtures/<source>/sample-*.json (최소 1건씩)
- CLAUDE.md 업데이트 (승인 목록 반영)
- progress.md 업데이트 (승인/보류/금지 구분 + 다음 구현 대상)

중요 규칙:
- MVP 승인 / 보류 / 금지를 반드시 구분
- Open-Meteo 는 "참고용"으로만 정리, 승인 목록 금지
- 각 소스에 Trust Tag 와 caveat 필수
- landmine(URL 변경 이력, 스키마 rename 등) 발견 즉시 docs/guardrails.md 에 추가

수락 기준:
- MVP 6개 Globe 레이어에 필요한 소스 확정
- 어떤 데이터가 프로덕션 승인인지 명확
- progress.md 에 승인 / 보류 / 금지 목록과 다음 구현 대상이 남아있음
```

### 산출물 체크
- [ ] `docs/datasets/source-spike-matrix.md`
- [ ] `docs/datasets/gibs-approved-layers.md`
- [ ] `docs/datasets/runtime-vs-batch-sources.md`
- [ ] `data/fixtures/*` 샘플 응답
- [ ] `docs/guardrails.md` landmine 갱신

---

## Step 3 — 프로젝트 세팅 / 모노레포 구축

**모델:** Claude Opus
**스킬:** `superpowers:executing-plans` · `claude-md-management:revise-claude-md`
**에이전트:** 단일 순차

### 작업 목표
기존 `backend/` + `frontend/` 구조를 **v2 모노레포** (`apps/web` + `apps/worker` + `packages/schemas` + `pipelines/`) 로 재편성하고 기본 스캐폴드를 실행 가능한 상태로 만든다.

### 프롬프트
```text
/model opus

@CLAUDE.md 와 @progress.md 와 @docs/architecture/architecture-v2.md 읽어.

작업 원칙:
- Rule 7 준수: 실제 이동 전에 [유지 / 이동 / 삭제] 후보 분류를 먼저 보여주고 승인받기.
- Rule 5 준수: 마이그레이션 중에도 기존 /api 경로가 graceful 하게 degrade 되도록.
- 파일 이동은 git mv 로 추적 유지.

선행 작업:
1. 현재 repo 의 backend/ + frontend/ 를 스캔해서
   [keep / move to apps/* / deprecate / delete candidate] 표 작성.
2. 사용자에게 표를 제시 → 승인 후 실행.

구현 범위:
- apps/web/               → Astro + React + TS scaffold
  - src/pages/ (index, globe, atlas/, reports/, guides/, rankings/)
  - src/islands/ (React hydration 대상만)
  - src/components/ · layouts/ · lib/
- apps/worker/            → Cloudflare Worker (Hono 기반)
  - src/routes/ · services/ · cache/ · index.ts
  - wrangler.jsonc
- packages/schemas/       → zod 공유 계약
- packages/ui/            → presentational 컴포넌트
- packages/config/        → ts/eslint/prettier 공유
- pipelines/              → Python 3.11 (connectors/ · jobs/ · transforms/ · publish/)
- pnpm-workspace.yaml · pyproject.toml
- .claude/settings.json 점검 (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)

필수 산출물:
- 실제 디렉토리 구조 반영 커밋
- 최소 실행 가능 scaffold
  - pnpm --filter web dev 동작
  - pnpm --filter worker dev (wrangler) 동작
  - uv run pytest pipelines/tests/ 동작(빈 테스트라도 pass)
- docs/setup/local-dev.md (명령 모음)
- docs/architecture/repo-layout.md (실제 반영 구조)
- CLAUDE.md 업데이트
- progress.md 업데이트 (파일 이동 목록 + 남은 마이그레이션)

landmine 후보:
- Cloudflare Pages 빌드 경로 변경 필요 → wrangler.jsonc + pages-build-output-dir
- backend/ 제거 시 Render 배포 설정 영향 확인

수락 기준:
- 로컬에서 web / worker / pipeline 각 명령 실행 가능
- 문서와 실제 repo 구조 일치
- progress.md 에 변경 파일 목록과 남은 마이그레이션 항목이 있음
```

### 산출물 체크
- [ ] `apps/web/` · `apps/worker/` · `packages/` · `pipelines/`
- [ ] `pnpm-workspace.yaml` · `pyproject.toml`
- [ ] `docs/setup/local-dev.md`
- [ ] `.claude/settings.json`

---

## Step 4 — 커넥터 개발 (병렬)

**모델:** 오케스트레이터 Opus / 서브에이전트 Opus
**스킬:** `superpowers:subagent-driven-development` · `superpowers:dispatching-parallel-agents`
**에이전트:** 3~4 병렬

### 작업 목표
승인된 v2 소스를 기준으로 **Python connectors** 와 **Worker service layer** 를 구현한다. 우선순위: GIBS manifest · FIRMS · USGS · NOAA ERDDAP.

### 프롬프트
```text
/model opus

@CLAUDE.md 와 @progress.md 와 @docs/datasets/source-spike-matrix.md 와 @docs/architecture/architecture-v2.md 와 @docs/connectors.md 읽어.

작업 원칙:
- Rule 3 준수: 4 병렬 서브에이전트 (subagent-driven-development).
- Rule 4 준수: 각 커넥터 docstring 에 발견한 landmine 기록. 동시에 docs/guardrails.md 업데이트.
- Rule 5 준수: 모든 커넥터는 실패 시 status=error 로 graceful degrade.

선행 작업:
1. 공통 응답 스키마(packages/schemas/)와 에러 정책 확정:
   - EventPoint / LayerManifest / TrustTag 타입 → zod + python pydantic 동기화
   - retry · timeout · cache TTL 정책 확정
2. fixtures 디렉토리 레이아웃 확정.

병렬 분담:
- Agent 1: GIBS layer manifest / legend / metadata
  → pipelines/connectors/gibs.py + packages/schemas/layer.ts
- Agent 2: FIRMS connector + cache strategy + fixtures
  → pipelines/connectors/firms.py + apps/worker/src/routes/fires.ts
- Agent 3: USGS(earthquake) connector + severity mapping + fixtures
  → pipelines/connectors/usgs.py + apps/worker/src/routes/earthquakes.ts
- Agent 4: NOAA ERDDAP SST point query connector
  → pipelines/connectors/erddap_sst.py + apps/worker/src/routes/sst-point.ts

구현 규칙:
- 모든 커넥터는 fixture 기반 테스트 보유
- 공통 schema validation 통과
- raw 응답을 UI 에 직접 노출 금지 → normalized contract 변환
- retries / timeouts / cache TTL 명시 (예: FIRMS 600s, USGS 300s, SST 3600s)
- Open-Meteo 의존 금지

산출물:
- pipelines/connectors/{gibs,firms,usgs,erddap_sst}.py
- apps/worker/src/services/* + routes/*
- packages/schemas/* (TrustTag, LayerManifest, EventPoint, DatasetRegistryItem)
- pipelines/tests/fixtures/*
- pipelines/tests/test_*_contract.py (계약 테스트)
- docs/datasets/normalized-contracts.md
- CLAUDE.md 업데이트
- progress.md 업데이트 (커넥터 완료 목록 + 엔드포인트 수)

수락 기준:
- 각 커넥터 독립 테스트 가능 (pytest pipelines/tests)
- Worker 에서 소비 가능한 normalized shape 고정
- progress.md 에 구현 완료 소스 목록이 있음
```

### 산출물 체크
- [ ] `pipelines/connectors/*.py` (4개)
- [ ] `apps/worker/src/routes/*` (fires · earthquakes · sst-point)
- [ ] `packages/schemas/*`
- [ ] `pipelines/tests/fixtures/*`
- [ ] `docs/datasets/normalized-contracts.md`

---

## Step 5 — Report Build Pipeline (Runtime → Batch 전환)

**모델:** Claude Opus
**스킬:** `superpowers:executing-plans` · `superpowers:systematic-debugging`
**에이전트:** 단일 순차

### 작업 목표
기존 Report API (`/api/reports/{slug}`) 를 폐기하고, **도시별 `report.json` 을 빌드타임에 생성**하는 배치 파이프라인으로 대체한다.

### 프롬프트
```text
/model opus

@CLAUDE.md 와 @progress.md 와 @docs/report-spec.md 와 @docs/datasets/normalized-contracts.md 읽어.

작업 원칙:
- Rule 7 준수: 런타임 → 빌드타임 이동 대상을 표로 먼저 확정 후 실행.
- Rule 5 준수: 블록별 데이터 부재 시 "데이터 없음" 정책 일관 적용.
- Rule 4 준수: 블록별 trust tag 누락 / citation 누락 등 발견 시 guardrails.md 에 기록.

선행 작업:
1. 현재 Report API 코드와 데이터 흐름을 파악.
2. [런타임 유지 / 빌드타임 이동 / 제거] 표를 먼저 정리 후 승인.

구현 범위:
- packages/schemas/report.ts : CityReport zod 스키마
- pipelines/jobs/build_reports.py : 도시 목록 → connectors → normalized → block composer → report.json
- pipelines/transforms/block_composer.py : 8개 핵심 블록 + 선택 확장 블록
  핵심 8:
    1. 대기질
    2. 기후/열환경
    3. 재해 노출
    4. 음용수/수질
    5. 산업시설·배출
    6. 오염부지·정화
    7. 인구 노출/환경정의
    8. 방법론 + 데이터 신뢰 설명
  선택: PFAS / 해안 / 세부 재해 이력 / 도시 비교 / 관련 도시
- pipelines/jobs/build_rankings.py : rankings JSON 생성기
- 샘플 3개 도시로 E2E 생성 검증 (예: New York / Los Angeles / Houston)

정책:
- 모든 Report 는 정적 생성 전제
- 블록별 Trust Tag 필수 (TrustTag union 값 중 하나 이상)
- citations / updatedAt / caveats 필수
- 데이터 부재 블록은 숨기거나 "데이터 없음" 표시 — 정책 일관성 유지
- ECHO / WQP / AirNow 의무 disclaimer 포함

산출물:
- pipelines/jobs/build_reports.py · build_rankings.py
- pipelines/transforms/block_composer.py
- data/reports/*.json (샘플 3개)
- data/rankings/*.json
- docs/reports/report-schema.md
- docs/reports/report-block-policy.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 샘플 도시 3개 report.json 생성 가능
- packages/schemas/report.ts 로 validation 통과
- 50개 도시 확장 가능한 구조 (도시 레지스트리 기반)
- progress.md 에 샘플 생성 결과 + 확장 계획
```

### 산출물 체크
- [ ] `pipelines/jobs/build_reports.py` · `build_rankings.py`
- [ ] `data/reports/*.json` (샘플 3개)
- [ ] `docs/reports/report-schema.md`
- [ ] `docs/reports/report-block-policy.md`

---

## Step 6 — 홈 / Globe 프런트 구현

**모델:** 오케스트레이터 Opus / 서브에이전트 Opus
**스킬:** `superpowers:subagent-driven-development` · `ecc:frontend-design`
**에이전트:** 2~3 병렬

### 작업 목표
**Astro 홈** (SEO 친화 랜딩) 과 **React/Cesium Globe** (`/globe` 라우트 client island) 를 v2 구조로 구현한다. Globe 번들을 홈에서 즉시 로드하지 않는다.

### 프롬프트
```text
/model opus

@CLAUDE.md 와 @progress.md 와 @docs/architecture/architecture-v2.md 와 @docs/datasets/gibs-approved-layers.md 읽어.
먼저 ecc:frontend-design 스킬 읽고 시작해.

작업 원칙:
- Rule 3 준수: 2~3 병렬 서브에이전트.
- Rule 5 준수: GIBS 타일 실패 시 legend + "데이터 불러오는 중" placeholder.
- Globe 번들은 /globe 라우트에서만 hydration (index.astro 금지).

선행 작업:
1. 홈 ↔ Globe 역할 분리 UI 정보구조 제안 후 승인.
2. MVP 6개 레이어를 gibs-approved-layers.md 와 대조.

병렬 분담:
- Agent 1: Globe island
  - apps/web/src/islands/GlobeApp.tsx
  - layer switching (6개 MVP 레이어)
  - event popup (fires / earthquakes)
  - client:visible hydration
- Agent 2: 홈 랜딩
  - apps/web/src/pages/index.astro
  - trend strip (CO₂ / Temp / Sea Ice — 정적 JSON 소비)
  - featured reports (3~5개)
  - atlas / guides 링크
- Agent 3: Legend / TrustTag / mobile fallback
  - packages/ui/Legend.tsx
  - packages/ui/TrustTag.tsx
  - Globe 의 모바일 fallback (Static map preview 또는 "데스크톱 권장")

구현 규칙:
- 홈은 정적 페이지 우선 (Astro SSG)
- Globe 는 Cesium/deck.gl 번들 lazy load
- GIBS imagery 는 브라우저 직접 로드 (Worker 경유 금지)
- 이벤트 데이터(fires/earthquakes)는 Worker API 경유
- layer · legend · trust tag 설명은 항상 UI 노출
- PM2.5 대용으로 AOD 쓸 경우 "에어로졸 프록시" 라벨 필수
- 클릭 조회: SST 만 우선 지원, 나머지 표면 레이어는 설명 중심

산출물:
- apps/web/src/pages/index.astro
- apps/web/src/pages/globe.astro
- apps/web/src/islands/GlobeApp.tsx
- apps/web/src/components/*
- packages/ui/Legend.tsx · TrustTag.tsx
- docs/architecture/frontend-routing.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 홈: SEO-friendly HTML (view-source 에서 텍스트 렌더 확인)
- Globe: 6개 MVP 레이어 안정 표시
- 이벤트 팝업 동작 + 기본 legend 노출
- 번들 사이즈: index 라우트 200KB 이하 gzipped
- progress.md 에 실제 동작 확인 항목 기록
```

### 산출물 체크
- [ ] `apps/web/src/pages/index.astro` · `globe.astro`
- [ ] `apps/web/src/islands/GlobeApp.tsx`
- [ ] `packages/ui/Legend.tsx` · `TrustTag.tsx`
- [ ] `docs/architecture/frontend-routing.md`

---

## Step 7 — Report 프런트 구현

**모델:** 오케스트레이터 Opus / 서브에이전트 Opus
**스킬:** `superpowers:subagent-driven-development` · `ecc:frontend-design`
**에이전트:** 2~3 병렬

### 작업 목표
정적 생성된 `report.json` 을 소비하는 Report 페이지 구현. 샘플 3개 도시로 시작, 50개 확장 가능 구조.

### 프롬프트
```text
/model opus

@CLAUDE.md 와 @progress.md 와 @docs/reports/report-schema.md 와 @docs/reports/report-block-policy.md 와 @data/reports/ 의 샘플 3건 읽어.

작업 원칙:
- Rule 3 준수: 2~3 병렬 서브에이전트.
- Rule 5 준수: 블록 누락 / 빈 값 정책 일관 적용.
- Rule 4 준수: 렌더링 중 발견한 데이터 함정(예: updatedAt 누락 케이스)을 guardrails.md 에 기록.

선행 작업:
1. 블록 렌더링 규칙 + 없는 데이터 처리 규칙을 먼저 문서화.
2. getStaticPaths 전략(모든 도시 정적 생성 vs ISR) 승인받기.

병렬 분담:
- Agent 1: Report layout
  - apps/web/src/pages/reports/[...slug].astro
  - hero / summary / methodology 섹션
- Agent 2: Block renderer
  - apps/web/src/components/reports/BlockRenderer.astro
  - metrics / citations / trust tags
  - "데이터 없음" placeholder
- Agent 3: Related cities / rankings / ad slot
  - Related cities 사이드바
  - Rankings 스니펫 카드
  - AdSense placeholder (Step 8 에서 실제 코드로 대체)

구현 규칙:
- 모든 블록은 Trust Tag 와 updatedAt 맥락 표시
- thin content 방지 — block minimum content 기준 적용 (예: 60자 이상)
- 구조화 데이터 (Article / Dataset / Breadcrumb JSON-LD) 포함
- 광고 슬롯은 레이아웃을 깨지 않는 placeholder (<aside data-ad-slot>)
- Internal link: report → atlas dataset → globe layer 연결

산출물:
- apps/web/src/pages/reports/[...slug].astro (getStaticPaths 사용)
- apps/web/src/components/reports/BlockRenderer.astro
- apps/web/src/components/reports/RelatedCities.astro
- 샘플 도시 3개 정적 렌더링
- docs/reports/report-page-ux.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 샘플 도시 3개 정적 렌더링 (pnpm --filter web build 통과)
- 블록 누락/빈 값 정책 일관
- JSON-LD 구조화 데이터 validator 통과
- progress.md 에 구현된 블록 목록
```

### 산출물 체크
- [ ] `apps/web/src/pages/reports/[...slug].astro`
- [ ] `apps/web/src/components/reports/*`
- [ ] `docs/reports/report-page-ux.md`

---

## Step 8 — SEO / 수익화 구조

**모델:** Claude Opus
**스킬:** `superpowers:writing-plans` · `superpowers:brainstorming` · `superpowers:executing-plans` · `ecc:seo`
**에이전트:** 단일

### 작업 목표
TerraSight v2 의 **SEO 및 수익화 구조**를 정적 사이트 기준으로 설계/구현. Reports · Rankings · Guides · 내부 링킹 · metadata · sitemap · ad slot 정책.

### 프롬프트
```text
/model opus

@CLAUDE.md 와 @progress.md 와 @docs/architecture/architecture-v2.md 와 @docs/architecture/frontend-routing.md 읽어.

작업 원칙:
- Rule 7 준수: SEO IA 먼저 승인 후 구현.
- Rule 5 준수: AdSense 실패 시에도 레이아웃 깨지지 않게.

선행 작업:
1. 현재 route 구조 + 샘플 page 상태 점검.
2. 검색 유입 관점의 landing hierarchy 먼저 설계:
   - 유입용 (rankings / guides / report index)
   - 체류용 (report detail / atlas dataset)
   - 수익용 (report detail / rankings)

구현 범위:
- Route taxonomy 정리 + canonical 정책
- metadata / OG / twitter card helpers (apps/web/src/lib/seo.ts)
- sitemap.xml (@astrojs/sitemap) + robots.txt
- Rankings page scaffold (TRI / GHG / Superfund / Drinking Water 등)
- Guides page scaffold (4개 이상)
- report ↔ atlas ↔ globe internal linking 규칙 (packages/ui/InternalLink.tsx)
- Ad slot placement rules (블록 사이 정적 슬롯만)

산출물:
- docs/architecture/seo-ia.md
- apps/web/src/lib/seo.ts
- apps/web/src/pages/rankings/*
- apps/web/src/pages/guides/*
- docs/revenue/adsense-placement-policy.md
- CLAUDE.md 업데이트
- progress.md 업데이트

수락 기준:
- 어떤 페이지가 유입 / 체류 / 수익용인지 명확
- internal linking 전략이 구현과 문서에서 일치
- sitemap.xml 에 모든 정적 경로 포함
- progress.md 에 남은 콘텐츠 생산 목록
```

### 산출물 체크
- [ ] `docs/architecture/seo-ia.md`
- [ ] `apps/web/src/lib/seo.ts`
- [ ] `apps/web/src/pages/rankings/*` · `guides/*`
- [ ] `docs/revenue/adsense-placement-policy.md`

---

## Step 9 — Reviewer 검증

**모델:** Claude Opus
**스킬:** `superpowers:verification-before-completion` · `ecc:code-review`
**에이전트:** 단일

### 작업 목표
현재 브랜치의 구현을 **CLAUDE.md 규칙 · architecture-v2 · data contracts** 와 대조 검증. Trust Tag 누락 / 금지 소스 사용 / 런타임 계산 회귀 집중 검사.

### 프롬프트
```text
/model opus

@CLAUDE.md 와 @progress.md 와 @docs/architecture/architecture-v2.md 와 @docs/datasets/data-source-policy.md 읽어.

작업 원칙:
- Rule 7 준수: must / must-not 체크리스트 먼저 작성 후 검증.
- Rule 2 준수: grep/glob 병렬 호출로 코드베이스 스캔.
- Rule 4 준수: 신규 landmine 발견 시 guardrails.md 에 추가.

선행 작업:
1. 문서 기준의 must / must-not 체크리스트 생성:
   must: Trust Tag / citations / updatedAt / graceful status / normalized contract
   must-not: Render runtime / Open-Meteo prod / 런타임 PNG / raw 응답 노출

2. 변경 파일 범위로 검증 대상 좁히기 (git diff main..HEAD).

검증 항목 (핵심):
- [ ] Render 상시 런타임 의존 잔존 여부 (grep "onrender.com", "fastapi")
- [ ] Open-Meteo 프로덕션 핵심 경로 잔존 (grep "open-meteo")
- [ ] 모든 Report 가 정적 생성 전제 (getStaticPaths 사용 여부)
- [ ] 모든 dataset / report block 에 Trust Tag 존재
- [ ] schema 와 실제 payload 일치 (zod safeParse 로 fixtures 전수 검증)
- [ ] 홈 ↔ Globe 역할 분리 (Cesium 번들이 index 라우트에 없는지)
- [ ] 광고 슬롯이 레이아웃 깨지지 않음

산출물:
- docs/review/review-checklist.md (체크리스트 + pass/fail)
- 수정 필요 항목 목록
- 작은 수정 커밋 (필요 시)
- CLAUDE.md 업데이트 (보강 규칙 있으면)
- progress.md 업데이트 (release blocker + 남은 리스크)

수락 기준:
- pass / fail 이 항목별 명확
- 규칙 위반은 파일:라인 단위로 지적
- release blocker 가 progress.md 에 명시
```

### 산출물 체크
- [ ] `docs/review/review-checklist.md`
- [ ] 수정 커밋 (필요 시)
- [ ] `progress.md` release blocker 갱신

---

## Step 10 — QA / E2E / 회귀 점검

**모델:** Claude Sonnet (실패 원인 추적 필요 시 Opus 로 재실행)
**스킬:** `superpowers:executing-plans` · `superpowers:systematic-debugging` · `ecc:e2e`
**에이전트:** 단일

### 작업 목표
v2 MVP 핵심 경로를 테스트하고, 실패 시 **재현 가능한 형태** 로 기록.

### 프롬프트
```text
/model sonnet

@CLAUDE.md 와 @progress.md 와 @docs/review/review-checklist.md 읽어.

작업 원칙:
- Rule 6 준수: 테스트 결과를 progress.md 에 남기기.
- Rule 4 준수: 실패 케이스마다 재현 단계 + 원인 가설 + guardrails.md 등록.
- 실패 원인 추적이 막히면 systematic-debugging 스킬로 전환 후 Opus 재실행.

선행 작업:
1. MVP 핵심 사용자 경로 정의:
   home → globe → report → atlas
2. 우선순위 순서 고정.

테스트 범위:
- [ ] 홈 렌더링 (lighthouse score > 90)
- [ ] /globe 진입 + 6개 MVP 레이어 로드 확인
- [ ] /api/fires 응답 (Worker)
- [ ] /api/earthquakes 응답
- [ ] /api/sst-point 응답 (샘플 좌표)
- [ ] 샘플 report 3개 정적 렌더링
- [ ] atlas dataset 페이지 렌더링
- [ ] metadata / sitemap.xml / robots.txt
- [ ] broken links 0

산출물:
- test results summary (docs/review/qa-results-YYYY-MM-DD.md)
- 재현 단계 있는 bug list (있으면)
- Playwright/Vitest/Pytest 보강 (필요 시)
- CLAUDE.md 업데이트 (신규 규칙 있으면)
- progress.md 업데이트 (출시 가능 여부 + 잔여 버그)

수락 기준:
- MVP 핵심 경로 pass/fail 정리
- 실패는 반드시 재현 단계 + 원인 가설 포함
- progress.md 에 잔여 버그 + 출시 가능 여부
```

### 산출물 체크
- [ ] `docs/review/qa-results-*.md`
- [ ] Bug list (재현 단계 포함)
- [ ] `progress.md` 출시 가능 여부 판정

---

## 부록 A — 단계별 참조 파일 표

| Step | 읽어야 할 문서 | 핵심 출력 디렉토리 |
|------|---------------|---------------------|
| 1 | CLAUDE.md, progress.md, project-blueprint.md, globe-vision.md | `docs/architecture/` |
| 2 | Step 1 산출물 + api-spike-results.md | `docs/datasets/`, `data/fixtures/` |
| 3 | Step 1/2 산출물 | `apps/`, `packages/`, `pipelines/` |
| 4 | Step 2 산출물 + connectors.md | `pipelines/connectors/`, `apps/worker/src/` |
| 5 | Step 4 산출물 + report-spec.md | `pipelines/jobs/`, `data/reports/` |
| 6 | Step 2/4 산출물 | `apps/web/src/`, `packages/ui/` |
| 7 | Step 5 산출물 + data/reports/* | `apps/web/src/pages/reports/` |
| 8 | Step 3/6/7 산출물 | `apps/web/src/lib/`, `docs/revenue/` |
| 9 | 전체 산출물 | `docs/review/` |
| 10 | Step 9 산출물 | `docs/review/` |

---

## 부록 B — 데이터 계약 Quick Reference

```ts
// packages/schemas/core.ts
export type TrustTag =
  | 'observed' | 'near-real-time' | 'forecast' | 'derived' | 'compliance';

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

export interface EventPoint {
  id: string;
  type: 'fire' | 'earthquake';
  lat: number; lon: number;
  observedAt: string;
  severity?: number;
  label: string;
  properties: Record<string, string | number | boolean | null>;
}
```

---

## 부록 C — 모델 선택 플로우차트

```
작업이 아키텍처/계약/핵심 로직/디버깅/검증인가?
    ├─ YES → Opus
    └─ NO  → 반복/정리/확장인가?
              ├─ YES → Sonnet
              └─ NO  → Opus (기본값)
```

---

## 부록 D — Skills 매핑

| 스킬 | 언제 쓰나 |
|------|----------|
| `superpowers:writing-plans` | Step 1, 2, 8 — 아키텍처/계획 문서화 |
| `superpowers:brainstorming` | Step 1, 8 — 구조 선택지 탐색 |
| `superpowers:executing-plans` | Step 3, 5, 8 — 승인된 계획 실행 |
| `superpowers:dispatching-parallel-agents` | Step 2, 4 — 병렬 조사/구현 |
| `superpowers:subagent-driven-development` | Step 4, 6, 7 — 병렬 구현 |
| `superpowers:systematic-debugging` | Step 5, 10 — 원인 추적 |
| `superpowers:verification-before-completion` | Step 9 — 완료 직전 검증 |
| `ecc:frontend-design` | Step 6, 7 — 프런트 UI |
| `ecc:code-review` | Step 9 — 리뷰 |
| `ecc:e2e` | Step 10 — E2E |
| `claude-md-management:revise-claude-md` | 전 Step — CLAUDE.md 관리 |
| `ecc:seo` | Step 8 — SEO |

---

## 최종 운영 원칙 한 줄

> **TerraSight v2는 "무거운 실시간 분석 앱"이 아니라, "전지구 환경 관측 포털 + 정적 지역 리포트 + 신뢰도 중심 데이터 허브"로 운영한다.**
