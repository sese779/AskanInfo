"""Construit le site statique dans _site/ à partir de :
- data/items.json        (fil d'actualité : titres + liens vers les sources)
- content/articles/*.md  (vos articles, signés « Rédaction »)
- content/syntheses/*.md (synthèses écrites par l'agent)
"""

import json
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
NOM_SITE = "AskanInfo"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


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
        date = parse_date(meta.get("date", datetime.fromtimestamp(f.stat().st_mtime, timezone.utc)))
        contenus.append({
            "type": type_,
            "titre": meta["titre"],
            "chapo": meta.get("chapo", ""),
            "rubrique": meta.get("rubrique", "Actualité"),
            "auteur": meta.get("auteur", "Rédaction" if type_ == "article" else "Synthèse automatique"),
            "sources": meta.get("sources", []),
            "date": date,
            "date_fr": date_fr(date),
            "slug": f.stem,
            "html": markdown.markdown(m.group(2), extensions=["extra"]),
        })
    return contenus


def main():
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    items = json.loads((ROOT / "data" / "items.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "items.json").exists() else []
    for i in items:
        i["date_fr"] = date_fr(parse_date(i["date"]))

    a_la_une = sorted(lire_contenus("articles", "article") + lire_contenus("syntheses", "synthese"),
                      key=lambda c: c["date"], reverse=True)
    rubriques = sorted({i["rubrique"] for i in items} | {c["rubrique"] for c in a_la_une})
    sources = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))["sources"]

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "article").mkdir(parents=True)
    (OUT / "rubrique").mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")

    commun = {"nom_site": NOM_SITE, "rubriques": rubriques, "slugify": slugify,
              "maj": date_fr(datetime.now(timezone.utc))}

    def ecrire(chemin, template, racine, **ctx):
        (OUT / chemin).write_text(env.get_template(template).render(racine=racine, **commun, **ctx),
                                  encoding="utf-8")

    ecrire("index.html", "index.html", "", une=a_la_une[:12], fil=items[:80], titre_page=None)
    for r in rubriques:
        ecrire(f"rubrique/{slugify(r)}.html", "index.html", "../",
               une=[c for c in a_la_une if c["rubrique"] == r][:12],
               fil=[i for i in items if i["rubrique"] == r][:80], titre_page=r)
    for c in a_la_une:
        ecrire(f"article/{c['slug']}.html", "article.html", "../", c=c, titre_page=c["titre"])
    ecrire("sources.html", "sources.html", "", sources=sources, titre_page="Nos sources")
    ecrire("a-propos.html", "a-propos.html", "", titre_page="À propos")
    (OUT / ".nojekyll").touch()
    print(f"Site construit : {len(a_la_une)} article(s)/synthèse(s), {len(items)} lien(s) dans le fil.")


if __name__ == "__main__":
    main()
