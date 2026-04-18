import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Header() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const isGlobe = location.pathname === '/';

  const isActive = (path: string) => location.pathname === path || location.pathname.startsWith(path + '/');

  // On globe page: hide "Earth Now" since user is already there
  const navItems = isGlobe ? NAV_ITEMS.filter((i) => i.to !== '/earth-now') : NAV_ITEMS;

  return (
    <header style={isGlobe ? headerTransparentStyle : headerStyle}>
      <nav style={navStyle}>
        <Link to="/" style={logoStyle} onClick={() => setOpen(false)}>
          TerraSight
        </Link>

        <div className="desktop-nav" style={desktopLinks}>
          {navItems.map(({ to, label }) => (
            <Link key={to} to={to} style={{
              ...navLinkStyle,
              ...(isGlobe ? navLinkGlobeStyle : {}),
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
        <div style={isGlobe ? mobileMenuGlobeStyle : mobileMenuStyle}>
          {navItems.map(({ to, label }) => (
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
const headerTransparentStyle: React.CSSProperties = {
  position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
  background: 'transparent',
  borderBottom: 'none',
  pointerEvents: 'auto',
};
const navLinkGlobeStyle: React.CSSProperties = {
  background: 'rgba(10,14,26,0.5)',
  backdropFilter: 'blur(8px)',
  borderRadius: '16px',
  border: '1px solid rgba(51,65,85,0.3)',
  padding: '5px 14px',
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
const mobileMenuGlobeStyle: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', padding: '8px 16px 16px',
  background: 'rgba(10, 14, 26, 0.92)', backdropFilter: 'blur(12px)',
  borderRadius: '0 0 12px 12px',
};
const mobileLinkStyle: React.CSSProperties = {
  padding: '10px 8px', fontSize: '15px', color: '#cbd5e1',
  textDecoration: 'none', textAlign: 'left', cursor: 'pointer',
  fontFamily: 'system-ui, sans-serif', borderBottom: '1px solid rgba(30, 41, 59, 0.5)',
};
