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

## Фичи (v0.1)

| Фича | Описание |
|-------|----------|
| 📅 `/schedule` | Интерактивный календарь с пресетами времени |
| 🎯 `/meet` | Создание встречи: пресеты названий, умный подбор дат, локация, дедлайн |
| 🧠 Smart matching | Бот находит когда все свободны (sweep-line алгоритм) |
| 🗳 Голосование | ✅ Иду / ❌ Не могу / 🤔 Не уверен — можно передумать |
| ⏰ Дедлайн | 1 час / 3 часа / до завтра / 2 дня / без дедлайна |
| 📌 Авто-пин | Карточка встречи закрепляется в чате |
| 👑 Контроль | Подтвердить/отменить может только организатор |
| 🛡 Безопасность | HTML-экранирование, rate-limiting, creator-only guards |
| 👥 Группы | Welcome-сообщение, авто-трекинг участников |

---

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis (опционально, fallback на in-memory)
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))

### Local

```bash
git clone https://github.com/KirillFain/MeetBroBot.git
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

---

## Архитектура

Модульный монолит — структурирован как микросервисы, деплоится как один юнит.

```
src/
├── bot/
│   ├── handlers/      # start, schedule, meet, vote, help, group
│   ├── keyboards/     # Inline-клавиатуры
│   ├── middlewares/    # DB session, chat tracker, throttle
│   └── states.py      # FSM states
├── services/
│   ├── scheduling.py  # Sweep-line overlap + date/time summaries
│   ├── meeting_card.py # Card builder + vote grouping
│   └── user.py        # User get_or_create
├── database/
│   ├── models/        # User, Meeting, Vote, Availability, ChatMember
│   └── repositories/  # Data access layer
├── core/
│   └── config.py      # pydantic-settings
└── utils/
    └── text.py        # HTML escaping
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot Framework | aiogram 3.10 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Cache / FSM | Redis 7 |
| Config | pydantic-settings |
| Deploy | Docker Compose |

---

## Planned

- 📆 Google Calendar sync
- 🔔 Напоминания перед встречей
- 📍 Карта с точками встречи
- 🛒 Список покупок (кто что несёт)
- 🌤 Прогноз погоды для outdoor-тусовок
- 🎂 Авто-планирование дней рождения
- 📸 Сбор фоток → общий альбом
- 🤖 AI-рекомендации по времени и месту

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
