# 20+ prebuilt workflow templates (stubs – you can add more)
WORKFLOW_TEMPLATES = {
    "WT-01": {
        "name": "Exposure Triage",
        "description": "Auto-triage new exposures",
        "definition": {
            "steps": [
                {"id": "start", "type": "condition", "condition": "context.severity in ['critical','high']"},
                {"id": "notify", "type": "action", "action": "send_notification", "input": {"channel": "slack"}},
                {"id": "create_record", "type": "action", "action": "create_record", "input": {"table": "exposures"}}
            ]
        },
        "trigger": {"type": "event", "event": "ExposureDetected"}
    },
    "WT-02": {
        "name": "Critical Exposure Escalation",
        "description": "Immediate escalation for critical exposures",
        "definition": {
            "steps": [
                {"id": "page", "type": "action", "action": "send_notification", "input": {"channel": "sms"}},
                {"id": "approval", "type": "approval", "approvers": ["role:oncall_sec"], "sla_hours": 1}
            ]
        },
        "trigger": {"type": "event", "event": "ExposureDetected", "filter": "severity == 'critical'"}
    },
    # Add more templates as needed
}
