(() => {
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const PANE_STORAGE_KEY = "webui_characters_splitter_width";
  const FILTER_HEIGHT_STORAGE_KEY = "webui_filter_splitter_height_characters";
  const FILTER_PANEL_STORAGE_KEY = "webui_characters_filters_collapsed";
  const state = {
    container: null,
    data: null,
    language: "",
    query: "",
    kind: "all",
    source: "all",
    selectedId: "",
    loadToken: 0,
    filterPanel: null,
  };

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
  const currentLanguage = () => String(document.querySelector("#language")?.value || "CN").toUpperCase();
  const zh = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").toLowerCase().startsWith("zh");
  const ui = (en, cn) => zh() ? cn : en;
  const sourceLabel = (source) => ({
    TextTable: "TextTable npcName_*",
    CharacterTable: "CharacterTable",
    NpcTable: "NpcTable",
    SNSChatTable: "SNSChatTable",
    "Story actor registry": ui("Story sources", "剧情角色来源"),
    "Exported assets": ui("Exported assets", "导出资源"),
  }[source] || source);
  const kindLabel = (kind) => ({
    character: ui("Playable character", "可玩角色"),
    npc: "NPC",
    actor: ui("Story actor", "剧情角色"),
    asset_npc: ui("Asset NPC", "资源 NPC"),
  }[kind] || kind);

  function dataPath(language) {
    return `data/lang/${encodeURIComponent(language)}/characters/index.json`;
  }

  function normalizedName(value) {
    return String(value || "").trim().normalize("NFKC").toLocaleLowerCase();
  }

  function isUnknownName(value) {
    return /^\?+$/.test(String(value || "").trim().normalize("NFKC"));
  }

  function knownNames(row) {
    return [...new Set((row.names || [])
      .map((name) => String(name.text || "").trim())
      .filter((name) => name && !isUnknownName(name))
      .map(normalizedName))]
      .sort();
  }

  function groupedRecords() {
    const groups = new Map();
    for (const row of state.data?.records || []) {
      const primaryName = String(row.primaryName || row.id || "").trim();
      const nameKey = normalizedName(primaryName) || normalizedName(row.id);
      const foundNames = knownNames(row);
      const groupKey = JSON.stringify([nameKey, foundNames]);
      let group = groups.get(groupKey);
      if (!group) {
        group = {
          id: groupKey,
          primaryName,
          knownNames: foundNames,
          records: [],
          kinds: [],
          sourceTypes: [],
          aliases: [],
          names: [],
        };
        groups.set(groupKey, group);
      }
      group.records.push(row);
      if (row.kind && !group.kinds.includes(row.kind)) group.kinds.push(row.kind);
      for (const source of row.sourceTypes || []) {
        if (!group.sourceTypes.includes(source)) group.sourceTypes.push(source);
      }
      for (const alias of [row.id, ...(row.aliases || [])]) {
        if (alias && !group.aliases.includes(alias)) group.aliases.push(alias);
      }
      for (const name of row.names || []) {
        const identity = [name.text, name.source, name.language, name.key].join("\u0000");
        if (!group.names.some((item) => item._identity === identity)) {
          group.names.push({ ...name, _identity: identity });
        }
      }
    }
    return [...groups.values()].map((group) => ({
      ...group,
      kinds: [...group.kinds].sort(),
      sourceTypes: [...group.sourceTypes].sort(),
      aliases: [...group.aliases].sort(),
      names: group.names.map(({ _identity, ...name }) => name),
    }));
  }

  function allSources() {
    return [...new Set(groupedRecords().flatMap((row) => row.sourceTypes || []))].sort();
  }

  function filteredRecords() {
    const query = state.query.trim().toLocaleLowerCase();
    return groupedRecords().filter((row) => {
      if (state.kind !== "all" && !(row.kinds || []).includes(state.kind)) return false;
      if (state.source !== "all" && !(row.sourceTypes || []).includes(state.source)) return false;
      if (!query) return true;
      const haystack = [
        row.id,
        row.primaryName,
        ...(row.aliases || []),
        ...(row.names || []).map((item) => `${item.text} ${item.key}`),
        ...(row.records || []).flatMap((identity) => [
          identity.id,
          ...(identity.evidence || []).flatMap((item) => [item.key, ...(item.paths || [])]),
        ]),
      ].join(" ").toLocaleLowerCase();
      return haystack.includes(query);
    });
  }

  function isMobileLayout() {
    return !!window.matchMedia?.(MOBILE_LAYOUT_QUERY).matches;
  }

  function parsePixels(value, fallback = 0) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function renderFilterChips() {
    const buildChips = window.WebUI?.filters?.buildChips;
    if (!buildChips) return;
    const records = groupedRecords();
    const kindCounts = new Map();
    const sourceCounts = new Map();
    for (const row of records) {
      for (const kind of row.kinds || []) {
        kindCounts.set(kind, (kindCounts.get(kind) || 0) + 1);
      }
      for (const source of row.sourceTypes || []) {
        sourceCounts.set(source, (sourceCounts.get(source) || 0) + 1);
      }
    }
    buildChips("#characters-kind-filter", ["character", "npc", "actor", "asset_npc"], {
      active: state.kind === "all" ? "" : state.kind,
      single: true,
      label: (kind) => kindLabel(kind),
      count: kindCounts,
      onToggle: (next) => {
        state.kind = next || "all";
        renderFilterChips();
        renderList();
      },
    });
    buildChips("#characters-source-filter", allSources(), {
      active: state.source === "all" ? "" : state.source,
      single: true,
      label: (source) => sourceLabel(source),
      count: sourceCounts,
      onToggle: (next) => {
        state.source = next || "all";
        renderFilterChips();
        renderList();
      },
    });
  }

  function bindFilterSections() {
    state.container?.querySelectorAll(".filter-section-toggle").forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const section = toggle.closest(".filter-section");
        const body = section?.querySelector(".filter-section-body");
        if (!section || !body) return;
        const collapsed = !section.classList.contains("is-collapsed");
        section.classList.toggle("is-collapsed", collapsed);
        body.hidden = collapsed;
        toggle.setAttribute("aria-expanded", String(!collapsed));
        window.dispatchEvent(new Event("resize"));
      });
    });
  }

  function setupFilterPanel() {
    state.filterPanel = window.WebUI?.filters?.createPanelToggle?.({
      panel: "#characters-filter-panel",
      toggle: "#characters-filter-toggle",
      left: "#characters-left",
      storageKey: FILTER_PANEL_STORAGE_KEY,
      isMobile: isMobileLayout,
      labels: (collapsed) => ui(collapsed ? "Show filters" : "Hide filters", collapsed ? "显示筛选" : "隐藏筛选"),
      onChange: () => window.dispatchEvent(new Event("resize")),
    }) || null;
  }

  function setupSplitters() {
    const setupSplitter = window.WebUI?.setupSplitter;
    const utils = window.WebUI?.splitterUtils;
    const shell = state.container;
    const sidebar = shell?.querySelector("#characters-left");
    const paneHandle = shell?.querySelector("#characters-splitter");
    const filterPanel = shell?.querySelector("#characters-filter-panel");
    const filterHandle = shell?.querySelector("#characters-filter-splitter");
    const list = shell?.querySelector("#characters-list");
    if (!setupSplitter || !utils || !shell || !sidebar || !paneHandle || !filterPanel || !filterHandle || !list) return;

    let paneWasMobile = isMobileLayout();
    setupSplitter({
      handle: paneHandle,
      storageKey: PANE_STORAGE_KEY,
      bodyDragClass: "is-resizing-pane",
      client: (event) => event.clientX,
      keys: { decrease: ["ArrowLeft"], increase: ["ArrowRight"] },
      enabled: () => !isMobileLayout(),
      bounds: () => {
        const min = parsePixels(getComputedStyle(sidebar).minWidth, 320);
        const handleWidth = Math.max(1, paneHandle.getBoundingClientRect().width);
        return { min, max: Math.max(min, shell.getBoundingClientRect().width - handleWidth - 320) };
      },
      read: () => parsePixels(sidebar.style.width, sidebar.getBoundingClientRect().width),
      write: (width) => { sidebar.style.width = `${Math.round(width)}px`; },
      clear: () => { sidebar.style.removeProperty("width"); },
      sync: (ctrl) => {
        if (isMobileLayout()) {
          paneWasMobile = true;
          ctrl.clear({ commit: false });
          return;
        }
        if (shell.getBoundingClientRect().width < 48) return;
        let width = parsePixels(sidebar.style.width, sidebar.getBoundingClientRect().width);
        if (paneWasMobile || !sidebar.style.width) {
          const stored = utils.readStoredNumber(PANE_STORAGE_KEY);
          if (stored !== null) width = stored;
        }
        paneWasMobile = false;
        ctrl.set(width, { persist: false, commit: false });
      },
    });

    const minPanelHeight = 56;
    const minListHeight = 160;
    let filterWasMobile = isMobileLayout();
    const naturalFilterHeight = () => {
      const previous = filterPanel.style.height;
      const resized = filterPanel.classList.contains("is-filter-resized");
      filterPanel.style.removeProperty("height");
      filterPanel.classList.remove("is-filter-resized");
      const height = Math.ceil(filterPanel.getBoundingClientRect().height);
      if (previous) filterPanel.style.height = previous;
      filterPanel.classList.toggle("is-filter-resized", resized);
      return Math.max(minPanelHeight, height);
    };
    const filterBounds = () => {
      let fixedHeight = 0;
      for (const child of sidebar.children) {
        if (child === filterPanel || child === list) continue;
        fixedHeight += child.getBoundingClientRect().height;
      }
      const available = Math.max(minPanelHeight, sidebar.getBoundingClientRect().height - fixedHeight - minListHeight);
      return { min: minPanelHeight, max: Math.max(minPanelHeight, Math.min(available, naturalFilterHeight())) };
    };
    const filterController = setupSplitter({
      handle: filterHandle,
      storageKey: FILTER_HEIGHT_STORAGE_KEY,
      bodyDragClass: "is-resizing-filter",
      client: (event) => event.clientY,
      keys: { decrease: ["ArrowUp"], increase: ["ArrowDown"] },
      enabled: () => !isMobileLayout() && !filterPanel.hidden,
      bounds: filterBounds,
      read: () => filterPanel.getBoundingClientRect().height,
      write: (height) => {
        filterPanel.style.height = `${Math.round(height)}px`;
        filterPanel.classList.add("is-filter-resized");
      },
      clear: () => {
        filterPanel.style.removeProperty("height");
        filterPanel.classList.remove("is-filter-resized");
      },
      sync: (ctrl) => {
        if (isMobileLayout() || filterPanel.hidden) {
          filterWasMobile = isMobileLayout();
          ctrl.clear({ commit: false });
          return;
        }
        if (sidebar.getBoundingClientRect().height < 48) return;
        const stored = utils.readStoredNumber(FILTER_HEIGHT_STORAGE_KEY);
        if (stored !== null) {
          filterWasMobile = false;
          ctrl.set(stored, { persist: false, commit: false });
        } else {
          if (filterWasMobile) ctrl.clear({ commit: false });
          filterWasMobile = false;
          ctrl.syncAria();
        }
      },
    });
    if (window.MutationObserver && filterController) {
      const observer = new MutationObserver(filterController.requestSync);
      observer.observe(filterPanel, { attributes: true, attributeFilter: ["hidden"] });
      observer.observe(filterPanel, { childList: true, subtree: true });
    }
  }

  function renderShell() {
    if (!state.container) return;
    const groupCount = groupedRecords().length;
    state.container.innerHTML = `
      <aside id="characters-left">
        <header>
          <h1>${ui("Characters & NPCs", "人物")}</h1>
          <div class="characters-count">${groupCount.toLocaleString()} ${ui("names", "个名称")}</div>
          <div class="sidebar-header-actions">
            <button id="characters-filter-toggle" class="panel-toggle" type="button" aria-controls="characters-filter-panel" aria-expanded="true"></button>
            <button id="characters-reset" type="button">${ui("Reset filters", "重置筛选")}</button>
          </div>
        </header>

        <div id="characters-filter-panel" class="filters">
          <section class="filter-section filter-section-basic" data-filter-section="characters-basic" data-fixed-open="1">
            <div class="filter-section-title"><span>${ui("Basic filters", "基础筛选")}</span></div>
            <div class="filter-section-body filter-section-body-stack">
              <div class="filter-control-row">
                <label for="characters-q">${ui("Search", "搜索")}</label>
                <input id="characters-q" type="search" value="${esc(state.query)}" placeholder="${ui("Name, ID, table key, or asset path", "名称、ID、表键或资源路径")}">
              </div>
            </div>
          </section>
          <section class="filter-section is-collapsed" data-filter-section="characters-kind">
            <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="characters-kind-filter-body">
              <span>${ui("Kind", "类型")}</span>
            </button>
            <div id="characters-kind-filter-body" class="filter-section-body" hidden>
              <div id="characters-kind-filter" class="chips" data-multi="1"></div>
            </div>
          </section>
          <section class="filter-section is-collapsed" data-filter-section="characters-source">
            <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="characters-source-filter-body">
              <span>${ui("Evidence source", "证据来源")}</span>
            </button>
            <div id="characters-source-filter-body" class="filter-section-body" hidden>
              <div id="characters-source-filter" class="chips" data-multi="1"></div>
            </div>
          </section>
        </div>
        <div id="characters-filter-splitter" class="filter-splitter" role="separator" aria-label="Resize character filters" aria-orientation="horizontal" tabindex="0"></div>
        <div id="characters-list-meta" class="characters-list-meta"></div>
        <div id="characters-list" class="characters-list"></div>
      </aside>
      <div id="characters-splitter" class="pane-splitter" role="separator" aria-label="Resize character sidebar" aria-orientation="vertical" tabindex="0"></div>
      <main id="characters-detail" class="characters-detail"></main>`;
    state.container.querySelector("#characters-q")?.addEventListener("input", (event) => {
      state.query = event.target.value;
      renderList();
    });
    state.container.querySelector("#characters-reset")?.addEventListener("click", () => {
      state.query = "";
      state.kind = "all";
      state.source = "all";
      const search = state.container.querySelector("#characters-q");
      if (search) search.value = "";
      renderFilterChips();
      renderList();
    });
    bindFilterSections();
    renderFilterChips();
    setupFilterPanel();
    setupSplitters();
    renderList();
  }

  function renderList() {
    const list = state.container?.querySelector("#characters-list");
    const meta = state.container?.querySelector("#characters-list-meta");
    if (!list || !meta) return;
    const rows = filteredRecords();
    if (state.selectedId && !rows.some((row) => row.id === state.selectedId)) state.selectedId = "";
    if (!state.selectedId && rows.length) state.selectedId = rows[0].id;
    meta.textContent = `${rows.length.toLocaleString()} ${ui("matching names", "个匹配名称")}`;
    list.innerHTML = rows.map((row) => `
      <button class="characters-list-row${row.id === state.selectedId ? " is-selected" : ""}" type="button" data-character-id="${esc(row.id)}">
        <span class="characters-row-name">${esc(row.primaryName || row.id)}</span>
        <span class="characters-row-meta">
          <span>${(row.kinds || []).map((kind) => esc(kindLabel(kind))).join(" · ")}</span>
          <code>${row.records.length.toLocaleString()} ${ui(row.records.length === 1 ? "identity" : "identities", "身份")}</code>
        </span>
        ${(row.knownNames || []).some((name) => name !== normalizedName(row.primaryName)) ? `
          <span class="characters-row-found-names">${ui("Also found", "其他名称")}: ${row.knownNames
            .filter((name) => name !== normalizedName(row.primaryName))
            .map(esc)
            .join(" · ")}</span>` : ""}
        <span class="characters-row-sources">${(row.sourceTypes || []).map((source) => `<span>${esc(sourceLabel(source))}</span>`).join("")}</span>
      </button>`).join("");
    list.querySelectorAll("[data-character-id]").forEach((button) => {
      button.addEventListener("click", () => {
        state.selectedId = button.dataset.characterId || "";
        list.querySelector(".characters-list-row.is-selected")?.classList.remove("is-selected");
        button.classList.add("is-selected");
        renderDetail();
      });
    });
    renderDetail();
  }

  function evidenceDetails(item) {
    const facts = [];
    if (item.textId !== undefined) facts.push(`text id: ${item.textId}`);
    if (item.nameTextId !== undefined) facts.push(`name text id: ${item.nameTextId}`);
    if (item.dataKey) facts.push(`data key: ${item.dataKey}`);
    if (item.npcGroupId) facts.push(`NPC group: ${item.npcGroupId}`);
    if (item.assetKind) facts.push(`asset kind: ${item.assetKind}`);
    if (item.matchedIdentity) facts.push(`${ui("matched existing identity", "匹配现有身份")}: ${item.matchedIdentity}`);
    if (item.matchRule) facts.push(`${ui("match rule", "匹配规则")}: ${String(item.matchRule).replaceAll("_", " ")}`);
    if (item.count) facts.push(`${Number(item.count).toLocaleString()} ${ui("matching exported files", "个匹配的导出文件")}`);
    return facts;
  }

  function assetPageUrl(rel) {
    const url = new URL(window.location.href);
    url.searchParams.set("asset", String(rel || ""));
    url.hash = "#assets";
    return url.toString();
  }

  function renderAssetPathLink(rel) {
    return `<a class="characters-asset-link" href="${esc(assetPageUrl(rel))}" title="${esc(ui("Open in Assets", "在资源页打开"))}"><code>${esc(rel)}</code></a>`;
  }

  function renderEvidence(item) {
    const facts = evidenceDetails(item);
    const paths = Array.isArray(item.paths) ? item.paths : [];
    const evidenceKey = paths.length
      ? `<a class="characters-evidence-key characters-asset-key-link" href="${esc(assetPageUrl(paths[0]))}" title="${esc(ui("Open first matching asset", "打开首个匹配资源"))}"><code>${esc(item.key)}</code></a>`
      : `<code class="characters-evidence-key">${esc(item.key)}</code>`;
    return `
      <article class="characters-evidence">
        <header>
          <span class="characters-evidence-source">${esc(sourceLabel(item.source))}</span>
          <span class="characters-evidence-type">${esc(String(item.type || "").replaceAll("_", " "))}</span>
        </header>
        ${evidenceKey}
        ${facts.length ? `<ul>${facts.map((fact) => `<li>${esc(fact)}</li>`).join("")}</ul>` : ""}
        ${item.note ? `<p>${esc(item.note)}</p>` : ""}
        ${paths.length ? `<details><summary>${ui("Asset path samples", "资源路径示例")} (${paths.length}${item.count > paths.length ? ` / ${item.count}` : ""})</summary><div class="characters-paths">${paths.map((path) => renderAssetPathLink(path)).join("")}</div></details>` : ""}
      </article>`;
  }

  function renderDetail() {
    const detail = state.container?.querySelector("#characters-detail");
    if (!detail) return;
    const row = groupedRecords().find((item) => item.id === state.selectedId);
    if (!row) {
      detail.innerHTML = `<div class="characters-empty">${ui("Select an identity to inspect its names and evidence.", "选择一个身份以查看名称与证据。")}</div>`;
      return;
    }
    detail.innerHTML = `
      <header class="characters-detail-header">
        <div>
          ${(row.kinds || []).map((kind) => `<span class="characters-kind">${esc(kindLabel(kind))}</span>`).join(" ")}
          <h2>${esc(row.primaryName || row.id)}</h2>
          <code>${row.records.length.toLocaleString()} ${ui(row.records.length === 1 ? "grouped identity" : "grouped identities", "已合并身份")}</code>
        </div>
        <div class="characters-detail-count">${row.records.reduce((total, identity) => total + (identity.evidence || []).length, 0)} ${ui("evidence groups", "组证据")}</div>
      </header>
      <section class="characters-section">
        <h3>${ui("Grouped identities", "已合并的身份")}</h3>
        <div class="characters-identity-list">${row.records.map((identity) => `
          <div class="characters-identity">
            <span class="characters-kind">${esc(kindLabel(identity.kind))}</span>
            <code>${esc(identity.id)}</code>
            <span>${(identity.sourceTypes || []).map((source) => esc(sourceLabel(source))).join(" · ")}</span>
          </div>`).join("")}
        </div>
      </section>
      <section class="characters-section">
        <h3>${ui("Observed names", "已发现的名称")}</h3>
        <div class="characters-name-grid">${(row.names || []).map((name) => `
          <div class="characters-name">
            <strong>${esc(name.text)}</strong>
            <span>${esc(sourceLabel(name.source))}${name.language ? ` · ${esc(name.language)}` : ""}</span>
            <code>${esc(name.key)}</code>
          </div>`).join("") || `<p>${ui("No localized name was found; this identity comes from an exported asset marker.", "未找到本地化名称；该身份来自导出资源标识。")}</p>`}
        </div>
      </section>
      <section class="characters-section">
        <h3>${ui("Identifiers and aliases", "标识与别名")}</h3>
        <div class="characters-aliases">${(row.aliases || []).map((alias) => `<code>${esc(alias)}</code>`).join("")}</div>
      </section>
      <section class="characters-section">
        <h3>${ui("Evidence", "证据")}</h3>
        <div class="characters-identity-evidence-list">${row.records.map((identity) => `
          <section class="characters-identity-evidence">
            <header>
              <span class="characters-kind">${esc(kindLabel(identity.kind))}</span>
              <code>${esc(identity.id)}</code>
              <span>${(identity.evidence || []).length} ${ui("evidence groups", "组证据")}</span>
            </header>
            <div class="characters-evidence-list">${(identity.evidence || []).map(renderEvidence).join("")}</div>
          </section>`).join("")}
        </div>
      </section>`;
  }

  async function load(language = currentLanguage(), force = false) {
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && state.data && state.language === nextLanguage) {
      renderShell();
      return state.data;
    }
    const token = ++state.loadToken;
    state.language = nextLanguage;
    if (state.container) state.container.innerHTML = `<div class="characters-empty">${ui("Loading character evidence…", "正在加载人物证据…")}</div>`;
    try {
      const response = await fetch(dataPath(nextLanguage), { cache: "no-store" });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const data = await response.json();
      if (token !== state.loadToken) return null;
      state.data = data;
      state.selectedId = "";
      renderShell();
      return data;
    } catch (error) {
      if (token !== state.loadToken) return null;
      if (state.container) state.container.innerHTML = `<div class="characters-empty characters-error">${ui("Character data could not be loaded. Rebuild it with scripts/build_character_data.py.", "无法加载人物数据。请运行 scripts/build_character_data.py 重新生成。")}<br><code>${esc(error.message)}</code></div>`;
      return null;
    }
  }

  function init() {
    state.container = document.querySelector("#characters-app");
    if (!state.container) return;
    if (document.body.dataset.activeView === "characters" || location.hash === "#characters") load();
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.characters = { init, load };
  window.addEventListener("webui:view-changed", (event) => {
    if (event.detail?.view === "characters") load();
  });
  window.addEventListener("webui:language-changed", (event) => {
    if (document.body.dataset.activeView === "characters") load(event.detail?.language || currentLanguage());
    else state.language = "";
  });
  window.addEventListener("webui:ui-locale-changed", () => {
    if (state.data && state.container) renderShell();
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
