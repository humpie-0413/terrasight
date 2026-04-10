# EarthPulse / TerraSight — Progress Log

## 1차 MVP 완료 (2026-04-11)

### 라이브 URL
| 서비스 | URL |
|--------|-----|
| Frontend (CF Pages) | https://terrasight.pages.dev |
| Backend (Render) | https://terrasight-api-o959.onrender.com |
| GitHub | https://github.com/humpie-0413/terrasight |

### 핵심 수치
| 항목 | 수치 |
|------|------|
| Git commits | 21 |
| Backend connectors | 14 구현 (12 live, 2 stub) |
| API endpoints | 16개 |
| Frontend components / pages | ~25개 |
| Local Reports metros | 10 / 50 목표 |
| Bundle size | 591 KB gzipped (< 600 KB 가드레일) |
| 배포 스택 | Cloudflare Pages + Render (Docker) |

---

## 완료 항목 요약

### Phase 0 — Scaffold (`a95ea56`)
- React + Vite + TypeScript 프런트 skeleton (15 컴포넌트, 5 페이지, hooks/utils/types)
- FastAPI 백엔드 skeleton (14 커넥터 stub, 5 API 라우터)
- 프로젝트 구조: `frontend/`, `backend/`, `data/`, `docs/`

### Phase 1 — API Spike (`7414e6b`, `ad3175b`)
14개 P0 소스 검증. 최종 결과: **9 GO / 5 주의 / 0 블로커**

| 소스 | 결과 | 주요 사항 |
|------|------|-----------|
| NOAA GML CO₂ | ✅ | 직접 파일 다운로드, 인증 불필요 |
| NOAAGlobalTemp CDR | ✅ | CtaG 대체 (공개 REST API 없음) |
| NSIDC Sea Ice | ✅ | CSV, noaadata.apps.nsidc.org |
| NOAA OISST | ✅ | ERDDAP griddap (CoastWatch) |
| U.S. Climate Normals | ✅ | NCEI 1991-2020 per-station CSV |
| AirNow | ✅ | 무료 키, 500 req/hr |
| OpenAQ v3 | ✅ | v1/v2 은퇴 2025-01-31; v3 키 필요 |
| NASA FIRMS | ✅ | 무료 MAP_KEY, 5,000 트랜잭션/10분 |
| NASA GIBS | ✅ | 공개 WMTS, 인증 불필요 |
| EPA ECHO | ✅ | echodata.epa.gov (ofmpub 차단됨) |
| USGS modernized | ✅ | OGC API, api.waterdata.usgs.gov |
| WQP | ✅ | `/wqx3/` beta 필수 (legacy 폐기) |
| EPA AQS | ⚠️ | 이메일+키, 10 req/min — P1 |
| CAMS (ADS) | ⚠️ | Copernicus 계정 필요 — P1 보류 |

### Phase 2 — Climate Trends Strip (`f69988b`, `ddf8735`)
3개 카드 모두 라이브.

| 카드 | 커넥터 | 최신값 (검증일) |
|------|--------|-----------------|
| CO₂ | `noaa_gml.py` — Mauna Loa 직접 다운로드 | 429.35 ppm (2026-02) |
| Global Temp | `noaa_ctag.py` — NOAAGlobalTemp CDR v6.1 ASCII | +0.53 °C vs 1991-2020 (2026-02) |
| Arctic Sea Ice | `nsidc.py` — G02135 v4.0 daily CSV, 5-day mean | 13.98 M km² (2026-04-09) |

- 팬아웃 엔드포인트 `GET /api/trends` — 3개 커넥터 병렬 실행, 한 개 실패해도 나머지 정상 반환
- `TrendsStrip.tsx` — MetaLine(cadence · badge · source)이 수치 위에 표시

### Phase 3 — Earth Now Globe (`00a1ae1`, `0b85e37`)
글로브 + 4개 레이어 + Story Panel.

**라이브러리:** `react-globe.gl` (Cesium 대신 — 번들 3-5 MB 절감)

| 레이어 | 커넥터 | 상태 |
|--------|--------|------|
| Base (BlueMarble) | NASA GIBS WMS GetMap | ✅ 항상 ON |
| Fires | `firms.py` — VIIRS Area API, top 1,500 by FRP | ✅ 기본 ON |
| Ocean Heat | `oisst.py` — ERDDAP griddap stride 20, 1,684 points | ✅ |
| Air Monitors | `openaq.py` — v3 PM2.5 locations, AQI 색상 밴드 | ✅ (키 필요) |
| Smoke | `cams.py` | ⚪ P1 보류 (Copernicus 계정 없음) |

- `Globe.tsx` — `forwardRef` + `flyTo()` 명령 핸들 (Story Panel 연동)
- `StoryPanel.tsx` — "2026 Wildfire Season" 프리셋, "Explore on Globe" + "Read Local Report →"
- 레이어 규칙: 연속 필드 1개 + 이벤트 오버레이 1개

### Phase 4 — Local Reports (`e925798`, `7265819`, `f430f89`, `0342dd9`)
10개 metro, 6블록 구조 라이브.

**커넥터 (Block별):**
| 커넥터 | 블록 | 검증 수치 |
|--------|------|-----------|
| `airnow.py` | Block 1 현재 AQI | Houston AQI 63 · Moderate · PM2.5 |
| `climate_normals.py` | Block 2 기준선 | Houston 71.1°F / 55.6 in (1991-2020) |
| `echo.py` | Block 3 시설 | 500 샘플, FacSNCFlg + ComplianceStatus |
| `usgs.py` | Block 4 수문 | Houston 51 NRT 사이트 |
| `wqp.py` | Block 4 수질 | Houston 31,549 이산 샘플 |

**ECHO 주요 변경사항 (이전 ofmpub → echodata):**
- Two-hop API: `get_facilities` → QueryID → `get_qid`
- `p_act=Y` 필수 (LA bbox → 363k rows → queryset 한계 초과)
- `FacLong` 없음 (지도 P1 보류), `CurrVioFlag` 없음 → `FacSNCFlg` 사용

**10개 Metro (data/cbsa_mapping.json):**
| CBSA | 이름 | 인구 | 기후 | NOAA 스테이션 |
|------|------|------|------|---------------|
| 26420 | Houston-The Woodlands-Sugar Land | 7.3M | Cfa | USW00012918 |
| 31080 | Los Angeles-Long Beach-Anaheim | 13.2M | Csb | USW00023174 |
| 35620 | New York-Newark-Jersey City | 19.8M | Cfa | USW00094728 |
| 16980 | Chicago-Naperville-Elgin | 9.5M | Dfa | USW00094846 |
| 19100 | Dallas-Fort Worth-Arlington | 7.8M | Cfa | USW00003927 |
| 38060 | Phoenix-Mesa-Chandler | 5.1M | BWh | USW00023183 |
| 37980 | Philadelphia-Camden-Wilmington | 6.2M | Cfa | USW00013739 |
| 41700 | San Antonio-New Braunfels | 2.6M | Cfa | USW00012921 |
| 41740 | San Diego-Chula Vista-Carlsbad | 3.3M | Csb | USW00023188 |
| 41940 | San Jose-Sunnyvale-Santa Clara | 2.0M | Csb | USW00023293 |

**Backend endpoints:**
- `GET /api/reports/` — metro 목록
- `GET /api/reports/search?q=` — ZIP prefix + 이름 매칭
- `GET /api/reports/{cbsa_slug}` — 6블록 리포트 (5개 커넥터 병렬)

**Frontend:**
- `ReportPage.tsx` — 6블록 + MetaLine + graceful degradation + AdSense 슬롯
- 홈 LocalReportsSection: 상위 4개 카드 + "View all N →" + 랭킹/가이드 링크

### Phase 5 — Atlas + Navigation (`02de1c2`)
- `atlas_catalog.json` — 8개 카테고리 × 2-5 데이터셋, 14개 live
- `Atlas.tsx` (/atlas) — 카테고리 카드, trust badge 샘플
- `AtlasCategory.tsx` (/atlas/:slug) — 데이터셋 목록, MetaLine, 404 처리
- `AtlasGrid.tsx` — 홈 진입 카드 (emoji, count, live badge)
- `Header.tsx` — sticky, scrollTo() 앵커, 모바일 햄버거

### Phase 6 — SEO 콘텐츠 (`0342dd9`)
- `GET /api/rankings/epa-violations` — 10개 metro ECHO 병렬 호출, 위반순 정렬
- `Ranking.tsx` (/rankings/epa-violations) — 로딩 안내 + 위반 테이블 + ECHO 면책
- `Guide.tsx` (/guides/how-to-read-aqi) — AQI 6단계 + 색상 스와치 + 오염물질 테이블

### Phase 7 — 배포 + 인프라 (`8d03752`, `46d1c52`)
- `Dockerfile` — python:3.12-slim, 비루트 유저, `$PORT`
- `render.yaml` — Render blueprint (docker runtime, free plan)
- `frontend/public/_headers` — CF Pages 보안 헤더 + 정적 에셋 캐싱
- `frontend/public/_redirects` — SPA fallback
- `docs/deploy.md` — 3가지 옵션 비교 + 단계별 가이드
- **CORS 버그 수정:** pydantic-settings `list[str]` 필드가 plain URL 파싱 실패
  → `str` 타입으로 변경, `main.py`에서 `_parse_origins()` 직접 파싱

### 토큰 최적화 (`085ffe7`)
- `.claudeignore` 추가 (node_modules, dist, __pycache__ 등)
- CLAUDE.md: 299 → 123줄 (다이어트)
- 분산 docs: `connectors.md`, `report-spec.md`, `guardrails.md`, `api-spike-results.md`

---

## 알려진 랜드마인 (docs/guardrails.md 상세 기록)

| 소스 | 함정 | 해결책 |
|------|------|--------|
| EPA ECHO | `ofmpub.epa.gov` 차단 | `echodata.epa.gov` 사용 |
| EPA ECHO | `echo13_rest_services` 404 | `echo_rest_services` 사용 |
| EPA ECHO | 단일 요청으로 시설 목록 안 나옴 | Two-hop: get_facilities → get_qid |
| EPA ECHO | LA같은 대도시 bbox → queryset 초과 | `p_act=Y` 파라미터 필수 |
| EPA ECHO | `FacLong` 없음 | 위도만 사용; 지도 기능 P1 보류 |
| WQP | legacy `/data/` — USGS 2024-03-11 이후 데이터 없음 | `/wqx3/` beta 필수 |
| WQP | `providers=NWIS,STORET` comma-join → 0 rows | repeated params 사용 |
| pydantic-settings | `list[str]` 필드 — plain URL → json.loads 실패 | `str` 타입 + 직접 파싱 |

---

## 2차 작업 목록

### 우선순위 높음
1. **Metro 40개 추가** — 50개 채우기 (현재 10/50)
   - 상위 50개 CBSA 선정, CBSA code / NOAA 스테이션 / ZIP prefix 조사
2. **PM2.5 연간 랭킹** — EPA AQS key 등록 후 `GET /api/rankings/pm25`
3. **AdSense 신청** — 콘텐츠 충분 (10개 리포트 + 2개 SEO 페이지)
4. **커스텀 도메인** — CF Pages + Render 양쪽 설정

### 우선순위 중간
5. **가이드 3~4개 추가**
   - "What Your Water Quality Samples Mean"
   - "How to Interpret ECHO Compliance Data"
   - "Understanding Climate Normals"
6. **Born-in Interactive 완성** (P1 바이럴)
   - CO₂ / 기온 / 해빙 then vs now 비교
   - OG image 자동 생성 → SNS 공유

### 우선순위 낮음
7. **Story Panel 프리셋 확장** — 5~10개 (현재 1개)
8. **Block 2 도시 시계열** — NOAAGlobalTemp city product 연동
9. **CAMS Smoke 레이어** — Copernicus 계정 승인 후

---

## 블로커

| 항목 | 내용 | 해결 방법 |
|------|------|-----------|
| Render Free tier 슬립 | 15분 비활성 → 30초 cold start | UptimeRobot 핑 or Starter $7/월 전환 |
| CAMS Smoke | Copernicus ADS 계정 수동 승인 | 신청 완료 후 대기 |
| EPA AQS | 이메일 + 키 등록 필요 (10 req/min) | 등록 후 `epa_aqs_email/key` .env 추가 |
| FIRMS / OpenAQ | 키 미등록 → 해당 레이어 비활성 | 무료 등록 필요 |
