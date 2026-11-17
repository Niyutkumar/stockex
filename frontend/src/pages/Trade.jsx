import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { money, plain, todayISO } from "../utils/format";

export default function Trade() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);

  const [side, setSide] = useState("BUY");
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [date, setDate] = useState(todayISO());
  const [notes, setNotes] = useState("");

  const [error, setError] = useState(null);
  const [done, setDone] = useState(null);
  const [busy, setBusy] = useState(false);

  // Debounced search: without the delay every keystroke fires a request
  // and the answers can arrive out of order.
  useEffect(() => {
    const term = query.trim();
    if (term.length < 1) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const rows = await api.searchStocks(term);
        if (!cancelled) setResults(rows);
      } catch {
        if (!cancelled) setResults([]);
      }
    }, 250);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [query]);

  async function choose(stock) {
    setSelected(stock);
    setError(null);
    setDone(null);
    // Prefill the price with the last close — nearly always what someone
    // recording today's trade wants, and still editable.
    try {
      const q = await api.quote(stock.id);
      setPrice(String(q.price));
    } catch {
      /* no quote available; leave the field for them to fill */
    }
  }

  const consideration = useMemo(() => {
    const q = Number(qty);
    const p = Number(price);
    return Number.isFinite(q) && Number.isFinite(p) ? q * p : null;
  }, [qty, price]);

  async function onSubmit(event) {
    event.preventDefault();
    if (!selected) return;
    setError(null);
    setDone(null);
    setBusy(true);
    try {
      await api.createTransaction({
        stock_id: selected.id,
        transaction_type: side,
        quantity: qty,
        price,
        transaction_date: date,
        notes: notes || null,
      });
      setDone(`${side === "BUY" ? "Bought" : "Sold"} ${qty} ${selected.symbol}`);
      setQty("");
      setNotes("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="workhead">
        <div>
          <h1>Record a trade</h1>
          <p>Entries are permanent. Your positions are derived from them.</p>
        </div>
      </div>

      <div className="panels" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,370px)" }}>
        <div className="card">
          <div className="card-head">
            <h2>Search the market</h2>
          </div>
          <div style={{ padding: "0 18px 10px" }}>
            <input type="text" placeholder="Symbol or company, e.g. TCS"
                   aria-label="Search symbol or company"
                   value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <div style={{ padding: "0 10px 14px" }}>
            {results.length === 0 && query.trim() ? (
              <p className="muted" style={{ padding: "8px 8px 2px", fontSize: 13 }}>
                Nothing matches “{query.trim()}”.
              </p>
            ) : null}
            {results.map((stock) => (
              <button type="button" key={stock.id}
                      className={"result" + (selected?.id === stock.id ? " selected" : "")}
                      aria-label={`Select ${stock.symbol}, ${stock.name}`}
                      aria-pressed={selected?.id === stock.id}
                      onClick={() => choose(stock)}>
                <span>
                  <span className="sym">{stock.symbol}</span>
                  <span className="co">{stock.name}{stock.sector ? ` · ${stock.sector}` : ""}</span>
                </span>
                <span className="ltp">{stock.exchange}</span>
              </button>
            ))}
          </div>
        </div>

        <form className="panel" onSubmit={onSubmit}>
          <div className="panel-head"><div><h2>Details</h2></div></div>

          {error ? <div className="alert error">{error}</div> : null}
          {done ? <div className="alert info">{done}</div> : null}

          <div className="field">
            <label>Side</label>
            <div className="seg">
              <button type="button" className={side === "BUY" ? "on-buy" : ""}
                      aria-pressed={side === "BUY"} onClick={() => setSide("BUY")}>Buy</button>
              <button type="button" className={side === "SELL" ? "on-sell" : ""}
                      aria-pressed={side === "SELL"} onClick={() => setSide("SELL")}>Sell</button>
            </div>
          </div>

          <div className="field">
            <label htmlFor="holding">Holding</label>
            <input id="holding" type="text" readOnly
                   value={selected ? `${selected.symbol} — ${selected.name}` : ""}
                   placeholder="Pick one from the search" />
          </div>

          <div className="field-row">
            <div className="field">
              <label htmlFor="qty">Quantity</label>
              <input id="qty" type="number" min="0" step="0.0001" required
                     value={qty} onChange={(e) => setQty(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="price">Price</label>
              <input id="price" type="number" min="0" step="0.01" required
                     value={price} onChange={(e) => setPrice(e.target.value)} />
            </div>
          </div>

          <div className="field">
            <label htmlFor="date">Trade date</label>
            {/* max stops a future date being picked at all; the API
                rejects one too, because the browser is not a guarantee. */}
            <input id="date" type="date" required max={todayISO()}
                   value={date} onChange={(e) => setDate(e.target.value)} />
          </div>

          <div className="field">
            <label htmlFor="notes">Note</label>
            <input id="notes" type="text" placeholder="optional"
                   value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>

          {consideration ? (
            <div className="recap">
              <div className="recap-row">
                <span>Consideration</span>
                <b>{money(consideration, { paise: true })}</b>
              </div>
              <div className="recap-row">
                <span>{side === "BUY" ? "Buying" : "Selling"}</span>
                <b>{plain(qty)} × {plain(price, { paise: true })}</b>
              </div>
            </div>
          ) : null}

          <button className="btn" type="submit" disabled={busy || !selected}>
            {busy ? "Recording…" : "Record trade"}
          </button>
        </form>
      </div>
    </>
  );
}
