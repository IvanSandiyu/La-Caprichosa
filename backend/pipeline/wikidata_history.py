"""Historia argentina pre-2010 vía Wikidata (SPARQL, gratis y sin key).

Para cada club (QIDs en wikidata_clubs.json) consulta todos los
humanos con un statement P54 (miembro del equipo) cuya fecha de salida
(pq:P582) sea anterior a 2012 -> capta jugadores que Transfermarkt
no tiene porque su cobertura de transferencias arranca ~2010.

Resultados cacheados por club en wikidata_history.json para que los
rebuilds no reconsulten. La inserción saltea jugadores cuyo nombre
normalizado ya existe (evita duplicar a los del dataset).

IDs sintéticos: rango <= -100000 (los curados manuales usan -1..).

Uso:
    python pipeline/wikidata_history.py            # fetch + insert
    (build_dataset.py lo llama automáticamente al final del rebuild)
"""

import json
import sys
import time
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.text import normalize  # noqa: E402

DB_PATH = BACKEND_DIR / "data" / "futbol_argentino.db"
CLUBS_PATH = Path(__file__).resolve().parent / "wikidata_clubs.json"
CACHE_PATH = Path(__file__).resolve().parent / "wikidata_history.json"
EXCLUSIONS_PATH = Path(__file__).resolve().parent / "wikidata_exclusions.json"
SCRAPED_ID_FLOOR = -100000
CUTOFF = "2012-01-01T00:00:00Z"

HEADERS = {
    "User-Agent": "LaCaprichosa/1.0 (trivia game; local use)",
    "Accept": "application/sparql-results+json",
}

QUERY = """
SELECT DISTINCT ?item ?itemLabel ?dob ?ctryLabel ?posLabel ?foto WHERE {
  ?st ps:P54 wd:%(qid)s ;
      pq:P582 ?fin .
  FILTER(?fin < "%(cutoff)s"^^<http://www.w3.org/2001/XMLSchema#dateTime>)
  ?item p:P54 ?st ;
        wdt:P31 wd:Q5 .
  OPTIONAL { ?item wdt:P569 ?dob }
  OPTIONAL { ?item wdt:P27 ?ctry }
  OPTIONAL { ?item wdt:P413 ?pos }
  OPTIONAL { ?item wdt:P18 ?foto }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". }
}
"""

# orden importa: primero específico, después genéricos
POSITION_RULES: list[tuple[tuple[str, ...], str]] = [
    (("arquero", "portero", "guardameta"), "Goalkeeper"),
    (("defensor", "defensa", "carrilero", "lateral", "zaguero"), "Defender"),
    (("delantero", "extremo", "punta", "atacante", "centroforward"), "Attack"),
    (("mediocampista", "volante", "centrocampista", "medio"), "Midfield"),
]


def map_position(label: str | None) -> str | None:
    if not label:
        return None
    low = f" {label.lower()} "
    for keys, bucket in POSITION_RULES:
        if any(k in low for k in keys):
            return bucket
    return None


def sparql(qid: str) -> list[dict]:
    q = QUERY % {"qid": qid, "cutoff": CUTOFF}
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(
                "https://query.wikidata.org/sparql",
                params={"query": q},
                headers=HEADERS,
                timeout=120,
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                raise RuntimeError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json().get("results", {}).get("bindings", [])
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"WDQS falló para {qid}: {last_exc}")


def parse_rows(rows: list[dict]) -> list[dict]:
    out: dict[str, dict] = {}
    for row in rows:
        item_uri = row["item"]["value"]
        # el QID identifica inequívocamente a la persona: dos futbolistas
        # homónimos son items distintos y NO deben fusionarse
        qid = item_uri.rsplit("/", 1)[-1]
        name = (row.get("itemLabel") or {}).get("value")
        if not name or normalize(name) == "":
            continue
        image = (row.get("foto") or {}).get("value")
        out.setdefault(
            item_uri,
            {
                "qid": qid,
                "name": name,
                "dob": ((row.get("dob") or {}).get("value") or "")[:10] or None,
                "citizenship": (row.get("ctryLabel") or {}).get("value"),
                "position": map_position((row.get("posLabel") or {}).get("value")),
                "image": image,
            },
        )
    return list(out.values())


def fetch_all(force_refresh: bool = False) -> dict[str, list[dict]]:
    clubs = json.loads(CLUBS_PATH.read_text(encoding="utf-8"))
    cache = (
        {}
        if force_refresh
        else (
            json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if CACHE_PATH.exists()
            else {}
        )
    )
    dirty = False
    for club, qid in sorted(clubs.items()):
        if club in cache:
            continue
        print(f"  [historia] consultando {club} ({qid}) ...")
        try:
            cache[club] = parse_rows(sparql(qid))
        except RuntimeError as exc:
            print(f"    ERROR: {exc}")
            continue
        dirty = True
        CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        time.sleep(2)  # cortesía con WDQS
    if dirty:
        CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return cache


def insert_history(conn) -> int:
    """Inserta jugadores históricos ausentes. Devuelve cuántos agregó."""
    cache = fetch_all()
    cur = conn.cursor()

    existing_norms = {r[0] for r in conn.execute("SELECT norm FROM players")}
    club_ids_by_name: dict[str, list[int]] = {}
    for cid, name in conn.execute("SELECT club_id, name FROM clubs"):
        club_ids_by_name.setdefault(name, []).append(int(cid))
    club_ids_by_norm: dict[str, list[int]] = {}
    for cid, name in conn.execute("SELECT club_id, name FROM clubs"):
        club_ids_by_norm.setdefault(normalize(name), []).append(int(cid))

    next_id = SCRAPED_ID_FLOOR
    # si la DB ya tiene scrapeados previos, continuamos desde ahí
    min_id = conn.execute("SELECT MIN(player_id) FROM players").fetchone()[0]
    if min_id is not None and min_id < SCRAPED_ID_FLOOR:
        next_id = min_id

    added = 0
    seen: dict[str, int] = {}  # QID de Wikidata -> player_id de la sesión
    exclusions: dict[str, list[str]] = (
        json.loads(EXCLUSIONS_PATH.read_text(encoding="utf-8"))
        if EXCLUSIONS_PATH.exists()
        else {}
    )
    for club, records in sorted(cache.items()):
        cids = club_ids_by_name.get(club) or club_ids_by_norm.get(
            normalize(club), []
        )
        if not cids:
            print(f"  [historia] club sin match en DB: {club}")
            continue
        for rec in records:
            norm = normalize(rec["name"])
            # homónimo de alguien del pool TM/curado: no lo insertamos
            # (no podemos garantizar que sea la misma persona)
            if norm in existing_norms:
                continue
            qid = rec.get("qid") or f"norm:{norm}"
            if club in exclusions.get(qid, []):
                continue
            pid = seen.get(qid)
            if pid is None:
                cur.execute(
                    "INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        next_id,
                        rec["name"],
                        norm,
                        rec.get("position"),
                        rec.get("dob"),
                        rec.get("citizenship"),
                        rec.get("image"),
                    ),
                )
                pid = next_id
                seen[qid] = pid
                next_id -= 1
                added += 1
                if rec.get("citizenship"):
                    cty = str(rec["citizenship"])
                    cur.execute(
                        "INSERT OR IGNORE INTO player_countries VALUES (?, ?, ?)",
                        (pid, cty, normalize(cty)),
                    )
            # relación con este club: se agrega siempre (el mismo QID puede
            # aparecer en varias consultas de clubes)
            for cid in cids:
                cur.execute(
                    "INSERT OR IGNORE INTO player_clubs VALUES (?, ?)",
                    (pid, cid),
                )
    conn.commit()
    return added


if __name__ == "__main__":
    import sqlite3

    force = "--refresh" in sys.argv
    if force and CACHE_PATH.exists():
        CACHE_PATH.unlink()
    if not DB_PATH.exists():
        sys.exit(f"No existe {DB_PATH}; corré primero pipeline/build_dataset.py")
    conn = sqlite3.connect(DB_PATH)
    n = insert_history(conn)
    conn.close()
    total = sum(len(v) for v in fetch_all().values())
    print(f"Registros históricos en cache: {total}; nuevos insertados: {n}")
