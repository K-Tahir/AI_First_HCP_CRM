"""Data access layer for the Doctor (HCP) entity."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.doctor import Doctor


class DoctorRepository:
    """Encapsulates all SQL access for Doctor records."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_name(self, name: str) -> Doctor | None:
        stmt = select(Doctor).where(func.lower(Doctor.name) == name.strip().lower())
        return self._db.execute(stmt).scalar_one_or_none()

    def get_or_create(
        self, name: str, hospital: str | None = None, specialty: str | None = None
    ) -> Doctor:
        doctor = self.find_by_name(name)
        if doctor:
            # Backfill missing metadata without overwriting known data.
            if hospital and not doctor.hospital:
                doctor.hospital = hospital
            if specialty and not doctor.specialty:
                doctor.specialty = specialty
            self._db.flush()
            return doctor

        doctor = Doctor(name=name.strip(), hospital=hospital, specialty=specialty)
        self._db.add(doctor)
        self._db.flush()
        return doctor

    def get_by_id(self, doctor_id: int) -> Doctor | None:
        return self._db.get(Doctor, doctor_id)
