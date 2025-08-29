import os

from fastapi import HTTPException, Request, status
from structlog.contextvars import bind_contextvars


ALLOW_ANON = os.getenv("ALLOW_ANON", "true").lower() != "false"


def get_current_user(request: Request):
    """Return the current user context.

    Reads the ``Authorization`` header expecting a ``Bearer`` token. When
    ``ALLOW_ANON`` is true, requests without credentials are allowed and a
    placeholder anonymous user context is returned. Otherwise, a bearer token
    is required but not validated (stub).
    """

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        if ALLOW_ANON:
            user = {"sub": "anonymous"}
            bind_contextvars(user=user)
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        scheme, token = auth_header.split(" ", 1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    # Stub validation: accept any token and return a placeholder user
    user = {"sub": "user", "token": token}
    bind_contextvars(user=user)
    return user

