# Guardrails & Verification Checklist

Non-negotiable rules and the checks to run before declaring any feature
"done". CLAUDE.md links here — keep this file short and actionable.

## Absolute rules

1. **Never claim "Live" loosely.** Separate "Now" and "Trends" in the
   UI, and always print the update cadence next to the value.
2. **U.S.-first.** Local Reports ship for U.S. metros first. The Atlas
   is global, but revenue and SEO effort are U.S.-aligned.
3. **Reports have interpretation.** No purely templated auto-generated
   report pages. Every report must offer a unique editorial or
   analytical angle.
4. **No environmental "scores".** We ship *reports*, not composite
   scores. Only transparent screenings are allowed; never claim a
   number is a holistic environmental grade.
5. **Source separation for current vs trend.** Even when two signals
   cover the same topic, current and trend must cite different
   sources (AirNow vs AirData / AQS; USGS continuous vs WQP discrete).
6. **Mandatory disclaimers (non-removable):**
   - ECHO: "Regulatory compliance ≠ environmental exposure or health
     risk."
   - WQP: "Discrete samples — dates vary."
   - AirNow: "Reporting area ≠ CBSA boundary."
7. **Google policy compliance.** Avoid scaled content abuse.
   People-first content. No AdSense inside data tables or charts.

## Layer composition rule (Earth Now globe)

At most **one continuous field + one event overlay** active at the
same time. Layer groups in `frontend/src/components/earth-now/Globe.tsx`
enforce this client-side. Examples:

- ✅ Ocean Heat (continuous) + Fires (event)
- ✅ Air Monitors (continuous) + Fires (event)
- ❌ Ocean Heat + Air Monitors (both continuous)

## Trust-tag vocabulary (always attach one)

`observed` 🟢 / `near-real-time` 🟡 / `forecast` 🟠 / `derived` 🔵 /
`estimated` ⚪. Enforced by the `TrustTag` `Literal` in
`backend/connectors/base.py`.

## Trust signal placement

The MetaLine (cadence · trust badge · source) renders **before** the
numerical value. From CLAUDE.md: "메타정보가 숫자보다 먼저 보여야 함".
Applies to every indicator, card, and block.

---

## Verification checklist (before marking a feature done)

Run these in order.

### Backend

- [ ] New / modified connectors use `ConnectorResult` with a valid
      `tag` value (compile-time enforced).
- [ ] Connector has a module docstring explaining endpoint quirks —
      especially anything learned the hard way during implementation
      (see `docs/connectors.md` for the landmines we already know).
- [ ] `python -c "from backend.main import app"` imports cleanly.
- [ ] For each new connector: a standalone smoke test that fetches
      real data (or returns `configured: false` gracefully).
- [ ] Orchestrator endpoints wrap connector failures — a single
      connector outage MUST NOT 5xx the whole route.

### Frontend

- [ ] `npm run build` succeeds with zero TypeScript errors.
- [ ] Bundle stays under 600 KB gzipped (currently ~580 KB).
- [ ] Every new data surface renders a `MetaLine` before any numbers.
- [ ] Loading / error / `not_configured` / `pending` states are
      handled distinctly — no blank screens on partial failure.
- [ ] Mandatory disclaimers from the Absolute Rules section appear
      verbatim on the relevant blocks (ECHO / WQP / AirNow).

### Data correctness

- [ ] Cross-check at least one value in the payload against the
      upstream source (e.g. the AirNow website, the NCEI file you
      fetched from) to catch unit or schema drift.
- [ ] Preserve any URL / endpoint quirk notes in the connector
      docstring so the next person hitting the same landmine finds
      the answer in the code they already have open.

---

## Known landmines (do not re-discover)

| Landmine | Where | Fix |
|---|---|---|
| ECHO `ofmpub.epa.gov` → blocked | `connectors/echo.py` | Use `https://echodata.epa.gov/echo/` |
| ECHO `echo13_rest_services` → 404 on echodata | `connectors/echo.py` | Use `echo_rest_services` (no `13`) |
| ECHO single-hop returns no Facilities | `connectors/echo.py` | Two-hop required: `get_facilities` → QueryID → `get_qid` paginated |
| ECHO `FacLong` absent from QID response | `connectors/echo.py` | Only `FacLat` available; facility map deferred |
| ECHO `CurrVioFlag`/`Over3yrsFormalActions` absent | `connectors/echo.py` | Use `FacSNCFlg` + `FacComplianceStatus` instead |
| WQP `/data/` missing USGS post-2024-03-11 | `connectors/wqp.py` | Use `/wqx3/` beta |
| WQP `/wqx3/Result/search` 500 without profile | `connectors/wqp.py` | `dataProfile=basicPhysChem` |
| WQP `providers=NWIS,STORET` → zero rows | `connectors/wqp.py` | Repeat the param: `providers=NWIS&providers=STORET` |
| WQX 3.0 column renames | `connectors/wqp.py` | `Location_Identifier`, `Result_Characteristic`, `Result_Measure`, `Result_MeasureUnit` |
| USGS feature has no `site_name` | `connectors/usgs.py` | Fall back to `monitoring_location_id`; optional second hop to `/collections/monitoring-locations` |
| NSIDC CSV column contains commas | `connectors/nsidc.py` | Parse via `csv` module, not `.split(",")` |
| CtaG has no REST API | `connectors/noaa_ctag.py` | Pivot to NOAAGlobalTemp CDR v6.1 ASCII |
| `USW00012918` is Houston Hobby, not IAH | `data/cbsa_mapping.json` | Already corrected — watch for similar mislabels on other stations |

Any new landmine discovered during implementation must be added
**to this table and to the relevant connector docstring** before the
feature is marked done. The goal is zero re-learned lessons.
