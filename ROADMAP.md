# EarthPulse — Roadmap & Next Steps

## 현재 상태

- [x] 아이디어 도출 및 방향 확정
- [x] 경쟁 분석 완료 (nullschool, Worldview, Resource Watch, Windy, EPA/USGS/NOAA)
- [x] 3층 구조 확정 (Earth Now + Trends / Atlas / Local Reports)
- [x] 데이터셋 우선순위 P0/P1/P2 확정
- [x] 홈 와이어프레임 컴포넌트 명세 완료
- [x] Local Report 페이지 템플릿 6블록 명세 완료
- [x] 지리 단위·소스 분리·신뢰 태그 규칙 확정
- [x] CLAUDE.md 문서화 완료

---

## 다음 단계 (순서대로)

### Phase 1: 기반 설계 (코딩 전)

#### 1-1. Atlas 상세 IA
- 8개 카테고리별 데이터셋 목록 확정
- 각 데이터셋의 API endpoint, 인증 방식, 응답 포맷 조사
- 카테고리 상세 페이지 구조 설계
- 데이터셋 상세 페이지 구조 설계

#### 1-2. API 연결 가능성 검증 (Spike)
- P0 소스 7개의 실제 API 호출 테스트
  - NOAA GML (CO₂) — 인증 불필요, CSV/JSON
  - NSIDC (해빙) — 공개 FTP/HTTP
  - NOAA Climate at a Glance — REST API
  - NASA FIRMS — API key 필요, 무료
  - AirNow — API key 필요, 무료
  - EPA ECHO — REST, 인증 불필요
  - USGS modernized API — 인증 불필요
  - WQP beta API — 인증 불필요
  - NOAA OISST — NetCDF/OPeNDAP
  - OpenAQ — API v3, 인증 필요 (무료)
  - NASA GIBS — WMTS, 인증 불필요
  - CAMS — Copernicus CDS API, 계정 필요
- 각 API의 rate limit, 응답 속도, 데이터 포맷 기록
- 블로커 발견 시 대안 소스 확인

#### 1-3. CBSA 매핑 테이블 구축
- Census CBSA 목록 다운로드
- ZIP → CBSA 매핑 테이블 구축
- AirNow reporting area → CBSA 매핑 확인
- 초기 50개 metro 선정 (인구 상위 + 데이터 커버리지 확인)

### Phase 2: 백엔드 MVP

#### 2-1. 프로젝트 초기 세팅
- React + Vite 프런트엔드 프로젝트 생성
- FastAPI 백엔드 프로젝트 생성
- PostgreSQL + Redis 로컬 환경 구성
- CLAUDE.md를 프로젝트 루트에 배치
- progress.md 생성

#### 2-2. 데이터 수집 파이프라인 (P0 소스)
- 소스별 connector 모듈 개발
  - `connectors/noaa_gml.py` — CO₂
  - `connectors/nsidc.py` — 해빙
  - `connectors/noaa_ctag.py` — 기온 편차
  - `connectors/firms.py` — 산불
  - `connectors/airnow.py` — 현재 AQI
  - `connectors/echo.py` — 시설/위반
  - `connectors/usgs.py` — 수문 (modernized API)
  - `connectors/wqp.py` — 수질 (beta API)
  - `connectors/oisst.py` — SST
  - `connectors/openaq.py` — 글로벌 Air monitors
  - `connectors/gibs.py` — 위성 imagery
  - `connectors/cams.py` — 연기/대기조성
- 공통 정규화 레이어 (표준 JSON 스키마)
- 스케줄러 설정 (소스별 갱신 주기에 맞춰)
- 캐시 전략 (Redis: 빈번 갱신 / PostgreSQL: 장기 시계열)

#### 2-3. Local Report API
- `/api/reports/{cbsa_code}` 엔드포인트
- 7개 소스 병렬 호출 → 정규화 → 응답
- 캐시: 블록별 TTL 차등 (AirNow 1h, ECHO 24h, CtaG 30d 등)

### Phase 3: 프런트엔드 MVP

#### 3-1. 홈 페이지
- Header + Navigation
- Climate Trends strip (3 cards + sparkline)
- Earth Now globe (Cesium/Globe.gl + GIBS + FIRMS)
- Story panel (프리셋 1~2개로 시작)
- Atlas entry cards (8개, 정적)
- Local Reports teaser + ZIP 검색

#### 3-2. Local Report 페이지
- Block 0~6 컴포넌트 개발
- 차트 라이브러리 (Recharts or D3)
- 시설 지도 (Leaflet + ECHO 좌표)
- AdSense 배치 영역

#### 3-3. Atlas 페이지 (기본)
- 카테고리 목록 페이지
- 데이터셋 목록 + 태그 필터
- 데이터셋 상세 페이지 (메타데이터 + 외부 링크)

### Phase 4: SEO & 수익화

#### 4-1. 초기 50개 Metro 리포트 생성
- 데이터 자동 수집 + Context 블록 수동 작성
- Methodology 블록 통일 템플릿
- 각 페이지 고유 가치 검증

#### 4-2. 팩트 랭킹 페이지
- EPA violations 랭킹 (ECHO)
- PM2.5 metro 랭킹 (AirData/AQS)
- 각 랭킹에 출처·기준·연도 명시

#### 4-3. 교육 가이드
- "How to Read an AQI Report"
- "Understanding EPA Compliance Data"
- "What Your City's Water Quality Samples Mean"

#### 4-4. AdSense 신청 및 배치
- Google 정책 준수 확인
- 최소 50개 리포트 + 5개 가이드 확보 후 신청

### Phase 5: 고도화

- Born-in 인터랙티브 (OG image 생성 포함)
- 이벤트 해설 자동/반자동 생성 파이프라인
- Atlas 데이터셋 확장 (P1 → P2)
- 글로벌 Local Report 확장
- 성능 최적화 (CDN, SSR/SSG)

---

## Claude CLI 작업 가이드

### 파일 구조
```
project-root/
├── CLAUDE.md          ← 프로젝트 전체 기획 (이 파일을 항상 참조)
├── progress.md        ← 진행 상황 기록
├── frontend/          ← React + Vite
├── backend/           ← FastAPI
│   ├── connectors/    ← 소스별 데이터 커넥터
│   ├── api/           ← REST 엔드포인트
│   ├── models/        ← DB 모델
│   └── scheduler/     ← 자동 수집
└── docs/              ← 추가 설계 문서
```

### Claude CLI 사용 시 참고
- `CLAUDE.md`를 `@CLAUDE.md`로 참조하여 컨텍스트 유지
- 긴 프롬프트는 파일에 저장 후 `@filename.md`로 참조 (터미널 truncation 방지)
- `progress.md`에 완료된 작업, 블로커, 다음 할 일 기록
- ultraplan으로 Phase별 세부 계획 수립
- harness 기법으로 코드 품질 관리

### 즉시 시작 가능한 첫 작업
```
Phase 1-2: API 연결 가능성 검증
→ P0 소스 12개의 실제 API를 하나씩 호출해보고
   응답 포맷, 인증, rate limit, 데이터 구조를 정리
→ 결과를 docs/api-spike-results.md에 기록
```

이것이 전체 프로젝트에서 가장 리스크가 높은 부분이므로 코딩 전에 반드시 먼저 수행.

---

## 리스크 체크리스트

| 리스크 | 영향 | 대응 |
|--------|------|------|
| API rate limit 초과 | 데이터 갱신 실패 | 캐시 + 갱신 주기 조절 |
| NOAA/EPA API 불안정 | 리포트 빈 블록 | fallback 표시 + 재시도 로직 |
| USGS 구형 API 조기 폐기 | 수문 데이터 중단 | modernized API로 시작 (확정) |
| WQP beta API 변경 | 수질 데이터 중단 | API 버전 모니터링 |
| Google scaled content 판정 | AdSense 거절 | Context 블록 수동 작성 + 페이지당 고유 가치 |
| CAMS 계정 승인 지연 | Smoke 레이어 지연 | P0에서 Smoke 빼고 P1으로 이동 가능 |
| 지구본 성능 이슈 | 모바일 UX 저하 | 모바일은 2D 맵 fallback |
