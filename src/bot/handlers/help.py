from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

HELP_TEXT_PM = """
🤝 <b>MeetBroBot</b> — бот, который организует тусовки за тебя.

<b>Что делать в личке:</b>
📅 /schedule — задать своё расписание (когда ты свободен)
⚙️ /settings — настройки напоминаний
🆕 /whatsnew — что нового в боте

<b>Что делать в группе:</b>
🎯 /meet — создать встречу (бот подберёт время по расписаниям)
📋 /meetings — список активных встреч
💰 /expense — добавить расход (разделить счёт)
📊 /debts — кто кому должен

<b>Как это работает:</b>
1️⃣ Каждый заполняет /schedule здесь, в личке
2️⃣ Добавьте бота в групповой чат
3️⃣ Кто-то пишет /meet — бот покажет пересечения
4️⃣ Все голосуют ✅ / ❌ / 🤔 под карточкой
5️⃣ Собрались — потусили — повторили 🔁

<b>Фишки:</b>
• Умный подбор дат — видно, когда все свободны
• Повторяющиеся встречи (каждую неделю / 2 нед / месяц)
• Разделение расходов после тусовки
• Inline-режим — делись встречами через @MeetMyBroBot
• Напоминания перед встречей и дедлайном

━━━━━━━━━━━━━━━━━━━

<i>Создано с ❤️ двумя чуваками, которым надоело быть организаторами:</i>

👤 @kikir_kir · 👤 @KirillFain

<b>GitHub:</b> <a href="https://github.com/Kirakiuru/MeetBroBot">github.com/Kirakiuru/MeetBroBot</a>

<i>Если ты это читаешь — ты уже один из первых.
Мы строим штуку, которую сами хотим использовать.
⭐ на гитхабе = +1 к мотивации.</i>
""".strip()


HELP_TEXT_GROUP = """
🤝 <b>MeetBroBot</b> — организатор тусовок.

<b>Команды:</b>
🎯 /meet — создать встречу (бот подберёт время)
📋 /meetings — список активных встреч
📅 /schedule — заполнить своё расписание
💰 /expense — добавить расход
📊 /debts — кто кому должен
🆕 /whatsnew — что нового
ℹ️ /help — эта справка

<b>⚡ Важно:</b> расписание лучше заполнять <b>в личке с ботом</b> — так удобнее.
Бот сам найдёт пересечения, когда все свободны.

━━━━━━━━━━━━━━━━━━━
👤 @kikir_kir · 👤 @KirillFain
<a href="https://github.com/Kirakiuru/MeetBroBot">GitHub</a> · ⭐ = +1 к мотивации
""".strip()


# ── Changelog (shown to users via /whatsnew) ──────────

CHANGELOG = """
🆕 <b>Что нового в MeetBroBot</b>

<b>v0.3</b> — 21.02.2026
🔁 Повторяющиеся встречи — каждую неделю / 2 нед / месяц
💰 Разделение расходов — /expense + /debts
🧹 Рефакторинг — код стал чище и быстрее
🤖 Авто-подбор встреч — бот сам предложит время

<b>v0.2</b> — 20.02.2026
🔔 Напоминания перед встречей (15м / 30м / 1ч / 3ч)
⏰ Дедлайн голосования + авто-напоминание
📅 Еженедельное напоминание заполнить расписание
📋 /meetings — список активных встреч
📢 «Кто не голосовал?» — кнопка-пинг
⚙️ /settings — настройки напоминаний
🗑 Авто-очистка старых слотов
🧪 34 теста (pytest)
🤖 Inline-режим (@MeetMyBroBot)
⚡ CI/CD (GitHub Actions)
🛡 Sentry (опционально)

<b>v0.1</b> — 20.02.2026
📅 Расписание с календарём и пресетами
🎯 Создание встреч с умным подбором дат
🗳 Голосование ✅ / ❌ / 🤔
📌 Авто-пин карточки в чате
👥 Групповой режим с трекингом участников
🛡 HTML-экранирование + rate-limiting
""".strip()


@router.message(Command("help"))
async def cmd_help(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    text = HELP_TEXT_GROUP if is_group else HELP_TEXT_PM
    await message.answer(text, disable_web_page_preview=True)


@router.message(Command("whatsnew"))
async def cmd_whatsnew(message: Message):
    await message.answer(CHANGELOG)
