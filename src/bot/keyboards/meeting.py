from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# ── Title presets ──────────────────────────────────────

TITLE_PRESETS = [
    ("🥩 Шашлыки", "Шашлыки"),
    ("🎬 Кино", "Кино"),
    ("🍺 Бар", "Бар"),
    ("🎲 Настолки", "Настолки"),
    ("🚶 Прогулка", "Прогулка"),
    ("🍕 Поесть", "Поесть"),
]


def title_presets_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    rows.append([
        InlineKeyboardButton(text=TITLE_PRESETS[0][0], callback_data=f"meet_title:{TITLE_PRESETS[0][1]}"),
        InlineKeyboardButton(text=TITLE_PRESETS[1][0], callback_data=f"meet_title:{TITLE_PRESETS[1][1]}"),
        InlineKeyboardButton(text=TITLE_PRESETS[2][0], callback_data=f"meet_title:{TITLE_PRESETS[2][1]}"),
    ])
    rows.append([
        InlineKeyboardButton(text=TITLE_PRESETS[3][0], callback_data=f"meet_title:{TITLE_PRESETS[3][1]}"),
        InlineKeyboardButton(text=TITLE_PRESETS[4][0], callback_data=f"meet_title:{TITLE_PRESETS[4][1]}"),
        InlineKeyboardButton(text=TITLE_PRESETS[5][0], callback_data=f"meet_title:{TITLE_PRESETS[5][1]}"),
    ])
    rows.append([
        InlineKeyboardButton(text="✏️ Своё название", callback_data="meet_title_custom"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Vote ───────────────────────────────────────────────

def vote_keyboard(meeting_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Иду", callback_data=f"vote:{meeting_id}:yes"
                ),
                InlineKeyboardButton(
                    text="❌ Не могу", callback_data=f"vote:{meeting_id}:no"
                ),
                InlineKeyboardButton(
                    text="🤔 Не уверен", callback_data=f"vote:{meeting_id}:maybe"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📢 Кто не голосовал?",
                    callback_data=f"meet_ping:{meeting_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👑 Подтвердить",
                    callback_data=f"meet_finalize:{meeting_id}",
                ),
                InlineKeyboardButton(
                    text="👑 Отменить",
                    callback_data=f"meet_drop:{meeting_id}",
                ),
            ],
        ]
    )


# ── Confirm ────────────────────────────────────────────

def confirm_meeting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Создать", callback_data="meet_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="meet_cancel"),
            ]
        ]
    )


# ── Deadline ───────────────────────────────────────────

def deadline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏱ 1 час", callback_data="meet_dl:1h"),
                InlineKeyboardButton(text="⏱ 3 часа", callback_data="meet_dl:3h"),
            ],
            [
                InlineKeyboardButton(text="⏱ До завтра", callback_data="meet_dl:tomorrow"),
                InlineKeyboardButton(text="⏱ 2 дня", callback_data="meet_dl:2d"),
            ],
            [
                InlineKeyboardButton(text="♾ Без дедлайна", callback_data="meet_dl:none"),
            ],
        ]
    )


# ── Meeting reminder ──────────────────────────────────

def reminder_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔔 За 15 мин", callback_data="meet_rem:15"),
                InlineKeyboardButton(text="🔔 За 30 мин", callback_data="meet_rem:30"),
            ],
            [
                InlineKeyboardButton(text="🔔 За 1 час", callback_data="meet_rem:60"),
                InlineKeyboardButton(text="🔔 За 3 часа", callback_data="meet_rem:180"),
            ],
            [
                InlineKeyboardButton(text="🔕 Без напоминания", callback_data="meet_rem:none"),
            ],
        ]
    )


# ── Location ───────────────────────────────────────────

def location_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Написать адрес", callback_data="meet_loc_text")],
            [
                InlineKeyboardButton(text="🌐 Онлайн", callback_data="meet_loc:online"),
                InlineKeyboardButton(text="🤷 Решим позже", callback_data="meet_loc:later"),
            ],
        ]
    )


# ── Slot suggestions ──────────────────────────────────

def slot_pick_keyboard(slots: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for i, slot in enumerate(slots):
        d = slot["date"]
        day_name = DAYS_SHORT[d.weekday()]
        label = (
            f"{day_name} {d.strftime('%d.%m')} "
            f"{slot['start'].strftime('%H:%M')}–{slot['end'].strftime('%H:%M')} "
            f"({slot['count']} 👤)"
        )
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"meet_slot:{i}")
        ])

    rows.append([
        InlineKeyboardButton(text="📅 Выбрать свою дату", callback_data="meet_pick_date:0"),
    ])
    rows.append([
        InlineKeyboardButton(text="⏭ Без даты", callback_data="meet_skip:datetime"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Calendar for date picking ──────────────────────────

def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def date_pick_keyboard(
    week_offset: int = 0,
    avail_summary: dict[str, dict] | None = None,
) -> InlineKeyboardMarkup:
    """Week calendar with availability annotations."""
    today = date.today()
    monday = _monday_of_week(today) + timedelta(weeks=week_offset)
    sunday = monday + timedelta(days=6)

    if avail_summary is None:
        avail_summary = {}

    rows: list[list[InlineKeyboardButton]] = []

    header = f"📅 {monday.strftime('%d.%m')} — {sunday.strftime('%d.%m')}"
    rows.append([InlineKeyboardButton(text=header, callback_data="noop")])

    # Mon–Thu
    row1 = []
    for i in range(4):
        d = monday + timedelta(days=i)
        info = avail_summary.get(d.isoformat(), {})
        cnt = info.get("total", 0) if isinstance(info, dict) else 0
        row1.append(_day_btn(d, today, cnt))
    rows.append(row1)

    # Fri–Sun
    row2 = []
    for i in range(4, 7):
        d = monday + timedelta(days=i)
        info = avail_summary.get(d.isoformat(), {})
        cnt = info.get("total", 0) if isinstance(info, dict) else 0
        row2.append(_day_btn(d, today, cnt))
    rows.append(row2)

    # Nav
    nav = []
    if week_offset > 0:
        nav.append(InlineKeyboardButton(text="← Пред.", callback_data=f"meet_pick_date:{week_offset - 1}"))
    nav.append(InlineKeyboardButton(text="След. →", callback_data=f"meet_pick_date:{week_offset + 1}"))
    rows.append(nav)

    rows.append([
        InlineKeyboardButton(text="⏭ Без даты", callback_data="meet_skip:datetime"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _day_btn(d: date, today: date, avail_count: int = 0) -> InlineKeyboardButton:
    day_name = DAYS_SHORT[d.weekday()]
    label = f"{day_name} {d.strftime('%d.%m')}"
    if avail_count:
        label += f" ({avail_count}👤)"
    if d == today:
        label = f"• {label}"
    if d < today:
        return InlineKeyboardButton(text=f"  {label}", callback_data="noop")
    return InlineKeyboardButton(text=label, callback_data=f"meet_date:{d.isoformat()}")


# ── Time presets for chosen date ───────────────────────

TIME_PRESETS = [
    ("🌅 Утро 9–12", "09:00", "morning"),
    ("☀️ День 12–17", "12:00", "day"),
    ("🌆 Вечер 17–21", "17:00", "evening"),
    ("🌙 Ночь 21–00", "21:00", "night"),
]


def time_pick_keyboard(
    date_str: str,
    date_info: dict | None = None,
) -> InlineKeyboardMarkup:
    """Time presets annotated with per-period availability count."""
    if date_info is None:
        date_info = {}

    rows: list[list[InlineKeyboardButton]] = []

    for i in range(0, len(TIME_PRESETS), 2):
        row = []
        for j in range(i, min(i + 2, len(TIME_PRESETS))):
            label, time_val, period_key = TIME_PRESETS[j]
            cnt = date_info.get(period_key, 0)
            if cnt:
                label = f"{label} [{cnt}👤]"
            row.append(
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"meet_time:{date_str}:{time_val}",
                )
            )
        rows.append(row)

    rows.append([
        InlineKeyboardButton(text="⬅️ Назад к датам", callback_data="meet_pick_date:0"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
