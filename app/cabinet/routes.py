from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required

from ..extensions import db
from ..models import Cabinet, Location, Shelf
from ..utils import get_library_or_403, save_photo

cabinet_bp = Blueprint("cabinet", __name__, url_prefix="/cabinet")


@cabinet_bp.route("/location/<int:location_id>/create", methods=["POST"])
@login_required
def create(location_id):
    location = Location.query.get_or_404(location_id)
    library, membership = get_library_or_403(location.library_id)
    name = request.form.get("name", "").strip()

    if not name:
        flash("Podaj nazwę szafki.", "danger")
    else:
        photo = save_photo(request.files.get("photo"), "cabinets")
        cabinet = Cabinet(location_id=location.id, name=name, photo_filename=photo)
        db.session.add(cabinet)
        db.session.commit()
        flash(f"Dodano szafkę „{name}”.", "success")

    return redirect(url_for("location.view", location_id=location.id))


@cabinet_bp.route("/<int:cabinet_id>")
@login_required
def view(cabinet_id):
    cabinet = Cabinet.query.get_or_404(cabinet_id)
    library, membership = get_library_or_403(cabinet.location.library_id)
    shelves = Shelf.query.filter_by(cabinet_id=cabinet.id).order_by(Shelf.name).all()
    return render_template(
        "cabinet/view.html",
        library=library,
        membership=membership,
        cabinet=cabinet,
        shelves=shelves,
    )


@cabinet_bp.route("/<int:cabinet_id>/photo", methods=["POST"])
@login_required
def upload_photo(cabinet_id):
    cabinet = Cabinet.query.get_or_404(cabinet_id)
    library, membership = get_library_or_403(cabinet.location.library_id)
    photo = save_photo(request.files.get("photo"), "cabinets")
    if photo:
        cabinet.photo_filename = photo
        db.session.commit()
        flash("Zaktualizowano zdjęcie szafki.", "success")
    else:
        flash("Nie udało się dodać zdjęcia (dozwolone: png, jpg, jpeg, gif, webp).", "danger")
    return redirect(url_for("cabinet.view", cabinet_id=cabinet.id))


@cabinet_bp.route("/<int:cabinet_id>/delete", methods=["POST"])
@login_required
def delete(cabinet_id):
    cabinet = Cabinet.query.get_or_404(cabinet_id)
    library, membership = get_library_or_403(cabinet.location.library_id)
    location_id = cabinet.location_id
    db.session.delete(cabinet)
    db.session.commit()
    flash("Usunięto szafkę.", "info")
    return redirect(url_for("location.view", location_id=location_id))
