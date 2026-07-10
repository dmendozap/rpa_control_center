from flask import Blueprint, render_template

from app.container import get_container
from app.security import (
    AccessLevel,
    access_required,
)

audit_bp = Blueprint(
    "audit",
    __name__,
    url_prefix="/audit",
)


@audit_bp.get("/")
@access_required(AccessLevel.ADMIN)
def index():
    events = (
        get_container()
        .audit
        .list_recent(limit=300)
    )

    return render_template(
        "audit/index.html",
        events=events,
    )