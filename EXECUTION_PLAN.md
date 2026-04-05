# Execution Plan — deadletter / Production Engineering Hackathon
## URL Shortener + Event Audit Log (Flask + Peewee + DigitalOcean)

Each session maps to one `/clear` block in Claude Code. Run `/clear` at the start of each.
Use plan mode (Shift+Tab) before complex implementation. Default model: Sonnet.

The project is simpler than the original job queue plan (no ARQ, no Redis, no worker process).
Two Docker services instead of four. This buys time for polish, better tests, and the CLI.

---

## Master Checklist

### Before the Hackathon
- [x] Fork and rename repo to `deadletter`
- [x] Download seed files, commit to `seeds/`
- [x] Install uv locally
- [x] Claude Code setup

### Session 1: Template Onboarding
- [x] Template runs locally
- [x] Schema confirmed against seed files
- [x] Architecture plan reviewed

### Session 2: Models + Routes + Error Handlers
- [x] `app/models/user.py`, `url.py`, `event.py` (exact schema)
- [x] `app/validators.py` (URL format, event_type, short_code)
- [x] `app/errors.py` (JSON errorhandlers for 400, 404, 500)
- [x] `app/routes/urls.py` (all URL endpoints, `db.atomic()`, redirect logic)
- [x] `app/routes/users.py`
- [x] `app/routes/events.py`
- [x] `app/routes/health.py`
- [x] `app/routes/metrics.py`
- [x] `migrate.py`

### Session 3: Docker + CI/CD
- [x] `Dockerfile`
- [x] `docker-compose.yml` (postgres + api, `restart: always`)
- [x] `docker-compose.observability.yml`
- [x] `.github/workflows/ci.yml` (test job + deploy-on-green job)
- [ ] CI `test` job has postgres service defined
- [ ] CI runs `--cov-fail-under=50`
- [ ] DigitalOcean Droplet provisioned and live (`/health` returns 200)
- [ ] `DO_HOST` and `DO_SSH_KEY` GitHub secrets set
- [ ] First manual deploy completed
- [ ] Screenshot: green CI run
- [ ] Screenshot: blocked CI run (broken test)

### Session 4: Tests
- [x] `tests/conftest.py` (SQLite in-memory fixture)
- [x] `tests/unit/test_validators.py`
- [x] `tests/integration/test_urls.py` (all reliability scenarios)
- [ ] All tests passing (`pytest` green)
- [ ] Coverage >= 70% (`--cov-fail-under=70`)

### Session 5: Observability
- [x] `docker-compose.observability.yml`
- [x] `observability/prometheus/prometheus.yml`
- [x] `observability/grafana/provisioning/` (datasource + dashboard provisioning)
- [ ] `app/logging_config.py` (JSON structured logging with python-json-logger)
- [ ] Request logging middleware in `app/__init__.py` (method, path, status_code, duration_ms)
- [ ] `app/alerts.py` (Apprise -> Discord webhook)
- [ ] `POST /admin/test-alert` endpoint
- [ ] 500 errorhandler fires Discord alert
- [ ] Optional Prometheus support via `PROMETHEUS_ENABLED=true`
- [ ] Grafana dashboard built (4 panels) and exported to `observability/grafana/dashboards/deadletter.json`
- [ ] Discord alert tested (stop postgres, wait, confirm notification)

### Session 6: Rich CLI
- [x] `cli.py` (Typer + Rich)
- [ ] All commands verified working: `shorten`, `redirect`, `inspect`, `list`, `delete`, `events`, `dashboard`, `health`, `metrics`
- [ ] `inspect <code>` shows URL panel + colored event history table
- [ ] `dashboard` runs for 2+ minutes with live refresh

### Session 7: Documentation
- [x] `docs/failure-modes.md`
- [x] `docs/runbook.md`
- [x] `docs/decisions.md`
- [x] `docs/deploy.md`
- [x] `docs/api.md`
- [x] `docs/capacity.md`
- [x] `README.md`

### Session 8: Demo Video
- [ ] Practice run completed
- [ ] Chaos demo: container kill + recovery visible on dashboard
- [ ] Delete + redirect-returns-404 demo recorded
- [ ] GitHub Actions green/blocked screenshots in video
- [ ] Discord notification shown
- [ ] Video uploaded to submission

### Stretch: Grafana Incident Response (Gold)
- [ ] Prometheus + Grafana overlay running with traffic
- [ ] 4-panel dashboard screenshot captured
- [ ] "Sherlock Mode" incident demo (stop postgres, observe error spike, find root cause in logs)

---

## Remaining Work (Priority Order)

1. **DigitalOcean deployment** -- Droplet provisioned, secrets set, app live
2. **Observability gap** -- `logging_config.py`, `alerts.py`, Discord alert, request middleware
3. **CI fixes** -- add postgres service, add `--cov-fail-under=50`
4. **Tests** -- verify all pass, confirm 70%+ coverage
5. **CLI verification** -- run each command end-to-end against live server
6. **Grafana dashboard** -- build 4 panels, export JSON
7. **Demo video** -- record and upload

---

## Before the Hackathon Starts

1. Fork: https://github.com/MLH-Fellowship/PE-Hackathon-Template-2026
2. Rename repo to `deadletter`
3. Log into https://www.mlh-pe-hackathon.com, download seed files, commit to `seeds/`
4. Provision DigitalOcean Droplet (Ubuntu 24.04, 2GB RAM), install Docker
5. Add GitHub secrets: `DO_HOST`, `DO_SSH_KEY`
6. Install uv locally: `curl -LsSf https://astral.sh/uv/install.sh | sh`
7. Claude Code setup: `unset ANTHROPIC_API_KEY && export DISABLE_NON_ESSENTIAL_MODEL_CALLS=1`

---

## Session 1: Template Onboarding + Architecture (45 min)
**Goal:** Template runs locally, schema confirmed, plan reviewed.

Use Opus for this session only. Switch to Sonnet after.

```
"I am building a URL shortener with event audit log for the MLH PE Hackathon on top of
this Flask + Peewee template. The schema is fixed by seed files. Here are the three
models: [paste models from CLAUDE.md]. Here is the endpoint plan: [paste API table].

Review and confirm: (1) anything in the template that conflicts with these models,
(2) whether BinaryJSONField from playhouse.postgres_ext works with the template's DB
setup, (3) any Peewee gotchas with the column_name FK pattern. Do not write code yet."
```

Then run the template to confirm it works:
```bash
uv sync
cp .env.example .env
docker compose up -d postgres
uv run migrate.py   # will write this in Session 2
uv run run.py
curl http://localhost:5000/health
```

Switch to Sonnet: `/model sonnet`

**Run `/clear` before Session 2.**

---

## Session 2: Models + Routes + Error Handlers (1.5 hours)
**Goal:** All endpoints working, correct error shapes everywhere.

Use plan mode (Shift+Tab) first:
```
"Plan the implementation of a Flask URL shortener with these endpoints: [paste API table
from CLAUDE.md]. The models are fixed: [paste models]. Plan the file structure within
app/ before writing any code."
```

After approving plan, implement in this order:

**Prompt 1 -- Models and validators:**
```
"Create app/models/user.py, app/models/url.py, app/models/event.py using the exact
Peewee model definitions in CLAUDE.md. Create app/validators.py with:
- validate_url(url): must start with http:// or https://, return error dict or None
- validate_event_type(t): must be 'created'/'updated'/'deleted'
- validate_short_code(code): must be 6 chars alphanumeric
Create app/errors.py with @app.errorhandler for 400, 404, 500 -- all return
{"error": str, "detail": str} JSON, never HTML."
```

**Prompt 2 -- Core routes:**
```
"Create app/routes/urls.py with all URL endpoints. Critical requirements:
- POST /urls: generate short_code, insert Url + Event(event_type='created') in db.atomic()
- PUT /urls/<code>: update url + insert Event(event_type='updated') in db.atomic(),
  set updated_at=datetime.utcnow() manually, return 404 if inactive
- DELETE /urls/<code>: set is_active=False + insert Event(event_type='deleted') in
  db.atomic(), return 409 if already inactive
- GET /r/<code>: 302 redirect if active, 404 JSON if inactive or missing (never redirect
  an inactive URL -- this is the most important behavior)
- Duplicate short_code: catch peewee.IntegrityError, return 409 JSON"
```

**Prompt 3 -- Remaining routes:**
```
"Create app/routes/users.py (POST /users, GET /users/<id>),
app/routes/events.py (GET /events with url_id and event_type filters),
app/routes/health.py (GET /health -> {"status": "ok"}),
app/routes/metrics.py (GET /metrics -> psutil CPU/RAM + URL counts from DB).
Wire all blueprints in app/routes/__init__.py.
Create migrate.py that runs db.create_tables([User, Url, Event], safe=True)
and loads seed data from seeds/ if tables are empty."
```

Test manually:
```bash
docker compose up -d
uv run migrate.py
# Create a user, shorten a URL, redirect, delete, confirm 404 on redirect
curl -X POST localhost:5000/urls -d '{"user_id":1,"original_url":"https://example.com","title":"test"}'
# Note the short_code, then:
curl -L localhost:5000/r/<short_code>   # should redirect
curl -X DELETE localhost:5000/urls/<short_code> -d '{"reason":"user_requested"}'
curl localhost:5000/r/<short_code>      # should return 404 JSON, not redirect
```

**Done when:** All endpoints work. Inactive URL returns 404, not redirect. Events are created.

**Run `/clear` before Session 3.**

---

## Session 3: Docker + DigitalOcean Deploy + CI (1 hour)
**Goal:** App live on DigitalOcean, CI deploys only on green tests.

**Prompt 1 -- Dockerfile:**
```
"Write a Dockerfile for this Flask + Peewee app using the uv base image:
FROM ghcr.io/astral-sh/uv:python3.12-bookworm
Install with RUN uv sync --frozen. Entry point: uv run run.py.
Write docker-compose.yml with postgres:17 and api services, both restart: always.
Add a healthcheck to the api service that hits /health."
```

**Prompt 2 -- CI/CD:**
```
"Write .github/workflows/ci.yml with two jobs:
1. 'test': triggers on push and PR. Services: postgres:17. Runs uv sync then
   uv run pytest --cov=app --cov-fail-under=50. Fails if pytest fails.
2. 'deploy': runs only after 'test' passes, only on push to main. Uses
   appleboy/ssh-action@v1 with DO_HOST and DO_SSH_KEY secrets to SSH in and run:
   cd /app && git pull && docker compose up -d --build
This is the Silver 'Gatekeeper' requirement: failed tests block production deploys."
```

Deploy manually the first time:
```bash
ssh root@<droplet-ip>
git clone https://github.com/pragyan2002/deadletter /app
cd /app && cp .env.example .env   # fill in DATABASE_URL etc.
docker compose up -d
curl http://<droplet-ip>:5000/health
```

**Done when:** Live URL returns 200. Break a test, confirm CI blocks deploy. Fix it, confirm
auto-deploy runs. Screenshot both states for submission.

**Run `/clear` before Session 4.**

---

## Session 4: Tests (1.5 hours)
**Goal:** 70%+ coverage, all reliability scenarios verified.

**Prompt 1 -- conftest and unit tests:**
```
"Write tests/conftest.py: Flask test client fixture using app.test_client(), test
database using SQLite (override DATABASE_URL in test config), tables created and
torn down per test. Write tests/unit/test_validators.py:
- valid URL accepted
- URL without http:// rejected
- valid event_type accepted
- unknown event_type rejected
- short_code exactly 6 chars accepted, 5 chars rejected
Run pytest tests/unit/ and confirm pass."
```

**Prompt 2 -- integration tests:**
```
"Write tests/integration/test_urls.py covering:
- POST /urls valid -> 201, short_code in response, event created
- POST /urls duplicate short_code -> 409 JSON (mock or force collision)
- POST /urls invalid URL format -> 400 JSON
- GET /r/<code> active -> 302
- GET /r/<code> inactive -> 404 JSON (not redirect)
- GET /r/<code> missing -> 404 JSON
- PUT /urls/<code> active -> 200, updated event created, updated_at changed
- PUT /urls/<code> inactive -> 404 JSON
- DELETE /urls/<code> active -> 200, deleted event created, is_active=False
- DELETE /urls/<code> already inactive -> 409 JSON
- GET /urls/<code> -> event history included
- GET /health -> 200
- GET /metrics -> has cpu_percent, memory_used_mb, url counts (active/inactive/total), event counts

For each test include a comment explaining which reliability property it verifies.
Run pytest tests/integration/ and fix all failures before continuing."
```

**Prompt 3 -- coverage gap:**
```
"Run pytest --cov=app --cov-report=term-missing. If below 70%, show me which lines
in app/routes/urls.py are uncovered and write tests to cover them."
```

**Done when:** pytest passes, 70%+ coverage. Screenshot for submission.

**Run `/clear` before Session 5.**

---

## Session 5: Observability (1.5 hours)
**Goal:** JSON logs, /metrics live, Discord alert fires, Grafana overlay committed.

**Prompt 1 -- Logging and alerts:**
```
"Add structured JSON logging to app/logging_config.py using python-json-logger.
Each entry: timestamp, level, component, message. Add Flask before/after request
middleware logging method, path, status_code, duration_ms. Write app/alerts.py
using Apprise: send_alert(title, body) posts to DISCORD_WEBHOOK_URL. Add
POST /admin/test-alert endpoint. Add an alert on 500 errors (hook into the 500
errorhandler in errors.py)."
```

**Prompt 2 -- Prometheus overlay:**
```
"Add optional Prometheus support. When PROMETHEUS_ENABLED=true, use
prometheus-flask-exporter. Add with: uv add prometheus-flask-exporter.
Create observability/prometheus/prometheus.yml scraping api:5000/metrics every 15s.
Create observability/grafana/provisioning/ files for datasource and dashboard
auto-load. Create docker-compose.observability.yml adding prometheus and grafana.
Leave the dashboard JSON empty for now."
```

Build Grafana dashboard in the UI after spinning up the overlay:
```bash
PROMETHEUS_ENABLED=true docker compose -f docker-compose.yml \
  -f docker-compose.observability.yml up -d
# generate some traffic: run CLI commands, curl redirects
# open localhost:3000, build 4 panels:
#   1. Request latency p50/p95
#   2. Requests/sec
#   3. Error rate (4xx+5xx)
#   4. Active URLs count (from /metrics JSON or custom gauge)
# export dashboard JSON -> observability/grafana/dashboards/deadletter.json
```

Test Discord alert: `docker compose stop postgres`, wait 5 minutes, confirm notification.

**Done when:** Logs are JSON, /metrics returns data, Discord fires, Grafana overlay works.

**Run `/clear` before Session 6.**

---

## Session 6: Rich CLI (1 hour)
**Goal:** All CLI commands working. `inspect` and `dashboard` look great on camera.

Use plan mode (Shift+Tab) first:
```
"Plan cli.py using Rich + Typer against a Flask API at API_URL env var
(default http://localhost:5000). Commands: shorten, redirect, inspect, list, delete,
events, dashboard, health, metrics.

Key views:
- inspect <code>: URL panel showing all fields (status colored green/red), then event
  history table with event_type colored (created=green, updated=yellow, deleted=red),
  details JSONB syntax-highlighted
- dashboard: rich.Live layout, refreshes every 2s:
    top-left: stats panel (total URLs, active, inactive, total events)
    top-right: table of 10 most recently created/updated URLs with status badge
    bottom: last 5 events as a scrolling log
- list: table with short_code, title, original_url (truncated), status badge, created_at

Show the plan before writing code."
```

Implement in two passes:
1. Simple: health, metrics, shorten, redirect, list, delete, events
2. Live: inspect (static but rich), dashboard (rich.Live)

**Done when:** `inspect HOE5E` shows URL + event history. Dashboard runs for 2 minutes.

**Run `/clear` before Session 7.**

---

## Session 7: Documentation (45 min)
**Goal:** All docs committed.

One prompt per file:

```
"Write docs/failure-modes.md. Cover exactly these scenarios with the precise behavior
for each: inactive URL redirect attempt, duplicate short_code, invalid URL format on
create, PUT on inactive URL, DELETE on already-inactive URL, DB connection lost during
atomic transaction, container crash mid-redirect. SRE style -- specific enough that an
on-call engineer knows exactly what to expect."
```

```
"Write docs/runbook.md with two runbooks: 'Service Down' and 'High Error Rate'.
Step-by-step for a 3am engineer. Each includes: what the alert means, step 1 (check
docker ps on Droplet), step 2 (check docker logs), step 3 (check DB connection),
recovery steps, rollback procedure (git revert + docker compose up --build)."
```

```
"Write docs/decisions.md: why Flask + Peewee (required template), why no job queue
(seed schema defines URL shortener, not queue), why event log atomicity with db.atomic(),
why soft deletes on URLs, why DigitalOcean Droplet over App Platform, why Rich CLI
over web UI."
```

```
"Write README.md: one-command setup (docker compose up), what deadletter does, ASCII
architecture diagram (browser -> Flask -> Postgres, CLI -> Flask), quick start showing
3 CLI commands, link to live DigitalOcean URL."
```

Write manually (faster):
- `docs/deploy.md`: Droplet setup steps + rollback
- `docs/api.md`: endpoint list with curl examples
- `docs/capacity.md`: single Droplet estimate from /metrics

---

## Session 8: Demo Video (30 min)
**Goal:** 2-minute video recorded and uploaded.

**Practice this sequence once before recording:**

1. "Hey, I'm [name] and this is my demo for the Production Engineering Hackathon."
2. Show live URL: `curl http://<droplet-ip>:5000/health` returns 200
3. `python cli.py dashboard` -- running against live DO server
4. `python cli.py shorten --url https://anthropic.com --title "Anthropic"` -- appears on dashboard
5. `python cli.py inspect <short_code>` -- URL panel + event history
6. `docker kill <api_container_on_droplet>` via SSH -- show it recover on dashboard
7. `python cli.py redirect <short_code>` after delete -- show 404 JSON, not redirect
8. Show GitHub Actions: green run, blocked run screenshot
9. Show Discord notification
10. Done

**Stretch: Incident Response Gold (if 45+ minutes remain before deadline)**

```bash
PROMETHEUS_ENABLED=true \
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
# Generate traffic with CLI commands
# Screenshot 4-panel Grafana dashboard
# Sherlock Mode: stop postgres, observe error rate spike, show log for root cause
```

---

## Per-Session Token Tips

- Session 2 (routes) and Session 4 (tests) are the highest-token sessions
- Use `/compact Focus on app/routes/urls.py and test results` if sessions grow long
- Session 6 (CLI) has complex Rich layout -- use plan mode, it prevents expensive rewrites
- If a session hits a wall, `/rewind` to last checkpoint rather than asking for a rewrite
