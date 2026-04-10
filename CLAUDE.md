# EarthPulse — Project Specification (V4 Final)

## 한 줄 정의

기후변화 시각화로 후킹하고, 환경공학 데이터 아틀라스로 체류시키며, 지역별 환경 리포트로 광고 수익을 만드는 영문 환경 포털

> A visual-first environmental engineering platform: Live climate signals on the front, Environmental Data Atlas inside, Local Environmental Reports for revenue.

---

## 서비스 정체성

- **언어:** English-first
- **타겟:** 환경공학 전공자/학생 + 기후변화에 관심 있는 일반 대중 + 미국 지역 환경정보 검색자
- **포지션:** Portal + Observatory + Atlas의 중간. 단순 지구본도 아니고, 데이터 카탈로그도 아닌, "보게 만들고 → 찾게 만들고 → 검색 유입시키는" 3층 퍼널
- **수익 모델:** AdSense (주) + 교육/도구형 부수익 (보조). 광고 단독은 약하므로 Local Reports의 SEO 롱테일이 핵심 트래픽 엔진

---

## 3층 구조

### 1층: Earth Now + Climate Trends (후킹)

방문 즉시 "지구가 변하고 있다"를 느끼게 하는 메인 페이지.

**Climate Trends (느린 변화 카드 3개):**

| 카드 | 소스 | 갱신 | 태그 | 데이터 시작 |
|------|------|------|------|-------------|
| CO₂ 농도 | NOAA GML Mauna Loa | daily + monthly | observed | 1958 |
| 글로벌 기온 편차 | NOAA Climate at a Glance | monthly | NRT/preliminary | 1880 |
| 북극 해빙 면적 | NSIDC Sea Ice Index | daily (5-day running mean) | observed | 1979 |

- 각 카드에 값 + sparkline + 갱신주기 + 신뢰태그 + 출처 기관명 표시
- 메타정보(Daily, Monthly, Preliminary 등)가 숫자보다 먼저 보여야 함

**Earth Now (지구본 + 빠른 현재 레이어):**

| 레이어 | 소스 | 갱신 | 태그 | 뱃지 |
|--------|------|------|------|------|
| Fires | NASA FIRMS | NRT (~3h) | observed | 🟢 |
| Ocean Heat | NOAA OISST | daily | observed | 🟢 |
| Smoke | CAMS | 6-12h | forecast/model | 🟠 |
| Air monitors | OpenAQ | varies | observed (집계) | 🟡 |

- **지구본 렌더링:** Cesium 또는 Globe.gl
- **베이스 레이어:** NASA GIBS Natural Earth imagery
- **기본 on:** Natural Earth + Fires
- **레이어 규칙:** 연속 필드 1개 + 이벤트 오버레이 1개만 동시 활성화
- **각 레이어 옆 뱃지:** observed / NRT / forecast 컬러 구분
- **홈 Air 표기:** "Air monitors" (글로벌). "AQI"는 Local Reports에서만 사용

**이달의 기후 이야기 (Story Panel):**
- P0 (핵심 기능)
- 계절/이벤트 프리셋 기반 (산불 시즌, 허리케인, 폭염, 홍수, 해빙 최소)
- 초기 프리셋 5~10개 사전 준비
- "Explore on Globe" → 해당 레이어+위치 자동 활성화
- "Read Local Report →" → 해당 지역 리포트 연결

**Born-in Interactive:**
- P1 (바이럴 핵심이지만 코어 기능은 아님)
- 출생 연도 입력 → CO₂, 기온, 해빙 then vs now 비교
- 데이터 시작점 자동 보정: CO₂ 1958 이전 → "1958 (record start)", 해빙 1979 이전 → "1979 (record start)"
- OG image 자동 생성 → SNS 공유

### 2층: Environmental Data Atlas (깊이)

환경공학 전공 기준 8개 카테고리. 변경 없음.

| # | 카테고리 | 주요 데이터셋 |
|---|----------|---------------|
| 1 | Air & Atmosphere | AirNow, EPA AQS, OpenAQ, CAMS, GEMS |
| 2 | Water Quality, Drinking Water & Wastewater | Water Quality Portal, SDWIS |
| 3 | Hydrology & Floods | USGS Water Data, flood forecasts |
| 4 | Coast & Ocean | NOAA CO-OPS, NDBC, GHRSST, Ocean Color, HABSOS |
| 5 | Soil, Land & Site Condition | SoilGrids, land cover |
| 6 | Waste & Materials | hazardous waste, TRI |
| 7 | Emissions, Energy & Facilities | EPA Envirofacts, FRS, ECHO, Climate TRACE |
| 8 | Climate, Hazards & Exposure | wildfire, storms, drought, sea level rise |

**각 데이터셋 필수 표시:**
- observed / near-real-time / forecast / derived / estimated 태그
- 출처, 갱신주기, 공간 범위, 라이선스
- 데이터 한계 및 품질 노트

### 3층: Local Environmental Reports (수익 엔진)

**기본 설정:**
- U.S.-first
- 기본 지리 단위: Metro/CBSA (Climate 블록만 city 예외 허용)
- 초기 규모: 50~100개 주요 metro
- 각 블록에 실제 사용 지리 단위 명시

**URL 구조:** `/reports/{cbsa-slug}`

**6블록 구성:**

#### Block 0: Metro Header
- CBSA 공식 명칭, 인구(Census ACS), 기후대(Köppen), 최종 갱신일
- Key signal 미니카드 4개 (AQI, Temp trend, EPA facilities, Water status)

#### Block 1: Air Quality
- **Current:** AirNow → reporting area 기반 현재 AQI (hourly, observed)
- **Annual Trend:** EPA AirData/AQS → county/CBSA 기준 연간 PM2.5, Ozone (annual, observed)
- **Context:** 2~3문장 지역 해석 (수동 작성 or AI+검수)
- ⚠️ reporting area ≠ city 경계임을 명시

#### Block 2: Climate Change Locally
- NOAA Climate at a Glance city time series (monthly, observed)
- U.S. Climate Normals 1991-2020 baseline (30-yr, reference)
- 기온 30년 차트 + 강수 30년 차트 + 온난화율 계산
- Context: 지역 고유 기후 특성 해석

#### Block 3: Regulated Facilities & Compliance
- EPA ECHO (좌표 기반 → CBSA 집계, live feed, regulatory)
- 시설 수, 현재 위반, 집행 조치, 벌금 요약
- 위반 시설 테이블 + CBSA 경계 내 시설 지도
- ⚠️ 필수 면책: "regulatory compliance ≠ environmental exposure or health risk"

#### Block 4: Water Snapshot
- **Hydrology (NRT):** USGS modernized API (15-min, observed)
  - streamflow, stage → "Near-real-time (15-minute interval)"
- **Water Quality (discrete):** WQP beta API + USGS modernized (varies, observed)
  - → "Discrete samples — dates vary"
- ⚠️ USGS continuous vs WQP discrete 구분 반드시 화면에 명시
- ⚠️ WQP 백엔드: UI export 의존 금지, beta API + USGS modernized 직접 호출

#### Block 5: Methodology & Data Limitations
- 지리 단위 설명 (CBSA vs reporting area vs city)
- 소스별 갱신주기·신뢰태그 표
- Known limitations 목록
- "교육·탐색 용도이며 공식 환경 평가 대체 불가" 면책

#### Block 6: Related Content
- 해당 metro의 랭킹 순위 링크
- 교육 가이드 링크
- 인근 metro 리포트 링크
- → 체류 시간 + 내부 링크 + 추가 페이지뷰

**AdSense 배치:**
- Block 1-2 사이, Block 3-4 사이, Block 6 내부/아래
- 블록 내부 삽입 금지, 데이터 테이블·차트와 시각적 분리
- 모바일 블록당 최대 1개

**SEO 콘텐츠 (병행):**
- 팩트 랭킹: EPA violations → ECHO, PM2.5 → AirData/AQS (각 출처·기준 명시)
- 교육 가이드: "How to Read an AQI Report", "What Your Water Quality Samples Mean"
- 이벤트 해설: 산불/홍수/오염 사고 발생 시 반자동 생성

---

## 확정 규칙

### 지리 단위
- 기본: Metro/CBSA
- Climate 블록만 city 허용 (NOAA CtaG가 city time series 제공)
- 각 블록에 실제 사용 단위 명시

### 소스 분리 (Current vs Trend)
- Air: Current = AirNow (reporting area) / Trend·Ranking = AirData·AQS (county/CBSA)
- Water: Hydrology = USGS continuous (NRT) / Quality = WQP discrete (시차 있음)

### 신뢰 태그 (5단계 뱃지)
| 태그 | 색상 | 의미 |
|------|------|------|
| observed | 🟢 | 기기 직접 측정 |
| near-real-time | 🟡 | 수시간 내 처리 |
| forecast/model | 🟠 | CAMS, GFS 등 |
| derived | 🔵 | 관측값에서 계산 |
| estimated | ⚪ | 통계/ML 추론 |

### WQP 백엔드
- WQP 기본 UI는 WQX 2.2만 제공, 2024-03-11 이후 USGS 데이터 미포함
- WQP beta API + USGS modernized endpoints 직접 호출

### USGS API
- modernized Water Data APIs 사용 (구형 WaterServices 2027 Q1 decommission 예정)

---

## 데이터셋 우선순위

### P0 — 뼈대

**Earth Now:**
| 소스 | 용도 | 갱신 | 태그 |
|------|------|------|------|
| NASA GIBS/Worldview | 베이스 imagery | varies | observed/NRT |
| NASA FIRMS | 산불/열 이상 | NRT ~3h | observed |
| AirNow | 현재 AQI (리포트용) | hourly | observed |
| OpenAQ | 글로벌 Air monitors (홈 지구본) | varies | observed |
| NOAA OISST | 일별 SST | daily | observed |
| CAMS | 연기/대기조성 | 6-12h | forecast/model |

**Climate Trends:**
| 소스 | 용도 | 갱신 | 태그 |
|------|------|------|------|
| NOAA GML Mauna Loa | CO₂ | daily+monthly | observed |
| NOAA Climate at a Glance | 기온 편차 | monthly | NRT/preliminary |
| NSIDC Sea Ice Index | 해빙 면적 | daily (5d mean) | observed |

**Local Reports:**
| 소스 | 용도 | 갱신 | 태그 |
|------|------|------|------|
| AirNow | 현재 AQI | hourly | observed |
| EPA AirData/AQS | 연간 AQI·PM2.5 | annual | observed |
| NOAA Climate at a Glance | 도시 기온·강수 시계열 | monthly | observed |
| U.S. Climate Normals | 1991-2020 기준선 | 30-yr | reference |
| EPA ECHO | 시설/위반/집행 | live feed | regulatory |
| USGS modernized API | 수문 연속관측 | 15-min | observed |
| WQP beta API | 수질 이산 샘플 | discrete | observed |

**이달의 기후 이야기:** 프리셋 5-10개, 월간/이벤트, editorial

### P1 — 차별화
- Worldview 추가 imagery 레이어
- ECHO 팩트 랭킹 (EPA violations)
- AirData PM2.5 연간 랭킹
- Born-in 인터랙티브 완성
- 교육 가이드 시리즈

### P2 — 확장
- Soil/Land (SoilGrids)
- Waste & Materials
- Climate TRACE 배출 시설 지도
- 글로벌 Local Report 확장
- 자체 종합 환경지수

---

## 기존 서비스 대비 차별점

| 기존 서비스 | 그들의 강점 | 우리의 차별점 |
|-------------|-------------|---------------|
| earth.nullschool.net | 10년+ 운영, 수백만 방문, 아름다운 시각화 | 기상/대기만. 수질·토양·시설·규제·compliance 없음 |
| NASA Worldview | 1,200+ 레이어, 압도적 데이터 깊이 | 전문가 도구. 교육용 큐레이션·지역 리포트 없음 |
| Resource Watch (WRI) | 300+ 데이터셋, 정책 프레임 | 정책/의사결정자 대상. 환경공학 전공 분류 아님 |
| Windy.com | 대중적 UI, 큰 사용자 기반 | 기상 예보 전문. 환경공학 범위 밖 |
| EPA/USGS/NOAA 개별 포털 | 각 도메인 최고 품질 | 완전 분산. 크로스도메인 연결 없음 |

**핵심 차별화:**
1. 환경공학 전공 기준 8개 카테고리 분류 (기존 어디에도 없음)
2. observed/forecast/estimated 구분 표시 (대부분 안 함)
3. EPA 규제/시설 데이터 + 환경 관측 데이터 연결
4. 기후 시각화(후킹) → 아틀라스(깊이) → 지역 리포트(수익) 퍼널

---

## 홈 와이어프레임

```
┌──────────────────────────────────────────────────────────┐
│ Header: Logo | Earth Now | Climate Trends | Atlas |      │
│         Local Reports | Guides | Rankings | Search       │
├──────────────────────────────────────────────────────────┤
│ Climate Trends strip (3 cards)                           │
│ [CO₂ · Daily · Observed] [Temp · Monthly · Prelim]      │
│ [Sea Ice · Daily(5d) · Observed]                         │
├──────────────────────────────────────────────────────────┤
│ Hero: Earth Now Globe + This Month's Climate Story       │
│ globe: Natural Earth + Fires (default)                   │
│ toggles: Fires | Ocean Heat | Smoke | Air monitors       │
│ badges: 🟢observed 🟡NRT 🟠forecast                      │
├──────────────────────────────────────────────────────────┤
│ Born in [year]? See how Earth changed                    │
├──────────────────────────────────────────────────────────┤
│ Explore the Atlas (8 category cards)                     │
├──────────────────────────────────────────────────────────┤
│ Local Environmental Reports                              │
│ [Top metros] [Fact rankings] [Guides] [ZIP search]      │
├──────────────────────────────────────────────────────────┤
│ Methods / Sources / Data Status legend                   │
└──────────────────────────────────────────────────────────┘
```

---

## 기술 스택 (계획)

- **Frontend:** React (Vite)
- **Backend:** FastAPI (Python)
- **Globe:** Cesium or Globe.gl
- **Maps (Local Reports):** Mapbox or Leaflet
- **DB/Cache:** PostgreSQL + Redis
- **Scheduler:** cron or APScheduler (데이터 자동 수집)
- **Deploy:** TBD
- **Development:** VS Code + Claude CLI (ultraplan, harness, skills)

---

## 가드레일 (절대 규칙)

1. "Live" 남용 금지 — Now/Trends 분리, 갱신 단위 반드시 명시
2. U.S.-first — 지역 리포트는 미국부터, Atlas는 글로벌
3. 해석 있는 리포트 — 템플릿 자동 생성이 아닌 고유 가치 페이지
4. 환경 점수 금지 — "score"가 아닌 "report". transparent screening만 허용
5. 소스 분리 — 같은 주제라도 Current vs Trend는 다른 소스
6. 면책 표시 — ECHO는 compliance 데이터, WQP는 discrete sample임을 항상 명시
7. Google 정책 준수 — scaled content abuse 회피, people-first content
