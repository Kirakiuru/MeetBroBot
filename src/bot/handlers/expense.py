"""Expense splitting handlers: /expense, /debts, inline buttons."""

from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ForceReply
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.expense import (
    expense_amount_keyboard,
    expense_split_keyboard,
)
from src.bot.states import ExpenseStates
from src.database.repositories.expense import ExpenseRepository
from src.database.repositories.user import UserRepository
from src.database.repositories.chat_member import ChatMemberRepository
from src.services.debt_calculator import calculate_debts
from src.utils.text import safe

router = Router()

EXPENSE_PRESETS = [
    ("🍺 Бар", "Бар"),
    ("🍕 Еда", "Еда"),
    ("🚕 Такси", "Такси"),
    ("🎬 Развлечения", "Развлечения"),
]


# ── /expense ──────────────────────────────────────────

@router.message(Command("expense"))
async def cmd_expense(message: Message, state: FSMContext, session: AsyncSession):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("💰 Команда /expense работает только в групповых чатах.")
        return

    await state.clear()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйся → /start")
        return

    await state.update_data(
        paid_by_id=user.id,
        paid_by_name=user.full_name,
        chat_id=message.chat.id,
        meeting_id=None,
    )
    await state.set_state(ExpenseStates.entering_title)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    rows = []
    for i in range(0, len(EXPENSE_PRESETS), 2):
        row = []
        for j in range(i, min(i + 2, len(EXPENSE_PRESETS))):
            label, val = EXPENSE_PRESETS[j]
            row.append(InlineKeyboardButton(text=label, callback_data=f"exp_title:{val}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✏️ Своё", callback_data="exp_title_custom")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="exp_cancel")])

    await message.answer(
        "💰 <b>Новый расход</b>\n\nЗа что платил(а)?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


# ── Title preset ──────────────────────────────────────

@router.callback_query(F.data.startswith("exp_title:"))
async def on_exp_title_preset(callback: CallbackQuery, state: FSMContext):
    title = callback.data.split(":", 1)[1]
    await state.update_data(title=title)
    await callback.message.edit_text(f"💰 <b>{safe(title)}</b>\n\nСколько?")
    await state.set_state(ExpenseStates.entering_amount)
    await callback.message.answer(
        "Выбери сумму или введи свою:",
        reply_markup=expense_amount_keyboard(),
    )
    await callback.answer()


# ── Title custom ──────────────────────────────────────

@router.callback_query(F.data == "exp_title_custom")
async def on_exp_title_custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ExpenseStates.entering_title)
    await callback.message.edit_text("💰 Введи название расхода:")
    await callback.message.answer(
        "Название:",
        reply_markup=ForceReply(input_field_placeholder="Пицца на всех"),
    )
    await callback.answer()


@router.message(ExpenseStates.entering_title, F.text)
async def on_exp_title_typed(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title or len(title) > 200:
        await message.answer(
            "❌ 1–200 символов.",
            reply_markup=ForceReply(input_field_placeholder="Название"),
        )
        return
    await state.update_data(title=title)
    await state.set_state(ExpenseStates.entering_amount)
    await message.answer(
        f"💰 <b>{safe(title)}</b>\n\nВыбери сумму или введи свою:",
        reply_markup=expense_amount_keyboard(),
    )


# ── Amount preset ─────────────────────────────────────

@router.callback_query(F.data.startswith("exp_amt:"))
async def on_exp_amount_preset(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    amount = int(callback.data.split(":")[1])
    await state.update_data(amount=amount)
    await _go_to_participants(callback.message, state, session, edit=True)
    await callback.answer()


# ── Amount custom ─────────────────────────────────────

@router.callback_query(F.data == "exp_amt_custom")
async def on_exp_amount_custom(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("💰 Введи сумму (число):")
    await callback.message.answer(
        "Сумма:",
        reply_markup=ForceReply(input_field_placeholder="1500"),
    )
    await callback.answer()


@router.message(ExpenseStates.entering_amount, F.text)
async def on_exp_amount_typed(message: Message, state: FSMContext, session: AsyncSession):
    try:
        amount = Decimal(message.text.strip().replace(",", ".").replace(" ", ""))
        if amount <= 0 or amount > 1_000_000:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer(
            "❌ Введи число от 1 до 1 000 000.",
            reply_markup=ForceReply(input_field_placeholder="1500"),
        )
        return
    await state.update_data(amount=float(amount))
    await _go_to_participants(message, state, session, edit=False)


# ── Participant selection ─────────────────────────────

async def _go_to_participants(
    msg: Message, state: FSMContext, session: AsyncSession, edit: bool = False
):
    data = await state.get_data()
    chat_id = data["chat_id"]

    cm_repo = ChatMemberRepository(session)
    user_ids = await cm_repo.get_user_ids_in_chat(chat_id)

    users = []
    for uid in user_ids:
        from sqlalchemy import select
        from src.database.models.user import User
        stmt = select(User).where(User.id == uid)
        result = await session.execute(stmt)
        u = result.scalar_one_or_none()
        if u:
            users.append((u.id, u.full_name))

    # Pre-select all
    selected = {uid for uid, _ in users}
    await state.update_data(
        participants=users,
        selected_ids=list(selected),
    )
    await state.set_state(ExpenseStates.choosing_participants)

    text = (
        f"💰 <b>{safe(data['title'])}</b> — {data['amount']:.0f} ₽\n"
        f"Платил(а): {safe(data['paid_by_name'])}\n\n"
        f"Кто участвует? (выбери кто скидывается)"
    )

    kb = expense_split_keyboard(users, selected)
    if edit:
        await msg.edit_text(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


# ── Toggle participant ────────────────────────────────

@router.callback_query(F.data.startswith("exp_toggle:"))
async def on_exp_toggle(callback: CallbackQuery, state: FSMContext):
    uid = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = set(data.get("selected_ids", []))

    if uid in selected:
        selected.discard(uid)
    else:
        selected.add(uid)

    await state.update_data(selected_ids=list(selected))

    users = data.get("participants", [])
    kb = expense_split_keyboard(users, selected)

    text = (
        f"💰 <b>{safe(data['title'])}</b> — {data['amount']:.0f} ₽\n"
        f"Платил(а): {safe(data['paid_by_name'])}\n\n"
        f"Кто участвует? ({len(selected)} выбрано)"
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "exp_toggle_all")
async def on_exp_toggle_all(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    users = data.get("participants", [])
    selected = set(data.get("selected_ids", []))

    all_ids = {uid for uid, _ in users}
    if selected == all_ids:
        selected = set()  # deselect all
    else:
        selected = all_ids  # select all

    await state.update_data(selected_ids=list(selected))
    kb = expense_split_keyboard(users, selected)

    text = (
        f"💰 <b>{safe(data['title'])}</b> — {data['amount']:.0f} ₽\n"
        f"Платил(а): {safe(data['paid_by_name'])}\n\n"
        f"Кто участвует? ({len(selected)} выбрано)"
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── Confirm split ─────────────────────────────────────

@router.callback_query(F.data == "exp_split_done")
async def on_exp_split_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    selected_ids = data.get("selected_ids", [])

    if len(selected_ids) < 1:
        await callback.answer("❌ Выбери хотя бы одного участника", show_alert=True)
        return

    expense_repo = ExpenseRepository(session)
    await expense_repo.create(
        chat_id=data["chat_id"],
        paid_by_id=data["paid_by_id"],
        title=data["title"],
        amount=Decimal(str(data["amount"])),
        share_user_ids=selected_ids,
        meeting_id=data.get("meeting_id"),
    )

    await state.clear()

    per_person = Decimal(str(data["amount"])) / len(selected_ids)
    users_map = {uid: name for uid, name in data.get("participants", [])}
    names = ", ".join(safe(users_map.get(uid, "???")) for uid in selected_ids)

    await callback.message.edit_text(
        f"✅ <b>Расход добавлен!</b>\n\n"
        f"💰 <b>{safe(data['title'])}</b> — {data['amount']:.0f} ₽\n"
        f"💳 Платил(а): {safe(data['paid_by_name'])}\n"
        f"👥 Участники ({len(selected_ids)}): {names}\n"
        f"💵 По {per_person:.0f} ₽ с человека\n\n"
        f"📊 Посмотреть долги → /debts"
    )
    await callback.answer("✅ Расход добавлен!")


# ── Cancel ────────────────────────────────────────────

@router.callback_query(F.data == "exp_cancel")
async def on_exp_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Расход отменён.")
    await callback.answer()


# ── /debts ────────────────────────────────────────────

@router.message(Command("debts"))
async def cmd_debts(message: Message, session: AsyncSession):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("📊 Команда /debts работает только в групповых чатах.")
        return

    debts = await calculate_debts(session, chat_id=message.chat.id)

    if not debts:
        await message.answer("✅ <b>Все квиты!</b>\n\nНикто никому не должен. 🎉")
        return

    lines = ["📊 <b>Кто кому должен:</b>\n"]
    total = Decimal("0")
    for d in debts:
        lines.append(
            f"  {safe(d['from_name'])} → {safe(d['to_name'])}: "
            f"<b>{d['amount']:.0f} ₽</b>"
        )
        total += d["amount"]

    lines.append(f"\n💰 Всего к переводу: <b>{total:.0f} ₽</b>")
    lines.append("\n<i>Добавить расход: /expense</i>")

    await message.answer("\n".join(lines))


# ── Expense from meeting card ─────────────────────────

@router.callback_query(F.data.startswith("exp_from_meet:"))
async def on_exp_from_meeting(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    meeting_id = int(callback.data.split(":")[1])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ /start сначала", show_alert=True)
        return

    await state.clear()
    await state.update_data(
        paid_by_id=user.id,
        paid_by_name=user.full_name,
        chat_id=callback.message.chat.id,
        meeting_id=meeting_id,
    )
    await state.set_state(ExpenseStates.entering_title)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    rows = []
    for i in range(0, len(EXPENSE_PRESETS), 2):
        row = []
        for j in range(i, min(i + 2, len(EXPENSE_PRESETS))):
            label, val = EXPENSE_PRESETS[j]
            row.append(InlineKeyboardButton(text=label, callback_data=f"exp_title:{val}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✏️ Своё", callback_data="exp_title_custom")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="exp_cancel")])

    await callback.message.answer(
        "💰 <b>Новый расход для встречи</b>\n\nЗа что платил(а)?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


# ── Debts for a specific meeting ──────────────────────

@router.callback_query(F.data.startswith("exp_debts_meet:"))
async def on_debts_from_meeting(callback: CallbackQuery, session: AsyncSession):
    meeting_id = int(callback.data.split(":")[1])

    debts = await calculate_debts(
        session, chat_id=callback.message.chat.id, meeting_id=meeting_id
    )

    if not debts:
        await callback.answer("✅ Расходов пока нет", show_alert=True)
        return

    lines = ["📊 <b>Долги по встрече:</b>\n"]
    for d in debts:
        lines.append(
            f"  {safe(d['from_name'])} → {safe(d['to_name'])}: "
            f"<b>{d['amount']:.0f} ₽</b>"
        )

    lines.append("\n💰 Добавить расход — кнопка выше")
    await callback.message.answer("\n".join(lines))
    await callback.answer()
