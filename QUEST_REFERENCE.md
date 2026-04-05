# Quest Reference — Production Engineering Hackathon

---

## Critical: Before You Write a Single Line of Code

1. Fork the official template: https://github.com/MLH-Fellowship/PE-Hackathon-Template-2026
2. Log into https://www.mlh-pe-hackathon.com and download the seed files
3. Provision your DigitalOcean Droplet and note the IP

The template is Flask + Peewee + PostgreSQL + uv. Build on top of it, do not replace it.

---

## Reliability Engineering -- TARGET: GOLD

### Bronze
- [ ] pytest test suite, unit tests in isolation
- [ ] GitHub Actions CI running on every commit
- [ ] GET /health returns 200 OK

Verification: CI logs showing green + working /health (ideally against live DO URL).

### Silver
- [ ] 50%+ coverage via pytest-cov
- [ ] Integration tests hitting the API and checking DB state
- [ ] CI blocks deploys on test failure (the deploy-to-DigitalOcean job only runs on green)
- [ ] Documented 404 and 500 handling

Verification: coverage report screenshot + screenshot of blocked deploy in GitHub Actions.

### Gold
- [ ] 70%+ coverage
- [ ] Bad inputs return clean JSON errors, app never crashes
- [ ] Docker restart policy -- kill container on Droplet, it restarts automatically
- [ ] Failure Mode documentation committed

Verification: live demo kill+resurrect on DigitalOcean + garbage input returning JSON error.

### Hidden Score (up to +50 bonus)
- Unknown task_type -> 400 JSON (not HTML, not 500)
- Duplicate idempotency_key -> 409 JSON
- Missing job ID -> 404 JSON (not Flask HTML 404)
- Cancel non-PENDING job -> 409
- All errors share the same shape: {"error": str, "detail": str}

---

## Incident Response -- TARGET: SILVER (GOLD IF TIME ALLOWS)

### Bronze
- [ ] Structured JSON logs with timestamps and log levels
- [ ] /metrics endpoint showing CPU/RAM + job counts
- [ ] Logs viewable without SSH (docker logs accessible via CI or log drain)

### Silver
- [ ] Alerts for Service Down and High Error Rate via Apprise -> Discord
- [ ] Alert fires within 5 minutes
- [ ] Alert config code committed

### Gold (STRETCH -- pre-built, activate with one command)
- [ ] Grafana dashboard with 4 panels: Latency, Traffic, Errors, Saturation
- [ ] Runbook (docs/runbook.md -- already written for Silver)
- [ ] Sherlock Mode: diagnose fake issue using dashboard

---

## Documentation -- TARGET: GOLD

### Bronze
- [ ] README with one-command setup + live DO URL
- [ ] Architecture diagram
- [ ] API docs

### Silver
- [ ] Deploy guide (DigitalOcean Droplet steps + rollback)
- [ ] Troubleshooting guide
- [ ] .env.example with all vars

### Gold
- [ ] docs/runbook.md (Service Down + High Error Rate)
- [ ] docs/decisions.md (why template, why ARQ, why DO, etc.)
- [ ] docs/capacity.md

---

## Submission Checklist

- [ ] Demo video 2 minutes or less
- [ ] Starts with "Production Engineering Hackathon"
- [ ] Public GitHub repo (forked from template)
- [ ] Repo and video stay public post-event
- [ ] Devpost registration complete
- [ ] MLH event page check-in complete
- [ ] Email matches on both platforms
- [ ] Video recorded during hackathon weekend
- [ ] Seed files used (schema matches what platform provides)
- [ ] Live DigitalOcean URL working at submission time
- [ ] At least one teammate (solo projects not prize-eligible)
