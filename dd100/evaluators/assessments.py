"""Validate judgment scores (agent or human) before they are allowed to count.

This is the verification layer between the Skill (judgment) and the scorer
(arithmetic). An assessment is REJECTED — not repaired — when it:

  * scores a rule dimension (rules are computed, not opined)
  * comes from an agent for a human-only dimension
  * has a score outside 0..4 or an unknown confidence level
  * cites no evidence, or cites evidence ids that are not in the pack
  * has an empty rationale

High confidence is DOWNGRADED to medium when the cited evidence is thin
(see config.high_confidence_requires). Downgrades are reported, not hidden.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..models import CONFIDENCE_LEVELS, DimScore, EvidencePack
from ..framework import Framework


def load_assessment_file(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("assessments", [])


def validate(raw: dict[str, Any], fw: Framework, pack: EvidencePack) -> DimScore:
    did = raw.get("id", "?")
    dim = fw.dimensions.get(did)
    if dim is None:
        return DimScore(did, status="rejected", notes=["unknown dimension id"])

    assessor = str(raw.get("assessor", "agent"))
    is_human = assessor.startswith("human")

    def reject(msg: str) -> DimScore:
        return DimScore(did, status="rejected", assessor=assessor, notes=[msg])

    if dim.method == "rule":
        return reject("rule dimensions are computed from metrics; supply the metric instead")
    if dim.method == "human" and not is_human:
        return reject("human-only dimension cannot be scored by an agent")

    score = raw.get("score")
    if raw.get("status") == "pending":
        return DimScore(did, status="pending_human" if dim.method == "human" else "unscored",
                        assessor=assessor, notes=[raw.get("rationale", "awaiting input")])
    if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= fw.config["scale_max"]:
        return reject(f"score must be an integer 0..{fw.config['scale_max']}, got {score!r}")

    confidence = raw.get("confidence")
    if confidence not in CONFIDENCE_LEVELS:
        return reject(f"confidence must be one of {CONFIDENCE_LEVELS}")

    rationale = str(raw.get("rationale", "")).strip()
    if not rationale:
        return reject("rationale is required")

    cited = list(raw.get("evidence") or [])
    if not cited:
        return reject("no evidence cited — uncited judgments are not scored")
    missing = [e for e in cited if e not in pack.sources]
    if missing:
        return reject(f"cites evidence not in the pack: {', '.join(missing)}")

    notes = []
    req = fw.config["high_confidence_requires"]
    if confidence == "high":
        tier1 = sum(1 for e in cited if pack.sources[e].tier == 1)
        if len(set(cited)) < req["min_sources"] and tier1 < req["or_min_tier1_sources"]:
            confidence = "medium"
            notes.append("confidence downgraded high→medium: single non-primary source")

    return DimScore(did, status="scored", score=score, confidence=confidence, evidence=cited,
                    rationale=rationale, assessor=assessor, notes=notes)
