import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

/**
 * Site-wide header with responsive hamburger menu.
 *
 * Nav targets:
 *   Earth Now     → / (home, scrolls to #earth-now)
 *   Climate Trends → / (home, scrolls to #climate-trends)
 *   Atlas          → /atlas
 *   Local Reports  → / (home, scrolls to #local-reports)
 *   Guides         → /guides/how-to-read-aqi
 *   Rankings       → /rankings/pm25
 */
export default function Header() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const scrollTo = (id: string) => {
    setOpen(false);
    if (window.location.pathname !== '/') {
      navigate('/');
      // give the page a tick to mount before scrolling
      setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }), 80);
    } else {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header style={headerStyle}>
      <nav style={navStyle}>
        {/* Logo */}
        <Link to="/" style={logoStyle} onClick={() => setOpen(false)}>
          EarthPulse
        </Link>

        {/* Desktop links */}
        <div style={desktopLinks}>
          <button style={navBtnStyle} onClick={() => scrollTo('earth-now')}>Earth Now</button>
          <button style={navBtnStyle} onClick={() => scrollTo('climate-trends')}>Climate Trends</button>
          <Link to="/atlas" style={navLinkStyle}>Atlas</Link>
          <button style={navBtnStyle} onClick={() => scrollTo('local-reports')}>Local Reports</button>
          <Link to="/guides/how-to-read-aqi" style={navLinkStyle}>Guides</Link>
          <Link to="/rankings/pm25" style={navLinkStyle}>Rankings</Link>
        </div>

        {/* Hamburger button (mobile only) */}
        <button
          aria-label={open ? 'Close menu' : 'Open menu'}
          style={hamburgerStyle}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? '✕' : '☰'}
        </button>
      </nav>

      {/* Mobile dropdown */}
      {open && (
        <div style={mobileMenuStyle}>
          <button style={mobileLinkStyle} onClick={() => scrollTo('earth-now')}>Earth Now</button>
          <button style={mobileLinkStyle} onClick={() => scrollTo('climate-trends')}>Climate Trends</button>
          <Link to="/atlas" style={mobileLinkStyle} onClick={() => setOpen(false)}>Atlas</Link>
          <button style={mobileLinkStyle} onClick={() => scrollTo('local-reports')}>Local Reports</button>
          <Link to="/guides/how-to-read-aqi" style={mobileLinkStyle} onClick={() => setOpen(false)}>Guides</Link>
          <Link to="/rankings/pm25" style={mobileLinkStyle} onClick={() => setOpen(false)}>Rankings</Link>
        </div>
      )}
    </header>
  );
}

const headerStyle: React.CSSProperties = {
  position: 'sticky',
  top: 0,
  zIndex: 100,
  background: '#fff',
  borderBottom: '1px solid #e5e7eb',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
};
const navStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '10px 24px',
  maxWidth: '1200px',
  margin: '0 auto',
};
const logoStyle: React.CSSProperties = {
  fontWeight: 800,
  fontSize: '18px',
  color: '#0f172a',
  textDecoration: 'none',
  letterSpacing: '-0.02em',
  flexShrink: 0,
};
const desktopLinks: React.CSSProperties = {
  display: 'flex',
  gap: '4px',
  alignItems: 'center',
  // hide on mobile via inline media — we handle visibility via JS state
  // (full CSS breakpoints require a stylesheet; keep it simple here)
};
const navLinkStyle: React.CSSProperties = {
  padding: '6px 10px',
  fontSize: '14px',
  color: '#374151',
  textDecoration: 'none',
  borderRadius: '6px',
  fontFamily: 'system-ui, sans-serif',
};
const navBtnStyle: React.CSSProperties = {
  padding: '6px 10px',
  fontSize: '14px',
  color: '#374151',
  background: 'none',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontFamily: 'system-ui, sans-serif',
};
const hamburgerStyle: React.CSSProperties = {
  display: 'none',   // shown via CSS @media in the head — here as fallback
  background: 'none',
  border: 'none',
  fontSize: '20px',
  cursor: 'pointer',
  padding: '4px 8px',
  color: '#374151',
};
const mobileMenuStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  padding: '8px 16px 16px',
  borderTop: '1px solid #f1f5f9',
  background: '#fff',
};
const mobileLinkStyle: React.CSSProperties = {
  padding: '10px 8px',
  fontSize: '15px',
  color: '#0f172a',
  textDecoration: 'none',
  background: 'none',
  border: 'none',
  textAlign: 'left',
  cursor: 'pointer',
  fontFamily: 'system-ui, sans-serif',
  borderBottom: '1px solid #f1f5f9',
};
