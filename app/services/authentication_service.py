from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta, timezone
from typing import Any

from app.models import AuthUser
from app.repositories import UserRepository
from app.security import (
    AccessLevel,
    BreakGlassUser,
    get_access_level,
    utc_now,
    verify_password,
)


@dataclass(frozen=True)
class AuthenticationResult:
    user: Any | None
    code: str
    message: str


class AuthenticationService:
    def __init__(
        self,
        *,
        users: UserRepository,
        max_failed_attempts: int,
        lock_minutes: int,
        break_glass_enabled: bool,
        break_glass_username: str,
        break_glass_password_hash: str,
    ) -> None:
        self._users = users
        self._max_failed_attempts = (
            max_failed_attempts
        )
        self._lock_minutes = lock_minutes
        self._break_glass_enabled = (
            break_glass_enabled
        )
        self._break_glass_username = (
            break_glass_username
        )
        self._break_glass_password_hash = (
            break_glass_password_hash
        )

    def authenticate(
        self,
        identifier: str,
        password: str,
    ) -> AuthenticationResult:
        normalized = identifier.strip().lower()

        break_glass_result = (
            self._authenticate_break_glass(
                normalized,
                password,
            )
        )

        if break_glass_result is not None:
            return break_glass_result

        user = self._users.find_by_identifier(
            normalized
        )

        if user is None:
            return AuthenticationResult(
                user=None,
                code="invalid_credentials",
                message="Credenciales inválidas.",
            )

        now = utc_now()

        if user.locked_until:
            locked_until = user.locked_until

            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(
                    tzinfo=timezone.utc
                )

            if locked_until > now:
                return AuthenticationResult(
                    user=None,
                    code="locked",
                    message=(
                        "La cuenta está bloqueada "
                        "temporalmente."
                    ),
                )

        if not user.is_active:
            return AuthenticationResult(
                user=None,
                code="inactive",
                message="La cuenta está inactiva.",
            )

        if not verify_password(
            user.password,
            password,
        ):
            self._register_failed_attempt(user)

            return AuthenticationResult(
                user=None,
                code="invalid_credentials",
                message="Credenciales inválidas.",
            )

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now

        self._users.save(user)

        if (
            user.must_change_password
            or user.has_password_expired()
        ):
            return AuthenticationResult(
                user=None,
                code="password_change_required",
                message=(
                    "Debes actualizar tu contraseña "
                    "en Authentication Manager "
                    "antes de ingresar."
                ),
            )

        if (
            get_access_level(user)
            < AccessLevel.VIEWER
        ):
            return AuthenticationResult(
                user=None,
                code="access_denied",
                message=(
                    "El usuario no tiene acceso "
                    "al RPA Control Center."
                ),
            )

        return AuthenticationResult(
            user=user,
            code="success",
            message="Autenticación correcta.",
        )

    def load_break_glass_user(
        self,
    ) -> BreakGlassUser | None:
        if not self._break_glass_enabled:
            return None

        return BreakGlassUser(
            username=self._break_glass_username
        )

    def _authenticate_break_glass(
        self,
        normalized_identifier: str,
        password: str,
    ) -> AuthenticationResult | None:
        if (
            not self._break_glass_enabled
            or normalized_identifier
            != self._break_glass_username
        ):
            return None

        if not verify_password(
            self._break_glass_password_hash,
            password,
        ):
            return AuthenticationResult(
                user=None,
                code="invalid_credentials",
                message="Credenciales inválidas.",
            )

        return AuthenticationResult(
            user=BreakGlassUser(
                username=self._break_glass_username
            ),
            code="success",
            message=(
                "Acceso de recuperación concedido."
            ),
        )

    def _register_failed_attempt(
        self,
        user: AuthUser,
    ) -> None:
        user.failed_login_attempts = (
            user.failed_login_attempts or 0
        ) + 1

        if (
            user.failed_login_attempts
            >= self._max_failed_attempts
        ):
            user.locked_until = (
                utc_now()
                + timedelta(
                    minutes=self._lock_minutes
                )
            )

        self._users.save(user)