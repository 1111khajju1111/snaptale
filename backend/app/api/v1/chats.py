from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user_id, verify_snapplus_session_token
from app.models.models import Chat, ChatMessage, Character
from app.schemas.chat import (
    ChatCreate, ChatResponse, ChatMessageCreate, ChatMessageResponse
)
from app.services.chat_service import create_chat_thread, post_chat_message

router = APIRouter(tags=["chats"])

@router.post("/characters/{id}/chats", response_model=ChatResponse)
async def create_character_chat(
    id: str,
    payload: ChatCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    chat = await create_chat_thread(
        db=db,
        user_id=user_id,
        character_id=id,
        title=payload.title,
        topic=payload.topic or "Random Talks",
        is_protected=payload.is_protected,
        universe_id=payload.universe_id,
        language=payload.language
    )
    resp = ChatResponse.model_validate(chat)
    if chat.character:
        resp.character_name = chat.character.name
    return resp

@router.get("/characters/{id}/chats", response_model=List[ChatResponse])
async def list_character_chats(
    id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Chat).where(
        Chat.character_id == id,
        Chat.user_id == user_id
    ).order_by(Chat.last_message_at.desc()))
    chats = res.scalars().all()
    output = []
    for c in chats:
        resp = ChatResponse.model_validate(c)
        if c.character:
            resp.character_name = c.character.name
        output.append(resp)
    return output

@router.get("/chats/{id}", response_model=ChatResponse)
async def get_chat(
    id: str,
    x_snapplus_session: Optional[str] = Header(None, alias="X-SnapPlus-Session"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Chat).where(Chat.id == id, Chat.user_id == user_id))
    chat = res.scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")

    if chat.is_protected:
        if not x_snapplus_session or not verify_snapplus_session_token(x_snapplus_session, user_id):
            raise HTTPException(
                status_code=403,
                detail="SnapTale+ private chat is locked. Please verify 4-digit PIN first."
            )
    
    msg_res = await db.execute(
        select(ChatMessage).where(ChatMessage.chat_id == id).order_by(ChatMessage.created_at.asc())
    )
    messages = msg_res.scalars().all()
    resp = ChatResponse.model_validate(chat)
    if chat.character:
        resp.character_name = chat.character.name
    resp.messages = [ChatMessageResponse.model_validate(m) for m in messages]
    return resp

@router.post("/chats/{id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    id: str,
    payload: ChatMessageCreate,
    x_snapplus_session: Optional[str] = Header(None, alias="X-SnapPlus-Session"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    bot_reply = await post_chat_message(
        db=db,
        user_id=user_id,
        chat_id=id,
        message_content=payload.content,
        snapplus_session_token=x_snapplus_session
    )
    return ChatMessageResponse.model_validate(bot_reply)

@router.delete("/chats/{id}")
async def delete_chat(
    id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Chat).where(Chat.id == id, Chat.user_id == user_id))
    chat = res.scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    await db.delete(chat)
    await db.commit()
    return {"message": "Chat thread deleted."}