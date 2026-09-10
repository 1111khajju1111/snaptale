import pytest
from app.core.security import hash_pin, verify_pin
from app.services.snapplus_service import setup_snapplus_pin, verify_snapplus_pin
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_snapplus_pin_security(db_session):
    """Verify 4-digit PIN Argon2/bcrypt hashing, verification, and brute-force lockout."""
    user_id = "test-user-security-123"
    
    # 1. Verify invalid PIN format rejected
    with pytest.raises(ValueError):
        hash_pin("123") # Less than 4 digits
    with pytest.raises(ValueError):
        hash_pin("abcd") # Non-numeric
        
    pin_hash = hash_pin("4321")
    assert pin_hash != "4321" # Must be securely hashed, never plaintext
    assert verify_pin("4321", pin_hash) is True
    assert verify_pin("0000", pin_hash) is False

    # 2. Verify lockout logic in service
    await setup_snapplus_pin(db_session, user_id, "9876")
    
    # Succeeded verification
    assert await verify_snapplus_pin(db_session, user_id, "9876") is True
    
    # 4 failed attempts keep track of attempts
    for _ in range(4):
        with pytest.raises(HTTPException) as exc:
            await verify_snapplus_pin(db_session, user_id, "0000")
        assert exc.value.status_code == 401
        
    # 5th failure locks account with 429
    with pytest.raises(HTTPException) as exc:
        await verify_snapplus_pin(db_session, user_id, "0000")
    assert exc.value.status_code == 429
