from datetime import datetime, timedelta

from app.extensions import db
from app.models import RSVP, Announcement, Event, Membership

from .helpers import login, logout, make_user
from .test_clubs import make_club


def make_event(app, club_id, capacity=None, days=7):
    with app.app_context():
        event = Event(
            club_id=club_id,
            title="Robot Wars",
            location="Lab 3",
            starts_at=datetime.now() + timedelta(days=days),
            capacity=capacity,
        )
        db.session.add(event)
        db.session.commit()
        return event.id


def join(app, user_id, club_id):
    with app.app_context():
        db.session.add(Membership(user_id=user_id, club_id=club_id))
        db.session.commit()


def test_club_admin_creates_and_edits_event(client, app):
    lead = make_user(app, email="lead@college.edu")
    club_id = make_club(app, admin_id=lead)
    login(client, email="lead@college.edu")
    starts = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    resp = client.post(
        f"/clubs/{club_id}/events/new",
        data={"title": "Kickoff", "starts_at": starts, "location": "Hall A", "capacity": "50"},
    )
    assert resp.status_code == 302
    with app.app_context():
        event = Event.query.filter_by(title="Kickoff").one()
        assert event.capacity == 50
        event_id = event.id

    resp = client.post(
        f"/events/{event_id}/edit",
        data={"title": "Kickoff 2.0", "starts_at": starts, "capacity": ""},
    )
    assert resp.status_code == 302
    with app.app_context():
        event = db.session.get(Event, event_id)
        assert event.title == "Kickoff 2.0" and event.capacity is None

    assert b"Kickoff 2.0" in client.get("/events").data


def test_invalid_event_form(client, app):
    lead = make_user(app, email="lead@college.edu")
    club_id = make_club(app, admin_id=lead)
    login(client, email="lead@college.edu")
    resp = client.post(f"/clubs/{club_id}/events/new", data={"title": "X", "starts_at": "soon"})
    assert resp.status_code == 400


def test_member_cannot_create_event(client, app):
    user_id = make_user(app)
    club_id = make_club(app)
    join(app, user_id, club_id)
    login(client)
    assert client.get(f"/clubs/{club_id}/events/new").status_code == 403


def test_rsvp_requires_membership(client, app):
    user_id = make_user(app)
    club_id = make_club(app)
    event_id = make_event(app, club_id)
    login(client)
    client.post(f"/events/{event_id}/rsvp")
    with app.app_context():
        assert RSVP.query.count() == 0
    join(app, user_id, club_id)
    client.post(f"/events/{event_id}/rsvp")
    client.post(f"/events/{event_id}/rsvp")  # no duplicates
    with app.app_context():
        assert RSVP.query.filter_by(user_id=user_id).count() == 1
    client.post(f"/events/{event_id}/rsvp/cancel")
    with app.app_context():
        assert RSVP.query.count() == 0


def test_rsvp_blocked_when_full(client, app):
    first = make_user(app, email="first@college.edu")
    second = make_user(app, email="second@college.edu")
    club_id = make_club(app)
    join(app, first, club_id)
    join(app, second, club_id)
    event_id = make_event(app, club_id, capacity=1)

    login(client, email="first@college.edu")
    client.post(f"/events/{event_id}/rsvp")
    logout(client)
    login(client, email="second@college.edu")
    resp = client.post(f"/events/{event_id}/rsvp", follow_redirects=True)
    assert b"full" in resp.data
    with app.app_context():
        assert RSVP.query.filter_by(event_id=event_id).count() == 1


def test_rsvp_blocked_for_past_event(client, app):
    user_id = make_user(app)
    club_id = make_club(app)
    join(app, user_id, club_id)
    event_id = make_event(app, club_id, days=-1)
    login(client)
    client.post(f"/events/{event_id}/rsvp")
    with app.app_context():
        assert RSVP.query.count() == 0


def test_organizer_sees_attendees(client, app):
    lead = make_user(app, email="lead@college.edu", name="Lead")
    member = make_user(app, email="member@college.edu", name="Mira Member")
    club_id = make_club(app, admin_id=lead)
    join(app, member, club_id)
    event_id = make_event(app, club_id)
    login(client, email="member@college.edu")
    client.post(f"/events/{event_id}/rsvp")
    assert b"Attendees" not in client.get(f"/events/{event_id}").data
    logout(client)
    login(client, email="lead@college.edu")
    assert b"Mira Member" in client.get(f"/events/{event_id}").data


def test_announcements_flow(client, app):
    lead = make_user(app, email="lead@college.edu")
    member = make_user(app, email="member@college.edu")
    club_id = make_club(app, admin_id=lead)
    join(app, member, club_id)

    login(client, email="member@college.edu")
    resp = client.post(f"/clubs/{club_id}/announcements", data={"title": "Hi", "body": "x"})
    assert resp.status_code == 403
    logout(client)

    login(client, email="lead@college.edu")
    client.post(
        f"/clubs/{club_id}/announcements",
        data={"title": "Meeting moved", "body": "Now in room 204"},
    )
    logout(client)

    login(client, email="member@college.edu")
    assert b"Meeting moved" in client.get("/dashboard").data
    logout(client)

    login(client, email="lead@college.edu")
    with app.app_context():
        announcement_id = Announcement.query.one().id
    client.post(f"/clubs/{club_id}/announcements/{announcement_id}/delete")
    with app.app_context():
        assert Announcement.query.count() == 0


def test_deleting_club_cascades(client, app):
    make_user(app, email="admin@college.edu", admin=True)
    club_id = make_club(app)
    make_event(app, club_id)
    login(client, email="admin@college.edu")
    client.post(f"/clubs/{club_id}/delete")
    with app.app_context():
        assert Event.query.count() == 0


# ── AM-30: RSVP End-to-End Lifecycle Test ─────────────────────────────────────


def test_rsvp_full_lifecycle(client, app):
    """
    Complete RSVP lifecycle:
      1. Student registers and logs in.
      2. Student joins a club.
      3. An upcoming event exists for that club.
      4. Student RSVPs → DB record created, event-detail page shows "You're going".
      5. RSVP appears on the student's dashboard (AM-27 Going to section).
      6. Student cancels RSVP → DB record removed.
      7. Dashboard no longer shows the RSVP (empty Going to state).
    """
    # 1. Register + login
    user_id = make_user(app, email="student@college.edu", name="Sam Student")
    club_id = make_club(app)
    event_id = make_event(app, club_id)  # 7 days from now

    # 2. Join club (non-member cannot RSVP — business rule enforced)
    join(app, user_id, club_id)

    login(client, email="student@college.edu")

    # 3. Confirm non-member block is bypassed now we've joined
    with app.app_context():
        assert RSVP.query.count() == 0

    # 4. RSVP
    resp = client.post(f"/events/{event_id}/rsvp", follow_redirects=True)
    assert resp.status_code == 200
    assert b"You&#39;re going" in resp.data or b"You're going" in resp.data

    # 5. Verify DB record
    with app.app_context():
        assert RSVP.query.filter_by(user_id=user_id, event_id=event_id).count() == 1

    # 6. Verify RSVP appears on dashboard (AM-27 Going to section)
    dashboard = client.get("/dashboard")
    assert b"Going to" in dashboard.data
    assert b"Robot Wars" in dashboard.data  # event title from make_event

    # 7. Cancel RSVP
    resp = client.post(f"/events/{event_id}/rsvp/cancel", follow_redirects=True)
    assert resp.status_code == 200

    # 8. Verify DB record removed
    with app.app_context():
        assert RSVP.query.filter_by(user_id=user_id, event_id=event_id).count() == 0

    # 9. Verify dashboard no longer shows the RSVP
    dashboard = client.get("/dashboard")
    assert b"No upcoming RSVPs" in dashboard.data

