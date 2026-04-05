# Failure Modes

## Database connection lost

**Symptom:** 500 errors on all routes.
**Cause:** PostgreSQL container restarted or network partition.
**Detection:** /health returns 500; docker compose ps shows postgres unhealthy.
**Recovery:** `docker compose restart postgres`. The api container reconnects automatically on the next request (Peewee reconnects per-request via before_request hook).
**Prevention:** postgres healthcheck in docker-compose.yml with restart: always.

## Short code collision

**Symptom:** 409 on POST /urls (rare).
**Cause:** Two concurrent requests generated the same 6-char code.
**Detection:** Response body contains `{"error": "conflict", ...}`.
**Recovery:** Client retries the POST. The route itself retries code generation before inserting.
**Prevention:** Unique constraint on urls.short_code enforced at DB level.

## Event insert fails after URL write

**Symptom:** URL exists but has no corresponding event in the audit log.
**Cause:** Crash or exception between URL save and Event insert.
**Prevention:** All URL mutations use `db.atomic()` -- if the Event insert fails, the URL change is rolled back. The log stays consistent.

## Redirect to inactive URL

**Symptom:** GET /r/<code> returns 404 instead of redirecting.
**Cause:** URL was soft-deleted (is_active=False). This is expected behavior, not a bug.
**Resolution:** Restore with PUT /urls/<code> if needed (sets is_active back via admin action).

## Disk full (PostgreSQL)

**Symptom:** 500 on writes; postgres logs show no space left.
**Detection:** `df -h` on the Droplet.
**Recovery:** Free space or resize the Droplet volume. Restart postgres.
