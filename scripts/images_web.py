"""Prépare les photos pour le web, au format habituel de la presse en ligne.

Pour chaque photo choisie (Pages CMS ou images.yaml), deux copies sont créées dans
_site/static/images/web/ (les originaux du dépôt ne sont jamais modifiés) :

- « pleine » : la photo entière, remise à l'endroit (orientation des téléphones),
  1200 px de large au plus, pour la page de l'article ;
- « carte » : 1200 × 675 (16:9, le format des sites de presse et des aperçus de partage).
  Si la photo est proche du 16:9, elle est simplement recadrée au centre ; sinon elle est
  posée entière sur un fond flouté tiré d'elle-même, pour ne jamais couper un visage.

Les logos (type « logo ») ne sont pas touchés.
"""

from pathlib import Path
from urllib.parse import quote, unquote

from PIL import Image, ImageFilter, ImageOps

LARGEUR = 1200
CARTE = (1200, 675)
TOLERANCE = 0.12      # écart de format accepté avant de passer au fond flouté
QUALITE = 84

_deja = {}


def _ouvrir(chemin):
    im = Image.open(chemin)
    im = ImageOps.exif_transpose(im)          # photo de téléphone remise à l'endroit
    if im.mode not in ("RGB", "L"):
        fond = Image.new("RGB", im.size, (255, 255, 255))
        im = im.convert("RGBA")
        fond.paste(im, mask=im.split()[-1])
        im = fond
    return im.convert("RGB")


def _pleine(im):
    if im.width > LARGEUR:
        im = im.resize((LARGEUR, round(im.height * LARGEUR / im.width)), Image.LANCZOS)
    return im


def _carte(im):
    l, h = CARTE
    ratio, cible = im.width / im.height, l / h
    if abs(ratio - cible) / cible <= TOLERANCE:
        return ImageOps.fit(im, CARTE, Image.LANCZOS, centering=(0.5, 0.4))
    fond = ImageOps.fit(im, CARTE, Image.LANCZOS).filter(ImageFilter.GaussianBlur(28))
    fond = Image.blend(fond, Image.new("RGB", CARTE, (20, 20, 20)), 0.35)
    photo = ImageOps.contain(im, CARTE, Image.LANCZOS)
    fond.paste(photo, ((l - photo.width) // 2, (h - photo.height) // 2))
    return fond


def preparer(img, racine, sortie):
    """Ajoute img['pleine'] et img['carte'] (adresses web) à une illustration de type photo."""
    if not img or img.get("type") == "logo" or img.get("carte"):
        return img
    source = unquote(img["image"])
    if source not in _deja:
        _deja[source] = None
        try:
            chemin = Path(racine) / source.lstrip("/")
            im = _ouvrir(chemin)
            dossier = Path(sortie) / "static" / "images" / "web"
            dossier.mkdir(parents=True, exist_ok=True)
            base = Path(source).stem
            _pleine(im).save(dossier / f"{base}-pleine.jpg", "JPEG", quality=QUALITE, optimize=True, progressive=True)
            _carte(im).save(dossier / f"{base}-carte.jpg", "JPEG", quality=QUALITE, optimize=True, progressive=True)
            _deja[source] = (quote(f"/static/images/web/{base}-pleine.jpg"), quote(f"/static/images/web/{base}-carte.jpg"))
        except Exception as e:  # une photo illisible ne doit jamais casser le site
            print(f"  ! photo non redimensionnée ({source}) : {e}")
    if _deja[source]:
        img["pleine"], img["carte"] = _deja[source]
    return img
