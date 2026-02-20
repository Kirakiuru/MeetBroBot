"""Repository for expenses and expense shares."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.expense import Expense, ExpenseShare


class ExpenseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        chat_id: int,
        paid_by_id: int,
        title: str,
        amount: Decimal,
        share_user_ids: list[int],
        meeting_id: int | None = None,
        currency: str = "RUB",
    ) -> Expense:
        """Create an expense and split equally among share_user_ids."""
        expense = Expense(
            chat_id=chat_id,
            meeting_id=meeting_id,
            paid_by_id=paid_by_id,
            title=title,
            amount=amount,
            currency=currency,
        )
        self.session.add(expense)
        await self.session.flush()  # get expense.id

        per_person = amount / len(share_user_ids)
        for uid in share_user_ids:
            share = ExpenseShare(
                expense_id=expense.id,
                user_id=uid,
                amount=per_person,
            )
            self.session.add(share)

        await self.session.commit()
        await self.session.refresh(expense)
        return expense

    async def get_by_id(self, expense_id: int) -> Expense | None:
        stmt = (
            select(Expense)
            .options(selectinload(Expense.shares), selectinload(Expense.paid_by))
            .where(Expense.id == expense_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_chat(self, chat_id: int, limit: int = 20) -> list[Expense]:
        stmt = (
            select(Expense)
            .options(selectinload(Expense.shares), selectinload(Expense.paid_by))
            .where(Expense.chat_id == chat_id)
            .order_by(Expense.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_meeting(self, meeting_id: int) -> list[Expense]:
        stmt = (
            select(Expense)
            .options(selectinload(Expense.shares), selectinload(Expense.paid_by))
            .where(Expense.meeting_id == meeting_id)
            .order_by(Expense.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def settle_share(self, share_id: int) -> ExpenseShare | None:
        stmt = select(ExpenseShare).where(ExpenseShare.id == share_id)
        result = await self.session.execute(stmt)
        share = result.scalar_one_or_none()
        if share:
            share.is_settled = True
            await self.session.commit()
            await self.session.refresh(share)
        return share

    async def delete_expense(self, expense_id: int) -> bool:
        expense = await self.get_by_id(expense_id)
        if expense:
            await self.session.delete(expense)
            await self.session.commit()
            return True
        return False
