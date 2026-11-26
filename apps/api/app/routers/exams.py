import hashlib
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import Appointment, Exam, Patient, Role, User
from app.pagination import Page, PageParams
from app.schemas import ExamOut
from app.storage import FileStorage, get_storage
from app.validators import safe_filename

router = APIRouter(tags=["exams"])

attach_roles = require_roles(Role.DOCTOR, Role.RECEPTIONIST)
view_roles = require_roles(Role.DOCTOR)

MAX_BYTES = 10 * 1024 * 1024  # 10 MB

# tipo declarado -> assinatura (primeiros bytes) que o arquivo de verdade precisa ter
ALLOWED_TYPES = {
    "application/pdf": b"%PDF-",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}


def _exam_or_404(db: Session, exam_id: uuid.UUID) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@router.post("/exams", response_model=ExamOut, status_code=201)
def attach_exam(
    patient_id: uuid.UUID = Form(...),
    name: str = Form(..., min_length=1, max_length=200),
    performed_at: date = Form(...),
    appointment_id: uuid.UUID | None = Form(None),
    file: UploadFile = File(...),
    user: User = Depends(attach_roles),
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
):
    if db.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    if appointment_id is not None:
        appointment = db.get(Appointment, appointment_id)
        if appointment is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if appointment.patient_id != patient_id:
            raise HTTPException(
                status_code=422, detail="Appointment belongs to another patient"
            )

    declared_type = (file.content_type or "").lower()
    if declared_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415, detail="Unsupported file type (allowed: PDF, PNG, JPEG)"
        )

    data = file.file.read(MAX_BYTES + 1)  # lê 1 byte a mais só para detectar o excesso
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    if not data.startswith(ALLOWED_TYPES[declared_type]):
        raise HTTPException(
            status_code=415, detail="File content does not match the declared type"
        )

    exam_id = uuid.uuid4()
    storage_key = exam_id.hex
    storage.save(storage_key, data)

    exam = Exam(
        id=exam_id,
        patient_id=patient_id,
        appointment_id=appointment_id,
        name=name,
        performed_at=performed_at,
        file_name=safe_filename(file.filename),
        content_type=declared_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        storage_key=storage_key,
        uploaded_by=user.id,
    )
    db.add(exam)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(storage_key)  # não deixa arquivo órfão se o banco falhar
        raise
    db.refresh(exam)
    return exam


@router.get("/exams/{exam_id}", response_model=ExamOut)
def get_exam(
    exam_id: uuid.UUID, _user: User = Depends(view_roles), db: Session = Depends(get_db)
):
    return _exam_or_404(db, exam_id)


@router.get("/exams/{exam_id}/file")
def download_exam_file(
    exam_id: uuid.UUID,
    _user: User = Depends(view_roles),
    db: Session = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
):
    exam = _exam_or_404(db, exam_id)
    try:
        content = storage.read(exam.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Exam file not found")
    return Response(
        content=content,
        media_type=exam.content_type,
        headers={"Content-Disposition": f'attachment; filename="{exam.file_name}"'},
    )


@router.get("/patients/{patient_id}/exams", response_model=Page[ExamOut])
def list_patient_exams(
    patient_id: uuid.UUID,
    page: PageParams = Depends(),
    _user: User = Depends(view_roles),
    db: Session = Depends(get_db),
):
    if db.get(Patient, patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    stmt = select(Exam).where(Exam.patient_id == patient_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(Exam.performed_at.desc(), Exam.created_at.desc(), Exam.id)
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    return Page[ExamOut](
        items=[ExamOut.model_validate(r) for r in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
