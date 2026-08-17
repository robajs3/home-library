import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    # Jak długo trzyma ciasteczko "zapamiętaj mnie" po zaznaczeniu opcji przy logowaniu.
    REMEMBER_COOKIE_DURATION = timedelta(
        days=int(os.environ.get("REMEMBER_COOKIE_DAYS", "30"))
    )
    REMEMBER_COOKIE_HTTPONLY = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://homelibrary:homelibrary@db:5432/homelibrary",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/app/uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    # Prefiks, pod jakim appka jest widoczna z zewnątrz (czyli w przeglądarce),
    # np. "/homelibrary". Ustaw go zawsze wtedy, gdy appka dzieli host/port
    # z inną usługą pod konkretną ścieżką - niezależnie od tego, czy proxy przed
    # nią ucina ten prefiks (jak `tailscale serve --set-path=/homelibrary`) czy
    # nie (np. zwykły `nginx proxy_pass` bez rewrite) - middleware w app/__init__.py
    # sam wykrywa który przypadek zachodzi. Zostaw puste tylko gdy appka ma
    # własny, dedykowany port/subdomenę i odpowiada wprost pod "/".
    APP_PREFIX = os.environ.get("APP_PREFIX", "")
