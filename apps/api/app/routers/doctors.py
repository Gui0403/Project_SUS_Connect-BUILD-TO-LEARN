import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import Doctor, Role, User
from app.pagination import Page, PageParams
from app.schemas import DoctorIn, DoctorOut

router = APIRouter(prefix="/doctors", tags=["doctors"])

any_staff = require_roles(Role.ADMIN, Role.DOCTOR, Role.RECEPTIONIST)
admin_only = require_roles(Role.ADMIN)


def _get_or_404(db: Session, doctor_id: uuid.UUID) -> Doctor:
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.post("", response_model=DoctorOut, status_code=201)
def register_doctor(
    body: DoctorIn, _user: User = Depends(admin_only), db: Session = Depends(get_db)
):
    duplicated = db.scalar(
        select(Doctor.id).where(
            Doctor.license_number == body.license_number,
            Doctor.license_state == body.license_state,
        )
    )
    if duplicated is not None:
        raise HTTPException(status_code=409, detail="License already registered")

    doctor = Doctor(**body.model_dump())
    db.add(doctor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="License already registered")
    return doctor


@router.get("", response_model=Page[DoctorOut])
def list_doctors(
    page: PageParams = Depends(),
    _user: User = Depends(any_staff),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(Doctor))
    rows = db.scalars(
        select(Doctor)
        .order_by(Doctor.full_name, Doctor.id)
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    return Page[DoctorOut](
        items=[DoctorOut.model_validate(r) for r in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(
    doctor_id: uuid.UUID,
    _user: User = Depends(any_staff),
    db: Session = Depends(get_db),
):
    return _get_or_404(db, doctor_id)


@router.delete("/{doctor_id}", status_code=204, response_class=Response)
def deactivate_doctor(
    doctor_id: uuid.UUID,
    _user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    doctor = _get_or_404(db, doctor_id)
    doctor.active = False
    db.commit()
    return Response(status_code=204)
