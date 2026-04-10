/**
 * 이달의 기후 이야기 (Story Panel) — P0.
 * 계절/이벤트 프리셋 기반: 산불, 허리케인, 폭염, 홍수, 해빙 최소.
 * 초기 프리셋 5~10개 사전 준비.
 */
export default function StoryPanel() {
  return (
    <aside style={{ padding: '16px', border: '1px solid #e5e7eb', borderRadius: '8px', background: '#fff' }}>
      <h3>This Month's Climate Story</h3>
      <p style={{ color: '#64748b', fontSize: '14px' }}>
        Preset-driven editorial card (TBD).
      </p>
      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
        <button>Explore on Globe</button>
        <button>Read Local Report →</button>
      </div>
    </aside>
  );
}
