// Affiche le texte du communiqué officiel du Conseil des ministres publié sur
// presidence.sn (page publique, ouverte dans un navigateur comme par un visiteur).
// Utilisé par l'agent de rédaction pour la synthèse des nominations
// (« mesures individuelles »). Aucune autre page n'est consultée.
//
//   node scripts/communique_conseil.js 2026-11-18 > communique.txt
//
// La date est celle du mercredi du Conseil. Code de sortie 2 si la page n'existe
// pas ou ne contient pas de communiqué.
const { chromium } = require("playwright");

const MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
  "aout", "septembre", "octobre", "novembre", "decembre"];
const JOURS = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];

function adresse(dateIso) {
  const [a, m, j] = dateIso.split("-").map(Number);
  const d = new Date(Date.UTC(a, m - 1, j));
  return "https://www.presidence.sn/fr/actualites/communique-du-conseil-des-ministres-du-"
    + `${JOURS[d.getUTCDay()]}-${j}-${MOIS[m - 1]}-${a}`;
}

(async () => {
  const date = process.argv[2];
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date || "")) {
    console.error("usage : node scripts/communique_conseil.js AAAA-MM-JJ");
    process.exit(1);
  }
  const url = adresse(date);
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const navigateur = await chromium.launch({ proxy });
  try {
    const page = await navigateur.newPage();
    await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
    const texte = await page.evaluate(() => document.body.innerText);
    const debut = texte.search(/COMMUNIQU[EÉ] DU CONSEIL DES MINISTRES/i);
    if (debut < 0) {
      console.error(`Pas de communiqué à cette adresse : ${url}`);
      process.exit(2);
    }
    const fin = texte.search(/Porte-Parole du Gouvernement/i);
    console.log(`Source : ${url}\n`);
    console.log(texte.slice(debut, fin > debut ? fin + 30 : undefined).trim());
  } finally {
    await navigateur.close();
  }
})().catch((e) => { console.error(e.message); process.exit(1); });
