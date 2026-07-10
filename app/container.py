from __future__ import annotations

from dataclasses import dataclass

from flask import Flask, current_app

from app.repositories import (
    ApplicationRepository,
    AuditRepository,
    UserRepository,
)
from app.services.application_service import (
    ApplicationService,
)
from app.services.authentication_service import (
    AuthenticationService,
)
from app.services.health_service import (
    HealthCheckService,
)
from app.services.log_service import LogService
from app.services.metrics_service import (
    ProcessMetricsService,
)
from app.services.service_manager import (
    ServiceManager,
)
from app.services.windows_service_manager import (
    MockServiceManager,
    WindowsPowerShellServiceManager,
)


@dataclass(frozen=True)
class ServiceContainer:
    users: UserRepository
    applications: ApplicationRepository
    audit: AuditRepository
    authentication: AuthenticationService
    application_service: ApplicationService
    log_service: LogService
    service_manager: ServiceManager


def build_container(
    app: Flask,
) -> ServiceContainer:
    users = UserRepository()
    applications = ApplicationRepository()
    audit = AuditRepository()

    if app.config["SERVICE_BACKEND"] == "windows":
        service_manager: ServiceManager = (
            WindowsPowerShellServiceManager(
                executable=app.config[
                    "POWERSHELL_EXECUTABLE"
                ],
                timeout_seconds=app.config[
                    "SERVICE_ACTION_TIMEOUT_SECONDS"
                ],
            )
        )
    else:
        service_manager = MockServiceManager()

    health = HealthCheckService(
        timeout_seconds=app.config[
            "HEALTHCHECK_TIMEOUT_SECONDS"
        ],
        verify_tls=app.config[
            "HEALTHCHECK_VERIFY_TLS"
        ],
    )

    metrics = ProcessMetricsService()

    log_service = LogService(
        allowed_roots=app.config[
            "ALLOWED_LOG_ROOTS"
        ],
        poll_seconds=app.config[
            "LOG_STREAM_POLL_SECONDS"
        ],
    )

    authentication = AuthenticationService(
        users=users,
        max_failed_attempts=app.config[
            "MAX_FAILED_LOGIN_ATTEMPTS"
        ],
        lock_minutes=app.config[
            "ACCOUNT_LOCK_MINUTES"
        ],
        break_glass_enabled=app.config[
            "BREAK_GLASS_ENABLED"
        ],
        break_glass_username=app.config[
            "BREAK_GLASS_USERNAME"
        ],
        break_glass_password_hash=app.config[
            "BREAK_GLASS_PASSWORD_HASH"
        ],
    )

    application_service = ApplicationService(
        applications=applications,
        audit=audit,
        service_manager=service_manager,
        health=health,
        metrics=metrics,
    )

    return ServiceContainer(
        users=users,
        applications=applications,
        audit=audit,
        authentication=authentication,
        application_service=application_service,
        log_service=log_service,
        service_manager=service_manager,
    )


def get_container() -> ServiceContainer:
    return current_app.extensions[
        "rpa_control_services"
    ]