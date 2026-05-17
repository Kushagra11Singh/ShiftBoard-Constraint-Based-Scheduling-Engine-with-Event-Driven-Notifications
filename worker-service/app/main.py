import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.worker import start_worker, stop_worker, trigger_now
from app.metrics import metrics_response

logging.basicConfig(level=logging.INFO, format='%(levelname)s [%(name)s] %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Worker service starting')
    start_worker()
    yield
    logger.info('Worker service shutting down')
    stop_worker()


app = FastAPI(
    title='ShiftBoard – Worker Service',
    description='Polls for unscheduled shifts and triggers the constraint solver automatically.',
    version='1.0.0',
    lifespan=lifespan,
)


@app.get('/health', tags=['monitoring'])
def health():
    return {'status': 'ok', 'service': 'worker-service'}


@app.post('/trigger', tags=['operations'])
def trigger():
    """Manually trigger one scheduling run immediately (useful for testing)."""
    result = trigger_now()
    return JSONResponse(content=result)


@app.get('/metrics', tags=['monitoring'], include_in_schema=False)
def metrics():
    return metrics_response()
