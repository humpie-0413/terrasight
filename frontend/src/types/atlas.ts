import type { TrustTag } from '../utils/trustTags';

export interface AtlasCategory {
  slug: string;
  title: string;
  description: string;
}

export interface AtlasDataset {
  id: string;
  title: string;
  categorySlug: string;
  source: string;
  sourceUrl: string;
  cadence: string;
  spatialScope: string;
  license: string;
  tag: TrustTag;
  notes: string[];
}
