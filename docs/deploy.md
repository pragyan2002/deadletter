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

Test it:
```bash
curl http://<DROPLET_IP>:5000/health
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
