import { Link } from 'react-router-dom';

export default function Header() {
  return (
    <header style={{ padding: '12px 24px', borderBottom: '1px solid #e5e7eb' }}>
      <nav style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <Link to="/" style={{ fontWeight: 700 }}>EarthPulse</Link>
        <Link to="/#earth-now">Earth Now</Link>
        <Link to="/#climate-trends">Climate Trends</Link>
        <Link to="/atlas/air">Atlas</Link>
        <Link to="/reports">Local Reports</Link>
        <Link to="/guides/how-to-read-aqi">Guides</Link>
        <Link to="/rankings/pm25">Rankings</Link>
      </nav>
    </header>
  );
}
