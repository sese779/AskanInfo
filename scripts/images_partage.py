"""Images d'aperçu (1200×630) pour le partage sur WhatsApp, Facebook, X et
Google : une par article/synthèse, plus une image par défaut pour le site."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
POLICE_GRASSE = str(ROOT / "assets" / "polices" / "DejaVuSans-Bold.ttf")
POLICE = str(ROOT / "assets" / "polices" / "DejaVuSans.ttf")
L, H = 1200, 630
VERT, JAUNE, ROUGE, BLANC = (0, 133, 63), (253, 239, 66), (227, 27, 35), (255, 255, 255)


def _lignes(dessin, texte, police, largeur_max, max_lignes):
    mots, lignes, courante = texte.split(), [], ""
    for mot in mots:
        essai = f"{courante} {mot}".strip()
        if dessin.textlength(essai, font=police) <= largeur_max:
            courante = essai
        else:
            lignes.append(courante)
            courante = mot
    lignes.append(courante)
    if len(lignes) > max_lignes:
        lignes = lignes[:max_lignes]
        lignes[-1] = lignes[-1].rstrip(" ,;:") + "…"
    return lignes


def _fond():
    img = Image.new("RGB", (L, H), VERT)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, L, 14], fill=JAUNE)
    d.rectangle([0, H - 14, L, H], fill=ROUGE)
    return img, d


def _logo(d, x, y, taille):
    police = ImageFont.truetype(POLICE_GRASSE, taille)
    d.text((x, y), "Askan", font=police, fill=BLANC)
    d.text((x + d.textlength("Askan", font=police), y), "Info", font=police, fill=JAUNE)


def image_article(titre, rubrique, etiquette, chemin):
    img, d = _fond()
    _logo(d, 70, 52, 52)
    badge = ImageFont.truetype(POLICE_GRASSE, 30)
    texte_badge = f"{etiquette} · {rubrique}".upper()
    lb = d.textlength(texte_badge, font=badge)
    d.rounded_rectangle([70, 150, 70 + lb + 36, 150 + 52], radius=8, fill=JAUNE)
    d.text((88, 158), texte_badge, font=badge, fill=VERT)
    # titre : la plus grande taille qui tient en 4 lignes
    for taille in (64, 58, 52, 46, 42):
        police = ImageFont.truetype(POLICE_GRASSE, taille)
        lignes = _lignes(d, titre, police, L - 140, 4)
        if len(lignes) * taille * 1.22 <= 330 and not lignes[-1].endswith("…") or taille == 42:
            break
    y = 240
    for ligne in lignes:
        d.text((70, y), ligne, font=police, fill=BLANC)
        y += int(taille * 1.22)
    pied = ImageFont.truetype(POLICE, 28)
    d.text((70, H - 70), "askaninfo.com  ·  Le Sénégal, l'Afrique, le monde", font=pied, fill=BLANC)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    img.save(chemin, optimize=True)


def image_site(chemin):
    img, d = _fond()
    police = ImageFont.truetype(POLICE_GRASSE, 130)
    lg = d.textlength("AskanInfo", font=police)
    x = (L - lg) / 2
    d.text((x, 190), "Askan", font=police, fill=BLANC)
    d.text((x + d.textlength("Askan", font=police), 190), "Info", font=police, fill=JAUNE)
    sous = ImageFont.truetype(POLICE_GRASSE, 44)
    t = "Le Sénégal, l'Afrique, le monde"
    d.text(((L - d.textlength(t, font=sous)) / 2, 370), t, font=sous, fill=BLANC)
    t2 = "l'actualité en un seul endroit"
    p2 = ImageFont.truetype(POLICE, 36)
    d.text(((L - d.textlength(t2, font=p2)) / 2, 440), t2, font=p2, fill=BLANC)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    img.save(chemin, optimize=True)
