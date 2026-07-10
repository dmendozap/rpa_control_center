from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import requests


@dataclass(frozen=True)
class HealthResult:
    status: str
    http_status: int | None
    response_time_ms: int | None
    message: str | None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "http_status": self.http_status,
            "response_time_ms": self.response_time_ms,
            "message": self.message,
        }


class HealthCheckService:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        verify_tls: bool,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._verify_tls = verify_tls

    def check(
        self,
        url: str | None,
    ) -> HealthResult:
        if not url:
            return HealthResult(
                status="not_configured",
                http_status=None,
                response_time_ms=None,
                message="Health check no configurado.",
            )

        started = perf_counter()

        try:
            response = requests.get(
                url,
                timeout=self._timeout_seconds,
                verify=self._verify_tls,
                allow_redirects=False,
                headers={
                    "User-Agent":
                        "rpa-control-center/1.0"
                },
            )

            elapsed = int(
                (perf_counter() - started) * 1000
            )
            healthy = (
                200 <= response.status_code < 400
            )

            return HealthResult(
                status=(
                    "healthy"
                    if healthy
                    else "unhealthy"
                ),
                http_status=response.status_code,
                response_time_ms=elapsed,
                message=(
                    None
                    if healthy
                    else f"HTTP {response.status_code}"
                ),
            )
        except requests.RequestException as exc:
            elapsed = int(
                (perf_counter() - started) * 1000
            )

            return HealthResult(
                status="unhealthy",
                http_status=None,
                response_time_ms=elapsed,
                message=str(exc),
            )