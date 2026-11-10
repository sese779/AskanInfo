"""Application web installable (PWA) : icônes, manifeste, service worker
(lecture hors connexion des derniers articles) et page hors ligne."""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
POLICE = str(ROOT / "assets" / "polices" / "DejaVuSans-Bold.ttf")
VERT, JAUNE, ROUGE, BLANC = (0, 133, 63), (253, 239, 66), (227, 27, 35), (255, 255, 255)
PAGES_HORS_LIGNE = 15   # derniers articles enregistrés pour la lecture hors connexion


def icone(taille, chemin, masquable=False):
    """Carré vert, « A » blanc + « i » jaune ; version « masquable » avec marge."""
    img = Image.new("RGB", (taille, taille), VERT)
    d = ImageDraw.Draw(img)
    bande = max(2, taille // 24)
    if not masquable:
        d.rectangle([0, 0, taille, bande], fill=JAUNE)
        d.rectangle([0, taille - bande, taille, taille], fill=ROUGE)
    zone = taille * (0.62 if masquable else 0.78)
    police = ImageFont.truetype(POLICE, int(zone * 0.72))
    la, li = d.textlength("A", font=police), d.textlength("i", font=police)
    x = (taille - la - li) / 2
    haut = police.getbbox("Ai")
    y = (taille - (haut[3] - haut[1])) / 2 - haut[1]
    d.text((x, y), "A", font=police, fill=BLANC)
    d.text((x + la, y), "i", font=police, fill=JAUNE)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    img.save(chemin, optimize=True)


def ecrire_pwa(out, contenus, url_site, nom_site, description):
    dossier = out / "static" / "icones"
    for t in (180, 192, 512):
        icone(t, dossier / f"icone-{t}.png")
    icone(512, dossier / "icone-masquable-512.png", masquable=True)

    manifeste = {
        "name": nom_site,
        "short_name": nom_site,
        "description": description,
        "lang": "fr",
        "start_url": "/?source=application",
        "scope": "/",
        "display": "standalone",
        "background_color": "#00853f",
        "theme_color": "#00853f",
        "icons": [
            {"src": "/static/icones/icone-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icones/icone-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/icones/icone-masquable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "Podcast", "url": "/podcast.html"},
            {"name": "Diaspora", "url": "/rubrique/diaspora.html"},
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")

    # pages enregistrées pour la lecture hors connexion
    pages = ["/", "/index.html", "/podcast.html", "/hors-ligne.html", "/static/style.css",
             "/static/app.js", "/static/icones/icone-192.png"]
    pages += [f"/article/{c['slug']}.html" for c in contenus[:PAGES_HORS_LIGNE]]
    version = hashlib.sha1("|".join(pages).encode() + (out / "index.html").read_bytes()).hexdigest()[:10]
    sw = (ROOT / "templates" / "sw.js").read_text(encoding="utf-8")
    sw = sw.replace("__VERSION__", version).replace("__PAGES__", json.dumps(pages, ensure_ascii=False))
    (out / "sw.js").write_text(sw, encoding="utf-8")
