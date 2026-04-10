# EarthPulse — 프로젝트 셋업 & Claude CLI 운영 가이드

---

## Part 1: Claude CLI 환경 셋업

### 1-1. 플러그인 설치 순서

CLI에서 순서대로 실행:

```bash
# 1. ECC (Everything Claude Code) 마켓플레이스 등록 + 설치
/plugin marketplace add https://github.com/affaan-m/everything-claude-code
/plugin
# → Discover 탭에서 ecc 선택 → User scope 설치

# 2. Harness 마켓플레이스 등록 + 설치
/plugin marketplace add revfactory/harness
/plugin
# → Discover 탭에서 harness 선택 → Project scope 설치

# 3. 리로드
/reload-plugins
```

### 1-2. ECC Rules 수동 설치 (플러그인으로 자동 배포 안 됨)

ECC README에 명시된 upstream limitation. rules는 별도 clone + copy 필요.

```
everything-claude-code 저장소를 클론하고,
common + typescript rules를 프로젝트의 .claude/rules에 설치해줘.
```

### 1-3. Agent Teams 활성화

기본 비활성화 상태. `.claude/settings.json`에 추가:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### 1-4. Ultraplan 연결

```bash
/web-setup          # GitHub 저장소 + 웹 계정 연동 (브라우저 인증 필요)
/ultraplan <prompt>  # 계획 수립 → 브라우저에서 검토/승인/실행
```

요구사항: Claude Code v2.1.91+, Claude Code on the web 계정, GitHub 저장소. Bedrock/Vertex/Foundry 불가.

---

## Part 2: 스킬 활용 계획

### 이 프로젝트에서 사용할 스킬

| 스킬 | 활용 시점 | 구체적 활용 |
|------|----------|------------|
| **writing-plans** | Phase별 계획 수립 | 각 Phase의 실행 계획서를 Step별 수락 기준 + 프롬프트로 구조화. CLAUDE.md 참조하며 작성 |
| **executing-plans** | Phase별 실행 | 계획서의 Step을 순차 실행, 수락 기준 통과 후 다음 Step 진행 |
| **dispatching-parallel-agents** | API spike 검증, 커넥터 개발 | P0 소스 12개 API 병렬 검증 (3~4개 에이전트), 커넥터 12개 병렬 개발 |
| **subagent-driven-development** | 커넥터·컴포넌트 개발 | 소스별 커넥터를 에이전트 분담 개발, 프런트 컴포넌트 분담 |
| **verification-before-completion** | 데이터 정합성 검증 | CLAUDE.md 규칙 ↔ 실제 구현 대조, API 응답 ↔ 화면 표시 일치 확인 |
| **brainstorming** | Story 프리셋 설계, UX 이터레이션 | 계절/이벤트 프리셋 목록 도출, 지구본 인터랙션 설계 |
| **systematic-debugging** | API 연동 버그 | rate limit, 인증 실패, 데이터 포맷 불일치 등 근본 원인 추적 |
| **claude-md-management** | 세션 간 컨텍스트 관리 | CLAUDE.md 진행 상태 업데이트, Phase 완료마다 수치 갱신 |

### 이전 프로젝트에서 미사용했으나 이번에 고려할 스킬

| 스킬 | 이번 프로젝트 활용 가능성 |
|------|--------------------------|
| **test-driven-development** | 커넥터별 응답 스키마 검증에 TDD 적용 가능. 각 커넥터의 expected output을 먼저 정의하고 구현 |
| **finishing-a-development-branch** | Phase별 브랜치 전략 사용 시 활용 (main 직접 커밋보다 안전) |
| **writing-skills** | 프로젝트 전용 커스텀 스킬 작성 가능 (예: connector-generator 스킬) |

### 사용하지 않을 스킬

| 스킬 | 이유 |
|------|------|
| receiving-code-review | 1인 개발, 외부 리뷰어 없음 |
| requesting-code-review | 동일 |
| using-git-worktrees | 프로젝트 규모상 불필요 |
| claude-md-improver | claude-md-management로 충분 |

---

## Part 3: 프로젝트 초기 셋업 절차

### 3-1. 저장소 생성 및 구조

```
earthpulse/
├── CLAUDE.md              ← 프로젝트 전체 기획 (V4 Final)
├── progress.md            ← 진행 상황 기록 (세션마다 업데이트)
├── .claude/
│   └── settings.json      ← agent teams 등 설정
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── components/
│   │   │   ├── header/
│   │   │   ├── climate-trends/    ← 3 cards strip
│   │   │   ├── earth-now/         ← globe + story panel
│   │   │   ├── born-in/           ← interactive comparison
│   │   │   ├── atlas/             ← 8 category cards + detail
│   │   │   ├── local-reports/     ← report page blocks 0-6
│   │   │   └── common/            ← badges, charts, maps
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── AtlasCategory.tsx
│   │   │   ├── AtlasDataset.tsx
│   │   │   ├── LocalReport.tsx
│   │   │   ├── Ranking.tsx
│   │   │   └── Guide.tsx
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── types/
│   └── public/
│
├── backend/
│   ├── requirements.txt
│   ├── main.py
│   ├── connectors/                ← 소스별 데이터 커넥터
│   │   ├── base.py                ← BaseConnector 추상 클래스
│   │   ├── noaa_gml.py            ← CO₂ (Mauna Loa)
│   │   ├── noaa_ctag.py           ← Climate at a Glance
│   │   ├── nsidc.py               ← Sea Ice Index
│   │   ├── firms.py               ← NASA FIRMS
│   │   ├── airnow.py              ← Current AQI (U.S.)
│   │   ├── openaq.py              ← Global air monitors
│   │   ├── oisst.py               ← SST daily
│   │   ├── cams.py                ← Smoke/atmosphere forecast
│   │   ├── gibs.py                ← Satellite imagery tiles
│   │   ├── airdata.py             ← EPA AirData/AQS annual
│   │   ├── echo.py                ← EPA facilities/compliance
│   │   ├── usgs.py                ← Hydrology (modernized API)
│   │   ├── wqp.py                 ← Water quality (beta API)
│   │   └── climate_normals.py     ← U.S. Climate Normals
│   ├── api/
│   │   ├── trends.py              ← /api/trends (CO₂, temp, ice)
│   │   ├── earth_now.py           ← /api/earth-now (layers)
│   │   ├── reports.py             ← /api/reports/{cbsa}
│   │   ├── atlas.py               ← /api/atlas/categories
│   │   └── rankings.py            ← /api/rankings
│   ├── models/
│   │   ├── database.py
│   │   ├── cbsa.py                ← CBSA 매핑 테이블
│   │   └── cache.py               ← Redis 캐시 관리
│   ├── scheduler/
│   │   └── jobs.py                ← 소스별 갱신 스케줄
│   └── tests/
│       ├── test_connectors/
│       └── test_api/
│
├── data/
│   ├── cbsa_mapping.csv           ← ZIP → CBSA 매핑
│   └── metro_list.json            ← 초기 50개 metro 목록
│
└── docs/
    ├── api-spike-results.md       ← Phase 1-2 결과
    ├── atlas-ia.md                ← Atlas 상세 IA
    └── context-blocks.md          ← metro별 Context 원고
```

### 3-2. 초기 셋업 CLI 시나리오

Claude CLI 세션에서 순서대로:

```
# Step 1: 저장소 생성
GitHub에서 earthpulse 저장소를 만들고 클론해줘.
React + Vite + TypeScript 프런트엔드와
FastAPI + Python 백엔드 프로젝트를 초기화해줘.

# Step 2: CLAUDE.md 배치
@CLAUDE.md 파일을 프로젝트 루트에 복사해줘.

# Step 3: progress.md 초기화
progress.md를 만들고 "Phase 1 시작" 상태로 초기화해줘.

# Step 4: 플러그인 설치
/plugin marketplace add https://github.com/affaan-m/everything-claude-code
/plugin marketplace add revfactory/harness
/reload-plugins

# Step 5: Agent Teams 활성화
.claude/settings.json에 CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 추가해줘.

# Step 6: ECC Rules 설치
everything-claude-code 저장소를 클론하고,
common rules를 .claude/rules에 설치해줘.

# Step 7: Ultraplan 연결
/web-setup
```

### 3-3. Phase 1 첫 작업: API Spike

셋업 완료 후 바로 실행:

```
/ultraplan
@CLAUDE.md 의 P0 데이터셋 12개 소스에 대해 API spike를 수행할 계획을 세워줘.
각 소스별로: endpoint URL, 인증 방식, 호출 예시, 응답 포맷, rate limit, 블로커 여부를 확인.
dispatching-parallel-agents로 3~4개 에이전트가 병렬로 검증.
결과는 docs/api-spike-results.md에 기록.
```

**에이전트 분배 예시:**

| 에이전트 | 담당 소스 |
|----------|-----------|
| Agent 1 (대기) | NOAA GML, AirNow, OpenAQ, CAMS |
| Agent 2 (해양/기후) | NSIDC, NOAA CtaG, OISST, Climate Normals |
| Agent 3 (수문/수질) | USGS modernized, WQP beta |
| Agent 4 (시설/위성) | EPA ECHO, AirData, NASA FIRMS, GIBS |

---

## Part 4: 세션 간 컨텍스트 관리 규칙

### CLAUDE.md (읽기 전용 참조)
- 프로젝트 전체 기획, 확정 규칙, 데이터셋 목록, 와이어프레임
- 변경 시 명시적 버전 업데이트 (V4 → V5)
- 모든 세션 시작 시 `@CLAUDE.md` 참조

### progress.md (매 세션 업데이트)
- 현재 Phase, 완료된 Step, 다음 할 일
- 블로커 및 미해결 이슈
- 데이터 수치 (커넥터 수, 테스트 통과율, 리포트 수 등)

### 세션 시작 프롬프트 템플릿

```
@CLAUDE.md 와 @progress.md 를 읽고,
현재 진행 상황을 파악한 뒤 다음 작업을 이어해줘.
```

### Phase 완료 시 체크리스트

```
1. verification-before-completion으로 CLAUDE.md 규칙 ↔ 구현 대조
2. progress.md 수치 갱신
3. 블로커/이슈 기록
4. 다음 Phase 계획 확인
```

---

## Part 5: Phase별 스킬 매핑

| Phase | 주요 스킬 | 에이전트 구조 |
|-------|----------|---------------|
| **1. 기반 설계** | writing-plans, brainstorming | 단일 |
| **1-2. API Spike** | dispatching-parallel-agents | 3~4 에이전트 병렬 |
| **2-1. 프로젝트 세팅** | executing-plans | 단일 순차 |
| **2-2. 커넥터 개발** | subagent-driven-development, dispatching-parallel-agents | 3~4 에이전트 병렬 |
| **2-3. Report API** | executing-plans, systematic-debugging | 단일 순차 |
| **3-1. 홈 프런트** | subagent-driven-development | 2~3 에이전트 (globe/cards/story) |
| **3-2. Report 프런트** | subagent-driven-development | 2~3 에이전트 (blocks) |
| **4. SEO/수익화** | writing-plans, brainstorming | 단일 |
| **전 Phase** | claude-md-management, verification-before-completion | 매 세션 |

---

## Part 6: Harness Agent Teams 구조 (제안)

Ultraplan 첫 실행 시 아래 구조를 제안:

```
/ultraplan
이 저장소에 맞는 harness-engineering 운영안을 설계해줘.

Agent Teams 구조:
- architect: CLAUDE.md 기반 설계 검증, API 스키마 정의, 컴포넌트 인터페이스 설계
- implementer: 커넥터·API·컴포넌트 구현
- reviewer: CLAUDE.md 규칙 ↔ 코드 대조, 신뢰 태그·면책 문구 누락 검사
- qa: 커넥터 응답 검증, E2E 테스트, 데이터 정합성 확인

ECC는 user-level 기반 레이어로 두고,
Harness는 project-level agent/skill 생성기로 쓰고,
architect / implementer / reviewer / qa 팀 구조로 운영.
```

### 이 프로젝트 특화 검증 포인트

reviewer/qa가 반드시 확인해야 할 항목 (CLAUDE.md 가드레일 기반):

| # | 검증 항목 | 위반 시 영향 |
|---|----------|-------------|
| 1 | 모든 데이터 표시에 신뢰 태그(5단계) 있는가 | 서비스 신뢰도 붕괴 |
| 2 | Current vs Trend 소스 분리 되어 있는가 | 데이터 정확성 훼손 |
| 3 | 지리 단위(CBSA/reporting area/city) 명시되어 있는가 | 사용자 오해 유발 |
| 4 | ECHO 면책 문구 표시되어 있는가 | "위험한 도시" 오독 |
| 5 | WQP "discrete samples" 명시되어 있는가 | 실시간 수질로 오해 |
| 6 | CAMS에 forecast/model 뱃지 있는가 | observed와 혼동 |
| 7 | 홈에서 "AQI" 대신 "Air monitors" 쓰고 있는가 | 글로벌/미국 혼동 |
| 8 | USGS modernized API 사용하고 있는가 (구형 아닌지) | 2027 decommission 리스크 |

---

## 즉시 실행 체크리스트

```
[ ] GitHub 저장소 생성 (earthpulse)
[ ] React + Vite + TypeScript 초기화
[ ] FastAPI 프로젝트 초기화
[ ] CLAUDE.md 루트에 배치
[ ] progress.md 생성
[ ] ECC 플러그인 설치 (User scope)
[ ] Harness 플러그인 설치 (Project scope)
[ ] ECC rules 수동 복사
[ ] Agent Teams 활성화 (.claude/settings.json)
[ ] /web-setup 실행
[ ] /ultraplan으로 Phase 1-2 API Spike 계획 수립
[ ] API Spike 실행 (3~4 에이전트 병렬)
[ ] docs/api-spike-results.md 작성
```
