"""Scraper del "histórico de jugadores" de BDFA para La Caprichosa.

Cada club de BDFA tiene una página `historico-{slug}-{id}.html` con los
"Jugadores Históricos": tablas por categoría (TOTALES, PRIMERA DIVISIÓN,
COPA ARGENTINA, ...) y por métrica (PARTIDOS / GOLES), con el ranking de
jugadores y su valor. Nos sirve para el juego "Top 10".

Estructura observada por bloque de tabla:
    <h3 class="alert alert-primary mt-2">Jugadores Historicos TOTALES *</h3>
    <p><strong>Jugadores con MAS PARTIDOS</strong></p>
    <table class="table">
      <tr>
        <td><div align="center"><img ... alt="Jugador de Argentina" /></div></td>
        <td><a href="jugadores-NOMBRE-ID.html">GATTI, HUGO ORLANDO</a></td>
        <td>412</td>
      ...

Guarda el resultado en la tabla `club_history`:
    club_bdfa_id | club_name | category | metric | bdfa_player_id | name | country | value

Uso:
    python pipeline/bdfa_historico.py [--clubs A-B-C] [--fresh-clubs]
"""

import argparse
import re
import sqlite3
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

from pipeline.bdfa_scraper import (  # noqa: E402
    BASE,
    PRIMERA_URL,
    HEADERS,
    http_get,
    parse_club_list,
    unescape,
    resolve_club_by_name,
)

DB_PATH = BACKEND_DIR / "data" / "futbol_argentino.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS club_history (
    club_bdfa_id INTEGER NOT NULL,
    club_name TEXT,
    club_id INTEGER,
    category TEXT NOT NULL,
    metric TEXT NOT NULL,
    bdfa_player_id INTEGER,
    name TEXT,
    country TEXT,
    value INTEGER,
    PRIMARY KEY (club_bdfa_id, category, metric, bdfa_player_id)
);
CREATE INDEX IF NOT EXISTS idx_club_history_club ON club_history(club_bdfa_id);
"""

H3_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.I | re.S)
STRONG_RE = re.compile(r"<p>\s*<strong>(Jugadores con MAS (PARTIDOS|GOLES))\s*</strong>\s*</p>", re.I | re.S)
TABLE_RE = re.compile(r'<table class="table">(.*?)</table>', re.I | re.S)
FLAG_ALT_RE = re.compile(r'alt="Jugador de ([^"]+)"', re.I)
PLAYER_LINK_RE = re.compile(r'href="(jugadores-[^"]+?)-(\d+)\.html"[^>]*>(.*?)</a>', re.I | re.S)


def extract_club_slug(plantel_url: str) -> str | None:
    m = re.search(r"plantel-(.+?)-(\d+)\.html", plantel_url)
    return m.group(1) if m else None


def parse_historico(html_text: str) -> tuple[list[dict], list[dict]]:
    """Parsea la página histórico de un club.

    Devuelve (bloques, filas): cada "bloque" es {"category", "metric"} y
    "filas" la lista de dicts por jugador (con el bloque al que pertenecen).

    Recorremos h3 / strong / table en orden de documento: el h3 fija la
    categoría, el <strong> la métrica, y la tabla siguiente sus filas.
    """
    h3s = [(m.start(), m.group(1)) for m in H3_RE.finditer(html_text)]
    strongs = [(m.start(), m.group(2).strip().upper()) for m in STRONG_RE.finditer(html_text)]
    tables = [(m.start(), m.group(1)) for m in TABLE_RE.finditer(html_text)]

    items = sorted(h3s + strongs + tables, key=lambda x: x[0])

    cur_cat: str | None = None
    cur_metric: str | None = None
    blocks: list[dict] = []
    rows_out: list[dict] = []

    for pos, payload in items:
        if isinstance(payload, str) and pos in [p for p, _ in h3s]:
            # es un h3: payload = contenido del h3. Solo nos interesan los
            # "Jugadores Historicos <CATEGORIA> *"; otros h3 se ignoran.
            text = re.sub(r"<[^>]+>", " ", unescape(payload))
            text = re.sub(r"\s+", " ", text).strip()
            if not re.match(r"^Jugadores Hist\s*oricos\b", text, re.I):
                continue
            text = re.sub(r"^Jugadores Hist\s*oricos\s*", "", text, flags=re.I)
            text = text.rstrip("* ").strip()
            cur_cat = text or None
            cur_metric = None
        elif pos in [p for p, _ in strongs]:
            cur_metric = payload if isinstance(payload, str) else None
        else:
            # tabla
            if cur_cat is None:
                continue
            metric = cur_metric or "PARTIDOS"
            rows = parse_table_rows(payload)
            if not rows:
                continue
            blocks.append({"category": cur_cat, "metric": metric})
            for r in rows:
                rows_out.append(
                    {
                        "category": cur_cat,
                        "metric": metric,
                        "name": r["name"],
                        "bdfa_player_id": r["bdfa_player_id"],
                        "country": r["country"],
                        "value": r["value"],
                    }
                )
    return blocks, rows_out


def parse_table_rows(table_body: str) -> list[dict]:
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", table_body, re.DOTALL | re.I):
        name_m = re.search(PLAYER_LINK_RE, tr)
        if not name_m:
            continue
        name = unescape(re.sub(r"<[^>]+>", "", name_m.group(3))).strip()
        bdfa_player_id = int(name_m.group(2))
        # valor: el último <td> numérico
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.DOTALL | re.I)
        value = 0
        for td_text in reversed(tds):
            raw = unescape(re.sub(r"<[^>]+>", "", td_text)).strip()
            if raw.replace(".", "").replace(",", "").lstrip("-").isdigit():
                value = int(raw.replace(".", "").replace(",", ""))
                break
        country = ""
        fc = FLAG_ALT_RE.search(tr)
        if fc:
            country = unescape(fc.group(1)).strip()
        if not country:
            src = re.search(r"src=\"banderas/[^/]+/([^/\"]+)\.png\"", tr)
            if src:
                country = unescape(src.group(1))
        rows.append(
            {
                "name": name,
                "bdfa_player_id": bdfa_player_id,
                "country": country,
                "value": value,
            }
        )
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clubs", type=str, default=None,
                    help="Subconjunto de clubes (nombres separados por coma).")
    args = ap.parse_args()

    print("Descargando lista de clubes de Primera División...")
    primera_html = http_get(PRIMERA_URL)
    clubs = parse_club_list(primera_html)
    print(f"Clubes encontrados: {len(clubs)}")
    if args.clubs:
        wanted = {c.strip().lower() for c in args.clubs.split(",")}
        clubs = [c for c in clubs if c["name"].lower() in wanted]
        print(f"Filtrando a {len(clubs)} clubes")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    total_rows = 0
    for club in clubs:
        slug = extract_club_slug(club["plantel_url"] or "")
        if not slug or club["bdfa_id"] is None:
            print(f"  [skip] {club['name']} (sin slug/id)")
            continue
        url = f"{BASE}/historico-{slug}-{club['bdfa_id']}.html"
        print(f"\n=== {club['name']} ({url}) ===")
        try:
            html_text = http_get(url)
        except requests.RequestException as exc:
            print(f"  [error] {exc}")
            continue
        blocks, rows = parse_historico(html_text)
        print(f"  bloques: {len(blocks)} | filas: {len(rows)}")

        club_id = resolve_club_by_name(conn, club["name"])
        n_insert = 0
        for row in rows:
            conn.execute(
                """INSERT INTO club_history
                   (club_bdfa_id, club_name, club_id, category, metric,
                    bdfa_player_id, name, country, value)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(club_bdfa_id, category, metric, bdfa_player_id) DO UPDATE SET
                     club_name = excluded.club_name,
                     club_id = excluded.club_id,
                     name = excluded.name,
                     country = excluded.country,
                     value = excluded.value""",
                (
                    club["bdfa_id"],
                    club["name"],
                    club_id,
                    row["category"],
                    row["metric"],
                    row["bdfa_player_id"],
                    row["name"],
                    row["country"],
                    row["value"],
                ),
            )
            n_insert += 1
        conn.commit()
        total_rows += n_insert
        time.sleep(0.15)

    conn.close()
    print("\n=== RESUMEN ===")
    print(f"Filas insertadas/actualizadas: {total_rows}")


if __name__ == "__main__":
    main()