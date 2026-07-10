"""HCP Interaction ORM model - the core record behind the Log Interaction screen."""
import enum
from datetime import date as date_, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InteractionType(str, enum.Enum):
    MEETING = "Meeting"
    CALL = "Call"
    EMAIL = "Email"
    CONFERENCE = "Conference"
    VIRTUAL = "Virtual"


class Sentiment(str, enum.Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"


class Interaction(Base):
    """A single logged interaction between a rep and an HCP.

    This is the record that backs the left-hand "Interaction Details" form.
    It is only ever created/updated through LangGraph tools, never directly
    from the frontend or the LLM.
    """

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), nullable=True)
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="interactions")

    hospital: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specialty: Mapped[str | None] = mapped_column(String(255), nullable=True)

    interaction_date: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    interaction_type: Mapped[str | None] = mapped_column(
        Enum(InteractionType, native_enum=False, length=32, validate_strings=True), nullable=True
    )

    products_discussed: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated
    sentiment: Mapped[str | None] = mapped_column(
        Enum(Sentiment, native_enum=False, length=16, validate_strings=True), nullable=True
    )

    brochures_shared: Mapped[bool] = mapped_column(default=False)
    samples_requested: Mapped[bool] = mapped_column(default=False)

    questions_raised: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    discussion_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    follow_up_date: Mapped[date_ | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    follow_ups: Mapped[list["FollowUp"]] = relationship(
        "FollowUp", back_populates="interaction", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Interaction id={self.id} doctor_id={self.doctor_id} sentiment={self.sentiment}>"
