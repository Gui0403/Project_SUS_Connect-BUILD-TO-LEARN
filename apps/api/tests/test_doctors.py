from uuid import uuid4

from tests.factories import doctor_payload

API = "/api/v1"
DOCTORS = f"{API}/doctors"


def test_admin_registers_doctor(client, admin):
    payload = doctor_payload()
    resp = client.post(DOCTORS, json=payload, headers=admin.headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["license_number"] == payload["license_number"]
    assert body["active"] is True


def test_register_doctor_with_duplicate_license_returns_409(client, admin):
    payload = doctor_payload()
    client.post(DOCTORS, json=payload, headers=admin.headers)
    resp = client.post(DOCTORS, json=doctor_payload(license_number=payload["license_number"]), headers=admin.headers)
    assert resp.status_code == 409


def test_same_license_number_in_another_state_is_allowed(client, admin):
    payload = doctor_payload(license_state="MS")
    client.post(DOCTORS, json=payload, headers=admin.headers)
    other_state = doctor_payload(license_number=payload["license_number"], license_state="SP")
    assert client.post(DOCTORS, json=other_state, headers=admin.headers).status_code == 201


def test_doctor_cannot_register_doctor(client, doctor):
    assert client.post(DOCTORS, json=doctor_payload(), headers=doctor.headers).status_code == 403


def test_receptionist_cannot_register_doctor(client, receptionist):
    assert client.post(DOCTORS, json=doctor_payload(), headers=receptionist.headers).status_code == 403


def test_receptionist_can_list_doctors_with_pagination(client, receptionist, doctor):
    resp = client.get(f"{DOCTORS}?limit=1", headers=receptionist.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) <= 1
    assert body["limit"] == 1
    assert body["total"] >= 1


def test_get_doctor_by_id(client, receptionist, doctor):
    resp = client.get(f"{DOCTORS}/{doctor.doctor_id}", headers=receptionist.headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == doctor.doctor_id


def test_get_unknown_doctor_returns_404(client, receptionist):
    assert client.get(f"{DOCTORS}/{uuid4()}", headers=receptionist.headers).status_code == 404


def test_admin_deactivates_doctor(client, admin, doctor):
    assert client.delete(f"{DOCTORS}/{doctor.doctor_id}", headers=admin.headers).status_code == 204
    resp = client.get(f"{DOCTORS}/{doctor.doctor_id}", headers=admin.headers)
    assert resp.json()["active"] is False
