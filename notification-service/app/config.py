import os

KAFKA_BOOTSTRAP_SERVERS: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_CONSUMER_GROUP: str = os.getenv('KAFKA_CONSUMER_GROUP', 'notification-group')
KAFKA_TOPIC: str = os.getenv('KAFKA_TOPIC', 'shift-events')
