# Deploy Guide: DigitalOcean Droplet

## Prerequisites

- DigitalOcean account with credits
- SSH key added to your DO account
- GitHub repo at github.com/pragyan2002/deadletter

## Step 1: Create a Droplet

1. DigitalOcean console -> Create Droplet
2. Ubuntu 24.04 LTS
3. Basic plan, 2GB RAM / 1 vCPU ($12/mo, or free with credits)
4. Add your SSH key
5. Note the Droplet IP

## Step 2: Install Docker on the Droplet

```bash
ssh root@<DROPLET_IP>

apt-get update
apt-get install -y docker.io docker-compose-plugin
systemctl enable docker
systemctl start docker
```

## Step 3: Clone and configure the app

```bash
mkdir /app && cd /app
git clone https://github.com/pragyan2002/deadletter.git .
cp .env.example .env
# Edit .env: set DATABASE_PASSWORD and DISCORD_WEBHOOK_URL
nano .env
```

## Step 4: Start the stack

```bash
docker compose up -d --build
docker compose logs -f
```

The app is live at `http://<DROPLET_IP>:5000`.

The API container starts as a Gunicorn master process with multiple worker processes:

- Default worker count is `2 * CPU + 1` (override with `WEB_CONCURRENCY`)
- Default timeouts: `GUNICORN_TIMEOUT=60`, `GUNICORN_GRACEFUL_TIMEOUT=30`, `GUNICORN_KEEPALIVE=5`
- `restart: always` restarts the container if the Gunicorn master exits
- Gunicorn itself supervises and replaces crashed workers without restarting the container

Test it:
```bash
curl http://<DROPLET_IP>:5000/health
docker compose ps api  # should show healthy once /health checks pass
```

## Step 5: Load seed data

```bash
docker compose exec api uv run migrate.py --seed
```

## Step 6: Configure GitHub Actions secrets

In your GitHub repo -> Settings -> Secrets and variables -> Actions:

| Secret | Value |
|--------|-------|
| `DO_HOST` | Your Droplet IP |
| `DO_SSH_KEY` | Your private SSH key (the full key, including BEGIN/END lines) |

After this, every push to main that passes tests will auto-deploy.

## Verifying the deploy gate

Push a failing test to a branch. Open a PR to main. The `deploy` job will not run because `test` failed. Merge a fix. Both jobs run and deploy succeeds.

## Optional: Add a firewall

DigitalOcean Firewall -> Allow inbound TCP on port 5000 only.
This prevents direct DB access from the internet.

## Observability overlay (optional)

On the Droplet:
```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

Grafana at `http://<DROPLET_IP>:3000` (admin/admin).

## Rollback

Use this if a fresh deploy introduces user-facing errors, sustained health-check failures, or clear regressions.

### When to rollback (decision checklist)

- [ ] `curl http://<DROPLET_IP>:5000/health` fails repeatedly (not a one-off blip).
- [ ] Core user flow is broken (for example, your primary API path returns 5xx or bad data).
- [ ] Error rate/latency is significantly worse than the last stable baseline.
- [ ] Recent deploy is the most likely cause (timing matches incident start).
- [ ] A fast forward fix is not safer/faster than restoring known-good behavior.

### Step-by-step rollback commands

1. **Identify the previous known-good commit or tag**
   ```bash
   ssh root@<DROPLET_IP>
   cd /app

   # Show recent history and tags to choose a known-good revision
   git log --oneline --decorate -n 20
   git tag --sort=-creatordate | head -n 20

   # Set this to a trusted commit SHA or tag (example values)
   export ROLLBACK_REF=<KNOWN_GOOD_SHA_OR_TAG>
   git show --no-patch --oneline "$ROLLBACK_REF"
   ```

2. **Pull/reset on the Droplet to that revision**
   ```bash
   cd /app
   git fetch --all --tags --prune
   git reset --hard "$ROLLBACK_REF"
   git status --short --branch
   ```

3. **Rebuild and restart containers**
   ```bash
   cd /app
   docker compose down
   docker compose up -d --build
   docker compose ps
   ```

4. **Run smoke checks (`/health` + one URL flow)**
   ```bash
   # Health endpoint
   curl -fsS http://<DROPLET_IP>:5000/health

   # One representative flow (replace with your real endpoint/path)
   curl -i http://<DROPLET_IP>:5000/<CRITICAL_PATH>
   ```

5. **Confirm logs and metrics are normal**
   ```bash
   docker compose logs --since=10m api worker
   docker compose logs --since=10m postgres
   ```
   If observability is enabled, verify dashboards (error rate, latency, saturation) are back to expected levels.

### Rollback verification checklist

- [ ] `/health` is green across multiple checks.
- [ ] One critical end-to-end URL flow succeeds.
- [ ] No sustained 5xx bursts in container logs.
- [ ] CPU/memory/restart counts are stable after rollback.
- [ ] Incident note records rollback ref, time, and operator.
