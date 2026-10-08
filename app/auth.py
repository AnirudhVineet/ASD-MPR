from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import metrics
from .extensions import db
from .models import User

bp = Blueprint("auth", __name__)

MIN_PASSWORD_LENGTH = 8


def site_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_site_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def _safe_next(target: str | None) -> str | None:
    # Only allow relative redirects to avoid open-redirects via ?next=
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not name or not email or "@" not in email:
            error = "Please provide your name and a valid email."
        elif len(password) < MIN_PASSWORD_LENGTH:
            error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        elif User.query.filter_by(email=email).first():
            error = "An account with that email already exists."

        if error:
            flash(error, "error")
            return render_template("auth/register.html", name=name, email=email), 400

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        metrics.REGISTRATIONS.inc()
        login_user(user)
        flash(f"Welcome, {user.name}!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            metrics.LOGINS.labels(result="failure").inc()
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html", email=email), 401

        metrics.LOGINS.labels(result="success").inc()
        login_user(user, remember=bool(request.form.get("remember")))
        flash("Logged in.", "success")
        return redirect(_safe_next(request.args.get("next")) or url_for("main.dashboard"))

    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("main.index"))
