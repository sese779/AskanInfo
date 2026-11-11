"""Regroupe les articles du fil qui parlent du même événement (comme Google Actualités)
et choisit les images par sujet (images.yaml).

Le regroupement compare les mots importants des titres : deux titres vont ensemble
s'ils partagent assez de mots rares (les mots trop fréquents comme « JOJ » ou
« Dakar » sont ignorés, sinon tous les articles des Jeux seraient mis ensemble).
"""

import re
import unicodedata
from collections import Counter
from datetime import timedelta
from pathlib import Path

import yaml

MOTS_VIDES = set("""le la les un une des du de d l au aux et ou en a dans sur pour par avec sans ce
cette ces son sa ses leur leurs qui que quoi est sont ete etre plus pas ne se s il elle ils on nous
vous y apres avant entre contre vers chez lors face selon depuis tout tous deux trois senegal
senegalais senegalaise""".split())


def normaliser(texte):
    texte = unicodedata.normalize("NFD", str(texte).lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def mots(titre):
    # 7 premières lettres : « recensés » et « recense » comptent pour le même mot
    return {m[:7] for m in re.findall(r"[a-z0-9]+", normaliser(titre))
            if len(m) > 2 and m not in MOTS_VIDES}


def grouper(items):
    """items triés du plus récent au plus ancien -> liste de groupes (listes d'items)."""
    signatures = [mots(i["titre"]) for i in items]
    freq = Counter(m for s in signatures for m in s)
    seuil = max(3, len(items) * 0.04)
    frequents = {m for m, n in freq.items() if n > seuil}
    groupes = []   # (signature de tête, [items])
    for item, sig in zip(items, signatures):
        sig = sig - frequents
        meilleur, score = None, 0
        for tete, membres in groupes:
            commun = len(sig & tete)
            if not commun:
                continue
            part = commun / max(1, min(len(sig), len(tete)))
            ok = (commun >= 3 and part >= 0.4) or (commun >= 2 and commun / max(len(sig), len(tete)) >= 0.5)
            if ok and part > score:
                meilleur, score = membres, part
        if meilleur is not None:
            meilleur.append(item)
        else:
            groupes.append((sig, [item]))
    return [membres for _, membres in groupes]


def lire_images(racine):
    """images.yaml -> liste de règles valides {mots, image, type, credit}."""
    f = racine / "images.yaml"
    if not f.exists():
        return []
    regles = []
    for r in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("images") or []:
        if not isinstance(r, dict) or r.get("actif") is False:
            continue
        image, credit = str(r.get("image") or "").strip(), str(r.get("credit") or "").strip()
        cles = r.get("mots_cles") or []
        cles = [cles] if isinstance(cles, str) else cles
        cles = [normaliser(c).strip() for c in cles if str(c).strip()]
        valide = re.fullmatch(r"/static/images/[A-Za-z0-9._-]+\.(png|jpe?g|webp)", image, re.I)
        if not (valide and credit and cles and (racine / image.lstrip("/")).is_file()):
            print(f"  ! images.yaml : règle ignorée (image absente, crédit ou mots-clés manquants) : {image or r}")
            continue
        regles.append({"mots": cles, "image": image, "credit": credit,
                       "type": "logo" if r.get("type") == "logo" else "photo"})
    return regles


def image_pour(titres, regles):
    texte = " " + " ".join(re.sub(r"[^a-z0-9]+", " ", normaliser(t)) for t in titres) + " "
    for r in regles:
        for c in r["mots"]:
            if f" {re.sub(r'[^a-z0-9]+', ' ', c).strip()} " in texte:
                return r
    return None


def sujets(items, contenus, regles, maintenant, nb_une=5, heures=36):
    """-> (sujets à la une, tous les groupes) ; chaque sujet est un dict prêt pour le gabarit."""
    synthese_par_lien = {}
    for c in contenus:
        for s in c.get("sources") or []:
            synthese_par_lien.setdefault(s["url"], c)

    def habiller(g):
        vus, un_par_media = set(), []
        for i in g:
            if i["source"] not in vus:
                vus.add(i["source"])
                un_par_media.append(i)
        synthese = next((synthese_par_lien[i["lien"]] for i in g if i["lien"] in synthese_par_lien), None)
        titres = [g[0]["titre"]] + ([synthese["titre"]] if synthese else [])
        # la tête du sujet : de préférence un média principal
        principaux = [i for i in un_par_media if not i.get("secondaire")]
        if principaux and principaux[0] is not un_par_media[0]:
            un_par_media.remove(principaux[0])
            un_par_media.insert(0, principaux[0])
        return {"tete": un_par_media[0], "autres": un_par_media[1:], "tous": g, "nb_medias": len(un_par_media),
                "nb_principaux": len(principaux), "secondaire": not principaux,
                "rubrique": g[0]["rubrique"], "synthese": synthese, "image": image_pour(titres, regles)}

    groupes = [habiller(g) for g in grouper(items)]
    limite = (maintenant - timedelta(hours=heures)).isoformat()
    # à la une : au moins 2 médias principaux (les sources secondaires complètent la carte)
    candidats = [s for s in groupes if s["nb_principaux"] >= 2 and s["tete"]["date"] >= limite]
    candidats.sort(key=lambda s: (s["nb_principaux"], s["nb_medias"], s["tete"]["date"]), reverse=True)
    return candidats[:nb_une], groupes
