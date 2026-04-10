import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import GlobeGL, { type GlobeMethods } from 'react-globe.gl';

import MetaLine from '../common/MetaLine';
import { TrustTag } from '../../utils/trustTags';
import { useApi } from '../../hooks/useApi';

/**
 * Earth Now globe — NASA GIBS BlueMarble base + multiple data layers.
 *
 * CLAUDE.md 1층 spec:
 *   - base: NASA GIBS BlueMarble_ShadedRelief_Bathymetry
 *   - layer rule: 1 continuous field + 1 event overlay active at a time
 *   - trust badge next to each layer (🟢 observed, NRT, etc.)
 *
 * Layer topology (2026-04-10):
 *   event (independent toggle):
 *     - Fires       → NASA FIRMS, pointsData (red dots, log-scaled FRP)
 *   continuous (mutually exclusive, at most one ON):
 *     - Ocean Heat  → NOAA OISST, hexBinPointsData (cold→warm color ramp)
 *     - Smoke       → CAMS forecast — DISABLED PLACEHOLDER (Copernicus account, P1)
 *     - Air Monitors → OpenAQ PM2.5, labelsData (EPA AQI color bands)
 *
 * The globe is a controlled component — parent (Home) owns layer state so
 * the Story Panel can call `globeHandleRef.flyTo(...)` and swap layers
 * when the user clicks "Explore on Globe".
 */

// NASA GIBS WMS GetMap — single equirectangular JPEG for the BlueMarble base.
const GIBS_BLUEMARBLE_URL =
  'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
  '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1' +
  '&LAYERS=BlueMarble_ShadedRelief_Bathymetry' +
  '&STYLES=&FORMAT=image/jpeg&SRS=EPSG:4326' +
  '&BBOX=-180,-90,180,90&WIDTH=2048&HEIGHT=1024';

// --- Types --------------------------------------------------------------

export type ContinuousLayer = 'ocean-heat' | 'smoke' | 'air-monitors' | null;

export interface GlobeHandle {
  flyTo: (lat: number, lng: number, altitude?: number) => void;
}

interface GlobeProps {
  firesOn: boolean;
  onToggleFires: (on: boolean) => void;
  continuousLayer: ContinuousLayer;
  onSetContinuousLayer: (layer: ContinuousLayer) => void;
}

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
  count: number;
  configured: boolean;
  message?: string;
  fires: FireHotspot[];
}

interface SstPoint {
  lat: number;
  lon: number;
  sst_c: number;
}
interface SstResponse {
  count: number;
  configured: boolean;
  stats: { min_c: number | null; max_c: number | null; mean_c: number | null };
  points: SstPoint[];
}

interface AirMonitor {
  lat: number;
  lon: number;
  pm25: number;
  location_name: string;
  datetime_utc: string;
  country: string | null;
}
interface AirMonitorsResponse {
  count: number;
  configured: boolean;
  message?: string;
  monitors: AirMonitor[];
}

// --- Component ----------------------------------------------------------

const Globe = forwardRef<GlobeHandle, GlobeProps>(function Globe(
  { firesOn, onToggleFires, continuousLayer, onSetContinuousLayer },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [dims, setDims] = useState({ width: 640, height: 520 });

  // Fetch all three datasets on mount — total payload ~500KB, acceptable.
  const { data: firesData, loading: firesLoading } =
    useApi<FiresResponse>('/earth-now/fires');
  const { data: sstData, loading: sstLoading } =
    useApi<SstResponse>('/earth-now/sst');
  const { data: airData, loading: airLoading } =
    useApi<AirMonitorsResponse>('/earth-now/air-monitors');

  // Responsive sizing
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

  // Initial camera + auto-rotate
  useEffect(() => {
    if (!globeRef.current) return;
    const controls = globeRef.current.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controls.enableZoom = true;
    globeRef.current.pointOfView({ lat: 15, lng: 0, altitude: 2.3 }, 0);
  }, []);

  // Expose imperative flyTo() to the parent (Story Panel uses this).
  useImperativeHandle(
    ref,
    () => ({
      flyTo: (lat: number, lng: number, altitude = 1.8) => {
        if (!globeRef.current) return;
        // Pause auto-rotate during a commanded flight so the view lands
        // at the requested coordinates instead of immediately spinning off.
        const controls = globeRef.current.controls();
        controls.autoRotate = false;
        globeRef.current.pointOfView({ lat, lng, altitude }, 1500);
      },
    }),
    [],
  );

  // --- Memoized overlay datasets -----------------------------------------

  const firePoints = useMemo<FireHotspot[]>(
    () => (firesOn && firesData?.fires ? firesData.fires : []),
    [firesOn, firesData],
  );

  const sstPoints = useMemo<SstPoint[]>(
    () =>
      continuousLayer === 'ocean-heat' && sstData?.points ? sstData.points : [],
    [continuousLayer, sstData],
  );

  const airPoints = useMemo<AirMonitor[]>(
    () =>
      continuousLayer === 'air-monitors' && airData?.monitors
        ? airData.monitors
        : [],
    [continuousLayer, airData],
  );

  // --- Status + meta -----------------------------------------------------

  const activeMeta = useMemo(() => {
    if (continuousLayer === 'ocean-heat') {
      return {
        cadence: 'Daily',
        tag: TrustTag.Observed,
        source: 'NOAA OISST v2.1',
        sourceUrl: 'https://coralreefwatch.noaa.gov/product/5km/',
      };
    }
    if (continuousLayer === 'air-monitors') {
      return {
        cadence: 'Varies',
        tag: TrustTag.Observed,
        source: 'OpenAQ',
        sourceUrl: 'https://openaq.org/',
      };
    }
    // Default: show Fires meta (always the "active" event overlay).
    return {
      cadence: 'NRT ~3h',
      tag: TrustTag.Observed,
      source: 'NASA FIRMS / NASA GIBS',
      sourceUrl: 'https://firms.modaps.eosdis.nasa.gov/',
    };
  }, [continuousLayer]);

  const statusMessage = useMemo(() => {
    const loading =
      firesLoading ||
      (continuousLayer === 'ocean-heat' && sstLoading) ||
      (continuousLayer === 'air-monitors' && airLoading);
    if (loading) return 'Loading…';

    if (firesData && !firesData.configured) {
      return 'FIRMS_MAP_KEY not configured — fire layer disabled. See .env.example.';
    }
    if (
      continuousLayer === 'air-monitors' &&
      airData &&
      !airData.configured
    ) {
      return 'OPENAQ_API_KEY not configured — air monitors disabled. See .env.example.';
    }
    return null;
  }, [
    firesLoading,
    sstLoading,
    airLoading,
    continuousLayer,
    firesData,
    airData,
  ]);

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
        // --- Fires (pointsData, event overlay) ---
        pointsData={firePoints}
        pointLat={(d: object) => (d as FireHotspot).lat}
        pointLng={(d: object) => (d as FireHotspot).lon}
        pointColor={() => '#ff3d00'}
        pointAltitude={(d: object) => firePointAltitude(d as FireHotspot)}
        pointRadius={(d: object) => firePointRadius(d as FireHotspot)}
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
        // --- Ocean Heat (hexBinPointsData, continuous field) ---
        hexBinPointsData={sstPoints}
        hexBinPointLat={(d: object) => (d as SstPoint).lat}
        hexBinPointLng={(d: object) => (d as SstPoint).lon}
        hexBinPointWeight={(d: object) => (d as SstPoint).sst_c}
        hexBinResolution={3}
        hexAltitude={0.008}
        hexTopColor={(d: { sumWeight: number; points: object[] }) =>
          sstColor(d.sumWeight / Math.max(d.points.length, 1))
        }
        hexSideColor={(d: { sumWeight: number; points: object[] }) =>
          sstColor(d.sumWeight / Math.max(d.points.length, 1))
        }
        hexBinMerge={false}
        hexLabel={(d: { sumWeight: number; points: object[] }) => {
          const mean = d.sumWeight / Math.max(d.points.length, 1);
          return `
            <div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;
                 border:1px solid #475569;border-radius:4px;font-size:11px;
                 font-family:system-ui,sans-serif;">
              <div><b>Ocean Heat</b></div>
              <div>${mean.toFixed(1)}°C (${d.points.length} grid cell${d.points.length === 1 ? '' : 's'})</div>
            </div>
          `;
        }}
        // --- Air monitors (labelsData with dot rendering) ---
        labelsData={airPoints}
        labelLat={(d: object) => (d as AirMonitor).lat}
        labelLng={(d: object) => (d as AirMonitor).lon}
        labelText={() => ''}
        labelDotRadius={0.25}
        labelDotOrientation={() => 'top'}
        labelColor={(d: object) => pm25Color((d as AirMonitor).pm25)}
        labelResolution={2}
        labelLabel={(d: object) => {
          const m = d as AirMonitor;
          return `
            <div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;
                 border:1px solid #475569;border-radius:4px;font-size:11px;
                 font-family:system-ui,sans-serif;max-width:240px;">
              <div><b>${m.location_name}</b>${m.country ? ` · ${m.country}` : ''}</div>
              <div>PM2.5: ${m.pm25.toFixed(1)} µg/m³</div>
              <div style="color:#94a3b8;">${m.datetime_utc || '—'}</div>
            </div>
          `;
        }}
      />

      {/* Overlay: active-layer meta */}
      <div style={headerStyle}>
        <MetaLine
          cadence={activeMeta.cadence}
          tag={activeMeta.tag}
          source={activeMeta.source}
          sourceUrl={activeMeta.sourceUrl}
        />
      </div>

      {/* Overlay: layer toggles (top-right) */}
      <div style={layerToggleStyle}>
        <LayerBtn
          label={`🔥 Fires${firesData ? ` (${firesData.count})` : ''}`}
          active={firesOn}
          onClick={() => onToggleFires(!firesOn)}
          activeColor="#dc2626"
        />
        <LayerBtn
          label={`🌊 Ocean Heat${sstData ? ` (${sstData.count})` : ''}`}
          active={continuousLayer === 'ocean-heat'}
          onClick={() =>
            onSetContinuousLayer(
              continuousLayer === 'ocean-heat' ? null : 'ocean-heat',
            )
          }
          activeColor="#0284c7"
        />
        <LayerBtn
          label="💨 Smoke"
          active={false}
          onClick={() => {}}
          activeColor="#f97316"
          disabled
          title="CAMS forecast — Copernicus ADS account required (P1)"
        />
        <LayerBtn
          label={`🏭 Air Monitors${airData && airData.configured ? ` (${airData.count})` : ''}`}
          active={continuousLayer === 'air-monitors'}
          onClick={() =>
            onSetContinuousLayer(
              continuousLayer === 'air-monitors' ? null : 'air-monitors',
            )
          }
          activeColor="#ca8a04"
          disabled={airData ? !airData.configured : false}
          title={
            airData && !airData.configured
              ? 'OPENAQ_API_KEY not configured'
              : undefined
          }
        />
      </div>

      {/* Status line */}
      {statusMessage && <div style={statusLineStyle}>{statusMessage}</div>}
    </div>
  );
});

export default Globe;

// --- Helpers ------------------------------------------------------------

function firePointRadius(f: FireHotspot): number {
  const frp = Math.max(f.frp, 1);
  return 0.15 + Math.log10(frp) * 0.18;
}
function firePointAltitude(f: FireHotspot): number {
  const frp = Math.max(f.frp, 1);
  return 0.005 + Math.min(Math.log10(frp) * 0.008, 0.04);
}

/**
 * SST color ramp (°C) — cold to warm.
 * -2 → deep blue, 5 → teal, 15 → green, 22 → orange, 30+ → red.
 */
function sstColor(c: number): string {
  const stops: Array<[number, [number, number, number]]> = [
    [-2, [8, 48, 107]],
    [5, [65, 182, 196]],
    [15, [199, 233, 180]],
    [22, [253, 174, 97]],
    [30, [179, 0, 0]],
  ];
  if (c <= stops[0][0]) return rgb(stops[0][1]);
  if (c >= stops[stops.length - 1][0])
    return rgb(stops[stops.length - 1][1]);
  for (let i = 0; i < stops.length - 1; i++) {
    const [c1, rgb1] = stops[i];
    const [c2, rgb2] = stops[i + 1];
    if (c >= c1 && c <= c2) {
      const t = (c - c1) / (c2 - c1);
      return rgb([
        Math.round(rgb1[0] + (rgb2[0] - rgb1[0]) * t),
        Math.round(rgb1[1] + (rgb2[1] - rgb1[1]) * t),
        Math.round(rgb1[2] + (rgb2[2] - rgb1[2]) * t),
      ]);
    }
  }
  return rgb(stops[0][1]);
}

/**
 * EPA AQI PM2.5 color bands (µg/m³).
 * 0-12 green, 12-35 yellow, 35-55 orange, 55-150 red, 150+ purple.
 */
function pm25Color(pm: number): string {
  if (pm <= 12) return '#22c55e';
  if (pm <= 35) return '#eab308';
  if (pm <= 55) return '#f97316';
  if (pm <= 150) return '#dc2626';
  return '#7e22ce';
}

function rgb([r, g, b]: [number, number, number]): string {
  return `rgb(${r},${g},${b})`;
}

// --- Small UI bits ------------------------------------------------------

interface LayerBtnProps {
  label: string;
  active: boolean;
  onClick: () => void;
  activeColor: string;
  disabled?: boolean;
  title?: string;
}
function LayerBtn({
  label,
  active,
  onClick,
  activeColor,
  disabled,
  title,
}: LayerBtnProps) {
  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      title={title}
      disabled={disabled}
      aria-pressed={active}
      style={{
        padding: '6px 10px',
        fontSize: '12px',
        fontWeight: 600,
        border: '1px solid',
        borderRadius: '6px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontFamily: 'system-ui, sans-serif',
        background: disabled ? '#0f172a' : active ? activeColor : '#1e293b',
        color: disabled ? '#475569' : active ? '#fff' : '#94a3b8',
        borderColor: disabled
          ? '#1e293b'
          : active
            ? activeColor
            : '#334155',
        opacity: disabled ? 0.55 : 1,
      }}
    >
      {label}
    </button>
  );
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
  gap: '6px',
  flexWrap: 'wrap',
  justifyContent: 'flex-end',
  maxWidth: '60%',
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
