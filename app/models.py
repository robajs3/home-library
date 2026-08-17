import random
import string
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db


def generate_join_code(length=8):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    memberships = db.relationship(
        "LibraryMember", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Library(db.Model):
    __tablename__ = "libraries"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    join_code = db.Column(
        db.String(16), unique=True, nullable=False, default=generate_join_code
    )
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User")
    members = db.relationship(
        "LibraryMember", back_populates="library", cascade="all, delete-orphan"
    )
    locations = db.relationship(
        "Location", back_populates="library", cascade="all, delete-orphan"
    )
    books = db.relationship(
        "Book", back_populates="library", cascade="all, delete-orphan"
    )


class LibraryMember(db.Model):
    __tablename__ = "library_members"

    id = db.Column(db.Integer, primary_key=True)
    library_id = db.Column(db.Integer, db.ForeignKey("libraries.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(20), default="member")  # owner | member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    library = db.relationship("Library", back_populates="members")
    user = db.relationship("User", back_populates="memberships")

    __table_args__ = (
        db.UniqueConstraint("library_id", "user_id", name="uq_library_user"),
    )


class Location(db.Model):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    library_id = db.Column(db.Integer, db.ForeignKey("libraries.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    library = db.relationship("Library", back_populates="locations")
    cabinets = db.relationship(
        "Cabinet", back_populates="location", cascade="all, delete-orphan"
    )


class Cabinet(db.Model):
    __tablename__ = "cabinets"

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    photo_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    location = db.relationship("Location", back_populates="cabinets")
    shelves = db.relationship(
        "Shelf",
        back_populates="cabinet",
        cascade="all, delete-orphan",
        order_by="Shelf.name",
    )

    @property
    def books(self):
        """Wszystkie książki w tej szafce, niezależnie na której półce leżą."""
        result = []
        for shelf in self.shelves:
            result.extend(shelf.books)
        return result


class Shelf(db.Model):
    __tablename__ = "shelves"

    id = db.Column(db.Integer, primary_key=True)
    cabinet_id = db.Column(db.Integer, db.ForeignKey("cabinets.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cabinet = db.relationship("Cabinet", back_populates="shelves")
    books = db.relationship(
        "Book",
        back_populates="shelf",
        foreign_keys="Book.shelf_id",
        cascade="all, delete-orphan",
    )


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    library_id = db.Column(db.Integer, db.ForeignKey("libraries.id"), nullable=False)
    shelf_id = db.Column(db.Integer, db.ForeignKey("shelves.id"), nullable=True)
    last_shelf_id = db.Column(db.Integer, db.ForeignKey("shelves.id"), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255))
    genre = db.Column(db.String(120))
    year = db.Column(db.Integer)
    cover_color = db.Column(db.String(30))
    photo_filename = db.Column(db.String(255))
    is_removed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    library = db.relationship("Library", back_populates="books")
    shelf = db.relationship("Shelf", back_populates="books", foreign_keys=[shelf_id])
    last_shelf = db.relationship("Shelf", foreign_keys=[last_shelf_id])

    # Wygodne, tylko-do-odczytu skróty do szafki (przez półkę) - dzięki nim
    # stare miejsca w kodzie/szablonach odwołujące się do "cabinet"/"cabinet_id"
    # nadal działają bez zmian, mimo że fizycznie książka jest przypisana
    # teraz do półki, nie bezpośrednio do szafki.
    @property
    def cabinet(self):
        return self.shelf.cabinet if self.shelf else None

    @property
    def cabinet_id(self):
        return self.shelf.cabinet_id if self.shelf else None

    @property
    def last_cabinet(self):
        return self.last_shelf.cabinet if self.last_shelf else None

    @property
    def last_cabinet_id(self):
        return self.last_shelf.cabinet_id if self.last_shelf else None
