from __future__ import annotations

import logging
from html import escape
from typing import Any

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from jinja2 import TemplateNotFound
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

logger = logging.getLogger(__name__)


def register_error_handlers(
    app: Flask,
) -> None:
    @app.errorhandler(401)
    def unauthorized(error):
        if _wants_json_response():
            return jsonify(
                {
                    "ok": False,
                    "error": "Autenticación requerida.",
                }
            ), 401

        next_url = (
            request.full_path
            if request.query_string
            else request.path
        )

        return redirect(
            url_for(
                "auth.login",
                next=next_url,
            )
        )

    @app.errorhandler(403)
    def forbidden(error):
        if _wants_json_response():
            return jsonify(
                {
                    "ok": False,
                    "error": "Permiso insuficiente.",
                }
            ), 403

        return _render_error_page(
            template_name="errors/403.html",
            status_code=403,
            title="Acceso denegado",
            message=(
                "No tienes permisos suficientes "
                "para ejecutar esta operación."
            ),
        )

    @app.errorhandler(404)
    def not_found(error):
        if _wants_json_response():
            return jsonify(
                {
                    "ok": False,
                    "error": "Recurso no encontrado.",
                }
            ), 404

        return _render_error_page(
            template_name="errors/404.html",
            status_code=404,
            title="Recurso no encontrado",
            message=(
                "La página o aplicación solicitada "
                "no existe."
            ),
        )

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()

        logger.exception(
            "Database error",
            exc_info=error,
        )

        if _wants_json_response():
            return jsonify(
                {
                    "ok": False,
                    "error": (
                        "No fue posible completar "
                        "la operación de base de datos."
                    ),
                }
            ), 500

        return _render_error_page(
            template_name="errors/500.html",
            status_code=500,
            title="Error interno",
            message=(
                "Ocurrió un error al acceder "
                "a la base de datos."
            ),
        )

    @app.errorhandler(Exception)
    def unexpected_error(error):
        db.session.rollback()

        logger.exception(
            "Unexpected error",
            exc_info=error,
        )

        if _wants_json_response():
            return jsonify(
                {
                    "ok": False,
                    "error": (
                        "Ocurrió un error inesperado."
                    ),
                }
            ), 500

        return _render_error_page(
            template_name="errors/500.html",
            status_code=500,
            title="Error interno",
            message=(
                "Ocurrió un error inesperado. "
                "Consulta los logs del Control Center."
            ),
        )


def _wants_json_response() -> bool:
    if request.path.startswith("/applications/"):
        return True

    best_match = request.accept_mimetypes.best

    return best_match in {
        "application/json",
        "text/event-stream",
    }


def _render_error_page(
    *,
    template_name: str,
    status_code: int,
    title: str,
    message: str,
) -> tuple[Any, int]:
    try:
        return (
            render_template(template_name),
            status_code,
        )

    except TemplateNotFound:
        logger.error(
            "Error template not found: %s",
            template_name,
        )

        safe_title = escape(title)
        safe_message = escape(message)

        fallback_html = f"""<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>{status_code} | {safe_title}</title>
</head>
<body>
    <main>
        <h1>{status_code}</h1>
        <h2>{safe_title}</h2>
        <p>{safe_message}</p>
        <a href="/">Volver al inicio</a>
    </main>
</body>
</html>
"""

        return fallback_html, status_code