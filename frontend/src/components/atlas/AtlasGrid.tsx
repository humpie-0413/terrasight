import { Link } from 'react-router-dom';

/**
 * Environmental Data Atlas — 환경공학 전공 기준 8개 카테고리 그리드.
 * CLAUDE.md Block 2층.
 */
const CATEGORIES = [
  { slug: 'air', title: 'Air & Atmosphere' },
  { slug: 'water', title: 'Water Quality, Drinking Water & Wastewater' },
  { slug: 'hydrology', title: 'Hydrology & Floods' },
  { slug: 'coast-ocean', title: 'Coast & Ocean' },
  { slug: 'soil-land', title: 'Soil, Land & Site Condition' },
  { slug: 'waste', title: 'Waste & Materials' },
  { slug: 'emissions', title: 'Emissions, Energy & Facilities' },
  { slug: 'climate-hazards', title: 'Climate, Hazards & Exposure' },
];

export default function AtlasGrid() {
  return (
    <section style={{ padding: '24px' }}>
      <h2>Explore the Atlas</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        {CATEGORIES.map((c) => (
          <Link key={c.slug} to={`/atlas/${c.slug}`} style={cardStyle}>
            <h3>{c.title}</h3>
          </Link>
        ))}
      </div>
    </section>
  );
}

const cardStyle: React.CSSProperties = {
  display: 'block',
  padding: '16px',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  textDecoration: 'none',
  color: 'inherit',
};
