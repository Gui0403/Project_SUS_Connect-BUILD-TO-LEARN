"""Fixtures compartilhadas da suíte de testes da API.

Convenções (docs/architecture.md, seção 13):
- A API é testada como caixa-preta, via TestClient.
- Os testes usam um banco separado: <POSTGRES_DB>_test.
- Usuários de teste são criados por `app.cli.create_user`, implementado no Dia 4
  (a mesma função usada pelo comando de seed do primeiro ADMIN).
"""
import os
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

import pytest
from sqlalchemy.engine import make_url

# Precisa vir ANTES de importar a aplicação: aponta para o banco de testes.
_url = make_url(os.environ["DATABASE_URL"])
if not _url.database.endswith("_test"):
    _url = _url.set(database=f"{_url.database}_test")
os.environ["DATABASE_URL"] = _url.render_as_string(hide_password=False)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from tests import factories  # noqa: E402

API = "/api/v1"


@dataclass
class Account:
    email: str
    password: str
    role: str
    doctor_id: Optional[str] = None


@dataclass
class Actor(Account):
    """Conta já autenticada: traz os headers prontos para as requisições."""

    headers: dict = field(default_factory=dict)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def create_account() -> Callable[..., Account]:
    def _create(role="RECEPTIONIST", doctor_id=None, password=factories.PASSWORD, email=None) -> Account:
        from app.cli import create_user  # implementado no Dia 4

        email = email or f"{role.lower()}-{uuid.uuid4().hex[:8]}@test.local"
        create_user(email=email, password=password, role=role, doctor_id=doctor_id)
        return Account(email=email, password=password, role=role, doctor_id=doctor_id)

    return _create


@pytest.fixture
def make_actor(client, create_account) -> Callable[[str], Actor]:
    def _make(role: str) -> Actor:
        doctor_id = None
        if role == "DOCTOR":
            admin = _make("ADMIN")
            resp = client.post(f"{API}/doctors", json=factories.doctor_payload(), headers=admin.headers)
            assert resp.status_code == 201, resp.text
            doctor_id = resp.json()["id"]
        account = create_account(role=role, doctor_id=doctor_id)
        resp = client.post(f"{API}/auth/login", json={"email": account.email, "password": account.password})
        assert resp.status_code == 200, resp.text
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        return Actor(account.email, account.password, role, doctor_id, headers)

    return _make


@pytest.fixture
def admin(make_actor) -> Actor:
    return make_actor("ADMIN")


@pytest.fixture
def doctor(make_actor) -> Actor:
    return make_actor("DOCTOR")


@pytest.fixture
def other_doctor(make_actor) -> Actor:
    return make_actor("DOCTOR")


@pytest.fixture
def receptionist(make_actor) -> Actor:
    return make_actor("RECEPTIONIST")


@pytest.fixture
def patient(client, receptionist) -> dict:
    resp = client.post(f"{API}/patients", json=factories.patient_payload(), headers=receptionist.headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def scheduled_appointment(client, receptionist, doctor, patient) -> dict:
    payload = factories.appointment_payload(patient["id"], doctor.doctor_id)
    resp = client.post(f"{API}/appointments", json=payload, headers=receptionist.headers)
    assert resp.status_code == 201, resp.text
    return resp.json()
