#!/usr/bin/env bash
# Prépare (ou refait) le dépôt PUBLIC à partir du DERNIER COMMIT du dépôt de travail. Ne pousse RIEN sur GitHub.
#   bash scripts/publish_public_repo.sh [DOSSIER_PUBLIC]      (par défaut : ~/loto-public)
# Ce qui ne part jamais dans le dépôt public : la base de travail, le fichier source xlsx, les fichiers dérivés
# volumineux (data/analytic, data/features) et tes prédictions figées (data/predictions/*.json).
set -eu

WORK="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PUBLIC="${1:-$HOME/loto-public}"

cd "$WORK"
if [ -n "$(git status --porcelain)" ]; then
  echo "Des modifications ne sont pas commitées dans $WORK."
  echo "Commite-les d'abord :  git add -A && git commit -m \"Message\""
  exit 1
fi

NAME="${PUBLIC_NAME:-}"
EMAIL="${PUBLIC_EMAIL:-}"
REMOTE="${PUBLIC_REMOTE:-}"
if [ -d "$PUBLIC/.git" ]; then
  [ -n "$NAME" ] || NAME="$(git -C "$PUBLIC" config user.name || true)"
  [ -n "$EMAIL" ] || EMAIL="$(git -C "$PUBLIC" config user.email || true)"
  [ -n "$REMOTE" ] || REMOTE="$(git -C "$PUBLIC" remote get-url origin 2>/dev/null || true)"
fi
if [ -z "$NAME" ] || [ -z "$EMAIL" ]; then
  echo "Identité des commits inconnue. Relance avec :"
  echo "  PUBLIC_NAME=\"Prénom Nom\" PUBLIC_EMAIL=\"adresse\" bash scripts/publish_public_repo.sh"
  exit 1
fi

if [ -e "$PUBLIC" ]; then
  OLD="${PUBLIC}_ancien_$(date +%Y%m%d_%H%M%S)"
  mv "$PUBLIC" "$OLD"
  echo "Ancien dossier public conservé : $OLD"
fi
mkdir -p "$PUBLIC"
git archive HEAD | tar -x -C "$PUBLIC"
cd "$PUBLIC"

rm -f data/raw/*.xlsx data/predictions/*.json
rm -rf data/analytic data/features
cat >> .gitignore <<'EOF'
data/raw/*.xlsx
data/raw/nouveaux_tirages_log.csv
*.sqlite
.streamlit/
.DS_Store
EOF

git init -q -b main
git config user.name "$NAME"
git config user.email "$EMAIL"
git add -A
git commit -q -m "Initial commit"
if [ -n "$REMOTE" ]; then
  git remote add origin "$REMOTE"
fi

echo
echo "=== Dépôt public prêt : $PUBLIC ==="
echo "Fichiers : $(git ls-files | wc -l), taille : $(du -sh --exclude=.git . | cut -f1)"
echo "Auteur des commits : $(git log -1 --format='%an <%ae>')"
echo "Dépôt distant : ${REMOTE:-aucun (git remote add origin ADRESSE)}"
echo
echo "Contrôle des chemins personnels (doit rester vide) :"
git grep -I -n "/home/" | head -20 || true
echo
echo "Si tout est bon, envoi (le jeton d'accès sera demandé) :"
echo "  cd $PUBLIC && git push -u origin main"
echo "Si le dépôt GitHub contenait déjà un ancien historique, l'envoi sera refusé : dis-le, on le traitera."
