(() => {
  const DATA_VERSION = "20260715-econ1";
  const DEFAULT_CONTAINER = "#economy-app";
  const LIST_PAGE_SIZE = 100;
  const RELATION_PAGE_SIZE = 40;
  const VIEWS = ["recipes", "machines", "technology", "logistics", "resources", "shops", "activities"];
  const UI = {
    clear: "Clear search", retry: "Retry", results: "results", showing: "showing", of: "of", selected: "Selected",
    showMore: "Show more", incoming: "Incoming", outgoing: "Outgoing", evidence: "Evidence", capabilities: "Capabilities",
    searchLabel: "Search factory and economy data",
  };
  const TEXT = {
    en: {
      title: "Factory & Economy", search: "Search this section by name, item, or internal ID", loading: "Loading economy data…",
      eyebrow: "How the game's production and exchange rules connect", purpose: "Explore what items are made from, which facilities make them, and how technology, resources, shops, and rewards connect.",
      whyCare: "Why care? This is the quickest way to untangle a production chain, check a facility's intended role, or follow a cost or reward back to its game-data source.",
      startHere: "Start here", startHint: "Pick a question below, then search for an item name or internal ID and select a result.",
      questionRecipe: "How is an item made?", answerRecipe: "Open Recipes to compare the required inputs with the resulting output.", actionRecipe: "Browse recipes",
      questionMachine: "What can a facility do?", answerMachine: "Open Facilities to see its game-defined crafting, storage, power, or logistics capabilities.", actionMachine: "Browse facilities",
      questionUnlock: "What unlocks or pays for this?", answerUnlock: "Open Technology for prerequisites and costs, or Shops for currencies, prices, and rewards.", actionUnlock: "Trace unlocks",
      limits: "What this page can and cannot prove", limitsBody: "These are rules saved in the game's data files—not a live factory simulation. They can show declared inputs, outputs, links, and settings, but cannot prove current throughput, availability, shop rotation, inventory, or your account state.",
      terms: "Plain-language guide", termsBody: "A facility is a buildable machine. A recipe is a declared input-to-output rule. A connected record is a link between two saved records. Game-defined settings are the original fields retained for verification.",
      empty: "No records match. Try clearing the search or choosing another section.", noData: "Economy data is unavailable. Run scripts/build_economy_data.py.",
      recipes: "Recipes", machines: "Facilities", technology: "Technology unlocks", logistics: "Logistics rules", resources: "Power & resources",
      shops: "Shops", activities: "Activity rewards", inputs: "Required inputs", outputs: "Produces", configuration: "Game-defined settings (advanced)",
      source: "Game-data source", prerequisites: "Requires these technologies", rewards: "Gives", costs: "Costs", related: "Connected records",
      searchLabel: "Search factory and economy data", incoming: "Linked from", outgoing: "Links to", capabilities: "What this facility can do",
      scope: "Static authored configuration. Live throughput, availability, rotations, inventory, and account state are not inferred.",
    },
    zh: {
      title: "工厂与经济", search: "搜索名称、原始 ID、输入与产物", loading: "正在加载经济数据…",
      eyebrow: "了解游戏中的生产与交换规则如何连接", purpose: "查看物品由什么制成、哪些设施可以生产，以及科技、资源、商店与奖励之间的联系。",
      whyCare: "为什么值得看？这里可以快速理清生产链、确认设施的设计用途，并把消耗或奖励追溯到游戏数据来源。",
      startHere: "从这里开始", startHint: "先选择下面的一个问题，再搜索物品名称或内部 ID，然后选择结果。",
      questionRecipe: "物品是如何制造的？", answerRecipe: "打开配方，对照所需材料与最终产物。", actionRecipe: "浏览配方",
      questionMachine: "一个设施能做什么？", answerMachine: "打开设施，查看游戏设定的制造、储存、供电或物流能力。", actionMachine: "浏览设施",
      questionUnlock: "什么会解锁它，或者要用什么购买？", answerUnlock: "打开工业科技查看前置与消耗，或在商店查看货币、价格与奖励。", actionUnlock: "追踪解锁条件",
      limits: "本页能证明什么、不能证明什么", limitsBody: "这里展示的是游戏数据文件中保存的规则，并非实时工厂模拟。它能展示已声明的输入、产物、连接和设置，但不能证明当前产能、开放状态、商店轮换、库存或账号状态。",
      terms: "通俗术语指南", termsBody: "“设施”指可建造的机器；“配方”指已声明的输入到产物规则；“连接记录”指两个已保存记录之间的链接；“游戏设定”保留原始字段用于核验。",
      empty: "没有匹配记录。请尝试清空搜索或选择其他分类。", noData: "缺少经济数据，请运行 scripts/build_economy_data.py。",
      recipes: "配方", machines: "设施", technology: "工业科技", logistics: "物流", resources: "资源系统",
      shops: "商店", activities: "活动", inputs: "所需材料", outputs: "产物", configuration: "游戏设定（进阶）",
      source: "游戏数据来源", prerequisites: "所需前置科技", rewards: "获得", costs: "消耗", related: "连接记录",
      searchLabel: "搜索工厂与经济数据", incoming: "链接来源", outgoing: "链接到", capabilities: "该设施可以做什么",
      clear: "清空搜索", retry: "重试", results: "条结果", showing: "显示", of: "/", selected: "已选择", showMore: "显示更多", evidence: "证据",
      scope: "仅展示静态原始配置；不推算实时产能、开放状态、轮换、库存或账号状态。",
    },
  };

  const STATE = {
    container: null,
    language: "CN",
    uiLocale: "en",
    data: null,
    itemById: new Map(),
    view: "recipes",
    query: "",
    selectedKey: "",
    visibleLimit: LIST_PAGE_SIZE,
    relationLimit: RELATION_PAGE_SIZE,
    loading: null,
    lastError: "",
    loadToken: 0,
    abortController: null,
    initialized: false,
    listeners: [],
  };

  const webui = () => window.WebUI || {};
  const esc = (value) => {
    if (webui().escapeHtml) return webui().escapeHtml(value == null ? "" : String(value));
    const node = document.createElement("div");
    node.textContent = value == null ? "" : String(value);
    return node.innerHTML;
  };
  const format = (value) => {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value === "number" && Number.isFinite(value)) return value.toLocaleString();
    if (typeof value === "boolean") return value ? "true" : "false";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  };
  const readable = (value) => String(value || "").replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const t = (key) => (TEXT[STATE.uiLocale] || TEXT.en)[key] || TEXT.en[key] || UI[key] || key;
  const itemName = (id) => STATE.itemById?.get(String(id || ""))?.name || String(id || "");
  const dataPath = (language) => `data/lang/${encodeURIComponent(language)}/economy/index.json?v=${DATA_VERSION}`;

  function detectLocale() {
    const raw = String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "en").toLowerCase();
    return raw.startsWith("zh") ? "zh" : "en";
  }

  function currentLanguage() {
    return String(document.querySelector("#language")?.value || STATE.language || "CN").toUpperCase();
  }

  function isActive() {
    return document.body.dataset.activeView === "economy" || location.hash.replace(/^#/, "").toLowerCase() === "economy";
  }

  function listen(target, name, handler) {
    target?.addEventListener(name, handler);
    STATE.listeners.push(() => target?.removeEventListener(name, handler));
  }

  function shellHtml() {
    return `<section class="economy-shell" aria-label="${esc(t("title"))}">
      <header class="economy-header">
        <div class="economy-heading"><span class="economy-eyebrow">${esc(t("eyebrow"))}</span><h1>${esc(t("title"))}</h1><p>${esc(t("purpose"))}</p><p class="economy-why">${esc(t("whyCare"))}</p></div>
        <div class="economy-search"><label for="economy-search">${esc(t("searchLabel"))}</label><div><input id="economy-search" type="search" value="${esc(STATE.query)}" placeholder="${esc(t("search"))}" autocomplete="off" aria-controls="economy-list"><button type="button" data-economy-clear ${STATE.query ? "" : "disabled"}>${esc(t("clear"))}</button></div></div>
      </header>
      <section class="economy-guide" aria-labelledby="economy-start-title">
        <div class="economy-guide-heading"><h2 id="economy-start-title">${esc(t("startHere"))}</h2><p>${esc(t("startHint"))}</p></div>
        <div class="economy-question-grid">
          ${questionCard("recipes", "questionRecipe", "answerRecipe", "actionRecipe")}
          ${questionCard("machines", "questionMachine", "answerMachine", "actionMachine")}
          ${questionCard("technology", "questionUnlock", "answerUnlock", "actionUnlock")}
        </div>
        <div class="economy-guide-notes">
          <details><summary>${esc(t("limits"))}</summary><p>${esc(t("limitsBody"))}</p><p class="economy-source-scope">${esc(STATE.uiLocale === "en" ? (STATE.data?.scopeNote || t("scope")) : t("scope"))}</p></details>
          <details><summary>${esc(t("terms"))}</summary><p>${esc(t("termsBody"))}</p></details>
        </div>
      </section>
      <nav class="economy-tabs" role="tablist" aria-label="${esc(t("title"))}">${VIEWS.map((view) => `<button id="economy-view-${view}" type="button" role="tab" aria-controls="economy-view-panel" aria-selected="${STATE.view === view}" tabindex="${STATE.view === view ? "0" : "-1"}" data-economy-view="${view}" class="${STATE.view === view ? "is-active" : ""}">${esc(t(view))}<span>${esc(viewCount(view))}</span></button>`).join("")}</nav>
      <div class="economy-workspace" id="economy-view-panel" role="tabpanel" aria-labelledby="economy-view-${STATE.view}"><aside class="economy-list" id="economy-list" role="region" aria-label="${esc(t(STATE.view))}" aria-describedby="economy-result-status"></aside><main class="economy-detail" id="economy-detail" tabindex="-1"></main></div>
    </section>`;
  }

  function questionCard(view, questionKey, answerKey, actionKey) {
    return `<article class="economy-question"><h3>${esc(t(questionKey))}</h3><p>${esc(t(answerKey))}</p><button type="button" data-economy-start="${esc(view)}">${esc(t(actionKey))}<span aria-hidden="true"> →</span></button></article>`;
  }

  function resourceEntries() {
    const resources = STATE.data?.resources || {};
    return [
      ...(resources.power || []).map((row) => ({ ...row, resourceKind: "power", title: row.id })),
      ...(resources.fuels || []).map((row) => ({ ...row, id: row.itemId, resourceKind: "fuel", title: itemName(row.itemId) })),
      ...(resources.batteries || []).map((row) => ({ ...row, id: row.itemId, resourceKind: "battery", title: itemName(row.itemId) })),
      ...(resources.liquids || []).map((row) => ({ ...row, id: row.itemId, resourceKind: "liquid", title: itemName(row.itemId) })),
      ...(resources.mining || []).map((row) => ({ ...row, resourceKind: "mining", title: row.id })),
      ...(resources.sewage || []).map((row) => ({ ...row, resourceKind: "sewage", title: row.name || (row.itemId ? itemName(row.itemId) : row.id) })),
    ];
  }

  function shopEntries() {
    const data = STATE.data || {};
    return [
      ...(data.shopGroups || []).map((row) => ({ ...row, shopKind: "group", title: row.name })),
      ...(data.shops || []).map((row) => ({ ...row, shopKind: "shop", title: row.name })),
      ...(data.goods || []).map((row) => ({ ...row, shopKind: "goods", title: (row.reward?.items || []).map((v) => itemName(v.itemId)).join(" + ") || row.id })),
    ];
  }

  function activityEntries() {
    const data = STATE.data || {};
    return [
      ...(data.activities || []).map((row) => ({ ...row, activityKind: "activity", title: row.name })),
      ...(data.activityMilestones || []).map((row) => ({ ...row, id: `${row.activityId}:${row.stageKey || row.stageId}`, activityKind: "milestone", title: `${row.activityId} / ${row.stageKey || row.stageId}` })),
    ];
  }

  function viewEntries(view = STATE.view) {
    const data = STATE.data || {};
    if (view === "recipes") return (data.recipes || []).map((row) => ({ ...row, title: row.name }));
    if (view === "machines") return (data.machines || []).map((row) => ({ ...row, title: row.name }));
    if (view === "technology") return (data.technologies?.nodes || []).map((row) => ({ ...row, title: row.name }));
    if (view === "logistics") return (data.logistics || []).map((row) => ({ ...row, title: row.name }));
    if (view === "resources") return resourceEntries();
    if (view === "shops") return shopEntries();
    if (view === "activities") return activityEntries();
    return [];
  }

  function viewCount(view) {
    return STATE.data ? viewEntries(view).length.toLocaleString() : "0";
  }

  function entryKey(entry) {
    return `${STATE.view}:${entry.shopKind || entry.activityKind || entry.resourceKind || entry.kind || "entry"}:${entry.id}`;
  }

  function searchText(entry) {
    const ids = [];
    const gather = (value) => {
      if (Array.isArray(value)) value.forEach(gather);
      else if (value && typeof value === "object") Object.entries(value).forEach(([key, child]) => { if (/id$/i.test(key)) ids.push(format(child)); gather(child); });
    };
    gather(entry);
    return [entry.id, entry.title, entry.name, entry.description, entry.kind, entry.resourceKind, entry.shopKind, entry.activityKind, ...ids].join(" ").toLowerCase();
  }

  function filteredEntries() {
    const tokens = STATE.query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const rows = viewEntries();
    return tokens.length ? rows.filter((row) => tokens.every((token) => searchText(row).includes(token))) : rows;
  }

  function badge(value) {
    return value ? `<span class="economy-badge">${esc(value)}</span>` : "";
  }

  function focusEconomyRow(key) {
    if (!key) return;
    const row = [...(STATE.container?.querySelectorAll("[data-economy-key]") || [])].find((node) => node.dataset.economyKey === key);
    row?.focus();
  }

  function renderList(focusKey = "") {
    const root = STATE.container?.querySelector("#economy-list");
    if (!root) return;
    const rows = filteredEntries();
    const total = viewEntries().length;
    const clear = STATE.container?.querySelector("[data-economy-clear]");
    if (clear) clear.disabled = !STATE.query;
    if (!rows.length) {
      root.innerHTML = `<div class="economy-list-count" id="economy-result-status" role="status" aria-live="polite">0 ${esc(t("results"))} / ${total.toLocaleString()}</div><div class="economy-note">${esc(t("empty"))}</div>`;
      renderDetail(null);
      return;
    }
    if (!rows.some((row) => entryKey(row) === STATE.selectedKey)) STATE.selectedKey = entryKey(rows[0]);
    const selected = rows.find((row) => entryKey(row) === STATE.selectedKey);
    const visibleRows = rows.slice(0, STATE.visibleLimit);
    const selectedIsPinned = selected && !visibleRows.includes(selected);
    if (selectedIsPinned) {
      if (visibleRows.length >= STATE.visibleLimit) visibleRows[visibleRows.length - 1] = selected;
      else visibleRows.push(selected);
    }
    root.innerHTML = `<div class="economy-list-count" id="economy-result-status" role="status" aria-live="polite">${esc(t("showing"))} ${Math.min(STATE.visibleLimit, rows.length).toLocaleString()} ${esc(t("of"))} ${rows.length.toLocaleString()} ${esc(t("results"))}${rows.length !== total ? ` / ${total.toLocaleString()} total` : ""}</div>${visibleRows.map((row) => {
      const key = entryKey(row);
      const kind = row.kind || row.resourceKind || row.shopKind || row.activityKind || "";
      const isSelected = key === STATE.selectedKey;
      return `<button type="button" ${isSelected ? 'aria-current="true"' : ""} class="economy-row ${isSelected ? "is-selected" : ""}" data-economy-key="${esc(key)}">
        <span class="economy-row-title">${esc(row.title || row.id)}${selectedIsPinned && isSelected ? ` <small>${esc(t("selected"))}</small>` : ""}</span><span class="economy-row-id">${esc(row.id)}</span>${badge(kind)}
      </button>`;
    }).join("")}${STATE.visibleLimit < rows.length ? `<button type="button" class="economy-show-more" data-economy-more>${esc(t("showMore"))} (${Math.min(LIST_PAGE_SIZE, rows.length - STATE.visibleLimit).toLocaleString()})</button>` : ""}`;
    renderDetail(rows.find((row) => entryKey(row) === STATE.selectedKey) || rows[0]);
    focusEconomyRow(focusKey);
  }

  function itemBundleHtml(groups, heading) {
    if (!groups?.length) return "";
    const normalized = groups.map((group) => Array.isArray(group) ? group : [group]);
    return section(heading, `<div class="economy-bundles">${normalized.map((group) => `<div class="economy-bundle">${group.map((row) => `<span><b>${esc(itemName(row.itemId))}</b><code>${esc(row.itemId)}</code><em>× ${esc(format(row.count))}</em></span>`).join(`<i>or</i>`)}</div>`).join("")}</div>`);
  }

  function factsHtml(entries) {
    return `<dl class="economy-facts">${entries.filter(([, value]) => value !== undefined && value !== null && value !== "" && !(Array.isArray(value) && !value.length)).map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(format(value))}</dd></div>`).join("")}</dl>`;
  }

  function section(title, body, open = true) {
    return body ? `<details class="economy-section" ${open ? "open" : ""}><summary>${esc(title)}</summary><div>${body}</div></details>` : "";
  }

  function sourceHtml(source) {
    return source?.table ? section(t("source"), factsHtml([["table", source.table], ["id", source.id]]), false) : "";
  }

  function recipeDetail(row) {
    return itemBundleHtml(row.inputs, t("inputs")) + itemBundleHtml(row.outputs, t("outputs")) + section(t("configuration"), factsHtml([
      ["kind", row.kind], ["machineId", row.machineId], ["formulaGroupId", row.formulaGroupId], ["domainId", row.domainId],
      ["defaultUnlock", row.defaultUnlock], ["progressRound", row.progressRound], ["totalProgress", row.totalProgress], ["usableLevel", row.usableLevel],
    ])) + sourceHtml(row.source);
  }

  function machineDetail(row) {
    const capabilities = (row.capabilities || []).map((cap) => `<article><h3>${esc(readable(cap.kind))}</h3>${factsHtml(Object.entries(cap).filter(([key]) => !["kind", "sourceTable"].includes(key)))}</article>`).join("");
    return section(t("configuration"), factsHtml([["buildItemId", row.buildItemId], ...Object.entries(row.config || {})])) + section(t("capabilities"), capabilities) + sourceHtml(row.source);
  }

  function technologyDetail(row) {
    return itemBundleHtml((row.costs || []).map((v) => [v]), t("costs")) + itemBundleHtml((row.rewards || []).map((v) => [v]), t("rewards")) + section(t("configuration"), factsHtml([
      ["groupId", row.groupId], ["categoryId", row.categoryId], ["layerId", row.layerId], ["costPointCount", row.costPointCount],
      ["authoredAlreadyUnlock", row.authoredAlreadyUnlock], ["defaultHidden", row.defaultHidden], ["action", row.action],
    ])) + section(t("prerequisites"), (row.preNodeIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")) + sourceHtml(row.source);
  }

  function shopDetail(row) {
    if (row.shopKind === "goods") return itemBundleHtml(((row.reward || {}).items || []).map((v) => [v]), t("rewards")) + section(t("configuration"), factsHtml([
      ["shopId", row.shopId], ["moneyItemId", row.moneyItemId], ["price", row.price], ["discount", row.discount],
      ["limitCount", row.limitCount], ["limitRefreshType", row.limitRefreshType], ["authoredVisibleWhenLocked", row.authoredVisibleWhenLocked],
    ])) + sourceHtml(row.source);
    return section(t("configuration"), factsHtml(Object.entries(row).filter(([key]) => !["title", "source"].includes(key)))) + sourceHtml(row.source);
  }

  function genericDetail(row) {
    const entries = Object.entries(row || {}).filter(([key]) => !["title", "source", "description", "name"].includes(key));
    const reward = row.reward?.items || [];
    return itemBundleHtml(reward.map((v) => [v]), t("rewards")) + section(t("configuration"), factsHtml(entries)) + sourceHtml(row.source);
  }

  function relationNodeId(row) {
    if (STATE.view === "recipes") return `recipe:${row.id}`;
    if (STATE.view === "machines") return `machine:${row.id}`;
    if (STATE.view === "technology") return `tech:${row.id}`;
    if (STATE.view === "shops" && row.shopKind === "goods") return `shopGood:${row.id}`;
    if (STATE.view === "activities" && row.activityKind === "activity") return `activity:${row.id}`;
    if (STATE.view === "resources" && row.itemId) return `item:${row.itemId}`;
    return "";
  }

  function relationsHtml(row) {
    const nodeId = relationNodeId(row);
    if (!nodeId) return "";
    const relations = (STATE.data?.relations || []).filter((relation) => relation.from === nodeId || relation.to === nodeId);
    if (!relations.length) return "";
    const visible = relations.slice(0, STATE.relationLimit);
    const body = `<div class="economy-relations">${visible.map((relation) => {
      const outgoing = relation.from === nodeId;
      const other = outgoing ? relation.to : relation.from;
      const target = resolveRelationNode(other);
      const targetHtml = target
        ? `<button type="button" data-economy-node="${esc(other)}" aria-label="${esc(`${outgoing ? t("outgoing") : t("incoming")} ${relation.kind}: ${target.row.title || target.row.id}`)}"><b>${esc(target.row.title || target.row.id)}</b><code>${esc(other)}</code></button>`
        : `<code>${esc(other)}</code>`;
      return `<div class="economy-relation" tabindex="-1"><span>${esc(outgoing ? t("outgoing") : t("incoming"))}</span><b>${esc(readable(relation.kind))}</b>${targetHtml}<small>${relation.sourceTable ? `${esc(t("source"))}: ${esc(relation.sourceTable)}` : ""}</small></div>`;
    }).join("")}${relations.length > visible.length ? `<button type="button" class="economy-show-more" data-economy-relations-more>${esc(t("showMore"))} (${Math.min(RELATION_PAGE_SIZE, relations.length - STATE.relationLimit).toLocaleString()})</button>` : ""}</div>`;
    return section(t("related"), body, false);
  }

  function resolveRelationNode(nodeId) {
    const mappings = [["recipe:", "recipes"], ["machine:", "machines"], ["tech:", "technology"], ["shopGood:", "shops"], ["activity:", "activities"], ["item:", "resources"]];
    const mapping = mappings.find(([prefix]) => nodeId.startsWith(prefix));
    if (!mapping) return null;
    const [prefix, view] = mapping;
    const id = nodeId.slice(prefix.length);
    const row = viewEntries(view).find((entry) => String(entry.id) === id || String(entry.itemId || "") === id);
    return row ? { view, row } : null;
  }

  function navigateToNode(nodeId) {
    const target = resolveRelationNode(nodeId);
    if (!target) return;
    STATE.view = target.view;
    STATE.selectedKey = entryKey(target.row);
    STATE.visibleLimit = LIST_PAGE_SIZE;
    STATE.relationLimit = RELATION_PAGE_SIZE;
    render();
    focusEconomyRow(STATE.selectedKey);
  }

  function renderDetail(row) {
    const root = STATE.container?.querySelector("#economy-detail");
    if (!root) return;
    if (!row) { root.innerHTML = `<div class="economy-note">${esc(t("empty"))}</div>`; return; }
    let body = genericDetail(row);
    if (STATE.view === "recipes") body = recipeDetail(row);
    else if (STATE.view === "machines") body = machineDetail(row);
    else if (STATE.view === "technology") body = technologyDetail(row);
    else if (STATE.view === "shops") body = shopDetail(row);
    root.innerHTML = `<article class="economy-detail-card" aria-labelledby="economy-detail-title"><header><div>${badge(row.kind || row.resourceKind || row.shopKind || row.activityKind)}<h2 id="economy-detail-title">${esc(row.title || row.name || row.id)}</h2></div><code>${esc(row.id)}</code>${row.description ? `<p>${esc(row.description)}</p>` : ""}</header>${body}${relationsHtml(row)}</article>`;
  }

  function render() {
    if (!STATE.container) return;
    if (!STATE.data) {
      STATE.container.innerHTML = `<div class="economy-note economy-state" role="${STATE.lastError ? "alert" : "status"}"><strong>${esc(STATE.loading ? t("loading") : t("noData"))}</strong>${STATE.lastError ? `<small>${esc(STATE.lastError)}</small><button type="button" data-economy-retry>${esc(t("retry"))}</button>` : ""}</div>`;
      return;
    }
    STATE.container.innerHTML = shellHtml();
    renderList();
  }

  async function load(language = currentLanguage(), force = false) {
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && STATE.data && STATE.language === nextLanguage) return STATE.data;
    if (!force && STATE.loading && STATE.language === nextLanguage) return STATE.loading;
    STATE.abortController?.abort();
    const controller = new AbortController();
    const token = ++STATE.loadToken;
    STATE.abortController = controller;
    STATE.language = nextLanguage;
    STATE.lastError = "";
    STATE.data = null;
    STATE.itemById = new Map();
    STATE.loading = Promise.resolve(null);
    render();
    STATE.loading = (async () => {
      try {
        const fetcher = webui().fetchWithProgress || window.fetch.bind(window);
        const response = await fetcher(dataPath(nextLanguage), { signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        if (token !== STATE.loadToken) return null;
        STATE.data = payload;
        STATE.itemById = new Map((payload.items || []).map((row) => [String(row.id || ""), row]));
        const familiarRecipe = (payload.recipes || []).find((row) => row.id === "dismantler_copper_water_1");
        STATE.selectedKey = familiarRecipe ? `recipes:${familiarRecipe.kind || "entry"}:${familiarRecipe.id}` : "";
        STATE.visibleLimit = LIST_PAGE_SIZE;
        STATE.relationLimit = RELATION_PAGE_SIZE;
        return STATE.data;
      } catch (error) {
        if (error?.name === "AbortError" || token !== STATE.loadToken) return null;
        STATE.data = null;
        STATE.itemById = new Map();
        STATE.lastError = error instanceof Error ? error.message : String(error);
        console.warn("Economy data load failed", error);
        return null;
      } finally {
        if (token === STATE.loadToken) {
          STATE.loading = null;
          STATE.abortController = null;
          render();
        }
      }
    })();
    return STATE.loading;
  }

  function bindEvents() {
    listen(STATE.container, "input", (event) => {
      if (event.target?.id !== "economy-search") return;
      STATE.query = event.target.value || "";
      STATE.visibleLimit = LIST_PAGE_SIZE;
      renderList();
    });
    listen(STATE.container, "click", (event) => {
      if (event.target.closest("[data-economy-retry]")) {
        const retry = webui().retryViewLoad || webui().retryView;
        if (typeof retry === "function") retry("economy", currentLanguage());
        else load(currentLanguage(), true);
        return;
      }
      if (event.target.closest("[data-economy-clear]")) {
        STATE.query = "";
        STATE.visibleLimit = LIST_PAGE_SIZE;
        render();
        STATE.container?.querySelector("#economy-search")?.focus();
        return;
      }
      const startButton = event.target.closest("[data-economy-start]");
      if (startButton) {
        STATE.view = VIEWS.includes(startButton.dataset.economyStart) ? startButton.dataset.economyStart : STATE.view;
        STATE.query = "";
        STATE.selectedKey = "";
        STATE.visibleLimit = LIST_PAGE_SIZE;
        STATE.relationLimit = RELATION_PAGE_SIZE;
        render();
        STATE.container?.querySelector("#economy-search")?.focus();
        return;
      }
      if (event.target.closest("[data-economy-more]")) {
        const previousLimit = STATE.visibleLimit;
        STATE.visibleLimit += LIST_PAGE_SIZE;
        renderList();
        const nextMore = STATE.container?.querySelector("[data-economy-more]");
        const rows = [...(STATE.container?.querySelectorAll("[data-economy-key]") || [])];
        (nextMore || rows[Math.min(previousLimit, rows.length - 1)])?.focus();
        return;
      }
      if (event.target.closest("[data-economy-relations-more]")) {
        const previousLimit = STATE.relationLimit;
        STATE.relationLimit += RELATION_PAGE_SIZE;
        const selected = filteredEntries().find((row) => entryKey(row) === STATE.selectedKey);
        renderDetail(selected || null);
        const nextMore = STATE.container?.querySelector("[data-economy-relations-more]");
        const relations = [...(STATE.container?.querySelectorAll(".economy-relation") || [])];
        (nextMore || relations[Math.min(previousLimit, relations.length - 1)])?.focus();
        return;
      }
      const relationButton = event.target.closest("[data-economy-node]");
      if (relationButton) { navigateToNode(relationButton.dataset.economyNode || ""); return; }
      const viewButton = event.target.closest("[data-economy-view]");
      if (viewButton) {
        STATE.view = VIEWS.includes(viewButton.dataset.economyView) ? viewButton.dataset.economyView : STATE.view;
        STATE.selectedKey = "";
        STATE.visibleLimit = LIST_PAGE_SIZE;
        STATE.relationLimit = RELATION_PAGE_SIZE;
        render();
        STATE.container?.querySelector(`[data-economy-view="${STATE.view}"]`)?.focus();
        return;
      }
      const row = event.target.closest("[data-economy-key]");
      if (row) {
        STATE.selectedKey = row.dataset.economyKey || "";
        STATE.relationLimit = RELATION_PAGE_SIZE;
        renderList(STATE.selectedKey);
      }
    });
    listen(STATE.container, "keydown", (event) => {
      const tab = event.target.closest?.("[data-economy-view]");
      if (tab && ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        const current = VIEWS.indexOf(tab.dataset.economyView);
        const next = event.key === "Home" ? 0 : event.key === "End" ? VIEWS.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + VIEWS.length) % VIEWS.length;
        STATE.view = VIEWS[next];
        STATE.selectedKey = "";
        STATE.visibleLimit = LIST_PAGE_SIZE;
        STATE.relationLimit = RELATION_PAGE_SIZE;
        render();
        STATE.container?.querySelector(`[data-economy-view="${STATE.view}"]`)?.focus();
        return;
      }
      const row = event.target.closest?.("[data-economy-key]");
      if (!row || !["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const rows = filteredEntries();
      const current = rows.findIndex((entry) => entryKey(entry) === row.dataset.economyKey);
      const next = event.key === "Home" ? 0 : event.key === "End" ? rows.length - 1 : Math.max(0, Math.min(rows.length - 1, current + (event.key === "ArrowDown" ? 1 : -1)));
      if (rows[next]) {
        STATE.selectedKey = entryKey(rows[next]);
        STATE.relationLimit = RELATION_PAGE_SIZE;
        renderList(STATE.selectedKey);
      }
    });
    listen(window, "webui:view-changed", (event) => { if (event.detail?.view === "economy") load(currentLanguage()); });
    listen(window, "webui:language-changed", (event) => { if (isActive()) load(event.detail?.language || currentLanguage(), true); });
    listen(window, "webui:ui-locale-changed", (event) => { STATE.uiLocale = String(event.detail?.locale || "en").toLowerCase().startsWith("zh") ? "zh" : "en"; render(); });
    listen(window, "hashchange", () => { if (isActive()) load(currentLanguage()); });
  }

  function destroy() {
    STATE.abortController?.abort();
    STATE.loadToken += 1;
    STATE.listeners.splice(0).forEach((remove) => remove());
    if (STATE.container) STATE.container.replaceChildren();
    STATE.container = null;
    STATE.data = null;
    STATE.itemById = new Map();
    STATE.loading = null;
    STATE.lastError = "";
    STATE.abortController = null;
    STATE.initialized = false;
  }

  function init(options = {}) {
    if (STATE.initialized) return STATE;
    STATE.container = typeof options.container === "string" ? document.querySelector(options.container) : (options.container || document.querySelector(DEFAULT_CONTAINER));
    if (!STATE.container) return STATE;
    STATE.initialized = true;
    STATE.uiLocale = options.uiLocale || detectLocale();
    STATE.language = String(options.language || currentLanguage()).toUpperCase();
    bindEvents();
    render();
    if (options.load !== false && isActive()) load(STATE.language);
    return STATE;
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.economy = { init, load, render, destroy, state: STATE, containerId: "economy-app", dataPath };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => init(), { once: true });
  else init();
})();
