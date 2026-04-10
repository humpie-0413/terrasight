/**
 * Earth Now 지구본 컴포넌트.
 * TODO: Cesium or Globe.gl 선택 후 렌더링.
 * CLAUDE.md: "베이스 = NASA GIBS Natural Earth, 기본 on = Natural Earth + Fires"
 * 레이어 규칙: 연속 필드 1개 + 이벤트 오버레이 1개만 동시 활성화
 */
export default function Globe() {
  return (
    <div id="earth-now" style={{ position: 'relative', width: '100%', height: '520px', background: '#0b1120', borderRadius: '8px' }}>
      <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: '#94a3b8' }}>
        Globe placeholder (Cesium/Globe.gl TBD)
      </div>
      {/* TODO: layer toggles — Fires | Ocean Heat | Smoke | Air monitors */}
    </div>
  );
}
