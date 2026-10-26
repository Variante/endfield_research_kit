// Gameplay composes entity, item, stage and activity catalogs. This controller
// owns navigation and refresh; activities reuses Text and Assets publications
// on selection. Each renderer retains its own filters and detail layout.
(() => {
  const W = window.WebUI;
  const kinds = ["character", "weapon", "gem", "equipment", "item", "enemy", "stage", "activity"];
  const catalogs = { item: "items" };
  let selected = "character";
  let token = 0;
  let loadedLanguage = "";
  const active = () => document.body.dataset.activeView === "gameplay";

  function readKind() {
    const params = new URLSearchParams(location.search);
    const explicit = params.get("gameplayKind");
    return kinds.includes(explicit) ? explicit : selected;
  }

  function label(kind) {
    const zh = String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").startsWith("zh");
    return (zh
      ? { character: "角色", weapon: "武器", gem: "基质", equipment: "装备", item: "物品", enemy: "敌人", stage: "战斗关卡", activity: "活动" }
      : { character: "Characters", weapon: "Weapons", gem: "Essences", equipment: "Equipment", item: "Items", enemy: "Enemies", stage: "Combat stages", activity: "Activities" })[kind];
  }

  function render() {
    const root = document.querySelector("#gameplay-kind-tabs");
    if (!root) return;
    const focused = root.contains(document.activeElement) ? document.activeElement.dataset.gameplayKind : "";
    root.innerHTML = kinds.map((kind) => {
      const count = kind === "activity" ? W.gameplayActivities.count() : kind === "stage" ? W.battleStages?.count() : catalogs[kind] ? W.gameplayItems.count(catalogs[kind]) : W.gameplay.count(kind);
      return `<button type="button" class="page-mode-button${selected === kind ? " is-active" : ""}" data-gameplay-kind="${kind}" aria-pressed="${selected === kind}">${W.escapeHtml(label(kind))}${count == null ? "" : ` (${W.formatNumber(count)})`}</button>`;
    }).join("");
    root.setAttribute("aria-label", label("character") === "角色" ? "玩法数据集" : "Gameplay dataset");
    if (focused) root.querySelector(`[data-gameplay-kind="${focused}"]`)?.focus({ preventScroll: true });
  }

  async function route({ force = false } = {}) {
    if (!active()) return;
    const generation = ++token;
    loadedLanguage = String(document.querySelector("#language")?.value || "CN").toUpperCase();
    selected = readKind();
    const catalog = catalogs[selected];
    if (force) W.gameplay.invalidateItems();
    document.querySelector("#gameplay-app").hidden = !!catalog || selected === "stage" || selected === "activity";
    document.querySelector("#gameplay-items-app").hidden = !catalog;
    document.querySelector("#battle-stages-app").hidden = selected !== "stage";
    document.querySelector("#activities-app").hidden = selected !== "activity";
    render();
    const [data, catalogData, stageData] = await Promise.all([
      W.gameplay.load(force, { render: false }),
      W.gameplayItems.load(undefined, force, { render: false }),
      W.battleStages.load(force, { render: false }),
      W.gameplayActivities.loadCount(),
      selected === "activity" ? W.gameplayActivities.load(force) : null,
    ]);
    if (generation !== token || !active()) return;
    if (selected === "stage") {
      if (stageData) await W.battleStages.load();
    } else if (catalog) {
      if (catalogData) await W.gameplayItems.load();
    } else if (data && selected !== "activity") W.gameplay.selectKind(selected);
    if (generation !== token || !active()) return;
    render();
    window.dispatchEvent(new Event("resize"));
  }

  function pageUrl(kind, id = "", { fresh = false } = {}) {
    const url = new URL(location.href);
    for (const key of [...url.searchParams.keys()]) {
      if (fresh && !["ui", "uiLang", "lang"].includes(key)) url.searchParams.delete(key);
      if (key.startsWith("item") || ["gameplay", "gameplayKind", "activity", "activityTable", "battleStage"].includes(key)) url.searchParams.delete(key);
    }
    url.searchParams.set("gameplayKind", kind);
    if (kind === "activity") {
      url.searchParams.delete("activityTable");
      if (id) url.searchParams.set("activity", id);
    } else if (kind === "stage") {
      if (id) url.searchParams.set("battleStage", id);
    } else if (catalogs[kind]) {
      if (id) url.searchParams.set("gameplay", id.includes(":") ? id : `items:${id}`);
    } else if (id) url.searchParams.set("gameplay", `${kind}:${id}`);
    url.hash = "gameplay";
    return url.href;
  }

  function open(kind, id = "", options = {}) {
    if (!kinds.includes(kind)) return;
    selected = kind;
    history.pushState(history.state, "", pageUrl(kind, id, options));
    if (!active()) W.setActiveView("gameplay");
    else void route();
  }

  function init() {
    document.querySelector("#gameplay-kind-tabs")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-gameplay-kind]");
      if (button) open(button.dataset.gameplayKind);
    });
    window.addEventListener("webui:view-changed", (event) => { if (event.detail?.view === "gameplay") void route(); });
    window.addEventListener("webui:language-changed", () => {
      const language = String(document.querySelector("#language")?.value || "CN").toUpperCase();
      if (active() && language !== loadedLanguage) void route({ force: true });
    });
    window.addEventListener("webui:ui-locale-changed", render);
    window.addEventListener("webui:retry-view", (event) => { if (event.detail?.view === "gameplay") void route({ force: true }); });
    window.addEventListener("popstate", () => {
      // pushState can change datasets without changing the page hash.
      if (location.hash.toLowerCase() === "#gameplay") {
        if (active()) void route();
        else W.setActiveView("gameplay");
      }
    });
    render();
    void route();
  }

  W.gameplayTabs = { open, pageUrl, render, get kind() { return selected; } };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
