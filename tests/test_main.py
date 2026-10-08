def test_index_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Campus Clubs" in resp.data


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_404_page(client):
    resp = client.get("/this-page-does-not-exist")
    assert resp.status_code == 404
    assert b"404" in resp.data
    assert b"Go home" in resp.data


def test_403_page(client, app):
    # /clubs/new requires site_admin; a logged-in regular student is 403, not a redirect
    from tests.helpers import login, make_user

    make_user(app)
    login(client)
    resp = client.get("/clubs/new")
    assert resp.status_code == 403
    assert b"403" in resp.data
    assert b"Go home" in resp.data


# ── AM-27: My RSVPs on Dashboard ──────────────────────────────────────────────


def test_dashboard_shows_my_rsvp(client, app):
    """A user who has RSVP'd to an event sees it in the Going to section."""
    from tests.helpers import login, make_user
    from tests.test_clubs import make_club
    from tests.test_events import join, make_event

    user_id = make_user(app)
    club_id = make_club(app)
    join(app, user_id, club_id)
    event_id = make_event(app, club_id)  # defaults to 7 days from now
    login(client)
    client.post(f"/events/{event_id}/rsvp")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Going to" in resp.data
    assert b"Robot Wars" in resp.data  # event title set by make_event fixture


def test_dashboard_no_rsvps_shows_empty_state(client, app):
    """A user with no RSVPs sees the empty state for the Going to section."""
    from tests.helpers import login, make_user

    make_user(app)
    login(client)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Going to" in resp.data
    assert b"No upcoming RSVPs" in resp.data


def test_dashboard_does_not_show_other_users_rsvp(client, app):
    """One user's RSVP must not appear on another user's dashboard."""
    from tests.helpers import login, logout, make_user
    from tests.test_clubs import make_club
    from tests.test_events import join, make_event

    user_a = make_user(app, email="a@college.edu", name="Alice")
    user_b = make_user(app, email="b@college.edu", name="Bob")
    club_id = make_club(app)
    join(app, user_a, club_id)
    join(app, user_b, club_id)
    event_id = make_event(app, club_id)

    login(client, email="a@college.edu")
    client.post(f"/events/{event_id}/rsvp")
    logout(client)

    login(client, email="b@college.edu")
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"No upcoming RSVPs" in resp.data


def test_dashboard_existing_sections_intact(client, app):
    """My clubs and Upcoming events in my clubs sections are unaffected by AM-27."""
    from tests.helpers import login, make_user
    from tests.test_clubs import make_club
    from tests.test_events import join, make_event

    user_id = make_user(app)
    club_id = make_club(app)
    join(app, user_id, club_id)
    make_event(app, club_id)
    login(client)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"My clubs" in resp.data
    assert b"Upcoming events in my clubs" in resp.data
    assert b"stat-value" in resp.data

