import hashlib
import json
from redis.asyncio import Redis
from src.config import get_settings

settings = get_settings()

class IdempotencyManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.ttl = settings.idempotency_ttl
        self.prefix = "idempotency:"

    def generate_key(self, workflow_id, trigger_data):
        data = f"{workflow_id}:{json.dumps(trigger_data, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()

    async def get_existing(self, key):
        val = await self.redis.get(f"{self.prefix}{key}")
        if val:
            return json.loads(val)
        return None

    async def set_execution(self, key, execution_data):
        await self.redis.setex(f"{self.prefix}{key}", self.ttl, json.dumps(execution_data))
