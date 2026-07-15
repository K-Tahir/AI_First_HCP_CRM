"""LangGraph Tool 2 - Edit Interaction.

Applies a partial correction to an already-logged interaction. Only the
fields explicitly supplied are changed; everything else is preserved.

Target resolution (which interaction gets edited) goes through
InteractionService.resolve_target_interaction: an explicit interaction_id
wins, then target_hcp_name is looked up, and only when neither is given does
it fall back to the most recently logged interaction in the session. A
target_hcp_name that doesn't match exactly one HCP returns a not_found /
ambiguous result instead of guessing - see resolve_target_interaction's
docstring for why that matters.
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
            "ID of the interaction to edit, if known. If omitted, target_hcp_name (if given) is "
            "used to locate it; otherwise the most recently logged interaction in this "
            "conversation is edited."
        ),
    )
    target_hcp_name: Optional[str] = Field(
        None,
        description=(
            "The HCP the rep is referring to, used ONLY to find WHICH interaction to edit when "
            "interaction_id isn't known - e.g. the rep says 'fix Dr. Sharma's notes' or 'no, I "
            "meant the Sharma interaction'. Do NOT use this to correct a misspelled name on the "
            "record - that's what the separate hcp_name field is for."
        ),
    )
    hcp_name: Optional[str] = Field(
        None,
        description=(
            "The CORRECTED HCP name to write onto the target interaction - use this only when "
            "the rep is fixing a wrong/misspelled name already on that record, e.g. 'actually "
            "his name is spelled Mohammed, not Mohamed'."
        ),
    )
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

    def _run(interaction_id: Optional[int] = None, target_hcp_name: Optional[str] = None, **kwargs) -> dict:
        resolution = service.resolve_target_interaction(session_id, interaction_id, target_hcp_name)
        if resolution["status"] != "resolved":
            # not_found / ambiguous - surfaced as-is so the assistant asks the rep to
            # clarify instead of guessing and silently editing the wrong record.
            result = {"status": resolution["status"], "message": resolution["message"]}
            if "candidates" in resolution:
                result["candidates"] = resolution["candidates"]
            return result
        target_id = resolution["interaction"].id

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
