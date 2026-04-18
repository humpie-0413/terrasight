const ctaLinkStyle = {
  display: 'inline-block',
  padding: '10px 20px',
  margin: '6px',
  background: '#1e293b',
  color: '#22c55e',
  borderRadius: '6px',
  textDecoration: 'none',
  fontWeight: 600,
} as const;

export function GlobeMobileFallback() {
  return (
    <div
      style={{
        width: '100%',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0f172a',
        color: '#e2e8f0',
        padding: '32px 24px',
        textAlign: 'center',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1
        style={{
          fontSize: '22px',
          fontWeight: 700,
          margin: '0 0 16px',
          lineHeight: 1.3,
        }}
      >
        Earth Now is desktop-optimized
      </h1>
      <p
        style={{
          fontSize: '14px',
          lineHeight: 1.6,
          maxWidth: '440px',
          margin: '0 0 24px',
          color: '#cbd5e1',
        }}
      >
        The 3D globe uses CesiumJS WebGL rendering, which is best experienced
        on a desktop browser with a pointer device. You can still explore
        TerraSight from here:
      </p>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <a href="/" style={ctaLinkStyle}>
          Home
        </a>
        <a href="/reports" style={ctaLinkStyle}>
          Local Reports
        </a>
        <a href="/atlas" style={ctaLinkStyle}>
          Environmental Data Atlas
        </a>
      </div>
    </div>
  );
}
