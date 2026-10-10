// Gameplay composes two independently published datasets. This controller
// owns their shared navigation; each renderer retains its filters and details.
(() => {
  const W = window.WebUI;
  const kinds = ["character", "weapon", "gem", "equipment", "item", "enemy", "recipe", "machine"];
  const catalogs = { item: "items", recipe: "recipes", machine: "machines" };
  const catalogKinds = Object.fromEntries(Object.entries(catalogs).map(([kind, catalog]) => [catalog, kind]));
  let selected = "character";
  let token = 0;
  const active = () => document.body.dataset.activeView === "gameplay";

  function readKind() {
    const params = new URLSearchParams(location.search);
    const explicit = params.get("gameplayKind");
    if (kinds.includes(explicit)) return explicit;
    const entry = params.get("gameplay") || params.get("gameplayId") || params.get("entry") || "";
    const kind = entry.split(":")[0];
    if (kinds.includes(kind)) return kind;
    const id = W.gameplay.normalizeSelection(entry);
    const resolved = W.gameplay.resolveKind(entry) || Object.entries({ chr_: "character", wpn_: "weapon", eqp_: "equipment", item_equip_: "equipment", item_: "item", eny_: "enemy" }).find(([prefix]) => id.startsWith(prefix))?.[1];
    return resolved || catalogKinds[params.get("productionKind")] || "character";
  }

  function label(kind) {
    const zh = String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").startsWith("zh");
    return (zh
      ? { character: "角色", weapon: "武器", gem: "基质", equipment: "装备", item: "物品", enemy: "敌人", recipe: "配方", machine: "设备与建筑" }
      : { character: "Characters", weapon: "Weapons", gem: "Essences", equipment: "Equipment", item: "Items", enemy: "Enemies", recipe: "Recipes", machine: "Machines & buildings" })[kind];
  }

  function render() {
    const root = document.querySelector("#gameplay-kind-tabs");
    if (!root) return;
    const focused = root.contains(document.activeElement) ? document.activeElement.dataset.gameplayKind : "";
    root.innerHTML = kinds.map((kind) => {
      const count = catalogs[kind] ? W.production.count(catalogs[kind]) : W.gameplay.count(kind);
      return `<button type="button" class="page-mode-button${selected === kind ? " is-active" : ""}" data-gameplay-kind="${kind}" aria-pressed="${selected === kind}">${W.escapeHtml(label(kind))}${count == null ? "" : ` (${W.formatNumber(count)})`}</button>`;
    }).join("");
    root.setAttribute("aria-label", label("character") === "角色" ? "玩法数据集" : "Gameplay dataset");
    if (focused) root.querySelector(`[data-gameplay-kind="${focused}"]`)?.focus({ preventScroll: true });
  }

  async function route({ force = false } = {}) {
    if (!active()) return;
    const generation = ++token;
    selected = readKind();
    const catalog = catalogs[selected];
    if (force) W.gameplay.invalidateItems();
    document.querySelector("#gameplay-app").hidden = !!catalog;
    document.querySelector("#production-app").hidden = !catalog;
    render();
    if (catalog) {
      W.hideLoader?.("gameplay");
      await W.production.load(undefined, force);
    } else {
      const data = await W.gameplay.load(force);
      if (data && generation === token && active()) {
        // Bare legacy IDs can be resolved exactly once the index is loaded.
        if (readKind() !== selected) { void route(); return; }
        W.gameplay.selectKind(selected);
      }
    }
    if (generation === token) render();
    window.dispatchEvent(new Event("resize"));
  }

  function pageUrl(kind, id = "") {
    const url = new URL(location.href);
    for (const key of [...url.searchParams.keys()]) {
      if (key.startsWith("production") || ["gameplay", "gameplayId", "entry", "gameplayKind"].includes(key)) url.searchParams.delete(key);
    }
    url.searchParams.set("gameplayKind", kind);
    if (catalogs[kind]) {
      url.searchParams.set("productionKind", catalogs[kind]);
      if (id) url.searchParams.set("productionId", id);
    } else if (id) url.searchParams.set("gameplay", `${kind}:${id}`);
    url.hash = "gameplay";
    return url.href;
  }

  function open(kind, id = "") {
    if (!kinds.includes(kind)) return;
    history.pushState(history.state, "", pageUrl(kind, id));
    if (!active()) W.setActiveView("gameplay");
    else void route();
  }

  function init() {
    document.querySelector("#gameplay-kind-tabs")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-gameplay-kind]");
      if (button) open(button.dataset.gameplayKind);
    });
    window.addEventListener("webui:view-changed", (event) => { if (event.detail?.view === "gameplay") void route(); });
    window.addEventListener("webui:language-changed", () => { if (active()) void route({ force: true }); });
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
