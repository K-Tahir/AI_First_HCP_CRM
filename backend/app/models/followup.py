"""Follow-up ORM model."""
from datetime import date as date_, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FollowUp(Base):
    """A scheduled follow-up action tied to a specific interaction."""

    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey("interactions.id"), nullable=False)
    interaction: Mapped["Interaction"] = relationship("Interaction", back_populates="follow_ups")

    follow_up_date: Mapped[date_] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="Pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<FollowUp id={self.id} interaction_id={self.interaction_id} date={self.follow_up_date}>"
