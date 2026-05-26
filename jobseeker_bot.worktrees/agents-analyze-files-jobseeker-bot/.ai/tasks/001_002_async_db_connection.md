# TASK 001_002_async_db_connection
## Назначение: Инициализация асинхронного подключения к PostgreSQL через SQLAlchemy 2.0.
## Входные данные: Готовая структура проекта, настроенный `.env`.
## Что сделать: 
1. Написать `app/core/db.py`: настройку `asyncpg` пула соединений и `AsyncEngine`.
2. Реализовать `get_async_session` factory для зависимости DI (Dependency Injection).
3. Добавить скрипт миграции Alembic или `alembic init`.
## Ожидаемый результат: Модуль `db.py` с фабрикой сессий, готовый к подключению к PostgreSQL.
## Как протестировать: Скрипт `test_db_conn.py`: импортирует `get_async_session`, открывает сессию, выполняет `SELECT 1`, закрывает сессию без ошибок `asyncio`.