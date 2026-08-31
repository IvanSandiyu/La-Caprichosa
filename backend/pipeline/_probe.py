import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from app.db import get_conn
from pipeline.cantera_wikidata import clean_club_name, build_club_index, resolve_club, MATCH_RE

conn = get_conn()
idx_norm, _ = build_club_index(conn)

cats = [
    "Categoría:Futbolistas de las inferiores del Club Atlético Boca Juniors",
    "Categoría:Futbolistas de las inferiores de la Asociación Atlética Argentinos Juniors",
    "Categoría:Futbolistas de las inferiores del Club Atlético Newell's Old Boys",
    "Categoría:Futbolistas de las inferiores del Club Atlético Independiente",
    "Categoría:Futbolistas de las inferiores del Club Atlético River Plate",
    "Categoría:Futbolistas de las inferiores del Club Atlético San Lorenzo de Almagro",
    "Categoría:Futbolistas de las inferiores del Racing Club",
    "Categoría:Futbolistas de las inferiores del Club Atlético Rosario Central",
    "Categoría:Futbolistas de las inferiores del Club de Gimnasia y Esgrima La Plata",
    "Categoría:Futbolistas de las inferiores del Club Estudiantes de La Plata",
    "Categoría:Futbolistas de las inferiores del Club Atlético Vélez Sarsfield",
    "Categoría:Futbolistas de las inferiores de la Asociación Atlética Huracán",
    "Categoría:Futbolistas de las inferiores del Club Atlético Banfield",
    "Categoría:Futbolistas de las inferiores del Club Atlético Lanús",
    "Categoría:Futbolistas de las inferiores del Club Atlético Argentino de Quilmes",
    "Categoría:Futbolistas de las inferiores del Club Atlético Platense",
    "Categoría:Futbolistas de las inferiores del Barcelona",
    "Categoría:Futbolistas de las inferiores del Club Atlético Tigre",
    "Categoría:Futbolistas de las inferiores de Velez Sarsfield",
    "Categoría:Futbolistas de las inferiores del Club Atletico Talleres (Cordoba)",
]
for c in cats:
    m = MATCH_RE.match(c)
    grp = m.group(1) if m else None
    cleaned = clean_club_name(grp) if grp else None
    cid = resolve_club(idx_norm, cleaned) if cleaned else None
    name = conn.execute("SELECT name FROM clubs WHERE club_id=?", (cid,)).fetchone()
    print(f"  {'NO-MATCH' if not grp else grp[:55]:55s} -> {str(cleaned)[:25]:25s} -> {name[0] if name else '???'}")
