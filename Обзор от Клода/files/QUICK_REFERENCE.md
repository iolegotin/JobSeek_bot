# 🚀 JobSeeker Bot - Quick Reference Card

## Структура проекта в одной строке

```
Telegram (aiogram v3) ← Handlers ← Services ← DB (PostgreSQL + JSONB) + Redis
```

## Основные сервисы

| Сервис | Файл | Статус | Ключевая функция |
|--------|------|--------|------------------|
| **StateManager** | state_manager.py | ✅ DONE | `is_stopped()` - проверка режима STOP |
| **TGDeduplicator** | tg_deduplicator.py | ✅ DONE | `is_duplicate()` - MD5 проверка в Redis |
| **HHClient** | hh_client.py | 🟡 PARTIAL | `fetch_vacancies()` - с exponential backoff |
| **LiteLLMService** | litellm_svc.py | 🟡 PARTIAL | `get_vacancy_score()` - AI анализ (❌ BUG: sync) |
| **FeedbackService** | feedback_svc.py | 🟡 PARTIAL | `process_feedback()` - weight adjustment (❌ BUG: логика) |
| **AlertService** | alert_svc.py | 🟡 PARTIAL | `send_alert()` - админ уведомления |
| **TGChannelHandler** | tg_channel_handler.py | 🟡 PARTIAL | `process_message()` - парсинг каналов (❌ TODO: Pyrogram) |

## Data Model

```sql
users
├── id (UUID PK)
├── tg_chat_id (BIGINT, UNIQUE)
├── role (ENUM: user, admin)
└── weights_config (JSONB) → {"python": 0.8, "remote": 1.0}

vacancies
├── id (UUID PK)
├── source_type (ENUM: hh, tg_channel)
├── external_id
├── title
└── raw_data (JSONB)

match_logs
├── user_id (FK)
├── vacancy_id (FK)
├── ai_score (FLOAT)
├── status (ENUM: delivered, disliked, ignored)
└── feedback_type (ENUM: like, dislike)
```

## Key Flows

### Поиск вакансий
```
Scheduler → HH/TG Parser → Deduplicator → LiteLLM → Feedback Buffer → TG Send
                               ↓                                          ↓
                          Redis Cache                              notify_user()
```

### Пользовательский feedback
```
User: ❤️ Like
  ↓
process_feedback(user_id, vacancy_id, "like")
  ↓
Extract keywords from vacancy → Get AI suggestions
  ↓
Apply delta: weights_config["python"] += 0.5
  ↓
Save to DB: match_logs + users.weights_config
```

### Graceful Degradation
```
ERROR (DB fail / API ban)
  ↓
StateManager.set_stop()
  ↓
AlertService.send_alert(admin) ← Real-time to TG
  ↓
Users get: "Технические работы..."
  ↓
Retry queue holds tasks in Redis
```

## Critical Bugs

| Bug | File | Impact | Fix |
|-----|------|--------|-----|
| `litellm.completion()` is SYNC | litellm_svc.py | 🔴 BLOCKS async | Use `litellm.acompletion()` |
| Feedback ↑ALL weights | feedback_svc.py | 🟡 LOGIC ERROR | Analyze only relevant keywords |
| Async tests use sync asserts | test_*.py | 🟡 TESTS FAIL | Use pytest-asyncio |
| No config files | - | 🔴 DEPLOYMENT BROKEN | Create pyproject.toml + settings.py |

## Quick Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run migrations
alembic upgrade head

# Start bot
python -m app.main

# Redis check
redis-cli
> KEYS *
> GET system_state
```

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/jobseeker_db
REDIS_URL=redis://localhost:6379
TG_BOT_TOKEN=123456:ABC...
ADMIN_TG_ID=-123456789
OPENAI_API_KEY=sk-...
```

## Common Patterns

### Redis-based deduplication
```python
hash_key = hashlib.md5(f"{text}{channel_id}".encode()).hexdigest()
exists = await redis.exists(hash_key)
if not exists:
    await redis.setex(hash_key, time=604800, value="1")  # 7 days
```

### Exponential backoff on 429
```python
delay = base_delay * (2 ** (retries - 1))  # 1, 2, 4, 8, 16 sec
await asyncio.sleep(delay)
```

### JSONB weight update
```python
from sqlalchemy.orm.attributes import flag_modified

user.weights_config["python"] += 0.5
flag_modified(user, 'weights_config')
session.commit()
```

### Global state check
```python
sm = StateManager.get_instance()
if await sm.is_stopped():
    return sm.get_degradation_message()
```

## Development Phases

```
Phase 1: Config + DB     [████░░░░░░] 40% ← YOU ARE HERE
Phase 2: Parsers         [░░░░░░░░░░] 0%
Phase 3: AI Loop         [░░░░░░░░░░] 0%
Phase 4: Orchestration   [░░░░░░░░░░] 0%
Phase 5: QA + Deploy     [░░░░░░░░░░] 0%
```

## Files to Create/Fix URGENTLY

```
PRIORITY 1 (BLOCKS DEPLOYMENT):
☐ pyproject.toml          (dependencies)
☐ app/settings.py         (Pydantic config)
☐ .env.example            (config template)
☐ Fix litellm.completion() → acompletion()

PRIORITY 2 (BLOCKS TESTING):
☐ Fix FeedbackService logic
☐ Fix graceful_degradation tests
☐ Alembic migrations

PRIORITY 3 (FEATURE COMPLETE):
☐ Pyrogram TG client
☐ Redis retry queue
☐ Main dispatcher
```

## References

- **Tech Spec:** `.ai/specs/tech_spec.md` (100 lines)
- **User Spec:** `.ai/specs/user_spec.md` (40 lines)
- **Tasks:** `.ai/tasks/` (14 markdown files for phases 1-5)

## Stats

- 📦 11 components
- ✅ 2 complete (StateManager, TGDeduplicator)
- 🟡 8 partial/in-design
- 🐛 1 critical bug (litellm sync)
- 📝 3 high-priority config files missing
- ⏱️ ~12-15 days to MVP

---

**Last updated:** 2026-05-25  
**Status:** Early Development (~20% ready)  
**Next step:** Create config layer → unblock development
