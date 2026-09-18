import importlib
import os

import pytest


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


def test_treasury_models_match_expected_schema():
    from src.models.treasury import InvestmentModel, TreasuryModel

    assert hasattr(TreasuryModel, "main_account_balance")
    assert hasattr(TreasuryModel, "account_balance_date")
    assert hasattr(TreasuryModel, "total_investments")
    assert hasattr(InvestmentModel, "investment_type")
    assert hasattr(InvestmentModel, "name")
    assert hasattr(InvestmentModel, "initial_amount")
    assert hasattr(InvestmentModel, "interest")
    assert hasattr(InvestmentModel, "current_amount")
    assert hasattr(InvestmentModel, "more_info")

    choices = [
        "MMF",
        "boma_yangu",
        "government_bonds",
        "cryptocurrency",
        "land_asset",
    ]
    assert InvestmentModel.investment_type.property.columns[0].type.enums == choices


def test_investments_can_be_fetched_by_user(client):
    import src.app as app_module
    from src.models.treasury import InvestmentModel, TreasuryModel

    _, token = _signup_member(client, "InvestmentUser", "investments@example.com", 123456789)
    headers = {"Authorization": f"Bearer {token}"}

    with app_module.app.app_context():
        treasury = TreasuryModel(
            main_account_balance=5000.00,
            account_balance_date=None,
            total_investments=1200.00,
        )
        app_module.db.session.add(treasury)
        app_module.db.session.flush()
        investment = InvestmentModel(
            treasury_id=treasury.id,
            investment_type="MMF",
            name="Emergency Fund",
            initial_amount=1000.00,
            interest=50.00,
            current_amount=1050.00,
            more_info="High liquidity",
        )
        app_module.db.session.add(investment)
        app_module.db.session.commit()
        investment_id = investment.id

    all_response = client.get("/treasury/investments", headers=headers)
    assert all_response.status_code == 200
    assert len(all_response.get_json()) == 1

    single_response = client.get(f"/treasury/investments/{investment_id}", headers=headers)
    assert single_response.status_code == 200
    payload = single_response.get_json()
    assert payload["name"] == "Emergency Fund"
    assert payload["investment_type"] == "MMF"


def test_treasury_get_requires_authentication(client):
    response = client.get("/treasury")

    assert response.status_code == 401


def test_admin_can_record_account_withdrawal(client):
    import src.app as app_module
    from src.models.member import memberModel
    from src.models.treasury import TreasuryModel

    signup_payload = {
        "name": "TreasuryAdmin",
        "email_address": "treasuryadmin@example.com",
        "phone_number": 777666555,
        "password": "password123",
    }
    signup_response = client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201

    with app_module.app.app_context():
        member = memberModel.query.filter_by(name="TreasuryAdmin").first()
        assert member is not None
        member.role = memberModel.ADMIN_ROLE
        treasury = TreasuryModel(
            main_account_balance=5000.00,
            account_balance_date=None,
            total_investments=1200.00,
        )
        app_module.db.session.add(treasury)
        app_module.db.session.commit()

    login_response = client.post(
        "/auth/login",
        json={"name": "TreasuryAdmin", "password": "password123"},
    )
    assert login_response.status_code == 200
    token = login_response.get_json()["access_token"]

    response = client.post(
        "/treasury/withdrawals",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": 500.00, "details": "Office rent"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["main_account_balance"] == "4500.00"
    assert payload["account_balance_date"] is not None


def test_treasury_get_returns_summary_records_for_authenticated_users(client):
    import src.app as app_module
    from src.models.treasury import TreasuryModel

    _, token = _signup_member(client, "TreasuryReader", "treasuryreader@example.com", 999888777)
    headers = {"Authorization": f"Bearer {token}"}

    with app_module.app.app_context():
        treasury = TreasuryModel(
            main_account_balance=5000.00,
            account_balance_date=None,
            total_investments=1200.00,
        )
        app_module.db.session.add(treasury)
        app_module.db.session.commit()

    response = client.get("/treasury", headers=headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0]["main_account_balance"] == "5000.00"
    assert payload[0]["total_investments"] == "1200.00"
