import re
import uuid
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.models import Role

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValueError("invalid email")
    return value


# Não usamos EmailStr: o email-validator rejeita domínios como ".local" (usados em dev/testes).
Email = Annotated[str, AfterValidator(_normalize_email)]
Password = Annotated[str, Field(min_length=10, max_length=128)]


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
