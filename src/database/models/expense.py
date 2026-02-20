"""Expense splitting models."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base


class Expense(Base):
    """A single expense paid by one person, split among participants."""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("meetings.id"), default=None
    )
    paid_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB", server_default="RUB")

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    paid_by: Mapped["User"] = relationship()
    shares: Mapped[list["ExpenseShare"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Expense {self.id} '{self.title}' {self.amount}>"


class ExpenseShare(Base):
    """How much each person owes for a given expense."""

    __tablename__ = "expense_shares"

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_settled: Mapped[bool] = mapped_column(default=False, server_default="false")

    # Relationships
    expense: Mapped["Expense"] = relationship(back_populates="shares")
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<ExpenseShare expense={self.expense_id} user={self.user_id} {self.amount}>"
