"""Diagnostic Phase 1 — lecture seule du RAW. Cherche où pourraient manquer des lignes."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import openpyxl

raw = sorted(Path("data/raw").glob("loteriema_*_original.xlsx"))
assert len(raw) == 1, raw
ws = openpyxl.load_workbook(raw[0]).worksheets[0]
rows = list(ws.iter_rows(min_row=2, values_only=True))   # ligne Excel = index + 2

def to_int(v):
    try: return int(str(v).strip())
    except Exception: return None

def to_date(v):
    if isinstance(v, datetime): return v.date()
    try: return datetime.strptime(str(v).strip(), "%Y-%m-%d").date()
    except Exception: return None

recs = [(i + 2, to_int(r[0]), to_date(r[8]), [r[j] for j in range(1, 7)], r[7]) for i, r in enumerate(rows)]
print("Lignes lues:", len(recs), "| N illisibles:", [x[0] for x in recs if x[1] is None][:10],
      "| dates illisibles:", [x[0] for x in recs if x[2] is None][:10])

# 1. Ordre du fichier (attendu : dates strictement décroissantes)
bad = [(a[0], a[2], b[0], b[2]) for a, b in zip(recs, recs[1:]) if a[2] and b[2] and b[2] >= a[2]]
print("\n[1] Ruptures d'ordre des dates:", len(bad))
for x in bad[:20]: print("   ligne", x[0], x[1], "->", "ligne", x[2], x[3])

# 2. Dates dupliquées
dc = Counter(x[2] for x in recs if x[2])
dups = {d: c for d, c in dc.items() if c > 1}
print("\n[2] Dates dupliquées:", len(dups), "(lignes concernées:", sum(dups.values()), ")")
for d in sorted(dups)[:20]: print("  ", d, "x", dups[d], "lignes", [x[0] for x in recs if x[2] == d])

# 3. Numérotation : attendu N(suivant) = N(précédent) - 1 dans l'ordre du fichier
br = [(a, b) for a, b in zip(recs, recs[1:]) if a[1] is not None and b[1] is not None and b[1] != a[1] - 1]
print("\n[3] Ruptures de la numérotation N:", len(br))
for a, b in br[:40]: print(f"   ligne {a[0]} N={a[1]} ({a[2]})  ->  ligne {b[0]} N={b[1]} ({b[2]})")

# 4. Par année civile : lignes vs plage de N
by = {}
for row, n, d, _, _ in recs:
    if d: by.setdefault(d.year, []).append((row, n, d))
print("\n[4] Par année : lignes | N_min | N_max | attendues(max-min+1) | N manquants | N dupliqués")
for y in sorted(by):
    ns = [n for _, n, _ in by[y] if n is not None]
    if not ns: continue
    s = set(ns); miss = [k for k in range(min(ns), max(ns) + 1) if k not in s]
    dp = [k for k, v in Counter(ns).items() if v > 1]
    print(f"   {y}: {len(by[y]):4d} | {min(ns):4d} | {max(ns):4d} | {max(ns)-min(ns)+1:4d} | {len(miss)} {miss[:8]} | {len(dp)} {dp[:8]}")

# 5. Calendrier : jours de la semaine par année, écarts > 7 jours
jours = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
print("\n[5] Jours de tirage par année:")
for y in sorted(by):
    print("  ", y, dict(Counter(jours[d.weekday()] for _, _, d in by[y])))
ud = sorted(set(x[2] for x in recs if x[2]))
gaps = [(a, b, (b - a).days) for a, b in zip(ud, ud[1:]) if (b - a).days > 7]
print("   Écarts > 7 jours:", len(gaps))
for a, b, g in gaps[:30]: print("     ", a, "->", b, f"({g} j)")

# 6. Lignes atypiques (comptage/identification seulement, aucune suppression)
zero = [x[0] for x in recs if all(v == 0 for v in x[3]) and x[4] == 0]
out = [x[0] for x in recs if any((not isinstance(v, int)) or v < 1 or v > 49 for v in x[3] + [x[4]])]
print("\n[6] Lignes tout à zéro (0 0 0 0 0 0 + 0):", len(zero), zero[:10])
print("    Lignes avec une valeur hors [1,49] (zéros inclus):", len(out), out[:20])
