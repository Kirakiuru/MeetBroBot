from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.meeting import Meeting  # noqa: F401
    from src.database.models.user import User  # noqa: F401


class VoteChoice(str, enum.Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("meeting_id", "user_id", name="uq_vote_meeting_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    choice: Mapped[VoteChoice]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="votes")
    user: Mapped["User"] = relationship(back_populates="votes")

    def __repr__(self) -> str:
        return f"<Vote user={self.user_id} meeting={self.meeting_id} {self.choice.value}>"
