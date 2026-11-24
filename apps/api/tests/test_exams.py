import hashlib
from uuid import uuid4

from tests.factories import exam_upload

API = "/api/v1"
EXAMS = f"{API}/exams"
CONTENT = b"%PDF-1.4 conteudo ficticio de exame"


def _attach(client, patient, headers, **kwargs):
    return client.post(EXAMS, headers=headers, **exam_upload(patient["id"], **kwargs))


def test_doctor_attaches_exam_and_gets_its_metadata(client, doctor, patient):
    resp = _attach(client, patient, doctor.headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["patient_id"] == patient["id"]
    assert body["name"] == "Hemograma completo"
    assert body["file_name"] == "hemograma.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(CONTENT)
    assert body["sha256"] == hashlib.sha256(CONTENT).hexdigest()
    assert "storage_key" not in body


def test_receptionist_can_attach_exam(client, receptionist, patient):
    assert _attach(client, patient, receptionist.headers).status_code == 201


def test_admin_cannot_attach_exam(client, admin, patient):
    assert _attach(client, patient, admin.headers).status_code == 403


def test_attach_exam_without_token_returns_401(client, patient):
    assert client.post(EXAMS, **exam_upload(patient["id"])).status_code == 401


def test_attach_exam_with_unsupported_file_type_returns_415(client, doctor, patient):
    resp = _attach(
        client, patient, doctor.headers, content=b"MZ...", filename="virus.exe", content_type="application/x-msdownload"
    )
    assert resp.status_code == 415


def test_attach_exam_larger_than_10mb_returns_413(client, doctor, patient):
    resp = _attach(client, patient, doctor.headers, content=b"0" * (10 * 1024 * 1024 + 1))
    assert resp.status_code == 413


def test_attach_exam_to_unknown_patient_returns_404(client, doctor):
    resp = client.post(EXAMS, headers=doctor.headers, **exam_upload(str(uuid4())))
    assert resp.status_code == 404


def test_doctor_gets_exam_by_id(client, doctor, patient):
    exam = _attach(client, patient, doctor.headers).json()
    resp = client.get(f"{EXAMS}/{exam['id']}", headers=doctor.headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == exam["id"]


def test_receptionist_cannot_view_exam(client, receptionist, doctor, patient):
    exam = _attach(client, patient, doctor.headers).json()
    assert client.get(f"{EXAMS}/{exam['id']}", headers=receptionist.headers).status_code == 403


def test_get_unknown_exam_returns_404(client, doctor):
    assert client.get(f"{EXAMS}/{uuid4()}", headers=doctor.headers).status_code == 404


def test_doctor_downloads_the_original_file(client, doctor, patient):
    exam = _attach(client, patient, doctor.headers).json()
    resp = client.get(f"{EXAMS}/{exam['id']}/file", headers=doctor.headers)
    assert resp.status_code == 200
    assert resp.content == CONTENT


def test_list_exams_of_a_patient(client, doctor, patient):
    exam = _attach(client, patient, doctor.headers).json()
    resp = client.get(f"{API}/patients/{patient['id']}/exams", headers=doctor.headers)
    assert resp.status_code == 200
    assert [e["id"] for e in resp.json()["items"]] == [exam["id"]]
