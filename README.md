# 🤝 MeetBroBot

> Telegram-бот, который организует тусовки за тебя.

[![Telegram Bot](https://img.shields.io/badge/Telegram-@MeetMyBroBot-blue?logo=telegram)](https://t.me/MeetMyBroBot)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)

---

## Проблема

Хочешь собраться с друзьями. Один может в пятницу, другой только в воскресенье. Кто-то всегда становится «организатором» — пишет каждому, собирает ответы, разруливает логистику. Это утомляет.

## Решение

**MeetBroBot** берёт это на себя:

1. 📅 Каждый заполняет своё расписание в личке с ботом
2. 🎯 В группе кто-то пишет `/meet` — бот находит пересечения
3. 🗳 Все голосуют ✅ / ❌ / 🤔 прямо под карточкой
4. 📌 Карточка автоматически закрепляется в чате
5. 🎉 Собрались — потусили — повторили

Никаких «когда свободен?» в чате. Никаких забытых планов.

---

## Фичи

| Фича | Описание |
|-------|----------|
| 📅 `/schedule` | Интерактивный календарь с пресетами времени, поштучное удаление слотов |
| 🎯 `/meet` | Пресеты названий, умный подбор дат, локация, дедлайн, напоминание |
| 🔁 Повторяющиеся встречи | Каждую неделю / раз в 2 недели / раз в месяц — авто-создание |
| 🧠 Smart matching | Бот находит когда все свободны (sweep-line алгоритм) |
| 🤖 Auto-suggest | Бот сам предложит встречу, когда найдёт пересечения |
| 🗳 Голосование | ✅ Иду / ❌ Не могу / 🤔 Не уверен — можно передумать |
| 📢 «Кто не голосовал?» | Кнопка на карточке — пингует тех, кто ещё не ответил |
| 💰 `/expense` | Разделение расходов — кто сколько заплатил |
| 📊 `/debts` | Кто кому должен — оптимизация транзакций |
| ⏰ Дедлайн | 1 час / 3 часа / до завтра / 2 дня / без дедлайна |
| 🔔 Напоминания | За 15 мин / 30 мин / 1 ч / 3 ч до встречи + за 30 мин до дедлайна |
| 📅 Еженедельный nudge | Бот напомнит заполнить расписание (настраивается через `/settings`) |
| 📋 `/meetings` | Список активных встреч в группе с ссылками на карточки |
| 🆕 `/whatsnew` | Чейнджлог прямо в боте — что нового |
| ⚙️ `/settings` | Настройка дня/времени напоминаний, вкл/выкл |
| 📌 Авто-пин | Карточка встречи закрепляется в чате |
| 🤖 Inline-режим | Поделиться встречей через `@MeetMyBroBot` в любом чате |
| 👑 Контроль | Подтвердить/отменить может только организатор |
| 🛡 Безопасность | HTML-экранирование, rate-limiting, creator-only guards |
| 👥 Группы | Welcome-сообщение, авто-трекинг участников |
| 🗑 Auto-cleanup | Устаревшие слоты удаляются ежедневно в 7:00 |
| ⚡ CI/CD | GitHub Actions — lint (Ruff) + тесты на каждый PR |
| 🛡 Sentry | Опциональный мониторинг ошибок |
| 🧪 Тесты | 34 теста (pytest + async SQLite), покрытие: repos, scheduling, card, scheduler |

---

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis (опционально, fallback на in-memory)
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))

### Local

```bash
git clone https://github.com/Kirakiuru/MeetBroBot.git
cd MeetBroBot

cp .env.example .env
# Вставь свой BOT_TOKEN в .env

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
python -m src
```

### Docker (recommended)

```bash
cp .env.example .env
# Вставь свой BOT_TOKEN в .env

docker compose up -d
```

### Tests

```bash
python -m pytest tests/ -v
```

---

## Архитектура

Модульный монолит — структурирован как микросервисы, деплоится как один юнит.

```
src/
├── bot/
│   ├── handlers/        # start, schedule, meet, meet_actions, meet_helpers,
│   │                    # vote, help, group, settings, meetings, expense, inline
│   ├── keyboards/       # Inline-клавиатуры (meeting, expense)
│   ├── middlewares/      # DB session, chat tracker, throttle
│   └── states.py        # FSM states
├── services/
│   ├── scheduling.py    # Sweep-line overlap + date/time summaries
│   ├── meeting_card.py  # Card builder + vote grouping
│   ├── debt_calculator.py # Оптимизация долгов
│   └── scheduler/       # APScheduler jobs:
│       ├── reminders.py     # Напоминания перед встречей
│       ├── deadlines.py     # Напоминания о дедлайне
│       ├── weekly_nudge.py  # Еженедельный nudge
│       ├── recurring.py     # Авто-создание повторяющихся встреч
│       ├── auto_suggest.py  # Авто-подбор встреч
│       └── cleanup.py       # Очистка устаревших слотов
├── database/
│   ├── models/          # User, Meeting, Vote, Availability, ChatMember, Expense
│   └── repositories/    # Data access layer
├── core/
│   └── config.py        # pydantic-settings
└── utils/
    └── text.py          # HTML escaping
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot Framework | aiogram 3.10 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Scheduler | APScheduler 3.10 |
| Cache / FSM | Redis 7 |
| Config | pydantic-settings |
| Tests | pytest + pytest-asyncio + aiosqlite |
| Deploy | Docker Compose |

---

## Planned

- 📸 Фото/заметки после встречи (мини-дневник тусовок)
- 📍 2GIS/Яндекс.Карты — поиск мест при создании встречи
- 🌐 Webhook mode для прода
- 🌐 Telegram Mini App (визуальный календарь, настройки)

---

## Contributing

1. Fork the repo
2. `git checkout -b feature/amazing-feature`
3. `git commit -m 'Add amazing feature'`
4. `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## Авторы

- 👤 [@kikir_kir](https://t.me/kikir_kir)
- 👤 [@KirillFain](https://t.me/KirillFain)

## License

MIT — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ for everyone who's tired of organizing meetups manually.*
