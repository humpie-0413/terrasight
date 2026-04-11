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
 * Phase B expansion:
 *   - 5-category accordion layer panel (top-right overlay)
 *   - GIBS WMS transparent PNG composited on BlueMarble via offscreen canvas
 *   - New layers: Storms (IBTrACS/ATCF), Coral Bleaching (NOAA CRW), CMEMS SLA
 *   - Existing: Fires (FIRMS), Ocean Heat (OISST), Air Monitors (OpenAQ)
 *
 * Layer composition rules:
 *   - At most 1 continuous field active (ocean-heat, coral, cmems-sla, or gibs-*)
 *   - At most 1 event overlay active (fires, storms, monitors)
 *   - Both can be ON simultaneously
 */

// ─── GIBS WMS base URLs ───────────────────────────────────────────────────────

const BLUEMARBLE_URL =
  'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
  '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1' +
  '&LAYERS=BlueMarble_ShadedRelief_Bathymetry' +
  '&STYLES=&FORMAT=image/jpeg&SRS=EPSG:4326' +
  '&BBOX=-180,-90,180,90&WIDTH=2048&HEIGHT=1024';

const GIBS_WMS_BASE =
  'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
  '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1' +
  '&STYLES=&FORMAT=image/png&TRANSPARENT=TRUE&SRS=EPSG:4326' +
  '&BBOX=-180,-90,180,90&WIDTH=2048&HEIGHT=1024';

// GIBS layer name mapping
const GIBS_LAYER_NAMES: Record<string, string> = {
  'gibs-pm25': 'MERRA2_Total_Aerosol_Optical_Thickness_550nm_Scattering_Monthly',
  'gibs-aod': 'MODIS_Terra_Aerosol_Optical_Depth_3km',
  'gibs-oco2': 'OCO2_CO2_Column_Daily',
  'gibs-flood': 'MODIS_Terra_Flood_3-Day',
};

// ─── Types ────────────────────────────────────────────────────────────────────

export type ActiveEvent = 'fires' | 'storms' | 'monitors' | null;
export type ActiveContinuous =
  | 'ocean-heat'
  | 'coral'
  | 'cmems-sla'
  | 'gibs-aod'
  | 'gibs-pm25'
  | 'gibs-oco2'
  | 'gibs-flood'
  | null;

export interface GlobeHandle {
  flyTo: (lat: number, lng: number, altitude?: number) => void;
}

interface GlobeProps {
  activeEvent: ActiveEvent;
  activeContinuous: ActiveContinuous;
  onLayerChange: (type: 'event' | 'continuous', key: string | null) => void;
}

// ─── Data interfaces ──────────────────────────────────────────────────────────

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

interface Storm {
  sid: string;
  name: string;
  basin: string;
  season: string;
  lat: number;
  lon: number;
  wind_kt: number;
  pres_hpa: number;
  sshs: number;
  iso_time: string;
}
interface StormsResponse {
  count: number;
  configured: boolean;
  storms: Storm[];
}

interface CoralPoint {
  lat: number;
  lon: number;
  bleaching_alert: number;
  dhw: number;
  sst_c: number;
  sst_anomaly_c: number;
}
interface CoralResponse {
  count: number;
  configured: boolean;
  status: string;
  points: CoralPoint[];
}

interface SlaPoint {
  lat: number;
  lon: number;
  sla_m: number;
}
interface SlaResponse {
  count: number;
  configured: boolean;
  status: string;
  message?: string;
  points: SlaPoint[];
}

// ─── Layer category definitions ───────────────────────────────────────────────

interface LayerDef {
  key: string;
  label: string;
  type: 'event' | 'continuous';
  activeColor: string;
  tag: TrustTag;
  cadence: string;
  source: string;
  sourceUrl: string;
  available: boolean;
  note?: string;
}

interface CategoryDef {
  name: string;
  layers: LayerDef[];
}

const CATEGORIES: CategoryDef[] = [
  {
    name: 'Atmosphere',
    layers: [
      {
        key: 'gibs-pm25',
        label: 'PM2.5 (MERRA-2)',
        type: 'continuous',
        activeColor: '#a855f7',
        tag: TrustTag.Derived,
        cadence: 'Monthly',
        source: 'NASA GIBS / MERRA-2',
        sourceUrl: 'https://disc.gsfc.nasa.gov/datasets/M2TMNXAER_5.12.4/',
        available: true,
      },
      {
        key: 'gibs-aod',
        label: 'Aerosol Optical Depth',
        type: 'continuous',
        activeColor: '#f59e0b',
        tag: TrustTag.NearRealTime,
        cadence: 'Daily',
        source: 'NASA GIBS / MODIS Terra',
        sourceUrl: 'https://worldview.earthdata.nasa.gov/',
        available: true,
      },
      {
        key: 'monitors',
        label: 'Air Monitors (PM2.5)',
        type: 'event',
        activeColor: '#ca8a04',
        tag: TrustTag.Observed,
        cadence: 'Varies',
        source: 'OpenAQ',
        sourceUrl: 'https://openaq.org/',
        available: true,
      },
    ],
  },
  {
    name: 'Fire & Land',
    layers: [
      {
        key: 'fires',
        label: 'Active Fires',
        type: 'event',
        activeColor: '#dc2626',
        tag: TrustTag.NearRealTime,
        cadence: 'NRT ~3h',
        source: 'NASA FIRMS',
        sourceUrl: 'https://firms.modaps.eosdis.nasa.gov/',
        available: true,
      },
      {
        key: 'deforestation',
        label: 'Deforestation',
        type: 'continuous',
        activeColor: '#16a34a',
        tag: TrustTag.Derived,
        cadence: 'Annual',
        source: 'Hansen / GFW',
        sourceUrl: 'https://www.globalforestwatch.org/',
        available: false,
        note: 'Country-level points require polygon query (P1)',
      },
      {
        key: 'drought',
        label: 'Drought Index',
        type: 'continuous',
        activeColor: '#b45309',
        tag: TrustTag.Derived,
        cadence: 'Weekly',
        source: 'JRC GWIS',
        sourceUrl: 'https://gwis.jrc.ec.europa.eu/',
        available: false,
        note: 'JRC GWIS drought index — Phase P1',
      },
    ],
  },
  {
    name: 'Ocean',
    layers: [
      {
        key: 'ocean-heat',
        label: 'Sea Surface Temp',
        type: 'continuous',
        activeColor: '#0284c7',
        tag: TrustTag.Observed,
        cadence: 'Daily',
        source: 'NOAA OISST v2.1',
        sourceUrl: 'https://coralreefwatch.noaa.gov/product/5km/',
        available: true,
      },
      {
        key: 'coral',
        label: 'Coral Bleaching Alert',
        type: 'continuous',
        activeColor: '#f97316',
        tag: TrustTag.NearRealTime,
        cadence: 'Daily',
        source: 'NOAA Coral Reef Watch',
        sourceUrl: 'https://coralreefwatch.noaa.gov/',
        available: true,
      },
      {
        key: 'cmems-sla',
        label: 'Sea Level Anomaly',
        type: 'continuous',
        activeColor: '#3b82f6',
        tag: TrustTag.Derived,
        cadence: 'Daily',
        source: 'CMEMS / Copernicus Marine',
        sourceUrl: 'https://marine.copernicus.eu/',
        available: true,
      },
    ],
  },
  {
    name: 'GHG',
    layers: [
      {
        key: 'gibs-oco2',
        label: 'CO₂ Column (OCO-2)',
        type: 'continuous',
        activeColor: '#22c55e',
        tag: TrustTag.Observed,
        cadence: 'Daily',
        source: 'NASA GIBS / OCO-2',
        sourceUrl: 'https://ocov2.jpl.nasa.gov/',
        available: true,
      },
      {
        key: 'gibs-ch4',
        label: 'CH₄ (TROPOMI)',
        type: 'continuous',
        activeColor: '#84cc16',
        tag: TrustTag.Observed,
        cadence: 'Daily',
        source: 'Copernicus GES DISC',
        sourceUrl: 'https://disc.gsfc.nasa.gov/',
        available: false,
        note: 'Satellite data coming soon',
      },
    ],
  },
  {
    name: 'Hazards',
    layers: [
      {
        key: 'storms',
        label: 'Tropical Storms',
        type: 'event',
        activeColor: '#ec4899',
        tag: TrustTag.NearRealTime,
        cadence: 'NRT ~6h',
        source: 'ATCF / IBTrACS',
        sourceUrl: 'https://www.nrlmry.navy.mil/atcf_web/atlas/ibtracks/',
        available: true,
      },
      {
        key: 'gibs-flood',
        label: 'Flood Detection',
        type: 'continuous',
        activeColor: '#0ea5e9',
        tag: TrustTag.NearRealTime,
        cadence: '3-Day',
        source: 'NASA GIBS / MODIS Terra',
        sourceUrl: 'https://worldview.earthdata.nasa.gov/',
        available: true,
      },
    ],
  },
];

// Flat lookup by key
const LAYER_LOOKUP = new Map<string, LayerDef>(
  CATEGORIES.flatMap((c) => c.layers.map((l) => [l.key, l])),
);

// ─── GIBS texture hook ────────────────────────────────────────────────────────

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

function gibsOverlayUrl(layerName: string, date: string): string {
  return `${GIBS_WMS_BASE}&LAYERS=${layerName}&TIME=${date}`;
}

function dateString(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function dateCandidates(): string[] {
  const now = new Date();
  const candidates: string[] = [];
  // today, yesterday, day before
  for (let i = 0; i < 3; i++) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    candidates.push(dateString(d));
  }
  // first of this month
  const firstThis = new Date(now.getFullYear(), now.getMonth(), 1);
  candidates.push(dateString(firstThis));
  // first of last month
  const firstLast = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  candidates.push(dateString(firstLast));
  return candidates;
}

function useGibsTexture(gibsLayerName: string | null): string {
  const [textureUrl, setTextureUrl] = useState<string>(BLUEMARBLE_URL);

  useEffect(() => {
    if (!gibsLayerName) {
      setTextureUrl(BLUEMARBLE_URL);
      return;
    }

    let cancelled = false;

    async function buildComposite() {
      const canvas = document.createElement('canvas');
      canvas.width = 2048;
      canvas.height = 1024;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Load BlueMarble base
      let baseImg: HTMLImageElement;
      try {
        baseImg = await loadImage(BLUEMARBLE_URL);
      } catch {
        // Can't even load base — fall back
        return;
      }
      if (cancelled) return;

      ctx.drawImage(baseImg, 0, 0, 2048, 1024);

      // Try date candidates until one succeeds
      const candidates = dateCandidates();
      let overlayLoaded = false;

      for (const date of candidates) {
        if (cancelled) return;
        try {
          const url = gibsOverlayUrl(gibsLayerName!, date);
          const overlayImg = await loadImage(url);
          if (cancelled) return;
          ctx.globalAlpha = 0.72;
          ctx.drawImage(overlayImg, 0, 0, 2048, 1024);
          ctx.globalAlpha = 1.0;
          overlayLoaded = true;
          break;
        } catch {
          // try next date
        }
      }

      if (cancelled) return;

      if (overlayLoaded) {
        setTextureUrl(canvas.toDataURL('image/jpeg', 0.9));
      }
      // If no overlay loaded, we already drew BlueMarble — but the canvas
      // approach can cause CORS issues in toDataURL; fall back to BLUEMARBLE_URL
    }

    buildComposite().catch(() => {
      if (!cancelled) setTextureUrl(BLUEMARBLE_URL);
    });

    return () => {
      cancelled = true;
    };
  }, [gibsLayerName]);

  return textureUrl;
}

// ─── Color helpers ────────────────────────────────────────────────────────────

function rgb([r, g, b]: [number, number, number]): string {
  return `rgb(${r},${g},${b})`;
}

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
  if (c >= stops[stops.length - 1][0]) return rgb(stops[stops.length - 1][1]);
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

/**
 * DHW color ramp — Degree Heating Weeks.
 * 0→white, 4→yellow, 8→orange, 12→red, 16→purple
 */
function dhwColor(dhw: number): string {
  const stops: Array<[number, [number, number, number]]> = [
    [0, [255, 255, 255]],
    [4, [255, 255, 0]],
    [8, [255, 165, 0]],
    [12, [220, 38, 38]],
    [16, [126, 34, 206]],
  ];
  if (dhw <= stops[0][0]) return rgb(stops[0][1]);
  if (dhw >= stops[stops.length - 1][0]) return rgb(stops[stops.length - 1][1]);
  for (let i = 0; i < stops.length - 1; i++) {
    const [c1, rgb1] = stops[i];
    const [c2, rgb2] = stops[i + 1];
    if (dhw >= c1 && dhw <= c2) {
      const t = (dhw - c1) / (c2 - c1);
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
 * SLA color ramp — Sea Level Anomaly (meters).
 * -0.3 → blue, ~0 → white, +0.3 → red.
 */
function slaColor(sla_m: number): string {
  const clamped = Math.max(-0.3, Math.min(0.3, sla_m));
  const t = (clamped + 0.3) / 0.6; // 0 → 1
  if (t < 0.5) {
    const tt = t / 0.5;
    return rgb([
      Math.round(59 + (255 - 59) * tt),
      Math.round(130 + (255 - 130) * tt),
      Math.round(246 + (255 - 246) * tt),
    ]);
  } else {
    const tt = (t - 0.5) / 0.5;
    return rgb([
      Math.round(255 + (220 - 255) * tt),
      Math.round(255 + (38 - 255) * tt),
      Math.round(255 + (38 - 255) * tt),
    ]);
  }
}

/**
 * Storm wind speed color.
 * <34→white, 34-63→yellow, 64-82→orange, 83-95→red, 96-112→magenta, >112→purple
 */
function stormColor(windKt: number): string {
  if (windKt < 34) return '#ffffff';
  if (windKt < 64) return '#eab308';
  if (windKt < 83) return '#f97316';
  if (windKt < 96) return '#dc2626';
  if (windKt < 113) return '#ec4899';
  return '#7c3aed';
}

// ─── TrustTag color reference ─────────────────────────────────────────────────

const TRUST_TAG_COLORS: Record<TrustTag, string> = {
  [TrustTag.Observed]: '#22c55e',
  [TrustTag.NearRealTime]: '#f59e0b',
  [TrustTag.ForecastModel]: '#8b5cf6',
  [TrustTag.Derived]: '#64748b',
  [TrustTag.Estimated]: '#6b7280',
};

// ─── LayerPanel component ─────────────────────────────────────────────────────

interface LayerPanelProps {
  activeEvent: ActiveEvent;
  activeContinuous: ActiveContinuous;
  onLayerChange: (type: 'event' | 'continuous', key: string | null) => void;
  slaConfigured: boolean;
  slaStatus?: string;
  airConfigured: boolean;
}

function LayerPanel({
  activeEvent,
  activeContinuous,
  onLayerChange,
  slaConfigured,
  slaStatus,
  airConfigured,
}: LayerPanelProps) {
  const [openCategory, setOpenCategory] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  function isActive(layer: LayerDef): boolean {
    if (layer.type === 'event') return activeEvent === layer.key;
    return activeContinuous === layer.key;
  }

  function isEffectivelyDisabled(layer: LayerDef): boolean {
    if (!layer.available) return true;
    if (layer.key === 'cmems-sla' && !slaConfigured) return true;
    if (layer.key === 'monitors' && !airConfigured) return true;
    return false;
  }

  function handleLayerClick(layer: LayerDef) {
    if (isEffectivelyDisabled(layer)) return;
    const currentlyActive = isActive(layer);
    onLayerChange(layer.type, currentlyActive ? null : layer.key);
  }

  return (
    <div
      style={{
        position: 'absolute',
        top: 12,
        right: 12,
        zIndex: 10,
        background: 'rgba(11,17,32,0.88)',
        border: '1px solid #334155',
        borderRadius: '8px',
        backdropFilter: 'blur(6px)',
        fontFamily: 'system-ui, sans-serif',
        minWidth: '200px',
        maxWidth: '240px',
      }}
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setPanelOpen((v) => !v)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: '#e2e8f0',
          fontSize: '13px',
          fontWeight: 600,
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        <span>&#128193; Layers</span>
        <span style={{ fontSize: '10px', color: '#64748b' }}>
          {panelOpen ? '▲' : '▼'}
        </span>
      </button>

      {panelOpen && (
        <div style={{ borderTop: '1px solid #1e293b' }}>
          {CATEGORIES.map((cat) => (
            <div key={cat.name}>
              {/* Category row */}
              <button
                type="button"
                onClick={() =>
                  setOpenCategory((prev) =>
                    prev === cat.name ? null : cat.name,
                  )
                }
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 12px',
                  background: 'none',
                  border: 'none',
                  borderTop: '1px solid #1e293b',
                  cursor: 'pointer',
                  color: '#94a3b8',
                  fontSize: '11px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  fontFamily: 'system-ui, sans-serif',
                }}
              >
                <span>{cat.name}</span>
                <span>{openCategory === cat.name ? '▲' : '▼'}</span>
              </button>

              {/* Layer buttons */}
              {openCategory === cat.name && (
                <div
                  style={{
                    padding: '4px 8px 8px 8px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                  }}
                >
                  {cat.layers.map((layer) => {
                    const active = isActive(layer);
                    const disabled = isEffectivelyDisabled(layer);
                    const tagColor = TRUST_TAG_COLORS[layer.tag];
                    const tooltipNote = disabled
                      ? (layer.note ??
                        (layer.key === 'cmems-sla'
                          ? slaStatus === 'pending'
                            ? 'Sea level data migration in progress — coming soon'
                            : slaStatus === 'error'
                              ? 'Sea level service error — check backend logs'
                              : 'CMEMS credentials not configured'
                          : layer.key === 'monitors'
                            ? 'OPENAQ_API_KEY not configured'
                            : undefined))
                      : undefined;

                    return (
                      <button
                        key={layer.key}
                        type="button"
                        onClick={() => handleLayerClick(layer)}
                        title={tooltipNote}
                        disabled={disabled}
                        aria-pressed={active}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '5px 8px',
                          fontSize: '12px',
                          fontWeight: active ? 600 : 400,
                          border: '1px solid',
                          borderRadius: '5px',
                          cursor: disabled ? 'not-allowed' : 'pointer',
                          fontFamily: 'system-ui, sans-serif',
                          background: active ? layer.activeColor : '#1e293b',
                          color: active ? '#fff' : '#94a3b8',
                          borderColor: active ? layer.activeColor : '#334155',
                          opacity: disabled ? 0.4 : 1,
                          textAlign: 'left',
                        }}
                      >
                        <span
                          style={{
                            display: 'inline-block',
                            width: '7px',
                            height: '7px',
                            borderRadius: '50%',
                            background: tagColor,
                            flexShrink: 0,
                          }}
                        />
                        {layer.label}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Globe component ──────────────────────────────────────────────────────────

const Globe = forwardRef<GlobeHandle, GlobeProps>(function Globe(
  { activeEvent, activeContinuous, onLayerChange },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [dims, setDims] = useState({ width: 640, height: 520 });

  // Data fetches
  const { data: firesData, loading: firesLoading } =
    useApi<FiresResponse>('/earth-now/fires');
  const { data: sstData, loading: sstLoading } =
    useApi<SstResponse>('/earth-now/sst');
  const { data: airData, loading: airLoading } =
    useApi<AirMonitorsResponse>('/earth-now/air-monitors');
  const { data: stormsData, loading: stormsLoading } =
    useApi<StormsResponse>('/earth-now/storms');
  const { data: coralData, loading: coralLoading } =
    useApi<CoralResponse>('/earth-now/coral');
  const { data: slaData, loading: slaLoading } =
    useApi<SlaResponse>('/earth-now/sea-level-anomaly');

  // GIBS texture composite (only for gibs-* layers)
  const gibsLayerName = useMemo<string | null>(() => {
    if (!activeContinuous) return null;
    return GIBS_LAYER_NAMES[activeContinuous] ?? null;
  }, [activeContinuous]);

  const globeImageUrl = useGibsTexture(gibsLayerName);

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

  // Expose imperative flyTo()
  useImperativeHandle(
    ref,
    () => ({
      flyTo: (lat: number, lng: number, altitude = 1.8) => {
        if (!globeRef.current) return;
        const controls = globeRef.current.controls();
        controls.autoRotate = false;
        globeRef.current.pointOfView({ lat, lng, altitude }, 1500);
      },
    }),
    [],
  );

  // ── Overlay datasets ────────────────────────────────────────────────────

  const firePoints = useMemo<FireHotspot[]>(
    () => (activeEvent === 'fires' && firesData?.fires ? firesData.fires : []),
    [activeEvent, firesData],
  );

  const stormPoints = useMemo<Storm[]>(
    () =>
      activeEvent === 'storms' && stormsData?.storms ? stormsData.storms : [],
    [activeEvent, stormsData],
  );

  // pointsData merges fires + storms (both are event overlays, at most one active)
  const pointsData = useMemo<(FireHotspot | Storm)[]>(
    () => [...firePoints, ...stormPoints],
    [firePoints, stormPoints],
  );

  const sstPoints = useMemo<SstPoint[]>(
    () =>
      activeContinuous === 'ocean-heat' && sstData?.points
        ? sstData.points
        : [],
    [activeContinuous, sstData],
  );

  const coralPoints = useMemo<CoralPoint[]>(
    () =>
      activeContinuous === 'coral' && coralData?.points
        ? coralData.points
        : [],
    [activeContinuous, coralData],
  );

  // hexBinPointsData = SST or Coral (mutually exclusive via activeContinuous)
  const hexBinData = useMemo<(SstPoint | CoralPoint)[]>(
    () => [...sstPoints, ...coralPoints],
    [sstPoints, coralPoints],
  );

  const airPoints = useMemo<AirMonitor[]>(
    () =>
      activeEvent === 'monitors' && airData?.monitors ? airData.monitors : [],
    [activeEvent, airData],
  );

  const slaPoints = useMemo<SlaPoint[]>(
    () =>
      activeContinuous === 'cmems-sla' && slaData?.points
        ? slaData.points
        : [],
    [activeContinuous, slaData],
  );

  // labelsData = air monitors OR SLA dots
  const labelsData = useMemo<(AirMonitor | SlaPoint)[]>(
    () => [...airPoints, ...slaPoints],
    [airPoints, slaPoints],
  );

  // ── Meta + status ────────────────────────────────────────────────────────

  const activeMeta = useMemo(() => {
    if (activeContinuous) {
      const def = LAYER_LOOKUP.get(activeContinuous);
      if (def) {
        return {
          cadence: def.cadence,
          tag: def.tag,
          source: def.source,
          sourceUrl: def.sourceUrl,
        };
      }
    }
    if (activeEvent) {
      const def = LAYER_LOOKUP.get(activeEvent);
      if (def) {
        return {
          cadence: def.cadence,
          tag: def.tag,
          source: def.source,
          sourceUrl: def.sourceUrl,
        };
      }
    }
    // Default: fires
    return {
      cadence: 'NRT ~3h',
      tag: TrustTag.Observed,
      source: 'NASA FIRMS',
      sourceUrl: 'https://firms.modaps.eosdis.nasa.gov/',
    };
  }, [activeContinuous, activeEvent]);

  const statusMessage = useMemo(() => {
    const loading =
      firesLoading ||
      stormsLoading ||
      coralLoading ||
      slaLoading ||
      (activeContinuous === 'ocean-heat' && sstLoading) ||
      (activeEvent === 'monitors' && airLoading);
    if (loading) return 'Loading…';

    if (firesData && !firesData.configured && activeEvent === 'fires') {
      return 'FIRMS_MAP_KEY not configured — fire layer disabled. See .env.example.';
    }
    if (activeEvent === 'monitors' && airData && !airData.configured) {
      return 'OPENAQ_API_KEY not configured — air monitors disabled. See .env.example.';
    }
    if (activeContinuous === 'cmems-sla' && slaData) {
      if (!slaData.configured) {
        return 'CMEMS credentials not configured — sea level layer disabled.';
      }
      if (slaData.status === 'pending') {
        return 'Sea Level Anomaly: endpoint migration in progress — full data integration coming soon.';
      }
      if (slaData.status === 'error') {
        return `Sea Level Anomaly error: ${slaData.message ?? 'service unavailable.'}`;
      }
    }
    return null;
  }, [
    firesLoading,
    sstLoading,
    airLoading,
    stormsLoading,
    coralLoading,
    slaLoading,
    activeContinuous,
    activeEvent,
    firesData,
    airData,
    slaData,
  ]);

  // ── Hex bin helpers ──────────────────────────────────────────────────────

  function hexWeight(d: object): number {
    if (activeContinuous === 'ocean-heat') return (d as SstPoint).sst_c;
    if (activeContinuous === 'coral') return (d as CoralPoint).dhw;
    return 0;
  }

  function hexTopColorFn(d: { sumWeight: number; points: object[] }): string {
    const mean = d.sumWeight / Math.max(d.points.length, 1);
    if (activeContinuous === 'coral') return dhwColor(mean);
    return sstColor(mean);
  }

  // ── Label helpers ────────────────────────────────────────────────────────

  function labelColor(d: object): string {
    if (activeContinuous === 'cmems-sla') return slaColor((d as SlaPoint).sla_m);
    return pm25Color((d as AirMonitor).pm25);
  }

  function labelTooltip(d: object): string {
    if (activeContinuous === 'cmems-sla') {
      const s = d as SlaPoint;
      return `
        <div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;
             border:1px solid #475569;border-radius:4px;font-size:11px;
             font-family:system-ui,sans-serif;">
          <div><b>Sea Level Anomaly</b></div>
          <div>SLA: ${s.sla_m >= 0 ? '+' : ''}${s.sla_m.toFixed(3)} m</div>
          <div>${s.lat.toFixed(2)}°, ${s.lon.toFixed(2)}°</div>
        </div>
      `;
    }
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
  }

  // ── Point helpers (fires + storms) ───────────────────────────────────────

  function pointColor(d: object): string {
    if (activeEvent === 'storms') return stormColor((d as Storm).wind_kt);
    return '#ff3d00';
  }

  function pointAltitude(d: object): number {
    if (activeEvent === 'storms') return 0.01;
    return firePointAltitude(d as FireHotspot);
  }

  function pointRadius(d: object): number {
    if (activeEvent === 'storms') return 0.4;
    return firePointRadius(d as FireHotspot);
  }

  function pointTooltip(d: object): string {
    if (activeEvent === 'storms') {
      const s = d as Storm;
      return `
        <div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;
             border:1px solid #475569;border-radius:4px;font-size:11px;
             font-family:system-ui,sans-serif;">
          <div><b>${s.name}</b> (${s.basin} basin)</div>
          <div>${s.iso_time} UTC</div>
          <div>Wind: ${s.wind_kt} kt · Pressure: ${s.pres_hpa} hPa · SSHS: ${s.sshs}</div>
          <div>${s.lat.toFixed(2)}°, ${s.lon.toFixed(2)}°</div>
        </div>
      `;
    }
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
  }

  // slaConfigured = credentials present AND actual data is available (status 'ok').
  // 'pending' (endpoint migration) and 'error' both disable the toggle.
  const slaConfigured = slaData
    ? slaData.configured && slaData.status === 'ok'
    : true; // optimistic while loading
  const airConfigured = airData ? airData.configured : true;

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
        globeImageUrl={globeImageUrl}
        backgroundColor="#0b1120"
        showAtmosphere={true}
        atmosphereColor="#88aaff"
        atmosphereAltitude={0.18}
        // --- Points (fires or storms, event overlay) ---
        pointsData={pointsData}
        pointLat={(d: object) =>
          activeEvent === 'storms'
            ? (d as Storm).lat
            : (d as FireHotspot).lat
        }
        pointLng={(d: object) =>
          activeEvent === 'storms'
            ? (d as Storm).lon
            : (d as FireHotspot).lon
        }
        pointColor={pointColor}
        pointAltitude={pointAltitude}
        pointRadius={pointRadius}
        pointResolution={4}
        pointLabel={pointTooltip}
        // --- Hex bin (SST or Coral, continuous field) ---
        hexBinPointsData={hexBinData}
        hexBinPointLat={(d: object) => (d as SstPoint).lat}
        hexBinPointLng={(d: object) => (d as SstPoint).lon}
        hexBinPointWeight={hexWeight}
        hexBinResolution={3}
        hexAltitude={0.008}
        hexTopColor={hexTopColorFn}
        hexSideColor={hexTopColorFn}
        hexBinMerge={false}
        hexLabel={(d: { sumWeight: number; points: object[] }) => {
          const mean = d.sumWeight / Math.max(d.points.length, 1);
          if (activeContinuous === 'coral') {
            return `
              <div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;
                   border:1px solid #475569;border-radius:4px;font-size:11px;
                   font-family:system-ui,sans-serif;">
                <div><b>Coral Bleaching</b></div>
                <div>DHW: ${mean.toFixed(1)} °C-weeks (${d.points.length} cell${d.points.length === 1 ? '' : 's'})</div>
              </div>
            `;
          }
          return `
            <div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;
                 border:1px solid #475569;border-radius:4px;font-size:11px;
                 font-family:system-ui,sans-serif;">
              <div><b>Ocean Heat</b></div>
              <div>${mean.toFixed(1)}°C (${d.points.length} grid cell${d.points.length === 1 ? '' : 's'})</div>
            </div>
          `;
        }}
        // --- Labels (air monitors or SLA dots) ---
        labelsData={labelsData}
        labelLat={(d: object) =>
          activeContinuous === 'cmems-sla'
            ? (d as SlaPoint).lat
            : (d as AirMonitor).lat
        }
        labelLng={(d: object) =>
          activeContinuous === 'cmems-sla'
            ? (d as SlaPoint).lon
            : (d as AirMonitor).lon
        }
        labelText={() => ''}
        labelDotRadius={activeContinuous === 'cmems-sla' ? 0.3 : 0.25}
        labelDotOrientation={() => 'top'}
        labelColor={labelColor}
        labelResolution={2}
        labelLabel={labelTooltip}
      />

      {/* Overlay: active-layer meta (top-left) */}
      <div style={headerStyle}>
        <MetaLine
          cadence={activeMeta.cadence}
          tag={activeMeta.tag}
          source={activeMeta.source}
          sourceUrl={activeMeta.sourceUrl}
        />
      </div>

      {/* Overlay: 5-category accordion layer panel (top-right) */}
      <LayerPanel
        activeEvent={activeEvent}
        activeContinuous={activeContinuous}
        onLayerChange={onLayerChange}
        slaConfigured={slaConfigured}
        slaStatus={slaData?.status}
        airConfigured={airConfigured}
      />

      {/* Status line */}
      {statusMessage && <div style={statusLineStyle}>{statusMessage}</div>}
    </div>
  );
});

export default Globe;

// ─── Styles ───────────────────────────────────────────────────────────────────

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
