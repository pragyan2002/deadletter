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
- test job runs first,
- deploy job runs only after tests pass on `main`.

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

See [`.env.example`](.env.example) for full list. Important values:
- `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`
- `DISCORD_WEBHOOK_URL`
- `PROMETHEUS_ENABLED`
- `LOG_LEVEL`

---

## Team

**Team name:** deadletter

Built for the MLH Production Engineering Hackathon.
