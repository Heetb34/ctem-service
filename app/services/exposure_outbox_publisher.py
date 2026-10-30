import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

from aiokafka import AIOKafkaProducer
from sqlalchemy import or_

from app.database import SessionLocal
from app.models.outbox_event import OutboxEvent

logger = logging.getLogger(__name__)
OUTBOX_LEASE = timedelta(seconds=60)


def _claim_next_event():
    now = datetime.utcnow()
    with SessionLocal() as db:
        event = (
            db.query(OutboxEvent)
            .filter(
                OutboxEvent.published_at.is_(None),
                OutboxEvent.next_attempt_at <= now,
                or_(OutboxEvent.lease_until.is_(None), OutboxEvent.lease_until <= now),
            )
            .order_by(OutboxEvent.id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if event is None:
            return None

        event.lease_until = now + OUTBOX_LEASE
        claimed = {"id": event.id, "topic": event.topic, "payload": event.payload}
        db.commit()
        return claimed


def _mark_published(event_id: int):
    with SessionLocal() as db:
        event = db.get(OutboxEvent, event_id)
        if event is None:
            return
        event.published_at = datetime.utcnow()
        event.lease_until = None
        event.last_error = None
        db.commit()


def _mark_failed(event_id: int, error: Exception):
    now = datetime.utcnow()
    with SessionLocal() as db:
        event = db.get(OutboxEvent, event_id)
        if event is None:
            return
        event.attempts += 1
        delay = min(300, 2 ** min(event.attempts, 8))
        event.next_attempt_at = now + timedelta(seconds=delay)
        event.lease_until = None
        event.last_error = f"{type(error).__name__}: {error}"[:1000]
        db.commit()


async def publish_exposure_outbox(stop_event: asyncio.Event):
    """Retry pending CTEM events until the app shuts down."""
    brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    while not stop_event.is_set():
        producer = AIOKafkaProducer(
            bootstrap_servers=brokers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )
        producer_started = False
        try:
            await producer.start()
            producer_started = True
            while not stop_event.is_set():
                event = await asyncio.to_thread(_claim_next_event)
                if event is None:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=1)
                    except asyncio.TimeoutError:
                        pass
                    continue

                try:
                    await producer.send_and_wait(event["topic"], event["payload"])
                except Exception as exc:
                    await asyncio.to_thread(_mark_failed, event["id"], exc)
                    logger.exception("Failed to publish CTEM outbox event %s", event["id"])
                else:
                    await asyncio.to_thread(_mark_published, event["id"])
                    logger.info("Published CTEM outbox event %s", event["id"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("CTEM outbox publisher disconnected; retrying")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=3)
            except asyncio.TimeoutError:
                pass
        finally:
            if producer_started:
                await producer.stop()
