import os
import uuid

from flask import current_app, abort
from flask_login import current_user

from .models import LibraryMember, Library


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_photo(file_storage, subfolder):
    """Zapisuje przesłane zdjęcie na dysku i zwraca względną ścieżkę, albo None."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return f"{subfolder}/{filename}"


def get_library_or_403(library_id):
    """Zwraca (library, membership) jeśli current_user należy do biblioteki, inaczej 403/404."""
    library = Library.query.get_or_404(library_id)
    membership = LibraryMember.query.filter_by(
        library_id=library.id, user_id=current_user.id
    ).first()
    if not membership:
        abort(403)
    return library, membership


def owner_required(membership):
    if membership.role != "owner":
        abort(403)
