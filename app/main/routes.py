from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    send_from_directory,
    current_app,
)
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Library, LibraryMember

main_bp = Blueprint("main", __name__, url_prefix="")


@main_bp.route("/")
@login_required
def dashboard():
    memberships = (
        LibraryMember.query.filter_by(user_id=current_user.id)
        .join(Library)
        .order_by(Library.name)
        .all()
    )
    return render_template("main/dashboard.html", memberships=memberships)


@main_bp.route("/library/create", methods=["POST"])
@login_required
def create_library():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Podaj nazwę biblioteki.", "danger")
        return redirect(url_for("main.dashboard"))

    library = Library(name=name, owner_id=current_user.id)
    db.session.add(library)
    db.session.flush()
    db.session.add(
        LibraryMember(library_id=library.id, user_id=current_user.id, role="owner")
    )
    db.session.commit()
    flash(f"Utworzono bibliotekę „{name}”.", "success")
    return redirect(url_for("library.home", library_id=library.id))


@main_bp.route("/library/join", methods=["POST"])
@login_required
def join_library():
    code = request.form.get("join_code", "").strip().upper()
    library = Library.query.filter_by(join_code=code).first()
    if not library:
        flash("Nie znaleziono biblioteki o podanym kodzie.", "danger")
        return redirect(url_for("main.dashboard"))

    existing = LibraryMember.query.filter_by(
        library_id=library.id, user_id=current_user.id
    ).first()
    if existing:
        flash("Już należysz do tej biblioteki.", "info")
    else:
        db.session.add(
            LibraryMember(library_id=library.id, user_id=current_user.id, role="member")
        )
        db.session.commit()
        flash(f"Dołączono do biblioteki „{library.name}”.", "success")
    return redirect(url_for("library.home", library_id=library.id))


@main_bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@main_bp.route("/privacy")
def privacy():
    return render_template("main/privacy.html")
