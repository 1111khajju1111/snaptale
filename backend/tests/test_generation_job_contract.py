import io
import pytest
from httpx import AsyncClient


async def _register_and_get_token(client: AsyncClient, email: str) -> str:
    res = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePassword123!",
        "username": email.split("@")[0],
    })
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_generate_story_requires_auth_token(client: AsyncClient):
    """POST /stories/generate with no Authorization header must be a clean
    401, not a payload that a client could mistake for a queued job."""
    res = await client.post(
        "/api/v1/stories/generate",
        data={"experience_mode": "snaptale", "language": "te-en"},
    )
    assert res.status_code == 401
    body = res.json()
    assert "job_id" not in body


@pytest.mark.asyncio
async def test_generate_story_with_valid_token_returns_job_id(client: AsyncClient):
    """A properly authenticated request must return a non-empty job_id that
    the client can immediately poll."""
    token = await _register_and_get_token(client, "creator@snaptale.ai")
    res = await client.post(
        "/api/v1/stories/generate",
        data={"experience_mode": "snaptale", "language": "te-en"},
        files={"file": ("photo.jpg", io.BytesIO(b"fake-bytes"), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("job_id")

    # The job must be immediately pollable by id with the same token.
    job_id = body["job_id"]
    poll_res = await client.get(
        f"/api/v1/generation-jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert poll_res.status_code == 200
    assert poll_res.json()["job_id"] == job_id


@pytest.mark.asyncio
async def test_job_status_requires_auth_token(client: AsyncClient):
    """GET /generation-jobs/{id} with no Authorization header must 401,
    not leak job existence/state to an anonymous caller."""
    res = await client.get("/api/v1/generation-jobs/some-job-id")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_job_status_without_id_has_no_route(client: AsyncClient):
    """Documents the exact contract Flutter must follow: there is no
    collection route at /generation-jobs/, only /generation-jobs/{id}.
    A client that polls with an empty job id will always get a 404 here
    -- which is why the mobile client must never construct that URL."""
    res = await client.get("/api/v1/generation-jobs/")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_job_status_for_other_users_job_is_not_found(client: AsyncClient):
    """A job belonging to a different user must not be visible (404, not
    403, so job existence isn't leaked to non-owners)."""
    token_a = await _register_and_get_token(client, "owner@snaptale.ai")
    token_b = await _register_and_get_token(client, "stranger@snaptale.ai")

    gen_res = await client.post(
        "/api/v1/stories/generate",
        data={"experience_mode": "snaptale", "language": "te-en"},
        files={"file": ("photo.jpg", io.BytesIO(b"fake-bytes"), "image/jpeg")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    job_id = gen_res.json()["job_id"]

    res = await client.get(
        f"/api/v1/generation-jobs/{job_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404
