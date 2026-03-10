from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from api.internal.orm_models.dao import TaskStatus
from api.internal.services.tasks import TaskService


def _make_service(repo_mock: MagicMock) -> TaskService:
    service = TaskService()
    service._repo = repo_mock
    return service


def _make_task(status: TaskStatus) -> MagicMock:
    task = MagicMock()
    task.status = status
    task.id = uuid.uuid4()
    return task


async def test_get_task_raises_404_when_not_found():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.get_task(MagicMock(), uuid.uuid4())

    assert exc.value.status_code == 404


async def test_get_task_returns_task_when_found():
    task = _make_task(TaskStatus.created)
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    service = _make_service(repo)

    result = await service.get_task(MagicMock(), task.id)

    assert result is task


@pytest.mark.parametrize("current,target", [
    (TaskStatus.created,   TaskStatus.review),
    (TaskStatus.created,   TaskStatus.done),
    (TaskStatus.review,    TaskStatus.created),
    (TaskStatus.done,      TaskStatus.in_progress),
    (TaskStatus.cancelled, TaskStatus.created),
])
async def test_change_status_raises_400_for_invalid_transition(current, target):
    task = _make_task(current)
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.change_status(MagicMock(), task.id, target, uuid.uuid4(), None)

    assert exc.value.status_code == 400


@pytest.mark.parametrize("terminal", [TaskStatus.done, TaskStatus.cancelled])
async def test_change_status_400_message_mentions_terminal(terminal):
    task = _make_task(terminal)
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.change_status(MagicMock(), task.id, TaskStatus.created, uuid.uuid4(), None)

    assert "терминальным" in exc.value.detail.lower()


@pytest.mark.parametrize("current,target", [
    (TaskStatus.created,     TaskStatus.in_progress),
    (TaskStatus.created,     TaskStatus.cancelled),
    (TaskStatus.in_progress, TaskStatus.review),
    (TaskStatus.in_progress, TaskStatus.cancelled),
    (TaskStatus.in_progress, TaskStatus.created),
    (TaskStatus.review,      TaskStatus.done),
    (TaskStatus.review,      TaskStatus.in_progress),
    (TaskStatus.review,      TaskStatus.cancelled),
])
async def test_change_status_delegates_to_repo_for_valid_transition(current, target):
    task = _make_task(current)
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    repo.update_status = AsyncMock(return_value=task)
    service = _make_service(repo)

    changed_by = uuid.uuid4()
    await service.change_status(MagicMock(), task.id, target, changed_by, "комментарий")

    repo.update_status.assert_awaited_once()
    _, args = repo.update_status.call_args
    assert args["new_status"] == target
    assert args["changed_by"] == changed_by
    assert args["comment"] == "комментарий"


async def test_get_history_raises_404_when_task_missing():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    service = _make_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.get_history(MagicMock(), uuid.uuid4())

    assert exc.value.status_code == 404


async def test_get_history_returns_list_when_task_exists():
    task = _make_task(TaskStatus.in_progress)
    history = [MagicMock(), MagicMock()]
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=task)
    repo.get_history = AsyncMock(return_value=history)
    service = _make_service(repo)

    result = await service.get_history(MagicMock(), task.id)

    assert result == history
