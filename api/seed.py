from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import settings

URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)


async def seed() -> None:
    engine = create_async_engine(URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        alice_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        bob_id   = uuid.UUID("00000000-0000-0000-0000-000000000002")
        carol_id = uuid.UUID("00000000-0000-0000-0000-000000000003")

        await session.execute(text("""
            INSERT INTO users (id, email, name) VALUES
              (:alice_id, 'alice@example.com', 'Alice'),
              (:bob_id,   'bob@example.com',   'Bob'),
              (:carol_id, 'carol@example.com', 'Carol')
            ON CONFLICT DO NOTHING
        """), {"alice_id": alice_id, "bob_id": bob_id, "carol_id": carol_id})

        proj1_id = uuid.UUID("00000000-0000-0000-0001-000000000001")
        proj2_id = uuid.UUID("00000000-0000-0000-0001-000000000002")

        await session.execute(text("""
            INSERT INTO projects (id, name, description, owner_id) VALUES
              (:p1, 'Backend Platform', 'Core API services', :alice_id),
              (:p2, 'Mobile App',       'iOS & Android',    :bob_id)
            ON CONFLICT DO NOTHING
        """), {"p1": proj1_id, "p2": proj2_id, "alice_id": alice_id, "bob_id": bob_id})

        await session.execute(text("""
            INSERT INTO project_members (project_id, user_id, role) VALUES
              (:p1, :alice_id, 'owner'),
              (:p1, :bob_id,   'member'),
              (:p1, :carol_id, 'viewer'),
              (:p2, :bob_id,   'owner'),
              (:p2, :alice_id, 'member')
            ON CONFLICT DO NOTHING
        """), {"p1": proj1_id, "p2": proj2_id,
               "alice_id": alice_id, "bob_id": bob_id, "carol_id": carol_id})

        tasks = [
            dict(id=uuid.UUID("00000000-0000-0000-0002-000000000001"),
                 project_id=proj1_id, title="Set up CI/CD pipeline",
                 description="Configure GitHub Actions for tests and deployment",
                 priority="critical", status="in_progress",
                 author_id=alice_id, assignee_id=bob_id),
            dict(id=uuid.UUID("00000000-0000-0000-0002-000000000002"),
                 project_id=proj1_id, title="Design database schema",
                 description=None, priority="high", status="done",
                 author_id=alice_id, assignee_id=alice_id),
            dict(id=uuid.UUID("00000000-0000-0000-0002-000000000003"),
                 project_id=proj1_id, title="Write API documentation",
                 description="Swagger + README", priority="medium", status="created",
                 author_id=bob_id, assignee_id=carol_id),
            dict(id=uuid.UUID("00000000-0000-0000-0002-000000000004"),
                 project_id=proj1_id, title="Fix auth token expiry bug",
                 description=None, priority="high", status="review",
                 author_id=alice_id, assignee_id=bob_id),
            dict(id=uuid.UUID("00000000-0000-0000-0002-000000000005"),
                 project_id=proj2_id, title="Implement push notifications",
                 description="FCM integration", priority="medium", status="created",
                 author_id=bob_id, assignee_id=None),
            dict(id=uuid.UUID("00000000-0000-0000-0002-000000000006"),
                 project_id=proj2_id, title="Dark mode UI",
                 description=None, priority="low", status="cancelled",
                 author_id=bob_id, assignee_id=carol_id),
        ]

        await session.execute(text("""
            INSERT INTO tasks (id, project_id, title, description, priority, status, author_id, assignee_id)
            VALUES (:id, :project_id, :title, :description, :priority, :status, :author_id, :assignee_id)
            ON CONFLICT DO NOTHING
        """), tasks)

        history = [
            dict(task_id=uuid.UUID("00000000-0000-0000-0002-000000000002"),
                 changed_by=alice_id, from_status="created",     to_status="in_progress", comment=None),
            dict(task_id=uuid.UUID("00000000-0000-0000-0002-000000000002"),
                 changed_by=alice_id, from_status="in_progress", to_status="review",      comment="Looks good"),
            dict(task_id=uuid.UUID("00000000-0000-0000-0002-000000000002"),
                 changed_by=alice_id, from_status="review",      to_status="done",        comment="Approved"),
            dict(task_id=uuid.UUID("00000000-0000-0000-0002-000000000001"),
                 changed_by=alice_id, from_status="created",     to_status="in_progress", comment="Starting"),
            dict(task_id=uuid.UUID("00000000-0000-0000-0002-000000000004"),
                 changed_by=bob_id,   from_status="created",     to_status="in_progress", comment=None),
            dict(task_id=uuid.UUID("00000000-0000-0000-0002-000000000004"),
                 changed_by=bob_id,   from_status="in_progress", to_status="review",      comment="PR raised"),
            dict(task_id=uuid.UUID("00000000-0000-0000-0002-000000000006"),
                 changed_by=bob_id,   from_status="created",     to_status="cancelled",   comment="Out of scope"),
        ]

        await session.execute(text("""
            INSERT INTO task_status_history (task_id, changed_by, from_status, to_status, comment)
            VALUES (:task_id, :changed_by, :from_status, :to_status, :comment)
        """), history)

        await session.commit()

    await engine.dispose()

    print("Seed complete:")
    print("  Users   : alice, bob, carol")
    print("  Projects: Backend Platform, Mobile App")
    print("  Tasks   : 6 tasks across both projects")


if __name__ == "__main__":
    asyncio.run(seed())
