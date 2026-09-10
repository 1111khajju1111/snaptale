import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Chat, ChatMessage, Character

@pytest.mark.asyncio
async def test_chat_message_content_search(client: AsyncClient, db_session: AsyncSession):
    char = Character(
        id='char-mars-1',
        user_id='user-mars-owner',
        name='Dogesh Bhai',
        species_or_object='dog',
        dna={'name': 'Dogesh', 'species_or_object': 'dog', 'personality': 'funny'}
    )
    chat = Chat(
        id='chat-random-talks',
        user_id='user-mars-owner',
        character_id='char-mars-1',
        title='Random Daily Talks',
        topic='General Gossip'
    )
    msg = ChatMessage(
        id='msg-mars-1',
        chat_id='chat-random-talks',
        sender_type='user',
        content='Bro remember our secret Mars mission? We nearly lost the spaceship!'
    )
    db_session.add_all([char, chat, msg])
    await db_session.commit()

    res = await client.get(
        '/api/v1/library/search?q=Mars',
        headers={'Authorization': 'Bearer test-token-user-mars-owner'}
    )
    assert res.status_code == 200
    data = res.json()
    chat_results = [r for r in data['results'] if r['type'] == 'chat']
    assert len(chat_results) >= 1
    assert chat_results[0]['id'] == 'chat-random-talks'
