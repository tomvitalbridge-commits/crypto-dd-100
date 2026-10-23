# Listing backtest data

- `features.csv`: one row per listing event (exchange × token), with every input
  metric as of the listing day, plus prices 30 and 90 days later and on
  2026-10-23. Collected by `scripts/collect_listings.js` from public, keyless APIs
  (Binance, Coinbase, CoinGecko, DefiLlama) on 2026-10-23.
- `results.csv`: features plus the DD-100 screening score, rule-dimension scores,
  fired gates, and returns relative to BTC (`x30`, `x90`, `xlast`).
- `summary.json`: every statistic quoted in `docs/BACKTEST.md`.

Regenerate `results.csv`, `summary.json` and the charts with
`python scripts/backtest.py data/backtest/features.csv`. The per-event evidence
packs and manifests go to `runs/`, which is git-ignored because it can be
regenerated.
