import pytest
from app.models.models import Character, Story, StoryBranch
from app.api.v1.stories import get_lore_tree
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_lore_tree_user_isolation(db_session):
    """Verify that lore tree branches belonging to User B never leak into User A's lore tree."""
    user_a = "user-alice-lore"
    user_b = "user-bob-lore"

    # User A's character and stories
    char_a = Character(user_id=user_a, name="Hero A", species_or_object="dog", dna={"name": "Hero A", "species_or_object": "dog"})
    db_session.add(char_a)
    await db_session.commit()
    await db_session.refresh(char_a)

    story_a1 = Story(user_id=user_a, character_id=char_a.id, title="Story A1", content="Setup A1")
    story_a2 = Story(user_id=user_a, character_id=char_a.id, title="Story A2", content="Setup A2")
    db_session.add_all([story_a1, story_a2])
    await db_session.commit()
    await db_session.refresh(story_a1)
    await db_session.refresh(story_a2)

    branch_a = StoryBranch(parent_story_id=story_a1.id, child_story_id=story_a2.id, mutation_type="space", created_by=user_a)
    db_session.add(branch_a)

    # User B's character and stories
    char_b = Character(user_id=user_b, name="Hero B", species_or_object="cat", dna={"name": "Hero B", "species_or_object": "cat"})
    db_session.add(char_b)
    await db_session.commit()
    await db_session.refresh(char_b)

    story_b1 = Story(user_id=user_b, character_id=char_b.id, title="Story B1", content="Setup B1")
    story_b2 = Story(user_id=user_b, character_id=char_b.id, title="Story B2", content="Setup B2")
    db_session.add_all([story_b1, story_b2])
    await db_session.commit()
    await db_session.refresh(story_b1)
    await db_session.refresh(story_b2)

    branch_b = StoryBranch(parent_story_id=story_b1.id, child_story_id=story_b2.id, mutation_type="horror", created_by=user_b)
    db_session.add(branch_b)
    await db_session.commit()

    # User A requests their lore tree for Story A1
    nodes = await get_lore_tree(id=story_a1.id, user_id=user_a, db=db_session)
    node_ids = [n.id for n in nodes]

    assert story_a1.id in node_ids
    assert story_a2.id in node_ids
    # User B's stories MUST NOT be present
    assert story_b1.id not in node_ids
    assert story_b2.id not in node_ids

    # User A cannot request User B's story lore tree -> MUST return 404
    with pytest.raises(HTTPException) as exc:
        await get_lore_tree(id=story_b1.id, user_id=user_a, db=db_session)
    assert exc.value.status_code == 404