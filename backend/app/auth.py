from functools import lru_cache
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from loguru import logger

from app.config import settings


@lru_cache(maxsize=1)
def _jwks() -> dict:
    base = settings.supabase_url.rstrip("/")
    if not base:
        raise HTTPException(500, "SUPABASE_URL is not configured on the server")
    url = f"{base}/auth/v1/.well-known/jwks.json"
    logger.info(f"[AUTH] Fetching JWKS from {url}")
    r = httpx.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def _find_jwk(kid: str) -> dict:
    for key in _jwks().get("keys", []):
        if key.get("kid") == kid:
            return key
    _jwks.cache_clear()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Unknown JWT kid: {kid}",
    )


def _decode(token: str) -> dict:
    try:
        headers = jwt.get_unverified_header(token)
    except JWTError as e:
        logger.warning(f"[AUTH] Could not parse JWT header: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token header: {e}",
        ) from e

    alg = headers.get("alg", "HS256")

    try:
        if alg == "HS256":
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )

        kid = headers.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing kid header",
            )
        key = _find_jwk(kid)
        return jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience="authenticated",
        )
    except JWTError as e:
        logger.warning(f"[AUTH] JWT decode failed (alg={alg}): {e}")
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
