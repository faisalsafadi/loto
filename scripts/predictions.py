#!/usr/bin/env python
"""Prédictions exploratoires figées pour le PROCHAIN tirage. NON VALIDÉ : aucun modèle ne bat le hasard.

  python scripts/predictions.py next      # calcule, affiche, puis fige seulement si tu tapes FIGER
  python scripts/predictions.py status    # prédictions figées, intégrité, évaluation cumulée
"""
import argparse
import subprocess
import sys

from loto_research.db.core import ValidationError, connect, init_db
from loto_research.prediction import engine, store, trusted_time


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def open_db(args):
    conn = connect(args.db)
    init_db(conn)
    store.ensure_tables(conn)
    game = conn.execute("SELECT * FROM games WHERE name = ?", (args.game,)).fetchone()
    if game is None:
        sys.exit(f"Jeu introuvable : {args.game!r}")
    return conn, game


def cmd_next(args):
    conn, game = open_db(args)
    print(store.NOTE)
    print("Calcul en cours (environ 20 secondes)...")
    try:
        clock = trusted_time.reference_now()
        payload = store.prepare_prediction(conn, game["id"], target_date=args.target_date, now=clock["now"],
                                           clock=trusted_time.clock_record(clock), code_commit=git_commit(),
                                           allow_stale=args.allow_stale)
    except ValidationError as e:
        sys.exit(f"Refusé : {e}")
    names = {"frequency": "Variante A (fréquence)", "logistic": "Variante B (logistique)",
             "uniform_random": "Variante C (contrôle aléatoire)"}
    print(f"\nProchain tirage : {payload['target_date']} ({payload['n_draws']} tirages en base, dernier le "
          f"{payload['last_draw_date']})")
    for note in payload["notes"]:
        print(f"NOTE : {note}")
    for name in ("frequency", "logistic", "uniform_random"):
        m = payload["models"][name]
        comp = m.get("complementary")
        print(f"{names[name]:<34} {m['variant_numbers']}" + (f"  + complémentaire {comp['variant']}" if comp else ""))
    print("\nCes combinaisons n'ont aucun avantage démontré. Elles servent à mesurer, après le tirage, si un modèle "
          "fait mieux que le hasard.")
    if not args.yes:
        answer = input("\nTape FIGER pour figer cette prédiction (définitif) : ")
        if answer.strip() != "FIGER":
            sys.exit("Annulé : rien n'est écrit.")
    freeze_clock = trusted_time.reference_now()
    try:
        res = store.freeze_prediction(conn, game["id"], payload, out_dir=args.out_dir, now=freeze_clock["now"],
                                      clock=trusted_time.clock_record(freeze_clock))
    except ValidationError as e:
        sys.exit(f"Refusé : {e}")
    print(f"\nPrédiction figée (n° {res['id']}).\nFichier : {res['path']}\nSHA256 : {res['sha256']}")
    print(f"Heure de référence du gel : {freeze_clock['source']}")
    print("\nFacultatif : pour prouver à d'autres que la prédiction précède le tirage, dépose ce fichier sur ton dépôt "
          "GitHub avant le tirage. Pour un usage personnel, rien à faire.")


def cmd_status(args):
    conn, game = open_db(args)
    rows = store.list_frozen(conn, game["id"])
    if not rows:
        print("Aucune prédiction figée.")
        return
    problems = store.verify_frozen(conn, game["id"], out_dir=args.out_dir)
    ev, pending = store.evaluations(conn, game["id"])
    print(store.NOTE)
    print(f"\n{len(rows)} prédiction(s) figée(s), {len(pending)} en attente de leur tirage {pending}.")
    print("Intégrité : " + ("OK (toutes les empreintes correspondent)" if not problems else "ANOMALIES :"))
    for p in problems:
        print("  - " + p)
    for r in rows:
        print(f"  {r['target_date']}  figée le {r['frozen_at']}  SHA256 {r['payload_sha256'][:12]}")
    summ = store.cumulative_summary(ev)
    if summ.empty:
        print("\nAucun tirage encore évalué.")
        return
    print("\nÉvaluation cumulée (DESCRIPTIVE ; écart de log loss au hasard : négatif = mieux que le hasard) :")
    print(summ.round(6).to_string(index=False))
    print(f"\nH010 : {int(summ['n'].max())} / {store.H010_N_STAR} prédictions évaluées. Le test confirmatoire "
          f"ne se lit qu'à {store.H010_N_STAR}.")
    csumm = store.complementary_summary(ev)
    n_comp = int(csumm["n"].max()) if not csumm.empty else 0
    print(f"H011 (complémentaire) : {n_comp} / {store.H011_N_STAR} prédictions évaluées avec complémentaire.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/loto.sqlite")
    ap.add_argument("--game", default="Loto Maroc 6/49")
    ap.add_argument("--out-dir", default="data/predictions")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next", help="calculer puis figer la prédiction du prochain tirage")
    n.add_argument("--target-date", default=None, help="AAAA-MM-JJ ; par défaut : prochain jour de tirage attendu")
    n.add_argument("--allow-stale", action="store_true", help="forcer malgré un tirage manquant en base")
    n.add_argument("--yes", action="store_true", help="ne pas demander la confirmation FIGER")
    n.set_defaults(func=cmd_next)
    s = sub.add_parser("status", help="état des prédictions figées")
    s.set_defaults(func=cmd_status)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
