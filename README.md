# StockEx

A portfolio tracker for the Indian stock market (NSE). Record what you
bought, and it works out where you stand — what you hold, what is in
profit, what is in loss, and how the portfolio has moved over time.

Built with FastAPI, PostgreSQL and React.

> Not a brokerage. No money moves through it; it tracks positions you
> enter yourself. Market prices come from a free, delayed feed.

---

## What it does

- **Record buys and sells.** Every trade is a permanent ledger entry.
- **Derive positions from the ledger.** Holdings are never stored; they
  are calculated by replaying your transactions.
- **Price them at the market.** Delayed NSE closes, cached locally.
- **Separate realized from unrealized profit.** Money actually banked is
  reported apart from profit that still moves daily.
- **FIFO cost basis**, as Indian tax rules require.
- **Search any listed stock** and keep a watchlist of ones you do not own.
- **Dashboard** with portfolio value over twelve months and month-on-month
  change, in light or dark.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (Python 3.13) | Type hints generate the API docs; same language as the analysis work |
| Database | PostgreSQL 16 | The data is relational and financial — constraints belong in the database |
| ORM | SQLAlchemy 2.0 | Typed models; raw SQL still available where it is better |
| Migrations | Alembic | Schema changes are versioned and reversible |
| Auth | bcrypt + JWT | Hashed passwords, signed stateless tokens |
| Market data | yfinance | Free, no API key, covers NSE |
| Front end | React 18 + Vite | — |

Charts are hand-drawn SVG. No charting dependency.

## Design decisions worth knowing

**The ledger is append-only.** The obvious design is a table of current
holdings — but selling 20 of 50 shares means editing that row down to 30,
and the fact that 50 were ever held is gone. Instead every buy and sell is
stored as an immutable event and positions are computed from the history.

That is what makes these answerable, none of which a holdings table can
answer:

- What was the portfolio worth last March?
- How much profit was actually booked this year, as opposed to on paper?
- What did I hold before I sold it?

**FIFO, not average cost.** Sell 60 of 150 TCS shares bought at ₹2,100 and
₹2,400 and the realized profit is ₹24,000 under FIFO and ₹18,000 under
average cost. Same trades, ₹6,000 difference in taxable profit.

**Money uses `NUMERIC`, never `FLOAT`.** Floats cannot represent decimals
exactly — `0.1 + 0.2` is `0.30000000000000004` — and the error compounds
across rows until the books stop balancing.

**The position engine is pure.** `app/services/portfolio.py` has no
database, no network and no framework in it. That is what makes it
exhaustively testable, and it is the one module where a bug silently
produces wrong money.

**Market data sits behind one module.** `yfinance` is unofficial and will
break eventually. Everything else asks for a `Quote` and does not care
where it came from, so swapping providers is a one-file change. When the
feed fails the dashboard degrades — holdings still listed, market figures
blank — rather than breaking.

## Running it

**Requires:** Python 3.13, PostgreSQL 16, Node 18+.

```bash
# 1. Database
createdb stockex

# 2. Backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then set DATABASE_URL and SECRET_KEY
alembic upgrade head          # creates the tables
python -m scripts.seed_stocks # loads NSE symbols so search works

uvicorn app.main:app --reload
```

Interactive API docs: <http://127.0.0.1:8000/docs>

```bash
# 3. Front end, in a second terminal
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

```bash
# 4. Price history, so the dashboard charts have something to draw
python -m scripts.fetch_prices
```

### With Docker instead

```bash
cp .env.example .env
docker compose up --build
```

Brings up Postgres, the API on :8000 and the front end on :5173, and runs
the migration automatically.

## Tests

```bash
pytest -q
```

34 tests. The ones that matter most:

- `tests/test_portfolio.py` — the FIFO engine, including a sale spanning
  two lots, selling out completely, overselling, and decimal exactness.
- `tests/test_api.py` — every endpoint end to end against a real database,
  including that one user cannot read another's ledger.
- `tests/test_history.py` — reconstructing a *past* position: buy 100, sell
  60, then ask what 31 March was worth.

## API

| Method | Path | Does |
|---|---|---|
| POST | `/api/auth/register` | Create an account |
| POST | `/api/auth/login` | Email and password for a bearer token |
| GET | `/api/auth/me` | Confirm a stored token |
| GET | `/api/stocks/search?q=` | Search the local stock list |
| GET | `/api/stocks/{id}/quote` | Current delayed price |
| POST | `/api/transactions` | Record a buy or sell (rejects overselling) |
| GET | `/api/transactions` | The ledger, newest first |
| DELETE | `/api/transactions/{id}` | Correct a mistyped entry |
| GET | `/api/portfolio` | The whole dashboard in one call |
| GET | `/api/portfolio/history` | Month-end values replayed from the ledger |
| GET/POST/DELETE | `/api/watchlist` | Follow stocks without owning them |

## Layout

```
app/
  core/        settings, password hashing, tokens
  db/          engine, session, model base
  models/      users, stocks, transactions, watchlist, price_history
  schemas/     request and response shapes (never expose a password hash)
  services/    portfolio.py (pure FIFO engine), positions.py, market_data.py
  api/routes/  one file per feature
scripts/       seeding, price fetching, environment checks
tests/
frontend/      React app
docs/          design decisions and reasoning
```

## Limitations

- Prices are delayed roughly fifteen minutes. Real-time market data is a
  paid product.
- Dividends, bonuses, splits and brokerage charges are not modelled.
- The stock list ships with the large NSE names; the full list imports from
  NSE's published CSV via `python -m scripts.seed_stocks path/to/EQUITY_L.csv`.
