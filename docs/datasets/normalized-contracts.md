# Normalized Contracts — Step 4 freeze

**Last updated:** 2026-04-17 (Step 4 prerequisite)
**Purpose:** lock the exact JSON shapes that cross the Python → Worker → Browser boundary. Any drift between `packages/schemas/src/index.ts` (zod), `pipelines/contracts/__init__.py` (pydantic), and this doc is a bug.

---

## 1. TrustTag (5 values, frozen)

```
observed · near-real-time · forecast · derived · compliance
```

The v1 `estimated` value is **retired**. Model-origin data now maps to `forecast` (runtime prediction) or `derived` (reanalysis / computed). Regulator-curated data is `compliance`.

---

## 2. Worker response envelope

Every Worker route returns one of two shapes:

### 2a. Event-collection envelope (used by `/api/fires`, `/api/earthquakes`)

```jsonc
{
  "status": "ok" | "error" | "not_configured" | "pending",
  "source": "NASA FIRMS",
  "source_url": "https://firms.modaps.eosdis.nasa.gov/api/area/",
  "cadence": "NRT ~3h",
  "tag": "near-real-time",
  "count": 128,
  "data": [ /* EventPoint[] — see §3 */ ],
  "notes": []  // optional operator-facing strings; UI must not render
}
```

### 2b. Scalar-point envelope (used by `/api/sst-point`)

```jsonc
{
  "status": "ok" | "no_data" | "error",
  "source": "NOAA OISST v2.1",
  "source_url": "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg",
  "cadence": "daily",
  "tag": "observed",
  "lat": 35.2,
  "lon": -120.5,
  "snappedLat": 35.125,       // ERDDAP grid cell centre
  "snappedLon": -120.625,
  "sst_c": 13.42,
  "observed_at": "2026-04-17T00:00:00Z",
  "message": null             // populated when status != ok
}
```

Land / ice cells return `status: "no_data"` with `sst_c: null` and a `message` explaining why. Never `500`.

### 2c. Manifest envelope (used by browser-direct `/api/layers` if ever exposed)

```jsonc
{
  "status": "ok",
  "source": "NASA GIBS",
  "count": 5,
  "data": [ /* LayerManifest[] — see §4 */ ]
}
```

---

## 3. EventPoint (frozen)

Fields:

| Field        | Type                                   | Notes                                             |
|--------------|----------------------------------------|---------------------------------------------------|
| `id`         | `string`                               | Stable per record across time-windows             |
| `type`       | `"wildfire" \| "earthquake" \| "alert"`| Alert = NWS active, Step 6+                       |
| `lat`        | `number` (-90..90)                     |                                                   |
| `lon`        | `number` (-180..180)                   | **Always `-180..180`**, even from 0-360 sources   |
| `observedAt` | `string` (ISO-8601 UTC)                | Not raw epoch-ms                                  |
| `severity`   | `number \| string \| null`             | Source-specific: FIRMS FRP, USGS magnitude        |
| `label`      | `string`                               | Short human-readable — "M4.3 — 12 km E of Adak"   |
| `properties` | `Record<string, unknown>`              | Anything else the source returned                 |

**Severity mapping reference:**

| Source    | `severity` field              | Unit / range                  |
|-----------|-------------------------------|-------------------------------|
| FIRMS     | Fire Radiative Power          | MW, ~0.1 – 5000               |
| USGS      | Magnitude (moment / local)    | Richter-ish, -1.0 – 9.5       |
| NWS alert | Severity enum string          | "minor"\|"moderate"\|"severe"\|"extreme" |

---

## 4. LayerManifest (frozen; 5 entries in v2 MVP)

Already defined in `packages/schemas/src/index.ts`. Repeated here with the MVP-freeze notes:

- `category`: `"imagery"` for GIBS tiles, `"event"` for Worker-proxied points.
- `kind`: `"continuous"` (bounded colormap) vs `"event"` (point overlay).
- `imagery.urlTemplate` uses `{Time}` for date token and `{z}/{y}/{x}` for tile coords — Cesium REST pattern. No XYZ/TMS.
- `imagery.availableDates` is a human-readable range, e.g. `"2012-01-19/present"`.
- `eventApi.path` is a relative path (`/api/fires`), not absolute. The web app prepends Worker origin at runtime.
- `caveats` is required and non-empty — every layer has at least one known limitation (ENCC frozen, ocean-only, day-only, dust-proxy labelling, etc.).

---

## 5. Caching policy (Worker)

| Route              | TTL (seconds) | Reason                                   |
|--------------------|--------------:|------------------------------------------|
| `/api/fires`       | `600` (10 m)  | FIRMS NRT cadence ~3h; 10m is safe       |
| `/api/earthquakes` | `300` (5 m)   | USGS summary feed regenerates ~1-5 min   |
| `/api/sst-point`   | `3600` (1 h)  | OISST daily — hourly cache is generous   |

Keys: `{route}:{sorted-query-string}`. Worker uses the Cloudflare Cache API (`caches.default`). Missing key → fetch upstream → `Cache-Control: public, max-age=<ttl>` + put.

---

## 6. Graceful-degradation rules

- Transport error (network, 5xx, timeout) → `status: "error"`, `data: []`, `message: <short op string>`. **Never** re-throw to the handler (no 502s from Worker).
- Auth missing (e.g. `FIRMS_MAP_KEY` unset in dev) → `status: "not_configured"`, `data: []`. UI renders the toggle as disabled.
- Empty but successful upstream (zero fires in bbox) → `status: "ok"`, `data: []`, `count: 0`. Not an error.
- Unimplemented route → `status: "pending"`. Should never ship to prod.

---

## 7. Python ↔ TypeScript sync

Run after any contract change:

```bash
# Python side
uv run pytest pipelines/tests -k contract

# TypeScript side (type-checks zod against imports in apps/ and packages/ui/)
pnpm -r lint
```

Both must pass in the same PR.

---

## 8. Related files

- `packages/schemas/src/index.ts` — zod authoritative copy
- `pipelines/contracts/__init__.py` — pydantic mirror
- `pipelines/connectors/base.py` — `ConnectorResult` wrapper used inside Python
- `apps/worker/src/index.ts` — Worker entrypoint that glues routes to this envelope
