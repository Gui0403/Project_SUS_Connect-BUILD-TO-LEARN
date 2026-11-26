"""Regras de autorização que dependem do recurso (além do papel)."""
from fastapi import HTTPException

from app.models import Appointment, User

def ensure_own_appointment(user: User, appointment: Appointment) -> None:
    """Prontuário, adendo e conclusão só valem para o médico do próprio atendimento."""
    if user.doctor_id is None or user.doctor_id != appointment.doctor_id:
        raise HTTPException(status_code=403, detail="Not your appointment")