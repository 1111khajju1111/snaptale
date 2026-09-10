from typing import List, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.models import Chat, ChatMessage, Character, Universe, CharacterRelationship, Story
from app.schemas.character import CharacterDNA
from app.core.security import verify_snapplus_session_token
from app.ai import story_provider

async def create_chat_thread(
    db: AsyncSession,
    user_id: str,
    character_id: str,
    title: str,
    topic: str = "Random Talks",
    is_protected: bool = False,
    universe_id: Optional[str] = None,
    language: str = "te-en"
) -> Chat:
    # Verify character ownership
    res = await db.execute(select(Character).where(Character.id == character_id, Character.user_id == user_id))
    char = res.scalars().first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found or access denied.")

    chat = Chat(
        user_id=user_id,
        character_id=character_id,
        universe_id=universe_id or char.universe_id,
        title=title,
        topic=topic,
        is_protected=is_protected,
        language=language,
        last_message_at=datetime.now(timezone.utc)
    )
    db.add(chat)
    char.chat_count += 1
    await db.commit()
    await db.refresh(chat)
    return chat

async def post_chat_message(
    db: AsyncSession,
    user_id: str,
    chat_id: str,
    message_content: str,
    snapplus_session_token: Optional[str] = None
) -> ChatMessage:
    # 1. Fetch chat thread and check ownership
    res = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id))
    chat = res.scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat thread not found.")

    # 2. Check SnapTale+ private chat protection
    if chat.is_protected:
        if not snapplus_session_token or not verify_snapplus_session_token(snapplus_session_token, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SnapTale+ private chat requires an active 4-digit PIN unlock session."
            )

    # 3. Add user message
    user_msg = ChatMessage(
        chat_id=chat_id,
        sender_type="user",
        content=message_content,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user_msg)
    await db.commit()

    # 4. Load recent chat history
    msg_res = await db.execute(
        select(ChatMessage).where(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at.desc()).limit(15)
    )
    history_records = list(reversed(msg_res.scalars().all()))
    formatted_history = [
        {"role": m.sender_type, "content": m.content}
        for m in history_records
    ]

    # 5. Fetch Character DNA, Long-Term Memories, and Universe Context
    char_res = await db.execute(select(Character).where(Character.id == chat.character_id))
    character = char_res.scalars().first()
    character_dna = CharacterDNA(**character.dna)

    # Assemble Episodic Memory & Universe Context
    universe_context_str = ""
    if character.origin_story:
        universe_context_str += f"Origin Story: {character.origin_story}\n"

    # Query up to 3 past stories for this character to provide long-term episodic memory
    past_stories_res = await db.execute(
        select(Story).where(Story.character_id == character.id).order_by(Story.created_at.desc()).limit(3)
    )
    past_stories = past_stories_res.scalars().all()
    if past_stories:
        past_memories = [f"Past adventure '{s.title}': {s.punchline or s.content[:80]}" for s in past_stories]
        universe_context_str += "Past Adventures & Memories:\n- " + "\n- ".join(past_memories) + "\n"

    if chat.universe_id or character.universe_id:
        target_univ_id = chat.universe_id or character.universe_id
        u_res = await db.execute(select(Universe).where(Universe.id == target_univ_id))
        universe = u_res.scalars().first()
        if universe:
            universe_context_str += f"Universe: {universe.name}. {universe.description or ''}\n"

    # Fetch character relationships
    rel_res = await db.execute(
        select(CharacterRelationship).where(CharacterRelationship.source_character_id == character.id)
    )
    relationships = rel_res.scalars().all()
    if relationships:
        rel_descriptions = [f"{r.relationship_type}: {r.notes or 'connected'}" for r in relationships]
        universe_context_str += f"Relationships: {'; '.join(rel_descriptions)}\n"

    # 6. Generate in-character reply with Character DNA + Memory + Universe Context
    reply_text = await story_provider.chat_response(
        character_dna=character_dna,
        chat_history=formatted_history,
        message=message_content,
        universe_context=universe_context_str if universe_context_str else None,
        is_snapplus=chat.is_protected
    )

    # 7. Save character reply
    bot_msg = ChatMessage(
        chat_id=chat_id,
        sender_type="character",
        content=reply_text,
        created_at=datetime.now(timezone.utc)
    )
    db.add(bot_msg)
    chat.last_message_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(bot_msg)

    return bot_msg