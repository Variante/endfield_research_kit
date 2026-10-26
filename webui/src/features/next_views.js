(() => {
  const WebUI = window.WebUI;
  let audioLanguage = "";
  let mapRecoveryLoaded = false;
  const trackedLoads = new Map();

  function currentLanguage() {
    return String(document.querySelector("#language")?.value || "CN").toUpperCase();
  }

  function errorText(view) {
    const english = {
      audio: "Audio-system data could not be loaded. Check the inline error and try opening the view again.",
      "map": "Map data could not be loaded. Check the inline error and try opening the view again.",
    };
    const chinese = {
      audio: "\u65e0\u6cd5\u52a0\u8f7d\u97f3\u9891\u7cfb\u7edf\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
      "map": "\u65e0\u6cd5\u52a0\u8f7d\u5730\u56fe\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u3002",
    };
    const locale = String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").toLowerCase();
    return (locale.startsWith("zh") ? chinese : english)[view] || english[view] || "Unable to load this view.";
  }

  function beginLoad(view) {
    WebUI.clearShellStatus(view);
    WebUI.setViewBusy(view, true);
  }

  function finishLoad(view, succeeded = true) {
    WebUI.setViewBusy(view, false);
    if (!succeeded && document.body.dataset.activeView === view) {
      WebUI.setShellStatus(errorText(view), { tone: "error", view });
    }
  }

  function trackLoad(view, result, onFailure, isCurrent = () => true) {
    // Both page loaders are async. Promise identity rejects obsolete completions.
    trackedLoads.set(view, result);
    beginLoad(view);
    const finish = (succeeded) => {
      if (trackedLoads.get(view) !== result || !isCurrent()) return;
      trackedLoads.delete(view);
      if (!succeeded) onFailure();
      finishLoad(view, succeeded);
    };
    result.then((value) => finish(value !== null && value !== false), () => finish(false));
    return result;
  }

  function initAudio(language = currentLanguage(), { force = false } = {}) {
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && audioLanguage === nextLanguage) return trackedLoads.get("audio");
    audioLanguage = nextLanguage;
    WebUI.audio.init();
    return trackLoad("audio", WebUI.audio.load(nextLanguage, { force }),
      () => { audioLanguage = ""; }, () => audioLanguage === nextLanguage);
  }

  function retryView(view = document.body.dataset.activeView, language = currentLanguage()) {
    const target = String(view || "").toLowerCase();
    const nextLanguage = String(language || currentLanguage()).toUpperCase();
    if (target === "audio") {
      audioLanguage = "";
      return initAudio(nextLanguage, { force: true });
    }
    if (target === "map") {
      mapRecoveryLoaded = false;
      return initMapRecovery();
    }
    return false;
  }

  function activate(view) {
    if (view === "audio") initAudio();
    if (view === "map") initMapRecovery();
  }

  function initMapRecovery() {
    if (mapRecoveryLoaded) return trackedLoads.get("map");
    mapRecoveryLoaded = true;
    WebUI.mapRecovery.init();
    return trackLoad("map", WebUI.mapRecovery.load(),
      () => { mapRecoveryLoaded = false; });
  }

  function initNextViews() {
    WebUI.retryView = retryView;
    activate(String(document.body.dataset.activeView || window.location.hash.slice(1) || "story").toLowerCase());
    window.addEventListener("webui:view-changed", (event) => {
      activate(String(event.detail?.view || "").toLowerCase());
    });
    window.addEventListener("webui:language-changed", (event) => {
      const language = String(event.detail?.language || currentLanguage()).toUpperCase();
      if (document.body.dataset.activeView === "audio") initAudio(language);
      else audioLanguage = "";
    });
    window.addEventListener("webui:retry-view", (event) => {
      retryView(event.detail?.view, event.detail?.language);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initNextViews, { once: true });
  } else {
    initNextViews();
  }
})();
