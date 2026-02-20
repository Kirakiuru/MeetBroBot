from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# Preset time slots
TIME_PRESETS = [
    ("🌅 Утро (9–12)", "09:00", "12:00"),
    ("☀️ День (12–17)", "12:00", "17:00"),
    ("🌆 Вечер (17–21)", "17:00", "21:00"),
    ("🌙 Ночь (21–00)", "21:00", "23:59"),
]


def _monday_of_week(d: date) -> date:
    """Get Monday of the week containing `d`."""
    return d - timedelta(days=d.weekday())


def week_calendar_keyboard(week_offset: int = 0) -> InlineKeyboardMarkup:
    """
    Week calendar with real dates.
    week_offset: 0 = current week, 1 = next week, -1 = prev week.
    """
    today = date.today()
    monday = _monday_of_week(today) + timedelta(weeks=week_offset)

    rows: list[list[InlineKeyboardButton]] = []

    # Week header: "24.02 — 02.03"
    sunday = monday + timedelta(days=6)
    header = f"📅 {monday.strftime('%d.%m')} — {sunday.strftime('%d.%m')}"
    rows.append([InlineKeyboardButton(text=header, callback_data="noop")])

    # Days row 1: Mon-Thu
    row1 = []
    for i in range(4):
        d = monday + timedelta(days=i)
        row1.append(_day_button(d, today))
    rows.append(row1)

    # Days row 2: Fri-Sun
    row2 = []
    for i in range(4, 7):
        d = monday + timedelta(days=i)
        row2.append(_day_button(d, today))
    rows.append(row2)

    # Navigation
    nav_row = []
    if week_offset > 0:
        nav_row.append(
            InlineKeyboardButton(text="← Пред.", callback_data=f"sched_week:{week_offset - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(text="След. →", callback_data=f"sched_week:{week_offset + 1}")
    )
    rows.append(nav_row)

    # Utility buttons
    rows.append(
        [InlineKeyboardButton(text="📋 Моё расписание", callback_data="sched_show")]
    )
    rows.append(
        [
            InlineKeyboardButton(text="🗑 Очистить", callback_data="sched_clear"),
            InlineKeyboardButton(text="✅ Готово", callback_data="sched_done"),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _day_button(d: date, today: date) -> InlineKeyboardButton:
    """Single day button. Past days are crossed out."""
    day_name = DAYS_SHORT[d.weekday()]
    label = f"{day_name} {d.strftime('%d.%m')}"

    if d == today:
        label = f"• {label}"  # marker for today

    if d < today:
        # Past day — show but disabled
        return InlineKeyboardButton(text=f"  {label}", callback_data="noop")

    return InlineKeyboardButton(
        text=label, callback_data=f"sched_date:{d.isoformat()}"
    )


def time_presets_keyboard(selected_date: str) -> InlineKeyboardMarkup:
    """Time preset buttons + custom input."""
    rows: list[list[InlineKeyboardButton]] = []

    # 2x2 grid of presets
    rows.append([
        InlineKeyboardButton(
            text=TIME_PRESETS[0][0],
            callback_data=f"sched_time:{selected_date}:{TIME_PRESETS[0][1]}-{TIME_PRESETS[0][2]}",
        ),
        InlineKeyboardButton(
            text=TIME_PRESETS[1][0],
            callback_data=f"sched_time:{selected_date}:{TIME_PRESETS[1][1]}-{TIME_PRESETS[1][2]}",
        ),
    ])
    rows.append([
        InlineKeyboardButton(
            text=TIME_PRESETS[2][0],
            callback_data=f"sched_time:{selected_date}:{TIME_PRESETS[2][1]}-{TIME_PRESETS[2][2]}",
        ),
        InlineKeyboardButton(
            text=TIME_PRESETS[3][0],
            callback_data=f"sched_time:{selected_date}:{TIME_PRESETS[3][1]}-{TIME_PRESETS[3][2]}",
        ),
    ])

    # Whole day
    rows.append([
        InlineKeyboardButton(
            text="🌍 Весь день",
            callback_data=f"sched_time:{selected_date}:00:00-23:59",
        ),
    ])

    # Custom time
    rows.append([
        InlineKeyboardButton(
            text="⌨️ Своё время",
            callback_data=f"sched_custom:{selected_date}",
        ),
    ])

    # Back
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад к датам", callback_data="sched_back"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_calendar_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к датам", callback_data="sched_back")],
        ]
    )
