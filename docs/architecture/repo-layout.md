# Repo Layout — v2 monorepo

Last updated: 2026-04-17 (Step 3)

```
terrasight/
├── apps/
│   ├── web/                 # Astro SSG + React islands (new frontend)
│   │   ├── src/
│   │   │   ├── pages/       # .astro routes (SSG output)
│   │   │   ├── layouts/     # shared page shells
│   │   │   └── islands/     # React components (Globe, TrendCards, ...)
│   │   └── astro.config.mjs
│   └── worker/              # Cloudflare Worker (Hono) — proxy + cache only
│       ├── src/
│       │   ├── index.ts     # entry; routes /health, /api/fires, /api/earthquakes, /api/sst-point
│       │   └── routes/
│       └── wrangler.jsonc
│
├── packages/
│   ├── schemas/             # Zod contracts shared by apps/web + apps/worker + pipelines loaders
│   │   └── src/index.ts     # TrustTag, BlockStatus, LayerManifest, EventPoint, CityReport
│   ├── ui/                  # Reusable React UI (trust badges, meta lines, source labels)
│   │   └── src/             # MetaLine, TrustBadge, SourceLabel
│   └── config/              # Shared TS config base
│       └── tsconfig.base.json
│
├── pipelines/               # Python 3.11 batch — GitHub Actions scheduled runs
│   ├── connectors/          # 33 data-source clients (FIRMS, OISST, GIBS, EPA, NOAA, ...)
│   ├── transforms/          # raster → tiles, CSV → parquet, etc. (Step 5)
│   ├── jobs/                # orchestration; one module per scheduled job
│   ├── publish/             # R2 upload + manifest writers
│   └── tests/               # pytest suite (run via `pnpm test:pipelines`)
│
├── backend/                 # **Maintenance stub only** — FastAPI on Render
│   ├── main.py              # 4 endpoints: /health, /fires, /quakes, /sst-point
│   └── requirements.txt     # fastapi + httpx + uvicorn (shrunk from v1)
│
├── legacy/                  # v1 code kept until v2 parity verified
│   ├── backend-api/         # old FastAPI routers (atlas, reports, hazards, ...)
│   ├── backend-connectors/  # connectors excluded from v2 (Open-Meteo, CAMS ads-key, CMEMS)
│   ├── backend-models/      # old SQLAlchemy models (CBSA, cache)
│   ├── backend-scheduler/   # old APScheduler entry
│   ├── backend-utils/       # old surface-renderer (Render runtime raster — banned in v2)
│   ├── frontend/            # v1 Vite + React app (pre-Astro)
│   └── scripts-experimental/# compute_bbox*.py and other one-off scripts
│
├── docs/
│   ├── architecture/        # architecture-v2, mvp-scope-v2, data-source-policy, repo-layout (this file)
│   ├── datasets/            # source-spike-matrix, gibs-approved-layers, runtime-vs-batch-sources
│   ├── setup/               # local-dev
│   ├── legacy/              # retired planning docs (INITIAL_PROMPTS, PROJECT_SETUP, ROADMAP, ...)
│   ├── report-spec.md       # Local Environmental Reports v2 block spec
│   ├── guardrails.md        # verification checklist + landmine table
│   ├── connectors.md        # per-connector cookbook
│   └── terrasight-v2-step-prompts.md   # Step 1-10 execution plan
│
├── progress.md              # current state; update every work session
├── CLAUDE.md                # project context for agents (this repo's charter)
├── package.json             # pnpm root — workspaces + scripts
├── pnpm-workspace.yaml      # apps/* + packages/*
├── pyproject.toml           # pipelines + dev deps
├── Dockerfile               # legacy Render image (points at backend/)
└── data/                    # static seed data bundled into the Render image
```

## One-line rules per top-level directory

- **apps/** — deployable surfaces. Anything user-facing lives here or is imported from packages.
- **packages/** — shared libraries. No deployment target; imported by `apps/*` and `pipelines/`.
- **pipelines/** — long-running batch jobs. Never called at runtime; publish to R2 / Pages.
- **backend/** — *legacy maintenance only*. Will be retired once Worker parity is verified.
- **legacy/** — read-only reference. Delete after parity sign-off (Step 8+).
- **docs/** — source of truth for architecture, data policy, and per-component cookbooks.

## Dependency direction

```
apps/web   →  packages/{schemas,ui}
apps/worker →  packages/schemas
pipelines/ →  packages/schemas (via generated JSON loader, no TS runtime)
```

**Never** the other direction — packages must not import from apps or pipelines.

## Where new code goes

| If you are adding … | Put it in …                                         |
|---------------------|-----------------------------------------------------|
| A new React UI atom | `packages/ui/src/`                                  |
| A new globe layer   | `packages/schemas` (manifest type) + `apps/web`     |
| A new data fetcher  | `pipelines/connectors/`                             |
| A new R2 artifact   | `pipelines/jobs/` + `pipelines/publish/`            |
| A new Worker route  | `apps/worker/src/routes/` + register in `index.ts`  |
| A new Report block  | `packages/schemas` (block type) + `apps/web` page   |

## What should *not* land here

- Runtime raster rendering in `apps/worker/` or `backend/` (forbidden — see `architecture-v2.md` rule 1).
- New imports from `legacy/` outside of a parity-verification PR.
- New dependencies on Open-Meteo in production paths (reference-only; see `data-source-policy.md`).
