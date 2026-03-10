from __future__ import annotations

import math
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_async_session
from ..models.tasks import (
    PaginatedTaskResponse,
    TaskCreate,
    TaskHistoryResponse,
    TaskResponse,
    TaskStatusUpdate,
)
from ..orm_models.dao import TaskPriority, TaskStatus
from ..services.tasks import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service() -> TaskService:
    return TaskService()


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    session: AsyncSession = Depends(get_async_session),
    service: TaskService = Depends(get_task_service),
):
    return await service.create_task(
        session,
        project_id=body.project_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        author_id=body.author_id,
        assignee_id=body.assignee_id,
    )


@router.get("/", response_model=PaginatedTaskResponse)
async def list_tasks(
    project_id: uuid.UUID | None = Query(None),
    status: TaskStatus | None = Query(None),
    priority: TaskPriority | None = Query(None),
    assignee_id: uuid.UUID | None = Query(None),
    sort_by: Literal["created_at", "priority"] = Query("created_at"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    service: TaskService = Depends(get_task_service),
):
    items, total = await service.list_tasks(
        session,
        project_id=project_id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    pages = math.ceil(total / page_size) if total else 0
    return PaginatedTaskResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    service: TaskService = Depends(get_task_service),
):
    return await service.get_task(session, task_id)


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def change_task_status(
    task_id: uuid.UUID,
    body: TaskStatusUpdate,
    session: AsyncSession = Depends(get_async_session),
    service: TaskService = Depends(get_task_service),
):
    return await service.change_status(session, task_id, body.new_status, body.changed_by, body.comment)


@router.get("/{task_id}/history", response_model=list[TaskHistoryResponse])
async def get_task_history(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    service: TaskService = Depends(get_task_service),
):
    return await service.get_history(session, task_id)
