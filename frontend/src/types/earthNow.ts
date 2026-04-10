import type { TrustTag } from '../utils/trustTags';

export type EarthLayerKind = 'base' | 'continuous' | 'event';

export interface EarthLayer {
  id: string;
  title: string;
  kind: EarthLayerKind;
  source: string;
  cadence: string;
  tag: TrustTag;
  enabledByDefault?: boolean;
}
