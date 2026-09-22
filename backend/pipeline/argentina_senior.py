"""Listado de jugadores de la seleccion ARGENTINA MAYOR (>= 1 cap).

Fuente: Wikipedia "List of Argentina international footballers" (wikitexto).
Genera `argentina_senior.json` con {name, caps} para restringir el pool
"Argentina" del grid (player_countries) a jugadores que jugaron al menos
UN partido en la seleccion mayor; los juveniles / sub 20 NO cuentan.

El matching contra la BDD es determinista y reproducible (mismo criterio
`answerMatches` del frontend):
  * cada token del nombre senior debe ser token completo o prefijo (>=2
    letras) de un token del nombre del jugador en la BDD (ambos normalizados);
  * los tokens del senior se consumen uno a uno (sin repetir) y TODOS deben
    encontrar un match.

El archivo `argentina_senior_extra.json` permite curaciones manuales de
futbolistas senior cuyo nombre en la BDD NO incluye el segundo nombre
(p.ej. "José Sand" en la BDD == senior "José Gustavo Sand"). Cada entrada:
  {name_bdd, name_senior, caps}. El matching usa el NOMBRE BDD normalizado
  (identidad exacta), nunca tokens sueltos, para no colgarse de homonimos.
"""

import json
import re
import sqlite3
import urllib.request
from pathlib import Path

from app.text import normalize

URL = (
    "https://en.wikipedia.org/w/index.php?title="
    "List_of_Argentina_international_footballers&action=raw"
)
OUT = Path(__file__).resolve().parent / "argentina_senior.json"
EXTRA = Path(__file__).resolve().parent / "argentina_senior_extra.json"

_LINK = re.compile(r"\[\[([^\[\]|]+)(?:\|[^\[\]]*)?\]\]")


def _tokens(norm: str) -> list[str]:
    return [t for t in (norm or "").split() if t]


def _strip_disambig(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def _clean_name(raw: str) -> str:
    text = raw.replace("'''", "").replace("''", "")

    def repl(m: re.Match) -> str:
        return m.group(1).strip()

    text = _LINK.sub(repl, text)
    text = text.replace("&nbsp;", " ").strip()
    return _strip_disambig(text)


def _to_int(s: str) -> int | None:
    try:
        return int(s)
    except (ValueError, TypeError):
        m = re.search(r"\d+", s or "")
        return int(m.group()) if m else None


def build_senior_names() -> list[list[str]]:
    """[[tokens_normalizados]] de los seniores con >=1 cap y nombre util."""
    out: list[list[str]] = []
    if not OUT.exists():
        return out
    data = json.loads(OUT.read_text(encoding="utf-8"))
    seen: set[str] = set()
    for p in data.get("players", []):
        if (p.get("caps") or 0) < 1:
            continue
        toks = _tokens(normalize(p.get("name", "")))
        key = " ".join(toks).casefold()
        if not toks or key in seen:
            continue
        seen.add(key)
        out.append(toks)
    return out


def name_matches_senior(norm: str, senior_names) -> bool:
    """True si `norm` cubre todos los tokens de algun senior.

    Criterio `answerMatches` del frontend: cada token del senior debe ser
    token completo o prefijo (>=2 letras) de un token del norm; los tokens
    del norm se consumen sin repetir.
    """
    if not norm:
        return False
    n = _tokens(norm)
    for s_toks in senior_names:
        used = [False] * len(n)
        ok = True
        for g in s_toks:
            hit = False
            for i in range(len(n)):
                if used[i]:
                    continue
                t = n[i]
                if len(g) >= 2:
                    if t == g or t.startswith(g):
                        used[i] = True
                        hit = True
                        break
                else:
                    if t == g:
                        used[i] = True
                        hit = True
                        break
            if not hit:
                ok = False
                break
        if ok:
            return True
    return False


def _read_extra() -> list[dict]:
    if not EXTRA.exists():
        return []
    try:
        return json.loads(EXTRA.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def restrict_argentina(conn: sqlite3.Connection) -> dict:
    """Reescribe player_countries 'Argentina': solo jugadores de la Mayot.

    Devuelve {removidos, agregados, jugadores_senior, total_final}.
    """
    senior_names = build_senior_names()
    extra = _read_extra()
    extra_norm = {normalize(e.get("name_bdd", "")): e for e in extra}

    players = conn.execute("SELECT player_id, name, norm FROM players").fetchall()
    player_norm = {pid: norm for pid, _n, norm in players}
    player_name = {pid: name for pid, name, _n in players}

    senior_ids: set[int] = set()
    for pid, norm in player_norm.items():
        if name_matches_senior(norm or "", senior_names):
            senior_ids.add(pid)
    # EXTRA: match por nombre BDD normalizado (identidad exacta, curado)
    for e in extra:
        key = normalize(e.get("name_bdd", ""))
        if not key:
            continue
        for pid, nm in player_name.items():
            if normalize(nm or "") == key:
                senior_ids.add(pid)

    current = {
        r[0]
        for r in conn.execute(
            "SELECT player_id FROM player_countries WHERE norm = 'argentina'"
        ).fetchall()
    }
    all_norms = set(player_norm)

    to_remove = current - senior_ids
    to_add = (senior_ids - current) & all_norms

    for pid in sorted(to_remove):
        conn.execute(
            "DELETE FROM player_countries WHERE player_id = ? AND norm = 'argentina'",
            (pid,),
        )
    for pid in sorted(to_add):
        conn.execute(
            "INSERT OR IGNORE INTO player_countries VALUES (?, 'Argentina', 'argentina')",
            (pid,),
        )
    conn.commit()

    final = conn.execute(
        "SELECT COUNT(*) FROM player_countries WHERE norm = 'argentina'"
    ).fetchone()[0]
    return {
        "removidos": len(to_remove),
        "agregados": len(to_add),
        "jugadores_senior": len(senior_ids),
        "total_final": final,
    }


def main() -> None:
    players = _fetch_wiki()
    print(f"total jugadores unicos: {len(players)}")
    print("archivo:", OUT)
    print("extra curaciones:", len(_read_extra()))


def _fetch_wiki() -> list[dict]:
    """Descarga/lee el listado senior (cache en `argentina_senior.json`)."""
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8")).get("players", [])

    raw = urllib.request.urlopen(
        urllib.request.Request(URL, headers={"User-Agent": "LaCaprichosaBot/1.0"}),
        timeout=60,
    ).read().decode("utf-8")

    lines = raw.splitlines()
    players: list[dict] = []
    seen: set[str] = set()
    i = 0
    while i < len(lines):
        if lines[i].strip() != "|-":
            i += 1
            continue
        i += 1
        name_raw, fields, j = "", [], i
        while j < len(lines):
            ln = lines[j].strip()
            if ln == "|-":
                break
            if ln.startswith("|"):
                if not name_raw:
                    name_raw = ln[1:].strip()
                else:
                    fields.append(ln[1:].strip())
            j += 1
        i = j
        if not name_raw or len(fields) < 1:
            continue
        name = _clean_name(name_raw)
        caps = _to_int(fields[0]) if fields else None
        if not name or caps is None:
            continue
        key = name.casefold()
        if key in seen or "{" in name or "style=" in name.casefold():
            continue
        seen.add(key)
        players.append({"name": name, "caps": caps})

    players.sort(key=lambda p: p["name"].casefold())
    OUT.write_text(
        json.dumps(
            {"source": URL, "count": len(players), "players": players},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    return players


if __name__ == "__main__":
    main()
