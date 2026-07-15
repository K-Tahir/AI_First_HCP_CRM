"""LangGraph Tool 4 - Schedule Follow-up.

Creates a follow-up record (date + notes) associated with an interaction.

Target resolution goes through InteractionService.resolve_target_interaction:
an explicit interaction_id wins, then hcp_name is looked up via tiered name
matching, and only when neither is given does it fall back to the most
recently logged interaction in the session. Previously, a hcp_name with zero
matches silently fell back to "latest interaction in session" regardless of
whose HCP that was - which is how a follow-up meant for one doctor could end
up attached to a completely different one with no error surfaced anywhere.
That silent fallback no longer happens: zero or multiple matches now return
a not_found/ambiguous result for the assistant to ask about instead.
"""
from datetime import date
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.repositories.followup_repository import FollowUpRepository
from app.services.interaction_service import InteractionService, serialize_interaction


class ScheduleFollowUpArgs(BaseModel):
    interaction_id: Optional[int] = Field(
        None,
        description=(
            "ID of the interaction this follow-up relates to. If omitted, hcp_name (if given) "
            "is used to locate it; otherwise the most recently logged interaction in this "
            "conversation is used."
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
        resolution = interaction_service.resolve_target_interaction(session_id, interaction_id, hcp_name)
        if resolution["status"] != "resolved":
            # not_found / ambiguous - never fall back to "whatever interaction was
            # touched last"; that cross-HCP guess is exactly what caused follow-ups
            # to land on the wrong doctor.
            result = {"status": resolution["status"], "message": resolution["message"]}
            if "candidates" in resolution:
                result["candidates"] = resolution["candidates"]
            return result
        target = resolution["interaction"]
        target_id = target.id

        follow_up = followups.create(
            interaction_id=target_id, follow_up_date=follow_up_date, notes=notes, status="Pending"
        )
        # Also mirror the follow-up date onto the interaction so the left panel reflects it.
        interaction = interaction_service.update_interaction(
            target_id, {"follow_up_date": follow_up_date}
        )
        db.commit()

        target_hcp_display = interaction.doctor.name if interaction.doctor else "this interaction"
        return {
            "status": "success",
            "message": (
                f"Scheduled a follow-up for {target_hcp_display} on "
                f"{follow_up_date.strftime('%d/%m/%Y')}."
            ),
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
