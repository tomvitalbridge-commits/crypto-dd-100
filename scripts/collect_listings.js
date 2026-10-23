// Data collection for the listing backtest (docs/BACKTEST.md).
//
// Runs in a browser console on https://api.coingecko.com/api/v3/ping (any page
// whose origin can reach the public APIs below). It was run that way because
// the build environment could not reach these hosts directly. Everything here
// is a free, keyless, public endpoint. Output: window._csv (features.csv).
//
// Steps
//  1. Binance listings: "New Cryptocurrency Listing" announcements (catalog 48),
//     titles "Binance Will List …", "… HODLer Airdrops", "… Launchpool".
//     Stablecoins, tokenised stocks and gold were excluded by hand.
//     Listing date = first daily kline on data-api.binance.vision.
//  2. Coinbase listings: every USD product; listing date = first daily candle.
//  3. CoinGecko id per token (symbol + name match), validated by requiring the
//     CoinGecko price to sit within 25% of the exchange's last close.
//  4. Prices: exchange daily candles from listing day to 2026-10-23; BTC from
//     the same exchange. p0 = close of the first trading day.
//  5. Supply at listing: DefiLlama documented unlock schedule where available
//     ("llama_schedule"); otherwise CoinGecko's current circulating supply
//     ("coingecko_now" — see the look-ahead caveat in docs/BACKTEST.md).
//  6. TVL / fees / revenue at listing: DefiLlama history up to the listing day.

const sleep = ms => new Promise(s => setTimeout(s, ms));
const day = ms => new Date(ms).toISOString().slice(0, 10);
const J = async u => { try { const r = await fetch(u); return r.status === 200 ? r.json() : null; } catch { return null; } };
const START = '2025-10-23', END = '2026-10-23';

async function binanceAnnouncements() {
  const out = [];
  for (let p = 1; p <= 40; p++) {
    const r = await J(`https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=${p}&pageSize=50`);
    const a = r?.data?.catalogs?.[0]?.articles || [];
    out.push(...a);
    if (!a.length || day(a[a.length - 1].releaseDate) < START) break;
    await sleep(300);
  }
  return out.filter(a => day(a.releaseDate) >= START &&
    /Binance Will List|HODLer Airdrops|Launchpool/i.test(a.title) &&
    !/Futures|bStocks|Margin|Pre-Market|Alpha Points/i.test(a.title));
}

async function binanceFirstDay(sym) {
  let first = null;
  for (const q of ['USDT', 'USDC', 'FDUSD', 'TRY', 'BNB']) {
    const k = await J(`https://data-api.binance.vision/api/v3/klines?symbol=${encodeURIComponent(sym + q)}&interval=1d&startTime=0&limit=1`);
    if (k?.length) { const d = day(k[0][0]); if (!first || d < first) first = d; }
  }
  return first;
}

async function coinbaseListings() {
  const prods = await J('https://api.exchange.coinbase.com/products');
  const out = [];
  for (const p of prods.filter(p => p.quote_currency === 'USD')) {
    const w1 = await J(`https://api.exchange.coinbase.com/products/${p.id}/candles?granularity=86400&start=2025-09-23T00:00:00Z&end=2026-07-19T00:00:00Z`);
    let first = Array.isArray(w1) && w1.length ? Math.min(...w1.map(c => c[0])) : null;
    if (first === null) {
      const w2 = await J(`https://api.exchange.coinbase.com/products/${p.id}/candles?granularity=86400&start=2026-07-19T00:00:00Z&end=${END}T00:00:00Z`);
      if (Array.isArray(w2) && w2.length) first = Math.min(...w2.map(c => c[0]));
    }
    if (first && day(first * 1000) >= START) out.push({ ex: 'coinbase', sym: p.base_currency, date: day(first * 1000) });
    await sleep(130);
  }
  return out;
}

// Daily candles normalised to [date, high, close, usdVolume], ascending.
async function candles(ex, sym, from) {
  let rows = [];
  if (ex === 'coinbase') {
    for (let s = Date.parse(from); s < Date.parse(END);) {
      const e = Math.min(s + 299 * 864e5, Date.parse(END));
      const c = await J(`https://api.exchange.coinbase.com/products/${sym}-USD/candles?granularity=86400&start=${new Date(s).toISOString()}&end=${new Date(e).toISOString()}`);
      if (Array.isArray(c)) rows.push(...c.map(x => [day(x[0] * 1000), x[2], x[4], x[5] * x[4]])); // [t, low, high, open, close, vol]
      s = e; await sleep(150);
    }
  } else {
    const k = await J(`https://data-api.binance.vision/api/v3/klines?symbol=${encodeURIComponent(sym + 'USDT')}&interval=1d&startTime=${Date.parse(from)}&limit=1000`);
    rows = (k || []).map(x => [day(x[0]), +x[2], +x[4], +x[7]]);
  }
  const seen = new Set();
  return rows.filter(x => !seen.has(x[0]) && seen.add(x[0])).sort((a, b) => a[0].localeCompare(b[0])); // Coinbase returns newest first
}

// DefiLlama: TVL / fees / revenue history and documented unlock schedule for a CoinGecko id.
async function llama(cgId, protosByGecko, chainsByGecko, emissionsSlugByGecko) {
  const out = {};
  const ps = (protosByGecko[cgId] || []).sort((a, b) => (b.tvl || 0) - (a.tvl || 0));
  if (ps.length) {
    out.category = ps[0].category;
    const pr = await J(`https://api.llama.fi/protocol/${ps[0].slug}`);
    if (pr?.tvl) out.tvl = pr.tvl.map(x => [x.date, x.totalLiquidityUSD]);
    for (const t of ['dailyFees', 'dailyRevenue']) {
      const f = await J(`https://api.llama.fi/summary/fees/${ps[0].slug}?dataType=${t}`);
      if (f?.totalDataChart?.length) out[t] = f.totalDataChart;
    }
  } else if (chainsByGecko[cgId]) {
    out.category = 'Chain';
    const h = await J(`https://api.llama.fi/v2/historicalChainTvl/${encodeURIComponent(chainsByGecko[cgId])}`);
    if (h) out.tvl = h.map(x => [x.date, x.tvl]);
    for (const t of ['dailyFees', 'dailyRevenue']) {
      const f = await J(`https://api.llama.fi/overview/fees/${encodeURIComponent(chainsByGecko[cgId])}?dataType=${t}`);
      if (f?.totalDataChart?.length) out[t] = f.totalDataChart;
    }
  }
  if (emissionsSlugByGecko[cgId]) {
    const e = await J(`https://defillama-datasets.llama.fi/emissions/${emissionsSlugByGecko[cgId]}`);
    if (e?.documentedData?.data) out.emis = { cats: e.categories, total: e.metadata?.total,
      series: e.documentedData.data.map(s => ({ label: s.label, d: s.data.map(x => [x.timestamp, x.unlocked]) })) };
  }
  return out;
}

// Feature definitions used for each listing event (see docs/BACKTEST.md):
//  p0, p30, p90, plast   close on listing day, +30d, +90d, 2026-10-23 (same exchange)
//  btc0 … btclast        BTC close on the same dates and exchange
//  circ0                 unlocked supply at listing per DefiLlama schedule, else CoinGecko now
//  unlock90 / unlock12   % increase in scheduled unlocked supply 90 / 365 days after listing
//  insider_pct           insiders + private-sale share of documented allocation
//  tvl0                  last TVL point on or before listing day
//  fees_ann0 / rev_ann0  30 days before listing × 365/30 (requires ≥25 data points)
//  rev_qoq               revenue in the 90 days before listing vs the 90 days before that

// Binance futures-only listings (data/backtest/futures_only.csv)
//  - USDⓈ-M perpetuals from https://www.binance.com/fapi/v1/exchangeInfo (contractType PERPETUAL,
//    quote USDT, onboardDate inside the window). The exchangeInfo endpoint lists live and settling
//    contracts only, so contracts removed entirely before 2026-10-23 are missing (survivorship).
//  - "Futures-only" = base asset (with any 1000/1000000 prefix stripped) absent from the spot
//    exchangeInfo on data-api.binance.vision, which also lists halted and delisted spot pairs.
//  - Prices: daily futures klines (www.binance.com/fapi/v1/klines) from the onboard day; BTC from
//    BTCUSDT perpetual klines on the same dates. x30 / x90 / xlast as for spot.
async function futuresOnly() {
  const fx = await J('https://www.binance.com/fapi/v1/exchangeInfo');
  const sx = await J('https://data-api.binance.vision/api/v3/exchangeInfo');
  const spot = new Set(sx.symbols.map(s => s.baseAsset));
  const norm = b => b.replace(/^(1000000|1000|1M)/, '');
  return fx.symbols.filter(s => s.contractType === 'PERPETUAL' && s.quoteAsset === 'USDT' &&
      day(s.onboardDate) >= START && day(s.onboardDate) < END &&
      !spot.has(s.baseAsset) && !spot.has(norm(s.baseAsset)))
    .map(s => ({ sym: s.symbol, base: s.baseAsset, date: day(s.onboardDate), status: s.status }));
}
