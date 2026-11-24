from tests.factories import medical_record_payload

API = "/api/v1"
APPOINTMENTS = f"{API}/appointments"


def _url(appointment):
    return f"{APPOINTMENTS}/{appointment['id']}/medical-record"


def test_doctor_registers_medical_record_on_own_appointment(client, doctor, scheduled_appointment):
    payload = medical_record_payload()
    resp = client.post(_url(scheduled_appointment), json=payload, headers=doctor.headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["appointment_id"] == scheduled_appointment["id"]
    assert body["patient_id"] == scheduled_appointment["patient_id"]
    assert body["diagnosis"] == payload["diagnosis"]


def test_second_medical_record_for_same_appointment_returns_409(client, doctor, scheduled_appointment):
    client.post(_url(scheduled_appointment), json=medical_record_payload(), headers=doctor.headers)
    resp = client.post(_url(scheduled_appointment), json=medical_record_payload(), headers=doctor.headers)
    assert resp.status_code == 409


def test_other_doctor_cannot_register_medical_record(client, other_doctor, scheduled_appointment):
    resp = client.post(_url(scheduled_appointment), json=medical_record_payload(), headers=other_doctor.headers)
    assert resp.status_code == 403


def test_receptionist_cannot_register_medical_record(client, receptionist, scheduled_appointment):
    resp = client.post(_url(scheduled_appointment), json=medical_record_payload(), headers=receptionist.headers)
    assert resp.status_code == 403


def test_cannot_register_medical_record_on_cancelled_appointment(
    client, receptionist, doctor, scheduled_appointment
):
    client.post(f"{APPOINTMENTS}/{scheduled_appointment['id']}/cancel", headers=receptionist.headers)
    resp = client.post(_url(scheduled_appointment), json=medical_record_payload(), headers=doctor.headers)
    assert resp.status_code == 409


def test_doctor_reads_medical_record(client, doctor, scheduled_appointment):
    client.post(_url(scheduled_appointment), json=medical_record_payload(), headers=doctor.headers)
    resp = client.get(_url(scheduled_appointment), headers=doctor.headers)
    assert resp.status_code == 200
    assert resp.json()["appointment_id"] == scheduled_appointment["id"]


def test_receptionist_cannot_read_medical_record(client, receptionist, doctor, scheduled_appointment):
    client.post(_url(scheduled_appointment), json=medical_record_payload(), headers=doctor.headers)
    assert client.get(_url(scheduled_appointment), headers=receptionist.headers).status_code == 403


def test_medical_record_cannot_be_overwritten(client, doctor, scheduled_appointment):
    client.post(_url(scheduled_appointment), json=medical_record_payload(), headers=doctor.headers)
    resp = client.put(_url(scheduled_appointment), json=medical_record_payload(), headers=doctor.headers)
    assert resp.status_code == 405


def test_correction_is_added_as_an_addendum(client, doctor, scheduled_appointment):
    record = client.post(_url(scheduled_appointment), json=medical_record_payload(), headers=doctor.headers).json()
    resp = client.post(
        f"{API}/medical-records/{record['id']}/addenda",
        json={"text": "Correção: dor iniciou há quatro dias."},
        headers=doctor.headers,
    )
    assert resp.status_code == 201
    reread = client.get(_url(scheduled_appointment), headers=doctor.headers).json()
    assert len(reread["addenda"]) == 1
