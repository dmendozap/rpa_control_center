from __future__ import annotations

from dataclasses import dataclass
from time import time

import psutil


@dataclass(frozen=True)
class ProcessMetrics:
    available: bool
    cpu_percent: float | None
    memory_mb: float | None
    uptime_seconds: int | None
    message: str | None = None

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "uptime_seconds": self.uptime_seconds,
            "message": self.message,
        }


class ProcessMetricsService:
    def get_metrics(
        self,
        process_id: int | None,
    ) -> ProcessMetrics:
        if not process_id:
            return ProcessMetrics(
                available=False,
                cpu_percent=None,
                memory_mb=None,
                uptime_seconds=None,
                message="Proceso no disponible.",
            )

        try:
            process = psutil.Process(process_id)

            memory_mb = (
                process.memory_info().rss
                / (1024 * 1024)
            )
            cpu_percent = process.cpu_percent(
                interval=0.05
            )
            uptime_seconds = max(
                int(time() - process.create_time()),
                0,
            )

            return ProcessMetrics(
                available=True,
                cpu_percent=round(
                    cpu_percent,
                    2,
                ),
                memory_mb=round(
                    memory_mb,
                    2,
                ),
                uptime_seconds=uptime_seconds,
            )
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
        ) as exc:
            return ProcessMetrics(
                available=False,
                cpu_percent=None,
                memory_mb=None,
                uptime_seconds=None,
                message=str(exc),
            )