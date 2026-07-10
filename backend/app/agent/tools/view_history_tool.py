"""LangGraph Tool 3 - View Interaction History.

Retrieves previously logged interactions, optionally filtered by HCP name
and/or date range, sorted chronologically (most recent first).
"""
from datetime import date
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.interaction_service import InteractionService, serialize_interaction


class ViewHistoryArgs(BaseModel):
    hcp_name: Optional[str] = Field(
        None, description="Filter history to interactions with this HCP name (partial match ok)"
    )
    date_from: Optional[date] = Field(None, description="Only include interactions on/after this date")
    date_to: Optional[date] = Field(None, description="Only include interactions on/before this date")
    limit: Optional[int] = Field(10, description="Maximum number of interactions to return")


def make_view_history_tool(db: Session, session_id: str) -> StructuredTool:
    service = InteractionService(db)

    def _run(
        hcp_name: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: Optional[int] = 10,
    ) -> dict:
        interactions = service.list_history(
            doctor_name=hcp_name, date_from=date_from, date_to=date_to, limit=limit or 10
        )
        items = [serialize_interaction(i) for i in interactions]

        if not items:
            scope = f" for {hcp_name}" if hcp_name else ""
            return {
                "status": "success",
                "message": f"No interaction history found{scope}.",
                "history": [],
            }

        scope = f" with {hcp_name}" if hcp_name else ""
        return {
            "status": "success",
            "message": f"Found {len(items)} interaction(s){scope}.",
            "history": items,
        }

    return StructuredTool.from_function(
        func=_run,
        name="view_interaction_history",
        description=(
            "Retrieve previously logged HCP interactions, optionally filtered by HCP name and/or "
            "a date range, sorted with the most recent first."
        ),
        args_schema=ViewHistoryArgs,
    )
