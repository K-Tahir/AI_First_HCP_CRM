"""Pydantic schemas for the Interaction resource (the left-panel CRM form)."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class InteractionBase(BaseModel):
    hcp_name: Optional[str] = Field(None, description="Name of the Healthcare Professional")
    hospital: Optional[str] = None
    specialty: Optional[str] = None
    interaction_date: Optional[date] = None
    interaction_type: Optional[str] = None
    products_discussed: Optional[list[str]] = None
    sentiment: Optional[str] = None
    brochures_shared: Optional[bool] = None
    samples_requested: Optional[bool] = None
    questions_raised: Optional[str] = None
    notes: Optional[str] = None
    discussion_summary: Optional[str] = None
    follow_up_date: Optional[date] = None


class InteractionCreate(InteractionBase):
    session_id: str


class InteractionUpdate(InteractionBase):
    """All fields optional; only provided fields are updated (partial update)."""
    pass


class InteractionRead(InteractionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    doctor_id: Optional[int] = None


class InteractionListResponse(BaseModel):
    total: int
    items: list[InteractionRead]
