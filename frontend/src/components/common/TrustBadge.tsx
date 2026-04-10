import { TrustTag, TRUST_TAG_META } from '../../utils/trustTags';

interface TrustBadgeProps {
  tag: TrustTag;
}

/**
 * 5단계 신뢰 태그 뱃지: observed / near-real-time / forecast / derived / estimated
 * CLAUDE.md 가드레일: 모든 데이터 표시에 신뢰 태그 필수.
 */
export default function TrustBadge({ tag }: TrustBadgeProps) {
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
        backgroundColor: meta.color + '22',
        color: meta.color,
        border: `1px solid ${meta.color}55`,
      }}
    >
      <span>{meta.emoji}</span>
      <span>{meta.label}</span>
    </span>
  );
}
