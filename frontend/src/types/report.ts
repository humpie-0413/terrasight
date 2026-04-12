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

// ── Phase E.3: shared BlockBase envelope for the four new report blocks ──
//
// These interfaces mirror the backend's per-block envelope. They live here
// so that any future consumer outside `ReportPage.tsx` can import a single
// canonical shape. `ReportPage.tsx` keeps its own inline copies for local
// rendering, following the file's existing pattern for blocks 0-6.

export interface BlockBase {
  status: 'ok' | 'error' | 'not_configured' | 'pending';
  error?: string | null;
  message?: string;
  source?: string;
  source_url?: string;
  cadence?: string;
  tag?: TrustTag;
  spatial_scope?: string;
  license?: string;
  notes?: string[];
}

// ── toxic_releases (EPA TRI) ─────────────────────────────────────────────

export interface ToxicReleasesFacility {
  name: string;
  city: string | null;
  state: string | null;
  chemicals: string[]; // up to 5
  year: number | null;
}

export interface ToxicReleasesValues {
  facility_count: number;
  top_facilities: ToxicReleasesFacility[];
  chemicals_sampled: number;
}

export interface ToxicReleasesBlock extends BlockBase {
  values: ToxicReleasesValues | null;
}

// ── site_cleanup (Superfund + Brownfields) ───────────────────────────────

export interface SuperfundSite {
  name: string;
  lat: number | null;
  lon: number | null;
  city: string | null;
  state: string | null;
  // "F" (Final), "P" (Proposed), "D" (Deleted), "R" (Removed)
  npl_status: string | null;
  address: string | null;
}

export interface BrownfieldsSite {
  name: string;
  lat: number | null;
  lon: number | null;
  city: string | null;
  state: string | null;
  // Always null per connector landmine: spatial point layer doesn't
  // expose cleanup status.
  cleanup_status: string | null;
}

export interface SiteCleanupValues {
  superfund: {
    count: number;
    sites: SuperfundSite[];
  };
  brownfields: {
    count: number;
    sites: BrownfieldsSite[];
  };
}

export interface SiteCleanupBlock extends BlockBase {
  values: SiteCleanupValues | null;
}

// ── facility_ghg (EPA GHGRP) ─────────────────────────────────────────────

export interface FacilityGhgFacility {
  name: string;
  city: string | null;
  state: string | null;
  total_co2e_tonnes: number | null;
  year: number | null;
}

export interface FacilityGhgValues {
  facility_count: number;
  total_co2e_tonnes: number | null;
  year: number | null;
  top_facilities: FacilityGhgFacility[];
}

export interface FacilityGhgBlock extends BlockBase {
  values: FacilityGhgValues | null;
}

// ── drinking_water (EPA SDWIS) ───────────────────────────────────────────

export interface DrinkingWaterViolation {
  pwsid: string;
  name: string;
  city: string | null;
  population_served: number | null;
  // "GW" (groundwater), "SW" (surface water), etc.
  primary_source: string | null;
  // YYYY-MM-DD
  latest_violation_date: string | null;
  violation_count: number;
}

export interface DrinkingWaterValues {
  system_count: number;
  violation_count: number;
  systems_with_violations: number;
  violation_rate_pct: number | null;
  recent_violations: DrinkingWaterViolation[];
  total_population_affected: number;
}

export interface DrinkingWaterBlock extends BlockBase {
  values: DrinkingWaterValues | null;
}
