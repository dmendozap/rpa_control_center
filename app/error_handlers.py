from __future__ import annotations

import logging

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
)
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

logger = logging.getLogger(__name__)


def register_error_handlers(
    app: Flask,
) -> None:
    @app.errorhandler(401)
    def unauthorized(error):
        if request.path.startswith(
            "/applications/"
        ):
            return jsonify(
                {
                    "error":
                        "Autenticación requerida."
                }
            ), 401

        return render_template(
            "errors/401.html"
        ), 401

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith(
            "/applications/"
        ):
            return jsonify(
                {
                    "error":
                        "Permiso insuficiente."
                }
            ), 403

        return render_template(
            "errors/403.html"
        ), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template(
            "errors/404.html"
        ), 404

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        logger.exception("Database error")

        return render_template(
            "errors/500.html"
        ), 500

    @app.errorhandler(Exception)
    def unexpected_error(error):
        db.session.rollback()
        logger.exception("Unexpected error")

        return render_template(
            "errors/500.html"
        ), 500