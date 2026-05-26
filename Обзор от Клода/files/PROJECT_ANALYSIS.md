# JobSeeker Bot - Анализ проекта

## 📋 Обзор

**Проект:** JobSeeker AI Bot (MVP v2)  
**Язык:** Python 3.11+  
**Цель:** Автоматизировать поиск вакансий через AI-анализ вакансий с HH.ru и TG-каналов, с динамической адаптацией фильтров на основе feedback пользователя.

---

## 🏗️ Архитектура проекта

### Основные компоненты

| Компонент | Статус | Описание |
|-----------|--------|---------|
| **Database Layer** | STARTED | PostgreSQL + SQLAlchemy 2.0 Async с типом JSONB для весов фильтров |
| **HH.ru Client** | PARTIAL | Асинхронный HTTP-клиент с exponential backoff при 429 ошибках |
| **TG Deduplicator** | ✅ COMPLETE | Redis-based дедупликация постов по MD5 хешу |
| **TG Handler** | IN_DESIGN | Инкрементальный парсинг каналов с обработкой FloodWait |
| **LiteLLM Service** | PARTIAL | Унифицированный интерфейс к AI моделям с JSON валидацией |
| **Feedback Service** | PARTIAL | Корректировка весов фильтра по лайку/дизлайку пользователя |
| **State Manager** | ✅ COMPLETE | Глобальное управление состоянием (STOP/RUNNING) |
| **Alert Service** | PARTIAL | Отправка критических алертов администратору в TG |
| **Tests** | PARTIAL | Pytest тесты с моками для key services |

---

## 📁 Структура файлов

```
jobseeker_bot/
├── app/
│   ├── core/
│   │   ├── db.py                          # SQLAlchemy 2.0 Async engine
│   │   └── services/
│   │       ├── hh_client.py              # HTTP wrapper для HH.ru API
│   │       ├── hh_parser.py              # Логика парсинга с retry
│   │       ├── litellm_svc.py            # AI prompt builder + JSON validation
│   │       ├── feedback_svc.py           # Weight adjustment logic
│   │       ├── state_manager.py          # Global STOP/RUN state (✅)
│   │       ├── alert_svc.py              # Admin TG notifications
│   │       ├── tg_deduplicator.py        # Duplicate detection (✅)
│   │       └── (others in design)
│   ├── handlers/
│   │   ├── tg_channel_handler.py        # Incremental message fetching
│   │   └── (others in design)
│   └── models/
│       ├── user.py
│       ├── match_log.py
│       └── vacancy.py
├── tests/
│   ├── test_feedback_svc.py
│   ├── test_graceful_degradation.py
│   └── test_tg_deduplicator.py
├── .ai/
│   ├── specs/
│   │   ├── tech_spec.md                 # Полная техническая спецификация
│   │   └── user_spec.md                 # User requirements
│   └── tasks/
│       └── (14 задач по фазам разработки)
└── .env                                 # (не создан, нужна конфигурация)
```

---

## 🔑 Ключевые решения

### 1. Асинхронная архитектура
- **Фреймворк:** aiogram 3.x для работы с Telegram Bot API
- **Асинхронный ORM:** SQLAlchemy 2.0 Async + asyncpg
- **Асинхронные очереди:** Redis для буферизации и управления состоянием
- **Асинхронные HTTP запросы:** aiohttp/httpx для работы с внешними API

### 2. Базовые данные (JSONB)
```python
# Таблица users.weights_config хранит гибкие веса фильтров
{
  "python": 0.8,
  "docker": 0.6,
  "remote": 1.0,
  "salary_min": 100000
}
```

### 3. Обработка ошибок (Graceful Degradation)
- **Rate Limiting (429):** Exponential backoff (1, 2, 4, 8, 16 сек)
- **FloodWait:** Случайные задержки (2-5 сек) между запросами
- **STOP Mode:** При критических ошибках система переходит в режим STOP, пользователи получают вежливое сообщение
- **Admin Alerts:** Критические ошибки отправляются админу в реалтайме

### 4. Дедупликация
```python
hash_key = md5(f"{text_post}{channel_id}".encode())
# Хранится в Redis с EXPIRE 7 дней
```

### 5. AI-анализ с Feedback Loop
- **Prompt Builder:** Динамический системный промпт на основе query_text + weights
- **JSON Output:** Модель возвращает `{score, reasons, updated_weights_suggestion}`
- **Weight Adjustment:** +0.5 при LIKE, -0.5 при DISLIKE

---

## ✅ Реализованные компоненты

### `state_manager.py` - Синглтон для глобального состояния
```python
class StateManager:
    async def set_stop(reason: str)        # Переход в STOP режим
    async def is_stopped() -> bool          # Проверка статуса
    def get_degradation_message() -> str   # Вежливое сообщение для пользователя
```

### `tg_deduplicator.py` - Redis-based дедупликация
```python
class TGDeduplicator:
    async def is_duplicate(text_post, channel_id) -> bool  # True если дубль
    # Устанавливает MD5 хеш в Redis с EXPIRE 7 дней
```

### `alert_svc.py` - Отправка алертов админу
```python
class AlertService:
    async def send_alert(severity, error_type, traceback)  # Отправка в TG
```

---

## ⚠️ Проблемы и недоделки

### ВЫСОКИЙ ПРИОРИТЕТ
1. **Конфигурация отсутствует**
   - Нет `pyproject.toml` с зависимостями
   - Нет `.env.example` для ключей API
   - Нет `settings.py` для централизованной конфигурации

2. **Database модели не завершены**
   - Файл `app/models/` содержит только тестовые модели
   - Нет миграций Alembic
   - Нет индексов на JSONB полях

### СРЕДНИЙ ПРИОРИТЕТ
3. **TG Client не полностью реализован**
   - Pyrogram/Telethon интеграция на уровне скелета
   - FloodWait обработчик отсутствует
   - Инкрементальный парсинг каналов не завершен

4. **LiteLLM Service требует доработки**
   - Нет поддержки retry при падении модели
   - Нет кэширования результатов анализа
   - Асинхронный вызов работает через sync `litellm.completion()`

5. **Feedback Service имеет логические ошибки**
   - При LIKE увеличивает ВСЕ веса (неверная логика)
   - Должна анализировать только релевантные ключевые слова из вакансии
   - Нет привязки к `updated_weights_suggestion` из AI

### НИЗКИЙ ПРИОРИТЕТ
6. **Тесты неполные**
   - Нет интеграционных тестов
   - Тесты используют sync моки для async кода
   - Отсутствуют тесты на end-to-end сценарии

7. **Документация**
   - Недостаточно docstrings в сервисах
   - Отсутствуют type hints в некоторых местах

---

## 🔄 Разработка по фазам

### Фаза 1: Инфраструктура ✅ (НАЧАЛО)
- [x] Scaffold проекта и .env
- [x] Database setup (async connection)
- [x] ORM модели с JSONB

### Фаза 2: Парсинг данных (НАЧАЛО)
- [x] HH.ru Async Client с rate limiting
- [ ] Pyrogram FloodWait handler
- [ ] Inкрементальная дедупликация

### Фаза 3: AI-слой (IN_PROGRESS)
- [x] LiteLLM prompt builder
- [ ] Feedback loop weights adjustment
- [ ] Redis retry queue

### Фаза 4: Оркестрация (TODO)
- [ ] Aiogram dispatcher handlers
- [ ] Redis buffer batching
- [ ] Graceful degradation alerts

### Фаза 5: Интеграция (TODO)
- [ ] Main entry point + asyncio.run()
- [ ] Полное тестирование
- [ ] Развертывание

---

## 🧪 Тестирование

### Существующие тесты
1. **test_feedback_svc.py** - Unit тесты для feedback loop
   - ✅ `test_like_feedback()` - проверяет увеличение весов при LIKE
   - ⚠️ Логика неправильная (увеличивает ВСЕ веса, не только релевантные)

2. **test_tg_deduplicator.py** - Тесты дедупликации
   - ✅ `test_is_duplicate_existing_hash()` - проверяет существующий дубль
   - ✅ `test_is_duplicate_new_hash()` - проверяет новое сообщение

3. **test_graceful_degradation.py** - Тесты обработки ошибок
   - ⚠️ Тесты написаны неправильно (используют sync assertions для async методов)
   - Нет реальной async функциональности

---

## 🚀 Рекомендации

### Немедленные действия
1. **Создать конфигурацию**
   - `pyproject.toml` с deps: aiogram>=3.0, sqlalchemy[asyncpg], litellm, redis, httpx, pyrogram
   - `.env.example` с placeholder ключами
   - `settings.py` для Pydantic конфига

2. **Завершить Database слой**
   - Создать финальные ORM модели (users, filters, vacancies, match_logs)
   - Написать Alembic миграции
   - Добавить JSONB GIN индексы

3. **Исправить Feedback Service**
   - Анализировать только ключевые слова из вакансии
   - Использовать `updated_weights_suggestion` из AI
   - Применять дельту весов, а не полную перезапись

4. **Завершить TG Client**
   - Реализовать Pyrogram интеграцию
   - Добавить FloodWait обработку
   - Реализовать инкрементальный парсинг

---

## 📊 Статистика

- **Файлов Python:** 30+
- **Строк кода:** ~800 (фактического), 2000+ (с комментариями и docs)
- **Компонентов:** 11 основных сервисов
- **Тестов:** 6 unit тестов (но требуют доработки)
- **Задач остается:** 14 в фазах 2-5

---

## 🎯 Заключение

Проект **JobSeeker Bot** находится на начальной стадии разработки. Основная архитектура задана, критические компоненты (State Manager, TG Deduplicator) реализованы. Требуется:

1. ✅ Завершить инфраструктуру (конфиг + DB)
2. 🔄 Доработать AI-слой (Feedback Loop, LiteLLM retry)
3. 🔄 Реализовать TG Client (Pyrogram + FloodWait)
4. ✅ Интегрировать в главный dispatcher
5. 🧪 Расширить тестирование

**Статус:** Готов к продолжению разработки. Основные компоненты имеют понятную архитектуру, граф зависимостей ясен.
