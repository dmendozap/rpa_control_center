from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Iterator


class LogAccessError(RuntimeError):
    pass


class LogService:
    def __init__(
        self,
        *,
        allowed_roots: tuple[Path, ...],
        poll_seconds: float,
    ) -> None:
        self._allowed_roots = tuple(
            root.resolve(strict=False)
            for root in allowed_roots
        )
        self._poll_seconds = poll_seconds

    def tail(
        self,
        raw_path: str | None,
        lines: int = 200,
    ) -> list[str]:
        path = self._validated_path(raw_path)

        if not path.exists():
            return [
                "[Control Center] "
                f"El archivo de log no existe: {path}"
            ]

        if not path.is_file():
            raise LogAccessError(
                "La ruta configurada no es un archivo."
            )

        with path.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            return list(
                deque(
                    handle,
                    maxlen=max(
                        1,
                        min(lines, 2000),
                    ),
                )
            )

    def stream(
        self,
        raw_path: str | None,
    ) -> Iterator[str]:
        path = self._validated_path(raw_path)

        def generate() -> Iterator[str]:
            position = (
                path.stat().st_size
                if path.exists()
                else 0
            )
            last_keepalive = time.monotonic()

            while True:
                try:
                    if (
                        path.exists()
                        and path.is_file()
                    ):
                        current_size = (
                            path.stat().st_size
                        )

                        if current_size < position:
                            position = 0

                        if current_size > position:
                            with path.open(
                                "r",
                                encoding="utf-8",
                                errors="replace",
                            ) as handle:
                                handle.seek(position)

                                for line in handle:
                                    payload = json.dumps(
                                        {
                                            "line": line.rstrip(
                                                "\r\n"
                                            )
                                        },
                                        ensure_ascii=False,
                                    )

                                    yield (
                                        f"data: {payload}\n\n"
                                    )

                                position = handle.tell()

                    now = time.monotonic()

                    if now - last_keepalive >= 15:
                        yield ": keepalive\n\n"
                        last_keepalive = now

                    time.sleep(
                        self._poll_seconds
                    )

                except GeneratorExit:
                    return

                except OSError as exc:
                    payload = json.dumps(
                        {
                            "line": (
                                "[Control Center] "
                                "Error leyendo log: "
                                f"{exc}"
                            )
                        },
                        ensure_ascii=False,
                    )

                    yield f"data: {payload}\n\n"

                    time.sleep(
                        self._poll_seconds
                    )

        return generate()

    def _validated_path(
        self,
        raw_path: str | None,
    ) -> Path:
        if not raw_path:
            raise LogAccessError(
                "La aplicación no tiene "
                "un log configurado."
            )

        path = Path(raw_path).resolve(
            strict=False
        )

        if not any(
            path == root or root in path.parents
            for root in self._allowed_roots
        ):
            raise LogAccessError(
                "La ruta del log está fuera de "
                "los directorios permitidos."
            )

        return path