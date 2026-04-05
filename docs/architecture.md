# Architecture

This diagram shows the runtime topology for the API, Postgres, optional observability stack, and CLI interactions.

```mermaid
flowchart LR
    subgraph Host[Developer host / Docker network boundary]
        CLI[CLI\nTyper + Rich\nclient process]

        subgraph AppNet[deadletter_default network]
            API[API service\nFlask app\n:5000]
            DB[(PostgreSQL\n:5432)]
        end

        subgraph ObsNet[Optional observability overlay\nfrom docker-compose.observability.yml]
            PROM[Prometheus\n:9090]
            GRAF[Grafana\n:3000]
        end
    end

    CLI -->|HTTP request\ncreate/read/update/delete| API
    API -->|SQL read/write\nusers, urls, events| DB

    PROM -->|metrics scrape\nGET /metrics| API
    GRAF -->|dashboard read\nPromQL queries| PROM

    CLI -.->|optional dashboard open\nhttp://localhost:3000| GRAF
```

## Port and network notes

- CLI to API: `localhost:5000` (request/response path).
- API to Postgres: `postgres:5432` on the compose network.
- Prometheus to API: scrape `http://api:5000/metrics`.
- Grafana UI: `localhost:3000`, reading data from Prometheus at `prometheus:9090`.
- Prometheus UI: `localhost:9090`.
