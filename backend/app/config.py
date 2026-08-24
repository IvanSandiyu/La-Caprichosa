from datetime import date
from pathlib import Path

# Base de datos relativa a la carpeta backend/
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "futbol_argentino.db"

GAME_NAME = "La Caprichosa"
TODAY = date.today
