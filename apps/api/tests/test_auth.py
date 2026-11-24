from tests.factories import PASSWORD

API = "/api/v1"
LOGIN = f"{API}/auth/login"
REFRESH = f"{API}/auth/refresh"
LOGOUT = f"{API}/auth/logout"
ME = f"{API}/auth/me"
CHANGE_PASSWORD = f"{API}/auth/change-password"


def _login(client, account):
    return client.post(LOGIN, json={"email": account.email, "password": account.password})


def test_login_with_valid_credentials_returns_tokens(client, create_account):
    account = create_account()
    resp = _login(client, account)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_with_wrong_password_returns_generic_401(client, create_account):
    account = create_account()
    resp = client.post(LOGIN, json={"email": account.email, "password": "senha-errada-123"})
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Invalid credentials"}


def test_login_with_unknown_email_returns_same_error_as_wrong_password(client, create_account):
    account = create_account()
    wrong_password = client.post(LOGIN, json={"email": account.email, "password": "senha-errada-123"})
    unknown_email = client.post(LOGIN, json={"email": "ninguem@test.local", "password": "senha-errada-123"})
    assert unknown_email.status_code == wrong_password.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_account_is_locked_after_five_failed_attempts(client, create_account):
    account = create_account()
    for _ in range(5):
        client.post(LOGIN, json={"email": account.email, "password": "senha-errada-123"})
    resp = _login(client, account)  # senha correta, mas a conta está bloqueada
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Invalid credentials"}


def test_me_returns_the_authenticated_user_without_secrets(client, receptionist):
    resp = client.get(ME, headers=receptionist.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == receptionist.email
    assert body["role"] == "RECEPTIONIST"
    assert "password_hash" not in body
    assert "password" not in body


def test_protected_route_without_token_returns_401(client):
    assert client.get(f"{API}/patients").status_code == 401


def test_protected_route_with_invalid_token_returns_401(client):
    resp = client.get(f"{API}/patients", headers={"Authorization": "Bearer token.invalido.aqui"})
    assert resp.status_code == 401


def test_refresh_returns_a_new_token_pair(client, create_account):
    tokens = _login(client, create_account()).json()
    resp = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json()["refresh_token"] != tokens["refresh_token"]


def test_used_refresh_token_cannot_be_used_again(client, create_account):
    tokens = _login(client, create_account()).json()
    client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    resp = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401


def test_reusing_a_refresh_token_revokes_the_whole_family(client, create_account):
    tokens = _login(client, create_account()).json()
    rotated = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]}).json()
    client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})  # reuso suspeito
    resp = client.post(REFRESH, json={"refresh_token": rotated["refresh_token"]})
    assert resp.status_code == 401


def test_logout_revokes_the_refresh_token(client, create_account):
    tokens = _login(client, create_account()).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    resp = client.post(LOGOUT, json={"refresh_token": tokens["refresh_token"]}, headers=headers)
    assert resp.status_code == 204
    resp = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401


def test_change_password_with_wrong_current_password_returns_400(client, receptionist):
    body = {"current_password": "nao-e-a-senha-atual", "new_password": "Nova-Senha-Forte-123"}
    resp = client.post(CHANGE_PASSWORD, json=body, headers=receptionist.headers)
    assert resp.status_code == 400


def test_change_password_with_weak_new_password_returns_422(client, receptionist):
    body = {"current_password": PASSWORD, "new_password": "curta"}
    resp = client.post(CHANGE_PASSWORD, json=body, headers=receptionist.headers)
    assert resp.status_code == 422


def test_change_password_allows_login_with_the_new_password_only(client, receptionist):
    new_password = "Nova-Senha-Forte-123"
    body = {"current_password": PASSWORD, "new_password": new_password}
    assert client.post(CHANGE_PASSWORD, json=body, headers=receptionist.headers).status_code == 204
    assert client.post(LOGIN, json={"email": receptionist.email, "password": new_password}).status_code == 200
    assert client.post(LOGIN, json={"email": receptionist.email, "password": PASSWORD}).status_code == 401
