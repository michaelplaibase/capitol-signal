// GET /api/price?ticker=NVDA&date=2026-01-16
// Returns the market close on the trade date (an estimate of the price a
// politician traded at, since disclosures give only an amount range) plus the
// current price. Signal only, read-only market data.

const { yahooDaily, closeOnOrBefore } = require("./_yahoo");

module.exports = async (req, res) => {
  const ticker = String((req.query && req.query.ticker) || "").toUpperCase().trim();
  const date = String((req.query && req.query.date) || "").slice(0, 10);
  try {
    if (!ticker) throw new Error("ticker kraeves");
    const now = Math.floor(Date.now() / 1000);
    let p1;
    if (/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      p1 = Math.floor(new Date(date + "T00:00:00Z").getTime() / 1000) - 10 * 86400;
    } else {
      p1 = now - 370 * 86400;
    }
    const data = await yahooDaily(ticker, p1, now);
    const onDate = date ? closeOnOrBefore(data.series, date) : null;
    res.setHeader("Cache-Control", "s-maxage=3600, stale-while-revalidate=86400");
    res.status(200).json({
      ticker,
      currency: data.currency,
      date: date || null,
      close_on_date: onDate != null ? Number(onDate.toFixed(2)) : null,
      current_price: data.current != null ? Number(data.current.toFixed(2)) : null,
      change_pct:
        onDate && data.current
          ? Number(((100 * (data.current - onDate)) / onDate).toFixed(1))
          : null,
    });
  } catch (e) {
    res.status(200).json({ ticker, error: String((e && e.message) || e) });
  }
};
