from tests.factories import PASSWORD, user_payload

API = "/api/v1"
USERS = f"{API}/users"


def test_admin_creates_user_and_response_hides_secrets(client, admin):
    payload = user_payload("RECEPTIONIST")
    resp = client.post(USERS, json=payload, headers=admin.headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["email"] == payload["email"]
    assert body["role"] == "RECEPTIONIST"
    assert body["active"] is True
    assert "password" not in body
    assert "password_hash" not in body


def test_doctor_cannot_create_user(client, doctor):
    resp = client.post(USERS, json=user_payload(), headers=doctor.headers)
    assert resp.status_code == 403


def test_receptionist_cannot_create_user(client, receptionist):
    resp = client.post(USERS, json=user_payload(), headers=receptionist.headers)
    assert resp.status_code == 403


def test_create_user_without_token_returns_401(client):
    assert client.post(USERS, json=user_payload()).status_code == 401


def test_create_user_with_duplicate_email_returns_409(client, admin):
    payload = user_payload()
    client.post(USERS, json=payload, headers=admin.headers)
    resp = client.post(USERS, json=payload, headers=admin.headers)
    assert resp.status_code == 409


def test_create_user_with_weak_password_returns_422(client, admin):
    resp = client.post(USERS, json=user_payload(password="curta"), headers=admin.headers)
    assert resp.status_code == 422


def test_create_doctor_user_without_doctor_link_returns_422(client, admin):
    resp = client.post(USERS, json=user_payload("DOCTOR"), headers=admin.headers)
    assert resp.status_code == 422


def test_email_is_stored_in_lowercase(client, admin):
    payload = user_payload(email="MaiusculasNoEmail@Test.Local")
    assert client.post(USERS, json=payload, headers=admin.headers).status_code == 201
    login = client.post(f"{API}/auth/login", json={"email": "maiusculasnoemail@test.local", "password": PASSWORD})
    assert login.status_code == 200
