import TrustBadge from './TrustBadge';
import SourceLabel from './SourceLabel';
import { TrustTag } from '../../utils/trustTags';

interface MetaLineProps {
  cadence: string; // e.g. "Daily", "Monthly", "NRT ~3h"
  tag: TrustTag;
  source: string;
  sourceUrl?: string;
}

/**
 * 메타정보 한 줄: 갱신주기 · 신뢰태그 · 출처.
 * CLAUDE.md: "메타정보가 숫자보다 먼저 보여야 함"
 */
export default function MetaLine({ cadence, tag, source, sourceUrl }: MetaLineProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
      <span style={{ fontSize: '11px', color: '#64748b' }}>{cadence}</span>
      <TrustBadge tag={tag} />
      <SourceLabel source={source} url={sourceUrl} />
    </div>
  );
}
