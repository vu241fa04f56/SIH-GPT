"""
security.py — API key middleware stub.

In production, replace the hardcoded check with a database lookup
or a proper JWT verification flow.
"""

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from backend.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency that validates X-API-Key header.

    Usage in routes:
        @router.get("/protected", dependencies=[Depends(verify_api_key)])
    """
    if api_key is None or api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
    return api_key
