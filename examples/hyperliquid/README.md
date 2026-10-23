# Case study: Hyperliquid (HYPE), a real listing, public data only

Binance listed HYPE for spot trading on **24 Sep 2026**, with the pairs
HYPE/USDT, HYPE/USDC and HYPE/TRY. It carried a **Seed Tag**, which flags higher
risk and requires users to pass a quiz every 90 days. This folder runs the same
review from the outside, as of **23 Oct 2026**, using only sources anyone can
check: 61 sources, each cited by id.

```
Hyperliquid (HYPE)  ·  🟡 CONDITIONAL  ·  grade B  ·  66.0/100 (range 41–81)  ·  coverage 82%
  ❔ RF02 [critical] Sanctions / illicit-finance exposure — unchecked
  ❔ RF06 [major] Upgradeable contracts with no meaningful timelock — unchecked
  ❔ RF07 [major] Extreme holder concentration — unchecked
  🚩 RF16 [minor] Volume implausible versus depth — fired
```

[One-page memo](report/memo.md) · [Full report](report/report.md) · [Radar](report/radar.svg)

## How this compares with what Binance did

DD-100 says **conditional**: the score clears the listing bar, but the listing
is blocked until a critical gate and three private checks are closed. Binance
listed, but with a Seed Tag rather than as a standard listing, about 16 months
after it listed HYPE perpetuals (May 2025). Reaching a similar answer from
public data alone is a sanity check on the framework. It is not proof the
framework is right.

The score sits **one point above the B line**. A single judgment moved by one
step would make it a C. That is why the report leads with the range (41–81),
not the point.

## What drives the result

The radar shape is the story. The business is strong. Control, security and
legal standing are weak.

| Strong | Weak |
|---|---|
| Real demand: $212B in 30-day perp volume and $907M in annualised fees, with **zero** usage incentives | **Control:** 5 Foundation validators hold about 49% of stake; one closed-source client; no token-holder vote |
| All revenue goes to holders: $1.36B of on-chain buybacks to date | **Security coverage:** the only public audits (Zellic, 2023) cover the legacy bridge, not the L1 that holds most of the ~$8.4B TVL |
| No private investors, so no VC unlock overhang | **Licensing:** retail leverage up to 40× with no licence; UK FCA warning, MAS investor alert, US House Oversight records request |
| Category leader: 57.5% of perp-DEX open interest | **Supply:** contributor unlocks could add up to 53.5% of circulating supply in 12 months at the contractual ceiling (about 20% at the current claim pace) |
| Regained volume share after the late-2025 Lighter/Aster surge, without incentives | **Manipulation:** thin markets were exploited repeatedly (JELLY, XPL, POPCAT); HLP took the losses |

## The verification layer caught a wrong gate

The first run said **WATCHLIST, grade C**. Major gate RF06 fired because a
research note said that L2BEAT calls the bridge "instantly upgradable".

An independent fact-check could not find that wording on L2BEAT. Reading
`Bridge2.sol` directly showed the contract is **not upgradeable**: it has no
proxy and no admin, and only validator signatures can change it.

The L1 does upgrade through validator-adopted binaries. No source documents how
much notice users get, and *not documented* is not *zero*. So the metric is
left unset, RF06 shows as **unchecked**, and the question goes to the team.
The verdict moved to CONDITIONAL.

The same pass corrected four smaller errors:
- revenue is buybacks **plus** reserve yield and burns
- there are **two** Zellic reports, not one
- the Lazarus flows were about $30M in **Aug** 2026
- the ETF dates

This is the pipeline doing its job. A judgment that rests on a source has to
survive a re-read of that source.

## What an insider would close next

Everything left open is listed in the report. Most of it can be closed with
data an exchange already has:

1. **RF02 sanctions exposure.** Screen the Assistance Fund, team, staking and
   top-holder addresses with the exchange's own Chainalysis/TRM tooling. Public
   reports show about $30M of Lazarus-linked flows through the venue.
2. **K03 / RF07 holder concentration.** Label the top holders with internal
   entity data. Public explorers didn't render for this review.
3. **S04 / RF06.** Ask the team what notice users get before a protocol upgrade
   takes effect.
4. **M05 market makers, T02 KYC, L07 legal opinion.** These are human-only. The
   team says it has no paid market makers. That claim is worth confirming.
5. **D04 user geography.** Use the exchange's own deposit and withdrawal data.

## Limits

- All market data is a snapshot from 21–23 Oct 2026, and sources disagree
  slightly. For example, circulating supply is 222M on CoinGecko and 254M on
  CoinMarketCap. Each metric's source and caveats are in `evidence/*.json`.
- RF16 fired because reported 24h volume ($829M across 83 markets) is set
  against depth measured on only 4 venues. M03 explains this rather than hiding
  it.
- GitHub activity scores 0 because core development is private. That is
  accurate for what can be verified, and it is why P09 (open source) is the
  more meaningful score.
- This is an outside-in research exercise, not investment advice, and not a
  statement of Binance's reasoning.
