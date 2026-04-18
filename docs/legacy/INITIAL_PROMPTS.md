# Terrasight — Claude CLI 초기 세팅 프롬프트

아래 프롬프트들을 Claude CLI에서 순서대로 실행합니다.
각 단계 완료 확인 후 다음 단계로 진행하세요.

---

## STEP 1: 프로젝트 초기화

```
다음 프로젝트를 초기화해줘.

프로젝트명: Terrasight
설명: 기후변화 시각화 + 환경공학 데이터 아틀라스 + 지역 환경 리포트 영문 포털

구조:
- frontend: React + Vite + TypeScript
- backend: FastAPI + Python 3.12
- DB: PostgreSQL + Redis (설정 파일만, 로컬 설치는 별도)

디렉토리 구조를 아래와 같이 생성해줘:

terrasight/
├── CLAUDE.md
├── progress.md
├── .gitignore
├── .claude/
│   └── settings.json
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── header/
│   │   │   │   └── Header.tsx
│   │   │   ├── climate-trends/
│   │   │   │   └── TrendsStrip.tsx
│   │   │   ├── earth-now/
│   │   │   │   ├── Globe.tsx
│   │   │   │   └── StoryPanel.tsx
│   │   │   ├── born-in/
│   │   │   │   └── BornIn.tsx
│   │   │   ├── atlas/
│   │   │   │   └── AtlasGrid.tsx
│   │   │   ├── local-reports/
│   │   │   │   ├── ReportPage.tsx
│   │   │   │   ├── AirBlock.tsx
│   │   │   │   ├── ClimateBlock.tsx
│   │   │   │   ├── FacilitiesBlock.tsx
│   │   │   │   ├── WaterBlock.tsx
│   │   │   │   ├── MethodologyBlock.tsx
│   │   │   │   └── RelatedBlock.tsx
│   │   │   └── common/
│   │   │       ├── TrustBadge.tsx
│   │   │       ├── SourceLabel.tsx
│   │   │       └── MetaLine.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── AtlasCategory.tsx
│   │   │   ├── AtlasDataset.tsx
│   │   │   ├── LocalReport.tsx
│   │   │   ├── Ranking.tsx
│   │   │   └── Guide.tsx
│   │   ├── hooks/
│   │   │   └── useApi.ts
│   │   ├── utils/
│   │   │   └── trustTags.ts
│   │   └── types/
│   │       ├── trends.ts
│   │       ├── earthNow.ts
│   │       ├── report.ts
│   │       └── atlas.ts
│   └── public/
│       └── favicon.svg
│
├── backend/
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── noaa_gml.py
│   │   ├── noaa_ctag.py
│   │   ├── nsidc.py
│   │   ├── firms.py
│   │   ├── airnow.py
│   │   ├── openaq.py
│   │   ├── oisst.py
│   │   ├── cams.py
│   │   ├── gibs.py
│   │   ├── airdata.py
│   │   ├── echo.py
│   │   ├── usgs.py
│   │   ├── wqp.py
│   │   └── climate_normals.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── trends.py
│   │   ├── earth_now.py
│   │   ├── reports.py
│   │   ├── atlas.py
│   │   └── rankings.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── cbsa.py
│   │   └── cache.py
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── jobs.py
│   └── tests/
│       ├── __init__.py
│       ├── test_connectors/
│       │   └── __init__.py
│       └── test_api/
│           └── __init__.py
│
├── data/
│   └── .gitkeep
│
└── docs/
    ├── api-spike-results.md
    └── .gitkeep

frontend 패키지 의존성:
- react, react-dom, react-router-dom
- @types/react, @types/react-dom
- typescript
- tailwindcss (v4)
- recharts (차트)
- lucide-react (아이콘)
- axios

backend 의존성 (requirements.txt):
- fastapi
- uvicorn[standard]
- httpx
- pydantic
- python-dotenv
- apscheduler
- redis
- asyncpg
- sqlalchemy[asyncio]

.gitignore에 포함:
node_modules, __pycache__, .env, .venv, *.pyc, dist, build, .DS_Store

각 파일은 빈 boilerplate로 생성하되:
- main.py: FastAPI app 기본 구조 (CORS 설정 포함, frontend localhost:5173 허용)
- App.tsx: react-router-dom 기본 라우팅 (Home, LocalReport, AtlasCategory, Ranking, Guide)
- base.py (connectors): BaseConnector 추상 클래스 (fetch, normalize, cache 메서드)
- TrustBadge.tsx: observed/NRT/forecast/derived/estimated 5단계 뱃지 컴포넌트
- trustTags.ts: 5단계 태그 enum + 색상 매핑
```

---

## STEP 2: CLAUDE.md 배치

```
@CLAUDE.md 파일 내용을 프로젝트 루트의 CLAUDE.md에 복사해줘.
```

(사전에 다운로드한 CLAUDE.md 파일을 프로젝트 폴더에 넣어두거나, 내용을 직접 붙여넣기)

---

## STEP 3: progress.md 초기화

```
progress.md를 아래 내용으로 생성해줘:

# Terrasight — Progress

## 현재 상태
- Phase: 1 (기반 설계)
- Step: 1-1 (프로젝트 초기화)
- 날짜: 2026-04-10

## 완료
- [x] 아이디어 확정 (V4 Final)
- [x] CLAUDE.md 문서화
- [x] ROADMAP.md 작성
- [x] PROJECT_SETUP.md 작성
- [x] 프로젝트 초기화 (디렉토리 + boilerplate)

## 진행 중
- [ ] Phase 1-2: API Spike (P0 소스 12개 검증)

## 다음 할 일
- Phase 1-2: API Spike 실행
- Phase 1-3: CBSA 매핑 테이블 구축

## 수치
- 커넥터: 14개 스켈레톤 생성 / 0개 구현 완료
- 프런트 컴포넌트: 스켈레톤 생성 / 0개 구현 완료
- Local Reports: 0 / 50 목표
- 테스트: 0개

## 블로커
- 없음

## 메모
- USGS modernized API 사용 (구형 WaterServices 2027 Q1 decommission)
- WQP beta API + USGS modernized 직접 호출 (UI export 의존 금지)
- 홈 Air 표기: "Air monitors" (AQI는 Local Reports에서만)
```

---

## STEP 4: .claude/settings.json 설정

```
.claude/settings.json을 아래 내용으로 생성해줘:

{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "permissions": {
    "allow": [
      "Read",
      "Edit",
      "Bash(npm *)",
      "Bash(pip *)",
      "Bash(python *)",
      "Bash(npx *)",
      "Bash(git *)",
      "Bash(curl *)",
      "Bash(cat *)",
      "Bash(mkdir *)",
      "Bash(cp *)",
      "Bash(ls *)"
    ]
  }
}
```

---

## STEP 5: 플러그인 설치

```
/plugin marketplace add https://github.com/affaan-m/everything-claude-code
/plugin
```
→ Discover 탭에서 ecc 선택 → User scope 설치

```
/plugin marketplace add revfactory/harness
/plugin
```
→ Discover 탭에서 harness 선택 → Project scope 설치

```
/reload-plugins
```

---

## STEP 6: ECC Rules 설치

```
everything-claude-code 저장소를 클론해서 /tmp/ecc에 넣고,
common rules를 이 프로젝트의 .claude/rules 디렉토리에 복사해줘.
클론한 임시 디렉토리는 삭제해줘.
```

---

## STEP 7: Ultraplan 연결

```
/web-setup
```
→ 브라우저에서 GitHub 인증 완료

---

## STEP 8: Git 초기 커밋

```
git init
git add .
git commit -m "chore: project scaffold — Terrasight V4 Final

- React + Vite + TypeScript frontend
- FastAPI backend with 14 connector skeletons
- CLAUDE.md (V4 Final project spec)
- progress.md initialized
- TrustBadge component (5-level data trust system)
- BaseConnector abstract class
- Directory structure per CLAUDE.md spec"
```

---

## STEP 9: API Spike 계획 수립

```
/ultraplan

@CLAUDE.md 를 참조해서 Phase 1-2 API Spike 계획을 세워줘.

목표: P0 데이터 소스 14개의 실제 API 호출 가능성 검증

각 소스별 확인 항목:
1. API endpoint URL (정확한 최신 URL)
2. 인증 방식 (API key / OAuth / 없음)
3. 실제 호출 예시 (curl or httpx)
4. 응답 포맷 (JSON / CSV / NetCDF / GeoJSON)
5. Rate limit (시간당 / 일당)
6. 데이터 갱신 주기 (실제 확인)
7. 블로커 여부 (접근 불가, 유료, 승인 대기 등)
8. 대안 소스 (블로커 시)

에이전트 분배:
- Agent 1 (대기): NOAA GML, AirNow, OpenAQ, CAMS
- Agent 2 (해양/기후): NSIDC, NOAA CtaG, OISST, Climate Normals
- Agent 3 (수문/수질): USGS modernized, WQP beta
- Agent 4 (시설/위성): EPA ECHO, AirData, NASA FIRMS, GIBS

dispatching-parallel-agents 스킬을 사용해서 4개 에이전트 병렬 실행.
각 에이전트는 담당 소스를 실제로 호출하고 결과를 기록.
전체 결과를 docs/api-spike-results.md에 아래 포맷으로 통합:

## {소스명}
- Endpoint: 
- Auth: 
- Sample call: 
- Response format: 
- Rate limit: 
- Update frequency: 
- Status: ✅ GO / ⚠️ 주의사항 있음 / ❌ 블로커
- Notes: 
- Fallback: 

완료 후 progress.md를 업데이트해줘.
```

---

## STEP 10: Spike 완료 후 다음 작업

```
@CLAUDE.md 와 @progress.md 를 읽고,
API Spike 결과를 기반으로 Phase 2 계획을 세워줘.

writing-plans 스킬을 사용해서:
1. 블로커가 발견된 소스의 대안 확정
2. 커넥터 개발 우선순위 재조정
3. Phase 2-2 커넥터 개발 실행 계획서 작성
   - Step별 수락 기준
   - 에이전트 분배안
   - 테스트 기준 (각 커넥터별 expected output 스키마)

결과를 docs/phase2-plan.md에 저장하고
progress.md를 업데이트해줘.
```

---

## 매 세션 시작 프롬프트 (반복 사용)

```
@CLAUDE.md 와 @progress.md 를 읽고,
현재 진행 상황을 파악한 뒤 다음 작업을 이어해줘.
```

## Phase 완료 시 검증 프롬프트 (반복 사용)

```
verification-before-completion 스킬을 사용해서:

1. @CLAUDE.md 의 가드레일 7개를 하나씩 대조
2. 현재 구현된 코드에서 위반 사항 확인
3. 특히 다음 항목 중점 검사:
   - 모든 데이터 표시에 신뢰 태그(5단계) 있는가
   - Current vs Trend 소스 분리 되어 있는가
   - 지리 단위 명시되어 있는가
   - ECHO 면책 문구 있는가
   - WQP "discrete samples" 명시되어 있는가
   - CAMS에 forecast/model 뱃지 있는가
   - 홈에서 "AQI" 대신 "Air monitors" 쓰고 있는가
   - USGS modernized API 사용하고 있는가
4. 위반 0건이면 PASS, 아니면 수정 후 재검증
5. progress.md 수치 갱신
```
