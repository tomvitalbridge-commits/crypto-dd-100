"""The pipeline. Deterministic everywhere except one optional node (--llm).

    manifest
      -> load evidence packs (merge, reference checks)
      -> contradiction detection + derived metrics
      -> rule dimensions scored from metrics
      -> judgment dimensions validated (citation + confidence gates)
      -> [optional] LLM fills remaining agent dimensions -> validated the same way
      -> pillar aggregation, coverage, score range
      -> red-flag gates (tri-state)
      -> grade + verdict
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .evaluators import load_assessment_file, score_rule, validate
from .evidence import add_derived_metrics, find_contradictions, load_packs
from .framework import Framework, load_framework
from .gates import evaluate_gates
from .models import Assessment, DimScore, EvidencePack
from .scorer import overall_coverage, pillar_results, point_score, score_range, to_grade, verdict


class ManifestError(ValueError):
    pass


def load_manifest(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        m = yaml.safe_load(f)
    for key in ("project", "profile", "evidence"):
        if key not in m:
            raise ManifestError(f"{path}: manifest needs '{key}'")
    m["_dir"] = path.parent
    return m


def _merge_assessments(fw: Framework, files: list[Path], pack) -> dict[str, DimScore]:
    out: dict[str, DimScore] = {}
    for f in files:
        for raw in load_assessment_file(f):
            ds = validate(raw, fw, pack)
            prev = out.get(ds.dim_id)
            if prev is not None:
                prev_human = prev.assessor.startswith("human")
                this_human = ds.assessor.startswith("human")
                if prev_human == this_human:
                    raise ManifestError(f"{ds.dim_id} assessed twice by the same kind of assessor ({f})")
                if prev_human:      # human always wins over agent
                    prev.notes.append(f"agent assessment in {f.name} ignored (human score present)")
                    continue
                ds.notes.append("overrides agent assessment")
            out[ds.dim_id] = ds
    return out


def run(manifest_path: Path, use_llm: bool = False, fw: Framework | None = None) -> tuple[Assessment, EvidencePack]:
    fw = fw or load_framework()
    m = load_manifest(manifest_path)
    base: Path = m["_dir"]
    profile = fw.profile(m["profile"])

    pack = load_packs([base / p for p in m["evidence"]])
    contradictions = find_contradictions(pack, fw.config["contradiction_tolerance"])
    add_derived_metrics(pack, contradictions)

    na = set(profile.get("not_applicable", []))
    judged = _merge_assessments(fw, [base / p for p in m.get("assessments", [])], pack)

    dims: dict[str, DimScore] = {}
    for did, d in fw.dimensions.items():
        if did in na:
            dims[did] = DimScore(did, status="na", notes=[f"not applicable to profile '{m['profile']}'"])
        elif d.method == "rule":
            dims[did] = score_rule(d, pack)
        elif did in judged:
            dims[did] = judged[did]
        elif d.method == "human":
            dims[did] = DimScore(did, status="pending_human", notes=["requires private channel"])
        else:
            dims[did] = DimScore(did, status="unscored", notes=["no assessment provided"])

    # Analyst notes on specific dimensions (e.g. why a metric could not be established).
    for did, note in (m.get("notes") or {}).items():
        if did not in dims:
            raise ManifestError(f"notes: unknown dimension {did}")
        dims[did].notes.append(str(note))

    if use_llm:
        from .evaluators.llm import run_llm
        todo = [did for did, ds in dims.items()
                if fw.dimensions[did].method == "agent" and ds.status == "unscored"]
        if todo:
            out = base / "assessments" / "llm.generated.yaml"
            for raw in run_llm(fw, pack, todo, out):
                dims[raw["id"]] = validate(raw, fw, pack)

    pillars = pillar_results(fw, dims, profile["pillar_weights"])
    gates = evaluate_gates(fw.gates, pack, dims, pillars)
    pscore = point_score(fw, pillars)
    lo, hi = score_range(fw, dims, pillars)
    cov = overall_coverage(pillars)
    grade, vd, reasons = verdict(fw, to_grade(fw, pscore), cov, gates, dims)

    return Assessment(
        project=m["project"], profile=m["profile"], as_of=pack.as_of or str(m.get("as_of", "")),
        dims=dims, pillars=pillars, gates=gates, contradictions=contradictions,
        point_score=pscore, score_low=lo, score_high=hi, coverage=cov,
        grade=grade, verdict=vd, verdict_reasons=reasons,
    ), pack
