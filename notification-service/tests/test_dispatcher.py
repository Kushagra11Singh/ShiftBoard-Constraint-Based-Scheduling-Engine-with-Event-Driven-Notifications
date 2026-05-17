# Unit tests for the notification dispatcher – no Kafka required

from unittest.mock import patch, MagicMock
from app.dispatcher import dispatch


BASE_EVENT = {
    'event_type': 'SHIFT_ASSIGNED',
    'shift_id': 1,
    'staff_id': 42,
    'staff_name': 'Alice',
    'shift_name': 'Morning Shift',
    'shift_date': '2024-12-01',
    'start_time': '08:00:00',
    'end_time': '16:00:00',
    'location': 'Warehouse A',
    'timestamp': '2024-12-01T07:00:00',
}


def test_dispatch_shift_assigned_increments_counter():
    from app import metrics
    before = metrics.EVENTS_CONSUMED.labels(event_type='SHIFT_ASSIGNED')._value.get()
    dispatch(dict(BASE_EVENT))
    after = metrics.EVENTS_CONSUMED.labels(event_type='SHIFT_ASSIGNED')._value.get()
    assert after > before


def test_dispatch_increments_notifications_sent():
    from app import metrics
    before = metrics.NOTIFICATIONS_SENT.labels(channel='log')._value.get()
    dispatch(dict(BASE_EVENT))
    after = metrics.NOTIFICATIONS_SENT.labels(channel='log')._value.get()
    assert after > before


def test_dispatch_unknown_event_type_does_not_raise():
    event = {**BASE_EVENT, 'event_type': 'UNKNOWN_TYPE'}
    dispatch(event)  # should not raise


def test_dispatch_missing_fields_does_not_raise():
    dispatch({'event_type': 'SHIFT_ASSIGNED'})  # minimal event


def test_dispatch_records_processing_time():
    from app import metrics
    count_before = metrics.CONSUMER_LAG_PROCESSING_SECONDS._count.get()
    dispatch(dict(BASE_EVENT))
    count_after = metrics.CONSUMER_LAG_PROCESSING_SECONDS._count.get()
    assert count_after > count_before


def test_dispatch_all_fields_logged(caplog):
    import logging
    with caplog.at_level(logging.INFO, logger='app.dispatcher'):
        dispatch(dict(BASE_EVENT))
    assert any('NOTIFICATION_DISPATCHED' in r.message for r in caplog.records)
    assert any('Alice' in r.message for r in caplog.records)
