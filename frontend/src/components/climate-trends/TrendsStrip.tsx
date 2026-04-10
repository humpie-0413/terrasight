import MetaLine from '../common/MetaLine';
import { TrustTag } from '../../utils/trustTags';

/**
 * Climate Trends strip — 3 cards: CO2, Global Temp Anomaly, Arctic Sea Ice.
 * CLAUDE.md Block 1층 "Climate Trends (느린 변화 카드 3개)"
 */
export default function TrendsStrip() {
  return (
    <section id="climate-trends" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', padding: '16px 24px' }}>
      <article style={cardStyle}>
        <MetaLine
          cadence="Daily + Monthly"
          tag={TrustTag.Observed}
          source="NOAA GML Mauna Loa"
          sourceUrl="https://gml.noaa.gov/ccgg/trends/"
        />
        <h3>CO₂</h3>
        <p>— ppm</p>
        {/* TODO: sparkline since 1958 */}
      </article>
      <article style={cardStyle}>
        <MetaLine
          cadence="Monthly (preliminary)"
          tag={TrustTag.NearRealTime}
          source="NOAA Climate at a Glance"
          sourceUrl="https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/"
        />
        <h3>Global Temp Anomaly</h3>
        <p>— °C</p>
        {/* TODO: sparkline since 1880 */}
      </article>
      <article style={cardStyle}>
        <MetaLine
          cadence="Daily (5-day running mean)"
          tag={TrustTag.Observed}
          source="NSIDC Sea Ice Index"
          sourceUrl="https://nsidc.org/data/seaice_index"
        />
        <h3>Arctic Sea Ice</h3>
        <p>— million km²</p>
        {/* TODO: sparkline since 1979 */}
      </article>
    </section>
  );
}

const cardStyle: React.CSSProperties = {
  padding: '16px',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  background: '#fff',
};
