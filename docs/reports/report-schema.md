# CityReport Schema (v2, Step 5)

> Frozen contract for the static ``data/reports/{slug}.json`` artifact
> produced by ``pipelines/jobs/build_reports.py``. Mirror in zod:
> ``packages/schemas/src/index.ts``. Mirror in pydantic:
> ``pipelines/contracts/__init__.py``.
>
> Block inclusion rules: ``docs/reports/report-block-policy.md``.

## 1. Top-level shape

```jsonc
{
  "slug": "new-york-newark-jersey-city",
  "cbsaCode": "35620",
  "city": "New York-Newark-Jersey City",
  "region": "NY",
  "country": "US",
  "coastal": true,
  "lat": 40.71,
  "lon": -74.00,
  "population": 19768000,
  "populationYear": "2022",
  "climateZone": "Humid subtropical (Cfa)",
  "summary": { "headline": "...", "bullets": ["..."] },
  "blocks": [ /* 8 core + 0..4 optional — see §3 */ ],
  "meta": { /* §4 */ }
}
```

Required: everything above except `population`, `populationYear`,
`climateZone` (optional — may be missing for smaller metros).

### 1.1 Field reference

| Field | Type | Notes |
|---|---|---|
| `slug` | string | Stable URL segment; matches the filename (`{slug}.json`). |
| `cbsaCode` | string | 5-digit CBSA code from the U.S. Census OMB list. |
| `city` | string | CBSA title-case name (e.g., "Houston-The Woodlands-Sugar Land"). |
| `region` | string | Primary state abbreviation (may be multi-state; first state from mapping). |
| `country` | literal `"US"` | Reports are U.S.-only at Step 5. |
| `coastal` | boolean | Gates the optional `coastal_conditions` block. |
| `lat` / `lon` | number | CBSA centroid (approximate, hand-curated). |
| `population` | int \| null | Census CBSA estimate. |
| `populationYear` | string \| null | Year label for the estimate. |
| `climateZone` | string \| null | Köppen classification + label. |
| `summary` | object | `headline` + `bullets[]` auto-composed from block state. |
| `blocks` | `ReportBlock[]` | See §3. |
| `meta` | `CityReportMeta` | See §4. |

## 2. `ReportBlock`

```jsonc
{
  "id": "air_quality",
  "title": "Air Quality",
  "status": "ok",
  "trustTag": "observed",
  "body": "Ambient air quality ...",
  "metrics": [
    {
      "label": "PM2.5 annual mean",
      "value": 10.4,
      "unit": "µg/m³",
      "note": "...",
      "trustTag": "observed"
    }
  ],
  "citations": [
    { "label": "EPA AirNow", "url": "https://www.airnow.gov/" }
  ],
  "error": null,
  "notes": [
    "AirNow reporting area may differ from the CBSA boundary."
  ],
  "data": { /* optional block-specific payload */ }
}
```

### 2.1 Field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `BlockId` enum | yes | One of 13 block ids — 8 core + 5 optional (see §3). |
| `title` | string | yes | Display label — stable across builds. |
| `status` | `BlockStatus` enum | yes | `ok` / `error` / `not_configured` / `pending`. |
| `trustTag` | `TrustTag` enum | yes | Block-level; weakest-wins across sources. |
| `body` | string | yes | Short prose explaining what the block measures and why. |
| `metrics` | `ReportMetric[]` | yes (≥0) | Per-metric rows with optional per-metric `trustTag`. |
| `citations` | `ReportCitation[]` | yes (≥0) | Human-readable label + URL per source programme. |
| `error` | string \| null | no | Populated when `status ≠ "ok"`. |
| `notes` | string[] | yes (≥0) | Mandatory disclaimers / caveats (ECHO / WQP / AirNow). |
| `data` | object \| null | no | Freeform block-specific data (e.g., ranking payload). |

### 2.2 Enum vocabularies

**`BlockId`** (13):
- Core (8): `air_quality` · `climate_locally` · `hazards_disasters` · `water` · `industrial_emissions` · `site_cleanup` · `population_exposure` · `methodology`
- Optional (5): `pfas_monitoring` · `coastal_conditions` · `disaster_history_detailed` · `city_comparison` · `related_cities`

**`BlockStatus`**: `ok` · `error` · `not_configured` · `pending`

**`TrustTag`**: `observed` · `near-real-time` · `forecast` · `compliance` · `derived`
(Weakest-wins combine rule: weakest = last in this list)

## 3. Block list (`blocks[]`)

Order is fixed. See `docs/reports/report-block-policy.md` for the full
inclusion contract.

1. `air_quality` (core, always)
2. `climate_locally` (core, always)
3. `hazards_disasters` (core, always)
4. `water` (core, always)
5. `industrial_emissions` (core, always)
6. `site_cleanup` (core, always)
7. `population_exposure` (core, always)
8. `methodology` (core, always)
9. `pfas_monitoring` (optional — gate: UCMR5 has ≥1 sample for CBSA ZIP)
10. `coastal_conditions` (optional — gate: `coastal === true`)
11. `disaster_history_detailed` (optional — gate: OpenFEMA ≥1 declaration)
12. `related_cities` (optional — gate: ≥1 peer in same climate_zone OR region)

`city_comparison` **never** appears in `blocks[]`. Ranking data is
served separately at `data/rankings/*.json` and joined on the client.

## 4. `CityReportMeta`

```jsonc
{
  "updatedAt": "2026-04-18T00:28:36+00:00",
  "build": {
    "pipelineVersion": "v2.step5.0",
    "generatedAt": "2026-04-18T00:28:36+00:00"
  },
  "optionalAvailability": {
    "pfas_monitoring": "absent",
    "coastal_conditions": "included",
    "disaster_history_detailed": "absent",
    "city_comparison": "external",
    "related_cities": "included"
  }
}
```

- `updatedAt` — when the report's underlying data was last considered
  current. Equal to `build.generatedAt` for now; may diverge once
  per-block recomputation lands in later steps.
- `build.pipelineVersion` — bumps on any composer or schema change
  (Step 5 baseline = `v2.step5.0`). Downstream readers use this to
  detect stale artifacts.
- `optionalAvailability` — fixed 5-key map. Values: `"included"` /
  `"absent"` / `"external"`. The `"external"` value applies only to
  `city_comparison` by design.

## 5. Report index (`data/reports/index.json`)

```jsonc
{
  "generatedAt": "2026-04-18T00:28:36+00:00",
  "pipelineVersion": "v2.step5.0",
  "reports": [
    {
      "slug": "new-york-newark-jersey-city",
      "cbsaCode": "35620",
      "city": "New York-Newark-Jersey City",
      "region": "NY",
      "updatedAt": "2026-04-18T00:28:36+00:00",
      "status": "partial",
      "coreBlocksOk": 2,
      "coreBlocksTotal": 8
    }
  ]
}
```

`status` rollup rules (from `_classify_index_status` in
`pipelines/jobs/build_reports.py`):

| Report rollup | Condition |
|---|---|
| `ok` | Every core block's `status == "ok"` |
| `error` | Any core block's `status == "error"` |
| `partial` | Otherwise (mixture of `ok` / `pending` / `not_configured`) |

## 6. Rankings (`data/rankings/*.json`)

One file per metric. Step 5 ships 4:

| Metric | Unit | Direction | Source block |
|---|---|---|---|
| `air_quality_pm25` | µg/m³ | asc (lower = better) | `air_quality` |
| `emissions_ghg_total` | metric tons CO₂e | asc | `industrial_emissions` |
| `water_violations_count` | violations | asc | `water` |
| `disaster_declarations_10y` | events | asc | `hazards_disasters` |

Each `Ranking` carries `rows[]` of `RankingRow` ordered by rank.
`value=null` rows drop to the bottom with `rank=null`.

`data/rankings/index.json` is a `RankingsIndex` listing every ranking
file with its `nCbsa` count + `generatedAt` timestamp.

## 7. Validation

**Python (pydantic):**
```python
from pipelines.contracts import CityReport
CityReport.model_validate(json.loads(path.read_text()))
```

**TypeScript (zod):**
```ts
import { CityReport } from '@terrasight/schemas';
CityReport.parse(await (await fetch(url)).json());
```

Locking tests: `pipelines/tests/test_report_contract.py` — 14 tests
covering composer output, sample artifacts, and all invariants from §3.

## 8. Versioning

Pipeline version bumps (`vX.stepN.M`) happen when:

- The block list changes (add/remove/rename core OR optional).
- `ReportBlock` field shape changes.
- `CityReportMeta` gains/loses fields.
- Any enum grows a new value.

Renaming a block id is a breaking change — bump `pipelineVersion` AND
produce a migration note. Adding a new `notes[]` entry is NOT a
breaking change.
