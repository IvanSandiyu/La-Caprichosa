"""Scraper de BDFA (https://www.bdfa.com.ar) para La Caprichosa.

BDFA no tiene API pública: solo HTML (charset iso-8859-1). Este script:

1. Descarga la página de Primera División (lista de clubes) -> 30 clubes.
2. Para cada club descarga su "Plantel Actual" -> jugadores (id BDFA, apellido,
   nombres, posición, nacionalidad, nacimiento, lugar).
3. Asocia cada jugador del plantel con un jugador de nuestra DB (por nombre
   normalizado + fecha de nacimiento).
4. Para los jugadores asociados, descarga su página individual y extrae la
   CARRERA: períodos por club/división (tabla "Ficha Histórica").
5. Guarda todo en la tabla `player_career` (períodos por club) y en
   `player_bdfa` (planteles vistos) para referencia.

Antecedente de uso: resolver el conflicto de "cantera" en el juego Fútbol Link
(¿de verdad coincidieron en el mismo club en el mismo período?).

Uso:
    python pipeline/bdfa_scraper.py [--clubs A-B-C] [--limit N] [--players-only]

Convenciones tomadas de los demás scripts del pipeline (build_dataset.py,
cantera_wikidata.py): sys.path, DB_PATH, normalize() desde app.text.
"""

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.text import normalize  # noqa: E402

DB_PATH = BACKEND_DIR / "data" / "futbol_argentino.db"
CACHE_PATH = Path(__file__).resolve().parent / "bdfa_cache.json"

BASE = "https://www.bdfa.com.ar"
PRIMERA_URL = BASE + "/argentina-primera-division.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
}

# Secciones de la tabla de carrera que representan ligas de DIVISIÓN (las que
# nos sirven para "¿coincidieron en tal club en tal división?").
# '?': año de fin abierto (jugador actualmente ahí) -> year_to None.
YEARS_RE = re.compile(r"(\d{4})")


def http_get(url, retries=6):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            r.encoding = "iso-8859-1"
            return r.text
        except requests.RequestException as exc:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))
    return ""


def unescape(text: str) -> str:
    """Convierte entidades HTML (&ntilde;, &aacute;, &amp;, ...) a texto plano."""
    import html
    return html.unescape(text or "")


# ---------------------------------------------------------------- CLUBS ----

def parse_club_list(html_text: str) -> list[dict]:
    """Parsea la lista de clubes de Primera División.

    Estructura (observada):
        <h3>Nombre</h3>
        <p class="desc"><a href="clubese-NOMBRE-ID.html" title="Ficha de Club...">Ficha del Club</a></p>
        <p class="desc"><a href="plantel-NOMBRE-ID.html" title="Plantel de...">Plantel Actual</a></p>
    """
    soup = BeautifulSoup(html_text, "html.parser")
    clubs = []
    seen_urls = set()
    # En el orden del documento, los clubes van: <h3>Nombre</h3> ... enlaces ...
    # Recorremos h3 y enlaces de plantel juntos, asignando a cada enlace de
    # plantel el último h3 visto (que es su bloque).
    last_h3 = None
    for el in soup.find_all(["h3", "a"]):
        if el.name == "h3":
            t = el.get_text(strip=True)
            if t:
                last_h3 = t
            continue
        href = el.get("href") or ""
        if not re.search(r"plantel-[^/]+\.html$", href):
            continue
        if last_h3 is None:
            continue
        # key único por URL de plantel (evita dedupe por nombre: hay clubes con
        # el mismo nombre 'Estudiantes'/'Gimnasia y Esgrima' pero IDs distintos)
        if href in seen_urls:
            continue
        seen_urls.add(href)
        mid = re.search(r"plantel-[^/]+-(\d+)\.html", href)
        plantel_url = href if href.startswith("http") else BASE + "/" + href
        ficha_href = ""
        # ficha del club: buscar dentro del contenedor del h3
        h3node = el
        for _ in range(6):
            h3node = h3node.find_previous("h3")
            if h3node is None or h3node.get_text(strip=True) == last_h3:
                break
        block = h3node.find_parent(["div", "section", "li", "td"]) if h3node else None
        if block:
            fa = block.find("a", href=re.compile(r"clubese-[^/]+\.html"))
            if fa:
                ficha_href = fa.get("href")
        clubs.append(
            {
                "name": last_h3,
                "plantel_url": plantel_url,
                "ficha_url": (BASE + "/" + ficha_href) if ficha_href and not ficha_href.startswith("http") else (ficha_href or None),
                "bdfa_id": int(mid.group(1)) if mid else None,
            }
        )
    return clubs


# ------------------------------------------------------------- PLANTEL ----

def parse_plantel(html_text: str) -> list[dict]:
    """Parsea el plantel actual de un club. Devuelve lista de jugadores."""
    soup = BeautifulSoup(html_text, "html.parser")
    players = []
    cards = soup.find_all("div", class_="player-card")
    for card in cards:
        pid_attr = card.get("data-player-id")
        link = card.find("a", href=re.compile(r"jugadores-[^/]+\.html"))
        if link is None:
            continue
        href = link.get("href")
        # nombre: <strong>APELLIDO</strong>, NOMBRES
        strong = link.find("strong")
        apellido = strong.get_text(strip=True) if strong else None
        # nombres = resto del texto del <a> después de ","
        link_text = link.get_text(" ", strip=True)  # p.ej. "BELTRAN, SANTIAGO"
        nombres = None
        if "," in link_text:
            nombres = link_text.split(",", 1)[1].strip()
        full = (nombres + " " + apellido).strip() if (nombres and apellido) else link_text
        # posición
        pos_badge = card.find(class_="player-position-badge")
        pos_map = {
            "ARQ": "Arquero",
            "DEF": "Defensor",
            "VOL": "Volante",
            "DEL": "Delantero",
        }
        pos = pos_badge.get_text(strip=True) if pos_badge else "Volante"
        pos = pos_map.get(pos.upper(), pos)
        # nacionalidad: imgs con alt dentro de .player-nationality
        nat_box = card.find(class_="player-nationality")
        nats = []
        if nat_box:
            for img in nat_box.find_all("img"):
                alt = img.get("alt")
                if alt:
                    nats.append(alt)
        # nacimiento
        birth = ""
        pb = card.find(class_="player-birth")
        if pb:
            m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", pb.get_text(" ", strip=True))
            if m:
                birth = m.group(1)
        players.append(
            {
                "bdfa_id": int(pid_attr) if pid_attr else None,
                "profile_url": href if href.startswith("http") else BASE + "/" + href,
                "apellido": apellido,
                "nombres": nombres,
                "name": full,
                "position": pos,
                "nationality": nats,
                "birth": birth,
            }
        )
    return players


# -------------------------------------------------------------- CAREER ----

def parse_career(html_text: str) -> dict:
    """Parsea la página individual de un jugador -> datos + carrera.

    La carrera viene en UNA sola tabla `table.modern-table` con secciones
    `tr.table-section` (Primera División, Segunda, Tercera, Copa Argentina,
    Copa Libertadores, Selecciones Nacionales, ...) y filas por club.

    Devuelve:
        {
          "name": ...,
          "position": ...,
          "nationality": ...,
          "birth": "D/M/YYYY",
          "birth_place": ...,
          "sections": [
             {"section": "Primera División", "rows": [
                {"club": "Boca Juniors", "city": "Capital Federal",
                 "country": "Argentina", "years": "2006-2011 / 2020-?",
                 "year_from": 2006, "year_to": None, "is_current": True,
                 "pj": 61, "goals": 0},
             ]}
          ],
        }
    """
    name = ""
    nm = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.DOTALL | re.IGNORECASE)
    if nm:
        name = unescape(re.sub(r"<[^>]+>", "", nm.group(1))).strip()

    position = ""
    nationality = ""
    birth = ""
    birth_place = ""
    # .jugador-datos
    jd = re.search(r'<div class="jugador-header">(.*?)<!-- FIN DATOS JUGADOR -->', html_text, re.DOTALL | re.IGNORECASE)
    if jd:
        block = jd.group(1)
        def labelled(label):
            m = re.search(
                r'<span class="etiqueta">[^<]*' + label + r'[^<]*</span>\s*(.*?)(?:<img|</p>)',
                block,
                re.DOTALL | re.IGNORECASE,
            )
            if not m:
                return ""
            txt = unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
            return txt.strip()
        nationality = labelled("Nacionalidad")
        position = labelled("Posici")
        b = labelled("Nacimiento")
        if b:
            b0 = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", b)
            if b0:
                birth = b0.group(1)
        birth_place = labelled("Lugar")

    # TABLA DE CARRERA
    table = None
    tm = re.search(r'<table[^>]*class="[^"]*modern-table[^"]*"[^>]*>(.*?)</table>', html_text, re.DOTALL | re.IGNORECASE)
    if tm:
        table = tm.group(1)

    sections = []
    if table:
        # dividir el <tbody> en segmentos por <tr class="table-section">
        parts = re.split(r'<tr[^>]*class="table-section"[^>]*>.*?</tr>', table, flags=re.DOTALL | re.IGNORECASE)
        # capturar los títulos de sección en su orden
        sec_titles = re.findall(
            r'<tr[^>]*class="table-section"[^>]*>.*?>(.*?)<span', table, re.DOTALL | re.IGNORECASE
        )
        titles = []
        for st in sec_titles:
            t = unescape(re.sub(r"<[^>]+>", " ", st)).strip()
            t = re.sub(r"\s+", " ", t)
            titles.append(t)
        # parts[0] es el thead + nada; parts[i] corresponde a titles[i-1]
        for i, body in enumerate(parts[1:], start=0):
            if i >= len(titles):
                break
            section_name = titles[i]
            rows = parse_section_rows(body)
            if rows:
                sections.append({"section": section_name, "rows": rows})

    return {
        "name": name,
        "position": position,
        "nationality": nationality,
        "birth": birth,
        "birth_place": birth_place,
        "sections": sections,
    }


def parse_section_rows(body_part: str) -> list[dict]:
    """Parsea las filas de datos de una sección de la tabla de carrera.

    Cada fila:
        <tr>
          <td class="club-cell">
            <div class="years-line">2006-2011 / 2020-?</div>
            <div class="club-info">
              <img ... alt="Argentina" .../>
              <a href="...">Boca Juniors</a><span class="city">(Capital Federal)</span>
            </div>
          </td>
          <td>61</td><td>0</td><td>0,00</td>
        </tr>
    """
    rows = []
    # aislar cada <tr> que contenga years-line (los de datos)
    trs = re.findall(r"<tr>(.*?)</tr>", body_part, re.DOTALL | re.IGNORECASE)
    for tr in trs:
        yl = re.search(r'class="years-line"[^>]*>(.*?)</div>', tr, re.DOTALL | re.IGNORECASE)
        if not yl:
            continue
        years_raw = unescape(re.sub(r"<[^>]+>", "", yl.group(1))).strip()
        is_current = "current-club" in yl.group(1)
        # club
        club = ""
        cm = re.search(r'club-info.*?<a[^>]*>(.*?)</a>', tr, re.DOTALL | re.IGNORECASE)
        if cm:
            club = unescape(re.sub(r"<[^>]+>", "", cm.group(1))).strip()
        city = ""
        cym = re.search(r'class="city"[^>]*>\(([^)]*)\)', tr, re.IGNORECASE)
        if cym:
            city = unescape(cym.group(1)).strip()
        country = ""
        fm = re.search(r'<img[^>]*alt="([^"]+)"[^>]*class="flag-icon"', tr, re.IGNORECASE)
        if not fm:
            fm = re.search(r'class="flag-icon"[^>]*alt="([^"]+)"', tr, re.IGNORECASE)
        if fm:
            country = unescape(fm.group(1)).strip()
        if not country:
            # el <img> de la bandera no lleva alt; lo inferimos del nombre de archivo
            fsrc = re.search(r'<img[^>]*class="flag-icon"[^>]*src="[^"]*/([^/]+)\.png"', tr, re.IGNORECASE)
            if fsrc:
                country = unescape(fsrc.group(1)).strip()
        # tds numéricos: PJ, Goles, Prom
        tds = re.findall(r"<td[^>]*class=\"text-center\"[^>]*>(.*?)</td>", tr, re.DOTALL | re.IGNORECASE)
        nums = [unescape(re.sub(r"<[^>]+>", "", t)).strip() for t in tds]
        def to_int(s):
            s = s.replace(".", "").replace(",", "")
            return int(s) if s.lstrip("-").isdigit() else 0
        pj = to_int(nums[0]) if len(nums) > 0 else 0
        goals = to_int(nums[1]) if len(nums) > 1 else 0
        # rango de años
        years_all = YEARS_RE.findall(years_raw)
        year_from = int(min(years_all)) if years_all else None
        year_to_raw = max(years_all) if years_all else None
        year_to = int(year_to_raw) if year_to_raw else None
        if is_current or "?" in years_raw:
            year_to = None  # abierto / actual
        rows.append(
            {
                "club": club,
                "city": city,
                "country": country,
                "years": years_raw,
                "year_from": year_from,
                "year_to": year_to,
                "is_current": bool(is_current),
                "pj": pj,
                "goals": goals,
            }
        )
    return rows


# ------------------------------------------------------------ MATCHING ----

def build_player_index(conn):
    """Índice de jugadores de nuestra DB por token de nombre normalizado.

    Mapea cada token (por ejemplo 'otamendi', 'nicolas') a la lista de
    (player_id, tokens_normalizados, dob).
    """
    idx = {}
    for pid, name, _norm, dob in conn.execute(
        "SELECT player_id, name, norm, dob FROM players"
    ):
        tokens = set(normalize(name).split())
        for t in tokens:
            idx.setdefault(t, []).append((pid, tokens, dob))
    return idx


def match_player(idx, apellido, nombres, birth):
    """Devuelve el player_id de nuestra DB que mejor combina, o None.

    Emplea coincidencia por tokens de nombre (tolerante a nombres de pila/medio
    extra) y confirma con fecha de nacimiento cuando es posible.
    """
    surnames = set(normalize(apellido).split())
    given = set(normalize(nombres).split())
    full = surnames | given
    if not full:
        return None
    cands = {}
    for t in surnames:
        for pid, toks, dob in idx.get(t, []):
            cands.setdefault(pid, (toks, dob))
    if not cands:
        return None
    best = []
    for pid, (toks, dob) in cands.items():
        # el nombre de la DB debe contener todo el apellido BDFA
        if not surnames.issubset(toks):
            continue
        # y todos sus tokens deben estar presentes en el nombre completo BDFA
        if not toks.issubset(full):
            continue
        best.append((pid, dob))
    if not best:
        return None
    if birth:
        bdate = birth_to_iso(birth)
        exact = [b for b in best if b[1] and b[1][:10] == bdate]
        if len(exact) == 1:
            return exact[0][0]
        if len(exact) > 1:
            return None
    if len(best) == 1:
        return best[0][0]
    return None


def birth_to_iso(birth_dmY):
    """Convierte 'D/M/YYYY' -> 'YYYY-MM-DD'."""
    try:
        d, m, y = birth_dmY.split("/")
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except Exception:
        return None


# --------------------------------------------------------------- DB ---- ----

SCHEMA = """
CREATE TABLE IF NOT EXISTS player_bdfa (
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    bdfa_id INTEGER NOT NULL,
    club_bdfa_id INTEGER,
    club_id INTEGER,
    name TEXT,
    apellido TEXT,
    nombres TEXT,
    position TEXT,
    nationality TEXT,
    birth TEXT,
    profile_url TEXT,
    PRIMARY KEY (player_id, bdfa_id)
);
CREATE INDEX IF NOT EXISTS idx_player_bdfa_club ON player_bdfa(club_id);
CREATE INDEX IF NOT EXISTS idx_player_bdfa_bdfa ON player_bdfa(bdfa_id);

CREATE TABLE IF NOT EXISTS player_career (
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    section TEXT NOT NULL,
    club_id INTEGER,
    club_name TEXT,
    country TEXT,
    years TEXT,
    year_from INTEGER,
    year_to INTEGER,
    is_current INTEGER DEFAULT 0,
    pj INTEGER,
    goals INTEGER,
    PRIMARY KEY (player_id, section, club_id, years)
);
CREATE INDEX IF NOT EXISTS idx_career_club ON player_career(club_id);
CREATE INDEX IF NOT EXISTS idx_career_player ON player_career(player_id);
"""

# Nombres de clubes BDFA (tal como figuran en las fichas de carrera) que no
# casan con los nombres cortos de la base o que son ambiguos, mapeados a
# nuestro club_id. Clave = nombre normalizado (con espacios).
CLUB_ALIAS = {
    "newell old boys": 1286,            # "Newell's Old Boys"
    "newells old boys": 1286,
    "newells": 1286,
    "velez sarsfield": 1029,
    "velez": 1029,
    "gimnasia y esgrima": 1106,         # Gimnasia (LP)
    "gimnasia y esgrima la plata": 1106,
    "gimnasia la plata": 1106,
    "gimnasia de mendoza": 14687,
    "gimnasia y esgrima de mendoza": 14687,
    "estudiantes de la plata": 288,
    "estudiantes": 288,
    "estudiantes la plata": 288,
    "independiente rivadavia": 12179,
    "independ. rivadavia": 12179,
    "independiente r.": 12179,
    "instituto de cordoba": 1829,
    "instituto": 1829,
    "central cordoba": 31284,
    "central cordoba santiago del estero": 31284,
    "atletico tucuman": 14554,
    "san martin de san juan": 10511,
    "san martin san juan": 10511,
    "deportivo riestra": 19775,
    "union de santa fe": 7097,
    "union": 7097,
    "talleres de cordoba": 3938,
    "talleres": 3938,
    "ca talleres": 3938,
    "club atletico tigre": 11831,
    "racing avellaneda": 1444,
    "sarmiento de junin": 12454,
    "sarmiento": 12454,
}


def resolve_club_by_name(conn, club_name):
    """Mapea un nombre de club BDFA -> club_id de nuestra DB."""
    n = normalize(club_name)
    if not n:
        return None
    if n in CLUB_ALIAS:
        return CLUB_ALIAS[n]
    row = conn.execute("SELECT club_id FROM clubs WHERE norm=?", (n,)).fetchone()
    if row:
        return row[0]
    # substring (solo cuando es inequívoco)
    hits = []
    for cid, name, cnorm in conn.execute("SELECT club_id, name, norm FROM clubs"):
        if n and (n in cnorm or cnorm in n):
            hits.append(cid)
    if len(hits) == 1:
        return hits[0]
    return None


# Desambiguación del club del plantel por ID BDFA. Algunos nombres BDFA son
# ambiguos ('Estudiantes', 'Gimnasia y Esgrima'); el ID del slug (antes del
# '.html') es la forma confiable de distinguirlos.
# bdfa_id -> club_id de nuestra DB (None => club excluido/irrelevante).
BDFA_CLUB_ID = {
    59: 288,      # Estudiantes de La Plata
    9: None,      # segundo 'Estudiantes' (Caseros/BA) -> excluido
    10: 1106,     # Gimnasia y Esgrima La Plata
    66: 14687,    # Gimnasia y Esgrima de Mendoza
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clubs", type=str, default=None,
                    help="Subconjunto de clubes (nombres separados por coma).")
    ap.add_argument("--limit", type=int, default=None,
                    help="Límite de páginas de jugador a scrapear.")
    ap.add_argument("--players-only", action="store_true",
                    help="Solo scrapear planteles (saltar páginas de jugador).")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    # ---------- 1) lista de clubes ----------
    print("Descargando lista de clubes de Primera División...")
    primera_html = http_get(PRIMERA_URL)
    clubs = parse_club_list(primera_html)
    print(f"Clubes encontrados: {len(clubs)}")
    if args.clubs:
        wanted = {c.strip().lower() for c in args.clubs.split(",")}
        clubs = [c for c in clubs if c["name"].lower() in wanted]
        print(f"Filtrando a {len(clubs)} clubes")

    idx = build_player_index(conn)

    all_players_seen = []
    career_inserts = 0
    profile_fetched = 0

    for club in clubs:
        if not club["plantel_url"]:
            continue
        name = club["name"]
        print(f"\n=== {name} ===")
        try:
            plantel_html = http_get(club["plantel_url"])
        except requests.RequestException as exc:
            print(f"  [error] plantel {name}: {exc}")
            continue
        players = parse_plantel(plantel_html)
        print(f"  plantel: {len(players)} jugadores")
        # club_id destino (desambiguar por ID BDFA cuando hay nombres duplicados)
        if club["bdfa_id"] in BDFA_CLUB_ID:
            club_id = BDFA_CLUB_ID[club["bdfa_id"]]
        else:
            club_id = resolve_club_by_name(conn, name)
        print(f"  club_id en DB: {club_id}")
        if club_id is None:
            # club excluido/irrelevante (p.ej. Estudiantes de BA): igual
            # anotamos los jugadores por si están en la base, sin club.
            pass

        for p in players:
            pid = match_player(idx, p["apellido"], p["nombres"], p["birth"])
            if pid is None:
                continue  # no está en nuestra DB -> lo anotamos igual pero sin carrera
            all_players_seen.append((pid, p, club_id))
            # registrar en player_bdfa
            conn.execute(
                """INSERT OR IGNORE INTO player_bdfa
                   (player_id, bdfa_id, club_bdfa_id, club_id, name, apellido,
                    nombres, position, nationality, birth, profile_url)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    pid,
                    p["bdfa_id"],
                    club["bdfa_id"],
                    club_id,
                    p["name"],
                    p["apellido"],
                    p["nombres"],
                    p["position"],
                    "/".join(p["nationality"]),
                    p["birth"],
                    p["profile_url"],
                ),
            )

    conn.commit()
    print(f"\nJugadores asociados a nuestra DB: {len(all_players_seen)}")

    # ---------- 2) carreras de los jugadores asociados ----------
    if args.players_only:
        conn.close()
        print("players-only: skip de páginas de jugador.")
        return

    # dedupe por player id
    seen_pid = {}
    for pid, p, club_id in all_players_seen:
        seen_pid.setdefault(pid, p)

    # caché de perfiles ya parseados
    cache = {}
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    todo = [p for pid, p in sorted(seen_pid.items(), key=lambda x: x[0])]
    if args.limit:
        todo = todo[: args.limit]

    for i, p in enumerate(todo):
        pid = None
        for k, v in seen_pid.items():
            if v is p:
                pid = k
                break
        if pid is None:
            continue
        url = p["profile_url"]
        card = cache.get(url)
        if card is None:
            try:
                html_text = http_get(url)
            except requests.RequestException as exc:
                print(f"  [error] {p['name']}: {exc}")
                continue
            card = parse_career(html_text)
            cache[url] = card
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            profile_fetched += 1
            time.sleep(0.25)
        # insertar carrera
        for sec in card.get("sections", []):
            sec_name = sec["section"]
            for row in sec["rows"]:
                club_id_row = resolve_club_by_name(conn, row["club"])
                conn.execute(
                    """INSERT OR IGNORE INTO player_career
                       (player_id, section, club_id, club_name, country, years,
                        year_from, year_to, is_current, pj, goals)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        pid,
                        sec_name,
                        club_id_row,
                        row["club"],
                        row["country"],
                        row["years"],
                        row["year_from"],
                        row["year_to"],
                        int(row["is_current"]),
                        row["pj"],
                        row["goals"],
                    ),
                )
                career_inserts += 1
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(todo)} jugadores procesados")
            conn.commit()

    conn.commit()
    conn.close()
    print("\n=== RESUMEN ===")
    print(f"Perfiles descargados: {profile_fetched}")
    print(f"Filas de carrera insertadas: {career_inserts}")


if __name__ == "__main__":
    main()
