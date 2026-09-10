import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import GenerationJob

@pytest.mark.asyncio
async def test_idempotency_race_handling(client: AsyncClient, db_session: AsyncSession):
    job = GenerationJob(
        id='job-existing-123',
        user_id='user-race-1',
        status='processing',
        stage='story',
        progress=50,
        idempotency_key='unique-race-key-999'
    )
    db_session.add(job)
    await db_session.commit()

    res = await client.post(
        '/api/v1/stories/generate',
        data={'experience_mode': 'snaptale'},
        headers={
            'Authorization': 'Bearer test-token-user-race-1',
            'Idempotency-Key': 'unique-race-key-999'
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data['job_id'] == 'job-existing-123'
    assert data['status'] == 'processing'
