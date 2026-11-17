import { useEffect, useState } from "react";
import { api } from "../api/client";
import { plain } from "../utils/format";

export default function Watchlist() {
  const [rows, setRows] = useState(null);
  const [quotes, setQuotes] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const stocks = await api.watchlist();
        if (cancelled) return;
        setRows(stocks);

        // Prices one at a time, each failure isolated: one unavailable
        // quote must not blank out the whole list.
        const found = {};
        await Promise.all(
          stocks.map(async (stock) => {
            try {
              const q = await api.quote(stock.id);
              found[stock.id] = q;
            } catch {
              /* leave it missing; the row shows "no price" */
            }
          })
        );
        if (!cancelled) setQuotes(found);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  async function remove(stockId) {
    try {
      await api.removeFromWatchlist(stockId);
      setRows((current) => current.filter((s) => s.id !== stockId));
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <div className="alert error">{error}</div>;

  return (
    <>
      <div className="workhead">
        <div>
          <h1>Watchlist</h1>
          <p>Followed, not owned{rows ? ` · ${rows.length} names` : ""}</p>
        </div>
      </div>

      <div className="card">
        {rows === null ? (
          <div className="empty">Loading…</div>
        ) : rows.length === 0 ? (
          <div className="empty">
            <p>Nothing on the watchlist.</p>
            <p className="muted">Add stocks you want to follow without owning them.</p>
          </div>
        ) : (
          <div className="tscroll">
            <table>
              <thead>
                <tr>
                  <th>Holding</th><th>Sector</th>
                  <th className="r">Last price</th><th className="r">As of</th><th />
                </tr>
              </thead>
              <tbody>
                {rows.map((stock) => {
                  const q = quotes[stock.id];
                  return (
                    <tr key={stock.id}>
                      <td>
                        <span className="sym">{stock.symbol}</span>
                        <span className="co">{stock.name}</span>
                      </td>
                      <td className="muted">{stock.sector || "—"}</td>
                      <td className="r">
                        {q ? plain(q.price, { paise: true }) : <span className="muted">no price</span>}
                      </td>
                      <td className="r muted">{q ? q.as_of : "—"}</td>
                      <td className="r">
                        <button className="chip" onClick={() => remove(stock.id)}>Remove</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
