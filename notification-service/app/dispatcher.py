# Notification Dispatcher
# Receives a structured shift-event dict and dispatches notifications.
# Currently uses console/structured-log output as the "channel".
# Swap _send_email / _send_sms / _send_slack for real integrations later.

import json
import logging
import time

from app.metrics import CONSUMER_LAG_PROCESSING_SECONDS, EVENTS_CONSUMED, NOTIFICATIONS_SENT

logger = logging.getLogger(__name__)


def _send_log_notification(event: dict) -> None:
    """Emit a structured JSON log line – simulates sending a notification."""
    notification = {
        'channel': 'log',
        'event_type': event.get('event_type'),
        'shift_id': event.get('shift_id'),
        'staff_id': event.get('staff_id'),
        'staff_name': event.get('staff_name', 'Unknown'),
        'shift_name': event.get('shift_name', 'Unknown'),
        'shift_date': event.get('shift_date'),
        'start_time': event.get('start_time'),
        'end_time': event.get('end_time'),
        'location': event.get('location', ''),
        'message': (
            f"Shift notification: {event.get('staff_name', 'Staff')} assigned to "
            f"{event.get('shift_name', 'shift')} on {event.get('shift_date')} "
            f"({event.get('start_time')} – {event.get('end_time')}) "
            f"@ {event.get('location', 'TBD')}"
        ),
    }
    logger.info('NOTIFICATION_DISPATCHED %s', json.dumps(notification))
    NOTIFICATIONS_SENT.labels(channel='log').inc()


def dispatch(event: dict) -> None:
    """
    Entry point called by the Kafka consumer for every shift event.
    Tracks Prometheus metrics and calls the appropriate dispatcher.
    """
    event_type = event.get('event_type', 'UNKNOWN')
    start = time.perf_counter()

    try:
        EVENTS_CONSUMED.labels(event_type=event_type).inc()

        if event_type == 'SHIFT_ASSIGNED':
            _send_log_notification(event)
        else:
            logger.info('Unhandled event_type=%s – skipping dispatch', event_type)

    finally:
        elapsed = time.perf_counter() - start
        CONSUMER_LAG_PROCESSING_SECONDS.observe(elapsed)
