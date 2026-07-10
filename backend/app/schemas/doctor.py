"""Pydantic schemas for the Doctor (HCP) resource."""
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DoctorBase(BaseModel):
    name: str
    hospital: Optional[str] = None
    specialty: Optional[str] = None


class DoctorRead(DoctorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
