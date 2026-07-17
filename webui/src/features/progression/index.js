(() => {
  const DEFAULT_CONTAINER = "#progression-app";
  const ROOT_KINDS = [
    "character",
    "weapon",
    "equipment",
    "item",
    "reward_bundle",
    "drop_pool",
    "enemy_reference",
    "character_level_curve",
  ];
  const PAGE_SIZE = 200;
  const RELATION_PAGE_SIZE = 60;
  let localeListenerBound = false;
  const ROOT_LABELS = {
    character: "Characters",
    weapon: "Weapons",
    equipment: "Equipment",
    item: "Items & currencies",
    reward_bundle: "Reward packages",
    drop_pool: "Drop pools",
    enemy_reference: "Enemies",
    character_level_curve: "Character level curve",
  };
  const ROOT_LABELS_ZH = {
    character: "角色", weapon: "武器", equipment: "装备", item: "道具与货币",
    reward_bundle: "奖励包", drop_pool: "掉落池", enemy_reference: "敌人",
    character_level_curve: "角色等级曲线",
  };
  const TEXT = {
    en: {
      title: "Upgrade Costs & Rewards", purpose: "See how upgrades, items, rewards, and drops connect. This complements the Gameplay catalog by answering what something costs, contains, unlocks, or is used by.", why: "Why care?", whyBody: "Use this when the catalog shows what an item or character is, but you need to know what feeds into it or where it leads.", q1: "What will this upgrade cost?", q1b: "Open a character, weapon, or equipment entry and follow its cost and breakthrough links.", q2: "What is inside this reward?", q2b: "Open a reward package or drop pool to see its authored contents and possible drops.", q3: "Where is this item used?", q3b: "Open an item, then check “Other records that use this” for upgrades or rewards that point to it.", start: "Start here:", startBody: "choose a category, select a familiar entry, then follow a linked name in either direction.", limits: "Limits, evidence, and graph terms", connection: "Connection", connectionBody: "A link between two exported records, such as an upgrade costing an item.", from: "From this entry", fromBody: "What the selected record uses, contains, grants, or leads to.", to: "Other records that use this", toBody: "Records elsewhere in the data that point back to the selection.", search: "Find something in this category", placeholder: "Name or game-data ID", noMatch: "Nothing matched", noMatchBody: "Try a shorter name or clear the search. Game-data IDs also work when you know one.", choose: "Choose something to investigate", chooseBody: "Select a row on the left. You will see what it uses or contains, plus which other records point back to it.", linked: "Linked subrecord", linkedBody: "This is a supporting record reached through a connection. It is not part of the current category list.", fromThis: "From this", toThis: "To this", outTitle: "What this entry uses, contains, or leads to", inTitle: "Other records that use this", sources: "Source records",
    },
    zh: {
      title: "升级消耗与奖励", purpose: "查看升级、道具、奖励与掉落之间的联系。本页补充“玩法数据”目录，回答某项内容需要什么、包含什么、解锁什么，或被哪些内容使用。", why: "为什么值得看？", whyBody: "当目录只告诉你角色或道具“是什么”，而你想知道它需要什么、又会通向哪里时，请使用本页。", q1: "这次升级需要什么？", q1b: "打开角色、武器或装备，沿着消耗与突破联系继续查看。", q2: "这个奖励里有什么？", q2b: "打开奖励包或掉落池，查看配置中包含的内容与可能掉落。", q3: "这个道具用在哪里？", q3b: "打开道具，再查看“哪些记录使用它”，找到指向它的升级或奖励。", start: "建议从这里开始：", startBody: "选择一个分类和熟悉的条目，再点击任一关联名称继续追踪。", limits: "局限、证据与关系图术语", connection: "联系", connectionBody: "两条导出记录之间的链接，例如某次升级消耗某个道具。", from: "从当前条目出发", fromBody: "当前记录使用、包含、给予或通向的内容。", to: "哪些记录使用它", toBody: "游戏数据中指回当前条目的其他记录。", search: "在当前分类中查找", placeholder: "名称或游戏数据 ID", noMatch: "没有匹配结果", noMatchBody: "请缩短名称或清除搜索；知道游戏数据 ID 时也可直接输入。", choose: "选择要调查的内容", chooseBody: "从左侧选择一项，即可查看它使用或包含的内容，以及哪些记录指向它。", linked: "关联子记录", linkedBody: "这是沿关联打开的辅助记录，不属于当前分类列表。", fromThis: "从这里", toThis: "指向这里", outTitle: "当前条目使用、包含或通向的内容", inTitle: "哪些记录使用当前条目", sources: "来源记录",
    },
  };

  const STATE = {
    container: null,
    uiLocale: "en",
    data: null,
    language: "",
    loadToken: 0,
    abortController: null,
    kind: "character",
    query: "",
    selectedId: "",
    visibleLimit: PAGE_SIZE,
    nodeById: new Map(),
    outgoing: new Map(),
    incoming: new Map(),
    relationLimits: new Map(),
  };

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

  const label = (value) => String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const rootLabel = (kind) => (STATE.uiLocale === "zh" ? ROOT_LABELS_ZH[kind] : ROOT_LABELS[kind]) || label(kind);
  const normalizeLocale = (value) => String(value || "en").toLowerCase().startsWith("zh") ? "zh" : "en";
  const detectLocale = () => normalizeLocale(window.WEBUI_UI_LOCALE || document.documentElement.lang || "en");
  const t = (key) => (TEXT[STATE.uiLocale] || TEXT.en)[key] || TEXT.en[key] || key;
  const ui = (en, zh) => STATE.uiLocale === "zh" ? zh : en;

  function bindLocaleListener() {
    if (localeListenerBound) return;
    localeListenerBound = true;
    window.addEventListener("webui:ui-locale-changed", (event) => {
      const next = normalizeLocale(event.detail?.locale || detectLocale());
      if (next === STATE.uiLocale) return;
      STATE.uiLocale = next;
      if (STATE.container && STATE.data) renderShell();
    });
  }

  function dataPath(language) {
    return `data/lang/${encodeURIComponent(language)}/progression/index.json`;
  }

  function addIndex(index, key, value) {
    if (!index.has(key)) index.set(key, []);
    index.get(key).push(value);
  }

  function rebuildIndexes() {
    STATE.nodeById = new Map((STATE.data?.nodes || []).map((node) => [node.id, node]));
    STATE.outgoing = new Map();
    STATE.incoming = new Map();
    for (const relation of STATE.data?.relations || []) {
      addIndex(STATE.outgoing, relation.source, relation);
      addIndex(STATE.incoming, relation.target, relation);
    }
  }

  function rootNodes() {
    const query = STATE.query.trim().toLowerCase();
    return (STATE.data?.rootIds || [])
      .map((id) => STATE.nodeById.get(id))
      .filter((node) => node && node.kind === STATE.kind)
      .filter((node) => !query || `${node.name || ""} ${node.id} ${node.kind}`.toLowerCase().includes(query));
  }

  function rootCount(kind) {
    let count = 0;
    for (const id of STATE.data?.rootIds || []) {
      if (STATE.nodeById.get(id)?.kind === kind) count += 1;
    }
    return count;
  }

  function renderShell() {
    if (!STATE.container) return;
    STATE.container.innerHTML = `
      <section class="progression-shell" aria-label="Progression and rewards">
        <header class="progression-header">
          <div>
            <h1>${esc(t("title"))}</h1>
            <p>${esc(t("purpose"))}</p>
          </div>
          <label class="progression-search"><span>${esc(t("search"))}</span><input id="progression-search" type="search" value="${esc(STATE.query)}" placeholder="${esc(t("placeholder"))}" aria-controls="progression-list" autocomplete="off"></label>
        </header>
        <section class="progression-intro" aria-labelledby="progression-why-title">
          <div class="progression-intro-lead"><strong id="progression-why-title">${esc(t("why"))}</strong><span>${esc(t("whyBody"))}</span></div>
          <div class="progression-question-grid" aria-label="Example questions this page can answer">
            <article><strong>${esc(t("q1"))}</strong><span>${esc(t("q1b"))}</span></article>
            <article><strong>${esc(t("q2"))}</strong><span>${esc(t("q2b"))}</span></article>
            <article><strong>${esc(t("q3"))}</strong><span>${esc(t("q3b"))}</span></article>
          </div>
          <p class="progression-first-step"><strong>${esc(t("start"))}</strong> ${esc(t("startBody"))}</p>
        </section>
        <details class="progression-scope">
          <summary>${esc(t("limits"))}</summary>
          <div><p>${esc(STATE.uiLocale === "en" ? (STATE.data?.scope?.note || "Relationships come from exported tables; they do not represent inventory, current availability, runtime rolls, or an optimal upgrade plan.") : "这些联系来自导出表格，不代表账号库存、当前开放状态、运行时随机结果或最佳升级方案。")}</p><dl><div><dt>${esc(t("connection"))}</dt><dd>${esc(t("connectionBody"))}</dd></div><div><dt>${esc(t("from"))}</dt><dd>${esc(t("fromBody"))}</dd></div><div><dt>${esc(t("to"))}</dt><dd>${esc(t("toBody"))}</dd></div></dl></div>
        </details>
        <nav class="progression-tabs" aria-label="Progression categories">
          ${ROOT_KINDS.filter((kind) => rootCount(kind)).map((kind) => `<button type="button" aria-pressed="${STATE.kind === kind}" data-progression-kind="${esc(kind)}" class="${STATE.kind === kind ? "is-active" : ""}">${esc(rootLabel(kind))}<span>${rootCount(kind).toLocaleString()}</span></button>`).join("")}
        </nav>
        <div class="progression-workspace">
          <aside id="progression-list" class="progression-list" aria-label="${ui("Matching progression entries", "匹配的升级与奖励条目")}"></aside>
          <main id="progression-detail" class="progression-detail" aria-label="${ui("Selected progression entry", "已选择的升级与奖励条目")}"></main>
        </div>
      </section>`;
    bindEvents();
    renderList();
    renderDetail();
  }

  function renderList() {
    const root = STATE.container?.querySelector("#progression-list");
    if (!root) return;
    const nodes = rootNodes();
    if (!nodes.length) {
      root.innerHTML = `<div class="progression-list-toolbar"><span role="status">0</span>${STATE.query ? `<button type="button" data-progression-clear>${STATE.uiLocale === "zh" ? "清除搜索" : "Clear search"}</button>` : ""}</div><div class="progression-note"><strong>${esc(t("noMatch"))}</strong><span>${esc(t("noMatchBody"))}</span></div>`;
      return;
    }
    const visible = nodes.slice(0, STATE.visibleLimit);
    const selected = nodes.find((node) => node.id === STATE.selectedId);
    const selectedIsPinned = Boolean(selected && !visible.includes(selected));
    if (selectedIsPinned) {
      if (visible.length >= PAGE_SIZE) visible[visible.length - 1] = selected;
      else visible.push(selected);
    }
    root.innerHTML = `<div class="progression-list-toolbar"><span class="progression-list-count" role="status">${ui(`Showing ${visible.length.toLocaleString()} of ${nodes.length.toLocaleString()}`, `显示 ${visible.length.toLocaleString()} / ${nodes.length.toLocaleString()}`)}</span>${STATE.query ? `<button type="button" data-progression-clear>${ui("Clear search", "清除搜索")}</button>` : ""}</div>
      ${visible.map((node) => `<button type="button" class="progression-row ${STATE.selectedId === node.id ? "is-selected" : ""}" data-progression-node="${esc(node.id)}"${STATE.selectedId === node.id ? ' aria-current="true"' : ""}>
        <span class="progression-row-title">${esc(node.name || node.id)}${selectedIsPinned && node.id === STATE.selectedId ? `<small class="progression-selected-note">${ui("Selected", "已选择")}</small>` : ""}</span>
        <code>${esc(node.id)}</code><span class="sr-only">${STATE.selectedId === node.id ? ui("Selected", "已选择") : ui("Open details", "打开详情")}</span>
      </button>`).join("")}
      ${visible.length < nodes.length ? `<button id="progression-more" class="progression-more" type="button">${ui(`Show ${Math.min(PAGE_SIZE, nodes.length - visible.length).toLocaleString()} more`, `再显示 ${Math.min(PAGE_SIZE, nodes.length - visible.length).toLocaleString()} 条`)}</button>` : ""}`;
  }

  function evidenceHtml(evidence) {
    if (!evidence) return "";
    const location = [evidence.table, evidence.row, evidence.path].filter((value) => value !== null && value !== undefined && value !== "").join(" › ");
    return location ? `<small class="progression-evidence"><b>${ui("Exported source", "导出来源")}</b><span>${esc(location)}</span></small>` : "";
  }

  function relationHtml(relation, direction) {
    const otherId = direction === "out" ? relation.target : relation.source;
    const other = STATE.nodeById.get(otherId);
    return `<article class="progression-relation">
      <span class="progression-direction">${esc(direction === "out" ? t("fromThis") : t("toThis"))}</span>
      <div>
        <b>${esc(label(relation.kind))}</b><span class="progression-confidence">${ui("Direct exported relationship", "导出数据中的直接联系")}</span>
        <button type="button" data-progression-node="${esc(otherId)}">${esc(other?.name || otherId)}</button>
        <code>${esc(otherId)}</code>
        ${evidenceHtml(relation.evidence)}
        ${relation.note ? `<small>${esc(relation.note)}</small>` : ""}
      </div>
    </article>`;
  }

  function relationSection(title, relations, direction) {
    if (!relations.length) return "";
    const grouped = new Map();
    for (const relation of relations) addIndex(grouped, relation.kind, relation);
    return `<section class="progression-section"><h3>${esc(title)} <span>${relations.length.toLocaleString()}</span></h3>
      ${Array.from(grouped.entries()).map(([kind, rows]) => {
        const key = `${STATE.selectedId}|${direction}|${kind}`;
        const limit = STATE.relationLimits.get(key) || RELATION_PAGE_SIZE;
        const visible = rows.slice(0, limit);
        return `<details ${relations.length < 80 || limit > RELATION_PAGE_SIZE ? "open" : ""}><summary>${esc(label(kind))} <span>${rows.length.toLocaleString()}</span></summary><div>${visible.map((row) => relationHtml(row, direction)).join("")}${visible.length < rows.length ? `<button type="button" class="progression-relations-more" data-progression-relation-kind="${esc(kind)}" data-progression-relation-direction="${esc(direction)}">${ui(`Show next ${Math.min(RELATION_PAGE_SIZE, rows.length - visible.length).toLocaleString()}`, `再显示 ${Math.min(RELATION_PAGE_SIZE, rows.length - visible.length).toLocaleString()} 条`)} <span>(${visible.length.toLocaleString()} / ${rows.length.toLocaleString()})</span></button>` : ""}</div></details>`;
      }).join("")}
    </section>`;
  }

  function rawHtml(node) {
    const fields = Object.entries(node.raw || {}).filter(([, value]) => value !== null && value !== "" && !(Array.isArray(value) && !value.length));
    if (!fields.length) return "";
    return `<details class="progression-raw"><summary>${ui("Authored fields", "配置原始字段")}</summary><dl>${fields.map(([key, value]) => `<div><dt>${esc(label(key))}</dt><dd><pre>${esc(typeof value === "string" ? value : JSON.stringify(value, null, 2))}</pre></dd></div>`).join("")}</dl></details>`;
  }

  function sourceHtml(node) {
    const sources = node.sources || (node.source ? [node.source] : []);
    if (!sources.length) return "";
    return `<details class="progression-sources"><summary>${esc(t("sources"))}</summary><div>${sources.map((source) => `<code>${esc(typeof source === "string" ? source : JSON.stringify(source))}</code>`).join("")}</div></details>`;
  }

  function renderDetail() {
    const root = STATE.container?.querySelector("#progression-detail");
    if (!root) return;
    const node = STATE.nodeById.get(STATE.selectedId);
    if (!node) {
      root.innerHTML = `<div class="progression-note progression-detail-empty"><strong>${esc(t("choose"))}</strong><span>${esc(t("chooseBody"))}</span></div>`;
      return;
    }
    const outgoing = STATE.outgoing.get(node.id) || [];
    const incoming = STATE.incoming.get(node.id) || [];
    const isRoot = (STATE.data?.rootIds || []).includes(node.id);
    root.innerHTML = `<article class="progression-card">
      <header tabindex="-1"><span class="progression-badge">${esc(isRoot ? rootLabel(node.kind) : t("linked"))}</span><h2>${esc(node.name || node.id)}</h2><code>${esc(node.id)}</code>${isRoot ? "" : `<p class="progression-linked-note">${esc(t("linkedBody"))}</p>`}<p>${outgoing.length.toLocaleString()} ${STATE.uiLocale === "zh" ? "条从这里出发的联系" : `connection${outgoing.length === 1 ? "" : "s"} from this entry`} · ${incoming.length.toLocaleString()} ${STATE.uiLocale === "zh" ? "条记录指向这里" : `other record${incoming.length === 1 ? "" : "s"} point${incoming.length === 1 ? "s" : ""} to it`}</p></header>
      ${rawHtml(node)}
      ${relationSection(t("outTitle"), outgoing, "out")}
      ${relationSection(t("inTitle"), incoming, "in")}
      ${sourceHtml(node)}
    </article>`;
  }

  function selectNode(id, { focusDetail = false } = {}) {
    const node = STATE.nodeById.get(id);
    if (!node) return;
    if (STATE.selectedId !== id) STATE.relationLimits.clear();
    STATE.selectedId = id;
    const isRoot = (STATE.data?.rootIds || []).includes(id) && ROOT_KINDS.includes(node.kind);
    const incompatibleQuery = STATE.query && !`${node.name || ""} ${node.id} ${node.kind}`.toLowerCase().includes(STATE.query.trim().toLowerCase());
    const shellChanged = isRoot && (STATE.kind !== node.kind || incompatibleQuery);
    if (isRoot) STATE.kind = node.kind;
    if (isRoot && incompatibleQuery) STATE.query = "";
    if (shellChanged) renderShell();
    else {
      renderList();
      renderDetail();
    }
    STATE.container?.querySelector("#progression-detail")?.scrollTo?.({ top: 0 });
    if (focusDetail) STATE.container?.querySelector(".progression-card > header")?.focus();
  }

  function bindEvents() {
    STATE.container?.querySelector("#progression-search")?.addEventListener("input", (event) => {
      STATE.query = event.target.value;
      STATE.visibleLimit = PAGE_SIZE;
      renderList();
    });
    STATE.container.onclick = (event) => {
      const kindButton = event.target.closest("[data-progression-kind]");
      if (kindButton) {
        STATE.kind = kindButton.dataset.progressionKind;
        STATE.selectedId = "";
        STATE.visibleLimit = PAGE_SIZE;
        STATE.relationLimits.clear();
        renderShell();
        STATE.container?.querySelector(`[data-progression-kind="${STATE.kind}"]`)?.focus();
        return;
      }
      const nodeButton = event.target.closest("[data-progression-node]");
      if (nodeButton) {
        selectNode(nodeButton.dataset.progressionNode, { focusDetail: Boolean(nodeButton.closest(".progression-relation")) });
        return;
      }
      if (event.target.closest("[data-progression-clear]")) {
        STATE.query = "";
        STATE.visibleLimit = PAGE_SIZE;
        const search = STATE.container.querySelector("#progression-search");
        if (search) search.value = "";
        renderList();
        search?.focus();
        return;
      }
      const relationMore = event.target.closest("[data-progression-relation-kind]");
      if (relationMore) {
        const direction = relationMore.dataset.progressionRelationDirection;
        const kind = relationMore.dataset.progressionRelationKind;
        const key = `${STATE.selectedId}|${direction}|${kind}`;
        STATE.relationLimits.set(key, (STATE.relationLimits.get(key) || RELATION_PAGE_SIZE) + RELATION_PAGE_SIZE);
        renderDetail();
        const replacement = STATE.container?.querySelector(`[data-progression-relation-kind="${kind}"][data-progression-relation-direction="${direction}"]`);
        const relationLinks = STATE.container?.querySelectorAll?.(".progression-relation [data-progression-node]");
        (replacement || relationLinks?.[relationLinks.length - 1])?.focus();
        return;
      }
      if (event.target.closest("#progression-more")) {
        STATE.visibleLimit += PAGE_SIZE;
        renderList();
        const replacement = STATE.container?.querySelector("#progression-more");
        const rows = STATE.container?.querySelectorAll?.(".progression-row");
        (replacement || rows?.[rows.length - 1])?.focus();
      }
    };
  }

  async function load(language = "CN") {
    const nextLanguage = String(language || "CN").toUpperCase();
    if (STATE.language === nextLanguage && STATE.data) {
      renderShell();
      return STATE.data;
    }
    const token = ++STATE.loadToken;
    STATE.abortController?.abort();
    STATE.abortController = new AbortController();
    if (STATE.container) STATE.container.innerHTML = `<div class="progression-note progression-loading" role="status"><span class="progression-spinner" aria-hidden="true"></span><span>${ui("Loading progression relationships…", "正在加载升级与奖励联系…")}</span></div>`;
    try {
      const response = await fetch(dataPath(nextLanguage), { cache: "no-store", signal: STATE.abortController.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      if (token !== STATE.loadToken) return null;
      STATE.data = payload;
      STATE.language = nextLanguage;
      STATE.selectedId = (payload.rootIds || []).includes("character:chr_0004_pelica")
        ? "character:chr_0004_pelica"
        : "";
      STATE.visibleLimit = PAGE_SIZE;
      STATE.relationLimits.clear();
      rebuildIndexes();
      if (!rootCount(STATE.kind)) STATE.kind = ROOT_KINDS.find((kind) => rootCount(kind)) || "character";
      renderShell();
      return payload;
    } catch (error) {
      if (error.name === "AbortError" || token !== STATE.loadToken) return null;
      STATE.language = "";
      if (STATE.container) {
        STATE.container.innerHTML = `<div class="progression-note progression-error" role="alert"><strong>${ui("Progression data could not be loaded", "无法加载升级与奖励数据")}</strong><span>${esc(error.message)}</span><button type="button" data-progression-retry>${ui("Try again", "重试")}</button></div>`;
        STATE.container.querySelector("[data-progression-retry]")?.addEventListener("click", () => {
          if (typeof window.WebUI?.retryView === "function") window.WebUI.retryView("progression", nextLanguage);
          else load(nextLanguage);
        });
      }
      return null;
    }
  }

  function init({ container = DEFAULT_CONTAINER, language = "CN", uiLocale = "" } = {}) {
    STATE.container = typeof container === "string" ? document.querySelector(container) : container;
    if (!STATE.container) return null;
    STATE.uiLocale = normalizeLocale(uiLocale || detectLocale());
    bindLocaleListener();
    return load(language);
  }

  function destroy() {
    STATE.loadToken += 1;
    STATE.abortController?.abort();
    STATE.abortController = null;
    STATE.data = null;
    STATE.language = "";
    STATE.nodeById.clear();
    STATE.outgoing.clear();
    STATE.incoming.clear();
    STATE.relationLimits.clear();
    if (STATE.container) STATE.container.innerHTML = "";
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.progression = { init, load, destroy, state: STATE, dataPath };
})();
