from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from functools import wraps
from typing import Any, Callable, TypeVar, cast
from urllib.parse import urljoin, urlparse

from flask import abort, current_app, request
from flask_login import UserMixin, current_user
from werkzeug.security import check_password_hash

from app.extensions import bcrypt


class AccessLevel(IntEnum):
    NONE = 0
    VIEWER = 10
    OPERATOR = 20
    ADMIN = 30


@dataclass
class BreakGlassUser(UserMixin):
    username: str
    email: str = "break-glass@local"
    is_admin: bool = True
    is_active: bool = True
    role_description: str = "BREAK_GLASS"

    def get_id(self) -> str:
        return "break-glass"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def verify_password(
    stored_hash: str,
    password: str,
) -> bool:
    if not stored_hash:
        return False

    if stored_hash.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(
            stored_hash,
            password,
        )

    try:
        return bcrypt.check_password_hash(
            stored_hash,
            password,
        )
    except (ValueError, TypeError):
        return False


def get_access_level(user: Any) -> AccessLevel:
    if not getattr(user, "is_authenticated", False):
        return AccessLevel.NONE

    if getattr(user, "is_admin", False):
        return AccessLevel.ADMIN

    role = str(
        getattr(user, "role_description", "") or ""
    ).strip().upper()

    if role in current_app.config[
        "CONTROL_CENTER_ADMIN_ROLES"
    ]:
        return AccessLevel.ADMIN

    if role in current_app.config[
        "CONTROL_CENTER_OPERATOR_ROLES"
    ]:
        return AccessLevel.OPERATOR

    if role in current_app.config[
        "CONTROL_CENTER_VIEWER_ROLES"
    ]:
        return AccessLevel.VIEWER

    return AccessLevel.NONE


F = TypeVar(
    "F",
    bound=Callable[..., Any],
)


def access_required(
    minimum: AccessLevel,
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            if not current_user.is_authenticated:
                abort(401)

            if get_access_level(current_user) < minimum:
                abort(403)

            return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def is_safe_redirect_target(
    target: str | None,
) -> bool:
    if not target:
        return False

    host_url = request.host_url
    reference = urlparse(host_url)
    candidate = urlparse(
        urljoin(host_url, target)
    )

    return (
        candidate.scheme in {"http", "https"}
        and reference.netloc == candidate.netloc
    )