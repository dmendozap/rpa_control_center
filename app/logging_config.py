from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4

from flask import Flask, g, has_request_context, request
from flask_login import current_user


class RequestContextFilter(logging.Filter):
    def filter(
        self,
        record: logging.LogRecord,
    ) -> bool:
        record.request_id = "-"
        record.remote_address = "-"
        record.user_email = "-"

        if has_request_context():
            record.request_id = getattr(
                g,
                "request_id",
                "-",
            )
            record.remote_address = request.headers.get(
                "X-Forwarded-For",
                request.remote_addr or "-",
            ).split(",")[0].strip()

            if current_user.is_authenticated:
                record.user_email = getattr(
                    current_user,
                    "email",
                    "-",
                )

        return True


def configure_logging(app: Flask) -> None:
    log_directory = Path(
        app.config["LOG_DIRECTORY"]
    )
    log_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | "
        "rpa-control-center | "
        "request_id=%(request_id)s | "
        "user=%(user_email)s | "
        "remote=%(remote_address)s | "
        "%(name)s | %(message)s"
    )

    context_filter = RequestContextFilter()

    file_handler = RotatingFileHandler(
        log_directory / "application.log",
        maxBytes=app.config["LOG_MAX_BYTES"],
        backupCount=app.config["LOG_BACKUP_COUNT"],
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)

    error_handler = RotatingFileHandler(
        log_directory / "error.log",
        maxBytes=app.config["LOG_MAX_BYTES"],
        backupCount=app.config["LOG_BACKUP_COUNT"],
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(context_filter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger("waitress").setLevel(
        logging.INFO
    )
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING
    )


def register_request_context(app: Flask) -> None:
    @app.before_request
    def assign_request_id() -> None:
        g.request_id = (
            request.headers.get("X-Request-ID")
            or uuid4().hex
        )

    @app.after_request
    def add_request_id(response):
        response.headers["X-Request-ID"] = getattr(
            g,
            "request_id",
            "-",
        )
        return response