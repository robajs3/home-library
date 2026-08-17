# Home Library

Aplikacja Flask + PostgreSQL do zarządzania domową biblioteką: biblioteki, lokalizacje,
szafki i książki, ze zdjęciami i pełnym systemem kont.

Prefiks URL jest konfigurowalny przez zmienną środowiskową `APP_PREFIX`:

- **`APP_PREFIX=` (domyślnie, puste)** — aplikacja odpowiada normalnie pod `/`
  (np. `/`, `/library/1`). Tego trybu używaj, gdy appka ma własny port/subdomenę,
  albo gdy wystawiasz ją przez reverse proxy, które **ucina** prefiks przed
  przekazaniem żądania do backendu (tak właśnie robi `tailscale serve --set-path`).
- **`APP_PREFIX=/homelibrary`** — cała aplikacja działa wyłącznie pod tym prefiksem
  (np. `/homelibrary/`, `/homelibrary/library/1`), a każde żądanie poza nim zwraca
  404. Tego trybu używaj, gdy dzielisz port z inną usługą przez proxy, które
  **nie ucina** prefiksu (np. bezpośrednie wystawienie portu bez ścieżkowania).

## Uruchomienie (Docker)

1. Skopiuj plik `.env.example` do `.env` i ustaw losowy `SECRET_KEY`:

   ```bash
   cp .env.example .env
   # edytuj .env i wpisz długi losowy ciąg jako SECRET_KEY
   ```

2. Zbuduj i uruchom kontenery:

   ```bash
   docker compose up -d --build
   ```

3. Aplikacja będzie dostępna pod: `http://localhost:8001/homelibrary/`

   Baza danych (tabele) tworzy się automatycznie przy starcie kontenera `web`
   (nie trzeba ręcznie uruchamiać migracji).

4. Zdjęcia (książek i szafek) trafiają do wolumenu `uploads_data`
   (`/app/uploads` w kontenerze) — przetrwają restart/aktualizację.

## Udostępnienie przez Tailscale

**Uwaga:** `tailscale serve --set-path=<prefiks>` **ucina** ten prefiks z URL-a
zanim żądanie trafi do backendu — appka pod spodem widzi samo `/`, nie
`/homelibrary/`. Dlatego przy takim wystawieniu zostaw `APP_PREFIX` puste
(wartość domyślna) w `.env`, a URL-owy prefiks kontroluje wyłącznie Tailscale:

```bash
# .env: APP_PREFIX= (puste, domyślnie)
sudo tailscale serve --bg --https=443 --set-path=/homelibrary http://localhost:8001
sudo tailscale funnel --bg --https=443 http://localhost:8001   # jeśli chcesz dostęp z internetu
```

Appka będzie dostępna pod `https://twoj-host.ts.net/homelibrary/`.

Jeśli zamiast tego chcesz wystawić appkę na **własnym, osobnym porcie** (bez
dzielenia ścieżki z inną usługą), również zostaw `APP_PREFIX` puste i po prostu
zamontuj ją pod rootem tego portu:

```bash
sudo tailscale funnel --bg --https=8443 http://localhost:8001
```

Ustawiaj `APP_PREFIX=/homelibrary` tylko jeśli świadomie wystawiasz port appki
bez żadnego proxy ucinającego ścieżkę (np. bezpośrednio, albo przez prosty
`nginx proxy_pass` bez `rewrite`).

## Struktura funkcjonalna

- **Konta użytkowników** — pełna rejestracja/logowanie (e-mail + hasło, hasła hashowane).
- **Biblioteki** — każdy użytkownik może utworzyć własną bibliotekę (staje się jej
  właścicielem) i/lub dołączyć do istniejącej podając **kod dołączenia** (widoczny
  i regenerowalny w ustawieniach biblioteki przez właściciela).
- **Lokalizacje** — jednostki w bibliotece (np. „Salon”, „Piwnica”), można je dodawać
  i wchodzić w ich profil.
- **Szafki** — należą do konkretnej lokalizacji, mają własny profil ze zdjęciem.
- **Książki** — należą do konkretnej szafki (czyli: biblioteka → lokalizacja → szafka →
  książka). Pola: tytuł, autor, rok wydania, kolor okładki, zdjęcie.
- **Master search** — pasek wyszukiwania na stronie głównej biblioteki, filtruje po
  tytule / autorze / kolorze okładki.
- **Wyjmij / Odłóż / Przełóż** — z profilu książki można ją „wyjąć” (trafia do kategorii
  „Wyjęte książki”), następnie **odłożyć z powrotem** na ostatnie znane miejsce, albo
  **przełożyć** do wybranej z listy szafki (działa też dla książek, które nie zostały
  wyjęte — czyli można od razu przenieść książkę w inne miejsce).

## Uruchomienie bez Dockera (dev)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://user:pass@localhost:5432/homelibrary"
export UPLOAD_FOLDER="./uploads"
export SECRET_KEY="dev"
python run.py
```

Aplikacja wystartuje na `http://localhost:8001/homelibrary/`.
