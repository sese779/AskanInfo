"""Publication automatique sur la chaîne Telegram d'AskanInfo.

Publie chaque nouvelle synthèse ou article (titre, chapô, lien) et chaque
nouvel épisode du podcast (fichier audio). Ne fait rien tant que les secrets
GitHub TELEGRAM_TOKEN (jeton du bot) et TELEGRAM_CANAL (ex. « @askaninfo »)
ne sont pas définis.

data/telegram.txt garde la liste de ce qui a déjà été publié. Au tout premier
passage, tout ce qui existe déjà est noté comme publié, sans rien envoyer
(pour ne pas inonder la chaîne).
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEJA = ROOT / "data" / "telegram.txt"
URL_SITE = os.environ.get("URL_SITE", "https://askaninfo.com").rstrip("/")
MAX_PAR_PASSAGE = 10


def appel(token, methode, donnees):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{methode}",
        data=urllib.parse.urlencode(donnees).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        rep = json.loads(r.read())
    if not rep.get("ok"):
        raise RuntimeError(rep.get("description", "erreur Telegram"))


def entete(f):
    m = re.match(r"^---\n(.*?)\n---\n", f.read_text(encoding="utf-8"), re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def contenus():
    """(clé, message ou épisode) dans l'ordre chronologique."""
    elements = []
    for dossier in ("syntheses", "articles"):
        for f in (ROOT / "content" / dossier).glob("[!_.]*.md"):
            meta = entete(f)
            if meta.get("brouillon"):
                continue
            elements.append((str(meta.get("date", f.stem)), f"{dossier}/{f.stem}", {
                "texte": "\n\n".join(x for x in [
                    f"📰 {meta.get('titre', '')}",
                    meta.get("chapo", ""),
                    f"{URL_SITE}/article/{f.stem}.html"] if x)}))
    for f in (ROOT / "data" / "podcast").glob("*.json"):
        audio = json.loads(f.read_text(encoding="utf-8"))
        nom = Path(audio["url"]).name
        elements.append((f.stem + "T19", f"podcast/{f.stem}", {
            "audio": f"{URL_SITE}/podcast/{nom}",
            "texte": f"🎧 La revue de presse d'AskanInfo du {f.stem[8:10]}/{f.stem[5:7]}/{f.stem[:4]}\n{URL_SITE}/podcast.html"}))
    return sorted(elements)


def main():
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    if not token or not canal:
        print("Telegram non configuré : rien à faire.")
        return
    tous = contenus()
    if not DEJA.exists():
        DEJA.write_text("".join(f"{cle}\n" for _, cle, _ in tous), encoding="utf-8")
        print(f"Premier passage : {len(tous)} contenu(s) existant(s) notés, rien n'est envoyé.")
        return
    deja = set(DEJA.read_text(encoding="utf-8").split())
    nouveaux = [(cle, el) for _, cle, el in tous if cle not in deja][:MAX_PAR_PASSAGE]
    for cle, el in nouveaux:
        try:
            if "audio" in el:
                appel(token, "sendAudio", {"chat_id": canal, "audio": el["audio"], "caption": el["texte"],
                                           "title": "AskanInfo – la revue de presse"})
            else:
                appel(token, "sendMessage", {"chat_id": canal, "text": el["texte"]})
        except Exception as e:  # on réessaiera au prochain passage
            print(f"  ! {cle} : {e}", file=sys.stderr)
            continue
        with DEJA.open("a", encoding="utf-8") as f:
            f.write(f"{cle}\n")
        print(f"  Telegram : {cle}")


if __name__ == "__main__":
    main()
