import json
from pathlib import Path

import pytest
import yaml

from dd100.evaluators import band_score, validate
from dd100.evidence import EvidenceError, find_contradictions, load_packs
from dd100.framework import FrameworkError, load_framework
from dd100.gates import evaluate_gates
from dd100.harness import run
from dd100.models import DimScore, EvidencePack, Metric, Source

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"


@pytest.fixture(scope="module")
def fw():
    return load_framework()


def _pack(sources=None, metrics=None, claims=None):
    sources = sources or {"E1": Source("E1", "doc", "doc", 3), "E2": Source("E2", "onchain", "chain", 1),
                          "E3": Source("E3", "api", "api", 2)}
    return EvidencePack("x", "2026-01-01", sources, metrics or {}, claims or [])


# ------------------------------------------------------------------ framework
def test_framework_shape(fw):
    assert len(fw.dimensions) == 100
    for p in fw.pillars:
        assert len(fw.by_pillar(p)) == 10
    for prof in fw.config["profiles"].values():
        assert sum(prof["pillar_weights"].values()) == 100


def test_framework_rejects_99_dimensions(tmp_path):
    raw = yaml.safe_load((ROOT / "framework" / "dimensions.yaml").read_text())
    raw["dimensions"] = raw["dimensions"][:-1]
    bad = tmp_path / "dims.yaml"
    bad.write_text(yaml.safe_dump(raw))
    with pytest.raises(FrameworkError, match="100 dimensions"):
        load_framework(framework_path=bad)


def test_framework_rejects_misordered_bands(tmp_path):
    raw = yaml.safe_load((ROOT / "framework" / "dimensions.yaml").read_text())
    for d in raw["dimensions"]:
        if d["id"] == "K03":
            d["rule"]["bands"] = [60, 40, 25, 15]
    bad = tmp_path / "dims.yaml"
    bad.write_text(yaml.safe_dump(raw))
    with pytest.raises(FrameworkError, match="out of order"):
        load_framework(framework_path=bad)


# ------------------------------------------------------------------ rules
@pytest.mark.parametrize("value,expected", [(100, 4), (60, 3), (59.9, 2), (15, 1), (14, 0)])
def test_band_higher(value, expected):
    assert band_score(value, "higher", [100, 60, 30, 15]) == expected


@pytest.mark.parametrize("value,expected", [(15, 4), (16, 3), (40, 2), (60, 1), (61, 0)])
def test_band_lower(value, expected):
    assert band_score(value, "lower", [15, 25, 40, 60]) == expected


# ------------------------------------------------------------------ verification gates on judgments
def test_uncited_judgment_rejected(fw):
    ds = validate({"id": "T01", "score": 3, "confidence": "medium", "evidence": [], "rationale": "x"}, fw, _pack())
    assert ds.status == "rejected" and "no evidence" in ds.notes[0]


def test_unknown_evidence_rejected(fw):
    ds = validate({"id": "T01", "score": 3, "confidence": "medium", "evidence": ["E9"], "rationale": "x"}, fw, _pack())
    assert ds.status == "rejected" and "E9" in ds.notes[0]


def test_agent_cannot_fill_human_dimension(fw):
    ds = validate({"id": "T02", "score": 4, "confidence": "high", "evidence": ["E2"], "rationale": "x",
                   "assessor": "agent:claude"}, fw, _pack())
    assert ds.status == "rejected"


def test_rule_dimension_cannot_be_opined(fw):
    ds = validate({"id": "K03", "score": 4, "confidence": "high", "evidence": ["E2"], "rationale": "x"}, fw, _pack())
    assert ds.status == "rejected"


def test_high_confidence_downgraded_on_single_self_reported_source(fw):
    ds = validate({"id": "T01", "score": 3, "confidence": "high", "evidence": ["E1"], "rationale": "x"}, fw, _pack())
    assert ds.status == "scored" and ds.confidence == "medium"


def test_high_confidence_kept_with_primary_source(fw):
    ds = validate({"id": "T01", "score": 3, "confidence": "high", "evidence": ["E2"], "rationale": "x"}, fw, _pack())
    assert ds.confidence == "high"


def test_out_of_range_score_rejected(fw):
    ds = validate({"id": "T01", "score": 5, "confidence": "low", "evidence": ["E1"], "rationale": "x"}, fw, _pack())
    assert ds.status == "rejected"


# ------------------------------------------------------------------ evidence
def test_conflicting_metrics_across_packs_raise(tmp_path):
    a = {"sources": [{"id": "S1", "tier": 2}], "metrics": {"tvl_usd": {"value": 1, "source": "S1"}}}
    b = {"sources": [{"id": "S1", "tier": 2}], "metrics": {"tvl_usd": {"value": 2, "source": "S1"}}}
    (tmp_path / "a.json").write_text(json.dumps(a))
    (tmp_path / "b.json").write_text(json.dumps(b))
    with pytest.raises(EvidenceError, match="conflicts"):
        load_packs([tmp_path / "a.json", tmp_path / "b.json"])


def test_project_cannot_contradict_itself():
    from dd100.models import Claim
    pack = _pack(metrics={"tvl_usd": Metric("tvl_usd", 100, "E1")},
                 claims=[Claim("C", "tvl", "tvl_usd", 500, "E1")])
    assert find_contradictions(pack, 0.2) == []


def test_independent_source_contradicts_claim():
    from dd100.models import Claim
    pack = _pack(metrics={"tvl_usd": Metric("tvl_usd", 100, "E2")},
                 claims=[Claim("C", "tvl", "tvl_usd", 500, "E1")])
    assert len(find_contradictions(pack, 0.2)) == 1


# ------------------------------------------------------------------ gates
def test_gate_tristate(fw):
    gates = [{"id": "G", "severity": "critical", "title": "t", "why": "w",
              "when": {"all": [{"metric": "mint_authority", "op": "eq", "value": "eoa"}]}}]
    dims: dict[str, DimScore] = {}
    assert evaluate_gates(gates, _pack(), dims, {})[0].status == "unchecked"
    p = _pack(metrics={"mint_authority": Metric("mint_authority", "eoa", "E2")})
    assert evaluate_gates(gates, p, dims, {})[0].status == "fired"
    p = _pack(metrics={"mint_authority": Metric("mint_authority", "renounced", "E2")})
    assert evaluate_gates(gates, p, dims, {})[0].status == "clear"


# ------------------------------------------------------------------ end to end
def test_halcyon_is_conditional_on_human_check(fw):
    a, _ = run(EX / "halcyon" / "manifest.yaml", fw=fw)
    assert a.verdict == "CONDITIONAL"
    assert a.grade == "B"
    assert a.score_low <= a.point_score <= a.score_high
    assert a.dims["M05"].status == "pending_human"
    assert len(a.contradictions) == 1
    assert not [g for g in a.gates if g.status == "fired" and g.severity != "minor"]


def test_moonvault_rejected_by_critical_gate(fw):
    a, _ = run(EX / "moonvault" / "manifest.yaml", fw=fw)
    assert a.verdict == "REJECT"
    fired = {g.id for g in a.gates if g.status == "fired"}
    assert {"RF01", "RF07", "RF10"} <= fired
    assert a.dims["T02"].status == "rejected"   # agent tried a human-only dimension
    assert a.dims["C04"].status == "rejected"   # cited evidence that does not exist


def test_unscored_dimensions_widen_the_range(fw):
    a, _ = run(EX / "halcyon" / "manifest.yaml", fw=fw)
    b, _ = run(EX / "moonvault" / "manifest.yaml", fw=fw)
    assert (b.score_high - b.score_low) > (a.score_high - a.score_low)


# ------------------------------------------------------------------ template + llm plumbing
def test_blank_template_round_trips(tmp_path, fw):
    import shutil
    from dd100.cli import main
    proj = tmp_path / "p"
    shutil.copytree(EX / "halcyon", proj)
    assert main(["template", str(proj)]) == 0
    m = yaml.safe_load((proj / "manifest.yaml").read_text())
    m["assessments"] = ["assessments/template.yaml"]
    (proj / "manifest.yaml").write_text(yaml.safe_dump(m))
    a, _ = run(proj / "manifest.yaml", fw=fw)
    statuses = {s.status for s in a.dims.values()}
    assert "rejected" not in statuses            # a blank sheet is "pending", never invalid
    assert a.verdict in ("INSUFFICIENT_DATA", "WATCHLIST", "CONDITIONAL")


def test_llm_output_parser_and_fail_loud(fw, monkeypatch, tmp_path):
    from dd100.evaluators.llm import _parse_json_array, run_llm
    assert _parse_json_array('Here you go:\n[{"id": "T01", "score": 3}]')[0]["score"] == 3
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        run_llm(fw, _pack(), ["T01"], tmp_path / "out.yaml")


# ------------------------------------------------------------------ real-project example
def test_hyperliquid_public_review(fw):
    a, _ = run(EX / "hyperliquid" / "manifest.yaml", fw=fw)
    gates = {g.id: g.status for g in a.gates}
    assert a.verdict == "CONDITIONAL" and a.grade == "B"
    assert gates["RF06"] == "unchecked"                    # L1 upgrade notice period not documented
    assert not [g for g, st in gates.items() if st == "fired" and g != "RF16"]
    assert gates["RF02"] == "unchecked"                    # no public sanctions screening
    assert a.dims["K06"].status == "na"                    # no private round, explicit n/a
    assert {d for d, s in a.dims.items() if s.status == "pending_human"} == {"T02", "M05", "L07"}


def test_null_metric_means_not_applicable(fw):
    from dd100.evaluators import score_rule
    pack = _pack(metrics={"price_to_last_round_multiple": Metric("price_to_last_round_multiple", None, "E1", "no round")})
    ds = score_rule(fw.dimensions["K06"], pack)
    assert ds.status == "na" and "no round" in ds.notes[0]
