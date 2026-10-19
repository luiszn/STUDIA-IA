"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
    UserUpdate,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and sign in",
)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    return AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse, summary="Sign in with email and password")
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    return AuthService(db).login(payload)


@router.post("/refresh", response_model=TokenResponse, summary="Exchange a refresh token")
def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    return AuthService(db).refresh(payload.refresh_token)


@router.get("/me", response_model=UserRead, summary="Current profile")
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead, summary="Update profile")
def update_me(payload: UserUpdate, user: CurrentUser, db: DbSession) -> UserRead:
    return AuthService(db).update_profile(user, payload)


@router.post(
    "/me/password",
    response_model=MessageResponse,
    summary="Change password",
)
def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> MessageResponse:
    AuthService(db).change_password(
        user, current_password=payload.current_password, new_password=payload.new_password
    )
    return MessageResponse(message="Password updated successfully.")


@router.post(
    "/password-reset",
    response_model=MessageResponse,
    summary="Request a password reset link",
)
def request_reset(payload: PasswordResetRequest, db: DbSession) -> MessageResponse:
    AuthService(db).request_password_reset(payload.email)
    # Always the same answer so the endpoint cannot be used to enumerate accounts.
    return MessageResponse(
        message="If that email exists in STUDIA AI, a reset link has been sent."
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Complete a password reset",
)
def confirm_reset(payload: PasswordResetConfirm, db: DbSession) -> MessageResponse:
    AuthService(db).confirm_password_reset(token=payload.token, new_password=payload.new_password)
    return MessageResponse(message="Password updated. You can sign in now.")


@router.post("/logout", response_model=MessageResponse, summary="Sign out")
def logout(user: CurrentUser) -> MessageResponse:
    return MessageResponse(message="Signed out successfully.")