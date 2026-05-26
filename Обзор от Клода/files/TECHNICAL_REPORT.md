# JobSeeker Bot - Детальный технический отчет

## 1. Архитектурная диаграмма

```
┌─────────────────────────────────────────────────────────────┐
│                    TELEGRAM BOT LAYER (aiogram v3)          │
│  /start, /filters, feedback handlers, graceful messages    │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
    ┌────────▼────────┐          ┌───────────▼────────┐
    │  Handlers       │          │  Middleware        │
    │  (tg_channel)   │          │  (auth, logging)   │
    └────────┬────────┘          └───────────────────┘
             │
    ┌────────▼──────────────────────────────────────────┐
    │            CORE SERVICES LAYER                    │
    │                                                  │
    │  ┌──────────────┐  ┌──────────────────────────┐ │
    │  │ HH.ru Client │  │ Telegram Client (TG)    │ │
    │  │ - rate limit │  │ - FloodWait handler     │ │
    │  │ - 429 backoff│  │ - incremental parsing   │ │
    │  │ - caching    │  │ - deduplication        │ │
    │  └──────┬───────┘  └──────────┬──────────────┘ │
    │         │                     │                 │
    │  ┌──────▼────────────────────▼──────────┐      │
    │  │  TG Deduplicator (Redis)             │      │
    │  │  - MD5 hash check                    │      │
    │  │  - EXPIRE 7 days                     │      │
    │  └──────┬──────────────────────────────┘      │
    │         │                                      │
    │  ┌──────▼────────────────────────────────┐    │
    │  │  LiteLLM Service (AI Analysis)        │    │
    │  │  - prompt builder (query + weights)  │    │
    │  │  - JSON schema validation            │    │
    │  │  - retry queue on failure            │    │
    │  └──────┬───────────────────────────────┘    │
    │         │                                     │
    │  ┌──────▼────────────────────────────────┐   │
    │  │  Feedback Service                     │   │
    │  │  - weight adjustment (LIKE/DISLIKE)  │   │
    │  │  - flag_modified for JSONB tracking  │   │
    │  └──────┬───────────────────────────────┘   │
    │         │                                    │
    │  ┌──────▼──────────────────────────────┐    │
    │  │  State Manager (Redis) + Alert Svc  │    │
    │  │  - STOP/RUN state                   │    │
    │  │  - admin TG alerts                  │    │
    │  └──────────────────────────────────────┘   │
    └────────┬──────────────────────────────────────┘
             │
    ┌────────▼──────────────────────────────────────┐
    │         DATA PERSISTENCE LAYER                 │
    │                                               │
    │  ┌────────────────────────────────────────┐  │
    │  │  PostgreSQL (Main DB)                  │  │
    │  │  - users (id, tg_chat_id, weights)    │  │
    │  │  - vacancies (source, external_id)    │  │
    │  │  - match_logs (score, feedback)       │  │
    │  └────────────────────────────────────────┘  │
    │                                               │
    │  ┌────────────────────────────────────────┐  │
    │  │  Redis (Cache + Queue)                 │  │
    │  │  - dedup hashes (EXPIRE 7d)           │  │
    │  │  - state key (STOP)                   │  │
    │  │  - retry queue (ai_analysis_queue)    │  │
    │  │  - notification batches                │  │
    │  └────────────────────────────────────────┘  │
    └──────────────────────────────────────────────┘
```

---

## 2. Data Flow Diagram

### Сценарий 1: Поиск новых вакансий

```
┌─────────────────────┐
│  Scheduler Timer    │
│  (every 30 min)     │
└────────────┬────────┘
             │
    ┌────────▼──────────────────┐
    │  Fetch from HH.ru API     │
    │  - query by user keywords │
    │  - handle 429 backoff     │
    └────────┬──────────────────┘
             │
    ┌────────▼──────────────────┐
    │  Fetch from TG Channels   │
    │  - incremental from offset│
    │  - handle FloodWait       │
    └────────┬──────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  Deduplicate (Redis MD5 check)    │
    │  - if exists: drop               │
    │  - if new: setex + continue      │
    └────────┬──────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  Analyze with LiteLLM             │
    │  - send prompt + vacancy text     │
    │  - get: {score, reasons, ...}     │
    │  - on error: add to retry queue   │
    └────────┬──────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  Score > Threshold?               │
    │  YES: buffer in Redis by user_id  │
    │  NO:  discard                     │
    └────────┬──────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  Check cooldown_interval passed?  │
    │  YES: send batch + save to DB     │
    │  NO:  wait                        │
    └───────────────────────────────────┘
```

### Сценарий 2: User Feedback Loop

```
User clicks "❤️ Like" on vacancy
       │
       ▼
┌──────────────────────────┐
│ process_feedback()       │
│ - action = "like"        │
│ - old_weights snapshot   │
└────────┬─────────────────┘
         │
    ┌────▼─────────────────────────────┐
    │ AI suggests weights delta         │
    │ - analyze vacancy keywords       │
    │ - return: {python: +0.5, ...}   │
    └────┬─────────────────────────────┘
         │
    ┌────▼──────────────────────┐
    │ Apply delta to user config│
    │ weights_config[key] += 0.5│
    │ (flag_modified for JSONB) │
    └────┬──────────────────────┘
         │
    ┌────▼──────────────────────┐
    │ Save to match_logs        │
    │ - user_id, vacancy_id     │
    │ - old/new weights delta   │
    │ - timestamp               │
    └────┬──────────────────────┘
         │
    ┌────▼──────────────────────┐
    │ Commit to PostgreSQL      │
    │ - users.weights_config    │
    │ - match_logs entry        │
    └───────────────────────────┘
```

---

## 3. Компоненты по файлам

### 3.1 Database Layer

**Файл:** `app/core/db.py`
- ✅ **Статус:** INITIALIZED
- **Код:**
  ```python
  DATABASE_URL = os.getenv("DATABASE_URL")
  engine: AsyncEngine = create_async_engine(DATABASE_URL)
  async_session_factory = sessionmaker(engine, expire_on_commit=False)
  ```
- **Проблемы:**
  - Нет обработки отсутствия DATABASE_URL
  - Нет миграций Alembic
  - Нет индексов на JSONB полях

### 3.2 HH.ru Client

**Файл:** `app/core/services/hh_client.py` (60 строк)
- ⚠️ **Статус:** PARTIAL
- **Реализовано:**
  - Асинхронный fetch через aiohttp
  - Обработка HTTP 429 с exponential backoff (1, 2, 4, 8, 16 сек)
  - Локальное кэширование в Redis
  - Предусмотрена отправка алерта админу
- **Не реализовано:**
  - Реальное подключение к Redis (placeholder)
  - Реальная отправка алерта в TG
  - Обработка других ошибок (5xx, timeout)

### 3.3 TG Deduplicator

**Файл:** `app/core/services/tg_deduplicator.py` (27 строк)
- ✅ **Статус:** COMPLETE
- **Функции:**
  ```python
  async def is_duplicate(text_post: str, channel_id: int) -> bool
  ```
- **Логика:**
  1. Вычислить MD5(text_post + channel_id)
  2. Проверить EXISTS в Redis
  3. Если новый: setex с EXPIRE 7 дней (604800 сек)
  4. Вернуть True/False

### 3.4 LiteLLM Service

**Файл:** `app/core/services/litellm_svc.py` (58 строк)
- ⚠️ **Статус:** PARTIAL
- **Реализовано:**
  ```python
  async def get_vacancy_score(query_text, weights_config) -> Dict
  ```
  - Сборка системного промпта
  - JSON парсинг ответа модели
  - Валидация структуры (score ∈ [0,1], reasons список, weights dict)
- **Проблемы:**
  - `await litellm.completion()` - НЕ асинхронная функция (нужен litellm.acompletion())
  - Нет retry на ошибку модели
  - Нет кэширования результатов
  - Нет timeout обработки

### 3.5 Feedback Service

**Файл:** `app/core/services/feedback_svc.py` (46 строк)
- ⚠️ **Статус:** PARTIAL
- **Проблема логики:**
  ```python
  if action == "like":
      for key in new_weights:
          new_weights[key] = new_weights.get(key, 0) + 0.5  # ❌ ВСЕ ключи!
  ```
  - Должна только релевантные ключевые слова из вакансии
  - Должна использовать `updated_weights_suggestion` из AI

### 3.6 State Manager

**Файл:** `app/core/services/state_manager.py` (46 строк)
- ✅ **Статус:** COMPLETE
- **Функции:**
  - `async set_stop(reason)` - переход в STOP режим
  - `async is_stopped()` - проверка статуса
  - `get_degradation_message()` - вежливое сообщение
- **Реализация:** Redis ключ `system_state`

### 3.7 Alert Service

**Файл:** `app/core/services/alert_svc.py` (35 строк)
- ⚠️ **Статус:** PARTIAL
- **Функция:** `async send_alert(severity, error_type, traceback)`
- **Проблемы:**
  - Hardcoded bot token (должен быть конфиг)
  - Нет обработки ошибок при отправке
  - Нет retry логики

---

## 4. Модели данных (ORM)

### Из tech_spec.md

| Таблица | Поля | Индексы |
|---------|------|---------|
| **users** | id (UUID PK), tg_chat_id (BIGINT, UNIQUE), role (ENUM), is_active (BOOL), created_at | (tg_chat_id) |
| **user_filters** | id, user_id (FK), query_text, weights_config (JSONB), cooldown_interval | (user_id, created_at), GIN(weights_config) |
| **vacancies** | id, source_type (ENUM), external_id, title, raw_data (JSONB), is_processed_by_ai | (source_type, external_id), GIN(raw_data) |
| **match_logs** | id, user_id (FK), vacancy_id (FK), ai_score, status (ENUM), feedback_type | (user_id, created_at), (vacancy_id) |

### Текущие модели (в тестах)

```python
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    weights_config = Column(JSON, nullable=True)

class MatchLog(Base):
    __tablename__ = 'match_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    vacancy_id = Column(Integer)
    action = Column(String)
    old_weights = Column(JSON)
    new_weights = Column(JSON)
    timestamp = Column(DateTime)
```

**Проблемы:**
- Используют `Integer` вместо `UUID`
- Используют `JSON` вместо `JSONB`
- Отсутствуют индексы
- Отсутствуют FK связи с ON_DELETE CASCADE

---

## 5. Тесты

### test_feedback_svc.py

```python
def test_like_feedback(self, db_session):
    user = User(id=1, weights_config={"python": 0.5, "sql": 0.3})
    svc = FeedbackService(db_session)
    result = svc.process_feedback(1, 101, "like")
    
    assert result["status"] == "ok"
    assert user.weights_config["python"] == 1.0  # ✅ Проверяет +0.5
```

⚠️ **Логика теста неправильная** - тест проверяет неправильное поведение.

### test_tg_deduplicator.py

- ✅ `test_is_duplicate_existing_hash()` - мокирует Redis.exists() = 1
- ✅ `test_is_duplicate_new_hash()` - мокирует Redis.exists() = 0, проверяет setex()

### test_graceful_degradation.py

```python
def test_global_exception_intercepts_and_stops(self):
    assert sm.is_stopped() == True  # ❌ Ошибка: is_stopped() - async функция
```

⚠️ **Тесты не работают** - используют sync вызовы для async функций.

---

## 6. Конфигурация (ОТСУТСТВУЕТ)

### Требуется создать:

1. **pyproject.toml**
   ```toml
   [project]
   name = "jobseeker-bot"
   version = "0.1.0"
   dependencies = [
       "aiogram>=3.0",
       "sqlalchemy[asyncpg]>=2.0",
       "litellm>=1.0",
       "redis[asyncio]>=5.0",
       "httpx>=0.24",
       "pyrogram>=2.0",
       "pytest>=7.0",
   ]
   ```

2. **.env.example**
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/jobseeker_db
   REDIS_URL=redis://localhost:6379
   TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   ADMIN_TG_ID=-123456789
   HH_API_KEY=your_hh_api_key
   OPENAI_API_KEY=sk-...
   ```

3. **settings.py**
   ```python
   from pydantic_settings import BaseSettings
   
   class Settings(BaseSettings):
       DATABASE_URL: str
       REDIS_URL: str
       TG_BOT_TOKEN: str
       ADMIN_TG_ID: int
       
       class Config:
           env_file = ".env"
   ```

---

## 7. Проблемы и решения

| Проблема | Статус | Решение |
|----------|--------|---------|
| Нет конфигурации | 🔴 HIGH | Создать pyproject.toml, .env, settings.py |
| `litellm.completion()` sync | 🔴 HIGH | Использовать `litellm.acompletion()` |
| Feedback Service логика | 🔴 HIGH | Анализировать только релевантные слова |
| TG FloodWait | 🟡 MEDIUM | Реализовать Pyrogram с обработкой |
| Модели не финализированы | 🟡 MEDIUM | Завершить ORM модели, миграции |
| Тесты для async кода | 🟡 MEDIUM | Использовать pytest-asyncio |
| Нет retry очереди | 🟡 MEDIUM | Реализовать Redis очередь для LiteLLM |

---

## 8. Дорожная карта реализации

```
Фаза 1: Инфраструктура (1-2 дня)
├─ Создать pyproject.toml, settings.py, .env
├─ Завершить ORM модели + Alembic миграции
└─ Добавить JSONB индексы

Фаза 2: Источники данных (3-4 дня)
├─ Завершить HH.ru client с обработкой ошибок
├─ Реализовать Pyrogram для TG каналов
└─ Добавить FloodWait handling + инкрементальный парсинг

Фаза 3: AI-анализ (2-3 дня)
├─ Исправить litellm.acompletion() вызовы
├─ Реализовать retry queue в Redis
├─ Исправить Feedback Service логику
└─ Добавить кэширование результатов

Фаза 4: Оркестрация (2-3 дня)
├─ Реализовать Aiogram диспетчер с хендлерами
├─ Добавить батчинг рассылок через Redis
├─ Завершить graceful degradation + алерты
└─ Добавить расписание (scheduler)

Фаза 5: Тестирование и интеграция (2-3 дня)
├─ Переписать тесты на pytest-asyncio
├─ Добавить интеграционные тесты
├─ Добавить end-to-end тесты
└─ Документирование + development guide
```

---

## 9. Заключение

**Статус проекта:** Ранняя стадия разработки (MVP v2)

✅ **Готово:**
- Архитектура определена
- State Manager, TG Deduplicator реализованы
- Tech spec и User spec написаны

⚠️ **В процессе:**
- Database models (нужны миграции, индексы)
- HH.ru parser (нужна обработка ошибок)
- LiteLLM service (нужна async переделка)

❌ **Требуется:**
- Конфигурация (pyproject.toml, settings)
- Pyrogram интеграция
- Feedback Service (правильная логика)
- Полное тестирование
- Main entry point + dispatcher

**Рекомендуемый порядок работ:** Инфраструктура → Источники → AI → Оркестрация → Тесты
