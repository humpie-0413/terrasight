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
  source_id: string;
  lat: number | null;
  lon: number | null;
  in_violation: boolean;
  formal_actions_3yr: number;
  penalties_3yr_usd: number;
}

interface EchoSummary {
  total_facilities: number;
  in_violation: number;
  formal_actions_3yr: number;
  penalties_3yr_usd: number;
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
    water: WaterBlock;
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
    return (
      <article style={pageStyle}>
        <h1 style={h1Style}>Report unavailable</h1>
        <p style={errorStyle}>
          {error?.message ?? 'Unknown error'} — for slug "{cbsaSlug}".
        </p>
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

      {/* Block 3 — Regulated Facilities & Compliance */}
      <Block3Facilities block={blocks.facilities} />

      {/* AdSense slot #2 */}
      <AdSlot id="ad-2" />

      {/* Block 4 — Water Snapshot */}
      <Block4Water block={blocks.water} />

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
        <Stat label="Facilities tracked" value={values.total_facilities} />
        <Stat label="Currently in violation" value={values.in_violation} />
        <Stat
          label="Formal actions (3 yr)"
          value={values.formal_actions_3yr}
        />
        <Stat
          label="Penalties (3 yr)"
          value={`$${Math.round(values.penalties_3yr_usd).toLocaleString()}`}
        />
      </div>
      {values.top_violations.length > 0 && (
        <>
          <h3 style={h3Style}>Top facilities by enforcement activity</h3>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Facility</th>
                <th style={thStyle}>In violation</th>
                <th style={thStyle}>Formal actions (3 yr)</th>
                <th style={thStyle}>Penalties (3 yr)</th>
              </tr>
            </thead>
            <tbody>
              {values.top_violations.map((f) => (
                <tr key={f.source_id || f.name}>
                  <td style={tdStyle}>{f.name}</td>
                  <td style={tdStyle}>{f.in_violation ? '🔴 Yes' : '—'}</td>
                  <td style={tdStyle}>{f.formal_actions_3yr}</td>
                  <td style={tdStyle}>
                    ${Math.round(f.penalties_3yr_usd).toLocaleString()}
                  </td>
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
