from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

WORKER_RUNS_TOTAL = Counter(
    'worker_runs_total',
    'Total scheduling worker runs',
    ['result'],
)

WORKER_RUN_DURATION_SECONDS = Histogram(
    'worker_run_duration_seconds',
    'Time taken per worker scheduling run',
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

UNSCHEDULED_SHIFTS_GAUGE = Gauge(
    'worker_unscheduled_shifts_total',
    'Number of unscheduled shifts found during last run',
)

SHIFTS_SCHEDULED_TOTAL = Counter(
    'worker_shifts_scheduled_total',
    'Cumulative shifts successfully scheduled by the worker',
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
