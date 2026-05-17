import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import shifts, skills, staff
from app.metrics import metrics_response

logging.basicConfig(level=logging.INFO, format='%(levelname)s [%(name)s] %(message)s')
logger = logging.getLogger(__name__)

# NOTE: Table creation is intentionally NOT done here.
# In production the Dockerfile runs `alembic upgrade head` before starting uvicorn.
# In tests conftest.py creates the schema against the test DB directly.
# Calling Base.metadata.create_all() at import time would try to connect to
# DATABASE_URL (which may not exist in CI), crashing pytest collection.

app = FastAPI(
    title='ShiftBoard – Scheduling API',
    description='Constraint-based staff scheduling engine. Backtracking + forward-checking CSP.',
    version='1.0.0',
)

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

app.include_router(staff.router)
app.include_router(skills.router)
app.include_router(shifts.router)


@app.get('/health', tags=['monitoring'])
def health():
    return {'status': 'ok', 'service': 'scheduling-service'}


@app.get('/metrics', tags=['monitoring'], include_in_schema=False)
def metrics():
    return metrics_response()
