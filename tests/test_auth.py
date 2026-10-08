from app.models import User

from .helpers import login, logout, make_user


def test_register_creates_user_and_logs_in(client, app):
    resp = client.post(
        "/register",
        data={"name": "Asha", "email": "Asha@College.edu", "password": "password123"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/dashboard")
    with app.app_context():
        user = User.query.filter_by(email="asha@college.edu").one()
        assert user.password_hash != "password123"
    assert client.get("/dashboard").status_code == 200


def test_register_rejects_duplicate_email(client, app):
    make_user(app)
    resp = client.post(
        "/register",
        data={"name": "Again", "email": "student@college.edu", "password": "password123"},
    )
    assert resp.status_code == 400
    assert b"already exists" in resp.data


def test_register_rejects_short_password(client):
    resp = client.post("/register", data={"name": "A", "email": "a@b.edu", "password": "short"})
    assert resp.status_code == 400


def test_login_and_logout(client, app):
    make_user(app)
    assert login(client, password="wrong-pass").status_code == 401
    assert login(client).status_code == 302
    assert client.get("/dashboard").status_code == 200
    logout(client)
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_ignores_external_next(client, app):
    make_user(app)
    resp = client.post(
        "/login?next=//evil.example.com",
        data={"email": "student@college.edu", "password": "password123"},
    )
    assert resp.headers["Location"].endswith("/dashboard")


def test_create_admin_cli(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin", "--email", "boss@college.edu", "--password", "password123"]
    )
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert User.query.filter_by(email="boss@college.edu").one().is_site_admin
