"""Telegram WebApp initData validation (HMAC-SHA256)."""

import hashlib
import hmac
import json
from urllib.parse import parse_qs

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.database.engine import async_session
from src.database.repositories.user import UserRepository


def _validate_init_data(init_data: str, bot_token: str) -> dict:
    """
    Validate Telegram WebApp initData and return parsed data.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    parsed = parse_qs(init_data)

    if "hash" not in parsed:
        raise ValueError("Missing hash")

    received_hash = parsed.pop("hash")[0]

    # Build data-check-string: sorted key=value pairs
    data_check_parts = []
    for key in sorted(parsed.keys()):
        data_check_parts.append(f"{key}={parsed[key][0]}")
    data_check_string = "\n".join(data_check_parts)

    # secret_key = HMAC_SHA256(bot_token, "WebAppData")
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()

    # calculated_hash = HMAC_SHA256(data_check_string, secret_key)
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Invalid hash")

    # Parse user JSON
    user_data = json.loads(parsed["user"][0]) if "user" in parsed else {}
    return user_data


async def get_db():
    """Dependency: async DB session."""
    async with async_session() as session:
        yield session


async def get_current_user(request: Request, session: AsyncSession = Depends(get_db)):
    """
    Dependency: extract and validate Telegram user from initData header.
    Returns DB User object.
    """
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing initData")

    try:
        tg_user = _validate_init_data(init_data, settings.bot_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    telegram_id = tg_user.get("id")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="No user in initData")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user:
        # Auto-create user from WebApp data
        user = await user_repo.create(
            telegram_id=telegram_id,
            username=tg_user.get("username"),
            full_name=tg_user.get("first_name", "")
            + (" " + tg_user["last_name"] if tg_user.get("last_name") else ""),
        )

    return user
