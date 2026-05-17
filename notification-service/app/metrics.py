from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

EVENTS_CONSUMED = Counter(
    'notification_events_consumed_total',
    'Total Kafka shift-events consumed',
    ['event_type'],
)

NOTIFICATIONS_SENT = Counter(
    'notification_notifications_sent_total',
    'Total notifications dispatched',
    ['channel'],
)

CONSUMER_LAG_PROCESSING_SECONDS = Histogram(
    'notification_processing_duration_seconds',
    'Time to process a single Kafka event',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

RETRY_COUNTER = Counter(
    'notification_consumer_retries_total',
    'Total consumer retry attempts',
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
