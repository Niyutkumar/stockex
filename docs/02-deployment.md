# Deployment

Free, no card required, and nothing that expires.

| Piece | Where | Why |
|---|---|---|
| Database | **Neon** free tier | 1 GB, no credit card, no expiry. Sleeps after 5 minutes idle and wakes on the next query |
| API | **Render** free web service | 512 MB |
| Front end | **Render** static site | No spin-down |

**Render's own free Postgres is not used, deliberately.** It expires 30
days after creation, then is deleted after a 14-day grace period — which
would kill the link a month after it goes on a CV.

---

## 1. Database — Neon

1. Sign up at <https://neon.tech> with GitHub.
2. Create a project. Region: Singapore or Mumbai if offered.
3. Copy the connection string. It looks like:

       postgresql://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

Note it starts `postgresql://`. SQLAlchemy needs `postgresql+psycopg://`,
and `app/core/config.py` rewrites it automatically, so paste it unchanged.

## 2. Services — Render

1. Sign up at <https://render.com> with GitHub.
2. **New → Blueprint**, pick the `stockex` repository. Render reads
   `render.yaml` and proposes both services.
3. When prompted for `DATABASE_URL` on **stockex-api**, paste the Neon
   string. `SECRET_KEY` is generated for you.
4. Apply. First build takes a few minutes.

The names in `render.yaml` assume the resulting URLs are
`stockex-api.onrender.com` and `stockex-web.onrender.com`. If Render gives
different ones, update `CORS_ORIGINS` and `VITE_API_BASE` to match and
redeploy — a mismatch shows up in the browser as a CORS error.

## 3. Seed the stock list

The migration creates empty tables. In the Render dashboard, open
**stockex-api → Shell**:

    python -m scripts.seed_stocks

Search returns nothing until this has run.

## 4. Prices for the charts

    python -m scripts.fetch_prices

Only fetches stocks someone holds or watches, so run it after recording
some trades. Worth repeating daily — Render's free plan has no scheduler,
so either run it by hand or add a cron job elsewhere that calls it.

---

## The cold start, honestly

A free Render web service **spins down after 15 minutes of inactivity**,
and the next request takes **50 seconds or more** while it restarts.

Someone opening your link from a CV will often be the first visitor in
hours, and will meet that wait. Three options:

1. **Live with it**, and say so on the page: "first load may take a
   minute, free hosting."
2. **Keep it warm.** A scheduled ping of `/health` every 10 minutes
   prevents spin-down. The free plan allows 750 instance-hours a month and
   a month is about 744 hours, so one always-on service just fits — with
   almost no margin, and a second service would exceed it.
3. **Pay.** Render's cheapest paid instance removes spin-down.

Option 1 is the honest one, and a visible note reads better than a blank
page.

## Other limits worth knowing

- 5 GB bandwidth a month across the workspace.
- 500 build minutes a month.
- Neon sleeps after 5 minutes idle; the first query wakes it, which adds
  a second or so on top of the Render cold start.
- `yfinance` is unofficial. If it stops working the dashboard still shows
  holdings and cost, with market figures blank.
