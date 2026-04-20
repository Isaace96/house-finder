from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from loguru import logger

from app.config import settings


def _decode(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        logger.warning(f"[AUTH] JWT decode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        ) from e


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> UUID:
    if not authorization or not authorization.lower().startswith("bearer "):
        logger.warning(
            f"[AUTH] Missing/invalid Authorization header: {authorization!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.split(" ", 1)[1].strip()
    payload = _decode(token)
    sub = payload.get("sub")
    if not sub:
        logger.warning("[AUTH] Token missing sub claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )
    try:
        return UUID(sub)
    except ValueError as e:
        logger.warning(f"[AUTH] Invalid sub claim: {sub!r}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sub claim",
        ) from e


CurrentUserId = Depends(get_current_user_id)
