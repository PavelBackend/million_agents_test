from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..orm_models.dao import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority = TaskPriority.medium
    author_id: uuid.UUID
    assignee_id: uuid.UUID | None = None


class TaskStatusUpdate(BaseModel):
    new_status: TaskStatus
    changed_by: uuid.UUID
    comment: str | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    priority: TaskPriority
    status: TaskStatus
    author_id: uuid.UUID
    assignee_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskHistoryResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    changed_by: uuid.UUID
    from_status: TaskStatus
    to_status: TaskStatus
    changed_at: datetime
    comment: str | None

    model_config = {"from_attributes": True}


class PaginatedTaskResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
    pages: int
