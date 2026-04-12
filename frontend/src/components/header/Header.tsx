import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Header() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <header style={headerStyle}>
      <nav style={navStyle}>
        <Link to="/" style={logoStyle} onClick={() => setOpen(false)}>
          TerraSight
        </Link>

        <div className="desktop-nav" style={desktopLinks}>
          {NAV_ITEMS.map(({ to, label }) => (
            <Link key={to} to={to} style={{
              ...navLinkStyle,
              ...(isActive(to) ? activeLinkStyle : {}),
            }}>{label}</Link>
          ))}
        </div>

        <button
          className="hamburger-btn"
          aria-label={open ? 'Close menu' : 'Open menu'}
          style={hamburgerStyle}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? '\u2715' : '\u2630'}
        </button>
      </nav>

      {open && (
        <div style={mobileMenuStyle}>
          {NAV_ITEMS.map(({ to, label }) => (
            <Link key={to} to={to} style={{
              ...mobileLinkStyle,
              ...(isActive(to) ? { color: '#60a5fa' } : {}),
            }} onClick={() => setOpen(false)}>{label}</Link>
          ))}
        </div>
      )}
    </header>
  );
}

const NAV_ITEMS = [
  { to: '/earth-now', label: 'Earth Now' },
  { to: '/trends', label: 'Climate Trends' },
  { to: '/atlas', label: 'Atlas' },
  { to: '/reports', label: 'Local Reports' },
  { to: '/guides', label: 'Guides' },
  { to: '/rankings', label: 'Rankings' },
];

const headerStyle: React.CSSProperties = {
  position: 'sticky', top: 0, zIndex: 100,
  background: 'rgba(10, 14, 26, 0.85)',
  backdropFilter: 'blur(12px)',
  borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
};
const navStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '10px 24px', maxWidth: '1200px', margin: '0 auto',
};
const logoStyle: React.CSSProperties = {
  fontWeight: 800, fontSize: '18px', color: '#f1f5f9',
  textDecoration: 'none', letterSpacing: '-0.02em', flexShrink: 0,
};
const desktopLinks: React.CSSProperties = {
  display: 'flex', gap: '2px', alignItems: 'center',
};
const navLinkStyle: React.CSSProperties = {
  padding: '6px 12px', fontSize: '14px', color: '#94a3b8',
  textDecoration: 'none', borderRadius: '6px',
  fontFamily: 'system-ui, sans-serif', transition: 'color 0.15s, background 0.15s',
};
const activeLinkStyle: React.CSSProperties = {
  color: '#e2e8f0', background: 'rgba(59, 130, 246, 0.15)',
};
const hamburgerStyle: React.CSSProperties = {
  display: 'none', background: 'none', border: 'none',
  fontSize: '20px', cursor: 'pointer', padding: '4px 8px', color: '#e2e8f0',
};
const mobileMenuStyle: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', padding: '8px 16px 16px',
  borderTop: '1px solid rgba(51, 65, 85, 0.5)', background: 'rgba(10, 14, 26, 0.95)',
};
const mobileLinkStyle: React.CSSProperties = {
  padding: '10px 8px', fontSize: '15px', color: '#cbd5e1',
  textDecoration: 'none', textAlign: 'left', cursor: 'pointer',
  fontFamily: 'system-ui, sans-serif', borderBottom: '1px solid rgba(30, 41, 59, 0.5)',
};
