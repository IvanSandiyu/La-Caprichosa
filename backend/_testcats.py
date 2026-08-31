from datetime import date
from collections import Counter
from app.impostor import generate_impostor_puzzle

seen = Counter()
examples = {}
all_numeric_ok = True
for d in range(1, 31):
    for diff in ["facil", "normal", "dificil"]:
        p = generate_impostor_puzzle(date(2026, 8, d), diff)
        if p:
            seen[p.category_type] += 1
            examples.setdefault(p.category_type, f"{p.category} / {diff}")
            # verificar que ninguna categoría contenga numeros corruptos de país
            if p.category_type == "nationality":
                for c in ["3584", "15232", "3700", "5233", "3581", "3504", "15738"]:
                    if c in p.category:
                        all_numeric_ok = False

print("=== categorías (30 días x 3 dificultades = 90 puzzles) ===")
for t, n in sorted(seen.items()):
    print(f"  {t:15s} x{n:3d}   ej: {examples[t]}")
print("nationality sin corruptos:", all_numeric_ok)

print("\n=== determinismo por tipo ===")
for t in seen:
    for d in range(1, 31):
        p1 = generate_impostor_puzzle(date(2026, 8, d), "normal")
        if p1 and p1.category_type == t:
            p2 = generate_impostor_puzzle(date(2026, 8, d), "normal")
            ok = [x.id for x in p1.players] == [x.id for x in p2.players] and p1.category == p2.category
            print(f"  {t}: deterministic={ok}")
            break
