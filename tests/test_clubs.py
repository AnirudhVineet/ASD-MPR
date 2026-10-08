from app.extensions import db
from app.models import ROLE_ADMIN, Club, Membership

from .helpers import login, logout, make_user


def make_club(app, name="Robotics Club", category="Technology", admin_id=None):
    with app.app_context():
        club = Club(name=name, category=category, description="We build robots")
        db.session.add(club)
        db.session.flush()
        if admin_id:
            db.session.add(Membership(user_id=admin_id, club_id=club.id, role=ROLE_ADMIN))
        db.session.commit()
        return club.id


def test_site_admin_creates_club_with_admin(client, app):
    make_user(app, email="admin@college.edu", admin=True)
    lead = make_user(app, email="lead@college.edu", name="Lead")
    login(client, email="admin@college.edu")
    resp = client.post(
        "/clubs/new",
        data={
            "name": "Chess Club",
            "category": "Academic",
            "description": "Checkmate",
            "admin_email": "lead@college.edu",
        },
    )
    assert resp.status_code == 302
    with app.app_context():
        club = Club.query.filter_by(name="Chess Club").one()
        membership = Membership.query.filter_by(club_id=club.id, user_id=lead).one()
        assert membership.role == ROLE_ADMIN


def test_duplicate_club_name_rejected(client, app):
    make_user(app, email="admin@college.edu", admin=True)
    make_club(app, name="Chess Club")
    login(client, email="admin@college.edu")
    resp = client.post("/clubs/new", data={"name": "chess club", "category": "Academic"})
    assert resp.status_code == 400


def test_student_cannot_create_club(client, app):
    make_user(app)
    login(client)
    assert client.get("/clubs/new").status_code == 403


def test_directory_search_and_filter(client, app):
    make_club(app, name="Robotics Club", category="Technology")
    make_club(app, name="Drama Society", category="Arts & Culture")
    resp = client.get("/clubs/?q=robot")
    assert b"Robotics Club" in resp.data and b"Drama Society" not in resp.data
    resp = client.get("/clubs/?category=Arts+%26+Culture")
    assert b"Drama Society" in resp.data and b"Robotics Club" not in resp.data


def test_join_and_leave(client, app):
    user_id = make_user(app)
    club_id = make_club(app)
    login(client)
    client.post(f"/clubs/{club_id}/join")
    client.post(f"/clubs/{club_id}/join")  # idempotent
    with app.app_context():
        assert Membership.query.filter_by(user_id=user_id, club_id=club_id).count() == 1
    client.post(f"/clubs/{club_id}/leave")
    with app.app_context():
        assert Membership.query.filter_by(user_id=user_id, club_id=club_id).count() == 0


def test_club_admin_manages_members(client, app):
    lead = make_user(app, email="lead@college.edu")
    member = make_user(app, email="member@college.edu")
    club_id = make_club(app, admin_id=lead)

    login(client, email="member@college.edu")
    client.post(f"/clubs/{club_id}/join")
    assert client.get(f"/clubs/{club_id}/members").status_code == 403
    assert client.get(f"/clubs/{club_id}/edit").status_code == 403
    logout(client)

    login(client, email="lead@college.edu")
    assert b"member@college.edu" in client.get(f"/clubs/{club_id}/members").data
    client.post(f"/clubs/{club_id}/members/{member}/role", data={"role": "admin"})
    with app.app_context():
        m = Membership.query.filter_by(club_id=club_id, user_id=member).one()
        assert m.role == ROLE_ADMIN
    client.post(f"/clubs/{club_id}/members/{member}/remove")
    with app.app_context():
        assert Membership.query.filter_by(club_id=club_id, user_id=member).count() == 0


def test_club_admin_can_edit_but_not_delete(client, app):
    lead = make_user(app, email="lead@college.edu")
    club_id = make_club(app, admin_id=lead)
    login(client, email="lead@college.edu")
    resp = client.post(
        f"/clubs/{club_id}/edit",
        data={"name": "Robotics & AI", "category": "Technology", "description": "x"},
    )
    assert resp.status_code == 302
    assert client.post(f"/clubs/{club_id}/delete").status_code == 403


def test_unknown_club_404(client):
    assert client.get("/clubs/999").status_code == 404


def test_club_detail_renders_for_visitors_and_managers(client, app):
    lead = make_user(app, email="lead@college.edu")
    club_id = make_club(app, admin_id=lead)
    resp = client.get(f"/clubs/{club_id}")
    assert resp.status_code == 200 and b"Log in to join" in resp.data
    login(client, email="lead@college.edu")
    resp = client.get(f"/clubs/{club_id}")
    assert b"Manage members" in resp.data and b"Post announcement" in resp.data
