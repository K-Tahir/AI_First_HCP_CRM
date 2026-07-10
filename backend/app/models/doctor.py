"""Doctor (Healthcare Professional / HCP) ORM model."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Doctor(Base):
    """Represents a Healthcare Professional (HCP) that a rep engages with."""

    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hospital: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specialty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    interactions: Mapped[list["Interaction"]] = relationship(
        "Interaction", back_populates="doctor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} name={self.name!r} hospital={self.hospital!r}>"
