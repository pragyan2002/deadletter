# Execution Plan — Production Engineering Hackathon
## Project: Job Queue / Task Runner API (Flask + Peewee + DigitalOcean)

Each session maps to one `/clear` block in Claude Code. Run `/clear` at the start of each.
Use plan mode (Shift+Tab) before any complex implementation. Default model: Sonnet.

---

## Before the Hackathon Starts (Do These Now)

1. **Fork the official template**: https://github.com/MLH-Fellowship/PE-Hackathon-Template-2026
   Fork it to your GitHub account. Do not clone a fresh repo -- the template is the required
   starting point.

2. **Get the seed files**: Log into https://www.mlh-pe-hackathon.com with MyMLH and download
   the seed files from the platform. These define the database schema and give you test data.
   Save them to `seeds/` in your repo before writing a single line of code.

3. **Provision DigitalOcean Droplet**: Create a Droplet now (don't wait until hour 4).
   - Ubuntu 24.04, Basic, 2GB RAM / 1 vCPU
   - Enable SSH key auth
   - Install Docker + Docker Compose on it: `curl -fsSL https://get.docker.com | sh`
   - Note the IP address

4. **Set GitHub Secrets**: In your forked repo settings, add:
   - `DO_HOST`: your Droplet IP
   - `DO_SSH_KEY`: your private SSH key content

5. **Install uv locally**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

6. **One-time Claude Code setup**:
   ```bash
   unset ANTHROPIC_API_KEY
   export DISABLE_NON_ESSENTIAL_MODEL_CALLS=1
   ```

---

## Session 1: Template Onboarding + Architecture
**Goal:** Understand the template, plan the job queue additions, run the template locally.

**Claude Code approach:**
Start with Opus for this session only:
```
"I am building a job queue API for the MLH PE Hackathon on top of this Flask + Peewee
template. Here is the template structure: [paste README from template]. Here is my plan:
[paste relevant sections of CLAUDE.md]. Review the plan and tell me: (1) what parts of
the template I keep unchanged, (2) what I add, (3) any conflicts between Peewee and my
data model. Do not write any code yet."
```

After review, switch to Sonnet: `/model sonnet`

Then:
```
"Look at the seed files in seeds/. Based on these, propose the Peewee Job model fields
that match the schema. Keep the template's database.py and BaseModel unchanged."
```

Run the template locally to confirm it works before touching anything:
```bash
uv sync
cp .env.example .env
createdb hackathon_db   # or use Docker postgres
uv run run.py
curl http://localhost:5000/health
```

**Done when:** Template runs, /health returns 200, seed files reviewed, architecture confirmed.

**Run `/clear` before Session 2.**

---

## Session 2: Flask Routes + Peewee Models + Validators
**Goal:** All 7 endpoints implemented with proper validation and error handling.

**Claude Code prompt (use plan mode first, Shift+Tab):**
```
"Add a job queue to the Flask template. I need:

1. app/models/job.py: Peewee Job model with these fields: [paste field list from CLAUDE.md].
   idempotency_key must have unique=True at the field level.

2. app/validators.py: validate_job_create(data) function that checks task_type against
   this allowlist: [list]. Returns {"error": str, "detail": str} or None.

3. app/errors.py: JSON error handlers for 400, 404, 500 using @app.errorhandler.
   All must return {"error": str, "detail": str}.

4. app/routes/jobs.py: Blueprint with all 7 endpoints. For duplicate idempotency_key,
   catch peewee.IntegrityError and return 409. For missing job, return 404 JSON.

5. app/routes/health.py: GET /health -> {"status": "ok"}

6. app/routes/metrics.py: GET /metrics -> psutil CPU/RAM + job counts from DB.

7. migrate.py: db.create_tables([Job], safe=True) script.

Wire everything in app/__init__.py and app/routes/__init__.py. Then run:
  uv run migrate.py
  uv run run.py
  curl -X POST localhost:5000/jobs -H 'Content-Type: application/json' \
    -d '{\"task_type\": \"send_email\", \"payload\": {\"to\": \"test@example.com\"}}'
Confirm it returns 201 with a job ID."
```

**Done when:** All endpoints return correct responses. Duplicate idempotency_key returns 409.
Unknown task_type returns 400 JSON (not HTML). Missing job returns 404 JSON.

**Run `/clear` before Session 3.**

---

## Session 3: ARQ Worker + Tasks + Stuck Job Monitor
**Goal:** Jobs process end-to-end, chaos recovery works.

**Claude Code prompt:**
```
"Add an ARQ-based worker to this Flask + Peewee project. The worker connects to
REDIS_URL from env and processes jobs stored in PostgreSQL. Create:

1. worker/tasks.py: async functions for send_email, resize_image, process_csv,
   generate_report, send_webhook. Each does asyncio.sleep(random.uniform(2, 8)) to
   simulate work and has 20% random failure rate. Each marks the job PROCESSING on
   start (update DB), COMPLETED on success, FAILED on error (increment retry_count,
   requeue if under max_retries).

2. worker/worker.py: ARQ WorkerSettings connecting to REDIS_URL. on_startup handler
   requeues any PROCESSING jobs left from a previous crash.

3. worker/monitor.py: ARQ cron function running every STUCK_JOB_TIMEOUT_MINUTES that
   finds PROCESSING jobs older than the threshold and requeues them.

Add Dockerfile.worker and the worker service to docker-compose.yml with restart: always."
```

After writing, test end-to-end:
```bash
docker compose up -d
curl -X POST localhost:5000/jobs ... # submit a job
# watch it go PENDING -> PROCESSING -> COMPLETED
docker kill <worker_container>       # chaos test
# wait for monitor, verify requeue
```

**Done when:** Full lifecycle works. Kill/recover cycle confirmed.

**Run `/clear` before Session 4.**

---

## Session 4: Docker Compose + DigitalOcean Deploy
**Goal:** App running live on DigitalOcean, CI deploys on green tests.

**Claude Code prompt (two parts):**

Part 1 -- Docker Compose:
```
"Review docker-compose.yml and confirm all four services (postgres, redis, api, worker)
have restart: always. The api Dockerfile should use the uv base image:
FROM ghcr.io/astral-sh/uv:python3.12-bookworm
and install with RUN uv sync --frozen. Add a healthcheck to the api service."
```

Part 2 -- CI/CD with DigitalOcean deploy gate:
```
"Write .github/workflows/ci.yml with two jobs:
1. 'test': runs on push/PR, spins up postgres:17 and redis:7 services, runs
   uv run pytest --cov=app --cov-fail-under=50. Job fails if pytest fails.
2. 'deploy': runs only after 'test' passes, only on pushes to main. Uses
   appleboy/ssh-action to SSH into DO_HOST with DO_SSH_KEY secret and runs:
   cd /app && git pull && docker compose up -d --build
This means: failed tests block deploys. Green tests deploy automatically."
```

Then deploy manually the first time:
```bash
ssh root@<droplet-ip>
git clone <your-repo> /app
cp /app/.env.example /app/.env  # fill in real values
cd /app && docker compose up -d
curl http://<droplet-ip>:5000/health  # confirm live
```

**Done when:** `curl http://<droplet-ip>:5000/health` returns 200. Push a broken commit,
confirm CI blocks. Push a fix, confirm it auto-deploys.

**Run `/clear` before Session 5.**

---

## Session 5: pytest Unit + Integration Tests
**Goal:** 70%+ coverage, all reliability scenarios tested.

**Claude Code prompt (two passes):**

Pass 1:
```
"Write tests/conftest.py with a Flask test client fixture using app.test_client().
Use a separate SQLite test database by overriding DATABASE_URL in the test config.
Then write tests/unit/test_validators.py testing: valid task types accepted,
unknown task_type returns error dict, missing required fields caught, idempotency_key
is optional. Run pytest tests/unit/ and confirm all pass."
```

Pass 2:
```
"Write tests/integration/test_jobs.py with these cases:
- POST valid job -> 201, job ID in response
- POST duplicate idempotency_key -> 409, error='duplicate_idempotency_key'
- POST unknown task_type -> 400, error field present
- GET existing job -> 200
- GET non-existent job -> 404, error field present
- POST cancel PENDING job -> 200
- POST cancel non-PENDING job -> 409
- GET /stats -> has pending/processing/completed/failed keys
- GET /health -> 200, status='ok'
- GET /metrics -> has cpu_percent, memory_used_mb, jobs_pending keys
Run pytest tests/integration/ and fix any failures before continuing."
```

Pass 3 (if coverage is under 70%):
```
"Run pytest --cov=app --cov-report=term-missing. Show me which lines in app/routes/jobs.py
and app/validators.py are not covered. Write tests to cover them."
```

**Done when:** pytest passes, coverage report shows 70%+. Screenshot for submission.

**Run `/clear` before Session 6.**

---

## Session 6: CI Coverage Gate + Blocked Deploy Screenshot
**Goal:** CI enforces coverage minimum, screenshot the blocked deploy for submission.

- Update ci.yml test job: `--cov-fail-under=70` (was 50 in Session 4)
- Push a deliberate test failure to a branch, screenshot the blocked CI run
- Merge the fix, confirm green
- Screenshot the green run too

**This session is short (30-45 min).** Use remaining time to review the hidden reliability
score checklist in CLAUDE.md and add any missing edge case tests.

**Run `/clear` before Session 7.**

---

## Session 7: Observability (Incident Response Bronze/Silver + Gold Prep)
**Goal:** JSON logs everywhere, /metrics live, Discord alert fires, Grafana overlay ready.

**Claude Code prompt (two halves -- /compact between them):**

Half 1:
```
"Add structured JSON logging to the Flask project using python-json-logger. Configure
in app/logging_config.py. Each log entry must have: timestamp, level, component,
message. Add a @app.before_request and @app.after_request middleware that logs method,
path, status_code, and duration_ms. Add logging to worker/tasks.py: INFO on pickup,
WARN on retry, ERROR on final failure. Write app/alerts.py using Apprise to send
a Discord notification to DISCORD_WEBHOOK_URL. Add POST /admin/test-alert endpoint.
Add an alert call in worker/monitor.py when stale jobs are found."
```

Half 2 (after /compact):
```
"Add optional Prometheus support. When PROMETHEUS_ENABLED=true, use
prometheus-flask-exporter to instrument the app. Add it to pyproject.toml with
uv add prometheus-flask-exporter. Create these observability files:
- observability/prometheus/prometheus.yml: scrape api:5000/metrics every 15s
- observability/grafana/provisioning/datasources/prometheus.yml
- observability/grafana/provisioning/dashboards/dashboard.yml
- docker-compose.observability.yml: adds prometheus + grafana services
Leave the Grafana dashboard JSON for manual creation in the UI."
```

Test Discord alert:
```bash
docker compose stop postgres
# wait 5 minutes, confirm Discord gets a notification
docker compose start postgres
```

Build Grafana dashboard in UI, export JSON, save to
`observability/grafana/dashboards/job-queue.json`:
- Panel 1: Request latency (p50/p95)
- Panel 2: Requests/sec by endpoint
- Panel 3: Error rate (4xx+5xx)
- Panel 4: Queue depth (jobs_pending + jobs_processing)

**Done when:** Discord fires on DB kill. Grafana loads with 4 panels when overlay is active.

**Run `/clear` before Session 8.**

---

## Session 8: Rich CLI
**Goal:** All 8 CLI commands working. Dashboard looks great on camera.

**Claude Code -- use plan mode (Shift+Tab) first:**
```
"Plan cli.py using Rich and Typer that talks to a Flask API running at API_URL env var
(default http://localhost:5000). Commands: submit, watch, dashboard, list, inspect,
cancel, health, metrics. Dashboard uses rich.Live with 3-region Layout: queue stats
panel top-left, recent jobs table top-right, log tail bottom. Status colors: PENDING
yellow, PROCESSING cyan, COMPLETED green, FAILED red bold, CANCELLED dim. Show plan
before writing code."
```

After plan approval, implement in two passes:
1. Simple commands: health, metrics, submit, list, inspect, cancel
2. Live commands: watch (spinner + poll), dashboard (rich.Live layout)

Run the dashboard for 2 minutes with 5-10 jobs cycling through to confirm it looks good.

**Done when:** All 8 commands work. Dashboard is visually polished.

**Run `/clear` before Session 9.**

---

## Session 9: Documentation
**Goal:** All docs committed. README is clean enough to be the submission page.

One prompt per doc (keeps each turn cheap):

```
"Write docs/failure-modes.md documenting these scenarios with exact behavior:
[paste hidden reliability checklist from CLAUDE.md]. SRE style -- specific, not vague."
```

```
"Write docs/runbook.md with two runbooks: Service Down and High Error Rate. Each is
step-by-step for a 3am engineer. Include: what the alert means, step 1, step 2, how
to confirm fix, how to rollback."
```

```
"Write docs/decisions.md: why Flask + Peewee template (required by hackathon), why ARQ
over Celery, why idempotency keys, why stuck job monitor, why Apprise, why Rich CLI,
why DigitalOcean Droplet over App Platform."
```

```
"Write README.md: one-command setup (docker compose up), what the app does, ASCII
architecture diagram of the 4 services + DigitalOcean deployment, quick start showing
3 CLI commands, link to live URL on DigitalOcean."
```

Write manually (faster than prompting):
- `docs/deploy.md`: Droplet setup steps + rollback (git revert + docker compose up)
- `docs/api.md`: endpoint list with examples (copy from Swagger or curl output)
- `docs/capacity.md`: rough estimate from /metrics during load

---

## Session 10: Demo Video
**Goal:** 2-minute video recorded and uploaded.

**Demo sequence (practice this once before recording):**

1. "Hey, I'm [name] and this is my demo for the Production Engineering Hackathon."
2. Show the live DigitalOcean URL in browser: `http://<droplet-ip>:5000/health` returns 200
3. `python cli.py dashboard` -- live dashboard running against DO server
4. `python cli.py submit --type process_csv --payload '{...}'` -- job appears on dashboard
5. `docker kill <worker_container_on_droplet>` via SSH -- job stuck in PROCESSING on dashboard
6. Worker restarts (restart: always), monitor fires, job completes -- recovery on dashboard
7. `python cli.py submit --type invalid_type` -- clean JSON error
8. Show GitHub Actions: green run, then the screenshot of the blocked deploy
9. Show Discord notification screenshot
10. Done

Keep it under 2 minutes. Do not narrate every detail -- let the dashboard speak.

---

## Stretch: Incident Response Gold
**Only if you have 45+ minutes before the submission deadline.**

```bash
# On the Droplet
PROMETHEUS_ENABLED=true \
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# Generate traffic
for i in {1..20}; do
  python cli.py submit --type send_email --payload '{"to": "test@example.com"}'
done

# Open localhost:3000 (or <droplet-ip>:3000 if port is open)
# Confirm 4 panels have data, screenshot

# Sherlock Mode: stop postgres, observe error rate spike, show log for root cause
# Restart postgres, show recovery
```

---

## Token Budget Notes

Highest-cost sessions are 5 (tests, pytest runs multiple times) and 8 (CLI with complex
Rich layout). Use `/compact` proactively in both. If you hit limits mid-session, stay in
the session and compact rather than starting cold -- prompt cache has a 5-minute lifetime.
