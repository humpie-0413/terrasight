# Local Development Setup — v2 monorepo

Last updated: 2026-04-17

The repo is a **pnpm workspace** for TypeScript/React code and a **uv / pip** project for Python pipelines. The transitional `backend/` FastAPI stub has its own `requirements.txt`.

---

## Prerequisites

| Tool     | Version        | Why                                         |
|----------|----------------|---------------------------------------------|
| Node.js  | `>= 20.10`     | Astro 4, Wrangler, React 18                 |
| pnpm     | `9.6.0`        | Pinned in root `package.json` packageManager|
| Python   | `3.11.x`       | `pyproject.toml` requires-python            |
| uv       | latest         | Fast Python env/runner (preferred over pip) |
| Wrangler | `>= 3.80`      | Cloudflare Worker local dev                 |
| git      | any            | Large history — avoid full clones on CI     |

Install pnpm via Corepack:

```bash
corepack enable
corepack prepare pnpm@9.6.0 --activate
```

Install `uv`:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## One-time setup

```bash
# 1. Clone + enter
git clone https://github.com/<org>/terrasight.git
cd terrasight

# 2. JS workspace install
pnpm install

# 3. Python env (pipelines + backend stub)
uv sync                    # creates .venv from pyproject.toml
# OR, if you prefer pip:
# python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# 4. Copy env templates where they exist
cp legacy/frontend/.env.example .env.local    # any values you still need
```

---

## Daily commands

All commands run from the repo root.

| Goal                                   | Command                                 |
|----------------------------------------|-----------------------------------------|
| Run the Astro site (port 4321)         | `pnpm dev:web`                          |
| Run the Cloudflare Worker locally      | `pnpm dev:worker`                       |
| Build Astro site for production        | `pnpm build:web`                        |
| Build / deploy Worker                  | `pnpm build:worker`                     |
| Run pipelines pytest suite             | `pnpm test:pipelines` *(alias)*         |
|                                        | `uv run pytest pipelines/tests`         |
| Lint every TS workspace                | `pnpm lint`                             |
| Run the legacy Render stub (optional)  | `uvicorn backend.main:app --reload`     |

The Astro dev server and the Worker dev server can run side-by-side: Astro serves the site at `http://localhost:4321`, Worker binds `http://localhost:8787`. The Astro `_redirects` file points `/api/*` to the current deployed Worker URL; override this in dev via a Vite proxy when needed.

---

## Pipelines (GitHub Actions batch)

The `pipelines/` package produces R2 artifacts on a schedule. Local smoke test:

```bash
uv run pytest pipelines/tests -v
```

Individual job invocations (once implemented) will follow:

```bash
uv run python -m pipelines.jobs.<job_name> --date 2026-04-17
```

See `docs/architecture/architecture-v2.md` §"Batch pipeline boundary" for which sources are batch vs runtime.

---

## Common issues

- **pnpm install fails with "packageManager mismatch"** — run `corepack prepare pnpm@9.6.0 --activate`.
- **Wrangler cannot find `wrangler.jsonc`** — `cd apps/worker` then `wrangler dev`, or use the root `pnpm dev:worker` script.
- **`cfgrib` install fails on Windows** — expected. It is declared non-Windows in `pyproject.toml`. Run GRIB-consuming jobs inside WSL or on the CI runner.
- **CesiumJS assets 404 in Astro dev** — Cesium's static assets must be copied to `apps/web/public/cesium/`. Step 4 wires this up; the v2 Globe island is a placeholder until then.

---

## Where to read next

- `docs/architecture/repo-layout.md` — which directory does what.
- `docs/architecture/architecture-v2.md` — the full v2 system diagram.
- `docs/guardrails.md` — landmines you will hit; read **before** adding a connector.
- `progress.md` — current step, blockers, next actions.
