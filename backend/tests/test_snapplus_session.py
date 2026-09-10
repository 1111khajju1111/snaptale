import pytest
from app.core.security import create_snapplus_session_token, verify_snapplus_session_token
from app.services.chat_service import create_chat_thread, post_chat_message
from app.models.models import Character
from app.schemas.character import CharacterDNA, SpeechStyle
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_snapplus_session_and_protected_chat(db_session):
    """Verify short-lived session token generation and protected chat gate enforcement."""
    user_id = "user-snapplus-tester"

    # 1. Verify token signing and validation
    session_token = create_snapplus_session_token(user_id)
    assert verify_snapplus_session_token(session_token, user_id) is True
    assert verify_snapplus_session_token("invalid-fake-token", user_id) is False
    assert verify_snapplus_session_token(session_token, "other-user-999") is False

    # 2. Create character with complete Character DNA
    dna = CharacterDNA(
        name="Shadow Dogesh",
        species_or_object="dog",
        personality=["dark", "cynical"],
        secret="Night shadow courier",
        fear="Daylight inspections",
        origin="Underground alleys",
        occupation="Black market detective",
        abilities=["Night vision"],
        weaknesses=["Bright flashlights"],
        comedy_archetype="dark_deadpan",
        humor_style=["sarcasm"],
        speech_style=SpeechStyle(language="te-en", register="naatu")
    )
    char = Character(
        user_id=user_id,
        name="Shadow Dogesh",
        species_or_object="dog",
        dna=dna.model_dump()
    )
    db_session.add(char)
    await db_session.commit()
    await db_session.refresh(char)

    chat = await create_chat_thread(
        db=db_session,
        user_id=user_id,
        character_id=char.id,
        title="Late Night Secret Chat",
        is_protected=True # SnapTale+ private chat
    )

    # 3. Post message WITHOUT token -> MUST FAIL with 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        await post_chat_message(
            db=db_session,
            user_id=user_id,
            chat_id=chat.id,
            message_content="Are you awake?",
            snapplus_session_token=None
        )
    assert exc.value.status_code == 403

    # 4. Post message WITH valid session token -> MUST SUCCEED
    msg = await post_chat_message(
        db=db_session,
        user_id=user_id,
        chat_id=chat.id,
        message_content="Are you awake?",
        snapplus_session_token=session_token
    )
    assert msg.sender_type == "character"
    assert msg.content != ""