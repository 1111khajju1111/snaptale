import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, ForeignKey, JSON, Date, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def gen_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    security = relationship("SnapPlusChatSecurity", back_populates="user", uselist=False, cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="user", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    pinned_items = relationship("PinnedItem", back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(150), nullable=True)
    avatar_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    is_snapplus_eligible = Column(Boolean, default=False)
    snapplus_enabled = Column(Boolean, default=False)
    preferred_language = Column(String(10), default="te-en")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    user = relationship("User", back_populates="profile")

class SnapPlusChatSecurity(Base):
    __tablename__ = "snapplus_chat_security"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    pin_hash = Column(String(255), nullable=False)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    user = relationship("User", back_populates="security")

class Universe(Base):
    __tablename__ = "universes"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    characters = relationship("Character", back_populates="universe")

class Character(Base):
    __tablename__ = "characters"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    universe_id = Column(String(36), ForeignKey("universes.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    species_or_object = Column(String(100), nullable=False)
    photo_url = Column(Text, nullable=True)
    dna = Column(JSON, nullable=False)
    origin_story = Column(Text, nullable=True)
    story_count = Column(Integer, default=0)
    chat_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    last_activity_at = Column(DateTime(timezone=True), default=utc_now)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    user = relationship("User", back_populates="characters")
    universe = relationship("Universe", back_populates="characters")
    stories = relationship("Story", back_populates="character", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="character", cascade="all, delete-orphan")

class CharacterRelationship(Base):
    __tablename__ = "character_relationships"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    source_character_id = Column(String(36), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    target_character_id = Column(String(36), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(36), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    universe_id = Column(String(36), ForeignKey("universes.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    punchline = Column(Text, nullable=True)
    experience_mode = Column(String(20), default="snaptale")
    language = Column(String(10), default="te-en")
    dice_roll = Column(JSON, nullable=True)
    generated_image_url = Column(Text, nullable=True)
    privacy = Column(String(20), default="private", index=True)
    moderation_status = Column(String(20), default="pending", index=True)
    like_count = Column(Integer, default=0)
    remix_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    
    user = relationship("User", back_populates="stories")
    character = relationship("Character", back_populates="stories")
    child_branches = relationship("StoryBranch", foreign_keys="StoryBranch.parent_story_id", back_populates="parent_story")

class StoryBranch(Base):
    __tablename__ = "story_branches"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    parent_story_id = Column(String(36), ForeignKey("stories.id", ondelete="SET NULL"), nullable=True, index=True)
    child_story_id = Column(String(36), ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True)
    mutation_type = Column(String(50), nullable=True)
    mutation_prompt = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    parent_story = relationship("Story", foreign_keys=[parent_story_id], back_populates="child_branches")
    child_story = relationship("Story", foreign_keys=[child_story_id])

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(String(36), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    universe_id = Column(String(36), ForeignKey("universes.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(150), nullable=False)
    topic = Column(String(100), nullable=True)
    is_protected = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    language = Column(String(10), default="te-en")
    last_message_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    user = relationship("User", back_populates="chats")
    character = relationship("Character", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    chat_id = Column(String(36), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    chat = relationship("Chat", back_populates="messages")

class PinnedItem(Base):
    __tablename__ = "pinned_items"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type = Column(String(50), nullable=False)
    item_id = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    user = relationship("User", back_populates="pinned_items")
    __table_args__ = (UniqueConstraint("user_id", "item_type", "item_id", name="uq_user_pinned_item"),)

class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="queued", index=True)
    stage = Column(String(50), default="queued")
    progress = Column(Integer, default=0)
    request_hash = Column(String(64), nullable=True)
    idempotency_key = Column(String(128), nullable=True, index=True)
    story_id = Column(String(36), ForeignKey("stories.id", ondelete="SET NULL"), nullable=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_user_idempotency_job"),)

class Like(Base):
    __tablename__ = "likes"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    story_id = Column(String(36), ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    __table_args__ = (UniqueConstraint("user_id", "story_id", name="uq_user_story_like"),)

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    story_id = Column(String(36), ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    reporter_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    story_id = Column(String(36), ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), default=utc_now)

class UsageLimit(Base):
    __tablename__ = "usage_limits"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    usage_date = Column(Date, default=datetime.now(timezone.utc).date())
    stories_created = Column(Integer, default=0)
    mutations_created = Column(Integer, default=0)
    images_generated = Column(Integer, default=0)
    chats_sent = Column(Integer, default=0)
    remixes_created = Column(Integer, default=0)
    
    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_user_usage_date"),)