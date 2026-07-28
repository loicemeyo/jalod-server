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
            "type": "mpesa",
        },
    )
    assert create_response.status_code == 201
    created = create_response.get_json()
    assert created["amount"] == "250.00"
    assert created["type"] == "mpesa"
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
        json={"amount": 300.00, "type": "cash"},
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["amount"] == "300.00"
    assert updated["type"] == "cash"

    delete_response = client.delete(f"/contributions/{contribution_id}", headers=headers)
    assert delete_response.status_code == 204

    with app_module.app.app_context():
        assert app_module.db.session.get(ContributionModel, contribution_id) is None


def test_contribution_crud_requires_authentication(client):
    assert client.post("/contributions", json={"amount": 1, "date": "2026-07-10T00:00:00", "type": "cash"}).status_code == 401
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
        json={"amount": 50.00, "date": "2026-07-10T00:00:00", "type": "cash"},
    )
    assert create_response.status_code == 201
    contribution_id = create_response.get_json()["id"]

    assert client.get(f"/contributions/{contribution_id}", headers=headers_two).status_code == 404
    assert client.put(f"/contributions/{contribution_id}", headers=headers_two, json={"amount": 55.00}).status_code == 404
    assert client.delete(f"/contributions/{contribution_id}", headers=headers_two).status_code == 404
