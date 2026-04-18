# TerraSight 자체 렌더링 파이프라인 — 단계별 CLI 프롬프트

**작성일:** 2026-04-15
**목적:** 전지구 환경 데이터를 자체 연속 표면 PNG로 렌더링하여 Globe에 드레이프

---

## 전체 로드맵

```
Step 0: SST 파이프라인 검증 (이미 구현됨 — 동작 확인만)
Step 1: SST 파이프라인 수정 (안 되면 디버깅)
Step 2: PM2.5 대기질 연속 표면 (Tier 1 최우선)
Step 3: 강수량 연속 표면
Step 4: NO₂ 대기오염 연속 표면
Step 5: 기온 연속 표면
Step 6: 산불 이벤트 레이어 개선
Step 7: 지진 이벤트 레이어 유지
Step 8: Globe UI 최종 정리 (카테고리 재배치 + 범례 통일)
Step 9: 나머지 Tier 2 레이어 (토양수분, 풍속, 해수면, 산호)
Step 10: 전체 QA + 배포 + 정리
```

---

## Step 0: SST 파이프라인 동작 확인

> 이미 구현됨. 배포 후 동작만 확인.

```
/model sonnet
@CLAUDE.md 와 @progress.md 읽고 다음을 해줘.

## SST 자체 렌더링 파이프라인 동작 확인

1. 백엔드에서 직접 테스트:
   curl https://terrasight-api-o959.onrender.com/api/globe/surface/sst.png -o test_sst.png
   파일 크기와 이미지 유효성 확인.

2. 프런트에서 "Sea Surface Temp" 탭 클릭 시:
   - BitmapLayer가 PNG를 로드하는지 Network 탭 확인
   - Globe에 연속 표면이 보이는지

3. 안 되면 원인 진단:
   - Render Free tier에서 numpy/scipy 메모리 초과?
   - OISST ERDDAP 응답 타임아웃?
   - PNG 렌더링 에러?

결과만 보고해줘. 수정은 Step 1에서.
```

---

## Step 1: SST 파이프라인 수정 (필요 시)

> Step 0에서 문제가 발견된 경우에만 실행.

```
/model sonnet
@CLAUDE.md 와 @progress.md 읽고 다음을 해줘.

## SST 파이프라인 수정

Step 0에서 발견된 문제를 수정해줘.

가능한 문제와 해결법:
- 메모리 초과 → stride를 4로 올려서 격자 크기 줄이기
- ERDDAP 타임아웃 → timeout 60s로 늘리기 + retry 3회
- PNG 렌더링 실패 → surface_renderer.py 디버깅
- BitmapLayer 안 보임 → bounds [-180,-90,180,90] 확인, opacity 조절

수정 후 로컬에서 테스트:
python -c "from backend.utils.surface_renderer import render_gridded_surface_png; print('OK')"

git commit + push + progress.md 업데이트.
```

---

## Step 2: PM2.5 대기질 연속 표면 (Tier 1 최우선)

> SST와 동일한 파이프라인 패턴. 가장 임팩트 높은 레이어.

```
/model opus
먼저 /mnt/skills/public/frontend-design/SKILL.md 읽어.
그 다음 @CLAUDE.md 와 @progress.md 와 @backend/utils/surface_renderer.py 와 @backend/api/globe_surface.py 읽고 다음을 해줘.

## PM2.5 전지구 연속 표면 — SST 패턴 복제

### 데이터 소스 조사 + 선택

전지구 PM2.5 격자 데이터를 무료로 제공하는 소스를 조사:
1. Open-Meteo Air Quality API — https://open-meteo.com/en/docs/air-quality-api
   - 전지구 PM2.5, PM10, NO₂, O₃ 격자 (CAMS 기반)
   - REST JSON API (인증 불필요)
   - 해상도 0.4° (약 40km)
   - 시간별 갱신
   
2. CAMS Global Atmospheric Composition (Copernicus ADS)
   - 더 고해상도이지만 CDS API 인증 + cdsapi 패키지 필요
   
3. 둘 다 안 되면 대안은?

가장 쉽고 빠른 소스 1개를 선택해서 구현.

### 백엔드 구현

1. connectors/open_meteo_aq.py (또는 선택한 소스):
   - 전지구 격자에서 PM2.5 값 fetch
   - Open-Meteo의 경우: 위도/경도 범위를 분할해서 격자 구성
   - 응답: list[{lat, lon, pm25}]

2. surface_renderer.py에 PM2.5용 colormap 추가:
   - AQI 6단계: Good(녹) → Moderate(노) → USG(주) → Unhealthy(빨) → VU(보라) → Hazardous(갈)
   - vmin=0, vmax=150

3. globe_surface.py에 GET /api/globe/surface/pm25.png 추가:
   - 커넥터 → render_gridded_surface_png → PNG 반환
   - Cache-Control: 1시간

### 프런트엔드

GlobeDeck.tsx:
- "Air Quality" 카테고리가 이 PNG를 BitmapLayer로 로드
- 기존 GIBS AOD 타일 제거 (자체 렌더링으로 대체)
- 범례: AQI 6단계 색상 바

### 검증
- curl /api/globe/surface/pm25.png -o test.png → 유효한 PNG
- Globe에서 Air Quality 선택 → 전지구 PM2.5 연속 표면
- Render Free tier에서 메모리/시간 초과 안 나는지 확인

git commit + push + progress.md 업데이트.
```

---

## Step 3: 강수량 연속 표면

```
/model sonnet
@CLAUDE.md 와 @progress.md 와 @backend/utils/surface_renderer.py 와 @backend/api/globe_surface.py 읽고 다음을 해줘.

## 강수량 전지구 연속 표면

### 데이터 소스
Open-Meteo Weather API — https://open-meteo.com/en/docs
- 전지구 precipitation (mm) 격자
- REST JSON (인증 불필요)
- 시간별 or 일별

### 구현 (SST/PM2.5 패턴 복제)

1. connectors/open_meteo_weather.py:
   - 전지구 격자 강수량 fetch
   - 응답: list[{lat, lon, precipitation_mm}]

2. surface_renderer.py: 강수 colormap
   - 투명(0mm) → 연한파랑(1mm) → 파랑(10mm) → 남색(50mm) → 보라(100mm+)
   - 0mm = 완전 투명 (비 안 오는 지역은 BlueMarble이 보임)

3. globe_surface.py: GET /api/globe/surface/precipitation.png
   - Cache-Control: 1시간

4. GlobeDeck.tsx: "Precipitation" 카테고리 추가
   - BitmapLayer + 범례

git commit + push + progress.md 업데이트.
```

---

## Step 4: NO₂ 대기오염 연속 표면

```
/model sonnet
@CLAUDE.md 와 @progress.md 와 @backend/utils/surface_renderer.py 와 @backend/api/globe_surface.py 읽고 다음을 해줘.

## NO₂ 전지구 연속 표면

### 데이터 소스
Open-Meteo Air Quality API — nitrogen_dioxide 파라미터
- 전지구 NO₂ 격자 (µg/m³)
- CAMS 기반

### 구현 (동일 패턴)

1. 기존 open_meteo_aq.py에 NO₂ fetch 추가 (PM2.5와 같은 커넥터)

2. surface_renderer.py: NO₂ colormap
   - 투명(0) → 녹(10) → 노(40) → 주황(80) → 빨강(150) → 보라(200+)

3. globe_surface.py: GET /api/globe/surface/no2.png
   - Cache-Control: 1시간

4. GlobeDeck.tsx: "NO₂ Pollution" 카테고리 추가
   - BitmapLayer + 범례

git commit + push + progress.md 업데이트.
```

---

## Step 5: 기온 연속 표면

```
/model sonnet
@CLAUDE.md 와 @progress.md 와 @backend/utils/surface_renderer.py 와 @backend/api/globe_surface.py 읽고 다음을 해줘.

## 기온 전지구 연속 표면

### 데이터 소스
Open-Meteo Weather API — temperature_2m 파라미터
- 전지구 2m 기온 격자 (°C)

### 구현 (동일 패턴)

1. 기존 open_meteo_weather.py에 기온 fetch 추가

2. surface_renderer.py: 기온 colormap
   - 남색(-40°C) → 파랑(-20) → 시안(0) → 녹(10) → 노(20) → 주황(30) → 빨강(40) → 갈(50)

3. globe_surface.py: GET /api/globe/surface/temperature.png
   - Cache-Control: 1시간

4. GlobeDeck.tsx: "Temperature" 카테고리 추가
   - BitmapLayer + 범례

git commit + push + progress.md 업데이트.
```

---

## Step 6: 산불 이벤트 레이어 개선

> 점 데이터 — 연속 표면 아님. 별도 이벤트 레이어로 유지.

```
/model sonnet
@CLAUDE.md 와 @progress.md 와 @frontend/src/components/earth-now/GlobeDeck.tsx 읽고 다음을 해줘.

## 산불 이벤트 레이어 개선

산불은 연속 표면이 아닌 이벤트 점 데이터.
현재 ScatterplotLayer로 표시 중.

개선:
1. 3D Globe: ScatterplotLayer + glow ring 유지
   - FRP에 따라 점 크기/색상 그라데이션 (이미 구현됨)
   - 호버 시 상세 정보 팝업

2. 2D Map: HeatmapLayer로 밀도 히트맵 (이미 구현됨)
   - 동작 확인

3. 데이터 카운트를 상단 pill에 표시 (이미 구현됨)

4. 문제 있으면 수정. 없으면 현행 유지.

git commit (변경 있을 때만) + progress.md 업데이트.
```

---

## Step 7: 지진 이벤트 레이어 유지

> 현재 상태 양호. 큰 수정 불필요.

```
/model sonnet
@CLAUDE.md 읽고 확인만 해줘.

## 지진 레이어 확인

현재 Earthquakes 레이어:
- ScatterplotLayer + glow ring
- 진도별 크기/색상
- 호버 시 상세 정보

동작 확인만. 문제 없으면 넘어가.
```

---

## Step 8: Globe UI 최종 정리

> 연속 표면 레이어 + 이벤트 레이어가 모두 완성된 후.

```
/model opus
먼저 /mnt/skills/public/frontend-design/SKILL.md 읽어.
그 다음 @CLAUDE.md 와 @progress.md 읽고 다음을 해줘.

## Globe 카테고리 최종 정리

### 카테고리 재배치 (관심도순)

연속 표면 (Type A):
1. 🌬️ Air Quality (PM2.5) — 기본 표시
2. 🌡️ Temperature
3. 🌧️ Precipitation  
4. 🏭 NO₂ Pollution
5. 🌊 Sea Surface Temp
6. 🪸 Coral Bleaching (SST + DHW 통합 — Step 9에서)

이벤트 (Type B):
7. 🔥 Wildfires
8. 🌍 Earthquakes

제거 (안 되거나 의미 없는 것):
- CO₂ Column (OCO-2) — 3-5% 커버리지라 빈 화면
- Floods (GIBS) — GIBS 타일이 불안정
- Storms — 활성 폭풍 없을 때 빈 화면 (있을 때만 임시 표시?)

### UI 정리
- 하단 바: 8개 탭 (6 연속 + 2 이벤트)
- 연속/이벤트 구분 표시 (색상 또는 아이콘으로)
- 범례: 각 카테고리별 통일된 스타일
- 3D/2D 토글 유지
- 투명 헤더 유지

### 범례 통일
모든 연속 표면 범례를 동일한 레이아웃으로:
- 좌하단, 가로 그라데이션 바
- 단위 + 값 범위
- 반투명 다크 배경

git commit + push + progress.md 업데이트.
```

---

## Step 9: Tier 2 레이어 추가

> Step 2~5 패턴 반복. 필요한 만큼 선택적으로 실행.

```
/model sonnet
@CLAUDE.md 와 @progress.md 와 @backend/utils/surface_renderer.py 와 @backend/api/globe_surface.py 읽고 다음을 해줘.

## Tier 2 연속 표면 레이어 추가

동일한 파이프라인 패턴으로 추가. dispatching-parallel-agents 활용:

Agent 1: 토양수분 (NASA SMAP via Open-Meteo soil_moisture)
- colormap: 갈색(건조) → 녹(적정) → 파랑(습윤)
- GET /api/globe/surface/soil-moisture.png

Agent 2: 풍속 (Open-Meteo wind_speed_10m)  
- colormap: 연회색(0) → 파랑(10) → 녹(20) → 노(30) → 빨강(40+)
- GET /api/globe/surface/wind.png

Agent 3: 산호 통합 (SST anomaly + CRW DHW → stress score)
- colormap: 파랑(건강) → 노(주의) → 빨강(위험) → 보라(극심)
- GET /api/globe/surface/ocean-stress.png

각 에이전트: 커넥터 + surface_renderer colormap + globe_surface 엔드포인트 + GlobeDeck 카테고리.

git commit + push + progress.md 업데이트.
```

---

## Step 10: 전체 QA + 배포 + 정리

```
/model sonnet
@CLAUDE.md 와 @progress.md 읽고 다음을 해줘.

## 최종 QA

### 1. 모든 연속 표면 PNG 엔드포인트 테스트
- /api/globe/surface/sst.png
- /api/globe/surface/pm25.png
- /api/globe/surface/precipitation.png
- /api/globe/surface/no2.png
- /api/globe/surface/temperature.png
각각 curl로 다운받아서 유효한 PNG인지 확인.

### 2. 프런트 전체 카테고리 순회
- 8개 탭 각각 클릭
- Globe에 연속 표면 또는 이벤트 점이 보이는지
- 범례가 표시되는지
- 3D/2D 토글 동작하는지

### 3. 다른 페이지 점검
- /trends — 6개 카드
- /reports — 50개 metro
- /atlas — 8개 카테고리
- /rankings — 6개
- /guides — 4개
각각 접근 가능 + 데이터 표시 확인.

### 4. 빌드 확인
- npm run build 통과
- tsc --noEmit 통과
- 번들 사이즈 기록

### 5. Render 재배포 + Cloudflare 재배포

### 6. progress.md 최종 업데이트
- 연속 표면 레이어 수
- 이벤트 레이어 수
- 전체 커넥터/엔드포인트 수
- 번들 사이즈

git commit + push.
```

---

## 실행 규칙

1. **순서대로** 실행할 것. Step 0 → 1 → 2 → ... → 10
2. **Step 0이 성공해야** Step 2 이후 진행 가능
3. 각 Step 완료 후 **결과 확인** 후 다음 진행
4. 문제 발생 시 **해당 Step에서 해결** 후 넘어가기
5. `/model sonnet`은 구현, `/model opus`는 설계/디버깅
6. 모든 Step 끝에 **progress.md 업데이트 필수**

---

## 핵심 파일 참조

```
백엔드:
- backend/connectors/oisst.py         ← SST 데이터 소스 (참조 패턴)
- backend/utils/surface_renderer.py    ← PNG 렌더링 엔진
- backend/utils/surface_cache.py       ← 파일 캐시
- backend/api/globe_surface.py         ← /api/globe/surface/* 라우터

프런트:
- frontend/src/components/earth-now/GlobeDeck.tsx  ← Globe 컴포넌트
- frontend/src/pages/EarthNow.tsx                  ← Earth Now 페이지

문서:
- docs/globe-first-plan.md
- docs/viz-iterations.md
- docs/self-rendering-plan.md
- progress.md
```
