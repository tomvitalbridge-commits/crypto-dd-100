# What bad looks like in the data

Use these while researching. Each pattern says what to measure and which
dimension or gate it feeds.

## Supply & control
- **Owner mint left "for rewards".** A mint function callable by an EOA or a
  low-threshold multisig, justified as game or ecosystem rewards. → S06, RF01.
- **Proxy without delay.** UUPS/transparent proxy whose admin can upgrade in
  the same block. → S04, RF06.
- **Vesting on paper only.** Allocations described in a deck but held in plain
  wallets rather than vesting contracts. → K09; recompute K04 assuming they can sell.
- **Same-funder top holders.** Several "independent" top wallets funded from one
  address near deployment. Treat them as one holder. → K03, RF07.

## Activity & traction
- **Campaign-shaped activity.** Daily actives that rise and fall with points or
  quest campaigns; retention collapses after claim. → O02, O03, O06, K10.
- **Funding clusters.** A large share of active addresses funded by a handful of
  sources, often via the same CEX withdrawal pattern. → O06.
- **Looped TVL.** Deposits funded by borrowing the protocol's own token, or TVL
  concentrated in pools with outsized emissions. → O05, B02, RF15.
- **Dashboard vs chain.** The project's dashboard shows numbers that your own
  query cannot reproduce. Record the dashboard figure as a claim. → T10, RF10.

## Markets
- **Volume without depth.** Daily volume far above ±2% depth (well beyond
  sector peers), especially concentrated on one venue. → M01, M02, M03, RF16.
- **Round-lot and self-trade prints.** Repeated identical trade sizes at regular
  intervals; prints with no change in the book. → M03.
- **Predatory MM terms.** Large token loans with low-strike call options,
  volume KPIs, or a "launch support" fee paid in tokens. These create an
  incentive to sell into listing demand. → M05, RF13.
- **Unlock-timed listings.** Listing requested shortly before a cliff; check the
  calendar against the listing date. → K04, RF08.

## Disclosure
- **Logo walls.** Partner logos with no observable on-chain flows. → C09.
- **Audit theatre.** Audit of the token contract only, or of an old commit, cited
  as "fully audited". → S01, S02, RF09.
- **Silent edits.** Docs or tokenomics pages changed without changelog (check
  archived versions). → D08, T10.
- **Revenue relabelling.** Total fees presented as revenue, or treasury token
  sales presented as income. → B01, B02.

## Legal
- **Profit-expectation marketing.** Price, yield or "number go up" language from
  official channels, combined with team control. → L02.
- **Geofence theatre.** Front end blocks restricted countries but incentives,
  airdrops and APIs do not. → L10.
