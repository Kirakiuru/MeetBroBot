from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.meeting import MeetingStatus
from src.database.models.user import User
from src.database.models.vote import VoteChoice
from src.database.repositories.meeting import MeetingRepository
from src.database.repositories.vote import VoteRepository
from src.database.repositories.user import UserRepository
from src.bot.keyboards.meeting import vote_keyboard
from src.services.meeting_card import build_card, get_votes_grouped

router = Router()

CHOICE_MAP = {
    "yes": VoteChoice.YES,
    "no": VoteChoice.NO,
    "maybe": VoteChoice.MAYBE,
}

CHOICE_EMOJI = {
    VoteChoice.YES: "✅",
    VoteChoice.NO: "❌",
    VoteChoice.MAYBE: "🤔",
}


@router.callback_query(F.data.startswith("vote:"))
async def on_vote(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    _, meeting_id_str, choice_str = callback.data.split(":")
    meeting_id = int(meeting_id_str)
    choice = CHOICE_MAP.get(choice_str)

    if choice is None:
        await callback.answer("❌ Неизвестный выбор")
        return

    # Ensure user exists
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if user is None:
        user = await user_repo.create(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
        )

    # Get meeting
    meeting_repo = MeetingRepository(session)
    meeting = await meeting_repo.get_by_id(meeting_id)

    if meeting is None:
        await callback.answer("❌ Встреча не найдена")
        return

    if meeting.status != MeetingStatus.PROPOSED:
        await callback.answer("⏹ Голосование закрыто")
        return

    # Check deadline
    if meeting.vote_deadline and datetime.now() > meeting.vote_deadline:
        await callback.answer(
            "⏰ Дедлайн голосования истёк!", show_alert=True
        )
        return

    # Upsert vote (returns (vote, is_changed))
    vote_repo = VoteRepository(session)
    vote, is_changed = await vote_repo.upsert(
        meeting_id=meeting.id,
        user_id=user.id,
        choice=choice,
    )

    # Get creator name
    creator = None
    if meeting.creator_id:
        stmt = select(User).where(User.id == meeting.creator_id)
        result = await session.execute(stmt)
        creator = result.scalar_one_or_none()
    creator_name = creator.full_name if creator else ""

    # Rebuild card
    votes_by_choice = await get_votes_grouped(session, meeting_id)
    card = build_card(meeting, votes_by_choice, creator_name=creator_name)

    try:
        await callback.message.edit_text(
            card,
            reply_markup=vote_keyboard(meeting.id),
        )
    except TelegramBadRequest:
        pass  # Message not modified (same vote clicked again)

    emoji = CHOICE_EMOJI[choice]
    if is_changed:
        await callback.answer(f"{emoji} Голос изменён!")
    else:
        await callback.answer(f"{emoji} Голос принят!")
