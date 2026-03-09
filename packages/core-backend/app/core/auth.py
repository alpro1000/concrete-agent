"""
app/core/auth.py — JWT / API-key аутентификация.

Экспортирует:
  verify_token(token: str) -> str    — возвращает user_id или бросает HTTPException 401

Поддерживаемые схемы:
  1. Статичный сервисный токен через SERVICE_API_KEY в .env
     (быстро для dev и межсервисных вызовов)
  2. JWT Bearer (HS256) через JWT_SECRET в .env

Если оба ключа не заданы — модуль логирует предупреждение и принимает
любой токен (НЕБЕЗОПАСНО — только для локальной разработки).
"""
import logging
from typing import Optional

from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_service_api_key() -> Optional[str]:
    """Читает SERVICE_API_KEY из settings (или None)."""
    return getattr(settings, "SERVICE_API_KEY", None) or None


def _get_jwt_secret() -> Optional[str]:
    """Читает JWT_SECRET из settings (или None)."""
    return getattr(settings, "JWT_SECRET", None) or None


async def verify_token(token: str) -> str:
    """
    Проверяет Bearer-токен и возвращает user_id.

    Приоритет проверок:
    1. Совпадение со статичным SERVICE_API_KEY
    2. Декодирование JWT (HS256) с JWT_SECRET
    3. Если ничего не настроено — пропускает (dev-режим)

    Args:
        token: Строка токена без префикса 'Bearer '

    Returns:
        user_id (str) — из JWT sub, или 'service' для API-key, или 'dev'

    Raises:
        HTTPException(401) — если токен невалиден
    """
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    service_api_key = _get_service_api_key()
    jwt_secret = _get_jwt_secret()

    # --- 1. Статичный API-ключ ---
    if service_api_key and token == service_api_key:
        logger.debug("Auth: static API key accepted")
        return "service"

    # --- 2. JWT ---
    if jwt_secret:
        try:
            import jwt  # PyJWT

            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"require": ["sub"]},
            )
            user_id: str = payload["sub"]
            logger.debug(f"Auth: JWT accepted, user_id={user_id}")
            return user_id

        except ImportError:
            logger.warning(
                "PyJWT not installed. "
                "Run: pip install PyJWT  — falling through to dev mode"
            )
        except Exception as e:
            logger.warning(f"Auth: JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired token: {e}",
            )

    # --- 3. Dev-режим (нет ключей) ---
    if not service_api_key and not jwt_secret:
        logger.warning(
            "⚠️  AUTH: SERVICE_API_KEY and JWT_SECRET are not set. "
            "Accepting all tokens — DO NOT use in production!"
        )
        return "dev"

    # Ключ задан, но токен не совпал с API-key и JWT не настроен
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )


__all__ = ["verify_token"]
