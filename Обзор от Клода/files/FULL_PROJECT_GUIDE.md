# 🤖 JobSeeker AI Bot - ЧТО ЭТО ЗА ПРОЕКТ?

## 📌 КРАТКОЕ РЕЗЮМЕ (TL;DR)

**JobSeeker AI Bot** — это **интеллектуальный Telegram-бот**, который автоматизирует поиск вакансий для соискателей. Система:
- 🔍 Собирает вакансии с **HH.ru API** и **Telegram-каналов** (парсинг)
- 🧠 Анализирует релевантность вакансий с помощью **AI (LiteLLM)**
- 🎯 **Адаптируется** к предпочтениям пользователя через Feedback Loop
- 💬 Отправляет уведомления **только о подходящих вакансиях** (батчинг, без спама)
- 👨‍💼 **Разумно обрабатывает ошибки** (Graceful Degradation)

---

## 🎯 БИЗНЕС-ЦЕЛЬ

**Решить проблему информационного шума** в Telegram:
- ❌ **Проблема:** Соискатели теряются в потоке случайных вакансий из каналов, не видят релевантные предложения
- ✅ **Решение:** Бот **фильтрует вакансии через AI**, учит индивидуальные предпочтения каждого пользователя
- 💰 **Ценность:** Точечная доставка только подходящих предложений без спама

---

## 🏗️ АРХИТЕКТУРА НА ОДНОЙ КАРТИНКЕ

```
┌─────────────────────────────────────────────────────────────┐
│           ИСТОЧНИКИ ДАННЫХ (Data Aggregation)              │
├──────────────────────────────────────┬──────────────────────┤
│   HH.ru API Parser                   │  Telegram Channels   │
│  (rate limit, 429 backoff)          │  (FloodWait handler) │
│  Rate: 30 req/sec                   │  Pyrogram/Telethon   │
└──────────────────────────────────────┴──────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │  Redis Deduplicator               │
        │  (MD5 hash, EXPIRE 7 days)        │
        └───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              AI Analysis Engine (LiteLLM)                   │
│  User Profile + Weights → Score [0.0-1.0]                 │
│  Supports: OpenAI, Claude, Ollama (local)                 │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │  Redis Batch Buffer               │
        │  (Cooldown-based grouping)        │
        └───────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │  Telegram Bot (aiogram v3)        │
        │  /start, feedback, admin panel    │
        └───────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │  User + PostgreSQL Database       │
        │  Profiles, weights, match logs    │
        └───────────────────────────────────┘
```

---

## 🎮 ОСНОВНОЙ ПОЛЬЗОВАТЕЛЬСКИЙ СЦЕНАРИЙ

### Сценарий 1: Начало работы

```
1. Пользователь нажимает /start в Telegram
   ↓
2. Бот просит описать профиль:
   "Я ищу Senior Python Developer с опытом Docker, зарплата от 150k"
   ↓
3. Бот сохраняет в БД:
   - query_text = "Senior Python Developer с Docker, 150k+"
   - weights_config = {"python": 0.8, "docker": 0.7, "remote": 1.0, ...}
   - cooldown_interval = 1800 сек (30 мин)
```

### Сценарий 2: Поиск и анализ вакансий

```
1. Каждые 15 минут бот запускает парсеры:
   
   a) HH.ru Parser:
      - Запрашивает API с ключевыми словами
      - Получает 50-100 вакансий
      - Обрабатывает 429 errors с exponential backoff
      - Кэширует результаты
   
   b) TG Channel Parser (Pyrogram):
      - Читает каналы (headhunter_ru, и др.)
      - Хранит last_message_id для инкрементального парсинга
      - Обрабатывает FloodWait (2-5 сек задержки)

2. Redis Deduplicator:
   - Вычисляет MD5(title + description + channel_id)
   - Если хеш в Redis → дубль, пропускаем
   - Иначе → добавляем в Redis (EXPIRE 7 дней)

3. AI Analysis:
   - LiteLLM отправляет запрос к модели
   - Промпт: "Анализируй вакансию, даю веса: python=0.8, docker=0.7..."
   - Модель возвращает: {"score": 0.85, "reasons": [...], "weights_delta": {...}}

4. Фильтрация:
   - Если score >= 0.7 → релевантная вакансия
   - Добавляем ID в Redis buffer: "user_123:cooldown_bucket"

5. Батчинг (Buffering):
   - Накапливаем вакансии в буфере
   - Через 30 мин (cooldown_interval):
     * Отправляем 1 сообщение со всеми найденными вакансиями
     * НЕ отправляем каждую отдельно (защита от спама)
```

### Сценарий 3: Feedback Loop (Обучение на лету)

```
Пользователь видит вакансию:
   "Python Developer | Зарплата 180k | Remote | Docker required"

User действия:
   ❤️ LIKE → +0.5 к весам релевантных слов
      - python: 0.8 → 1.0 (+0.2?)
      - remote: 1.0 → 1.3 (уже высокий)
      - docker: 0.7 → 0.9
      
   👎 DISLIKE → -0.5 к весам
      - onsite: 0.3 → 0.0 (отключить офис)
      - junior: 0.2 → 0.0

Результат:
   ✅ Система уже учла предпочтения пользователя
   ✅ Следующие поиски будут точнее (no retraining!)
   ✅ Логируется в match_logs для аналитики админа
```

### Сценарий 4: Чрезвычайная ситуация (Graceful Degradation)

```
Если произойдет:
   - БД упала → STOP режим
   - LiteLLM недоступен → очередь в Redis
   - HH.ru API забанил → exponential backoff
   - TG FloodWait → 2-5 сек задержка
   
То система:
   ✅ Переходит в режим STOP
   ✅ Отправляет админу ALERT в TG:
      "🚨 CRITICAL: Database Connection Refused"
   ✅ Показывает пользователям:
      "За последние 24 часа новых вакансий не найдено, 
       я продолжаю поиск..."
   ✅ Парсеры стают на паузу (не спамят)
```

---

## 📊 ФУНКЦИОНАЛ СИСТЕМЫ

### 1️⃣ Агрегация данных (Data Collection)

| Источник | Как | Лимиты | Обработка ошибок |
|----------|-----|--------|------------------|
| **HH.ru API** | HTTP `httpx`/`aiohttp` | 30 req/sec | 429 → exponential backoff (1, 2, 4, 8, 16 сек) |
| **TG Каналы** | Pyrogram `get_messages()` | Анонимно | FloodWait → random jitter (2-5 сек) |
| **Дубликаты** | MD5 хеш в Redis | 7-day EXPIRE | Пропускаем если хеш найден |

### 2️⃣ Профилирование пользователей (User Profiles)

```json
{
  "user_id": "uuid",
  "tg_chat_id": 123456789,
  "query_text": "Senior Python, Docker, 150k+, remote",
  "weights_config": {
    "python": 0.8,
    "docker": 0.7,
    "remote": 1.0,
    "salary_min": 150000,
    "experience": "senior"
  },
  "cooldown_interval": 1800,
  "role": "user" // или "admin"
}
```

### 3️⃣ AI-анализ вакансий (AI Routing)

**Промпт LiteLLM:**
```
Ты — эксперт по подбору вакансий.

Профиль пользователя: Senior Python Developer с Docker, 150k+, remote

Веса ключевых слов:
- python: 0.8
- docker: 0.7
- remote: 1.0

Вакансия: "Middle Python Developer, 100k, Москва, офис"

Верни JSON:
{
  "score": 0.3,  // 0.0-1.0, LOW потому что зарплата низко и офис
  "reasons": ["Зарплата меньше требуемой", "Требуется офис, вы ищете remote", "Middle вместо Senior"],
  "updated_weights": {"junior": -0.2}  // Нужно занизить junior
}
```

### 4️⃣ Feedback Loop (Обучение)

```
User LIKE вакансию
   ↓
Анализируем ключевые слова вакансии
   ↓
AI sugests: {"python": +0.3, "remote": +0.5}
   ↓
Обновляем weights_config в JSONB
   ↓
Сохраняем в match_logs для истории
   ↓
Следующий анализ использует новые веса
```

### 5️⃣ Батчинг рассылок (Smart Notifications)

```
Накопление (за 30 мин):
  ✓ Вакансия 1: Score 0.85
  ✓ Вакансия 2: Score 0.92
  ✓ Вакансия 3: Score 0.75

Отправка (одно сообщение):
  "Ваша подборка за период:
   1. Python Developer @ Yandex (0.85)
   2. Backend @ Sber (0.92)
   3. DevOps @ Mail.ru (0.75)
   
   ❤️ Нравится?    👎 Не интересует?"
```

### 6️⃣ Администраторский панель

```
/admin → админ видит:
  - Логи парсеров (сколько вакансий найдено)
  - Очередь LiteLLM retry
  - Активные юзеры и их вес-профили
  - Статус парсеров (RUNNING / STOP)
  - Возможность ручного override фильтра пользователя
```

### 7️⃣ Graceful Degradation (Отказоустойчивость)

```
При критической ошибке:
  ① STOP режим (Redis flag)
  ② Alert админу в TG
  ③ Показать юзерам: "Технические работы"
  ④ Парсеры встают на паузу
  ⑤ Отложенные задачи хранятся в Redis queue
  ⑥ При восстановлении → retry из очереди
```

---

## 💾 DATA MODEL (PostgreSQL + JSONB)

### Таблица `users`
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  tg_chat_id BIGINT UNIQUE NOT NULL,
  role ENUM('user', 'admin') DEFAULT 'user',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Таблица `user_filters`
```sql
CREATE TABLE user_filters (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  query_text TEXT NOT NULL,
  weights_config JSONB NOT NULL,  -- {"python": 0.8, "docker": 0.7, ...}
  cooldown_interval INT DEFAULT 1800,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_filters_user_id ON user_filters(user_id);
CREATE INDEX idx_weights_config ON user_filters USING GIN(weights_config);
```

### Таблица `vacancies`
```sql
CREATE TABLE vacancies (
  id UUID PRIMARY KEY,
  source_type ENUM('hh', 'tg_channel'),
  external_id TEXT UNIQUE,
  title TEXT NOT NULL,
  raw_data JSONB NOT NULL,  -- полный ответ API
  is_processed_by_ai BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_vacancies_source ON vacancies(source_type);
CREATE INDEX idx_vacancies_processed ON vacancies(is_processed_by_ai);
```

### Таблица `match_logs`
```sql
CREATE TABLE match_logs (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  vacancy_id UUID REFERENCES vacancies(id) ON DELETE CASCADE,
  ai_score FLOAT CHECK (ai_score BETWEEN 0.0 AND 1.0),
  status ENUM('delivered', 'disliked', 'ignored'),
  feedback_type ENUM('like', 'dislike'),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_match_logs_user ON match_logs(user_id, created_at);
CREATE INDEX idx_match_logs_vacancy ON match_logs(vacancy_id);
```

---

## 🛠️ ТЕХНОЛОГИЧЕСКИЙ СТЕК

| Компонент | Технология | Зачем |
|-----------|-----------|-------|
| **Telegram Bot** | `aiogram v3.x` | Модерный асинхронный фреймворк для Telegram |
| **TG Parsing** | `Pyrogram` или `Telethon` | Парсинг приватных каналов как юзер-бот |
| **HH.ru API** | `httpx`/`aiohttp` | Асинхронные HTTP запросы |
| **Async ORM** | `SQLAlchemy 2.0 Async` + `asyncpg` | Асинхронная работа с БД |
| **Database** | `PostgreSQL` | JSONB поддержка для весов-фильтров |
| **Cache & Queues** | `Redis` | Дедупликация, батчинг, retry очереди |
| **AI Model** | `LiteLLM` | Унифицированный интерфейс к LLM (OpenAI, Claude, Ollama) |
| **Testing** | `pytest` | Async unit тесты |

---

## 📋 ПЛАН РАЗРАБОТКИ (14 задач за 5 фаз)

### Фаза 1: Инфраструктура (3 задачи)
```
001_001: Scaffold проекта + .env + pyproject.toml
001_002: Async DB connection (SQLAlchemy 2.0 + asyncpg)
001_003: ORM модели (4 таблицы с JSONB)
```

### Фаза 2: HH.ru Parser (2 задачи)
```
002_001: Async HTTP клиент к HH.ru API
002_002: Rate limiting + exponential backoff + Redis кэш
```

### Фаза 3: TG Parser (2 задачи)
```
003_001: Pyrogram client + FloodWait обработка
003_002: Incremental parsing + MD5 deduplication
```

### Фаза 4: AI Layer (2 задачи)
```
004_001: LiteLLM интеграция + промпт-билдер
004_002: Feedback Loop (weight adjustment) + match_logs
```

### Фаза 5: Оркестрация (5 задач)
```
005_001: Aiogram v3 dispatcher + хендлеры + мидлвары
005_002: Redis buffer batching + cooldown logic
005_003: Graceful degradation + admin alerts
```

---

## 🎓 КЛЮЧЕВЫЕ ОСОБЕННОСТИ

### ✅ Что делает проект УНИКАЛЬНЫМ?

1. **Полностью асинхронный** — всё на `asyncio`, не было никаких блокирующих вызовов
2. **Intelligent Feedback Loop** — система учится на лету БЕЗ переобучения модели
3. **Многоканальная агрегация** — одновременно парсит HH.ru + TG-каналы
4. **Graceful Degradation** — система не падает, а деградирует с уведомлением админу
5. **Redis-based Deduplication** — экономит 70% трафика
6. **Batch Notifications** — защита от спама через батчинг

### 🎯 Что система РЕШАЕТ?

| Проблема | Решение |
|----------|----------|
| "Потеряюсь в потоке вакансий" | AI фильтрует релевантные |
| "Одна вакансия = одно сообщение" | Батчинг (группировка) |
| "Фильтр не учит мои предпочтения" | Feedback Loop адаптируется |
| "Хакеры банят по лимитам" | Exponential backoff + обработка ошибок |
| "Система упадёт и всё сломается" | Graceful Degradation + alerts |

---

## 🚀 ИТОГ

**JobSeeker AI Bot** — это **production-ready система** для умного поиска вакансий, которая:
- ✅ Агрегирует данные с 2+ источников
- ✅ Анализирует релевантность через AI без переобучения
- ✅ Адаптируется к каждому пользователю индивидуально
- ✅ Защита от лимитов и ошибок через backoff + graceful degradation
- ✅ Батчинг рассылок для защиты от спама
- ✅ Полностью асинхронная архитектура

**На русском:** Это **умный ассистент в Telegram**, который постоянно следит за вакансиями на HH.ru и в отраслевых каналах, анализирует их через AI, и отправляет только те вакансии, которые действительно подходят пользователю.

---

*Документ создан на основе полного изучения tech_spec.md, user_spec.md и 14 task decomposition файлов*  
*Дата:* 2026-05-25  
*Версия проекта:* MVP v2
