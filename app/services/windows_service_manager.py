from __future__ import annotations

import json
import re
import subprocess
import threading
from collections import defaultdict

from app.services.service_manager import (
    ServiceManager,
    ServiceStatus,
)

SERVICE_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9_.-]{1,128}$"
)


class ServiceOperationError(RuntimeError):
    pass


class WindowsPowerShellServiceManager(
    ServiceManager
):
    def __init__(
        self,
        *,
        executable: str,
        timeout_seconds: int,
    ) -> None:
        self._executable = executable
        self._timeout_seconds = timeout_seconds
        self._locks: defaultdict[
            str,
            threading.Lock,
        ] = defaultdict(threading.Lock)

    def get_status(
        self,
        service_name: str,
    ) -> ServiceStatus:
        self._validate_service_name(service_name)

        script = r"""
& {
    param([string]$Name)

    $OutputEncoding = [Console]::OutputEncoding =
        [System.Text.UTF8Encoding]::new()

    $escapedName = $Name.Replace("'", "''")

    $service = Get-CimInstance `
        -ClassName Win32_Service `
        -Filter "Name='$escapedName'" `
        -ErrorAction SilentlyContinue

    if ($null -eq $service) {
        [PSCustomObject]@{
            exists = $false
            name = $Name
            state = "not_found"
            start_mode = $null
            process_id = $null
            message = "Servicio no encontrado"
        } | ConvertTo-Json -Compress

        exit 0
    }

    [PSCustomObject]@{
        exists = $true
        name = $service.Name
        state = $service.State.ToLowerInvariant()
        start_mode = $service.StartMode
        process_id = [int]$service.ProcessId
        message = $null
    } | ConvertTo-Json -Compress
}
"""

        payload = self._run(
            script,
            service_name,
        )

        return self._to_status(
            payload,
            service_name,
        )

    def start(
        self,
        service_name: str,
    ) -> ServiceStatus:
        return self._perform_action(
            service_name,
            "start",
        )

    def stop(
        self,
        service_name: str,
    ) -> ServiceStatus:
        return self._perform_action(
            service_name,
            "stop",
        )

    def restart(
        self,
        service_name: str,
    ) -> ServiceStatus:
        return self._perform_action(
            service_name,
            "restart",
        )

    def _perform_action(
        self,
        service_name: str,
        action: str,
    ) -> ServiceStatus:
        self._validate_service_name(service_name)

        with self._locks[service_name]:
            script = r"""
& {
    param(
        [string]$Name,
        [string]$Action,
        [int]$TimeoutSeconds
    )

    $OutputEncoding = [Console]::OutputEncoding =
        [System.Text.UTF8Encoding]::new()

    $service = Get-Service `
        -Name $Name `
        -ErrorAction Stop

    $timeout = [TimeSpan]::FromSeconds(
        $TimeoutSeconds
    )

    switch ($Action) {
        "start" {
            if (
                $service.Status -ne
                [System.ServiceProcess.ServiceControllerStatus]::Running
            ) {
                Start-Service `
                    -Name $Name `
                    -ErrorAction Stop
            }

            $service = Get-Service -Name $Name

            $service.WaitForStatus(
                [System.ServiceProcess.ServiceControllerStatus]::Running,
                $timeout
            )
        }

        "stop" {
            if (
                $service.Status -ne
                [System.ServiceProcess.ServiceControllerStatus]::Stopped
            ) {
                Stop-Service `
                    -Name $Name `
                    -Force `
                    -ErrorAction Stop
            }

            $service = Get-Service -Name $Name

            $service.WaitForStatus(
                [System.ServiceProcess.ServiceControllerStatus]::Stopped,
                $timeout
            )
        }

        "restart" {
            if (
                $service.Status -ne
                [System.ServiceProcess.ServiceControllerStatus]::Stopped
            ) {
                Stop-Service `
                    -Name $Name `
                    -Force `
                    -ErrorAction Stop

                $service = Get-Service -Name $Name

                $service.WaitForStatus(
                    [System.ServiceProcess.ServiceControllerStatus]::Stopped,
                    $timeout
                )
            }

            Start-Service `
                -Name $Name `
                -ErrorAction Stop

            $service = Get-Service -Name $Name

            $service.WaitForStatus(
                [System.ServiceProcess.ServiceControllerStatus]::Running,
                $timeout
            )
        }

        default {
            throw "Acción no soportada: $Action"
        }
    }

    $escapedName = $Name.Replace("'", "''")

    $serviceInfo = Get-CimInstance `
        -ClassName Win32_Service `
        -Filter "Name='$escapedName'" `
        -ErrorAction Stop

    [PSCustomObject]@{
        exists = $true
        name = $serviceInfo.Name
        state = $serviceInfo.State.ToLowerInvariant()
        start_mode = $serviceInfo.StartMode
        process_id = [int]$serviceInfo.ProcessId
        message = $null
    } | ConvertTo-Json -Compress
}
"""

            payload = self._run(
                script,
                service_name,
                action,
                str(self._timeout_seconds),
            )

            return self._to_status(
                payload,
                service_name,
            )

    def _run(
        self,
        script: str,
        *arguments: str,
    ) -> dict:
        command = [
            self._executable,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
            *arguments,
        ]

        creation_flags = getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0,
        )

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=self._timeout_seconds + 10,
                creationflags=creation_flags,
            )
        except (
            OSError,
            subprocess.TimeoutExpired,
        ) as exc:
            raise ServiceOperationError(
                f"No fue posible ejecutar PowerShell: {exc}"
            ) from exc

        if completed.returncode != 0:
            message = (
                completed.stderr
                or completed.stdout
            ).strip()

            raise ServiceOperationError(
                message
                or "PowerShell finalizó con error."
            )

        output_lines = [
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        ]

        if not output_lines:
            raise ServiceOperationError(
                "PowerShell no devolvió información."
            )

        try:
            return json.loads(output_lines[-1])
        except json.JSONDecodeError as exc:
            raise ServiceOperationError(
                "Respuesta inválida de PowerShell: "
                f"{output_lines[-1]}"
            ) from exc

    @staticmethod
    def _validate_service_name(
        service_name: str,
    ) -> None:
        if not SERVICE_NAME_PATTERN.fullmatch(
            service_name
        ):
            raise ServiceOperationError(
                "Nombre de servicio inválido."
            )

    @staticmethod
    def _to_status(
        payload: dict,
        fallback_name: str,
    ) -> ServiceStatus:
        process_id = payload.get("process_id")

        if process_id in {0, "0", None}:
            process_id = None

        return ServiceStatus(
            exists=bool(payload.get("exists")),
            name=str(
                payload.get("name")
                or fallback_name
            ),
            state=str(
                payload.get("state")
                or "unknown"
            ).lower(),
            start_mode=payload.get("start_mode"),
            process_id=(
                int(process_id)
                if process_id is not None
                else None
            ),
            message=payload.get("message"),
        )


class MockServiceManager(ServiceManager):
    def __init__(self) -> None:
        self._states: dict[str, str] = {}
        self._lock = threading.Lock()

    def get_status(
        self,
        service_name: str,
    ) -> ServiceStatus:
        with self._lock:
            state = self._states.setdefault(
                service_name,
                "stopped",
            )

        return ServiceStatus(
            exists=True,
            name=service_name,
            state=state,
            start_mode="Manual",
            process_id=None,
            message=(
                "Backend simulado para desarrollo."
            ),
        )

    def start(
        self,
        service_name: str,
    ) -> ServiceStatus:
        return self._set_state(
            service_name,
            "running",
        )

    def stop(
        self,
        service_name: str,
    ) -> ServiceStatus:
        return self._set_state(
            service_name,
            "stopped",
        )

    def restart(
        self,
        service_name: str,
    ) -> ServiceStatus:
        return self._set_state(
            service_name,
            "running",
        )

    def _set_state(
        self,
        service_name: str,
        state: str,
    ) -> ServiceStatus:
        with self._lock:
            self._states[service_name] = state

        return self.get_status(service_name)