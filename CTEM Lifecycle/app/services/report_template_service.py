from copy import deepcopy


COMMON_PARAMETERS = [
    "cycle_id",
    "start_date",
    "end_date",
    "severity",
    "status",
    "business_unit",
    "asset_group",
    "owner",
]


_TEMPLATE_DEFINITIONS = [
    ("executive-overview", "Executive CTEM Overview", "Overall CTEM risk and exposure summary", "Executive"),
    ("exposure-inventory", "Exposure Inventory", "Detailed inventory of identified exposures", "Exposure"),
    ("severity-breakdown", "Risk by Severity", "Exposure distribution across severity levels", "Risk"),
    ("asset-exposure", "Asset Exposure Summary", "Exposures grouped by asset", "Asset"),
    ("critical-assets", "Critical Asset Report", "Exposure summary for critical business assets", "Asset"),
    ("attack-surface", "Attack Surface Summary", "Overview of recorded attack surface exposures", "Exposure"),
    ("exposure-trends", "Exposure Trend Report", "Changes in exposures over time", "Trend"),
    ("remediation-progress", "Remediation Progress", "Summary of remediation status and completion", "Remediation"),
    ("overdue-remediations", "Overdue Remediations", "Remediation items requiring attention", "Remediation"),
    ("validation-results", "Validation Results", "Validation plans and their recorded results", "Validation"),
    ("exceptions-register", "Exceptions Register", "List of recorded security exceptions", "Exception"),
    ("exception-expiry", "Exception Expiry Report", "Exceptions approaching or past expiry", "Exception"),
    ("framework-coverage", "Framework Coverage", "Mapping status across security frameworks", "Compliance"),
    ("nist-csf-coverage", "NIST CSF Coverage", "Recorded mappings for NIST CSF controls", "Compliance"),
    ("compliance-gaps", "Compliance Gaps", "Framework mappings requiring attention", "Compliance"),
    ("cycle-summary", "CTEM Cycle Summary", "Summary of exposures and activities for a cycle", "Cycle"),
    ("cycle-comparison", "CTEM Cycle Comparison", "Compare recorded results between CTEM cycles", "Comparison"),
    ("annual-exposure-trend", "12-Month Exposure Trend", "Monthly exposure trends across twelve months", "Trend"),
    ("business-unit-risk", "Business Unit Risk", "Risk breakdown by business unit", "Risk"),
    ("asset-group-risk", "Asset Group Risk", "Risk breakdown by asset group", "Risk"),
    ("owner-accountability", "Owner Accountability", "Recorded remediation and validation ownership", "Operations"),
    ("high-risk-exposures", "High-Risk Exposures", "Exposures with high recorded risk or severity", "Risk"),
    ("new-exposures", "New Exposures", "Exposures recorded within a selected period", "Exposure"),
    ("closed-exposures", "Closed Exposures", "Exposures recorded as closed or resolved", "Exposure"),
    ("operations-summary", "CTEM Operations Summary", "Summary of recorded validation and remediation activity", "Operations"),
]


BUILT_IN_TEMPLATES = [
    {
        "id": template_id,
        "name": name,
        "description": description,
        "category": category,
        "version": "1.0",
        "built_in": True,
        "supported_formats": ["pdf", "csv", "xlsx"],
        "parameters": COMMON_PARAMETERS.copy(),
    }
    for template_id, name, description, category in _TEMPLATE_DEFINITIONS
]


def get_report_templates():
    """Return the available built-in report template definitions."""
    return deepcopy(BUILT_IN_TEMPLATES)


def get_report_template(template_id: str):
    """Return one built-in template, or None if it does not exist."""
    for template in BUILT_IN_TEMPLATES:
        if template["id"] == template_id:
            return deepcopy(template)

    return None