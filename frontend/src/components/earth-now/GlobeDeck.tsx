import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Deck, _GlobeView as GlobeView } from '@deck.gl/core';
import { BitmapLayer, ScatterplotLayer } from '@deck.gl/layers';
import { TileLayer } from '@deck.gl/geo-layers';

import MetaLine from '../common/MetaLine';
import { TrustTag } from '../../utils/trustTags';
import { useApi } from '../../hooks/useApi';

// ─── Types ────────────────────────────────────────────────────────────────────

export type ActiveEvent = 'fires' | 'storms' | 'monitors' | 'earthquakes' | null;
export type ActiveContinuous =
  | 'ocean-heat' | 'coral' | 'cmems-sla'
  | 'gibs-aod' | 'gibs-pm25' | 'gibs-oco2' | 'gibs-flood'
  | null;
export type ViewMode = 'globe' | 'map';

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
  lat: number; lon: number; brightness: number; frp: number;
  confidence: string; acq_date: string; acq_time: string; daynight: string;
}
interface FiresResponse { count: number; configured: boolean; message?: string; fires: FireHotspot[]; }

interface SstPoint { lat: number; lon: number; sst_c: number; }
interface SstResponse { count: number; configured: boolean; stats: { min_c: number | null; max_c: number | null; mean_c: number | null }; points: SstPoint[]; }

interface AirMonitor { lat: number; lon: number; pm25: number; location_name: string; datetime_utc: string; country: string | null; }
interface AirMonitorsResponse { count: number; configured: boolean; message?: string; monitors: AirMonitor[]; }

interface Storm { sid: string; name: string; basin: string; season: string; lat: number; lon: number; wind_kt: number; pres_hpa: number; sshs: number; iso_time: string; }
interface StormsResponse { count: number; configured: boolean; storms: Storm[]; }

interface Earthquake { lat: number; lon: number; depth_km: number; magnitude: number; place: string; time_utc: string; event_url: string; tsunami: boolean; }
interface EarthquakeResponse { count: number; configured: boolean; status: string; earthquakes: Earthquake[]; }

interface CoralPoint { lat: number; lon: number; bleaching_alert: number; dhw: number; sst_c: number; sst_anomaly_c: number; }
interface CoralResponse { count: number; configured: boolean; status: string; points: CoralPoint[]; }

interface SlaPoint { lat: number; lon: number; sla_m: number; }
interface SlaResponse { count: number; configured: boolean; status: string; message?: string; points: SlaPoint[]; }

// ─── BlueMarble Tile URL ──────────────────────────────────────────────────────

const BLUEMARBLE_TILE_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/BlueMarble_ShadedRelief_Bathymetry/default/2004-08/{z}/{y}/{x}.jpg';

// ─── GIBS WMS overlay ─────────────────────────────────────────────────────────

const GIBS_WMS_BASE =
  'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
  '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1' +
  '&STYLES=&FORMAT=image/png&TRANSPARENT=TRUE&SRS=EPSG:4326';

const GIBS_LAYER_NAMES: Record<string, string> = {
  'gibs-pm25': 'MERRA2_Total_Aerosol_Optical_Thickness_550nm_Scattering_Monthly',
  'gibs-aod': 'MODIS_Terra_Aerosol_Optical_Depth_3km',
  'gibs-oco2': 'OCO2_CO2_Column_Daily',
  'gibs-flood': 'MODIS_Terra_Flood_3-Day',
};

function getGibsDate(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1); // yesterday for data availability
  return d.toISOString().slice(0, 10);
}

// ─── Layer category definitions ───────────────────────────────────────────────

interface LayerDef {
  key: string; label: string; type: 'event' | 'continuous';
  activeColor: string; tag: TrustTag; cadence: string;
  source: string; sourceUrl: string; available: boolean; note?: string;
}

interface CategoryDef { name: string; layers: LayerDef[]; }

const CATEGORIES: CategoryDef[] = [
  {
    name: 'Atmosphere',
    layers: [
      { key: 'gibs-pm25', label: 'PM2.5 (MERRA-2)', type: 'continuous', activeColor: '#a855f7', tag: TrustTag.Derived, cadence: 'Monthly', source: 'NASA GIBS / MERRA-2', sourceUrl: 'https://disc.gsfc.nasa.gov/datasets/M2TMNXAER_5.12.4/', available: true },
      { key: 'gibs-aod', label: 'Aerosol Optical Depth', type: 'continuous', activeColor: '#f59e0b', tag: TrustTag.NearRealTime, cadence: 'Daily', source: 'NASA GIBS / MODIS Terra', sourceUrl: 'https://worldview.earthdata.nasa.gov/', available: true },
      { key: 'monitors', label: 'Air Monitors (PM2.5)', type: 'event', activeColor: '#ca8a04', tag: TrustTag.Observed, cadence: 'Varies', source: 'OpenAQ', sourceUrl: 'https://openaq.org/', available: true },
    ],
  },
  {
    name: 'Fire & Land',
    layers: [
      { key: 'fires', label: 'Active Fires', type: 'event', activeColor: '#dc2626', tag: TrustTag.NearRealTime, cadence: 'NRT ~3h', source: 'NASA FIRMS', sourceUrl: 'https://firms.modaps.eosdis.nasa.gov/', available: true },
      { key: 'deforestation', label: 'Deforestation', type: 'continuous', activeColor: '#16a34a', tag: TrustTag.Derived, cadence: 'Annual', source: 'Hansen / GFW', sourceUrl: 'https://www.globalforestwatch.org/', available: false, note: 'Country-level points require polygon query (P1)' },
      { key: 'drought', label: 'Drought Index', type: 'continuous', activeColor: '#b45309', tag: TrustTag.Derived, cadence: 'Weekly', source: 'JRC GWIS', sourceUrl: 'https://gwis.jrc.ec.europa.eu/', available: false, note: 'JRC GWIS drought index — Phase P1' },
    ],
  },
  {
    name: 'Ocean',
    layers: [
      { key: 'ocean-heat', label: 'Sea Surface Temp', type: 'continuous', activeColor: '#0284c7', tag: TrustTag.Observed, cadence: 'Daily', source: 'NOAA OISST v2.1', sourceUrl: 'https://coralreefwatch.noaa.gov/product/5km/', available: true },
      { key: 'coral', label: 'Coral Bleaching Alert', type: 'continuous', activeColor: '#f97316', tag: TrustTag.NearRealTime, cadence: 'Daily', source: 'NOAA Coral Reef Watch', sourceUrl: 'https://coralreefwatch.noaa.gov/', available: true },
      { key: 'cmems-sla', label: 'Sea Level Anomaly', type: 'continuous', activeColor: '#3b82f6', tag: TrustTag.Derived, cadence: 'Daily', source: 'CMEMS / Copernicus Marine', sourceUrl: 'https://marine.copernicus.eu/', available: true },
    ],
  },
  {
    name: 'GHG',
    layers: [
      { key: 'gibs-oco2', label: 'CO₂ Column (OCO-2)', type: 'continuous', activeColor: '#22c55e', tag: TrustTag.Observed, cadence: 'Daily', source: 'NASA GIBS / OCO-2', sourceUrl: 'https://ocov2.jpl.nasa.gov/', available: true },
      { key: 'gibs-ch4', label: 'CH₄ (TROPOMI)', type: 'continuous', activeColor: '#84cc16', tag: TrustTag.Observed, cadence: 'Daily', source: 'Copernicus GES DISC', sourceUrl: 'https://disc.gsfc.nasa.gov/', available: false, note: 'Satellite data coming soon' },
    ],
  },
  {
    name: 'Hazards',
    layers: [
      { key: 'storms', label: 'Tropical Storms', type: 'event', activeColor: '#ec4899', tag: TrustTag.NearRealTime, cadence: 'NRT ~6h', source: 'ATCF / IBTrACS', sourceUrl: 'https://www.nrlmry.navy.mil/atcf_web/atlas/ibtracks/', available: true },
      { key: 'earthquakes', label: 'Earthquakes (M4+)', type: 'event', activeColor: '#ef4444', tag: TrustTag.Observed, cadence: 'NRT ~5 min', source: 'USGS', sourceUrl: 'https://earthquake.usgs.gov/', available: true },
      { key: 'gibs-flood', label: 'Flood Detection', type: 'continuous', activeColor: '#0ea5e9', tag: TrustTag.NearRealTime, cadence: '3-Day', source: 'NASA GIBS / MODIS Terra', sourceUrl: 'https://worldview.earthdata.nasa.gov/', available: true },
    ],
  },
];

const LAYER_LOOKUP = new Map<string, LayerDef>(
  CATEGORIES.flatMap((c) => c.layers.map((l) => [l.key, l] as [string, LayerDef])),
);

const TRUST_TAG_COLORS: Record<TrustTag, string> = {
  [TrustTag.Observed]: '#22c55e',
  [TrustTag.NearRealTime]: '#f59e0b',
  [TrustTag.ForecastModel]: '#8b5cf6',
  [TrustTag.Derived]: '#64748b',
  [TrustTag.Estimated]: '#6b7280',
};

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
  if (frp >= 500) return rgbArr(127, 29, 29, 230);
  if (frp >= 100) return rgbArr(220, 38, 38, 220);
  if (frp >= 50) return rgbArr(249, 115, 22, 200);
  if (frp >= 10) return rgbArr(234, 179, 8, 190);
  return rgbArr(253, 224, 71, 180);
}

function fireRadius(frp: number): number {
  return Math.max(3, Math.min(12, 3 + Math.log10(Math.max(frp, 1)) * 3));
}

function sstColorRGBA(c: number): [number, number, number, number] {
  return lerpColor([
    [-2, [8, 20, 80]], [5, [20, 90, 180]], [12, [30, 160, 200]],
    [18, [80, 200, 140]], [24, [240, 200, 40]], [28, [230, 100, 20]], [32, [180, 10, 10]],
  ], c);
}

function pm25ColorRGBA(pm: number): [number, number, number, number] {
  if (pm <= 12) return rgbArr(0, 228, 0, 200);
  if (pm <= 35.4) return rgbArr(255, 255, 0, 200);
  if (pm <= 55.4) return rgbArr(255, 126, 0, 210);
  if (pm <= 150.4) return rgbArr(255, 0, 0, 220);
  if (pm <= 250.4) return rgbArr(143, 63, 151, 230);
  return rgbArr(126, 0, 35, 240);
}

function dhwColorRGBA(dhw: number): [number, number, number, number] {
  return lerpColor([
    [0, [200, 200, 255]], [4, [255, 255, 0]], [8, [255, 165, 0]],
    [12, [220, 38, 38]], [16, [126, 34, 206]],
  ], dhw);
}

function slaColorRGBA(sla_m: number): [number, number, number, number] {
  return lerpColor([
    [-0.3, [59, 130, 246]], [0, [200, 200, 255]], [0.3, [220, 38, 38]],
  ], sla_m);
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

// ─── ViewState type ───────────────────────────────────────────────────────────

interface GlobeViewState {
  longitude: number;
  latitude: number;
  zoom: number;
}

const INITIAL_VIEW_STATE: GlobeViewState = {
  longitude: 0,
  latitude: 20,
  zoom: 1.2,
};

// ─── LayerPanel ───────────────────────────────────────────────────────────────

interface LayerPanelProps {
  activeEvent: ActiveEvent;
  activeContinuous: ActiveContinuous;
  onLayerChange: (type: 'event' | 'continuous', key: string | null) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  slaConfigured: boolean;
  slaStatus?: string;
  airConfigured: boolean;
}

function LayerPanel({
  activeEvent, activeContinuous, onLayerChange,
  viewMode, onViewModeChange,
  slaConfigured, slaStatus, airConfigured,
}: LayerPanelProps) {
  const [openCategory, setOpenCategory] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const isActive = (layer: LayerDef): boolean =>
    layer.type === 'event' ? activeEvent === layer.key : activeContinuous === layer.key;

  const isDisabled = (layer: LayerDef): boolean => {
    if (!layer.available) return true;
    if (layer.key === 'cmems-sla' && !slaConfigured) return true;
    if (layer.key === 'monitors' && !airConfigured) return true;
    return false;
  };

  return (
    <div style={layerPanelStyle}>
      {/* View mode toggle */}
      <div style={{ display: 'flex', borderBottom: '1px solid #1e293b' }}>
        {(['globe', 'map'] as ViewMode[]).map((m) => (
          <button key={m} type="button" onClick={() => onViewModeChange(m)}
            style={{
              flex: 1, padding: '6px 0', background: viewMode === m ? 'rgba(59,130,246,0.2)' : 'none',
              border: 'none', borderBottom: viewMode === m ? '2px solid #3b82f6' : '2px solid transparent',
              color: viewMode === m ? '#e2e8f0' : '#64748b', fontSize: '11px', fontWeight: 600,
              cursor: 'pointer', fontFamily: 'system-ui, sans-serif', textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
            {m === 'globe' ? '🌍 Globe' : '🗺️ Map'}
          </button>
        ))}
      </div>

      {/* Layers header */}
      <button type="button" onClick={() => setPanelOpen((v) => !v)}
        style={layerHeaderBtnStyle}>
        <span>Layers</span>
        <span style={{ fontSize: '10px', color: '#64748b' }}>{panelOpen ? '▲' : '▼'}</span>
      </button>

      {panelOpen && (
        <div style={{ borderTop: '1px solid #1e293b' }}>
          {CATEGORIES.map((cat) => (
            <div key={cat.name}>
              <button type="button"
                onClick={() => setOpenCategory((prev) => prev === cat.name ? null : cat.name)}
                style={categoryBtnStyle}>
                <span>{cat.name}</span>
                <span>{openCategory === cat.name ? '▲' : '▼'}</span>
              </button>
              {openCategory === cat.name && (
                <div style={{ padding: '4px 8px 8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {cat.layers.map((layer) => {
                    const active = isActive(layer);
                    const disabled = isDisabled(layer);
                    const tagColor = TRUST_TAG_COLORS[layer.tag];
                    const tooltipNote = disabled
                      ? (layer.note ?? (layer.key === 'cmems-sla'
                        ? slaStatus === 'pending' ? 'Sea level data migration in progress — coming soon'
                          : slaStatus === 'error' ? 'Sea level service error — check backend logs'
                            : 'CMEMS credentials not configured'
                        : layer.key === 'monitors' ? 'OPENAQ_API_KEY not configured' : undefined))
                      : undefined;

                    return (
                      <button key={layer.key} type="button" disabled={disabled}
                        aria-pressed={active} title={tooltipNote}
                        onClick={() => !disabled && onLayerChange(layer.type, active ? null : layer.key)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '6px', padding: '5px 8px',
                          fontSize: '12px', fontWeight: active ? 600 : 400,
                          border: '1px solid', borderRadius: '5px',
                          cursor: disabled ? 'not-allowed' : 'pointer',
                          fontFamily: 'system-ui, sans-serif',
                          background: active ? layer.activeColor : '#1e293b',
                          color: active ? '#fff' : '#94a3b8',
                          borderColor: active ? layer.activeColor : '#334155',
                          opacity: disabled ? 0.4 : 1, textAlign: 'left',
                        }}>
                        <span style={{
                          display: 'inline-block', width: 7, height: 7,
                          borderRadius: '50%', background: tagColor, flexShrink: 0,
                        }} />
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

// ─── Legend component ─────────────────────────────────────────────────────────

function Legend({ activeEvent, activeContinuous }: { activeEvent: ActiveEvent; activeContinuous: ActiveContinuous }) {
  if (activeEvent === 'fires') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Fire Radiative Power (MW)</div>
      <div style={legendBarStyle}>
        <span style={{ ...legendSwatch, background: '#fde047' }} />
        <span style={{ ...legendSwatch, background: '#eab308' }} />
        <span style={{ ...legendSwatch, background: '#f97316' }} />
        <span style={{ ...legendSwatch, background: '#dc2626' }} />
        <span style={{ ...legendSwatch, background: '#7f1d1d' }} />
      </div>
      <div style={legendLabelsStyle}><span>0</span><span>10</span><span>50</span><span>100</span><span>500+</span></div>
    </div>
  );
  if (activeEvent === 'monitors') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>PM2.5 AQI</div>
      <div style={legendBarStyle}>
        <span style={{ ...legendSwatch, background: '#00e400' }} />
        <span style={{ ...legendSwatch, background: '#ffff00' }} />
        <span style={{ ...legendSwatch, background: '#ff7e00' }} />
        <span style={{ ...legendSwatch, background: '#ff0000' }} />
        <span style={{ ...legendSwatch, background: '#8f3f97' }} />
        <span style={{ ...legendSwatch, background: '#7e0023' }} />
      </div>
      <div style={legendLabelsStyle}><span>Good</span><span>Mod</span><span>USG</span><span>Unhealthy</span><span>VU</span><span>Haz</span></div>
    </div>
  );
  if (activeEvent === 'earthquakes') return (
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
  if (activeEvent === 'storms') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Storm Wind Speed (kt)</div>
      <div style={legendBarStyle}>
        <span style={{ ...legendSwatch, background: '#fff', border: '1px solid #475569' }} />
        <span style={{ ...legendSwatch, background: '#eab308' }} />
        <span style={{ ...legendSwatch, background: '#f97316' }} />
        <span style={{ ...legendSwatch, background: '#dc2626' }} />
        <span style={{ ...legendSwatch, background: '#ec4899' }} />
        <span style={{ ...legendSwatch, background: '#7c3aed' }} />
      </div>
      <div style={legendLabelsStyle}><span>TD</span><span>TS</span><span>C1</span><span>C2</span><span>C3</span><span>C4+</span></div>
    </div>
  );
  if (activeContinuous === 'ocean-heat') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Sea Surface Temperature (°C)</div>
      <div style={{ ...legendBarStyle, background: 'linear-gradient(to right, rgb(8,20,80), rgb(20,90,180), rgb(80,200,140), rgb(240,200,40), rgb(180,10,10))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>-2</span><span>5</span><span>15</span><span>25</span><span>32+</span></div>
    </div>
  );
  if (activeContinuous === 'coral') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Degree Heating Weeks (°C-weeks)</div>
      <div style={{ ...legendBarStyle, background: 'linear-gradient(to right, rgb(200,200,255), rgb(255,255,0), rgb(255,165,0), rgb(220,38,38), rgb(126,34,206))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>0</span><span>4</span><span>8</span><span>12</span><span>16+</span></div>
    </div>
  );
  return null;
}

// ─── Tooltip component ────────────────────────────────────────────────────────

function Tooltip({ info }: { info: { x: number; y: number; object: Record<string, unknown>; layer: { id: string } } | null }) {
  if (!info?.object) return null;
  const obj = info.object;
  const layerId = info.layer?.id ?? '';

  let content = '';
  if (layerId === 'fires-layer') {
    const f = obj as unknown as FireHotspot;
    content = `<b>FIRMS hotspot</b><br/>${f.acq_date} ${f.acq_time} UTC (${f.daynight === 'D' ? 'day' : 'night'})<br/>FRP: ${f.frp?.toFixed(1)} MW · confidence: ${f.confidence || '—'}<br/>${f.lat?.toFixed(2)}°, ${f.lon?.toFixed(2)}°`;
  } else if (layerId === 'storms-layer') {
    const s = obj as unknown as Storm;
    content = `<b>${s.name}</b> (${s.basin} basin)<br/>${s.iso_time} UTC<br/>Wind: ${s.wind_kt} kt · Pressure: ${s.pres_hpa} hPa · SSHS: ${s.sshs}<br/>${s.lat?.toFixed(2)}°, ${s.lon?.toFixed(2)}°`;
  } else if (layerId === 'earthquakes-layer') {
    const e = obj as unknown as Earthquake;
    content = `<b>M${e.magnitude?.toFixed(1)}</b> — ${e.place}<br/>Depth: ${e.depth_km?.toFixed(1)} km<br/>${e.time_utc} UTC${e.tsunami ? '<br/><span style="color:#ef4444;font-weight:600;">⚠ Tsunami flag</span>' : ''}<br/><span style="color:#94a3b8;">${e.lat?.toFixed(2)}°, ${e.lon?.toFixed(2)}°</span>`;
  } else if (layerId === 'monitors-layer') {
    const m = obj as unknown as AirMonitor;
    content = `<b>${m.location_name}</b>${m.country ? ` · ${m.country}` : ''}<br/>PM2.5: ${m.pm25?.toFixed(1)} µg/m³<br/><span style="color:#94a3b8;">${m.datetime_utc || '—'}</span>`;
  } else if (layerId === 'sst-layer') {
    const s = obj as unknown as SstPoint;
    content = `<b>Ocean Heat</b><br/>SST: ${s.sst_c?.toFixed(1)}°C<br/>${s.lat?.toFixed(2)}°, ${s.lon?.toFixed(2)}°`;
  } else if (layerId === 'coral-layer') {
    const c = obj as unknown as CoralPoint;
    content = `<b>Coral Bleaching</b><br/>DHW: ${c.dhw?.toFixed(1)} °C-weeks<br/>SST: ${c.sst_c?.toFixed(1)}°C<br/>${c.lat?.toFixed(2)}°, ${c.lon?.toFixed(2)}°`;
  } else if (layerId === 'sla-layer') {
    const s = obj as unknown as SlaPoint;
    content = `<b>Sea Level Anomaly</b><br/>SLA: ${s.sla_m >= 0 ? '+' : ''}${s.sla_m?.toFixed(3)} m<br/>${s.lat?.toFixed(2)}°, ${s.lon?.toFixed(2)}°`;
  }

  if (!content) return null;

  return (
    <div style={{
      position: 'absolute', left: info.x + 12, top: info.y - 12, pointerEvents: 'none',
      background: 'rgba(10,14,26,0.92)', color: '#f1f5f9', padding: '8px 10px',
      border: '1px solid #475569', borderRadius: '6px', fontSize: '11px',
      fontFamily: 'system-ui, sans-serif', maxWidth: 280, zIndex: 20,
      backdropFilter: 'blur(8px)',
    }} dangerouslySetInnerHTML={{ __html: content }} />
  );
}

// ─── Main Globe component ─────────────────────────────────────────────────────

const GlobeDeck = forwardRef<GlobeHandle, GlobeProps>(function GlobeDeck(
  { activeEvent, activeContinuous, onLayerChange },
  ref,
) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const deckRef = useRef<any>(null);
  const [viewState, setViewState] = useState<GlobeViewState>(INITIAL_VIEW_STATE);
  const [viewMode, setViewMode] = useState<ViewMode>('globe');
  const [hoverInfo, setHoverInfo] = useState<{
    x: number; y: number; object: Record<string, unknown>; layer: { id: string };
  } | null>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });

  // Data fetches
  const { data: firesData } = useApi<FiresResponse>('/earth-now/fires');
  const { data: sstData } = useApi<SstResponse>('/earth-now/sst');
  const { data: airData } = useApi<AirMonitorsResponse>('/earth-now/air-monitors');
  const { data: stormsData } = useApi<StormsResponse>('/earth-now/storms');
  const { data: coralData } = useApi<CoralResponse>('/earth-now/coral');
  const { data: slaData } = useApi<SlaResponse>('/earth-now/sea-level-anomaly');
  const { data: earthquakeData } = useApi<EarthquakeResponse>('/hazards/earthquakes?min_magnitude=4&limit=500&days=7');

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

  // Expose flyTo
  useImperativeHandle(ref, () => ({
    flyTo: (lat: number, lng: number, altitude = 1.8) => {
      const zoom = Math.max(0.5, 4 - altitude);
      setViewState({ latitude: lat, longitude: lng, zoom });
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

  // ── Build deck.gl layers ──────────────────────────────────────────────────

  const layers = useMemo(() => {
    const result: unknown[] = [];
    const gibsDate = getGibsDate();

    // 1. BlueMarble base tile layer
    result.push(
      new TileLayer({
        id: 'bluemarble-tiles',
        data: BLUEMARBLE_TILE_URL,
        minZoom: 0,
        maxZoom: 5,
        tileSize: 512,
        renderSubLayers: (props: Record<string, unknown>) => {
          const tileProps = props.tile as {
            bbox: { west: number; south: number; east: number; north: number };
          };
          const { west, south, east, north } = tileProps.bbox;
          return new BitmapLayer({
            ...props,
            data: undefined,
            image: props.data as string,
            bounds: [west, south, east, north],
          });
        },
      }),
    );

    // 2. GIBS overlay tile layer (for gibs-* continuous layers)
    const gibsLayerName = activeContinuous ? GIBS_LAYER_NAMES[activeContinuous] : null;
    if (gibsLayerName) {
      const gibsUrl = `${GIBS_WMS_BASE}&LAYERS=${gibsLayerName}&TIME=${gibsDate}&BBOX={south},{west},{north},{east}&WIDTH=512&HEIGHT=512`;
      result.push(
        new TileLayer({
          id: 'gibs-overlay',
          data: gibsUrl,
          minZoom: 0,
          maxZoom: 5,
          tileSize: 512,
          opacity: 0.7,
          renderSubLayers: (props: Record<string, unknown>) => {
            const tileProps = props.tile as {
              bbox: { west: number; south: number; east: number; north: number };
            };
            const { west, south, east, north } = tileProps.bbox;
            return new BitmapLayer({
              ...props,
              data: undefined,
              image: props.data as string,
              bounds: [west, south, east, north],
            });
          },
        }),
      );
    }

    // 3. Fire points
    if (activeEvent === 'fires' && firesData?.fires) {
      result.push(
        new ScatterplotLayer({
          id: 'fires-layer',
          data: firesData.fires,
          getPosition: (d: FireHotspot) => [d.lon, d.lat],
          getFillColor: (d: FireHotspot) => fireColorRGBA(d.frp),
          getRadius: (d: FireHotspot) => fireRadius(d.frp),
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 2,
          radiusMaxPixels: 14,
          pickable: true,
          onHover,
          antialiasing: true,
          parameters: { blend: true },
        }),
      );
    }

    // 4. Storm points
    if (activeEvent === 'storms' && stormsData?.storms) {
      result.push(
        new ScatterplotLayer({
          id: 'storms-layer',
          data: stormsData.storms,
          getPosition: (d: Storm) => [d.lon, d.lat],
          getFillColor: (d: Storm) => stormColorRGBA(d.wind_kt),
          getRadius: (d: Storm) => stormRadius(d.wind_kt),
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 3,
          radiusMaxPixels: 18,
          stroked: true,
          getLineColor: rgbArr(255, 255, 255, 120),
          lineWidthMinPixels: 1,
          pickable: true,
          onHover,
        }),
      );
    }

    // 5. Earthquake points
    if (activeEvent === 'earthquakes' && earthquakeData?.earthquakes) {
      result.push(
        new ScatterplotLayer({
          id: 'earthquakes-layer',
          data: earthquakeData.earthquakes,
          getPosition: (d: Earthquake) => [d.lon, d.lat],
          getFillColor: (d: Earthquake) => earthquakeColorRGBA(d.magnitude),
          getRadius: (d: Earthquake) => earthquakeRadius(d.magnitude),
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 3,
          radiusMaxPixels: 24,
          stroked: true,
          getLineColor: rgbArr(255, 255, 255, 80),
          lineWidthMinPixels: 1,
          pickable: true,
          onHover,
        }),
      );
    }

    // 6. Air Monitor points
    if (activeEvent === 'monitors' && airData?.monitors) {
      result.push(
        new ScatterplotLayer({
          id: 'monitors-layer',
          data: airData.monitors,
          getPosition: (d: AirMonitor) => [d.lon, d.lat],
          getFillColor: (d: AirMonitor) => pm25ColorRGBA(d.pm25),
          getRadius: 5,
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 3,
          radiusMaxPixels: 8,
          pickable: true,
          onHover,
        }),
      );
    }

    // 7. SST scatter (continuous)
    if (activeContinuous === 'ocean-heat' && sstData?.points) {
      result.push(
        new ScatterplotLayer({
          id: 'sst-layer',
          data: sstData.points,
          getPosition: (d: SstPoint) => [d.lon, d.lat],
          getFillColor: (d: SstPoint) => sstColorRGBA(d.sst_c),
          getRadius: 8,
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 4,
          radiusMaxPixels: 12,
          pickable: true,
          onHover,
        }),
      );
    }

    // 8. Coral bleaching scatter (continuous)
    if (activeContinuous === 'coral' && coralData?.points) {
      result.push(
        new ScatterplotLayer({
          id: 'coral-layer',
          data: coralData.points,
          getPosition: (d: CoralPoint) => [d.lon, d.lat],
          getFillColor: (d: CoralPoint) => dhwColorRGBA(d.dhw),
          getRadius: 8,
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 4,
          radiusMaxPixels: 12,
          pickable: true,
          onHover,
        }),
      );
    }

    // 9. SLA scatter (continuous)
    if (activeContinuous === 'cmems-sla' && slaData?.points) {
      result.push(
        new ScatterplotLayer({
          id: 'sla-layer',
          data: slaData.points,
          getPosition: (d: SlaPoint) => [d.lon, d.lat],
          getFillColor: (d: SlaPoint) => slaColorRGBA(d.sla_m),
          getRadius: 6,
          radiusUnits: 'pixels' as const,
          radiusMinPixels: 3,
          radiusMaxPixels: 10,
          pickable: true,
          onHover,
        }),
      );
    }

    return result;
  }, [activeEvent, activeContinuous, firesData, stormsData, earthquakeData, airData, sstData, coralData, slaData, onHover]);

  // ── Initialize / update Deck instance ─────────────────────────────────────

  useEffect(() => {
    if (!canvasRef.current) return;

    if (!deckRef.current) {
      deckRef.current = new Deck({
        canvas: canvasRef.current,
        width: dims.width,
        height: dims.height,
        initialViewState: INITIAL_VIEW_STATE,
        views: new GlobeView({ id: 'globe', controller: true }),
        layers: layers as never[],
        onViewStateChange: ({ viewState: vs }: { viewState: Record<string, unknown> }) => {
          setViewState(vs as unknown as GlobeViewState);
        },
        getCursor: ({ isHovering }: { isHovering: boolean }) =>
          isHovering ? 'pointer' : 'grab',
      });
    } else {
      deckRef.current.setProps({
        width: dims.width,
        height: dims.height,
        views: new GlobeView({ id: 'globe', controller: true }),
        layers: layers as never[],
        viewState,
      });
    }

    return () => {
      // Don't finalize on re-render, only on unmount
    };
  }, [layers, dims, viewMode, viewState]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      deckRef.current?.finalize();
      deckRef.current = null;
    };
  }, []);

  // ── Meta + status ─────────────────────────────────────────────────────────

  const activeMeta = useMemo(() => {
    const key = activeContinuous || activeEvent;
    if (key) {
      const def = LAYER_LOOKUP.get(key);
      if (def) return { cadence: def.cadence, tag: def.tag, source: def.source, sourceUrl: def.sourceUrl };
    }
    return { cadence: 'NRT ~3h', tag: TrustTag.Observed, source: 'NASA FIRMS', sourceUrl: 'https://firms.modaps.eosdis.nasa.gov/' };
  }, [activeContinuous, activeEvent]);

  const slaConfigured = slaData ? slaData.configured && slaData.status === 'ok' : true;
  const airConfigured = airData ? airData.configured : true;

  return (
    <div ref={containerRef} style={containerStyle}>
      {/* CSS atmosphere glow */}
      <div style={atmosphereGlowStyle} />

      {/* deck.gl canvas */}
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', position: 'relative', zIndex: 1 }} />

      {/* Tooltip */}
      <Tooltip info={hoverInfo} />

      {/* Meta line (top-left) */}
      <div style={metaOverlayStyle}>
        <MetaLine cadence={activeMeta.cadence} tag={activeMeta.tag} source={activeMeta.source} sourceUrl={activeMeta.sourceUrl} />
      </div>

      {/* Layer panel (top-right) */}
      <LayerPanel
        activeEvent={activeEvent} activeContinuous={activeContinuous}
        onLayerChange={onLayerChange}
        viewMode={viewMode} onViewModeChange={setViewMode}
        slaConfigured={slaConfigured} slaStatus={slaData?.status}
        airConfigured={airConfigured}
      />

      {/* Legend (bottom-left) */}
      <Legend activeEvent={activeEvent} activeContinuous={activeContinuous} />
    </div>
  );
});

export default GlobeDeck;

// ─── Styles ───────────────────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  position: 'relative',
  width: '100%',
  height: '640px',
  background: 'radial-gradient(ellipse at center, #0a0e27 0%, #040610 100%)',
  borderRadius: '12px',
  overflow: 'hidden',
};

const atmosphereGlowStyle: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  zIndex: 0,
  background: 'radial-gradient(circle at 50% 50%, rgba(40,80,180,0.12) 0%, rgba(20,50,140,0.06) 30%, transparent 55%)',
  pointerEvents: 'none',
};

const metaOverlayStyle: React.CSSProperties = {
  position: 'absolute', top: 12, left: 12, zIndex: 10,
  background: 'rgba(10,14,26,0.78)', padding: '6px 10px',
  borderRadius: '6px', backdropFilter: 'blur(6px)', pointerEvents: 'none',
};

const layerPanelStyle: React.CSSProperties = {
  position: 'absolute', top: 12, right: 12, zIndex: 10,
  background: 'rgba(10,14,26,0.9)', border: '1px solid #334155',
  borderRadius: '8px', backdropFilter: 'blur(8px)',
  fontFamily: 'system-ui, sans-serif', minWidth: 200, maxWidth: 240,
};

const layerHeaderBtnStyle: React.CSSProperties = {
  width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '8px 12px', background: 'none', border: 'none', cursor: 'pointer',
  color: '#e2e8f0', fontSize: '13px', fontWeight: 600, fontFamily: 'system-ui, sans-serif',
};

const categoryBtnStyle: React.CSSProperties = {
  width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '6px 12px', background: 'none', border: 'none',
  borderTop: '1px solid #1e293b', cursor: 'pointer',
  color: '#94a3b8', fontSize: '11px', fontWeight: 700,
  textTransform: 'uppercase', letterSpacing: '0.05em', fontFamily: 'system-ui, sans-serif',
};

const legendStyle: React.CSSProperties = {
  position: 'absolute', bottom: 12, left: 12, zIndex: 10,
  background: 'rgba(10,14,26,0.88)', backdropFilter: 'blur(8px)',
  border: '1px solid rgba(51,65,85,0.5)', borderRadius: '8px',
  padding: '8px 12px', minWidth: 160, maxWidth: 260,
};

const legendTitleStyle: React.CSSProperties = {
  fontSize: '11px', fontWeight: 600, color: '#cbd5e1',
  marginBottom: 6, fontFamily: 'system-ui, sans-serif',
};

const legendBarStyle: React.CSSProperties = { display: 'flex', gap: 0 };

const legendSwatch: React.CSSProperties = { flex: 1, height: 10 };

const legendLabelsStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between',
  fontSize: '9px', color: '#64748b', marginTop: 2,
  fontFamily: 'system-ui, sans-serif',
};
