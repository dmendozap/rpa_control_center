from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_csv(name: str, default: str = "") -> frozenset[str]:
    value = os.getenv(name, default)
    return frozenset(
        item.strip().upper()
        for item in value.split(",")
        if item.strip()
    )


def env_paths(name: str, default: str) -> tuple[Path, ...]:
    value = os.getenv(name, default)
    paths: list[Path] = []

    for item in value.split(";"):
        item = item.strip()

        if item:
            paths.append(
                Path(os.path.expandvars(item)).resolve(strict=False)
            )

    return tuple(paths)


class Config:
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    SECRET_KEY = os.getenv("SECRET_KEY", "")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/rpa",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_size": 10,
        "max_overflow": 20,
    }

    CONTROL_CENTER_HOST = os.getenv("CONTROL_CENTER_HOST", "0.0.0.0")
    CONTROL_CENTER_PORT = int(os.getenv("CONTROL_CENTER_PORT", "8090"))
    CONTROL_CENTER_THREADS = int(os.getenv("CONTROL_CENTER_THREADS", "8"))
    CONTROL_CENTER_CONNECTION_LIMIT = int(
        os.getenv("CONTROL_CENTER_CONNECTION_LIMIT", "100")
    )
    CONTROL_CENTER_CHANNEL_TIMEOUT = int(
        os.getenv("CONTROL_CENTER_CHANNEL_TIMEOUT", "120")
    )

    SERVICE_BACKEND = os.getenv(
        "SERVICE_BACKEND",
        "windows" if os.name == "nt" else "mock",
    ).strip().lower()

    POWERSHELL_EXECUTABLE = os.getenv(
        "POWERSHELL_EXECUTABLE",
        "powershell.exe",
    )
    SERVICE_ACTION_TIMEOUT_SECONDS = int(
        os.getenv("SERVICE_ACTION_TIMEOUT_SECONDS", "45")
    )

    HEALTHCHECK_TIMEOUT_SECONDS = float(
        os.getenv("HEALTHCHECK_TIMEOUT_SECONDS", "3")
    )
    HEALTHCHECK_VERIFY_TLS = env_bool(
        "HEALTHCHECK_VERIFY_TLS",
        False,
    )

    LOG_DIRECTORY = Path(
        os.path.expandvars(
            os.getenv("LOG_DIRECTORY", str(BASE_DIR / "logs"))
        )
    ).resolve(strict=False)

    ALLOWED_LOG_ROOTS = env_paths(
        "ALLOWED_LOG_ROOTS",
        str(LOG_DIRECTORY),
    )

    LOG_MAX_BYTES = int(
        os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024))
    )
    LOG_BACKUP_COUNT = int(
        os.getenv("LOG_BACKUP_COUNT", "10")
    )
    LOG_STREAM_POLL_SECONDS = float(
        os.getenv("LOG_STREAM_POLL_SECONDS", "1.0")
    )

    AUTH_MANAGER_URL = os.getenv(
        "AUTH_MANAGER_URL",
        "http://127.0.0.1:5000",
    ).rstrip("/")

    MAX_FAILED_LOGIN_ATTEMPTS = int(
        os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5")
    )
    ACCOUNT_LOCK_MINUTES = int(
        os.getenv("ACCOUNT_LOCK_MINUTES", "15")
    )

    CONTROL_CENTER_VIEWER_ROLES = env_csv(
        "CONTROL_CENTER_VIEWER_ROLES",
        "RPA_CONTROL_VIEWER,RPA_CONTROL_OPERATOR,RPA_CONTROL_ADMIN",
    )
    CONTROL_CENTER_OPERATOR_ROLES = env_csv(
        "CONTROL_CENTER_OPERATOR_ROLES",
        "RPA_CONTROL_OPERATOR,RPA_CONTROL_ADMIN",
    )
    CONTROL_CENTER_ADMIN_ROLES = env_csv(
        "CONTROL_CENTER_ADMIN_ROLES",
        "RPA_CONTROL_ADMIN",
    )

    BREAK_GLASS_ENABLED = env_bool(
        "BREAK_GLASS_ENABLED",
        False,
    )
    BREAK_GLASS_USERNAME = os.getenv(
        "BREAK_GLASS_USERNAME",
        "control-recovery",
    ).strip().lower()

    BREAK_GLASS_PASSWORD_HASH = os.getenv(
        "BREAK_GLASS_PASSWORD_HASH",
        "",
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = env_bool(
        "SESSION_COOKIE_SECURE",
        False,
    )
    SESSION_COOKIE_SAMESITE = os.getenv(
        "SESSION_COOKIE_SAMESITE",
        "Lax",
    )

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    WTF_CSRF_TIME_LIMIT = None

    BEHIND_PROXY = env_bool("BEHIND_PROXY", False)

    @classmethod
    def validate(cls) -> None:
        errors: list[str] = []

        if not cls.SECRET_KEY:
            errors.append("SECRET_KEY no está configurada.")

        if not cls.SQLALCHEMY_DATABASE_URI:
            errors.append("DATABASE_URL no está configurada.")

        if cls.SERVICE_BACKEND not in {"windows", "mock"}:
            errors.append(
                "SERVICE_BACKEND debe ser 'windows' o 'mock'."
            )

        if (
            cls.BREAK_GLASS_ENABLED
            and not cls.BREAK_GLASS_PASSWORD_HASH
        ):
            errors.append(
                "BREAK_GLASS_PASSWORD_HASH es obligatorio cuando "
                "BREAK_GLASS_ENABLED=true."
            )

        if errors:
            raise RuntimeError(
                "Configuración inválida: " + " ".join(errors)
            )