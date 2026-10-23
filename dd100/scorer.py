"""Aggregation: dimension scores -> pillar scores -> overall score, range, grade, verdict.

Design choices, deliberately conservative:

* Unscored dimensions are NOT imputed. The point score uses only what was
  scored; the RANGE shows what the unknowns could do (unscored = 0 at the low
  end, 4 at the high end, plus each score's confidence radius).
* Coverage is reported everywhere. A high score on 40% coverage is a
  different statement from the same score on 95% coverage.
* Gates override arithmetic. See framework/red_flags.yaml.
"""
from __future__ import annotations

from typing import Any, Optional

from .framework import Framework
from .models import DimScore, GateResult, PillarResult

GRADE_ORDER = ["A", "B", "C", "D", "F"]


def pillar_results(fw: Framework, dims: dict[str, DimScore], weights: dict[str, float]) -> dict[str, PillarResult]:
    out = {}
    pillar_min = fw.config["coverage"]["pillar_min"]
    for p, name in fw.pillars.items():
        applicable = [d for d in fw.by_pillar(p) if dims[d.id].status != "na"]
        scored = [d for d in applicable if dims[d.id].status == "scored"]
        w_app = sum(d.weight for d in applicable)
        w_sc = sum(d.weight for d in scored)
        score = (sum(d.weight * dims[d.id].score for d in scored) / w_sc) if w_sc else None
        coverage = (w_sc / w_app) if w_app else 0.0
        out[p] = PillarResult(p, name, weights[p], score, coverage, coverage >= pillar_min,
                              len(scored), len(applicable))
    return out


def score_range(fw: Framework, dims: dict[str, DimScore], pillars: dict[str, PillarResult]) -> tuple[float, float]:
    radius = fw.config["confidence_radius"]
    smax = fw.config["scale_max"]
    lo_total = hi_total = 0.0
    for p, pr in pillars.items():
        applicable = [d for d in fw.by_pillar(p) if dims[d.id].status != "na"]
        w_app = sum(d.weight for d in applicable)
        if not w_app:
            continue
        lo = hi = 0.0
        for d in applicable:
            ds = dims[d.id]
            if ds.status == "scored":
                r = radius[ds.confidence]
                lo += d.weight * max(0.0, ds.score - r)
                hi += d.weight * min(smax, ds.score + r)
            else:
                hi += d.weight * smax
        lo_total += pr.weight * lo / w_app
        hi_total += pr.weight * hi / w_app
    # pillar weights sum to 100 and pillar averages are on 0..smax, so dividing
    # by smax lands the result on 0..100.
    return round(lo_total / smax, 1), round(hi_total / smax, 1)


def point_score(fw: Framework, pillars: dict[str, PillarResult]) -> Optional[float]:
    have = [pr for pr in pillars.values() if pr.score is not None]
    if not have:
        return None
    w = sum(pr.weight for pr in have)
    return round(100 * sum(pr.weight * pr.score for pr in have) / w / fw.config["scale_max"], 1)


def overall_coverage(pillars: dict[str, PillarResult]) -> float:
    return round(sum(pr.weight * pr.coverage for pr in pillars.values()) / 100, 3)


def to_grade(fw: Framework, score: Optional[float]) -> str:
    if score is None:
        return "—"
    for g in GRADE_ORDER:
        if score >= fw.config["grades"][g]:
            return g
    return "F"


def _cap(grade: str, cap: str) -> str:
    if grade == "—":
        return grade
    return grade if GRADE_ORDER.index(grade) >= GRADE_ORDER.index(cap) else cap


def verdict(fw: Framework, grade: str, coverage: float, gates: list[GateResult],
            dims: dict[str, DimScore]) -> tuple[str, str, list[str]]:
    """Returns (final_grade, verdict, reasons)."""
    cfg: dict[str, Any] = fw.config
    reasons: list[str] = []
    fired = [g for g in gates if g.status == "fired"]
    critical = [g for g in fired if g.severity == "critical"]
    major = [g for g in fired if g.severity == "major"]
    crit_unchecked = [g for g in gates if g.status == "unchecked" and g.severity == "critical"]
    pending_human = [f"{d} {fw.dimensions[d].name}" for d, s in dims.items() if s.status == "pending_human"]

    if critical:
        reasons += [f"critical gate {g.id}: {g.title}" for g in critical]
        return grade, "REJECT", reasons

    if coverage < cfg["coverage"]["overall_min_for_verdict"]:
        reasons.append(f"evidence coverage {coverage:.0%} below the "
                       f"{cfg['coverage']['overall_min_for_verdict']:.0%} needed for a verdict")
        return grade, "INSUFFICIENT_DATA", reasons

    if major:
        grade = _cap(grade, "C")
        reasons += [f"major gate {g.id}: {g.title} (grade capped at C)" for g in major]

    order = GRADE_ORDER
    list_ok = grade != "—" and order.index(grade) <= order.index(cfg["verdicts"]["list_min_grade"])
    watch_ok = grade != "—" and order.index(grade) <= order.index(cfg["verdicts"]["watchlist_min_grade"])

    if not watch_ok:
        reasons.append(f"grade {grade} below watchlist threshold")
        return grade, "REJECT", reasons

    blockers = []
    if major:
        blockers.append("major gates need committee sign-off")
    if crit_unchecked:
        blockers.append("critical gates not yet checkable: " + ", ".join(g.id for g in crit_unchecked))
    if pending_human:
        blockers.append("human-only checks outstanding: " + ", ".join(pending_human))

    if list_ok and not blockers:
        reasons.append(f"grade {grade}, no major or critical gates, all critical gates verified")
        return grade, "LIST", reasons
    if list_ok:
        reasons.append(f"grade {grade} meets the listing bar on score; listing is blocked until:")
        reasons += blockers
        return grade, "CONDITIONAL", reasons
    reasons.append(f"grade {grade}: monitor for improvement")
    reasons += blockers
    return grade, "WATCHLIST", reasons
