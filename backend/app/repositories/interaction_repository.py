"""Data access layer for the Interaction entity."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.interaction import Interaction


class InteractionRepository:
    """Encapsulates all SQL access for Interaction records."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, **fields) -> Interaction:
        interaction = Interaction(**fields)
        self._db.add(interaction)
        self._db.flush()
        return interaction

    def get_by_id(self, interaction_id: int) -> Interaction | None:
        return self._db.get(Interaction, interaction_id)

    def get_latest_for_session(self, session_id: str) -> Interaction | None:
        stmt = (
            select(Interaction)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.id.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def update_fields(self, interaction: Interaction, updates: dict) -> Interaction:
        """Apply a partial update, touching only the keys present in `updates`."""
        for key, value in updates.items():
            if hasattr(interaction, key):
                setattr(interaction, key, value)
        self._db.flush()
        return interaction

    def list_history(
        self,
        doctor_name: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
    ) -> list[Interaction]:
        stmt = select(Interaction).order_by(Interaction.interaction_date.desc().nullslast())

        if doctor_name:
            from app.models.doctor import Doctor

            stmt = stmt.join(Doctor, Interaction.doctor_id == Doctor.id).where(
                Doctor.name.ilike(f"%{doctor_name.strip()}%")
            )
        if date_from:
            stmt = stmt.where(Interaction.interaction_date >= date_from)
        if date_to:
            stmt = stmt.where(Interaction.interaction_date <= date_to)

        stmt = stmt.limit(limit)
        return list(self._db.execute(stmt).scalars().all())

    def list_all(self, limit: int = 100) -> list[Interaction]:
        stmt = select(Interaction).order_by(Interaction.id.desc()).limit(limit)
        return list(self._db.execute(stmt).scalars().all())
