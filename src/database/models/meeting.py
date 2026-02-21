from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.user import User  # noqa: F401


class MeetingStatus(str, enum.Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class RecurrenceRule(str, enum.Enum):
    """How often a meeting repeats."""
    NONE = "none"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[MeetingStatus] = mapped_column(default=MeetingStatus.PROPOSED)

    # Telegram context
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    message_id: Mapped[int | None] = mapped_column(Integer)

    # Time
    proposed_datetime: Mapped[datetime | None]
    confirmed_datetime: Mapped[datetime | None]

    # Location
    location: Mapped[str | None] = mapped_column(String(500))

    # Voting deadline
    vote_deadline: Mapped[datetime | None] = mapped_column(default=None)

    # Reminders
    reminder_minutes: Mapped[int | None] = mapped_column(
        SmallInteger, default=None
    )  # minutes before meeting
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    deadline_reminder_sent: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Recurrence
    recurrence: Mapped[str] = mapped_column(
        String(20), default=RecurrenceRule.NONE.value, server_default="none"
    )
    parent_meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("meetings.id"), default=None
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator: Mapped["User"] = relationship(back_populates="created_meetings")
    votes = relationship("Vote", back_populates="meeting", cascade="all, delete-orphan")
    parent = relationship("Meeting", remote_side="Meeting.id", uselist=False)

    @property
    def is_recurring(self) -> bool:
        return self.recurrence != RecurrenceRule.NONE.value

    def __repr__(self) -> str:
        return f"<Meeting {self.id} '{self.title}' [{self.status.value}]>"
