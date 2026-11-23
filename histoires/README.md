# Askan Histoires (prototype)

Second compte TikTok, séparé d'AskanInfo : de grands récits de l'histoire du Sénégal,
en vidéo verticale (photos d'archives libres avec zoom lent, voix de synthèse,
sous-titres). Ce dossier n'est pas publié sur askaninfo.com.

## Décisions du propriétaire
- Nom du compte : **Askan Histoires**.
- Série de départ : **les grandes affaires du passé** (affaires anciennes, jugées ou très
  documentées). D'autres séries possibles : contes du Sénégal, proverbes wolof, « le saviez-vous ».
- Images : **photos d'archives libres** (Wikimedia Commons, domaine public ou CC BY / CC BY-SA),
  crédit affiché à l'écran et repris dans la légende ; cartes de dates fabriquées sinon.
- Premier épisode prototype : la crise de décembre 1962 (Mamadou Dia), 1 min 25.
- Retour du propriétaire : l'histoire de Mamadou Dia peut être **plus longue et découpée en
  plusieurs parties** (jeunesse, ascension, crise, prison, après). D'où la série en 3 parties
  `dia-1.yaml` (1910-1962), `dia-2.yaml` (crise de 1962, ancien `episode-1962.yaml`),
  `dia-3.yaml` (Kédougou, libération, fin de vie).

## Règles
- Uniquement des faits vérifiés et recoupés (au moins deux sources sérieuses) ; une
  divergence entre sources : on laisse le détail de côté ou on la signale.
- Ton neutre ; quand l'histoire reste débattue, on présente les deux lectures.
- **Jamais d'image générée par IA d'une personne réelle**, ni de guide religieux.
- On ne nomme pas les victimes de drames ; prudence avec les familles.
- Pas de « cas » au sens buzz/rumeur : seulement des affaires anciennes et établies.
- Étiquette « Contenu généré par l'IA » cochée à la publication (voix de synthèse).

## Fabriquer l'épisode
```
python histoires/histoire.py <voix Piper fr_FR-siwis-medium.onnx> histoires/dia-1.yaml dia-1.mp4
```
La voix Piper se télécharge comme dans `.github/workflows/podcast.yml`.
Photos et crédits : `histoires/photos/` et `histoires/photos/credits.json`. Une photo absente
est remplacée par un fond uni (message à l'écran). Ne pas ranger la voix dans le dépôt.

Format d'un épisode (YAML) : `titre`, `serie`, `partie`, `sources`, puis `plans` ; chaque plan
a une `voix` et, au choix, `photo`, `haut` (petit titre), `date` (grande date), `grand`
(grand texte), `sans_sous_titres`.

## Réseau
Wikimedia Commons (`commons.wikimedia.org`, `upload.wikimedia.org`) et `fr.wikipedia.org`
sont autorisés dans l'environnement ; Wikimedia limite vite les requêtes (erreur 429) :
ne pas insister, espacer les appels, s'identifier avec un User-Agent générique.

## Suite prévue
1. Retours du propriétaire sur le prototype (durée, style, voix).
2. Création du compte TikTok « Askan Histoires » par le propriétaire (adresse e-mail dédiée).
3. Automatisation (épisodes dans un dossier, fabrication par GitHub Actions, page de
   téléchargement avec légende et crédits), puis liste d'épisodes : procès Habré, Joola,
   Me Babacar Sèye, Gorée, Lat Dior…
