import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import (
    Appointment,
    AppointmentStatus,
    MedicalRecord,
    MedicalRecordAddendum,
    Role,
    User,
)
from app.permissions import ensure_own_appointment
from app.schemas import AddendumIn, AddendumOut, MedicalRecordIn, MedicalRecordOut

router = APIRouter(tags=["medical-records"])

doctor_only = require_roles(Role.DOCTOR)


def _appointment_or_404(db: Session, appointment_id: uuid.UUID) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


def _record_out(db: Session, record: MedicalRecord) -> MedicalRecordOut:
    addenda = db.scalars(
        select(MedicalRecordAddendum)
        .where(MedicalRecordAddendum.medical_record_id == record.id)
        .order_by(MedicalRecordAddendum.created_at, MedicalRecordAddendum.id)
    ).all()
    return MedicalRecordOut(
        id=record.id,
        appointment_id=record.appointment_id,
        patient_id=record.patient_id,
        anamnesis=record.anamnesis,
        diagnosis=record.diagnosis,
        cid10_code=record.cid10_code,
        conduct=record.conduct,
        created_at=record.created_at,
        addenda=[AddendumOut.model_validate(a) for a in addenda],
    )


@router.post(
    "/appointments/{appointment_id}/medical-record",
    response_model=MedicalRecordOut,
    status_code=201,
)
def register_medical_record(
    appointment_id: uuid.UUID,
    body: MedicalRecordIn,
    user: User = Depends(doctor_only),
    db: Session = Depends(get_db),
):
    appointment = _appointment_or_404(db, appointment_id)
    ensure_own_appointment(user, appointment)
    if appointment.status != AppointmentStatus.SCHEDULED.value:
        raise HTTPException(
            status_code=409, detail="Medical record requires a scheduled appointment"
        )
    if (
        db.scalar(
            select(MedicalRecord.id).where(
                MedicalRecord.appointment_id == appointment.id
            )
        )
        is not None
    ):
        raise HTTPException(
            status_code=409,
            detail="Medical record already registered for this appointment",
        )

    record = MedicalRecord(
        appointment_id=appointment.id,
        patient_id=appointment.patient_id,
        **body.model_dump()
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Medical record already registered for this appointment",
        )
    db.refresh(record)
    return _record_out(db, record)


@router.get(
    "/appointments/{appointment_id}/medical-record", response_model=MedicalRecordOut
)
def get_medical_record(
    appointment_id: uuid.UUID,
    _user: User = Depends(doctor_only),
    db: Session = Depends(get_db),
):
    appointment = _appointment_or_404(db, appointment_id)
    record = db.scalar(
        select(MedicalRecord).where(MedicalRecord.appointment_id == appointment.id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Medical record not found")
    return _record_out(db, record)


@router.post(
    "/medical-records/{record_id}/addenda", response_model=AddendumOut, status_code=201
)
def add_addendum(
    record_id: uuid.UUID,
    body: AddendumIn,
    user: User = Depends(doctor_only),
    db: Session = Depends(get_db),
):
    record = db.get(MedicalRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Medical record not found")
    ensure_own_appointment(user, db.get(Appointment, record.appointment_id))

    addendum = MedicalRecordAddendum(
        medical_record_id=record.id, author_id=user.id, text=body.text
    )
    db.add(addendum)
    db.commit()
    db.refresh(addendum)
    return addendum
