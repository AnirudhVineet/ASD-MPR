from datetime import datetime

from flask import Blueprint, render_template
from sqlalchemy import text

from .extensions import db
from .models import Club, Event

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


@bp.route("/healthz")
def healthz():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return {"status": "error", "database": "unreachable"}, 503
    return {"status": "ok"}
