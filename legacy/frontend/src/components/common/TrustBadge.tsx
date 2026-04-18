import { TrustTag, TRUST_TAG_META } from '../../utils/trustTags';

interface TrustBadgeProps {
  tag: TrustTag;
}

export default function TrustBadge({ tag }: TrustBadgeProps) {
  const meta = TRUST_TAG_META[tag];
  if (!meta) {
    // Fallback for unknown tags — render a neutral gray badge
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: '4px',
        padding: '2px 8px', borderRadius: '9999px', fontSize: '11px',
        fontWeight: 600, backgroundColor: '#64748b22', color: '#64748b',
        border: '1px solid #64748b55',
      }}>
        <span>{'\u26AA'}</span><span>{String(tag)}</span>
      </span>
    );
  }
  return (
    <span
      title={meta.description}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: '4px',
        padding: '2px 8px', borderRadius: '9999px', fontSize: '11px',
        fontWeight: 600, backgroundColor: meta.color + '22',
        color: meta.color, border: `1px solid ${meta.color}55`,
      }}
    >
      <span>{meta.emoji}</span>
      <span>{meta.label}</span>
    </span>
  );
}
