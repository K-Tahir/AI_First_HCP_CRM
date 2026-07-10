"""Data access layer for the FollowUp entity."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.followup import FollowUp


class FollowUpRepository:
    """Encapsulates all SQL access for FollowUp records."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, **fields) -> FollowUp:
        follow_up = FollowUp(**fields)
        self._db.add(follow_up)
        self._db.flush()
        return follow_up

    def list_for_interaction(self, interaction_id: int) -> list[FollowUp]:
        stmt = select(FollowUp).where(FollowUp.interaction_id == interaction_id)
        return list(self._db.execute(stmt).scalars().all())

    def get_by_id(self, follow_up_id: int) -> FollowUp | None:
        return self._db.get(FollowUp, follow_up_id)
