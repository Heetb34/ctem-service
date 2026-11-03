import asyncio
import math

class RetryManager:
    def calculate_backoff(self, strategy: str, attempt: int) -> float:
        base = 5  # seconds
        if strategy == "linear":
            return attempt * base
        elif strategy == "exponential":
            return min(base * (2 ** attempt), 300)  # max 5 min
        else:
            return base
