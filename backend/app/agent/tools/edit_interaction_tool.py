"""LangGraph Tool 2 - Edit Interaction.

Applies a partial correction to an already-logged interaction. Only the
fields explicitly supplied are changed; everything else is preserved.
Defaults to the most recently logged interaction in the current session
unless an explicit interaction_id is given.
"""
from datetime import date
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.interaction_service import InteractionService, serialize_interaction


class EditInteractionArgs(BaseModel):
    interaction_id: Optional[int] = Field(
        None,
        description=(
            "ID of the interaction to edit, if known. If omitted, the most recently logged "
            "interaction in this conversation is edited."
        ),
    )
    hcp_name: Optional[str] = Field(None, description="Corrected HCP name")
    hospital: Optional[str] = None
    specialty: Optional[str] = None
    interaction_date: Optional[date] = None
    interaction_type: Optional[str] = Field(
        None, description="One of: Meeting, Call, Email, Conference, Virtual"
    )
    products_discussed: Optional[list[str]] = Field(
        None, description="Corrected/updated list of product names discussed"
    )
    sentiment: Optional[str] = Field(None, description="Corrected sentiment: Positive, Neutral, Negative")
    brochures_shared: Optional[bool] = None
    samples_requested: Optional[bool] = None
    questions_raised: Optional[str] = None
    notes: Optional[str] = None
    discussion_summary: Optional[str] = None
    follow_up_date: Optional[date] = None


def make_edit_interaction_tool(db: Session, session_id: str) -> StructuredTool:
    service = InteractionService(db)

    def _run(interaction_id: Optional[int] = None, **kwargs) -> dict:
        target_id = interaction_id
        if target_id is None:
            latest = service.get_latest_for_session(session_id)
            if latest is None:
                return {
                    "status": "error",
                    "message": (
                        "There's no interaction logged yet in this conversation to edit. "
                        "Please log an interaction first."
                    ),
                }
            target_id = latest.id

        updates = {k: v for k, v in kwargs.items() if v is not None}
        if not updates:
            return {"status": "error", "message": "No fields were specified to update."}

        try:
            interaction = service.update_interaction(target_id, updates)
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

        payload = serialize_interaction(interaction)
        changed_fields = ", ".join(updates.keys())
        return {
            "status": "success",
            "message": f"Updated the following field(s): {changed_fields}.",
            "interaction": payload,
        }

    return StructuredTool.from_function(
        func=_run,
        name="edit_interaction",
        description=(
            "Modify one or more fields of an already-logged interaction. Only pass the fields "
            "that actually changed - all other fields are preserved untouched."
        ),
        args_schema=EditInteractionArgs,
    )
