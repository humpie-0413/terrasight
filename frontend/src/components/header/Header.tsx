import { useState } from 'react';
import { Link } from 'react-router-dom';

/**
 * Site-wide header with responsive hamburger menu.
 *
 * Nav targets:
 *   Earth Now      → /earth-now
 *   Climate Trends → /trends
 *   Atlas          → /atlas
 *   Local Reports  → /reports
 *   Guides         → /guides
 *   Rankings       → /rankings
 */
export default function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header style={headerStyle}>
      <nav style={navStyle}>
        {/* Logo */}
        <Link to="/" style={logoStyle} onClick={() => setOpen(false)}>
          TerraSight
        </Link>

        {/* Desktop links */}
        <div style={desktopLinks}>
          <Link to="/earth-now" style={navLinkStyle}>Earth Now</Link>
          <Link to="/trends" style={navLinkStyle}>Climate Trends</Link>
          <Link to="/atlas" style={navLinkStyle}>Atlas</Link>
          <Link to="/reports" style={navLinkStyle}>Local Reports</Link>
          <Link to="/guides" style={navLinkStyle}>Guides</Link>
          <Link to="/rankings" style={navLinkStyle}>Rankings</Link>
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
          <Link to="/earth-now" style={mobileLinkStyle} onClick={() => setOpen(false)}>Earth Now</Link>
          <Link to="/trends" style={mobileLinkStyle} onClick={() => setOpen(false)}>Climate Trends</Link>
          <Link to="/atlas" style={mobileLinkStyle} onClick={() => setOpen(false)}>Atlas</Link>
          <Link to="/reports" style={mobileLinkStyle} onClick={() => setOpen(false)}>Local Reports</Link>
          <Link to="/guides" style={mobileLinkStyle} onClick={() => setOpen(false)}>Guides</Link>
          <Link to="/rankings" style={mobileLinkStyle} onClick={() => setOpen(false)}>Rankings</Link>
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
