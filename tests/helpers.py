from app.extensions import db
from app.models import User


def make_user(
    app, email="student@college.edu", name="Student", password="password123", admin=False
):
    with app.app_context():
        user = User(name=name, email=email, is_site_admin=admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client, email="student@college.edu", password="password123"):
    return client.post("/login", data={"email": email, "password": password})


def logout(client):
    return client.post("/logout")
