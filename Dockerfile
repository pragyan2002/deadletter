FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync

COPY . .

EXPOSE 5000

CMD ["sh", "-c", "uv run migrate.py && \
WORKERS="${WEB_CONCURRENCY:-$((2 * $(nproc) + 1))}" && \
exec uv run gunicorn \
  --workers "$WORKERS" \
  --worker-tmp-dir /dev/shm \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
  --keep-alive "${GUNICORN_KEEPALIVE:-5}" \
  --bind 0.0.0.0:5000 \
  run:app"]
