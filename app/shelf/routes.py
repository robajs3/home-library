from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required

from ..extensions import db
from ..models import Shelf, Cabinet, Book
from ..utils import get_library_or_403

shelf_bp = Blueprint("shelf", __name__, url_prefix="/shelf")


@shelf_bp.route("/cabinet/<int:cabinet_id>/create", methods=["POST"])
@login_required
def create(cabinet_id):
    cabinet = Cabinet.query.get_or_404(cabinet_id)
    library, membership = get_library_or_403(cabinet.location.library_id)
    name = request.form.get("name", "").strip()

    if not name:
        flash("Podaj nazwę półki.", "danger")
    else:
        shelf = Shelf(cabinet_id=cabinet.id, name=name)
        db.session.add(shelf)
        db.session.commit()
        flash(f"Dodano półkę „{name}”.", "success")

    return redirect(url_for("cabinet.view", cabinet_id=cabinet.id))


@shelf_bp.route("/<int:shelf_id>")
@login_required
def view(shelf_id):
    shelf = Shelf.query.get_or_404(shelf_id)
    library, membership = get_library_or_403(shelf.cabinet.location.library_id)
    books = (
        Book.query.filter_by(shelf_id=shelf.id, is_removed=False)
        .order_by(Book.title)
        .all()
    )
    return render_template(
        "shelf/view.html",
        library=library,
        membership=membership,
        shelf=shelf,
        books=books,
    )


@shelf_bp.route("/<int:shelf_id>/delete", methods=["POST"])
@login_required
def delete(shelf_id):
    shelf = Shelf.query.get_or_404(shelf_id)
    library, membership = get_library_or_403(shelf.cabinet.location.library_id)
    cabinet_id = shelf.cabinet_id
    db.session.delete(shelf)
    db.session.commit()
    flash("Usunięto półkę.", "info")
    return redirect(url_for("cabinet.view", cabinet_id=cabinet_id))
