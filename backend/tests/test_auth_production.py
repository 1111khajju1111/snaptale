import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_auth_registration_and_login(client: AsyncClient):
    reg_payload = {
        "email": "hero@snaptale.ai",
        "password": "SecurePassword123!",
        "username": "dogesh_master"
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 200
    data = reg_res.json()
    assert data["email"] == "hero@snaptale.ai"
    assert "access_token" in data
    user_id = data["user_id"]

    # Duplicate registration rejected
    dup_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 400

    # Login with wrong password fails strictly
    wrong_login = {
        "email": "hero@snaptale.ai",
        "password": "WrongPassword!"
    }
    wrong_res = await client.post("/api/v1/auth/login", json=wrong_login)
    assert wrong_res.status_code == 401
    assert "Invalid email or password" in wrong_res.json()["detail"]

    # Login with unknown email fails strictly (no silent auto-registration)
    unknown_login = {
        "email": "unknown_user@snaptale.ai",
        "password": "AnyPassword123!"
    }
    unk_res = await client.post("/api/v1/auth/login", json=unknown_login)
    assert unk_res.status_code == 401

    # Login with correct password succeeds
    good_login = {
        "email": "hero@snaptale.ai",
        "password": "SecurePassword123!"
    }
    good_res = await client.post("/api/v1/auth/login", json=good_login)
    assert good_res.status_code == 200
    assert good_res.json()["user_id"] == user_id
    assert "access_token" in good_res.json()
