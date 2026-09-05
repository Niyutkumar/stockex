# StockEx — Setup and Decisions

Project notes. Written as we go, so the reasoning behind each choice is
recorded while it is fresh rather than reconstructed later.

Last updated: 4 September 2026

---

## 1. What we are building

A stock portfolio tracker for the Indian market (NSE).

A user logs in, records the shares he has bought — which stock, how many,
at what price, on what date — and the site works out where he stands.
It fetches current market prices, compares them against what he paid, and
shows what is in profit and what is in loss.

**Features required:**

- User login
- Record a purchase (stock, quantity, price, date)
- Record a sale, which updates the position
- Dashboard: per-stock profit/loss, overall portfolio performance
- Search any stock listed on the market
- Watchlist — follow stocks without owning them
- Live (delayed) market prices

**Not included:** real money. No payments, no broker integration. It is a
tracker, not a brokerage. It should still look and behave like a real
product.

## 2. Why this project

Two goals at once:

1. **Learning** — understanding how a front end and back end actually fit
   together, rather than following a tutorial.
2. **Portfolio** — demonstrating both full-stack development and data
   analytics to employers.

Financial data suits this well: the app naturally produces data worth
analysing, so the analytics are the point of the product rather than a
bolt-on.

## 3. The stack, and why

| Piece | What it does | Why chosen |
|---|---|---|
| **Python 3.13** | Back end language | Already being learned; the standard language for data analysis, so it serves both goals |
| **PostgreSQL 16** | Database — permanent storage | The data is deeply relational (users, holdings, transactions, prices). Enforces consistency, which matters for financial figures. Gives real SQL practice, which nearly every data role requires |
| **FastAPI** | Web framework | Handles HTTP so we write logic, not plumbing. Generates API documentation automatically from type hints |
| **uvicorn** | The web server | Listens for requests and hands them to FastAPI |
| **React** | Front end (later) | What the user sees |
| **yfinance** | Market price data | Free, no API key, no request quota, covers NSE |

### Why Python 3.13 and not 3.14

The machine already had Python 3.14.6. We installed 3.13 anyway.

Data libraries such as pandas take months to publish prebuilt versions for
each new Python release. Until they do, installing them tries to compile
from source and fails with errors unrelated to your own code. Using a
slightly older Python avoids that entire class of problem.

The general principle: **pin your Python version, do not chase the newest.**

### Why PostgreSQL and not MongoDB

The earlier StockX project used MongoDB. This one uses Postgres because:

- The data is relational — a transaction belongs to a user and refers to a
  stock. Postgres enforces those links and refuses to store an orphaned
  record. MongoDB would accept it, and the problem surfaces later.
- Financial figures must stay consistent.
- It means writing real SQL, which is on nearly every data analytics job
  description.

## 4. Machine setup

Installed via Homebrew:

    brew install python@3.13 postgresql@16
    brew services start postgresql@16

`brew services start` matters: a database is not a file, it is a program
that must be running in the background for the app to connect to it. This
also sets it to start automatically after a reboot.

Homebrew installs versioned packages "keg-only" — deliberately not wired
into the shell, so multiple versions can coexist. So Postgres's commands
had to be added to `PATH`, the list of folders the shell searches when you
type a command:

    echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc

Appending to `~/.zshrc` makes it permanent — that file is read every time a
terminal opens.

Verified with:

    psql postgres -c "SELECT version();"

Returned PostgreSQL 16.15. Installed, running, and accepting connections.

## 5. Project structure

    stockex/
    ├── .gitignore
    ├── .venv/          # virtual environment (not committed)
    ├── app/            # the application itself
    │   ├── __init__.py
    │   └── main.py
    ├── docs/           # project notes (this file)
    └── scripts/        # standalone utilities, run by hand

### Why each folder exists

**`app/`** — the product. Code that runs when the server runs. Everything
that ships lives here.

**`scripts/`** — utilities run by hand and not part of the running app:
checking a data source, importing the stock list, backfilling prices,
resetting the database for testing. Kept separate so it stays obvious which
code actually ships.

**`docs/`** — written reasoning behind the design. Standard practice on real
teams, and it is what lets someone (including you, in three months)
understand why things are the way they are.

**`.venv/`** — the virtual environment. See below.

### `.gitignore`

Git tracks changes to code and publishes it to GitHub. `.gitignore` lists
what git should ignore. Two entries matter most:

- **`.venv/`** — tens of thousands of files, machine-specific, and
  rebuildable from a dependency list. Committing it is a common beginner
  tell on a portfolio repository.
- **`.env`** — will hold database passwords and API keys. Committed secrets
  are among the most common serious mistakes on public repositories, and
  once pushed they remain in git history even after deletion. Excluded
  before the file exists rather than after.

### The virtual environment

Created with:

    /opt/homebrew/bin/python3.13 -m venv .venv
    source .venv/bin/activate

Without one, every `pip install` goes into the system Python shared by
everything on the machine, so two projects needing different versions of the
same library break each other.

A virtual environment is a private Python belonging to this project alone.
Its packages cannot affect anything else.

`source .venv/bin/activate` turns it on for the current terminal — the
prompt then starts with `(.venv)`. It applies to that one terminal only and
must be run again in each new one. Forgetting it is the usual cause of
"but I installed that package".

## 6. First working endpoint

    pip install fastapi "uvicorn[standard]"

`app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="StockEx API")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

- `@app.get("/health")` is a **decorator** — it registers the function below
  as the handler for GET requests to `/health`. The function is never called
  directly; FastAPI calls it when a request arrives.
- `-> dict[str, str]` is a **type hint**. Not enforced at runtime, but the
  editor uses it to catch mistakes and FastAPI uses it to generate
  documentation.
- A `/health` endpoint is a real convention — hosting platforms ping it to
  check whether the app is alive.

`app/__init__.py` is empty on purpose. It marks the folder as a Python
package, which is what allows `from app.something import ...` later.

Run with:

    uvicorn app.main:app --reload

Reads as: in the `app` package, find the `main` module, use the object named
`app` inside it. `--reload` restarts the server whenever a file is saved.

Then visit:

- http://127.0.0.1:8000/health — returns `{"status": "ok"}`
- http://127.0.0.1:8000/docs — interactive API documentation, generated
  automatically from the code

## 7. Market data — verified before building

**Principle: verify external dependencies before designing around them.**

The entire app depends on being able to fetch stock prices for free. Rather
than assume it works, we tested it first — `scripts/check_data_source.py`
requests recent prices for four NSE stocks and prints the results.

Result: all four returned real prices, dated the same day.

    RELIANCE.NS    OK   last close Rs 1,318.50 on 2026-09-04
    TCS.NS         OK   last close Rs 2,330.00 on 2026-09-04
    INFY.NS        OK   last close Rs 1,140.50 on 2026-09-04
    HDFCBANK.NS    OK   last close Rs 709.65 on 2026-09-04

**Notes on the data source:**

- NSE tickers use a `.NS` suffix (`RELIANCE.NS`); BSE uses `.BO`.
- Prices are delayed, typically by around 15 minutes. Genuine real-time data
  is a paid product — exchanges charge for it. Delayed data is fine for a
  portfolio tracker.
- `yfinance` is an unofficial library reading Yahoo Finance. It can break
  without warning.

**Therefore:** all market data access will be isolated behind a single
module, so swapping the provider is a one-file change rather than a rewrite.

Fallbacks if needed, all free: NSE's own published end-of-day files,
Alpha Vantage free tier, Twelve Data free tier.

Installing `yfinance` also brought in **pandas** and **numpy** as
dependencies — the two libraries the analytics layer will be built on.

## 8. Key design decision: store transactions, not holdings

The obvious design is a table of what the user currently owns:

| user | stock | quantity | buy price |
|---|---|---|---|
| niyut | RELIANCE | 50 | 1250.00 |

This is a trap. When he sells 20 shares, you edit the row to 30 — and the
fact that he ever held 50 is gone. Information destroyed.

Instead we record **events**, never edited:

| user | stock | type | quantity | price | date |
|---|---|---|---|---|---|
| niyut | RELIANCE | BUY | 50 | 1250.00 | 2026-01-15 |
| niyut | RELIANCE | SELL | 20 | 1400.00 | 2026-06-10 |

Current holdings are not stored. They are calculated: 50 bought − 20 sold =
30 held. A sale appends a row rather than modifying one.

**What this buys us** — all of these become answerable, and none of them are
under the first design:

- What was the portfolio worth in March?
- How much profit was actually booked this year, versus on paper?
- What was held before it was sold?
- How has the portfolio performed over time?

The dashboard's history charts and the entire analytics layer depend on this
history existing. This pattern is called an **append-only ledger**, and it is
how brokerages, banks and accounting systems work.

### Cost basis: FIFO

When 20 of 50 shares bought at different prices are sold, which 20 were
sold? It changes the profit figure. We use **FIFO** — oldest shares first —
because that is what Indian tax rules require.

### Realized vs unrealized

- **Realized** — profit from shares actually sold. Fixed, historical.
- **Unrealized** — profit on paper for shares still held. Changes daily with
  the market.

The dashboard must show both, kept clearly separate. Conflating them is
where most portfolio trackers go wrong.

## 9. Planned tables

| Table | Holds | Why it exists |
|---|---|---|
| `users` | Email, hashed password, created date | Login. Passwords are hashed, never stored as text |
| `stocks` | Symbol, company name, exchange, sector | Master list of tradable stocks. Powers search locally instead of calling an API on every keystroke |
| `transactions` | user, stock, BUY/SELL, quantity, price, date | The ledger. The heart of the application |
| `watchlist` | user, stock | Stocks followed but not owned. Interest is not ownership |
| `price_history` | stock, date, closing price | Cached prices. Without it, charting a year of portfolio value means hundreds of API calls per page load |

## 10. Status

**Done and verified:**

- Python 3.13 virtual environment
- PostgreSQL 16 installed, running, and answering queries
- Project structure and `.gitignore`
- FastAPI application with a working `/health` endpoint
- Market data source tested and confirmed working for NSE stocks

**Open:**

- Run the server and confirm `/health` and `/docs` in the browser
- Write the database models
- Set up git and push to GitHub

**Next:** the database models — turning the tables above into code.
