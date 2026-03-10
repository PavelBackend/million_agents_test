from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..orm_models.dao import (
    VALID_TRANSITIONS,
    Task,
    TaskPriority,
    TaskStatus,
    TaskStatusHistory,
)
from ..repository.tasks import TaskRepository


class TaskService:
    def __init__(self):
        self._repo = TaskRepository()

    async def create_task(
        self,
        session: AsyncSession,
        *,
        project_id: uuid.UUID,
        title: str,
        description: str | None,
        priority: TaskPriority,
        author_id: uuid.UUID,
        assignee_id: uuid.UUID | None,
    ) -> Task:
        return await self._repo.create(
            session,
            project_id=project_id,
            title=title,
            description=description,
            priority=priority,
            author_id=author_id,
            assignee_id=assignee_id,
        )

    async def get_task(self, session: AsyncSession, task_id: uuid.UUID) -> Task:
        task = await self._repo.get_by_id(session, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
        return task

    async def list_tasks(
        self,
        session: AsyncSession,
        *,
        project_id: uuid.UUID | None,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: uuid.UUID | None,
        sort_by: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Task], int]:
        return await self._repo.list(
            session,
            project_id=project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )

    async def change_status(
        self,
        session: AsyncSession,
        task_id: uuid.UUID,
        new_status: TaskStatus,
        changed_by: uuid.UUID,
        comment: str | None,
    ) -> Task:
        task = await self.get_task(session, task_id)

        allowed = VALID_TRANSITIONS[task.status]
        if new_status not in allowed:
            if not allowed:
                detail = f"Статус '{task.status.value}' является терминальным — дальнейшие переходы невозможны."
            else:
                allowed_str = ", ".join(s.value for s in allowed)
                detail = (
                    f"Недопустимый переход '{task.status.value}' → '{new_status.value}'. "
                    f"Разрешённые переходы: {allowed_str}."
                )
            raise HTTPException(status_code=400, detail=detail)

        return await self._repo.update_status(
            session,
            task,
            new_status=new_status,
            changed_by=changed_by,
            comment=comment,
        )

    async def get_history(self, session: AsyncSession, task_id: uuid.UUID) -> list[TaskStatusHistory]:
        await self.get_task(session, task_id)
        return await self._repo.get_history(session, task_id)
