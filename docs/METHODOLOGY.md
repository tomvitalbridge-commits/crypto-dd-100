# Methodology

## What problem this solves

Listing and investment committees see hundreds of projects a quarter. The
failure modes are well known and mostly not about missing information:

1. **Averaging away a fatal flaw.** A great team and a hot narrative "outscore"
   an EOA that can mint unlimited supply.
2. **Self-reported numbers treated as facts.** Deck metrics flow straight into
   the memo.
3. **False precision.** "Score: 73.4" hides that a third of it was guessed.
4. **Inconsistent depth.** Two analysts diligence two projects to different
   standards, and the committee can't tell.
5. **Unaccountable AI output.** An LLM writes a fluent memo whose claims cannot
   be traced to anything.

DD-100 is built around those five failures.

## Design principles

| Principle | Mechanism |
|---|---|
| Red flags don't average out | 16 gates evaluated after scoring; critical → REJECT regardless of score, major → grade capped at C |
| Absence of evidence ≠ evidence of absence | Gates are tri-state; an unchecked critical gate blocks LIST |
| No evidence, no score | Judgments without valid citations are rejected, not repaired |
| Claims are not facts | Project claims are stored separately and cross-checked against independent sources of equal or better tier |
| Honest uncertainty | Every score ships with coverage and a range; low confidence widens it |
| Separation of judgment and arithmetic | The skill/LLM/analyst produces cited judgments; deterministic code validates, scores, gates and decides |
| Some things need a human | T02, M05, L07 cannot be filled by an agent |
| Methodology as data | All thresholds, weights and gates live in YAML; code contains none |

## Scoring

**Dimension.** Integer 0–4. Rule dimensions map a metric through four
thresholds `[t4, t3, t2, t1]`. Judgment dimensions use anchors at 0, 2, 4.

**Pillar.** Weighted mean of *scored* dimensions (weights 1–3). Coverage =
scored weight / applicable weight. Below 60% coverage the pillar is flagged.

**Point score.** Profile-weighted mean of pillar scores, scaled to 0–100.
Pillars with nothing scored are excluded rather than counted as zero.

**Range.** For the low end every scored dimension drops by its confidence
radius (high 0.25, medium 0.75, low 1.5) and every unscored dimension counts as
0; for the high end they rise by the radius and unscored count as 4. A narrow
range means the committee can trust the point score; a wide one means "go get
more evidence".

**Grade.** A ≥ 80, B ≥ 65, C ≥ 50, D ≥ 35, else F.

**Verdict.**

```
critical gate fired                          → REJECT
coverage < 70%                               → INSUFFICIENT_DATA
major gate fired                             → grade capped at C
grade < C                                    → REJECT
grade ≥ B, and no major gates, all critical
  gates verified, all human checks closed    → LIST
grade ≥ B but something above is open        → CONDITIONAL
otherwise                                    → WATCHLIST
```

## Confidence and source tiers

| Tier | Meaning | Examples |
|---|---|---|
| 1 | Primary | Your own on-chain query, contract state, audit report, signed document, KYC record |
| 2 | Independent third party | Data aggregators, order-book data vendors, screening providers, press |
| 3 | Project self-reported | Docs, decks, dashboards, calls with the team |

Rule scores inherit confidence from their metric's source tier. Judgment
scores claimed as `high` need two sources or one tier-1 source; otherwise the
harness downgrades them and says so in the report.

A project claim is contradicted when an observation from a *different* source
of equal or better tier differs by more than 20%. One contradiction lowers T10;
two or more fire RF10.

## Sector profiles

The same 100 questions apply to every project, but not with the same weight.
An RWA issuer lives or dies on legal structure (L = 18%), an L1 on technology
and tokenomics. Profiles also mark dimensions that don't apply (TVL for a
consumer app; custody for a DEX). See `config/scoring.yaml`.

## Known limitations

- Thresholds are starting points calibrated on judgment, not fitted to a
  labelled history of listings. The right next step is back-testing against
  past listings and their 6- and 12-month outcomes, then tuning the bands.
- Rule dimensions are only as good as the metric definitions. K03 in particular
  depends on correctly labelling exchange, bridge and vesting addresses.
- The collectors cover free public APIs. Order-book depth, wallet screening and
  entity labelling need paid data sources (see ARCHITECTURE.md).
- The framework scores a snapshot. Post-listing monitoring means re-running it
  on a schedule and diffing results.
