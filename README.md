# ModelWatch

> ML data-drift monitoring platform for production models

ModelWatch is a web-based monitoring platform that helps ML engineers detect when the **input data distribution seen by a production model changes significantly** compared with a versioned reference baseline.

It provides model/version management, reference snapshots, production observation ingestion, statistical drift detection, scheduled monitoring, alerts, and a React dashboard.

---

## Why ModelWatch?

A machine-learning model can continue running normally while the data it receives gradually changes.

For example:

```text
REFERENCE DATA                  PRODUCTION DATA
---------------                 ----------------
amount: 10-40                   amount: 500-1200
India: 70%                      India: 10%
US: 20%                         US: 65%
UK: 10%                         UK: 25%
```

ModelWatch compares these distributions and surfaces whether the change is:

- `OK`
- `MODERATE`
- `DRIFTED`
- `INSUFFICIENT_DATA`

The platform is focused on **input data drift**. It does not execute the customer's ML model or automatically intercept production traffic.

---

## Core Workflow

```text
                    MODELWATCH

             1. Create Model
                     |
             2. Create Version
                     |
             3. Define Features
                     |
             4. Upload Reference
                Snapshot
                     |
                     v
          Production Application
                     |
           sends observations
                     |
                     v
             ModelWatch API
                     |
                     v
         Store Production Data
                     |
                     v
          Monitoring / Scheduler
                     |
                     v
          PSI / KS / Jensen-Shannon
                     |
                     v
            Feature Results
                     |
                     v
             Overall Status
                     |
                +----+----+
                |         |
                v         v
            Dashboard   Alerts
```

The production application sends a copy of the model's **input data** to ModelWatch through its ingestion API.

---

## Features

### Model Registry
- Create models
- Create model versions
- Register model input features
- Support numeric and categorical feature types

### Reference Snapshots
- Store reference/baseline data
- Keep comparisons tied to a specific snapshot
- Support reproducible historical monitoring

### Production Ingestion
- Receive production observations through the FastAPI API
- Track valid, missing, invalid, and unseen-category values
- Process observations in model-version-specific windows

### Drift Detection
ModelWatch currently supports:

- Population Stability Index (PSI)
- Kolmogorov-Smirnov (KS) test
- Jensen-Shannon divergence

Example V1 thresholds:

```text
PSI:
< 0.10       -> OK
0.10-0.25    -> MODERATE
>= 0.25      -> DRIFTED

KS statistic:
>= 0.20      -> DRIFTED

Jensen-Shannon:
>= 0.10      -> DRIFTED
```

A minimum of 30 usable samples is required for a feature to be evaluated.

### Monitoring
- Manual drift runs
- Asynchronous jobs with Redis + RQ
- Monitoring schedules
- Non-overlapping observation windows

### Alerts
- Feature-level drift alerts
- Persisted alert records
- Separate alert-delivery model for future notification integrations

### Dashboard
The React dashboard provides:
- model/version selection
- feature information
- reference information
- drift run history
- overall drift status
- feature-level metrics
- charts
- alerts

---

## Architecture

```text
                         React + TypeScript
                                |
                                | HTTP / JSON
                                v
                          FastAPI Backend
                                |
              +-----------------+-----------------+
              |                 |                 |
              v                 v                 v
         PostgreSQL           Redis          Drift Engine
              |                 |                 |
              |                 v                 |
              |              RQ Queue              |
              |                 |                 |
              |                 v                 |
              |              RQ Worker <-----------+
              |                                   |
              +-------------------+---------------+
                                  |
                                  v
                           Monitoring Jobs
                                  |
                                  v
                               Alerts
```

### Technology Stack

**Backend**
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic
- Redis
- RQ
- NumPy / SciPy-based statistical calculations

**Frontend**
- React 18
- TypeScript
- Vite
- Recharts

**Infrastructure**
- Docker Compose
- PostgreSQL 16
- Redis 7

**Testing**
- Pytest
- Unit tests
- Service/integration tests
- API tests
- End-to-end workflow validation

---

## Repository Structure

```text
modelwatch/
|
â”œâ”€â”€ .gitignore
â”œâ”€â”€ README.md
â”œâ”€â”€ PROGRESS.md
â”œâ”€â”€ docker-compose.yml
|
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ .env.example
â”‚   â”œâ”€â”€ alembic.ini
â”‚   â”œâ”€â”€ pytest.ini
â”‚   â”œâ”€â”€ requirements.txt
â”‚   |
â”‚   â”œâ”€â”€ alembic/
â”‚   â”‚   â””â”€â”€ versions/
â”‚   â”‚       â”œâ”€â”€ create_users_and_api_keys_tables.py
â”‚   â”‚       â”œâ”€â”€ create_models_model_versions_features_.py
â”‚   â”‚       â”œâ”€â”€ create_reference_snapshot_tables.py
â”‚   â”‚       â”œâ”€â”€ create_production_observations_table.py
â”‚   â”‚       â”œâ”€â”€ create_drift_runs_feature_drift_results_.py
â”‚   â”‚       â”œâ”€â”€ create_monitoring_jobs_table.py
â”‚   â”‚       â”œâ”€â”€ create_monitoring_schedules_table_and_.py
â”‚   â”‚       â””â”€â”€ create_alerts_and_alert_deliveries_.py
â”‚   |
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ main.py
â”‚   â”‚   â”œâ”€â”€ scheduler.py
â”‚   â”‚   |
â”‚   â”‚   â”œâ”€â”€ api/
â”‚   â”‚   â”‚   â”œâ”€â”€ auth.py
â”‚   â”‚   â”‚   â”œâ”€â”€ registry.py
â”‚   â”‚   â”‚   â”œâ”€â”€ reference.py
â”‚   â”‚   â”‚   â”œâ”€â”€ ingestion.py
â”‚   â”‚   â”‚   â”œâ”€â”€ drift.py
â”‚   â”‚   â”‚   â”œâ”€â”€ monitoring_jobs.py
â”‚   â”‚   â”‚   â”œâ”€â”€ schedules.py
â”‚   â”‚   â”‚   â””â”€â”€ alerts.py
â”‚   â”‚   |
â”‚   â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â”‚   â”œâ”€â”€ config.py
â”‚   â”‚   â”‚   â””â”€â”€ security.py
â”‚   â”‚   |
â”‚   â”‚   â”œâ”€â”€ db/
â”‚   â”‚   â”‚   â”œâ”€â”€ base.py
â”‚   â”‚   â”‚   â”œâ”€â”€ base_class.py
â”‚   â”‚   â”‚   â””â”€â”€ session.py
â”‚   â”‚   |
â”‚   â”‚   â”œâ”€â”€ drift/
â”‚   â”‚   â”‚   â”œâ”€â”€ engine.py
â”‚   â”‚   â”‚   â””â”€â”€ metrics.py
â”‚   â”‚   |
â”‚   â”‚   â”œâ”€â”€ models/
â”‚   â”‚   â”‚   â”œâ”€â”€ user.py
â”‚   â”‚   â”‚   â”œâ”€â”€ api_key.py
â”‚   â”‚   â”‚   â”œâ”€â”€ model.py
â”‚   â”‚   â”‚   â”œâ”€â”€ model_version.py
â”‚   â”‚   â”‚   â”œâ”€â”€ feature.py
â”‚   â”‚   â”‚   â”œâ”€â”€ reference_snapshot.py
â”‚   â”‚   â”‚   â”œâ”€â”€ reference_stats.py
â”‚   â”‚   â”‚   â”œâ”€â”€ reference_raw_sample.py
â”‚   â”‚   â”‚   â”œâ”€â”€ reference_raw_categorical.py
â”‚   â”‚   â”‚   â”œâ”€â”€ production_observation.py
â”‚   â”‚   â”‚   â”œâ”€â”€ drift_run.py
â”‚   â”‚   â”‚   â”œâ”€â”€ feature_drift_result.py
â”‚   â”‚   â”‚   â”œâ”€â”€ feature_drift_metric.py
â”‚   â”‚   â”‚   â”œâ”€â”€ monitoring_schedule.py
â”‚   â”‚   â”‚   â”œâ”€â”€ monitoring_job.py
â”‚   â”‚   â”‚   â”œâ”€â”€ alert.py
â”‚   â”‚   â”‚   â””â”€â”€ alert_delivery.py
â”‚   â”‚   |
â”‚   â”‚   â”œâ”€â”€ schemas/
â”‚   â”‚   â”œâ”€â”€ services/
â”‚   â”‚   â””â”€â”€ workers/
â”‚   â”‚       â”œâ”€â”€ queue.py
â”‚   â”‚       â””â”€â”€ tasks.py
â”‚   |
â”‚   â””â”€â”€ tests/
â”‚       â”œâ”€â”€ api/
â”‚       â”œâ”€â”€ integration/
â”‚       â””â”€â”€ unit/
|
â””â”€â”€ frontend/
    â”œâ”€â”€ index.html
    â”œâ”€â”€ package.json
    â”œâ”€â”€ package-lock.json
    â”œâ”€â”€ tsconfig.json
    â”œâ”€â”€ vite.config.ts
    â””â”€â”€ src/
        â”œâ”€â”€ App.tsx
        â”œâ”€â”€ main.tsx
        â”œâ”€â”€ api/
        â”‚   â””â”€â”€ client.ts
        â””â”€â”€ components/
            â”œâ”€â”€ AuthGate.tsx
            â”œâ”€â”€ ModelSelector.tsx
            â”œâ”€â”€ FeaturesAndReference.tsx
            â””â”€â”€ DriftDashboard.tsx
```

---

## Backend API

The FastAPI backend currently exposes routes for:

```text
POST   /signup

Models / Versions / Features
...    /models
...    /models/{model_id}/versions
...    /versions/{version_id}/features

Reference data
...    /versions/{version_id}/reference-snapshots

Production ingestion
POST   /versions/{version_id}/observations

Drift
POST   /versions/{version_id}/drift-runs
GET    /versions/{version_id}/drift-runs
GET    /drift-runs/{drift_run_id}

Monitoring
...    /versions/{version_id}/monitoring-jobs

Scheduling
...    /versions/{version_id}/schedules

Alerts
...    alert routes
```

Health check:

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "app": "ModelWatch",
  "environment": "local"
}
```

FastAPI also exposes the standard OpenAPI documentation.

---

## Production Ingestion: How It Works

ModelWatch does not automatically connect to or execute a customer's ML model.

The customer's production application sends the model input data to ModelWatch.

Conceptually:

```text
              Production Application
                     |
             +-------+-------+
             |               |
             v               v
         ML Model       ModelWatch API
             |               |
             v               v
         Prediction      Store Input Data
                             |
                             v
                       Drift Monitoring
```

The existing V1 ingestion endpoint is:

```http
POST /versions/{version_id}/observations
X-API-Key: <api-key>
Content-Type: application/json
```

The current payload model associates observations with registered features.

Example:

```json
{
  "observations": [
    {
      "feature_id": "<amount-feature-id>",
      "raw_value": "950"
    },
    {
      "feature_id": "<region-feature-id>",
      "raw_value": "US"
    }
  ]
}
```

A future product milestone will turn this existing backend capability into a more polished developer integration flow with dedicated ingestion credentials, key management, and generated code examples.

---

## Drift Calculation

A drift run compares a selected reference snapshot with a deterministic production observation window.

### Windowing

First run:

```text
model_version.created_at
        |
        v
window_end
```

Subsequent runs:

```text
previous window_end (exclusive)
        |
        v
new window_end (inclusive)
```

This prevents overlapping observation windows.

An empty window is explicitly recorded as:

```text
DriftRun.status = empty
```

rather than being represented as a fabricated successful drift result.

### Overall Status

```text
Any feature DRIFTED
        -> DRIFTED

Else any feature MODERATE
        -> MODERATE

Else all features INSUFFICIENT_DATA
        -> INSUFFICIENT_DATA

Else
        -> OK
```

---

## Important Quantitative Validation

During V1 validation, the drift implementation was deliberately challenged with a strongly shifted numeric distribution.

Reference:

```text
10 ... 39
```

Production:

```text
80 ... 109
```

The first implementation incorrectly allowed production values outside the reference histogram range to be discarded, causing PSI and Jensen-Shannon to collapse to zero.

The root cause was traced to the numeric histogram bin construction.

The implementation was corrected to use open-ended outer bins so out-of-range production observations are still counted.

After the fix:

```text
PSI  â‰ˆ 8.2831
JS   â‰ˆ 0.7532
KS   = 1.0
p    â‰ˆ 1.69e-17
```

The feature was correctly classified as:

```text
DRIFTED
```

Regression tests were added for both:
- shifted production values outside the reference range
- constant reference distributions with shifted production data

This is one of the key correctness validations in the project.

---

## Running Locally

### Prerequisites

You need:

- Python 3.10+
- Node.js / npm
- Docker Desktop

### 1. Start infrastructure

From the repository root:

```powershell
docker compose up -d
```

Verify:

```powershell
docker compose ps
```

Expected services:

```text
modelwatch-postgres   healthy
modelwatch-redis      healthy
```

### 2. Backend

```powershell
cd backend
python -m pip install -r requirements.txt
```

Configure your local environment using `.env.example`.

Start FastAPI:

```powershell
uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Health:

```text
http://127.0.0.1:8000/health
```

### 3. Frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

The Vite development proxy forwards:

```text
/api/*
```

to the FastAPI backend.

---

## Testing

From `backend/`:

```powershell
pytest -q
```

The V1 validation suite currently passes:

```text
88 passed
0 failures
```

Tests cover:

- health
- authentication
- model registry
- references
- ingestion
- drift engine
- drift API
- monitoring jobs
- scheduling
- alerts
- integration behavior
- end-to-end workflow

The suite also contains regression tests for the quantitative binning issue and the drift-history `overall_status` API issue.

---

## Current V1 Status

### Implemented

```text
âœ… Authentication
âœ… Model registry
âœ… Model versions
âœ… Feature definitions
âœ… Reference snapshots
âœ… Production observation ingestion
âœ… Data-quality tracking
âœ… PSI
âœ… KS
âœ… Jensen-Shannon
âœ… Drift classification
âœ… Deterministic non-overlapping windows
âœ… Historical drift runs
âœ… Redis / RQ asynchronous jobs
âœ… Scheduling
âœ… Alerts
âœ… React dashboard
âœ… Live API E2E validation
âœ… Live UI validation
âœ… Quantitative regression tests
```

### Current V1 characterization

> **Functional V1 ML data-drift monitoring platform**

The core monitoring workflow is implemented and verified. The next stage is production hardening and developer-facing productization.

---

## Roadmap

### M13 â€” Professional Production Integration

Planned:

```text
Create ingestion API key
        â†“
Key management
        â†“
Model/version scoping
        â†“
Developer integration page
        â†“
Python / cURL snippets
        â†“
Production application integration
```

### Production Hardening

Planned areas:

- scoped ingestion credentials
- key rotation/revocation improvements
- rate limiting
- idempotency
- concurrency controls
- duplicate-ingestion protection
- structured logging
- metrics and observability
- alert delivery retries
- database/indexing review
- load testing
- retention policies
- deployment automation
- security hardening

### Kubernetes

Kubernetes is planned as a separate production-style deployment target.

The intended model is:

```text
Docker Compose
    -> local development

Kubernetes
    -> production-style orchestration
```

The application services can eventually scale independently:

```text
FastAPI replicas
RQ worker replicas
Scheduler
```

---

## Development Philosophy

ModelWatch follows a **modular monolith** design for V1.

The goal is to keep the system understandable while separating the responsibilities that naturally need independent evolution:

```text
API layer
Service layer
Persistence layer
Drift engine
Async workers
Scheduler
Frontend
```

The drift engine is intentionally kept as a pure/stateless computation layer where possible.

PostgreSQL is the source of truth.

Redis is used for asynchronous job queuing.

Kafka, Kubernetes, microservices, and other infrastructure are intentionally deferred until they solve a demonstrated production requirement.

---

## License

This project currently does not declare a public open-source license.

If the repository is intended for public redistribution, add an explicit `LICENSE` file before publishing it as an open-source project.

