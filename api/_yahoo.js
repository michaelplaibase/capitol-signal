// Shared Yahoo Finance daily-price helpers for the Capitol Signal web functions.
// Signal only: read-only market data, never orders. Files prefixed with "_" are
// not routed as endpoints by Vercel, so this is shared library code.

async function yahooDaily(ticker, period1, period2) {
  const url =
    "https://query1.finance.yahoo.com/v8/finance/chart/" +
    encodeURIComponent(ticker) +
    "?period1=" + period1 + "&period2=" + period2 + "&interval=1d";
  const r = await fetch(url, {
    headers: { "User-Agent": "Mozilla/5.0", accept: "application/json" },
  });
  if (!r.ok) throw new Error("yahoo " + r.status);
  const j = await r.json();
  const result = j && j.chart && j.chart.result && j.chart.result[0];
  if (!result || !result.timestamp || !result.indicators) {
    throw new Error("no data for " + ticker);
  }
  const ts = result.timestamp;
  const quote = result.indicators.quote[0] || {};
  const closes = quote.close || [];
  const highs = quote.high || [];
  const lows = quote.low || [];
  const meta = result.meta || {};
  const series = [];
  for (let i = 0; i < ts.length; i++) {
    if (closes[i] == null) continue;
    // Third element is the average price for the day: the midpoint of the daily
    // high and low (the "typical price"). Disclosures give only an amount range
    // and a date, never an execution price, so this midpoint is the fairest
    // single estimate of what the politician paid that day. Falls back to the
    // close when either high or low is missing.
    const hi = highs[i];
    const lo = lows[i];
    const avg = hi != null && lo != null ? (hi + lo) / 2 : closes[i];
    series.push([new Date(ts[i] * 1000).toISOString().slice(0, 10), closes[i], avg]);
  }
  const current =
    meta.regularMarketPrice != null
      ? meta.regularMarketPrice
      : series.length ? series[series.length - 1][1] : null;
  return { ticker, currency: meta.currency || "USD", series, current };
}

// Return the close on the given date, or the most recent trading day before it.
function closeOnOrBefore(series, dateStr) {
  let val = null;
  for (let i = 0; i < series.length; i++) {
    if (series[i][0] <= dateStr) val = series[i][1];
    else break;
  }
  return val;
}

// Return the day-average price (high/low midpoint) on the given date, or the
// most recent trading day before it. Falls back to the close when the average
// is unavailable for that row.
function avgOnOrBefore(series, dateStr) {
  let val = null;
  for (let i = 0; i < series.length; i++) {
    if (series[i][0] <= dateStr) val = series[i][2] != null ? series[i][2] : series[i][1];
    else break;
  }
  return val;
}

module.exports = { yahooDaily, closeOnOrBefore, avgOnOrBefore };
