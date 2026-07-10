from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.models import ManagedApplication
from app.repositories import (
    ApplicationRepository,
    AuditRepository,
)
from app.services.health_service import (
    HealthCheckService,
)
from app.services.metrics_service import (
    ProcessMetricsService,
)
from app.services.service_manager import (
    ServiceManager,
)
from app.services.windows_service_manager import (
    ServiceOperationError,
)


@dataclass(frozen=True)
class ActorContext:
    user_id: int | None
    email: str | None
    remote_address: str | None


class ApplicationService:
    ALLOWED_ACTIONS = {
        "start",
        "stop",
        "restart",
    }

    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        audit: AuditRepository,
        service_manager: ServiceManager,
        health: HealthCheckService,
        metrics: ProcessMetricsService,
    ) -> None:
        self._applications = applications
        self._audit = audit
        self._service_manager = service_manager
        self._health = health
        self._metrics = metrics

        self._locks: defaultdict[
            str,
            threading.Lock,
        ] = defaultdict(threading.Lock)

    def list_applications(
        self,
    ) -> list[ManagedApplication]:
        return self._applications.list_enabled()

    def get_application(
        self,
        code: str,
    ) -> ManagedApplication:
        application = (
            self._applications.get_by_code(code)
        )

        if (
            application is None
            or not application.is_enabled
        ):
            raise LookupError(
                "Aplicación no encontrada."
            )

        return application

    def get_snapshot(
        self,
        application: ManagedApplication,
    ) -> dict[str, Any]:
        service = self._service_manager.get_status(
            application.service_name
        )
        health = self._health.check(
            application.health_url
        )
        metrics = self._metrics.get_metrics(
            service.process_id
        )

        return {
            "application": {
                "code": application.code,
                "name": application.name,
                "application_url":
                    application.application_url,
                "allow_control":
                    application.allow_control,
            },
            "service": service.to_dict(),
            "health": health.to_dict(),
            "metrics": metrics.to_dict(),
        }

    def perform_action(
        self,
        *,
        application: ManagedApplication,
        action: str,
        actor: ActorContext,
    ) -> dict[str, Any]:
        normalized_action = (
            action.strip().lower()
        )

        if (
            normalized_action
            not in self.ALLOWED_ACTIONS
        ):
            raise ValueError(
                "Acción no soportada."
            )

        if not application.allow_control:
            raise PermissionError(
                "El control del servicio está "
                "deshabilitado para esta aplicación."
            )

        with self._locks[
            application.service_name
        ]:
            before = (
                self._service_manager.get_status(
                    application.service_name
                )
            )

            try:
                if normalized_action == "start":
                    after = (
                        self._service_manager.start(
                            application.service_name
                        )
                    )
                elif normalized_action == "stop":
                    after = (
                        self._service_manager.stop(
                            application.service_name
                        )
                    )
                else:
                    after = (
                        self._service_manager.restart(
                            application.service_name
                        )
                    )

                self._audit.record(
                    action=(
                        f"service.{normalized_action}"
                    ),
                    result="success",
                    actor_user_id=actor.user_id,
                    actor_email=actor.email,
                    remote_address=(
                        actor.remote_address
                    ),
                    application=application,
                    message=(
                        f"Servicio "
                        f"{application.service_name}: "
                        f"{before.state} -> "
                        f"{after.state}"
                    ),
                    details={
                        "before": before.to_dict(),
                        "after": after.to_dict(),
                    },
                )

                return after.to_dict()

            except Exception as exc:
                self._audit.record(
                    action=(
                        f"service.{normalized_action}"
                    ),
                    result="error",
                    actor_user_id=actor.user_id,
                    actor_email=actor.email,
                    remote_address=(
                        actor.remote_address
                    ),
                    application=application,
                    message=str(exc),
                    details={
                        "before": before.to_dict()
                    },
                )

                if isinstance(
                    exc,
                    ServiceOperationError,
                ):
                    raise

                raise ServiceOperationError(
                    str(exc)
                ) from exc