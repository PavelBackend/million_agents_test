import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

_priority_enum = sa.Enum("low", "medium", "high", "critical", name="task_priority")
_status_enum = sa.Enum("created", "in_progress", "review", "done", "cancelled", name="task_status")
_role_enum = sa.Enum("owner", "member", "viewer", name="member_role")


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_projects_owner", "projects", ["owner_id"])

    op.create_table(
        "project_members",
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", _role_enum, nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_project_members_user", "project_members", ["user_id"])

    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("priority", _priority_enum, nullable=False, server_default="medium"),
        sa.Column("status", _status_enum, nullable=False, server_default="created"),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assignee_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_tasks_project", "tasks", ["project_id"])
    op.create_index("idx_tasks_assignee", "tasks", ["assignee_id"])
    op.create_index("idx_tasks_author", "tasks", ["author_id"])
    op.create_index("idx_tasks_project_status", "tasks", ["project_id", "status"])

    op.create_table(
        "task_status_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("changed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum("created", "in_progress", "review", "done", "cancelled", name="task_status", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "to_status",
            sa.Enum("created", "in_progress", "review", "done", "cancelled", name="task_status", create_type=False),
            nullable=False,
        ),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("comment", sa.Text, nullable=True),
        sa.CheckConstraint("from_status <> to_status", name="chk_status_different"),
    )
    op.create_index("idx_status_history_task", "task_status_history", ["task_id"])
    op.create_index("idx_status_history_time", "task_status_history", [sa.text("changed_at DESC")])


def downgrade() -> None:
    op.drop_table("task_status_history")
    op.drop_table("tasks")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("users")

    _role_enum.drop(op.get_bind(), checkfirst=True)
    _status_enum.drop(op.get_bind(), checkfirst=True)
    _priority_enum.drop(op.get_bind(), checkfirst=True)
