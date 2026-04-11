import { useParams, Link } from 'react-router-dom';

// ── AQI Guide data ────────────────────────────────────────────────────────────

const AQI_CATEGORIES = [
  {
    range: '0–50',
    label: 'Good',
    color: '#00e400',
    textColor: '#064e3b',
    bg: '#f0fdf4',
    description:
      'Air quality is satisfactory, and air pollution poses little or no risk.',
    actions: [
      'No precautions needed — enjoy outdoor activities.',
      'Great day to exercise outside.',
    ],
  },
  {
    range: '51–100',
    label: 'Moderate',
    color: '#ffff00',
    textColor: '#713f12',
    bg: '#fefce8',
    description:
      'Air quality is acceptable. There may be a risk for some people, particularly those who are unusually sensitive to air pollution.',
    actions: [
      'Unusually sensitive people: consider reducing prolonged outdoor exertion.',
      'Most people can continue normal outdoor activities.',
    ],
  },
  {
    range: '101–150',
    label: 'Unhealthy for Sensitive Groups',
    color: '#ff7e00',
    textColor: '#7c2d12',
    bg: '#fff7ed',
    description:
      'Members of sensitive groups may experience health effects. The general public is less likely to be affected.',
    actions: [
      'Sensitive groups (heart/lung disease, older adults, children): limit prolonged outdoor exertion.',
      'Consider moving intense activities indoors or rescheduling.',
    ],
  },
  {
    range: '151–200',
    label: 'Unhealthy',
    color: '#ff0000',
    textColor: '#7f1d1d',
    bg: '#fef2f2',
    description:
      'Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects.',
    actions: [
      'Everyone: reduce prolonged or heavy outdoor exertion.',
      'Sensitive groups: avoid prolonged outdoor exertion; consider moving indoors.',
      'Keep windows closed if air conditioning is available.',
    ],
  },
  {
    range: '201–300',
    label: 'Very Unhealthy',
    color: '#8f3f97',
    textColor: '#3b0764',
    bg: '#faf5ff',
    description:
      'Health alert: The risk of health effects is increased for everyone.',
    actions: [
      'Everyone: avoid prolonged or heavy outdoor exertion.',
      'Sensitive groups: avoid all outdoor exertion.',
      'Stay indoors with windows and doors closed.',
      'Use air purifiers indoors if available.',
    ],
  },
  {
    range: '301–500',
    label: 'Hazardous',
    color: '#7e0023',
    textColor: '#fff',
    bg: '#4a0011',
    description:
      'Health warning of emergency conditions — everyone is more likely to be affected.',
    actions: [
      'Everyone: avoid all outdoor physical activity.',
      'Stay indoors. Keep all windows and doors closed.',
      'Run air purifiers on high if available.',
      'Follow local health authority emergency guidance.',
    ],
  },
];

// ── How AQI is calculated ─────────────────────────────────────────────────────

const POLLUTANTS = [
  { name: 'PM2.5', full: 'Fine particulate matter (≤ 2.5 µm)', why: 'Penetrates deep into lungs; linked to cardiovascular and respiratory disease.' },
  { name: 'PM10', full: 'Inhalable particles (≤ 10 µm)', why: 'Can irritate airways; sourced from dust, pollen, smoke.' },
  { name: 'O₃', full: 'Ground-level ozone', why: 'Formed by chemical reactions in sunlight; irritates airways and worsens asthma.' },
  { name: 'NO₂', full: 'Nitrogen dioxide', why: 'From vehicles and power plants; worsens respiratory disease.' },
  { name: 'SO₂', full: 'Sulfur dioxide', why: 'From burning fossil fuels; irritates the respiratory system.' },
  { name: 'CO', full: 'Carbon monoxide', why: 'From incomplete combustion; reduces blood oxygen at high levels.' },
];

// ── EPA Compliance Guide ───────────────────────────────────────────────────────

function EpaComplianceGuide() {
  return (
    <main style={pageStyle}>
      <div style={breadcrumbStyle}>
        <Link to="/" style={bcrumbLinkStyle}>Home</Link>
        <span style={sepStyle}>›</span>
        <span>Guides</span>
        <span style={sepStyle}>›</span>
        <span>Understanding EPA Compliance Data</span>
      </div>
      <h1 style={h1Style}>Understanding EPA Compliance Data</h1>
      <p style={subtitleStyle}>
        EPA ECHO tracks regulatory compliance across tens of thousands of U.S. facilities.
        Here's how to read it — and what it doesn't tell you.
      </p>
      <section style={sectionStyle}>
        <h2 style={h2Style}>What Is EPA ECHO?</h2>
        <p style={bodyStyle}>
          ECHO (Enforcement and Compliance History Online) aggregates compliance data for
          facilities regulated under four major EPA programs: Clean Air Act (CAA), Clean
          Water Act (CWA), Resource Conservation and Recovery Act (RCRA), and Safe Drinking
          Water Act (SDWA). It covers permit conditions, inspection history, violations, and
          enforcement actions for over 800,000 regulated entities.
        </p>
      </section>
      <section style={sectionStyle}>
        <h2 style={h2Style}>Significant Non-Compliance (SNC)</h2>
        <p style={bodyStyle}>
          The most serious violation classification in ECHO is{' '}
          <strong>Significant Non-Compliance</strong>. A facility reaches SNC when it exceeds
          effluent or emission limits by a threshold amount, fails to submit required reports,
          or has unresolved formal enforcement actions. This site uses <code>FacSNCFlg = Y</code>{' '}
          as the violation indicator.
        </p>
        <p style={bodyStyle}>
          Non-SNC violations exist below this threshold — minor exceedances, late reports,
          and administrative issues. These appear in ECHO but are not counted in our rankings.
        </p>
      </section>
      <section style={sectionStyle}>
        <h2 style={h2Style}>Key Caveats</h2>
        <ul style={listStyle}>
          <li>
            <strong>Compliance ≠ exposure or health risk.</strong> Regulatory limits are set
            conservatively, so a violation doesn't necessarily mean nearby residents are harmed.
          </li>
          <li>
            <strong>Reporting lags.</strong> ECHO data typically lags real-world events by
            weeks to months. Facilities may have already corrected a violation before ECHO
            reflects it.
          </li>
          <li>
            <strong>Sampled, not complete.</strong> This site queries up to 500 active
            facilities per metro bounding box. Large metros have far more regulated entities.
          </li>
          <li>
            <strong>Boundary mismatch.</strong> Metro bounding boxes may include facilities
            outside the CBSA or miss edge facilities. Use ECHO directly for exact searches.
          </li>
        </ul>
      </section>
      <section style={sectionStyle}>
        <h2 style={h2Style}>Enforcement Progression</h2>
        <ul style={listStyle}>
          <li>Informal action — notice of violation, warning letter</li>
          <li>Formal administrative action — compliance order, penalty assessment</li>
          <li>Judicial action — consent decree, civil penalty, criminal referral</li>
        </ul>
        <p style={bodyStyle}>
          Most violations are resolved informally before formal action. A high violation
          count warrants closer examination but does not equal severe environmental impact.
        </p>
      </section>
      <div style={footerStyle}>
        <p style={footerTextStyle}>
          Source: EPA ECHO (echodata.epa.gov) · ECHO REST Services v2.
          For facility-level detail, visit{' '}
          <a href="https://echo.epa.gov" target="_blank" rel="noopener noreferrer" style={linkStyle}>
            echo.epa.gov
          </a>.
        </p>
        <div style={relatedStyle}>
          <strong>Related:</strong>{' '}
          <Link to="/rankings/epa-violations" style={linkStyle}>EPA Violations Ranking</Link>
          {' · '}
          <Link to="/" style={linkStyle}>Local Reports</Link>
        </div>
      </div>
    </main>
  );
}

// ── Water Quality Samples Guide ───────────────────────────────────────────────

function WaterQualitySamplesGuide() {
  const WQP_PARAMS = [
    { name: 'pH', range: '6.5–8.5', why: 'Acidity/alkalinity balance; extremes harm aquatic life and indicate pollution.' },
    { name: 'Dissolved Oxygen', range: '> 5 mg/L', why: 'Oxygen available for aquatic organisms; low DO causes fish kills.' },
    { name: 'Nitrate (NO₃)', range: '< 10 mg/L (drinking water)', why: 'From fertilizer runoff; drives algal blooms; harmful to infants at high levels.' },
    { name: 'Total Phosphorus', range: 'Waterbody-specific', why: 'Primary nutrient driver of algal blooms and eutrophication.' },
    { name: 'E. coli / Fecal Coliform', range: '< 126 CFU/100 mL (swimming)', why: 'Sewage contamination indicator; key for beach closures.' },
    { name: 'Turbidity', range: 'Site-specific', why: 'Water clarity; elevated by sediment, reduces light, clogs fish gills.' },
    { name: 'Conductance', range: 'Varies widely', why: 'Dissolved mineral content; elevated by road salt, mining, industrial discharge.' },
  ];

  return (
    <main style={pageStyle}>
      <div style={breadcrumbStyle}>
        <Link to="/" style={bcrumbLinkStyle}>Home</Link>
        <span style={sepStyle}>›</span>
        <span>Guides</span>
        <span style={sepStyle}>›</span>
        <span>How to Interpret Water Quality Samples</span>
      </div>
      <h1 style={h1Style}>How to Interpret Water Quality Samples</h1>
      <p style={subtitleStyle}>
        The Water Quality Portal (WQP) aggregates millions of water chemistry measurements
        from federal, state, and local agencies. "Discrete samples" are point-in-time
        snapshots — understanding their limits is essential for correct interpretation.
      </p>
      <section style={sectionStyle}>
        <h2 style={h2Style}>What Is the Water Quality Portal?</h2>
        <p style={bodyStyle}>
          WQP is a cooperative service of the USGS, EPA, and USDA providing unified access
          to water quality data from over 400 agencies. Data comes from three main networks:
        </p>
        <ul style={listStyle}>
          <li><strong>NWIS</strong> — USGS National Water Information System (federal)</li>
          <li><strong>STORET</strong> — EPA Storage and Retrieval (state and local)</li>
          <li><strong>STEWARDS</strong> — USDA watershed monitoring</li>
        </ul>
      </section>
      <section style={sectionStyle}>
        <h2 style={h2Style}>What Is a Discrete Sample?</h2>
        <p style={bodyStyle}>
          A discrete sample is a single measurement taken at one location, date, and time — a
          snapshot, not continuous monitoring. A station might be sampled monthly, quarterly,
          or just once. <strong>Do not interpret a single sample as a trend.</strong> Look for
          patterns across multiple dates, stations, and years before drawing conclusions.
        </p>
        <p style={bodyStyle}>
          High nitrate on one date may reflect a storm runoff event. Low dissolved oxygen
          in summer often reflects seasonal thermal stratification — not permanent pollution.
        </p>
      </section>
      <section style={sectionStyle}>
        <h2 style={h2Style}>Key Parameters</h2>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Parameter</th>
              <th style={{ ...thStyle, textAlign: 'left' }}>Typical benchmark</th>
              <th style={{ ...thStyle, textAlign: 'left' }}>Why it matters</th>
            </tr>
          </thead>
          <tbody>
            {WQP_PARAMS.map((p, i) => (
              <tr key={p.name} style={i % 2 === 0 ? rowEven : rowOdd}>
                <td style={{ ...tdC, fontWeight: 600 }}>{p.name}</td>
                <td style={tdL}>{p.range}</td>
                <td style={tdL}>{p.why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section style={sectionStyle}>
        <h2 style={h2Style}>Detection Limits and Quality Codes</h2>
        <p style={bodyStyle}>WQP results include a detection condition flag:</p>
        <ul style={listStyle}>
          <li><strong>Detected and quantified</strong> — measured above the method detection limit (MDL)</li>
          <li><strong>Not detected</strong> — below the MDL; reported as &lt; MDL, not zero</li>
          <li><strong>Present but not quantified</strong> — detected but below quantification threshold</li>
        </ul>
        <p style={bodyStyle}>
          Treat "not detected" carefully. It means the method couldn't measure at that
          concentration — not that the chemical is absent.
        </p>
      </section>
      <div style={footerStyle}>
        <p style={footerTextStyle}>
          Source: Water Quality Portal (waterqualitydata.us) · USGS NWIS · EPA STORET.
          Discrete sample dates may span decades — always check the result date field.
        </p>
        <div style={relatedStyle}>
          <strong>Related:</strong>{' '}
          <Link to="/guides/how-to-read-aqi" style={linkStyle}>How to Read an AQI Report</Link>
          {' · '}
          <Link to="/" style={linkStyle}>Local Reports</Link>
        </div>
      </div>
    </main>
  );
}

// ── Climate Normals Guide ─────────────────────────────────────────────────────

function ClimateNormalsGuide() {
  return (
    <main style={pageStyle}>
      <div style={breadcrumbStyle}>
        <Link to="/" style={bcrumbLinkStyle}>Home</Link>
        <span style={sepStyle}>›</span>
        <span>Guides</span>
        <span style={sepStyle}>›</span>
        <span>Understanding Climate Normals</span>
      </div>
      <h1 style={h1Style}>Understanding Climate Normals</h1>
      <p style={subtitleStyle}>
        Climate normals are 30-year statistical averages of temperature, precipitation, and
        other variables. They're the baseline against which any single day, month, or year
        of weather is compared.
      </p>
      <section style={sectionStyle}>
        <h2 style={h2Style}>What Is a Climate Normal?</h2>
        <p style={bodyStyle}>
          A climate normal is calculated over a WMO-standard 30-year period. The current
          standard is <strong>1991–2020</strong>, replacing 1981–2010 in 2021. Normals are
          recalculated every decade to capture shifting climate conditions.
        </p>
        <p style={bodyStyle}>
          Normals are not predictions — they describe historical typical conditions. A
          January mean normal of 32°F is the 30-year average of January means at that
          station, not a forecast for next January.
        </p>
      </section>
      <section style={sectionStyle}>
        <h2 style={h2Style}>Why the Period Matters</h2>
        <p style={bodyStyle}>
          Because global temperatures have risen, the 1991–2020 normals are generally warmer
          than 1981–2010. This has real consequences:
        </p>
        <ul style={listStyle}>
          <li>
            A temperature that was "above normal" in 2015 using the old baseline may appear
            closer to normal on the 1991–2020 baseline — the reference shifted upward.
          </li>
          <li>
            Infrastructure designed to the 1981–2010 normals (storm drains, HVAC, pipe
            burial depth) may be undersized for the current climate envelope.
          </li>
          <li>
            This site uses NOAA NCEI 1991–2020 normals — the current official standard.
          </li>
        </ul>
      </section>
      <section style={sectionStyle}>
        <h2 style={h2Style}>Temperature vs Precipitation</h2>
        <p style={bodyStyle}>
          <strong>Temperature normals</strong> report annual, monthly, and daily averages of
          maximum, minimum, and mean temperatures. Annual mean temperature characterizes
          a location's broad climate tier.
        </p>
        <p style={bodyStyle}>
          <strong>Precipitation normals</strong> measure total water equivalent (rain +
          snowmelt). Annual totals are highly variable — one standard deviation is typically
          15–25% of the mean. A dry year in a wet city can still exceed the annual total of
          a wet year in a desert city.
        </p>
      </section>
      <section style={sectionStyle}>
        <h2 style={h2Style}>Engineering Applications</h2>
        <ul style={listStyle}>
          <li><strong>Design storm depths</strong> — 10-year, 100-year return period events derived from normals-era records</li>
          <li><strong>Heating/cooling degree days</strong> — energy load estimates for HVAC sizing</li>
          <li><strong>Frost-free season length</strong> — affects agriculture, pavement design, pipe burial depth</li>
          <li><strong>Drought frequency</strong> — Palmer Drought Severity Index uses normals as the reference baseline</li>
        </ul>
      </section>
      <div style={footerStyle}>
        <p style={footerTextStyle}>
          Source: NOAA NCEI 1991–2020 U.S. Climate Normals · Published 2021.
          Data via NCEI Data Access API v1.
        </p>
        <div style={relatedStyle}>
          <strong>Related:</strong>{' '}
          <Link to="/guides/how-to-read-aqi" style={linkStyle}>How to Read an AQI Report</Link>
          {' · '}
          <Link to="/" style={linkStyle}>Local Reports</Link>
        </div>
      </div>
    </main>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function Guide() {
  const { guideSlug } = useParams<{ guideSlug: string }>();

  if (guideSlug === 'understanding-epa-compliance') return <EpaComplianceGuide />;
  if (guideSlug === 'water-quality-samples') return <WaterQualitySamplesGuide />;
  if (guideSlug === 'climate-normals') return <ClimateNormalsGuide />;

  if (guideSlug !== 'how-to-read-aqi') {
    return (
      <main style={pageStyle}>
        <Link to="/" style={backLinkStyle}>← Back to home</Link>
        <h1 style={h1Style}>Guide: {guideSlug}</h1>
        <p style={{ color: '#64748b' }}>This guide is coming soon.</p>
      </main>
    );
  }

  return (
    <main style={pageStyle}>
      {/* Breadcrumb */}
      <div style={breadcrumbStyle}>
        <Link to="/" style={bcrumbLinkStyle}>Home</Link>
        <span style={sepStyle}>›</span>
        <span>Guides</span>
        <span style={sepStyle}>›</span>
        <span>How to Read an AQI Report</span>
      </div>

      <h1 style={h1Style}>How to Read an AQI Report</h1>
      <p style={subtitleStyle}>
        The Air Quality Index (AQI) is a standardized scale that translates complex air
        pollution measurements into a single number that tells you how clean or polluted
        the air is and what health effects might be a concern.
      </p>

      {/* What is AQI */}
      <section style={sectionStyle}>
        <h2 style={h2Style}>What Is the AQI?</h2>
        <p style={bodyStyle}>
          The U.S. Environmental Protection Agency (EPA) calculates the AQI for five major
          air pollutants regulated by the Clean Air Act. The AQI runs from 0 to 500 — the
          higher the value, the greater the level of air pollution and the greater the
          health concern. An AQI of 100 corresponds to the national air quality standard for
          each pollutant.
        </p>
        <p style={bodyStyle}>
          The <strong>reported AQI</strong> for any location is the <em>highest</em> sub-index
          value across all measured pollutants. The dominant pollutant driving the index is
          always disclosed — pay attention to it, because the protective actions differ.
        </p>
      </section>

      {/* Category table */}
      <section style={sectionStyle}>
        <h2 style={h2Style}>AQI Categories</h2>
        <div style={categoryGrid}>
          {AQI_CATEGORIES.map((cat) => (
            <div key={cat.label} style={{ ...categoryCard, background: cat.bg }}>
              <div style={categoryHeader}>
                <span style={{ ...colorSwatch, background: cat.color }} />
                <div>
                  <div style={{ ...categoryLabel, color: cat.textColor === '#fff' ? cat.color : cat.textColor }}>
                    {cat.label}
                  </div>
                  <div style={categoryRange}>{cat.range}</div>
                </div>
              </div>
              <p style={categoryDesc}>{cat.description}</p>
              <ul style={actionList}>
                {cat.actions.map((a) => (
                  <li key={a} style={actionItem}>{a}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Pollutants */}
      <section style={sectionStyle}>
        <h2 style={h2Style}>Which Pollutants Are Measured?</h2>
        <p style={bodyStyle}>
          The AQI covers six criteria pollutants. Each has its own sub-index calculated from
          concentration breakpoints set by the EPA.
        </p>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Pollutant</th>
              <th style={{ ...thStyle, textAlign: 'left' }}>Full name</th>
              <th style={{ ...thStyle, textAlign: 'left' }}>Why it matters</th>
            </tr>
          </thead>
          <tbody>
            {POLLUTANTS.map((p, i) => (
              <tr key={p.name} style={i % 2 === 0 ? rowEven : rowOdd}>
                <td style={{ ...tdC, fontWeight: 700 }}>{p.name}</td>
                <td style={tdL}>{p.full}</td>
                <td style={tdL}>{p.why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Sensitive groups */}
      <section style={sectionStyle}>
        <h2 style={h2Style}>Who Are "Sensitive Groups"?</h2>
        <ul style={listStyle}>
          <li>People with heart or lung disease (asthma, COPD, heart failure)</li>
          <li>Older adults (65+)</li>
          <li>Children and teenagers</li>
          <li>People who are active outdoors — exertion increases breathing rate</li>
          <li>Pregnant individuals</li>
        </ul>
        <p style={bodyStyle}>
          If you or someone in your household falls into any of these groups, start taking
          precautions at AQI 101 (Unhealthy for Sensitive Groups) rather than waiting for
          the Unhealthy threshold.
        </p>
      </section>

      {/* Data sources */}
      <section style={sectionStyle}>
        <h2 style={h2Style}>Where Does AQI Data Come From?</h2>
        <p style={bodyStyle}>
          AQI values on this site come from{' '}
          <a href="https://www.airnow.gov" target="_blank" rel="noopener noreferrer" style={linkStyle}>
            AirNow
          </a>{' '}
          (operated by EPA, USFS, NPS, and NOAA). AirNow aggregates readings from thousands
          of regulatory monitoring stations across the U.S. and reports by <em>reporting area</em> —
          a geographic zone that may differ from city or county boundaries.
        </p>
        <p style={bodyStyle}>
          Current AQI values are updated roughly hourly. Annual trends use EPA AQS (Air
          Quality System) data which is typically released 6–12 months after the measurement
          year as part of the regulatory data certification process.
        </p>
      </section>

      {/* Footer */}
      <div style={footerStyle}>
        <p style={footerTextStyle}>
          Source: U.S. EPA AQI Basics · AirNow.gov · Last reviewed 2025.
          For official advisories, visit{' '}
          <a href="https://www.airnow.gov" target="_blank" rel="noopener noreferrer" style={linkStyle}>
            airnow.gov
          </a>.
        </p>
        <div style={relatedStyle}>
          <strong>Related:</strong>{' '}
          <Link to="/rankings/epa-violations" style={linkStyle}>EPA Violations Ranking</Link>
          {' · '}
          <Link to="/" style={linkStyle}>Local Reports</Link>
        </div>
      </div>
    </main>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: '800px',
  margin: '0 auto',
  padding: '24px',
};
const breadcrumbStyle: React.CSSProperties = {
  display: 'flex',
  gap: '6px',
  alignItems: 'center',
  fontSize: '13px',
  color: '#64748b',
  marginBottom: '20px',
  flexWrap: 'wrap',
};
const bcrumbLinkStyle: React.CSSProperties = { color: '#2563eb', textDecoration: 'none' };
const sepStyle: React.CSSProperties = { color: '#94a3b8' };
const backLinkStyle: React.CSSProperties = { color: '#2563eb', fontSize: '14px', textDecoration: 'none' };
const h1Style: React.CSSProperties = { margin: '0 0 10px', fontSize: '28px', color: '#0f172a' };
const subtitleStyle: React.CSSProperties = { margin: '0 0 28px', fontSize: '15px', color: '#475569', lineHeight: 1.7 };
const sectionStyle: React.CSSProperties = { marginBottom: '36px' };
const h2Style: React.CSSProperties = { margin: '0 0 12px', fontSize: '20px', color: '#0f172a' };
const bodyStyle: React.CSSProperties = { margin: '0 0 12px', fontSize: '14px', color: '#374151', lineHeight: 1.7 };
const categoryGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
  gap: '14px',
};
const categoryCard: React.CSSProperties = {
  padding: '16px',
  borderRadius: '8px',
  border: '1px solid rgba(0,0,0,0.06)',
};
const categoryHeader: React.CSSProperties = { display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '8px' };
const colorSwatch: React.CSSProperties = {
  width: '28px',
  height: '28px',
  borderRadius: '6px',
  flexShrink: 0,
  border: '1px solid rgba(0,0,0,0.1)',
};
const categoryLabel: React.CSSProperties = { fontWeight: 700, fontSize: '15px' };
const categoryRange: React.CSSProperties = { fontSize: '12px', color: '#64748b', marginTop: '2px' };
const categoryDesc: React.CSSProperties = { margin: '0 0 8px', fontSize: '13px', color: '#374151', lineHeight: 1.6 };
const actionList: React.CSSProperties = { margin: 0, paddingLeft: '18px' };
const actionItem: React.CSSProperties = { fontSize: '12px', color: '#475569', marginBottom: '4px', lineHeight: 1.5 };
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: '14px' };
const thStyle: React.CSSProperties = {
  padding: '10px 12px',
  background: '#f1f5f9',
  borderBottom: '2px solid #e2e8f0',
  fontWeight: 600,
  color: '#374151',
  textAlign: 'center',
};
const rowEven: React.CSSProperties = { background: '#fff' };
const rowOdd: React.CSSProperties = { background: '#f8fafc' };
const tdC: React.CSSProperties = { padding: '10px 12px', textAlign: 'center', borderBottom: '1px solid #e2e8f0' };
const tdL: React.CSSProperties = { padding: '10px 12px', borderBottom: '1px solid #e2e8f0', color: '#374151', lineHeight: 1.5 };
const listStyle: React.CSSProperties = { margin: '0 0 12px', paddingLeft: '20px', fontSize: '14px', color: '#374151', lineHeight: 1.7 };
const linkStyle: React.CSSProperties = { color: '#2563eb' };
const footerStyle: React.CSSProperties = { marginTop: '32px', paddingTop: '16px', borderTop: '1px solid #e5e7eb' };
const footerTextStyle: React.CSSProperties = { margin: '0 0 8px', fontSize: '12px', color: '#94a3b8' };
const relatedStyle: React.CSSProperties = { fontSize: '13px', color: '#64748b' };
