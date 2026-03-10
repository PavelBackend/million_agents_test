from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.internal.orm_models.dao import (
    MemberRole,
    Project,
    ProjectMember,
    Task,
    TaskPriority,
    TaskStatus,
    TaskStatusHistory,
    User,
)


@pytest_asyncio.fixture
async def seed(db_session: AsyncSession):
    alice = User(email="alice@example.com", name="Alice")
    bob = User(email="bob@example.com", name="Bob")
    db_session.add_all([alice, bob])
    await db_session.flush()

    project = Project(name="Demo Project", owner_id=alice.id)
    db_session.add(project)
    await db_session.flush()

    db_session.add(ProjectMember(project_id=project.id, user_id=alice.id, role=MemberRole.owner))
    await db_session.flush()

    task_created = Task(
        project_id=project.id,
        title="Task Alpha",
        priority=TaskPriority.high,
        status=TaskStatus.created,
        author_id=alice.id,
        assignee_id=bob.id,
    )
    task_in_progress = Task(
        project_id=project.id,
        title="Task Beta",
        priority=TaskPriority.low,
        status=TaskStatus.in_progress,
        author_id=alice.id,
    )
    task_done = Task(
        project_id=project.id,
        title="Task Gamma",
        priority=TaskPriority.medium,
        status=TaskStatus.done,
        author_id=alice.id,
        assignee_id=bob.id,
    )
    db_session.add_all([task_created, task_in_progress, task_done])
    await db_session.flush()

    db_session.add(
        TaskStatusHistory(
            task_id=task_done.id,
            changed_by=alice.id,
            from_status=TaskStatus.created,
            to_status=TaskStatus.in_progress,
        )
    )
    db_session.add(
        TaskStatusHistory(
            task_id=task_done.id,
            changed_by=alice.id,
            from_status=TaskStatus.in_progress,
            to_status=TaskStatus.review,
        )
    )
    db_session.add(
        TaskStatusHistory(
            task_id=task_done.id,
            changed_by=alice.id,
            from_status=TaskStatus.review,
            to_status=TaskStatus.done,
        )
    )

    await db_session.commit()
    return {
        "alice": alice,
        "bob": bob,
        "project": project,
        "task_created": task_created,
        "task_in_progress": task_in_progress,
        "task_done": task_done,
    }


class TestCreateTask:
    async def test_creates_task_and_returns_201(self, client: AsyncClient, seed):
        resp = await client.post(
            "/tasks/",
            json={
                "project_id": str(seed["project"].id),
                "title": "New Task",
                "priority": "high",
                "author_id": str(seed["alice"].id),
                "assignee_id": str(seed["bob"].id),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Task"
        assert data["priority"] == "high"
        assert data["status"] == "created"
        assert data["author_id"] == str(seed["alice"].id)
        assert data["assignee_id"] == str(seed["bob"].id)

    async def test_creates_task_without_assignee(self, client: AsyncClient, seed):
        resp = await client.post(
            "/tasks/",
            json={
                "project_id": str(seed["project"].id),
                "title": "Unassigned Task",
                "author_id": str(seed["alice"].id),
            },
        )
        assert resp.status_code == 201
        assert resp.json()["assignee_id"] is None

    async def test_default_priority_is_medium(self, client: AsyncClient, seed):
        resp = await client.post(
            "/tasks/",
            json={
                "project_id": str(seed["project"].id),
                "title": "Default Priority Task",
                "author_id": str(seed["alice"].id),
            },
        )
        assert resp.status_code == 201
        assert resp.json()["priority"] == "medium"

    async def test_missing_title_returns_422(self, client: AsyncClient, seed):
        resp = await client.post(
            "/tasks/",
            json={
                "project_id": str(seed["project"].id),
                "author_id": str(seed["alice"].id),
            },
        )
        assert resp.status_code == 422

    async def test_missing_author_returns_422(self, client: AsyncClient, seed):
        resp = await client.post(
            "/tasks/",
            json={
                "project_id": str(seed["project"].id),
                "title": "No Author",
            },
        )
        assert resp.status_code == 422

    async def test_invalid_priority_returns_422(self, client: AsyncClient, seed):
        resp = await client.post(
            "/tasks/",
            json={
                "project_id": str(seed["project"].id),
                "title": "Bad Priority",
                "author_id": str(seed["alice"].id),
                "priority": "urgent",
            },
        )
        assert resp.status_code == 422


class TestListTasks:
    async def test_returns_all_tasks_paginated(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_filter_by_status(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/", params={"status": "created"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "created"

    async def test_filter_by_priority(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/", params={"priority": "high"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    async def test_filter_by_assignee(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/", params={"assignee_id": str(seed["bob"].id)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["assignee_id"] == str(seed["bob"].id)

    async def test_filter_by_project(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/", params={"project_id": str(seed["project"].id)})
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

    async def test_filter_unknown_project_returns_empty(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/", params={"project_id": str(uuid.uuid4())})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_sort_by_priority_descending(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/", params={"sort_by": "priority"})
        assert resp.status_code == 200
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        priorities = [order[i["priority"]] for i in resp.json()["items"]]
        assert priorities == sorted(priorities, reverse=True)

    async def test_pagination_page_size(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/", params={"page": 1, "page_size": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["pages"] == 2

    async def test_second_page_has_remaining_item(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/", params={"page": 2, "page_size": 2})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    async def test_invalid_page_size_returns_422(self, client: AsyncClient, seed):
        resp = await client.get("/tasks/", params={"page_size": 0})
        assert resp.status_code == 422


class TestGetTask:
    async def test_returns_task_with_correct_fields(self, client: AsyncClient, seed):
        task_id = str(seed["task_created"].id)
        resp = await client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == task_id
        assert data["title"] == "Task Alpha"
        assert data["status"] == "created"
        assert data["priority"] == "high"

    async def test_returns_404_for_nonexistent_id(self, client: AsyncClient, seed):
        resp = await client.get(f"/tasks/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestChangeTaskStatus:
    async def test_valid_transition_returns_200_and_new_status(self, client: AsyncClient, seed):
        task_id = str(seed["task_created"].id)
        resp = await client.patch(
            f"/tasks/{task_id}/status",
            json={
                "new_status": "in_progress",
                "changed_by": str(seed["alice"].id),
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    async def test_valid_transition_with_comment(self, client: AsyncClient, seed):
        task_id = str(seed["task_in_progress"].id)
        resp = await client.patch(
            f"/tasks/{task_id}/status",
            json={
                "new_status": "review",
                "changed_by": str(seed["alice"].id),
                "comment": "Готово к ревью",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "review"

    async def test_invalid_transition_returns_400(self, client: AsyncClient, seed):
        task_id = str(seed["task_created"].id)
        resp = await client.patch(
            f"/tasks/{task_id}/status",
            json={
                "new_status": "done",
                "changed_by": str(seed["alice"].id),
            },
        )
        assert resp.status_code == 400
        assert "Недопустимый переход" in resp.json()["detail"]

    async def test_terminal_status_returns_400_with_message(self, client: AsyncClient, seed):
        task_id = str(seed["task_done"].id)
        resp = await client.patch(
            f"/tasks/{task_id}/status",
            json={
                "new_status": "in_progress",
                "changed_by": str(seed["alice"].id),
            },
        )
        assert resp.status_code == 400
        assert "терминальным" in resp.json()["detail"].lower()

    async def test_nonexistent_task_returns_404(self, client: AsyncClient, seed):
        resp = await client.patch(
            f"/tasks/{uuid.uuid4()}/status",
            json={
                "new_status": "in_progress",
                "changed_by": str(seed["alice"].id),
            },
        )
        assert resp.status_code == 404

    async def test_missing_new_status_returns_422(self, client: AsyncClient, seed):
        task_id = str(seed["task_created"].id)
        resp = await client.patch(
            f"/tasks/{task_id}/status",
            json={
                "changed_by": str(seed["alice"].id),
            },
        )
        assert resp.status_code == 422


class TestGetTaskHistory:
    async def test_returns_history_in_chronological_order(self, client: AsyncClient, seed):
        task_id = str(seed["task_done"].id)
        resp = await client.get(f"/tasks/{task_id}/history")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) == 3
        assert entries[0]["from_status"] == "created"
        assert entries[0]["to_status"] == "in_progress"
        assert entries[-1]["to_status"] == "done"

    async def test_history_grows_after_status_change(self, client: AsyncClient, seed):
        task_id = str(seed["task_created"].id)

        await client.patch(
            f"/tasks/{task_id}/status",
            json={
                "new_status": "in_progress",
                "changed_by": str(seed["alice"].id),
                "comment": "Берём в работу",
            },
        )

        resp = await client.get(f"/tasks/{task_id}/history")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) == 1
        assert entries[0]["from_status"] == "created"
        assert entries[0]["to_status"] == "in_progress"
        assert entries[0]["comment"] == "Берём в работу"

    async def test_empty_history_for_new_task(self, client: AsyncClient, seed):
        task_id = str(seed["task_created"].id)
        resp = await client.get(f"/tasks/{task_id}/history")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_404_for_nonexistent_task(self, client: AsyncClient, seed):
        resp = await client.get(f"/tasks/{uuid.uuid4()}/history")
        assert resp.status_code == 404
