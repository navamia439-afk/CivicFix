"""
CivicFix Automated Priority Suggestion Service
Calculates recommended priority levels based on emergency indicators,
complaint categories, citizen support volume, and pending elapsed time.
"""

from typing import Tuple, Optional
import datetime

# Priority Levels
PRIORITY_LOW = "LOW"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_HIGH = "HIGH"
PRIORITY_EMERGENCY = "EMERGENCY"

# Standard Categories with baseline weights
HIGH_IMPACT_CATEGORIES = {
    "Road damage / pothole",
    "Water leakage",
    "Drainage blockage"
}


def calculate_suggested_priority(
    category: str,
    is_emergency: bool = False,
    support_count: int = 0,
    submitted_at: Optional[str] = None
) -> Tuple[str, str]:
    """
    Computes a rule-based priority recommendation and explanation.
    
    Returns:
        (suggested_priority, explanation_text)
    """
    # 1. Citizen Emergency Flag is the highest override
    if is_emergency:
        return (
            PRIORITY_EMERGENCY,
            "Flagged as EMERGENCY by citizen: acute public hazard or imminent structural risk."
        )

    # 2. High Community Support Cluster (5+ citizens affected)
    if support_count >= 5:
        return (
            PRIORITY_HIGH,
            f"High community impact: {support_count} citizens reported or supported this issue."
        )

    # 3. High Impact Hazard Categories with support
    if category in HIGH_IMPACT_CATEGORIES:
        if support_count >= 2:
            return (
                PRIORITY_HIGH,
                f"Critical category '{category}' with multiple citizen endorsements."
            )
        return (
            PRIORITY_MEDIUM,
            f"Standard priority for safety category '{category}'."
        )

    # 4. Check Pending Elapsed Time (if older than 3 days, escalate from LOW to MEDIUM)
    is_aged = False
    if submitted_at:
        try:
            # Parse SQLite timestamp
            sub_dt = datetime.datetime.fromisoformat(submitted_at.replace(" ", "T"))
            age_days = (datetime.datetime.now() - sub_dt).days
            if age_days >= 3:
                is_aged = True
        except Exception:
            pass

    if is_aged:
        return (
            PRIORITY_MEDIUM,
            f"Escalated to MEDIUM due to pending duration (> 3 days unaddressed)."
        )

    if category == "Broken streetlight" or category == "Garbage / waste issue":
        return (
            PRIORITY_MEDIUM,
            f"Standard maintenance priority for '{category}'."
        )

    return (
        PRIORITY_LOW,
        "Low impact issue without safety hazard or community clustering."
    )
