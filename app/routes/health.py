from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint(
    "health",
    __name__,
    url_prefix="/health",
)


@health_bp.get("/live")
def live():
    return jsonify(
        {
            "status": "ok",
            "application":
                "rpa-control-center",
        }
    )


@health_bp.get("/ready")
def ready():
    try:
        db.session.execute(
            text("SELECT 1")
        )

        return jsonify(
            {
                "status": "ready",
                "application":
                    "rpa-control-center",
                "database": "ok",
            }
        )

    except Exception:
        db.session.rollback()

        return jsonify(
            {
                "status": "unavailable",
                "application":
                    "rpa-control-center",
                "database": "error",
            }
        ), 503