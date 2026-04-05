# Runbook

## Check system health

```bash
curl http://localhost:5000/health
curl http://localhost:5000/metrics
python cli.py health
python cli.py metrics
```

## Restart the API

```bash
docker compose restart api
```

## Restart Postgres

```bash
docker compose restart postgres
# Wait for healthcheck to pass, then api reconnects automatically
```

## View logs

```bash
docker compose logs -f api
docker compose logs -f postgres
```

API request and error logs are emitted as JSON for easier filtering in Docker and external log systems. Example line:

```json
{"timestamp":"2026-04-05 12:43:09,442","level":"INFO","logger":"app.request","message":"request_completed","method":"GET","path":"/health","status_code":200,"duration_ms":1.27,"request_id":"9d5f5ec2-5037-45ea-a1ad-d372b807f146"}
```

Filter API logs by level (ERROR):

```bash
docker compose logs -f api | jq -c 'fromjson? | select(.level == "ERROR")'
```

Filter API logs by request path (`/health`):

```bash
docker compose logs -f api | jq -c 'fromjson? | select(.path == "/health")'
```

## Run migrations (create tables)

```bash
docker compose exec api uv run migrate.py
```

## Load seed data

```bash
docker compose exec api uv run migrate.py --seed
```

## Force-delete a URL (chaos demo)

```bash
python cli.py delete <short_code> --reason policy_cleanup
curl http://localhost:5000/r/<short_code>  # should return 404 JSON
```

## Check event log for a URL

```bash
python cli.py inspect <short_code>
# or
curl "http://localhost:5000/events?short_code=<short_code>"
```

## Chaos demo: kill the API mid-request

```bash
# Terminal 1: start dashboard
python cli.py dashboard

# Terminal 2: kill the api container
docker kill deadletter-api-1

# Container restarts automatically in ~5 seconds (restart: always)
# Dashboard recovers on next refresh
```

## Deploy to DigitalOcean manually

```bash
ssh root@<DO_HOST>
cd /app
git pull
docker compose up -d --build
```
