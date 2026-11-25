#!/usr/bin/env bash
# Publie le dépôt de travail vers le dépôt PUBLIC. Ne pousse RIEN sur GitHub.
#   bash scripts/publish_public_repo.sh              -> MET À JOUR ~/loto-public par un nouveau commit (historique conservé)
#   PUBLIC_MESSAGE="Texte" bash scripts/publish_public_repo.sh   -> même chose, avec le message de ton choix
#   FRESH=1 bash scripts/publish_public_repo.sh      -> REFAIT un dépôt neuf (historique réécrit : à éviter une fois publié)
# Ne part jamais dans le dépôt public : base de travail, fichier source xlsx, fichiers dérivés volumineux,
# prédictions figées, réglages de l'éditeur (.vscode).
set -eu

WORK="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PUBLIC="${1:-$HOME/loto-public}"
MESSAGE="${PUBLIC_MESSAGE:-Mise à jour}"
FRESH="${FRESH:-0}"

cd "$WORK"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "Des modifications suivies ne sont pas commitées dans $WORK."
  echo "Commite-les d'abord :  git add -A && git commit -m \"Message\""
  exit 1
fi

clean_tree() {
  rm -f "$1"/data/raw/*.xlsx "$1"/data/predictions/*.json
  rm -rf "$1"/data/analytic "$1"/data/features "$1"/.vscode
}

ensure_ignore() {
  for line in 'data/raw/*.xlsx' 'data/raw/nouveaux_tirages_log.csv' '*.sqlite' '.streamlit/' '.vscode/' '.DS_Store'; do
    grep -qxF "$line" "$1/.gitignore" 2>/dev/null || echo "$line" >> "$1/.gitignore"
  done
}

if [ "$FRESH" != "1" ] && [ -d "$PUBLIC/.git" ] && git -C "$PUBLIC" rev-parse HEAD >/dev/null 2>&1; then
  # ---- Mode mise à jour : nouveau commit au-dessus de l'historique existant
  command -v rsync >/dev/null || { echo "rsync est nécessaire :  sudo apt install rsync"; exit 1; }
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  git archive HEAD | tar -x -C "$TMP"
  clean_tree "$TMP"
  ensure_ignore "$TMP"
  rsync -a --delete --exclude='.git/' "$TMP"/ "$PUBLIC"/
  cd "$PUBLIC"
  git add -A
  if git diff --cached --quiet; then
    echo "Rien à publier : le dépôt public est déjà à jour."
    exit 0
  fi
  git commit -q -m "$MESSAGE"
  echo "=== Mise à jour prête dans $PUBLIC ==="
  git diff --stat HEAD~1 HEAD | tail -n 25
else
  # ---- Mode dépôt neuf (historique réécrit)
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
    echo "  PUBLIC_NAME=\"Prénom Nom\" PUBLIC_EMAIL=\"adresse\" FRESH=1 bash scripts/publish_public_repo.sh"
    exit 1
  fi
  if [ -e "$PUBLIC" ]; then
    OLD="${PUBLIC}_ancien_$(date +%Y%m%d_%H%M%S)"
    mv "$PUBLIC" "$OLD"
    echo "Ancien dossier public conservé : $OLD"
  fi
  mkdir -p "$PUBLIC"
  git archive HEAD | tar -x -C "$PUBLIC"
  clean_tree "$PUBLIC"
  ensure_ignore "$PUBLIC"
  cd "$PUBLIC"
  git init -q -b main
  git config user.name "$NAME"
  git config user.email "$EMAIL"
  git add -A
  git commit -q -m "Initial commit"
  if [ -n "$REMOTE" ]; then
    git remote add origin "$REMOTE"
  fi
  echo "=== Dépôt neuf prêt dans $PUBLIC (historique réécrit : l'envoi demandera --force-with-lease) ==="
fi

echo
echo "Fichiers : $(git ls-files | wc -l), auteur du dernier commit : $(git log -1 --format='%an <%ae>')"
echo "Contrôle des chemins personnels (doit rester vide) :"
git grep -I -n "/home/" -- . ':!scripts/publish_public_repo.sh' | head -20 || true
echo
echo "Si tout est bon :  cd $PUBLIC && git push"
