"""Payloads válidos e geradores de dados FICTÍCIOS para os testes."""
import uuid
from datetime import datetime, timedelta, timezone

PASSWORD = "Str0ng-Test-Pass!"
INVALID_CPF = "12345678900"  # dígitos verificadores errados


def _check_digit(digits: list[int]) -> int:
    weight = len(digits) + 1
    total = sum(d * (weight - i) for i, d in enumerate(digits))
    rest = (total * 10) % 11
    return 0 if rest == 10 else rest


def valid_cpf() -> str:
    """Gera um CPF com dígitos verificadores válidos (dados fictícios)."""
    while True:
        base = [int(c) for c in f"{uuid.uuid4().int % 10**9:09d}"]
        if len(set(base)) > 1:
            break
    base.append(_check_digit(base))
    base.append(_check_digit(base))
    return "".join(str(d) for d in base)


def unique_name(prefix: str = "Paciente") -> str:
    return f"{prefix} {uuid.uuid4().hex[:8]}"


def patient_payload(**overrides) -> dict:
    payload = {
        "full_name": unique_name("Maria Teste"),
        "cpf": valid_cpf(),
        "birth_date": "1985-04-12",
        "sex": "F",
        "phone": "67999990000",
        "email": "maria.teste@example.com",
        "address": {
            "street": "Rua das Flores",
            "number": "100",
            "district": "Centro",
            "city": "Campo Grande",
            "state": "MS",
            "zip_code": "79002-000",
        },
    }
    payload.update(overrides)
    return payload


def doctor_payload(**overrides) -> dict:
    payload = {
        "full_name": unique_name("Dr. Teste"),
        "license_number": str(uuid.uuid4().int % 10**6).zfill(6),
        "license_state": "MS",
        "specialty": "Clínica Geral",
    }
    payload.update(overrides)
    return payload


def user_payload(role: str = "RECEPTIONIST", **overrides) -> dict:
    payload = {
        "email": f"user-{uuid.uuid4().hex[:8]}@test.local",
        "password": PASSWORD,
        "full_name": unique_name("Usuário Teste"),
        "role": role,
    }
    payload.update(overrides)
    return payload


def future_datetime(days: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def appointment_payload(patient_id: str, doctor_id: str, **overrides) -> dict:
    payload = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "scheduled_at": future_datetime(),
        "reason": "Dor de cabeça recorrente",
    }
    payload.update(overrides)
    return payload


def medical_record_payload(**overrides) -> dict:
    payload = {
        "anamnesis": "Paciente relata cefaleia há três dias.",
        "diagnosis": "Cefaleia tensional",
        "cid10_code": "G44.2",
        "conduct": "Hidratação, repouso e retorno em 7 dias.",
    }
    payload.update(overrides)
    return payload


def exam_upload(
    patient_id: str,
    content: bytes = b"%PDF-1.4 conteudo ficticio de exame",
    filename: str = "hemograma.pdf",
    content_type: str = "application/pdf",
) -> dict:
    """Argumentos prontos para `client.post('/api/v1/exams', **exam_upload(...))`."""
    return {
        "files": {"file": (filename, content, content_type)},
        "data": {
            "patient_id": patient_id,
            "name": "Hemograma completo",
            "performed_at": "2026-11-01",
        },
    }
