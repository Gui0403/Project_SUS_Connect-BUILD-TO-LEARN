from uuid import uuid4

from tests.factories import appointment_payload, medical_record_payload

API = "/api/v1"
APPOINTMENTS = f"{API}/appointments"


def _record(client, appointment_id, headers):
    resp = client.post(
        f"{APPOINTMENTS}/{appointment_id}/medical-record", json=medical_record_payload(), headers=headers
    )
    assert resp.status_code == 201, resp.text


def test_receptionist_schedules_appointment(client, receptionist, doctor, patient):
    payload = appointment_payload(patient["id"], doctor.doctor_id)
    resp = client.post(APPOINTMENTS, json=payload, headers=receptionist.headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "SCHEDULED"
    assert body["patient_id"] == patient["id"]
    assert body["doctor_id"] == doctor.doctor_id


def test_admin_cannot_schedule_appointment(client, admin, doctor, patient):
    payload = appointment_payload(patient["id"], doctor.doctor_id)
    assert client.post(APPOINTMENTS, json=payload, headers=admin.headers).status_code == 403


def test_schedule_appointment_without_token_returns_401(client, doctor, patient):
    payload = appointment_payload(patient["id"], doctor.doctor_id)
    assert client.post(APPOINTMENTS, json=payload).status_code == 401


def test_schedule_for_deactivated_patient_returns_409(client, receptionist, doctor, patient):
    client.delete(f"{API}/patients/{patient['id']}", headers=receptionist.headers)
    payload = appointment_payload(patient["id"], doctor.doctor_id)
    assert client.post(APPOINTMENTS, json=payload, headers=receptionist.headers).status_code == 409


def test_schedule_with_deactivated_doctor_returns_409(client, admin, receptionist, doctor, patient):
    client.delete(f"{API}/doctors/{doctor.doctor_id}", headers=admin.headers)
    payload = appointment_payload(patient["id"], doctor.doctor_id)
    assert client.post(APPOINTMENTS, json=payload, headers=receptionist.headers).status_code == 409


def test_schedule_for_unknown_patient_returns_404(client, receptionist, doctor):
    payload = appointment_payload(str(uuid4()), doctor.doctor_id)
    assert client.post(APPOINTMENTS, json=payload, headers=receptionist.headers).status_code == 404


def test_schedule_with_datetime_without_timezone_returns_422(client, receptionist, doctor, patient):
    payload = appointment_payload(patient["id"], doctor.doctor_id, scheduled_at="2030-01-15T10:00:00")
    assert client.post(APPOINTMENTS, json=payload, headers=receptionist.headers).status_code == 422


def test_get_appointment_returns_the_appointment(client, receptionist, scheduled_appointment):
    resp = client.get(f"{APPOINTMENTS}/{scheduled_appointment['id']}", headers=receptionist.headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == scheduled_appointment["id"]


def test_list_appointments_is_paginated(client, receptionist, scheduled_appointment):
    resp = client.get(f"{APPOINTMENTS}?limit=5", headers=receptionist.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"items", "total", "limit", "offset"}
    assert body["total"] >= 1


def test_update_scheduled_appointment_changes_the_reason(client, receptionist, scheduled_appointment):
    payload = appointment_payload(
        scheduled_appointment["patient_id"], scheduled_appointment["doctor_id"], reason="Retorno de consulta"
    )
    resp = client.put(f"{APPOINTMENTS}/{scheduled_appointment['id']}", json=payload, headers=receptionist.headers)
    assert resp.status_code == 200
    assert resp.json()["reason"] == "Retorno de consulta"


def test_cancel_scheduled_appointment(client, receptionist, scheduled_appointment):
    resp = client.post(f"{APPOINTMENTS}/{scheduled_appointment['id']}/cancel", headers=receptionist.headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_complete_appointment_without_medical_record_returns_409(client, doctor, scheduled_appointment):
    resp = client.post(f"{APPOINTMENTS}/{scheduled_appointment['id']}/complete", headers=doctor.headers)
    assert resp.status_code == 409


def test_doctor_completes_appointment_after_medical_record(client, doctor, scheduled_appointment):
    _record(client, scheduled_appointment["id"], doctor.headers)
    resp = client.post(f"{APPOINTMENTS}/{scheduled_appointment['id']}/complete", headers=doctor.headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"


def test_receptionist_cannot_complete_appointment(client, receptionist, scheduled_appointment):
    resp = client.post(f"{APPOINTMENTS}/{scheduled_appointment['id']}/complete", headers=receptionist.headers)
    assert resp.status_code == 403


def test_completed_appointment_cannot_be_updated(client, receptionist, doctor, scheduled_appointment):
    _record(client, scheduled_appointment["id"], doctor.headers)
    client.post(f"{APPOINTMENTS}/{scheduled_appointment['id']}/complete", headers=doctor.headers)
    payload = appointment_payload(scheduled_appointment["patient_id"], scheduled_appointment["doctor_id"])
    resp = client.put(f"{APPOINTMENTS}/{scheduled_appointment['id']}", json=payload, headers=receptionist.headers)
    assert resp.status_code == 409


def test_completed_appointment_cannot_be_cancelled(client, receptionist, doctor, scheduled_appointment):
    _record(client, scheduled_appointment["id"], doctor.headers)
    client.post(f"{APPOINTMENTS}/{scheduled_appointment['id']}/complete", headers=doctor.headers)
    resp = client.post(f"{APPOINTMENTS}/{scheduled_appointment['id']}/cancel", headers=receptionist.headers)
    assert resp.status_code == 409
