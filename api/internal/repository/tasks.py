from __future__ import annotations

import uuid

from sqlalchemy import String, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..orm_models.dao import PRIORITY_ORDER, Task, TaskPriority, TaskStatus, TaskStatusHistory


class TaskRepository:
    async def create(
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
        task = Task(
            project_id=project_id,
            title=title,
            description=description,
            priority=priority,
            author_id=author_id,
            assignee_id=assignee_id,
            status=TaskStatus.created,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task

    async def get_by_id(self, session: AsyncSession, task_id: uuid.UUID) -> Task | None:
        result = await session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        *,
        project_id: uuid.UUID | None = None,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: uuid.UUID | None = None,
        sort_by: str = "created_at",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]:
        query = select(Task)

        if project_id is not None:
            query = query.where(Task.project_id == project_id)
        if status is not None:
            query = query.where(Task.status == status)
        if priority is not None:
            query = query.where(Task.priority == priority)
        if assignee_id is not None:
            query = query.where(Task.assignee_id == assignee_id)

        total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

        if sort_by == "priority":
            priority_case = case(
                {p.value: order for p, order in PRIORITY_ORDER.items()},
                value=cast(Task.priority, String),
            )
            query = query.order_by(priority_case.desc(), Task.created_at.desc())
        else:
            query = query.order_by(Task.created_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        return list(result.scalars().all()), total

    async def update_status(
        self,
        session: AsyncSession,
        task: Task,
        new_status: TaskStatus,
        changed_by: uuid.UUID,
        comment: str | None,
    ) -> Task:
        history = TaskStatusHistory(
            task_id=task.id,
            changed_by=changed_by,
            from_status=task.status,
            to_status=new_status,
            comment=comment,
        )
        task.status = new_status
        session.add(history)
        await session.commit()
        await session.refresh(task)
        return task

    async def get_history(self, session: AsyncSession, task_id: uuid.UUID) -> list[TaskStatusHistory]:
        result = await session.execute(
            select(TaskStatusHistory)
            .where(TaskStatusHistory.task_id == task_id)
            .order_by(TaskStatusHistory.changed_at.asc())
        )
        return list(result.scalars().all())
