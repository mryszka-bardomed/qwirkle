import os

import click
from datetime import datetime, timezone
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "qwirkle.db")
        ),
        RECORDS_PER_PAGE=20,
    )
    if config:
        app.config.update(config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Zaloguj się, aby kontynuować."
    login_manager.login_message_category = "info"

    from . import models
    from .auth import bp as auth_bp
    from .admin import bp as admin_bp
    from .newsletter import bp as newsletter_bp
    from .records import bp as records_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(newsletter_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    @app.context_processor
    def template_globals():
        from flask_wtf.csrf import generate_csrf
        from markupsafe import Markup
        def form_csrf():
            return Markup(f'<input type="hidden" name="csrf_token" value="{generate_csrf()}">')
        return {
            "now": datetime.now(timezone.utc),
            "form_csrf": form_csrf,
        }

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.password_option("--password", prompt="Hasło")
    def create_admin(username, password):
        """Tworzy konto administratora albo nadaje uprawnienia istniejącemu."""
        user = models.User.query.filter_by(username=username).first()
        if user is None:
            user = models.User(username=username)
            db.session.add(user)
        user.set_password(password)
        user.is_admin = True
        db.session.commit()
        click.echo(f"Administrator {username} gotowy.")

    with app.app_context():
        db.create_all()
        _upgrade_schema()

    return app


def _upgrade_schema():
    # Bazy utworzone przed dodaniem panelu admina nie mają kolumny is_admin,
    # a create_all() nie zmienia istniejących tabel.
    columns = {c["name"] for c in db.inspect(db.engine).get_columns("user")}
    if "is_admin" not in columns:
        with db.engine.begin() as conn:
            conn.execute(db.text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
