"""Request and response schemas for user operations."""

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Fields required to register an account."""

    username: str
    email: EmailStr = None
    password: str


class UserResponse(BaseModel):
    """Public profile fields returned by the API."""

    id: int
    username: str
    email: str
