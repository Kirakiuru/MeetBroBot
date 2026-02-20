"""Post-creation meeting actions: confirm, finalize, drop."""

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.meet_helpers import (
    get_user_by_id,
    is_group_chat,
    is_owner,
    parse_deadline,
    parse_state_datetime,
)
from src.bot.keyboards.expense import expense_meeting_keyboard
from src.bot.keyboards.meeting import vote_keyboard
from src.database.models.meeting import MeetingStatus
from src.database.repositories.meeting import MeetingRepository
from src.database.repositories.user import UserRepository
from src.services.meeting_card import build_card, get_votes_grouped
from src.utils.text import safe

router = Router()


# ── Confirm → create meeting + vote card ───────────────

@router.callback_query(F.data == "meet_confirm")
async def on_confirm(
    callback: CallbackQuery, state, session: AsyncSession, bot: Bot
):
    if not await is_owner(callback, state):
        return

    data = await state.get_data()
    await state.clear()

    if "title" not in data:
        await callback.answer(
            "❌ Данные потеряны — начни /meet заново", show_alert=True
        )
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    meeting_repo = MeetingRepository(session)
    meeting = await meeting_repo.create(
        creator_id=user.id,
        title=data["title"],
        proposed_datetime=parse_state_datetime(data),
        location=data.get("location"),
        chat_id=callback.message.chat.id,
        vote_deadline=parse_deadline(data),
        reminder_minutes=data.get("reminder_minutes"),
        recurrence=data.get("recurrence", "none"),
    )

    creator_name = user.full_name
    card = build_card(meeting, {}, creator_name=creator_name)
    msg = await callback.message.edit_text(
        card, reply_markup=vote_keyboard(meeting.id)
    )
    await meeting_repo.update(meeting, message_id=msg.message_id)

    # Auto-pin in groups so the card doesn't get buried
    if is_group_chat(callback.message):
        try:
            await bot.pin_chat_message(
                chat_id=callback.message.chat.id,
                message_id=msg.message_id,
                disable_notification=True,
            )
        except TelegramBadRequest:
            pass

    await callback.answer("✅ Встреча создана!")


# ── Finalize (creator only) ───────────────────────────

@router.callback_query(F.data.startswith("meet_finalize:"))
async def on_finalize(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    meeting_id = int(callback.data.split(":")[1])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    meeting_repo = MeetingRepository(session)
    meeting = await meeting_repo.get_by_id(meeting_id)

    if not meeting:
        await callback.answer("❌ Встреча не найдена")
        return
    if meeting.creator_id != user.id:
        await callback.answer(
            "⛔ Только организатор может подтвердить встречу",
            show_alert=True,
        )
        return

    await meeting_repo.update(meeting, status=MeetingStatus.CONFIRMED)

    creator = await get_user_by_id(session, meeting.creator_id)
    creator_name = creator.full_name if creator else ""

    votes = await get_votes_grouped(session, meeting_id)
    card = build_card(meeting, votes, creator_name=creator_name, confirmed=True)
    await callback.message.edit_text(
        card, reply_markup=expense_meeting_keyboard(meeting_id)
    )

    try:
        await bot.pin_chat_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            disable_notification=False,
        )
    except TelegramBadRequest:
        pass

    await callback.answer("🎉 Встреча подтверждена!")


# ── Drop (creator only) ───────────────────────────────

@router.callback_query(F.data.startswith("meet_drop:"))
async def on_drop(callback: CallbackQuery, session: AsyncSession):
    meeting_id = int(callback.data.split(":")[1])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    meeting_repo = MeetingRepository(session)
    meeting = await meeting_repo.get_by_id(meeting_id)

    if not meeting:
        await callback.answer("❌ Встреча не найдена")
        return
    if meeting.creator_id != user.id:
        await callback.answer(
            "⛔ Только организатор может отменить встречу",
            show_alert=True,
        )
        return

    await meeting_repo.update(meeting, status=MeetingStatus.CANCELLED)
    await callback.message.edit_text(
        f"🚫 <b>{safe(meeting.title)}</b> — встреча отменена."
    )
    await callback.answer("Отменена")
