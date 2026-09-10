from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.models.models import Character, Story, Chat, ChatMessage, Universe, StoryBranch
from app.schemas.library import LibrarySearchItem, LibrarySearchResult

async def search_library(
    db: AsyncSession,
    user_id: str,
    query: str,
    page: int = 1,
    page_size: int = 20
) -> LibrarySearchResult:
    q_str = f"%{query.strip().lower()}%"
    offset_val = (page - 1) * page_size
    all_items: List[LibrarySearchItem] = []

    # 1. Search Characters (Name, Species, Origin)
    char_res = await db.execute(
        select(Character).where(
            and_(
                Character.user_id == user_id,
                or_(
                    Character.name.ilike(q_str),
                    Character.species_or_object.ilike(q_str),
                    Character.origin_story.ilike(q_str)
                )
            )
        ).limit(100)
    )
    for c in char_res.scalars().all():
        all_items.append(LibrarySearchItem(
            id=c.id,
            type="character",
            title=c.name,
            subtitle=f"{c.species_or_object.title()} • {c.story_count} stories",
            preview_text=c.origin_story,
            image_url=c.photo_url,
            is_pinned=c.is_pinned,
            created_at=c.created_at
        ))

    # 2. Search Stories (Title, Content, Punchline)
    story_res = await db.execute(
        select(Story).where(
            and_(
                Story.user_id == user_id,
                or_(
                    Story.title.ilike(q_str),
                    Story.content.ilike(q_str),
                    Story.punchline.ilike(q_str)
                )
            )
        ).limit(100)
    )
    for s in story_res.scalars().all():
        all_items.append(LibrarySearchItem(
            id=s.id,
            type="story",
            title=s.title,
            subtitle=f"Story • {s.experience_mode.title()}",
            preview_text=s.punchline or s.content[:100],
            image_url=s.generated_image_url,
            is_pinned=s.is_pinned,
            created_at=s.created_at
        ))

    # 3. Search Universes (Name, Description)
    univ_res = await db.execute(
        select(Universe).where(
            and_(
                Universe.user_id == user_id,
                or_(
                    Universe.name.ilike(q_str),
                    Universe.description.ilike(q_str)
                )
            )
        ).limit(100)
    )
    for u in univ_res.scalars().all():
        all_items.append(LibrarySearchItem(
            id=u.id,
            type="universe",
            title=u.name,
            subtitle="Personal Universe",
            preview_text=u.description,
            is_pinned=u.is_pinned,
            created_at=u.created_at
        ))

    # 4. Search Chats & Messages (Title, Topic, Message Content)
    chat_res = await db.execute(
        select(Chat).distinct().outerjoin(ChatMessage, Chat.id == ChatMessage.chat_id).where(
            and_(
                Chat.user_id == user_id,
                or_(
                    Chat.title.ilike(q_str),
                    Chat.topic.ilike(q_str),
                    ChatMessage.content.ilike(q_str)
                )
            )
        ).limit(100)
    )
    for ch in chat_res.scalars().all():
        all_items.append(LibrarySearchItem(
            id=ch.id,
            type="chat",
            title=ch.title,
            subtitle=f"Chat Topic: {ch.topic or 'General'}",
            preview_text=f"Last message {ch.last_message_at.strftime('%Y-%m-%d')}",
            is_pinned=ch.is_pinned,
            created_at=ch.created_at
        ))

    # 5. Search Story Branches & Mutations
    branch_res = await db.execute(
        select(StoryBranch).where(
            and_(
                StoryBranch.created_by == user_id,
                or_(
                    StoryBranch.mutation_type.ilike(q_str),
                    StoryBranch.mutation_prompt.ilike(q_str)
                )
            )
        ).limit(100)
    )
    for b in branch_res.scalars().all():
        all_items.append(LibrarySearchItem(
            id=b.id,
            type="mutation",
            title=f"Mutation: {b.mutation_type or 'Branch'}",
            subtitle=f"Story Lineage Branch",
            preview_text=b.mutation_prompt or f"Branch of {b.parent_story_id}",
            created_at=b.created_at
        ))

    # Sort globally by created_at descending (newest first)
    all_items.sort(
        key=lambda item: item.created_at.timestamp() if item.created_at else 0,
        reverse=True
    )

    total_count = len(all_items)
    paginated_results = all_items[offset_val : offset_val + page_size]

    return LibrarySearchResult(
        query=query,
        total_count=total_count,
        page=page,
        results=paginated_results
    )