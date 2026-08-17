from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required

from ..extensions import db
from ..models import Book, Shelf
from ..utils import get_library_or_403, save_photo

book_bp = Blueprint("book", __name__, url_prefix="/book")


@book_bp.route("/shelf/<int:shelf_id>/create", methods=["POST"])
@login_required
def create(shelf_id):
    shelf = Shelf.query.get_or_404(shelf_id)
    library, membership = get_library_or_403(shelf.cabinet.location.library_id)

    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    genre = request.form.get("genre", "").strip()
    year = request.form.get("year", "").strip()
    color = request.form.get("cover_color", "").strip()

    if not title:
        flash("Podaj tytuł książki.", "danger")
        return redirect(url_for("shelf.view", shelf_id=shelf.id))

    photo = save_photo(request.files.get("photo"), "books")
    book = Book(
        library_id=library.id,
        shelf_id=shelf.id,
        last_shelf_id=shelf.id,
        title=title,
        author=author or None,
        genre=genre or None,
        year=int(year) if year.isdigit() else None,
        cover_color=color or None,
        photo_filename=photo,
    )
    db.session.add(book)
    db.session.commit()
    flash(f"Dodano książkę „{title}”.", "success")
    return redirect(url_for("shelf.view", shelf_id=shelf.id))


@book_bp.route("/<int:book_id>")
@login_required
def view(book_id):
    book = Book.query.get_or_404(book_id)
    library, membership = get_library_or_403(book.library_id)
    return render_template(
        "book/view.html", library=library, membership=membership, book=book
    )


@book_bp.route("/<int:book_id>/edit", methods=["POST"])
@login_required
def edit(book_id):
    book = Book.query.get_or_404(book_id)
    library, membership = get_library_or_403(book.library_id)

    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    genre = request.form.get("genre", "").strip()
    year = request.form.get("year", "").strip()
    color = request.form.get("cover_color", "").strip()

    if title:
        book.title = title
    book.author = author or None
    book.genre = genre or None
    book.year = int(year) if year.isdigit() else None
    book.cover_color = color or None
    db.session.commit()
    flash("Zaktualizowano dane książki.", "success")
    return redirect(url_for("book.view", book_id=book.id))


@book_bp.route("/<int:book_id>/photo", methods=["POST"])
@login_required
def upload_photo(book_id):
    book = Book.query.get_or_404(book_id)
    library, membership = get_library_or_403(book.library_id)
    photo = save_photo(request.files.get("photo"), "books")
    if photo:
        book.photo_filename = photo
        db.session.commit()
        flash("Zaktualizowano zdjęcie książki.", "success")
    else:
        flash("Nie udało się dodać zdjęcia (dozwolone: png, jpg, jpeg, gif, webp).", "danger")
    return redirect(url_for("book.view", book_id=book.id))


@book_bp.route("/<int:book_id>/take-out", methods=["POST"])
@login_required
def take_out(book_id):
    book = Book.query.get_or_404(book_id)
    library, membership = get_library_or_403(book.library_id)

    if book.is_removed:
        flash("Ta książka jest już wyjęta.", "info")
    else:
        book.last_shelf_id = book.shelf_id
        book.shelf_id = None
        book.is_removed = True
        db.session.commit()
        flash(f"Wyjęto książkę „{book.title}”.", "success")

    return redirect(url_for("book.view", book_id=book.id))


@book_bp.route("/<int:book_id>/put-back", methods=["POST"])
@login_required
def put_back(book_id):
    book = Book.query.get_or_404(book_id)
    library, membership = get_library_or_403(book.library_id)

    if not book.is_removed:
        flash("Ta książka nie jest wyjęta.", "info")
    elif not book.last_shelf_id:
        flash("Brak zapisanego ostatniego miejsca — użyj opcji „Przełóż do”.", "warning")
    else:
        book.shelf_id = book.last_shelf_id
        book.is_removed = False
        db.session.commit()
        flash(f"Odłożono książkę „{book.title}” na miejsce.", "success")

    return redirect(url_for("book.view", book_id=book.id))


@book_bp.route("/<int:book_id>/move", methods=["POST"])
@login_required
def move(book_id):
    book = Book.query.get_or_404(book_id)
    library, membership = get_library_or_403(book.library_id)

    shelf_id = request.form.get("shelf_id", type=int)
    shelf = Shelf.query.get(shelf_id) if shelf_id else None

    if not shelf or shelf.cabinet.location.library_id != library.id:
        flash("Wybierz prawidłową półkę.", "danger")
    else:
        book.shelf_id = shelf.id
        book.last_shelf_id = shelf.id
        book.is_removed = False
        db.session.commit()
        flash(
            f"Przełożono książkę „{book.title}” do „{shelf.cabinet.name} → {shelf.name}”.",
            "success",
        )

    return redirect(url_for("book.view", book_id=book.id))


@book_bp.route("/<int:book_id>/delete", methods=["POST"])
@login_required
def delete(book_id):
    book = Book.query.get_or_404(book_id)
    library, membership = get_library_or_403(book.library_id)
    library_id = library.id
    db.session.delete(book)
    db.session.commit()
    flash("Usunięto książkę.", "info")
    return redirect(url_for("library.home", library_id=library_id))
