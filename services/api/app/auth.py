import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from structlog.contextvars import bind_contextvars


ALLOW_ANON = os.getenv("ALLOW_ANON", "true").lower() != "false"
_scheme = HTTPBearer(auto_error=not ALLOW_ANON)


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_scheme),
):
    """Return the current user context.

    When ALLOW_ANON is true, requests without credentials are allowed and a
    placeholder anonymous user context is returned. Otherwise, a bearer token
    is required but not validated (stub).
    """
    if creds is None:
        if ALLOW_ANON:
            user = {"sub": "anonymous"}
            bind_contextvars(user=user)
            return user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = creds.credentials
    # Stub validation: accept any token and return a placeholder user
    user = {"sub": "user", "token": token}
    bind_contextvars(user=user)
    return user

