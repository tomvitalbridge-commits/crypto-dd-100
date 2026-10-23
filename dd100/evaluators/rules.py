"""Deterministic scoring for `method: rule` dimensions.

Thresholds come from framework/dimensions.yaml. This module contains no
numbers of its own — change the framework, not the code.
"""
from __future__ import annotations

from typing import Any

from ..models import Dimension, DimScore, EvidencePack


def band_score(value: float, direction: str, bands: list[float]) -> int:
    t4, t3, t2, t1 = bands
    if direction == "higher":
        for score, t in ((4, t4), (3, t3), (2, t2), (1, t1)):
            if value >= t:
                return score
        return 0
    if direction == "lower":
        for score, t in ((4, t4), (3, t3), (2, t2), (1, t1)):
            if value <= t:
                return score
        return 0
    raise ValueError(f"unknown direction {direction}")


def score_rule(dim: Dimension, pack: EvidencePack) -> DimScore:
    rule: dict[str, Any] = dim.rule or {}
    metric = pack.metrics.get(rule["metric"])
    if metric is None:
        return DimScore(dim.id, status="unscored",
                        notes=[f"metric '{rule['metric']}' not in evidence pack"])

    value = metric.value
    if value is None:
        # Explicit "does not apply to this project", with the reason in the note.
        # Different from a missing metric, which means "not yet established".
        return DimScore(dim.id, status="na", evidence=[metric.source],
                        notes=[f"n/a for this project: {metric.note or 'no reason given'}"])
    if rule["direction"] == "bool":
        if not isinstance(value, bool):
            return DimScore(dim.id, status="rejected",
                            notes=[f"metric '{rule['metric']}' must be true/false, got {value!r}"])
        score = 4 if value == rule["pass"] else 0
        shown = str(value).lower()
    else:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return DimScore(dim.id, status="rejected",
                            notes=[f"metric '{rule['metric']}' must be numeric, got {value!r}"])
        score = band_score(float(value), rule["direction"], rule["bands"])
        shown = f"{value:,}" if isinstance(value, int) else f"{value:,.2f}".rstrip("0").rstrip(".")
        sym = "≥" if rule["direction"] == "higher" else "≤"
        bands = ", ".join(f"{s}:{sym}{t:,g}" for s, t in zip((4, 3, 2, 1), rule["bands"]))
        shown = f"{shown}  (bands {bands})"

    src = pack.sources.get(metric.source)
    confidence = "high" if (src is None or src.tier == 1) else "medium" if src.tier == 2 else "low"
    # src is None only for HARNESS-derived metrics, which are computed, hence high.
    return DimScore(
        dim.id, status="scored", score=score, confidence=confidence,
        evidence=[metric.source], assessor="rule",
        rationale=f"{rule['metric']} = {shown}",
    )
