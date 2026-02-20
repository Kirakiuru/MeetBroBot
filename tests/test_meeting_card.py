"""Tests for meeting card builder and vote grouping."""

from datetime import datetime

from src.database.models.meeting import Meeting, MeetingStatus
from src.database.models.vote import VoteChoice
from src.database.repositories.user import UserRepository
from src.database.repositories.meeting import MeetingRepository
from src.database.repositories.vote import VoteRepository
from src.services.meeting_card import build_card, get_votes_grouped


class TestBuildCard:
    def _make_meeting(self, **kwargs) -> Meeting:
        """Helper to create a Meeting instance without DB (bypass SA instrumentation)."""
        defaults = dict(
            id=1,
            creator_id=1,
            title="Test Meeting",
            description=None,
            status=MeetingStatus.PROPOSED,
            chat_id=None,
            message_id=None,
            proposed_datetime=None,
            confirmed_datetime=None,
            location=None,
            vote_deadline=None,
            reminder_minutes=None,
            reminder_sent=False,
            deadline_reminder_sent=False,
        )
        defaults.update(kwargs)
        # Use constructor — SA will handle instrumentation
        return Meeting(**defaults)

    def test_basic_card(self):
        m = self._make_meeting(title="Шашлыки")
        card = build_card(m, {}, creator_name="Kir")

        assert "Шашлыки" in card
        assert "Kir" in card
        assert "Голосование" in card
        assert "никто не проголосовал" in card

    def test_card_with_votes(self):
        m = self._make_meeting(title="Бар")
        votes = {"yes": ["Alice", "Bob"], "no": ["Charlie"], "maybe": ["Dave"]}
        card = build_card(m, votes, creator_name="Eve")

        assert "Идут (2)" in card
        assert "Alice" in card
        assert "Не могут (1)" in card
        assert "Не уверены (1)" in card

    def test_card_with_datetime_and_location(self):
        m = self._make_meeting(
            title="Кино",
            proposed_datetime=datetime(2026, 3, 15, 19, 0),
            location="IMAX Авиапарк",
        )
        card = build_card(m, {}, creator_name="X")

        assert "15.03.2026 19:00" in card
        assert "IMAX Авиапарк" in card

    def test_card_with_deadline(self):
        m = self._make_meeting(
            title="D",
            vote_deadline=datetime(2026, 3, 20, 12, 0),
        )
        card = build_card(m, {}, creator_name="Y")
        assert "Голосовать до" in card
        assert "20.03 12:00" in card

    def test_confirmed_card(self):
        m = self._make_meeting(title="Done")
        card = build_card(m, {"yes": ["A"]}, creator_name="Z", confirmed=True)

        assert "ПОДТВЕРЖДЕНА" in card
        assert "Голосовать до" not in card  # no deadline shown when confirmed
        assert "передумать" not in card  # no voting hint

    def test_html_escaping(self):
        m = self._make_meeting(title="<script>alert(1)</script>")
        card = build_card(m, {}, creator_name="<b>hacker</b>")

        assert "<script>" not in card
        assert "&lt;script&gt;" in card
        assert "&lt;b&gt;hacker&lt;/b&gt;" in card


class TestGetVotesGrouped:
    async def test_groups_votes_by_choice(self, session):
        user_repo = UserRepository(session)
        u1 = await user_repo.create(telegram_id=800, username="g1", full_name="Alice")
        u2 = await user_repo.create(telegram_id=801, username="g2", full_name="Bob")
        u3 = await user_repo.create(telegram_id=802, username="g3", full_name="Charlie")

        meeting_repo = MeetingRepository(session)
        meeting = await meeting_repo.create(creator_id=u1.id, title="Group Test")

        vote_repo = VoteRepository(session)
        await vote_repo.upsert(meeting.id, u1.id, VoteChoice.YES)
        await vote_repo.upsert(meeting.id, u2.id, VoteChoice.YES)
        await vote_repo.upsert(meeting.id, u3.id, VoteChoice.NO)

        grouped = await get_votes_grouped(session, meeting.id)

        assert len(grouped["yes"]) == 2
        assert "Alice" in grouped["yes"]
        assert "Bob" in grouped["yes"]
        assert len(grouped["no"]) == 1
        assert "Charlie" in grouped["no"]

    async def test_empty_votes(self, session):
        user_repo = UserRepository(session)
        u = await user_repo.create(telegram_id=810, username="g10", full_name="Solo")

        meeting_repo = MeetingRepository(session)
        meeting = await meeting_repo.create(creator_id=u.id, title="No Votes")

        grouped = await get_votes_grouped(session, meeting.id)
        assert grouped == {}
