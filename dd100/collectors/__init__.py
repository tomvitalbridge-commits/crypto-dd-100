"""Automatic evidence collectors.

Each collector reads the `collect:` block of a project manifest, calls ONE
public data source, and returns a partial evidence pack (sources + metrics).
Collectors never score anything — they only fetch and label provenance.

Collectors that need a key (block explorers, Nansen, Arkham, Kaiko, Chainalysis)
are left as documented extension points: see docs/ARCHITECTURE.md.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.request
from typing import Any, Callable

Partial = dict[str, Any]
REGISTRY: dict[str, Callable[[dict[str, Any]], Partial]] = {}
UA = {"User-Agent": "dd100/0.1 (+https://github.com/)"}


def collector(key: str):
    def wrap(fn):
        REGISTRY[key] = fn
        return fn
    return wrap


def _get(url: str, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _today() -> str:
    return dt.date.today().isoformat()


@collector("coingecko_id")
def coingecko(cfg: dict[str, Any]) -> Partial:
    cid = cfg["coingecko_id"]
    url = (f"https://api.coingecko.com/api/v3/coins/{cid}?localization=false&tickers=false"
           f"&community_data=false&developer_data=false")
    d = _get(url)["market_data"]
    src = "AUTO-CG"
    metrics = {}
    for name, value in (
        ("market_cap_usd", d.get("market_cap", {}).get("usd")),
        ("fdv_usd", d.get("fully_diluted_valuation", {}).get("usd")),
        ("volume_24h_usd", d.get("total_volume", {}).get("usd")),
        ("circulating_supply", d.get("circulating_supply")),
        ("total_supply", d.get("total_supply") or d.get("max_supply")),
    ):
        if value:
            metrics[name] = {"value": value, "source": src}
    return {"sources": [{"id": src, "type": "api", "tier": 2, "title": f"CoinGecko market data: {cid}",
                         "url": f"https://www.coingecko.com/en/coins/{cid}", "retrieved": _today()}],
            "metrics": metrics}


@collector("defillama_slug")
def defillama(cfg: dict[str, Any]) -> Partial:
    slug = cfg["defillama_slug"]
    src_tvl, src_fees = "AUTO-DL-TVL", "AUTO-DL-FEES"
    out: Partial = {"sources": [], "metrics": {}}
    proto = _get(f"https://api.llama.fi/protocol/{slug}")
    tvl_series = proto.get("tvl") or []
    if tvl_series:
        out["metrics"]["tvl_usd"] = {"value": round(tvl_series[-1]["totalLiquidityUSD"]), "source": src_tvl}
        out["sources"].append({"id": src_tvl, "type": "api", "tier": 2, "title": f"DefiLlama TVL: {slug}",
                               "url": f"https://defillama.com/protocol/{slug}", "retrieved": _today()})
    try:
        fees = _get(f"https://api.llama.fi/summary/fees/{slug}?dataType=dailyFees")
        rev = _get(f"https://api.llama.fi/summary/fees/{slug}?dataType=dailyRevenue")
        if fees.get("total30d"):
            out["metrics"]["annualized_fees_usd"] = {"value": round(fees["total30d"] * 365 / 30), "source": src_fees}
        if rev.get("total30d"):
            out["metrics"]["annualized_revenue_usd"] = {"value": round(rev["total30d"] * 365 / 30), "source": src_fees}
        out["sources"].append({"id": src_fees, "type": "api", "tier": 2, "title": f"DefiLlama fees/revenue: {slug}",
                               "url": f"https://defillama.com/fees/{slug}", "retrieved": _today()})
    except Exception:  # fees adapters do not exist for every protocol
        pass
    return out


@collector("github_org")
def github(cfg: dict[str, Any]) -> Partial:
    org = cfg["github_org"]
    since = (dt.datetime.utcnow() - dt.timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    repos = _get(f"https://api.github.com/orgs/{org}/repos?per_page=100&sort=pushed")
    repos = [r for r in repos if not r.get("fork") and not r.get("archived")][: cfg.get("github_max_repos", 15)]
    commits, authors = 0, set()
    for r in repos:
        if r.get("pushed_at", "") < since:
            continue
        page = _get(f"https://api.github.com/repos/{org}/{r['name']}/commits?since={since}&per_page=100")
        commits += len(page)
        authors.update((c.get("author") or {}).get("login") or c["commit"]["author"]["email"] for c in page)
    src = "AUTO-GH"
    return {"sources": [{"id": src, "type": "github", "tier": 1, "title": f"GitHub org {org} (90d, up to 100 commits/repo)",
                         "url": f"https://github.com/{org}", "retrieved": _today()}],
            "metrics": {"github_commits_90d": {"value": commits, "source": src,
                                               "note": "lower bound: capped at 100 commits per repo"},
                        "github_active_contributors_90d": {"value": len(authors), "source": src}}}


def collect_all(cfg: dict[str, Any]) -> tuple[Partial, list[str]]:
    merged: Partial = {"sources": [], "metrics": {}}
    errors = []
    for key, fn in REGISTRY.items():
        if key not in cfg:
            continue
        try:
            part = fn(cfg)
        except Exception as e:  # report, don't swallow
            errors.append(f"{fn.__name__}: {e}")
            continue
        merged["sources"] += part["sources"]
        merged["metrics"].update(part["metrics"])
    return merged, errors
