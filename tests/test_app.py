import pytest

from app import create_app, db
from app.models import Record


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


def register(client, username="alice", password="secret123"):
    return client.post(
        "/register",
        data={"username": username, "password": password, "confirm": password},
        follow_redirects=True,
    )


def test_records_require_login(client):
    resp = client.get("/records/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_register_login_logout(client):
    assert "Konto utworzone" in register(client).get_data(as_text=True)
    client.post("/logout")
    resp = client.post("/login", data={"username": "alice", "password": "zle"}, follow_redirects=True)
    assert "Nieprawidłowy login" in resp.get_data(as_text=True)
    resp = client.post("/login", data={"username": "alice", "password": "secret123"})
    assert resp.status_code == 302


def test_duplicate_username_rejected(client):
    register(client)
    client.post("/logout")
    resp = register(client)
    assert "zajęty" in resp.get_data(as_text=True)


def test_login_ignores_external_next(client):
    register(client)
    client.post("/logout")
    resp = client.post(
        "/login?next=https://evil.example/",
        data={"username": "alice", "password": "secret123"},
    )
    assert "evil.example" not in resp.headers["Location"]


def test_crud_and_export(client, app):
    register(client)
    client.post("/records/new", data={"name": "Pierwszy", "category": "A", "date": "2026-10-01", "description": "opis"})
    client.post("/records/new", data={"name": "Drugi", "category": "B"})

    page = client.get("/records/").get_data(as_text=True)
    assert "Pierwszy" in page and "Drugi" in page

    filtered = client.get("/records/?category=A").get_data(as_text=True)
    assert "Pierwszy" in filtered and "Drugi" not in filtered

    searched = client.get("/records/?q=opis").get_data(as_text=True)
    assert "Pierwszy" in searched and "Drugi" not in searched

    with app.app_context():
        rid = Record.query.filter_by(name="Pierwszy").one().id

    client.post(f"/records/{rid}/edit", data={"name": "Zmieniony", "category": "A"})
    csv_text = client.get("/records/export.csv").get_data(as_text=True)
    assert "Zmieniony" in csv_text and "alice" in csv_text

    client.post(f"/records/{rid}/delete")
    with app.app_context():
        assert db.session.get(Record, rid) is None


def test_create_requires_name(client):
    register(client)
    resp = client.post("/records/new", data={"name": ""})
    assert resp.status_code == 200
    assert "Nowy rekord" in resp.get_data(as_text=True)
