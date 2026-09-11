# MakerGuide

AI-powered knowledge assistant for makers and crafters. This repository currently contains the application foundation: FastAPI, PostgreSQL with pgvector, Ollama, and a health endpoint. Retrieval-Augmented Generation is not implemented yet.

## Architecture

```
Client  -->  FastAPI (host API_PORT, default 8140)
                 |
                 +--> PostgreSQL + pgvector (postgres:5432)
                 +--> Ollama (ollama:11434)   # configured, unused until RAG
```

- **api** — HTTP layer. Routers call services; services talk to the database.
- **postgres** — persistent Postgres with the `vector` extension enabled via Alembic.
- **ollama** — local LLM runtime. The API reaches it at `http://ollama:11434` on the Compose network.

Configuration is environment-based (`DATABASE_URL`, `OLLAMA_BASE_URL`, `API_PORT`), so the same stack can later run on another machine (for example `192.168.0.45`) without code changes. The API listens on host port **8140** by default (`API_PORT` in `.env`) so it does not collide with other local apps on 8000.

## Important files

| Path | Purpose |
| --- | --- |
| `app/main.py` | FastAPI app factory and router mount |
| `app/core/config.py` | Settings from environment / `.env` |
| `app/core/logging.py` | Process logging |
| `app/api/health.py` | `GET /health` |
| `app/services/health.py` | Postgres `SELECT 1` check |
| `app/schemas/health.py` | Health response schema |
| `app/db/session.py` | SQLAlchemy engine and session |
| `app/db/base.py` | Declarative `Base` for models |
| `app/models/` | SQLAlchemy models (empty until RAG) |
| `app/repositories/` | Data access (empty until RAG) |
| `alembic/` | Migrations; first revision enables `vector` |
| `docker-compose.yml` | `api`, `postgres`, `ollama` |
| `.env.example` | Documented environment variables |

## Start locally

1. Copy environment defaults:

   ```bash
   copy .env.example .env
   ```

2. Start the stack:

   ```bash
   docker compose up --build
   ```

3. Apply migrations:

   ```bash
   docker compose exec api alembic upgrade head
   ```

4. Check the API:

   ```bash
   curl http://localhost:8140/health
   ```

   Expected when Postgres is up:

   ```json
   {"status":"ok","api":"ok","postgres":"ok"}
   ```

If Postgres is unreachable, `/health` returns HTTP 503 with `"postgres": "unavailable"`.

## Verify PostgreSQL

- Health endpoint: `curl http://localhost:8140/health` should show `"postgres":"ok"`.
- Direct query from the container:

  ```bash
  docker compose exec postgres psql -U makerguide -d makerguide -c "SELECT 1;"
  ```

  Confirm pgvector:

  ```bash
  docker compose exec postgres psql -U makerguide -d makerguide -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
  ```

  That last command returns a row after `alembic upgrade head`.

## Verify Ollama

Ollama is not included in `/health`. From the host:

```bash
curl http://localhost:11434/api/tags
```

A JSON list of models (often empty until you pull one) means the service is reachable. From the API container:

```bash
docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://ollama:11434/api/tags').status)"
```

Pulling a model is a later step (`docker compose exec ollama ollama pull <model>`).

## Later: Windows server at x.x.x.x

Use the same Docker Compose stack on that machine. Bindings already listen on `0.0.0.0` inside the containers, so LAN clients can use `http://x.x.x.x:8140` once Docker Desktop is running there. Change `API_PORT` in `.env` if that host port is taken.
