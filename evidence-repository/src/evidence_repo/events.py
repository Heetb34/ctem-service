
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaProducer

from .config import get_settings
from .logging import log


_producer: AIOKafkaProducer | None = None
_producer_loop: asyncio.AbstractEventLoop | None = None


async def get_producer() -> AIOKafkaProducer:
    global _producer, _producer_loop

    current_loop = asyncio.get_running_loop()

    # Reuse the producer only on its original event loop.
    if _producer is not None and _producer_loop is current_loop:
        return _producer

    # Never reuse a producer attached to another event loop.
    if _producer is not None:
        if _producer_loop is not None and not _producer_loop.is_closed():
            log.warning(
                "kafka_producer_loop_changed",
                message="Previous producer belongs to another event loop",
            )

        _producer = None
        _producer_loop = None

    producer = AIOKafkaProducer(
        bootstrap_servers=get_settings().kafka_bootstrap
    )

    await producer.start()

    _producer = producer
    _producer_loop = current_loop

    return producer


async def stop_producer() -> None:
    global _producer, _producer_loop

    producer = _producer
    producer_loop = _producer_loop

    _producer = None
    _producer_loop = None

    if producer is None:
        return

    current_loop = asyncio.get_running_loop()

    if producer_loop is current_loop:
        await producer.stop()
    else:
        log.warning(
            "kafka_producer_stop_skipped",
            message="Producer belongs to another event loop",
        )


async def publish(
    event_type: str,
    tenant_id: uuid.UUID,
    payload: dict[str, Any],
) -> None:

    envelope = {
        "event_type": event_type,
        "schema_version": "1.0",
        "tenant_id": str(tenant_id),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }

    try:
        producer = await get_producer()

        await producer.send_and_wait(
            "evidence.events",
            json.dumps(envelope).encode(),
            key=str(tenant_id).encode(),
        )

    except Exception as e:
        log.error(
            "kafka_publish_failed",
            event_type=event_type,
            error=str(e),
        )
