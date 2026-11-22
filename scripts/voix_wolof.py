"""Voix de synthèse en wolof, pour la vidéo wolof du soir.

Modèle : bilalfaye/speecht5_tts-wolof-v0.2 (licence MIT) et le vocodeur
microsoft/speecht5_hifigan (licence MIT), téléchargés depuis Hugging Face.
Timbre : voix d'homme enregistrée dans assets/voix-wolof.json (CMU ARCTIC).

Réglages validés à l'écoute par le propriétaire :
- lecture morceau par morceau (coupure à chaque virgule ou fin de phrase) ;
- un court silence donné au vocodeur avant et après chaque morceau, sinon le
  début des mots est avalé.

Dépendances (installées seulement quand une vidéo wolof est à faire) :
torch, transformers, sentencepiece, soundfile, numpy.

Usage : python scripts/voix_wolof.py "Texte en wolof." sortie.wav
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELE = "bilalfaye/speecht5_tts-wolof-v0.2"
VOCODEUR = "microsoft/speecht5_hifigan"
TAUX = 16000
HOP = 256          # échantillons par trame du spectrogramme
AMORCE = 20        # trames de silence données au vocodeur de chaque côté (0,3 s)
MARGE = 1600       # échantillons de silence gardés de chaque côté (0,1 s)
PAUSE = 2000       # silence entre deux morceaux (0,125 s)

_cache = {}


def _charger():
    if not _cache:
        import torch
        from transformers import SpeechT5ForTextToSpeech, SpeechT5HifiGan, SpeechT5Processor
        voix = json.loads((ROOT / "assets" / "voix-wolof.json").read_text(encoding="utf-8"))
        _cache.update(
            torch=torch,
            proc=SpeechT5Processor.from_pretrained(MODELE),
            modele=SpeechT5ForTextToSpeech.from_pretrained(MODELE),
            vocodeur=SpeechT5HifiGan.from_pretrained(VOCODEUR),
            timbre=torch.tensor(voix["xvector"]).unsqueeze(0),
        )
    return _cache


def _morceau(texte):
    c = _charger()
    torch = c["torch"]
    with torch.no_grad():
        ids = c["proc"](text=texte, return_tensors="pt")["input_ids"]
        spec = c["modele"].generate_speech(ids, c["timbre"], threshold=0.5)
        silence = spec.min(0).values.expand(AMORCE, -1)
        son = c["vocodeur"](torch.cat([silence, spec, silence])).numpy()
    return son[AMORCE * HOP - MARGE:len(son) - AMORCE * HOP + MARGE]


def dire(texte, wav):
    """Écrit le texte lu en wolof dans le fichier wav ; renvoie la durée en secondes."""
    import numpy as np
    import soundfile as sf
    sons = []
    for p in (p.strip() for p in re.split(r"(?<=[.,;:!?])\s+", texte.strip())):
        if p:
            sons += [_morceau(p), np.zeros(PAUSE, dtype="float32")]
    son = np.concatenate(sons)
    sf.write(str(wav), son, TAUX)
    return len(son) / TAUX


if __name__ == "__main__":
    print(f"{dire(sys.argv[1], sys.argv[2]):.1f} s")
