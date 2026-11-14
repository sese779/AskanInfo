"""Version audio des synthèses : lit chaque synthèse (titre, chapô, texte) avec
Piper, en fait un MP3 rangé dans la release GitHub « audio-articles », et écrit
data/audio/<nom>.json (adresse, taille, durée) que scripts/build.py utilise pour
afficher le lecteur sous la synthèse.

Usage (GitHub Actions, workflow Podcast) : python scripts/audio_articles.py <modele_voix.onnx>
"""

import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SYNTHESES = ROOT / "content" / "syntheses"
META = ROOT / "data" / "audio"
DEPOT = "sese779/AskanInfo"
RELEASE = "audio-articles"
MAX_PAR_PASSAGE = 30   # les plus récentes d'abord ; le reste au passage suivant


def a_lire(fichier):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", fichier.read_text(encoding="utf-8"), re.S)
    if not m:
        return None
    meta = yaml.safe_load(m.group(1)) or {}
    if meta.get("brouillon"):
        return None
    corps = m.group(2)
    corps = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", corps)   # liens Markdown : on garde le texte
    corps = re.sub(r"https?://\S+", "", corps)               # jamais d'adresse lue à voix haute
    corps = re.sub(r"[*_#>`|]", "", corps)
    morceaux = [str(meta.get("titre", "")).strip(), str(meta.get("chapo", "")).strip(), corps.strip()]
    texte = "\n\n".join(x for x in morceaux if x)
    return re.sub(r"\n{3,}", "\n\n", texte)


def lancer(*cmd, entree=None):
    subprocess.run(cmd, input=entree, check=True, text=entree is not None)


def main(modele):
    META.mkdir(parents=True, exist_ok=True)
    a_faire = [f for f in sorted(SYNTHESES.glob("[!_.]*.md"), reverse=True)
               if not (META / f"{f.stem}.json").exists()][:MAX_PAR_PASSAGE]
    if not a_faire:
        print("Aucune nouvelle synthèse à lire.")
        return
    if subprocess.run(["gh", "release", "view", RELEASE, "-R", DEPOT], capture_output=True).returncode != 0:
        lancer("gh", "release", "create", RELEASE, "-R", DEPOT, "--title", "Synthèses AskanInfo en audio",
               "--notes", "Versions audio (lecture automatique) des synthèses AskanInfo.")
    for f in a_faire:
        texte = a_lire(f)
        if not texte:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            wav, mp3 = Path(tmp) / "lecture.wav", Path(tmp) / f"{f.stem}.mp3"
            lancer(sys.executable, "-m", "piper", "-m", modele, "-f", str(wav),
                   "--sentence-silence", "0.3", entree=texte)
            with wave.open(str(wav)) as w:
                duree = round(w.getnframes() / w.getframerate())
            lancer("ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-ac", "1", "-b:a", "48k", str(mp3))
            lancer("gh", "release", "upload", RELEASE, str(mp3), "-R", DEPOT, "--clobber")
            meta = {"url": f"https://github.com/{DEPOT}/releases/download/{RELEASE}/{mp3.name}",
                    "taille": mp3.stat().st_size, "duree": duree}
        (META / f"{f.stem}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        print(f"  {f.stem} : {duree} s")


if __name__ == "__main__":
    main(sys.argv[1])
