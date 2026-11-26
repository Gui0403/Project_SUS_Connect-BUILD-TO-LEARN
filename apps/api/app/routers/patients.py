import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import Patient, Role, User
from app.pagination import Page, PageParams
from app.schemas import PatientIn, PatientOut
from app.validators import only_digits

router = APIRouter(prefix="/patients", tags=["patients"])

staff = require_roles(Role.DOCTOR, Role.RECEPTIONIST)
receptionist_only = require_roles(Role.RECEPTIONIST)


def _get_or_404(db: Session, patient_id: uuid.UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _fields(body: PatientIn) -> dict:
    return {
        "full_name": body.full_name,
        "cpf": body.cpf,
        "cns": body.cns,
        "birth_date": body.birth_date,
        "sex": body.sex.value,
        "phone": body.phone,
        "email": body.email,
        "address": body.address.model_dump() if body.address else None,
    }


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


@router.post("", response_model=PatientOut, status_code=201)
def register_patient(
    body: PatientIn, _user: User = Depends(staff), db: Session = Depends(get_db)
):
    # O CPF continua reservado mesmo se o paciente estiver desativado.
    if db.scalar(select(Patient.id).where(Patient.cpf == body.cpf)) is not None:
        raise HTTPException(status_code=409, detail="CPF already registered")

    patient = Patient(**_fields(body))
    db.add(patient)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="CPF already registered")
    return patient


@router.get("", response_model=Page[PatientOut])
def search_patients(
    q: str | None = None,
    page: PageParams = Depends(),
    _user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    stmt = select(Patient)
    if q and q.strip():
        term = q.strip()
        conditions = [Patient.full_name.ilike(_like(term), escape="\\")]
        digits = only_digits(term)
        if len(digits) == 11:
            conditions.append(Patient.cpf == digits)
        stmt = stmt.where(or_(*conditions))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(Patient.full_name, Patient.id)
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    return Page[PatientOut](
        items=[PatientOut.model_validate(r) for r in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: uuid.UUID, _user: User = Depends(staff), db: Session = Depends(get_db)
):
    return _get_or_404(db, patient_id)


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: uuid.UUID,
    body: PatientIn,
    _user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    patient = _get_or_404(db, patient_id)
    if not patient.active:
        raise HTTPException(status_code=409, detail="Patient is deactivated")
    if body.cpf != patient.cpf:
        raise HTTPException(status_code=422, detail="CPF cannot be changed")

    for field, value in _fields(body).items():
        setattr(patient, field, value)
    db.commit()
    return patient


@router.delete("/{patient_id}", status_code=204, response_class=Response)
def deactivate_patient(
    patient_id: uuid.UUID,
    _user: User = Depends(receptionist_only),
    db: Session = Depends(get_db),
):
    patient = _get_or_404(db, patient_id)
    patient.active = False
    db.commit()
    return Response(status_code=204)
