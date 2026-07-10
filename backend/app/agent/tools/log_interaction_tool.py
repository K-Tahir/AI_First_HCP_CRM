"""LangGraph Tool 1 - Log Interaction.

Captures a brand-new HCP interaction from natural language: extracts entities
(HCP name, hospital, products, etc.), detects sentiment, summarizes the
discussion, and persists a new Interaction row. This is the ONLY code path
that is allowed to create Interaction records.
"""
from datetime import date
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.interaction_service import InteractionService, serialize_interaction


class LogInteractionArgs(BaseModel):
    hcp_name: str = Field(..., description="Full name of the Healthcare Professional, e.g. 'Dr. Smith'")
    hospital: Optional[str] = Field(None, description="Hospital or clinic the HCP is affiliated with")
    specialty: Optional[str] = Field(None, description="Medical specialty of the HCP, e.g. Cardiology")
    interaction_date: Optional[date] = Field(
        None, description="Date the interaction took place, resolved from relative terms like 'today'"
    )
    interaction_type: Optional[str] = Field(
        None, description="One of: Meeting, Call, Email, Conference, Virtual"
    )
    products_discussed: Optional[list[str]] = Field(
        None, description="List of product names discussed during the interaction"
    )
    sentiment: Optional[str] = Field(
        None, description="Overall HCP sentiment: Positive, Neutral, or Negative"
    )
    brochures_shared: Optional[bool] = Field(None, description="Whether brochures were shared")
    samples_requested: Optional[bool] = Field(
        None, description="Whether the HCP requested product samples"
    )
    questions_raised: Optional[str] = Field(
        None, description="Any questions or concerns the HCP raised"
    )
    notes: Optional[str] = Field(None, description="Any additional free-form notes")
    discussion_summary: Optional[str] = Field(
        None, description="A concise 1-3 sentence summary of what was discussed"
    )
    follow_up_date: Optional[date] = Field(
        None, description="A follow-up date if one was mentioned"
    )


def make_log_interaction_tool(db: Session, session_id: str) -> StructuredTool:
    service = InteractionService(db)

    def _run(**kwargs) -> dict:
        interaction = service.create_interaction(session_id=session_id, **kwargs)
        payload = serialize_interaction(interaction)
        return {
            "status": "success",
            "message": f"Logged a new interaction with {payload.get('hcp_name') or 'the HCP'}.",
            "interaction": payload,
        }

    return StructuredTool.from_function(
        func=_run,
        name="log_interaction",
        description=(
            "Create a brand-new HCP interaction record from the representative's natural-language "
            "description of a visit, call, or meeting. Extract every field you can identify."
        ),
        args_schema=LogInteractionArgs,
    )
