"""Run proposal-level local Workflow and Notification load checks.

Uses the seeded in-app test user (user-123) and never contacts external
email, SMS, push, Slack, Teams, or webhook providers.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone
from uuid import uuid4

import httpx


def percentiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}

    def at(p: float) -> float:
        return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * p))]

    return {
        "min_ms": round(ordered[0] * 1000, 1),
        "median_ms": round(statistics.median(ordered) * 1000, 1),
        "p95_ms": round(at(0.95) * 1000, 1),
        "max_ms": round(ordered[-1] * 1000, 1),
    }


async def run(base_workflow: str, base_notification: str, user_id: str, count: int, rate_per_minute: int):
    limits = httpx.Limits(max_connections=150, max_keepalive_connections=100)
    async with httpx.AsyncClient(limits=limits, timeout=httpx.Timeout(60.0)) as client:
        tenant_id = str(uuid4())
        workflow_body = {
            "name": f"Performance smoke {uuid4()}",
            "tenant_id": tenant_id,
            "created_by": str(uuid4()),
            "definition": {
                "steps": [{"id": "work", "name": "No-op test action", "type": "action", "action": "create_record"}],
                "connections": [],
            },
            "triggers": [],
        }
        response = await client.post(f"{base_workflow}/workflows/", json=workflow_body)
        response.raise_for_status()
        workflow_id = response.json()["workflow_id"]

        start_gate = asyncio.Event()
        workflow_samples: list[float] = []
        workflow_errors: list[str] = []
        workflow_start_samples: list[float] = []
        completed = 0

        async def execute_one(index: int) -> None:
            nonlocal completed
            await start_gate.wait()
            started = time.perf_counter()
            request_started_at = datetime.now(timezone.utc)
            try:
                result = await client.post(
                    f"{base_workflow}/executions/workflows/{workflow_id}/execute",
                    json={
                        "trigger_type": "manual",
                        "tenant_id": tenant_id,
                        "input": {"type": "manual", "perf_run": str(uuid4()), "index": index},
                    },
                )
                result.raise_for_status()
                if result.json().get("status") != "completed":
                    raise RuntimeError(f"execution status was {result.json().get('status')}")
                execution_started_at = result.json().get("started_at")
                if execution_started_at:
                    parsed_started_at = datetime.fromisoformat(execution_started_at.replace("Z", "+00:00"))
                    if parsed_started_at.tzinfo is None:
                        parsed_started_at = parsed_started_at.replace(tzinfo=timezone.utc)
                    workflow_start_samples.append(max(0.0, (parsed_started_at - request_started_at).total_seconds()))
                completed += 1
                workflow_samples.append(time.perf_counter() - started)
            except Exception as exc:
                workflow_errors.append(f"{index}: {type(exc).__name__}: {exc}")

        workflow_tasks = [asyncio.create_task(execute_one(i)) for i in range(100)]
        workflow_start = time.perf_counter()
        start_gate.set()
        await asyncio.gather(*workflow_tasks)
        workflow_elapsed = time.perf_counter() - workflow_start

        notification_samples: list[float] = []
        notification_errors: list[str] = []
        published: dict[str, int] = {}
        semaphore = asyncio.Semaphore(100)
        marker = str(uuid4())
        request_start = time.perf_counter()

        async def send_one(index: int) -> None:
            started = time.perf_counter()
            async with semaphore:
                try:
                    result = await client.post(
                        f"{base_notification}/notifications",
                        json={
                            "userId": user_id,
                            "channel": "in-app",
                            "templateId": "security-alert",
                            "data": {
                                "severity": "Low",
                                "description": "Load verification",
                                "perf_run": marker,
                                "index": index,
                            },
                        },
                    )
                    result.raise_for_status()
                    item = result.json()
                    published[item["notification_id"]] = int(item["timestamp"])
                    notification_samples.append(time.perf_counter() - started)
                except Exception as exc:
                    notification_errors.append(f"{index}: {type(exc).__name__}: {exc}")

        interval = 60.0 / rate_per_minute
        tasks = []
        for index in range(count):
            delay = request_start + index * interval - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            tasks.append(asyncio.create_task(send_one(index)))
        await asyncio.gather(*tasks)
        posting_elapsed = time.perf_counter() - request_start

        delivered: dict[str, dict] = {}
        deadline = time.perf_counter() + 300
        while len(delivered) < len(published) and time.perf_counter() < deadline:
            try:
                feed = await client.get(f"{base_notification}/notifications/user/{user_id}")
                feed.raise_for_status()
                for item in feed.json():
                    notification_id = item.get("notification_id")
                    if notification_id in published:
                        delivered[notification_id] = item
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                notification_errors.append(f"feed poll: {type(exc).__name__}: {exc}")
            if len(delivered) < len(published):
                await asyncio.sleep(2)

        delivery_latencies: list[float] = []
        sent_count = failed_count = 0
        for notification_id, item in delivered.items():
            if item.get("status") == "SENT":
                sent_count += 1
                created = datetime.strptime(item["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                published_at = datetime.fromtimestamp(published[notification_id] / 1000, timezone.utc)
                delivery_latencies.append(max(0.0, (created - published_at).total_seconds()))
            else:
                failed_count += 1

        try:
            await client.delete(f"{base_workflow}/workflows/{workflow_id}")
        except httpx.HTTPError:
            pass

        accepted_timestamps = [timestamp for timestamp in published.values()]
        accepted_window_s = (
            (max(accepted_timestamps) - min(accepted_timestamps)) / 1000
            if len(accepted_timestamps) > 1 else 0
        )

        return {
            "workflow": {
                "requested_concurrent": 100,
                "completed": completed,
                "failures": len(workflow_errors),
                "elapsed_s": round(workflow_elapsed, 2),
                "end_to_end_latency": percentiles(workflow_samples),
                "under_1_second": sum(value < 1 for value in workflow_samples),
                "execution_start_latency_ms": percentiles(workflow_start_samples),
                "execution_started_under_1_second": sum(value < 1 for value in workflow_start_samples),
                "errors": workflow_errors[:10],
            },
            "notifications": {
                "count": count,
                "target_rate_per_minute": rate_per_minute,
                "posting_elapsed_s": round(posting_elapsed, 2),
                "achieved_rate_per_minute": round(count * 60 / posting_elapsed, 1) if posting_elapsed else 0,
                "accepted_timestamp_window_s": round(accepted_window_s, 2),
                "accepted_timestamp_rate_per_minute": round(
                    count * 60 / accepted_window_s, 1
                ) if accepted_window_s else 0,
                "post_failures": len(notification_errors),
                "post_latency": percentiles(notification_samples),
                "sent": sent_count,
                "failed_delivery": failed_count,
                "unobserved_before_5_minute_deadline": len(published) - len(delivered),
                "delivery_latency_seconds": percentiles(delivery_latencies),
                "errors": notification_errors[:10],
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-url", default="http://localhost:8001")
    parser.add_argument("--notification-url", default="http://localhost:3000")
    parser.add_argument("--user-id", default="user-123")
    parser.add_argument("--notifications", type=int, default=1000)
    parser.add_argument("--rate-per-minute", type=int, default=1000)
    args = parser.parse_args()
    result = asyncio.run(run(args.workflow_url, args.notification_url, args.user_id, args.notifications, args.rate_per_minute))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
