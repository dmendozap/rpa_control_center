from __future__ import annotations

import json
import os
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
    """Error al consultar o administrar un servicio Windows."""


class WindowsPowerShellServiceManager(ServiceManager):
    """Administra servicios Windows mediante PowerShell."""

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

        script = r'''
$ErrorActionPreference = "Stop"

$utf8 = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $utf8
[Console]::OutputEncoding = $utf8

$name = $env:RPA_SERVICE_NAME

if ([string]::IsNullOrWhiteSpace($name)) {
    throw "RPA_SERVICE_NAME no fue suministrado."
}

$escapedName = $name.Replace("'", "''")

$service = Get-CimInstance `
    -ClassName Win32_Service `
    -Filter "Name='$escapedName'" `
    -ErrorAction SilentlyContinue

if ($null -eq $service) {
    [PSCustomObject]@{
        exists = $false
        name = $name
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
'''

        payload = self._run(
            script,
            service_name=service_name,
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

        normalized_action = action.strip().lower()

        if normalized_action not in {
            "start",
            "stop",
            "restart",
        }:
            raise ServiceOperationError(
                f"Acción no soportada: {action}"
            )

        with self._locks[service_name]:
            script = r'''
$ErrorActionPreference = "Stop"

$utf8 = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $utf8
[Console]::OutputEncoding = $utf8

$name = $env:RPA_SERVICE_NAME
$action = $env:RPA_SERVICE_ACTION
$timeoutSeconds = [int]$env:RPA_SERVICE_TIMEOUT_SECONDS

if ([string]::IsNullOrWhiteSpace($name)) {
    throw "RPA_SERVICE_NAME no fue suministrado."
}

if ([string]::IsNullOrWhiteSpace($action)) {
    throw "RPA_SERVICE_ACTION no fue suministrado."
}

if ($timeoutSeconds -le 0) {
    throw "RPA_SERVICE_TIMEOUT_SECONDS no es válido."
}

$service = Get-Service `
    -Name $name `
    -ErrorAction Stop

$timeout = [TimeSpan]::FromSeconds(
    $timeoutSeconds
)

switch ($action) {
    "start" {
        if (
            $service.Status -ne
            [System.ServiceProcess.ServiceControllerStatus]::Running
        ) {
            Start-Service `
                -Name $name `
                -ErrorAction Stop
        }

        $service = Get-Service `
            -Name $name `
            -ErrorAction Stop

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
                -Name $name `
                -Force `
                -ErrorAction Stop
        }

        $service = Get-Service `
            -Name $name `
            -ErrorAction Stop

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
                -Name $name `
                -Force `
                -ErrorAction Stop

            $service = Get-Service `
                -Name $name `
                -ErrorAction Stop

            $service.WaitForStatus(
                [System.ServiceProcess.ServiceControllerStatus]::Stopped,
                $timeout
            )
        }

        Start-Service `
            -Name $name `
            -ErrorAction Stop

        $service = Get-Service `
            -Name $name `
            -ErrorAction Stop

        $service.WaitForStatus(
            [System.ServiceProcess.ServiceControllerStatus]::Running,
            $timeout
        )
    }

    default {
        throw "Acción no soportada: $action"
    }
}

$escapedName = $name.Replace("'", "''")

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
'''

            payload = self._run(
                script,
                service_name=service_name,
                action=normalized_action,
            )

            return self._to_status(
                payload,
                service_name,
            )

    def _run(
        self,
        script: str,
        *,
        service_name: str,
        action: str | None = None,
    ) -> dict:
        environment = os.environ.copy()

        environment.update(
            {
                "RPA_SERVICE_NAME": service_name,
                "RPA_SERVICE_ACTION": action or "",
                "RPA_SERVICE_TIMEOUT_SECONDS": str(
                    self._timeout_seconds
                ),
            }
        )

        command = [
            self._executable,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
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
                env=environment,
            )
        except (
            OSError,
            subprocess.TimeoutExpired,
        ) as exc:
            raise ServiceOperationError(
                "No fue posible ejecutar PowerShell: "
                f"{exc}"
            ) from exc

        if completed.returncode != 0:
            message = (
                completed.stderr
                or completed.stdout
                or ""
            ).strip()

            raise ServiceOperationError(
                message
                or "PowerShell finalizó con error."
            )

        output_lines = [
            line.strip().lstrip("\ufeff")
            for line in completed.stdout.splitlines()
            if line.strip()
        ]

        if not output_lines:
            raise ServiceOperationError(
                "PowerShell no devolvió información."
            )

        raw_payload = output_lines[-1]

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ServiceOperationError(
                "Respuesta inválida de PowerShell: "
                f"{raw_payload}"
            ) from exc

        if not isinstance(payload, dict):
            raise ServiceOperationError(
                "PowerShell devolvió una estructura inválida."
            )

        return payload

    @staticmethod
    def _validate_service_name(
        service_name: str,
    ) -> None:
        normalized = (
            service_name.strip()
            if isinstance(service_name, str)
            else ""
        )

        if not SERVICE_NAME_PATTERN.fullmatch(
            normalized
        ):
            raise ServiceOperationError(
                "Nombre de servicio inválido."
            )

    @staticmethod
    def _to_status(
        payload: dict,
        fallback_name: str,
    ) -> ServiceStatus:
        process_id = payload.get(
            "process_id"
        )

        if process_id in {
            0,
            "0",
            None,
            "",
        }:
            process_id = None

        return ServiceStatus(
            exists=bool(
                payload.get("exists")
            ),
            name=str(
                payload.get("name")
                or fallback_name
            ),
            state=str(
                payload.get("state")
                or "unknown"
            ).lower(),
            start_mode=payload.get(
                "start_mode"
            ),
            process_id=(
                int(process_id)
                if process_id is not None
                else None
            ),
            message=payload.get(
                "message"
            ),
        )


class MockServiceManager(ServiceManager):
    def __init__(self) -> None:
        self._states: dict[
            str,
            str,
        ] = {}
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
            self._states[
                service_name
            ] = state

        return self.get_status(
            service_name
        )