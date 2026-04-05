# API Reference

Base URL: `http://localhost:5000` (or your Droplet IP)

All error responses follow this shape:
```json
{"error": "short_code", "detail": "human readable message"}
```

---

## GET /health

Returns process and database health.

**Response:**
```json
{"status": "ok"}
```

**Degraded response (DB unavailable):**
```json
{"status": "degraded", "detail": "database unavailable: <ExceptionType>"}
```
Status code: `503`.

---

## GET /metrics

Returns system and application metrics.

**Response:**
```json
{
  "cpu_percent": 12.5,
  "memory_used_mb": 512,
  "memory_total_mb": 2048,
  "uptime_seconds": 3600,
  "urls_total": 100,
  "urls_active": 87,
  "urls_inactive": 13,
  "events_total": 423
}
```

---

## POST /users

Create a user.

**Body:**
```json
{"username": "alice", "email": "alice@example.com"}
```

**Response 201:**
```json
{"id": 1, "username": "alice", "email": "alice@example.com", "created_at": "2026-01-01T00:00:00"}
```

---

## GET /users/<user_id>

Get a user and their URLs.

**Response 200:**
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "created_at": "...",
  "urls": [{"short_code": "ABC123", "original_url": "...", ...}]
}
```

**Errors:** 404 if user not found.

---

## POST /urls

Create a shortened URL. Atomically creates a `created` event.

**Body:**
```json
{"original_url": "https://example.com", "title": "Example", "user_id": 1}
```

**Response 201:**
```json
{
  "short_code": "ABC123",
  "original_url": "https://example.com",
  "title": "Example",
  "is_active": true,
  "user_id": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

**Errors:**
- 400 if original_url missing or not http/https
- 400 if title missing
- 400 if user_id missing
- 404 if user not found

---

## GET /urls

List URLs. Optional filters: `?user_id=1`, `?is_active=true`, `?is_active=false`.

---

## GET /urls/<short_code>

Get URL details and full event history.

**Response 200:**
```json
{
  "short_code": "ABC123",
  ...
  "events": [
    {"id": 1, "event_type": "created", "timestamp": "...", "details": {...}, "user_id": 1}
  ]
}
```

**Errors:** 404 if not found.

---

## PUT /urls/<short_code>

Update original_url and/or title. Atomically creates an `updated` event.

**Body:** At least one of:
```json
{"original_url": "https://new.example.com"}
{"title": "New title"}
```

**Errors:**
- 400 if body is empty
- 404 if not found or inactive

---

## DELETE /urls/<short_code>

Soft-delete: sets is_active=False. Atomically creates a `deleted` event.

**Body (optional):**
```json
{"reason": "user_requested"}
```
Reason values: `policy_cleanup`, `user_requested`, `duplicate`. Defaults to `user_requested`.

**Errors:**
- 404 if not found
- 409 if already inactive

---

## GET /r/<short_code>

Redirect to the original URL.

**Response:**
- 302 redirect if active
- 404 JSON if inactive or missing

---

## GET /events

List events. Optional filters: `?url_id=1`, `?short_code=ABC123`, `?event_type=created`.
