import enum
import re
import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Optional

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models import AppointmentStatus, Role
from app.validators import is_valid_cpf, only_digits

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValueError("invalid email")
    return value


# Não usamos EmailStr: o email-validator rejeita domínios como ".local" (usados em dev/testes).
Email = Annotated[str, AfterValidator(_normalize_email)]
Password = Annotated[str, Field(min_length=10, max_length=128)]
UF = Annotated[str, Field(min_length=2, max_length=2), AfterValidator(str.upper)]


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


# Datetime com fuso obrigatório (sem fuso → 422), normalizado para UTC.
UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]


# ---------------------------------------------------------------- auth / users
class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: Password


class UserCreate(BaseModel):
    email: Email
    password: Password
    full_name: Annotated[str, Field(min_length=1, max_length=200)]
    role: Role
    doctor_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def _check_rules(self):
        if self.role == Role.DOCTOR and self.doctor_id is None:
            raise ValueError("doctor_id is required for DOCTOR users")
        if self.role != Role.DOCTOR and self.doctor_id is not None:
            raise ValueError("doctor_id is only allowed for DOCTOR users")
        if self.password.lower() == self.email:
            raise ValueError("password must differ from email")
        return self


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    doctor_id: Optional[uuid.UUID]
    active: bool
    must_change_password: bool


# ---------------------------------------------------------------- doctors
class DoctorIn(BaseModel):
    full_name: Annotated[str, Field(min_length=1, max_length=200)]
    license_number: Annotated[str, Field(min_length=1, max_length=20)]
    license_state: UF
    specialty: Annotated[str, Field(min_length=1, max_length=100)]


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    license_number: str
    license_state: str
    specialty: str
    active: bool


# ---------------------------------------------------------------- patients
class Sex(str, enum.Enum):
    F = "F"
    M = "M"
    OTHER = "OTHER"


class Address(BaseModel):
    street: str
    number: str
    district: str
    city: str
    state: UF
    zip_code: str


class PatientIn(BaseModel):
    full_name: Annotated[str, Field(min_length=1, max_length=200)]
    cpf: str
    cns: Optional[str] = None
    birth_date: date
    sex: Sex
    phone: Optional[Annotated[str, Field(max_length=20)]] = None
    email: Optional[Email] = None
    address: Optional[Address] = None

    @field_validator("cpf")
    @classmethod
    def _validate_cpf(cls, value: str) -> str:
        digits = only_digits(value)
        if not is_valid_cpf(digits):
            raise ValueError("invalid cpf")
        return digits

    @field_validator("cns")
    @classmethod
    def _validate_cns(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        digits = only_digits(value)
        if len(digits) != 15:
            raise ValueError("cns must have 15 digits")
        return digits

    @field_validator("birth_date")
    @classmethod
    def _validate_birth_date(cls, value: date) -> date:
        if value > datetime.now(timezone.utc).date():
            raise ValueError("birth_date cannot be in the future")
        return value


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    cpf: str
    cns: Optional[str]
    birth_date: date
    sex: Sex
    phone: Optional[str]
    email: Optional[str]
    address: Optional[Address]
    active: bool


# ---------------------------------------------------------------- appointments
class AppointmentIn(BaseModel):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    scheduled_at: UtcDatetime
    reason: Annotated[str, Field(min_length=1, max_length=500)]


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    scheduled_at: datetime
    status: AppointmentStatus
    reason: str


# ---------------------------------------------------------------- medical records
class MedicalRecordIn(BaseModel):
    anamnesis: Annotated[str, Field(min_length=1)]
    diagnosis: Annotated[str, Field(min_length=1)]
    cid10_code: Optional[Annotated[str, Field(max_length=10)]] = None
    conduct: Annotated[str, Field(min_length=1)]


class AddendumIn(BaseModel):
    text: Annotated[str, Field(min_length=1)]


class AddendumOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID
    text: str
    created_at: datetime


class MedicalRecordOut(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    anamnesis: str
    diagnosis: str
    cid10_code: Optional[str]
    conduct: str
    created_at: datetime
    addenda: list[AddendumOut]


# ---------------------------------------------------------------- exams
class ExamOut(BaseModel):
    """Nunca expõe storage_key: o cliente não precisa saber onde o arquivo está."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    appointment_id: Optional[uuid.UUID]
    name: str
    performed_at: date
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
