from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # Konta zakłada teraz LoginHub (jedno konto do wszystkich appek) — appka
    # przekierowuje na jego rejestrację zamiast pokazywać własny, osobny
    # formularz, żeby nie powstawały konta "tylko lokalne" bez SSO.
    from urllib.parse import quote
    next_url = request.args.get("next") or url_for("main.dashboard")
    return redirect(f"/auth/register?next={quote(next_url)}")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("main.dashboard"))
        flash("Nieprawidłowy e-mail lub hasło.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Wylogowano.", "info")
    return redirect(url_for("auth.login"))
