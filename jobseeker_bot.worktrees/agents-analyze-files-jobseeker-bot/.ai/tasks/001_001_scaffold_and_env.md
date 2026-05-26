# TASK 001_001_scaffold_and_env
## Назначение: Создание базовой структуры проекта, настройка переменных окружения и зависимостей.
## Входные данные: Пустой репозиторий.
## Что сделать: 
1. Создать файловую структуру согласно `jobseeker_bot/` из техспека.
2. Оформить `.env` с ключами для DB, Redis, TG Bot API, LiteLLM и HH.ru.
3. Написать `pyproject.toml` со строгими зависимостями: `aiogram>=3.0`, `telethon`/`pyrogram`, `asyncpg`, `sqlalchemy[async]`, `litellm`.
4. Добавить `.gitignore` и базовый README с описанием запуска в WSL2.
## Ожидаемый результат: Готовая файловая система проекта, корректный `.env.example`, рабочий `pyproject.toml`.
## Как протестировать: `cd jobseeker_bot && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` (или uv sync). Команда `python -c "import os; print('Scaffold OK')"` завершается успешно.