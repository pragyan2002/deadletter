# Quest Reference — deadletter / Production Engineering Hackathon

---

## Critical: Before Writing Any Code

1. Fork template: https://github.com/MLH-Fellowship/PE-Hackathon-Template-2026
2. Download seed files from https://www.mlh-pe-hackathon.com (MyMLH login required)
3. Commit seeds to `seeds/` -- the schema is fixed, do not deviate
4. Provision DigitalOcean Droplet

Schema is: `users`, `urls`, `events`. No job queue. URL shortener with event audit log.

---

## Reliability Engineering -- TARGET: GOLD

### Bronze
- [ ] pytest test suite, unit tests in isolation
- [ ] GitHub Actions CI on every commit
- [ ] GET /health returns 200

Verification: CI logs green + /health on live DO URL.

### Silver
- [ ] 50%+ coverage (pytest-cov)
- [ ] Integration tests hitting API and checking DB
- [ ] CI blocks deploy to DigitalOcean on test failure
- [ ] Documented 404 and 500 handling

Verification: coverage screenshot + blocked deploy screenshot in GitHub Actions.

### Gold
- [ ] 70%+ coverage
- [ ] Bad inputs return JSON errors, never crashes, never HTML error pages
- [ ] Docker restart: always -- kill container on Droplet, it recovers
- [ ] docs/failure-modes.md committed

Verification: kill+recover demo on DO + inactive URL returning 404 + failure modes link.

### Hidden Score (up to +50 bonus)
- Inactive URL GET /r/<code> -> 404 JSON (must NOT redirect)
- Missing short_code -> 404 JSON (not Flask HTML)
- Duplicate short_code -> 409 JSON
- Invalid URL format -> 400 JSON
- PUT on inactive URL -> 404 JSON
- DELETE on already-inactive -> 409 JSON
- All mutations create Events atomically (db.atomic())
- All errors: {"error": str, "detail": str}

---

## Incident Response -- TARGET: SILVER (GOLD IF TIME ALLOWS)

### Bronze
- [ ] Structured JSON logs (timestamp, level, component, message)
- [ ] GET /metrics: CPU, RAM, active/inactive URL counts, event counts
- [ ] Logs viewable without SSH (docker logs)

### Silver
- [ ] Discord alert on Service Down + High Error Rate (Apprise)
- [ ] Fires within 5 minutes
- [ ] Alert config code committed

### Gold (STRETCH -- pre-built in Session 5, one command to activate)
- [ ] Grafana dashboard: Latency, Traffic, Errors, Saturation (4 panels)
- [ ] docs/runbook.md (already written for Silver)
- [ ] Sherlock Mode diagnosis demo

Activation: `PROMETHEUS_ENABLED=true docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d`

---

## Documentation -- TARGET: GOLD

### Bronze
- [ ] README: one-command setup + live DO URL
- [ ] Architecture diagram
- [ ] API docs (all endpoints)

### Silver
- [ ] docs/deploy.md: Droplet steps + rollback
- [ ] Troubleshooting guide
- [ ] .env.example with all vars documented

### Gold
- [ ] docs/runbook.md (Service Down + High Error Rate)
- [ ] docs/decisions.md (why template, why event log atomicity, why DO, etc.)
- [ ] docs/capacity.md

---

## Submission Checklist

- [ ] Demo video 2 minutes or less
- [ ] Starts with "Production Engineering Hackathon"
- [ ] Public GitHub repo named `deadletter` forked from template
- [ ] Repo and video public post-event
- [ ] Devpost registration + MLH check-in (emails must match)
- [ ] Video recorded during hackathon weekend
- [ ] Seed files used -- schema matches platform exactly
- [ ] Live DO URL working at submission time
- [ ] At least one teammate (solo not prize-eligible)
- [ ] 18+ for fellowship eligibility
