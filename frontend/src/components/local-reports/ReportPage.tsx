import { useApi } from '../../hooks/useApi';
import MetaLine from '../common/MetaLine';
import { TrustTag } from '../../utils/trustTags';

/**
 * Local Environmental Report — 6-block layout backed by GET /api/reports/{slug}.
 *
 * CLAUDE.md "3층: Local Environmental Reports":
 *   Block 0: Metro Header (4 key-signal mini-cards)
 *   Block 1: Air Quality — AirNow current (reporting area)
 *   Block 2: Climate Change Locally — Climate Normals 1991-2020 baseline
 *   Block 3: Regulated Facilities & Compliance — EPA ECHO
 *   Block 4: Water Snapshot — USGS continuous + WQP discrete
 *   Block 5: Methodology & Data Limitations
 *   Block 6: Related Content (stub)
 *
 * Each backend block can report status "ok" / "error" / "not_configured" /
 * "pending". The frontend renders a healthy block normally, an error block
 * as a small notice, and a pending/not_configured block with registration
 * instructions — so a single connector outage never blanks the whole page.
 *
 * AdSense slots (commented) live between Block 1-2 and Block 3-4 per
 * CLAUDE.md, visually separated from data tables and charts.
 */

interface ReportPageProps {
  cbsaSlug: string;
}

// ── Backend response shape ────────────────────────────────────────────────

interface ReportMeta {
  cbsa_code: string;
  slug: string;
  name: string;
  state: string | null;
  population: number | null;
  population_year: string | null;
  climate_zone: string | null;
  lat: number | null;
  lon: number | null;
  core_county: string | null;
  core_county_fips: string | null;
}

interface KeySignal {
  label: string;
  value: string;
  tag: TrustTag;
  source: string;
}

interface BlockBase {
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

interface AirNowReading {
  aqi: number;
  category: string;
  category_number: number;
  pollutant: string;
  reporting_area: string;
  state_code: string;
  lat: number;
  lon: number;
  observed_at: string;
}

interface AirQualityBlock extends BlockBase {
  values: {
    readings: AirNowReading[];
    headline: AirNowReading | null;
  } | null;
}

interface MonthlyNormal {
  month: number;
  t_avg_f: number | null;
  t_max_f: number | null;
  t_min_f: number | null;
  precip_in: number | null;
}

interface StationNormals {
  station_id: string;
  station_name: string;
  lat: number;
  lon: number;
  elevation_m: number;
  monthly: MonthlyNormal[];
  annual_t_avg_f: number | null;
  annual_precip_in: number | null;
}

interface ClimateBlock {
  status: string;
  baseline: BlockBase & { values: StationNormals | null };
  city_time_series: { status: string; message: string; values: null };
}

interface FacilitySummary {
  name: string;
  registry_id: string;
  lat: number | null;
  in_violation: boolean;
  compliance_status: string | null;
}

interface EchoSummary {
  sampled_facilities: number;
  in_violation: number;
  caa_facilities: number;
  cwa_facilities: number;
  top_violations: FacilitySummary[];
}

interface FacilitiesBlock extends BlockBase {
  values: EchoSummary | null;
}

interface StreamflowReading {
  monitoring_location_id: string;
  site_name: string;
  lat: number;
  lon: number;
  datetime_utc: string;
  value_cfs: number;
  parameter_code: string;
}

interface UsgsWaterSummary {
  site_count: number;
  latest_readings: StreamflowReading[];
  bbox: number[];
}

interface WaterQualitySample {
  station_id: string;
  station_name: string;
  characteristic: string;
  result_value: number | null;
  result_unit: string;
  activity_start_date: string;
  provider: string;
}

interface WqpSummary {
  sample_count: number;
  station_count: number;
  characteristics: string[];
  recent_samples: WaterQualitySample[];
  earliest_sample_date: string | null;
  latest_sample_date: string | null;
}

interface WaterBlock {
  status: string;
  hydrology_nrt: BlockBase & { values: UsgsWaterSummary | null };
  water_quality_discrete: BlockBase & { values: WqpSummary | null };
  disclaimer: string;
}

// ── Phase E.3: 4 new block shapes ─────────────────────────────────────────

interface ToxicReleasesFacility {
  name: string;
  city: string | null;
  state: string | null;
  chemicals: string[];
  year: number | null;
}

interface RcraHandler {
  name: string;
  city: string | null;
  state: string | null;
  waste_tons: number | null;
  year: number | null;
}

interface RcraSummary {
  handler_count: number;
  top_handlers: RcraHandler[];
}

interface ToxicReleasesBlock extends BlockBase {
  values: {
    facility_count: number;
    top_facilities: ToxicReleasesFacility[];
    chemicals_sampled: number;
    rcra_summary: RcraSummary | null;
  } | null;
}

interface SuperfundSite {
  name: string;
  lat: number | null;
  lon: number | null;
  city: string | null;
  state: string | null;
  npl_status: string | null;
  address: string | null;
}

interface BrownfieldsSite {
  name: string;
  lat: number | null;
  lon: number | null;
  city: string | null;
  state: string | null;
  cleanup_status: string | null;
}

interface SiteCleanupBlock extends BlockBase {
  values: {
    superfund: { count: number; sites: SuperfundSite[] };
    brownfields: { count: number; sites: BrownfieldsSite[] };
  } | null;
}

interface FacilityGhgFacility {
  name: string;
  city: string | null;
  state: string | null;
  total_co2e_tonnes: number | null;
  year: number | null;
}

interface FacilityGhgBlock extends BlockBase {
  values: {
    facility_count: number;
    total_co2e_tonnes: number | null;
    year: number | null;
    top_facilities: FacilityGhgFacility[];
  } | null;
}

interface DrinkingWaterViolation {
  pwsid: string;
  name: string;
  city: string | null;
  population_served: number | null;
  primary_source: string | null;
  latest_violation_date: string | null;
  violation_count: number;
}

interface DrinkingWaterBlock extends BlockBase {
  values: {
    system_count: number;
    violation_count: number;
    systems_with_violations: number;
    violation_rate_pct: number | null;
    recent_violations: DrinkingWaterViolation[];
    total_population_affected: number;
  } | null;
}

// ── Phase E.4: Active Alerts + PFAS block shapes ──────────────────────────

interface WeatherAlertItem {
  event: string;
  severity: string;
  certainty: string;
  urgency: string;
  headline: string;
  area_desc: string;
  onset: string;
  expires: string;
  sender: string;
}

interface ActiveAlertsBlock extends BlockBase {
  values: {
    alert_count: number;
    alerts: WeatherAlertItem[];
  } | null;
}

interface PfasDetection {
  system_name: string;
  system_id: string;
  contaminant: string | null;
  city: string | null;
  state: string | null;
}

interface PfasBlock extends BlockBase {
  values: {
    monitored_systems: number;
    unique_contaminants: number;
    most_frequent_contaminant: string | null;
    total_samples: number;
    top_detections: PfasDetection[];
  } | null;
}

// ── Phase E.5: Hazards & Disasters + Coastal Conditions ─────────────────

interface DisasterItem {
  disaster_number: number;
  declaration_type: string;
  declaration_date: string;
  incident_type: string;
  title: string;
  designated_area: string;
}

interface EarthquakeItem {
  magnitude: number;
  place: string;
  depth_km: number;
  time_utc: string;
}

interface HazardsBlock extends BlockBase {
  values: {
    total_disasters: number;
    most_common_type: string | null;
    largest_quake_magnitude: number | null;
    largest_quake_place: string | null;
    recent_disasters: DisasterItem[];
    recent_earthquakes: EarthquakeItem[];
  } | null;
}

interface CoastalStation {
  station_id: string;
  name: string;
  lat: number;
  lon: number;
  water_level_ft: number | null;
  water_temp_f: number | null;
  timestamp: string;
}

interface CoastalBlock extends BlockBase {
  values: {
    station_count: number;
    stations: CoastalStation[];
  } | null;
}

interface MethodologySource {
  block: string;
  source: string;
  source_url: string;
  cadence: string;
  tag: TrustTag;
  spatial_scope: string;
  license: string;
}

interface MethodologyBlock {
  status: string;
  sources: MethodologySource[];
  disclaimers: string[];
}

interface ReportResponse {
  cbsa_slug: string;
  meta: ReportMeta;
  key_signals: KeySignal[];
  blocks: {
    air_quality: AirQualityBlock;
    climate_locally: ClimateBlock;
    facilities: FacilitiesBlock;
    toxic_releases: ToxicReleasesBlock;
    active_alerts: ActiveAlertsBlock;
    pfas_monitoring: PfasBlock;
    site_cleanup: SiteCleanupBlock;
    facility_ghg: FacilityGhgBlock;
    drinking_water: DrinkingWaterBlock;
    water: WaterBlock;
    hazards_disasters: HazardsBlock;
    coastal_conditions?: CoastalBlock;
    methodology: MethodologyBlock;
    related: { status: string; message: string };
  };
}

// ── Component ─────────────────────────────────────────────────────────────

export default function ReportPage({ cbsaSlug }: ReportPageProps) {
  const { data, loading, error } = useApi<ReportResponse>(
    `/reports/${cbsaSlug}`,
  );

  if (loading) {
    return (
      <article style={pageStyle}>
        <p style={loadingStyle}>Loading report for {cbsaSlug}…</p>
      </article>
    );
  }

  if (error || !data) {
    const is404 = error?.message?.includes('404');
    return (
      <article style={pageStyle}>
        <h1 style={h1Style}>{is404 ? 'Metro not found' : 'Report unavailable'}</h1>
        <p style={errorStyle}>
          {is404
            ? `No report exists for "${cbsaSlug}". Check the URL or search for another metro.`
            : (error?.message ?? 'Unknown error')}
        </p>
        <a href="/" style={{ color: '#2563eb', fontSize: '14px' }}>
          ← Back to home
        </a>
      </article>
    );
  }

  const { meta, key_signals, blocks } = data;

  return (
    <article style={pageStyle}>
      {/* Block 0 — Metro Header */}
      <section style={sectionStyle}>
        <h1 style={h1Style}>{meta.name}</h1>
        <p style={subheadStyle}>
          {meta.state ? `${meta.state} · ` : ''}
          {meta.population
            ? `Pop. ${meta.population.toLocaleString()}${
                meta.population_year ? ` (${meta.population_year})` : ''
              }`
            : ''}
          {meta.climate_zone ? ` · ${meta.climate_zone}` : ''}
        </p>
        <div style={keySignalsGrid}>
          {key_signals.map((s) => (
            <KeySignalCard key={s.label} signal={s} />
          ))}
        </div>
      </section>

      {/* Block 1 — Air Quality */}
      <Block1AirQuality block={blocks.air_quality} />

      {/* AdSense slot #1 */}
      <AdSlot id="ad-1" />

      {/* Block 2 — Climate Change Locally */}
      <Block2Climate block={blocks.climate_locally} />

      {/* Block 13 — Active Weather Alerts (NWS) */}
      <Block13ActiveAlerts block={blocks.active_alerts} />

      {/* Block 3 — Regulated Facilities & Compliance */}
      <Block3Facilities block={blocks.facilities} />

      {/* AdSense slot #2 */}
      <AdSlot id="ad-2" />

      {/* Block 7 — Toxic Releases (EPA TRI) */}
      <Block7ToxicReleases block={blocks.toxic_releases} />

      {/* Block 11 — PFAS Monitoring */}
      <Block11Pfas block={blocks.pfas_monitoring} />

      {/* AdSense slot #3 */}
      <AdSlot id="ad-3" />

      {/* Block 8 — Site Cleanup (Superfund + Brownfields) */}
      <Block8SiteCleanup block={blocks.site_cleanup} />

      {/* Block 9 — Facility GHG (EPA GHGRP) */}
      <Block9FacilityGhg block={blocks.facility_ghg} />

      {/* AdSense slot #4 */}
      <AdSlot id="ad-4" />

      {/* Block 10 — Drinking Water (EPA SDWIS) */}
      <Block10DrinkingWater block={blocks.drinking_water} />

      {/* Block 4 — Water Snapshot */}
      <Block4Water block={blocks.water} />

      {/* Block 14 — Coastal Conditions (CO-OPS) — conditional */}
      {blocks.coastal_conditions && (
        <Block14Coastal block={blocks.coastal_conditions} />
      )}

      {/* AdSense slot #5 */}
      <AdSlot id="ad-5" />

      {/* Block 12 — Hazards & Disaster History */}
      <Block12Hazards block={blocks.hazards_disasters} />

      {/* Block 5 — Methodology */}
      <Block5Methodology block={blocks.methodology} />

      {/* Block 6 — Related Content */}
      <Block6Related block={blocks.related} />
    </article>
  );
}

// ── Block 0: Key signal mini-card ─────────────────────────────────────────

function KeySignalCard({ signal }: { signal: KeySignal }) {
  return (
    <div style={keySignalCard}>
      <div style={keySignalLabel}>{signal.label}</div>
      <div style={keySignalValue}>{signal.value}</div>
      <div style={keySignalSource}>{signal.source}</div>
    </div>
  );
}

// ── Block 1: Air Quality ──────────────────────────────────────────────────

function Block1AirQuality({ block }: { block: AirQualityBlock }) {
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Air Quality</h2>
      {block.status === 'ok' && (
        <MetaLine
          cadence={block.cadence ?? 'hourly'}
          tag={(block.tag as TrustTag) ?? TrustTag.Observed}
          source={block.source ?? 'AirNow'}
          sourceUrl={block.source_url}
        />
      )}

      {block.status === 'not_configured' && (
        <NotConfiguredNotice message={block.message ?? ''} />
      )}
      {block.status === 'error' && (
        <ErrorNotice error={block.error ?? 'Unknown error'} />
      )}
      {block.status === 'ok' && block.values && (
        <AirQualityBody values={block.values} notes={block.notes ?? []} />
      )}

      <p style={disclaimerStyle}>
        ⚠️ AirNow reports values for a "reporting area", which is not the same
        as the CBSA boundary. Readings come from the monitor(s) closest to the
        sampled ZIP code.
      </p>
    </section>
  );
}

function AirQualityBody({
  values,
  notes,
}: {
  values: NonNullable<AirQualityBlock['values']>;
  notes: string[];
}) {
  const { headline, readings } = values;
  if (!headline) {
    return <p style={loadingStyle}>No readings available.</p>;
  }
  return (
    <>
      <p style={valueStyle}>
        AQI {headline.aqi} <span style={unitStyle}>· {headline.category}</span>
      </p>
      <p style={asOfStyle}>
        Worst pollutant: <strong>{headline.pollutant}</strong> · Reporting area:{' '}
        {headline.reporting_area} · {headline.observed_at}
      </p>
      {readings.length > 1 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Pollutant</th>
              <th style={thStyle}>AQI</th>
              <th style={thStyle}>Category</th>
            </tr>
          </thead>
          <tbody>
            {readings.map((r) => (
              <tr key={`${r.pollutant}-${r.observed_at}`}>
                <td style={tdStyle}>{r.pollutant}</td>
                <td style={tdStyle}>{r.aqi}</td>
                <td style={tdStyle}>{r.category}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {notes.length > 0 && <Notes notes={notes} />}
    </>
  );
}

// ── Block 2: Climate Change Locally ──────────────────────────────────────

function Block2Climate({ block }: { block: ClimateBlock }) {
  const baseline = block.baseline;
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Climate Change Locally</h2>
      {baseline.status === 'ok' && (
        <MetaLine
          cadence={baseline.cadence ?? '30-yr baseline'}
          tag={(baseline.tag as TrustTag) ?? TrustTag.Derived}
          source={baseline.source ?? 'U.S. Climate Normals 1991-2020'}
          sourceUrl={baseline.source_url}
        />
      )}
      {baseline.status === 'error' && (
        <ErrorNotice error={baseline.error ?? 'Unknown error'} />
      )}
      {baseline.status === 'ok' && baseline.values && (
        <ClimateBody values={baseline.values} />
      )}

      <p style={noteStyle}>
        City-level monthly time series (CtaG) is a separate data product and is
        still pending integration — this block currently shows the 30-year
        1991-2020 reference baseline only.
      </p>
    </section>
  );
}

function ClimateBody({ values }: { values: StationNormals }) {
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  return (
    <>
      <p style={asOfStyle}>
        Baseline station: <strong>{values.station_name}</strong> (
        {values.station_id})
      </p>
      <p style={valueStyle}>
        {values.annual_t_avg_f !== null
          ? `${values.annual_t_avg_f.toFixed(1)}°F`
          : '—'}{' '}
        <span style={unitStyle}>annual average</span>
      </p>
      <p style={asOfStyle}>
        Annual precip:{' '}
        {values.annual_precip_in !== null
          ? `${values.annual_precip_in.toFixed(1)} in`
          : '—'}
      </p>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>Month</th>
            <th style={thStyle}>Avg °F</th>
            <th style={thStyle}>Max °F</th>
            <th style={thStyle}>Min °F</th>
            <th style={thStyle}>Precip (in)</th>
          </tr>
        </thead>
        <tbody>
          {values.monthly.map((m) => (
            <tr key={m.month}>
              <td style={tdStyle}>{months[m.month - 1]}</td>
              <td style={tdStyle}>{m.t_avg_f?.toFixed(1) ?? '—'}</td>
              <td style={tdStyle}>{m.t_max_f?.toFixed(1) ?? '—'}</td>
              <td style={tdStyle}>{m.t_min_f?.toFixed(1) ?? '—'}</td>
              <td style={tdStyle}>{m.precip_in?.toFixed(2) ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

// ── Block 3: Regulated Facilities & Compliance ────────────────────────────

function Block3Facilities({ block }: { block: FacilitiesBlock }) {
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Regulated Facilities & Compliance</h2>
      {block.status === 'ok' && (
        <MetaLine
          cadence={block.cadence ?? 'live feed'}
          tag={(block.tag as TrustTag) ?? TrustTag.Observed}
          source={block.source ?? 'EPA ECHO'}
          sourceUrl={block.source_url}
        />
      )}
      {block.status === 'error' && (
        <ErrorNotice error={block.error ?? 'Unknown error'} />
      )}
      {block.status === 'ok' && block.values && (
        <FacilitiesBody values={block.values} notes={block.notes ?? []} />
      )}
      <p style={disclaimerStyle}>
        ⚠️ Regulatory compliance ≠ environmental exposure or health risk.
      </p>
    </section>
  );
}

function FacilitiesBody({
  values,
  notes,
}: {
  values: EchoSummary;
  notes: string[];
}) {
  return (
    <>
      <div style={statsGrid}>
        <Stat label="Facilities sampled" value={values.sampled_facilities} />
        <Stat label="Currently in violation" value={values.in_violation} />
        <Stat label="CAA-regulated (approx.)" value={values.caa_facilities} />
        <Stat label="CWA-regulated (approx.)" value={values.cwa_facilities} />
      </div>
      {values.top_violations.length > 0 && (
        <>
          <h3 style={h3Style}>Top facilities by enforcement activity</h3>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Facility</th>
                <th style={thStyle}>In violation</th>
                <th style={thStyle}>Compliance status</th>
              </tr>
            </thead>
            <tbody>
              {values.top_violations.map((f) => (
                <tr key={f.registry_id || f.name}>
                  <td style={tdStyle}>{f.name}</td>
                  <td style={tdStyle}>{f.in_violation ? '🔴 Yes' : '—'}</td>
                  <td style={tdStyle}>{f.compliance_status ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {notes.length > 0 && <Notes notes={notes} />}
    </>
  );
}

// ── Block 7: Toxic Releases (EPA TRI) ─────────────────────────────────────

function Block7ToxicReleases({ block }: { block: ToxicReleasesBlock }) {
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Toxic Releases — EPA TRI</h2>
      {block.status === 'ok' && (
        <MetaLine
          cadence={block.cadence ?? 'annual'}
          tag={(block.tag as TrustTag) ?? TrustTag.Observed}
          source={block.source ?? 'EPA TRI'}
          sourceUrl={block.source_url}
        />
      )}
      <BlockNonOk block={block} />
      {block.status === 'ok' && block.values && (
        <ToxicReleasesBody values={block.values} />
      )}
      <p style={disclaimerStyle}>
        ⚠️ TRI facilities self-report annual releases under EPCRA §313. Only
        facilities above reporting thresholds are included.
      </p>
    </section>
  );
}

function ToxicReleasesBody({
  values,
}: {
  values: NonNullable<ToxicReleasesBlock['values']>;
}) {
  return (
    <>
      <p style={valueStyle}>
        {values.facility_count}{' '}
        <span style={unitStyle}>TRI-reporting facilities</span>
      </p>
      {values.chemicals_sampled > 0 ? (
        <p style={asOfStyle}>
          {values.chemicals_sampled} unique chemicals sampled
        </p>
      ) : (
        <p style={noteStyle}>
          Chemical enrichment requires a specific reporting year.
        </p>
      )}
      {values.top_facilities.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>City</th>
              <th style={thStyle}>Chemicals</th>
              <th style={thStyle}>Year</th>
            </tr>
          </thead>
          <tbody>
            {values.top_facilities.map((f, i) => (
              <tr key={`tr-${i}`}>
                <td style={tdStyle}>{f.name}</td>
                <td style={tdStyle}>{f.city ?? '—'}</td>
                <td style={tdStyle}>
                  {f.chemicals.length > 0
                    ? f.chemicals.slice(0, 3).join(', ')
                    : '—'}
                </td>
                <td style={tdStyle}>{f.year ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {/* RCRA Hazardous Waste Generators sub-section */}
      {values.rcra_summary && values.rcra_summary.handler_count > 0 && (
        <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #e5e7eb' }}>
          <h3 style={h3Style}>Hazardous Waste Generators (RCRA)</h3>
          <p style={noteStyle}>{values.rcra_summary.handler_count} large-quantity generators (biennial report)</p>
          <table style={tableStyle}>
            <thead><tr>
              <th style={thStyle}>Handler</th>
              <th style={thStyle}>City</th>
              <th style={{...thStyle, textAlign: 'right'}}>Waste (tons)</th>
              <th style={thStyle}>Year</th>
            </tr></thead>
            <tbody>
              {values.rcra_summary.top_handlers.map((h, i) => (
                <tr key={`rcra-${i}`}>
                  <td style={tdStyle}>{h.name}</td>
                  <td style={tdStyle}>{h.city ?? '—'}</td>
                  <td style={{...tdStyle, textAlign: 'right'}}>
                    {h.waste_tons != null ? h.waste_tons.toLocaleString() : '—'}
                  </td>
                  <td style={tdStyle}>{h.year ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

// ── Block 8: Site Cleanup (Superfund + Brownfields) ───────────────────────

const NPL_STATUS_LABELS: Record<string, string> = {
  F: 'NPL Final',
  P: 'Proposed',
  D: 'Deleted',
  R: 'Removed',
};

function Block8SiteCleanup({ block }: { block: SiteCleanupBlock }) {
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Site Cleanup — Superfund & Brownfields</h2>
      {block.status === 'ok' && (
        <MetaLine
          cadence={block.cadence ?? 'quarterly'}
          tag={(block.tag as TrustTag) ?? TrustTag.Observed}
          source={block.source ?? 'EPA CERCLIS / ACRES'}
          sourceUrl={block.source_url}
        />
      )}
      <BlockNonOk block={block} />
      {block.status === 'ok' && block.values && (
        <SiteCleanupBody values={block.values} />
      )}
      <p style={disclaimerStyle}>
        ⚠️ Sites are EPA regulatory records, not exposure assessments.
      </p>
    </section>
  );
}

function SiteCleanupBody({
  values,
}: {
  values: NonNullable<SiteCleanupBlock['values']>;
}) {
  const { superfund, brownfields } = values;
  return (
    <div style={twoColGrid}>
      <div>
        <h3 style={h3Style}>Superfund</h3>
        {superfund.count > 0 ? (
          <>
            <p style={valueStyle}>
              {superfund.count} <span style={unitStyle}>sites</span>
            </p>
            <ul style={cleanupListStyle}>
              {superfund.sites.slice(0, 5).map((s, i) => (
                <li key={`sf-${i}`}>
                  <strong>{s.name}</strong>
                  <div style={cleanupMetaStyle}>
                    {(s.npl_status && NPL_STATUS_LABELS[s.npl_status]) ??
                      'Unknown'}
                    {s.city ? ` · ${s.city}` : ''}
                  </div>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p style={noteStyle}>None reported for this area.</p>
        )}
      </div>
      <div>
        <h3 style={h3Style}>Brownfields</h3>
        {brownfields.count > 0 ? (
          <>
            <p style={valueStyle}>
              {brownfields.count} <span style={unitStyle}>properties</span>
            </p>
            <ul style={cleanupListStyle}>
              {brownfields.sites.slice(0, 5).map((s, i) => (
                <li key={`bf-${i}`}>
                  <strong>{s.name}</strong>
                  {s.city && <div style={cleanupMetaStyle}>{s.city}</div>}
                </li>
              ))}
            </ul>
            <p style={noteStyle}>
              Cleanup status not available via the spatial point layer.
            </p>
          </>
        ) : (
          <p style={noteStyle}>None reported for this area.</p>
        )}
      </div>
    </div>
  );
}

// ── Block 9: Facility GHG (EPA GHGRP) ─────────────────────────────────────

function Block9FacilityGhg({ block }: { block: FacilityGhgBlock }) {
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>
        Facility Greenhouse Gas Emissions — EPA GHGRP
      </h2>
      {block.status === 'ok' && (
        <MetaLine
          cadence={block.cadence ?? 'annual'}
          tag={(block.tag as TrustTag) ?? TrustTag.Observed}
          source={block.source ?? 'EPA GHGRP'}
          sourceUrl={block.source_url}
        />
      )}
      <BlockNonOk block={block} />
      {block.status === 'ok' && block.values && (
        <FacilityGhgBody values={block.values} />
      )}
      <p style={disclaimerStyle}>
        ⚠️ GHGRP captures facilities emitting &gt;25,000 tCO₂e/year; smaller
        emitters are not reported.
      </p>
    </section>
  );
}

function FacilityGhgBody({
  values,
}: {
  values: NonNullable<FacilityGhgBlock['values']>;
}) {
  const totalLabel =
    values.total_co2e_tonnes !== null
      ? `${values.total_co2e_tonnes.toLocaleString()} tCO₂e${
          values.year ? ` (${values.year})` : ''
        }`
      : '—';
  return (
    <>
      <p style={valueStyle}>
        {values.facility_count}{' '}
        <span style={unitStyle}>GHGRP facilities</span>
      </p>
      <p style={asOfStyle}>Total reported emissions: {totalLabel}</p>
      {values.top_facilities.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>City</th>
              <th style={thStyle}>tCO₂e</th>
              <th style={thStyle}>Year</th>
            </tr>
          </thead>
          <tbody>
            {values.top_facilities.map((f, i) => (
              <tr key={`gh-${i}`}>
                <td style={tdStyle}>{f.name}</td>
                <td style={tdStyle}>{f.city ?? '—'}</td>
                <td style={tdStyle}>
                  {f.total_co2e_tonnes !== null
                    ? f.total_co2e_tonnes.toLocaleString()
                    : '—'}
                </td>
                <td style={tdStyle}>{f.year ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

// ── Block 10: Drinking Water (EPA SDWIS) ──────────────────────────────────

function Block10DrinkingWater({ block }: { block: DrinkingWaterBlock }) {
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Drinking Water — EPA SDWIS</h2>
      {block.status === 'ok' && (
        <MetaLine
          cadence={block.cadence ?? 'quarterly'}
          tag={(block.tag as TrustTag) ?? TrustTag.Observed}
          source={block.source ?? 'EPA SDWIS'}
          sourceUrl={block.source_url}
        />
      )}
      <BlockNonOk block={block} />
      {block.status === 'ok' && block.values && (
        <DrinkingWaterBody values={block.values} />
      )}
      <div style={highVisDisclaimerStyle}>
        ⚠️ A regulatory violation does NOT necessarily mean your tap water is
        unsafe. SDWIS data is quarterly and may lag real conditions. Contact
        your local water utility for current water quality information.
      </div>
    </section>
  );
}

function DrinkingWaterBody({
  values,
}: {
  values: NonNullable<DrinkingWaterBlock['values']>;
}) {
  return (
    <>
      <div style={statsGrid}>
        <Stat label="Public water systems" value={values.system_count} />
        <Stat label="Total violations" value={values.violation_count} />
        <Stat
          label="Systems with active violations"
          value={
            values.violation_rate_pct !== null
              ? `${values.violation_rate_pct}%`
              : '—'
          }
        />
        <Stat
          label="People served (systems w/ violations)"
          value={values.total_population_affected.toLocaleString()}
        />
      </div>
      {values.recent_violations.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>System Name</th>
              <th style={thStyle}>City</th>
              <th style={thStyle}>Pop. Served</th>
              <th style={thStyle}>Source</th>
              <th style={thStyle}>Last Violation</th>
              <th style={thStyle}>Violations</th>
            </tr>
          </thead>
          <tbody>
            {values.recent_violations.map((v) => (
              <tr key={v.pwsid}>
                <td style={tdStyle}>{v.name}</td>
                <td style={tdStyle}>{v.city ?? '—'}</td>
                <td style={tdStyle}>
                  {v.population_served !== null
                    ? v.population_served.toLocaleString()
                    : '—'}
                </td>
                <td style={tdStyle}>{v.primary_source ?? '—'}</td>
                <td style={tdStyle}>{v.latest_violation_date ?? '—'}</td>
                <td style={tdStyle}>{v.violation_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

// ── Block 11: PFAS Monitoring ──────────────────────────────────────────────

function Block11Pfas({ block }: { block: PfasBlock }) {
  if (block.status !== 'ok' || !block.values) {
    return (
      <section style={sectionStyle}>
        <h2 style={h2Style}>PFAS Monitoring</h2>
        <BlockNonOk block={block} />
      </section>
    );
  }
  const v = block.values;
  return (
    <section style={sectionStyle}>
      <MetaLine
        cadence={block.cadence ?? 'Quarterly'}
        tag={(block.tag as TrustTag) ?? TrustTag.Observed}
        source={block.source ?? 'EPA PFAS Analytic Tools'}
        sourceUrl={block.source_url}
      />
      <h2 style={h2Style}>PFAS Monitoring</h2>
      <div style={statsGrid}>
        <Stat label="Monitored Systems" value={String(v.monitored_systems)} />
        <Stat label="Unique Contaminants" value={String(v.unique_contaminants)} />
        <Stat label="Most Frequent" value={v.most_frequent_contaminant ?? '\u2014'} />
        <Stat label="Total Samples" value={String(v.total_samples)} />
      </div>
      {v.top_detections.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>System</th>
              <th style={thStyle}>Contaminant</th>
              <th style={thStyle}>City</th>
              <th style={thStyle}>State</th>
            </tr>
          </thead>
          <tbody>
            {v.top_detections.map((d, i) => (
              <tr key={`pfas-${i}`}>
                <td style={tdStyle}>{d.system_name}</td>
                <td style={tdStyle}>{d.contaminant ?? '\u2014'}</td>
                <td style={tdStyle}>{d.city ?? '\u2014'}</td>
                <td style={tdStyle}>{d.state ?? '\u2014'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div style={highVisDisclaimerStyle}>
        PFAS results are screening-level monitoring data. Detection does not
        imply a health risk at reported levels.
      </div>
    </section>
  );
}

// ── Block 13: Active Weather Alerts (NWS) ─────────────────────────────────

function Block13ActiveAlerts({ block }: { block: ActiveAlertsBlock }) {
  if (block.status !== 'ok' || !block.values) {
    return (
      <section style={sectionStyle}>
        <h2 style={h2Style}>Active Weather Alerts</h2>
        <BlockNonOk block={block} />
      </section>
    );
  }
  const { alert_count, alerts } = block.values;

  const severityColor = (s: string) => {
    switch (s) {
      case 'Extreme': return '#991b1b';
      case 'Severe': return '#dc2626';
      case 'Moderate': return '#f59e0b';
      case 'Minor': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  return (
    <section style={sectionStyle}>
      <MetaLine
        cadence={block.cadence ?? 'Near-real-time'}
        tag={(block.tag as TrustTag) ?? TrustTag.Observed}
        source={block.source ?? 'NOAA NWS'}
        sourceUrl={block.source_url}
      />
      <h2 style={h2Style}>Active Weather Alerts</h2>
      {alert_count === 0 ? (
        <p style={{ color: '#16a34a', fontWeight: 500 }}>
          No active weather alerts for this area.
        </p>
      ) : (
        <div>
          {alerts.map((a, i) => (
            <div key={`nws-${i}`} style={{
              borderLeft: `4px solid ${severityColor(a.severity)}`,
              padding: '8px 12px',
              marginBottom: '8px',
              background: '#fafafa',
              borderRadius: '4px',
            }}>
              <div style={{ fontWeight: 600, color: severityColor(a.severity) }}>
                {a.event}
              </div>
              <div style={{ fontSize: '13px', color: '#475569' }}>
                {a.area_desc}
              </div>
              {a.expires && (
                <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                  Expires: {a.expires}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ── Block 12: Hazards & Disaster History ──────────────────────────────────

function Block12Hazards({ block }: { block: HazardsBlock }) {
  if (block.status !== 'ok' || !block.values) {
    return (
      <section style={sectionStyle}>
        <h2 style={h2Style}>Hazards & Disaster History</h2>
        <BlockNonOk block={block} />
      </section>
    );
  }
  const v = block.values;
  return (
    <section style={sectionStyle}>
      <MetaLine
        cadence={block.cadence ?? 'Continuous / NRT'}
        tag={(block.tag as TrustTag) ?? TrustTag.Observed}
        source={block.source ?? 'FEMA / USGS'}
        sourceUrl={block.source_url}
      />
      <h2 style={h2Style}>Hazards & Disaster History</h2>
      <div style={statsGrid}>
        <Stat label="Federal Disasters (5 yr)" value={String(v.total_disasters)} />
        <Stat label="Most Common Type" value={v.most_common_type ?? '—'} />
        <Stat label="Largest Quake (30d)"
          value={v.largest_quake_magnitude != null ? `M${v.largest_quake_magnitude}` : 'None'} />
      </div>
      {v.recent_disasters.length > 0 && (
        <>
          <h3 style={h3Style}>Recent Disaster Declarations</h3>
          <table style={tableStyle}>
            <thead><tr>
              <th style={thStyle}>Date</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Title</th>
              <th style={thStyle}>Area</th>
            </tr></thead>
            <tbody>
              {v.recent_disasters.map((d, i) => (
                <tr key={`dis-${i}`}>
                  <td style={tdStyle}>{d.declaration_date?.slice(0, 10) ?? '—'}</td>
                  <td style={tdStyle}>{d.incident_type}</td>
                  <td style={tdStyle}>{d.title}</td>
                  <td style={tdStyle}>{d.designated_area}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {v.recent_earthquakes.length > 0 && (
        <>
          <h3 style={h3Style}>Recent Earthquakes Near Metro</h3>
          <table style={tableStyle}>
            <thead><tr>
              <th style={thStyle}>Mag</th>
              <th style={thStyle}>Location</th>
              <th style={thStyle}>Depth</th>
              <th style={thStyle}>Time (UTC)</th>
            </tr></thead>
            <tbody>
              {v.recent_earthquakes.map((q, i) => (
                <tr key={`eq-${i}`}>
                  <td style={{...tdStyle, fontWeight: 600}}>M{q.magnitude}</td>
                  <td style={tdStyle}>{q.place}</td>
                  <td style={tdStyle}>{q.depth_km.toFixed(1)} km</td>
                  <td style={tdStyle}>{q.time_utc?.slice(0, 16).replace('T', ' ') ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

// ── Block 14: Coastal Conditions (NOAA CO-OPS) ───────────────────────────

function Block14Coastal({ block }: { block: CoastalBlock }) {
  if (block.status !== 'ok' || !block.values) {
    return (
      <section style={sectionStyle}>
        <h2 style={h2Style}>Coastal Conditions</h2>
        <BlockNonOk block={block} />
      </section>
    );
  }
  const v = block.values;
  return (
    <section style={sectionStyle}>
      <MetaLine
        cadence={block.cadence ?? '6-minute'}
        tag={(block.tag as TrustTag) ?? TrustTag.Observed}
        source={block.source ?? 'NOAA CO-OPS'}
        sourceUrl={block.source_url}
      />
      <h2 style={h2Style}>Coastal Conditions</h2>
      <p style={noteStyle}>{v.station_count} tide station{v.station_count !== 1 ? 's' : ''} near this metro</p>
      {v.stations.length > 0 && (
        <table style={tableStyle}>
          <thead><tr>
            <th style={thStyle}>Station</th>
            <th style={{...thStyle, textAlign: 'right'}}>Water Level (ft)</th>
            <th style={{...thStyle, textAlign: 'right'}}>Water Temp (\u00b0F)</th>
            <th style={thStyle}>Last Reading</th>
          </tr></thead>
          <tbody>
            {v.stations.map((s, i) => (
              <tr key={`coast-${i}`}>
                <td style={tdStyle}>{s.name}</td>
                <td style={{...tdStyle, textAlign: 'right'}}>{s.water_level_ft?.toFixed(2) ?? '—'}</td>
                <td style={{...tdStyle, textAlign: 'right'}}>{s.water_temp_f?.toFixed(1) ?? '—'}</td>
                <td style={tdStyle}>{s.timestamp?.replace('T', ' ').slice(0, 16) ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

// ── Block 4: Water Snapshot ───────────────────────────────────────────────

function Block4Water({ block }: { block: WaterBlock }) {
  const usgs = block.hydrology_nrt;
  const wqp = block.water_quality_discrete;
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Water Snapshot</h2>

      {/* Hydrology NRT */}
      <div style={subBlockStyle}>
        <h3 style={h3Style}>Hydrology (Near-real-time)</h3>
        {usgs.status === 'ok' && (
          <MetaLine
            cadence={usgs.cadence ?? '15-min (continuous)'}
            tag={(usgs.tag as TrustTag) ?? TrustTag.NearRealTime}
            source={usgs.source ?? 'USGS Water Data'}
            sourceUrl={usgs.source_url}
          />
        )}
        {usgs.status === 'error' && (
          <ErrorNotice error={usgs.error ?? 'Unknown error'} />
        )}
        {usgs.status === 'ok' && usgs.values && (
          <HydrologyBody values={usgs.values} />
        )}
      </div>

      {/* Water quality discrete */}
      <div style={subBlockStyle}>
        <h3 style={h3Style}>Water Quality (Discrete samples)</h3>
        {wqp.status === 'ok' && (
          <MetaLine
            cadence={wqp.cadence ?? 'discrete samples — dates vary'}
            tag={(wqp.tag as TrustTag) ?? TrustTag.Observed}
            source={wqp.source ?? 'Water Quality Portal'}
            sourceUrl={wqp.source_url}
          />
        )}
        {wqp.status === 'error' && (
          <ErrorNotice error={wqp.error ?? 'Unknown error'} />
        )}
        {wqp.status === 'ok' && wqp.values && (
          <WaterQualityBody values={wqp.values} />
        )}
      </div>

      <p style={disclaimerStyle}>⚠️ {block.disclaimer}</p>
    </section>
  );
}

function HydrologyBody({ values }: { values: UsgsWaterSummary }) {
  return (
    <>
      <p style={valueStyle}>
        {values.site_count}{' '}
        <span style={unitStyle}>streamflow sites reporting</span>
      </p>
      {values.latest_readings.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Site</th>
              <th style={thStyle}>Discharge (ft³/s)</th>
              <th style={thStyle}>Observed</th>
            </tr>
          </thead>
          <tbody>
            {values.latest_readings.slice(0, 10).map((r) => (
              <tr key={r.monitoring_location_id}>
                <td style={tdStyle}>{r.site_name}</td>
                <td style={tdStyle}>{r.value_cfs.toFixed(1)}</td>
                <td style={tdStyle}>{r.datetime_utc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function WaterQualityBody({ values }: { values: WqpSummary }) {
  return (
    <>
      <div style={statsGrid}>
        <Stat label="Samples (past year)" value={values.sample_count} />
        <Stat label="Monitoring stations" value={values.station_count} />
        <Stat label="Distinct analytes" value={values.characteristics.length} />
        <Stat
          label="Date range"
          value={
            values.earliest_sample_date && values.latest_sample_date
              ? `${values.earliest_sample_date} → ${values.latest_sample_date}`
              : '—'
          }
        />
      </div>
      {values.recent_samples.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Date</th>
              <th style={thStyle}>Station</th>
              <th style={thStyle}>Analyte</th>
              <th style={thStyle}>Value</th>
              <th style={thStyle}>Provider</th>
            </tr>
          </thead>
          <tbody>
            {values.recent_samples.slice(0, 10).map((s, i) => (
              <tr key={`${s.station_id}-${s.activity_start_date}-${i}`}>
                <td style={tdStyle}>{s.activity_start_date}</td>
                <td style={tdStyle}>{s.station_name}</td>
                <td style={tdStyle}>{s.characteristic}</td>
                <td style={tdStyle}>
                  {s.result_value !== null ? s.result_value : '—'}{' '}
                  {s.result_unit}
                </td>
                <td style={tdStyle}>{s.provider}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

// ── Block 5: Methodology ──────────────────────────────────────────────────

function Block5Methodology({ block }: { block: MethodologyBlock }) {
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Methodology & Data Limitations</h2>
      {block.sources.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Block</th>
              <th style={thStyle}>Source</th>
              <th style={thStyle}>Cadence</th>
              <th style={thStyle}>Geo scope</th>
              <th style={thStyle}>Trust</th>
              <th style={thStyle}>License</th>
            </tr>
          </thead>
          <tbody>
            {block.sources.map((s) => (
              <tr key={s.block}>
                <td style={tdStyle}>{s.block}</td>
                <td style={tdStyle}>
                  {s.source_url ? (
                    <a href={s.source_url}>{s.source}</a>
                  ) : (
                    s.source
                  )}
                </td>
                <td style={tdStyle}>{s.cadence}</td>
                <td style={tdStyle}>{s.spatial_scope}</td>
                <td style={tdStyle}>{s.tag}</td>
                <td style={tdStyle}>{s.license}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <ul style={disclaimerListStyle}>
        {block.disclaimers.map((d) => (
          <li key={d}>{d}</li>
        ))}
      </ul>
    </section>
  );
}

// ── Block 6: Related Content ──────────────────────────────────────────────

function Block6Related({
  block,
}: {
  block: { status: string; message: string };
}) {
  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Related Content</h2>
      <p style={noteStyle}>
        {block.status === 'pending'
          ? block.message
          : 'Nearby metros, fact rankings and educational guides for this area.'}
      </p>
    </section>
  );
}

// ── Shared presentational bits ────────────────────────────────────────────

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={statCard}>
      <div style={statLabel}>{label}</div>
      <div style={statValue}>{value}</div>
    </div>
  );
}

function Notes({ notes }: { notes: string[] }) {
  return (
    <ul style={notesListStyle}>
      {notes.map((n) => (
        <li key={n}>{n}</li>
      ))}
    </ul>
  );
}

function NotConfiguredNotice({ message }: { message: string }) {
  return (
    <div style={noticeStyle}>
      <strong>Data source not configured.</strong>
      <p style={{ margin: '4px 0 0', fontSize: '13px' }}>{message}</p>
    </div>
  );
}

function ErrorNotice({ error }: { error: string }) {
  return (
    <div style={noticeStyle}>
      <strong>Could not load this block.</strong>
      <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#64748b' }}>
        {error}
      </p>
    </div>
  );
}

/**
 * Renders the three non-ok block states (error / not_configured / pending)
 * shared by every Phase E.3 block.
 */
function BlockNonOk({ block }: { block: BlockBase }) {
  if (block.status === 'error') {
    return <ErrorNotice error={block.error ?? 'Unknown error'} />;
  }
  if (block.status === 'not_configured' || block.status === 'pending') {
    return <NotConfiguredNotice message={block.message ?? ''} />;
  }
  return null;
}


function AdSlot({ id }: { id: string }) {
  // Placeholder for AdSense (CLAUDE.md: between Block 1-2 and 3-4).
  return (
    <div id={id} style={adSlotStyle} aria-label="Advertisement">
      Ad slot
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────

const pageStyle: React.CSSProperties = {
  padding: '24px',
  maxWidth: '960px',
  margin: '0 auto',
  color: '#0f172a',
};

const sectionStyle: React.CSSProperties = {
  marginBottom: '32px',
  padding: '16px',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  background: '#fff',
};

const subBlockStyle: React.CSSProperties = {
  marginTop: '16px',
  paddingTop: '16px',
  borderTop: '1px dashed #e5e7eb',
};

const h1Style: React.CSSProperties = {
  margin: '0 0 4px',
  fontSize: '26px',
  fontWeight: 700,
};

const h2Style: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '18px',
  fontWeight: 600,
};

const h3Style: React.CSSProperties = {
  margin: '16px 0 8px',
  fontSize: '14px',
  fontWeight: 600,
  color: '#334155',
};

const subheadStyle: React.CSSProperties = {
  margin: '0 0 12px',
  fontSize: '13px',
  color: '#64748b',
};

const keySignalsGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: '12px',
  marginTop: '8px',
};

const keySignalCard: React.CSSProperties = {
  padding: '12px',
  border: '1px solid #e5e7eb',
  borderRadius: '6px',
  background: '#f8fafc',
};

const keySignalLabel: React.CSSProperties = {
  fontSize: '11px',
  color: '#64748b',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
};

const keySignalValue: React.CSSProperties = {
  margin: '4px 0 2px',
  fontSize: '16px',
  fontWeight: 600,
};

const keySignalSource: React.CSSProperties = {
  fontSize: '11px',
  color: '#94a3b8',
};

const valueStyle: React.CSSProperties = {
  margin: '12px 0 4px',
  fontSize: '24px',
  fontWeight: 700,
};

const unitStyle: React.CSSProperties = {
  fontSize: '13px',
  fontWeight: 500,
  color: '#64748b',
};

const asOfStyle: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '12px',
  color: '#94a3b8',
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '13px',
  marginTop: '12px',
};

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '6px 8px',
  borderBottom: '2px solid #e5e7eb',
  color: '#475569',
  fontWeight: 600,
};

const tdStyle: React.CSSProperties = {
  padding: '6px 8px',
  borderBottom: '1px solid #f1f5f9',
  color: '#334155',
};

const statsGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
  gap: '12px',
  marginTop: '12px',
};

const statCard: React.CSSProperties = {
  padding: '12px',
  border: '1px solid #e5e7eb',
  borderRadius: '6px',
  background: '#f8fafc',
};

const statLabel: React.CSSProperties = {
  fontSize: '11px',
  color: '#64748b',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
};

const statValue: React.CSSProperties = {
  marginTop: '4px',
  fontSize: '18px',
  fontWeight: 700,
};

const disclaimerStyle: React.CSSProperties = {
  marginTop: '12px',
  fontSize: '12px',
  color: '#dc2626',
};

const disclaimerListStyle: React.CSSProperties = {
  marginTop: '12px',
  paddingLeft: '18px',
  fontSize: '12px',
  color: '#64748b',
};

const noteStyle: React.CSSProperties = {
  marginTop: '12px',
  fontSize: '12px',
  color: '#64748b',
};

const notesListStyle: React.CSSProperties = {
  marginTop: '12px',
  paddingLeft: '18px',
  fontSize: '11px',
  color: '#94a3b8',
};

const noticeStyle: React.CSSProperties = {
  marginTop: '8px',
  padding: '10px 12px',
  border: '1px dashed #f59e0b',
  borderRadius: '6px',
  background: '#fffbeb',
  color: '#92400e',
  fontSize: '13px',
};

const adSlotStyle: React.CSSProperties = {
  margin: '16px 0',
  padding: '24px',
  textAlign: 'center',
  background: '#f1f5f9',
  border: '1px dashed #cbd5e1',
  borderRadius: '6px',
  color: '#94a3b8',
  fontSize: '12px',
};

const loadingStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#94a3b8',
};

const errorStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#dc2626',
};

const twoColGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
  gap: '16px',
  marginTop: '8px',
};

const cleanupListStyle: React.CSSProperties = {
  margin: '8px 0 0',
  paddingLeft: '18px',
  fontSize: '13px',
  color: '#334155',
};

const cleanupMetaStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#94a3b8',
};

const highVisDisclaimerStyle: React.CSSProperties = {
  marginTop: '16px',
  padding: '12px 14px',
  border: '1px solid #f59e0b',
  borderRadius: '6px',
  background: '#fffbeb',
  color: '#92400e',
  fontSize: '13px',
  fontWeight: 500,
  lineHeight: 1.5,
};
