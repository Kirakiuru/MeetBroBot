"""Job: delete availability slots for past dates."""

import logging
from datetime import date, timedelta

from sqlalchemy import delete, and_
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.database.models.availability import Availability

logger = logging.getLogger(__name__)


async def cleanup_old_slots(sf: async_sessionmaker):
    """Delete availability slots for past dates (daily at 7am)."""
    try:
        async with sf() as session:
            yesterday = date.today() - timedelta(days=1)

            stmt = delete(Availability).where(
                and_(
                    Availability.specific_date.isnot(None),
                    Availability.specific_date < yesterday,
                )
            )
            result = await session.execute(stmt)
            count = result.rowcount
            await session.commit()

            if count:
                logger.info("Cleaned up %d old availability slots", count)
    except Exception:
        logger.exception("Error in cleanup job")
