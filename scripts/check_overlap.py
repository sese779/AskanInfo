"""Contrôle anti-copie : vérifie qu'une synthèse ne reprend pas de longues
suites de mots identiques aux extraits des sources.

Usage : python scripts/check_overlap.py [fichiers.md ...]
Sans argument, contrôle toutes les synthèses. Code de sortie 1 en cas de problème.
"""

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TAILLE_SEQUENCE = 8   # au-delà de 7 mots identiques d'affilée, c'est de la copie


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


_items = None


def items_par_lien():
    global _items
    if _items is None:
        chemin = ROOT / "data" / "items.json"
        items = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else []
        _items = {i["lien"]: i for i in items}
    return _items


def liens_cites(fichier):
    m = re.match(r"^---\n(.*?)\n---\n", fichier.read_text(encoding="utf-8"), re.S)
    meta = yaml.safe_load(m.group(1)) if m else {}
    return [s.get("url") for s in (meta or {}).get("sources") or [] if isinstance(s, dict)]


def passages_copies(fichier):
    """Suites de mots que la synthèse partage avec les sources qu'elle cite."""
    reference = set()
    for lien in liens_cites(fichier):
        i = items_par_lien().get(lien)
        if i:
            reference |= sequences(mots(f"{i['titre']} . {i['extrait']}"), TAILLE_SEQUENCE)
    return sequences(mots(corps(fichier)), TAILLE_SEQUENCE) & reference


def main(fichiers):
    erreurs = 0
    for f in fichiers:
        communes = passages_copies(f)
        if communes:
            erreurs += 1
            print(f"✗ {f.name} : {len(communes)} passage(s) trop proche(s) des sources, ex. « {' '.join(next(iter(communes)))} »")
        else:
            print(f"✓ {f.name}")
    return 1 if erreurs else 0


if __name__ == "__main__":
    args = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "content" / "syntheses").glob("[!_]*.md"))
    sys.exit(main(args))
