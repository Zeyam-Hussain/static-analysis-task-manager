"""Request and response schemas for task operations."""

from pydantic import BaseModel


class TaskCreate(BaseModel):
    """Fields required to create a task."""

    title: str
    description: str


class TaskUpdate(BaseModel):
    """Fields accepted when replacing a task."""

    title: str
    description: str
    completed: bool


class TaskResponse(BaseModel):
    """Public task representation returned by the API."""

    id: int
    title: str
    description: str
    completed: bool
