from datetime import datetime


def _signup_member(client, name, email_address, phone_number):
    response = client.post(
        "/auth/signup",
        json={
            "name": name,
            "email_address": email_address,
            "phone_number": phone_number,
            "password": "password123",
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    return data["member"]["id"], data["access_token"]


def test_contribution_crud_flow(client):
    import src.app as app_module
    from src.models.contribution import ContributionModel

    member_id, token = _signup_member(client, "ContributionUser", "contrib@example.com", 123456789)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/contributions",
        headers=headers,
        json={
            "amount": 250.00,
            "date": "2026-07-10T00:00:00",
            "contribution_type": "mpesa",
        },
    )
    assert create_response.status_code == 201
    created = create_response.get_json()
    assert created["amount"] == "250.00"
    assert created["contribution_type"] == "mpesa"
    assert created["member_id"] == member_id

    contribution_id = created["id"]

    get_response = client.get(f"/contributions/{contribution_id}", headers=headers)
    assert get_response.status_code == 200
    fetched = get_response.get_json()
    assert fetched["id"] == contribution_id
    assert fetched["amount"] == "250.00"

    update_response = client.put(
        f"/contributions/{contribution_id}",
        headers=headers,
        json={"amount": 300.00, "contribution_type": "cash"},
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["amount"] == "300.00"
    assert updated["contribution_type"] == "cash"

    delete_response = client.delete(f"/contributions/{contribution_id}", headers=headers)
    assert delete_response.status_code == 204

    with app_module.app.app_context():
        assert app_module.db.session.get(ContributionModel, contribution_id) is None


def test_contribution_crud_requires_authentication(client):
    assert client.post("/contributions", json={"amount": 1, "date": "2026-07-10T00:00:00", "contribution_type": "cash"}).status_code == 401
    assert client.get("/contributions/1").status_code == 401
    assert client.put("/contributions/1", json={"amount": 2}).status_code == 401
    assert client.delete("/contributions/1").status_code == 401


def test_member_cannot_manage_another_members_contribution(client):
    _, token_one = _signup_member(client, "MemberOne", "one@example.com", 111111111)
    _, token_two = _signup_member(client, "MemberTwo", "two@example.com", 222222222)
    headers_one = {"Authorization": f"Bearer {token_one}"}
    headers_two = {"Authorization": f"Bearer {token_two}"}

    create_response = client.post(
        "/contributions",
        headers=headers_one,
        json={"amount": 50.00, "date": "2026-07-10T00:00:00", "contribution_type": "cash"},
    )
    assert create_response.status_code == 201
    contribution_id = create_response.get_json()["id"]

    assert client.get(f"/contributions/{contribution_id}", headers=headers_two).status_code == 404
    assert client.put(f"/contributions/{contribution_id}", headers=headers_two, json={"amount": 55.00}).status_code == 404
    assert client.delete(f"/contributions/{contribution_id}", headers=headers_two).status_code == 404


def test_create_contribution_missing_fields(client):
    _, token = _signup_member(client, "MissingFields", "missing@example.com", 333333333)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/contributions", headers=headers, json={})
    assert resp.status_code == 422

    resp = client.post("/contributions", headers=headers, json={"amount": 100.00})
    assert resp.status_code == 422

    resp = client.post("/contributions", headers=headers, json={"date": "2026-07-10T00:00:00"})
    assert resp.status_code == 422

    resp = client.post("/contributions", headers=headers, json={"contribution_type": "cash"})
    assert resp.status_code == 422


def test_create_contribution_invalid_type(client):
    _, token = _signup_member(client, "InvalidType", "invalid@example.com", 444444444)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/contributions",
        headers=headers,
        json={"amount": 50.00, "date": "2026-07-10T00:00:00", "contribution_type": "invalid"},
    )
    assert resp.status_code == 422


def test_create_contribution_all_valid_types(client):
    _, token = _signup_member(client, "AllTypes", "alltypes@example.com", 555555555)
    headers = {"Authorization": f"Bearer {token}"}

    for ctype in ("boma", "mpesa", "cash", "bank"):
        resp = client.post(
            "/contributions",
            headers=headers,
            json={"amount": 75.00, "date": "2026-07-10T00:00:00", "contribution_type": ctype},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["contribution_type"] == ctype
        assert data["amount"] == "75.00"


def test_get_contribution_not_found(client):
    _, token = _signup_member(client, "GetNotFound", "getnotfound@example.com", 666666666)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/contributions/99999", headers=headers)
    assert resp.status_code == 404


def test_update_contribution_all_fields(client):
    _, token = _signup_member(client, "UpdateAll", "updateall@example.com", 777777777)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post(
        "/contributions",
        headers=headers,
        json={"amount": 100.00, "date": "2026-07-10T00:00:00", "contribution_type": "mpesa"},
    )
    assert create_resp.status_code == 201
    contribution_id = create_resp.get_json()["id"]

    update_resp = client.put(
        f"/contributions/{contribution_id}",
        headers=headers,
        json={"amount": 200.00, "date": "2026-08-15T00:00:00", "contribution_type": "bank"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.get_json()
    assert updated["amount"] == "200.00"
    assert updated["contribution_type"] == "bank"


def test_update_contribution_partial(client):
    _, token = _signup_member(client, "UpdatePartial", "updatepartial@example.com", 888888888)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post(
        "/contributions",
        headers=headers,
        json={"amount": 300.00, "date": "2026-07-10T00:00:00", "contribution_type": "cash"},
    )
    assert create_resp.status_code == 201
    contribution_id = create_resp.get_json()["id"]

    update_resp = client.put(
        f"/contributions/{contribution_id}",
        headers=headers,
        json={"amount": 350.00},
    )
    assert update_resp.status_code == 200
    assert update_resp.get_json()["amount"] == "350.00"

    update_resp = client.put(
        f"/contributions/{contribution_id}",
        headers=headers,
        json={"contribution_type": "boma"},
    )
    assert update_resp.status_code == 200
    assert update_resp.get_json()["contribution_type"] == "boma"


def test_update_contribution_invalid_type(client):
    _, token = _signup_member(client, "UpdateInvalid", "updateinvalid@example.com", 999999999)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post(
        "/contributions",
        headers=headers,
        json={"amount": 50.00, "date": "2026-07-10T00:00:00", "contribution_type": "cash"},
    )
    assert create_resp.status_code == 201
    contribution_id = create_resp.get_json()["id"]

    resp = client.put(
        f"/contributions/{contribution_id}",
        headers=headers,
        json={"contribution_type": "invalid"},
    )
    assert resp.status_code == 422


def test_update_contribution_not_found(client):
    _, token = _signup_member(client, "UpdateNotFound", "updatenotfound@example.com", 101010101)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/contributions/99999", headers=headers, json={"amount": 99.00})
    assert resp.status_code == 404


def test_delete_contribution_not_found(client):
    _, token = _signup_member(client, "DeleteNotFound", "deletenotfound@example.com", 121212121)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.delete("/contributions/99999", headers=headers)
    assert resp.status_code == 404
