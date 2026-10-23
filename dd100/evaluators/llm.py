"""Optional LLM evaluator for `method: agent` dimensions.

The model is invoked at ONE localized node: given a pillar's rubric and the
evidence pack, return structured scores. It never sees the overall score, the
gates or the verdict, and its output goes through exactly the same validator
as a human analyst's (assessments.validate). Output is written to a YAML file
so an analyst can review, edit or delete any line before it counts.

Requires `pip install anthropic` and ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from ..framework import Framework
from ..models import EvidencePack

SYSTEM = """You are a crypto due-diligence analyst on an exchange listing committee.
Score each dimension 0-4 against its anchors (1 and 3 sit between anchors).

Hard rules:
- Use ONLY the evidence provided. Cite source ids for every score.
- If the evidence does not support a score, return status "pending" with a note
  on what evidence is missing. A missing score is better than an invented one.
- confidence: high = multiple independent or primary sources agree;
  medium = one decent source; low = indirect or inferred.
- Write rationales as one or two factual sentences. No hype words.
Return ONLY a JSON array, no prose."""


def _evidence_digest(pack: EvidencePack) -> str:
    lines = ["SOURCES (id | tier | type | title | excerpt):"]
    for s in pack.sources.values():
        excerpt = (s.excerpt or "")[:600].replace("\n", " ")
        lines.append(f"{s.id} | T{s.tier} | {s.type} | {s.title} | {excerpt}")
    lines.append("\nMETRICS (name = value [source]):")
    for m in pack.metrics.values():
        lines.append(f"{m.name} = {m.value} [{m.source}]")
    return "\n".join(lines)


def _pillar_prompt(fw: Framework, pillar: str, dim_ids: list[str]) -> str:
    blocks = [f"PILLAR {pillar}: {fw.pillars[pillar]}\n"]
    for did in dim_ids:
        d = fw.dimensions[did]
        anchors = "; ".join(f"{k}={v}" for k, v in sorted(d.anchors.items()))
        blocks.append(f"- {d.id} {d.name}: {d.question}\n  anchors: {anchors}")
    blocks.append(
        '\nReturn: [{"id": "...", "score": 0-4, "confidence": "high|medium|low", '
        '"evidence": ["E01"], "rationale": "..."} or {"id": "...", "status": "pending", '
        '"rationale": "missing: ..."}]'
    )
    return "\n".join(blocks)


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        raise ValueError("model did not return a JSON array")
    return json.loads(match.group(0))


def run_llm(fw: Framework, pack: EvidencePack, todo: list[str], out_path: Path) -> list[dict[str, Any]]:
    try:
        import anthropic
    except ImportError as e:  # fail loud
        raise RuntimeError("`--llm` needs the anthropic package: pip install anthropic") from e
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("`--llm` needs ANTHROPIC_API_KEY in the environment")

    client = anthropic.Anthropic()
    digest = _evidence_digest(pack)
    results: list[dict[str, Any]] = []
    by_pillar: dict[str, list[str]] = {}
    for did in todo:
        by_pillar.setdefault(did[0], []).append(did)

    for pillar, ids in by_pillar.items():
        msg = client.messages.create(
            model=fw.config["llm"]["model"],
            max_tokens=fw.config["llm"]["max_tokens"],
            system=SYSTEM,
            messages=[{"role": "user", "content": f"{digest}\n\n{_pillar_prompt(fw, pillar, ids)}"}],
        )
        text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
        for item in _parse_json_array(text):
            if item.get("id") in ids:
                item["assessor"] = f"agent:{fw.config['llm']['model']}"
                results.append(item)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "# Machine-generated. Review before relying on it — edit or delete any line.\n"
        + yaml.safe_dump({"assessments": results}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return results
