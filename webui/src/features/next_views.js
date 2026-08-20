(() => {
  let audioLanguage = "";
  let missionPipelineLanguage = "";
  let mapRecoveryLoaded = false;
  const trackedLoads = new Map();

  function currentLanguage() {
    return String(document.querySelector("#language")?.value || "CN").toUpperCase();
  }

  function errorText(view) {
    const english = {
      audio: "Audio-system data could not be loaded. Check the inline error and try opening the view again.",
      "mission-pipeline": "Mission pipeline data could not be loaded. Check the inline error and try opening the view again.",
      "map-recovery": "Map recovery data could not be loaded. Check the inline error and try opening the view again.",
    };
    const chinese = {
      audio: "\u65e0\u6cd5\u52a0\u8f7d\u97f3\u9891\u7cfb\u7edf\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
      "mission-pipeline": "\u65e0\u6cd5\u52a0\u8f7d\u4efb\u52a1\u7ba1\u7ebf\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
      "map-recovery": "\u65e0\u6cd5\u52a0\u8f7d\u5730\u56fe\u6062\u590d\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u3002",
    };
    const locale = String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").toLowerCase();
    return (locale.startsWith("zh") ? chinese : english)[view] || english[view] || "Unable to load this view.";
  }

  function beginLoad(view) {
    window.WebUI?.clearShellStatus?.(view);
    window.WebUI?.setViewBusy?.(view, true);
  }

  function finishLoad(view, succeeded = true) {
    window.WebUI?.setViewBusy?.(view, false);
    if (!succeeded && document.body.dataset.activeView === view) {
      window.WebUI?.setShellStatus?.(errorText(view), { tone: "error", view });
    }
  }

  function trackLoad(view, result, isCurrent = () => true) {
    if (!result || typeof result.then !== "function") return result;
    const previous = trackedLoads.get(view);
    const generation = (previous?.generation || 0) + 1;
    const tracked = { generation, promise: result };
    trackedLoads.set(view, tracked);
    beginLoad(view);
    result.then((value) => {
      const current = trackedLoads.get(view);
      if (current?.generation !== generation || current.promise !== result || !isCurrent()) return;
      trackedLoads.delete(view);
      finishLoad(view, value !== null && value !== false);
    }, () => {
      const current = trackedLoads.get(view);
      if (current?.generation !== generation || current.promise !== result || !isCurrent()) return;
      trackedLoads.delete(view);
      finishLoad(view, false);
    });
    return result;
  }

  function initAudio(language = currentLanguage(), { force = false } = {}) {
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && audioLanguage === nextLanguage) return trackedLoads.get("audio")?.promise;
    audioLanguage = nextLanguage;
    window.WebUI?.audio?.init?.();
    const result = window.WebUI?.audio?.load?.(nextLanguage, { force });
    if (!result) {
      audioLanguage = "";
      finishLoad("audio", false);
      return null;
    }
    if (typeof result.then === "function") {
      trackLoad("audio", result, () => audioLanguage === nextLanguage);
      result.catch(() => { if (audioLanguage === nextLanguage) audioLanguage = ""; });
    }
    return result;
  }

  function initMissionPipeline(language = currentLanguage(), { force = false } = {}) {
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && missionPipelineLanguage === nextLanguage) return trackedLoads.get("mission-pipeline")?.promise;
    missionPipelineLanguage = nextLanguage;
    window.WebUI?.missionPipeline?.init?.();
    const result = window.WebUI?.missionPipeline?.load?.(nextLanguage, { force });
    if (!result) {
      missionPipelineLanguage = "";
      finishLoad("mission-pipeline", false);
      return null;
    }
    if (typeof result.then === "function") {
      trackLoad("mission-pipeline", result, () => missionPipelineLanguage === nextLanguage);
      result.catch(() => { if (missionPipelineLanguage === nextLanguage) missionPipelineLanguage = ""; });
    }
    return result;
  }

  function retryView(view = document.body.dataset.activeView, language = currentLanguage()) {
    const target = String(view || "").toLowerCase();
    const nextLanguage = String(language || currentLanguage()).toUpperCase();
    if (target === "audio") {
      audioLanguage = "";
      return initAudio(nextLanguage, { force: true });
    }
    if (target === "mission-pipeline") {
      missionPipelineLanguage = "";
      return initMissionPipeline(nextLanguage, { force: true });
    }
    if (target === "map-recovery") {
      mapRecoveryLoaded = false;
      return initMapRecovery();
    }
    return false;
  }

  function activate(view) {
    if (view === "audio") initAudio();
    if (view === "mission-pipeline") initMissionPipeline();
    if (view === "map-recovery") initMapRecovery();
  }

  function initMapRecovery() {
    if (mapRecoveryLoaded) return trackedLoads.get("map-recovery")?.promise;
    mapRecoveryLoaded = true;
    window.WebUI?.mapRecovery?.init?.();
    const result = window.WebUI?.mapRecovery?.load?.();
    if (!result) { mapRecoveryLoaded = false; finishLoad("map-recovery", false); return null; }
    if (typeof result.then === "function") {
      trackLoad("map-recovery", result);
      result.catch(() => { mapRecoveryLoaded = false; });
    }
    return result;
  }

  function initNextViews() {
    window.WebUI = window.WebUI || {};
    window.WebUI.retryView = retryView;
    activate(String(document.body.dataset.activeView || window.location.hash.slice(1) || "story").toLowerCase());
    window.addEventListener("webui:view-changed", (event) => {
      activate(String(event.detail?.view || "").toLowerCase());
    });
    window.addEventListener("webui:language-changed", (event) => {
      const language = String(event.detail?.language || currentLanguage()).toUpperCase();
      if (document.body.dataset.activeView === "audio") initAudio(language);
      else audioLanguage = "";
      if (document.body.dataset.activeView === "mission-pipeline") initMissionPipeline(language);
      else missionPipelineLanguage = "";
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
