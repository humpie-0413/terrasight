import type { TrustTag } from '../utils/trustTags';

export interface CbsaMeta {
  cbsaCode: string;
  slug: string;
  name: string; // official CBSA name
  population: number;
  koppen: string;
  lastUpdated: string;
}

export interface KeySignal {
  label: string;
  value: string;
  tag: TrustTag;
}

export interface ReportBlockSource {
  name: string;
  url?: string;
  cadence: string;
  tag: TrustTag;
  geoUnit: string; // "CBSA", "city", "reporting area", "county", ...
}

export interface LocalReport {
  meta: CbsaMeta;
  keySignals: KeySignal[];
  sources: ReportBlockSource[];
}
