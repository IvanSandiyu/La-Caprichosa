"""Completa imágenes faltantes usando la API de Wikidata (gratis, sin key).

Flujo por jugador sin imagen:
  1. wbsearchentities -> candidatos cuyo description menciona futbolista/football
  2. wbgetentities -> claim P18 (imagen) del primer candidato válido
  3. se guarda como Special:FilePath con ancho fijo (thumbnail)

Los resultados (incluidos los negativos) se cachean en wikidata_images.json
para no reconsultar en rebuilds.

Uso:
    python pipeline/enrich_wikidata.py            # sobre la DB existente
    (build_dataset.py lo llama automáticamente al final del rebuild)
"""

import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

DB_PATH = BACKEND_DIR / "data" / "futbol_argentino.db"
CACHE_PATH = Path(__file__).resolve().parent / "wikidata_images.json"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

HEADERS = {"User-Agent": "LaCaprichosa/1.0 (trivia game; local use)"}
FOOTBALLER_RE = re.compile(r"futbolista|football|soccer", re.IGNORECASE)

# debajo de este piso están los jugadores scrapeados de Wikidata
# (no les buscamos imagen por API: muestran silueta si P18 no vino)
SCRAPED_ID_FLOOR = -100000


def _get(params: dict) -> dict:
    resp = requests.get(
        WIKIDATA_API,
        params={**params, "format": "json"},
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def find_qid(name: str) -> str | None:
    """Busca el ítem de Wikidata del futbolista con ese nombre."""
    for lang in ("es", "en"):
        try:
            data = _get(
                {
                    "action": "wbsearchentities",
                    "search": name,
                    "language": lang,
                    "uselang": lang,
                    "type": "item",
                    "limit": 5,
                }
            )
        except Exception:
            continue
        for cand in data.get("search", []):
            desc = cand.get("description") or ""
            if FOOTBALLER_RE.search(desc):
                return cand["id"]
    return None


def get_p18_filename(qid: str) -> str | None:
    data = _get({"action": "wbgetentities", "ids": qid, "props": "claims"})
    claims = data.get("entities", {}).get(qid, {}).get("claims", {})
    p18 = claims.get("P18") or []
    if not p18:
        return None
    snak = p18[0].get("mainsnak", {})
    if snak.get("snaktype") != "value":
        return None
    value = snak.get("datavalue", {}).get("value")
    return value if isinstance(value, str) else None


def wikipedia_page_image(name: str) -> str | None:
    """Fallback: imagen del artículo de Wikipedia (prop=pageimages)."""
    for lang in ("es", "en"):
        try:
            resp = requests.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": name,
                    "prop": "pageimages",
                    "piprop": "original",
                    "redirects": 1,
                    "format": "json",
                },
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
            for page in resp.json().get("query", {}).get("pages", {}).values():
                src = page.get("original", {}).get("source")
                if src:
                    return src
        except Exception:
            continue
        time.sleep(1)
    return None


def find_photo(name: str) -> str | None:
    """Wikidata P18 primero; si no hay, imagen del artículo de Wikipedia."""
    qid = find_qid(name)
    if qid:
        fname = get_p18_filename(qid)
        if fname:
            return commons_thumb(fname)
    return wikipedia_page_image(name)


def commons_thumb(filename: str, width: int = 250) -> str:
    return (
        "https://commons.wikimedia.org/wiki/Special:FilePath/"
        + urllib.parse.quote(filename)
        + f"?width={width}"
    )


def fill_missing(conn) -> int:
    cache = (
        json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if CACHE_PATH.exists()
        else {}
    )
    rows = conn.execute(
        "SELECT player_id, name FROM players "
        "WHERE player_id > ? AND (image_url IS NULL OR image_url = '')",
        (SCRAPED_ID_FLOOR,),
    ).fetchall()
    updated = 0
    for pid, name in rows:
        key = name.casefold()
        if key in cache:
            url = cache[key]
        else:
            try:
                url = find_photo(name)
            except Exception as exc:  # red caída: no romper el build
                print(f"  [wikidata] error con '{name}': {exc}")
                continue
            cache[key] = url
            CACHE_PATH.write_text(
                json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            time.sleep(0.5)  # cortesía con la API
        if url:
            conn.execute(
                "UPDATE players SET image_url = ? WHERE player_id = ?", (url, pid)
            )
            print(f"  [wikidata] {name}: foto encontrada ({url})")
            updated += 1
        else:
            print(f"  [wikidata] {name}: sin resultado")
    conn.commit()
    return updated


if __name__ == "__main__":
    import sqlite3

    if not DB_PATH.exists():
        sys.exit(f"No existe {DB_PATH}; corré primero pipeline/build_dataset.py")
    conn = sqlite3.connect(DB_PATH)
    n = fill_missing(conn)
    conn.close()
    print(f"Imágenes agregadas: {n}")
