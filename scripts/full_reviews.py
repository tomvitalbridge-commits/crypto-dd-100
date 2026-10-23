"""Compare point-in-time full reviews with post-listing outcomes.

    python scripts/full_reviews.py            # 10 spot listings (Binance / Coinbase)
    python scripts/full_reviews.py futures    # 10 Binance futures-only listings

Reads reviews/listings-2025-26/*/report/scorecard.json (run the harness on each
manifest first) and data/backtest/results.csv; writes data/backtest/full_reviews.csv
and docs/img/backtest-full-reviews.png, and prints the markdown table used in
docs/BACKTEST.md.
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
LABEL_BELOW = {"MMT"}


SETS = {
    "spot": {"dir": "reviews/listings-2025-26", "csv": "data/backtest/full_reviews.csv",
             "png": "docs/img/backtest-full-reviews.png",
             "title": "Ten point-in-time full reviews: the score did not predict 90-day price"},
    "futures": {"dir": "reviews/futures-2025-26", "csv": "data/backtest/full_reviews_futures.csv",
                "png": "docs/img/backtest-futures-reviews.png",
                "title": "Ten Binance futures-only listings: full review score vs 90-day price"},
}


def outcome(kind: str, ex: str, sym: str):
    if kind == "spot":
        res = pd.read_csv(ROOT / "data/backtest/results.csv", dtype={"sym": str})
        o = res[(res.ex == ex) & (res.sym == sym)].iloc[0]
        return o.score, o.x30, o.x90, o.xlast
    fo = pd.read_csv(ROOT / "data/backtest/futures_only.csv", dtype={"base": str})
    o = fo[fo.base == sym].iloc[0]
    return float("nan"), o.x30, o.x90, o.xlast


def collect(kind: str = "spot") -> pd.DataFrame:
    rows = []
    for d in sorted(glob.glob(str(ROOT / SETS[kind]["dir"]) + "/*/")):
        sc = json.load(open(os.path.join(d, "report", "scorecard.json")))
        ex, sym = os.path.basename(d.rstrip("/")).split("-", 1)
        score, x30, x90, xlast = outcome(kind, ex, sym)
        gates = {g["id"]: g["status"] for g in sc["gates"]}
        rows.append({"token": sym, "exchange": ex, "as_of": sc["as_of"], "full_score": sc["point_score"],
                     "range_low": sc["score_low"], "range_high": sc["score_high"], "coverage": sc["coverage"],
                     "grade": sc["grade"], "verdict": sc["verdict"],
                     "gates_fired": ",".join(k for k, v in gates.items() if v == "fired"),
                     "critical_unchecked": ",".join(k for k, v in gates.items()
                                                    if v == "unchecked" and k in ("RF01", "RF02", "RF03", "RF04", "RF05")),
                     "screening_score": score, "x30": x30, "x90": x90, "x_to_date": xlast})
    return pd.DataFrame(rows).sort_values("x90")


def markdown(df: pd.DataFrame) -> str:
    pct = lambda x: f"{x * 100:+.0f}%"
    lines = ["| Token | Listed | Score (range) | Grade | Coverage | Gates fired | 90d vs BTC | To 23 Oct 2026 |",
             "|---|---|---|---|---:|---|---:|---:|"]
    for _, r in df.iterrows():
        lines.append(f"| {r.token} | {r.exchange.title()} {r.as_of} | {r.full_score:.1f} ({r.range_low:.0f}–{r.range_high:.0f}) "
                     f"| {r.grade} | {r.coverage:.0%} | {r.gates_fired or '–'} | {pct(r.x90)} | {pct(r.x_to_date)} |")
    return "\n".join(lines)


def chart(df: pd.DataFrame, out: Path, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in font_manager.findSystemFonts():
        if "Inter" in Path(f).name:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = ["Inter", "DejaVu Sans"]
    rho, p = stats.spearmanr(df.full_score, df.x90)
    fig, ax = plt.subplots(figsize=(10, 5), facecolor="white")
    fig.subplots_adjust(left=0.09, right=0.97, top=0.8, bottom=0.13)
    ax.set_facecolor("#fcfcfb")
    ax.axhline(0, color="#c3c2b7", lw=1)
    for _, r in df.iterrows():
        ax.plot([r.range_low, r.range_high], [r.x90 * 100] * 2, color="#cde2fb", lw=6, solid_capstyle="round", zorder=1)
        ax.scatter(r.full_score, r.x90 * 100, s=64, color="#2a78d6", edgecolor="white", linewidth=1.5, zorder=3)
        ax.annotate(r.token, (r.full_score, r.x90 * 100), xytext=(7, -15 if r.token in LABEL_BELOW else 6), textcoords="offset points", fontsize=9.5, color="#0b0b0b")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Full DD-100 review score at listing (bar = score range)", color="#52514e", fontsize=9.5)
    ax.set_ylabel("90-day return vs BTC (%)", color="#52514e", fontsize=9.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(True, color="#e1e0d9", lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0, colors="#52514e")
    fig.text(0.03, 0.93, title, fontsize=14, weight="bold", color="#0b0b0b")
    fig.text(0.03, 0.875, f"Spearman ρ = {rho:+.2f} (p = {p:.2f}, n = {len(df)}). Every review stayed below the 70% evidence coverage needed for a verdict.",
             fontsize=9.5, color="#52514e")
    fig.savefig(out, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    kind = sys.argv[1] if len(sys.argv) > 1 else "spot"
    cfg = SETS[kind]
    df = collect(kind)
    df.to_csv(ROOT / cfg["csv"], index=False)
    chart(df, ROOT / cfg["png"], cfg["title"])
    print(markdown(df))
    for a in ("full_score", "screening_score"):
        if df[a].isna().all():
            continue
        for b in ("x30", "x90", "x_to_date"):
            rho, p = stats.spearmanr(df[a], df[b])
            print(f"{a} vs {b}: rho={rho:+.2f} p={p:.2f}")
