# Backtest: one year of Binance and Coinbase listings

**Question.** If DD-100 had screened every token Binance and Coinbase listed
for spot trading in the last 12 months, using only data available on the day
of listing, would its score have told you anything about what happened next?

**Short answer.** The base rate is brutal: **85% of new listings lagged BTC
over the following 90 days**, with a median 34 points of underperformance. The
composite screening score, built from free public data, carried only a weak
signal that was not statistically significant. One input inside it did
predict returns: **float at listing**, meaning the share of total supply
actually circulating. A second signal that is not yet in the framework also
did: **listing-day trading volume**. Unlock schedules, insider share, revenue
and TVL showed no detectable signal at this sample size.

![Float at listing vs 90-day return](img/backtest-float.png)

## Sample

| | |
|---|---|
| Window | Listings from 23 Oct 2025 to 21 Oct 2026; prices through 23 Oct 2026 |
| Events | **120**: 29 Binance spot listings, 91 Coinbase USD listings |
| With 90 days of history | 105 events, 89 unique tokens (16 tokens listed on both exchanges) |
| Outcome | Token return ÷ BTC return − 1, from the listing-day close, measured on the same exchange's daily candles |
| Excluded | Stablecoins, tokenised stocks, gold tokens |

How the listings were identified:

- **Binance**: from its *New Cryptocurrency Listing* announcements (spot
  listings, HODLer Airdrops, Launchpool). Each listing date was confirmed by
  the token's first daily candle.
- **Coinbase**: every USD product whose first daily candle falls inside the
  window.

Each token was matched to CoinGecko, and the match was accepted only if
CoinGecko's price was within 25% of the exchange's own last close. All 120
passed.

## What the screening could see

On listing day, free public data could fill only a handful of the 37
rule-based dimensions:

| Dimension | Metric | Events covered |
|---|---|---:|
| K02 Circulating ratio | supply at listing ÷ max supply | 119 |
| K07 FDV / market cap | the reciprocal of K02 | 119 |
| K04 12-month unlock pressure | DefiLlama documented unlock schedule | 42 |
| K05 Insider allocation | DefiLlama schedule categories | 42 |
| O04 TVL | DefiLlama, last point before listing | 23 |
| B01 Protocol revenue | DefiLlama, 30 days before listing, annualised | 27 |
| B04 FDV / fees | derived | 30 |
| B08 Revenue growth | DefiLlama, quarter on quarter | 20 |

The median event had **2 scored dimensions out of 100**. Every event
therefore came out `INSUFFICIENT_DATA` as a verdict, which is the harness
working as designed. The backtest uses the point score: the same framework,
weights and thresholds as everywhere else in this repo, with **no tuning to
this sample**.

## Results

![Signal strength](img/backtest-signals.png)

| Signal (rank correlation with 90-day return vs BTC) | Events (n=105) | Unique tokens (n=89) |
|---|---|---|
| Composite screening score | ρ +0.12, p=0.22 | ρ +0.15, p=0.15 |
| Float at listing (K02; K07 is the same signal inverted) | **ρ +0.23, p=0.02** | **ρ +0.26, p=0.01** |
| Listing-day volume (not a DD-100 dimension) | **ρ −0.25, p=0.01** | **ρ −0.30, p<0.01** |
| 12-month unlocks, insider share, revenue, TVL | \|ρ\| ≤ 0.12, n=24–38, not significant | |

**Float.** Every one of the 9 tokens that listed with under 15% of supply
circulating lagged BTC, by a median of 74%. Tokens with more than 40% float
lagged by a median of 21%, and 30% of them beat BTC. The effect is stronger
(ρ +0.42, p<0.01, n=38) in the cleanest subset, where supply at listing comes
from the documented unlock schedule rather than today's circulating figure.
It holds in the same direction on both exchanges.

**Listing-day volume.** The tokens that traded most on day one did worst
afterwards. The median 90-day return vs BTC was −20% for the lowest-volume
third and −49% / −40% for the middle and top thirds. Within Coinbase alone,
ρ = −0.35 (p<0.01). One plausible reading is that heavy day-one volume is
airdrop and points-farming supply leaving. That makes it a candidate new
dimension, but this sample only shows correlation.

**Composite score.** Splitting the score into thirds gave medians of −33%,
−46% and −26%, which is not monotonic. With two dimensions doing almost all
the work, the composite mostly re-expresses float, diluted by noise from
sparsely covered metrics.

## What this means for DD-100

1. **The screening layer is not enough on its own.** Two metrics on listing
   day cannot separate good listings from bad ones well. This argues for the
   full review: the judgment and human-only dimensions are where the
   information is, and they are what a listing team adds.
2. **Float deserves more weight at screening time.** A fair change would be a
   red-flag gate for float under 15% at listing (9 of 9 lagged BTC). It is
   **not applied here**, because changing thresholds on the same sample that
   motivated them would overfit. The proper test is the next 12 months of
   listings.
3. **Add a hype dimension.** Listing-day volume relative to float or market
   cap is cheap to measure and carried signal here.
4. **Unlocks need better data, not a different weight.** DefiLlama documents
   schedules for only about a third of new tokens. The null result for K04/K05
   says more about coverage (n=38) than about whether unlocks matter.

## Caveats

- **Small sample, one regime.** 105 events in a year when BTC fell from about
  $110k to below $60k and ended near $82k. Nothing here has been tested out of sample.
- **Look-ahead in supply.** For 77 of 120 events, no documented schedule
  existed, so "supply at listing" uses CoinGecko's *current* circulating
  supply. Supply only grows, so this overstates float at listing for those
  tokens. The schedule-only subset, which has no look-ahead, shows a stronger
  float effect, not a weaker one.
- **Listing date ≠ token launch.** Some Coinbase listings were mature tokens
  (TON, RAY, HYPE, VIRTUAL). Others were day-one launches. The two are pooled.
- **Exchange volume is not comparable across venues.** Binance day-one volume
  is roughly 40× Coinbase's (median), so the volume signal should be read within each
  exchange.
- **Survivorship.** Coinbase products delisted before 23 Oct 2026 that were
  also listed inside the window would be missing. None were found.
- **Correlation, not a trading strategy.** Returns are close-to-close on
  daily candles, before fees and slippage.

## Reproduce

```bash
python scripts/backtest.py data/backtest/features.csv   # scores, summary.json, charts
```

- `data/backtest/features.csv`: one row per listing event, every input metric.
- `data/backtest/results.csv`: adds the screening score, the dimension scores,
  fired gates and outcomes.
- `data/backtest/summary.json`: every number quoted on this page.
- `scripts/collect_listings.js`: how the features were collected (public,
  keyless APIs: Binance, Coinbase, CoinGecko, DefiLlama).
