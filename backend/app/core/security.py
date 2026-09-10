import os
import datetime
from typing import Optional
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, Security, Header, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

# Configure password & PIN hashing (Argon2 with optimized parameters)
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__time_cost=1,
    argon2__memory_cost=1024,
    argon2__parallelism=1
)

security_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Securely hash user password using Argon2id/bcrypt."""
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verify user submitted password against cryptographic hash."""
    if not hashed_password or not plain_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def hash_pin(pin: str) -> str:
    """Securely hash 4-digit PIN using Argon2id/bcrypt. Never store plaintext."""
    if not (pin.isdigit() and len(pin) == 4):
        raise ValueError("PIN must be exactly 4 numeric digits")
    return pwd_context.hash(pin)

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify submitted PIN against stored cryptographic hash."""
    return pwd_context.verify(plain_pin, hashed_pin)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + (expires_delta or datetime.timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_snapplus_session_token(user_id: str) -> str:
    """Generate a short-lived (15-minute) signed token for accessing protected SnapTale+ chats."""
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=settings.SNAPPLUS_SESSION_MINUTES)
    payload = {
        "sub": user_id,
        "scope": "snapplus_private_chat",
        "exp": expire
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def verify_snapplus_session_token(token: str, user_id: str) -> bool:
    """Verify short-lived SnapTale+ unlock session token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False}
        )
        if payload.get("sub") != user_id or payload.get("scope") != "snapplus_private_chat":
            return False
        return True
    except JWTError:
        return False

async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> str:
    """Validate JWT token and derive user identity server-side. Supports local JWTs and Supabase Auth JWTs."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required."
        )
    
    token = credentials.credentials
    # Test token bypass only in unit tests
    if (settings.APP_ENV == "test" or os.environ.get("APP_ENV") == "test") and token.startswith("test-token-"):
        return token.replace("test-token-", "")

    # Try local JWT secret
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False}
        )
        user_id: str = payload.get("sub") or payload.get("user_id")
        if user_id:
            return user_id
    except JWTError:
        pass

    # Try Supabase JWT secret if configured
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            user_id = payload.get("sub")
            if user_id:
                return user_id
        except JWTError:
            pass

    # If development/test mode, accept Supabase unverified claims
    if settings.APP_ENV in ("development", "test"):
        try:
            unverified = jwt.get_unverified_claims(token)
            if unverified.get("iss", "").startswith("https://") and "supabase" in unverified.get("iss", ""):
                user_id = unverified.get("sub")
                if user_id:
                    return user_id
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials."
    )

async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> Optional[str]:
    """Extract user_id if valid authentication token is provided; returns None if unauthenticated."""
    if not credentials:
        return None
    try:
        return await get_current_user_id(credentials)
    except HTTPException:
        return None

async def require_snapplus_session(
    x_snapplus_session: Optional[str] = Header(None, alias="X-SnapPlus-Session"),
    user_id: str = Depends(get_current_user_id)
) -> bool:
    """Enforces active 4-digit PIN unlock session for SnapTale+ private chats."""
    if not x_snapplus_session or not verify_snapplus_session_token(x_snapplus_session, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SnapTale+ private chat is locked. Please enter your 4-digit PIN."
        )
    return True