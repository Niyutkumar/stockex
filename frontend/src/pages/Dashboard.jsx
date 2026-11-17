import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import MonthlyBars from "../components/MonthlyBars";
import ValueChart from "../components/ValueChart";
import {
  money, plain, quantity, shortDate, signedMoney, signedPercent,
} from "../utils/format";

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState(null);
  const [history, setHistory] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Both at once rather than one after the other: they do not
        // depend on each other, so waiting twice would be wasted time.
        const [summary, hist] = await Promise.all([
          api.portfolio(),
          api.portfolioHistory(12).catch(() => null),
        ]);
        if (!cancelled) {
          setPortfolio(summary);
          setHistory(hist);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error) return <div className="alert error">{error}</div>;
  if (!portfolio) return <p className="muted">Loading…</p>;

  const empty = portfolio.holdings.length === 0;

  const series = (history?.points || []).map((p) => ({
    label: shortDate(p.date),
    short: new Date(p.date + "T00:00:00").toLocaleDateString("en-IN", { month: "short" }),
    value: Number(p.value),
    cost: Number(p.cost),
  }));

  // Month-on-month MARKET change.
  //
  // Not simply (value now - value then) / value then: that counts money
  // you put in as performance. Buy 50 more shares and raw value jumps,
  // but the market did nothing — the chart would show a huge green bar
  // for a month in which you merely deposited.
  //
  // So the contribution is subtracted first. The history endpoint returns
  // cost basis alongside value, and the change in cost basis IS the money
  // added or taken out that month.
  const changes = series.slice(1).map((point, i) => {
    const openValue = series[i].value;
    const contribution = point.cost - series[i].cost;
    const marketGain = point.value - openValue - contribution;
    return {
      label: point.label,
      short: point.short[0],
      pct: openValue > 0 ? (marketGain / openValue) * 100 : 0,
    };
  });

  const best = portfolio.holdings.find((h) => h.unrealized_pnl != null);

  return (
    <>
      <div className="workhead">
        <div>
          <h1>Dashboard</h1>
          <p>Positions derived from your ledger, priced at the last close.</p>
        </div>
        <span className="pill">
          <span className="dot" />
          {portfolio.priced_count} of {portfolio.holdings_count} priced · delayed
        </span>
      </div>

      {empty ? (
        <div className="card">
          <div className="empty">
            <p>No holdings yet.</p>
            <p><Link to="/trade">Record your first trade</Link> and this fills in.</p>
          </div>
        </div>
      ) : (
        <>
          <div className="stats">
            <div className="stat">
              <div className="lab">Current value</div>
              <div className="big">{money(portfolio.total_value)}</div>
              <div className={"sub " + (portfolio.total_unrealized_pnl >= 0 ? "gain" : "loss")}>
                {signedPercent(portfolio.total_unrealized_pct)} vs invested
              </div>
            </div>
            <div className="stat">
              <div className="lab">Unrealized P&amp;L</div>
              <div className={"big " + (portfolio.total_unrealized_pnl >= 0 ? "gain" : "loss")}>
                {signedMoney(portfolio.total_unrealized_pnl)}
              </div>
              <div className="sub muted">moves with the market</div>
            </div>
            <div className="stat">
              <div className="lab">Realized P&amp;L</div>
              <div className={"big " + (portfolio.total_realized_pnl >= 0 ? "gain" : "loss")}>
                {signedMoney(portfolio.total_realized_pnl)}
              </div>
              <div className="sub muted">booked on FIFO</div>
            </div>
            <div className="stat">
              <div className="lab">Invested</div>
              <div className="big">{money(portfolio.total_cost)}</div>
              <div className="sub muted">{portfolio.holdings_count} holdings</div>
            </div>
            {best ? (
              <div className="stat">
                <div className="lab">Best performer</div>
                <div className="big">{best.symbol}</div>
                <div className={"sub " + (best.unrealized_pnl >= 0 ? "gain" : "loss")}>
                  {signedPercent(best.unrealized_pct)}
                </div>
              </div>
            ) : null}
          </div>

          <div className="panels">
            <div className="panel">
              <div className="panel-head">
                <div>
                  <h2>Portfolio value</h2>
                  <p className="sub">Month-end, last 12 months</p>
                </div>
              </div>
              <ValueChart series={series} investedLine={Number(portfolio.total_cost)} />
              {series.length > 1 ? (
                <figcaption>
                  The gap between the curve and the dotted rule is the unrealized gain.
                </figcaption>
              ) : (
                <figcaption>
                  Run <code>python -m scripts.fetch_prices</code> to fill in price history.
                </figcaption>
              )}
            </div>

            <div className="panel">
              <div className="panel-head">
                <div>
                  <h2>Monthly change</h2>
                  <p className="sub">Market movement only, green up</p>
                </div>
              </div>
              <MonthlyBars changes={changes} />
            </div>
          </div>

          <div className="card">
            <div className="card-head"><h2>Holdings</h2></div>
            <div className="tscroll">
              <table>
                <thead>
                  <tr>
                    <th>Holding</th>
                    <th className="r">Qty</th>
                    <th className="r">Avg cost</th>
                    <th className="r">Last price</th>
                    <th className="r">Value</th>
                    <th className="r">Unrealized</th>
                    <th className="r">Realized</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.holdings.map((h) => (
                    <tr key={h.stock_id}>
                      <td>
                        <span className="sym">{h.symbol}</span>
                        <span className="co">{h.name}{h.sector ? ` · ${h.sector}` : ""}</span>
                      </td>
                      <td className="r">{quantity(h.quantity)}</td>
                      <td className="r">{plain(h.average_cost, { paise: true })}</td>
                      <td className="r">
                        {h.current_price == null
                          ? <span className="muted">no price</span>
                          : plain(h.current_price, { paise: true })}
                      </td>
                      <td className="r">
                        {h.market_value == null ? "—" : plain(h.market_value)}
                      </td>
                      <td className="r">
                        {h.unrealized_pnl == null ? (
                          <span className="muted">—</span>
                        ) : (
                          <span className={"chipnum " + (h.unrealized_pnl >= 0 ? "up" : "down")}>
                            {signedPercent(h.unrealized_pct)}
                          </span>
                        )}
                      </td>
                      <td className={"r " + (h.realized_pnl > 0 ? "gain" : h.realized_pnl < 0 ? "loss" : "muted")}>
                        {Number(h.realized_pnl) === 0 ? "—" : signedMoney(h.realized_pnl)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td>Total</td>
                    <td className="r" /><td className="r" /><td className="r" />
                    <td className="r">{plain(portfolio.total_value)}</td>
                    <td className={"r " + (portfolio.total_unrealized_pnl >= 0 ? "gain" : "loss")}>
                      {signedMoney(portfolio.total_unrealized_pnl)}
                    </td>
                    <td className={"r " + (portfolio.total_realized_pnl >= 0 ? "gain" : "loss")}>
                      {signedMoney(portfolio.total_realized_pnl)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
