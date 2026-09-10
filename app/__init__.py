import os
import secrets

from flask import Flask

from .config import Config
from .extensions import db, login_manager, csrf


class PrefixMiddleware:
    """
    Sprawia, że appka jest poprawnie widoczna pod prefiksem (np. "/homelibrary"),
    niezależnie od tego, czy proxy przed nią ucina ten prefiks (Tailscale
    `serve --set-path` tak robi), czy nie (np. prosty `proxy_pass` bez rewrite):

    - jeśli PATH_INFO nadal zawiera prefiks (proxy go NIE ucięło) - usuwamy go
      sami, żeby trasy Flaska (zarejestrowane od "/") mogły dopasować żądanie;
    - ustawiamy SCRIPT_NAME na prefiks, dzięki czemu Flask/Werkzeug automatycznie
      dokleja go z powrotem przy generowaniu linków (url_for), przekierowań
      (redirect) i URL-i do plików statycznych - więc przeglądarka zawsze
      dostaje poprawny, pełny adres z prefiksem.
    """

    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix.rstrip("/") if prefix else ""

    def __call__(self, environ, start_response):
        if self.prefix:
            path = environ.get("PATH_INFO", "")
            if path.startswith(self.prefix):
                environ["PATH_INFO"] = path[len(self.prefix):] or "/"
            environ["SCRIPT_NAME"] = self.prefix
        return self.app(environ, start_response)


def _create_homelibrary_user(hub_username: str):
    """Zakłada w Home Library nowe lokalne konto dla usera z LoginHub, który
    jeszcze nie miał tu żadnego konta (wywoływane przez
    sso_client.resolve_or_create_local_user przy pierwszej wizycie).
    Hasło jest losowe i nieznane nikomu — logowanie idzie wyłącznie przez SSO.

    Home Library loguje po e-mailu, a nie po username, a Hub nie zna e-maila
    usera — generujemy deterministyczny placeholder z hub_username, więc
    powtórne wywołanie (np. gdy zgłoszenie do Huba nie doszło za pierwszym
    razem) trafi na już istniejące konto zamiast tworzyć duplikat.
    """
    from .extensions import db
    from .models import User

    placeholder_email = f"{hub_username}@sso.local"
    existing = User.query.filter_by(email=placeholder_email).first()
    if existing:
        return existing.id, existing.email

    email = placeholder_email
    suffix = 1
    while User.query.filter_by(email=email).first():
        suffix += 1
        email = f"{hub_username}{suffix}@sso.local"

    user = User(name=hub_username, email=email)
    user.set_password(secrets.token_urlsafe(24))
    db.session.add(user)
    db.session.commit()
    return user.id, user.email


def create_app():
    app = Flask(__name__, static_url_path="/static")
    app.config.from_object(Config)

    # APP_PREFIX opisuje, pod jakim prefiksem appka jest widoczna z ZEWNĄTRZ
    # (czyli to, co widzi przeglądarka), NIEZALEŻNIE od tego, czy proxy przed
    # aplikacją ucina ten prefiks (jak `tailscale serve --set-path`) czy nie
    # (np. zwykły `nginx proxy_pass` bez rewrite). Middleware niżej sam wykrywa
    # który przypadek zachodzi (czy PATH_INFO nadal ma prefiks, czy już nie) -
    # trasy wewnątrz Flaska ZAWSZE są rejestrowane bez prefiksu (od "/"), a
    # SCRIPT_NAME dba o to, żeby wygenerowane linki/przekierowania (url_for,
    # redirecty, linki do plików statycznych) i tak zawierały prefiks, którego
    # oczekuje przeglądarka.
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, Config.APP_PREFIX)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Zaloguj się, aby kontynuować."
    login_manager.login_message_category = "warning"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from . import sso_client
    from flask_login import login_user, current_user

    # --- SSO (LoginHub) ---------------------------------------------------
    # Jeśli user nie jest zalogowany lokalnie, sprawdź czy ma ważne ciasteczko
    # LoginHub. Jeśli jego konto jest już połączone z home-library — zaloguj
    # go lokalnie. Jeśli NIE jest jeszcze połączone — resolve_or_create_local_user
    # samo zakłada tu dla niego nowe konto (_create_homelibrary_user) i zgłasza
    # połączenie do Huba, więc nie trzeba czekać na ręczne sparowanie kont w
    # panelu /admin Huba. Zwykłe logowanie hasłem (/auth/login) zostaje bez
    # zmian jako plan B.
    @app.before_request
    def _sso_autologin():
        if current_user.is_authenticated:
            return
        local_id = sso_client.resolve_or_create_local_user(
            app_slug="homelibrary", create_user=_create_homelibrary_user
        )
        if local_id:
            user = User.query.get(local_id)
            if user:
                login_user(user)

    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .library.routes import library_bp
    from .location.routes import location_bp
    from .cabinet.routes import cabinet_bp
    from .shelf.routes import shelf_bp
    from .book.routes import book_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(location_bp)
    app.register_blueprint(cabinet_bp)
    app.register_blueprint(shelf_bp)
    app.register_blueprint(book_bp)

    with app.app_context():
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        db.create_all()
        _migrate_shelves_and_genre()
        _ensure_owner_memberships()

    return app


def _migrate_shelves_and_genre():
    """
    Bezpieczna, idempotentna migracja "na żywo" dla instalacji, które już
    mają dane w bazie (sprzed wprowadzenia półek i gatunku).

    `db.create_all()` tworzy tylko BRAKUJĄCE tabele (np. nową `shelves`),
    ale nie dokłada nowych kolumn do już istniejących tabel - dlatego kolumny
    `genre`, `shelf_id`, `last_shelf_id` w `books` trzeba dodać ręcznie przez
    ALTER TABLE. Dla każdej szafki, która miała książki przypisane po staremu
    bezpośrednio (kolumny `cabinet_id`/`last_cabinet_id`, jeśli jeszcze
    istnieją), tworzymy domyślną półkę "Półka 1" i przenosimy na nią książki.
    Bezpieczne do uruchamiania przy każdym starcie appki - kolejne przebiegi
    nic już nie zmieniają.
    """
    from sqlalchemy import text

    if db.engine.dialect.name != "postgresql":
        # Migracja poniżej używa składni specyficznej dla Postgresa (silnik
        # produkcyjny tej appki). Inne silniki (np. sqlite używany lokalnie/w
        # testach) zawsze startują z czystym schematem z models.py, więc nic
        # tu nie trzeba dokładać.
        return

    db.session.execute(text("ALTER TABLE books ADD COLUMN IF NOT EXISTS genre VARCHAR(120)"))
    db.session.execute(text(
        "ALTER TABLE books ADD COLUMN IF NOT EXISTS shelf_id INTEGER REFERENCES shelves(id)"
    ))
    db.session.execute(text(
        "ALTER TABLE books ADD COLUMN IF NOT EXISTS last_shelf_id INTEGER REFERENCES shelves(id)"
    ))
    db.session.commit()

    has_old_cabinet_id = db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'books' AND column_name = 'cabinet_id'"
    )).first()
    if not has_old_cabinet_id:
        return  # świeża instalacja - nie ma starych danych do przeniesienia

    cabinets_needing_shelf = db.session.execute(text(
        "SELECT DISTINCT cabinet_id FROM books "
        "WHERE cabinet_id IS NOT NULL AND shelf_id IS NULL "
        "UNION "
        "SELECT DISTINCT last_cabinet_id FROM books "
        "WHERE last_cabinet_id IS NOT NULL AND last_shelf_id IS NULL"
    )).fetchall()

    for (cabinet_id,) in cabinets_needing_shelf:
        existing_shelf = db.session.execute(text(
            "SELECT id FROM shelves WHERE cabinet_id = :cid ORDER BY id LIMIT 1"
        ), {"cid": cabinet_id}).first()
        if existing_shelf:
            shelf_id = existing_shelf[0]
        else:
            inserted = db.session.execute(text(
                "INSERT INTO shelves (cabinet_id, name, created_at) "
                "VALUES (:cid, 'Półka 1', now()) RETURNING id"
            ), {"cid": cabinet_id})
            shelf_id = inserted.first()[0]

        db.session.execute(text(
            "UPDATE books SET shelf_id = :sid "
            "WHERE cabinet_id = :cid AND shelf_id IS NULL"
        ), {"sid": shelf_id, "cid": cabinet_id})
        db.session.execute(text(
            "UPDATE books SET last_shelf_id = :sid "
            "WHERE last_cabinet_id = :cid AND last_shelf_id IS NULL"
        ), {"sid": shelf_id, "cid": cabinet_id})

    db.session.commit()


def _ensure_owner_memberships():
    """Zabezpieczenie: każdy właściciel biblioteki musi mieć wpis w library_members."""
    from .models import Library, LibraryMember

    changed = False
    for library in Library.query.all():
        exists = LibraryMember.query.filter_by(
            library_id=library.id, user_id=library.owner_id
        ).first()
        if not exists:
            db.session.add(
                LibraryMember(
                    library_id=library.id, user_id=library.owner_id, role="owner"
                )
            )
            changed = True
    if changed:
        db.session.commit()
