import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    MedicalRecord,
    Patient,
    Role,
    User,
)
from app.pagination import Page, PageParams
from app.permissions import ensure_own_appointment
from app.schemas import AppointmentIn, AppointmentOut

router = APIRouter(prefix="/appointments", tags=["appointments"])

staff = require_roles(Role.DOCTOR, Role.RECEPTIONIST)
doctor_only = require_roles(Role.DOCTOR)

SCHEDULED = AppointmentStatus.SCHEDULED.value
COMPLETED = AppointmentStatus.COMPLETED.value
CANCELLED = AppointmentStatus.CANCELLED.value


def _get_or_404(db: Session, appointment_id: uuid.UUID) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


def _active_patient(db: Session, patient_id: uuid.UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not patient.active:
        raise HTTPException(status_code=409, detail="Patient is deactivated")
    return patient


def _active_doctor(db: Session, doctor_id: uuid.UUID) -> Doctor:
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if not doctor.active:
        raise HTTPException(status_code=409, detail="Doctor is deactivated")
    return doctor


@router.post("", response_model=AppointmentOut, status_code=201)
def schedule_appointment(
    body: AppointmentIn, _user: User = Depends(staff), db: Session = Depends(get_db)
):
    _active_patient(db, body.patient_id)
    _active_doctor(db, body.doctor_id)

    appointment = Appointment(
        patient_id=body.patient_id,
        doctor_id=body.doctor_id,
        scheduled_at=body.scheduled_at,
        reason=body.reason,
        status=SCHEDULED,
    )
    db.add(appointment)
    db.commit()
    return appointment


@router.get("", response_model=Page[AppointmentOut])
def list_appointments(
    patient_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
    status: AppointmentStatus | None = None,
    page: PageParams = Depends(),
    _user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    stmt = select(Appointment)
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if status is not None:
        stmt = stmt.where(Appointment.status == status.value)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(Appointment.scheduled_at, Appointment.id)
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    return Page[AppointmentOut](
        items=[AppointmentOut.model_validate(r) for r in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: uuid.UUID,
    _user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    return _get_or_404(db, appointment_id)


@router.put("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: uuid.UUID,
    body: AppointmentIn,
    _user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    appointment = _get_or_404(db, appointment_id)
    if appointment.status != SCHEDULED:
        raise HTTPException(
            status_code=409, detail="Only scheduled appointments can be updated"
        )
    if body.patient_id != appointment.patient_id:
        raise HTTPException(status_code=422, detail="Patient cannot be changed")
    if body.doctor_id != appointment.doctor_id:
        _active_doctor(db, body.doctor_id)
        appointment.doctor_id = body.doctor_id

    appointment.scheduled_at = body.scheduled_at
    appointment.reason = body.reason
    db.commit()
    return appointment


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(
    appointment_id: uuid.UUID,
    _user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    appointment = _get_or_404(db, appointment_id)
    if appointment.status != SCHEDULED:
        raise HTTPException(
            status_code=409, detail="Only scheduled appointments can be cancelled"
        )
    appointment.status = CANCELLED
    db.commit()
    return appointment


@router.post("/{appointment_id}/complete", response_model=AppointmentOut)
def complete_appointment(
    appointment_id: uuid.UUID,
    user: User = Depends(doctor_only),
    db: Session = Depends(get_db),
):
    appointment = _get_or_404(db, appointment_id)
    ensure_own_appointment(user, appointment)
    if appointment.status != SCHEDULED:
        raise HTTPException(
            status_code=409, detail="Only scheduled appointments can be completed"
        )

    has_record = db.scalar(
        select(MedicalRecord.id).where(MedicalRecord.appointment_id == appointment.id)
    )
    if has_record is None:
        raise HTTPException(
            status_code=409,
            detail="A medical record is required to complete the appointment",
        )

    appointment.status = COMPLETED
    db.commit()
    return appointment
