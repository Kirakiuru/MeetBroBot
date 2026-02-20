import enum
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base


class MeetingStatus(str, enum.Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


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

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator: Mapped["User"] = relationship(back_populates="created_meetings")
    votes = relationship("Vote", back_populates="meeting", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Meeting {self.id} '{self.title}' [{self.status.value}]>"
