import re

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from . import db
from .models import Subscriber, utcnow

bp = Blueprint("newsletter", __name__)

# Celowo prosty wzorzec: jedna „@”, brak spacji, domena z kropką.
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")

INDUSTRIES = [
    "IT / Technologie",
    "Marketing / Media",
    "Handel / E-commerce",
    "Finanse",
    "Medycyna / Zdrowie",
    "Edukacja",
    "Produkcja",
    "Inna",
]

SUCCESS_MESSAGE = "Dziękujemy! Twój adres został zapisany."


def validate_subscription(data):
    """Zwraca (oczyszczone_dane, lista_błędów)."""
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    industry = (data.get("industry") or "").strip()
    consent = data.get("consent") in (True, "true", "on", "1", 1)

    errors = []
    if not email or len(email) > 254 or not EMAIL_RE.match(email) or ".." in email:
        errors.append("Podaj poprawny adres e-mail.")
    if len(name) > 100:
        errors.append("Imię może mieć maksymalnie 100 znaków.")
    if industry and industry not in INDUSTRIES:
        errors.append("Wybierz branżę z listy.")
    if not consent:
        errors.append("Zgoda na przetwarzanie danych jest wymagana.")

    return {"email": email, "name": name, "industry": industry}, errors


def save_subscriber(clean):
    """Zapisuje subskrybenta; ponowny zapis tego samego adresu nie jest błędem."""
    if Subscriber.query.filter_by(email=clean["email"]).first():
        return
    db.session.add(Subscriber(consent_at=utcnow(), **clean))
    try:
        db.session.commit()
    except IntegrityError:
        # Równoległy zapis tego samego adresu — traktujemy jak sukces.
        db.session.rollback()


@bp.route("/")
def landing():
    return render_template("newsletter/landing.html", industries=INDUSTRIES)


@bp.route("/subscribe", methods=["POST"])
def subscribe():
    wants_json = request.is_json
    data = request.get_json(silent=True) if wants_json else request.form
    if not hasattr(data, "get"):
        data = {}

    # Ukryte pole-pułapka: ludzie go nie widzą, boty zwykle je wypełniają.
    if data.get("website"):
        return (jsonify(ok=True, message=SUCCESS_MESSAGE) if wants_json
                else redirect(url_for("newsletter.landing", _anchor="zapisz")))

    clean, errors = validate_subscription(data)
    if errors:
        if wants_json:
            return jsonify(ok=False, errors=errors), 400
        for e in errors:
            flash(e, "error")
        return redirect(url_for("newsletter.landing", _anchor="zapisz"))

    save_subscriber(clean)

    # Ten sam komunikat dla nowych i już zapisanych adresów,
    # żeby nie dało się sprawdzić, kto jest na liście.
    if wants_json:
        return jsonify(ok=True, message=SUCCESS_MESSAGE)
    flash(SUCCESS_MESSAGE, "success")
    return redirect(url_for("newsletter.landing", _anchor="zapisz"))
