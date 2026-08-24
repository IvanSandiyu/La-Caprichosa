"""Resuelve los QIDs de Wikidata para los 32 clubes usando sitelinks
de Wikipedia en español (pageprops -> wikibase_item), batcheado."""

import json
import sqlite3
from pathlib import Path

import requests

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "futbol_argentino.db"
OUT_PATH = Path(__file__).resolve().parent / "wikidata_clubs.json"
HEADERS = {"User-Agent": "LaCaprichosa/1.0 (trivia game; local use)"}

# título canónico en es.wikipedia por nombre visible en nuestra DB
WIKI_TITLES = {
    "Aldosivi": "Club Atlético Aldosivi",
    "Argentinos Juniors": "Asociación Atlética Argentinos Juniors",
    "Atlético Tucumán": "Club Atlético Tucumán",
    "Banfield": "Club Atlético Banfield",
    "Barracas Central": "Club Atlético Barracas Central",
    "Belgrano": "Club Atlético Belgrano",
    "Boca Juniors": "Club Atlético Boca Juniors",
    "Central Córdoba (SE)": "Club Atlético Central Córdoba (Santiago del Estero)",
    "Defensa y Justicia": "Club Social y Deportivo Defensa y Justicia",
    "Deportivo Riestra": "Deportivo Riestra",
    "Estudiantes de BA": "Estudiantes de La Plata",
    "Estudiantes de La Plata": "Estudiantes de La Plata",
    "Gimnasia (LP)": "Club de Gimnasia y Esgrima La Plata",
    "Gimnasia y Esgrima de Mendoza": "Gimnasia y Esgrima de Mendoza",
    "Godoy Cruz": "Club Deportivo Godoy Cruz Antonio Tomba",
    "Huracán": "Club Atlético Huracán",
    "Indep. Rivadavia": "Club Sportivo Independiente Rivadavia",
    "Independiente": "Club Atlético Independiente",
    "Instituto (CBA)": "Instituto Atlético Central Córdoba",
    "Lanús": "Club Atlético Lanús",
    "Newell's Old Boys": "Newell's Old Boys",
    "Platense": "Club Atlético Platense",
    "Racing Club": "Racing Club",
    "River Plate": "Club Atlético River Plate",
    "Rosario Central": "Club Atlético Rosario Central",
    "San Lorenzo": "Club Atlético San Lorenzo de Almagro",
    "San Martín (SJ)": "San Martín de San Juan",
    "Sarmiento (Junín)": "Club Atlético Sarmiento (Junín)",
    "Talleres": "Club Atlético Talleres (Córdoba)",
    "Tigre": "Club Atlético Tigre",
    "Unión (SF)": "Club Atlético Unión",
    "Vélez Sársfield": "Club Atlético Vélez Sarsfield",
}


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    clubs = [r[0] for r in conn.execute("SELECT name FROM clubs ORDER BY name")]
    conn.close()

    missing_titles = [c for c in clubs if c not in WIKI_TITLES]
    if missing_titles:
        raise SystemExit(f"Faltan títulos wiki para: {missing_titles}")

    titles = [WIKI_TITLES[c] for c in clubs]
    resp = requests.get(
        "https://es.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "titles": "|".join(titles),
            "prop": "pageprops",
            "ppprop": "wikibase_item",
            "redirects": 1,
            "format": "json",
        },
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # normaliza redirecciones: title canónico -> QID
    qid_by_title: dict[str, str] = {}
    resolved = data.get("query", {})
    for page in resolved.get("pages", {}).values():
        qid = (page.get("pageprops") or {}).get("wikibase_item")
        if qid:
            qid_by_title[page["title"]] = qid

    # mapear redirecciones resueltas
    redirect_map: dict[str, str] = {}
    for r in resolved.get("redirects", []):
        redirect_map[r["from"]] = r["to"]

    mapping: dict[str, str] = {}
    unresolved: list[str] = []
    for club in clubs:
        title = WIKI_TITLES[club]
        final_title = redirect_map.get(title, title)
        # puede haber cadenas de redirecciones
        final_title = redirect_map.get(final_title, final_title)
        qid = qid_by_title.get(final_title) or qid_by_title.get(title)
        if qid:
            mapping[club] = qid
        else:
            unresolved.append(f"{club} ({final_title})")

    OUT_PATH.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{len(mapping)}/{len(clubs)} clubes mapeados -> {OUT_PATH.name}")
    if unresolved:
        print("SIN RESOLVER:")
        for u in unresolved:
            print(f"  {u}")


if __name__ == "__main__":
    main()
