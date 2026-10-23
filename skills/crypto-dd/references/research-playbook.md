# Research playbook — where to look, per pillar

Source types in brackets are the `type` field to use in the evidence pack.
Tier: 1 primary · 2 independent · 3 self-reported.

## T · Team & Governance
- Founder history: LinkedIn and conference talks (3), prior company filings and press (2), GitHub history of named engineers (1). Look for the *outcome* of prior ventures, not titles.
- Misconduct: court-record databases, regulator enforcement pages (SEC, CFTC, FCA, MAS, SFC), OFAC/EU sanctions lists (2/1). Wallet history of deployer and team addresses for links to past rugs (1).
- Vesting: vesting contract addresses from the tokenomics page, then read them on-chain (1). The page itself is tier 3.
- Governance: Governor/Snapshot proposals, quorum, voter concentration (1). Check who the top delegates are.
- Treasury: published treasury addresses reconciled against the treasury report (1 vs 3). A mismatch is a claim to record.

## P · Product & Technology
- Maturity: mainnet deployment dates from contract creation blocks (1), not from blog posts.
- Originality: diff the contracts against the obvious parent repo; check commit history for "forked from" (1).
- Activity: GitHub commits and contributors over 90 days (collector), excluding bots and dependency bumps.
- Delivery record: past roadmap posts vs release tags (3 vs 1).
- Reproducibility: does a tagged commit compile to deployed bytecode? (1)

## S · Security & Smart Contracts
- Audits: read the reports, not the logo list (1). Note scope, date, commit hash, open findings. Count only reputable firms covering the *deployed* code.
- Admin powers: on-chain owner/role holders, proxy admin, timelock min delay, multisig threshold and signer identities (1).
- Mint/freeze: read the token contract — mint functions, role holders, pause/blacklist (1). Set `mint_authority` to `eoa`, `multisig`, `timelocked_multisig`, `governance` or `renounced`.
- Incidents: rekt-style incident databases and post-mortems (2), reimbursement transactions (1). Set `unreimbursed_exploit_usd`.
- Oracles: which feeds, fallbacks, deviation checks; liquidity of the pools any TWAP reads from (1).

## K · Tokenomics & Supply
- Supply: total/circulating from contracts and vesting schedules (1), cross-checked with data providers (2).
- Concentration (K03): top-10 holders excluding exchange wallets, burn, bridges, staking and vesting contracts. Label every top-20 address.
- Unlocks: next 12 months and next 90 days as % of *current circulating* supply. Include ecosystem/treasury unlocks that can be sold.
- Investor overhang: last private round price vs current price (cap table under NDA is 3; a priced round reported by press is 2).

## O · On-chain Traction
- Activity, retention, fee payers: your own queries on an indexer (1). Provider dashboards are 2. The project's dashboard is 3.
- Sybil analysis: cluster active addresses by funding source and timing; look at activity before vs after incentive windows.
- TVL: independent aggregator (2); compute share of TVL in pools with active emissions for O05.

## M · Market Structure & Liquidity
- Depth and spread: order-book snapshots across venues, averaged over at least 7 days (2).
- Wash trading: volume/depth ratio vs sector peers, trade-size distribution, venue concentration, CEX volume vs on-chain transfer flows.
- MM arrangements: only from the project under NDA (human-only, M05). Ask for token loan size, call-option strikes and terms, KPIs.
- Perps: open interest relative to spot depth, funding history.

## B · Business Model & Fundamentals
- Revenue: protocol-retained revenue, not total fees (2, verified against treasury inflows 1). Annualise from 90 days.
- Incentives: USD value of emissions over the same window (1).
- Runway: non-native treasury at full value + native token at 50%, divided by monthly burn.

## C · Competition & Moat
- Category share and trajectory: aggregator category pages, two quarters (2).
- Relative valuation: FDV/fees, FDV/TVL against 3–5 named peers.
- Moat test: what happened to share when a competitor ran an incentive campaign?

## D · Community & Distribution
- Social analytics for engagement rate and bot likelihood (2). Follower counts alone are noise.
- Paid promotion: disclosed campaigns, KOL wallet receipts of tokens (1).
- Holders: non-dust holder count from an indexer (1).

## L · Legal, Compliance & Jurisdiction
- Entity: corporate registries (1).
- Securities analysis: the token's marketing (3) and the legal opinion if shared (human-only L07).
- Sanctions/AML: wallet screening of treasury, team, deployer and top holders (2). Set `sanctions_exposure` true when exposure exceeds your tolerance.
- Enforcement: regulator pages and court records (1/2). Set `active_enforcement_action`.
- RWA (profile `rwa`): custodian, SPV/trust documents, attestation reports and their frequency.
