import os
import httpx

CTEM_SERVICE_URL = os.getenv(
    "CTEM_SERVICE_URL",
    "http://localhost:8000"
).rstrip("/")


def _get(path):
    try:
        response = httpx.get(
            f"{CTEM_SERVICE_URL}{path}",
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Unable to retrieve CTEM data from {path}: {exc}"
        ) from exc


def get_exposures(cycle_id):
    return _get(f"/ctem/cycles/{cycle_id}/exposures")


def get_validation_plans(cycle_id):
    return _get(f"/ctem/cycles/{cycle_id}/validation-plan")


def get_remediations(cycle_id):
    return _get(f"/ctem/cycles/{cycle_id}/remediation")


def get_exceptions(cycle_id):
    return _get(f"/ctem/cycles/{cycle_id}/exceptions")


def get_framework_mappings(cycle_id):
    return _get(f"/ctem/cycles/{cycle_id}/framework-mappings")
