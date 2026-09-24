# Expense Tracker — Backend

FastAPI + PostgreSQL API for a small, mobile-first personal tracker for **expenses and income**.
The Next.js frontend lives in its own repository and talks to this API through a same-origin
`/api` proxy.

- See today's and this month's spending, income, and where the money went by category,
  compared with the same days last month
- Add an expense or income in a few taps, with how it was paid (UPI, cash, card, bank)
- Recurring entries (rent, subscriptions, salary) that are added automatically every month
- Insights: daily spending chart, average per day, no-spend days, a 6-month trend, and a
  breakdown by payment method
- Browse, edit, and delete past transactions

There is intentionally **no balance** concept, and no budgets or bank integrations.

## Stack

Python 3.13+ (3.14 in development) · FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 ·
PostgreSQL (local or Supabase) · Argon2id password hashing · ruff.

## Architecture

- **Layers:** `api/endpoints` (HTTP) → `services/*_service.py` (rules, validation, commits, and
  SQLAlchemy queries that are always scoped by `user_id`) → `models`.
- **Auth:** server-side sessions. Login sets an `HttpOnly`, `SameSite=Lax` cookie holding a
  random token; the database stores only its SHA-256 digest. Logout revokes the session.
  Failed logins are throttled per email.
- **Money:** `NUMERIC(12,2)` in Postgres, sent as **decimal strings** (`"1250.00"`) in JSON.
  All totals are computed in SQL.
- **Dates:** transaction dates are calendar dates (`DATE`, `"YYYY-MM-DD"`), never timestamps.

## Data model

| Table           | Notes |
|-----------------|-------|
| `users`         | email (unique, lower-cased), name, Argon2 hash |
| `auth_sessions` | token digest, `expires_at` (sliding, 30 days by default) |
| `categories`    | global reference data seeded by migration. `kind` = `expense` (Food, Transport…) or `income` (Salary, Freelance…) |
| `transactions`  | one table for both types: `type`, `amount NUMERIC(12,2)`, `category_id`, `description`, `occurred_on DATE`, `payment_method` (expenses only), `recurring_rule_id` |
| `recurring_rules` | monthly template: amount, category, `day_of_month`, `next_run_on`, `last_run_on`, `is_active` |

Expenses and income share a table because they share every column and are nearly always read
together (history, recent activity, monthly totals). A composite foreign key
`(category_id, type) → categories(id, kind)` means **Postgres itself** rejects an expense filed
under an income source, or the reverse. `amount > 0` is a check constraint, and so is
"income has no payment method".

## Recurring entries

There's no scheduler. When a request reads transaction data (dashboard, history, insights),
the backend first creates every occurrence that's due up to today in `APP_TIMEZONE`, then
answers. Totals are therefore always current, with no cron or worker to run. Generation is
idempotent: rows are locked with `FOR UPDATE SKIP LOCKED`, and a unique index on
`(recurring_rule_id, occurred_on)` makes a duplicate impossible. A rule on the 31st uses the
last day of shorter months without drifting. Pausing and resuming doesn't backfill the
missed months. Deleting a rule keeps the transactions it already created.

## API

Interactive docs (development only): <http://localhost:8000/api/docs>

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Sign in and set the session cookie |
| POST | `/api/auth/logout` | Revoke the session and clear the cookie |
| GET | `/api/auth/me` | Current user |
| GET | `/api/categories?kind=` | Expense categories and income sources |
| GET | `/api/dashboard/monthly?year=&month=&today=` | Totals, today, comparison with last month, category breakdown, and recent activity in one call |
| GET | `/api/history/monthly?year=&month=&type=` | A month of transactions grouped by day, with day and month totals |
| GET | `/api/insights/monthly?year=&month=&today=` | Daily spending, average, highest day, no-spend days, payment methods, and a 6-month trend |
| GET/POST | `/api/recurring` | List or create monthly recurring entries |
| GET/PATCH/DELETE | `/api/recurring/{id}` | Read, edit, pause/resume (`is_active`), or delete |
| GET | `/api/transactions?type=&year=&month=&cursor=&limit=` | Newest first, cursor-paginated |
| POST | `/api/transactions` | Create an expense or income entry |
| GET/PATCH/DELETE | `/api/transactions/{id}` | Read, partially update, or delete (owner only, else 404) |
| GET | `/api/health` | Liveness and DB check |

Errors always look like
`{"error": {"code": "validation_error", "message": "…", "fields": {"amount": "…"}}}`,
with status codes 401 (not signed in), 404 (missing or not yours), 422 (validation),
429 (login throttled), and 500 (generic message only; details go to server logs).

## Local setup

Requirements: Python 3.13+, PostgreSQL 14+. Every command runs from `backend/app/` (the folder
with `alembic.ini` and `.env`) using the `backend/myenv` virtualenv.

```bash
createdb expense_tracker                      # or use Supabase, see below
cd backend
python3 -m venv myenv                         # once
source myenv/bin/activate
cd app
pip install -r requirements-dev.txt           # runtime deps + ruff
cp .env.example .env                          # then edit DATABASE_URL
python test_db_connection.py                  # optional: checks DATABASE_URL works
alembic upgrade head                          # creates tables and seeds categories
python -m app.seed.manage_users create-user --email you@example.com --name "Your Name"
uvicorn app.main:app --reload --port 8000
```

There is no public sign-up. To change a password (this signs out every session):
`python -m app.seed.manage_users set-password --email you@example.com`.

## Hosting the database on Supabase

The database can live on Supabase instead of a local Postgres. Only `DATABASE_URL` changes.
Use the **Session pooler** connection string (port 5432) with `?sslmode=require`. The
Transaction pooler (6543) doesn't support the prepared statements psycopg uses. Then run
`alembic upgrade head` as usual.

Supabase exposes tables in `public` through its auto-generated Data API. This app never uses
that API, so migration `0004` enables row level security with no policies on every table and
revokes the `anon`/`authenticated` roles. The backend connects as the table owner and is
unaffected. **Any migration that adds a table must also enable RLS on it.** Supabase's security
advisor then reports only the expected "RLS enabled, no policy" notices.

## Environment variables (`backend/app/.env`)

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | none (required) | `postgresql://user:pass@host:5432/db` |
| `ENVIRONMENT` | `development` | `production` disables `/api/docs` and the OpenAPI schema |
| `APP_TIMEZONE` | `Asia/Kolkata` | Defines "today" for generating recurring entries |
| `COOKIE_SECURE` | `true` | Must be `true` behind HTTPS. Set `false` only for local http |
| `SESSION_TTL_DAYS` | `30` | Sliding session lifetime |
| `SESSION_COOKIE_NAME` | `et_session` | Keep in sync with the frontend |
| `CORS_ORIGINS` | `[]` | Only if a browser calls the API directly, bypassing the proxy |
| `LOGIN_MAX_FAILURES` / `LOGIN_FAILURE_WINDOW_MINUTES` | `5` / `15` | Login throttle |

## Commands (from `backend/app/`, virtualenv active)

| Task | Command |
|---|---|
| Dev server | `uvicorn app.main:app --reload` |
| Lint | `ruff check .` |
| Format | `ruff format .` |
| DB connectivity check | `python test_db_connection.py` |

## Migrations

```bash
alembic upgrade head                              # apply
alembic revision --autogenerate -m "describe it"  # after changing models; review the file
alembic downgrade -1                              # roll back one
alembic check                                     # verify models and migrations agree
```

Every schema change goes through a migration. Never edit the production schema by hand.

## Project structure

```
API_REFERENCE.md       frontend integration guide for every endpoint
backend/
  myenv/               virtualenv (not committed)
  app/                 application root: run every command from here
    .env / .env.example
    alembic.ini
    alembic/versions/  migrations (0001 schema + categories; 0002 payment methods +
                       recurring; 0003 per-user last payment method + design icons;
                       0004 lock tables against the Supabase Data API)
    requirements.txt / requirements-dev.txt / ruff.toml
    test_db_connection.py
    app/               Python package
      main.py          FastAPI app, error handlers, security headers
      utils.py         calendar/recurrence maths, "today", pagination cursors
      api/api.py       aggregates the routers in api/endpoints/
      api/endpoints/   auth, categories, transactions, recurring, dashboard, history,
                       insights, health
      core/            config, security (hashing, sessions, CurrentUser dependency), errors
      db/              base_class (Base), base (imports all models), session (get_db)
      models/          User, AuthSession, Category, Transaction, RecurringRule
      schemas/         Pydantic request/response models
      services/        *_service.py: business logic and user-scoped queries
      seed/            manage_users (create-user / set-password)
```

## Security notes and known limits

- CSRF: the session cookie is `SameSite=Lax`, so it isn't sent on cross-site
  POST/PATCH/DELETE. Every write needs a JSON body or a non-GET method.
- Ownership: every transaction query filters on the authenticated `user_id`. Another user's ID
  gets a 404, never a 403, so existence isn't leaked.
- API responses are sent with `Cache-Control: no-store`.
- The login throttle is in-memory, per process, and keyed by email. It resets on restart, and
  someone who knows your email can lock you out for 15 minutes. That's acceptable for a
  single-user app. Rate-limit `/api/auth/login` at the reverse proxy too.
- No Content-Security-Policy is set by the app. Add one at the proxy if wanted.
- Tests are not included yet.
