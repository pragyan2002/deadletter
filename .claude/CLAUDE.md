# CLAUDE.md — deadletter / Production Engineering Hackathon

## What This Project Is

A production-grade **URL Shortener with Event Audit Log** built on the official MLH PE
Hackathon template (Flask + Peewee + PostgreSQL + uv). The schema is defined by the seed
files provided on the MLH platform and must not deviate from it.

The app shortens URLs, tracks redirects, and logs every mutation as an immutable event.
The production engineering work -- tests, CI/CD, chaos engineering, structured logging,
alerting, observability -- is the actual submission. The URL shortener is the vehicle.

The entire interaction surface is a CLI built with Rich + Typer. No browser UI.
The app is deployed live on a DigitalOcean Droplet.

**Team name:** deadletter
**Repo:** github.com/pragyan2002/deadletter

---

## The Schema (from seed files -- do not deviate)

### users
| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | auto-increment |
| username | varchar | e.g. `urbanwindow57` |
| email | varchar | |
| created_at | datetime | |

### urls
| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | auto-increment |
| user_id | integer FK | references users |
| short_code | varchar(6) | unique, e.g. `HOE5E` |
| original_url | text | |
| title | varchar | |
| is_active | boolean | True/False |
| created_at | datetime | |
| updated_at | datetime | manual update required (no auto-trigger in Peewee) |

### events
| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | auto-increment |
| url_id | integer FK | references urls |
| user_id | integer FK | references users |
| event_type | varchar | `created` / `updated` / `deleted` |
| timestamp | datetime | |
| details | JSONB | shape varies by event_type |

### details shapes
- `created`: `{"short_code": "...", "original_url": "..."}`
- `updated`: `{"field": "original_url", "new_value": "..."}`
- `deleted`: `{"reason": "policy_cleanup" | "user_requested" | "duplicate"}`

---

## Peewee Models (exact -- do not change field names or table names)

```python
# app/models/user.py
from peewee import CharField, DateTimeField
from app.database import BaseModel
from datetime import datetime

class User(BaseModel):
    username = CharField()
    email = CharField()
    created_at = DateTimeField(default=datetime.utcnow)
    class Meta:
        table_name = 'users'

# app/models/url.py
from peewee import CharField, TextField, BooleanField, DateTimeField, ForeignKeyField
from app.database import BaseModel
from app.models.user import User
from datetime import datetime

class Url(BaseModel):
    user = ForeignKeyField(User, backref='urls', column_name='user_id')
    short_code = CharField(max_length=6, unique=True)
    original_url = TextField()
    title = CharField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    class Meta:
        table_name = 'urls'

# app/models/event.py
from peewee import CharField, DateTimeField, ForeignKeyField
from playhouse.postgres_ext import BinaryJSONField
from app.database import BaseModel
from app.models.url import Url
from app.models.user import User
from datetime import datetime

class Event(BaseModel):
    url = ForeignKeyField(Url, backref='events', column_name='url_id')
    user = ForeignKeyField(User, backref='events', column_name='user_id')
    event_type = CharField()   # 'created' | 'updated' | 'deleted'
    timestamp = DateTimeField(default=datetime.utcnow)
    details = BinaryJSONField()
    class Meta:
        table_name = 'events'
```

Key Peewee notes:
- `column_name='user_id'` on FK fields -- prevents Peewee's default `user_id_id` naming
- `updated_at` requires manual update: `url.updated_at = datetime.utcnow()` before `url.save()`
- `BinaryJSONField` from `playhouse.postgres_ext` for JSONB (better indexing than plain JSON)
- No `Job` model -- the seed schema has no job queue

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | 200 OK |
| GET | `/metrics` | CPU, RAM, URL counts, event counts |
| POST | `/users` | Create a user |
| GET | `/users/<user_id>` | Get user + their URLs |
| POST | `/urls` | Create a shortened URL (auto-generates short_code, logs `created` event) |
| GET | `/urls` | List URLs (filterable by user_id, is_active) |
| GET | `/urls/<short_code>` | Get URL details + event history |
| PUT | `/urls/<short_code>` | Update original_url or title (logs `updated` event) |
| DELETE | `/urls/<short_code>` | Soft-delete: sets is_active=False (logs `deleted` event) |
| GET | `/r/<short_code>` | Redirect to original_url (returns 404 if inactive or missing) |
| GET | `/events` | List events (filterable by url_id, event_type) |

---

## Error Response Shape (consistent everywhere, no exceptions)

```json
{"error": "short_code", "detail": "human readable message"}
```

Flask `@app.errorhandler` covers 400, 404, 500. Every route that can fail uses this shape.
Flask's default HTML error pages are completely disabled.

---

## Short Code Generation

Generate a random 6-character alphanumeric code. Check for uniqueness before inserting.
On collision (rare but possible), regenerate. Do not expose internal IDs as short codes.

```python
import random, string

def generate_short_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
```

---

## Event Log Rules (critical for hidden reliability score)

Every mutation to a URL must create a corresponding Event atomically (same DB transaction):
- POST /urls -> creates URL + Event(event_type='created')
- PUT /urls/<code> -> updates URL + creates Event(event_type='updated')
- DELETE /urls/<code> -> soft-deletes URL + creates Event(event_type='deleted')

If the event insert fails, the URL change must also be rolled back. Use `db.atomic()`.

The event log is append-only. Events are never updated or deleted.

---

## Redirect Behavior (hidden reliability score)

`GET /r/<short_code>` must:
- Return 302 redirect to original_url if URL exists AND is_active=True
- Return 404 JSON if short_code does not exist
- Return 404 JSON if URL exists but is_active=False (not a redirect, a proper 404)
- Never return 500 for any input

This is the key behavior judges will test: inactive URLs must not redirect.

---

## Hidden Reliability Score Checklist

- [ ] Duplicate short_code handled: unique constraint + 409 response (not 500)
- [ ] Inactive URL GET /r/<code> returns 404 JSON, not redirect
- [ ] Missing short_code returns 404 JSON, not Flask HTML 404
- [ ] Invalid URL format rejected on create (must start with http:// or https://)
- [ ] Event created atomically with URL mutation (db.atomic())
- [ ] PUT on inactive URL returns 404 (cannot update a deleted URL)
- [ ] DELETE on already-inactive URL returns 409 (already deleted)
- [ ] All errors: `{"error": "short_code", "detail": "human readable"}`
- [ ] DB constraint violations caught as 4xx not 5xx
- [ ] details JSONB shape matches spec exactly per event_type

---

## The Chaos Demo

Kill the Flask container while a redirect is in flight. The container restarts in ~5 seconds
via Docker `restart: always`. The redirect works again immediately after recovery. Show this
in the demo video with `python cli.py dashboard` running so the recovery is visible.

Secondary demo: `DELETE /urls/HOE5E` then `GET /r/HOE5E` -- show it returns 404, not a
redirect to the original URL.

---

## Rich CLI Commands

```bash
python cli.py shorten --url https://example.com --title "Example" --user 1
python cli.py redirect <short_code>    # shows what it would redirect to, or 404
python cli.py inspect <short_code>     # URL details + full event history table
python cli.py list --active            # table of active URLs
python cli.py delete <short_code> --reason user_requested
python cli.py events --url <short_code>  # event log for a URL
python cli.py dashboard                # live: total URLs, active/inactive, events/min
python cli.py health
python cli.py metrics
```

### Visual Design
- URL status: active (green), inactive (dim red strikethrough)
- Event types: created (green), updated (yellow), deleted (red)
- `inspect` shows URL panel at top, event history table below -- this is the hero view
- `dashboard` live layout: URL stats top-left, recent events top-right, log tail bottom
- All JSON details fields syntax-highlighted with `rich.syntax`

---

## Stack

| Layer | Choice |
|-------|--------|
| Framework | Flask (template) |
| ORM | Peewee (template) |
| Package manager | uv (template) |
| Database | PostgreSQL 17 |
| Testing | pytest + Flask test client + pytest-cov |
| Logging | python-json-logger |
| Metrics (Bronze/Silver) | psutil + custom /metrics JSON |
| Metrics (Gold stretch) | prometheus-flask-exporter |
| Visualization (Gold stretch) | Grafana + Prometheus (docker-compose.observability.yml) |
| Alerts | Apprise -> Discord webhook |
| CLI | Rich + Typer |
| CI/CD | GitHub Actions -> DigitalOcean Droplet |
| Containers | Docker + Docker Compose |

No ARQ, no Redis, no job queue. The app is simpler and faster to build because of it.

---

## File Structure

```
/
├── app/
│   ├── __init__.py           # create_app() factory (from template, extended)
│   ├── database.py           # Peewee DatabaseProxy (from template, unchanged)
│   ├── validators.py         # URL format, short_code format, event_type allowlist
│   ├── errors.py             # JSON errorhandlers for 400, 404, 500
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── url.py
│   │   └── event.py
│   └── routes/
│       ├── __init__.py       # register_routes()
│       ├── health.py
│       ├── metrics.py
│       ├── users.py
│       ├── urls.py           # includes /r/<short_code> redirect
│       └── events.py
├── cli.py                    # Rich + Typer CLI
├── migrate.py                # db.create_tables() + seed data loader
├── seeds/                    # seed files from MLH platform (committed)
├── tests/
│   ├── conftest.py           # Flask test client, test DB fixture
│   ├── unit/
│   │   └── test_validators.py
│   └── integration/
│       └── test_urls.py      # covers all reliability scenarios
├── docs/
│   ├── failure-modes.md
│   ├── runbook.md
│   ├── decisions.md
│   ├── deploy.md
│   ├── api.md
│   └── capacity.md
├── observability/
│   ├── prometheus/prometheus.yml
│   └── grafana/
│       ├── provisioning/datasources/prometheus.yml
│       ├── provisioning/dashboards/dashboard.yml
│       └── dashboards/deadletter.json
├── .github/workflows/ci.yml
├── docker-compose.yml        # postgres + api, both restart: always
├── docker-compose.observability.yml
├── Dockerfile
├── pyproject.toml            # uv-managed
├── run.py                    # entry point (from template)
├── .env.example
├── pytest.ini
└── README.md
```

---

## Docker Compose Services

Two services only (no worker, no Redis -- much simpler):
- `postgres`: PostgreSQL 17, `restart: always`
- `api`: Flask app on port 5000, `restart: always`

Observability overlay adds prometheus + grafana when needed.

---

## Environment Variables (.env.example)

```
DATABASE_URL=postgresql://user:password@postgres:5432/deadletter
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
PROMETHEUS_ENABLED=false
LOG_LEVEL=INFO
```

---

## DigitalOcean Deployment

Single Droplet running Docker Compose. Ubuntu 24.04, 2GB RAM.
CI deploys automatically on green tests via `appleboy/ssh-action`.
GitHub secrets needed: `DO_HOST`, `DO_SSH_KEY`.

Live URL for demo: `http://<droplet-ip>:5000`

---

## Claude Code Efficiency Rules

- `/clear` between every session block
- Shift+Tab (plan mode) before any complex scaffold
- Escape immediately if Claude goes wrong direction
- `/compact` when session grows long, with focus hint
- Sonnet for everything; Opus only for initial architecture session
- One-time setup: `unset ANTHROPIC_API_KEY && export DISABLE_NON_ESSENTIAL_MODEL_CALLS=1`
- Batch related file changes into one prompt
- Always include a verification step ("run pytest after, confirm it passes")

---

## Conventions (no exceptions)

- No em dashes anywhere (docs, code comments, commit messages, README)
- All errors: `{"error": "short_code", "detail": "human readable message"}`
- `updated_at` must be set manually before every `url.save()`
- Event log is append-only -- never update or delete events
- All URL mutations wrapped in `db.atomic()` to keep event log consistent
- uv for all package management -- never `pip install` directly