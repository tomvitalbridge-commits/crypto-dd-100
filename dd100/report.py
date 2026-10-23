"""Render an Assessment into: report.md, memo.md, scorecard.json, radar.svg."""
from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path

from .evidence import HARNESS_SOURCE_ID
from .framework import Framework
from .models import Assessment, EvidencePack

VERDICT_BADGE = {
    "LIST": "🟢 LIST",
    "CONDITIONAL": "🟡 CONDITIONAL",
    "WATCHLIST": "🟠 WATCHLIST",
    "REJECT": "🔴 REJECT",
    "INSUFFICIENT_DATA": "⚪ INSUFFICIENT DATA",
}

KEY_METRICS = [
    ("market_cap_usd", "Market cap", "usd"),
    ("fdv_usd", "FDV", "usd"),
    ("volume_24h_usd", "24h volume", "usd"),
    ("depth_2pct_usd", "±2% depth", "usd"),
    ("tvl_usd", "TVL", "usd"),
    ("annualized_revenue_usd", "Protocol revenue (ann.)", "usd"),
    ("unlock_12m_pct_of_circ", "12m unlocks / circ.", "pct"),
    ("top10_holder_pct_ex_contracts", "Top-10 holders", "pct"),
]


def _usd(v: float) -> str:
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= div:
            return f"${v / div:,.1f}{unit}"
    return f"${v:,.0f}"


def _fmt(v, kind: str) -> str:
    if kind == "usd":
        return _usd(v)
    if kind == "pct":
        return f"{v:.1f}%"
    return str(v)


def _bar(score: float | None, width: int = 10) -> str:
    if score is None:
        return "·" * width
    filled = round(score / 4 * width)
    return "█" * filled + "░" * (width - filled)


def _score_cell(ds) -> str:
    if ds.status == "scored":
        return f"**{ds.score}**"
    return {"na": "n/a", "pending_human": "⏳", "rejected": "✖", "unscored": "–"}[ds.status]


# ----------------------------------------------------------------------------- radar
def radar_svg(a: Assessment, fw: Framework, width: int = 640, height: int = 500) -> str:
    cx, cy = width / 2, height / 2 + 18
    r_max = 160
    keys = list(fw.pillars)
    n = len(keys)

    def pt(i: int, v: float) -> tuple[float, float]:
        ang = -math.pi / 2 + 2 * math.pi * i / n
        r = r_max * v / 4
        return cx + r * math.cos(ang), cy + r * math.sin(ang)

    color = {"LIST": "#16a34a", "CONDITIONAL": "#ca8a04", "WATCHLIST": "#ea580c",
             "REJECT": "#dc2626"}.get(a.verdict, "#6b7280")
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'font-family="Inter,Helvetica,Arial,sans-serif" font-size="12">',
             f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    for ring in (1, 2, 3, 4):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, ring) for i in range(n)))
        parts.append(f'<polygon points="{pts}" fill="none" stroke="#e5e7eb" stroke-width="1"/>')
    for i in range(n):
        x, y = pt(i, 4)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#e5e7eb"/>')

    vals = [a.pillars[k].score if a.pillars[k].score is not None else 0 for k in keys]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, v) for i, v in enumerate(vals)))
    parts.append(f'<polygon points="{poly}" fill="{color}" fill-opacity="0.18" stroke="{color}" '
                 f'stroke-width="2" stroke-linejoin="round"/>')

    for i, k in enumerate(keys):
        x, y = pt(i, 4.55)
        pr = a.pillars[k]
        anchor = "middle" if abs(x - cx) < 12 else ("start" if x > cx else "end")
        label = fw.pillars[k].split(" &")[0].split(",")[0]
        val = "no data" if pr.score is None else f"{pr.score:.1f} / 4"
        grey = "" if pr.sufficient else ' fill="#9ca3af"'
        dy = -6 if y < cy - r_max * 0.9 else (8 if y > cy + r_max * 0.9 else 0)
        parts.append(f'<text x="{x:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" font-weight="600"{grey}>{k} · {label}</text>')
        parts.append(f'<text x="{x:.1f}" y="{y + dy + 15:.1f}" text-anchor="{anchor}" fill="#6b7280">{val}</text>')

    score = "—" if a.point_score is None else f"{a.point_score:.0f}"
    parts.append(f'<text x="20" y="34" font-size="26" font-weight="700" fill="{color}">{score}</text>')
    parts.append(f'<text x="{20 + 17 * len(score)}" y="34" font-size="13" fill="#374151">/100 · '
                 f'{a.verdict.replace("_", " ")} · grade {a.grade}</text>')
    parts.append(f'<text x="20" y="54" font-size="11" fill="#6b7280">range {a.score_low:.0f}–{a.score_high:.0f} · '
                 f'coverage {a.coverage:.0%} · grey = insufficient coverage</text>')
    parts.append("</svg>")
    return "\n".join(parts)


# ----------------------------------------------------------------------------- report
def render_report(a: Assessment, fw: Framework, pack: EvidencePack) -> str:
    L: list[str] = []
    score = "—" if a.point_score is None else f"{a.point_score:.1f}"
    L += [
        f"# {a.project} — DD-100 Due-Diligence Report",
        "",
        f"> **{VERDICT_BADGE[a.verdict]}** · Grade **{a.grade}** · Score **{score}/100** "
        f"(range {a.score_low:.0f}–{a.score_high:.0f}) · Evidence coverage **{a.coverage:.0%}**  ",
        f"> Profile `{a.profile}` · Evidence as of {a.as_of} · 100 dimensions · {len(pack.sources)} sources",
        "",
        "The range is the honest number: it shows where the score could land once unscored "
        "dimensions are filled and low-confidence judgments are firmed up.",
        "",
        "## Why this verdict",
        "",
    ]
    L += [f"- {r}" for r in a.verdict_reasons] + [""]

    # gates
    L += ["## Red-flag gates", "", "| Gate | Severity | Status | What it means |", "|---|---|---|---|"]
    order = {"fired": 0, "unchecked": 1, "clear": 2, "n/a": 3}
    sev = {"critical": 0, "major": 1, "minor": 2}
    icon = {"fired": "🚩 fired", "unchecked": "❔ unchecked", "clear": "✅ clear"}
    for g in sorted(a.gates, key=lambda g: (order[g.status], sev[g.severity])):
        if g.status in ("clear", "n/a"):
            continue
        L.append(f"| {g.id} {g.title} | {g.severity} | {icon[g.status]} | {g.why} |")
    n_clear = sum(1 for g in a.gates if g.status == "clear")
    n_na = sum(1 for g in a.gates if g.status == "n/a")
    tail = f" ({n_na} not applicable to this profile)" if n_na else ""
    L += ["", f"{n_clear} of {len(a.gates)} gates verified clear{tail}.", ""]

    # pillars
    L += ["## Pillar scores", "", "![radar](radar.svg)", "",
          "| Pillar | Weight | Score /4 | | Coverage | Scored |", "|---|---:|---:|---|---:|---:|"]
    for k, pr in a.pillars.items():
        s = "n/a" if pr.score is None else f"{pr.score:.2f}"
        flag = "" if pr.sufficient else " ⚠️"
        L.append(f"| {k} · {pr.name} | {pr.weight:.0f} | {s} | `{_bar(pr.score)}` | "
                 f"{pr.coverage:.0%}{flag} | {pr.scored}/{pr.applicable} |")
    L += ["", "⚠️ = coverage below the pillar minimum; treat that pillar's score as indicative.", ""]

    # contradictions
    L += ["## Claims vs. observation", ""]
    if a.contradictions:
        L += ["| Claim | Claimed | Observed | Gap | Sources |", "|---|---:|---:|---:|---|"]
        for c in a.contradictions:
            L.append(f"| {c.claim.statement} | {c.claim.claimed_value:,} | {c.observed:,} | "
                     f"{c.deviation:.0%} | {c.claim.source} vs {c.observed_source} |")
    else:
        checked = len(pack.claims)
        L.append(f"No contradictions found across {checked} checked project claim(s).")
    L.append("")

    # strengths / risks
    scored = [(fw.dimensions[d], s) for d, s in a.dims.items() if s.status == "scored"]
    strengths = sorted([x for x in scored if x[1].score >= 3], key=lambda x: (-x[1].score, -x[0].weight))[:6]
    risks = sorted([x for x in scored if x[1].score <= 2], key=lambda x: (x[1].score, -x[0].weight))[:6]
    L += ["## Strengths", ""]
    L += [f"- **{d.id} {d.name}** ({s.score}/4) — {s.rationale}" for d, s in strengths] or ["- none scored ≥3"]
    L += ["", "## Risks", ""]
    L += [f"- **{d.id} {d.name}** ({s.score}/4) — {s.rationale}" for d, s in risks] or ["- none scored ≤2"]
    L.append("")

    # open questions
    L += ["## Open questions for the project team", "",
          "Everything below is unscored. Each one is a question to put to the team or a data "
          "request, not a negative finding.", ""]
    for status, header in (("pending_human", "Needs a private channel (call, data room, counsel)"),
                           ("unscored", "Needs evidence"),
                           ("rejected", "Submitted but rejected by the harness")):
        items = [(fw.dimensions[d], s) for d, s in a.dims.items() if s.status == status]
        if not items:
            continue
        L += [f"**{header}** ({len(items)})", ""]
        for d, s in items:
            note = f" — _{'; '.join(s.notes)}_" if s.notes else ""
            L.append(f"- {d.id} {d.name}: {d.question}{note}")
        L.append("")

    downgrades = [(d, s) for d, s in a.dims.items() if any("downgraded" in n for n in s.notes)]
    if downgrades:
        L += ["## Verification audit", "",
              "Confidence the harness lowered because the cited evidence did not meet the bar:", ""]
        L += [f"- {d}: {'; '.join(s.notes)}" for d, s in downgrades] + [""]

    # appendix
    L += ["## Appendix A — all 100 dimensions", ""]
    for k, name in fw.pillars.items():
        L += [f"### {k} · {name}", "", "| ID | Dimension | Method | W | Score | Conf. | Evidence | Basis |",
              "|---|---|---|---:|---:|---|---|---|"]
        for d in fw.by_pillar(k):
            s = a.dims[d.id]
            basis = s.rationale or "; ".join(s.notes)
            L.append(f"| {d.id} | {d.name} | {d.method} | {d.weight} | {_score_cell(s)} | "
                     f"{s.confidence or ''} | {', '.join(s.evidence)} | {basis} |")
        L.append("")

    L += ["## Appendix B — sources", "", "| ID | Tier | Type | Title |", "|---|---|---|---|"]
    tier_name = {1: "1 · primary", 2: "2 · independent", 3: "3 · self-reported"}
    for src in pack.sources.values():
        title = f"[{src.title}]({src.url})" if src.url else src.title
        L.append(f"| {src.id} | {tier_name[src.tier]} | {src.type} | {title} |")
    L += [f"| {HARNESS_SOURCE_ID} | computed | harness | Metrics derived by the harness from other evidence |", ""]
    L += ["---", "_Generated by DD-100. Scores are decision support for a listing committee, "
          "not investment advice. Every judgment above cites its evidence; anything uncited was not scored._"]
    return "\n".join(L)


def render_memo(a: Assessment, fw: Framework, pack: EvidencePack) -> str:
    score = "—" if a.point_score is None else f"{a.point_score:.0f}"
    scored = [(fw.dimensions[d], s) for d, s in a.dims.items() if s.status == "scored"]
    # The memo leads with explained judgments; computed rules fill in after them.
    judged = lambda d: 0 if d.method != "rule" else 1
    pros = sorted([x for x in scored if x[1].score >= 3 and x[1].evidence != [HARNESS_SOURCE_ID]],
                  key=lambda x: (judged(x[0]), -x[0].weight, -x[1].score))[:3]
    cons = sorted([x for x in scored if x[1].score <= 2],
                  key=lambda x: (judged(x[0]), x[1].score, -x[0].weight))[:3]
    fired = [g for g in a.gates if g.status == "fired" and g.severity != "minor"]

    L = [f"# Listing memo — {a.project}", "",
         f"**Recommendation: {VERDICT_BADGE[a.verdict]}** · Grade {a.grade} · {score}/100 "
         f"(range {a.score_low:.0f}–{a.score_high:.0f}) · coverage {a.coverage:.0%} · as of {a.as_of}", ""]
    nums = [(label, _fmt(pack.metrics[k].value, kind)) for k, label, kind in KEY_METRICS if k in pack.metrics]
    if nums:
        L += ["| " + " | ".join(n for n, _ in nums) + " |", "|" + "---|" * len(nums),
              "| " + " | ".join(v for _, v in nums) + " |", ""]
    L += ["**The case for**", ""]
    short = lambda r: r.split("  (bands")[0]
    L += [f"{i}. {d.name} ({s.score}/4) — {short(s.rationale)}" for i, (d, s) in enumerate(pros, 1)] or ["—"]
    L += ["", "**The case against**", ""]
    against = [f"{d.name} ({s.score}/4) — {short(s.rationale)}" for d, s in cons]
    against += [f"Claim contradicted: {c.claim.statement} vs observed {c.observed:,} ({c.deviation:.0%} gap)"
                for c in a.contradictions[:2]]
    L += [f"{i}. {t}" for i, t in enumerate(against, 1)] or ["—"]
    if fired:
        L += ["", "**Gates**", ""] + [f"- 🚩 {g.id} {g.title} ({g.severity})" for g in fired]
    L += ["", "**What has to be true before we act**", ""]
    L += [f"- {r}" for r in a.verdict_reasons]
    open_n = sum(1 for s in a.dims.values() if s.status in ("unscored", "pending_human"))
    if open_n:
        L.append(f"- {open_n} open question(s) for the team are listed in report.md")
    L += ["", "_Full 100-dimension report: report.md_"]
    return "\n".join(L)


def write_outputs(a: Assessment, fw: Framework, pack: EvidencePack, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "report.md": render_report(a, fw, pack),
        "memo.md": render_memo(a, fw, pack),
        "radar.svg": radar_svg(a, fw),
        "scorecard.json": json.dumps(asdict(a), indent=2, ensure_ascii=False, default=str),
    }
    paths = []
    for name, content in files.items():
        p = out_dir / name
        p.write_text(content, encoding="utf-8")
        paths.append(p)
    return paths
