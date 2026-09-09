# ModelWatch

A web-based ML data-drift monitoring platform. Register models, upload
reference baselines, ingest production observations, and run PSI / KS /
Jensen-Shannon drift checks — with results in a React dashboard.

This repository was built milestone by milestone (see `PROGRESS.md`).
**Status: V1 complete (M1–M12).** Signup through drift detection, alerts,
scheduling, async job processing, and a real dashboard all work
end-to-end locally. Production hardening (security, rate limiting,
observability, CI/CD, deployment) is a deliberately separate future
phase — see `PROGRESS.md` and the original spec for what's intentionally
deferred.

## Architecture (target, built incrementally)

```
Frontend (React) -> FastAPI -> PostgreSQL
                        |
                      Redis -> RQ Worker -> Drift Engine -> PostgreSQL
```

## Prerequisites

- Docker Desktop (for PostgreSQL + Redis)
- Python 3.10+
- Node.js 18+
- Windows PowerShell (instructions below use PowerShell syntax)

## 1. Start local infrastructure (PostgreSQL + Redis)

```powershell
docker compose up -d
```

Verify both containers are healthy:

```powershell
docker compose ps
```

## 2. Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` if your local Postgres/Redis differ from the defaults.

Run the API:

```powershell
uvicorn app.main:app --reload
```

Check it's alive:

```powershell
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "app": "ModelWatch", "environment": "local"}
```

Run the drift-check worker (separate terminal, same venv):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
rq worker monitoring --url redis://localhost:6379/0
```

Run the scheduler (separate terminal, same venv) — finds due `MonitoringSchedule`s and enqueues jobs; does not compute drift itself:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.scheduler
```

### Run backend tests

```powershell
cd backend
pytest
```

## 3. Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api` calls to
the backend at `http://localhost:8000`.

### Build the frontend

```powershell
npm run build
```

## Project layout

```
backend/
  app/
    main.py          FastAPI app + /health
    core/config.py    pydantic-settings configuration
    api/              routers (empty until M3+)
    models/           SQLAlchemy models (added M1 Task 2 / M2+)
    schemas/          Pydantic request/response schemas
    services/         business logic
    drift/            pure-Python statistical drift engine (M6)
    workers/          RQ job definitions (M8+)
    db/               session/engine setup, migrations support
  tests/
    unit/             statistical engine tests
    integration/      real-PostgreSQL database tests
    api/              FastAPI endpoint tests
frontend/
  src/                React + TypeScript dashboard
docker-compose.yml    PostgreSQL + Redis for local dev
```

## Development philosophy

Simple modular monolith first. No microservices, no Kafka, no Kubernetes,
no distributed workflow engine. Correctness on the fundamentals (schema
design, migrations, auth, statistics, tests) is not optional — but
infrastructure complexity is only added when a concrete requirement
demands it. See milestone plan in `PROGRESS.md`.
