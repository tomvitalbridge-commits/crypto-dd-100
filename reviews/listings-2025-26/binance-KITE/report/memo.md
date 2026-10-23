# Listing memo — Kite (KITE)

**Recommendation: ⚪ INSUFFICIENT DATA** · Grade D · 43/100 (range 9–85) · coverage 39% · as of 2025-11-03

| Market cap | FDV | Protocol revenue (ann.) |
|---|---|---|
| $315.0M | $1.8B | $0 |

**The case for**

1. Audit remediation (3/4) — The one High (missing pause controls) was fixed and the other report has no critical/high/medium findings, with three informational items acknowledged; deployed bytecode was not matched to the audited commits.
2. Backer quality & cap table (3/4) — Led by PayPal Ventures and General Catalyst with Coinbase Ventures, Samsung Next, 8VC, Hashed and HashKey; terms are opaque — valuation and token warrants undisclosed — and a market maker (GSR Markets) is on the cap table.
3. Privacy & obfuscation features (4/4) — No privacy features; the design is identity-first (three-tier identity, compliance-ready SPACE framework).

**The case against**

1. Problem clarity & real demand (1/4) — Agent payments is a real problem, but the lead investor calls current agent activity 'very small and experimental' and the PayPal and Shopify integrations are pilots; no paying users are evidenced.
2. Product maturity (1/4) — Mainnet is not live at listing; a public testnet has run since February 2025 and staking, commissions and governance are deferred to mainnet; Binance's own disclaimer says features are still in development.
3. Mint / freeze / blacklist powers (1/4) — No direct mint function, but the contract has owner-gated admin functions (pause/unpause per the ABI; onlyOwner on pause not confirmed from source) and an owner who sets the LayerZero peers whose messages mint supply on other chains; who holds that key is undisclosed.

**What has to be true before we act**

- evidence coverage 39% below the 70% needed for a verdict
- 60 open question(s) for the team are listed in report.md

_Full 100-dimension report: report.md_