# AskanInfo

Site d'informations sur le Sénégal et les Sénégalais, mis à jour automatiquement.

## Comment ça marche

| Étape | Qui | Quand |
|---|---|---|
| **Veille** : lecture des flux RSS des médias (`medias.yaml`) → `data/items.json` | GitHub Actions (`scripts/fetch.py`) | toutes les heures |
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

## Administrer le site : Pages CMS

Interface web gratuite : **https://app.pagescms.org** (connexion avec le compte
GitHub, puis choisir le dépôt AskanInfo). Configuration : `.pages.yml`.

| Menu | Pour… |
|---|---|
| **Mes articles** | écrire un article (titre, chapô, rubrique, texte, photos) ; cocher « Brouillon » pour ne pas le publier encore |
| **Synthèses** | corriger ou supprimer une synthèse écrite par l'agent |
| **Médias suivis** | ajouter, désactiver ou retirer une source |
| **Réglages** | slogan, e-mail de contact, code GoatCounter (statistiques) |

Chaque enregistrement met le site à jour en 1 à 2 minutes. Les photos vont
dans `static/images/`.

## Statistiques : GoatCounter

Créer un compte gratuit sur https://www.goatcounter.com (par ex. le code
« askaninfo »), puis saisir ce code dans **Réglages → Code GoatCounter**.
Les statistiques se consultent ensuite sur https://askaninfo.goatcounter.com.

## Modèles

`modeles/` contient les modèles d'article, de synthèse et de script de
podcast (utilisés par l'agent ; Pages CMS fournit ses propres formulaires).

## Tester sur son ordinateur

```bash
pip install -r requirements.txt
python scripts/fetch.py
python scripts/build.py   # le site est dans _site/
```
