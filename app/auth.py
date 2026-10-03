from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .forms import LoginForm, RegisterForm
from .models import User

bp = Blueprint("auth", __name__)


def _safe_next(target):
    # Only allow relative redirects to avoid open-redirects.
    if target and not urlsplit(target).netloc and target.startswith("/"):
        return target
    return url_for("records.list_records")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("records.list_records"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Konto utworzone.", "success")
        return redirect(url_for("records.list_records"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("records.list_records"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(_safe_next(request.args.get("next")))
        flash("Nieprawidłowy login lub hasło.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Wylogowano.", "info")
    return redirect(url_for("auth.login"))
