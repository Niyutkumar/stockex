# Code walkthrough

Read the codebase in this order. Each section says what the file does, the
one idea in it worth holding on to, and the question an interviewer is
likely to ask about it.

Roughly ninety minutes end to end.

---

## 1. `app/services/portfolio.py` — start here

The FIFO position engine. No database, no network, no framework: give it a
list of trades, it returns what is held, at what cost, and what profit has
been booked.

**The idea.** Holdings are never stored anywhere. They are *computed* by
replaying every buy and sell in date order. Buys push a lot onto a queue;
sells consume lots from the front, oldest first, and the profit on each
consumed slice is `quantity × (sell price − that lot's buy price)`.

**Read:** `compute_position`. The `while remaining > ZERO` loop is the
whole algorithm.

**Likely question — "why FIFO rather than average cost?"**
Indian tax rules require it, and it changes the number. Sell 60 of 150 TCS
shares bought at ₹2,100 and ₹2,400: FIFO gives ₹24,000 realized, average
cost gives ₹18,000. Same trades, ₹6,000 difference in taxable profit.

**Likely question — "why is this file so isolated?"**
Because it is the one place a bug silently produces wrong money. Pure
functions can be tested exhaustively without a database, which is why
`tests/test_portfolio.py` can cover eleven cases in under a second.

**Subtlety worth mentioning unprompted:** trades sort by date *and then by
id*. Without the id tiebreak, two trades on the same day could replay in
whatever order Postgres happened to return them, and FIFO would give
different answers on different runs. Non-deterministic money.

---

## 2. `app/models/transaction.py` — the ledger

**The idea.** Append-only. A sale never edits a purchase; it adds a row.

**Likely question — "why not just store current holdings?"**
Because selling 20 of 50 shares would mean editing that row to 30, and the
fact that 50 were ever held is destroyed. Then none of these can be
answered: what was the portfolio worth in March, how much was actually
booked this year, what was held before it was sold. The dashboard history
chart is impossible without the ledger.

**Likely question — "why `Numeric` and not `Float`?"**
Floats cannot represent decimals exactly: `0.1 + 0.2` is
`0.30000000000000004`. Fine in physics, unacceptable in money, where the
error compounds across thousands of rows.

**Look at `__table_args__`.** Three check constraints and a composite
index. The constraints live in the database, not in Python, because the
application is not the only thing that will ever write to this table —
scripts will, and so will you by hand in `psql`.

---

## 3. `app/models/` — the rest of the schema

- `user.py` — note the column is `hashed_password`, named so nobody is
  tempted to put a password in it.
- `stock.py` — note `symbol` and `yahoo_symbol` are separate. `RELIANCE`
  is the exchange's name; `.NS` is Yahoo's convention. Keeping them apart
  means swapping data provider touches one column, not every row.
- `watchlist.py` — `stock_id` is `CASCADE` here but `RESTRICT` in
  transactions. A watchlist row is a bookmark; losing it costs nothing. A
  transaction records money that moved and must never be orphaned.
- `price_history.py` — the UNIQUE on `(stock_id, price_date)` is what
  makes the price fetch safe to re-run.
- `__init__.py` — imports all five. Without it SQLAlchemy does not know
  they exist and Alembic generates an empty migration with no error.

---

## 4. `app/core/security.py` — passwords and tokens

Two jobs that are easy to confuse. **Hashing** turns a password into
something irreversible, used once at registration and once per login.
**Tokens** prove identity on every later request so the password is not
sent again.

**Likely question — "is the token encrypted?"**
No. It is *signed*. Anyone can read what is inside it, which is why it
carries only the user id and no secrets. Altering the payload invalidates
the signature, so a client cannot promote itself to another user.

**Likely question — "why bcrypt?"**
Deliberately slow, and salted per hash, so two users with the same password
get different stored values and brute-forcing a stolen database is
expensive.

---

## 5. `app/api/deps.py` — how routes get protected

`get_current_user` reads the token, verifies it, and loads the user. Any
route that declares it as a dependency is automatically protected: without
a valid token the request never reaches the route body.

**Worth noticing:** every failure returns the same 401 with the same
message. Distinguishing "no such user" from "wrong password" would let
anyone test which email addresses are registered.

---

## 6. `app/api/routes/` — one file per feature

Read `transactions.py` first.

**Likely question — "what stops someone selling shares they don't own?"**
The POST handler replays the existing ledger plus the proposed sale through
the FIFO engine before writing anything. If it raises `OversoldError`, the
request is rejected with a 400. Without that check, one bad entry makes
every figure on the dashboard quietly wrong.

**Likely question — "how do you stop one user reading another's data?"**
Every query filters on `user_id`. It is one line, it appears in every
handler that touches user-owned data, and `tests/test_api.py` has a test
that registers a second user and asserts they see an empty ledger.

Then `stocks.py` — search runs against the local `stocks` table rather than
calling an API per keystroke, which is why that table exists at all.

---

## 7. `app/services/market_data.py` — the swappable edge

**The idea.** This is the only module that knows Yahoo Finance exists.
Everything else asks for a `Quote`.

**Likely question — "what happens when the data source breaks?"**
It will; `yfinance` is unofficial. Every failure is caught and logged, and
the function returns an empty list. The dashboard then shows holdings with
their cost and quantity and blanks the market figures, rather than
crashing or inventing a price. There is a test for exactly that case.

The `MarketDataProvider` Protocol is the contract a replacement has to
satisfy — and the reason the test suite can substitute a fake provider and
never touch the network.

---

## 8. `app/services/positions.py` — the seam

Turns database rows into the dashboard. Note what it does *not* contain:
any arithmetic about lots or profit. That all lives in the pure engine.
This file only fetches, groups, and formats.

`build_history` is the newest part. It replays the ledger at each month end
and prices it from cached closes — which is the append-only design paying
for itself, since a holdings table could not answer the question at all.

---

## 9. `frontend/src/` — the client

Read in this order:

1. `api/client.js` — every backend call in one file, so the token header
   and error handling are defined once.
2. `context/AuthContext.jsx` — a stored token proves nothing, so on load
   the app asks the server who it belongs to.
3. `theme.css` — the light palette on `:root`, then dark redefined twice:
   once for the OS setting, once for the toggle. A colour defined only
   inside a media query is the classic bug that puts one theme's text on
   the other theme's background.
4. `components/ValueChart.jsx` — hand-drawn SVG. `smoothPath` converts
   points into bezier curves.
5. `pages/Dashboard.jsx` — fetches the summary and the history in
   parallel, then derives the monthly change from the series client-side.

**Likely question — "why no charting library?"**
One chart does not justify a dependency, and the SVG is about sixty lines.

**Likely question — "why are the light and dark greens different?"**
Because a mint green on white measures about 2:1 against the background
and is unreadable. Light uses `#047857`, dark uses `#3ddc84`. The chart
gradient is also nearly twice as strong in dark mode to be visible at all.
Dark mode is a designed palette, not an inversion.

---

## 10. `tests/`

Three files, 34 tests.

- `test_portfolio.py` — the engine, including a sale spanning two lots,
  selling out completely, overselling, empty input, and decimal exactness.
- `test_api.py` — every endpoint against a real database, with a stub
  price provider so the numbers are fixed.
- `test_history.py` — buy 100, sell 60, then ask what 31 March was worth.

**Likely question — "what would you test next?"**
Concurrency: two sells submitted at the same moment could both pass the
oversell check before either is written. The fix is a transaction-level
lock on the user's rows for that stock. It is a real gap, and saying so is
better than pretending the suite is complete.

---

## Known gaps, if asked

- Dividends, bonus issues and stock splits are not modelled. A split would
  silently corrupt the position maths.
- Brokerage, STT and stamp duty are not deducted, so realized profit is
  gross rather than net.
- Prices are delayed about fifteen minutes.
- `DELETE /api/transactions/{id}` sits in tension with the append-only
  principle. The reasoning: the ledger is append-only for *business
  events*, but a mistyped entry was never an event. Accounting systems
  use a reversing entry; for a personal tracker, deleting the wrong row is
  the honest equivalent.

Knowing your own project's limits is worth more in an interview than
pretending it has none.
