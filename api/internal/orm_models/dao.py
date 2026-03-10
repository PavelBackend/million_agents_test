from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskStatus(str, enum.Enum):
    created = "created"
    in_progress = "in_progress"
    review = "review"
    done = "done"
    cancelled = "cancelled"


class MemberRole(str, enum.Enum):
    owner = "owner"
    member = "member"
    viewer = "viewer"


VALID_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.created: [TaskStatus.in_progress, TaskStatus.cancelled],
    TaskStatus.in_progress: [TaskStatus.review, TaskStatus.cancelled, TaskStatus.created],
    TaskStatus.review: [TaskStatus.done, TaskStatus.in_progress, TaskStatus.cancelled],
    TaskStatus.done: [],
    TaskStatus.cancelled: [],
}

PRIORITY_ORDER = {
    TaskPriority.low: 1,
    TaskPriority.medium: 2,
    TaskPriority.high: 3,
    TaskPriority.critical: 4,
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owned_projects: Mapped[list[Project]] = relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")
    memberships: Mapped[list[ProjectMember]] = relationship("ProjectMember", back_populates="user")
    authored_tasks: Mapped[list[Task]] = relationship("Task", back_populates="author", foreign_keys="Task.author_id")
    assigned_tasks: Mapped[list[Task]] = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    status_changes: Mapped[list[TaskStatusHistory]] = relationship("TaskStatusHistory", back_populates="changed_by_user")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner: Mapped[User] = relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    members: Mapped[list[ProjectMember]] = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list[Task]] = relationship("Task", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_projects_owner", "owner_id"),)


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[MemberRole] = mapped_column(Enum(MemberRole, name="member_role"), nullable=False, default=MemberRole.member)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship("Project", back_populates="members")
    user: Mapped[User] = relationship("User", back_populates="memberships")

    __table_args__ = (Index("idx_project_members_user", "user_id"),)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority, name="task_priority"), nullable=False, default=TaskPriority.medium)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), nullable=False, default=TaskStatus.created)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship("Project", back_populates="tasks")
    author: Mapped[User] = relationship("User", back_populates="authored_tasks", foreign_keys=[author_id])
    assignee: Mapped[User | None] = relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    history: Mapped[list[TaskStatusHistory]] = relationship("TaskStatusHistory", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tasks_project", "project_id"),
        Index("idx_tasks_assignee", "assignee_id"),
        Index("idx_tasks_author", "author_id"),
        Index("idx_tasks_project_status", "project_id", "status"),
    )


class TaskStatusHistory(Base):
    __tablename__ = "task_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    from_status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), nullable=False)
    to_status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[Task] = relationship("Task", back_populates="history")
    changed_by_user: Mapped[User] = relationship("User", back_populates="status_changes")

    __table_args__ = (
        CheckConstraint("from_status <> to_status", name="chk_status_different"),
        Index("idx_status_history_task", "task_id"),
        Index("idx_status_history_time", "changed_at"),
    )
