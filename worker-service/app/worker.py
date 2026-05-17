# Scheduling Worker
# Polls the scheduling-service for unscheduled shifts on a fixed interval,
# then triggers the constraint solver to assign staff automatically.
#
# Runs as a daemon thread so FastAPI can serve /health and /metrics
# while the worker loop operates in the background.

import logging
import threading
import time
from typing import List

import httpx

from app.config import SCHEDULING_SERVICE_URL, WORKER_INTERVAL_SECONDS
from app.metrics import (
    SHIFTS_SCHEDULED_TOTAL,
    UNSCHEDULED_SHIFTS_GAUGE,
    WORKER_RUN_DURATION_SECONDS,
    WORKER_RUNS_TOTAL,
)

logger = logging.getLogger(__name__)

_worker_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _fetch_unscheduled_shifts(client: httpx.Client) -> List[dict]:
    """GET /shifts?status_filter=unscheduled from the scheduling-service."""
    resp = client.get(
        f'{SCHEDULING_SERVICE_URL}/shifts',
        params={'status_filter': 'unscheduled'},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _trigger_schedule(client: httpx.Client, shift_ids: List[int]) -> dict:
    """POST /shifts/schedule with a list of shift IDs."""
    resp = client.post(
        f'{SCHEDULING_SERVICE_URL}/shifts/schedule',
        json={'shift_ids': shift_ids},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _run_once() -> None:
    """Single worker iteration: fetch unscheduled shifts, trigger solver."""
    start = time.perf_counter()
    try:
        with httpx.Client() as client:
            shifts = _fetch_unscheduled_shifts(client)
            UNSCHEDULED_SHIFTS_GAUGE.set(len(shifts))

            if not shifts:
                logger.info('Worker: no unscheduled shifts found – nothing to do')
                WORKER_RUNS_TOTAL.labels(result='no_work').inc()
                return

            shift_ids = [s['id'] for s in shifts]
            logger.info('Worker: found %d unscheduled shift(s): %s', len(shift_ids), shift_ids)

            result = _trigger_schedule(client, shift_ids)

            if result.get('success'):
                count = len(result.get('assignments', []))
                logger.info(
                    'Worker: scheduled %d assignment(s) in %.1f ms',
                    count,
                    result.get('elapsed_ms', 0),
                )
                SHIFTS_SCHEDULED_TOTAL.inc(count)
                WORKER_RUNS_TOTAL.labels(result='success').inc()
            else:
                logger.warning('Worker: scheduler returned no feasible solution – %s', result.get('message'))
                WORKER_RUNS_TOTAL.labels(result='no_solution').inc()

    except httpx.HTTPStatusError as exc:
        logger.error('Worker: HTTP error from scheduling-service: %s', exc)
        WORKER_RUNS_TOTAL.labels(result='http_error').inc()

    except Exception as exc:
        logger.error('Worker: unexpected error: %s', exc)
        WORKER_RUNS_TOTAL.labels(result='error').inc()

    finally:
        elapsed = time.perf_counter() - start
        WORKER_RUN_DURATION_SECONDS.observe(elapsed)


def _worker_loop() -> None:
    logger.info(
        'Worker loop started – interval=%ds, scheduling-service=%s',
        WORKER_INTERVAL_SECONDS,
        SCHEDULING_SERVICE_URL,
    )
    while not _stop_event.is_set():
        _run_once()
        _stop_event.wait(timeout=WORKER_INTERVAL_SECONDS)
    logger.info('Worker loop stopped')


def start_worker() -> None:
    global _worker_thread
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True, name='shift-worker')
    _worker_thread.start()
    logger.info('Worker thread started')


def stop_worker() -> None:
    _stop_event.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=15)
    logger.info('Worker thread stopped')


def trigger_now() -> dict:
    """Run one worker iteration synchronously (used by the /trigger endpoint)."""
    _run_once()
    return {'triggered': True}
