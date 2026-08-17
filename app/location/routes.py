from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required

from ..extensions import db
from ..models import Location, Cabinet
from ..utils import get_library_or_403

location_bp = Blueprint("location", __name__, url_prefix="/location")


@location_bp.route("/library/<int:library_id>/create", methods=["POST"])
@login_required
def create(library_id):
    library, membership = get_library_or_403(library_id)
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Podaj nazwę lokalizacji.", "danger")
    else:
        loc = Location(library_id=library.id, name=name, description=description or None)
        db.session.add(loc)
        db.session.commit()
        flash(f"Dodano lokalizację „{name}”.", "success")

    return redirect(url_for("library.home", library_id=library.id))


@location_bp.route("/<int:location_id>")
@login_required
def view(location_id):
    location = Location.query.get_or_404(location_id)
    library, membership = get_library_or_403(location.library_id)
    cabinets = Cabinet.query.filter_by(location_id=location.id).order_by(Cabinet.name).all()
    return render_template(
        "location/view.html",
        library=library,
        membership=membership,
        location=location,
        cabinets=cabinets,
    )


@location_bp.route("/<int:location_id>/delete", methods=["POST"])
@login_required
def delete(location_id):
    location = Location.query.get_or_404(location_id)
    library, membership = get_library_or_403(location.library_id)
    db.session.delete(location)
    db.session.commit()
    flash("Usunięto lokalizację.", "info")
    return redirect(url_for("library.home", library_id=library.id))
