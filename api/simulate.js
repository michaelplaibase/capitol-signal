// GET /api/simulate?politician=pelosi&since=2026-01-01
// "If you had mirrored this politician's disclosed buys since <since>, what
// would they be worth now?" Uses the Kadoa per-filer full history plus Yahoo
// closing prices. Estimate only, buy-and-hold, signal only, not advice.

const { yahooDaily, closeOnOrBefore } = require("./_yahoo");

const FILER_DIR_API =
  "https://api.github.com/repos/kadoa-org/congress-trading-monitor/contents/public/data/filer?ref=main";
const FILER_RAW =
  "https://raw.githubusercontent.com/kadoa-org/congress-trading-monitor/main/public/data/filer/";

async function listFilerIds() {
  const r = await fetch(FILER_DIR_API, {
    headers: { "User-Agent": "capitol-signal", accept: "application/vnd.github+json" },
  });
  if (!r.ok) throw new Error("filer list " + r.status);
  const arr = await r.json();
  if (!Array.isArray(arr)) throw new Error("filer list shape");
  return arr
    .filter((x) => x && x.name && x.name.endsWith(".json"))
    .map((x) => x.name.replace(/\.json$/, ""));
}

function resolveFiler(query, ids) {
  const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
  const matches = ids.filter((id) => {
    const slug = id.toLowerCase();
    return tokens.every((t) => slug.indexOf(t) >= 0);
  });
  matches.sort((a, b) => a.length - b.length);
  return matches;
}

function prettyName(filerObj, id) {
  if (filerObj && (filerObj.filer_name || filerObj.name)) {
    return filerObj.filer_name || filerObj.name;
  }
  return id
    .replace(/^(house|senate|exec|oge)_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

async function poolMap(items, size, fn) {
  const out = new Array(items.length);
  let i = 0;
  async function worker() {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await fn(items[idx]);
    }
  }
  await Promise.all(Array.from({ length: Math.min(size, items.length) }, worker));
  return out;
}

module.exports = async (req, res) => {
  const query = String((req.query && req.query.politician) || "").trim();
  const since = String((req.query && req.query.since) || "2026-01-01").slice(0, 10);
  try {
    if (!query) throw new Error("politician kraeves");
    const ids = await listFilerIds();
    const matches = resolveFiler(query, ids);
    if (!matches.length) {
      res.status(200).json({
        politician_query: query, since, matched: null, positions: [], totals: null,
        note: "Ingen politiker matchede '" + query + "'.",
      });
      return;
    }
    const filerId = matches[0];
    const fr = await fetch(FILER_RAW + filerId + ".json", {
      headers: { "User-Agent": "capitol-signal" },
    });
    if (!fr.ok) throw new Error("filer file " + fr.status);
    const fdata = await fr.json();
    const trades = Array.isArray(fdata) ? fdata : fdata.trades || [];
    const filerName = prettyName(fdata.filer, filerId);

    const isBuy = (t) => /purchase/i.test(t || "");
    const buys = [];
    for (const x of trades) {
      if (!isBuy(x.transaction_type)) continue;
      const tk = String(x.ticker || "").toUpperCase().trim();
      if (!tk) continue;
      const td = String(x.transaction_date || "").slice(0, 10);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(td) || td < since) continue;
      const lo = x.amount_range_low;
      const hi = x.amount_range_high;
      const invested = lo != null && hi != null ? (lo + hi) / 2 : lo != null ? lo : hi;
      if (invested == null) continue;
      buys.push({ ticker: tk, date: td, invested });
    }
    if (!buys.length) {
      res.status(200).json({
        politician_query: query, since,
        matched: { filer_id: filerId, filer_name: filerName },
        positions: [], totals: null,
        note: "Ingen koeb med ticker for " + filerName + " siden " + since + ".",
      });
      return;
    }

    const byTicker = {};
    for (const b of buys) (byTicker[b.ticker] = byTicker[b.ticker] || []).push(b);
    const tickers = Object.keys(byTicker).slice(0, 40);
    const p1 = Math.floor(new Date(since + "T00:00:00Z").getTime() / 1000) - 10 * 86400;
    const now = Math.floor(Date.now() / 1000);

    const positions = await poolMap(tickers, 6, async (tk) => {
      try {
        const d = await yahooDaily(tk, p1, now);
        let shares = 0, invested = 0, priced = 0;
        for (const b of byTicker[tk]) {
          const px = closeOnOrBefore(d.series, b.date);
          if (px && px > 0) { shares += b.invested / px; invested += b.invested; priced++; }
        }
        if (!(invested > 0) || !d.current) {
          return { ticker: tk, trades: byTicker[tk].length, error: "ingen kurs" };
        }
        const curVal = shares * d.current;
        return {
          ticker: tk, trades: byTicker[tk].length, priced,
          invested: Math.round(invested), shares: Number(shares.toFixed(3)),
          current_price: Number(d.current.toFixed(2)), current_value: Math.round(curVal),
          return_pct: Number(((100 * (curVal - invested)) / invested).toFixed(1)),
        };
      } catch (e) {
        return { ticker: tk, trades: byTicker[tk].length, error: String((e && e.message) || e) };
      }
    });

    positions.sort((a, b) => (b.current_value || 0) - (a.current_value || 0));
    let invSum = 0, valSum = 0;
    for (const p of positions) if (!p.error) { invSum += p.invested; valSum += p.current_value; }
    const totals = invSum > 0 ? {
      invested: Math.round(invSum), current_value: Math.round(valSum),
      return_pct: Number(((100 * (valSum - invSum)) / invSum).toFixed(1)),
      tickers: positions.filter((p) => !p.error).length,
    } : null;

    res.setHeader("Cache-Control", "s-maxage=1800, stale-while-revalidate=86400");
    res.status(200).json({
      politician_query: query, since,
      matched: { filer_id: filerId, filer_name: filerName },
      candidates: matches.slice(0, 6),
      trades_used: buys.length, positions, totals,
      note:
        "Estimat: beloeb = midtpunkt af interval, koebt til lukkekurs paa handelsdagen, " +
        "buy-and-hold (senere salg ignoreret). Markedsdata: Yahoo Finance. Ikke investeringsraadgivning.",
    });
  } catch (e) {
    res.status(200).json({ politician_query: query, since, error: String((e && e.message) || e) });
  }
};
