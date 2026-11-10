// Service worker AskanInfo : lecture hors connexion des derniers articles.
// Généré par scripts/pwa.py (la version change à chaque mise à jour du site).
const CACHE = "askaninfo-__VERSION__";
const PAGES = __PAGES__;

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => Promise.allSettled(PAGES.map((p) => c.add(p))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((cles) => Promise.all(cles.filter((k) => k.startsWith("askaninfo-") && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;  // MP3, stats, liens externes : pas touchés
  if (url.pathname.endsWith(".mp3")) return;

  if (req.mode === "navigate") {
    // pages : toujours la version en ligne d'abord, la copie enregistrée si pas de réseau
    e.respondWith(
      fetch(req)
        .then((rep) => {
          const copie = rep.clone();
          caches.open(CACHE).then((c) => c.put(req, copie));
          return rep;
        })
        .catch(() => caches.match(req).then((r) => r || caches.match("/hors-ligne.html")))
    );
    return;
  }
  // feuilles de style, icônes, images : la copie enregistrée d'abord
  e.respondWith(caches.match(req).then((r) => r || fetch(req)));
});
