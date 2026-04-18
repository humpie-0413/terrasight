# Report Block Policy (v2, Step 5)

> Authoritative contract for how `data/reports/{slug}.json` blocks are
> composed, included, and surfaced. Locked **before** `build_reports.py`
> and `block_composer.py` are written, so schema + composer + client can
> never drift from each other.
>
> Referenced by: `packages/schemas/src/index.ts` · `pipelines/transforms/block_composer.py` · `pipelines/jobs/build_reports.py` · `docs/reports/report-schema.md` (TBD)

## 0. Scope

Per CLAUDE.md Rule 3, every `report.json` is **statically generated**
at build time. This document fixes two policy gates that must be
settled before any schema or composer code is written.

## 1. Block inclusion — Rule 5 refined

Rule 5 ("Graceful status — every block/endpoint returns `ok` / `error`
/ `not_configured` / `pending`") is refined for reports as follows:

### 1.1 Core blocks (8, **always present**)

| # | id | Title | Primary sources |
|---|---|---|---|
| 1 | `air_quality` | 대기질 / Air Quality | AirNow + ECHO context |
| 2 | `climate_locally` | 기후·열환경 / Climate Locally | NOAA ClimateNormals + derived heat-days |
| 3 | `hazards_disasters` | 재해노출 / Disaster Exposure | OpenFEMA (summary) |
| 4 | `water` | 음용수·수질 / Drinking Water + Surface WQ | SDWIS + WQP |
| 5 | `industrial_emissions` | 산업시설·배출 / Industrial & Emissions | TRI + GHGRP + ECHO |
| 6 | `site_cleanup` | 오염부지·정화 / Contaminated Sites | Superfund + Brownfields + RCRA |
| 7 | `population_exposure` | 인구노출·환경정의 / EJ | cbsa_mapping + EJSCREEN (Step 5: stub) |
| 8 | `methodology` | 방법론·데이터신뢰 / Methodology & Data Trust | composed from all above |

**Rule:** These 8 block ids MUST appear in `blocks[]` in every
report, in this exact order, regardless of data availability.

Failure semantics (core block):

| State | Resulting block | `status` | `data` | `error`/`notes` |
|---|---|---|---|---|
| Composer produced a valid block | present | `"ok"` | populated | — |
| Required API key missing at build | present | `"not_configured"` | `null` | explain key |
| Block wired but source fetch failed | present | `"error"` | `null` | error summary |
| Block reserved, composer not wired | present | `"pending"` | `null` | "pending" |

**Core blocks are never omitted.** This keeps per-metro report
layouts structurally identical, so the frontend never has to branch
on "does this metro have a water block" — it always does.

### 1.2 Optional blocks (5, **gate-based**)

| # | id | Title | Gate condition |
|---|---|---|---|
| 1 | `pfas_monitoring` | PFAS Monitoring | UCMR5 has ≥1 sample for any ZIP in `cbsa.zip_prefixes[]` |
| 2 | `coastal_conditions` | Coastal Conditions | `cbsa.coastal === true` |
| 3 | `disaster_history_detailed` | Disaster History (detail) | OpenFEMA returns ≥1 declaration in last 10 years |
| 4 | `city_comparison` | City Comparison | **external** — not embedded (see §2) |
| 5 | `related_cities` | Related Cities | ≥1 other CBSA in same `climate_zone` or `region` |

**Rule:** Optional blocks are included in `blocks[]` **only when
their gate is `true`**.

Gate truth table:

| Gate | Fetch | Behavior |
|---|---|---|
| `false` | — | Block **omitted** from `blocks[]`; status recorded in `meta.optionalAvailability` |
| `true` | success | Block present; `status = "ok"` |
| `true` | failure | Block present; `status ∈ {"error", "not_configured", "pending"}` |

### 1.3 `meta.optionalAvailability`

Every `CityReport.meta` carries a map of the 5 optional block ids
to their availability state:

```jsonc
{
  "meta": {
    "updatedAt": "2026-04-18T06:00:00Z",
    "optionalAvailability": {
      "pfas_monitoring":           "absent",   // gate=false
      "coastal_conditions":        "included", // gate=true, present in blocks[]
      "disaster_history_detailed": "included",
      "city_comparison":           "external", // served via data/rankings/*.json
      "related_cities":            "included"
    }
  }
}
```

Values: `"included"` (gate=true, block in `blocks[]`) ·
`"absent"` (gate=false, block omitted) ·
`"external"` (always-absent by policy — applies only to `city_comparison`).

Frontends consume this map to show copy like "PFAS not monitored in
this metro" without having to scan `blocks[]`.

### 1.4 Rationale

Forcing 8 core blocks to always render keeps the report page
layout and SEO structure deterministic across all CBSAs. Optional
blocks by definition don't apply uniformly (PFAS covers ~4% of
U.S. public water systems; coastal applies to coastal metros only) —
hiding them when their gate is false prevents a wall of "N/A"
sections that would both hurt UX and dilute page relevance for
SEO.

## 2. City Comparison — separate `rankings.json` artifact

**Decision:** `city_comparison` is **not embedded** in any
`report.json`. Ranking data lives in a separate set of artifacts:
`data/rankings/*.json`.

### 2.1 Alternatives considered

| Option | Description | Decision |
|---|---|---|
| A. 2-pass enrichment | `build_reports.py` writes reports without city_comparison; `build_rankings.py` then **rewrites** each report.json injecting the block | **Rejected** |
| B. Separate rankings file | `build_reports.py` owns `reports/*.json`; `build_rankings.py` owns `rankings/*.json`; client composes at render | **Chosen** |

### 2.2 Why separate files win

- **Single-owner write semantics.** Each artifact has one producer
  and one write path. No job ever overwrites another job's output.
- **Scales to 100 CBSAs** without N-file second-pass churn. At
  scale, pass-2 enrichment means 100+ atomic-rewrite operations
  per build; a failure mid-pass leaves the tree inconsistent.
- **Different cadences.** Report data may rebuild monthly;
  rankings can rebuild weekly or on-demand without regenerating
  all reports.
- **Client already loads manifests.** Astro report page will fetch
  `reports/{slug}.json`; adding a second `fetch()` for the
  relevant `rankings/*.json` is cheap (~5-50 KB at 100 CBSAs,
  served from R2 edge).
- **Portable report.json.** A single report file remains
  self-verifiable — its contents describe a metro's own state,
  not its neighbors'.

### 2.3 File layout

```
data/
├── reports/
│   ├── index.json                          # { slug, city, region, updatedAt, status }[]
│   ├── new-york-newark-jersey-city.json
│   ├── los-angeles-long-beach-anaheim.json
│   └── houston-the-woodlands-sugar-land.json
└── rankings/
    ├── index.json                          # { metric, file, generatedAt, n_cbsa }[]
    ├── air_quality.json                    # { metric: "pm25_mean", rows: [{ slug, value, rank, trustTag }] }
    ├── emissions_ghg.json
    ├── water_violations.json
    └── disaster_exposure.json
```

### 2.4 Build ordering (unchanged from approval flow)

```
schema → block-policy doc → composer → build_reports(NY/LA/Houston)
        → schema/QA verify → build_rankings → (optional 2nd enrichment)
        → expand to full CBSA set
```

`build_rankings.py` **reads** each `data/reports/{slug}.json` but
never writes back to it.

### 2.5 Client join

The Astro/React report page fetches both in parallel:

```ts
const [report, ...rankings] = await Promise.all([
  fetch(`/data/reports/${slug}.json`).then(r => r.json()),
  fetch(`/data/rankings/air_quality.json`).then(r => r.json()),
  fetch(`/data/rankings/emissions_ghg.json`).then(r => r.json()),
  // …
]);
```

The City Comparison view is composed at render time from `slug`
lookups into each rankings file. Miss = "not ranked in this
metric" (shown as `—`).

## 3. Block `status` vocabulary (canonical, v2)

Matches Step 4 `BlockStatus` enum frozen in
`packages/schemas/src/index.ts` and `pipelines/contracts/__init__.py`:

| Value | Meaning |
|---|---|
| `ok` | Composer produced a valid block from usable source data |
| `not_configured` | Required env var / API key missing at build time |
| `pending` | Block reserved but composer not yet wired (Step 5 placeholder) |
| `error` | Build-time fetch / compose threw after retries |

All blocks present in `blocks[]` — core or optional — MUST carry a
`status` field. The frontend never renders data for any `status`
other than `"ok"`; instead it renders the `error` / `notes`
explanation in a muted "데이터 없음" card.

## 4. TrustTag propagation per block

Per Step 4 vocabulary: `observed | near-real-time | forecast | derived | compliance`.

Rule: a block's `trustTag` = the **weakest** tag among its
composited source tags, ranked (strongest → weakest):

```
observed > near-real-time > forecast > compliance > derived
```

Special cases:
- `methodology` block: always `derived` (no direct observation).
- `population_exposure` block in Step 5: `derived` (stub; upgrade
  to `observed` when EJSCREEN wired).
- `city_comparison` (if re-embedded in a future step): `derived`.

## 5. Summary of pre-coding lock-in

| Decision | Value |
|---|---|
| Core block count | 8 (always present) |
| Core block IDs & order | see §1.1 |
| Optional block count | 5 (gate-based) |
| Optional block gates | see §1.2 |
| Gate=false behavior | block omitted, recorded in `meta.optionalAvailability` |
| Gate=true + fetch fail | block present, `status ≠ "ok"` |
| City Comparison | separate `data/rankings/*.json`, client-joined |
| `blocks[]` uniform shape | `{ id, title, status, trustTag, data, error?, notes? }` |
| TrustTag combine rule | weakest-wins |

No schema or composer code is written until this document is in
the repo at this path.
