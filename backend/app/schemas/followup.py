"""Pydantic schemas for the FollowUp resource."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FollowUpBase(BaseModel):
    follow_up_date: date
    notes: Optional[str] = None
    status: Optional[str] = "Pending"


class FollowUpCreate(FollowUpBase):
    interaction_id: int


class FollowUpRead(FollowUpBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interaction_id: int
    created_at: datetime
