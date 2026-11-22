// AskanInfo : lecture hors connexion, bouton « Installer l'application »
// et bandeau d'invitation en haut du site.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}

const MEMOIRE_FERME = "askaninfo-bandeau-ferme";   // date de fermeture du bandeau
const MEMOIRE_INSTALLEE = "askaninfo-appli-installee";
const DELAI_RETOUR = 30 * 24 * 3600 * 1000;        // 30 jours

function lire(cle) { try { return localStorage.getItem(cle); } catch (e) { return null; } }
function ecrire(cle, valeur) { try { localStorage.setItem(cle, valeur); } catch (e) { /* navigation privée */ } }

// Statistiques GoatCounter (si activé) : événements anonymes, sans cookie.
function evenement(nom) {
  let essais = 0;
  const envoyer = () => {
    if (window.goatcounter && window.goatcounter.count) {
      window.goatcounter.count({ path: nom, title: nom, event: true });
    } else if (essais++ < 20) {
      setTimeout(envoyer, 500);   // le script de statistiques se charge en différé
    }
  };
  envoyer();
}

const dansLAppli = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
const ua = navigator.userAgent;
const surIOS = /iPhone|iPad|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
const safariIOS = surIOS && /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
const surMobile = surIOS || /Android|Mobi/i.test(ua);   // bandeau réservé aux téléphones et tablettes

function bandeauAutorise() {
  if (!surMobile || dansLAppli || lire(MEMOIRE_INSTALLEE)) return false;
  const ferme = Number(lire(MEMOIRE_FERME) || 0);
  return !ferme || Date.now() - ferme > DELAI_RETOUR;
}

function montrerBandeau(mode) {   // mode : "android" ou "ios"
  const b = document.getElementById("bandeau-appli");
  if (!b || !bandeauAutorise()) return;
  b.querySelector(mode === "ios" ? ".bandeau-ios" : ".installer").hidden = false;
  b.hidden = false;
}

function cacherBandeau() {
  const b = document.getElementById("bandeau-appli");
  if (b) b.hidden = true;
}

if (dansLAppli) {
  ecrire(MEMOIRE_INSTALLEE, "1");
  // une ouverture de l'application = un événement par session
  try {
    if (!sessionStorage.getItem("askaninfo-session")) {
      sessionStorage.setItem("askaninfo-session", "1");
      evenement("appli-ouverture");
    }
  } catch (e) { /* stockage indisponible */ }
}

let invitation = null;
window.addEventListener("beforeinstallprompt", (e) => {   // Android / Chrome / Edge
  e.preventDefault();
  invitation = e;
  document.querySelectorAll(".installer").forEach((b) => {
    if (!b.closest("#bandeau-appli")) b.hidden = false;      // bouton de la page Application
  });
  montrerBandeau("android");
});

document.addEventListener("DOMContentLoaded", () => {
  if (safariIOS) montrerBandeau("ios");                     // iPhone : pas d'installation en un clic
});

document.addEventListener("click", async (e) => {
  if (e.target.closest(".bandeau-fermer")) {
    ecrire(MEMOIRE_FERME, String(Date.now()));
    cacherBandeau();
    evenement("bandeau-ferme");
    return;
  }
  if (e.target.closest(".bandeau-ios")) evenement("bandeau-comment-faire");
  const bouton = e.target.closest(".installer");
  if (!bouton || !invitation) return;
  invitation.prompt();
  const choix = await invitation.userChoice;
  invitation = null;
  if (choix && choix.outcome === "accepted") ecrire(MEMOIRE_INSTALLEE, "1");
  evenement(choix && choix.outcome === "accepted" ? "appli-installation" : "appli-installation-refusee");
  document.querySelectorAll(".installer").forEach((b) => { b.hidden = true; });
  cacherBandeau();
});

window.addEventListener("appinstalled", () => {
  ecrire(MEMOIRE_INSTALLEE, "1");
  cacherBandeau();
  document.querySelectorAll(".installer").forEach((b) => { b.hidden = true; });
  document.querySelectorAll(".deja-installee").forEach((b) => { b.hidden = false; });
});

// Image de sujet introuvable : on retire le cadre plutôt que d'afficher une image cassée
document.addEventListener("error", function (e) {
  var f = e.target && e.target.closest && e.target.closest("figure.illustration");
  if (f) f.remove();
}, true);

// Ligne « Suivre AskanInfo » de l'accueil : masquée une fois qu'on a cliqué
// sur WhatsApp ou Telegram, ou qu'on l'a fermée (mémorisé sur cet appareil).
const MEMOIRE_SUIVRE = "askaninfo-suivre-masque";
document.addEventListener("DOMContentLoaded", () => {
  const l = document.getElementById("suivre-accueil");
  if (l && !lire(MEMOIRE_SUIVRE)) l.hidden = false;
});
document.addEventListener("click", (e) => {
  const lien = e.target.closest("[data-suivre]");
  const fermer = e.target.closest(".suivre-fermer");
  if (!lien && !fermer) return;
  ecrire(MEMOIRE_SUIVRE, "1");
  evenement(lien ? "suivre-" + lien.dataset.suivre : "suivre-masque");
  if (fermer) { const l = document.getElementById("suivre-accueil"); if (l) l.hidden = true; }
});

// Page « Message du jour » : bouton qui copie le texte prêt pour Facebook.
document.querySelectorAll("[data-copier]").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    const source = document.getElementById(bouton.dataset.copier);
    if (!source) return;
    const texte = source.textContent;
    const confirmer = () => {
      const initial = bouton.textContent;
      bouton.textContent = bouton.dataset.copie || "Copié ✓";
      setTimeout(() => { bouton.textContent = initial; }, 4000);
      evenement("partage-copie-facebook");
    };
    const secours = () => {
      // Anciens navigateurs : copie via une zone de texte temporaire.
      const zone = document.createElement("textarea");
      zone.value = texte;
      zone.setAttribute("readonly", "");
      zone.className = "hors-ecran";
      document.body.appendChild(zone);
      zone.select();
      try { document.execCommand("copy"); confirmer(); } catch (e) { /* rien */ }
      zone.remove();
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(texte).then(confirmer, secours);
    } else {
      secours();
    }
  });
});

// Page « Vidéo du jour » : bouton « Partager » (téléphones). Il copie la légende, puis
// ouvre le menu de partage du téléphone avec le fichier vidéo (TikTok, Instagram,
// WhatsApp…), sans passer par la galerie. Seulement pour les vidéos servies par le site.
const videosPretes = new Map();   // adresse → fichier déjà chargé
function partagePossible() {
  try {
    const essai = new File([new Blob([""], { type: "video/mp4" })], "essai.mp4", { type: "video/mp4" });
    return !!(navigator.share && navigator.canShare && navigator.canShare({ files: [essai] }));
  } catch (e) { return false; }
}
document.addEventListener("DOMContentLoaded", () => {
  if (!partagePossible()) return;
  document.querySelectorAll("[data-partager]").forEach((b) => {
    if (b.dataset.partager.startsWith("/")) b.hidden = false;
  });
});
document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-partager]");
  if (!b) return;
  const legende = document.getElementById(b.dataset.legende);
  if (legende && navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(legende.textContent).catch(() => {});
  }
  let fichier = videosPretes.get(b.dataset.partager);
  if (!fichier) {
    b.disabled = true;
    b.textContent = "Préparation…";
    try {
      const r = await fetch(b.dataset.partager);
      if (!r.ok) throw new Error(String(r.status));
      fichier = new File([await r.blob()], b.dataset.nom, { type: "video/mp4" });
      videosPretes.set(b.dataset.partager, fichier);
    } catch (err) {
      b.disabled = false;
      b.textContent = "Partager";
      const lien = b.parentElement.querySelector("a[download]");
      if (lien) lien.click();            // secours : téléchargement classique
      return;
    }
    b.disabled = false;
  }
  try {
    await navigator.share({ files: [fichier] });
    b.textContent = "Partager";
    evenement("video-partage");
  } catch (err) {
    // Le chargement a pris trop de temps : le téléphone demande un second appui.
    b.textContent = err && err.name === "NotAllowedError" ? "Toucher à nouveau pour partager" : "Partager";
  }
});
