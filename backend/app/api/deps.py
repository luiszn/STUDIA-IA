"""FastAPI dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError
from app.core.security import TokenError, decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.users import UserRepository

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError(
            "Sign in to access this feature.", code="missing_credentials"
        )
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError as exc:
        raise AuthenticationError(str(exc), code="invalid_token") from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError as exc:
        raise AuthenticationError("The provided token is not valid.", code="invalid_token") from exc

    user = UserRepository(db).get(user_id)
    if user is None:
        raise AuthenticationError("Your account no longer exists.", code="user_not_found")
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated.", code="account_disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


class Pagination:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=200, description="Max records")] = 50,
        offset: Annotated[int, Query(ge=0, description="Records to skip")] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


Paging = Annotated[Pagination, Depends()]