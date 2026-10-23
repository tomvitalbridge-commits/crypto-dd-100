"""Plain data structures shared across the harness. No logic lives here."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

CONFIDENCE_LEVELS = ("high", "medium", "low")
METHODS = ("rule", "agent", "human")
SEVERITIES = ("critical", "major", "minor")


@dataclass(frozen=True)
class Dimension:
    id: str
    pillar: str
    name: str
    question: str
    method: str
    weight: int
    evidence: tuple[str, ...]
    anchors: dict[int, str] = field(default_factory=dict)
    rule: Optional[dict[str, Any]] = None


@dataclass
class Source:
    id: str
    type: str
    title: str
    tier: int                      # 1 = primary (on-chain, audit, signed doc), 2 = independent third party, 3 = project self-reported
    url: str = ""
    retrieved: str = ""
    excerpt: str = ""


@dataclass
class Metric:
    name: str
    value: Any
    source: str                    # Source.id
    note: str = ""


@dataclass
class Claim:
    id: str
    statement: str
    metric: str
    claimed_value: float
    source: str


@dataclass
class Contradiction:
    claim: Claim
    observed: Any
    observed_source: str
    deviation: float


@dataclass
class EvidencePack:
    project: str
    as_of: str
    sources: dict[str, Source]
    metrics: dict[str, Metric]
    claims: list[Claim]


@dataclass
class DimScore:
    dim_id: str
    status: str                    # scored | unscored | na | rejected | pending_human
    score: Optional[int] = None
    confidence: Optional[str] = None
    evidence: list[str] = field(default_factory=list)
    rationale: str = ""
    assessor: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class GateResult:
    id: str
    severity: str
    title: str
    why: str
    status: str                    # fired | clear | unchecked | n/a


@dataclass
class PillarResult:
    pillar: str
    name: str
    weight: float
    score: Optional[float]         # 0..4, None if no scored dims
    coverage: float                # 0..1 share of applicable weight scored
    sufficient: bool
    scored: int
    applicable: int


@dataclass
class Assessment:
    project: str
    profile: str
    as_of: str
    dims: dict[str, DimScore]
    pillars: dict[str, PillarResult]
    gates: list[GateResult]
    contradictions: list[Contradiction]
    point_score: Optional[float]   # 0..100
    score_low: float
    score_high: float
    coverage: float
    grade: str
    verdict: str
    verdict_reasons: list[str]
