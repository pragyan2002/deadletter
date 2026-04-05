# Capacity Planning

## Current environment

- 1 vCPU, 2GB RAM DigitalOcean Droplet
- Single PostgreSQL 17 instance (local to Droplet)
- Flask development server (single process, single thread by default)

## Estimated limits

| Metric | Estimate | Basis |
|--------|----------|-------|
| Requests/sec | ~100-200 | Flask dev server, single thread |
| Concurrent connections | ~50 | Default Flask threading |
| DB connections | 1 per request | Peewee per-request connect/close |
| Storage per URL row | ~500 bytes | short_code + url + title + timestamps |
| Storage per event row | ~300 bytes | event_type + timestamp + details JSON |
| 1M URLs | ~500MB | Row size estimate |
| 3M events | ~900MB | Row size estimate |

## Bottlenecks

1. **Flask dev server**: Not production-grade. For real load, add gunicorn: `gunicorn -w 4 run:app`.
2. **Single DB connection per request**: Fine for low concurrency. For >100 req/s, add a connection pool (PgBouncer or Peewee PooledPostgresqlDatabase).
3. **No caching on redirects**: Every GET /r/<code> hits Postgres. For high-traffic short codes, add Redis cache.

## Scaling path

1. Replace `uv run run.py` with `uv run gunicorn -w 4 -b 0.0.0.0:5000 run:app`
2. Add a DigitalOcean Managed Postgres (removes DB from Droplet, adds HA)
3. Add Redis for redirect caching (most-accessed short codes cached for 60s)
4. Add a second Droplet + load balancer for API horizontal scaling
