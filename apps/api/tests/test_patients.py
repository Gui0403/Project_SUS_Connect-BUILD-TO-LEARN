from uuid import uuid4

from tests.factories import INVALID_CPF, patient_payload, unique_name

API = "/api/v1"
PATIENTS = f"{API}/patients"


def test_register_patient_returns_201_and_active_patient(client, receptionist):
    payload = patient_payload()
    resp = client.post(PATIENTS, json=payload, headers=receptionist.headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["cpf"] == payload["cpf"]
    assert body["full_name"] == payload["full_name"]
    assert body["active"] is True


def test_doctor_can_register_patient(client, doctor):
    assert client.post(PATIENTS, json=patient_payload(), headers=doctor.headers).status_code == 201


def test_admin_cannot_register_patient(client, admin):
    assert client.post(PATIENTS, json=patient_payload(), headers=admin.headers).status_code == 403


def test_register_patient_without_token_returns_401(client):
    assert client.post(PATIENTS, json=patient_payload()).status_code == 401


def test_register_patient_with_invalid_cpf_returns_422(client, receptionist):
    resp = client.post(PATIENTS, json=patient_payload(cpf=INVALID_CPF), headers=receptionist.headers)
    assert resp.status_code == 422


def test_register_patient_with_future_birth_date_returns_422(client, receptionist):
    resp = client.post(PATIENTS, json=patient_payload(birth_date="2999-01-01"), headers=receptionist.headers)
    assert resp.status_code == 422


def test_register_patient_with_invalid_cns_returns_422(client, receptionist):
    resp = client.post(PATIENTS, json=patient_payload(cns="123"), headers=receptionist.headers)
    assert resp.status_code == 422


def test_register_patient_with_duplicate_cpf_returns_409(client, receptionist, patient):
    resp = client.post(PATIENTS, json=patient_payload(cpf=patient["cpf"]), headers=receptionist.headers)
    assert resp.status_code == 409


def test_get_patient_returns_the_patient(client, doctor, patient):
    resp = client.get(f"{PATIENTS}/{patient['id']}", headers=doctor.headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == patient["id"]


def test_get_unknown_patient_returns_404(client, doctor):
    assert client.get(f"{PATIENTS}/{uuid4()}", headers=doctor.headers).status_code == 404


def test_admin_cannot_view_patient(client, admin, patient):
    assert client.get(f"{PATIENTS}/{patient['id']}", headers=admin.headers).status_code == 403


def test_update_patient_changes_the_fields(client, receptionist, patient):
    payload = patient_payload(cpf=patient["cpf"], full_name=patient["full_name"], phone="67988887777")
    resp = client.put(f"{PATIENTS}/{patient['id']}", json=payload, headers=receptionist.headers)
    assert resp.status_code == 200
    assert resp.json()["phone"] == "67988887777"


def test_update_patient_cannot_change_cpf(client, receptionist, patient):
    resp = client.put(f"{PATIENTS}/{patient['id']}", json=patient_payload(), headers=receptionist.headers)
    assert resp.status_code == 422


def test_search_patients_by_name(client, receptionist):
    name = unique_name("Buscavel")
    client.post(PATIENTS, json=patient_payload(full_name=name), headers=receptionist.headers)
    resp = client.get(PATIENTS, params={"q": name}, headers=receptionist.headers)
    assert resp.status_code == 200
    assert [p["full_name"] for p in resp.json()["items"]] == [name]


def test_search_patients_by_cpf(client, receptionist, patient):
    resp = client.get(PATIENTS, params={"q": patient["cpf"]}, headers=receptionist.headers)
    assert resp.status_code == 200
    assert [p["id"] for p in resp.json()["items"]] == [patient["id"]]


def test_list_patients_is_paginated(client, receptionist):
    for _ in range(2):
        client.post(PATIENTS, json=patient_payload(), headers=receptionist.headers)
    resp = client.get(f"{PATIENTS}?limit=1&offset=0", headers=receptionist.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert body["total"] >= 2


def test_deactivate_patient_returns_204_and_keeps_the_record(client, receptionist, patient):
    assert client.delete(f"{PATIENTS}/{patient['id']}", headers=receptionist.headers).status_code == 204
    resp = client.get(f"{PATIENTS}/{patient['id']}", headers=receptionist.headers)
    assert resp.status_code == 200
    assert resp.json()["active"] is False


def test_doctor_cannot_deactivate_patient(client, doctor, patient):
    assert client.delete(f"{PATIENTS}/{patient['id']}", headers=doctor.headers).status_code == 403


def test_deactivated_patient_cannot_be_updated(client, receptionist, patient):
    client.delete(f"{PATIENTS}/{patient['id']}", headers=receptionist.headers)
    payload = patient_payload(cpf=patient["cpf"], full_name=patient["full_name"])
    resp = client.put(f"{PATIENTS}/{patient['id']}", json=payload, headers=receptionist.headers)
    assert resp.status_code == 409


def test_cpf_stays_reserved_after_deactivation(client, receptionist, patient):
    client.delete(f"{PATIENTS}/{patient['id']}", headers=receptionist.headers)
    resp = client.post(PATIENTS, json=patient_payload(cpf=patient["cpf"]), headers=receptionist.headers)
    assert resp.status_code == 409
