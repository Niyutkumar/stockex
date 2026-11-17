import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { money, plain, quantity, shortDate } from "../utils/format";

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "BUY", label: "Buys" },
  { key: "SELL", label: "Sells" },
];

export default function Transactions() {
  const [rows, setRows] = useState(null);
  const [filter, setFilter] = useState("ALL");
  const [error, setError] = useState(null);

  async function load() {
    try {
      setRows(await api.transactions());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, []);

  async function remove(id) {
    try {
      await api.deleteTransaction(id);
      setRows((current) => current.filter((r) => r.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  const shown = useMemo(
    () => (rows || []).filter((r) => filter === "ALL" || r.transaction_type === filter),
    [rows, filter]
  );

  if (error) return <div className="alert error">{error}</div>;

  return (
    <>
      <div className="workhead">
        <div>
          <h1>Transactions</h1>
          <p>Append-only ledger{rows ? ` · ${rows.length} entries` : ""}</p>
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h2>All entries</h2></div>
        <div className="filters">
          {FILTERS.map((f) => (
            <button key={f.key} className={"chip" + (filter === f.key ? " on" : "")}
                    aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>
              {f.label}
            </button>
          ))}
        </div>

        {rows === null ? (
          <div className="empty">Loading…</div>
        ) : shown.length === 0 ? (
          <div className="empty">Nothing recorded yet.</div>
        ) : (
          <div className="tscroll">
            <table>
              <thead>
                <tr>
                  <th>Date</th><th>Holding</th><th>Side</th>
                  <th className="r">Qty</th><th className="r">Price</th>
                  <th className="r">Consideration</th><th>Note</th><th />
                </tr>
              </thead>
              <tbody>
                {shown.map((row) => (
                  <tr key={row.id}>
                    <td className="num">{shortDate(row.transaction_date)}</td>
                    <td>
                      <span className="sym">{row.symbol}</span>
                      <span className="co">{row.stock_name}</span>
                    </td>
                    <td>
                      <span className={"chipnum " + (row.transaction_type === "BUY" ? "up" : "down")}>
                        {row.transaction_type === "BUY" ? "Buy" : "Sell"}
                      </span>
                    </td>
                    <td className="r">{quantity(row.quantity)}</td>
                    <td className="r">{plain(row.price, { paise: true })}</td>
                    <td className="r">{money(Number(row.quantity) * Number(row.price))}</td>
                    <td className="muted">{row.notes || "—"}</td>
                    <td className="r">
                      <button className="chip" onClick={() => remove(row.id)}
                              title="Remove a mistyped entry">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
