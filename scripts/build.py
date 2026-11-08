"""Construit le site statique dans _site/ à partir de :
- data/items.json        (fil d'actualité : titres + liens vers les sources)
- content/articles/*.md  (vos articles, signés « Rédaction »)
- content/syntheses/*.md (synthèses écrites par l'agent)
"""

import json
import os
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import markdown
import nh3
import yaml
from jinja2 import Environment, FileSystemLoader

from check_overlap import passages_copies

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
NOM_SITE = "AskanInfo"
CONTACT = "contact@askaninfo.com"
# Adresse publique du site (à changer si vous prenez un nom de domaine)
URL_SITE = os.environ.get("URL_SITE", "https://askaninfo.com").rstrip("/")
DESCRIPTION = "L'actualité du Sénégal et des Sénégalais, en un seul endroit."

# Balises HTML autorisées dans les articles (tout le reste, dont <script>, est supprimé)
BALISES = {"p", "br", "hr", "h2", "h3", "h4", "strong", "em", "b", "i", "u", "a", "ul", "ol",
           "li", "blockquote", "code", "pre", "img", "figure", "figcaption", "table",
           "thead", "tbody", "tr", "th", "td", "sup", "sub"}
ATTRIBUTS = {"a": {"href", "title"}, "img": {"src", "alt", "title", "width", "height"},
             "th": {"align"}, "td": {"align"}, "sup": {"id"}, "li": {"id"}}
# Les vidéos YouTube intégrées sont permises dans vos articles, pas dans les synthèses
BALISES_REDACTION = BALISES | {"iframe"}
ATTRIBUTS_REDACTION = ATTRIBUTS | {"iframe": {"src", "width", "height", "title", "allowfullscreen"}}
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


def lien_valide(url):
    return isinstance(url, str) and re.match(r"^https?://[^\s\"'<>]+$", url.strip()) is not None


def nettoyer_html(html, type_):
    if type_ == "article":
        propre = nh3.clean(html, tags=BALISES_REDACTION, attributes=ATTRIBUTS_REDACTION,
                           url_schemes={"http", "https", "mailto"}, link_rel="noopener")
        # iframes : seulement YouTube
        return re.sub(r'<iframe(?![^>]*src="https://www\.youtube(-nocookie)?\.com/embed/)[^>]*>.*?</iframe>',
                      "", propre, flags=re.S)
    return nh3.clean(html, tags=BALISES, attributes=ATTRIBUTS,
                     url_schemes={"http", "https"}, link_rel="noopener")


def slugify(texte):
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def parse_date(valeur):
    if isinstance(valeur, datetime):
        d = valeur
    else:
        d = datetime.fromisoformat(str(valeur))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def date_fr(d):
    return f"{d.day} {MOIS[d.month - 1]} {d.year} à {d:%H:%M}"


def lire_contenus(dossier, type_):
    contenus = []
    for f in sorted((ROOT / "content" / dossier).glob("*.md")):
        if f.name.startswith("_"):
            continue
        texte = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", texte, re.S)
        if not m:
            print(f"  ! {f.name} : en-tête manquant, ignoré")
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        if meta.get("brouillon"):
            continue
        if type_ == "synthese" and passages_copies(f):
            print(f"  ! {f.name} : trop proche des sources, NON publiée (voir check_overlap.py)")
            continue
        date = parse_date(meta.get("date", datetime.fromtimestamp(f.stat().st_mtime, timezone.utc)))
        contenus.append({
            "type": type_,
            "titre": meta["titre"],
            "chapo": meta.get("chapo", ""),
            "rubrique": meta.get("rubrique", "Actualité"),
            "auteur": meta.get("auteur", "Rédaction" if type_ == "article" else "Synthèse automatique"),
            "sources": [s for s in meta.get("sources") or []
                        if isinstance(s, dict) and lien_valide(s.get("url"))],
            "date": date,
            "date_fr": date_fr(date),
            "slug": f.stem,
            "html": nettoyer_html(markdown.markdown(m.group(2), extensions=["extra"]), type_),
        })
    return contenus


def ecrire_sitemap(pages):
    # même adresse que la balise canonical : « / » plutôt que « /index.html »
    urls = "".join(
        f"<url><loc>{URL_SITE}/{'' if p == 'index.html' else p}</loc>"
        + (f"<lastmod>{d.strftime('%Y-%m-%dT%H:%M:%SZ')}</lastmod>" if d else "")
        + "</url>"
        for p, d in pages)
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>', encoding="utf-8")


def ecrire_archives(ecrire, items, contenus):
    """Une page par mois : synthèses et articles de la rédaction, puis tous les
    liens du fil, jour par jour (fil récent + data/archives/AAAA-MM.json)."""
    dossier = ROOT / "data" / "archives"
    tous = {i["id"]: i for i in items}
    for f in sorted(dossier.glob("*.json")) if dossier.exists() else []:
        for i in json.loads(f.read_text(encoding="utf-8")):
            if lien_valide(i.get("lien")):
                tous.setdefault(i["id"], i)
    mois = {}
    for i in tous.values():
        d = parse_date(i["date"])
        i["date_fr"] = date_fr(d)
        mois.setdefault(d.strftime("%Y-%m"), {}).setdefault(d.strftime("%Y-%m-%d"), []).append(i)
    for c in contenus:
        mois.setdefault(c["date"].strftime("%Y-%m"), {})
    liste = []
    for m in sorted(mois, reverse=True):
        annee, num = int(m[:4]), int(m[5:])
        nom = f"{MOIS[num - 1].capitalize()} {annee}"
        jours = [(f"{int(j[8:])} {MOIS[num - 1]} {annee}",
                  sorted(v, key=lambda i: i["date"], reverse=True))
                 for j, v in sorted(mois[m].items(), reverse=True)]
        une = [c for c in contenus if c["date"].strftime("%Y-%m") == m]
        ecrire(f"archives/{m}.html", "archives.html", "../", titre_page=f"Archives – {nom}",
               nom_mois=nom, une=une, jours=jours)
        liste.append((m, nom, sum(len(v) for _, v in jours), len(une)))
    ecrire("archives.html", "archives.html", "", titre_page="Archives", liste_mois=liste)


def main():
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    items = json.loads((ROOT / "data" / "items.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "items.json").exists() else []
    items = [i for i in items if lien_valide(i.get("lien"))]
    for i in items:
        i["date_fr"] = date_fr(parse_date(i["date"]))

    a_la_une = sorted(lire_contenus("articles", "article") + lire_contenus("syntheses", "synthese"),
                      key=lambda c: c["date"], reverse=True)
    presentes = {i["rubrique"] for i in items} | {c["rubrique"] for c in a_la_une}
    ORDRE = ["Politique", "Faits divers", "Sport", "Diaspora", "Économie", "Culture",
             "Afrique", "Monde", "Actualité"]
    rubriques = sorted(presentes, key=lambda r: (ORDRE.index(r) if r in ORDRE else len(ORDRE), r))
    sources = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))["sources"]

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "article").mkdir(parents=True)
    (OUT / "rubrique").mkdir()
    (OUT / "archives").mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")

    commun = {"nom_site": NOM_SITE, "url_site": URL_SITE, "contact": CONTACT, "description": DESCRIPTION, "rubriques": rubriques, "slugify": slugify,
              "maj": date_fr(datetime.now(timezone.utc))}

    pages = []

    def ecrire(chemin, template, racine, date=None, **ctx):
        (OUT / chemin).write_text(env.get_template(template).render(
            racine=racine, chemin=chemin, **commun, **ctx), encoding="utf-8")
        pages.append((chemin, date))

    # accueil : l'actualité du Sénégal ; l'Afrique et le Monde ont leurs onglets
    ecrire("index.html", "index.html", "", une=a_la_une[:12],
           fil=[i for i in items if i["rubrique"] not in ("Afrique", "Monde")][:80], titre_page=None)
    for r in rubriques:
        ecrire(f"rubrique/{slugify(r)}.html", "index.html", "../",
               une=[c for c in a_la_une if c["rubrique"] == r][:12],
               fil=[i for i in items if i["rubrique"] == r][:80], titre_page=r)
    for c in a_la_une:
        ecrire(f"article/{c['slug']}.html", "article.html", "../", date=c["date"], c=c, titre_page=c["titre"])
    ecrire("sources.html", "sources.html", "", sources=sources, titre_page="Nos sources")
    ecrire_archives(ecrire, items, a_la_une)
    ecrire("a-propos.html", "a-propos.html", "", titre_page="À propos")
    (OUT / ".nojekyll").touch()
    ecrire_sitemap(pages)
    (OUT / "flux.xml").write_text(env.get_template("flux.xml").render(
        une=a_la_une[:30], **commun), encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {URL_SITE}/sitemap.xml\n")
    print(f"Site construit : {len(a_la_une)} article(s)/synthèse(s), {len(items)} lien(s) dans le fil.")


if __name__ == "__main__":
    main()
