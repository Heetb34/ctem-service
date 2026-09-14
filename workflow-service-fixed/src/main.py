from fastapi import FastAPI
from contextlib import asynccontextmanager
import redis.asyncio as redis
from aiokafka import AIOKafkaProducer
import json
from src.config import get_settings
from src.database import engine, Base, AsyncSessionLocal
from src.api.routes import workflows, executions, approvals
# from src.events.consumer import consume_events  # uncomment if needed
import asyncio

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.redis = redis.from_url(settings.redis_url)
    app.state.kafka_producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode()
    )
    await app.state.kafka_producer.start()
    # Start background consumer (if needed)
    # asyncio.create_task(consume_events(AsyncSessionLocal, app.state.redis, app.state.kafka_producer))
    yield
    # Shutdown
    await app.state.redis.close()
    await app.state.kafka_producer.stop()

app = FastAPI(lifespan=lifespan)

app.include_router(workflows.router)
app.include_router(executions.router)
app.include_router(approvals.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
