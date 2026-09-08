"""Refresh del historial de equipos desde el dataset local de Transfermarkt.

Reconstruye/actualiza:
  1. player_clubs  -> todos los clubes en los que cada jugador jugó o fue
                      transferido (matches + transfers), para los 4834
                      jugadores de la DB.
  2. player_career -> filas 'temporada limpia' (un solo año) para el Statdle:
                      section='Primera División', una fila por (jugador,
                      temporada, club), con pj y goles reales de los partidos
                      ARG1 del dataset (appearances + games).

Todo offline desde transfermarkt-datasets.zip. Idempotente (INSERT OR IGNORE),
no borra nada existente. Uso: python pipeline/refresh_career.py
"""

import gzip
import io
import sqlite3
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

DB_PATH = BACKEND_DIR / "data" / "futbol_argentino.db"
ZIP_PATH = Path(tempfile.gettempdir()) / "la-caprichosa" / "transfermarkt-datasets.zip"


def extract(zf: zipfile.ZipFile, basename: str) -> pd.DataFrame:
    matches = [
        n for n in zf.namelist() if Path(n).name.lower() in (basename, basename + ".gz")
    ]
    name = sorted(matches)[0]
    raw = zf.read(name)
    if name.lower().endswith(".gz"):
        raw = gzip.decompress(raw)
    return pd.read_csv(io.BytesIO(raw), low_memory=False)


def main() -> None:
    if not ZIP_PATH.exists():
        sys.exit(f"No existe {ZIP_PATH}; corré python pipeline/build_dataset.py")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    db_ids = set(r[0] for r in cur.execute("SELECT player_id FROM players"))
    db_club_ids = set(r[0] for r in cur.execute("SELECT club_id FROM clubs"))

    print("Leyendo dataset local de Transfermarkt ...")
    with zipfile.ZipFile(ZIP_PATH) as zf:
        players = extract(zf, "players.csv")
        transfers = extract(zf, "transfers.csv")
        games = extract(zf, "games.csv")
        appearances = extract(zf, "appearances.csv")
        clubs_csv = extract(zf, "clubs.csv")

    # jugadores de la DB presentes en el dataset
    tm_ids = db_ids - {i for i in db_ids if i < 0}
    tm_ids = set(players["player_id"].astype("int64")) & tm_ids
    print(f"  jugadores TM activos: {len(tm_ids)}")

    # ---- 1) player_clubs: transferencias hacia/dese clubes argentinos ----
    t = transfers[["player_id", "from_club_id", "to_club_id"]].dropna()
    t["player_id"] = t["player_id"].astype("int64")
    t["from_club_id"] = t["from_club_id"].astype("int64")
    t["to_club_id"] = t["to_club_id"].astype("int64")
    frames = []
    for col in ("from_club_id", "to_club_id"):
        sub = t[t[col].isin(db_club_ids)][["player_id", col]].dropna()
        sub = sub[sub["player_id"].isin(tm_ids)]
        frames.append(sub.rename(columns={col: "club_id"}))
    # ---- partidos jugados por un club argentino ----
    app = appearances[["player_id", "player_club_id"]].dropna()
    app["player_id"] = app["player_id"].astype("int64")
    app["player_club_id"] = app["player_club_id"].astype("int64")
    app = app[app["player_club_id"].isin(db_club_ids)]
    app = app[app["player_id"].isin(tm_ids)]
    frames.append(app.rename(columns={"player_club_id": "club_id"}))
    clubs_set = pd.concat(frames).drop_duplicates()
    print(f"  relaciones (jugador, club) desde dataset: {len(clubs_set)}")

    before = dict(
        cur.execute("SELECT player_id, COUNT(*) FROM player_clubs GROUP BY player_id")
    )
    existing = set(cur.execute("SELECT player_id || '|' || club_id FROM player_clubs"))
    new_rows = [
        (int(r.player_id), int(r.club_id))
        for r in clubs_set.itertuples(index=False)
        if f"{int(r.player_id)}|{int(r.club_id)}" not in existing
    ]
    cur.executemany("INSERT OR IGNORE INTO player_clubs VALUES (?, ?)", new_rows)
    print(f"  player_clubs: {len(new_rows)} filas nuevas")
    updated_players = len({pid for pid, _ in new_rows})
    print(f"  jugadores con nuevo club: {updated_players}")

    # ---- 2) temporadas de Primera por jugador/club para el Statdle ----
    g = games[["game_id", "competition_id", "season"]].dropna(subset=["season"])
    g = g[g["competition_id"] == "ARG1"]
    g["game_id"] = g["game_id"].astype("int64")
    g["season"] = g["season"].astype("int64")
    a = appearances[
        ["game_id", "player_id", "player_club_id", "goals"]
    ].dropna(subset=["player_club_id"])
    a["game_id"] = a["game_id"].astype("int64")
    a["player_id"] = a["player_id"].astype("int64")
    a["player_club_id"] = a["player_club_id"].astype("int64")
    a["goals"] = a["goals"].fillna(0).astype("int64")
    m = a.merge(g, on="game_id", how="inner")
    m = m[m["player_club_id"].isin(db_club_ids)]
    m = m[m["player_id"].isin(tm_ids)]
    print(f"  apariciones ARG1 del dataset: {len(m)}")

    agg = (
        m.groupby(["player_id", "season", "player_club_id"])
        .agg(pj=("game_id", "nunique"), goals=("goals", "sum"))
        .reset_index()
    )
    club_name = {}
    for cid, cname in cur.execute("SELECT club_id, name FROM clubs"):
        club_name[cid] = cname
    max_season = int(m["season"].max()) if len(m) else None
    print(f"  temporadas ARG1 (jugador, año, club): {len(agg)}")

    career_rows = []
    for r in agg.itertuples(index=False):
        career_rows.append(
            (
                int(r.player_id),
                "Primera División",
                int(r.player_club_id),
                club_name.get(int(r.player_club_id)),
                "",
                str(int(r.season)),
                int(r.season),
                int(r.season),
                1 if max_season and int(r.season) == max_season else 0,
                int(r.pj),
                int(r.goals),
            )
        )
    n_pre = cur.execute(
        "SELECT COUNT(*) FROM player_career WHERE section='Primera División'"
    ).fetchone()[0]
    cur.executemany(
        """INSERT OR IGNORE INTO player_career
           (player_id, section, club_id, club_name, country, years,
            year_from, year_to, is_current, pj, goals)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        career_rows,
    )
    n_post = cur.execute(
        "SELECT COUNT(*) FROM player_career WHERE section='Primera División'"
    ).fetchone()[0]
    print(f"  player_career 'Primera División': {n_pre} -> {n_post} filas")

    conn.commit()
    conn.close()

    print("\n=== RESUMEN ===")
    print(f"Jugadores en DB: {len(db_ids)}")
    print(f"Jugadores TM presentes: {len(tm_ids)}")
    print(f"Nuevas relaciones jugador-club: {len(new_rows)}")
    print(f"Jugadores con al menos un club nuevo: {updated_players}")
    print(f"Filas de temporada agregadas a carrera: {len(career_rows)}")


if __name__ == "__main__":
    main()