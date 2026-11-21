"""Lance le tableau de bord : python -m loto_research.dashboard [--writable] [--db CHEMIN] [--game NOM] [--port 8501]
Par défaut la base est ouverte en lecture seule. Avec --writable, les pages Tirages et Prédictions permettent d'ajouter
des tirages, de les corriger et de figer une prédiction, avec exactement les mêmes garde-fous que la ligne de commande.
Le serveur n'écoute que sur 127.0.0.1 (cette machine)."""
import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Tableau de bord d'audit statistique.")
    ap.add_argument("--db", default="data/loto.sqlite")
    ap.add_argument("--game", default="Loto Maroc 6/49")
    ap.add_argument("--port", default="8501")
    ap.add_argument("--writable", action="store_true",
                    help="active l'ajout de tirages, les corrections et le gel de prédictions (local uniquement)")
    args = ap.parse_args()

    for module in ("streamlit", "plotly"):
        if importlib.util.find_spec(module) is None:
            sys.exit(f"Le module {module!r} est requis : pip install streamlit plotly")
    if not Path(args.db).exists():
        sys.exit(f"Base introuvable : {args.db} (lance la commande depuis la racine du dépôt).")

    env = dict(os.environ, LOTO_DB=str(Path(args.db).resolve()), LOTO_GAME=args.game,
               LOTO_WRITABLE="1" if args.writable else "0")
    if args.writable:
        print("MODE ÉCRITURE ACTIVÉ : ajout de tirages, corrections et gel de prédictions possibles.", file=sys.stderr)
    app = Path(__file__).with_name("app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(args.port),
           "--server.address", "127.0.0.1", "--browser.gatherUsageStats", "false"]
    sys.exit(subprocess.call(cmd, env=env))


if __name__ == "__main__":
    main()
