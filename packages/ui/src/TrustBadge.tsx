import type { TrustTag } from '@terrasight/schemas';

interface TrustTagMeta {
  label: string;
  color: string;
  emoji: string;
  description: string;
}

const TRUST_TAG_META: Record<TrustTag, TrustTagMeta> = {
  observed: {
    label: 'observed',
    color: '#22c55e',
    emoji: '\u{1F7E2}',
    description: 'Direct instrument measurement',
  },
  'near-real-time': {
    label: 'near-real-time',
    color: '#eab308',
    emoji: '\u{1F7E1}',
    description: 'Processed within hours',
  },
  forecast: {
    label: 'forecast',
    color: '#f97316',
    emoji: '\u{1F7E0}',
    description: 'Model output (CAMS, GFS, ERA5)',
  },
  derived: {
    label: 'derived',
    color: '#3b82f6',
    emoji: '\u{1F535}',
    description: 'Computed from observations',
  },
  compliance: {
    label: 'compliance',
    color: '#a855f7',
    emoji: '\u{1F7E3}',
    description: 'Self-reported regulatory data',
  },
};

export interface TrustBadgeProps {
  tag: TrustTag;
}

export function TrustBadge({ tag }: TrustBadgeProps) {
  const meta = TRUST_TAG_META[tag];
  return (
    <span
      title={meta.description}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 8px',
        borderRadius: '9999px',
        fontSize: '11px',
        fontWeight: 600,
        backgroundColor: `${meta.color}22`,
        color: meta.color,
        border: `1px solid ${meta.color}55`,
      }}
    >
      <span>{meta.emoji}</span>
      <span>{meta.label}</span>
    </span>
  );
}
