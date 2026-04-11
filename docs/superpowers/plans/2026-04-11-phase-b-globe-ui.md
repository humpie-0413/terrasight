# Phase B — Globe UI Layer Expansion & Trends Carousel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the Earth Now globe from 4 flat toggles to a 5-category accordion layer panel (13 layers), and grow the Climate Trends strip from 3 cards to a 5-card horizontal scroll carousel (adding CH₄ and Sea Level Rise).

**Architecture:** Backend adds CH₄/sea-level trend endpoints and three new earth-now endpoints (storms, coral, sea-level-anomaly). Frontend refactors Globe.tsx state model to `activeEvent + activeContinuous`, builds an accordion layer panel, composites GIBS WMS GetMap transparent PNGs onto BlueMarble via offscreen canvas, and converts TrendsStrip to a flex scroll-snap carousel.

**Tech Stack:** FastAPI (Python), React + TypeScript, react-globe.gl, httpx, browser Canvas API, NASA GIBS WMS (CORS: *), NOAA IBTrACS CSV, NOAA CRW ERDDAP

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/api/trends.py` | Modify | Add `_ch4_payload()`, `_sea_level_payload()`, 5-indicator fan-out |
| `backend/api/earth_now.py` | Modify | Add `/storms`, `/coral`, `/sea-level-anomaly` endpoints |
| `frontend/src/components/climate-trends/TrendsStrip.tsx` | Modify | 5-card scroll-snap carousel |
| `frontend/src/pages/Home.tsx` | Modify | New layer state: `activeEvent` + `activeContinuous` |
| `frontend/src/components/earth-now/Globe.tsx` | Modify | Accordion panel + GIBS canvas composite + new fetches |

---

## Task 1 — Backend: CH₄ and Sea Level Trends

**Files:**
- Modify: `backend/api/trends.py`

- [ ] **Step 1: Add `_ch4_payload()` function**

In `trends.py`, after the `_sea_ice_payload` function, add:

```python
async def _ch4_payload() -> dict[str, Any]:
    from backend.connectors.noaa_gml_ch4 import NoaaGmlCh4Connector
    connector = NoaaGmlCh4Connector()
    result = await connector.run()
    points = result.values
    if not points:
        raise HTTPException(status_code=502, detail="NOAA GML CH4 returned no data")

    latest = points[-1]
    sparkline = points[-12:]
    return {
        "id": "ch4",
        "label": "CH₄ (Methane)",
        "unit": "ppb",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "record_start": "1983",
        "latest": {"date": latest.iso_month, "value": latest.value_ppb},
        "series": [
            {"date": p.iso_month, "value": p.value_ppb} for p in sparkline
        ],
        "notes": result.notes,
    }
```

- [ ] **Step 2: Add `_sea_level_payload()` function**

After `_ch4_payload`, add:

```python
async def _sea_level_payload() -> dict[str, Any]:
    from backend.connectors.noaa_sea_level import NoaaSeaLevelConnector
    connector = NoaaSeaLevelConnector()
    result = await connector.run()
    # normalize() may return error dict in values on connection failure
    if isinstance(result.values, dict):
        raise HTTPException(
            status_code=502,
            detail=f"NOAA sea level fetch failed: {result.values.get('message', 'unknown error')}",
        )
    points = result.values
    if not points:
        raise HTTPException(status_code=502, detail="NOAA sea level returned no data")

    latest = points[-1]
    sparkline = points[-24:]  # ~8 months of ~10-day data
    return {
        "id": "sea-level",
        "label": "Sea Level Rise",
        "unit": "mm",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "record_start": "1992",
        "baseline": "1993–2012 mean",
        "latest": {"date": latest.date_str, "value": round(latest.gmsl_mm, 1)},
        "series": [
            {"date": p.date_str, "value": round(p.gmsl_mm, 1)} for p in sparkline
        ],
        "notes": result.notes,
    }
```

- [ ] **Step 3: Extend `get_trends()` fan-out to 5 indicators**

Replace the existing `get_trends()` body:

```python
@router.get("")
async def get_trends() -> dict[str, Any]:
    """Fan-out endpoint for the Climate Trends home-page strip.

    Runs all five connectors in parallel. A failure in any single
    indicator is reported as `error` on its entry without blocking the
    others — the UI can render partial strips.
    """
    results = await asyncio.gather(
        _co2_payload(),
        _temperature_payload(),
        _sea_ice_payload(),
        _ch4_payload(),
        _sea_level_payload(),
        return_exceptions=True,
    )
    indicators: list[dict[str, Any]] = []
    ids = ("co2", "temp", "sea-ice", "ch4", "sea-level")
    for indicator_id, outcome in zip(ids, results):
        if isinstance(outcome, Exception):
            indicators.append({"id": indicator_id, "error": str(outcome)})
        else:
            indicators.append(outcome)
    return {"indicators": indicators}
```

- [ ] **Step 4: Add individual debug endpoints**

After the existing `/sea-ice` endpoint, add:

```python
@router.get("/ch4")
async def get_ch4() -> dict[str, Any]:
    """NOAA GML global CH₄ monthly mean — observed, since 1983."""
    try:
        return await _ch4_payload()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch CH4 series: {exc}"
        ) from exc


@router.get("/sea-level")
async def get_sea_level() -> dict[str, Any]:
    """NOAA NESDIS GMSL — observed altimetry, since 1992."""
    try:
        return await _sea_level_payload()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch sea level series: {exc}"
        ) from exc
```

- [ ] **Step 5: Smoke-test**

```bash
cd C:/0_project/terrasight
python -c "from backend.api.trends import get_trends; print('trends OK')"
```
Expected: `trends OK`

- [ ] **Step 6: Commit**

```bash
git add backend/api/trends.py
git commit -m "feat(trends): add CH4 and sea-level indicators to /api/trends fan-out"
```

---

## Task 2 — Backend: New Earth-Now Endpoints

**Files:**
- Modify: `backend/api/earth_now.py`

- [ ] **Step 1: Add `/storms` endpoint (IBTrACS ACTIVE)**

Add after the `/air-monitors` endpoint:

```python
@router.get("/storms")
async def get_storms() -> dict[str, Any]:
    """NOAA IBTrACS active tropical storms — latest track point per storm.

    Returns only currently ACTIVE storms from the IBTrACS ACTIVE CSV.
    Each storm entry shows its most recent position, name, basin, and intensity.
    Returns empty list (not an error) when no active storms exist.
    """
    from backend.connectors.ibtracs import IbtracConnector
    connector = IbtracConnector()
    try:
        raw = await connector.fetch(source="ACTIVE")
        result = connector.normalize(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch IBTrACS ACTIVE: {exc}"
        ) from exc

    storms_out = []
    for storm in result.values:
        pt = storm.latest_point
        if pt is None:
            continue
        storms_out.append({
            "sid": storm.sid,
            "name": storm.name,
            "basin": storm.basin,
            "season": storm.season,
            "lat": pt.lat,
            "lon": pt.lon,
            "wind_kt": pt.wind_kt,
            "pres_hpa": pt.pres_hpa,
            "sshs": pt.sshs,
            "iso_time": pt.iso_time,
        })

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "count": len(storms_out),
        "configured": True,
        "storms": storms_out,
    }
```

- [ ] **Step 2: Add `/coral` endpoint (CRW)**

```python
@router.get("/coral")
async def get_coral() -> dict[str, Any]:
    """NOAA Coral Reef Watch daily bleaching heat stress grid.

    Returns the most recent day's CoralTemp stress pixels (BAA > 0)
    at ~0.5° resolution for the coral belt (35°S–35°N).
    Continuous-field layer on the Earth Now globe.
    """
    from backend.connectors.coral_reef_watch import CoralReefWatchConnector
    connector = CoralReefWatchConnector()
    try:
        raw = await connector.fetch()
        result = connector.normalize(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch CRW coral data: {exc}"
        ) from exc

    if isinstance(result.values, dict):
        # connector returned graceful error dict
        return {
            "source": result.source,
            "source_url": result.source_url,
            "cadence": result.cadence,
            "tag": result.tag,
            "count": 0,
            "configured": True,
            "status": "error",
            "message": result.values.get("message", "CRW fetch failed"),
            "points": [],
        }

    points_out = [
        {
            "lat": p.lat,
            "lon": p.lon,
            "bleaching_alert": p.bleaching_alert,
            "dhw": round(p.dhw, 2),
            "sst_c": round(p.sst_c, 2),
            "sst_anomaly_c": round(p.sst_anomaly_c, 2),
        }
        for p in result.values
    ]
    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "count": len(points_out),
        "configured": True,
        "status": "ok",
        "points": points_out,
    }
```

- [ ] **Step 3: Add `/sea-level-anomaly` endpoint (CMEMS)**

```python
@router.get("/sea-level-anomaly")
async def get_sea_level_anomaly() -> dict[str, Any]:
    """Copernicus Marine CMEMS daily SSH/SLA L4 NRT — global 0.25° grid.

    Requires CMEMS_USERNAME and CMEMS_PASSWORD env vars (free registration
    at marine.copernicus.eu). Returns not_configured status if credentials absent.
    """
    from backend.connectors.cmems import CmemsConnector
    settings = get_settings()
    connector = CmemsConnector(
        username=getattr(settings, "cmems_username", None),
        password=getattr(settings, "cmems_password", None),
    )

    if not getattr(settings, "cmems_username", None):
        return {
            "source": connector.source,
            "source_url": connector.source_url,
            "cadence": connector.cadence,
            "tag": connector.tag,
            "count": 0,
            "configured": False,
            "message": (
                "CMEMS_USERNAME and CMEMS_PASSWORD are not set. "
                "Register free at https://marine.copernicus.eu/ "
                "and add credentials to your environment."
            ),
            "points": [],
        }

    try:
        raw = await connector.fetch()
        result = connector.normalize(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch CMEMS SLA: {exc}"
        ) from exc

    if isinstance(result.values, dict):
        return {
            "source": result.source,
            "source_url": result.source_url,
            "cadence": result.cadence,
            "tag": result.tag,
            "count": 0,
            "configured": True,
            "status": "error",
            "message": result.values.get("message", "CMEMS fetch failed"),
            "points": [],
        }

    points_out = [
        {"lat": p.lat, "lon": p.lon, "sla_m": round(p.sla_m, 4)}
        for p in result.values
    ]
    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "count": len(points_out),
        "configured": True,
        "status": "ok",
        "points": points_out,
    }
```

- [ ] **Step 4: Check CmemsConnector constructor signature**

Before committing, verify that CmemsConnector accepts `username` and `password` kwargs (or equivalent). Read `backend/connectors/cmems.py` lines 1-60 and adjust the constructor call if the parameter names differ.

- [ ] **Step 5: Smoke-test**

```bash
python -c "from backend.api.earth_now import get_storms, get_coral; print('earth_now OK')"
```
Expected: `earth_now OK`

- [ ] **Step 6: Commit**

```bash
git add backend/api/earth_now.py
git commit -m "feat(earth-now): add /storms, /coral, /sea-level-anomaly endpoints"
```

---

## Task 3 — Frontend: TrendsStrip 5-Card Carousel

**Files:**
- Modify: `frontend/src/components/climate-trends/TrendsStrip.tsx`

- [ ] **Step 1: Extend TrendIndicator id union**

Change line:
```ts
id: 'co2' | 'temp' | 'sea-ice';
```
to:
```ts
id: 'co2' | 'temp' | 'sea-ice' | 'ch4' | 'sea-level';
```

- [ ] **Step 2: Extend ORDER array**

Change:
```ts
const ORDER: Array<TrendIndicator['id']> = ['co2', 'temp', 'sea-ice'];
```
to:
```ts
const ORDER: Array<TrendIndicator['id']> = ['co2', 'temp', 'sea-ice', 'ch4', 'sea-level'];
```

- [ ] **Step 3: Add STATIC_META entries for CH₄ and Sea Level**

Add to the `STATIC_META` object (after `'sea-ice'` entry):

```ts
ch4: {
  title: 'CH₄ (Methane)',
  cadence: 'Monthly',
  tag: TrustTag.Observed,
  source: 'NOAA GML Global CH₄',
  sourceUrl: 'https://gml.noaa.gov/ccgg/trends/ch4/',
  sparkColor: '#d97706',
},
'sea-level': {
  title: 'Sea Level Rise',
  cadence: '~10-day',
  tag: TrustTag.Observed,
  source: 'NOAA NESDIS GMSL',
  sourceUrl: 'https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/',
  sparkColor: '#2563eb',
},
```

- [ ] **Step 4: Add `formatValue` cases for new ids**

Update `formatValue`:
```ts
function formatValue(value: number, id: TrendIndicator['id']): string {
  if (id === 'temp') {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}`;
  }
  if (id === 'sea-level') {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}`;
  }
  if (id === 'ch4') return value.toFixed(1);
  return value.toFixed(2);
}
```

- [ ] **Step 5: Convert sectionStyle to horizontal scroll carousel**

Replace:
```ts
const sectionStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap: '16px',
  padding: '16px 24px',
};
```
with:
```ts
const sectionStyle: React.CSSProperties = {
  display: 'flex',
  gap: '14px',
  padding: '16px 24px',
  overflowX: 'auto',
  scrollSnapType: 'x mandatory',
  WebkitOverflowScrolling: 'touch',
};
```

- [ ] **Step 6: Make each card snap-aligned with fixed width**

Replace `cardStyle`:
```ts
const cardStyle: React.CSSProperties = {
  padding: '16px',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  background: '#fff',
  minWidth: '200px',
  flexShrink: 0,
  scrollSnapAlign: 'start',
};
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/climate-trends/TrendsStrip.tsx
git commit -m "feat(trends): expand to 5-card scroll-snap carousel (add CH4, sea-level)"
```

---

## Task 4 — Frontend: Home.tsx Layer State Refactor

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

- [ ] **Step 1: Remove old imports and add new layer type imports**

At the top of Home.tsx, change the Globe import line from:
```ts
import Globe, {
  type ContinuousLayer,
  type GlobeHandle,
} from '../components/earth-now/Globe';
```
to:
```ts
import Globe, {
  type ActiveEvent,
  type ActiveContinuous,
  type GlobeHandle,
} from '../components/earth-now/Globe';
```

- [ ] **Step 2: Replace state variables**

In the `Home` component, replace:
```ts
const [firesOn, setFiresOn] = useState(true);
const [continuousLayer, setContinuousLayer] = useState<ContinuousLayer>(null);
```
with:
```ts
const [activeEvent, setActiveEvent] = useState<ActiveEvent>('fires');
const [activeContinuous, setActiveContinuous] = useState<ActiveContinuous>(null);
```

- [ ] **Step 3: Update `handleExploreOnGlobe`**

Replace:
```ts
const handleExploreOnGlobe = (
  layerOn: string,
  camera: { lat: number; lng: number; altitude: number },
) => {
  if (layerOn === 'firms') setFiresOn(true);
  if (layerOn === 'oisst') setContinuousLayer('ocean-heat');
  if (layerOn === 'openaq') setContinuousLayer('air-monitors');
  globeRef.current?.flyTo(camera.lat, camera.lng, camera.altitude);
};
```
with:
```ts
const handleExploreOnGlobe = (
  layerOn: string,
  camera: { lat: number; lng: number; altitude: number },
) => {
  if (layerOn === 'firms') setActiveEvent('fires');
  if (layerOn === 'oisst') setActiveContinuous('ocean-heat');
  if (layerOn === 'openaq') setActiveContinuous('air-monitors');
  globeRef.current?.flyTo(camera.lat, camera.lng, camera.altitude);
};
```

- [ ] **Step 4: Update Globe props in JSX**

Replace:
```tsx
<Globe
  ref={globeRef}
  firesOn={firesOn}
  onToggleFires={setFiresOn}
  continuousLayer={continuousLayer}
  onSetContinuousLayer={setContinuousLayer}
/>
```
with:
```tsx
<Globe
  ref={globeRef}
  activeEvent={activeEvent}
  activeContinuous={activeContinuous}
  onLayerChange={(type, key) => {
    if (type === 'event') setActiveEvent(key as ActiveEvent);
    else setActiveContinuous(key as ActiveContinuous);
  }}
/>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat(home): update Globe layer state to activeEvent + activeContinuous"
```

---

## Task 5 — Frontend: Globe.tsx Accordion Panel + GIBS Composite

**Files:**
- Modify: `frontend/src/components/earth-now/Globe.tsx`

This is the largest task. Replace Globe.tsx entirely with the version below.

- [ ] **Step 1: Replace the type definitions section (top of file)**

Replace from the start through the end of the `GlobeProps` interface with:

```ts
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import GlobeGL, { type GlobeMethods } from 'react-globe.gl';

import { TrustTag } from '../../utils/trustTags';
import MetaLine from '../common/MetaLine';
import { useApi } from '../../hooks/useApi';

// ── GIBS WMS base URL (CORS: Access-Control-Allow-Origin: *) ──────────────
const GIBS_WMS =
  'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
  '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&STYLES=' +
  '&FORMAT=image/jpeg&SRS=EPSG:4326&BBOX=-180,-90,180,90&WIDTH=2048&HEIGHT=1024';

const GIBS_WMS_PNG =
  'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
  '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&STYLES=' +
  '&FORMAT=image/png&TRANSPARENT=TRUE&SRS=EPSG:4326&BBOX=-180,-90,180,90' +
  '&WIDTH=2048&HEIGHT=1024';

const BLUEMARBLE_URL =
  GIBS_WMS + '&LAYERS=BlueMarble_ShadedRelief_Bathymetry';

// ── Layer type exports ─────────────────────────────────────────────────────
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

// ── GIBS layer definitions (continuous GIBS raster layers) ────────────────
interface GibsLayerDef {
  layerId: string;      // exact GIBS layer name
  cadence: 'daily' | 'monthly';
  label: string;
  trust: TrustTag;
  source: string;
  sourceUrl: string;
  note?: string;        // e.g. dust-fraction caveat
}

const GIBS_LAYER_DEFS: Partial<Record<ActiveContinuous, GibsLayerDef>> = {
  'gibs-aod': {
    layerId: 'MODIS_Terra_Aerosol',
    cadence: 'daily',
    label: 'AOD (MODIS Terra)',
    trust: TrustTag.Observed,
    source: 'NASA GIBS / MODIS Terra',
    sourceUrl: 'https://worldview.earthdata.nasa.gov/',
  },
  'gibs-pm25': {
    layerId: 'MERRA2_Dust_Surface_Mass_Concentration_PM25_Monthly',
    cadence: 'monthly',
    label: 'PM2.5 Dust (MERRA-2)',
    trust: TrustTag.Derived,
    source: 'NASA GIBS / MERRA-2',
    sourceUrl: 'https://worldview.earthdata.nasa.gov/',
    note: 'Dust fraction only — not total PM2.5',
  },
  'gibs-oco2': {
    layerId: 'OCO-2_Carbon_Dioxide_Total_Column_Average',
    cadence: 'daily',
    label: 'CO₂ Column (OCO-2)',
    trust: TrustTag.Observed,
    source: 'NASA GIBS / OCO-2',
    sourceUrl: 'https://worldview.earthdata.nasa.gov/',
    note: 'Sparse daily swath — large blank regions are normal',
  },
  'gibs-flood': {
    layerId: 'MODIS_Combined_Flood_2-Day',
    cadence: 'daily',
    label: 'Flood Map (MODIS 2-Day)',
    trust: TrustTag.Observed,
    source: 'NASA GIBS / MODIS',
    sourceUrl: 'https://worldview.earthdata.nasa.gov/',
  },
};

// ── Category panel definition ──────────────────────────────────────────────
interface LayerEntry {
  key: ActiveEvent | ActiveContinuous;
  type: 'event' | 'continuous';
  label: string;
  emoji: string;
  trust: TrustTag;
  note?: string;
  disabled?: boolean;
  disabledReason?: string;
}

interface CategoryDef {
  id: string;
  label: string;
  emoji: string;
  layers: LayerEntry[];
}

const CATEGORIES: CategoryDef[] = [
  {
    id: 'atmosphere',
    label: 'Atmosphere',
    emoji: '🌫',
    layers: [
      { key: 'gibs-pm25', type: 'continuous', label: 'PM2.5 Dust (MERRA-2)', emoji: '🔵', trust: TrustTag.Derived, note: 'Dust fraction only' },
      { key: 'gibs-aod', type: 'continuous', label: 'AOD (MODIS)', emoji: '🟢', trust: TrustTag.Observed },
      { key: 'monitors', type: 'event', label: 'Air Monitors (OpenAQ)', emoji: '🟢', trust: TrustTag.Observed },
    ] as LayerEntry[],
  },
  {
    id: 'fire-land',
    label: 'Fire & Land',
    emoji: '🔥',
    layers: [
      { key: 'fires', type: 'event', label: 'Active Fires (FIRMS)', emoji: '🟢', trust: TrustTag.Observed },
      { key: null, type: 'continuous', label: 'Deforestation (GFW)', emoji: '🔵', trust: TrustTag.Derived, disabled: true, disabledReason: 'Country-level points require polygon query (P1)' },
      { key: null, type: 'continuous', label: 'Drought (JRC WMS)', emoji: '🔵', trust: TrustTag.Derived, disabled: true, disabledReason: 'WMS tiles only — globe composite P1' },
    ] as LayerEntry[],
  },
  {
    id: 'ocean',
    label: 'Ocean',
    emoji: '🌊',
    layers: [
      { key: 'ocean-heat', type: 'continuous', label: 'SST Anomaly (OISST)', emoji: '🟢', trust: TrustTag.Observed },
      { key: 'coral', type: 'continuous', label: 'Coral Bleaching (CRW)', emoji: '🟡', trust: TrustTag.NearRealTime },
      { key: 'cmems-sla', type: 'continuous', label: 'Sea Level (CMEMS)', emoji: '🟢', trust: TrustTag.Observed },
    ] as LayerEntry[],
  },
  {
    id: 'ghg',
    label: 'Greenhouse Gas',
    emoji: '🌿',
    layers: [
      { key: 'gibs-oco2', type: 'continuous', label: 'CO₂ Column (OCO-2)', emoji: '🟢', trust: TrustTag.Observed },
      { key: null, type: 'continuous', label: 'CH₄ (TROPOMI)', emoji: '⚪', trust: TrustTag.Observed, disabled: true, disabledReason: 'TROPOMI CH₄ not in GIBS — Copernicus GES DISC (P1)' },
    ] as LayerEntry[],
  },
  {
    id: 'hazards',
    label: 'Hazards',
    emoji: '⚡',
    layers: [
      { key: 'storms', type: 'event', label: 'Tropical Storms (IBTrACS)', emoji: '🟢', trust: TrustTag.Observed },
      { key: 'gibs-flood', type: 'continuous', label: 'Flood Map (MODIS 2-Day)', emoji: '🟢', trust: TrustTag.Observed },
    ] as LayerEntry[],
  },
];
```

- [ ] **Step 2: Add API response interfaces and data interfaces**

After the CATEGORIES definition, add:

```ts
// ── API response types ─────────────────────────────────────────────────────
interface FireHotspot { lat: number; lon: number; brightness: number; frp: number; confidence: string; acq_date: string; acq_time: string; daynight: string; }
interface FiresResponse { count: number; configured: boolean; message?: string; fires: FireHotspot[]; }

interface SstPoint { lat: number; lon: number; sst_c: number; }
interface SstResponse { count: number; configured: boolean; stats: { min_c: number | null; max_c: number | null; mean_c: number | null }; points: SstPoint[]; }

interface AirMonitor { lat: number; lon: number; pm25: number; location_name: string; datetime_utc: string; country: string | null; }
interface AirMonitorsResponse { count: number; configured: boolean; message?: string; monitors: AirMonitor[]; }

interface StormPoint { sid: string; name: string; basin: string; lat: number; lon: number; wind_kt: number; sshs: number; iso_time: string; }
interface StormsResponse { count: number; configured: boolean; storms: StormPoint[]; }

interface CoralPoint { lat: number; lon: number; bleaching_alert: number; dhw: number; sst_c: number; sst_anomaly_c: number; }
interface CoralResponse { count: number; configured: boolean; status: string; points: CoralPoint[]; }

interface CmemsPoint { lat: number; lon: number; sla_m: number; }
interface CmemsResponse { count: number; configured: boolean; status: string; points: CmemsPoint[]; }
```

- [ ] **Step 3: Write `useGibsTexture` hook**

After the interface definitions, add this hook:

```ts
// ── GIBS canvas composite hook ─────────────────────────────────────────────
function useGibsTexture(activeContinuous: ActiveContinuous): string {
  const [texture, setTexture] = useState<string>(BLUEMARBLE_URL);

  useEffect(() => {
    const def = activeContinuous ? GIBS_LAYER_DEFS[activeContinuous] : undefined;
    if (!def) {
      setTexture(BLUEMARBLE_URL);
      return;
    }

    let cancelled = false;

    const tryDate = async (iso: string): Promise<boolean> => {
      const gibsUrl =
        GIBS_WMS_PNG + `&LAYERS=${def.layerId}&TIME=${iso}`;

      const bmImg = new Image();
      bmImg.crossOrigin = 'anonymous';
      const layerImg = new Image();
      layerImg.crossOrigin = 'anonymous';

      try {
        await Promise.all([
          new Promise<void>((res, rej) => {
            bmImg.onload = () => res();
            bmImg.onerror = rej;
            bmImg.src = BLUEMARBLE_URL;
          }),
          new Promise<void>((res, rej) => {
            layerImg.onload = () => res();
            layerImg.onerror = rej;
            layerImg.src = gibsUrl;
          }),
        ]);
      } catch {
        return false;
      }

      if (cancelled) return true;

      const canvas = document.createElement('canvas');
      canvas.width = 2048;
      canvas.height = 1024;
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(bmImg, 0, 0, 2048, 1024);
      ctx.globalAlpha = 0.72;
      ctx.drawImage(layerImg, 0, 0, 2048, 1024);

      if (!cancelled) setTexture(canvas.toDataURL('image/jpeg', 0.82));
      return true;
    };

    const run = async () => {
      const now = new Date();
      const fmt = (d: Date) => d.toISOString().slice(0, 10);

      // Try today, then fallback 1 day/month
      for (let offset = 0; offset <= 3; offset++) {
        if (cancelled) return;
        const d = new Date(now);
        if (def.cadence === 'daily') {
          d.setDate(d.getDate() - offset);
        } else {
          d.setMonth(d.getMonth() - offset);
          d.setDate(1);
        }
        const ok = await tryDate(fmt(d));
        if (ok) return;
      }
    };

    run();
    return () => { cancelled = true; };
  }, [activeContinuous]);

  return texture;
}
```

- [ ] **Step 4: Write the Globe component body**

Replace the existing `Globe` forwardRef component with:

```ts
const Globe = forwardRef<GlobeHandle, GlobeProps>(function Globe(
  { activeEvent, activeContinuous, onLayerChange },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [dims, setDims] = useState({ width: 640, height: 520 });
  const [openCategory, setOpenCategory] = useState<string | null>(null);

  // Globe texture (BlueMarble or GIBS composite)
  const globeTexture = useGibsTexture(activeContinuous);

  // Data fetches
  const { data: firesData } = useApi<FiresResponse>('/earth-now/fires');
  const { data: sstData } = useApi<SstResponse>('/earth-now/sst');
  const { data: airData } = useApi<AirMonitorsResponse>('/earth-now/air-monitors');
  const { data: stormsData } = useApi<StormsResponse>('/earth-now/storms');
  const { data: coralData } = useApi<CoralResponse>('/earth-now/coral');
  const { data: cmemsData } = useApi<CmemsResponse>('/earth-now/sea-level-anomaly');

  // Responsive sizing
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const observer = new ResizeObserver(() =>
      setDims({ width: el.clientWidth, height: el.clientHeight }),
    );
    observer.observe(el);
    setDims({ width: el.clientWidth, height: el.clientHeight });
    return () => observer.disconnect();
  }, []);

  // Camera init + auto-rotate
  useEffect(() => {
    if (!globeRef.current) return;
    const controls = globeRef.current.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controls.enableZoom = true;
    globeRef.current.pointOfView({ lat: 15, lng: 0, altitude: 2.3 }, 0);
  }, []);

  useImperativeHandle(ref, () => ({
    flyTo: (lat, lng, altitude = 1.8) => {
      if (!globeRef.current) return;
      const controls = globeRef.current.controls();
      controls.autoRotate = false;
      globeRef.current.pointOfView({ lat, lng, altitude }, 1500);
    },
  }), []);

  // ── Memoized overlay data ─────────────────────────────────────────────

  const firePoints = useMemo<FireHotspot[]>(
    () => (activeEvent === 'fires' && firesData?.fires ? firesData.fires : []),
    [activeEvent, firesData],
  );

  const stormPoints = useMemo<StormPoint[]>(
    () => (activeEvent === 'storms' && stormsData?.storms ? stormsData.storms : []),
    [activeEvent, stormsData],
  );

  const airPoints = useMemo<AirMonitor[]>(
    () => (activeEvent === 'monitors' && airData?.monitors ? airData.monitors : []),
    [activeEvent, airData],
  );

  const sstPoints = useMemo<SstPoint[]>(
    () => (activeContinuous === 'ocean-heat' && sstData?.points ? sstData.points : []),
    [activeContinuous, sstData],
  );

  const coralPoints = useMemo<CoralPoint[]>(
    () => (activeContinuous === 'coral' && coralData?.points ? coralData.points : []),
    [activeContinuous, coralData],
  );

  const cmemsPoints = useMemo<CmemsPoint[]>(
    () => (activeContinuous === 'cmems-sla' && cmemsData?.points ? cmemsData.points : []),
    [activeContinuous, cmemsData],
  );

  // Combine hexbin data: SST, coral, or CMEMS
  const hexPoints = useMemo(() => {
    if (activeContinuous === 'ocean-heat') return sstPoints.map(p => ({ lat: p.lat, lon: p.lon, val: p.sst_c }));
    if (activeContinuous === 'coral') return coralPoints.map(p => ({ lat: p.lat, lon: p.lon, val: p.dhw }));
    if (activeContinuous === 'cmems-sla') return cmemsPoints.map(p => ({ lat: p.lat, lon: p.lon, val: p.sla_m * 1000 })); // m → mm
    return [];
  }, [activeContinuous, sstPoints, coralPoints, cmemsPoints]);

  const hexColorFn = useCallback((d: { sumWeight: number; points: object[] }) => {
    const mean = d.sumWeight / Math.max(d.points.length, 1);
    if (activeContinuous === 'ocean-heat') return sstColor(mean);
    if (activeContinuous === 'coral') return dhwColor(mean);
    if (activeContinuous === 'cmems-sla') return slaColor(mean);
    return '#334155';
  }, [activeContinuous]);

  // Active layer meta for top-left MetaLine
  const activeMeta = useMemo(() => {
    const gibsDef = activeContinuous ? GIBS_LAYER_DEFS[activeContinuous] : undefined;
    if (gibsDef) return { cadence: gibsDef.cadence === 'daily' ? 'Daily' : 'Monthly', tag: gibsDef.trust, source: gibsDef.source, sourceUrl: gibsDef.sourceUrl };
    if (activeContinuous === 'ocean-heat') return { cadence: 'Daily', tag: TrustTag.Observed, source: 'NOAA OISST v2.1', sourceUrl: 'https://coralreefwatch.noaa.gov/product/5km/' };
    if (activeContinuous === 'coral') return { cadence: 'Daily', tag: TrustTag.NearRealTime, source: 'NOAA Coral Reef Watch', sourceUrl: 'https://coralreefwatch.noaa.gov/' };
    if (activeContinuous === 'cmems-sla') return { cadence: 'Daily', tag: TrustTag.Observed, source: 'Copernicus Marine CMEMS', sourceUrl: 'https://marine.copernicus.eu/' };
    if (activeEvent === 'storms') return { cadence: 'NRT ~6h', tag: TrustTag.Observed, source: 'NOAA IBTrACS', sourceUrl: 'https://www.ncei.noaa.gov/products/international-best-track-archive' };
    if (activeEvent === 'monitors') return { cadence: 'Varies', tag: TrustTag.Observed, source: 'OpenAQ', sourceUrl: 'https://openaq.org/' };
    return { cadence: 'NRT ~3h', tag: TrustTag.Observed, source: 'NASA FIRMS', sourceUrl: 'https://firms.modaps.eosdis.nasa.gov/' };
  }, [activeContinuous, activeEvent]);

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div
      id="earth-now"
      ref={containerRef}
      style={{ position: 'relative', width: '100%', height: '520px', background: '#0b1120', borderRadius: '8px', overflow: 'hidden' }}
    >
      <GlobeGL
        ref={globeRef}
        width={dims.width}
        height={dims.height}
        globeImageUrl={globeTexture}
        backgroundColor="#0b1120"
        showAtmosphere
        atmosphereColor="#88aaff"
        atmosphereAltitude={0.18}
        // Fires (event points)
        pointsData={[...firePoints, ...stormPoints]}
        pointLat={(d: object) => (d as FireHotspot & StormPoint).lat}
        pointLng={(d: object) => (d as FireHotspot & StormPoint).lon}
        pointColor={(d: object) => {
          if ('frp' in (d as object)) return '#ff3d00';
          const s = d as StormPoint;
          return stormColor(s.sshs);
        }}
        pointAltitude={(d: object) => {
          if ('frp' in (d as object)) return firePointAltitude(d as FireHotspot);
          return 0.012;
        }}
        pointRadius={(d: object) => {
          if ('frp' in (d as object)) return firePointRadius(d as FireHotspot);
          return 0.4;
        }}
        pointResolution={4}
        pointLabel={(d: object) => {
          if ('frp' in (d as object)) {
            const f = d as FireHotspot;
            return `<div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;border:1px solid #475569;border-radius:4px;font-size:11px;font-family:system-ui,sans-serif;"><div><b>FIRMS hotspot</b></div><div>${f.acq_date} ${f.acq_time} UTC (${f.daynight === 'D' ? 'day' : 'night'})</div><div>FRP: ${f.frp.toFixed(1)} MW · ${f.confidence || '—'}</div></div>`;
          }
          const s = d as StormPoint;
          return `<div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;border:1px solid #475569;border-radius:4px;font-size:11px;font-family:system-ui,sans-serif;"><div><b>🌀 ${s.name}</b> (${s.basin})</div><div>Wind: ${s.wind_kt} kt · Cat ${s.sshs < 0 ? 'TS' : s.sshs}</div><div>${s.iso_time} UTC</div></div>`;
        }}
        // Hex (SST / Coral / CMEMS)
        hexBinPointsData={hexPoints}
        hexBinPointLat={(d: object) => (d as {lat:number}).lat}
        hexBinPointLng={(d: object) => (d as {lat:number;lon:number}).lon}
        hexBinPointWeight={(d: object) => (d as {val:number}).val}
        hexBinResolution={3}
        hexAltitude={0.008}
        hexTopColor={hexColorFn}
        hexSideColor={hexColorFn}
        hexBinMerge={false}
        hexLabel={(d: { sumWeight: number; points: object[] }) => {
          const mean = d.sumWeight / Math.max(d.points.length, 1);
          const label = activeContinuous === 'ocean-heat' ? `${mean.toFixed(1)}°C SST`
            : activeContinuous === 'coral' ? `${mean.toFixed(1)} °C·wk DHW`
            : `${mean.toFixed(0)} mm SLA`;
          return `<div style="background:#0b1120;color:#f1f5f9;padding:5px 8px;border:1px solid #475569;border-radius:4px;font-size:11px;font-family:system-ui,sans-serif;">${label}</div>`;
        }}
        // Air monitors (labels)
        labelsData={airPoints}
        labelLat={(d: object) => (d as AirMonitor).lat}
        labelLng={(d: object) => (d as AirMonitor).lon}
        labelText={() => ''}
        labelDotRadius={0.25}
        labelDotOrientation={() => 'top' as const}
        labelColor={(d: object) => pm25Color((d as AirMonitor).pm25)}
        labelResolution={2}
        labelLabel={(d: object) => {
          const m = d as AirMonitor;
          return `<div style="background:#0b1120;color:#f1f5f9;padding:6px 8px;border:1px solid #475569;border-radius:4px;font-size:11px;font-family:system-ui,sans-serif;max-width:240px;"><div><b>${m.location_name}</b>${m.country ? ` · ${m.country}` : ''}</div><div>PM2.5: ${m.pm25.toFixed(1)} µg/m³</div><div style="color:#94a3b8;">${m.datetime_utc || '—'}</div></div>`;
        }}
      />

      {/* Top-left meta */}
      <div style={headerStyle}>
        <MetaLine cadence={activeMeta.cadence} tag={activeMeta.tag} source={activeMeta.source} sourceUrl={activeMeta.sourceUrl} />
      </div>

      {/* Right accordion layer panel */}
      <LayerPanel
        categories={CATEGORIES}
        activeEvent={activeEvent}
        activeContinuous={activeContinuous}
        openCategory={openCategory}
        onOpenCategory={setOpenCategory}
        onLayerChange={onLayerChange}
        firesData={firesData}
        stormsData={stormsData}
        airData={airData}
      />
    </div>
  );
});

export default Globe;
```

- [ ] **Step 5: Add LayerPanel component**

After the Globe component, add:

```ts
// ── LayerPanel (accordion) ─────────────────────────────────────────────────

interface LayerPanelProps {
  categories: CategoryDef[];
  activeEvent: ActiveEvent;
  activeContinuous: ActiveContinuous;
  openCategory: string | null;
  onOpenCategory: (id: string | null) => void;
  onLayerChange: (type: 'event' | 'continuous', key: string | null) => void;
  firesData: FiresResponse | null;
  stormsData: StormsResponse | null;
  airData: AirMonitorsResponse | null;
}

function LayerPanel({
  categories, activeEvent, activeContinuous, openCategory,
  onOpenCategory, onLayerChange, firesData, stormsData, airData,
}: LayerPanelProps) {
  return (
    <div style={{
      position: 'absolute', top: 12, right: 12,
      width: 188, background: '#111827',
      border: '1px solid #1e293b', borderRadius: '8px',
      overflow: 'hidden', fontFamily: 'system-ui, sans-serif',
      boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
    }}>
      <div style={{ padding: '7px 10px', background: '#1e293b', fontSize: '11px', fontWeight: 600, color: '#e2e8f0' }}>
        🗂 Layers
      </div>
      {categories.map((cat) => {
        const isOpen = openCategory === cat.id;
        return (
          <div key={cat.id}>
            <button
              type="button"
              onClick={() => onOpenCategory(isOpen ? null : cat.id)}
              style={{
                width: '100%', display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', padding: '6px 10px', background: 'transparent',
                border: 'none', cursor: 'pointer', fontSize: '11px',
                color: isOpen ? '#7dd3fc' : '#94a3b8', textAlign: 'left',
              }}
            >
              <span>{cat.emoji} {cat.label}</span>
              <span style={{ fontSize: '9px' }}>{isOpen ? '▾' : '▸'}</span>
            </button>
            {isOpen && (
              <div style={{ paddingBottom: '4px' }}>
                {cat.layers.map((layer, i) => {
                  const isEventActive = layer.type === 'event' && activeEvent === layer.key;
                  const isContinuousActive = layer.type === 'continuous' && activeContinuous === layer.key;
                  const isActive = isEventActive || isContinuousActive;
                  const isDisabled = layer.disabled || layer.key === null;

                  // Count suffix for known layers
                  let countSuffix = '';
                  if (layer.key === 'fires' && firesData) countSuffix = ` (${firesData.count})`;
                  if (layer.key === 'storms' && stormsData) countSuffix = ` (${stormsData.count})`;
                  if (layer.key === 'monitors' && airData?.configured) countSuffix = ` (${airData.count})`;

                  return (
                    <button
                      key={i}
                      type="button"
                      disabled={isDisabled}
                      title={layer.disabledReason}
                      onClick={() => {
                        if (isDisabled || layer.key === null) return;
                        if (layer.type === 'event') {
                          onLayerChange('event', isEventActive ? null : layer.key);
                        } else {
                          onLayerChange('continuous', isContinuousActive ? null : layer.key);
                        }
                      }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '5px',
                        width: '100%', padding: '4px 10px 4px 16px',
                        background: isActive ? '#1d4ed8' : 'transparent',
                        border: 'none', cursor: isDisabled ? 'not-allowed' : 'pointer',
                        fontSize: '10px', color: isDisabled ? '#334155' : isActive ? '#fff' : '#94a3b8',
                        textAlign: 'left', opacity: isDisabled ? 0.55 : 1,
                      }}
                    >
                      <span>{layer.emoji}</span>
                      <span style={{ flex: 1 }}>{layer.label}{countSuffix}</span>
                      {isActive && <span style={{ color: '#93c5fd', fontSize: '9px' }}>ON</span>}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 6: Add color helpers at the bottom**

Keep existing `firePointRadius`, `firePointAltitude`, `sstColor`, `pm25Color`, `rgb` helpers. Add new ones:

```ts
function dhwColor(dhw: number): string {
  // 0 = no stress (blue), 4+ = bleaching alert (red)
  const stops: Array<[number, [number, number, number]]> = [
    [0, [8, 48, 107]],
    [1, [65, 182, 196]],
    [2, [253, 174, 97]],
    [4, [179, 0, 0]],
    [8, [128, 0, 128]],
  ];
  if (dhw <= stops[0][0]) return rgb(stops[0][1]);
  if (dhw >= stops[stops.length - 1][0]) return rgb(stops[stops.length - 1][1]);
  for (let i = 0; i < stops.length - 1; i++) {
    const [c1, rgb1] = stops[i];
    const [c2, rgb2] = stops[i + 1];
    if (dhw >= c1 && dhw <= c2) {
      const t = (dhw - c1) / (c2 - c1);
      return rgb([Math.round(rgb1[0] + (rgb2[0] - rgb1[0]) * t), Math.round(rgb1[1] + (rgb2[1] - rgb1[1]) * t), Math.round(rgb1[2] + (rgb2[2] - rgb1[2]) * t)]);
    }
  }
  return rgb(stops[0][1]);
}

function slaColor(mm: number): string {
  // negative = below average (blue), positive = above (red)
  if (mm < -50) return '#1d4ed8';
  if (mm < 0) return '#38bdf8';
  if (mm < 50) return '#fb923c';
  return '#dc2626';
}

function stormColor(sshs: number): string {
  if (sshs <= 0) return '#fbbf24';   // TD/TS
  if (sshs === 1) return '#f97316';  // Cat 1
  if (sshs === 2) return '#ef4444';  // Cat 2
  if (sshs === 3) return '#b91c1c';  // Cat 3
  if (sshs === 4) return '#7f1d1d';  // Cat 4
  return '#4c0519';                   // Cat 5
}
```

Also remove the now-unused `ContinuousLayer` type and the old `LayerBtn` component and `layerToggleStyle` constant.

- [ ] **Step 7: TypeScript build check**

```bash
cd C:/0_project/terrasight/frontend
npx tsc --noEmit 2>&1 | head -40
```
Fix any type errors before committing. Common issues:
- `TrustTag.Derived` may not exist — check `src/utils/trustTags.ts` and add if missing
- `note` property on `LayerEntry` — add `note?: string` to the interface if needed

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/earth-now/Globe.tsx
git commit -m "feat(globe): accordion layer panel + GIBS canvas composite + storms/coral layers"
```

---

## Task 6 — Check TrustTag.Derived and fix trustTags.ts if missing

**Files:**
- Modify: `frontend/src/utils/trustTags.ts` (if needed)

- [ ] **Step 1: Read trustTags.ts**

```bash
cat frontend/src/utils/trustTags.ts
```

- [ ] **Step 2: Add Derived if missing**

If `TrustTag.Derived` or `TrustTag.NearRealTime` don't exist, add them. The expected full enum:

```ts
export enum TrustTag {
  Observed = 'observed',
  NearRealTime = 'near-real-time',
  ForecastModel = 'forecast/model',
  Derived = 'derived',
  Estimated = 'estimated',
}
```

And add entries to `TRUST_TAG_COLORS` and `TRUST_TAG_LABELS` if those maps exist in the file. If the file exports only `TrustTag`, just add the missing enum values.

- [ ] **Step 3: Commit if changed**

```bash
git add frontend/src/utils/trustTags.ts
git commit -m "feat(trust-tags): add Derived and NearRealTime enum values"
```

---

## Task 7 — Final Build Verify + Push + Progress Update

- [ ] **Step 1: Backend import check**

```bash
cd C:/0_project/terrasight
python -c "from backend.main import app; print('backend OK')"
```
Expected: `backend OK`

- [ ] **Step 2: Frontend type check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```
Expected: no output (zero errors)

- [ ] **Step 3: Git push**

```bash
cd C:/0_project/terrasight
git push origin master
```

- [ ] **Step 4: Update progress.md**

Append a Phase B completion section to `progress.md`:

```markdown
## Phase B — Globe UI 레이어 확장 + Trends 캐러셀 (2026-04-11)

### B.1 Climate Trends 5카드 캐러셀
- `/api/trends` → 5개 병렬 fan-out (CO₂, Temp, Sea Ice, CH₄, Sea Level)
- TrendsStrip.tsx: 3-card grid → 5-card horizontal scroll-snap 캐러셀
- 신규 카드: CH₄ (NOAA GML, ppb) · Sea Level Rise (NOAA NESDIS, mm vs 1993 baseline)

### B.2 Globe 레이어 패널 (우측 아코디언)
5개 카테고리:
| 카테고리 | 레이어 |
|---|---|
| 🌫 Atmosphere | PM2.5 (GIBS) · AOD (GIBS) · Air Monitors (OpenAQ) |
| 🔥 Fire & Land | Active Fires (FIRMS) · Deforestation (disabled P1) · Drought (disabled P1) |
| 🌊 Ocean | SST Anomaly (OISST) · Coral Bleaching (CRW) · Sea Level (CMEMS) |
| 🌿 GHG | CO₂ Column (OCO-2 GIBS) · CH₄ GIBS (disabled — GIBS 미지원) |
| ⚡ Hazards | Tropical Storms (IBTrACS) · Flood Map (GIBS) |

### B.3 새 백엔드 엔드포인트
- `GET /api/earth-now/storms` — IBTrACS ACTIVE 열대폭풍 현재 위치
- `GET /api/earth-now/coral` — CRW 산호 표백 열스트레스 격자
- `GET /api/earth-now/sea-level-anomaly` — CMEMS SLA (CMEMS 계정 필요)

### GIBS 렌더링
- GIBS WMS GetMap transparent PNG → offscreen canvas 합성 → globeImageUrl
- 날짜: 자동 (오늘 → 최대 3일 전 폴백)
```

- [ ] **Step 5: Commit progress.md**

```bash
git add progress.md
git commit -m "docs: update progress.md Phase B completion"
git push origin master
```
