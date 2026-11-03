from types import SimpleNamespace
from uuid import uuid4

from src.events.consumer import _trigger_for_event
from src.utils.safe_eval import evaluate_condition


def test_trigger_requires_event_and_matching_tenant():
    tenant_id = uuid4()
    workflow = SimpleNamespace(tenant_id=tenant_id, triggers=[{
        "type": "event", "event": "ExposureDetected", "filter": "severity == 'critical'"
    }])

    assert _trigger_for_event(workflow, {
        "event_type": "ExposureDetected", "tenant_id": str(tenant_id), "severity": "critical"
    }) is not None
    assert _trigger_for_event(workflow, {
        "event_type": "ExposureDetected", "tenant_id": str(uuid4()), "severity": "critical"
    }) is None
    assert _trigger_for_event(workflow, {
        "event_type": "ExposureDetected", "tenant_id": str(tenant_id), "severity": "low"
    }) is None


def test_safe_eval_exposes_flat_fields_without_attribute_access():
    assert evaluate_condition("severity == 'critical' and risk_score >= 80", {
        "severity": "critical", "risk_score": 91
    })
