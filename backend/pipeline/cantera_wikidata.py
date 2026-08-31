"""Completa datos de cantera/inferiores desde Wikipedia.

Para cada jugador de la base, busca su artículo en la Wikipedia en español
y extrae las categorías del tipo "Futbolistas de las inferiores de <club>".
Esa categoría indica en qué club(es) se formó el jugador (divisiones juveniles).

Guarda el resultado en una tabla nueva `player_youth (player_id, club_id)`.

Uso:
    python pipeline/cantera_wikidata.py
(build_dataset.py no lo llama automáticamente; se corre aparte por ser lento)
"""

import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.text import normalize  # noqa: E402

DB_PATH = BACKEND_DIR / "data" / "futbol_argentino.db"
CACHE_PATH = Path(__file__).resolve().parent / "wikidata_cantera.json"
WIKI_API = "https://es.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "LaCaprichosa/1.0 (trivia game; local use)",
    "Accept-Encoding": "gzip",
}

BATCH = 50
# "del Club" = "de el Club" -> la preposicion "de" se fusiona con "el".
# El grupo capturado es el nombre legal del club (con artículos "el/la/..."),
# que luego limpia clean_club_name().
MATCH_RE = re.compile(
    r"^Categoría:Futbolistas de las inferiores de(?:l | la | los | las | el | al )?(.*)$",
    re.IGNORECASE,
)

# prefijos de nombres legales de clubes, ordenados (artículo primero).
PREFIXES = (
    # artículos + nombres de personas jurídicas
    "el ", "la ", "los ", "las ", "del ", "de la ", "de los ", "de las ", "al ",
    "Asociación de Fomento Deportivo ", "Asociación Atlética ",
    "Asociación Mutual Social y Deportiva ", "Asociación del Fútbol Argentino ",
    "Club Atlético ", "Club Deportivo ", "Club Social y Deportivo ",
    "Centro Juventud ", "Asociación Civil ", "Asociación ", "Club ",
    "Club y Biblioteca ", "Instituto ", "Deportivo ",
    "CD ", "CA ", "de ",
)


def clean_club_name(cat_name: str) -> str:
    """De 'el Club Atlético Boca Juniors' -> 'Boca Juniors'."""
    name = cat_name.strip()
    changed = True
    while changed:
        changed = False
        for p in PREFIXES:
            if name.lower().startswith(p.lower()):
                name = name[len(p):].strip()
                changed = True
                break
    # quitar paréntesis final "(club)"
    return re.sub(r"\s*\(.*?\)\s*$", "", name).strip()


def build_club_index(conn) -> tuple[dict, dict]:
    idx_norm = {}
    idx_sub = {}
    for cid, name, _norm in conn.execute("SELECT club_id, name, norm FROM clubs"):
        idx_norm[normalize(name)] = cid
        # substrings útiles para desambiguar
        idx_sub.setdefault(normalize(name), cid)
    return idx_norm, idx_sub


# Alias manuales para nombres legales que no casan con los nombres cortos de la base.
CLUB_ALIASES = {
    "gimnasia y esgrima la plata": 1106,  # Gimnasia (LP)
    "gimnasia lp": 1106,
    "talleres de cordoba": 3938,
    "talleres cordoba": 3938,
}


def resolve_club(idx_norm, cleaned: str):
    nc = normalize(cleaned)
    if not nc:
        return None
    if nc in idx_norm:
        return idx_norm[nc]
    if nc in CLUB_ALIASES:
        return CLUB_ALIASES[nc]
    # coincidencia por contenido (ignora prefijos que ya se quitaron)
    for key, cid in idx_norm.items():
        if nc in key or key in nc:
            return cid
    return None


def api_get(params, retries=6):
    for i in range(retries):
        try:
            r = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                time.sleep(min(6 * (i + 1), 40))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))
    return {}


def categories_for_titles(titles: list[str]) -> tuple[dict, dict]:
    """Devuelve (categorias_por_titulo, mapa_entrada->salida)."""
    params = {
        "action": "query",
        "prop": "categories",
        "titles": "|".join(titles),
        "cllimit": "max",
        "clshow": "!hidden",
        "redirects": "1",
        "format": "json",
    }
    data = api_get(params)
    q = data.get("query", {})
    pages = q.get("pages", {})
    # construir mapa del nombre que mandamos -> título resuelto
    mapping = {}
    for pair in q.get("normalized", []):
        mapping[pair["from"]] = pair["to"]
    for pair in q.get("redirects", []):
        mapping[pair["from"]] = pair["to"]
    # si no hubo redirect/normalize, entrada == título
    for title in titles:
        mapping.setdefault(title, title)
    out = {}
    for page in pages.values():
        title = page.get("title")
        if title is None:
            continue
        cats = [c["title"] for c in page.get("categories", [])]
        out[title] = cats
    return out, mapping


def fetch_cantera(conn) -> tuple[int, int]:
    """Devuelve (con_cantera, sin_resultado)."""
    players = conn.execute(
        "SELECT player_id, name FROM players "
        "WHERE image_url IS NOT NULL AND image_url != '' "
        "  AND image_url NOT LIKE '%default.jpg%'"
    ).fetchall()

    cache = (
        json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if CACHE_PATH.exists()
        else {}
    )

    idx_norm, _ = build_club_index(conn)

    # 1) títulos que todavía no consultamos
    names = [p[1] for p in players]
    todo_names = [n for n in names if n not in cache]

    print(f"Jugadores con foto: {len(players)} · ya consultados: {len(players) - len(todo_names)} · por consultar: {len(todo_names)}")

    # 2) agrupar títulos exactos en lotes
    for i in range(0, len(todo_names), BATCH):
        batch = todo_names[i:i + BATCH]
        try:
            res, mapping = categories_for_titles(batch)
        except requests.RequestException as exc:
            print(f"  [cantera] error de red en lote {i}: {exc}; guardo y sigo")
            break
        # cachear bajo el NOMBRE que mandamos (mapping entrada->título resuelto)
        for input_name in batch:
            resolved = mapping.get(input_name, input_name)
            cache[input_name] = res.get(resolved, [])
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        if (i // BATCH) % 5 == 0:
            print(f"  {i + len(batch)}/{len(todo_names)} consultados")
        time.sleep(0.4)

    # 3) resolver: para cada jugador, su nombre ya está cacheado
    inserted = 0
    unmatched_player = 0
    no_article = 0
    for pid, name in players:
        cats = cache.get(name)
        if cats is None:
            unmatched_player += 1
            continue
        if not cats:
            no_article += 1
            continue
        youths = []
        for c in cats:
            m = MATCH_RE.match(c)
            if m:
                cd = clean_club_name(m.group(1))
                cid = resolve_club(idx_norm, cd)
                if cid is not None:
                    youths.append(cid)
        for cid in set(youths):
            conn.execute(
                "INSERT OR IGNORE INTO player_youth (player_id, club_id) VALUES (?, ?)",
                (pid, cid),
            )
            inserted += 1

    conn.commit()
    return inserted, unmatched_player, no_article


def main():
    if not DB_PATH.exists():
        sys.exit(f"No existe {DB_PATH}; corré primero pipeline/build_dataset.py")
    conn = sqlite3.connect(DB_PATH)
    # crear tabla si no existe
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS player_youth (
            player_id INTEGER NOT NULL REFERENCES players(player_id),
            club_id INTEGER NOT NULL REFERENCES clubs(club_id),
            PRIMARY KEY (player_id, club_id)
        );
        CREATE INDEX IF NOT EXISTS idx_player_youth_club ON player_youth(club_id);
        """
    )
    try:
        inserted, unmatched, no_article = fetch_cantera(conn)
        print(f"Relaciones cantera insertadas: {inserted}; jugadores sin artículo: {unmatched}; sin categorías de inferiores: {no_article}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
