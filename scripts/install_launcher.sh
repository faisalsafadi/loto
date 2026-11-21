#!/usr/bin/env bash
# Installe l'icône « Loto » (menu des applications et bureau) pour lancer le logiciel d'un clic.
# À lancer une seule fois depuis le dossier du dépôt :  bash scripts/install_launcher.sh
set -eu

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
APPS="$HOME/.local/share/applications"
mkdir -p "$APPS"

cat > "$APPS/loto.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Loto
GenericName=Audit statistique du Loto
Comment=Tirages, analyses et prédictions exploratoires
Exec=bash "$ROOT/scripts/launch_loto.sh"
Icon=$ROOT/assets/loto.svg
Terminal=false
Categories=Education;Science;
StartupNotify=true
EOF
chmod +x "$APPS/loto.desktop"

if [ -d "$DESKTOP_DIR" ]; then
  cp "$APPS/loto.desktop" "$DESKTOP_DIR/Loto.desktop"
  chmod +x "$DESKTOP_DIR/Loto.desktop"
  gio set "$DESKTOP_DIR/Loto.desktop" metadata::trusted true 2>/dev/null || true
fi

echo "Icône installée : cherche « Loto » dans le menu des applications, ou sur le bureau."
echo "Si le bureau demande une autorisation : clic droit sur l'icône, puis « Autoriser le lancement »."
