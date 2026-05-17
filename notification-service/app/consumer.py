# Kafka Consumer – runs in a background thread started at app startup.
# Uses async-retry semantics: on transient errors the consumer continues
# (does not commit the offset) so Kafka will redeliver the message.

import json
import logging
import threading
import time

from app.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_CONSUMER_GROUP, KAFKA_TOPIC
from app.dispatcher import dispatch
from app.metrics import RETRY_COUNTER

logger = logging.getLogger(__name__)

_consumer_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _consume_loop() -> None:
    """
    Long-running loop that connects to Kafka and processes shift events.
    Retries with exponential back-off on connection failures.
    """
    retry_delay = 2  # seconds

    while not _stop_event.is_set():
        try:
            from kafka import KafkaConsumer
            logger.info(
                'Connecting to Kafka broker=%s topic=%s group=%s',
                KAFKA_BOOTSTRAP_SERVERS,
                KAFKA_TOPIC,
                KAFKA_CONSUMER_GROUP,
            )
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_CONSUMER_GROUP,
                auto_offset_reset='earliest',
                enable_auto_commit=False,   # manual commit for at-least-once semantics
                value_deserializer=lambda b: json.loads(b.decode('utf-8')),
                consumer_timeout_ms=1000,   # poll timeout; lets us check _stop_event
                max_poll_interval_ms=300_000,
                session_timeout_ms=30_000,
                heartbeat_interval_ms=10_000,
            )
            logger.info('Kafka consumer ready – polling for events')
            retry_delay = 2  # reset back-off on successful connect

            for message in consumer:
                if _stop_event.is_set():
                    break
                try:
                    dispatch(message.value)
                    consumer.commit()  # commit only after successful dispatch
                except Exception as exc:
                    logger.error(
                        'Failed to dispatch event (will retry on next poll): %s', exc
                    )
                    RETRY_COUNTER.inc()
                    # Do NOT commit – Kafka will redeliver this message

            consumer.close()

        except Exception as exc:
            logger.warning(
                'Kafka consumer error: %s – retrying in %ds', exc, retry_delay
            )
            RETRY_COUNTER.inc()
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # exponential back-off, cap 60s


def start_consumer() -> None:
    """Launch the Kafka consumer in a daemon thread."""
    global _consumer_thread
    _stop_event.clear()
    _consumer_thread = threading.Thread(target=_consume_loop, daemon=True, name='kafka-consumer')
    _consumer_thread.start()
    logger.info('Kafka consumer thread started')


def stop_consumer() -> None:
    """Signal the consumer thread to stop and wait for it."""
    _stop_event.set()
    if _consumer_thread and _consumer_thread.is_alive():
        _consumer_thread.join(timeout=10)
    logger.info('Kafka consumer thread stopped')
