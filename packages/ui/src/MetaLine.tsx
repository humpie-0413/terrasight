import type { TrustTag } from '@terrasight/schemas';
import { TrustBadge } from './TrustBadge';
import { SourceLabel } from './SourceLabel';

export interface MetaLineProps {
  cadence: string;
  tag: TrustTag;
  source: string;
  sourceUrl?: string;
}

export function MetaLine({ cadence, tag, source, sourceUrl }: MetaLineProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flexWrap: 'wrap',
      }}
    >
      <span style={{ fontSize: '11px', color: '#64748b' }}>{cadence}</span>
      <TrustBadge tag={tag} />
      <SourceLabel source={source} url={sourceUrl} />
    </div>
  );
}
