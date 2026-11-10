// AskanInfo : active la lecture hors connexion et le bouton « Installer l'application ».
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}

let invitation = null;
window.addEventListener("beforeinstallprompt", (e) => {   // Android / Chrome
  e.preventDefault();
  invitation = e;
  document.querySelectorAll(".installer").forEach((b) => { b.hidden = false; });
});

document.addEventListener("click", async (e) => {
  const bouton = e.target.closest(".installer");
  if (!bouton || !invitation) return;
  invitation.prompt();
  await invitation.userChoice;
  invitation = null;
  bouton.hidden = true;
});

window.addEventListener("appinstalled", () => {
  document.querySelectorAll(".installer").forEach((b) => { b.hidden = true; });
  document.querySelectorAll(".deja-installee").forEach((b) => { b.hidden = false; });
});
