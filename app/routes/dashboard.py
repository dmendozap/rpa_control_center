from flask import Blueprint, render_template

from app.container import get_container
from app.security import (
    AccessLevel,
    access_required,
)

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
)


@dashboard_bp.get("/")
@access_required(AccessLevel.VIEWER)
def index():
    applications = (
        get_container()
        .application_service
        .list_applications()
    )

    return render_template(
        "dashboard/index.html",
        applications=applications,
    )