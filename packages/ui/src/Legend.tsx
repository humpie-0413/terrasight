import type { TrustTag } from '@terrasight/schemas';
import { TrustBadge } from './TrustBadge';

// Inline dark-theme equivalent of MetaLine (MetaLine is dark-on-light).
// We intentionally keep this local so we don't touch MetaLine (another
// agent consumes it).
interface DarkMetaRowProps {
  cadence: string;
  tag: TrustTag;
  source: string;
  sourceUrl?: string;
}

function DarkMetaRow({ cadence, tag, source, sourceUrl }: DarkMetaRowProps) {
  const mutedStyle = { fontSize: '11px', color: '#94a3b8' } as const;
  const sourceText = `Source: ${source}`;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flexWrap: 'wrap',
        marginTop: '4px',
      }}
    >
      <span style={mutedStyle}>{cadence}</span>
      <TrustBadge tag={tag} />
      {sourceUrl ? (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{ ...mutedStyle, textDecoration: 'underline' }}
        >
          {sourceText}
        </a>
      ) : (
        <span style={mutedStyle}>{sourceText}</span>
      )}
    </div>
  );
}

// Color-bar gradient lookup by LayerManifest.legend.colormap.
const COLORMAP_GRADIENTS: Record<string, string> = {
  GHRSST_L4_MUR_Sea_Surface_Temperature:
    'linear-gradient(to right, #1e3a8a, #06b6d4, #fde047, #ef4444)',
  MODIS_Terra_Aerosol: 'linear-gradient(to right, #bae6fd, #fbbf24, #b45309)',
  MODIS_Aqua_Cloud_Fraction_Day:
    'linear-gradient(to right, #0f172a, #64748b, #f1f5f9)',
};

const FALLBACK_GRADIENT = 'linear-gradient(to right, #64748b, #cbd5e1)';

export interface LayerSummary {
  id: string;
  title: string;
  source: string;
  sourceUrl?: string;
  trustTag: TrustTag;
  cadence: string;
  // Color bar + unit, only set for continuous layers with a numeric legend.
  // For layers like NightLights that lack a numeric scale, omit this.
  scale?: { unit: string; min: number; max: number; colormap?: string };
  caveat?: string;
}

export interface EventLayerSummary {
  id: string;
  title: string;
  source: string;
  sourceUrl?: string;
  trustTag: TrustTag;
  cadence: string;
  count?: number;
  caveat?: string;
}

export interface LegendProps {
  activeImagery: LayerSummary | null;
  activeEvent: EventLayerSummary | null;
}

const sectionLabelStyle = {
  fontSize: '10px',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.08em',
  color: '#94a3b8',
  fontWeight: 600,
  marginBottom: '4px',
};

const titleStyle = {
  fontSize: '13px',
  fontWeight: 700,
  color: '#f1f5f9',
};

const caveatStyle = {
  fontSize: '10px',
  fontStyle: 'italic' as const,
  color: '#94a3b8',
  marginTop: '6px',
  lineHeight: 1.4,
};

const dimmedTextStyle = {
  fontSize: '12px',
  color: '#64748b',
  fontStyle: 'italic' as const,
};

function ColorBar({ scale }: { scale: NonNullable<LayerSummary['scale']> }) {
  const gradient =
    (scale.colormap && COLORMAP_GRADIENTS[scale.colormap]) || FALLBACK_GRADIENT;
  return (
    <div style={{ marginTop: '8px' }}>
      <div
        style={{
          height: '8px',
          borderRadius: '4px',
          background: gradient,
        }}
      />
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: '4px',
          fontSize: '10px',
          color: '#94a3b8',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        <span>
          {scale.min} {scale.unit}
        </span>
        <span>
          {scale.max} {scale.unit}
        </span>
      </div>
    </div>
  );
}

export function Legend({ activeImagery, activeEvent }: LegendProps) {
  return (
    <div
      style={{
        position: 'absolute',
        bottom: '16px',
        left: '16px',
        zIndex: 10,
        background: 'rgba(15, 23, 42, 0.85)',
        color: '#e2e8f0',
        padding: '12px 16px',
        borderRadius: '8px',
        minWidth: '240px',
        maxWidth: '320px',
        fontFamily: 'system-ui, sans-serif',
        fontSize: '12px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
        border: '1px solid rgba(148, 163, 184, 0.15)',
      }}
    >
      <section>
        <div style={sectionLabelStyle}>Imagery</div>
        {activeImagery === null ? (
          <div style={dimmedTextStyle}>
            Base: Natural Earth (Blue Marble composite)
          </div>
        ) : (
          <>
            <div style={titleStyle}>{activeImagery.title}</div>
            <DarkMetaRow
              cadence={activeImagery.cadence}
              tag={activeImagery.trustTag}
              source={activeImagery.source}
              sourceUrl={activeImagery.sourceUrl}
            />
            {activeImagery.scale && <ColorBar scale={activeImagery.scale} />}
            {activeImagery.caveat && (
              <div style={caveatStyle}>{activeImagery.caveat}</div>
            )}
          </>
        )}
      </section>

      <div
        style={{
          borderTop: '1px solid rgba(148, 163, 184, 0.2)',
          margin: '10px 0',
        }}
      />

      <section>
        <div style={sectionLabelStyle}>Events</div>
        {activeEvent === null ? (
          <div style={dimmedTextStyle}>No event layer active</div>
        ) : (
          <>
            <div
              style={{
                display: 'flex',
                alignItems: 'baseline',
                gap: '6px',
                flexWrap: 'wrap',
              }}
            >
              <span style={titleStyle}>{activeEvent.title}</span>
              {typeof activeEvent.count === 'number' && (
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                  &middot; {activeEvent.count} events
                </span>
              )}
            </div>
            <DarkMetaRow
              cadence={activeEvent.cadence}
              tag={activeEvent.trustTag}
              source={activeEvent.source}
              sourceUrl={activeEvent.sourceUrl}
            />
            {activeEvent.caveat && (
              <div style={caveatStyle}>{activeEvent.caveat}</div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
