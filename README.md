# AskanInfo

Site d'informations sur le Sénégal et les Sénégalais, mis à jour automatiquement.

## Comment ça marche

| Étape | Qui | Quand |
|---|---|---|
| **Veille** : lecture des flux RSS des médias (`sources.yaml`) → `data/items.json` | GitHub Actions (`scripts/fetch.py`) | toutes les heures |
| **Site** : construction et mise en ligne sur GitHub Pages | GitHub Actions (`scripts/build.py`) | toutes les heures et à chaque modification |
| **Synthèses** : courts articles originaux qui citent leurs sources → `content/syntheses/` | Claude Code (tâche planifiée, consignes dans `CLAUDE.md`), sur une branche `claude/…` ; publiées par la mise à jour horaire (`scripts/integrer_syntheses.sh`) si la branche ne modifie que des synthèses | 2 fois par jour |
| **Vos articles** → `content/articles/` | Vous | quand vous voulez |

Le fil n'affiche que les **titres** des articles, avec un lien vers le média
d'origine (comme Google Actualités). Les synthèses sont rédigées avec d'autres
mots, citent toutes leurs sources et passent un contrôle anti-copie
(`scripts/check_overlap.py`).

## Mise en route (une seule fois)

1. Fusionner cette branche dans `main`.
2. Sur GitHub : **Settings → Pages → Source : « GitHub Actions »**.
3. Onglet **Actions** → « Mise à jour du site » → **Run workflow**.
4. Le site est en ligne à l'adresse `https://askaninfo.com` (domaine acheté chez OVHcloud).

GitHub Pages est gratuit si le dépôt est **public**. Pour un dépôt privé, il faut un
abonnement GitHub payant.

## Écrire un article

Dans `content/articles/`, copiez `_modele.md` sous un nouveau nom (par exemple
`2026-11-07-mon-article.md`), écrivez, enregistrez. Vous pouvez le faire
directement sur le site de GitHub (bouton « Add file »). Le site se met à jour
en quelques minutes.

## Ajouter ou retirer une source

Modifiez `sources.yaml`. Si un média demande à être retiré, supprimez son bloc.

## Tester sur son ordinateur

```bash
pip install -r requirements.txt
python scripts/fetch.py
python scripts/build.py   # le site est dans _site/
```
