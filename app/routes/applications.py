from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
    request,
    stream_with_context,
)
from flask_login import current_user

from app.container import get_container
from app.security import (
    AccessLevel,
    access_required,
)
from app.services.application_service import (
    ActorContext,
)
from app.services.log_service import (
    LogAccessError,
)
from app.services.windows_service_manager import (
    ServiceOperationError,
)

applications_bp = Blueprint(
    "applications",
    __name__,
    url_prefix="/applications",
)


@applications_bp.get("/<string:code>")
@access_required(AccessLevel.VIEWER)
def detail(code: str):
    container = get_container()

    application = (
        container.application_service
        .get_application(code)
    )

    try:
        log_lines = container.log_service.tail(
            application.log_file,
            lines=200,
        )
    except LogAccessError as exc:
        log_lines = [
            f"[Control Center] {exc}"
        ]

    return render_template(
        "applications/detail.html",
        application=application,
        log_lines=log_lines,
    )


@applications_bp.get(
    "/<string:code>/status"
)
@access_required(AccessLevel.VIEWER)
def status(code: str):
    container = get_container()

    application = (
        container.application_service
        .get_application(code)
    )

    try:
        snapshot = (
            container.application_service
            .get_snapshot(application)
        )

        return jsonify(snapshot)

    except ServiceOperationError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 503


@applications_bp.post(
    "/<string:code>/actions/<string:action>"
)
@access_required(AccessLevel.OPERATOR)
def perform_action(
    code: str,
    action: str,
):
    container = get_container()

    application = (
        container.application_service
        .get_application(code)
    )

    actor = ActorContext(
        user_id=getattr(
            current_user,
            "id",
            None,
        ),
        email=getattr(
            current_user,
            "email",
            None,
        ),
        remote_address=request.remote_addr,
    )

    try:
        result = (
            container.application_service
            .perform_action(
                application=application,
                action=action,
                actor=actor,
            )
        )

        return jsonify(
            {
                "ok": True,
                "message": (
                    f"Acción {action} ejecutada "
                    "correctamente."
                ),
                "service": result,
            }
        )

    except (
        ValueError,
        PermissionError,
    ) as exc:
        return jsonify(
            {
                "ok": False,
                "error": str(exc),
            }
        ), 400

    except ServiceOperationError as exc:
        return jsonify(
            {
                "ok": False,
                "error": str(exc),
            }
        ), 503


@applications_bp.get(
    "/<string:code>/logs/stream"
)
@access_required(AccessLevel.VIEWER)
def stream_logs(code: str):
    container = get_container()

    application = (
        container.application_service
        .get_application(code)
    )

    try:
        generator = container.log_service.stream(
            application.log_file
        )
    except LogAccessError as exc:
        return jsonify(
            {"error": str(exc)}
        ), 400

    response = Response(
        stream_with_context(generator),
        mimetype="text/event-stream",
    )

    response.headers[
        "Cache-Control"
    ] = "no-cache"

    response.headers[
        "X-Accel-Buffering"
    ] = "no"

    return response