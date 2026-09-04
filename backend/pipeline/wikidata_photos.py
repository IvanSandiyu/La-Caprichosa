"""Completa fotos faltantes de los jugadores scrapeados de Wikidata.

Los jugadores con player_id negativo (históricos scrapeados por club) fueron
cargados sin imagen cuando P18 no vino durante el scrape. Sus QIDs están en
wikidata_history.json (clave: nombre normalizado). Este script relé el claim
P18 de todos esos QIDs por lotes, arma la URL de thumbnail y la guarda en
players.image_url.

Para los pocos jugadores curados (player_id > -100000, p. ej. -1..-5) hace una
búsqueda por nombre con VERIFICACIÓN de fecha de nacimiento, para no asignar
la foto de un homónimo histórico.

Uso:
    python pipeline/wikidata_photos.py
"""

import json
import sys
import time
import urllib.parse
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.text import normalize  # noqa: E402

DB_PATH = BACKEND_DIR / "data" / "futbol_argentino.db"
HISTORY_PATH = Path(__file__).resolve().parent / "wikidata_history.json"
IMAGES_CACHE = Path(__file__).resolve().parent / "wikidata_images.json"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_UA = "LaCaprichosa/1.0 (trivia game; local use)"
FOOTBALLER_RE = __import__("re").compile(r"futbolista|football|soccer", __import__("re").IGNORECASE)
BATCH = 25
BATCH_DELAY = 2.0
BACKOFF = [3, 6, 12, 24, 48, 90]


def _get(params: dict) -> dict:
    last = None
    for attempt, wait in enumerate(BACKOFF):
        try:
            resp = requests.get(
                WIKIDATA_API,
                params={**params, "format": "json"},
                headers={"User-Agent": WIKIDATA_UA},
                timeout=40,
            )
            if resp.status_code == 429:
                raise requests.HTTPError("429")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last = exc
            print(f"    ... reintento en {wait}s ({exc})")
            time.sleep(wait)
    raise last


def commons_thumb(filename: str, width: int = 250) -> str:
    return (
        "https://commons.wikimedia.org/wiki/Special:FilePath/"
        + urllib.parse.quote(filename)
        + f"?width={width}"
    )


def p18_for_qids(qids: list[str]) -> dict[str, str | None]:
    """Consulta claims de hasta BATCH QIDs. Devuelve {qid: filename|None}."""
    data = _get(
        {
            "action": "wbgetentities",
            "ids": "|".join(qids),
            "props": "claims",
        }
    )
    out: dict[str, str | None] = {}
    entities = data.get("entities", {})
    for qid in qids:
        claim = entities.get(qid, {}).get("claims", {}).get("P18") or []
        if not claim:
            out[qid] = None
            continue
        snak = claim[0].get("mainsnak", {})
        if snak.get("snaktype") != "value":
            out[qid] = None
            continue
        value = snak.get("datavalue", {}).get("value")
        out[qid] = value if isinstance(value, str) else None
    return out


def search_candidates(name: str) -> list[dict]:
    """Candidatos de wbsearchentities (descripción futbolista), todos los idiomas."""
    out: list[dict] = []
    seen: set[str] = set()
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
        except requests.RequestException as exc:
            print(f"    [warn] búsqueda '{name}' ({lang}): {exc}")
            continue
        for cand in data.get("search", []):
            desc = cand.get("description") or ""
            if not FOOTBALLER_RE.search(desc):
                continue
            qid = cand["id"]
            if qid in seen:
                continue
            seen.add(qid)
            out.append({"qid": qid, "name": cand.get("label") or "", "desc": desc})
    return out


def dobs_for_qids(qids: list[str]) -> dict[str, str | None]:
    data = _get({"action": "wbgetentities", "ids": "|".join(qids), "props": "claims"})
    out: dict[str, str | None] = {}
    for qid in qids:
        claims = data.get("entities", {}).get(qid, {}).get("claims", {})
        p569 = claims.get("P569") or []
        if not p569:
            out[qid] = None
            continue
        st = p569[0].get("mainsnak", {})
        if st.get("snaktype") != "value":
            out[qid] = None
            continue
        v = st.get("datavalue", {}).get("value")
        if isinstance(v, dict):
            out[qid] = str(v.get("time", ""))[:10]
        else:
            out[qid] = None
    return out


def verified_photo(name: str, dob: str | None) -> str | None:
    """Busca P18 de un jugador curado, verificando fecha de nacimiento si hay."""
    cands = search_candidates(name)
    if not cands:
        return None
    qids = [c["qid"] for c in cands]
    file_by_qid = p18_for_qids(qids)
    dob_by_qid = {}
    for i in range(0, len(qids), BATCH):
        dob_by_qid.update(dobs_for_qids(qids[i:i + BATCH]))
    # prioridad: qid con fecha coincidente y foto
    if dob:
        for c in cands:
            q = c["qid"]
            wd_dob = dob_by_qid.get(q)
            if wd_dob and wd_dob[:4] == dob[:4] and file_by_qid.get(q):
                return commons_thumb(file_by_qid[q]) if file_by_qid[q] else None
    # fallback: cualquier futbolista candidato con foto
    for c in cands:
        f = file_by_qid.get(c["qid"])
        if f:
            return commons_thumb(f)
    return None


def main():
    if not HISTORY_PATH.exists():
        sys.exit("No existe wikidata_history.json")
    import sqlite3

    conn = sqlite3.connect(DB_PATH)

    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    by_norm: dict[str, dict] = {}
    for club, players in history.items():
        for p in players:
            n = normalize(p.get("name", ""))
            if n and p.get("qid"):
                by_norm.setdefault(n, {"qid": p["qid"], "name": p["name"]})

    rows = conn.execute(
        "SELECT player_id, name, dob FROM players "
        "WHERE (image_url IS NULL OR image_url = '')"
    ).fetchall()
    print(f"Jugadores sin foto: {len(rows)}")

    jobs: list[tuple[int, str, str]] = []
    curated = []
    for pid, name, dob in rows:
        if pid > -100000:
            curated.append((pid, name, dob))
            continue
        hit = by_norm.get(normalize(name))
        if hit:
            jobs.append((pid, name, hit["qid"]))
        else:
            curated.append((pid, name, dob))

    print(f"Con qid a consultar: {len(jobs)} · curados (verificados): {len(curated)}")

    qids = sorted({q for _, _, q in jobs})
    results: dict[str, str | None] = {}
    for i in range(0, len(qids), BATCH):
        chunk = qids[i:i + BATCH]
        try:
            results.update(p18_for_qids(chunk))
        except requests.RequestException as exc:
            print(f"  [error] lote {i} agotó reintentos: {exc}")
        time.sleep(BATCH_DELAY)

    cache = {}
    if IMAGES_CACHE.exists():
        try:
            cache = json.loads(IMAGES_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    updated = 0
    missing = 0
    for pid, name, qid in jobs:
        filename = results.get(qid)
        if filename:
            url = commons_thumb(filename)
            conn.execute("UPDATE players SET image_url = ? WHERE player_id = ?", (url, pid))
            updated += 1
        else:
            missing += 1
        cache[name.casefold()] = commons_thumb(filename) if filename else None

    for pid, name, dob in curated:
        key = name.casefold()
        url = cache.get(key)
        if url:  # ya resuelto en una corrida anterior
            conn.execute("UPDATE players SET image_url = ? WHERE player_id = ?", (url, pid))
            updated += 1
            continue
        try:
            url2 = verified_photo(name, dob)
        except requests.RequestException as exc:
            print(f"  [warn] '{name}': {exc}")
            url2 = None
        cache[key] = url2
        if url2:
            conn.execute("UPDATE players SET image_url = ? WHERE player_id = ?", (url2, pid))
            updated += 1
            print(f"  [foto] {name} -> {url2}")
        else:
            print(f"  [sin foto] {name}")

    conn.commit()
    conn.close()
    IMAGES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Fotos asignadas: {updated} · sin P18: {missing}")

    c2 = sqlite3.connect(DB_PATH)
    left = c2.execute("SELECT COUNT(*) FROM players WHERE (image_url IS NULL OR image_url='')").fetchone()[0]
    print(f"Siguen sin foto: {left}")


if __name__ == "__main__":
    main()