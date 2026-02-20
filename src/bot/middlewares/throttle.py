import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class ThrottleMiddleware(BaseMiddleware):
    """
    Simple per-user rate limiting.
    Drops messages if user sends more than `rate` per `period` seconds.
    """

    def __init__(self, rate: int = 5, period: float = 10.0):
        self.rate = rate
        self.period = period
        self._timestamps: dict[int, list[float]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None

        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        timestamps = self._timestamps.setdefault(user_id, [])

        # Remove old timestamps
        timestamps[:] = [t for t in timestamps if now - t < self.period]

        if len(timestamps) >= self.rate:
            # Throttled — silently drop
            if isinstance(event, CallbackQuery):
                await event.answer("⏳ Слишком быстро, подожди немного")
            return None

        timestamps.append(now)
        return await handler(event, data)
