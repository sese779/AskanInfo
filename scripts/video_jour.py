"""Vidéo verticale « L'essentiel du jour » (TikTok, Reels, Shorts).

Entrée : content/video/AAAA-MM-JJ.md, écrit par l'agent le soir avec le podcast :

    ---
    titre: "L'essentiel du vendredi 20 novembre"
    accroche: "Ismaïla Sarr reçoit deux trophées de la Conference League"
    sujets:
      - synthese: 2026-11-20-ismaila-sarr-trophees-conference-league
        accroche: "Deux trophées pour Ismaïla Sarr"
        texte: "Ismaïla Sarr a reçu ses trophées de meilleur joueur ..."
      - ...
    ---

Deux sortes de vidéos : la vidéo complète (tous les sujets), et une courte vidéo par
sujet (15 à 25 secondes). Chacune s'ouvre sur l'accroche, affichée en grand et lue en
premier : les deux premières secondes décident si l'on regarde la suite.

Chaque sujet : la photo de la synthèse (champ photo, sinon image par mots-clés,
sinon fond aux couleurs du site), sa rubrique, son titre, et un court texte lu par
la voix de synthèse (Piper) et affiché en sous-titres.

Usage :
  python scripts/video_jour.py <modele_voix.onnx> content/video/2026-11-20.md sortie.mp4
  python scripts/video_jour.py <modele_voix.onnx> --lot     (GitHub Actions, workflow Podcast)
  python scripts/video_jour.py <modele_voix.onnx> content/video/2026-11-20.md sortie.mp4 2
      (courte vidéo du 2e sujet)
Le mode --lot fabrique les vidéos pas encore faites, les range dans la release
GitHub « video » et écrit data/video/<date>.json (adresse, taille, durée, et la même
chose pour chaque vidéo de sujet dans « sujets »).
"""
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from regroupement import illustration, image_pour, lire_images  # noqa: E402

L, H = 1080, 1920
VERT, JAUNE, ROUGE, BLANC, NOIR = (0, 133, 63), (253, 239, 66), (227, 27, 35), (255, 255, 255), (12, 18, 14)
GRAS = str(ROOT / "assets" / "polices" / "DejaVuSans-Bold.ttf")
NORMAL = str(ROOT / "assets" / "polices" / "DejaVuSans.ttf")
PAUSE = 0.45            # silence entre deux sujets (secondes)
DEPOT = "sese779/AskanInfo"
RELEASE = "video"
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def police(taille, gras=True):
    return ImageFont.truetype(GRAS if gras else NORMAL, taille)


def lignes(d, texte, f, largeur, max_lignes=None):
    mots, res, cur = texte.split(), [], ""
    for m in mots:
        essai = f"{cur} {m}".strip()
        if d.textlength(essai, font=f) <= largeur:
            cur = essai
        else:
            res.append(cur)
            cur = m
    if cur:
        res.append(cur)
    if max_lignes and len(res) > max_lignes:
        res = res[:max_lignes]
        res[-1] = res[-1].rstrip(".,;:") + "…"
    return res


def logo(d, x, y, taille):
    f = police(taille)
    d.text((x, y), "Askan", font=f, fill=BLANC)
    d.text((x + d.textlength("Askan", font=f), y), "Info", font=f, fill=JAUNE)


def bandes(d):
    d.rectangle([0, 0, L, 16], fill=JAUNE)
    d.rectangle([0, H - 16, L, H], fill=ROUGE)


def photo_recadree(chemin, largeur, hauteur):
    img = Image.open(chemin).convert("RGB")
    r = max(largeur / img.width, hauteur / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x, y = (img.width - largeur) // 2, (img.height - hauteur) // 2
    return img.crop((x, y, x + largeur, y + hauteur))


def carte_sujet(sujet, date_txt, sous_titre, accroche=None):
    img = Image.new("RGB", (L, H), VERT)
    d = ImageDraw.Draw(img)
    # photo (ou fond de marque)
    zone = (0, 200, L, 1060)
    if sujet.get("image"):
        ph = photo_recadree(sujet["image"], zone[2] - zone[0], zone[3] - zone[1])
        img.paste(ph, zone[:2])
        if sujet.get("credit"):
            f = police(24, False)
            t = sujet["credit"]
            w = d.textlength(t, font=f)
            d.rectangle([L - w - 36, zone[3] - 46, L, zone[3]], fill=(0, 0, 0))
            d.text((L - w - 18, zone[3] - 40), t, font=f, fill=BLANC)
    else:
        d.rectangle(zone, fill=(0, 110, 52))
        logo(d, 250, 560, 120)
    bandes(d)
    logo(d, 48, 60, 64)
    f = police(34, False)
    d.text((L - 48 - d.textlength(date_txt, font=f), 82), date_txt, font=f, fill=BLANC)
    # rubrique
    f = police(38)
    rub = sujet["rubrique"].upper()
    w = d.textlength(rub, font=f)
    d.rounded_rectangle([48, 1100, 48 + w + 40, 1166], radius=10, fill=JAUNE)
    d.text((68, 1110), rub, font=f, fill=VERT)
    # titre
    for taille in (70, 64, 58, 52):
        f = police(taille)
        ls = lignes(d, sujet["titre"], f, L - 96, 4)
        if not ls[-1].endswith("…") or taille == 52:
            break
    y = 1200
    for ligne in ls:
        d.text((48, y), ligne, font=f, fill=BLANC)
        y += int(taille * 1.2)
    # accroche : grand bandeau jaune sur la photo, le temps qu'elle est lue
    if accroche:
        for taille in (76, 68, 60):
            f = police(taille)
            ls = lignes(d, accroche, f, L - 150, 3)
            if not ls[-1].endswith("…") or taille == 60:
                break
        pas = int(taille * 1.18)
        h = len(ls) * pas + 56
        y0 = 1040 - h
        d.rounded_rectangle([40, y0, L - 40, 1040], radius=20, fill=JAUNE)
        for i, ligne in enumerate(ls):
            d.text(((L - d.textlength(ligne, font=f)) / 2, y0 + 28 + i * pas), ligne, font=f, fill=VERT)
    # sous-titre (ce que dit la voix)
    if sous_titre:
        f = police(50)
        ls = lignes(d, sous_titre, f, L - 140)
        h = len(ls) * 64 + 50
        y0 = 1820 - h
        d.rounded_rectangle([40, y0, L - 40, 1820], radius=18, fill=NOIR)
        for i, ligne in enumerate(ls):
            d.text(((L - d.textlength(ligne, font=f)) / 2, y0 + 25 + i * 64), ligne, font=f, fill=JAUNE)
    return img


def carte_titre(haut, bas, mention=None):
    img = Image.new("RGB", (L, H), VERT)
    d = ImageDraw.Draw(img)
    bandes(d)
    logo(d, 215, 700, 130)
    f = police(56)
    for i, ligne in enumerate(lignes(d, haut, f, L - 120)):
        d.text(((L - d.textlength(ligne, font=f)) / 2, 900 + i * 72), ligne, font=f, fill=BLANC)
    f = police(44, False)
    for i, ligne in enumerate(lignes(d, bas, f, L - 120)):
        d.text(((L - d.textlength(ligne, font=f)) / 2, 1120 + i * 60), ligne, font=f, fill=JAUNE)
    if mention:
        f = police(30, False)
        d.text(((L - d.textlength(mention, font=f)) / 2, H - 120), mention, font=f, fill=BLANC)
    return img


def carte_accroche(accroche, bas):
    """Ouverture de la vidéo complète : le fait le plus fort du jour, en très grand."""
    img = Image.new("RGB", (L, H), VERT)
    d = ImageDraw.Draw(img)
    bandes(d)
    logo(d, 48, 60, 64)
    for taille in (96, 86, 76, 66):
        f = police(taille)
        ls = lignes(d, accroche, f, L - 120, 5)
        if not ls[-1].endswith("…") or taille == 66:
            break
    pas = int(taille * 1.18)
    y = 860 - len(ls) * pas // 2
    for ligne in ls:
        d.text(((L - d.textlength(ligne, font=f)) / 2, y), ligne, font=f, fill=BLANC)
        y += pas
    f = police(44, False)
    for i, ligne in enumerate(lignes(d, bas, f, L - 120)):
        d.text(((L - d.textlength(ligne, font=f)) / 2, y + 70 + i * 60), ligne, font=f, fill=JAUNE)
    return img


def morceaux(texte, n=7):
    """Sous-titres : phrase par phrase, chaque phrase coupée en parts égales
    d'environ n mots (jamais un mot isolé en fin de phrase)."""
    res = []
    for phrase in re.split(r"(?<=[.!?])\s+", texte.strip()):
        mots = phrase.split()
        if not mots:
            continue
        nb = max(1, round(len(mots) / n))
        taille = -(-len(mots) // nb)
        res += [" ".join(mots[k:k + taille]) for k in range(0, len(mots), taille)]
    return res


def voix(modele, texte, wav):
    subprocess.run([sys.executable, "-m", "piper", "-m", modele, "-f", str(wav)],
                   input=texte.encode("utf-8"), check=True, capture_output=True)
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def lire_synthese(slug, regles):
    texte = (ROOT / "content" / "syntheses" / f"{slug}.md").read_text(encoding="utf-8")
    meta = yaml.safe_load(texte.split("---")[1]) or {}
    img = None
    if meta.get("photo"):
        img = illustration(ROOT, meta.get("photo"), meta.get("credit_photo"))
    img = img or image_pour([meta["titre"], meta.get("chapo", "")], regles)
    chemin = credit = None
    if img and img.get("type") != "logo":
        from urllib.parse import unquote
        chemin, credit = ROOT / unquote(img["image"]).lstrip("/"), img["credit"]
    return {"titre": meta["titre"], "rubrique": meta.get("rubrique", "Actualité"),
            "image": chemin, "credit": credit}


def encoder(tmp, plans, wavs, sortie):
    """Assemble images (avec leur durée) et voix en MP4 vertical."""
    liste = tmp / "audio.txt"
    silence = tmp / "silence.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=22050:cl=mono", "-t", str(PAUSE), str(silence)], check=True)
    liste.write_text("".join(f"file '{w}'\nfile '{silence}'\n" for w, _ in wavs))
    audio = tmp / "voix.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(liste), "-ar", "22050", "-ac", "1", str(audio)], check=True)
    images = tmp / "images.txt"
    images.write_text("".join(f"file '{p}'\nduration {du:.3f}\n" for p, du in plans)
                      + f"file '{plans[-1][0]}'\n")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(images), "-i", str(audio),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "23", "-c:a", "aac", "-b:a", "96k", "-shortest",
                    "-movflags", "+faststart", str(sortie)], check=True)


def main(modele, entree, sortie, numero=None):
    """Vidéo complète, ou (numero = 1, 2, …) courte vidéo d'un seul sujet."""
    brut = Path(entree).read_text(encoding="utf-8")
    spec = yaml.safe_load(brut.split("---")[1])
    regles = lire_images(ROOT)
    date_txt = spec.get("date_courte") or ""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", Path(entree).stem)
    if not date_txt and m:
        date_txt = f"{int(m.group(3))} {MOIS[int(m.group(2)) - 1]} {m.group(1)}"
    sujets = spec["sujets"]
    if numero is not None:
        sujets = [sujets[int(numero) - 1]]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        plans, wavs = [], []   # (image, durée), (voix, durée)

        def plan(img, duree):
            p = tmp / f"p{len(plans):03d}.png"
            img.save(p)
            plans.append((p, duree))

        def dire(texte):
            w = tmp / f"w{len(wavs):03d}.wav"
            d = voix(modele, texte, w)
            wavs.append((w, d))
            return d

        # ouverture de la vidéo complète : l'accroche du jour, sans formule de politesse
        if numero is None:
            accroche = spec.get("accroche")
            if accroche:
                rdv = ("Le rendez-vous sport, avec AskanInfo." if Path(entree).stem.endswith("-sport")
                       else "L'essentiel du jour, avec AskanInfo.")
                d = dire(f"{accroche.rstrip('.')}. {rdv}")
                plan(carte_accroche(accroche, spec["titre"]), d + PAUSE)
            else:
                d = dire(spec.get("intro") or "Voici l'essentiel de l'actualité, avec AskanInfo.")
                plan(carte_titre(spec["titre"], "L'actualité du Sénégal en une minute"), d + PAUSE)
        # sujets
        for s in sujets:
            sujet = lire_synthese(s["synthese"], regles)
            # vidéo d'un sujet : elle s'ouvre sur son accroche, en grand sur la photo
            if numero is not None and s.get("accroche"):
                d = dire(s["accroche"])
                plan(carte_sujet(sujet, date_txt, None, s["accroche"]), d + PAUSE)
            d = dire(s["texte"])
            parts = morceaux(s["texte"])
            total = sum(len(p) for p in parts)
            for j, p in enumerate(parts):
                duree = d * len(p) / total + (PAUSE if j == len(parts) - 1 else 0)
                plan(carte_sujet(sujet, date_txt, p), duree)
        # fin
        if numero is None:
            outro = spec.get("outro") or "Retrouvez toutes nos synthèses, avec leurs sources, sur askaninfo point com."
        else:
            outro = "Toutes les sources sur askaninfo point com."
        d = dire(outro)
        plan(carte_titre("Toutes les sources sur", "askaninfo.com", "Voix de synthèse · AskanInfo"), d + 1.2)
        encoder(tmp, plans, wavs, sortie)
    print(f"Vidéo : {sortie}")


def publier(mp4):
    """Range une vidéo dans la release et renvoie son adresse, sa taille et sa durée."""
    duree = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                  "-of", "csv=p=0", str(mp4)], capture_output=True, text=True,
                                 check=True).stdout.strip())
    subprocess.run(["gh", "release", "upload", RELEASE, str(mp4), "-R", DEPOT, "--clobber"], check=True)
    return {"url": f"https://github.com/{DEPOT}/releases/download/{RELEASE}/{mp4.name}",
            "taille": mp4.stat().st_size, "duree": round(duree)}


def lot(modele):
    """Fabrique et publie les vidéos de content/video/ qui n'ont pas encore de data/video/<date>.json."""
    meta_dir = ROOT / "data" / "video"
    meta_dir.mkdir(parents=True, exist_ok=True)
    a_faire = [f for f in sorted((ROOT / "content" / "video").glob("[!_]*.md"), reverse=True)
               if not (meta_dir / f"{f.stem}.json").exists()][:3]
    if not a_faire:
        return
    if subprocess.run(["gh", "release", "view", RELEASE, "-R", DEPOT], capture_output=True).returncode != 0:
        subprocess.run(["gh", "release", "create", RELEASE, "-R", DEPOT, "--title", "Vidéos AskanInfo",
                        "--notes", "Vidéos « L'essentiel du jour » d'AskanInfo."], check=True)
    for f in a_faire:
        spec = yaml.safe_load(f.read_text(encoding="utf-8").split("---")[1]) or {}
        with tempfile.TemporaryDirectory() as tmp:
            mp4 = Path(tmp) / f"askaninfo-{f.stem}.mp4"
            try:
                main(modele, f, mp4)
            except Exception as e:      # une vidéo ratée ne bloque pas les autres
                print(f"  ! {f.name} : {e}", file=sys.stderr)
                continue
            meta = publier(mp4)
            meta["sujets"] = []
            for i, s in enumerate(spec.get("sujets") or [], 1):
                court = Path(tmp) / f"askaninfo-{f.stem}-{i}.mp4"
                try:
                    main(modele, f, court, i)
                    meta["sujets"].append(dict(publier(court), synthese=s["synthese"]))
                except Exception as e:
                    print(f"  ! {f.name}, sujet {i} : {e}", file=sys.stderr)
        (meta_dir / f"{f.stem}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[2] == "--lot":
        lot(sys.argv[1])
    else:
        main(*sys.argv[1:5])
