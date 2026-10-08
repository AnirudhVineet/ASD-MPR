from datetime import datetime

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import text

from .extensions import db
from .models import RSVP, Announcement, Club, Event, Membership

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    upcoming = (
        Event.query.filter(Event.starts_at >= datetime.now())
        .order_by(Event.starts_at)
        .limit(5)
        .all()
    )
    clubs = Club.query.order_by(Club.created_at.desc()).limit(6).all()
    return render_template("index.html", upcoming=upcoming, clubs=clubs)


@bp.route("/dashboard")
@login_required
def dashboard():
    memberships = (
        Membership.query.filter_by(user_id=current_user.id)
        .join(Club)
        .order_by(Club.name)
        .all()
    )
    club_ids = [m.club_id for m in memberships]
    events = (
        Event.query.filter(Event.club_id.in_(club_ids), Event.starts_at >= datetime.now())
        .order_by(Event.starts_at)
        .limit(10)
        .all()
        if club_ids
        else []
    )
    announcements = (
        Announcement.query.filter(Announcement.club_id.in_(club_ids))
        .order_by(Announcement.created_at.desc())
        .limit(10)
        .all()
        if club_ids
        else []
    )
    my_rsvps = (
        RSVP.query.filter_by(user_id=current_user.id)
        .join(Event)
        .filter(Event.starts_at >= datetime.now())
        .order_by(Event.starts_at)
        .limit(10)
        .all()
    )
    return render_template(
        "dashboard.html",
        memberships=memberships,
        events=events,
        announcements=announcements,
        my_rsvps=my_rsvps,
    )


@bp.route("/healthz")
def healthz():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return {"status": "error", "database": "unreachable"}, 503
    return {"status": "ok"}
