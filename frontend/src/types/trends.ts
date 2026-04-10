import type { TrustTag } from '../utils/trustTags';

export interface TrendPoint {
  date: string; // ISO 8601
  value: number;
}

export interface ClimateTrendCard {
  id: 'co2' | 'temp' | 'sea-ice';
  title: string;
  unit: string;
  latest: TrendPoint;
  series: TrendPoint[];
  cadence: string;
  tag: TrustTag;
  source: string;
  sourceUrl: string;
  recordStart: string; // e.g. "1958", "1880", "1979"
}
