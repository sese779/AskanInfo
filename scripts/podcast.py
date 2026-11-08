"""Revue de presse audio : transforme les scripts content/podcast/*.md en MP3.

Pour chaque script sans fichier data/podcast/<nom>.json :
  1. synthèse vocale avec Piper (logiciel libre, voix française) ;
  2. conversion en MP3 avec ffmpeg ;
  3. envoi du MP3 dans la « release » GitHub « podcast » (hors du dépôt Git,
     pour ne pas l'alourdir) ;
  4. écriture de data/podcast/<nom>.json (adresse, taille, durée) que
     scripts/build.py utilise pour la page Podcast et le flux podcast.

Usage (dans GitHub Actions) : python scripts/podcast.py <modele_voix.onnx>
"""

import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "content" / "podcast"
META = ROOT / "data" / "podcast"
DEPOT = "sese779/AskanInfo"
RELEASE = "podcast"


def texte_a_lire(fichier):
    """Corps du script, sans l'en-tête ni la mise en forme Markdown."""
    texte = fichier.read_text(encoding="utf-8")
    m = re.match(r"^---\n.*?\n---\n(.*)$", texte, re.S)
    corps = m.group(1) if m else texte
    corps = re.sub(r"https?://\S+", "", corps)          # jamais d'adresse lue à voix haute
    corps = re.sub(r"[*_#>`\[\]]", "", corps)
    return re.sub(r"\n{3,}", "\n\n", corps).strip()


def lancer(*cmd, entree=None):
    subprocess.run(cmd, input=entree, check=True, text=entree is not None)


def main(modele):
    META.mkdir(parents=True, exist_ok=True)
    a_faire = [f for f in sorted(SCRIPTS.glob("[!_]*.md")) if not (META / f"{f.stem}.json").exists()]
    if not a_faire:
        print("Aucun nouvel épisode.")
        return
    # la release qui stocke les MP3 (créée une seule fois)
    if subprocess.run(["gh", "release", "view", RELEASE, "-R", DEPOT],
                      capture_output=True).returncode != 0:
        lancer("gh", "release", "create", RELEASE, "-R", DEPOT, "--title", "Podcast AskanInfo",
               "--notes", "Fichiers audio de la revue de presse AskanInfo.")
    for f in a_faire:
        with tempfile.TemporaryDirectory() as tmp:
            wav, mp3 = Path(tmp) / "episode.wav", Path(tmp) / f"askaninfo-{f.stem}.mp3"
            lancer(sys.executable, "-m", "piper", "-m", modele, "-f", str(wav),
                   "--sentence-silence", "0.35", entree=texte_a_lire(f))
            with wave.open(str(wav)) as w:
                duree = round(w.getnframes() / w.getframerate())
            lancer("ffmpeg", "-loglevel", "error", "-y", "-i", str(wav),
                   "-ac", "1", "-b:a", "64k", str(mp3))
            lancer("gh", "release", "upload", RELEASE, str(mp3), "-R", DEPOT, "--clobber")
            meta = {
                "url": f"https://github.com/{DEPOT}/releases/download/{RELEASE}/{mp3.name}",
                "taille": mp3.stat().st_size,
                "duree": duree,
            }
        (META / f"{f.stem}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        print(f"Épisode {f.stem} : {duree // 60} min {duree % 60:02d} s")


if __name__ == "__main__":
    main(sys.argv[1])
