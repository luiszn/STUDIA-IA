"""Authentication and profile services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from app.core.security import (
    TokenError,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
    UserUpdate,
)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    # ------------------------------------------------------------ register
    def register(self, payload: RegisterRequest) -> TokenResponse:
        if self.users.exists_email(payload.email):
            raise ConflictError(
                "An account with this email already exists.", code="email_taken"
            )

        user = self.users.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            university=payload.university,
            career=payload.career,
            academic_year=payload.academic_year,
            daily_study_goal_minutes=payload.daily_study_goal_minutes,
        )
        user.touch_login()
        self.db.commit()
        return self._issue(user)

    # --------------------------------------------------------------- login
    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.users.get_by_email(payload.email)
        # Constant work whether or not the account exists (timing safety).
        stored_hash = user.hashed_password if user else "$2b$12$" + "." * 53
        password_ok = verify_password(payload.password, stored_hash)

        if user is None or not password_ok:
            raise AuthenticationError(
                "Email or password is incorrect.", code="invalid_credentials"
            )
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated.", code="account_disabled")

        user.touch_login()
        self.db.commit()
        return self._issue(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except TokenError as exc:
            raise AuthenticationError(str(exc), code="invalid_token") from exc
        try:
            user_id = uuid.UUID(payload["sub"])
        except ValueError as exc:
            raise AuthenticationError("The provided token is not valid.") from exc

        user = self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Your session is no longer valid.")
        return self._issue(user)

    # -------------------------------------------------------------- profile
    def get_user(self, user_id: uuid.UUID) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("We could not find your account.")
        return user

    def update_profile(self, user: User, payload: UserUpdate) -> UserRead:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return UserRead.model_validate(user)

    def change_password(self, user: User, *, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Your current password is incorrect.", code="invalid_credentials")
        user.hashed_password = hash_password(new_password)
        self.users.revoke_all_tokens(user.id)
        self.db.commit()

    # ------------------------------------------------- password reset prep
    def request_password_reset(self, email: str) -> str | None:
        """Create a reset token.

        Returns the token so a mail transport can be wired in later. The API
        layer deliberately never echoes it back to the caller.
        """
        user = self.users.get_by_email(email)
        if user is None:
            return None
        token = self.users.create_reset_token(user)
        self.db.commit()
        return token.token

    def confirm_password_reset(self, *, token: str, new_password: str) -> None:
        record = self.users.get_reset_token(token)
        if record is None or not record.is_usable:
            raise ValidationError("This reset link is invalid or has expired.")
        user = self.users.get(record.user_id)
        if user is None:
            raise NotFoundError("We could not find your account.")
        user.hashed_password = hash_password(new_password)
        record.used_at = datetime.now(UTC)
        self.db.commit()

    # -------------------------------------------------------------- helpers
    def _issue(self, user: User) -> TokenResponse:
        tokens = create_token_pair(user.id)
        return TokenResponse(**tokens, user=UserRead.model_validate(user))

    @staticmethod
    def token_ttl() -> timedelta:
        from app.core.config import settings

        return timedelta(minutes=settings.access_token_expire_minutes)