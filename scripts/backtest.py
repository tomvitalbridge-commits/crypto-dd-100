"""Backtest the DD-100 screening score against post-listing performance.

    python scripts/backtest.py data/backtest/features.csv

Input: one row per listing event (exchange, token, listing date) with metrics
known AT the listing date, plus prices after it. See data/backtest/README.md
for how each column was collected.

For every event the script writes an evidence pack + manifest, runs the real
DD-100 harness on it (same framework, same thresholds, no tuning), and then
compares the resulting screening score with the token's return relative to BTC
30 and 90 days after listing.

Only ~10 of the 37 rule dimensions can be observed at listing time from free
public data, so this is a test of the SCREENING layer, not of a full review.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dd100.framework import load_framework  # noqa: E402
from dd100.harness import run  # noqa: E402

DEFI = {"Dexs", "Lending", "Derivatives", "Yield", "Yield Aggregator", "Liquid Staking", "CDP", "Restaking",
        "Liquid Restaking", "Basis Trading", "Perpetuals", "Options", "Launchpad", "Prediction Market",
        "Synthetics", "Bridge", "Cross Chain", "Onchain Capital Allocator", "Liquidity manager", "Staking Pool",
        "Insurance", "Algo-Stables", "Stablecoin Issuer", "Interface"}

METRIC_SOURCES = {
    "circulating_supply": "S-SUPPLY", "total_supply": "S-SUPPLY", "market_cap_usd": "S-SUPPLY", "fdv_usd": "S-SUPPLY",
    "unlock_12m_pct_of_circ": "S-UNLOCK", "unlock_90d_pct_of_circ": "S-UNLOCK", "insider_allocation_pct": "S-UNLOCK",
    "tvl_usd": "S-LLAMA", "annualized_fees_usd": "S-LLAMA", "annualized_revenue_usd": "S-LLAMA",
    "revenue_qoq_growth_pct": "S-LLAMA", "volume_24h_usd": "S-EXCH",
}


def num(x):
    try:
        v = float(x)
        return None if np.isnan(v) else v
    except (TypeError, ValueError):
        return None


def profile_for(category: str) -> str:
    if category == "Chain":
        return "l1_l2"
    if category == "RWA":
        return "rwa"
    if category in DEFI:
        return "defi"
    return "infra"


def build_pack(r: dict) -> dict:
    d = r["date"]
    sources = [
        {"id": "S-EXCH", "type": "api", "tier": 2, "title": f"{r['ex'].title()} public market data (daily candles)", "retrieved": "2026-10-23"},
        {"id": "S-SUPPLY", "type": "api", "tier": 2, "title": f"Supply at listing ({r['circ_src']}) and max supply (CoinGecko)", "retrieved": "2026-10-23"},
        {"id": "S-UNLOCK", "type": "tokenomics", "tier": 2, "title": "DefiLlama documented unlock schedule", "retrieved": "2026-10-23"},
        {"id": "S-LLAMA", "type": "api", "tier": 2, "title": "DefiLlama TVL / fees / revenue history", "retrieved": "2026-10-23"},
    ]
    m = {}
    p0, circ0, maxs = num(r["p0"]), num(r["circ0"]), num(r["max_supply"])
    if p0 and circ0:
        m["circulating_supply"] = circ0
        m["market_cap_usd"] = p0 * circ0
    if p0 and maxs:
        m["total_supply"] = maxs
        m["fdv_usd"] = p0 * maxs
    for col, metric in (("unlock12", "unlock_12m_pct_of_circ"), ("unlock90", "unlock_90d_pct_of_circ"),
                        ("insider_pct", "insider_allocation_pct"), ("tvl0", "tvl_usd"), ("fees_ann0", "annualized_fees_usd"),
                        ("rev_ann0", "annualized_revenue_usd"), ("rev_qoq", "revenue_qoq_growth_pct"), ("vol0", "volume_24h_usd")):
        v = num(r.get(col))
        if v is not None:
            m[metric] = round(v, 4)
    metrics = {k: {"value": v, "source": METRIC_SOURCES[k]} for k, v in m.items()}
    return {"project": f"{r['name']} ({r['sym']})", "as_of": d, "sources": sources, "metrics": metrics, "claims": []}


def score_all(df: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    fw = load_framework()
    rows = []
    for _, r in df.iterrows():
        r = r.to_dict()
        slug = f"{r['ex']}_{r['sym']}".replace("/", "-")
        d = out_dir / slug
        (d / "evidence").mkdir(parents=True, exist_ok=True)
        (d / "evidence" / "pack.json").write_text(json.dumps(build_pack(r), indent=1, ensure_ascii=False))
        (d / "manifest.yaml").write_text(
            f"project: \"{r['name']} ({r['sym']})\"\nprofile: {profile_for(str(r.get('category') or ''))}\n"
            f"as_of: {r['date']}\nevidence:\n  - evidence/pack.json\n", encoding="utf-8")
        a, _ = run(d / "manifest.yaml", fw=fw)
        fired = [g.id for g in a.gates if g.status == "fired"]
        dims = {k: (v.score if v.status == "scored" else None) for k, v in a.dims.items() if fw.dimensions[k].method == "rule"}
        rows.append({"ex": r["ex"], "sym": r["sym"], "score": a.point_score, "coverage": a.coverage,
                     "n_scored": sum(1 for v in a.dims.values() if v.status == "scored"),
                     "gates_fired": ",".join(fired), **{f"d_{k}": v for k, v in dims.items()}})
    return pd.DataFrame(rows)


def excess(p1, p0, b1, b0):
    if not all(x and x > 0 for x in (p1, p0, b1, b0)):
        return None
    return (p1 / p0) / (b1 / b0) - 1


def main(path: str) -> None:
    raw = pd.read_csv(path, dtype={"sym": str})
    df = raw.copy()
    for h in (30, 90):
        df[f"x{h}"] = [excess(num(a.get(f"p{h}")), num(a.get("p0")), num(a.get(f"btc{h}")), num(a.get("btc0")))
                       for a in df.to_dict("records")]
    df["xlast"] = [excess(num(a.get("plast")), num(a.get("p0")), num(a.get("btclast")), num(a.get("btc0")))
                   for a in df.to_dict("records")]
    scores = score_all(df, ROOT / "data" / "backtest" / "runs")
    res = df.merge(scores, on=["ex", "sym"])
    res.to_csv(ROOT / "data" / "backtest" / "results.csv", index=False)
    print(f"scored {len(res)} listing events → data/backtest/results.csv")
    summary = analyse(res)
    (ROOT / "data" / "backtest" / "summary.json").write_text(json.dumps(summary, indent=2))
    figures(res, summary, ROOT / "docs" / "img")
    print(json.dumps(summary, indent=2))


def spear(df: pd.DataFrame, a: str, b: str) -> dict:
    s = df[[a, b]].dropna()
    if len(s) < 8:
        return {"n": len(s)}
    rho, p = stats.spearmanr(s[a], s[b])
    return {"rho": round(float(rho), 3), "p": round(float(p), 4), "n": int(len(s))}


def analyse(r: pd.DataFrame) -> dict:
    r = r.copy()
    r["circ_pct"] = (r.circ0 / r.max_supply * 100).clip(upper=100)
    r["fdv_mcap"] = r.max_supply / r.circ0
    d = r.dropna(subset=["x90"]).copy()
    tok = d.sort_values("date").drop_duplicates("cg")
    out = {
        "events": int(len(r)), "by_exchange": r.ex.value_counts().to_dict(),
        "window": [str(r.date.min()), str(r.date.max())],
        "n90": int(len(d)), "unique_tokens90": int(len(tok)),
        "base_rate": {h: {"median": round(float(r[h].median()), 3), "share_below_btc": round(float((r[h].dropna() < 0).mean()), 3),
                          "n": int(r[h].notna().sum())} for h in ("x30", "x90", "xlast")},
        "by_exchange_x90": d.groupby("ex").x90.agg(["size", "median"]).round(3).to_dict("index"),
        "signals_event": {c: spear(d, c, "x90") for c in ("score", "circ_pct", "fdv_mcap", "vol0", "unlock12", "insider_pct", "rev_ann0", "tvl0")},
        "signals_token": {c: spear(tok, c, "x90") for c in ("score", "circ_pct", "vol0")},
        "circ_pct_schedule_subset": spear(d[d.circ_src == "llama_schedule"], "circ_pct", "x90"),
        "coverage_median_dims": float(r.n_scored.median()),
    }
    d["float_bucket"] = pd.cut(d.circ_pct, [0, 15, 25, 40, 100.1], labels=["<15%", "15-25%", "25-40%", ">40%"])
    out["float_buckets"] = {str(k): {"n": int(len(g)), "median": round(float(g.x90.median()), 3),
                                    "share_below_btc": round(float((g.x90 < 0).mean()), 3)}
                            for k, g in d.groupby("float_bucket", observed=True)}
    d["score_tercile"] = pd.qcut(d.score.rank(method="first"), 3, labels=["low", "mid", "high"])
    out["score_terciles"] = {str(k): {"n": int(len(g)), "median": round(float(g.x90.median()), 3),
                                     "score_range": [float(g.score.min()), float(g.score.max())]}
                             for k, g in d.groupby("score_tercile", observed=True)}
    d["vol_tercile"] = pd.qcut(d.vol0.rank(method="first"), 3, labels=["low", "mid", "high"])
    out["volume_terciles"] = {str(k): {"n": int(len(g)), "median": round(float(g.x90.median()), 3)}
                              for k, g in d.groupby("vol_tercile", observed=True)}
    return out


def figures(r: pd.DataFrame, s: dict, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in font_manager.findSystemFonts():
        if "Inter" in Path(f).name:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = ["Inter", "DejaVu Sans"]
    INK, INK2, MUTED, GRID, BLUE, ORANGE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#2a78d6", "#eb6834", "#fcfcfb"

    def style(ax):
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color("#c3c2b7"); ax.tick_params(length=0, colors=INK2)
        ax.set_facecolor(SURF)

    # 1 — float at listing vs 90d return vs BTC
    fb = s["float_buckets"]; labs = list(fb)
    fig, ax = plt.subplots(figsize=(10, 4.6), facecolor="white")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.78, bottom=0.16)
    vals = [fb[k]["median"] * 100 for k in labs]
    bars = ax.bar(labs, vals, width=0.58, color=[ORANGE if i == 0 else BLUE for i in range(len(vals))])
    for b, k, v in zip(bars, labs, vals):
        ax.text(b.get_x() + b.get_width() / 2, v - 2, f"{v:.0f}%", ha="center", va="top", color=INK, fontsize=12, weight="bold")
        ax.text(b.get_x() + b.get_width() / 2, 3, f"n={fb[k]['n']} · {fb[k]['share_below_btc']:.0%} lagged BTC", ha="center", fontsize=8.8, color=INK2)
    ax.axhline(0, color="#c3c2b7", lw=1); ax.set_ylim(min(vals) - 14, 14)
    ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); style(ax)
    ax.set_ylabel("Median 90-day return vs BTC", color=INK2, fontsize=9.5)
    ax.set_xlabel("Share of max supply circulating on listing day (float)", color=INK2, fontsize=9.5)
    fig.text(0.03, 0.92, "Low float at listing was the clearest warning sign", fontsize=14, weight="bold", color=INK)
    fig.text(0.03, 0.865, f"{s['n90']} Binance + Coinbase spot listings with 90 days of history (Oct 2025 – Jul 2026)", fontsize=9.5, color=INK2)
    fig.savefig(out / "backtest-float.png", dpi=200); plt.close(fig)

    # 2 — which signals predicted
    names = {"circ_pct": "Float at listing (K02 / K07)", "fdv_mcap": "FDV / market cap (K07)", "vol0": "Listing-day volume*",
             "score": "Composite screening score", "insider_pct": "Insider allocation (K05)", "unlock12": "12-month unlocks (K04)",
             "rev_ann0": "Protocol revenue (B01)", "tvl0": "TVL (O04)"}
    # K07 (FDV/mcap) is the reciprocal of K02 (float), so it is the same signal; show it once.
    sig = [(names[k], v) for k, v in s["signals_event"].items() if "rho" in v and k != "fdv_mcap"]
    sig.sort(key=lambda x: x[1]["rho"])
    fig, ax = plt.subplots(figsize=(10, 4.6), facecolor="white")
    fig.subplots_adjust(left=0.29, right=0.8, top=0.8, bottom=0.13)
    ys = range(len(sig))
    for y, (n, v) in zip(ys, sig):
        strong = v["p"] < 0.05
        ax.barh(y, v["rho"], height=0.56, color=(BLUE if v["rho"] > 0 else ORANGE) if strong else "#d6d5cf")
        ax.text(1.02, y, f"ρ {v['rho']:+.2f}  ·  p={v['p']:.2f}  ·  n={v['n']}", transform=ax.get_yaxis_transform(),
                va="center", fontsize=8.6, color=INK if strong else MUTED)
    ax.set_yticks(list(ys)); ax.set_yticklabels([n for n, _ in sig], fontsize=9.5, color=INK)
    ax.axvline(0, color="#c3c2b7", lw=1); ax.set_xlim(-0.45, 0.45)
    ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True); style(ax)
    ax.set_xlabel("Rank correlation with 90-day return vs BTC (Spearman ρ)", color=INK2, fontsize=9.5)
    fig.text(0.03, 0.93, "Which listing-day signals predicted the next 90 days?", fontsize=14, weight="bold", color=INK)
    fig.text(0.03, 0.875, "Coloured = significant at p < 0.05; grey = no detectable signal at this sample size. "
             "*not yet a DD-100 dimension", fontsize=9, color=INK2)
    fig.savefig(out / "backtest-signals.png", dpi=200); plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "backtest" / "features.csv"))
