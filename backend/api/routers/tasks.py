"""
Task Router

Play의 Task(ToDoList) 관리 API
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.task import TaskPriority, TaskStatus
from backend.database.repositories.play_record import play_record_repo
from backend.database.repositories.task import task_repo
from backend.database.session import get_db
from backend.services.task_converter import task_converter

router = APIRouter()


# ============================================================
# Pydantic Models
# ============================================================


class TaskCreate(BaseModel):
    """Task 생성 요청"""

    play_id: str
    title: str
    description: str | None = None
    priority: str = TaskPriority.P1.value
    assignee: str | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    """Task 업데이트 요청"""

    title: str | None = None
    description: str | None = None
    priority: str | None = None
    assignee: str | None = None
    due_date: date | None = None
    status: str | None = None
    blocker_note: str | None = None


class TaskResponse(BaseModel):
    """Task 응답"""

    task_id: str
    play_id: str
    title: str
    description: str | None = None
    status: str
    priority: str
    assignee: str | None = None
    due_date: date | None = None
    completed_at: str | None = None
    order_index: int = 0
    source_text: str | None = None
    blocker_note: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Task 목록 응답"""

    items: list[TaskResponse]
    total: int


class TaskStatsResponse(BaseModel):
    """Task 통계 응답"""

    total: int
    completed: int
    in_progress: int
    pending: int
    blocked: int
    completion_rate: float


class GenerateTasksRequest(BaseModel):
    """Task 자동 생성 요청"""

    play_id: str
    include_goal_tasks: bool = False
    due_date: date | None = None


class GenerateTasksResponse(BaseModel):
    """Task 자동 생성 응답"""

    play_id: str
    tasks_created: int
    tasks: list[TaskResponse]


# ============================================================
# Helper Functions
# ============================================================


def _task_to_response(task) -> TaskResponse:
    """Task 모델을 응답 형식으로 변환"""
    return TaskResponse(
        task_id=task.task_id,
        play_id=task.play_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assignee=task.assignee,
        due_date=task.due_date,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        order_index=task.order_index,
        source_text=task.source_text,
        blocker_note=task.blocker_note,
        created_at=task.created_at.isoformat() if task.created_at else None,
        updated_at=task.updated_at.isoformat() if task.updated_at else None,
    )


# ============================================================
# Endpoints
# ============================================================


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    play_id: Annotated[str | None, Query(description="Play ID 필터")] = None,
    status: Annotated[str | None, Query(description="상태 필터 (pending, in_progress, completed, blocked)")] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Task 목록 조회

    - play_id: 특정 Play의 Task만 조회
    - status: 상태별 필터링
    """
    if play_id:
        tasks = await task_repo.get_by_play_id(db, play_id, status)
    elif status:
        if status in [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]:
            tasks = await task_repo.get_pending_tasks(db)
        elif status == TaskStatus.BLOCKED.value:
            tasks = await task_repo.get_blocked_tasks(db)
        else:
            tasks = await task_repo.get_multi(db, limit=100)
    else:
        tasks = await task_repo.get_multi(db, limit=100)

    return TaskListResponse(
        items=[_task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.get("/pending", response_model=TaskListResponse)
async def list_pending_tasks(
    play_id: Annotated[str | None, Query(description="Play ID 필터")] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """미완료 Task 목록 조회 (pending + in_progress)"""
    tasks = await task_repo.get_pending_tasks(db, play_id, limit)
    return TaskListResponse(
        items=[_task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.get("/overdue", response_model=TaskListResponse)
async def list_overdue_tasks(db: AsyncSession = Depends(get_db)):
    """기한 초과 Task 목록 조회"""
    tasks = await task_repo.get_overdue_tasks(db)
    return TaskListResponse(
        items=[_task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.get("/blocked", response_model=TaskListResponse)
async def list_blocked_tasks(db: AsyncSession = Depends(get_db)):
    """블로킹된 Task 목록 조회"""
    tasks = await task_repo.get_blocked_tasks(db)
    return TaskListResponse(
        items=[_task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.post("", response_model=TaskResponse)
async def create_task(
    request: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    새 Task 생성

    Play에 연결된 새로운 Task를 생성합니다.
    """
    # Play 존재 확인
    play = await play_record_repo.get_by_id(db, request.play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play를 찾을 수 없습니다.")

    # Task ID 생성
    task_id = await task_repo.get_next_task_id(db)

    # Task 생성
    task = await task_repo.create_task(
        db=db,
        task_id=task_id,
        play_id=request.play_id,
        title=request.title,
        description=request.description,
        priority=request.priority,
        assignee=request.assignee,
        due_date=request.due_date,
    )

    return _task_to_response(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Task 상세 조회"""
    task = await task_repo.get_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task를 찾을 수 없습니다.")

    return _task_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    request: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Task 업데이트"""
    task = await task_repo.get_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task를 찾을 수 없습니다.")

    # 업데이트할 필드 적용
    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(task, field):
            setattr(task, field, value)

    await db.flush()
    await db.refresh(task)

    return _task_to_response(task)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Task 완료 처리"""
    task = await task_repo.complete_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task를 찾을 수 없습니다.")

    return _task_to_response(task)


@router.post("/{task_id}/block", response_model=TaskResponse)
async def block_task(
    task_id: str,
    blocker_note: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Task 블로킹 처리"""
    task = await task_repo.update_status(db, task_id, TaskStatus.BLOCKED.value, blocker_note)
    if not task:
        raise HTTPException(status_code=404, detail="Task를 찾을 수 없습니다.")

    return _task_to_response(task)


@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Task 시작 (in_progress로 변경)"""
    task = await task_repo.update_status(db, task_id, TaskStatus.IN_PROGRESS.value)
    if not task:
        raise HTTPException(status_code=404, detail="Task를 찾을 수 없습니다.")

    return _task_to_response(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Task 삭제"""
    task = await task_repo.get_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task를 찾을 수 없습니다.")

    await db.delete(task)
    await db.flush()

    return {"status": "deleted", "task_id": task_id}


@router.post("/generate", response_model=GenerateTasksResponse)
async def generate_tasks(
    request: GenerateTasksRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Play에서 Task 자동 생성

    Play의 next_action을 파싱하여 Task 목록을 자동 생성합니다.
    기존 Task는 삭제되고 새로 생성됩니다.
    """
    # Play 조회
    play = await play_record_repo.get_by_id(db, request.play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play를 찾을 수 없습니다.")

    # Task 생성
    tasks = await task_converter.create_tasks_for_play(
        db=db,
        play=play,
        include_goal_tasks=request.include_goal_tasks,
        due_date=request.due_date,
    )

    return GenerateTasksResponse(
        play_id=request.play_id,
        tasks_created=len(tasks),
        tasks=[_task_to_response(t) for t in tasks],
    )


@router.get("/stats/{play_id}", response_model=TaskStatsResponse)
async def get_task_stats(
    play_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Play별 Task 통계 조회"""
    # Play 존재 확인
    play = await play_record_repo.get_by_id(db, play_id)
    if not play:
        raise HTTPException(status_code=404, detail="Play를 찾을 수 없습니다.")

    stats = await task_repo.get_stats_by_play(db, play_id)
    return TaskStatsResponse(**stats)
