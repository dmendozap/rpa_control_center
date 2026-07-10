from __future__ import annotations

import json
from pathlib import Path

import click
from flask import Flask
from sqlalchemy import select, text
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (
    AuditEvent,
    ManagedApplication,
    Role,
)
from app.repositories import ApplicationRepository


def register_cli(app: Flask) -> None:
    @app.cli.command("init-control-db")
    def init_control_db() -> None:
        """Crea el schema y tablas del Control Center."""

        db.session.execute(
            text(
                "CREATE SCHEMA IF NOT EXISTS "
                "rpa_control"
            )
        )
        db.session.commit()

        db.metadata.create_all(
            bind=db.engine,
            tables=[
                ManagedApplication.__table__,
                AuditEvent.__table__,
            ],
        )

        click.echo(
            "Schema rpa_control y tablas "
            "creados correctamente."
        )

    @app.cli.command("seed-applications")
    @click.option(
        "--file",
        "file_path",
        default="config/applications.json",
        show_default=True,
        type=click.Path(
            exists=True,
            dir_okay=False,
            path_type=Path,
        ),
    )
    def seed_applications(
        file_path: Path,
    ) -> None:
        """Registra o actualiza aplicaciones."""

        payload = json.loads(
            file_path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(payload, list):
            raise click.ClickException(
                "El JSON debe contener una lista."
            )

        repository = ApplicationRepository()

        try:
            for item in payload:
                _validate_application_payload(item)
                repository.upsert(item)

            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        click.echo(
            f"{len(payload)} aplicaciones "
            "registradas correctamente."
        )

    @app.cli.command("seed-control-roles")
    def seed_control_roles() -> None:
        """Crea los roles base en auth.role."""

        role_names = [
            "RPA_CONTROL_VIEWER",
            "RPA_CONTROL_OPERATOR",
            "RPA_CONTROL_ADMIN",
        ]

        created = 0

        for role_name in role_names:
            existing = db.session.scalar(
                select(Role).where(
                    Role.role_description
                    == role_name
                )
            )

            if existing is None:
                db.session.add(
                    Role(
                        role_description=role_name
                    )
                )
                created += 1

        db.session.commit()

        click.echo(
            f"Roles creados: {created}."
        )

    @app.cli.command("generate-password-hash")
    @click.password_option(
        prompt="Contraseña",
        confirmation_prompt=True,
    )
    def generate_hash(
        password: str,
    ) -> None:
        """Genera hash para la cuenta break-glass."""

        click.echo(
            generate_password_hash(
                password,
                method="pbkdf2:sha256",
                salt_length=16,
            )
        )


def _validate_application_payload(
    payload: dict,
) -> None:
    required_fields = {
        "code",
        "name",
        "service_name",
    }

    missing = sorted(
        required_fields - payload.keys()
    )

    if missing:
        raise click.ClickException(
            "Faltan campos obligatorios: "
            + ", ".join(missing)
        )