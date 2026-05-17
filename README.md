# ShiftBoard

**Constraint-Based Scheduling Engine with Event-Driven Notifications**

A production-grade staff scheduling system that automatically generates conflict-free shift assignments using a backtracking + forward-checking constraint satisfaction algorithm, backed by an Apache Kafka event pipeline for real-time notifications.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ShiftBoard System                         │
│                                                                   │
│  ┌──────────────────────┐    ┌──────────────────────────────┐   │
│  │   Worker Service      │───▶│   Scheduling Service          │   │
│  │   :8002               │    │   :8000  (FastAPI + CSP algo)│   │
│  │  Polls every 60s      │    │   PostgreSQL ORM (SQLAlchemy) │   │
│  │  /trigger endpoint    │    │   Alembic migrations          │   │
│  └──────────────────────┘    └──────────────┬───────────────┘   │
│                                              │ Kafka producer     │
│                                              ▼                    │
│                                    ┌─────────────────┐           │
│                                    │  Apache Kafka    │           │
│                                    │  (shift-events)  │           │
│                                    └────────┬────────┘           │
│                                             │ consumer            │
│                                             ▼                    │
│                                    ┌─────────────────┐           │
│                                    │ Notification Svc │           │
│                                    │ :8001            │           │
│                                    │ at-least-once    │           │
│                                    └─────────────────┘           │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Prometheus :9090  ←  scrapes /metrics from all 3 svcs  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Services

| Service | Port | Responsibility |
|---|---|---|
| **scheduling-service** | 8000 | REST API, CSP scheduler, PostgreSQL ORM, Kafka producer |
| **notification-service** | 8001 | Kafka consumer, notification dispatcher, at-least-once delivery |
| **worker-service** | 8002 | Periodic scheduler trigger, unscheduled shift poller |
| **Prometheus** | 9090 | Metrics scraping from all services |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| API Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 + Alembic migrations |
| Database | PostgreSQL 15 |
| Message Broker | Apache Kafka (Confluent 7.5) |
| Observability | Prometheus client (counters, gauges, histograms) |
| Containerisation | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Testing | pytest + pytest-cov, respx (HTTP mocking) |

---

## Scheduling Algorithm

The core algorithm is a **backtracking + forward-checking constraint satisfaction solver** (`scheduling-service/app/services/scheduler.py`):

- **Variables**: each `(shift, slot)` pair — one slot per required staff position
- **Domains**: active staff members who satisfy all constraints for that slot
- **Constraints enforced**:
  1. Staff must possess **all skills** required by the shift
  2. Staff **cannot be double-booked** across overlapping shifts on the same day
  3. Staff **weekly hours cap** is never exceeded
- **Forward checking** prunes domains of future slots after each assignment, abandoning dead-end branches early
- Benchmarked at **< 200 ms** against 500+ staff records / 20 simultaneous shifts

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git

### 1. Clone and configure

```bash
git clone https://github.com/Kushagra11Singh/shiftboard.git
cd shiftboard
cp .env.example .env
```

### 2. Start everything

```bash
docker compose up --build
```

Wait ~30 seconds for Kafka to initialise. You will see log lines like:
```
shiftboard-api       | INFO [app.main] Application startup complete.
shiftboard-notifications | INFO [app.consumer] Kafka consumer ready – polling for events
shiftboard-worker    | INFO [app.worker] Worker loop started – interval=60s
```

### 3. Verify services are healthy

```bash
curl http://localhost:8000/health   # {"status":"ok","service":"scheduling-service"}
curl http://localhost:8001/health   # {"status":"ok","service":"notification-service"}
curl http://localhost:8002/health   # {"status":"ok","service":"worker-service"}
```

### 4. Open the interactive API docs

Navigate to **http://localhost:8000/docs** in your browser to see the full OpenAPI/Swagger interface.

---

## API Walkthrough

### Step 1 – Create skills

```bash
curl -X POST http://localhost:8000/skills \
  -H "Content-Type: application/json" \
  -d '{"name": "Forklift", "description": "Certified forklift operator"}'

curl -X POST http://localhost:8000/skills \
  -H "Content-Type: application/json" \
  -d '{"name": "First Aid", "description": "Basic first aid certified"}'
```

### Step 2 – Create staff

```bash
curl -X POST http://localhost:8000/staff \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Kumar", "email": "alice@example.com", "max_hours_per_week": 40}'

curl -X POST http://localhost:8000/staff \
  -H "Content-Type: application/json" \
  -d '{"name": "Bob Sharma", "email": "bob@example.com", "max_hours_per_week": 40}'
```

### Step 3 – Assign skills to staff

```bash
# Replace 1 with the staff ID and 1 with the skill ID returned above
curl -X POST http://localhost:8000/staff/1/skills/1
curl -X POST http://localhost:8000/staff/2/skills/1
curl -X POST http://localhost:8000/staff/2/skills/2
```

### Step 4 – Create a shift

```bash
curl -X POST http://localhost:8000/shifts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Morning Warehouse",
    "date": "2024-12-15",
    "start_time": "08:00:00",
    "end_time": "16:00:00",
    "required_staff_count": 2,
    "skill_requirements": [{"skill_id": 1, "required_count": 2}]
  }'
```

### Step 5 – Run the scheduler

```bash
curl -X POST http://localhost:8000/shifts/schedule \
  -H "Content-Type: application/json" \
  -d '{"shift_ids": [1]}'
```

**Response:**
```json
{
  "success": true,
  "assignments": [
    {"shift_id": 1, "staff_id": 1},
    {"shift_id": 1, "staff_id": 2}
  ],
  "elapsed_ms": 12.4,
  "message": "Scheduled 2 assignments in 12.4 ms"
}
```

Immediately after, the notification service logs:
```
INFO [app.dispatcher] NOTIFICATION_DISPATCHED {"channel": "log", "event_type": "SHIFT_ASSIGNED", "staff_name": "Alice Kumar", ...}
```

### Step 6 – Trigger the worker manually

```bash
curl -X POST http://localhost:8002/trigger
```

The worker polls for all `unscheduled` shifts and runs the solver on them automatically.

---

## Prometheus Metrics

Visit **http://localhost:9090** and query:

| Metric | Description |
|---|---|
| `shiftboard_scheduling_duration_ms` | Scheduler runtime histogram |
| `shiftboard_scheduling_success_total` | Successful scheduling runs |
| `shiftboard_scheduling_failure_total` | Runs with no feasible solution |
| `shiftboard_active_staff_total` | Active staff gauge |
| `notification_events_consumed_total` | Kafka events consumed |
| `notification_notifications_sent_total` | Notifications dispatched |
| `worker_runs_total` | Worker polling runs by result label |
| `worker_unscheduled_shifts_total` | Unscheduled shifts found in last run |

---

## Running Tests Locally

You need a running PostgreSQL instance for the scheduling-service integration tests.

```bash
# Start just the database
docker compose up postgres -d

# Scheduling service (89% coverage enforced)
cd scheduling-service
pip install -r requirements.txt
TEST_DATABASE_URL=postgresql://shiftboard:shiftboard123@localhost:5432/shiftboard_test \
  alembic upgrade head
pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=89

# Notification service (no external deps needed)
cd ../notification-service
pip install -r requirements.txt
pytest tests/ -v --cov=app --cov-report=term-missing

# Worker service (all HTTP mocked with respx)
cd ../worker-service
pip install -r requirements.txt
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Project Structure

```
shiftboard/
├── docker-compose.yml            # Orchestrates all 5 services + Kafka + Prometheus
├── prometheus/
│   └── prometheus.yml            # Scrape configs for all 3 app services
├── .github/workflows/ci.yml      # GitHub Actions CI – tests all 3 services in parallel
│
├── scheduling-service/           # Core API + CSP scheduler
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/001_initial_schema.py
│   ├── app/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── metrics.py
│   │   ├── models.py             # SQLAlchemy ORM – staff ↔ skills ↔ shifts (many-to-many)
│   │   ├── schemas.py            # Pydantic v2 schemas
│   │   ├── routers/
│   │   │   ├── staff.py
│   │   │   ├── skills.py
│   │   │   └── shifts.py         # Includes /schedule endpoint
│   │   └── services/
│   │       ├── scheduler.py      # Backtracking + forward-checking CSP
│   │       └── kafka_producer.py
│   └── tests/
│       ├── conftest.py
│       ├── test_staff.py
│       ├── test_skills.py
│       ├── test_shifts.py
│       └── test_scheduler.py     # Pure unit tests, no DB required
│
├── notification-service/         # Kafka consumer + dispatcher
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── metrics.py
│   │   ├── consumer.py           # At-least-once Kafka consumer (manual commit)
│   │   └── dispatcher.py
│   └── tests/
│       ├── test_dispatcher.py
│       └── test_health.py
│
└── worker-service/               # Periodic scheduling trigger
    ├── Dockerfile
    ├── requirements.txt
    ├── app/
    │   ├── config.py
    │   ├── main.py
    │   ├── metrics.py
    │   └── worker.py             # Background thread + /trigger endpoint
    └── tests/
        ├── test_worker.py        # All HTTP mocked with respx
        └── test_health.py
```

---

## CI/CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`) runs on every push to `main`/`develop`:

- **test-scheduling-service** – spins up a real PostgreSQL service container, runs Alembic migrations, runs pytest with 89% coverage gate
- **test-notification-service** – installs deps, runs pytest (no external services needed)
- **test-worker-service** – installs deps, runs pytest (all HTTP mocked)

All three jobs run **in parallel**.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Backtracking + forward checking** | Guarantees complete search (finds a solution if one exists) while pruning dead ends early, keeping runtime well under 200 ms for realistic inputs |
| **Full ORM depth** | Zero raw SQL throughout – `select_related` / `prefetch_related` patterns via SQLAlchemy `selectinload` to avoid N+1 queries |
| **Manual Kafka offset commit** | Ensures at-least-once delivery: if the dispatcher crashes mid-process, Kafka redelivers the message |
| **Exponential back-off** | Consumer reconnection loop starts at 2 s, doubles each attempt, caps at 60 s |
| **Lazy Kafka producer** | Scheduling service starts up even if Kafka is unavailable; shift events are simply skipped with a warning |
| **Independent Docker services** | Three separately deployable microservices – scale notification consumers independently of the API |
