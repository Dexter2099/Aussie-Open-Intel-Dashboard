import os
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from structlog.contextvars import bind_contextvars


ALLOW_ANON = os.getenv("ALLOW_ANON", "true").lower() != "false"
SECRET_KEY = os.getenv("JWT_SECRET", "secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT from ``data``."""

    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request):
    """Return the current user context.

    Reads the ``Authorization`` header expecting a ``Bearer`` token. When
    ``ALLOW_ANON`` is true, requests without credentials are allowed and a
    placeholder anonymous user context is returned. Otherwise, a valid JWT is
    required.
    """

    # Allow unauthenticated access for the token issuance endpoint
    if request.url.path == "/token":
        return {"sub": "anonymous"}

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

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:  # pragma: no cover - detail for client
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc

    user = {"sub": payload.get("sub")}
    bind_contextvars(user=user)
    return user

