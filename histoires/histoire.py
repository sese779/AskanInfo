"""Prototype « Askan Histoires » : récit vertical, photos d'archives avec zoom lent,
voix de synthèse et sous-titres.  python histoire.py voix.onnx episode.yaml sortie.mp4"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from video_jour import lignes, morceaux, police, voix  # noqa: E402

L, H = 1080, 1920
ENCRE, OCRE, CREME, NOIR = (24, 19, 15), (217, 164, 65), (245, 236, 220), (0, 0, 0)
ICI = Path(__file__).parent / "photos"
CREDITS = json.loads((ICI / "credits.json").read_text(encoding="utf-8"))
FPS = 30


def marque(d):
    f = police(54)
    d.text((48, 70), "Askan", font=f, fill=CREME)
    d.text((48 + d.textlength("Askan ", font=f), 70), "Histoires", font=f, fill=OCRE)


def fond_photo(nom):
    """Photo recadrée en 9:16, un peu plus grande que l'écran (pour le zoom), assombrie en bas."""
    img = Image.open(ICI / f"{nom}.jpg").convert("RGB")
    W, Hh = int(L * 1.15), int(H * 1.15)
    r = max(W / img.width, Hh / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - Hh) // 2
    return img.crop((x, y, x + W, y + Hh))


def fond_uni():
    img = Image.new("RGB", (int(L * 1.15), int(H * 1.15)), ENCRE)
    return img


def calque(texte_haut=None, sous_titre=None, credit=None, grand=None, date=None):
    """Tout ce qui ne bouge pas : marque, grand texte, date, sous-titre, crédit photo."""
    c = Image.new("RGBA", (L, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    # dégradé sombre en haut et en bas pour la lisibilité
    for y in range(0, 300):
        d.line([(0, y), (L, y)], fill=(0, 0, 0, int(150 * (1 - y / 300))))
    for y in range(H - 900, H):
        d.line([(0, y), (L, y)], fill=(0, 0, 0, int(210 * (y - (H - 900)) / 900)))
    if grand:   # grand texte : voile sombre sur toute l'image
        d.rectangle([0, 0, L, H], fill=(0, 0, 0, 140))
    marque(d)
    if date:
        f = police(130)
        d.text(((L - d.textlength(date, font=f)) / 2, 560), date, font=f, fill=OCRE)
    if grand:
        for taille in (80, 70, 62):
            f = police(taille)
            ls = lignes(d, grand, f, L - 120, 6)
            if not ls[-1].endswith("…") or taille == 62:
                break
        y = 760 if date else 700
        for ligne in ls:
            d.text(((L - d.textlength(ligne, font=f)) / 2, y), ligne, font=f, fill=CREME)
            y += int(taille * 1.2)
    if sous_titre:
        f = police(52)
        ls = lignes(d, sous_titre, f, L - 140)
        y0 = 1560 - len(ls) * 66
        for i, ligne in enumerate(ls):
            x = (L - d.textlength(ligne, font=f)) / 2
            d.text((x + 3, y0 + i * 66 + 3), ligne, font=f, fill=(0, 0, 0, 200))
            d.text((x, y0 + i * 66), ligne, font=f, fill=CREME)
    if credit:
        f = police(24, False)
        d.text((L - 40 - d.textlength(credit, font=f), H - 70), credit, font=f, fill=(220, 210, 195, 220))
    if texte_haut:
        f = police(38)
        d.text((50, 162), texte_haut, font=f, fill=(0, 0, 0, 200))
        d.text((48, 160), texte_haut, font=f, fill=OCRE)
    return c


def clip(tmp, n, fond, couches, duree, sens):
    """Zoom lent et continu sur le fond ; les calques (sous-titres) changent par-dessus."""
    fp, out = tmp / f"f{n}.png", tmp / f"v{n:03d}.mp4"
    fond.save(fp)
    entrees, filtres, prec = ["-loop", "1", "-i", str(fp)], [], "z"
    images = max(1, round(duree * FPS))
    z = (f"zoom='1+0.12*on/{images}'" if sens else f"zoom='1.12-0.12*on/{images}'")
    filtres.append(f"[0]scale={L*2}:-1,zoompan={z}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                   f":d={images}:s={L}x{H}:fps={FPS}[z]")
    for i, (couche, t0, t1) in enumerate(couches, 1):
        cp = tmp / f"c{n}_{i}.png"
        couche.save(cp)
        entrees += ["-i", str(cp)]
        filtres.append(f"[{prec}][{i}]overlay=0:0:enable='between(t,{t0:.3f},{t1:.3f})'[o{i}]")
        prec = f"o{i}"
    filtres.append(f"[{prec}]format=yuv420p[sortie]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *entrees, "-filter_complex", ";".join(filtres),
                    "-map", "[sortie]", "-frames:v", str(images), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "22", str(out)], check=True)
    return out


def main(modele, episode, sortie):
    ep = yaml.safe_load(Path(episode).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        clips, wavs, n = [], [], 0
        for k, plan in enumerate(ep["plans"]):
            w = tmp / f"w{k:03d}.wav"
            d = voix(modele, plan["voix"], w) + 0.35
            wavs.append((w, d))
            nom = plan.get("photo")
            fond = fond_photo(nom) if nom else fond_uni()
            credit = f"Photo : {CREDITS[nom]}" if nom else None
            parts = [None] if plan.get("sans_sous_titres") else morceaux(plan["voix"])
            total = sum(len(p or "x") for p in parts)
            couches, t = [], 0.0
            for i, p in enumerate(parts):
                du = d * len(p or "x") / total
                fin = d + 1 if i == len(parts) - 1 else t + du
                couches.append((calque(plan.get("haut"), p, credit, plan.get("grand"), plan.get("date")), t, fin))
                t += du
            clips.append(clip(tmp, k, fond, couches, d, k % 2 == 0))
        # voix
        liste = tmp / "a.txt"
        sil = tmp / "sil.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "anullsrc=r=22050:cl=mono", "-t", "0.35", str(sil)], check=True)
        liste.write_text("".join(f"file '{w}'\nfile '{sil}'\n" for w, _ in wavs))
        audio = tmp / "voix.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                        "-i", str(liste), "-ar", "22050", "-ac", "1", str(audio)], check=True)
        vids = tmp / "v.txt"
        vids.write_text("".join(f"file '{c}'\n" for c in clips))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(vids),
                        "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", "-shortest",
                        "-movflags", "+faststart", str(sortie)], check=True)
    print("Vidéo :", sortie)


if __name__ == "__main__":
    main(*sys.argv[1:4])
