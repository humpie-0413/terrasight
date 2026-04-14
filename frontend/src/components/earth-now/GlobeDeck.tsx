import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Deck, MapView, _GlobeView as GlobeView } from '@deck.gl/core';
import { BitmapLayer, PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import { TileLayer } from '@deck.gl/geo-layers';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';

import MetaLine from '../common/MetaLine';
import { TrustTag } from '../../utils/trustTags';
import { useApi } from '../../hooks/useApi';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

// ─── Types ────────────────────────────────────────────────────────────────────

export type ActiveCategory =
  | 'air-quality' | 'temperature' | 'sst' | 'precipitation' | 'no2'
  | 'wildfires' | 'earthquakes' | 'co2-ghg'
  | 'ocean-crisis' | 'storms'
  | null;

export type ViewMode = 'globe' | 'map';

export interface GlobeHandle {
  flyTo: (lat: number, lng: number, altitude?: number) => void;
}

interface GlobeProps {
  activeCategory: ActiveCategory;
  onCategoryChange: (key: ActiveCategory) => void;
}

// ─── Data interfaces ──────────────────────────────────────────────────────────

interface FireHotspot {
  lat: number; lon: number; brightness: number; frp: number;
  confidence: string; acq_date: string; acq_time: string; daynight: string;
}
interface FiresResponse { count: number; configured: boolean; fires: FireHotspot[]; }

interface OceanHealthCell {
  lat: number; lon: number; stress_score: number; sst_c: number; dhw: number; source_count: number;
}
interface OceanHealthResponse {
  count: number; status: string;
  grid: OceanHealthCell[];
  stats: { min_stress: number; max_stress: number; mean_stress: number };
}

interface StormTrackPoint { lat: number; lon: number; wind_kt: number; iso_time: string; }
interface Storm { sid: string; name: string; basin: string; season: string; lat: number; lon: number; wind_kt: number; pres_hpa: number; sshs: number; iso_time: string; track_points?: StormTrackPoint[]; }
interface StormsResponse { count: number; configured: boolean; storms: Storm[]; }

interface Earthquake { lat: number; lon: number; depth_km: number; magnitude: number; place: string; time_utc: string; event_url: string; tsunami: boolean; }
interface EarthquakeResponse { count: number; configured: boolean; status: string; earthquakes: Earthquake[]; }

// ─── Tile URLs ────────────────────────────────────────────────────────────────

const BLUEMARBLE_TILE_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/2004-08/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg';

const CARTO_DARK_URL =
  'https://basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}@2x.png';

// ─── GIBS ─────────────────────────────────────────────────────────────────────

const GIBS_WMS_BASE =
  'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
  '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1' +
  '&STYLES=&FORMAT=image/png&TRANSPARENT=TRUE&SRS=EPSG:4326';

function loadWmsImage(url: string): Promise<ImageBitmap> {
  return fetch(url, { mode: 'cors' })
    .then((r) => r.blob())
    .then((b) => createImageBitmap(b));
}

const GIBS_LAYER_NAMES: Record<string, string> = {
  'gibs-pm25': 'MERRA2_Dust_Surface_Mass_Concentration_PM25_Monthly',
  'gibs-aod': 'MODIS_Terra_Aerosol_Optical_Depth_3km',
  'gibs-oco2': 'OCO2_CO2_Column_Daily',
  'gibs-flood': 'MODIS_Terra_Flood_3-Day',
};

function getGibsDate(layerKey: string): string {
  const d = new Date();
  if (layerKey === 'gibs-pm25') {
    // MERRA-2 monthly reanalysis has ~3 month latency
    d.setMonth(d.getMonth() - 3);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
  }
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

// ─── Categories (user-question driven, ordered by interest) ───────────────────

interface CategoryDef {
  key: string;
  icon: string;
  name: string;
  question: string;
  activeColor: string;
  tag: TrustTag;
  cadence: string;
  source: string;
  sourceUrl: string;
  activates: string[];
}

const CATEGORIES: CategoryDef[] = [
  // ── Continuous Surfaces (self-rendered PNGs) ────────────────────────
  {
    key: 'air-quality', icon: '🌬️', name: 'Air Quality',
    question: 'How is the air today?',
    activeColor: '#a855f7', tag: TrustTag.Derived, cadence: 'Hourly (CAMS model)',
    source: 'Open-Meteo / CAMS Global PM2.5', sourceUrl: 'https://open-meteo.com/en/docs/air-quality-api',
    activates: ['pm25-surface'],
  },
  {
    key: 'temperature', icon: '🌡️', name: 'Temperature',
    question: 'How warm is it globally?',
    activeColor: '#ef4444', tag: TrustTag.Derived, cadence: 'Hourly (GFS model)',
    source: 'Open-Meteo / GFS 2m Temperature', sourceUrl: 'https://open-meteo.com/en/docs',
    activates: ['temp-surface'],
  },
  {
    key: 'sst', icon: '🌊', name: 'Ocean Temp',
    question: 'How warm are the oceans?',
    activeColor: '#f97316', tag: TrustTag.Observed, cadence: 'Daily (1-day lag)',
    source: 'NOAA OISST v2.1', sourceUrl: 'https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg.html',
    activates: ['sst-surface'],
  },
  {
    key: 'precipitation', icon: '🌧️', name: 'Precipitation',
    question: 'Where is it raining?',
    activeColor: '#3b82f6', tag: TrustTag.Derived, cadence: 'Hourly (GFS model)',
    source: 'Open-Meteo / GFS Precipitation', sourceUrl: 'https://open-meteo.com/en/docs',
    activates: ['precip-surface'],
  },
  {
    key: 'no2', icon: '🏭', name: 'NO₂ Pollution',
    question: 'Where is NO₂ concentrated?',
    activeColor: '#d97706', tag: TrustTag.Derived, cadence: 'Hourly (CAMS model)',
    source: 'Open-Meteo / CAMS Global NO₂', sourceUrl: 'https://open-meteo.com/en/docs/air-quality-api',
    activates: ['no2-surface'],
  },
  // ── Event Layers (point data) ──────────────────────────────────────
  {
    key: 'wildfires', icon: '🔥', name: 'Wildfires',
    question: 'Where are fires burning?',
    activeColor: '#dc2626', tag: TrustTag.NearRealTime, cadence: 'NRT ~3h',
    source: 'NASA FIRMS', sourceUrl: 'https://firms.modaps.eosdis.nasa.gov/',
    activates: ['fires'],
  },
  {
    key: 'earthquakes', icon: '🌍', name: 'Earthquakes',
    question: 'Where did earthquakes hit?',
    activeColor: '#b91c1c', tag: TrustTag.Observed, cadence: 'NRT ~5 min',
    source: 'USGS', sourceUrl: 'https://earthquake.usgs.gov/',
    activates: ['earthquakes'],
  },
  {
    key: 'co2-ghg', icon: '💨', name: 'CO₂ & GHG',
    question: 'Where did OCO-2 measure CO₂ today?',
    activeColor: '#22c55e', tag: TrustTag.Observed, cadence: 'Daily (nadir swath ~3-5% coverage)',
    source: 'NASA OCO-2', sourceUrl: 'https://ocov2.jpl.nasa.gov/',
    activates: ['gibs-oco2'],
  },
];

const CATEGORY_LOOKUP = new Map<string, CategoryDef>(
  CATEGORIES.map((c) => [c.key, c]),
);

// ─── Color helpers ────────────────────────────────────────────────────────────

function rgbArr(r: number, g: number, b: number, a = 255): [number, number, number, number] {
  return [r, g, b, a];
}

function lerpColor(
  stops: Array<[number, [number, number, number]]>,
  val: number,
): [number, number, number, number] {
  if (val <= stops[0][0]) return [...stops[0][1], 255];
  if (val >= stops[stops.length - 1][0]) return [...stops[stops.length - 1][1], 255];
  for (let i = 0; i < stops.length - 1; i++) {
    const [c1, rgb1] = stops[i];
    const [c2, rgb2] = stops[i + 1];
    if (val >= c1 && val <= c2) {
      const t = (val - c1) / (c2 - c1);
      return [
        Math.round(rgb1[0] + (rgb2[0] - rgb1[0]) * t),
        Math.round(rgb1[1] + (rgb2[1] - rgb1[1]) * t),
        Math.round(rgb1[2] + (rgb2[2] - rgb1[2]) * t),
        255,
      ];
    }
  }
  return [...stops[0][1], 255];
}

function fireColorRGBA(frp: number): [number, number, number, number] {
  if (frp >= 500) return rgbArr(180, 20, 20, 245);
  if (frp >= 200) return rgbArr(220, 50, 10, 235);
  if (frp >= 100) return rgbArr(245, 100, 10, 225);
  if (frp >= 50) return rgbArr(255, 160, 20, 210);
  if (frp >= 10) return rgbArr(255, 200, 60, 195);
  return rgbArr(255, 230, 120, 170);
}

function fireRadius(frp: number): number {
  return Math.max(3, Math.min(14, 3 + Math.log10(Math.max(frp, 1)) * 3.5));
}

// Ocean stress: 0 = healthy blue, 1 = crisis red
function oceanStressColor(s: number): [number, number, number, number] {
  return lerpColor([
    [0.0, [20, 60, 180]],
    [0.15, [30, 140, 200]],
    [0.3, [60, 200, 160]],
    [0.5, [200, 210, 60]],
    [0.7, [245, 140, 30]],
    [0.85, [220, 50, 20]],
    [1.0, [160, 20, 80]],
  ], s);
}

function stormColorRGBA(windKt: number): [number, number, number, number] {
  if (windKt < 34) return rgbArr(255, 255, 255, 200);
  if (windKt < 64) return rgbArr(234, 179, 8, 210);
  if (windKt < 83) return rgbArr(249, 115, 22, 220);
  if (windKt < 96) return rgbArr(220, 38, 38, 230);
  if (windKt < 113) return rgbArr(236, 72, 153, 240);
  return rgbArr(124, 58, 237, 250);
}

function stormRadius(windKt: number): number {
  if (windKt < 34) return 4;
  if (windKt < 64) return 6;
  if (windKt < 83) return 9;
  if (windKt < 96) return 12;
  return 16;
}

function earthquakeColorRGBA(mag: number): [number, number, number, number] {
  if (mag < 5) return rgbArr(234, 179, 8, 200);
  if (mag < 6) return rgbArr(249, 115, 22, 220);
  if (mag < 7) return rgbArr(239, 68, 68, 240);
  return rgbArr(153, 27, 27, 255);
}

function earthquakeRadius(mag: number): number {
  return Math.max(4, 4 + (mag - 4) * 5);
}

const FIRE_HEATMAP_COLORS: [number, number, number][] = [
  [255, 255, 200], [255, 237, 160], [254, 204, 92],
  [253, 141, 60], [240, 59, 32], [189, 0, 38],
];

// ─── ViewState ────────────────────────────────────────────────────────────────

interface GlobeViewState { longitude: number; latitude: number; zoom: number; }
const INITIAL_VIEW_STATE: GlobeViewState = { longitude: 0, latitude: 20, zoom: 1.2 };

// ─── LayerBar ─────────────────────────────────────────────────────────────────

function LayerBar({
  activeCategory, onCategoryChange, viewMode, onViewModeChange,
}: {
  activeCategory: ActiveCategory;
  onCategoryChange: (key: ActiveCategory) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}) {
  return (
    <div style={layerBarStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '3px', overflowX: 'auto', paddingBottom: 2 }}>
        <button type="button"
          onClick={() => onViewModeChange(viewMode === 'globe' ? 'map' : 'globe')}
          style={{
            padding: '6px 10px', background: 'rgba(59,130,246,0.12)',
            border: '1px solid rgba(59,130,246,0.2)', borderRadius: '6px',
            color: '#94a3b8', fontSize: '12px', cursor: 'pointer',
            fontFamily: 'system-ui, sans-serif', flexShrink: 0,
          }}>
          {viewMode === 'globe' ? '3D' : '2D'}
        </button>

        <div style={{ width: 1, height: 20, background: 'rgba(51,65,85,0.4)', margin: '0 4px', flexShrink: 0 }} />

        {CATEGORIES.map((cat) => {
          const active = activeCategory === cat.key;
          return (
            <button key={cat.key} type="button"
              onClick={() => onCategoryChange(active ? null : cat.key as ActiveCategory)}
              style={{
                display: 'flex', alignItems: 'center', gap: '4px',
                padding: '5px 12px', fontSize: '11px', fontWeight: active ? 700 : 500,
                border: '1px solid', borderRadius: '16px',
                cursor: 'pointer', fontFamily: 'system-ui, sans-serif',
                whiteSpace: 'nowrap', flexShrink: 0,
                background: active ? cat.activeColor : 'rgba(30,41,59,0.5)',
                color: active ? '#fff' : '#94a3b8',
                borderColor: active ? cat.activeColor : 'rgba(51,65,85,0.4)',
                transition: 'all 0.2s',
                boxShadow: active ? `0 0 14px ${cat.activeColor}50` : 'none',
              }}>
              <span style={{ fontSize: '13px' }}>{cat.icon}</span>
              <span className="layer-pill-text">{cat.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Legend ────────────────────────────────────────────────────────────────────

function Legend({ activeCategory }: { activeCategory: ActiveCategory }) {
  if (activeCategory === 'wildfires') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Fire Radiative Power (MW)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(255,230,120), rgb(255,200,60), rgb(255,160,20), rgb(245,100,10), rgb(220,50,10), rgb(180,20,20))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>0</span><span>50</span><span>200</span><span>500+</span></div>
    </div>
  );
  if (activeCategory === 'earthquakes') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Earthquake Magnitude</div>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        {[{ label: 'M4', color: '#eab308', size: 8 }, { label: 'M5', color: '#f97316', size: 10 },
          { label: 'M6', color: '#ef4444', size: 13 }, { label: 'M7+', color: '#991b1b', size: 16 }].map((e) => (
          <span key={e.label} style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
            <span style={{ width: e.size, height: e.size, borderRadius: '50%', background: e.color, display: 'inline-block' }} />
            <span style={{ fontSize: '10px', color: '#94a3b8' }}>{e.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
  if (activeCategory === 'storms') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Storm Intensity (kt)</div>
      <div style={{ display: 'flex', gap: 0 }}>
        {['#fff', '#eab308', '#f97316', '#dc2626', '#ec4899', '#7c3aed'].map((c, i) => (
          <span key={i} style={{ flex: 1, height: 10, background: c, border: c === '#fff' ? '1px solid #475569' : 'none' }} />
        ))}
      </div>
      <div style={legendLabelsStyle}><span>TD</span><span>TS</span><span>C1</span><span>C2</span><span>C3</span><span>C4+</span></div>
    </div>
  );
  if (activeCategory === 'ocean-crisis') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Ocean Stress Index</div>
      <div style={{ background: 'linear-gradient(to right, rgb(20,60,180), rgb(60,200,160), rgb(200,210,60), rgb(245,140,30), rgb(160,20,80))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>Healthy</span><span>Moderate</span><span>Stressed</span><span>Crisis</span></div>
    </div>
  );
  if (activeCategory === 'sst') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Sea Surface Temperature (°C)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(49,54,149), rgb(116,173,209), rgb(253,174,97), rgb(215,48,39), rgb(165,0,38))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>-2</span><span>8</span><span>18</span><span>26</span><span>32</span></div>
    </div>
  );
  if (activeCategory === 'air-quality') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>PM2.5 (µg/m³)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(0,128,0), rgb(255,255,0), rgb(255,126,0), rgb(255,0,0), rgb(143,63,151), rgb(126,0,35))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>0</span><span>12</span><span>35</span><span>55</span><span>75+</span></div>
    </div>
  );
  if (activeCategory === 'temperature') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>2m Temperature (°C)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(49,54,149), rgb(69,117,180), rgb(116,173,209), rgb(171,217,233), rgb(253,174,97), rgb(244,109,67), rgb(215,48,39), rgb(165,0,38))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>-40</span><span>-20</span><span>0</span><span>20</span><span>50</span></div>
    </div>
  );
  if (activeCategory === 'precipitation') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Precipitation (mm)</div>
      <div style={{ background: 'linear-gradient(to right, rgba(198,219,239,0.3), rgb(158,202,225), rgb(107,174,214), rgb(49,130,189), rgb(8,81,156))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>0</span><span>5</span><span>10</span><span>20+</span></div>
    </div>
  );
  if (activeCategory === 'no2') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>NO₂ (µg/m³)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(255,255,178), rgb(254,204,92), rgb(253,141,60), rgb(240,59,32), rgb(189,0,38))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>0</span><span>20</span><span>40</span><span>60</span><span>80+</span></div>
    </div>
  );
  return null;
}

// ─── Tooltip ──────────────────────────────────────────────────────────────────

function Tooltip({ info }: { info: { x: number; y: number; object: Record<string, unknown>; layer: { id: string } } | null }) {
  if (!info?.object) return null;
  const obj = info.object;
  const layerId = info.layer?.id ?? '';

  let content = '';
  if (layerId === 'fires-layer') {
    const f = obj as unknown as FireHotspot;
    content = `<b>Fire hotspot</b><br/>${f.acq_date} ${f.acq_time} UTC<br/>FRP: ${f.frp?.toFixed(1)} MW<br/>${f.lat?.toFixed(2)}°, ${f.lon?.toFixed(2)}°`;
  } else if (layerId === 'storms-layer') {
    const s = obj as unknown as Storm;
    content = `<b>${s.name}</b> (${s.basin})<br/>${s.iso_time} UTC<br/>Wind: ${s.wind_kt} kt · ${s.pres_hpa} hPa`;
  } else if (layerId === 'earthquakes-layer') {
    const e = obj as unknown as Earthquake;
    content = `<b>M${e.magnitude?.toFixed(1)}</b> — ${e.place}<br/>Depth: ${e.depth_km?.toFixed(1)} km<br/>${e.time_utc} UTC${e.tsunami ? '<br/><span style="color:#ef4444;font-weight:600">⚠ Tsunami</span>' : ''}`;
  } else if (layerId === 'ocean-health-layer') {
    const c = obj as unknown as OceanHealthCell;
    const pct = (c.stress_score * 100).toFixed(0);
    content = `<b>Ocean Stress: ${pct}%</b><br/>SST: ${c.sst_c?.toFixed(1)}°C · DHW: ${c.dhw?.toFixed(1)}<br/>${c.lat?.toFixed(1)}°, ${c.lon?.toFixed(1)}°`;
  }

  if (!content) return null;
  return (
    <div style={{
      position: 'absolute', left: info.x + 14, top: info.y - 14, pointerEvents: 'none',
      background: 'rgba(12,18,32,0.94)', color: '#f1f5f9', padding: '10px 14px',
      border: '1px solid rgba(71,85,105,0.35)', borderRadius: '10px',
      fontSize: '12px', lineHeight: '1.5', fontFamily: 'system-ui, sans-serif',
      maxWidth: 300, zIndex: 25, backdropFilter: 'blur(14px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
    }} dangerouslySetInnerHTML={{ __html: content }} />
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

const GlobeDeck = forwardRef<GlobeHandle, GlobeProps>(function GlobeDeck(
  { activeCategory, onCategoryChange },
  ref,
) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const deckRef = useRef<any>(null);
  const [viewState, setViewState] = useState<GlobeViewState>(INITIAL_VIEW_STATE);
  const [viewMode, setViewMode] = useState<ViewMode>('globe');
  const lastInteractionRef = useRef(0);
  const viewStateRef = useRef(INITIAL_VIEW_STATE);
  const [hoverInfo, setHoverInfo] = useState<{
    x: number; y: number; object: Record<string, unknown>; layer: { id: string };
  } | null>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });

  // ── Lazy data fetches — only fetch what the active category needs ─────────

  const needsFires = activeCategory === 'wildfires';
  const needsOcean = activeCategory === 'ocean-crisis';
  const needsQuakes = activeCategory === 'earthquakes';
  const needsStorms = activeCategory === 'storms';

  const { data: firesData, loading: firesLoading } = useApi<FiresResponse>(
    '/earth-now/fires', needsFires,
  );
  const { data: oceanData, loading: oceanLoading } = useApi<OceanHealthResponse>(
    '/earth-now/integrated/ocean-health', needsOcean,
  );
  const { data: stormsData, loading: stormsLoading } = useApi<StormsResponse>(
    '/earth-now/storms', needsStorms,
  );
  const { data: earthquakeData, loading: quakesLoading } = useApi<EarthquakeResponse>(
    '/hazards/earthquakes?min_magnitude=4&limit=500&days=7', needsQuakes,
  );

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

  useImperativeHandle(ref, () => ({
    flyTo: (lat: number, lng: number, altitude = 1.8) => {
      const zoom = Math.max(0.5, 4 - altitude);
      const vs = { latitude: lat, longitude: lng, zoom };
      viewStateRef.current = vs;
      setViewState(vs);
    },
  }), []);

  const onHover = useCallback((info: unknown) => {
    const i = info as { x: number; y: number; object?: Record<string, unknown>; layer?: { id: string } };
    if (i.object && i.layer) {
      setHoverInfo({ x: i.x, y: i.y, object: i.object, layer: i.layer as { id: string } });
    } else {
      setHoverInfo(null);
    }
  }, []);

  const activeLayers = useMemo(() => {
    const cat = CATEGORIES.find((c) => c.key === activeCategory);
    return new Set(cat?.activates ?? []);
  }, [activeCategory]);

  // ── Build deck.gl layers ──────────────────────────────────────────────────

  const layers = useMemo(() => {
    const result: unknown[] = [];

    // 1. Base tiles
    const baseTileUrl = viewMode === 'globe' ? BLUEMARBLE_TILE_URL : CARTO_DARK_URL;
    result.push(
      new TileLayer({
        id: 'base-tiles',
        data: baseTileUrl,
        minZoom: 0,
        maxZoom: viewMode === 'globe' ? 8 : 19,
        tileSize: 256,
        renderSubLayers: (props: Record<string, unknown>) => {
          const tp = props.tile as { bbox: { west: number; south: number; east: number; north: number } };
          const { west, south, east, north } = tp.bbox;
          return new BitmapLayer({
            ...props, data: undefined,
            image: props.data as string,
            bounds: [west, south, east, north],
          });
        },
      }),
    );

    // 2. GIBS WMS overlay
    const gibsKey = ['gibs-pm25', 'gibs-aod', 'gibs-oco2', 'gibs-flood'].find((k) => activeLayers.has(k));
    if (gibsKey) {
      const gibsLayerName = GIBS_LAYER_NAMES[gibsKey];
      const gibsDate = getGibsDate(gibsKey);
      result.push(
        new TileLayer({
          id: 'gibs-overlay',
          minZoom: 0,
          maxZoom: gibsKey === 'gibs-pm25' ? 6 : 5,
          tileSize: 256,
          opacity: 0.50,
          getTileData: (tileInfo: unknown) => {
            const tile = tileInfo as { bbox: { west: number; south: number; east: number; north: number } };
            const { west, south, east, north } = tile.bbox;
            const url = `${GIBS_WMS_BASE}&LAYERS=${gibsLayerName}&TIME=${gibsDate}&BBOX=${west},${south},${east},${north}&WIDTH=256&HEIGHT=256`;
            return loadWmsImage(url);
          },
          renderSubLayers: (props: Record<string, unknown>) => {
            const tp = props.tile as { bbox: { west: number; south: number; east: number; north: number } };
            const { west, south, east, north } = tp.bbox;
            return new BitmapLayer({
              ...props, data: undefined,
              image: props.data as string,
              bounds: [west, south, east, north],
            });
          },
        }),
      );
    }

    const fade = { getRadius: { duration: 600, easing: (t: number) => t }, getFillColor: { duration: 400 } };

    // 3. Fires — HeatmapLayer (2D) or Density PNG + Scatter (3D)
    if (activeLayers.has('fires') && firesData?.fires) {
      if (viewMode === 'map') {
        result.push(
          new HeatmapLayer({
            id: 'fires-heatmap',
            data: firesData.fires,
            getPosition: (d: FireHotspot) => [d.lon, d.lat],
            getWeight: (d: FireHotspot) => Math.log10(Math.max(d.frp, 1)) + 1,
            radiusPixels: 50,
            intensity: 2,
            threshold: 0.03,
            colorRange: FIRE_HEATMAP_COLORS,
          }),
        );
      } else {
        // Density surface from backend PNG
        result.push(
          new BitmapLayer({
            id: 'fires-density-surface',
            image: `${API_BASE}/earth-now/integrated/fires/density-png`,
            bounds: [-180, -90, 180, 90] as [number, number, number, number],
            opacity: 0.7,
          }),
        );
        // Scatter overlay for hover interaction (top fires by FRP)
        result.push(
          new ScatterplotLayer({
            id: 'fires-layer',
            data: firesData.fires,
            getPosition: (d: FireHotspot) => [d.lon, d.lat],
            getFillColor: (d: FireHotspot) => fireColorRGBA(d.frp),
            getRadius: (d: FireHotspot) => fireRadius(d.frp),
            radiusUnits: 'pixels' as const,
            radiusMinPixels: 2, radiusMaxPixels: 14,
            pickable: true, onHover, antialiasing: true,
            transitions: fade,
          }),
        );
      }
    }

    // 4. Storms — track lines + current position
    if (activeLayers.has('storms') && stormsData?.storms) {
      // Track lines for each storm
      const stormsWithTracks = stormsData.storms.filter((s) => s.track_points && s.track_points.length > 1);
      if (stormsWithTracks.length > 0) {
        result.push(
          new PathLayer({
            id: 'storm-tracks',
            data: stormsWithTracks,
            getPath: (d: Storm) => (d.track_points ?? []).map((tp) => [tp.lon, tp.lat] as [number, number]),
            getColor: (d: Storm) => stormColorRGBA(d.wind_kt),
            getWidth: 2,
            widthUnits: 'pixels' as const,
            widthMinPixels: 1,
            widthMaxPixels: 4,
            jointRounded: true,
            capRounded: true,
            pickable: false,
          }),
        );
      }
      // Current position dots
      result.push(
        new ScatterplotLayer({
          id: 'storms-layer',
          data: stormsData.storms,
          getPosition: (d: Storm) => [d.lon, d.lat],
          getFillColor: (d: Storm) => stormColorRGBA(d.wind_kt),
          getRadius: (d: Storm) => stormRadius(d.wind_kt),
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 3, radiusMaxPixels: 18,
          stroked: true, getLineColor: rgbArr(255, 255, 255, 100), lineWidthMinPixels: 1,
          pickable: true, onHover, transitions: fade,
        }),
      );
    }

    // 5. Earthquakes — glow + core
    if (activeLayers.has('earthquakes') && earthquakeData?.earthquakes) {
      result.push(
        new ScatterplotLayer({
          id: 'earthquakes-glow',
          data: earthquakeData.earthquakes,
          getPosition: (d: Earthquake) => [d.lon, d.lat],
          getFillColor: (d: Earthquake) => { const c = earthquakeColorRGBA(d.magnitude); return [c[0], c[1], c[2], 60] as [number, number, number, number]; },
          getRadius: (d: Earthquake) => earthquakeRadius(d.magnitude) * 2,
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 6, radiusMaxPixels: 48,
          pickable: false,
        }),
      );
      result.push(
        new ScatterplotLayer({
          id: 'earthquakes-layer',
          data: earthquakeData.earthquakes,
          getPosition: (d: Earthquake) => [d.lon, d.lat],
          getFillColor: (d: Earthquake) => earthquakeColorRGBA(d.magnitude),
          getRadius: (d: Earthquake) => earthquakeRadius(d.magnitude),
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 3, radiusMaxPixels: 24,
          stroked: true, getLineColor: rgbArr(255, 255, 255, 100), lineWidthMinPixels: 1,
          pickable: true, onHover, transitions: fade,
        }),
      );
    }

    // 6. Ocean Health — continuous surface + tooltip scatter overlay
    if (activeLayers.has('ocean-integrated')) {
      // Continuous surface from backend PNG
      result.push(
        new BitmapLayer({
          id: 'ocean-surface',
          image: `${API_BASE}/earth-now/integrated/ocean/surface-png`,
          bounds: [-180, -90, 180, 90] as [number, number, number, number],
          opacity: 0.65,
        }),
      );
      // Sparse scatter overlay for hover tooltips (from existing JSON grid)
      if (oceanData?.grid) {
        // Show top stressed cells for tooltip interaction
        const topCells = [...oceanData.grid]
          .sort((a, b) => b.stress_score - a.stress_score)
          .slice(0, 300);
        result.push(
          new ScatterplotLayer({
            id: 'ocean-health-layer',
            data: topCells,
            getPosition: (d: OceanHealthCell) => [d.lon, d.lat],
            getFillColor: (d: OceanHealthCell) => { const c = oceanStressColor(d.stress_score); return [c[0], c[1], c[2], 0] as [number, number, number, number]; },
            getRadius: 20,
            radiusUnits: 'pixels' as const,
            radiusMinPixels: 10, radiusMaxPixels: 30,
            pickable: true, onHover,
          }),
        );
      }
    }

    // 7-11. Self-rendered continuous surfaces via TileLayer
    // Uses tile endpoint to crop the full PNG into small regions,
    // avoiding polygon distortion on GlobeView.
    const surfaceLayers: Array<{ key: string; layer: string; opacity: number }> = [
      { key: 'sst-surface', layer: 'sst', opacity: 0.85 },
      { key: 'pm25-surface', layer: 'pm25', opacity: 0.8 },
      { key: 'temp-surface', layer: 'temperature', opacity: 0.8 },
      { key: 'precip-surface', layer: 'precipitation', opacity: 0.75 },
      { key: 'no2-surface', layer: 'no2', opacity: 0.8 },
    ];

    for (const surf of surfaceLayers) {
      if (activeLayers.has(surf.key)) {
        result.push(
          new TileLayer({
            id: `${surf.key}-tiles`,
            minZoom: 0,
            maxZoom: 5,
            tileSize: 256,
            opacity: surf.opacity,
            getTileData: (tileInfo: unknown) => {
              const tile = tileInfo as { bbox: { west: number; south: number; east: number; north: number } };
              const { west, south, east, north } = tile.bbox;
              const url = `${API_BASE}/globe/surface/tile/${surf.layer}?west=${west}&south=${south}&east=${east}&north=${north}`;
              return fetch(url, { mode: 'cors' })
                .then((r) => {
                  if (!r.ok || r.status === 204) return null;
                  return r.blob();
                })
                .then((b) => b ? createImageBitmap(b) : null);
            },
            renderSubLayers: (props: Record<string, unknown>) => {
              const tp = props.tile as { bbox: { west: number; south: number; east: number; north: number } };
              const { west, south, east, north } = tp.bbox;
              return new BitmapLayer({
                ...props, data: undefined,
                image: props.data as string,
                bounds: [west, south, east, north],
              });
            },
          }),
        );
        break; // Only one surface at a time
      }
    }

    return result;
  }, [activeLayers, viewMode, firesData, stormsData, earthquakeData, oceanData, onHover]);

  // ── Deck instance ────────────────────────────────────────────────────────

  useEffect(() => {
    if (!canvasRef.current) return;
    const currentView = viewMode === 'globe'
      ? new GlobeView({ id: 'globe', controller: true })
      : new MapView({ id: 'globe', controller: true });

    if (!deckRef.current) {
      deckRef.current = new Deck({
        canvas: canvasRef.current,
        width: dims.width, height: dims.height,
        initialViewState: viewMode === 'map' ? { ...INITIAL_VIEW_STATE, zoom: 2 } : INITIAL_VIEW_STATE,
        views: currentView,
        layers: layers as never[],
        onViewStateChange: ({ viewState: vs }: { viewState: Record<string, unknown> }) => {
          lastInteractionRef.current = Date.now();
          const newVs = vs as unknown as GlobeViewState;
          viewStateRef.current = newVs;
          setViewState(newVs);
        },
        getCursor: ({ isHovering }: { isHovering: boolean }) => isHovering ? 'pointer' : 'grab',
      });
    } else {
      deckRef.current.setProps({
        width: dims.width, height: dims.height,
        views: currentView, layers: layers as never[], viewState,
      });
    }
  }, [layers, dims, viewMode, viewState]);

  useEffect(() => {
    return () => { deckRef.current?.finalize(); deckRef.current = null; };
  }, []);

  // Auto-rotation (globe only, 6s idle)
  useEffect(() => {
    if (viewMode !== 'globe') return;
    let rafId: number;
    const rotate = () => {
      if (Date.now() - lastInteractionRef.current > 6000 && deckRef.current) {
        const vs = { ...viewStateRef.current };
        vs.longitude = (vs.longitude + 0.015) % 360;
        viewStateRef.current = vs;
        deckRef.current.setProps({ viewState: vs });
      }
      rafId = requestAnimationFrame(rotate);
    };
    rafId = requestAnimationFrame(rotate);
    return () => cancelAnimationFrame(rafId);
  }, [viewMode]);

  // ── Status ───────────────────────────────────────────────────────────────

  const activeCatDef = activeCategory ? CATEGORY_LOOKUP.get(activeCategory) ?? null : null;

  const dataCount = useMemo(() => {
    if (activeCategory === 'wildfires') return firesData?.fires?.length ?? 0;
    if (activeCategory === 'storms') return stormsData?.storms?.length ?? 0;
    if (activeCategory === 'earthquakes') return earthquakeData?.earthquakes?.length ?? 0;
    if (activeCategory === 'ocean-crisis') return oceanData?.grid?.length ?? 0;
    return 0;
  }, [activeCategory, firesData, stormsData, earthquakeData, oceanData]);

  const isActiveLoading =
    (needsFires && firesLoading) ||
    (needsOcean && oceanLoading) ||
    (needsQuakes && quakesLoading) ||
    (needsStorms && stormsLoading);

  return (
    <div ref={containerRef} style={containerStyle}>
      {viewMode === 'globe' && <div style={atmosphereGlowStyle} />}

      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', position: 'relative', zIndex: 1 }} />

      <div style={{ position: 'absolute', inset: 0, zIndex: 2, pointerEvents: 'none', boxShadow: 'inset 0 0 150px 60px rgba(2,4,8,0.5)' }} />

      {/* Category-specific loading */}
      {isActiveLoading && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 5,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          pointerEvents: 'none',
        }}>
          <div style={{ textAlign: 'center', animation: 'fadeInUp 0.3s ease-out' }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              border: '2px solid #1e293b', borderTopColor: activeCatDef?.activeColor ?? '#3b82f6',
              animation: 'spin 0.8s linear infinite', margin: '0 auto 8px',
            }} />
            <div style={{ color: '#64748b', fontSize: '11px', fontFamily: 'system-ui, sans-serif' }}>
              Loading {activeCatDef?.name ?? 'data'}…
            </div>
          </div>
        </div>
      )}

      <Tooltip info={hoverInfo} />

      {/* Active category pill */}
      {activeCatDef && (
        <div style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
          zIndex: 10,
          background: 'rgba(10,14,26,0.75)', backdropFilter: 'blur(12px)',
          border: '1px solid rgba(51,65,85,0.3)', borderRadius: '20px',
          padding: '5px 16px', fontSize: '12px', color: '#cbd5e1',
          fontFamily: 'system-ui, sans-serif',
          display: 'flex', alignItems: 'center', gap: '8px',
        }}>
          <span style={{ fontSize: '14px' }}>{activeCatDef.icon}</span>
          <span style={{ fontWeight: 600 }}>{activeCatDef.name}</span>
          {dataCount > 0 && (
            <span style={{ color: '#64748b', fontSize: '11px' }}>{dataCount.toLocaleString()}</span>
          )}
          <span style={{ color: '#475569', fontSize: '10px' }}>{activeCatDef.question}</span>
        </div>
      )}

      {activeCatDef && (
        <div style={metaOverlayStyle}>
          <MetaLine cadence={activeCatDef.cadence} tag={activeCatDef.tag} source={activeCatDef.source} sourceUrl={activeCatDef.sourceUrl} />
        </div>
      )}

      <div style={{ position: 'absolute', bottom: 48, left: 0, right: 0, height: 40, zIndex: 14, background: 'linear-gradient(to bottom, transparent, rgba(10,14,26,0.35))', pointerEvents: 'none' }} />

      <Legend activeCategory={activeCategory} />

      <div style={{
        position: 'absolute', bottom: 60, right: 12, zIndex: 10,
        background: 'rgba(10,14,26,0.5)', borderRadius: '4px',
        padding: '3px 8px', fontSize: '10px', color: '#475569',
        fontFamily: 'ui-monospace, monospace', pointerEvents: 'none',
      }}>
        {viewState.latitude.toFixed(1)}° {viewState.longitude.toFixed(1)}° z{viewState.zoom.toFixed(1)}
      </div>

      <LayerBar
        activeCategory={activeCategory}
        onCategoryChange={onCategoryChange}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />
    </div>
  );
});

export default GlobeDeck;

// ─── Styles ───────────────────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  position: 'relative', width: '100%', height: '100%',
  background: 'radial-gradient(ellipse at 50% 48%, #0b1030 0%, #060a1a 40%, #020408 100%)',
  overflow: 'hidden',
};

const atmosphereGlowStyle: React.CSSProperties = {
  position: 'absolute', inset: 0, zIndex: 0,
  background: [
    'radial-gradient(circle at 50% 50%, rgba(40,80,200,0.14) 0%, rgba(30,70,180,0.06) 28%, transparent 52%)',
    'radial-gradient(circle at 48% 52%, rgba(20,60,160,0.08) 0%, transparent 42%)',
    'radial-gradient(circle at 52% 48%, rgba(60,120,255,0.04) 0%, transparent 38%)',
  ].join(', '),
  pointerEvents: 'none',
  animation: 'atmosphere-pulse 8s ease-in-out infinite',
};

const metaOverlayStyle: React.CSSProperties = {
  position: 'absolute', top: 12, left: 12, zIndex: 10,
  background: 'rgba(10,14,26,0.5)', padding: '5px 10px',
  borderRadius: '6px', backdropFilter: 'blur(8px)', pointerEvents: 'none',
  border: '1px solid rgba(51,65,85,0.2)',
};

const layerBarStyle: React.CSSProperties = {
  position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 15,
  background: 'rgba(10,14,26,0.85)', backdropFilter: 'blur(12px)',
  borderTop: '1px solid rgba(51,65,85,0.3)',
  padding: '8px 16px',
};

const legendStyle: React.CSSProperties = {
  position: 'absolute', bottom: 60, left: 12, zIndex: 10,
  background: 'rgba(10,14,26,0.82)', backdropFilter: 'blur(8px)',
  border: '1px solid rgba(51,65,85,0.4)', borderRadius: '8px',
  padding: '8px 12px', minWidth: 160, maxWidth: 260,
};

const legendTitleStyle: React.CSSProperties = {
  fontSize: '11px', fontWeight: 600, color: '#cbd5e1',
  marginBottom: 6, fontFamily: 'system-ui, sans-serif',
};

const legendLabelsStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between',
  fontSize: '9px', color: '#64748b', marginTop: 2,
  fontFamily: 'system-ui, sans-serif',
};
