import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.consumer import start_consumer, stop_consumer
from app.metrics import metrics_response

logging.basicConfig(level=logging.INFO, format='%(levelname)s [%(name)s] %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Notification service starting – launching Kafka consumer')
    start_consumer()
    yield
    logger.info('Notification service shutting down')
    stop_consumer()


app = FastAPI(
    title='ShiftBoard – Notification Service',
    description='Consumes shift events from Kafka and dispatches notifications.',
    version='1.0.0',
    lifespan=lifespan,
)


@app.get('/health', tags=['monitoring'])
def health():
    return {'status': 'ok', 'service': 'notification-service'}


@app.get('/metrics', tags=['monitoring'], include_in_schema=False)
def metrics():
    return metrics_response()
