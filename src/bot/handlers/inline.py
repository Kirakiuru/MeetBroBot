"""Inline mode — share active meetings into any chat via @BotName query."""

import logging
from hashlib import md5

from aiogram import Router, Bot
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChosenInlineResult,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.meeting import Meeting, MeetingStatus
from src.database.models.user import User
from src.database.models.chat_member import ChatMember
from src.database.repositories.user import UserRepository
from src.services.meeting_card import build_card, get_votes_grouped
from src.utils.text import safe

logger = logging.getLogger(__name__)
router = Router()


@router.inline_query()
async def on_inline_query(query: InlineQuery, session: AsyncSession):
    """
    User types @BotName in any chat.
    Shows list of their active meetings to share.
    """
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(query.from_user.id)

    if not user:
        await query.answer(
            results=[],
            cache_time=5,
            switch_pm_text="Сначала запусти бота → /start",
            switch_pm_parameter="start",
        )
        return

    # Find user's active meetings (from all their groups)
    cm_stmt = select(ChatMember.chat_id).where(ChatMember.user_id == user.id)
    cm_result = await session.execute(cm_stmt)
    chat_ids = [row[0] for row in cm_result.all()]

    meetings: list[Meeting] = []
    if chat_ids:
        stmt = (
            select(Meeting)
            .where(
                Meeting.chat_id.in_(chat_ids),
                Meeting.status == MeetingStatus.PROPOSED,
            )
            .order_by(Meeting.created_at.desc())
            .limit(20)
        )
        result = await session.execute(stmt)
        meetings = list(result.scalars().all())

    # Filter by query text if provided
    q = query.query.strip().lower()
    if q:
        meetings = [m for m in meetings if q in m.title.lower()]

    if not meetings:
        await query.answer(
            results=[],
            cache_time=5,
            switch_pm_text="Нет активных встреч. Создай → /meet",
            switch_pm_parameter="start",
        )
        return

    results = []
    for m in meetings:
        votes_grouped = await get_votes_grouped(session, m.id)

        # Creator name
        creator_stmt = select(User).where(User.id == m.creator_id)
        creator_result = await session.execute(creator_stmt)
        creator = creator_result.scalar_one_or_none()
        creator_name = creator.full_name if creator else ""

        card_text = build_card(m, votes_grouped, creator_name=creator_name)

        dt_str = ""
        if m.proposed_datetime:
            dt_str = m.proposed_datetime.strftime(" · %d.%m %H:%M")
        loc_str = f" · 📍 {m.location}" if m.location else ""

        description = f"🗳 Голосование{dt_str}{loc_str}"

        # Vote buttons
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Иду", callback_data=f"vote:{m.id}:yes"
                    ),
                    InlineKeyboardButton(
                        text="❌ Не могу", callback_data=f"vote:{m.id}:no"
                    ),
                    InlineKeyboardButton(
                        text="🤔 Не уверен", callback_data=f"vote:{m.id}:maybe"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="📢 Кто не голосовал?",
                        callback_data=f"meet_ping:{m.id}",
                    )
                ],
            ]
        )

        results.append(
            InlineQueryResultArticle(
                id=md5(f"meeting:{m.id}".encode()).hexdigest(),
                title=f"🎯 {m.title}",
                description=description,
                input_message_content=InputTextMessageContent(
                    message_text=card_text,
                    parse_mode="HTML",
                ),
                reply_markup=kb,
            )
        )

    await query.answer(results=results, cache_time=10, is_personal=True)
