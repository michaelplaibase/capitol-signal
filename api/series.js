// GET /api/series?ticker=NVDA
// Returns the recent daily close series plus the current price for one ticker.
// The page fetches this once per ticker (deduped, lazy on scroll) so it can show
// a price line on every card without hitting the API once per card. Signal only.

const { yahooDaily } = require("./_yahoo");

module.exports = async (req, res) => {
  const ticker = String((req.query && req.query.ticker) || "").toUpperCase().trim();
  try {
    if (!ticker) throw new Error("ticker kraeves");
    const now = Math.floor(Date.now() / 1000);
    const p1 = now - 220 * 86400;
    const d = await yahooDaily(ticker, p1, now);
    res.setHeader("Cache-Control", "s-maxage=3600, stale-while-revalidate=86400");
    res.status(200).json({
      ticker,
      currency: d.currency,
      current: d.current != null ? Number(d.current.toFixed(2)) : null,
      series: d.series.map((p) => [p[0], Number(p[1].toFixed(2))]),
    });
  } catch (e) {
    res.status(200).json({ ticker, error: String((e && e.message) || e) });
  }
};
