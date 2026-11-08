"""Télécharge dans cache-podcast/ les MP3 des épisodes récents (depuis la
release GitHub « podcast »), pour que scripts/build.py les publie sur
askaninfo.com. Les fichiers déjà présents (cache) ne sont pas retéléchargés."""

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache-podcast"
NOMBRE = 14

metas = sorted((ROOT / "data" / "podcast").glob("*.json"), reverse=True)[:NOMBRE]
CACHE.mkdir(exist_ok=True)
for m in metas:
    audio = json.loads(m.read_text(encoding="utf-8"))
    cible = CACHE / Path(audio["url"]).name
    if cible.exists() and cible.stat().st_size == audio["taille"]:
        continue
    try:
        req = urllib.request.Request(audio["url"], headers={"User-Agent": "AskanInfoBot/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            cible.write_bytes(r.read())
        print(f"  {cible.name} : récupéré ({cible.stat().st_size} octets)")
    except Exception as e:  # le site reste publié, avec le lien GitHub en secours
        print(f"  ! {cible.name} : {e}", file=sys.stderr)
