import json
import logging
from datetime import datetime
from app.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC

logger = logging.getLogger(__name__)
_producer = None


def _get_producer():
    global _producer
    if _producer is not None:
        return _producer
    try:
        from kafka import KafkaProducer
        _producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3,
            acks='all',
            request_timeout_ms=5000,
        )
        logger.info('Kafka producer connected to %s', KAFKA_BOOTSTRAP_SERVERS)
    except Exception as exc:
        logger.warning('Kafka producer unavailable (%s) – events will not be published.', exc)
    return _producer


def produce_shift_event(event_type: str, shift_id: int, staff_id: int, **kwargs) -> None:
    producer = _get_producer()
    if producer is None:
        return
    message = {
        'event_type': event_type,
        'shift_id': shift_id,
        'staff_id': staff_id,
        'timestamp': datetime.utcnow().isoformat(),
        **kwargs,
    }
    try:
        future = producer.send(KAFKA_TOPIC, value=message)
        future.get(timeout=5)
        logger.info('Kafka: published %s (shift=%d staff=%d)', event_type, shift_id, staff_id)
    except Exception as exc:
        logger.error('Kafka: failed to publish event – %s', exc)
