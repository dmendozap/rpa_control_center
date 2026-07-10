from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_user,
    logout_user,
)

from app.container import get_container
from app.forms import LoginForm
from app.security import is_safe_redirect_target

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)


@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():
    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard.index")
        )

    form = LoginForm()

    if form.validate_on_submit():
        container = get_container()

        result = (
            container.authentication.authenticate(
                form.identifier.data,
                form.password.data,
            )
        )

        actor_email = getattr(
            result.user,
            "email",
            None,
        )
        actor_user_id = getattr(
            result.user,
            "id",
            None,
        )

        if result.user is not None:
            login_user(result.user)

            container.audit.record(
                action="auth.login",
                result="success",
                actor_user_id=actor_user_id,
                actor_email=actor_email,
                remote_address=request.remote_addr,
                message=result.message,
                details={
                    "break_glass":
                        result.user.get_id()
                        == "break-glass"
                },
            )

            next_url = request.args.get("next")

            if is_safe_redirect_target(next_url):
                return redirect(next_url)

            return redirect(
                url_for("dashboard.index")
            )

        container.audit.record(
            action="auth.login",
            result="denied",
            actor_user_id=None,
            actor_email=(
                form.identifier.data
                .strip()
                .lower()
            ),
            remote_address=request.remote_addr,
            message=result.code,
        )

        if (
            result.code
            == "password_change_required"
        ):
            flash(
                result.message
                + " URL: "
                + current_app.config[
                    "AUTH_MANAGER_URL"
                ]
                + "/auth/change-password",
                "warning",
            )
        else:
            flash(
                result.message,
                "danger",
            )

    return render_template(
        "auth/login.html",
        form=form,
    )


@auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        container = get_container()

        container.audit.record(
            action="auth.logout",
            result="success",
            actor_user_id=getattr(
                current_user,
                "id",
                None,
            ),
            actor_email=getattr(
                current_user,
                "email",
                None,
            ),
            remote_address=request.remote_addr,
            message="Sesión finalizada.",
        )

        logout_user()

    flash(
        "Sesión finalizada correctamente.",
        "info",
    )

    return redirect(
        url_for("auth.login")
    )