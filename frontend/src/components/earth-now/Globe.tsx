import { useEffect, useMemo, useRef, useState } from 'react';
import GlobeGL, { type GlobeMethods } from 'react-globe.gl';

import MetaLine from '../common/MetaLine';
import { TrustTag } from '../../utils/trustTags';
import { useApi } from '../../hooks/useApi';

/**
 * Earth Now globe — NASA GIBS BlueMarble base + FIRMS fire hotspot overlay.
 *
 * CLAUDE.md 1층 spec:
 *   - base: NASA GIBS BlueMarble_ShadedRelief_Bathymetry (UI label "Natural Earth")
 *   - default on: Natural Earth + Fires
 *   - layer rule: 1 continuous field + 1 event overlay at a time (MVP: Fires only)
 *   - trust badge next to each layer (🟢 observed, NRT)
 *
 * Library choice (2026-04-10):
 *   Picked react-globe.gl over Cesium for MVP.
 *   - single-package install, no static-asset copying (Cesium needs
 *     vite-plugin-cesium + Workers/Assets/ThirdParty mirrored into public/)
 *   - ~700KB gz vs Cesium's 3-5MB minimum
 *   - declarative pointsData overlay; Cesium requires Entity plumbing
 *   - tradeoff: no WMTS tile streaming — fine for a static BlueMarble base,
 *     revisit if we need daily-updating tiled imagery (MODIS true color etc.)
 */

// NASA GIBS WMS GetMap — single equirectangular JPEG for the BlueMarble base.
// Verified 2026-04-10: returns image/jpeg with CORS `Access-Control-Allow-Origin: *`.
const GIBS_BLUEMARBLE_URL =
  'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
  '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1' +
  '&LAYERS=BlueMarble_ShadedRelief_Bathymetry' +
  '&STYLES=&FORMAT=image/jpeg&SRS=EPSG:4326' +
  '&BBOX=-180,-90,180,90&WIDTH=2048&HEIGHT=1024';

interface FireHotspot {
  lat: number;
  lon: number;
  brightness: number;
  frp: number;
  confidence: string;
  acq_date: string;
  acq_time: string;
  daynight: string;
}

interface FiresResponse {
  source: string;
  source_url: string;
  cadence: string;
  tag: string;
  count: number;
  total_24h?: number;
  configured: boolean;
  message?: string;
  fires: FireHotspot[];
}

export default function Globe() {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [dims, setDims] = useState({ width: 640, height: 520 });
  const [firesOn, setFiresOn] = useState(true);

  const { data: firesData, loading: firesLoading } =
    useApi<FiresResponse>('/earth-now/fires');

  // Responsive sizing — match parent container width.
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const observer = new ResizeObserver(() => {
      setDims({ width: el.clientWidth, height: el.clientHeight });
    });
    observer.observe(el);
    setDims({ width: el.clientWidth, height: el.clientHeight });
    return () => observer.disconnect();
  }, []);

  // Auto-rotate (slow) + nice initial camera position.
  useEffect(() => {
    if (!globeRef.current) return;
    const controls = globeRef.current.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controls.enableZoom = true;
    globeRef.current.pointOfView({ lat: 15, lng: 0, altitude: 2.3 }, 0);
  }, []);

  const points = useMemo(() => {
    if (!firesOn || !firesData?.fires) return [];
    return firesData.fires;
  }, [firesOn, firesData]);

  return (
    <div
      id="earth-now"
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '520px',
        background: '#0b1120',
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    >
      <GlobeGL
        ref={globeRef}
        width={dims.width}
        height={dims.height}
        globeImageUrl={GIBS_BLUEMARBLE_URL}
        backgroundColor="#0b1120"
        showAtmosphere={true}
        atmosphereColor="#88aaff"
        atmosphereAltitude={0.18}
        pointsData={points}
        pointLat={(d: object) => (d as FireHotspot).lat}
        pointLng={(d: object) => (d as FireHotspot).lon}
        pointColor={() => '#ff3d00'}
        pointAltitude={(d: object) => pointAltitude(d as FireHotspot)}
        pointRadius={(d: object) => pointRadius(d as FireHotspot)}
        pointResolution={4}
        pointLabel={(d: object) => {
          const f = d as FireHotspot;
          return `
            <div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;
                 border:1px solid #475569;border-radius:4px;font-size:11px;
                 font-family:system-ui,sans-serif;">
              <div><b>FIRMS hotspot</b></div>
              <div>${f.acq_date} ${f.acq_time} UTC (${f.daynight === 'D' ? 'day' : 'night'})</div>
              <div>FRP: ${f.frp.toFixed(1)} MW · confidence: ${f.confidence || '—'}</div>
              <div>${f.lat.toFixed(2)}°, ${f.lon.toFixed(2)}°</div>
            </div>
          `;
        }}
      />

      {/* Overlay controls */}
      <div style={headerStyle}>
        <MetaLine
          cadence="NRT ~3h"
          tag={TrustTag.Observed}
          source="NASA FIRMS / NASA GIBS"
          sourceUrl="https://firms.modaps.eosdis.nasa.gov/"
        />
      </div>

      <div style={layerToggleStyle}>
        <button
          type="button"
          onClick={() => setFiresOn((v) => !v)}
          style={{
            ...toggleBtnStyle,
            background: firesOn ? '#dc2626' : '#1e293b',
            color: firesOn ? '#fff' : '#94a3b8',
            borderColor: firesOn ? '#dc2626' : '#334155',
          }}
          aria-pressed={firesOn}
        >
          🔥 Fires
          {firesData && ` (${firesData.count})`}
        </button>
      </div>

      {/* Status line: loading / key-missing warning */}
      {(firesLoading || (firesData && !firesData.configured)) && (
        <div style={statusLineStyle}>
          {firesLoading
            ? 'Loading FIRMS hotspots…'
            : 'FIRMS_MAP_KEY not configured — fire layer disabled. See README.'}
        </div>
      )}
    </div>
  );
}

/**
 * Scale FRP (fire radiative power, MW) → globe point radius.
 * Log scale keeps a single massive wildfire from dominating the view.
 */
function pointRadius(f: FireHotspot): number {
  const frp = Math.max(f.frp, 1);
  return 0.15 + Math.log10(frp) * 0.18;
}

/**
 * Lift hotter fires slightly off the surface so they aren't occluded
 * by terrain wrinkles in the base texture. Also purely aesthetic.
 */
function pointAltitude(f: FireHotspot): number {
  const frp = Math.max(f.frp, 1);
  return 0.005 + Math.min(Math.log10(frp) * 0.008, 0.04);
}

const headerStyle: React.CSSProperties = {
  position: 'absolute',
  top: 12,
  left: 12,
  background: 'rgba(11, 17, 32, 0.72)',
  padding: '6px 10px',
  borderRadius: '6px',
  backdropFilter: 'blur(4px)',
  pointerEvents: 'none',
};

const layerToggleStyle: React.CSSProperties = {
  position: 'absolute',
  top: 12,
  right: 12,
  display: 'flex',
  gap: '8px',
};

const toggleBtnStyle: React.CSSProperties = {
  padding: '6px 10px',
  fontSize: '12px',
  fontWeight: 600,
  border: '1px solid',
  borderRadius: '6px',
  cursor: 'pointer',
  fontFamily: 'system-ui, sans-serif',
};

const statusLineStyle: React.CSSProperties = {
  position: 'absolute',
  bottom: 12,
  left: 12,
  right: 12,
  background: 'rgba(11, 17, 32, 0.78)',
  color: '#e2e8f0',
  padding: '6px 10px',
  borderRadius: '6px',
  fontSize: '11px',
  fontFamily: 'system-ui, sans-serif',
};
