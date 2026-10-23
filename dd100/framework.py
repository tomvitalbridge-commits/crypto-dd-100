"""Load and validate the framework, red flags and scoring config.

Fail-loud by design: a malformed framework raises FrameworkError rather than
being silently patched. The framework is the contract; if it is wrong, no
score produced from it should be trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import METHODS, SEVERITIES, Dimension

ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK_PATH = ROOT / "framework" / "dimensions.yaml"
RED_FLAGS_PATH = ROOT / "framework" / "red_flags.yaml"
CONFIG_PATH = ROOT / "config" / "scoring.yaml"

EXPECTED_DIMENSIONS = 100
EXPECTED_PER_PILLAR = 10


class FrameworkError(ValueError):
    pass


@dataclass
class Framework:
    pillars: dict[str, str]
    dimensions: dict[str, Dimension]
    gates: list[dict[str, Any]]
    config: dict[str, Any]

    def by_pillar(self, pillar: str) -> list[Dimension]:
        return [d for d in self.dimensions.values() if d.pillar == pillar]

    def profile(self, name: str) -> dict[str, Any]:
        profiles = self.config["profiles"]
        if name not in profiles:
            raise FrameworkError(f"Unknown profile '{name}'. Choose one of: {', '.join(profiles)}")
        return profiles[name]


def _load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_dimension(raw: dict[str, Any], pillars: dict[str, str]) -> Dimension:
    did = raw.get("id", "?")
    for key in ("id", "name", "question", "method", "weight"):
        if key not in raw:
            raise FrameworkError(f"{did}: missing '{key}'")
    pillar = did[0]
    if pillar not in pillars:
        raise FrameworkError(f"{did}: id prefix '{pillar}' is not a known pillar")
    if raw["method"] not in METHODS:
        raise FrameworkError(f"{did}: method must be one of {METHODS}")
    if raw["weight"] not in (1, 2, 3):
        raise FrameworkError(f"{did}: weight must be 1, 2 or 3")

    rule = raw.get("rule")
    anchors = {int(k): v for k, v in (raw.get("anchors") or {}).items()}
    if raw["method"] == "rule":
        if not rule or "metric" not in rule or "direction" not in rule:
            raise FrameworkError(f"{did}: rule dimensions need rule.metric and rule.direction")
        if rule["direction"] in ("higher", "lower"):
            bands = rule.get("bands")
            if not bands or len(bands) != 4:
                raise FrameworkError(f"{did}: rule.bands must have exactly 4 thresholds [t4, t3, t2, t1]")
            ordered = sorted(bands, reverse=rule["direction"] == "higher")
            if list(bands) != ordered:
                raise FrameworkError(f"{did}: bands out of order for direction '{rule['direction']}'")
        elif rule["direction"] == "bool":
            if "pass" not in rule:
                raise FrameworkError(f"{did}: bool rules need rule.pass")
        else:
            raise FrameworkError(f"{did}: unknown rule direction '{rule['direction']}'")
    else:
        if not {0, 2, 4} <= set(anchors):
            raise FrameworkError(f"{did}: agent/human dimensions need anchors for 0, 2 and 4")

    return Dimension(
        id=did,
        pillar=pillar,
        name=raw["name"],
        question=raw["question"],
        method=raw["method"],
        weight=raw["weight"],
        evidence=tuple(raw.get("evidence", [])),
        anchors=anchors,
        rule=rule,
    )


def load_framework(
    framework_path: Path = FRAMEWORK_PATH,
    red_flags_path: Path = RED_FLAGS_PATH,
    config_path: Path = CONFIG_PATH,
) -> Framework:
    raw = _load_yaml(framework_path)
    pillars = raw["pillars"]
    dims: dict[str, Dimension] = {}
    for item in raw["dimensions"]:
        d = _parse_dimension(item, pillars)
        if d.id in dims:
            raise FrameworkError(f"Duplicate dimension id {d.id}")
        dims[d.id] = d

    if len(dims) != EXPECTED_DIMENSIONS:
        raise FrameworkError(f"Framework must have {EXPECTED_DIMENSIONS} dimensions, found {len(dims)}")
    for p in pillars:
        n = sum(1 for d in dims.values() if d.pillar == p)
        if n != EXPECTED_PER_PILLAR:
            raise FrameworkError(f"Pillar {p} must have {EXPECTED_PER_PILLAR} dimensions, found {n}")

    config = _load_yaml(config_path)
    for name, prof in config["profiles"].items():
        total = sum(prof["pillar_weights"].values())
        if total != 100:
            raise FrameworkError(f"Profile '{name}' pillar weights sum to {total}, not 100")
        if set(prof["pillar_weights"]) != set(pillars):
            raise FrameworkError(f"Profile '{name}' must weight every pillar exactly once")
        for na in prof.get("not_applicable", []):
            if na not in dims:
                raise FrameworkError(f"Profile '{name}' marks unknown dimension {na} as N/A")

    gates = _load_yaml(red_flags_path)["gates"]
    for g in gates:
        if g["severity"] not in SEVERITIES:
            raise FrameworkError(f"{g['id']}: severity must be one of {SEVERITIES}")
        for cond in g["when"]["all"]:
            if "dim" in cond and cond["dim"] not in dims:
                raise FrameworkError(f"{g['id']}: references unknown dimension {cond['dim']}")
            if "pillar" in cond and cond["pillar"] not in pillars:
                raise FrameworkError(f"{g['id']}: references unknown pillar {cond['pillar']}")

    return Framework(pillars=pillars, dimensions=dims, gates=gates, config=config)
