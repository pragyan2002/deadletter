FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync

COPY . .

EXPOSE 5000

CMD ["sh", "-c", "uv run migrate.py && uv run gunicorn --workers 2 --threads 4 --timeout 30 --bind 0.0.0.0:5000 run:app"]
