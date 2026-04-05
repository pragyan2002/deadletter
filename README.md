# deadletter — Production Engineering Hackathon

A production-focused **URL Shortener with an immutable Event Audit Log** built with **Flask + Peewee + PostgreSQL**.

This project is designed around reliability and operability requirements from the MLH Production Engineering Hackathon:
- predictable JSON error handling,
- transactional URL mutation + audit event writes,
- CI gatekeeping before deploy,
- incident-response docs and observability hooks,
- CLI-first operations (no browser UI required).

---

## Architecture at a glance

- **API:** Flask
- **ORM:** Peewee
- **DB:** PostgreSQL 17
- **CLI:** Typer + Rich
- **Packaging/runtime:** `uv`
- **Containerization:** Docker + Docker Compose
- **Optional observability overlay:** Prometheus + Grafana

Core data model:
- `users`
- `urls`
- `events` (append-only audit log of URL mutations)

---

## Key behaviors

- Create short URLs with a generated 6-character alphanumeric short code.
- Redirect active short codes via `GET /r/<short_code>`.
- Soft-delete URLs (`is_active=false`) instead of hard delete.
- Every URL mutation creates an event entry (`created`, `updated`, `deleted`) in the same DB transaction.
- Consistent JSON errors (`{"error": "...", "detail": "..."}`) for API failures.

---

## Quick start (local)

### 1) Prerequisites
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker + Docker Compose

### 2) Install dependencies
```bash
uv sync
```

### 3) Configure environment
```bash
cp .env.example .env
```

### 4) Start services
```bash
docker compose up -d
```

### 5) Verify health
```bash
curl http://localhost:5000/health
# {"status":"ok"}
```

---

## API overview

Base URL: `http://localhost:5000`

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health |
| GET | `/metrics` | CPU/RAM + app counters |
| POST | `/users` | Create user |
| GET | `/users/<user_id>` | User + URLs |
| POST | `/urls` | Create short URL + `created` event |
| GET | `/urls` | List URLs (filters supported) |
| GET | `/urls/<short_code>` | URL details + event history |
| PUT | `/urls/<short_code>` | Update URL + `updated` event |
| DELETE | `/urls/<short_code>` | Soft-delete URL + `deleted` event |
| GET | `/r/<short_code>` | Redirect if active |
| GET | `/events` | List/filter events |

Full contract/examples: [`docs/api.md`](docs/api.md)

---

## CLI usage

The CLI is the primary interaction surface.

```bash
python cli.py shorten --url https://example.com --title "Example" --user 1
python cli.py redirect <short_code>
python cli.py inspect <short_code>
python cli.py list --active
python cli.py delete <short_code> --reason user_requested
python cli.py events --url <short_code>
python cli.py dashboard
python cli.py health
python cli.py metrics
```

---

## Testing

Run all tests:
```bash
uv run pytest
```

Current tests include:
- unit validation tests,
- integration tests for URL lifecycle,
- redirect/inactive/missing behaviors,
- error-shape checks.

---

## Deployment

DigitalOcean deployment guide: [`docs/deploy.md`](docs/deploy.md)

CI workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- push trigger runs tests on all branches (`**`) so feature branches get immediate CI feedback,
- pull requests targeting `main` also run tests to keep pre-merge visibility,
- deploy job stays gated by `needs: test` and runs only for `push` events on `main`.

---

## Observability and incident response

- Metrics endpoint: `GET /metrics`
- Optional Prometheus + Grafana stack:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
  ```
- Operational docs:
  - [`docs/runbook.md`](docs/runbook.md)
  - [`docs/failure-modes.md`](docs/failure-modes.md)
  - [`docs/capacity.md`](docs/capacity.md)
  - [`docs/decisions.md`](docs/decisions.md)

---

## Project structure

```text
deadletter/
├── app/                     # Flask app, routes, models, validation, alerting
├── tests/                   # Unit + integration tests
├── docs/                    # API, deploy, runbook, decisions, capacity, failure modes
├── observability/           # Prometheus + Grafana configs/dashboards
├── .github/workflows/       # CI/CD
├── cli.py                   # Rich/Typer CLI
├── migrate.py               # DB table creation + optional seed loading
├── docker-compose.yml
└── docker-compose.observability.yml
```

---

## Environment variables

The app and CLI support the following environment variables.

| Variable | Required? | Default | Example | Where used |
|---|---|---|---|---|
| `DATABASE_URL` | Optional | _(empty)_ | `postgres://postgres:postgres@localhost:5432/deadletter` | `app/database.py` (highest-priority DB config) |
| `DATABASE_ENGINE` | Optional | _(empty in code)_ | `postgres` | `app/database.py` (fallback selector when `DATABASE_URL` is unset) |
| `DATABASE_NAME` | Optional | `hackathon_db` | `deadletter` | `app/database.py` (Postgres fallback mode) |
| `DATABASE_HOST` | Optional | `localhost` | `postgres` | `app/database.py` (Postgres fallback mode) |
| `DATABASE_PORT` | Optional | `5432` | `5432` | `app/database.py` (Postgres fallback mode) |
| `DATABASE_USER` | Optional | `postgres` | `postgres` | `app/database.py` (Postgres fallback mode) |
| `DATABASE_PASSWORD` | Optional | `postgres` | `postgres` | `app/database.py` (Postgres fallback mode) |
| `SQLITE_PATH` | Optional | `deadletter.db` | `/data/deadletter.db` | `app/database.py` (SQLite fallback mode) |
| `API_URL` | Optional | `http://localhost:5000` | `http://127.0.0.1:5000` | `cli.py` (CLI API base URL) |
| `DISCORD_WEBHOOK_URL` | Optional | _(empty)_ | `https://discord.com/api/webhooks/<id>/<token>` | `app/alerting.py` (enables/disables alerting thread) |
| `PROMETHEUS_ENABLED` | Optional | `false` (compose/runtime default) | `true` | `docker-compose.yml` (container env for observability toggles; not currently read directly in app code) |
| `LOG_LEVEL` | Optional | `INFO` (compose/runtime default) | `DEBUG` | `docker-compose.yml` (container env; app logger currently defaults to `INFO`) |
| `FLASK_DEBUG` | Optional | framework-dependent | `true` | Flask runtime / local development workflow |

Notes:
- `DATABASE_URL` takes precedence over all other database variables.
- If `DATABASE_URL` is not set and `DATABASE_ENGINE=postgres`, Postgres fallback variables are used.
- If neither applies, SQLite is used with `SQLITE_PATH`.

---

## Team

**Team name:** deadletter

Built for the MLH Production Engineering Hackathon.
