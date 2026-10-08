import click

from .extensions import db
from .models import User


def register_cli(app) -> None:
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", default="Site Admin", show_default=True)
    @click.password_option(help="Only used when creating a new user.")
    def create_admin(email: str, name: str, password: str) -> None:
        """Create a site admin, or promote an existing user to site admin."""
        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            action = "Created"
        else:
            action = "Promoted"
        user.is_site_admin = True
        db.session.commit()
        click.echo(f"{action} site admin {email}")
