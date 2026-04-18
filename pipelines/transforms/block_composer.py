"""Block composer — builds the 8 core + 5 optional :class:`ReportBlock`
entries that make up a :class:`CityReport`.

Contract locked by ``docs/reports/report-block-policy.md``:

- **Core blocks (8)** — always present in ``blocks[]`` in the fixed order
  defined by :data:`CORE_BLOCK_ORDER`. Missing data ⇒ block with
  ``status != "ok"``, never omitted.
- **Optional blocks (5)** — included only when their gate is ``true``.
  Gate=false ⇒ block omitted; availability recorded in
  ``meta.optionalAvailability``. Gate=true + fetch-fail ⇒ block present
  with ``status != "ok"``.
- **TrustTag combine** — weakest-wins ranking
  ``observed > near-real-time > forecast > compliance > derived``.
- **City Comparison** is NEVER embedded — served externally via
  ``data/rankings/*.json`` (``optionalAvailability.city_comparison =
  "external"`` in every report).

v2 Step 5 scope note
--------------------
Only a handful of v2 connectors exist today (GIBS, FIRMS, USGS, ERDDAP).
The full report fan-out (AirNow, ECHO, TRI, GHGRP, Superfund,
Brownfields, RCRA, SDWIS, WQP, ClimateNormals, OpenFEMA, PFAS, CO-OPS)
still lives in ``legacy/backend-api/``. Step 5 ships the scaffolding:
every core block always appears, but blocks whose v2 connector is not
yet wired return ``status = "pending"`` with a human-readable note.
Subsequent steps replace those placeholders with real composed data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pipelines.contracts import (
    BlockId,
    BlockStatus,
    CoreBlockId,
    OptionalAvailability,
    OptionalAvailabilityMap,
    OptionalBlockId,
    ReportBlock,
    ReportCitation,
    ReportMetric,
    TrustTag,
)

# ---------------------------------------------------------------------------
# Fixed order of the 8 core blocks. CityReport.blocks[] MUST preserve this
# order for every report. Same order locked in
# docs/reports/report-block-policy.md §1.1.
# ---------------------------------------------------------------------------
CORE_BLOCK_ORDER: tuple[CoreBlockId, ...] = (
    "air_quality",
    "climate_locally",
    "hazards_disasters",
    "water",
    "industrial_emissions",
    "site_cleanup",
    "population_exposure",
    "methodology",
)

# Weakest-wins ranking. Smaller index = stronger. See policy §4.
_TRUST_TAG_RANK: dict[TrustTag, int] = {
    "observed": 0,
    "near-real-time": 1,
    "forecast": 2,
    "compliance": 3,
    "derived": 4,
}


def combine_trust_tags(tags: Iterable[TrustTag]) -> TrustTag:
    """Combine one or more trust tags into a single block-level tag.

    Returns the *weakest* tag (highest rank index). Empty input falls
    back to ``"derived"``, matching the methodology/EJ-stub convention.
    """
    tag_list = list(tags)
    if not tag_list:
        return "derived"
    return max(tag_list, key=lambda t: _TRUST_TAG_RANK[t])


# ---------------------------------------------------------------------------
# CBSA input shape — dict drawn from data/cbsa_mapping.json. The composer
# does not re-validate the mapping; build_reports.py is responsible.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CbsaContext:
    """Subset of cbsa_mapping.json fields used during composition.

    Kept as a dataclass so each block function can document which fields
    it actually consumes. Population/climate_zone are optional because
    they may be missing for smaller metros.
    """

    cbsa_code: str
    slug: str
    name: str
    state: str
    coastal: bool
    lat: float
    lon: float
    bbox_west: float
    bbox_south: float
    bbox_east: float
    bbox_north: float
    zip_prefixes: tuple[str, ...]
    population: int | None
    population_year: str | None
    climate_zone: str | None
    core_county_fips: str | None
    core_county_name: str | None
    airnow_reporting_area: str | None
    noaa_station_id: str | None
    noaa_station_name: str | None


def cbsa_from_mapping(cbsa_code: str, entry: dict) -> CbsaContext:
    """Build a :class:`CbsaContext` from one record in cbsa_mapping.json.

    Only the fields actually read by composer functions are extracted;
    everything else is ignored. Missing optional fields map to ``None``.
    """
    bbox = entry.get("bbox") or {}
    airnow = entry.get("airnow") or {}
    noaa = entry.get("noaa") or {}
    return CbsaContext(
        cbsa_code=cbsa_code,
        slug=entry["slug"],
        name=entry["name"],
        state=entry["state"],
        coastal=bool(entry.get("coastal", False)),
        lat=float(entry["lat"]),
        lon=float(entry["lon"]),
        bbox_west=float(bbox.get("west", entry["lon"] - 1.0)),
        bbox_south=float(bbox.get("south", entry["lat"] - 1.0)),
        bbox_east=float(bbox.get("east", entry["lon"] + 1.0)),
        bbox_north=float(bbox.get("north", entry["lat"] + 1.0)),
        zip_prefixes=tuple(entry.get("zip_prefixes") or ()),
        population=(
            int(entry["population"]) if entry.get("population") is not None else None
        ),
        population_year=(
            str(entry["population_year"])
            if entry.get("population_year") is not None
            else None
        ),
        climate_zone=entry.get("climate_zone"),
        core_county_fips=entry.get("core_county_fips"),
        core_county_name=entry.get("core_county_name"),
        airnow_reporting_area=airnow.get("reporting_area"),
        noaa_station_id=noaa.get("city_station_id"),
        noaa_station_name=noaa.get("city_station_name"),
    )


# ---------------------------------------------------------------------------
# Source data envelope — what each upstream connector hands the composer.
# Step 5 uses this shape for the few wired connectors; pending blocks get
# ``SourceResult.pending(...)``.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SourceResult:
    """One upstream source's contribution to a block.

    The composer reads ``status`` + ``trust_tag`` to determine the
    block's own status and tag. ``payload`` is the source-specific data
    (left freeform; each block function interprets its own keys).
    """

    status: BlockStatus
    trust_tag: TrustTag
    source_label: str
    source_url: str
    note: str | None = None
    payload: dict | None = None

    @classmethod
    def pending(cls, source_label: str, reason: str) -> "SourceResult":
        return cls(
            status="pending",
            trust_tag="derived",
            source_label=source_label,
            source_url="",
            note=reason,
            payload=None,
        )


# ---------------------------------------------------------------------------
# Pending-block helper. Used by every v1-only source until its v2
# connector lands. The block is present in blocks[] but carries
# status='pending' + a note explaining why.
# ---------------------------------------------------------------------------
def _pending_block(
    block_id: BlockId,
    title: str,
    body: str,
    sources: list[tuple[str, str]],
    notes: list[str] | None = None,
) -> ReportBlock:
    citations = [
        ReportCitation(label=label, url=url)
        for label, url in sources
    ]
    return ReportBlock(
        id=block_id,
        title=title,
        status="pending",
        trustTag="derived",
        body=body,
        metrics=[],
        citations=citations,
        error="Upstream v2 connector not yet wired (Step 5 scaffolding).",
        notes=notes or [],
        data=None,
    )


# ---------------------------------------------------------------------------
# 8 core block builders
# Each takes (ctx, *source_results) and returns exactly one ReportBlock.
# Step 5 wires the obvious signals; the rest are ``pending`` with notes.
# ---------------------------------------------------------------------------

def build_air_quality_block(
    ctx: CbsaContext,
    airnow: SourceResult | None = None,
    echo_facilities: SourceResult | None = None,
) -> ReportBlock:
    """대기질 — AirNow current AQI + ECHO compliance context."""
    if airnow is None and echo_facilities is None:
        return _pending_block(
            block_id="air_quality",
            title="Air Quality",
            body=(
                f"Ambient air quality in the {ctx.name} metro is tracked "
                "by EPA AirNow (current AQI) and regulated facility "
                "compliance via EPA ECHO. Step 5 scaffolding — live "
                "AirNow/ECHO data pending v2 connector migration."
            ),
            sources=[
                ("EPA AirNow", "https://www.airnow.gov/"),
                ("EPA ECHO", "https://echo.epa.gov/"),
            ],
            notes=[
                "AirNow reporting area may differ from the CBSA boundary — "
                "regional readings approximate metro conditions.",
                "ECHO compliance status is not a direct measure of local "
                "exposure (compliance ≠ exposure).",
            ],
        )
    # TODO(step6): compose real AirNow + ECHO data.
    return _pending_block(
        block_id="air_quality",
        title="Air Quality",
        body="",
        sources=[],
    )


def build_climate_locally_block(
    ctx: CbsaContext,
    normals: SourceResult | None = None,
) -> ReportBlock:
    """기후·열환경 — NOAA 1991-2020 climate normals + heat-days derived."""
    notes = []
    if ctx.climate_zone:
        notes.append(f"Köppen climate zone: {ctx.climate_zone}.")
    if ctx.noaa_station_name:
        notes.append(
            f"Reference station: {ctx.noaa_station_name} "
            f"({ctx.noaa_station_id})."
        )
    return _pending_block(
        block_id="climate_locally",
        title="Climate & Heat",
        body=(
            f"Local climate baseline for {ctx.name} is drawn from the "
            "NOAA 1991-2020 climate normals at the primary city station. "
            "Heat-day counts (days ≥ 90°F / ≥ 95°F) are derived from daily "
            "summaries. Step 5 scaffolding — ClimateNormals v2 connector "
            "pending."
        ),
        sources=[
            (
                "NOAA Climate Normals",
                "https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals",
            ),
        ],
        notes=notes,
    )


def build_hazards_disasters_block(
    ctx: CbsaContext,
    openfema: SourceResult | None = None,
) -> ReportBlock:
    """재해노출 — OpenFEMA declaration summary (last 10 years)."""
    return _pending_block(
        block_id="hazards_disasters",
        title="Disaster Exposure",
        body=(
            f"Federal disaster declarations affecting {ctx.core_county_name or ctx.name} "
            "over the past decade are catalogued by OpenFEMA. The summary "
            "block reports counts by incident type; the detailed "
            "event-level history appears in the optional Disaster History "
            "block when ≥1 declaration is present."
        ),
        sources=[
            ("OpenFEMA", "https://www.fema.gov/about/openfema"),
        ],
        notes=[
            "Declarations reflect federal response requests, not the full "
            "inventory of hazard events.",
        ],
    )


def build_water_block(
    ctx: CbsaContext,
    sdwis: SourceResult | None = None,
    wqp: SourceResult | None = None,
) -> ReportBlock:
    """음용수·수질 — SDWIS drinking water violations + WQP samples."""
    return _pending_block(
        block_id="water",
        title="Drinking Water & Surface Quality",
        body=(
            f"Public water system compliance in {ctx.name} is tracked by "
            "EPA SDWIS (violations and health-based actions). Ambient "
            "surface water quality samples come from the USGS/EPA Water "
            "Quality Portal (WQP). Step 5 scaffolding."
        ),
        sources=[
            (
                "EPA SDWIS",
                "https://www.epa.gov/ground-water-and-drinking-water/safe-drinking-water-information-system-sdwis-federal-reporting",
            ),
            ("Water Quality Portal", "https://www.waterqualitydata.us/"),
        ],
        notes=[
            "WQP samples are discrete observations — date coverage varies "
            "by parameter and station.",
            "SDWIS violation counts do not include every small system on "
            "identical cadence; reporting latency applies.",
        ],
    )


def build_industrial_emissions_block(
    ctx: CbsaContext,
    tri: SourceResult | None = None,
    ghgrp: SourceResult | None = None,
) -> ReportBlock:
    """산업시설·배출 — TRI toxic releases + GHGRP facility GHG."""
    return _pending_block(
        block_id="industrial_emissions",
        title="Industrial & Emissions",
        body=(
            f"Reporting facilities in and around {ctx.name} disclose "
            "toxic chemical releases to the EPA Toxics Release Inventory "
            "(TRI) and greenhouse-gas emissions to the GHGRP programme. "
            "Both inventories lag by roughly one reporting year."
        ),
        sources=[
            ("EPA TRI", "https://www.epa.gov/toxics-release-inventory-tri-program"),
            ("EPA GHGRP", "https://www.epa.gov/ghgreporting"),
        ],
        notes=[
            "TRI covers threshold facilities only — small emitters are "
            "not represented.",
            "GHGRP applies to facilities emitting ≥25,000 metric tons CO₂e.",
        ],
    )


def build_site_cleanup_block(
    ctx: CbsaContext,
    superfund: SourceResult | None = None,
    brownfields: SourceResult | None = None,
    rcra: SourceResult | None = None,
) -> ReportBlock:
    """오염부지·정화 — Superfund NPL + Brownfields ACRES + RCRA TSDF."""
    return _pending_block(
        block_id="site_cleanup",
        title="Contaminated Sites & Cleanup",
        body=(
            f"Federal contaminated-site programmes tracked in "
            f"{ctx.core_county_name or ctx.name} include Superfund NPL "
            "(National Priorities List), the EPA Brownfields ACRES "
            "database, and RCRA hazardous-waste TSDFs."
        ),
        sources=[
            ("Superfund NPL", "https://www.epa.gov/superfund"),
            ("EPA ACRES (Brownfields)", "https://www.epa.gov/cleanups/cleanups-my-community"),
            ("RCRA Info", "https://enviro.epa.gov/facts/rcrainfo/search.html"),
        ],
        notes=[
            "Site status reflects programme listings — active remediation "
            "status and on-site exposure pathways are case-specific.",
        ],
    )


def build_population_exposure_block(
    ctx: CbsaContext,
    ejscreen: SourceResult | None = None,
) -> ReportBlock:
    """인구노출·환경정의 — EJSCREEN + demographic exposure (Step 5 stub)."""
    pop_str = f"{ctx.population:,}" if ctx.population else "unknown"
    metrics: list[ReportMetric] = []
    if ctx.population:
        metrics.append(
            ReportMetric(
                label="CBSA population",
                value=ctx.population,
                unit="people",
                note=f"Census {ctx.population_year or 'recent'} estimate.",
                trustTag="observed",
            )
        )
    # Population-only stub satisfies 'population_exposure' block at Step 5.
    # Full EJSCREEN integration (demographic + environmental indicator
    # percentiles) is deferred to a later step per report-block-policy.md §1.1.
    return ReportBlock(
        id="population_exposure",
        title="Population Exposure & Environmental Justice",
        status="pending",
        trustTag="observed" if ctx.population else "derived",
        body=(
            f"Roughly {pop_str} residents live in the {ctx.name} CBSA. "
            "Full environmental-justice indicators (EJSCREEN percentile "
            "exposure + demographic overlap) are a Step-6 deliverable — "
            "this Step 5 block reports CBSA-level population only."
        ),
        metrics=metrics,
        citations=[
            ReportCitation(label="U.S. Census CBSA estimates", url="https://www.census.gov/programs-surveys/metro-micro.html"),
            ReportCitation(label="EPA EJSCREEN", url="https://www.epa.gov/ejscreen"),
        ],
        error="EJSCREEN indicators not yet wired (Step 6).",
        notes=[
            "CBSA boundaries approximate commuting patterns, not exposure "
            "watersheds. Block-group EJ analysis requires a different "
            "geographic unit.",
        ],
        data=None,
    )


def build_methodology_block(
    ctx: CbsaContext,
    blocks_so_far: list[ReportBlock],
) -> ReportBlock:
    """방법론·데이터신뢰 — summary of sources, trust tags, cadence."""
    tag_counts: dict[TrustTag, int] = {}
    for b in blocks_so_far:
        tag_counts[b.trustTag] = tag_counts.get(b.trustTag, 0) + 1
    trust_summary = ", ".join(
        f"{n} × {tag}" for tag, n in sorted(tag_counts.items())
    )
    metrics = [
        ReportMetric(
            label="Core blocks present",
            value=len(blocks_so_far),
            unit="blocks",
            trustTag="derived",
        ),
        ReportMetric(
            label="Block trust-tag mix",
            value=trust_summary or "n/a",
            trustTag="derived",
        ),
    ]
    return ReportBlock(
        id="methodology",
        title="Methodology & Data Trust",
        status="ok",
        trustTag="derived",
        body=(
            "This report is assembled at build time from multiple federal "
            "environmental data programmes. Each block above carries its "
            "own `trustTag` indicating how direct the underlying signal is "
            "— `observed` (direct measurement), `near-real-time` (satellite "
            "or sensor feeds with hours-to-day latency), `forecast` "
            "(modelled projections), `compliance` (regulatory self-reporting), "
            "and `derived` (composite or estimated quantities). Missing "
            "data is reported explicitly, never filled by imputation."
        ),
        metrics=metrics,
        citations=[
            ReportCitation(
                label="TerraSight data source policy",
                url="docs/architecture/architecture-v2.md#data-source-policy",
            ),
            ReportCitation(
                label="Report block policy",
                url="docs/reports/report-block-policy.md",
            ),
        ],
        notes=[
            "No composite environmental score is computed. Each indicator "
            "is reported on its own axis with its source programme named.",
        ],
        data=None,
    )


# ---------------------------------------------------------------------------
# 5 optional block builders (gated) + their gate evaluators.
# Gates take (ctx, *source_results) → bool. Gate=true means the block
# appears in blocks[]; gate=false means absent + meta.optionalAvailability
# records "absent".
# ---------------------------------------------------------------------------

def gate_pfas_monitoring(
    ctx: CbsaContext, pfas: SourceResult | None = None
) -> bool:
    """Gate: UCMR5 has ≥1 sample for any ZIP in cbsa.zip_prefixes."""
    # Until the PFAS v2 connector lands, gate defaults to False.
    # build_reports passes pfas=None so this is deterministic for Step 5.
    if pfas is None or pfas.status != "ok":
        return False
    payload = pfas.payload or {}
    return int(payload.get("sample_count", 0)) >= 1


def build_pfas_monitoring_block(
    ctx: CbsaContext, pfas: SourceResult | None
) -> ReportBlock:
    return _pending_block(
        block_id="pfas_monitoring",
        title="PFAS Monitoring (UCMR5)",
        body=(
            f"Per-and polyfluoroalkyl substance (PFAS) occurrence sampling "
            f"under EPA's UCMR5 rule applies to public water systems "
            f"serving {ctx.name}. Block appears when ≥1 sample is "
            "recorded for any metro ZIP prefix."
        ),
        sources=[
            (
                "EPA UCMR5",
                "https://www.epa.gov/dwucmr/fifth-unregulated-contaminant-monitoring-rule",
            ),
        ],
        notes=[
            "UCMR5 covers systems serving >10,000 people plus a sample "
            "of smaller systems. Occurrence data do not indicate "
            "exposure.",
        ],
    )


def gate_coastal_conditions(
    ctx: CbsaContext, coops: SourceResult | None = None
) -> bool:
    """Gate: cbsa.coastal === true."""
    return ctx.coastal


def build_coastal_conditions_block(
    ctx: CbsaContext, coops: SourceResult | None
) -> ReportBlock:
    return _pending_block(
        block_id="coastal_conditions",
        title="Coastal Conditions",
        body=(
            f"Tide gauge observations and mean sea-level trends for "
            f"{ctx.name} are drawn from NOAA CO-OPS. Step 5 scaffolding — "
            "CO-OPS v2 connector pending."
        ),
        sources=[
            ("NOAA CO-OPS", "https://tidesandcurrents.noaa.gov/"),
        ],
        notes=[
            "Station coverage is non-uniform — the nearest gauge may be "
            "outside the CBSA boundary.",
        ],
    )


def gate_disaster_history_detailed(
    ctx: CbsaContext, openfema: SourceResult | None = None
) -> bool:
    """Gate: OpenFEMA returned ≥1 declaration in last 10 years."""
    if openfema is None or openfema.status != "ok":
        return False
    payload = openfema.payload or {}
    return int(payload.get("declaration_count", 0)) >= 1


def build_disaster_history_detailed_block(
    ctx: CbsaContext, openfema: SourceResult | None
) -> ReportBlock:
    # Only called when gate_disaster_history_detailed is True, i.e. when
    # openfema returned ≥1 declaration. Keep a stub for contract shape.
    payload = (openfema and openfema.payload) or {}
    count = int(payload.get("declaration_count", 0))
    return ReportBlock(
        id="disaster_history_detailed",
        title="Disaster History",
        status="ok" if openfema and openfema.status == "ok" else "pending",
        trustTag=openfema.trust_tag if openfema else "compliance",
        body=(
            f"Event-level federal disaster declarations for "
            f"{ctx.core_county_name or ctx.name} over the past decade."
        ),
        metrics=[
            ReportMetric(
                label="Declarations (10-year)",
                value=count,
                unit="events",
                trustTag=openfema.trust_tag if openfema else None,
            ),
        ],
        citations=(
            [ReportCitation(label=openfema.source_label, url=openfema.source_url)]
            if openfema and openfema.source_url
            else []
        ),
        error=None,
        notes=[],
        data={"declaration_count": count},
    )


def gate_related_cities(
    ctx: CbsaContext, peer_slugs: list[str] | None = None
) -> bool:
    """Gate: ≥1 other CBSA in same climate_zone or region."""
    return bool(peer_slugs)


def build_related_cities_block(
    ctx: CbsaContext, peer_slugs: list[str] | None
) -> ReportBlock:
    peers = peer_slugs or []
    return ReportBlock(
        id="related_cities",
        title="Related Metros",
        status="ok",
        trustTag="derived",
        body=(
            f"Peer metros for comparison — selected on shared climate "
            f"zone ({ctx.climate_zone or 'unspecified'}) and region."
        ),
        metrics=[],
        citations=[],
        error=None,
        notes=[],
        data={"peer_slugs": peers},
    )


# ---------------------------------------------------------------------------
# Composer orchestrator — called by build_reports.py per CBSA.
# Assembles blocks in canonical order, evaluates optional gates, builds
# the optionalAvailability map, and returns (blocks, availability).
# ---------------------------------------------------------------------------

@dataclass
class ComposerInput:
    """Everything the composer needs from build_reports for one CBSA.

    Sources are optional — None means the upstream connector did not run
    (e.g., v1 source not yet migrated). The composer renders a pending
    block for any None source in core; gates treat None as failure.
    """

    ctx: CbsaContext
    # Core block sources
    airnow: SourceResult | None = None
    echo_facilities: SourceResult | None = None
    normals: SourceResult | None = None
    openfema: SourceResult | None = None
    sdwis: SourceResult | None = None
    wqp: SourceResult | None = None
    tri: SourceResult | None = None
    ghgrp: SourceResult | None = None
    superfund: SourceResult | None = None
    brownfields: SourceResult | None = None
    rcra: SourceResult | None = None
    ejscreen: SourceResult | None = None
    # Optional block sources
    pfas: SourceResult | None = None
    coops: SourceResult | None = None
    # Peer slugs list (for related_cities gate)
    peer_slugs: list[str] | None = None


def compose_city_report_blocks(
    inputs: ComposerInput,
) -> tuple[list[ReportBlock], OptionalAvailabilityMap]:
    """Build the full block list + optionalAvailability map for one CBSA.

    Order in the returned list: 8 core (fixed order) + any included
    optional blocks (insertion order: pfas, coastal, disaster-detail,
    related). City Comparison is never inserted — see §2 of the policy.
    """
    ctx = inputs.ctx
    blocks: list[ReportBlock] = [
        build_air_quality_block(ctx, inputs.airnow, inputs.echo_facilities),
        build_climate_locally_block(ctx, inputs.normals),
        build_hazards_disasters_block(ctx, inputs.openfema),
        build_water_block(ctx, inputs.sdwis, inputs.wqp),
        build_industrial_emissions_block(ctx, inputs.tri, inputs.ghgrp),
        build_site_cleanup_block(
            ctx, inputs.superfund, inputs.brownfields, inputs.rcra
        ),
        build_population_exposure_block(ctx, inputs.ejscreen),
    ]
    # Methodology reads the trust-tag mix of the 7 blocks above, so it
    # is built last.
    blocks.append(build_methodology_block(ctx, blocks.copy()))

    # Gate each optional block; included ⇒ append, absent ⇒ skip.
    availability: dict[OptionalBlockId, OptionalAvailability] = {}

    if gate_pfas_monitoring(ctx, inputs.pfas):
        blocks.append(build_pfas_monitoring_block(ctx, inputs.pfas))
        availability["pfas_monitoring"] = "included"
    else:
        availability["pfas_monitoring"] = "absent"

    if gate_coastal_conditions(ctx, inputs.coops):
        blocks.append(build_coastal_conditions_block(ctx, inputs.coops))
        availability["coastal_conditions"] = "included"
    else:
        availability["coastal_conditions"] = "absent"

    if gate_disaster_history_detailed(ctx, inputs.openfema):
        blocks.append(
            build_disaster_history_detailed_block(ctx, inputs.openfema)
        )
        availability["disaster_history_detailed"] = "included"
    else:
        availability["disaster_history_detailed"] = "absent"

    # City Comparison is always external — never embedded in blocks[].
    availability["city_comparison"] = "external"

    if gate_related_cities(ctx, inputs.peer_slugs):
        blocks.append(build_related_cities_block(ctx, inputs.peer_slugs))
        availability["related_cities"] = "included"
    else:
        availability["related_cities"] = "absent"

    return blocks, OptionalAvailabilityMap(**availability)


__all__ = [
    "CORE_BLOCK_ORDER",
    "combine_trust_tags",
    "CbsaContext",
    "cbsa_from_mapping",
    "SourceResult",
    "ComposerInput",
    "compose_city_report_blocks",
    "build_air_quality_block",
    "build_climate_locally_block",
    "build_hazards_disasters_block",
    "build_water_block",
    "build_industrial_emissions_block",
    "build_site_cleanup_block",
    "build_population_exposure_block",
    "build_methodology_block",
    "build_pfas_monitoring_block",
    "build_coastal_conditions_block",
    "build_disaster_history_detailed_block",
    "build_related_cities_block",
    "gate_pfas_monitoring",
    "gate_coastal_conditions",
    "gate_disaster_history_detailed",
    "gate_related_cities",
]
