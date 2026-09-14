from aiokafka import AIOKafkaConsumer
import json
from src.services.execution_service import ExecutionService
from src.config import get_settings

settings = get_settings()

async def consume_events(db_session_factory, redis_client, kafka_producer):
    consumer = AIOKafkaConsumer(
        "exposure-events",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="workflow-service",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    await consumer.start()
    try:
        async for msg in consumer:
            event = msg.value
            if event.get("event_type") == "ExposureDetected":
                # In real implementation, you would query DB to find workflows triggered by this event
                # For now, we just log and skip
                print(f"Received ExposureDetected event: {event}")
    finally:
        await consumer.stop()
