"""Render README figures for a reviewed project from its scorecard.json.

    python scripts/make_figures.py examples/hyperliquid --out docs/img

Every number on the figures is read from the harness output (scorecard.json)
or the evidence pack, except the short list of context facts in FACTS below,
each of which carries the evidence id it comes from. Re-run after re-scoring.
Needs matplotlib (pip install matplotlib).
"""
from __future__ import annotations

import argparse
import json
import textwrap
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle

# ---------------------------------------------------------------- style
for f in font_manager.findSystemFonts():
    if "Inter" in Path(f).name:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Inter", "DejaVu Sans"]

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BORDER = "#e6e5df"
BLUE = "#2a78d6"
BLUE_LIGHT = "#cde2fb"
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
VERDICT_STYLE = {
    "LIST": ("good", "LIST"),
    "CONDITIONAL": ("warning", "CONDITIONAL LISTING"),
    "WATCHLIST": ("serious", "WATCHLIST"),
    "REJECT": ("critical", "REJECT"),
    "INSUFFICIENT_DATA": ("serious", "INSUFFICIENT DATA"),
}
GRADE_BANDS = [(0, 35, "F"), (35, 50, "D"), (50, 65, "C"), (65, 80, "B"), (80, 100, "A")]
DPI = 200


def card(fig, x, y, w, h, fc=SURFACE, ec=BORDER, lw=1.2, r=0.012):
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                      transform=fig.transFigure, fc=fc, ec=ec, lw=lw, zorder=-5))


def usd(v: float) -> str:
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= div:
            return f"${v / div:,.1f}{unit}".replace(".0", "") if unit != "M" else f"${v / div:,.0f}M"
    return f"${v:,.0f}"


def save(fig, path: Path, tight: bool = False) -> None:
    fig.savefig(path, dpi=DPI, facecolor=fig.get_facecolor(),
                **({"bbox_inches": "tight", "pad_inches": 0.25} if tight else {}))
    plt.close(fig)
    print(f"wrote {path}")


# ---------------------------------------------------------------- 1 · verdict card
def verdict_card(sc, metrics, facts, out: Path) -> None:
    fig = plt.figure(figsize=(11, 4.4), facecolor="white")
    card(fig, 0.01, 0.02, 0.98, 0.96)
    status, label = VERDICT_STYLE[sc["verdict"]]
    col = STATUS[status]

    fig.text(0.045, 0.875, f"{sc['project']} · DD-100 listing review", fontsize=12.5, color=INK2, weight="medium")
    fig.text(0.045, 0.825, f"Public sources only · as of {sc['as_of']}", fontsize=9.5, color=MUTED)

    # verdict pill
    fig.patches.append(FancyBboxPatch((0.045, 0.60), 0.385, 0.15, boxstyle="round,pad=0,rounding_size=0.02",
                                      transform=fig.transFigure, fc=col, ec="none"))
    fig.text(0.065, 0.675, "◐  " + label, fontsize=18, weight="bold", color=INK if status == "warning" else "white",
             va="center")

    fired = [g for g in sc["gates"] if g["status"] == "fired" and g["severity"] != "minor"]
    unchecked_crit = [g for g in sc["gates"] if g["status"] == "unchecked" and g["severity"] == "critical"]
    pending = [d for d, s in sc["dims"].items() if s["status"] == "pending_human"]
    lines = []
    if sc["verdict"] == "CONDITIONAL":
        lines.append("Clears the listing bar on evidence, but listing is blocked until:")
    for g in unchecked_crit:
        lines.append(f"•  {g['title'].split(' /')[0]} screening is run ({g['id']})")
    if pending:
        lines.append(f"•  {len(pending)} private checks close: KYC, MM terms, legal opinion")
    for g in fired:
        lines.append(f"•  {g['id']} {g['title']}")
    fig.text(0.045, 0.53, "\n".join(lines), fontsize=10, color=INK, va="top", linespacing=1.75)

    # score range strip (secondary)
    ax = fig.add_axes([0.045, 0.07, 0.40, 0.14]); ax.set_zorder(5)
    ax.set_xlim(0, 100); ax.set_ylim(0, 1); ax.axis("off")
    for lo, hi, g in GRADE_BANDS:
        ax.add_patch(Rectangle((lo, 0.35), hi - lo - 0.6, 0.3, fc="#f1f0ec", ec="none"))
        ax.text((lo + hi) / 2, 0.08, g, ha="center", fontsize=8.5, color=MUTED)
    ax.add_patch(Rectangle((sc["score_low"], 0.35), sc["score_high"] - sc["score_low"], 0.3, fc=BLUE_LIGHT, ec="none"))
    ax.plot([sc["point_score"]] * 2, [0.28, 0.72], color=BLUE, lw=2.4, solid_capstyle="round")
    ax.text(sc["score_low"], 0.82, f"{sc['score_low']:.0f}", ha="center", fontsize=8, color=INK2)
    ax.text(sc["score_high"], 0.82, f"{sc['score_high']:.0f}", ha="center", fontsize=8, color=INK2)
    fig.text(0.045, 0.24, f"Score range {sc['score_low']:.0f}–{sc['score_high']:.0f}  ·  point {sc['point_score']:.0f}  ·  "
             f"grade {sc['grade']}  ·  evidence coverage {sc['coverage']:.0%}", fontsize=9, color=INK2)

    # key facts grid
    fig.text(0.50, 0.875, "What the evidence says", fontsize=11, color=INK, weight="semibold")
    x0, y0, cw, ch = 0.50, 0.50, 0.236, 0.29
    for i, (value, caption, tone) in enumerate(facts):
        cx = x0 + (i % 2) * (cw + 0.012)
        cy = y0 - (i // 2) * (ch + 0.03)
        card(fig, cx, cy, cw, ch, fc="white", ec=BORDER, lw=1, r=0.01)
        fig.patches.append(Rectangle((cx, cy + 0.03), 0.004, ch - 0.06, transform=fig.transFigure,
                                     fc=STATUS["good"] if tone == "+" else STATUS["critical"], ec="none"))
        fig.text(cx + 0.018, cy + ch - 0.085, value, fontsize=16, weight="bold", color=INK)
        fig.text(cx + 0.018, cy + 0.04, caption, fontsize=8.4, color=INK2, linespacing=1.35)
    fig.text(0.50, 0.035, "Green bar = strength, red bar = risk. Source ids refer to examples/hyperliquid/evidence.",
             fontsize=7.8, color=MUTED)
    save(fig, out)


# ---------------------------------------------------------------- 2 · pillar bars
def pillar_chart(sc, out: Path) -> None:
    rows = sorted(sc["pillars"].values(), key=lambda p: (p["score"] or 0))
    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor="white")
    fig.subplots_adjust(left=0.27, right=0.78, top=0.84, bottom=0.12)
    ax.set_facecolor(SURFACE)
    names = [f"{p['pillar']} · {p['name']}" for p in rows]
    vals = [p["score"] or 0 for p in rows]
    ys = range(len(rows))
    for y, p, v in zip(ys, rows, vals):
        weak = round(v, 1) < 2.5
        bar = ax.barh(y, v, height=0.62, color=BLUE if not weak else "#eb6834", edgecolor=SURFACE, lw=0)
        if not p["sufficient"]:
            bar[0].set_hatch("////"); bar[0].set_edgecolor("white"); bar[0].set_alpha(0.55)
        ax.text(v + 0.05, y, f"{v:.1f}", va="center", fontsize=10, color=INK, weight="semibold")
        cov = f"{p['coverage']:.0%} evidenced" + (" (low)" if not p["sufficient"] else "")
        ax.text(4.25, y, cov, va="center", fontsize=8.6, color=MUTED, transform=ax.transData, clip_on=False)
    ax.set_yticks(list(ys)); ax.set_yticklabels(names, fontsize=10, color=INK)
    ax.set_xlim(0, 4); ax.set_xticks([0, 1, 2, 3, 4])
    ax.set_xticklabels(["0", "1", "2", "3", "4  best"], fontsize=9, color=MUTED)
    ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(length=0)
    fig.text(0.03, 0.93, "Where Hyperliquid is strong and weak", fontsize=14, weight="bold", color=INK)
    fig.text(0.03, 0.885, "Average score per pillar, 0–4 · orange = below 2.5 · hatched = under 60% of the pillar could be evidenced",
             fontsize=9, color=INK2)
    save(fig, out)


# ---------------------------------------------------------------- 3 · gate board
def gate_board(sc, out: Path) -> None:
    icon = {"clear": ("✓", STATUS["good"], "Clear"), "fired": ("!", STATUS["critical"], "Fired"),
            "unchecked": ("?", STATUS["warning"], "Needs data"), "n/a": ("–", MUTED, "N/A")}
    groups = [("critical", "CRITICAL  ·  any one fired = reject"), ("major", "MAJOR  ·  fired = grade capped at C"),
              ("minor", "MINOR  ·  shown, no automatic effect")]
    fig = plt.figure(figsize=(10, 6.0), facecolor="white")
    fig.text(0.03, 0.945, "16 red-flag checks, run after scoring", fontsize=14, weight="bold", color=INK)
    counts = {k: sum(1 for g in sc["gates"] if g["status"] == k) for k in icon}
    fig.text(0.03, 0.905, f"{counts['clear']} clear  ·  {counts['unchecked']} need data that isn't public  ·  "
             f"{counts['fired']} fired (minor)", fontsize=9.5, color=INK2)
    y = 0.84
    cols, cw, ch, gap = 4, 0.228, 0.095, 0.012
    for sev, header in groups:
        gs = [g for g in sc["gates"] if g["severity"] == sev]
        fig.text(0.03, y, header, fontsize=8.5, color=MUTED, weight="semibold")
        y -= 0.02
        for i, g in enumerate(gs):
            r, c = divmod(i, cols)
            x = 0.03 + c * (cw + gap)
            yy = y - (r + 1) * (ch + gap)
            sym, colr, lab = icon[g["status"]]
            card(fig, x, yy, cw, ch, fc="white", ec=colr if g["status"] in ("fired", "unchecked") else BORDER,
                 lw=1.4 if g["status"] in ("fired", "unchecked") else 1, r=0.008)
            fig.patches.append(FancyBboxPatch((x + 0.01, yy + ch / 2 - 0.022), 0.032, 0.044,
                                              boxstyle="round,pad=0,rounding_size=0.01", transform=fig.transFigure,
                                              fc=colr, ec="none"))
            fig.text(x + 0.026, yy + ch / 2, sym, ha="center", va="center", fontsize=11, weight="bold",
                     color=INK if colr == STATUS["warning"] else "white")
            title = "\n".join(textwrap.wrap(g["title"], 33)[:2])
            fig.text(x + 0.052, yy + ch - 0.026, f"{g['id']}  {lab}", fontsize=7.6, color=INK2, weight="semibold")
            fig.text(x + 0.052, yy + ch - 0.04, title, fontsize=7.6, color=INK, va="top", linespacing=1.25)
        rows = -(-len(gs) // cols)
        y = y - rows * (ch + gap) - 0.045
    save(fig, out, tight=True)


# ---------------------------------------------------------------- 4 · timeline vs Binance
def timeline(events, verdict, out: Path) -> None:
    fig = plt.figure(figsize=(10, 4.4), facecolor="white")
    fig.text(0.03, 0.92, "Binance's decision vs. the DD-100 read", fontsize=14, weight="bold", color=INK)
    fig.text(0.03, 0.865, "Binance listed perps first, then spot with a Seed Tag (its conditional tier). "
             "DD-100, from public data only, lands on conditional too.", fontsize=9.5, color=INK2)
    ax = fig.add_axes([0.04, 0.12, 0.92, 0.66])
    d0, d1 = date(2024, 10, 15), date(2026, 12, 1)
    span = (d1 - d0).days
    X = lambda d: (d - d0).days / span
    ax.set_xlim(0, 1); ax.set_ylim(-1, 1); ax.axis("off")
    ax.plot([0, 1], [0, 0], color=BASELINE, lw=1.5)
    for yr in (2025, 2026):
        x = X(date(yr, 1, 1))
        ax.plot([x, x], [-0.06, 0.06], color=BASELINE, lw=1.2)
        ax.text(x, -0.16, str(yr), ha="center", fontsize=8.5, color=MUTED)
    above = True
    for d, text, kind in events:
        x = X(d)
        colr = {"binance": BLUE, "risk": STATUS["critical"], "project": MUTED, "dd": STATUS["warning"]}[kind]
        lvl = 0.42 if above else -0.42
        if kind in ("binance", "dd"):
            lvl = 0.62 if above else -0.62
        ax.plot([x, x], [0, lvl * 0.78], color=colr, lw=1.2)
        ax.scatter([x], [0], s=70 if kind in ("binance", "dd") else 38, color=colr, zorder=3,
                   edgecolor="white", linewidth=1.5)
        ax.text(x, lvl, f"{d:%b %Y}\n{text}", ha="center", va="bottom" if above else "top", fontsize=8.3,
                color=INK, weight="semibold" if kind in ("binance", "dd") else "normal", linespacing=1.3)
        above = not above
    # legend
    lx = 0.03
    for lab, colr in (("Binance action", BLUE), ("DD-100 review", STATUS["warning"]), ("Risk event", STATUS["critical"]),
                      ("Project milestone", MUTED)):
        fig.patches.append(Rectangle((lx, 0.05), 0.012, 0.025, transform=fig.transFigure, fc=colr, ec="none"))
        fig.text(lx + 0.018, 0.053, lab, fontsize=8.5, color=INK2)
        lx += 0.16
    save(fig, out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--out", default="docs/img")
    a = ap.parse_args()
    pdir, out = Path(a.project_dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sc = json.loads((pdir / "report" / "scorecard.json").read_text())
    metrics = {}
    for f in sorted((pdir / "evidence").glob("*.json")):
        metrics.update({k: v["value"] for k, v in json.loads(f.read_text())["metrics"].items()})

    # Context facts for the card. Values from evidence metrics where one exists;
    # the rest cite the source id they come from.
    facts = [
        (usd(metrics["annualized_fees_usd"]), "annualised fees, with $0 spent\non usage incentives (H02)", "+"),
        ("57.5%", "of perp-DEX open interest;\n32.8% of 30-day volume (H10)", "+"),
        ("~49%", "of stake held by 5 Foundation\nvalidators; L1 closed source (H18)", "-"),
        ("0", "public audits of the L1;\nno licence, FCA warning (H23, H34)", "-"),
    ]
    events = [
        (date(2024, 11, 29), "HYPE genesis,\nno VC allocation", "project"),
        (date(2025, 3, 26), "JELLY manipulation;\nvalidators force-settle", "risk"),
        (date(2025, 5, 30), "Binance lists\nHYPE perps", "binance"),
        (date(2025, 10, 13), "HIP-3 builder\nmarkets live", "project"),
        (date(2026, 5, 12), "US spot ETFs\nlaunch", "project"),
        (date(2026, 6, 26), "FCA warning (May),\nMAS alert (Jun)", "risk"),
        (date(2026, 9, 24), "Binance lists spot\nwith Seed Tag", "binance"),
        (date(2026, 10, 23), "DD-100: conditional\n(public data)", "dd"),
    ]
    verdict_card(sc, metrics, facts, out / "hyperliquid-verdict.png")
    pillar_chart(sc, out / "hyperliquid-pillars.png")
    gate_board(sc, out / "hyperliquid-gates.png")
    timeline(events, sc["verdict"], out / "hyperliquid-timeline.png")


if __name__ == "__main__":
    main()
