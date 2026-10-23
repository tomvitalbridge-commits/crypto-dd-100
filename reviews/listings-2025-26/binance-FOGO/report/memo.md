# Listing memo — Fogo (FOGO)

**Recommendation: ⚪ INSUFFICIENT DATA** · Grade D · 48/100 (range 18–82) · coverage 54% · as of 2026-01-15

| 12m unlocks / circ. |
|---|
| 23.6% |

**The case for**

1. Founder track record (3/4) — Colkitt built Ambient Finance (ex-Citadel quant); Sagurton ran digital-asset sales at Jump Crypto; engineering comes from Douro Labs, the team behind Pyth and Pythnet. Outcomes of Ambient were not established from these sources.
2. Controversies & misconduct history (3/4) — No enforcement or misconduct found; public criticism concerns pricing (the $1B-FDV presale called 'extractive', cancelled within two days) and raising on forked code, not conduct.
3. Mint / freeze / blacklist powers (3/4) — Native token with no mint key; issuance is a fixed 2% a year set in the client. Supply is not fixed, and the BSC token used for the Prime Sale was not checked.

**The case against**

1. Audit remediation (1/4) — The only audit found covers upstream Firedancer v0.1 for Jump (2 highs, Agave runtime out of scope); Fogo's own modifications and the Sessions programs have no public audit.
2. Admin key custody (1/4) — A genesis authority curates the validator set, and protocol changes ship as client releases from the Foundation-funded team; no on-chain timelock or independent signer set is documented.
3. Moat (1/4) — The only edge is latency from validator co-location and Firedancer; Solana is adopting the same client (~21% of stake), and no retention has been shown.
4. Claim contradicted: December tokenomics: institutional investors (Distributed Global, CMS Holdings) hold 8.77% of supply vs observed 12.06 (27% gap)

**Gates**

- 🚩 RF09 No independent audit (major)

**What has to be true before we act**

- evidence coverage 54% below the 70% needed for a verdict
- 48 open question(s) for the team are listed in report.md

_Full 100-dimension report: report.md_