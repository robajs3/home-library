from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Library, LibraryMember, Location, Book, Shelf, Cabinet, generate_join_code
from ..utils import get_library_or_403, owner_required

library_bp = Blueprint("library", __name__, url_prefix="/library")

# Dozwolone kolumny sortowania w spisie książek (klucz z URL -> kolumna SQLAlchemy).
_BOOK_SORT_COLUMNS = {
    "title": Book.title,
    "author": Book.author,
    "genre": Book.genre,
    "year": Book.year,
    "location": Location.name,
    "cabinet": Cabinet.name,
    "shelf": Shelf.name,
}


@library_bp.route("/<int:library_id>/books")
@login_required
def all_books(library_id):
    library, membership = get_library_or_403(library_id)

    query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "title")
    direction = request.args.get("dir", "asc")
    if sort not in _BOOK_SORT_COLUMNS:
        sort = "title"
    if direction not in ("asc", "desc"):
        direction = "asc"

    books_query = (
        Book.query.options(
            joinedload(Book.shelf).joinedload(Shelf.cabinet).joinedload(Cabinet.location)
        )
        .outerjoin(Shelf, Book.shelf_id == Shelf.id)
        .outerjoin(Cabinet, Shelf.cabinet_id == Cabinet.id)
        .outerjoin(Location, Cabinet.location_id == Location.id)
        .filter(Book.library_id == library.id, Book.is_removed.is_(False))
    )

    if query:
        like = f"%{query}%"
        books_query = books_query.filter(
            or_(
                Book.title.ilike(like),
                Book.author.ilike(like),
                Book.genre.ilike(like),
                Location.name.ilike(like),
                Cabinet.name.ilike(like),
                Shelf.name.ilike(like),
            )
        )

    sort_column = _BOOK_SORT_COLUMNS[sort]
    order = sort_column.desc() if direction == "desc" else sort_column.asc()
    books = books_query.order_by(order, Book.title).all()

    return render_template(
        "library/books.html",
        library=library,
        membership=membership,
        books=books,
        query=query,
        sort=sort,
        direction=direction,
    )


@library_bp.route("/<int:library_id>")
@login_required
def home(library_id):
    library, membership = get_library_or_403(library_id)

    query = request.args.get("q", "").strip()
    results = None
    if query:
        like = f"%{query}%"
        results = (
            Book.query.filter(Book.library_id == library.id, Book.is_removed.is_(False))
            .filter(
                or_(
                    Book.title.ilike(like),
                    Book.author.ilike(like),
                    Book.genre.ilike(like),
                    Book.cover_color.ilike(like),
                )
            )
            .order_by(Book.title)
            .all()
        )

    locations = Location.query.filter_by(library_id=library.id).order_by(Location.name).all()
    removed_count = Book.query.filter_by(library_id=library.id, is_removed=True).count()

    return render_template(
        "library/home.html",
        library=library,
        membership=membership,
        locations=locations,
        query=query,
        results=results,
        removed_count=removed_count,
    )


@library_bp.route("/<int:library_id>/removed")
@login_required
def removed_books(library_id):
    library, membership = get_library_or_403(library_id)
    books = (
        Book.query.filter_by(library_id=library.id, is_removed=True)
        .order_by(Book.title)
        .all()
    )
    return render_template(
        "library/removed.html", library=library, membership=membership, books=books
    )


@library_bp.route("/<int:library_id>/settings")
@login_required
def settings(library_id):
    library, membership = get_library_or_403(library_id)
    members = (
        LibraryMember.query.filter_by(library_id=library.id)
        .join(LibraryMember.user)
        .order_by(LibraryMember.role.desc())
        .all()
    )
    return render_template(
        "library/settings.html", library=library, membership=membership, members=members
    )


@library_bp.route("/<int:library_id>/rename", methods=["POST"])
@login_required
def rename(library_id):
    library, membership = get_library_or_403(library_id)
    owner_required(membership)
    name = request.form.get("name", "").strip()
    if name:
        library.name = name
        db.session.commit()
        flash("Zmieniono nazwę biblioteki.", "success")
    return redirect(url_for("library.settings", library_id=library.id))


@library_bp.route("/<int:library_id>/regenerate-code", methods=["POST"])
@login_required
def regenerate_code(library_id):
    library, membership = get_library_or_403(library_id)
    owner_required(membership)
    library.join_code = generate_join_code()
    db.session.commit()
    flash("Wygenerowano nowy kod dołączenia.", "success")
    return redirect(url_for("library.settings", library_id=library.id))


@library_bp.route("/<int:library_id>/members/<int:member_id>/remove", methods=["POST"])
@login_required
def remove_member(library_id, member_id):
    library, membership = get_library_or_403(library_id)
    owner_required(membership)
    target = LibraryMember.query.get_or_404(member_id)
    if target.library_id != library.id:
        abort(404)
    if target.role == "owner":
        flash("Nie można usunąć właściciela biblioteki.", "danger")
    else:
        db.session.delete(target)
        db.session.commit()
        flash("Usunięto członka z biblioteki.", "success")
    return redirect(url_for("library.settings", library_id=library.id))


@library_bp.route("/<int:library_id>/delete", methods=["POST"])
@login_required
def delete(library_id):
    library, membership = get_library_or_403(library_id)
    owner_required(membership)
    db.session.delete(library)
    db.session.commit()
    flash("Usunięto bibliotekę.", "info")
    return redirect(url_for("main.dashboard"))
