"""Veille : lit les flux RSS déclarés dans medias.yaml et met à jour data/items.json.

On ne garde que le titre, le lien, la date et un court extrait (usage interne
pour l'agent de rédaction). Le site n'affiche que le titre et renvoie vers
l'article d'origine.
"""

import concurrent.futures
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "items.json"
ARCHIVES = ROOT / "data" / "archives"
USER_AGENT = "AskanInfoBot/1.0 (agregateur RSS; +https://github.com/sese779/AskanInfo)"
DUREE_CONSERVATION = timedelta(days=7)
LONGUEUR_EXTRAIT = 300
DELAI_MAX = 20                 # secondes
TAILLE_MAX = 5 * 1024 * 1024   # 5 Mo


def nettoyer(texte):
    texte = re.sub(r"<[^>]+>", " ", texte or "")
    texte = html.unescape(texte)
    return re.sub(r"\s+", " ", texte).strip()


def couper(texte, n):
    if len(texte) <= n:
        return texte
    return texte[:n].rsplit(" ", 1)[0] + "…"


def date_item(entry):
    for cle in ("published_parsed", "updated_parsed"):
        t = entry.get(cle)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _motif(mots):
    # 4 lettres ou moins : mot exact (« mort » ≠ « morte ») ; au-delà : début de mot (« lioncel » → « Lioncelles »)
    parties = [re.escape(m.lower()) + (r"\b" if len(m) <= 4 else "") for m in mots]
    return re.compile(r"\b(?:" + "|".join(parties) + ")")


GEOGRAPHIQUES = ("Afrique", "Monde")
# contenus publicitaires glissés dans certains flux (ex. « Comparing Casino Bonus Details »)
PUBLICITE = re.compile(r"\bcasinos?\b|\bbetting\b|\bslot machines?\b|\bonline slots?\b|\bbonus details\b", re.I)


PRIORITAIRES = ("Sport", "Diaspora")
# « un Sénégalais / une Sénégalaise / des compatriotes » dans un titre qui cite
# un pays étranger = vie de la diaspora
SENEGALAIS = re.compile(r"\bs[ée]n[ée]galais(?:e|es)?\b|\bcompatriotes?\b")
MOTS_GENERIQUES = {"afrique", "africain", "monde", "mondial", "international", "europe",
                   "européen", "union européenne", "sahel", "cedeao", "union africaine",
                   "onu", "nations unies", "otan", "g20"}


def rubrique(titre, extrait, rubriques, mots_senegal, zone=None, diaspora=False):
    """1. Sport, Diaspora ; 2. hors Sénégal : Afrique puis Monde, d'après le
    TITRE seul (un extrait cite souvent un pays au passage) ; 3. thèmes.
    Le titre est toujours examiné avant l'extrait."""
    motifs = {nom: _motif(mots) for nom, mots in rubriques.items()}
    titre, extrait = titre.lower(), extrait.lower()

    def premiere(noms, textes=(titre, extrait)):
        for texte in textes:
            for nom in noms:
                if nom in motifs and motifs[nom].search(texte):
                    return nom
        return None

    # média consacré à la diaspora : tout va en Diaspora, sauf le sport
    if diaspora:
        return premiere(("Sport",)) or "Diaspora"
    parle_du_senegal = any(m in titre or m in extrait for m in mots_senegal)
    # source africaine ou mondiale, article qui ne concerne pas le Sénégal :
    # onglet Afrique si le titre cite l'Afrique, sinon la zone de la source
    if zone and not parle_du_senegal:
        return premiere(("Afrique",), (titre,)) or zone
    prioritaire = premiere(PRIORITAIRES)   # titre d'abord, puis extrait
    if prioritaire:
        return prioritaire
    pays = [m for nom in GEOGRAPHIQUES for m in rubriques.get(nom, []) if m.lower() not in MOTS_GENERIQUES]
    if SENEGALAIS.search(titre) and pays and _motif(pays).search(titre):
        return "Diaspora"
    themes = [n for n in motifs if n not in GEOGRAPHIQUES + PRIORITAIRES]
    return (premiere(PRIORITAIRES)
            or (None if parle_du_senegal else premiere(GEOGRAPHIQUES, (titre,)))
            or premiere(themes)
            # un article sur le Sénégal qui cite un autre pays (« Sénégal–Soudan »)
            # ne part pas en Afrique ou Monde
            or (None if parle_du_senegal else premiere(GEOGRAPHIQUES))
            or "Actualité")


def lien_valide(lien):
    """N'accepte que des liens web classiques (bloque javascript:, data:, etc.)."""
    try:
        u = urllib.parse.urlsplit(lien.strip())
    except ValueError:
        return False
    return u.scheme in ("http", "https") and bool(u.netloc)


def telecharger(url):
    """Télécharge un flux avec délai maximum et taille maximum."""
    if not url.startswith(("http://", "https://")):          # fichier local (tests)
        return Path(url).read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=DELAI_MAX) as r:
        donnees = r.read(TAILLE_MAX + 1)
    if len(donnees) > TAILLE_MAX:
        raise ValueError("flux trop volumineux")
    return donnees


def reparer_xml(donnees):
    """Corrige les erreurs XML courantes : « & » non échappés, caractères de contrôle."""
    texte = donnees.decode("utf-8", errors="replace")
    texte = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", texte)
    texte = re.sub(r"&(?!#\d+;|#x[0-9a-fA-F]+;|[a-zA-Z][a-zA-Z0-9]*;)", "&amp;", texte)
    return texte.encode("utf-8")


def lire_source(source, config):
    try:
        donnees = telecharger(source["flux"])
    except Exception as e:
        print(f"  ! {source['nom']} : téléchargement impossible ({e})", file=sys.stderr)
        return []
    flux = feedparser.parse(donnees)
    if flux.bozo and not flux.entries:
        flux = feedparser.parse(reparer_xml(donnees))
    if not flux.entries:
        print(f"  ! {source['nom']} : flux illisible ({flux.get('bozo_exception')})", file=sys.stderr)
        return []
    mots = [m.lower() for m in config.get("mots_cles_senegal", [])]
    items = []
    for e in flux.entries:
        titre = nettoyer(e.get("title"))
        lien = (e.get("link") or "").strip()
        if not titre or not lien_valide(lien) or PUBLICITE.search(titre):
            continue
        extrait = couper(nettoyer(e.get("summary")), LONGUEUR_EXTRAIT)
        texte = f"{titre} {extrait}"
        if source.get("filtre") and not any(m in texte.lower() for m in mots):
            continue
        items.append({
            "id": hashlib.sha1(lien.encode()).hexdigest()[:12],
            "titre": titre,
            "lien": lien,
            "source": source["nom"],
            "site_source": source.get("site", ""),
            "date": date_item(e).isoformat(),
            "rubrique": "",
            "zone": source.get("zone"),
            "diaspora": bool(source.get("diaspora")),
            "secondaire": bool(source.get("secondaire")),
            "extrait": extrait,
        })
    print(f"  {source['nom']} : {len(items)} article(s)")
    return items


def cle_doublon(titre):
    return re.sub(r"\W+", "", titre.lower())[:80]


def archiver(items):
    """Range les articles de plus de 7 jours dans data/archives/AAAA-MM.json
    (un fichier par mois) au lieu de les supprimer."""
    par_mois = {}
    for i in items:
        par_mois.setdefault(i["date"][:7], []).append(i)
    for mois, nouveaux in par_mois.items():
        f = ARCHIVES / f"{mois}.json"
        existants = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        ids = {i["id"] for i in existants}
        ajout = [i for i in nouveaux if i["id"] not in ids]
        if not ajout:
            continue
        tous = sorted(existants + ajout, key=lambda i: i["date"], reverse=True)
        ARCHIVES.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(tous, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  archives {mois} : +{len(ajout)} article(s)")


def ajouter_sport(config):
    """joueurs.yaml : les joueurs et clubs sénégalais comptent comme « parle du Sénégal »
    et rangent l'article en Sport ; les championnats étrangers rangent seulement en Sport."""
    f = ROOT / "joueurs.yaml"
    if not f.exists():
        return
    j = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    noms = [str(x).strip() for x in (j.get("joueurs") or []) + (j.get("clubs_senegal") or []) if str(x).strip()]
    competitions = [str(x).strip() for x in j.get("competitions") or [] if str(x).strip()]
    config["mots_cles_senegal"] = list(config.get("mots_cles_senegal") or []) + noms
    rubriques = config.setdefault("rubriques", {})
    rubriques["Sport"] = list(rubriques.get("Sport") or []) + [n.lower() for n in noms + competitions]


def main():
    config = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
    config["sources"] = yaml.safe_load((ROOT / "medias.yaml").read_text(encoding="utf-8"))["sources"] or []
    sources = [s for s in config["sources"] if s.get("actif", True)]
    ajouter_sport(config)

    anciens = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
    par_id = {i["id"]: i for i in anciens}
    deja_dans_le_fil = set(par_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for items in pool.map(lambda s: lire_source(s, config), sources):
            for i in items:
                par_id.setdefault(i["id"], i)

    # (re)classement de tous les articles, pour profiter des mots-clés à jour
    for i in par_id.values():
        i["rubrique"] = rubrique(i["titre"], i.get("extrait", ""), config.get("rubriques", {}),
                                 [m.lower() for m in config.get("mots_cles_senegal", [])],
                                 i.get("zone"), i.get("diaspora", False))

    limite = datetime.now(timezone.utc) - DUREE_CONSERVATION
    vus, resultat, a_archiver = set(), [], []
    for i in sorted(par_id.values(), key=lambda i: i["date"], reverse=True):
        if datetime.fromisoformat(i["date"]) < limite:
            # on n'archive que ce qui a été publié dans le fil ; un vieil article
            # découvert aujourd'hui dans un flux n'est pas une actualité
            if i["id"] in deja_dans_le_fil:
                a_archiver.append(i)
            continue
        k = cle_doublon(i["titre"])
        if k in vus:
            continue
        vus.add(k)
        resultat.append(i)

    archiver(a_archiver)
    DATA.parent.mkdir(exist_ok=True)
    DATA.write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(resultat)} article(s) dans le fil.")


if __name__ == "__main__":
    main()
