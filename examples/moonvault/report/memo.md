# Listing memo — Moonvault (MVLT)

**Recommendation: 🔴 REJECT** · Grade F · 19/100 (range 4–69) · coverage 45% · as of 2026-10-20

| Market cap | FDV | 24h volume | ±2% depth | Protocol revenue (ann.) | 12m unlocks / circ. | Top-10 holders |
|---|---|---|---|---|---|---|
| $95.0M | $610.0M | $48.0M | $90.0K | $2.1M | 290.0% | 62.0% |

**The case for**

1. Source verification (4/4) — contracts_verified = true
2. Daily active addresses (30d avg) (3/4) — daa_30d_avg = 31,000

**The case against**

1. Audit remediation (0/4) — Only high finding left unfixed; game contracts never audited.
2. Admin key custody (0/4) — A single EOA holds owner rights over the token and all game proxies.
3. Mint / freeze / blacklist powers (0/4) — Owner can mint unlimited MVLT; auditor flagged it, team kept it 'by design'.
4. Claim contradicted: Deck: "250,000 daily players" vs observed 31,000 (706% gap)
5. Claim contradicted: Deck: "2M+ holders" vs observed 48,000 (4067% gap)

**Gates**

- 🚩 RF01 Unrestricted mint controlled by a single key (critical)
- 🚩 RF06 Upgradeable contracts with no meaningful timelock (major)
- 🚩 RF07 Extreme holder concentration (major)
- 🚩 RF08 Unlock cliff within 90 days (major)
- 🚩 RF09 No independent audit (major)
- 🚩 RF10 Material misrepresentation (major)
- 🚩 RF11 Security pillar failing (major)

**What has to be true before we act**

- critical gate RF01: Unrestricted mint controlled by a single key
- 65 open question(s) for the team are listed in report.md

_Full 100-dimension report: report.md_