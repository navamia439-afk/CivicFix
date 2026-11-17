"""
CivicFix Citizen Module Business Controller
Orchestrates citizen workflows including reporting, tracking, neighborhood support,
reopening requests, and satisfaction surveys.
"""

from typing import List, Dict, Any, Optional, Tuple
from services.complaint_service import (
    create_complaint,
    get_citizen_complaints,
    get_complaint_details,
    get_complaint_timeline,
    support_complaint,
    has_supported_complaint,
    reopen_complaint,
    submit_feedback,
    get_citizen_stats,
    get_browseable_complaints,
    CATEGORIES
)
from database.database_operations import fetch_all, execute_update


class CitizenController:
    """Controller exposing business operations for the Citizen interface."""

    def __init__(self, citizen_id: int):
        self.citizen_id = citizen_id

    def submit_issue(
        self,
        title: str,
        description: str,
        category: str,
        location: str,
        locality: str,
        ward_number: Optional[str] = None,
        image_path: Optional[str] = None,
        is_emergency: bool = False,
        is_anonymous: bool = False
    ) -> Tuple[bool, Optional[str], Optional[int], str]:
        """Submits a new civic complaint."""
        return create_complaint(
            citizen_id=self.citizen_id,
            title=title,
            description=description,
            category=category,
            location=location,
            locality=locality,
            ward_number=ward_number,
            image_rel_path=image_path,
            is_emergency=is_emergency,
            is_anonymous=is_anonymous
        )

    def fetch_my_complaints(
        self,
        search_query: Optional[str] = None,
        category_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves complaints submitted by the current citizen."""
        return get_citizen_complaints(
            citizen_id=self.citizen_id,
            search_query=search_query,
            category_filter=category_filter,
            status_filter=status_filter
        )

    def fetch_tracking_details(self, complaint_id_or_code: Any) -> Optional[Dict[str, Any]]:
        """Fetches full tracking details and timeline for a complaint."""
        details = get_complaint_details(complaint_id_or_code)
        if details:
            details["timeline"] = get_complaint_timeline(details["id"])
        return details

    def support_existing_issue(self, complaint_id: int) -> Tuple[bool, int, str]:
        """Adds citizen support to an existing neighborhood complaint."""
        return support_complaint(complaint_id, self.citizen_id)

    def check_has_supported(self, complaint_id: int) -> bool:
        """Checks if citizen has already supported a complaint."""
        return has_supported_complaint(complaint_id, self.citizen_id)

    def request_reopen(self, complaint_id: int, reason: str) -> Tuple[bool, str]:
        """Requests reopening of a resolved/closed complaint."""
        return reopen_complaint(complaint_id, self.citizen_id, reason)

    def rate_and_review(
        self,
        complaint_id: int,
        rating: int,
        comments: Optional[str] = None,
        suggestions: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Submits citizen rating and resolution feedback."""
        return submit_feedback(complaint_id, self.citizen_id, rating, comments, suggestions)

    def get_dashboard_metrics(self) -> Dict[str, int]:
        """Calculates dashboard KPI metrics."""
        return get_citizen_stats(self.citizen_id)

    def browse_community_issues(
        self,
        locality: Optional[str] = None,
        category: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetches neighborhood issues available to support."""
        return get_browseable_complaints(
            citizen_id=self.citizen_id,
            locality=locality,
            category=category,
            search_query=search_query
        )

    def get_notifications(self) -> List[Dict[str, Any]]:
        """Fetches recent notifications for the citizen."""
        return fetch_all(
            "SELECT * FROM Notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 20;",
            (self.citizen_id,)
        )

    def mark_all_notifications_read(self) -> int:
        """Marks all notifications as read."""
        return execute_update(
            "UPDATE Notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0;",
            (self.citizen_id,)
        )
