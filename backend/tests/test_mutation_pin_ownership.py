import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import StoryBranch, Story, Character

@pytest.mark.asyncio
async def test_mutation_pin_ownership(client: AsyncClient, db_session: AsyncSession):
    char = Character(
        id='char-branch-1',
        user_id='user-alpha',
        name='Dogesh',
        species_or_object='dog',
        dna={'name': 'Dogesh', 'species_or_object': 'dog', 'personality': 'funny'}
    )
    p_story = Story(
        id='story-p-1',
        user_id='user-alpha',
        character_id='char-branch-1',
        title='Parent Story',
        content='Parent content...'
    )
    c_story = Story(
        id='story-c-1',
        user_id='user-alpha',
        character_id='char-branch-1',
        title='Mutated Child Story',
        content='Mutated content...'
    )
    branch = StoryBranch(
        id='branch-alpha-1',
        parent_story_id='story-p-1',
        child_story_id='story-c-1',
        mutation_type='horror',
        mutation_prompt='Make it scary',
        created_by='user-alpha'
    )
    db_session.add_all([char, p_story, c_story, branch])
    await db_session.commit()

    # User Beta tries to pin User Alpha's mutation -> 403 Forbidden
    res_beta = await client.post(
        '/api/v1/pins',
        json={'item_type': 'mutation', 'item_id': 'branch-alpha-1'},
        headers={'Authorization': 'Bearer test-token-user-beta'}
    )
    assert res_beta.status_code == 403

    # User Alpha pins their own mutation -> 200 OK
    res_alpha = await client.post(
        '/api/v1/pins',
        json={'item_type': 'mutation', 'item_id': 'branch-alpha-1'},
        headers={'Authorization': 'Bearer test-token-user-alpha'}
    )
    assert res_alpha.status_code == 200
