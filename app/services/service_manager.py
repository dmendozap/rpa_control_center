from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceStatus:
    exists: bool
    name: str
    state: str
    start_mode: str | None = None
    process_id: int | None = None
    message: str | None = None

    def to_dict(self) -> dict:
        return {
            "exists": self.exists,
            "name": self.name,
            "state": self.state,
            "start_mode": self.start_mode,
            "process_id": self.process_id,
            "message": self.message,
        }


class ServiceManager(ABC):
    @abstractmethod
    def get_status(
        self,
        service_name: str,
    ) -> ServiceStatus:
        raise NotImplementedError

    @abstractmethod
    def start(
        self,
        service_name: str,
    ) -> ServiceStatus:
        raise NotImplementedError

    @abstractmethod
    def stop(
        self,
        service_name: str,
    ) -> ServiceStatus:
        raise NotImplementedError

    @abstractmethod
    def restart(
        self,
        service_name: str,
    ) -> ServiceStatus:
        raise NotImplementedError