import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Story, Character

@pytest.mark.asyncio
async def test_story_visibility_authorization(client: AsyncClient, db_session: AsyncSession):
    char = Character(
        id='char-vis-1',
        user_id='user-owner-1',
        name='Dogesh Bhai',
        species_or_object='dog',
        dna={'name': 'Dogesh', 'species_or_object': 'dog', 'personality': 'funny'}
    )
    db_session.add(char)
    await db_session.commit()

    private_story = Story(
        id='story-priv-1',
        user_id='user-owner-1',
        character_id='char-vis-1',
        title='Dogesh Top Secret Heist',
        content='Ultra private comedy heist...',
        privacy='private',
        moderation_status='approved'
    )
    public_story = Story(
        id='story-pub-1',
        user_id='user-owner-1',
        character_id='char-vis-1',
        title='Dogesh Public Comedy Special',
        content='Public comedy...',
        privacy='public',
        moderation_status='approved'
    )
    unlisted_story = Story(
        id='story-unlisted-1',
        user_id='user-owner-1',
        character_id='char-vis-1',
        title='Dogesh Unlisted Share',
        content='Unlisted link...',
        privacy='unlisted',
        moderation_status='approved'
    )
    db_session.add_all([private_story, public_story, unlisted_story])
    await db_session.commit()

    res_owner = await client.get('/api/v1/stories/story-priv-1', headers={'Authorization': 'Bearer test-token-user-owner-1'})
    assert res_owner.status_code == 200
    assert res_owner.json()['title'] == 'Dogesh Top Secret Heist'

    res_other = await client.get('/api/v1/stories/story-priv-1', headers={'Authorization': 'Bearer test-token-user-stranger-2'})
    assert res_other.status_code == 404

    res_anon = await client.get('/api/v1/stories/story-priv-1')
    assert res_anon.status_code == 404

    res_pub_anon = await client.get('/api/v1/stories/story-pub-1')
    assert res_pub_anon.status_code == 200
    assert res_pub_anon.json()['title'] == 'Dogesh Public Comedy Special'

    res_unlisted_anon = await client.get('/api/v1/stories/story-unlisted-1')
    assert res_unlisted_anon.status_code == 200
    assert res_unlisted_anon.json()['title'] == 'Dogesh Unlisted Share'
