from __future__ import annotations

from fastapi import Header, HTTPException, status

from src.config import get_settings


def require_admin_password(x_admin_password: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_PASSWORD is not configured",
        )
    if x_admin_password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
