from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .csv_export import csv_response
from .forms import RecordForm
from .models import Record

bp = Blueprint("records", __name__, url_prefix="/records")

SORTABLE = {"name": Record.name, "category": Record.category, "date": Record.date, "updated": Record.updated_at}


def _filtered_query():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "updated")
    order = request.args.get("order", "desc")

    query = Record.query
    if q:
        like = f"%{q}%"
        query = query.filter(Record.name.ilike(like) | Record.description.ilike(like))
    if category:
        query = query.filter(Record.category == category)
    column = SORTABLE.get(sort, Record.updated_at)
    query = query.order_by(column.asc() if order == "asc" else column.desc(), Record.id.desc())
    return query


@bp.route("/")
@login_required
def list_records():
    page = request.args.get("page", 1, type=int)
    pagination = _filtered_query().paginate(
        page=page, per_page=current_app.config["RECORDS_PER_PAGE"], error_out=False
    )
    categories = [
        c for (c,) in db.session.query(Record.category).distinct().order_by(Record.category) if c
    ]
    return render_template("records/list.html", pagination=pagination, categories=categories)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create_record():
    form = RecordForm()
    if form.validate_on_submit():
        record = Record(created_by=current_user)
        form.populate_obj(record)
        db.session.add(record)
        db.session.commit()
        flash("Dodano rekord.", "success")
        return redirect(url_for("records.list_records"))
    return render_template("records/form.html", form=form, record=None)


@bp.route("/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_record(record_id):
    record = db.session.get(Record, record_id) or abort(404)
    form = RecordForm(obj=record)
    if form.validate_on_submit():
        form.populate_obj(record)
        db.session.commit()
        flash("Zapisano zmiany.", "success")
        return redirect(url_for("records.list_records"))
    return render_template("records/form.html", form=form, record=record)


@bp.route("/<int:record_id>/delete", methods=["POST"])
@login_required
def delete_record(record_id):
    record = db.session.get(Record, record_id) or abort(404)
    db.session.delete(record)
    db.session.commit()
    flash("Usunięto rekord.", "info")
    return redirect(url_for("records.list_records"))


@bp.route("/export.csv")
@login_required
def export_csv():
    rows = (
        (
            r.id,
            r.name,
            r.category or "",
            r.date.isoformat() if r.date else "",
            r.description or "",
            r.created_by.username if r.created_by else "",
            r.updated_at.strftime("%Y-%m-%d %H:%M"),
        )
        for r in _filtered_query()
    )
    return csv_response(
        ["id", "nazwa", "kategoria", "data", "opis", "autor", "zmieniono"], rows, "rekordy.csv"
    )
