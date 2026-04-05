# Architecture Decisions

## Flask + Peewee (not FastAPI + SQLAlchemy)

**Decision:** Use the MLH hackathon template as-is.
**Reason:** Judges expect the template as the base. Deviating risks point deductions.
**Trade-off:** No automatic request validation (Pydantic). Manual validators.py required.

## Soft delete (is_active=False) instead of hard delete

**Decision:** DELETE /urls/<code> sets is_active=False, does not remove the row.
**Reason:** Preserves event history integrity. Hard delete would orphan events. Also allows the chaos demo (delete then show 404 redirect) without destroying data.

## db.atomic() for all URL mutations

**Decision:** Every POST/PUT/DELETE that touches a URL also writes an Event, wrapped in db.atomic().
**Reason:** If the event write fails, the URL change rolls back. The audit log is always consistent with the URL state. This is a hard requirement for the hidden reliability score.

## Redirects are persisted as first-class events

**Decision:** Use canonical event types `created`, `updated`, `deleted`, `redirected`, and `click`; persist a `redirected` event on every successful `/r/<short_code>` redirect.
**Reason:** Redirects are user-visible access actions and part of the audit trail. Keeping them in the canonical enum makes validation and filtering predictable across `/events`, URL details, and manual event creation.
**Trade-off:** Redirect-heavy URLs generate more event rows and write load. We accept this for audit completeness and consistent semantics.

## Separate env vars for DB (not DATABASE_URL)

**Decision:** Keep template's DATABASE_NAME, DATABASE_HOST, etc. instead of a single DATABASE_URL.
**Reason:** Avoids touching database.py, which the template provides and judges expect unchanged.

## In-memory SQLite for tests (not test Postgres)

**Decision:** Tests use Peewee's SqliteDatabase(':memory:') instead of a test Postgres instance.
**Reason:** No Postgres dependency for CI. Tests run in GitHub Actions without a DB service.
**Trade-off:** BinaryJSONField (JSONB) is Postgres-specific. Tests use a JSON workaround via Peewee's field substitution. Integration tests against real Postgres run manually.

## No ARQ / Redis / job queue

**Decision:** The app is a URL shortener, not a task runner.
**Reason:** Seed files define the actual schema. ARQ would add complexity with no judging value.

## Single Dockerfile (not separate api/worker)

**Decision:** One Dockerfile, two compose services (postgres + api).
**Reason:** No worker process needed. Simpler to build, deploy, and demonstrate.
