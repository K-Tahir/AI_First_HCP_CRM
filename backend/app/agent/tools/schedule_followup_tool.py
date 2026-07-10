"""LangGraph Tool 4 - Schedule Follow-up.

Creates a follow-up record (date + notes) associated with an interaction.
Defaults to the most recently logged interaction in the current session
unless an explicit interaction_id is given.
"""
from datetime import date
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.repositories.followup_repository import FollowUpRepository
from app.services.interaction_service import InteractionService


class ScheduleFollowUpArgs(BaseModel):
    interaction_id: Optional[int] = Field(
        None,
        description=(
            "ID of the interaction this follow-up relates to. If omitted, uses the most "
            "recently logged interaction in this conversation."
        ),
    )
    hcp_name: Optional[str] = Field(
        None, description="HCP name, used to locate the interaction if interaction_id is unknown"
    )
    follow_up_date: date = Field(..., description="Date the follow-up should occur")
    notes: Optional[str] = Field(None, description="Notes describing what the follow-up is for")


def make_schedule_followup_tool(db: Session, session_id: str) -> StructuredTool:
    interaction_service = InteractionService(db)
    followups = FollowUpRepository(db)

    def _run(
        follow_up_date: date,
        interaction_id: Optional[int] = None,
        hcp_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        target_id = interaction_id

        if target_id is None and hcp_name:
            matches = interaction_service.list_history(doctor_name=hcp_name, limit=1)
            if matches:
                target_id = matches[0].id

        if target_id is None:
            latest = interaction_service.get_latest_for_session(session_id)
            if latest is None:
                return {
                    "status": "error",
                    "message": (
                        "There's no interaction to attach this follow-up to yet. Please log an "
                        "interaction first, or specify which HCP the follow-up is for."
                    ),
                }
            target_id = latest.id

        follow_up = followups.create(
            interaction_id=target_id, follow_up_date=follow_up_date, notes=notes, status="Pending"
        )
        # Also mirror the follow-up date onto the interaction so the left panel reflects it.
        interaction = interaction_service.update_interaction(
            target_id, {"follow_up_date": follow_up_date}
        )
        db.commit()

        from app.services.interaction_service import serialize_interaction

        return {
            "status": "success",
            "message": f"Scheduled a follow-up for {follow_up_date.strftime('%d/%m/%Y')}.",
            "follow_up": {
                "id": follow_up.id,
                "interaction_id": follow_up.interaction_id,
                "follow_up_date": follow_up.follow_up_date,
                "notes": follow_up.notes,
                "status": follow_up.status,
            },
            "interaction": serialize_interaction(interaction),
        }

    return StructuredTool.from_function(
        func=_run,
        name="schedule_followup",
        description=(
            "Create a follow-up action (date + notes) tied to an interaction, so the rep "
            "remembers to revisit or re-contact the HCP."
        ),
        args_schema=ScheduleFollowUpArgs,
    )
