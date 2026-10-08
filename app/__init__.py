from flask import Flask, render_template

from .config import Config
from .extensions import csrf, db, login_manager

ERRORS = {
    403: ("Forbidden", "You don't have permission to do that."),
    404: ("Not found", "We couldn't find that page."),
}


def create_app(config_object=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    from .auth import bp as auth_bp
    from .cli import register_cli
    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    register_cli(app)

    for code, (title, message) in ERRORS.items():
        app.register_error_handler(
            code,
            lambda e, code=code, title=title, message=message: (
                render_template("error.html", code=code, title=title, message=message),
                code,
            ),
        )

    with app.app_context():
        db.create_all()

    return app
