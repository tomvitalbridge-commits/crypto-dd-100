---
name: crypto-dd
description: Run a 100-dimension due-diligence review of a crypto project (listing review, investment screen, research report) using the DD-100 harness. Use when asked to evaluate, score, diligence, or write a listing memo / risk assessment for a token, protocol or chain. Produces an evidence pack, cited judgment scores, and a harness-verified report with verdict, score range and red-flag gates.
---

# Crypto project due diligence (DD-100)

You are the research and judgment layer. The `dd100` harness is the
verification and arithmetic layer. Keep them separate: you gather evidence and
make cited judgments; the harness decides what counts, computes the score,
applies the red-flag gates and writes the verdict. You never compute the final
score yourself and never argue with a gate — you either find evidence that
clears it, or you report it.

## The contract

1. **No evidence, no score.** Every judgment cites source ids from the
   evidence pack. If you can't cite it, mark it `status: pending` with what is
   missing. A gap is a finding; a guess is a defect.
2. **Rules are computed, not opined.** For the 37 `rule` dimensions you supply
   the metric; the harness scores it. Don't put scores on them.
3. **Human-only means human-only.** T02 (KYC), M05 (market-maker terms) and
   L07 (legal opinion) need a private channel. Leave them for the analyst and
   list them as open items.
4. **Record what the project claims, separately from what you observe.** Put
   the project's own numbers in `claims`. The harness cross-checks them against
   independent observations and counts contradictions — that is how T10 and
   gate RF10 work. Never "correct" a claim by quietly using it as a metric.
5. **Tier every source honestly.** 1 = primary (on-chain data you queried,
   audit report, signed document); 2 = independent third party (data
   providers, research, press); 3 = project self-reported (docs, decks,
   dashboards, calls). High confidence needs ≥2 sources or a tier-1 source;
   the harness downgrades it otherwise.
6. **Report the range, not just the point.** The score range reflects unscored
   dimensions and low-confidence calls. Lead with the verdict, then the range.

## Workflow

### 0 · Intake (2 minutes)
Get: project name and ticker, chain(s) and core contract addresses, official
docs/tokenomics links, the purpose of the review (listing, investment,
research). Choose the sector profile — `defi`, `l1_l2`, `rwa`, `infra`,
`consumer` (see `config/scoring.yaml`). If ambiguous, ask once.

Create the project folder:

```
projects/<slug>/
  manifest.yaml          # copy examples/halcyon/manifest.yaml and edit
  evidence/
  assessments/
```

Run `dd100 template projects/<slug>` to get a blank assessment sheet with every
judgment dimension, its question and its anchors.

### 1 · Automatic collection
If the manifest has a `collect:` block, run `dd100 collect projects/<slug>/manifest.yaml`
and add `evidence/auto.json` to the manifest. This pulls market data,
TVL/fees/revenue and GitHub activity. Treat it as a starting point; it does not
replace on-chain checks.

### 2 · Research, pillar by pillar → `evidence/research.json`
Work through `references/research-playbook.md`. For each pillar:

- Add every source you use to `sources` with id, tier, type, title, url,
  retrieval date and a short factual `excerpt` (your own words, numbers kept).
- Add every metric in `references/metrics-catalog.md` you can establish to
  `metrics`, each pointing to its source id. Units matter: percentages as
  numbers (38 not 0.38), USD as plain numbers, booleans as true/false.
- Add the project's own quantitative statements to `claims`
  (`metric`, `claimed_value`, `source`).
- The critical gates (RF01–RF05) need `mint_authority`, `sanctions_exposure`,
  `contracts_verified`, `unreimbursed_exploit_usd`, `active_enforcement_action`.
  Until all five are established the verdict cannot be LIST. Prioritise them.

Use `references/red-flag-patterns.md` while researching — it lists what
manipulation, sybil farming and predatory MM deals look like in the data.

### 3 · Judgment → `assessments/agent.yaml`
For each `agent` dimension, read its anchors and score 0–4 (1 and 3 sit
between anchors). Format:

```yaml
- {id: S05, score: 3, confidence: high, evidence: [E04, E13], assessor: "agent:claude",
   rationale: "Upgrades via 5-of-8 Safe + 48h timelock; 3 of 8 signers independent."}
```

Rationales are one or two factual sentences a committee member can check
against the cited source. No adjectives that the evidence doesn't carry.

Calibration: a 4 means best-in-class with proof, not "no problems found".
Absence of information is `pending`, not 2.

### 4 · Run the harness
```
dd100 run projects/<slug>/manifest.yaml
```
Read the console summary and `report/report.md`. Then:

- **Rejected** assessments: fix the cause (add the missing source, move a
  rule-dimension number into metrics). Do not change the score to get it
  accepted.
- **Downgraded** confidence: either find a second or primary source, or
  accept the downgrade.
- **Unchecked critical gates**: go and get those metrics.
- **Fired gates**: re-verify the underlying evidence once. If it holds, the
  gate stands. Do not soften the input.
- Iterate until remaining gaps are genuinely unobtainable from public sources.

### 5 · Deliver
Hand over `report/memo.md` (one page for decision-makers) and `report/report.md`
(full record). In your message, say in plain language:

- the verdict, grade and score range, and what drives the range
- the top 2–3 reasons for and against
- fired gates and what would clear them
- the open questions for the project team (straight from the report)
- any judgment you are least sure of

## Anti-patterns (the harness catches some; you must avoid all)

- Scoring from the project's own deck and calling it high confidence
- Converting "nothing found" into a 4 (absence of incidents ≠ evidence of security)
- Averaging away a red flag in the narrative ("despite the EOA mint, the community is strong…")
- Using total fees as revenue (B01 is revenue retained by the protocol)
- Counting CEX hot wallets, burn addresses or vesting contracts as holders in K03
- Treating announced partnerships as live integrations
- Writing a number in a rationale that is not in a cited source
- Filling human-only dimensions from a Telegram chat with the team

## Files

- `references/research-playbook.md` — where to look, per pillar
- `references/red-flag-patterns.md` — what bad looks like in the data
- `references/metrics-catalog.md` — every metric the harness reads (generated)
- Framework: `framework/dimensions.yaml`, gates: `framework/red_flags.yaml`,
  weights and thresholds: `config/scoring.yaml`
