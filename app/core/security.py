"""Password hashing and JWT authentication helpers."""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..core.config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/login/")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password) -> bool:
    """Compare a supplied password with its stored hash."""
    return pwd_context.verify(plain_password + settings.SALT, hashed_password)


def get_password_hash(password) -> Any:
    """Hash a password after applying the configured pepper."""
    return pwd_context.hash(password + settings.SALT)


def create_access_token(data: dict) -> str:
    """Create a signed JWT with the configured expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Decode a bearer token or raise an authentication error."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_user_by_token(payload: dict = Depends(decode_access_token)) -> str:
    """Extract the username from a validated token payload."""
    return payload.get("sub")
