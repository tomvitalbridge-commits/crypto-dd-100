"""Red-flag gate evaluation. Tri-state: fired / clear / unchecked.

A condition whose input is missing is UNKNOWN, not False. A gate is:
  clear      if any condition is definitely False
  unchecked  if no condition is False but at least one is unknown
  fired      if every condition is True
  n/a        if the gate only concerns dimensions the profile marks N/A
"""
from __future__ import annotations

import operator
from typing import Any, Optional

from .models import DimScore, EvidencePack, GateResult, PillarResult

OPS = {
    "eq": operator.eq, "ne": operator.ne, "gt": operator.gt,
    "gte": operator.ge, "lt": operator.lt, "lte": operator.le,
}


def _condition(cond: dict[str, Any], pack: EvidencePack, dims: dict[str, DimScore],
               pillars: dict[str, PillarResult]) -> Optional[bool]:
    op = OPS[cond["op"]]
    if "metric" in cond:
        m = pack.metrics.get(cond["metric"])
        if m is None or m.value is None:
            return None
        if isinstance(cond["value"], bool) != isinstance(m.value, bool):
            return None
        return bool(op(m.value, cond["value"]))
    if "dim" in cond:
        d = dims.get(cond["dim"])
        if d is None or d.status != "scored":
            return None
        return bool(op(d.score, cond["value"]))
    if "pillar" in cond:
        p = pillars.get(cond["pillar"])
        if p is None or p.score is None:
            return None
        return bool(op(p.score, cond["value"]))
    raise ValueError(f"condition needs metric, dim or pillar: {cond}")


def evaluate_gates(gates: list[dict[str, Any]], pack: EvidencePack, dims: dict[str, DimScore],
                   pillars: dict[str, PillarResult]) -> list[GateResult]:
    results = []
    for g in gates:
        skip = g.get("skip_if_na") or []
        if skip and all(dims.get(d) is not None and dims[d].status == "na" for d in skip):
            results.append(GateResult(g["id"], g["severity"], g["title"], g["why"], "n/a"))
            continue
        values = [_condition(c, pack, dims, pillars) for c in g["when"]["all"]]
        if any(v is False for v in values):
            status = "clear"
        elif any(v is None for v in values):
            status = "unchecked"
        else:
            status = "fired"
        results.append(GateResult(g["id"], g["severity"], g["title"], g["why"], status))
    return results
