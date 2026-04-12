"""EPA ECHO (Enforcement and Compliance History Online) connector.

REST services base: https://echodata.epa.gov/echo/
Docs:               https://echo.epa.gov/tools/web-services
Cadence:            live feed
Tag:                observed (enforcement records are observed regulatory facts)
Geo:                facility coordinates → aggregated to CBSA

=============================================================================
⚠️ TWO-HOP PATTERN (updated 2026-04-11)

Old endpoint (ofmpub.epa.gov): BLOCKED on most networks — do not use.
New endpoint (echodata.epa.gov): works via HTTPS.

  Hop 1 – GET /echo/echo_rest_services.get_facilities
    params:  p_c1lon/p_c1lat (SW corner), p_c2lon/p_c2lat (NE corner),
             output=JSON, responseset=100
    returns: QueryID + CAARows / CWARows / RCRRows header counts

  Hop 2 – GET /echo/echo_rest_services.get_qid
    params:  output=JSON, qid=<QueryID>, pageno=1..N
    returns: paginated facilities geographically filtered by the original bbox

Key behavioral differences from old echo13 API:
  • FacLong is ABSENT — only FacLat is returned.
  • CurrVioFlag, Over3yrsFormalActions, Over3yrsEnfAmt are absent.
    Use FacSNCFlg (Y=Significant Non-Compliance) + FacComplianceStatus.
  • QueryRows in both hops reflects GLOBAL (unconstrained) count — do not
    use for Houston-specific totals.  CAARows / CWARows are better proxies.
  • Geographic filtering is applied lazily to paginated QID results.
=============================================================================

MANDATORY disclaimer wherever this data is shown:
  "Regulatory compliance ≠ environmental exposure or health risk."
=============================================================================

Landmine added 2026-04-12:
  - echodata.epa.gov blocks httpx default User-Agent as "robotic query".
    Must send a browser-like UA header or the API returns an Error JSON
    with "robotic or programmed query" and no QueryID.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

# HTTPS works on echodata.epa.gov (unlike the old ofmpub.epa.gov).
BASE_URL = "https://echodata.epa.gov"
FACILITIES_PATH = "/echo/echo_rest_services.get_facilities"
QID_PATH = "/echo/echo_rest_services.get_qid"

# ECHO blocks requests with default httpx User-Agent ("python-httpx/...").
# Must send a descriptive UA to avoid "robotic query" block.
_UA = "TerraSight/1.0 (environmental data portal; contact: terrasight.pages.dev)"

# 100 facilities per page; 5 pages = 500 facility sample per call.
MAX_PAGES = 5


@dataclass
class FacilitySummary:
    name: str
    registry_id: str
    lat: float | None
    in_violation: bool
    compliance_status: str | None


@dataclass
class EchoSummary:
    sampled_facilities: int   # actual records scanned from QID pages
    in_violation: int         # count where FacSNCFlg=Y or compliance="In Violation"
    caa_facilities: int       # approximate CAA-regulated count (first-hop CAARows)
    cwa_facilities: int       # approximate CWA-regulated count (first-hop CWARows)
    top_violations: list[FacilitySummary]


class EchoConnector(BaseConnector):
    name = "echo"
    source = "EPA ECHO"
    source_url = "https://echo.epa.gov/"
    cadence = "live feed"
    tag = "observed"

    async def fetch(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
        max_pages: int = MAX_PAGES,
        **_: Any,
    ) -> dict[str, Any]:
        params = {
            "output": "JSON",
            "p_c1lon": west,
            "p_c1lat": south,
            "p_c2lon": east,
            "p_c2lat": north,
            # p_act=Y limits to active facilities — reduces row count for
            # large metro areas (e.g. LA) that otherwise exceed ECHO's
            # queryset limit and return an Error instead of a QueryID.
            "p_act": "Y",
            "responseset": 100,
        }
        timeout = httpx.Timeout(60.0, connect=15.0)
        headers = {"User-Agent": _UA}
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers=headers,
        ) as client:
            # Hop 1: obtain QueryID and program-level header counts.
            r1 = await client.get(BASE_URL + FACILITIES_PATH, params=params)
            r1.raise_for_status()
            first_hop = r1.json().get("Results", {})
            # ECHO returns {"Error": {"ErrorMessage": "..."}} when the queryset
            # limit is exceeded. Surface that message instead of a generic error.
            if "Error" in first_hop:
                msg = (
                    first_hop["Error"].get("ErrorMessage")
                    or "ECHO queryset error (unknown)"
                )
                raise RuntimeError(f"ECHO API error: {msg}")
            qid = first_hop.get("QueryID")
            if not qid:
                raise RuntimeError(
                    "ECHO returned no QueryID in first hop — API may have changed."
                )
            caa_rows = int(first_hop.get("CAARows") or 0)
            cwa_rows = int(first_hop.get("CWARows") or 0)

            # Hop 2: paginate get_qid to collect geographically-filtered records.
            all_facilities: list[dict[str, Any]] = []
            for pageno in range(1, max_pages + 1):
                r2 = await client.get(
                    BASE_URL + QID_PATH,
                    params={"output": "JSON", "qid": qid, "pageno": pageno},
                )
                r2.raise_for_status()
                page_facilities = r2.json().get("Results", {}).get("Facilities") or []
                if not page_facilities:
                    break
                all_facilities.extend(page_facilities)

        return {
            "caa_rows": caa_rows,
            "cwa_rows": cwa_rows,
            "facilities": all_facilities,
        }

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        facilities_raw = raw.get("facilities") or []
        caa_rows = int(raw.get("caa_rows") or 0)
        cwa_rows = int(raw.get("cwa_rows") or 0)

        summaries: list[FacilitySummary] = []
        in_violation = 0

        for f in facilities_raw:
            snc = str(f.get("FacSNCFlg") or "").upper() == "Y"
            compliance = str(f.get("FacComplianceStatus") or "")
            is_violation = snc or (
                "violation" in compliance.lower()
                and "no violation" not in compliance.lower()
            )
            if is_violation:
                in_violation += 1

            try:
                lat = float(f["FacLat"]) if f.get("FacLat") else None
            except (TypeError, ValueError):
                lat = None

            summaries.append(
                FacilitySummary(
                    name=str(f.get("FacName") or "Unknown facility").strip(),
                    registry_id=str(f.get("RegistryID") or ""),
                    lat=lat,
                    in_violation=is_violation,
                    compliance_status=compliance or None,
                )
            )

        # Sort: in-violation first.
        top = sorted(
            summaries, key=lambda fs: (1 if fs.in_violation else 0), reverse=True
        )[:10]

        return ConnectorResult(
            values=EchoSummary(
                sampled_facilities=len(summaries),
                in_violation=in_violation,
                caa_facilities=caa_rows,
                cwa_facilities=cwa_rows,
                top_violations=top,
            ),
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Facility coordinates within CBSA bounding box",
            license="Public domain (US EPA ECHO)",
            notes=[
                "Regulatory compliance \u2260 environmental exposure or health risk.",
                (
                    f"Violation count based on first {len(summaries)} facilities "
                    "sampled within the bbox (up to 500)."
                ),
                "FacLong absent from echodata.epa.gov API \u2014 facility map "
                "requires lat only; lon is unavailable from this endpoint.",
                "CAARows/CWARows are index-level counts from the ECHO query header.",
            ],
        )
