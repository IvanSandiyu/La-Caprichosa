"""Pipeline de datos para La Caprichosa.

Descarga transfermarkt-datasets (CC0), filtra jugadores con paso por la
Primera División de Argentina y arma una base SQLite liviana que usa el backend.

Uso:
    python pipeline/build_dataset.py [--skip-download]
"""

import argparse
import gzip
import io
import json
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.text import normalize  # noqa: E402

DATASET_URL = (
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.zip"
)
DB_PATH = BACKEND_DIR / "data" / "futbol_argentino.db"
ENRICHMENT_PATH = Path(__file__).resolve().parent / "enrichment.json"

# Competencia de primera división argentina en Transfermarkt.
ARG_COMPETITION = "ARG1"

TEMP_DIR = Path(tempfile.gettempdir()) / "la-caprichosa"
ZIP_PATH = TEMP_DIR / "transfermarkt-datasets.zip"


def download_dataset() -> None:
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 100 * 1024 * 1024:
        print(f"Usando descarga previa: {ZIP_PATH}")
        return
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Descargando dataset (~218 MB) desde {DATASET_URL} ...")
    with requests.get(DATASET_URL, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        done = 0
        with open(ZIP_PATH, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                fh.write(chunk)
                done += len(chunk)
                if total:
                    pct = done / total * 100
                    print(f"\r  {done / (1024*1024):.0f} / {total / (1024*1024):.0f} MB ({pct:.0f}%)", end="")
    print("\nDescarga completa.")


def extract_csv(archive: zipfile.ZipFile, basename: str) -> pd.DataFrame:
    matches = [
        n
        for n in archive.namelist()
        if Path(n).name.lower() in (basename, basename + ".gz")
    ]
    if not matches:
        raise FileNotFoundError(f"No se encontró {basename} dentro del zip")
    name = sorted(matches)[0]
    print(f"  leyendo {name} ...")
    raw = archive.read(name)
    if name.lower().endswith(".gz"):
        raw = gzip.decompress(raw)
    return pd.read_csv(io.BytesIO(raw), low_memory=False)


PREFIXES = (
    "Asociación de Fomento Deportivo ",
    "Asociación Atlética ",
    "Asociación Mutual Social y Deportiva ",
    "Club Atlético ",
    "Club Deportivo ",
    "Club Social y Deportivo ",
    "Centro Juventud ",
    "Asociación Civil ",
    "Asociación ",
    "Club ",
    "CD ",
)


def prettify_club(name: str) -> str:
    name = str(name).strip()
    changed = True
    while changed:
        changed = False
        for prefix in PREFIXES:
            if name.startswith(prefix):
                name = name[len(prefix):]
                changed = True
    if " (" in name:
        name = name.split(" (")[0]
    return name.strip()


# Etiquetas legibles para los nombres crudos de Transfermarkt.
CLUB_OVERRIDES = {
    "CA San Martín": "San Martín (SJ)",
    "Central Córdoba": "Central Córdoba (SE)",
    "Estudiantes": "Estudiantes de BA",
    "Godoy Cruz Antonio Tomba": "Godoy Cruz",
    "Independiente de Avellaneda": "Independiente",
    "Instituto Atlético Central Córdoba": "Instituto (CBA)",
    "Newell’s Old Boys": "Newell's Old Boys",
    "Racing Club Asociación Civil de Avellaneda": "Racing Club",
    "Riestra Barrio Colón": "Deportivo Riestra",
    "San Lorenzo de Almagro": "San Lorenzo",
    "Sarmiento": "Sarmiento (Junín)",
    "Sportivo Independiente Rivadavia": "Indep. Rivadavia",
    "Tucumán": "Atlético Tucumán",
    "Unión": "Unión (SF)",
    "de Gimnasia y Esgrima La Plata": "Gimnasia (LP)",
}


def merge_enrichment(cur: sqlite3.Cursor, club_names: dict[int, str]) -> int:
    """Inserta jugadores curados de enrichment.json con IDs sintéticos negativos."""
    if not ENRICHMENT_PATH.exists():
        return 0
    data = json.loads(ENRICHMENT_PATH.read_text(encoding="utf-8"))
    entries = [e for e in data.get("players", []) if e.get("name")]

    by_display = {name: cid for cid, name in club_names.items()}
    by_norm = {normalize(name): cid for cid, name in club_names.items()}

    added = 0
    for idx, entry in enumerate(entries):
        cur.execute("SELECT player_id FROM players WHERE norm = ?", (normalize(entry["name"]),))
        if cur.fetchone():
            continue
        pid = -(idx + 1)
        cur.execute(
            "INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                pid,
                entry["name"],
                normalize(entry["name"]),
                entry.get("position"),
                entry.get("dob"),
                entry.get("citizenship"),
                entry.get("image_url"),
            ),
        )
        if entry.get("citizenship"):
            c = str(entry["citizenship"])
            cur.execute(
                "INSERT OR IGNORE INTO player_countries VALUES (?, ?, ?)",
                (pid, c, normalize(c)),
            )
        missing = []
        for club in entry.get("clubs", []):
            cid = by_display.get(club) or by_norm.get(normalize(club))
            if cid is None:
                missing.append(club)
                continue
            cur.execute("INSERT OR IGNORE INTO player_clubs VALUES (?, ?)", (pid, cid))
        if missing:
            print(f"  [enrichment] {entry['name']}: clubes no encontrados: {missing}")
        added += 1
        print(f"  [enrichment] +{entry['name']} ({len(entry.get('clubs', [])) - len(missing)} clubes)")
    return added


def build_db(players, transfers, clubs, games, appearances) -> None:
    current_arg = set(
        clubs.loc[
            clubs["domestic_competition_id"] == ARG_COMPETITION, "club_id"
        ].astype(int)
    )
    hist_arg = games.loc[games["competition_id"] == ARG_COMPETITION]
    hist_ids = set(hist_arg["home_club_id"].dropna().astype(int)) | set(
        hist_arg["away_club_id"].dropna().astype(int)
    )
    arg_club_ids = current_arg | hist_ids
    print(f"Clubes con paso por Primera División Argentina: {len(arg_club_ids)}")

    # --- fuente 1: transferencias hacia/desde clubes argentinos ---
    t = transfers[["player_id", "from_club_id", "to_club_id"]].dropna()
    t["from_club_id"] = t["from_club_id"].astype(int)
    t["to_club_id"] = t["to_club_id"].astype(int)

    from_arg = t[t["from_club_id"].isin(arg_club_ids)][["player_id", "from_club_id"]]
    to_arg = t[t["to_club_id"].isin(arg_club_ids)][["player_id", "to_club_id"]]
    from_arg.columns = ["player_id", "club_id"]
    to_arg.columns = ["player_id", "club_id"]
    rel = pd.concat([from_arg, to_arg]).drop_duplicates()

    # --- fuente 2: partidos efectivamente jugados en cualquier competencia ---
    # por un club argentino (incluye copas e internacionales de clubes AR)
    a = appearances[["player_id", "player_club_id"]].dropna()
    a["player_club_id"] = a["player_club_id"].astype(int)
    app_arg = a[a["player_club_id"].isin(arg_club_ids)].drop_duplicates()
    app_arg.columns = ["player_id", "club_id"]
    print(f"  jugadores con minutos en clubes AR (appearances): {len(app_arg)}")
    rel = pd.concat([rel, app_arg]).drop_duplicates()

    # --- fuente 3: plantillas actuales de Primera (cantera incluida) ---
    if "current_club_domestic_competition_id" in players.columns:
        cur = players.loc[
            players["current_club_domestic_competition_id"] == ARG_COMPETITION,
            ["player_id", "current_club_id"],
        ].dropna()
        cur["player_id"] = cur["player_id"].astype(int)
        cur["current_club_id"] = cur["current_club_id"].astype(int)
        cur = cur[cur["current_club_id"].isin(arg_club_ids)]
        cur.columns = ["player_id", "club_id"]
        print(f"  jugadores en plantillas actuales de Primera: {len(cur)}")
        rel = pd.concat([rel, cur]).drop_duplicates()

    rel = rel.drop_duplicates()

    p = players[
        [
            "player_id",
            "name",
            "position",
            "date_of_birth",
            "country_of_citizenship",
            "image_url",
            "current_national_team_name" if "current_national_team_name" in players.columns else "current_national_team_id",
        ]
    ].copy()
    nat_col = p.columns[-1]
    p = p.rename(columns={nat_col: "national_team"})
    p["player_id"] = p["player_id"].astype(int)

    pool_ids = set(rel["player_id"].unique())
    p = p[p["player_id"].isin(pool_ids)].copy()
    p["name"] = p["name"].fillna("").str.strip()
    p = p[p["name"] != ""].copy()

    kept = set(p["player_id"])
    rel = rel[rel["player_id"].isin(kept)]

    countries = pd.concat(
        [
            p[["player_id"]].assign(country=p["country_of_citizenship"]),
            p.loc[p["national_team"].notna(), ["player_id"]].assign(country=p.loc[p["national_team"].notna(), "national_team"]),
        ],
        ignore_index=True,
    ).dropna()
    countries = countries.drop_duplicates()

    used_club_ids = sorted(set(rel["club_id"]))
    club_names_raw = clubs.set_index("club_id")["name"].to_dict()
    club_names = {}
    for cid in used_club_ids:
        raw = club_names_raw.get(cid)
        if raw is None:
            continue
        clean = prettify_club(raw)
        club_names[int(cid)] = CLUB_OVERRIDES.get(clean, clean)
    print(f"Jugadores en el pool (pasaron por fútbol argentino): {len(p)}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            norm TEXT NOT NULL,
            position TEXT,
            dob TEXT,
            citizenship TEXT,
            image_url TEXT
        );
        CREATE TABLE clubs (
            club_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            norm TEXT NOT NULL
        );
        CREATE TABLE player_clubs (
            player_id INTEGER NOT NULL REFERENCES players(player_id),
            club_id INTEGER NOT NULL REFERENCES clubs(club_id),
            PRIMARY KEY (player_id, club_id)
        );
        CREATE TABLE player_countries (
            player_id INTEGER NOT NULL REFERENCES players(player_id),
            country TEXT NOT NULL,
            norm TEXT NOT NULL,
            PRIMARY KEY (player_id, norm)
        );
        CREATE INDEX idx_players_norm ON players(norm);
        CREATE INDEX idx_player_clubs_club ON player_clubs(club_id);
        CREATE INDEX idx_player_countries_norm ON player_countries(norm);
        """
    )

    cur.executemany(
        "INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                int(r.player_id),
                r.name,
                normalize(str(r.name)),
                getattr(r, "position", None),
                getattr(r, "date_of_birth", None),
                getattr(r, "country_of_citizenship", None),
                getattr(r, "image_url", None),
            )
            for r in p.itertuples(index=False)
        ],
    )
    cur.executemany(
        "INSERT OR IGNORE INTO clubs VALUES (?, ?, ?)",
        [(cid, club_names.get(cid, f"Club {cid}"), normalize(club_names.get(cid, str(cid)))) for cid in used_club_ids],
    )
    cur.executemany(
        "INSERT OR IGNORE INTO player_clubs VALUES (?, ?)",
        [(int(r.player_id), int(r.club_id)) for r in rel.itertuples(index=False)],
    )
    cur.executemany(
        "INSERT OR IGNORE INTO player_countries VALUES (?, ?, ?)",
        [(int(r.player_id), str(r.country), normalize(str(r.country))) for r in countries.itertuples(index=False)],
    )

    # --- enriquecimiento curado (jugadores ausentes en el dataset) ---
    added = merge_enrichment(cur, club_names)

    # --- historia pre-2010 vía Wikidata (P54 con salida < 2012) ---
    try:
        from pipeline.wikidata_history import insert_history

        n_hist = insert_history(conn)
        print(f"  [historia] jugadores históricos agregados: {n_hist}")
    except Exception as exc:
        print(f"  [historia] omitido: {exc}")

    # --- imágenes faltantes vía Wikidata/Wikipedia (solo TM + curados) ---
    try:
        from pipeline.enrich_wikidata import fill_missing

        fill_missing(conn)
    except Exception as exc:
        print(f"  [wikidata] omitido: {exc}")
    conn.commit()

    stats = {
        "jugadores": cur.execute("SELECT COUNT(*) FROM players").fetchone()[0],
        "clubes": cur.execute("SELECT COUNT(*) FROM clubs").fetchone()[0],
        "paises": cur.execute("SELECT COUNT(DISTINCT norm) FROM player_countries").fetchone()[0],
    }
    conn.close()
    print(f"Base generada en {DB_PATH}: {stats}")

    top = pd.read_sql(
        """
        SELECT c.name AS etiqueta, 'club' AS tipo, COUNT(DISTINCT pc.player_id) AS jugadores
        FROM clubs c JOIN player_clubs pc ON pc.club_id = c.club_id GROUP BY c.club_id
        UNION ALL
        SELECT country, 'selección', COUNT(DISTINCT player_id)
        FROM player_countries GROUP BY norm ORDER BY jugadores DESC LIMIT 15
        """,
        conn2 := sqlite3.connect(DB_PATH),
    )
    print("\nTop etiquetas por pool de jugadores:")
    print(top.to_string(index=False))
    conn2.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    if not args.skip_download:
        download_dataset()
    elif not ZIP_PATH.exists():
        sys.exit("No existe descarga previa; corré sin --skip-download")

    with zipfile.ZipFile(ZIP_PATH) as archive:
        print("Extrayendo tablas necesarias...")
        players = extract_csv(archive, "players.csv")
        transfers = extract_csv(archive, "transfers.csv")
        clubs = extract_csv(archive, "clubs.csv")
        games = extract_csv(archive, "games.csv")
        appearances = extract_csv(archive, "appearances.csv")

    required = [
        (players, ["player_id", "name"]),
        (transfers, ["player_id", "from_club_id", "to_club_id"]),
        (clubs, ["club_id", "name", "domestic_competition_id"]),
        (games, ["competition_id", "home_club_id", "away_club_id"]),
        (appearances, ["player_id", "player_club_id"]),
    ]
    for df, cols in required:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            sys.exit(f"Faltan columnas {missing}; columnas disponibles: {list(df.columns)}")

    build_db(players, transfers, clubs, games, appearances)


if __name__ == "__main__":
    main()
