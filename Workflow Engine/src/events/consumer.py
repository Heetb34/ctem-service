import asyncio
import json
import logging
from uuid import UUID

from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from src.config import get_settings
from src.models import Workflow
from src.schemas import ExecutionTrigger
from src.services.execution_service import ExecutionService
from src.utils.safe_eval import UnsafeExpressionError, evaluate_condition

logger = logging.getLogger(__name__)
settings = get_settings()


def _trigger_for_event(workflow: Workflow, event: dict):
    """Return a matching event trigger, enforcing tenant and optional filter."""
    event_name = event.get("event_type") or event.get("type")
    if event_name != "ExposureDetected" or not event.get("tenant_id"):
        return None
    if str(workflow.tenant_id) != str(event["tenant_id"]):
        return None
    triggers = workflow.triggers or []
    if isinstance(triggers, dict):
        triggers = [triggers]
    for trigger in triggers:
        if not isinstance(trigger, dict) or trigger.get("type") not in (None, "event"):
            continue
        if (trigger.get("event") or trigger.get("event_type")) != event_name:
            continue
        condition = trigger.get("filter") or trigger.get("condition")
        if condition:
            try:
                if not evaluate_condition(condition, event):
                    continue
            except (UnsafeExpressionError, TypeError, ValueError):
                logger.warning("Ignoring invalid trigger filter for workflow %s", workflow.workflow_id)
                continue
        return trigger
    return None


async def process_exposure_event(event, db_session_factory, redis_client, kafka_producer):
    if not isinstance(event, dict) or event.get("event_type") != "ExposureDetected":
        return 0
    try:
        tenant_id = UUID(str(event["tenant_id"]))
    except (KeyError, ValueError, TypeError):
        logger.warning("Skipping unscoped/malformed exposure event")
        return 0
    started = 0
    async with db_session_factory() as db:
        result = await db.execute(select(Workflow).where(
            Workflow.tenant_id == tenant_id,
            Workflow.status == "active",
            Workflow.deleted_at.is_(None),
        ))
        workflows = result.scalars().all()
        for workflow in workflows:
            if _trigger_for_event(workflow, event) is None:
                continue
            exposure = event.get("exposure") or {}
            trigger_input = {
                "type": "event", "event_type": "ExposureDetected",
                "event_id": event.get("event_id"), "tenant_id": str(tenant_id),
                "cycle_id": event.get("cycle_id"), "severity": event.get("severity"),
                "exposure": exposure, "notification_data": exposure,
                "user_id": event.get("user_id"),
            }
            trigger = ExecutionTrigger(trigger_type="event", input=trigger_input, tenant_id=tenant_id)
            await ExecutionService(db, redis_client, kafka_producer).execute(workflow.workflow_id, trigger)
            started += 1
    return started


async def consume_events(db_session_factory, redis_client, kafka_producer, stop_event=None):
    """Consume at-least-once; commit offsets only after event processing succeeds."""
    while stop_event is None or not stop_event.is_set():
        consumer = AIOKafkaConsumer(
            "exposure-events", bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id="workflow-service", enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        try:
            await consumer.start()
            async for msg in consumer:
                if stop_event is not None and stop_event.is_set():
                    break
                try:
                    await process_exposure_event(msg.value, db_session_factory, redis_client, kafka_producer)
                    await consumer.commit()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Exposure event processing failed; offset will be retried")
                    raise
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Workflow Kafka consumer disconnected; reconnecting")
            await asyncio.sleep(3)
        finally:
            await consumer.stop()
