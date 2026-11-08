#!/usr/bin/env bash
# Intègre dans main les synthèses poussées par l'agent de rédaction sur des
# branches « claude/… ». Exécuté depuis main par le workflow horaire : l'agent
# ne peut donc pas modifier ce contrôle.
# Une branche n'est intégrée que si elle ne modifie QUE des fichiers
# content/syntheses/*.md ou content/podcast/*.md (scripts de la revue de presse). Sinon elle est ignorée (relecture humaine).
set -euo pipefail

PUBLIES=data/publies.txt   # tout ce qui a déjà été publié depuis une branche

git fetch -q origin '+refs/heads/claude/*:refs/remotes/origin/claude/*' || true

for branche in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin/claude/); do
  # rien de nouveau par rapport à main ?
  if [ -z "$(git rev-list HEAD.."$branche")" ]; then
    continue
  fi
  fichiers=$(git diff --name-only HEAD..."$branche")
  if [ -z "$fichiers" ]; then
    continue
  fi
  if echo "$fichiers" | grep -qvE '^content/(syntheses|podcast)/[A-Za-z0-9][A-Za-z0-9._-]*\.md$'; then
    echo "::notice::$branche modifie d'autres fichiers que des synthèses ou scripts de podcast : ignorée (relecture humaine nécessaire)."
    continue
  fi
  # seulement les synthèses pas encore publiées (on ne modifie jamais une
  # synthèse déjà en ligne) et encore présentes dans la branche
  nouveaux=""
  for f in $fichiers; do
    # déjà publié un jour (puis peut-être supprimé à la main) : on ne le reprend jamais
    if grep -qxF "$f" "$PUBLIES" 2>/dev/null; then
      continue
    fi
    if [ ! -e "$f" ] && git cat-file -e "$branche:$f" 2>/dev/null; then
      nouveaux="$nouveaux $f"
    fi
  done
  if [ -z "$nouveaux" ]; then
    continue
  fi
  echo "Intégration des synthèses de $branche :$nouveaux"
  # on ne prend que ces fichiers, jamais le reste de l'historique
  git checkout "$branche" -- $nouveaux
  printf '%s\n' $nouveaux >> "$PUBLIES"
  git add -- "$PUBLIES"
  git commit -q -m "Publication des synthèses ($branche)"
done
