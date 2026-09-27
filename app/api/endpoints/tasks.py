"""Task and WebSocket endpoints."""

from typing import List, Set

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.orm import Session

from ..models.task import TaskCreate, TaskUpdate, TaskResponse
from ...core.security import decode_access_token, get_user_by_token
from ...db.database import get_db
from ...db.db_structure import Task, User

router = APIRouter()


class ConnectionManager:
    """Track active sockets and deliver messages without retaining stale clients."""

    def __init__(self):
        """Initialize the active socket registry."""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a socket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a socket if it is still registered."""
        self.active_connections.discard(websocket)

    async def broadcast(self, message: str):
        """Send a message to active sockets and discard unreachable clients."""
        disconnected: Set[WebSocket] = set()
        for connection in tuple(self.active_connections):
            try:
                await connection.send_text(message)
            except (RuntimeError, WebSocketDisconnect):
                disconnected.add(connection)
        self.active_connections.difference_update(disconnected)


connection_manager = ConnectionManager()


def get_current_user(
    db: Session = Depends(get_db),
    username: str = Depends(get_user_by_token),
) -> User:
    """Resolve the authenticated user or reject tokens for deleted accounts."""
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_owned_task_or_404(db: Session, task_id: int, owner_id: int) -> Task:
    """Return a task only when it belongs to the requesting user."""
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == owner_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.websocket("/ws/tasks/{client_id}")
async def websocket_endpoint(client_id: int, websocket: WebSocket):
    """Accept a socket and broadcast messages until its client disconnects."""
    authorization = websocket.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        decode_access_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await connection_manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            await connection_manager.broadcast(
                f"Client with {client_id} wrote {message}!"
            )
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


@router.post("/tasks/", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a task for the authenticated user."""
    db_task = Task(**task.model_dump(), owner_id=current_user.id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    background_tasks.add_task(
        connection_manager.broadcast,
        f"New task created: {db_task.title}",
    )
    return db_task


@router.get("/tasks/", response_model=List[TaskResponse])
def read_tasks(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List only the authenticated user's tasks."""
    tasks = (
        db.query(Task)
        .filter(Task.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get one of the authenticated user's tasks."""
    return get_owned_task_or_404(db, task_id, current_user.id)


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace task fields and notify connected clients."""
    db_task = get_owned_task_or_404(db, task_id, current_user.id)
    for key, value in task_update.model_dump().items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    background_tasks.add_task(
        connection_manager.broadcast,
        f"Task {db_task.id} updated",
    )
    return db_task


@router.delete("/tasks/{task_id}", response_model=TaskResponse)
def delete_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one of the authenticated user's tasks."""
    task = get_owned_task_or_404(db, task_id, current_user.id)
    db.delete(task)
    db.commit()
    background_tasks.add_task(
        connection_manager.broadcast,
        f"Task {task.id} deleted",
    )
    return task
