"""Abstract base class for v2 data-source connectors.

Every connector normalizes data into a `ConnectorResult` with the trust tag
drawn from the v2 5-value vocabulary (`observed` / `near-real-time` /
`forecast` / `derived` / `compliance`) — NOTE: v1 `estimated` is retired.

Contract sync: this file is paired with `packages/schemas/src/index.ts`
(zod). Changing the TrustTag literal here REQUIRES updating that zod
schema at the same time, and vice-versa. The mirror lives in
`pipelines/contracts/` for runtime validation inside Python code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

TrustTag = Literal["observed", "near-real-time", "forecast", "derived", "compliance"]

BlockStatus = Literal["ok", "error", "not_configured", "pending"]


@dataclass
class ConnectorResult:
    """Normalized output of a connector run.

    `values` is deliberately `Any` — each connector returns either a list
    of dataclasses (events, points) or a dict (single point). Contract
    tests in `pipelines/tests/` lock the concrete shape per connector.
    """

    values: Any
    source: str
    source_url: str
    cadence: str
    tag: TrustTag
    spatial_scope: str
    license: str
    status: BlockStatus = "ok"
    notes: list[str] = field(default_factory=list)


class BaseConnector(ABC):
    """Base connector: fetch → normalize. Cache is Worker's job, not Python's."""

    name: str
    source: str
    source_url: str
    cadence: str
    tag: TrustTag

    @abstractmethod
    async def fetch(self, **params: Any) -> Any:
        """Call the external API. Raise on transport failure."""

    @abstractmethod
    def normalize(self, raw: Any) -> ConnectorResult:
        """Transform raw payload into a ConnectorResult."""

    async def run(self, **params: Any) -> ConnectorResult:
        raw = await self.fetch(**params)
        return self.normalize(raw)
