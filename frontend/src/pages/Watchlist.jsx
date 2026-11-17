import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { plain } from "../utils/format";

export default function Watchlist() {
  const [rows, setRows] = useState(null);
  const [quotes, setQuotes] = useState({});
  const [error, setError] = useState(null);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [adding, setAdding] = useState(null);

  /** Fetch a price for one stock, failing quietly.
   *  One unavailable quote must not blank out the whole list. */
  const loadQuote = useCallback(async (stockId) => {
    try {
      const q = await api.quote(stockId);
      setQuotes((current) => ({ ...current, [stockId]: q }));
    } catch {
      /* the row shows "no price" */
    }
  }, []);

  const loadList = useCallback(async () => {
    try {
      const stocks = await api.watchlist();
      setRows(stocks);
      stocks.forEach((stock) => loadQuote(stock.id));
    } catch (err) {
      setError(err.message);
    }
  }, [loadQuote]);

  useEffect(() => {
    loadList();
  }, [loadList]);

  // Debounced search, same as the trade screen: without the delay every
  // keystroke fires a request and the answers can arrive out of order.
  useEffect(() => {
    const term = query.trim();
    if (!term) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const found = await api.searchStocks(term, 8);
        if (!cancelled) setResults(found);
      } catch {
        if (!cancelled) setResults([]);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  async function add(stock) {
    setError(null);
    setAdding(stock.id);
    try {
      await api.addToWatchlist(stock.id);
      // Re-read rather than pushing locally, so the list always matches
      // the server — including when the stock was already on it.
      await loadList();
      setQuery("");
      setResults([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setAdding(null);
    }
  }

  async function remove(stockId) {
    setError(null);
    try {
      await api.removeFromWatchlist(stockId);
      setRows((current) => current.filter((s) => s.id !== stockId));
    } catch (err) {
      setError(err.message);
    }
  }

  const watched = new Set((rows || []).map((s) => s.id));

  return (
    <>
      <div className="workhead">
        <div>
          <h1>Watchlist</h1>
          <p>
          Followed, not owned
          {rows ? ` · ${rows.length} name${rows.length === 1 ? "" : "s"}` : ""}
        </p>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="card-head"><h2>Add a stock</h2></div>
        <div style={{ padding: "0 18px 10px" }}>
          <input
            type="text"
            placeholder="Symbol or company, e.g. ITC"
            aria-label="Search for a stock to add to the watchlist"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div style={{ padding: "0 10px 14px" }}>
          {query.trim() && results.length === 0 ? (
            <p className="muted" style={{ padding: "8px", fontSize: 13 }}>
              Nothing matches “{query.trim()}”.
            </p>
          ) : null}
          {results.map((stock) => {
            const already = watched.has(stock.id);
            return (
              <div className="result" key={stock.id}>
                <span>
                  <span className="sym">{stock.symbol}</span>
                  <span className="co">
                    {stock.name}
                    {stock.sector ? ` · ${stock.sector}` : ""}
                  </span>
                </span>
                <button
                  className="chip"
                  onClick={() => add(stock)}
                  disabled={already || adding === stock.id}
                  aria-label={`Add ${stock.symbol} to the watchlist`}
                >
                  {already ? "On list" : adding === stock.id ? "Adding…" : "Add"}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h2>Watching</h2></div>
        {rows === null ? (
          <div className="empty">Loading…</div>
        ) : rows.length === 0 ? (
          <div className="empty">
            <p>Nothing on the watchlist.</p>
            <p className="muted">Search above to follow a stock without owning it.</p>
          </div>
        ) : (
          <div className="tscroll">
            <table>
              <thead>
                <tr>
                  <th>Holding</th>
                  <th>Sector</th>
                  <th className="r">Last price</th>
                  <th className="r">As of</th>
                  <th />
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
                        <button
                          className="chip"
                          onClick={() => remove(stock.id)}
                          aria-label={`Remove ${stock.symbol} from the watchlist`}
                        >
                          Remove
                        </button>
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
