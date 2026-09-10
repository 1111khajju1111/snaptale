import pytest
from app.services.pin_service import pin_item
from app.models.models import Character, Story
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_pin_ownership_enforcement(db_session):
    """Verify that a user cannot pin resources owned by another user (HTTP 403)."""
    user_a = "user-alice-111"
    user_b = "user-bob-222"

    # Create character owned by User B
    char_b = Character(
        user_id=user_b,
        name="Bob's Cat",
        species_or_object="cat",
        dna={"name": "Bob's Cat", "species_or_object": "cat"}
    )
    db_session.add(char_b)
    await db_session.commit()
    await db_session.refresh(char_b)

    # User A attempts to pin User B's character -> MUST FAIL with 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        await pin_item(db_session, user_id=user_a, item_type="character", item_id=char_b.id)
    assert exc.value.status_code == 403

    # User B pins their own character -> MUST SUCCEED
    pinned = await pin_item(db_session, user_id=user_b, item_type="character", item_id=char_b.id)
    assert pinned.item_id == char_b.id