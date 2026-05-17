import os

DATABASE_URL: str = os.getenv(
    'DATABASE_URL',
    'postgresql://shiftboard:shiftboard123@localhost:5432/shiftboard',
)

KAFKA_BOOTSTRAP_SERVERS: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC: str = os.getenv('KAFKA_TOPIC', 'shift-events')
