(() => {
  let projectileInitialized = false;
  let projectileObserver = null;
  let projectileGeneration = 0;
  let combatLanguage = "";
  let progressionLanguage = "";
  let missionPipelineLanguage = "";
  const trackedLoads = new Map();

  function currentLanguage() {
    return String(document.querySelector("#language")?.value || "CN").toUpperCase();
  }

  function errorText(view) {
    const english = {
      projectiles: "Combat and projectile data could not be loaded. Check the inline error and try opening the view again.",
      combat: "Combat relationships could not be loaded. Check the inline error and try opening the view again.",
      progression: "Progression data could not be loaded. Check the inline error and try opening the view again.",
      "mission-pipeline": "Mission pipeline data could not be loaded. Check the inline error and try opening the view again.",
      economy: "Factory data could not be loaded. Check the inline error and try opening the view again.",
      world: "World data could not be loaded. Check the inline error and try opening the view again.",
      presentation: "Presentation data could not be loaded. Check the inline error and try opening the view again.",
    };
    const chinese = {
      projectiles: "\u65e0\u6cd5\u52a0\u8f7d\u6295\u5c04\u7269\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
      combat: "\u65e0\u6cd5\u52a0\u8f7d\u6218\u6597\u5173\u7cfb\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
      progression: "\u65e0\u6cd5\u52a0\u8f7d\u6210\u957f\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
      "mission-pipeline": "\u65e0\u6cd5\u52a0\u8f7d\u4efb\u52a1\u7ba1\u7ebf\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
      economy: "\u65e0\u6cd5\u52a0\u8f7d\u5de5\u5382\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
      world: "\u65e0\u6cd5\u52a0\u8f7d\u4e16\u754c\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
      presentation: "\u65e0\u6cd5\u52a0\u8f7d\u5c55\u793a\u5173\u7cfb\u6570\u636e\u3002\u8bf7\u67e5\u770b\u9875\u9762\u5185\u9519\u8bef\u5e76\u91cd\u65b0\u6253\u5f00\u6b64\u89c6\u56fe\u3002",
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

  function initCombat(language = currentLanguage(), { force = false } = {}) {
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && combatLanguage === nextLanguage) return trackedLoads.get("combat")?.promise;
    combatLanguage = nextLanguage;
    const result = window.WebUICombat?.init?.({
      containerId: "gameplay-combat-relationships",
      language: nextLanguage,
    });
    if (!result) {
      combatLanguage = "";
      finishLoad("combat", false);
      return null;
    }
    if (typeof result.then === "function") {
      trackLoad("combat", result, () => combatLanguage === nextLanguage);
      result.catch(() => { if (combatLanguage === nextLanguage) combatLanguage = ""; });
    }
    return result;
  }

  function initProjectiles() {
    if (projectileInitialized) return true;
    const generation = ++projectileGeneration;
    projectileInitialized = true;
    beginLoad("projectiles");
    const initialized = window.WebUI?.projectiles?.init?.({
      container: "#projectile-inspector",
      dataPath: "data/gameplay/projectiles.json",
    });
    if (!initialized) {
      projectileInitialized = false;
      if (generation === projectileGeneration) finishLoad("projectiles", false);
      return false;
    }
    const container = document.querySelector("#projectile-inspector");
    projectileObserver?.disconnect();
    const syncState = () => {
      if (generation !== projectileGeneration) return;
      if (container?.querySelector(".projectile-error")) {
        projectileInitialized = false;
        finishLoad("projectiles", false);
        projectileObserver?.disconnect();
      } else if (container?.querySelector(".projectile-toolbar")) {
        finishLoad("projectiles", true);
        projectileObserver?.disconnect();
      }
    };
    projectileObserver = new MutationObserver(syncState);
    if (container) projectileObserver.observe(container, { childList: true, subtree: true });
    syncState();
    return true;
  }

  function initProgression(language = currentLanguage(), { force = false } = {}) {
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && progressionLanguage === nextLanguage) return trackedLoads.get("progression")?.promise;
    progressionLanguage = nextLanguage;
    const result = window.WebUI?.progression?.init?.({
      container: "#progression-app",
      language: nextLanguage,
    });
    if (!result) {
      progressionLanguage = "";
      finishLoad("progression", false);
      return null;
    }
    if (typeof result.then === "function") {
      trackLoad("progression", result, () => progressionLanguage === nextLanguage);
      result.then((value) => {
        if (!value && progressionLanguage === nextLanguage) progressionLanguage = "";
      }, () => {
        if (progressionLanguage === nextLanguage) progressionLanguage = "";
      });
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
    if (target === "projectiles") {
      const container = document.querySelector("#projectile-inspector");
      const loading = container?.firstElementChild?.matches?.(".projectile-empty:not(.projectile-error)");
      if (projectileInitialized && loading) return false;
      projectileObserver?.disconnect();
      projectileInitialized = false;
      return initProjectiles();
    }
    if (target === "combat") {
      combatLanguage = "";
      return initCombat(nextLanguage, { force: true });
    }
    if (target === "progression") {
      progressionLanguage = "";
      return initProgression(nextLanguage, { force: true });
    }
    if (target === "mission-pipeline") {
      missionPipelineLanguage = "";
      return initMissionPipeline(nextLanguage, { force: true });
    }
    if (target === "economy") {
      return trackLoad("economy", window.WebUI?.economy?.load?.(nextLanguage, true));
    }
    if (target === "world") {
      return trackLoad("world", window.WebUI?.world?.load?.(nextLanguage, true));
    }
    if (target === "presentation") {
      return trackLoad("presentation", window.WebUI?.presentation?.load?.(nextLanguage, true));
    }
    return false;
  }

  function activate(view) {
    if (view === "mission-pipeline") initMissionPipeline();
    if (view === "projectiles") initProjectiles();
    if (view === "combat") initCombat();
    if (view === "progression") initProgression();
    if (view === "economy") trackLoad("economy", window.WebUI?.economy?.load?.(currentLanguage()));
    if (view === "world") trackLoad("world", window.WebUI?.world?.load?.(currentLanguage()));
    if (view === "presentation") trackLoad("presentation", window.WebUI?.presentation?.load?.(currentLanguage()));
  }

  function initNextViews() {
    window.WebUI = window.WebUI || {};
    window.WebUI.retryView = retryView;
    window.WebUI?.economy?.init?.();
    window.WebUI?.presentation?.init?.();
    activate(String(document.body.dataset.activeView || window.location.hash.slice(1) || "story").toLowerCase());
    window.addEventListener("webui:view-changed", (event) => {
      activate(String(event.detail?.view || "").toLowerCase());
    });
    window.addEventListener("webui:language-changed", (event) => {
      const language = String(event.detail?.language || currentLanguage()).toUpperCase();
      if (document.body.dataset.activeView === "combat") initCombat(language);
      else combatLanguage = "";
      if (document.body.dataset.activeView === "progression") initProgression(language);
      else progressionLanguage = "";
      if (document.body.dataset.activeView === "mission-pipeline") initMissionPipeline(language);
      else missionPipelineLanguage = "";
      if (document.body.dataset.activeView === "economy") {
        trackLoad("economy", window.WebUI?.economy?.load?.(language));
      }
      if (document.body.dataset.activeView === "world") {
        trackLoad("world", window.WebUI?.world?.load?.(language));
      }
      if (document.body.dataset.activeView === "presentation") {
        trackLoad("presentation", window.WebUI?.presentation?.load?.(language));
      }
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
