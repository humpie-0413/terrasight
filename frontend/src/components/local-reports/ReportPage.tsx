/**
 * Local Environmental Report — 6-block layout.
 * CLAUDE.md Block 3층.
 *   Block 0: Metro Header
 *   Block 1: Air Quality (AirNow current + AirData annual trend)
 *   Block 2: Climate Change Locally (NOAA CtaG + Normals)
 *   Block 3: Regulated Facilities & Compliance (EPA ECHO)
 *   Block 4: Water Snapshot (USGS continuous + WQP discrete)
 *   Block 5: Methodology & Data Limitations
 *   Block 6: Related Content
 *
 * AdSense 배치: Block 1-2 사이, Block 3-4 사이, Block 6 내부/아래.
 */

interface ReportPageProps {
  cbsaSlug: string;
}

export default function ReportPage({ cbsaSlug }: ReportPageProps) {
  return (
    <article style={{ padding: '24px', maxWidth: '960px', margin: '0 auto' }}>
      <section>
        <h1>Local Environmental Report — {cbsaSlug}</h1>
        <p>Block 0: Metro Header (TBD)</p>
      </section>

      <section>
        <h2>Air Quality</h2>
        <p>Block 1 (TBD)</p>
      </section>

      {/* AdSense slot #1 */}

      <section>
        <h2>Climate Change Locally</h2>
        <p>Block 2 (TBD)</p>
      </section>

      <section>
        <h2>Regulated Facilities & Compliance</h2>
        <p>Block 3 (TBD)</p>
        <p style={{ fontSize: '12px', color: '#64748b' }}>
          ⚠️ Regulatory compliance ≠ environmental exposure or health risk.
        </p>
      </section>

      {/* AdSense slot #2 */}

      <section>
        <h2>Water Snapshot</h2>
        <p>Block 4 (TBD)</p>
        <p style={{ fontSize: '12px', color: '#64748b' }}>
          USGS streamflow = continuous (15-min). WQP water quality = discrete samples — dates vary.
        </p>
      </section>

      <section>
        <h2>Methodology & Data Limitations</h2>
        <p>Block 5 (TBD)</p>
      </section>

      <section>
        <h2>Related Content</h2>
        <p>Block 6 (TBD)</p>
      </section>
    </article>
  );
}
