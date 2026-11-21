#!/usr/bin/env bash
# Lance le logiciel Loto : démarre le tableau de bord en mode écriture et ouvre le navigateur.
# Appelé par l'icône « Loto » (voir scripts/install_launcher.sh). Aucune commande à taper.
set -u

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PORT=8501
URL="http://127.0.0.1:${PORT}"
LOG_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/loto"
mkdir -p "$LOG_DIR"

port_open() { (exec 3<>/dev/tcp/127.0.0.1/"$PORT") 2>/dev/null; }

# Déjà lancé : on rouvre simplement la page.
if port_open; then
  xdg-open "$URL" >/dev/null 2>&1
  exit 0
fi

cd "$ROOT" || exit 1
if [ -f ".venv/bin/activate" ]; then
  . ".venv/bin/activate"
  PY=python
else
  PY=python3
fi

# Première utilisation : crée la base à partir des tirages livrés avec le logiciel.
if [ ! -f "data/loto.sqlite" ]; then
  "$PY" -m loto_research.cli init-db >>"$LOG_DIR/init.log" 2>&1
fi

export STREAMLIT_SERVER_HEADLESS=true
nohup "$PY" -m loto_research.dashboard --writable --port "$PORT" >>"$LOG_DIR/dashboard.log" 2>&1 &
disown

for _ in $(seq 1 90); do
  if port_open; then
    xdg-open "$URL" >/dev/null 2>&1
    exit 0
  fi
  sleep 1
done

notify-send "Loto" "Le logiciel n'a pas démarré. Détails : $LOG_DIR/dashboard.log" 2>/dev/null
exit 1
