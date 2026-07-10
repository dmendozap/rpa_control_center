from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Role(db.Model):
    __tablename__ = "role"
    __table_args__ = {"schema": "auth"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    role_description: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    users = relationship(
        "AuthUser",
        back_populates="role",
    )

    def __repr__(self) -> str:
        return (
            f"<Role id={self.id} "
            f"description={self.role_description!r}>"
        )


class AuthUser(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
    )
    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    schema_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    id_role: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("auth.role.id"),
        nullable=True,
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    password_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    role = relationship(
        "Role",
        back_populates="users",
        lazy="joined",
    )

    def get_id(self) -> str:
        return f"auth:{self.id}"

    @property
    def role_description(self) -> str:
        if self.role is None or not self.role.role_description:
            return ""

        return self.role.role_description.strip()

    def has_password_expired(self) -> bool:
        if self.password_expires_at is None:
            return False

        expires_at = self.password_expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc,
            )

        return expires_at <= utc_now()

    def __repr__(self) -> str:
        return (
            f"<AuthUser id={self.id} "
            f"email={self.email!r}>"
        )


class ManagedApplication(db.Model):
    __tablename__ = "managed_applications"
    __table_args__ = (
        Index(
            "idx_apps_managed_applications_display_order",
            "display_order",
        ),
        Index(
            "idx_apps_managed_applications_is_enabled",
            "is_enabled",
        ),
        {"schema": "apps"},
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    service_name: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )
    application_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    health_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    log_file: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    allow_control: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    audit_events = relationship(
        "AuditEvent",
        back_populates="application",
    )

    def __repr__(self) -> str:
        return (
            f"<ManagedApplication code={self.code!r} "
            f"service={self.service_name!r}>"
        )


class AuditEvent(db.Model):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index(
            "idx_apps_audit_events_created_at",
            "created_at",
        ),
        Index(
            "idx_apps_audit_events_action",
            "action",
        ),
        {"schema": "apps"},
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    application_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "apps.managed_applications.id"
        ),
        nullable=True,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    actor_email: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )
    result: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    remote_address: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    application = relationship(
        "ManagedApplication",
        back_populates="audit_events",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditEvent action={self.action!r} "
            f"result={self.result!r}>"
        )