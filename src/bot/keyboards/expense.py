"""Keyboards for expense splitting."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def expense_amount_keyboard() -> InlineKeyboardMarkup:
    """Quick amount presets."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="500 ₽", callback_data="exp_amt:500"),
                InlineKeyboardButton(text="1000 ₽", callback_data="exp_amt:1000"),
                InlineKeyboardButton(text="2000 ₽", callback_data="exp_amt:2000"),
            ],
            [
                InlineKeyboardButton(text="3000 ₽", callback_data="exp_amt:3000"),
                InlineKeyboardButton(text="5000 ₽", callback_data="exp_amt:5000"),
                InlineKeyboardButton(text="10000 ₽", callback_data="exp_amt:10000"),
            ],
            [
                InlineKeyboardButton(text="✏️ Своя сумма", callback_data="exp_amt_custom"),
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="exp_cancel"),
            ],
        ]
    )


def expense_split_keyboard(
    users: list[tuple[int, str]],
    selected_ids: set[int],
) -> InlineKeyboardMarkup:
    """Toggle users to include in the split. Selected users are marked ✅."""
    rows: list[list[InlineKeyboardButton]] = []

    for uid, name in users:
        mark = "✅" if uid in selected_ids else "⬜️"
        rows.append([
            InlineKeyboardButton(
                text=f"{mark} {name}",
                callback_data=f"exp_toggle:{uid}",
            )
        ])

    rows.append([
        InlineKeyboardButton(text="✅ Все", callback_data="exp_toggle_all"),
    ])
    rows.append([
        InlineKeyboardButton(text="🚀 Готово", callback_data="exp_split_done"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="exp_cancel"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def expense_meeting_keyboard(meeting_id: int) -> InlineKeyboardMarkup:
    """Button to add expense from meeting card."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Добавить расход",
                    callback_data=f"exp_from_meet:{meeting_id}",
                ),
                InlineKeyboardButton(
                    text="📊 Долги",
                    callback_data=f"exp_debts_meet:{meeting_id}",
                ),
            ]
        ]
    )


def settle_keyboard(debts: list[dict]) -> InlineKeyboardMarkup:
    """Mark a debt as settled."""
    rows = []
    for d in debts:
        rows.append([
            InlineKeyboardButton(
                text=f"✅ {d['from_name']} → {d['to_name']}: {d['amount']:.0f} ₽",
                callback_data=f"exp_settle:{d['from_id']}:{d['to_id']}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
