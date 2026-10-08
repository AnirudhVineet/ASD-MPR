from flask import Flask

from .config import Config
from .extensions import csrf, db, login_manager


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

    from .main import bp as main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
