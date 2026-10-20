import time
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import HTTPException, status
from app.config import settings

logger = logging.getLogger("investigation.security")

# Initialize Argon2id password hasher with high security settings
# Type.ID = Argon2id (resistant against both GPU side-channel and tradeoff attacks)
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32
)

def hash_password(plain_password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    if not plain_password or len(plain_password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    return _hasher.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against an Argon2id hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception as e:
        logger.error(f"Unexpected error during password verification: {e}")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a cryptographically signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decodes and validates a signed JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

# In-memory brute-force rate limiter
class LoginRateLimiter:
    """Tracks failed login attempts by key (user_id / IP) to mitigate brute force attacks."""
    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # key -> (attempt_count, lock_until_timestamp)
        self.attempts: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    def check_rate_limit(self, key: str):
        normalized_key = key.strip().lower()
        now = time.time()
        count, lock_until = self.attempts[normalized_key]
        if lock_until > now:
            remaining_seconds = int(lock_until - now)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Account temporarily locked. Please try again in {remaining_seconds} seconds."
            )

    def record_failure(self, key: str):
        normalized_key = key.strip().lower()
        now = time.time()
        count, lock_until = self.attempts[normalized_key]
        
        # If previous active lock expired, reset count
        if lock_until > 0 and lock_until < now:
            count = 0
            lock_until = 0.0
            
        new_count = count + 1
        if new_count >= self.max_attempts:
            new_lock = now + self.window_seconds
            self.attempts[normalized_key] = (new_count, new_lock)
            logger.warning(f"Brute-force lockout triggered for key '{normalized_key}' for {self.window_seconds}s.")
        else:
            self.attempts[normalized_key] = (new_count, 0.0)

    def record_success(self, key: str):
        normalized_key = key.strip().lower()
        if normalized_key in self.attempts:
            del self.attempts[normalized_key]

login_rate_limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)
