"""User repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.user import PasswordResetToken, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalars(
            select(User).where(User.email == email.strip().lower())
        ).first()

    def exists_email(self, email: str) -> bool:
        return self.db.scalar(
            select(User.id).where(User.email == email.strip().lower())
        ) is not None

    def create(self, *, email: str, hashed_password: str, **values: object) -> User:
        return super().create(
            email=email.strip().lower(), hashed_password=hashed_password, **values
        )

    # ------------------------------------------------- password reset prep
    def create_reset_token(self, user: User, *, ttl_hours: int = 1) -> PasswordResetToken:
        import secrets

        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
        ).delete(synchronize_session=False)
        token = PasswordResetToken(
            user_id=user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
        )
        self.db.add(token)
        self.db.flush()
        return token

    def get_reset_token(self, token: str) -> PasswordResetToken | None:
        return self.db.scalars(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        ).first()

    def revoke_all_tokens(self, user_id: uuid.UUID) -> None:
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None)
        ).update({"used_at": datetime.now(UTC)}, synchronize_session=False)
        self.db.flush()