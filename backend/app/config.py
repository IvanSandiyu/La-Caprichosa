from datetime import date
from pathlib import Path

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
