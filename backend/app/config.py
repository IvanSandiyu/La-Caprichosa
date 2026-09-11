from datetime import date
import os
from pathlib import Path

# --- carga mínima de .env (sin dependencias extra) ---
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
if _ENV_FILE.is_file():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

# Base de datos relativa a la carpeta backend/
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "futbol_argentino.db"

GAME_NAME = "La Caprichosa"
TODAY = date.today

# Clubes que no deben aparecer en ningún juego. "Estudiantes de BA" es un club
# distinto de "Estudiantes de La Plata" y solo confunde: queda excluido de
# grillas, categorías y compañeros de Link.
EXCLUDED_CLUBS: set[int] = {14602}

# Última temporada mínima para que un jugador entre en el pool de Conexiones.
# Filtra a jugadores con trayectoria reciente (con fotos modernas de TM).
MIN_SEASON = 2018

# --- Turso (feedback remoto) ---
TURSO_URL: str | None = os.environ.get("TURSO_URL")
TURSO_TOKEN: str | None = os.environ.get("TURSO_TOKEN")
