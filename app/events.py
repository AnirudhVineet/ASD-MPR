from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import metrics
from .clubs import get_club_or_404, require_manager
from .extensions import db
from .models import RSVP, Event

bp = Blueprint("events", __name__)

DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


def get_event_or_404(event_id: int) -> Event:
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    return event


def _parse_event_form(form) -> tuple[dict, str | None]:
    data = {
        "title": form.get("title", "").strip(),
        "description": form.get("description", "").strip(),
        "location": form.get("location", "").strip(),
    }
    if not data["title"]:
        return data, "Event title is required."
    try:
        data["starts_at"] = datetime.strptime(form.get("starts_at", ""), DATETIME_FORMAT)
    except ValueError:
        return data, "Please provide a valid start date and time."

    capacity = form.get("capacity", "").strip()
    if capacity:
        if not capacity.isdigit() or int(capacity) < 1:
            return data, "Capacity must be a positive whole number."
        data["capacity"] = int(capacity)
    else:
        data["capacity"] = None
    return data, None


def _form_values(event: Event) -> dict:
    return {
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "starts_at": event.starts_at.strftime(DATETIME_FORMAT),
        "capacity": event.capacity or "",
    }


@bp.route("/events")
def upcoming():
    events = (
        Event.query.filter(Event.starts_at >= datetime.now()).order_by(Event.starts_at).all()
    )
    return render_template("events/list.html", events=events)


@bp.route("/clubs/<int:club_id>/events/new", methods=["GET", "POST"])
@login_required
def create(club_id):
    club = get_club_or_404(club_id)
    require_manager(club)
    if request.method == "POST":
        data, error = _parse_event_form(request.form)
        if error:
            flash(error, "error")
            return (
                render_template("events/form.html", club=club, event=None, form=request.form),
                400,
            )
        event = Event(club_id=club.id, **data)
        db.session.add(event)
        db.session.commit()
        flash("Event created.", "success")
        return redirect(url_for("events.detail", event_id=event.id))
    return render_template("events/form.html", club=club, event=None, form={})


@bp.route("/events/<int:event_id>")
def detail(event_id):
    event = get_event_or_404(event_id)
    authed = current_user.is_authenticated
    return render_template(
        "events/detail.html",
        event=event,
        can_manage=authed and current_user.can_manage(event.club),
        is_member=authed and current_user.is_member_of(event.club),
        has_rsvp=authed and event.has_rsvp(current_user),
        is_past=event.starts_at < datetime.now(),
    )


@bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit(event_id):
    event = get_event_or_404(event_id)
    require_manager(event.club)
    if request.method == "POST":
        data, error = _parse_event_form(request.form)
        if error:
            flash(error, "error")
            return (
                render_template(
                    "events/form.html", club=event.club, event=event, form=request.form
                ),
                400,
            )
        for key, value in data.items():
            setattr(event, key, value)
        db.session.commit()
        flash("Event updated.", "success")
        return redirect(url_for("events.detail", event_id=event.id))
    return render_template(
        "events/form.html", club=event.club, event=event, form=_form_values(event)
    )


@bp.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
def delete(event_id):
    event = get_event_or_404(event_id)
    club_id = event.club_id
    require_manager(event.club)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted.", "info")
    return redirect(url_for("clubs.detail", club_id=club_id))


@bp.route("/events/<int:event_id>/rsvp", methods=["POST"])
@login_required
def rsvp(event_id):
    event = get_event_or_404(event_id)
    if not current_user.is_member_of(event.club):
        flash("Join the club to RSVP to its events.", "error")
    elif event.starts_at < datetime.now():
        flash("This event has already started.", "error")
    elif event.has_rsvp(current_user):
        flash("You're already going.", "info")
    elif event.is_full:
        flash("Sorry, this event is full.", "error")
    else:
        db.session.add(RSVP(user_id=current_user.id, event_id=event.id))
        db.session.commit()
        metrics.RSVPS.labels(action="rsvp").inc()
        flash("You're going! See you there.", "success")
    return redirect(url_for("events.detail", event_id=event_id))


@bp.route("/events/<int:event_id>/rsvp/cancel", methods=["POST"])
@login_required
def cancel_rsvp(event_id):
    get_event_or_404(event_id)
    existing = RSVP.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing is not None:
        db.session.delete(existing)
        db.session.commit()
        metrics.RSVPS.labels(action="cancel").inc()
        flash("RSVP cancelled.", "info")
    return redirect(url_for("events.detail", event_id=event_id))
