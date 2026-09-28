/*
 * Register the Sprite service worker (sprite_worker.js). The export keeps a
 * Sprite as a crop document over its texture, and serve.py answers a Sprite
 * image URL with that document; the worker renders the image, so every page
 * keeps linking to game/Unity/Sprite/<name>.png. On the first visit the page
 * loads before the worker controls it, so it reloads once the worker takes
 * over and the Sprite images it already requested are fetched again.
 */
(function () {
  "use strict";
  if (!("serviceWorker" in navigator) || !window.isSecureContext) return;
  const controlledAtLoad = Boolean(navigator.serviceWorker.controller);
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!controlledAtLoad) window.location.reload();
  });
  navigator.serviceWorker.register("sprite_worker.js", { scope: "./" }).catch((error) => {
    console.warn("[sprites] Sprite images need the service worker:", error);
  });
})();
