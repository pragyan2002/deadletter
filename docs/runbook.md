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
