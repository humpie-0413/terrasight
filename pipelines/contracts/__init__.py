"""Python pydantic mirrors of `packages/schemas/src/index.ts` (zod).

Keep this file 1:1 with the zod schema — same field names, same enum values,
same optional/required flags. Drift here is the #1 source of
Worker-vs-Pipeline contract bugs.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TrustTag = Literal["observed", "near-real-time", "forecast", "derived", "compliance"]
BlockStatus = Literal["ok", "error", "not_configured", "pending"]
LayerCategory = Literal["imagery", "event"]
LayerKind = Literal["continuous", "event"]
Coverage = Literal["global", "ocean-only", "land-only", "coastal"]
Cadence = Literal["daily", "monthly", "3h", "5min", "static"]


class LayerLegend(BaseModel):
    unit: str
    min: float
    max: float
    colormap: str


class LayerImagery(BaseModel):
    type: Literal["wmts"]
    urlTemplate: str
    tileMatrixSet: str
    availableDates: str


class LayerEventApi(BaseModel):
    path: str
    ttlSeconds: int


class LayerManifest(BaseModel):
    id: str
    title: str
    category: LayerCategory
    kind: LayerKind
    source: str
    trustTag: TrustTag
    coverage: Coverage
    cadence: Cadence
    enabled: bool
    legend: LayerLegend | None = None
    imagery: LayerImagery | None = None
    eventApi: LayerEventApi | None = None
    caveats: list[str] = Field(default_factory=list)


class EventPoint(BaseModel):
    id: str
    type: Literal["wildfire", "earthquake", "alert"]
    lat: float
    lon: float
    observedAt: str
    severity: float | str | None = None
    label: str
    properties: dict[str, object] = Field(default_factory=dict)


SSTStatus = Literal["ok", "no_data", "error"]


class SSTPoint(BaseModel):
    """Single-point SST result (ERDDAP OISST).

    Uses the SST-specific `SSTStatus` enum — `no_data` is the graceful
    response when the user clicked a land or ice cell, which is common
    and must not read as an error in the UI.
    """

    status: SSTStatus
    source: str
    source_url: str | None = None
    cadence: Cadence | None = None
    tag: TrustTag | None = None
    lat: float | None = None
    lon: float | None = None
    snappedLat: float | None = None
    snappedLon: float | None = None
    sst_c: float | None = None
    observed_at: str | None = None
    message: str | None = None


class NormalizedResponse(BaseModel):
    """Envelope that Worker routes return. Matches
    `docs/datasets/normalized-contracts.md` §2."""

    status: BlockStatus
    source: str
    source_url: str
    cadence: str
    tag: TrustTag
    count: int
    data: list[EventPoint] | list[LayerManifest] | list[dict]
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Report schema (v2, Step 5)
# Mirrors packages/schemas/src/index.ts. Block inclusion rules are locked
# in docs/reports/report-block-policy.md.
# ---------------------------------------------------------------------------

CoreBlockId = Literal[
    "air_quality",
    "climate_locally",
    "hazards_disasters",
    "water",
    "industrial_emissions",
    "site_cleanup",
    "population_exposure",
    "methodology",
]

OptionalBlockId = Literal[
    "pfas_monitoring",
    "coastal_conditions",
    "disaster_history_detailed",
    "city_comparison",
    "related_cities",
]

BlockId = Literal[
    "air_quality",
    "climate_locally",
    "hazards_disasters",
    "water",
    "industrial_emissions",
    "site_cleanup",
    "population_exposure",
    "methodology",
    "pfas_monitoring",
    "coastal_conditions",
    "disaster_history_detailed",
    "city_comparison",
    "related_cities",
]

OptionalAvailability = Literal["included", "absent", "external"]


class ReportMetric(BaseModel):
    label: str
    value: str | float | int | None
    unit: str | None = None
    note: str | None = None
    trustTag: TrustTag | None = None


class ReportCitation(BaseModel):
    label: str
    url: str


class ReportBlock(BaseModel):
    id: BlockId
    title: str
    status: BlockStatus
    trustTag: TrustTag
    body: str
    metrics: list[ReportMetric] = Field(default_factory=list)
    citations: list[ReportCitation] = Field(default_factory=list)
    error: str | None = None
    notes: list[str] = Field(default_factory=list)
    data: dict[str, object] | None = None


class OptionalAvailabilityMap(BaseModel):
    pfas_monitoring: OptionalAvailability
    coastal_conditions: OptionalAvailability
    disaster_history_detailed: OptionalAvailability
    city_comparison: OptionalAvailability
    related_cities: OptionalAvailability


class CityReportBuildMeta(BaseModel):
    pipelineVersion: str
    generatedAt: str


class CityReportMeta(BaseModel):
    updatedAt: str
    build: CityReportBuildMeta
    optionalAvailability: OptionalAvailabilityMap


class CityReportSummary(BaseModel):
    headline: str
    bullets: list[str] = Field(default_factory=list)


class CityReport(BaseModel):
    slug: str
    cbsaCode: str
    city: str
    region: str
    country: Literal["US"]
    coastal: bool
    lat: float
    lon: float
    population: int | None = None
    populationYear: str | None = None
    climateZone: str | None = None
    summary: CityReportSummary
    blocks: list[ReportBlock]
    meta: CityReportMeta


CityReportIndexStatus = Literal["ok", "partial", "error"]


class CityReportIndexEntry(BaseModel):
    slug: str
    cbsaCode: str
    city: str
    region: str
    updatedAt: str
    status: CityReportIndexStatus
    coreBlocksOk: int
    coreBlocksTotal: Literal[8]


class CityReportIndex(BaseModel):
    generatedAt: str
    pipelineVersion: str
    reports: list[CityReportIndexEntry]


RankingMetric = Literal[
    "air_quality_pm25",
    "emissions_ghg_total",
    "water_violations_count",
    "disaster_declarations_10y",
]


class RankingRow(BaseModel):
    slug: str
    city: str
    region: str
    value: float | int | None
    unit: str
    rank: int | None
    trustTag: TrustTag


class Ranking(BaseModel):
    metric: RankingMetric
    title: str
    direction: Literal["asc", "desc"]
    unit: str
    generatedAt: str
    pipelineVersion: str
    n: int
    rows: list[RankingRow]


class RankingsIndexEntry(BaseModel):
    metric: RankingMetric
    title: str
    file: str
    nCbsa: int
    generatedAt: str


class RankingsIndex(BaseModel):
    generatedAt: str
    pipelineVersion: str
    files: list[RankingsIndexEntry]


__all__ = [
    "TrustTag",
    "BlockStatus",
    "SSTStatus",
    "LayerManifest",
    "LayerLegend",
    "LayerImagery",
    "LayerEventApi",
    "EventPoint",
    "SSTPoint",
    "NormalizedResponse",
    # Report schema
    "CoreBlockId",
    "OptionalBlockId",
    "BlockId",
    "OptionalAvailability",
    "ReportMetric",
    "ReportCitation",
    "ReportBlock",
    "OptionalAvailabilityMap",
    "CityReportBuildMeta",
    "CityReportMeta",
    "CityReportSummary",
    "CityReport",
    "CityReportIndexStatus",
    "CityReportIndexEntry",
    "CityReportIndex",
    "RankingMetric",
    "RankingRow",
    "Ranking",
    "RankingsIndexEntry",
    "RankingsIndex",
]
