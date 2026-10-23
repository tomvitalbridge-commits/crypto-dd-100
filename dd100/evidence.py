"""Evidence pack: the only thing scores are allowed to stand on.

An evidence pack is one or more JSON files with three sections:

    sources  - every document, dataset or conversation used, with a tier:
               1 primary (on-chain data, audit report, signed document)
               2 independent third party (data providers, research, press)
               3 project self-reported (docs, decks, dashboards, interviews)
    metrics  - named numeric/boolean facts, each pointing at a source id
    claims   - things the PROJECT says about itself, tied to a metric name

Packs from different producers (automatic collectors, the Claude skill, a
human analyst) are merged. Later packs may add sources and metrics but may not
silently overwrite an existing metric with a different value — that raises,
because two producers disagreeing is a finding, not a merge conflict to hide.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .models import Claim, Contradiction, EvidencePack, Metric, Source

HARNESS_SOURCE_ID = "HARNESS"


class EvidenceError(ValueError):
    pass


def _parse_pack(raw: dict[str, Any], origin: str) -> EvidencePack:
    sources = {}
    for s in raw.get("sources", []):
        if "id" not in s or "tier" not in s:
            raise EvidenceError(f"{origin}: every source needs 'id' and 'tier'")
        if s["tier"] not in (1, 2, 3):
            raise EvidenceError(f"{origin}: source {s['id']} tier must be 1, 2 or 3")
        sources[s["id"]] = Source(
            id=s["id"], type=s.get("type", "doc"), title=s.get("title", ""), tier=s["tier"],
            url=s.get("url", ""), retrieved=s.get("retrieved", ""), excerpt=s.get("excerpt", ""),
        )
    metrics = {}
    for name, m in raw.get("metrics", {}).items():
        if not isinstance(m, dict) or "value" not in m or "source" not in m:
            raise EvidenceError(f"{origin}: metric '{name}' needs 'value' and 'source'")
        metrics[name] = Metric(name=name, value=m["value"], source=m["source"], note=m.get("note", ""))
    claims = [
        Claim(id=c["id"], statement=c["statement"], metric=c["metric"],
              claimed_value=c["claimed_value"], source=c["source"])
        for c in raw.get("claims", [])
    ]
    return EvidencePack(
        project=raw.get("project", ""), as_of=raw.get("as_of", ""),
        sources=sources, metrics=metrics, claims=claims,
    )


def load_packs(paths: Iterable[Path]) -> EvidencePack:
    merged: EvidencePack | None = None
    for path in paths:
        with open(path, encoding="utf-8") as f:
            pack = _parse_pack(json.load(f), str(path))
        if merged is None:
            merged = pack
            continue
        for sid, src in pack.sources.items():
            if sid in merged.sources and merged.sources[sid].url != src.url:
                raise EvidenceError(f"{path}: source id {sid} reused for a different document")
            merged.sources[sid] = src
        for name, m in pack.metrics.items():
            if name in merged.metrics and merged.metrics[name].value != m.value:
                raise EvidenceError(
                    f"{path}: metric '{name}' = {m.value!r} conflicts with earlier value "
                    f"{merged.metrics[name].value!r}. Resolve the disagreement explicitly."
                )
            merged.metrics[name] = m
        merged.claims.extend(pack.claims)
        merged.as_of = max(merged.as_of, pack.as_of)
    if merged is None:
        raise EvidenceError("No evidence files given")
    _check_references(merged)
    return merged


def _check_references(pack: EvidencePack) -> None:
    for m in pack.metrics.values():
        if m.source not in pack.sources and m.source != HARNESS_SOURCE_ID:
            raise EvidenceError(f"metric '{m.name}' cites unknown source '{m.source}'")
    for c in pack.claims:
        if c.source not in pack.sources:
            raise EvidenceError(f"claim {c.id} cites unknown source '{c.source}'")


def find_contradictions(pack: EvidencePack, tolerance: float) -> list[Contradiction]:
    """Compare what the project claims with what was observed.

    Only observations from a DIFFERENT source of equal or better tier (lower
    number) count — a project's own dashboard cannot contradict itself.
    """
    out = []
    for c in pack.claims:
        m = pack.metrics.get(c.metric)
        if m is None or not isinstance(m.value, (int, float)) or isinstance(m.value, bool):
            continue
        obs_src = pack.sources.get(m.source)
        claim_src = pack.sources[c.source]
        if obs_src is None or m.source == c.source or obs_src.tier > claim_src.tier:
            continue
        base = abs(m.value) if m.value else 1.0
        deviation = abs(c.claimed_value - m.value) / base
        if deviation > tolerance:
            out.append(Contradiction(claim=c, observed=m.value, observed_source=m.source, deviation=deviation))
    return out


def add_derived_metrics(pack: EvidencePack, contradictions: list[Contradiction]) -> None:
    """Metrics the harness computes itself. Never overwrites a supplied metric."""
    def put(name: str, value: Any, note: str) -> None:
        if name not in pack.metrics:
            pack.metrics[name] = Metric(name=name, value=value, source=HARNESS_SOURCE_ID, note=note)

    # Zero contradictions only means something if claims were actually checked.
    # With no claims in the pack the metric stays unset, so T10 is unscored
    # rather than silently awarded full marks.
    checkable = [c for c in pack.claims if c.metric in pack.metrics]
    if checkable:
        put("contradiction_count", len(contradictions),
            f"claims contradicted by independent observation ({len(checkable)} checked)")

    mv = {k: m.value for k, m in pack.metrics.items()}
    mv = {k: v for k, v in mv.items() if v is not None}
    if "fdv_usd" in mv and "market_cap_usd" in mv and mv["market_cap_usd"]:
        put("fdv_to_mcap", round(mv["fdv_usd"] / mv["market_cap_usd"], 2), "fdv_usd / market_cap_usd")
    if "volume_24h_usd" in mv and "depth_2pct_usd" in mv and mv["depth_2pct_usd"]:
        put("volume_to_depth_ratio", round(mv["volume_24h_usd"] / mv["depth_2pct_usd"], 1),
            "volume_24h_usd / depth_2pct_usd")
    if "fdv_usd" in mv and "annualized_fees_usd" in mv and mv["annualized_fees_usd"]:
        put("fdv_to_annual_fees", round(mv["fdv_usd"] / mv["annualized_fees_usd"], 1),
            "fdv_usd / annualized_fees_usd")
    if "circulating_supply" in mv and "total_supply" in mv and mv["total_supply"]:
        put("circulating_supply_pct", round(100 * mv["circulating_supply"] / mv["total_supply"], 1),
            "circulating_supply / total_supply")


def write_pack(pack: EvidencePack, path: Path) -> None:
    data = {
        "project": pack.project,
        "as_of": pack.as_of,
        "sources": [vars(s) for s in pack.sources.values()],
        "metrics": {k: {"value": m.value, "source": m.source, **({"note": m.note} if m.note else {})}
                    for k, m in pack.metrics.items()},
        "claims": [vars(c) for c in pack.claims],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
