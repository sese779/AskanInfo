"""Contrôle anti-copie : vérifie qu'une synthèse ne reprend pas de longues
suites de mots identiques aux extraits des sources.

Usage : python scripts/check_overlap.py [fichiers.md ...]
Sans argument, contrôle toutes les synthèses. Code de sortie 1 en cas de problème.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAILLE_SEQUENCE = 7   # nombre de mots consécutifs identiques tolérés au maximum - 1


def mots(texte):
    return re.findall(r"\w+", texte.lower())


def sequences(liste, n):
    return {tuple(liste[i:i + n]) for i in range(len(liste) - n + 1)}


def corps(fichier):
    texte = fichier.read_text(encoding="utf-8")
    m = re.match(r"^---\n.*?\n---\n(.*)$", texte, re.S)
    corps = m.group(1) if m else texte
    # les citations entre guillemets sont autorisées (droit de courte citation)
    return re.sub(r"«[^»]*»|\"[^\"]*\"", " ", corps)


def main(fichiers):
    items = json.loads((ROOT / "data" / "items.json").read_text(encoding="utf-8"))
    reference = set()
    for i in items:
        reference |= sequences(mots(f"{i['titre']} . {i['extrait']}"), TAILLE_SEQUENCE)

    erreurs = 0
    for f in fichiers:
        communes = sequences(mots(corps(f)), TAILLE_SEQUENCE) & reference
        if communes:
            erreurs += 1
            print(f"✗ {f.name} : {len(communes)} passage(s) trop proche(s) des sources, ex. « {' '.join(next(iter(communes)))} »")
        else:
            print(f"✓ {f.name}")
    return 1 if erreurs else 0


if __name__ == "__main__":
    args = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "content" / "syntheses").glob("[!_]*.md"))
    sys.exit(main(args))
