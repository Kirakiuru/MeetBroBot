"""Debt optimization — minimize the number of transfers between people."""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.expense import Expense
from src.database.models.user import User


async def calculate_debts(
    session: AsyncSession,
    chat_id: int,
    meeting_id: int | None = None,
) -> list[dict]:
    """
    Calculate optimized debts for a chat (or specific meeting).
    Returns list of {"from_id": int, "from_name": str, "to_id": int, "to_name": str, "amount": Decimal}
    """
    # Fetch expenses
    if meeting_id:
        stmt = (
            select(Expense)
            .options(selectinload(Expense.shares))
            .where(Expense.meeting_id == meeting_id)
        )
    else:
        stmt = (
            select(Expense)
            .options(selectinload(Expense.shares))
            .where(Expense.chat_id == chat_id)
        )
    result = await session.execute(stmt)
    expenses = list(result.scalars().all())

    if not expenses:
        return []

    # Net balance per user: positive = owed money, negative = owes money
    balance: dict[int, Decimal] = defaultdict(Decimal)

    for expense in expenses:
        # Payer gets credited the full amount
        balance[expense.paid_by_id] += expense.amount

        for share in expense.shares:
            if not share.is_settled:
                # Each participant owes their share
                balance[share.user_id] -= share.amount

    # Remove zero balances
    balance = {uid: amt for uid, amt in balance.items() if abs(amt) > Decimal("0.01")}

    if not balance:
        return []

    # Fetch user names
    user_ids = list(balance.keys())
    user_stmt = select(User).where(User.id.in_(user_ids))
    user_result = await session.execute(user_stmt)
    users_map = {u.id: u for u in user_result.scalars().all()}

    # Greedy optimization: match largest creditor with largest debtor
    transfers = _optimize_debts(balance)

    result_list = []
    for from_id, to_id, amount in transfers:
        from_user = users_map.get(from_id)
        to_user = users_map.get(to_id)
        result_list.append({
            "from_id": from_id,
            "from_name": from_user.full_name if from_user else "???",
            "to_id": to_id,
            "to_name": to_user.full_name if to_user else "???",
            "amount": round(amount, 2),
        })

    return result_list


def _optimize_debts(
    balance: dict[int, Decimal],
) -> list[tuple[int, int, Decimal]]:
    """
    Minimize number of transfers.
    Greedy: always match the person who owes most with the person owed most.
    """
    # Split into debtors (negative) and creditors (positive)
    debtors = []  # (user_id, abs_amount) — people who owe
    creditors = []  # (user_id, amount) — people who are owed

    for uid, amt in balance.items():
        if amt < -Decimal("0.01"):
            debtors.append([uid, -amt])  # make positive for easier math
        elif amt > Decimal("0.01"):
            creditors.append([uid, amt])

    # Sort by amount desc
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    transfers = []
    i, j = 0, 0

    while i < len(debtors) and j < len(creditors):
        debtor_id, debt = debtors[i]
        creditor_id, credit = creditors[j]

        transfer = min(debt, credit)
        transfers.append((debtor_id, creditor_id, transfer))

        debtors[i][1] -= transfer
        creditors[j][1] -= transfer

        if debtors[i][1] < Decimal("0.01"):
            i += 1
        if creditors[j][1] < Decimal("0.01"):
            j += 1

    return transfers
