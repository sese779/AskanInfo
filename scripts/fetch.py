"""Veille : lit les flux RSS déclarés dans sources.yaml et met à jour data/items.json.

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


def rubrique(titre, extrait, rubriques):
    """Cherche d'abord dans le titre (plus fiable), puis dans l'extrait."""
    motifs = [(nom, _motif(mots)) for nom, mots in rubriques.items()]
    for texte in (titre.lower(), extrait.lower()):
        for nom, motif in motifs:
            if motif.search(texte):
                return nom
    return "Actualité"


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
        if not titre or not lien_valide(lien):
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
            "extrait": extrait,
        })
    print(f"  {source['nom']} : {len(items)} article(s)")
    return items


def cle_doublon(titre):
    return re.sub(r"\W+", "", titre.lower())[:80]


def main():
    config = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
    sources = [s for s in config["sources"] if s.get("actif", True)]

    anciens = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
    par_id = {i["id"]: i for i in anciens}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for items in pool.map(lambda s: lire_source(s, config), sources):
            for i in items:
                par_id.setdefault(i["id"], i)

    # (re)classement de tous les articles, pour profiter des mots-clés à jour
    for i in par_id.values():
        i["rubrique"] = rubrique(i["titre"], i.get("extrait", ""), config.get("rubriques", {}))

    limite = datetime.now(timezone.utc) - DUREE_CONSERVATION
    vus, resultat = set(), []
    for i in sorted(par_id.values(), key=lambda i: i["date"], reverse=True):
        if datetime.fromisoformat(i["date"]) < limite:
            continue
        k = cle_doublon(i["titre"])
        if k in vus:
            continue
        vus.add(k)
        resultat.append(i)

    DATA.parent.mkdir(exist_ok=True)
    DATA.write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(resultat)} article(s) dans le fil.")


if __name__ == "__main__":
    main()
