"""Shared logic for building meeting cards and vote summaries."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user import User
from src.database.models.meeting import Meeting
from src.utils.text import safe


def build_card(
    meeting: Meeting,
    votes_by_choice: dict[str, list[str]],
    creator_name: str = "",
    confirmed: bool = False,
) -> str:
    status = "✅ ПОДТВЕРЖДЕНА" if confirmed else "🗳 Голосование"
    lines = [f"🎯 <b>{safe(meeting.title)}</b>  [{status}]"]

    if meeting.proposed_datetime:
        lines.append(
            f"📅 {meeting.proposed_datetime.strftime('%d.%m.%Y %H:%M')}"
        )
    if meeting.location:
        lines.append(f"📍 {safe(meeting.location)}")

    if creator_name:
        lines.append(f"👤 Организатор: {safe(creator_name)}")

    # Recurrence
    if hasattr(meeting, "recurrence") and meeting.recurrence and meeting.recurrence != "none":
        rec_labels = {"weekly": "Каждую неделю", "biweekly": "Раз в 2 недели", "monthly": "Раз в месяц"}
        lines.append(f"🔁 {rec_labels.get(meeting.recurrence, meeting.recurrence)}")

    # Deadline
    if meeting.vote_deadline and not confirmed:
        lines.append(
            f"⏰ Голосовать до: <b>{meeting.vote_deadline.strftime('%d.%m %H:%M')}</b>"
        )

    lines.append("")

    yes_names = votes_by_choice.get("yes", [])
    no_names = votes_by_choice.get("no", [])
    maybe_names = votes_by_choice.get("maybe", [])

    if yes_names:
        lines.append(
            f"✅ Идут ({len(yes_names)}): "
            f"{', '.join(safe(n) for n in yes_names)}"
        )
    if no_names:
        lines.append(
            f"❌ Не могут ({len(no_names)}): "
            f"{', '.join(safe(n) for n in no_names)}"
        )
    if maybe_names:
        lines.append(
            f"🤔 Не уверены ({len(maybe_names)}): "
            f"{', '.join(safe(n) for n in maybe_names)}"
        )

    if not (yes_names or no_names or maybe_names):
        lines.append("🗳 Пока никто не проголосовал")

    if not confirmed:
        lines.append("")
        lines.append(
            "<i>Голосуйте кнопками ниже.\n"
            "Можно передумать — нажмите другую кнопку.\n"
            "Подтвердить/отменить может только организатор.</i>"
        )

    return "\n".join(lines)


async def get_votes_grouped(
    session: AsyncSession, meeting_id: int
) -> dict[str, list[str]]:
    from src.database.repositories.vote import VoteRepository

    vote_repo = VoteRepository(session)
    votes = await vote_repo.get_by_meeting(meeting_id)

    user_ids = [v.user_id for v in votes]
    if not user_ids:
        return {}

    stmt = select(User).where(User.id.in_(user_ids))
    result = await session.execute(stmt)
    users_map = {u.id: u for u in result.scalars().all()}

    grouped: dict[str, list[str]] = {}
    for v in votes:
        u = users_map.get(v.user_id)
        name = u.full_name if u else "???"
        grouped.setdefault(v.choice.value, []).append(name)

    return grouped
