from datetime import date, datetime, time

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base


class Availability(Base):
    __tablename__ = "availabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Recurring: day_of_week (0=Mon .. 6=Sun) + time range
    day_of_week: Mapped[int | None]
    start_time: Mapped[time]
    end_time: Mapped[time]

    # One-time slot: specific_date instead of day_of_week
    is_recurring: Mapped[bool] = mapped_column(default=True)
    specific_date: Mapped[date | None]

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="availabilities")

    def __repr__(self) -> str:
        if self.is_recurring:
            return f"<Availability day={self.day_of_week} {self.start_time}-{self.end_time}>"
        return f"<Availability {self.specific_date} {self.start_time}-{self.end_time}>"
