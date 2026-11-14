"""Cherche sur Wikimedia Commons des photos libres de droits pour les sujets de
images_recherche.yaml et dépose 4 candidates par sujet dans candidats-images/
(image en 1280 px + auteur, licence, page d'origine dans index.json).

Lancé à la main par le workflow « Images candidates » : rien n'est ajouté au site,
les candidates sont examinées avant d'être choisies.
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SORTIE = ROOT / "candidats-images"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "AskanInfoBot/1.0 (https://askaninfo.com; contact@askaninfo.com)"
LICENCES = re.compile(r"^(cc0|public domain|pd\b|cc by(-sa)? [1-4]\.\d)", re.I)   # réutilisation libre avec crédit
PAR_SUJET = 4
PAUSE = 2   # secondes entre deux requêtes


def requete(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def texte(valeur):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", valeur or "")).strip()


def chercher(recherche):
    params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
              "gsrsearch": f"{recherche} filetype:bitmap", "gsrlimit": 20, "prop": "imageinfo",
              "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1280}
    pages = json.loads(requete(API + "?" + urllib.parse.urlencode(params))).get("query", {}).get("pages", {})
    resultats = []
    for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        licence = texte(meta.get("LicenseShortName", {}).get("value"))
        if info.get("mime") != "image/jpeg" or info.get("width", 0) < 1200 or info.get("width", 0) <= info.get("height", 0):
            continue
        if not LICENCES.match(licence) or not info.get("thumburl"):
            continue
        resultats.append({"titre": page["title"], "auteur": texte(meta.get("Artist", {}).get("value"))[:120],
                          "licence": licence, "page": info.get("descriptionurl", ""), "image": info["thumburl"],
                          "description": texte(meta.get("ImageDescription", {}).get("value"))[:200]})
    return resultats[:PAR_SUJET]


def main():
    recherches = (yaml.safe_load((ROOT / "images_recherche.yaml").read_text(encoding="utf-8")) or {}).get("recherches") or {}
    SORTIE.mkdir(exist_ok=True)
    index = {}
    for sujet, recherche in recherches.items():
        if not re.fullmatch(r"[a-z0-9-]{2,40}", str(sujet)):
            continue
        try:
            trouvees = chercher(str(recherche))
        except Exception as e:
            print(f"  ! {sujet} : recherche impossible ({e})", file=sys.stderr)
            trouvees = []
        time.sleep(PAUSE)
        index[sujet] = []
        for n, image in enumerate(trouvees, 1):
            fichier = f"{sujet}-{n}.jpg"
            try:
                (SORTIE / fichier).write_bytes(requete(image["image"]))
            except Exception as e:
                print(f"  ! {fichier} : téléchargement impossible ({e})", file=sys.stderr)
                continue
            time.sleep(PAUSE)
            index[sujet].append(dict(image, fichier=fichier))
        print(f"  {sujet} : {len(index[sujet])} image(s)")
    (SORTIE / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
