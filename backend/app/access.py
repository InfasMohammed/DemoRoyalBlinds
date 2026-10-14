"""Private demo access through Supabase-verified user sessions."""

import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_auth.errors import AuthApiError


@dataclass(frozen=True)
class AccessSettings:
    required: bool
    allowed_emails: frozenset[str]


@dataclass(frozen=True)
class Reviewer:
    user_id: str
    email: str


def access_settings() -> AccessSettings:
    production = os.getenv("APP_ENV") == "production" or bool(os.getenv("K_SERVICE"))
    configured = os.getenv("AUTH_REQUIRED", "true" if production else "false").lower()
    if configured not in ("true", "false"):
        raise RuntimeError("AUTH_REQUIRED must be true or false.")
    required = configured == "true"
    if production and not required:
        raise RuntimeError("Supabase sign-in is required for production deployment.")
    emails = frozenset(
        email.strip().casefold()
        for email in os.getenv("AUTH_ALLOWED_EMAILS", "").split(",")
        if email.strip()
    )
    if required:
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
            raise RuntimeError("Private deployment requires both backend Supabase variables.")
        if not emails or any("@" not in email or "*" in email for email in emails):
            raise RuntimeError(
                "AUTH_ALLOWED_EMAILS must list the invited reviewers' email addresses."
            )
    return AccessSettings(required, emails)


bearer = HTTPBearer(auto_error=False)


def require_reviewer(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Reviewer | None:
    settings = request.app.state.access_settings
    if not settings.required:
        return None
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            401, "Sign in to access this interview demo.", headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        # get_user verifies the token with this project's Supabase Auth service.
        # Never trust client-decoded claims or accept a browser-supplied server key.
        response = request.app.state.report_store.client.auth.get_user(credentials.credentials)
        user = response.user if response else None
    except AuthApiError as exc:
        if exc.status in (400, 401, 403):
            raise HTTPException(
                401,
                "Session expired or invalid. Sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        raise HTTPException(503, "Sign-in verification is temporarily unavailable.") from None
    except Exception:
        raise HTTPException(503, "Sign-in verification is temporarily unavailable.") from None
    if not user or user.role != "authenticated" or not user.email or not user.email_confirmed_at:
        raise HTTPException(401, "A verified user session is required.")
    if user.email.casefold() not in settings.allowed_emails:
        raise HTTPException(403, "This account has not been invited to the interview demo.")
    return Reviewer(str(user.id), user.email)
