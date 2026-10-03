import pytest

from app import create_app, db
from app.models import Subscriber


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
    })
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def subscribe(client, email="test@example.com", name="Jan", industry="IT / Technologie", consent="on"):
    return client.post("/subscribe", data={
        "email": email, "name": name, "industry": industry, "consent": consent
    })


def test_landing_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Zapisz się" in r.get_data(as_text=True)


def test_subscribe_success(client, app):
    r = subscribe(client)
    assert r.status_code == 302
    with app.app_context():
        s = Subscriber.query.filter_by(email="test@example.com").one()
        assert s.name == "Jan"
        assert s.consent_at is not None


def test_subscribe_ajax_returns_json(client, app):
    r = client.post("/subscribe", json={"email": "ajax@example.com", "consent": True})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_subscribe_invalid_email(client):
    r = client.post("/subscribe", data={"email": "niepoprawny", "consent": "on"})
    # Redirect z błędem lub 400
    assert r.status_code in (302, 400)


def test_subscribe_without_consent(client, app):
    r = subscribe(client, consent="")
    assert r.status_code in (302, 400)
    with app.app_context():
        assert Subscriber.query.count() == 0


def test_duplicate_email_is_silent(client, app):
    subscribe(client, email="dup@example.com")
    subscribe(client, email="dup@example.com")
    with app.app_context():
        assert Subscriber.query.filter_by(email="dup@example.com").count() == 1


def test_bot_trap(client, app):
    client.post("/subscribe", data={"email": "bot@example.com", "consent": "on", "website": "spam"})
    with app.app_context():
        assert Subscriber.query.count() == 0


def test_admin_panel_requires_admin(client, app):
    # Rejestracja zwykłego użytkownika nie daje dostępu do panelu admina.
    client.post("/register", data={"username": "alice", "password": "secret123", "confirm": "secret123"})
    r = client.get("/admin/subscribers")
    assert r.status_code == 403


def test_admin_panel_ok_for_admin(client, app):
    client.post("/register", data={"username": "admin", "password": "secret123", "confirm": "secret123"})
    with app.app_context():
        from app.models import User
        u = User.query.filter_by(username="admin").one()
        u.is_admin = True
        db.session.commit()
    client.post("/login", data={"username": "admin", "password": "secret123"})
    r = client.get("/admin/subscribers")
    assert r.status_code == 200
    assert "Subskrybenci" in r.get_data(as_text=True)


def test_admin_export_csv(client, app):
    subscribe(client, email="csv@example.com")
    client.post("/register", data={"username": "adm", "password": "secret123", "confirm": "secret123"})
    with app.app_context():
        from app.models import User
        u = User.query.filter_by(username="adm").one()
        u.is_admin = True
        db.session.commit()
    client.post("/login", data={"username": "adm", "password": "secret123"})
    r = client.get("/admin/subscribers.csv")
    assert r.status_code == 200
    assert "csv@example.com" in r.get_data(as_text=True)
