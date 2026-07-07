// Vercel serverless function: fetch recent congressional trades from the public
// Kadoa dataset, normalize them to the Capitol Signal shape, and return JSON.
//
// Signal only: this endpoint reads and returns disclosure data. It never places,
// prepares, or simulates any brokerage order. It mirrors the normalization done
// by the Python pipeline (see ingest/kadoa_puller.py and core/normalize.py).

const KADOA_URL =
  "https://raw.githubusercontent.com/kadoa-org/congress-trading-monitor/main/public/data/trades.json";

const SIDE = {
  purchase: "buy",
  "sale (full)": "sell",
  "sale (partial)": "sell",
  exchange: "exchange",
};

function normSide(value) {
  if (!value) return "other";
  return SIDE[String(value).trim().toLowerCase()] || "other";
}

function normParty(value) {
  if (!value) return null;
  const s = String(value).trim();
  if (/^republican/i.test(s)) return "R";
  if (/^democrat/i.test(s)) return "D";
  if (/^independ/i.test(s)) return "I";
  if (["R", "D", "I"].includes(s.toUpperCase())) return s.toUpperCase();
  return s.charAt(0).toUpperCase() || null;
}

function chamber(record) {
  if (record.chamber) return record.chamber;
  if (record.branch === "executive") return "oge";
  return null;
}

function iso(value) {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    return value.slice(0, 10);
  }
  return null;
}

module.exports = async (req, res) => {
  try {
    const resp = await fetch(KADOA_URL, { headers: { accept: "application/json" } });
    if (!resp.ok) throw new Error("kadoa upstream " + resp.status);
    const data = await resp.json();
    const recs = Array.isArray(data) ? data : data.trades || data.data || [];

    const cutoff = new Date(Date.now() + 86400000); // today + 1 day
    const out = [];
    for (const x of recs) {
      const td = iso(x.transaction_date);
      if (td && new Date(td) > cutoff) continue; // drop future-dated filings
      out.push({
        chamber: chamber(x),
        politician: x.filer_name || x.owner || "Unknown",
        party: normParty(x.party),
        state: x.state || null,
        ticker: x.ticker || null,
        asset_name: x.asset_name || null,
        side: normSide(x.transaction_type),
        trade_date: td,
        filing_date: iso(x.filing_date),
        amount_min: x.amount_range_low != null ? x.amount_range_low : null,
        amount_max: x.amount_range_high != null ? x.amount_range_high : null,
        doc_url: x.doc_url || null,
      });
    }
    out.sort(
      (a, b) =>
        (b.filing_date || "").localeCompare(a.filing_date || "") ||
        (b.trade_date || "").localeCompare(a.trade_date || "")
    );

    res.setHeader("Cache-Control", "s-maxage=600, stale-while-revalidate=1800");
    res.status(200).json({
      count: out.length,
      generated_at: new Date().toISOString(),
      trades: out.slice(0, 500),
    });
  } catch (e) {
    res.status(502).json({ error: String((e && e.message) || e) });
  }
};
