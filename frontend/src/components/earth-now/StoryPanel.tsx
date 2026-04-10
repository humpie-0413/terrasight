/**
 * This Month's Climate Story panel — P0.
 *
 * CLAUDE.md spec: preset-driven editorial card, initial preset bank 5-10.
 * MVP ships one hardcoded preset ("2026 Wildfire Season") backed by
 * /api/earth-now/story — the full preset bank lands in a later pass.
 *
 * Interaction:
 *   "Explore on Globe" → parent sets Fires layer ON + flies camera to
 *                        the preset's globe_hint location.
 *   "Read Local Report →" → links to /reports/{slug}.
 */

import { useApi } from '../../hooks/useApi';

interface StoryResponse {
  preset_id: string;
  title: string;
  body: string;
  globe_hint: {
    layer_on: string;
    camera: { lat: number; lng: number; altitude: number };
  };
  report_link: string;
}

interface StoryPanelProps {
  onExploreOnGlobe: (
    layerOn: string,
    camera: { lat: number; lng: number; altitude: number },
  ) => void;
}

export default function StoryPanel({ onExploreOnGlobe }: StoryPanelProps) {
  const { data, loading, error } = useApi<StoryResponse>('/earth-now/story');

  if (loading) {
    return (
      <aside style={cardStyle}>
        <div style={{ color: '#64748b', fontSize: '13px' }}>
          Loading this month's story…
        </div>
      </aside>
    );
  }
  if (error || !data) {
    return (
      <aside style={cardStyle}>
        <div style={{ color: '#b91c1c', fontSize: '13px' }}>
          Story unavailable.
        </div>
      </aside>
    );
  }

  return (
    <aside style={cardStyle}>
      <div
        style={{
          fontSize: '10px',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: '#64748b',
          marginBottom: '6px',
        }}
      >
        This Month's Climate Story
      </div>
      <h3 style={{ margin: '0 0 10px', fontSize: '20px', color: '#0f172a' }}>
        {data.title}
      </h3>
      <p
        style={{
          margin: '0 0 16px',
          fontSize: '14px',
          lineHeight: 1.55,
          color: '#334155',
        }}
      >
        {data.body}
      </p>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() =>
            onExploreOnGlobe(data.globe_hint.layer_on, data.globe_hint.camera)
          }
          style={primaryBtnStyle}
        >
          Explore on Globe
        </button>
        <a href={data.report_link} style={secondaryBtnStyle}>
          Read Local Report →
        </a>
      </div>

      <DataStatusLegend />
    </aside>
  );
}

function DataStatusLegend() {
  const items: Array<{ emoji: string; label: string }> = [
    { emoji: '🟢', label: 'observed' },
    { emoji: '🟡', label: 'NRT' },
    { emoji: '🟠', label: 'forecast' },
    { emoji: '🔵', label: 'derived' },
    { emoji: '⚪', label: 'estimated' },
  ];
  return (
    <div
      style={{
        marginTop: '20px',
        paddingTop: '14px',
        borderTop: '1px solid #e5e7eb',
      }}
    >
      <div
        style={{
          fontSize: '10px',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: '#64748b',
          marginBottom: '6px',
        }}
      >
        Data Status
      </div>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px 12px',
          fontSize: '11px',
          color: '#475569',
        }}
      >
        {items.map((it) => (
          <span key={it.label}>
            {it.emoji} {it.label}
          </span>
        ))}
      </div>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  padding: '20px',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  background: '#fff',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
  display: 'flex',
  flexDirection: 'column',
};

const primaryBtnStyle: React.CSSProperties = {
  padding: '8px 14px',
  fontSize: '13px',
  fontWeight: 600,
  background: '#dc2626',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontFamily: 'system-ui, sans-serif',
};

const secondaryBtnStyle: React.CSSProperties = {
  padding: '8px 14px',
  fontSize: '13px',
  fontWeight: 600,
  background: '#f1f5f9',
  color: '#0f172a',
  border: '1px solid #cbd5e1',
  borderRadius: '6px',
  textDecoration: 'none',
  fontFamily: 'system-ui, sans-serif',
  display: 'inline-block',
};
