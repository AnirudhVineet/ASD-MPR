from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import metrics
from .auth import site_admin_required
from .extensions import db
from .models import ROLE_ADMIN, ROLE_MEMBER, Club, Membership, User

bp = Blueprint("clubs", __name__, url_prefix="/clubs")

CATEGORIES = [
    "Academic",
    "Arts & Culture",
    "Community Service",
    "Cultural",
    "Media",
    "Sports",
    "Technology",
    "Other",
]


def get_club_or_404(club_id: int) -> Club:
    club = db.session.get(Club, club_id)
    if club is None:
        abort(404)
    return club


def require_manager(club: Club) -> None:
    if not current_user.is_authenticated or not current_user.can_manage(club):
        abort(403)


def _club_form_errors(name: str, category: str, existing: Club | None = None) -> str | None:
    if not name:
        return "Club name is required."
    if category not in CATEGORIES:
        return "Please choose a valid category."
    clash = Club.query.filter(db.func.lower(Club.name) == name.lower()).first()
    if clash is not None and clash is not existing:
        return "A club with that name already exists."
    return None


@bp.route("/")
def directory():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    query = Club.query
    if q:
        query = query.filter(Club.name.ilike(f"%{q}%"))
    if category:
        query = query.filter_by(category=category)
    clubs = query.order_by(Club.name).all()
    return render_template(
        "clubs/directory.html", clubs=clubs, q=q, category=category, categories=CATEGORIES
    )


@bp.route("/new", methods=["GET", "POST"])
@site_admin_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "")
        description = request.form.get("description", "").strip()
        admin_email = request.form.get("admin_email", "").strip().lower()

        error = _club_form_errors(name, category)
        admin = None
        if not error and admin_email:
            admin = User.query.filter_by(email=admin_email).first()
            if admin is None:
                error = "No registered user has that club admin email."
        if error:
            flash(error, "error")
            return (
                render_template(
                    "clubs/form.html", club=None, form=request.form, categories=CATEGORIES
                ),
                400,
            )

        club = Club(name=name, category=category, description=description)
        db.session.add(club)
        if admin is not None:
            db.session.add(Membership(user=admin, club=club, role=ROLE_ADMIN))
        db.session.commit()
        flash(f"Created {club.name}.", "success")
        return redirect(url_for("clubs.detail", club_id=club.id))

    return render_template("clubs/form.html", club=None, form={}, categories=CATEGORIES)


@bp.route("/<int:club_id>")
def detail(club_id):
    club = get_club_or_404(club_id)
    membership = current_user.membership_for(club) if current_user.is_authenticated else None
    can_manage = current_user.is_authenticated and current_user.can_manage(club)
    return render_template(
        "clubs/detail.html", club=club, membership=membership, can_manage=can_manage
    )


@bp.route("/<int:club_id>/edit", methods=["GET", "POST"])
@login_required
def edit(club_id):
    club = get_club_or_404(club_id)
    require_manager(club)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "")
        error = _club_form_errors(name, category, existing=club)
        if error:
            flash(error, "error")
            return (
                render_template(
                    "clubs/form.html", club=club, form=request.form, categories=CATEGORIES
                ),
                400,
            )
        club.name = name
        club.category = category
        club.description = request.form.get("description", "").strip()
        db.session.commit()
        flash("Club updated.", "success")
        return redirect(url_for("clubs.detail", club_id=club.id))

    form = {"name": club.name, "category": club.category, "description": club.description}
    return render_template("clubs/form.html", club=club, form=form, categories=CATEGORIES)


@bp.route("/<int:club_id>/delete", methods=["POST"])
@site_admin_required
def delete(club_id):
    club = get_club_or_404(club_id)
    name = club.name
    db.session.delete(club)
    db.session.commit()
    flash(f"Deleted {name}.", "info")
    return redirect(url_for("clubs.directory"))


@bp.route("/<int:club_id>/join", methods=["POST"])
@login_required
def join(club_id):
    club = get_club_or_404(club_id)
    if not current_user.is_member_of(club):
        db.session.add(Membership(user_id=current_user.id, club_id=club.id, role=ROLE_MEMBER))
        db.session.commit()
        metrics.MEMBERSHIP_CHANGES.labels(action="join").inc()
        flash(f"You joined {club.name}!", "success")
    return redirect(url_for("clubs.detail", club_id=club.id))


@bp.route("/<int:club_id>/leave", methods=["POST"])
@login_required
def leave(club_id):
    club = get_club_or_404(club_id)
    membership = current_user.membership_for(club)
    if membership is not None:
        db.session.delete(membership)
        db.session.commit()
        metrics.MEMBERSHIP_CHANGES.labels(action="leave").inc()
        flash(f"You left {club.name}.", "info")
    return redirect(url_for("clubs.detail", club_id=club_id))


@bp.route("/<int:club_id>/members")
@login_required
def members(club_id):
    club = get_club_or_404(club_id)
    require_manager(club)
    memberships = (
        Membership.query.filter_by(club_id=club.id).join(User).order_by(User.name).all()
    )
    return render_template("clubs/members.html", club=club, memberships=memberships)


def _get_membership_or_404(club: Club, user_id: int) -> Membership:
    membership = Membership.query.filter_by(club_id=club.id, user_id=user_id).first()
    if membership is None:
        abort(404)
    return membership


@bp.route("/<int:club_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_member(club_id, user_id):
    club = get_club_or_404(club_id)
    require_manager(club)
    membership = _get_membership_or_404(club, user_id)
    name = membership.user.name
    db.session.delete(membership)
    db.session.commit()
    metrics.MEMBERSHIP_CHANGES.labels(action="remove").inc()
    flash(f"Removed {name}.", "info")
    return redirect(url_for("clubs.members", club_id=club.id))


@bp.route("/<int:club_id>/members/<int:user_id>/role", methods=["POST"])
@login_required
def set_role(club_id, user_id):
    club = get_club_or_404(club_id)
    require_manager(club)
    membership = _get_membership_or_404(club, user_id)
    role = request.form.get("role")
    if role not in (ROLE_MEMBER, ROLE_ADMIN):
        abort(400)
    membership.role = role
    db.session.commit()
    flash(f"{membership.user.name} is now a club {role}.", "success")
    return redirect(url_for("clubs.members", club_id=club.id))
