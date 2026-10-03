from functools import wraps

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .csv_export import csv_response
from .models import Subscriber

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def _filtered_query():
    query = Subscriber.query
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(Subscriber.email.ilike(like) | Subscriber.name.ilike(like))
    return query.order_by(Subscriber.created_at.desc(), Subscriber.id.desc())


@bp.route("/subscribers")
@admin_required
def subscribers():
    page = request.args.get("page", 1, type=int)
    pagination = _filtered_query().paginate(
        page=page, per_page=current_app.config["RECORDS_PER_PAGE"], error_out=False
    )
    return render_template("admin/subscribers.html", pagination=pagination)


@bp.route("/subscribers.csv")
@admin_required
def export_subscribers():
    rows = (
        (s.id, s.name, s.email, s.industry, s.created_at.strftime("%Y-%m-%d %H:%M"))
        for s in _filtered_query()
    )
    return csv_response(["id", "imie", "email", "branza", "data_zapisu"], rows, "subskrybenci.csv")


@bp.route("/subscribers/<int:subscriber_id>/delete", methods=["POST"])
@admin_required
def delete_subscriber(subscriber_id):
    # Potrzebne np. przy żądaniu usunięcia danych (RODO).
    sub = db.session.get(Subscriber, subscriber_id) or abort(404)
    email = sub.email
    db.session.delete(sub)
    db.session.commit()
    flash(f"Usunięto {email}.", "info")
    return redirect(url_for("admin.subscribers", **request.args.to_dict()))
