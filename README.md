# Million Agents — Task Management API

REST API для управления задачами с поддержкой проектов, участников и истории изменений статусов.

## Стек

- **FastAPI** — веб-фреймворк
- **SQLAlchemy (async)** + **asyncpg** — ORM и драйвер PostgreSQL
- **Alembic** — миграции
- **Pydantic v2** — валидация и схемы
- **Docker Compose** — контейнеризация

### Запуск приложения

```bash
docker compose -f deploy/docker-compose.yml --env-file .env up --build -d
```

При старте автоматически выполняются:
1. `alembic upgrade head` — применяются миграции
2. `python -m api.seed` — заполнение БД тестовыми данными (идемпотентно)
3. `uvicorn` — запуск сервера

Приложение: [http://localhost:8000](http://localhost:8000)  
Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### Остановка

```bash
docker compose -f deploy/docker-compose.yml down
```

### Логи

```bash
docker logs million_agents_service -f
```

## Seed-данные

При запуске контейнера БД автоматически заполняется тестовыми данными:

| Что        | Детали                                               |
|------------|------------------------------------------------------|
| 3 юзера    | alice, bob, carol                                    |
| 2 проекта  | Backend Platform (owner: alice), Mobile App (owner: bob) |
| 6 задач    | Различные статусы и приоритеты в обоих проектах      |

UUID пользователей и проектов фиксированы (для удобства запросов к API):

```
alice   → 00000000-0000-0000-0000-000000000001
bob     → 00000000-0000-0000-0000-000000000002
carol   → 00000000-0000-0000-0000-000000000003

proj_1  → 00000000-0000-0000-0001-000000000001  (Backend Platform)
proj_2  → 00000000-0000-0000-0001-000000000002  (Mobile App)
```

## API Endpoints

| Метод   | URL                        | Описание                           |
|---------|----------------------------|------------------------------------|
| `POST`  | `/tasks/`                  | Создать задачу                     |
| `GET`   | `/tasks/`                  | Список задач (фильтры + пагинация) |
| `GET`   | `/tasks/{task_id}`         | Получить задачу                    |
| `PATCH` | `/tasks/{task_id}/status`  | Сменить статус                     |
| `GET`   | `/tasks/{task_id}/history` | История изменений статуса          |

## Тесты

Для запуска тестов выполните:
```bash
docker exec -it -f million_agents_service -c "poetry run pytest"
```

Тесты используют отдельную базу `million_agents_test` (создаётся автоматически).  
После каждого теста все таблицы очищаются — тесты полностью изолированы.
