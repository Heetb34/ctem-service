from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.config import get_settings
from src.services.workflow_service import WorkflowService
from src.services.execution_service import ExecutionService
from src.services.approval_service import ApprovalService
import redis.asyncio as redis
from aiokafka import AIOKafkaProducer
import json

async def get_redis():
    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url)
    yield redis_client
    await redis_client.close()

async def get_kafka_producer():
    settings = get_settings()
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode()
    )
    await producer.start()
    yield producer
    await producer.stop()

async def get_workflow_service(db: AsyncSession = Depends(get_db)):
    return WorkflowService(db)

async def get_execution_service(db: AsyncSession = Depends(get_db), redis=Depends(get_redis), kafka=Depends(get_kafka_producer)):
    return ExecutionService(db, redis, kafka)

async def get_approval_service(db: AsyncSession = Depends(get_db)):
    return ApprovalService(db)
