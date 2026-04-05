# API Endpoint Matrix

Base URL: `http://localhost:5000` (or your deployment host).

## Response conventions

- **Default success format:** JSON unless endpoint is an HTTP redirect.
- **Error envelope (400/404/409):**
  ```json
  {"error": "bad_request|not_found|conflict", "detail": "human readable message"}
  ```
- **Unhandled errors (500):**
  ```json
  {"error": "internal_error", "detail": "an unexpected error occurred"}
  ```

---

## Health and metrics

| Method + Path | Purpose | Request body / query params | Success response | Error statuses + shapes |
|---|---|---|---|---|
| `GET /health` | Liveness/readiness check with database probe. | None. | `200` → `{"status":"ok"}` when DB check succeeds. If DB is unavailable, this endpoint intentionally returns a degraded payload instead of the standard error envelope. | `503` → `{"status":"degraded","detail":"database unavailable: <ExceptionType>"}`. |
| `GET /metrics` | Runtime/system + app counters (CPU, memory, uptime, URL/event counts). | None. | `200` → `{"cpu_percent": <number>, "memory_used_mb": <int>, "memory_total_mb": <int>, "uptime_seconds": <int>, "urls_total": <int>, "urls_active": <int>, "urls_inactive": <int>, "events_total": <int>}`. | No explicit route-level 4xx errors; unexpected failures follow `500` envelope. |

---

## Users

| Method + Path | Purpose | Request body / query params | Success response | Error statuses + shapes |
|---|---|---|---|---|
| `GET /users` | List users with pagination. | Query: `page` (int, default `1`), `per_page` (int, default `20`). | `200` → array of users: `[{"id", "username", "email", "created_at"}]`. | No explicit route-level 4xx errors; unexpected failures follow `500` envelope. |
| `POST /users` | Create one user. | JSON object: `username` (string, required), `email` (string, required). | `201` → `{"id","username","email","created_at"}`. | `400` invalid/missing body fields; `409` duplicate username/email; plus `500` envelope. |
| `POST /users/bulk` **(Internal/Admin-only)** | Bulk load users from CSV upload or seed file; supports synthetic generation when `users.csv` is missing and `row_count` is provided. Intended for seeding/backfill, not public clients. | Accepts either multipart file upload (`file`) **or** JSON/form fields: `file` (required, must end `.csv`), optional `row_count` (int, only used when `file == "users.csv"` and the seed file is absent). | `201` when rows are imported and new users are created; response includes `Location: /users` and JSON `{"loaded": <int>, "imported": <int>, "row_count": <int>, "file": "<filename>.csv"}`. `200` for no-op imports (for example, zero rows imported). | `400` missing file, invalid extension/path, or missing seed file; plus `500` envelope. |
| `GET /users/<int:user_id>` | Fetch one user plus URLs owned by that user. | Path: `user_id` (int). | `200` → `{"id","username","email","created_at","urls":[{"short_code","original_url","title","is_active","created_at"}]}`. | `404` user not found; plus `500` envelope. |
| `PUT /users/<int:user_id>` | Update user `username` and/or `email`. | Path: `user_id` (int). JSON object with at least one of: `username` (string), `email` (string). | `200` → updated `{"id","username","email","created_at"}`. | `400` non-object body, missing update fields, or invalid types; `404` user not found; `409` duplicate username/email; plus `500` envelope. |
| `DELETE /users/<int:user_id>` | Delete user record. | Path: `user_id` (int). | `200` → `{"id","username","email"}` of deleted user. | `404` user not found; plus `500` envelope. |

---

## URLs and redirects

| Method + Path | Purpose | Request body / query params | Success response | Error statuses + shapes |
|---|---|---|---|---|
| `POST /urls` | Create a short URL for a user and create a `created` event in the same transaction. | JSON object: `original_url` (required string, must start `http://` or `https://`), `title` (required string), `user_id` (required positive int). | `201` → URL object: `{"id","short_code","original_url","title","is_active","user_id","created_at","updated_at"}`. | `400` validation failures; `404` user not found; `409` short-code conflict; plus `500` envelope. |
| `GET /urls` | List URLs with optional filters and optional pagination. | Query: `user_id` (int), `is_active` (`true`/`false`), `page` (int), `per_page` (int). Pagination is only applied when both `page` and `per_page` are provided. | `200` → array of URL objects. | No explicit route-level 4xx errors; unexpected failures follow `500` envelope. |
| `POST /urls/bulk` **(Internal/Admin-only)** | Bulk load URLs from seed CSV file for bootstrapping/backfill. Not intended for public-facing use. | JSON object: `file` (required, `.csv`, path constrained to seed directory). | `200` → `{"loaded": <int>, "file": "<filename>.csv"}`. | `400` missing file, invalid extension/path, or missing file; plus `500` envelope. |
| `GET /urls/<short_code>` | Get URL details and full event history for that URL. | Path: `short_code` (string). | `200` → URL object + `events` array (`id`, `event_type`, `timestamp`, `details`, `user_id`). | `404` short code not found; plus `500` envelope. |
| `GET /urls/<int:url_id>` | ID-based alias for `GET /urls/<short_code>`. | Path: `url_id` (int). | `200` → same as `GET /urls/<short_code>`. | `404` URL id not found (or underlying short code not found); plus `500` envelope. |
| `PUT /urls/<short_code>` | Update URL fields (`original_url`, `title`, optional `is_active`). Creates audit events for `original_url` changes and for deactivation (`is_active=false`). | Path: `short_code` (string). JSON object with at least one of: `original_url` (string, must start `http://` or `https://`), `title` (non-empty string), `is_active` (boolean). | `200` → updated URL object. | `400` non-object body or validation failures; `404` short code missing or already inactive; plus `500` envelope. |
| `PUT /urls/<int:url_id>` | ID-based alias for `PUT /urls/<short_code>`. | Path: `url_id` (int). Same JSON rules as short-code endpoint. | `200` → updated URL object. | `404` URL id not found (or underlying short code unavailable/inactive); `400` validation failures; plus `500` envelope. |
| `DELETE /urls/<short_code>` | Soft-delete URL (`is_active=false`) and create `deleted` event. | Path: `short_code` (string). JSON object optional `reason` (`policy_cleanup`, `user_requested`, `duplicate`; default `user_requested`). | `200` → updated URL object (`is_active=false`). | `400` non-object body or invalid reason; `404` short code not found; `409` already inactive; plus `500` envelope. |
| `DELETE /urls/<int:url_id>` | ID-based alias for `DELETE /urls/<short_code>`. | Path: `url_id` (int). Same optional JSON `reason`. | `200` → updated URL object. | `404` URL id not found (or underlying short code missing); `400` invalid reason/body; `409` already inactive; plus `500` envelope. |
| `GET /r/<short_code>` | Public redirect endpoint. Records `redirected` event then returns HTTP redirect to original URL. | Path: `short_code` (string). | `302` redirect (non-JSON) to `original_url`. | `404` short code missing or inactive; plus `500` envelope. |
| `GET /urls/<short_code>/redirect` | Alias for redirect by short code. | Path: `short_code` (string). | `302` redirect to `original_url`. | `404` short code missing or inactive; plus `500` envelope. |
| `GET /urls/<int:url_id>/redirect` | Alias for redirect by URL id. | Path: `url_id` (int). | `302` redirect to `original_url`. | `404` URL id missing (or mapped short code inactive/missing); plus `500` envelope. |

---

## Events

| Method + Path | Purpose | Request body / query params | Success response | Error statuses + shapes |
|---|---|---|---|---|
| `GET /events` | List events with optional filtering and optional pagination. | Query filters: `url_id` (int), `short_code` (string), `event_type` (`created`,`updated`,`deleted`,`redirected`,`click`). Optional pagination via `page` + `per_page` (both required to paginate). | `200` → array of events: `[{"id","url_id","user_id","event_type","timestamp","details"}]`. | `400` invalid `event_type`; plus `500` envelope. Unknown `short_code` returns `200` with empty array. |
| `POST /events` | Create event record explicitly. | JSON object: `url_id` (required positive int), `user_id` (required positive int), `event_type` (required allowed string), optional `details` (object, default `{}`). | `201` → created event object. | `400` invalid body/fields/type; `404` referenced URL/user not found; plus `500` envelope. |
| `POST /events/bulk` **(Internal/Admin-only)** | Bulk load event rows from seed CSV for seeding/backfill. Not intended for public-facing use. | JSON object: `file` (required, `.csv`, path constrained to seed directory). | `200` → `{"loaded": <int>, "file": "<filename>.csv"}`. | `400` missing file, invalid extension/path, or missing file; plus `500` envelope. |

---

## Notes on public vs internal endpoints

The following are explicitly **internal/admin-only** and should typically be protected behind admin auth, private network controls, or disabled in public deployments:

- `POST /users/bulk`
- `POST /urls/bulk`
- `POST /events/bulk`
