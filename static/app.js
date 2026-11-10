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
