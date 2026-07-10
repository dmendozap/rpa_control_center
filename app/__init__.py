from __future__ import annotations

from flask import Flask
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from app.cli import register_cli
from app.config import Config
from app.container import build_container, get_container
from app.error_handlers import register_error_handlers
from app.extensions import bcrypt, csrf, db, login_manager, migrate
from app.logging_config import configure_logging, register_request_context
from app.security import get_access_level


def create_app(config_class: type[Config] = Config) -> Flask:
    config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config["BEHIND_PROXY"]:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1,
        )

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    bcrypt.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para continuar."
    login_manager.login_message_category = "warning"

    configure_logging(app)
    register_request_context(app)

    app.extensions["rpa_control_services"] = build_container(app)

    _register_user_loader()
    _register_blueprints(app)
    _register_context_processors(app)
    _register_security_headers(app)

    register_error_handlers(app)
    register_cli(app)

    app.logger.info(
        "RPA Control Center initialized. env=%s backend=%s",
        app.config["APP_ENV"],
        app.config["SERVICE_BACKEND"],
    )

    return app


def _register_user_loader() -> None:
    @login_manager.user_loader
    def load_user(user_id: str):
        container = get_container()

        if user_id == "break-glass":
            return container.authentication.load_break_glass_user()

        if user_id.startswith("auth:"):
            raw_id = user_id.split(":", 1)[1]
            if raw_id.isdigit():
                return container.users.get_by_id(int(raw_id))

        return None


def _register_blueprints(app: Flask) -> None:
    from app.routes.applications import applications_bp
    from app.routes.audit import audit_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.health import health_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(health_bp)


def _register_context_processors(app: Flask) -> None:
    @app.context_processor
    def inject_security_context():
        return {
            "access_level": get_access_level(current_user),
        }


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self'; "
            "script-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';",
        )
        return response