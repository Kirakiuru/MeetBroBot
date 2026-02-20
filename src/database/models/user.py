from datetime import datetime

from sqlalchemy import BigInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    created_meetings = relationship("Meeting", back_populates="creator")
    votes = relationship("Vote", back_populates="user")
    availabilities = relationship("Availability", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.telegram_id} @{self.username}>"
