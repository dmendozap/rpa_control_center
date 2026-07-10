from __future__ import annotations

from sqlalchemy import or_, select

from app.extensions import db
from app.models import (
    AuditEvent,
    AuthUser,
    ManagedApplication,
)


class UserRepository:
    def find_by_identifier(
        self,
        identifier: str,
    ) -> AuthUser | None:
        normalized = identifier.strip().lower()

        statement = select(AuthUser).where(
            or_(
                AuthUser.email == normalized,
                AuthUser.username == normalized,
            )
        )

        return db.session.scalar(statement)

    def get_by_id(
        self,
        user_id: int,
    ) -> AuthUser | None:
        return db.session.get(
            AuthUser,
            user_id,
        )

    def save(
        self,
        user: AuthUser,
    ) -> None:
        db.session.add(user)
        db.session.commit()


class ApplicationRepository:
    def list_enabled(
        self,
    ) -> list[ManagedApplication]:
        statement = (
            select(ManagedApplication)
            .where(
                ManagedApplication.is_enabled.is_(True)
            )
            .order_by(
                ManagedApplication.display_order.asc(),
                ManagedApplication.name.asc(),
            )
        )

        return list(
            db.session.scalars(statement).all()
        )

    def get_by_code(
        self,
        code: str,
    ) -> ManagedApplication | None:
        statement = select(
            ManagedApplication
        ).where(
            ManagedApplication.code == code
        )

        return db.session.scalar(statement)

    def upsert(
        self,
        payload: dict,
    ) -> ManagedApplication:
        application = self.get_by_code(
            payload["code"]
        )

        if application is None:
            application = ManagedApplication(
                code=payload["code"]
            )
            db.session.add(application)

        application.name = payload["name"]
        application.description = payload.get(
            "description"
        )
        application.service_name = payload[
            "service_name"
        ]
        application.application_url = payload.get(
            "application_url"
        )
        application.health_url = payload.get(
            "health_url"
        )
        application.log_file = payload.get(
            "log_file"
        )
        application.display_order = int(
            payload.get("display_order", 0)
        )
        application.is_enabled = bool(
            payload.get("is_enabled", True)
        )
        application.allow_control = bool(
            payload.get("allow_control", True)
        )

        return application


class AuditRepository:
    def record(
        self,
        *,
        action: str,
        result: str,
        actor_user_id: int | None,
        actor_email: str | None,
        remote_address: str | None,
        application: ManagedApplication | None = None,
        message: str | None = None,
        details: dict | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            application=application,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            action=action,
            result=result,
            remote_address=remote_address,
            message=message,
            details=details or {},
        )

        db.session.add(event)
        db.session.commit()

        return event

    def list_recent(
        self,
        limit: int = 200,
    ) -> list[AuditEvent]:
        statement = (
            select(AuditEvent)
            .order_by(
                AuditEvent.created_at.desc()
            )
            .limit(limit)
        )

        return list(
            db.session.scalars(statement).all()
        )