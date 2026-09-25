// Data page controller: the mode switch (Files | SQL | Decoded), deep links,
// view events, and the two store modes.
//
// Files and SQL read the export's SQLite stores (game/Unity.sqlite,
// game/GameFiles.sqlite) through the local server's read-only /api/stores
// API (scripts/webui/data_inspector/store_browser.py). A row's bytes are
// fetched from the row's own /export_* URL, exactly like any exported file.
// A static package has no such API: both modes then explain that they need
// `python serve.py` from the repository, and the page opens in Decoded mode.
//
// The viewer is generic. It knows the store vocabulary the API publishes
// (store, group, row name, object name, PathID, CAB) and nothing about any
// Unity type's schema: a JSON document is rendered as its own tree, text as
// text, and anything that is not UTF-8 text as a hex dump.
(() => {
  const API_PREFIX = "/api/stores";
  const MODES = ["files", "sql", "decoded"];
  const MAX_API_ROWS = 1000;
  const ROW_HEIGHT = 50;
  const OVERSCAN_PX = 240;
  const FULL_FETCH_BYTES = 4 * 1024 * 1024;
  const PREFIX_FETCH_BYTES = 512 * 1024;
  const TEXT_PREVIEW_CHARS = 256 * 1024;
  const STRING_PREVIEW_CHARS = 600;
  const CHILD_CHUNK = 200;
  const EXPAND_ALL_BUDGET = 3000;
  const HEX_PREVIEW_BYTES = 512;
  // Base64-looking strings up to this many characters are decoded as the
  // tree renders them; longer ones keep a manual "decode base64" button.
  const BASE64_AUTO_DECODE_CHARS = 1024 * 1024;
  const HEX_MORE_BYTES = 16384;
  const SEARCH_DEBOUNCE_MS = 300;
  const PANE_STORAGE_KEY = "data_inspector_sidebar_width";
  const FILES_FILTER_HEIGHT_KEY = "data_files_filter_height";
  const FILES_FILTER_PANEL_KEY = "data_files_filters_collapsed";
  const FILES_GROUP_KEY = "data_files_last_group";
  const FILES_PAGE_SIZE_KEY = "data_files_page_size";
  const SQL_DRAFT_KEY = "data_sql_draft";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const PATH_ID_KEY = /path_?id$/i;
  const BASE64_TEXT = /^[A-Za-z0-9+/]+={0,2}$/;

  const WebUI = window.WebUI;
  const { $ } = WebUI;
  const esc = WebUI.escapeHtml;
  const formatNumber = WebUI.formatNumber;
  const zh = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh")
    .toLowerCase().startsWith("zh");
  const ui = (en, cn) => (zh() ? cn : en);
  const isMobileLayout = () => !!(window.matchMedia && window.matchMedia(MOBILE_LAYOUT_QUERY).matches);
  const shell = () => WebUI.dataInspectorShell || {};
  const formatBytes = (value) => (shell().formatBytes ? shell().formatBytes(value) : `${value} B`);

  // ------------------------------------------------------------------ API --

  class StoreApiError extends Error {
    constructor(message, { status = 0, unavailable = false } = {}) {
      super(message);
      this.status = status;
      this.unavailable = unavailable;
    }
  }

  // A static host (or a serve.py that predates the API) answers with a
  // non-JSON 404 or no response at all; that is "unavailable", not an error.
  async function storeApi(endpoint, params = {}) {
    let response;
    try {
      const url = new URL(`${API_PREFIX}${endpoint ? `/${endpoint}` : ""}`, window.location.href);
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
      }
      response = await fetch(url, { cache: "no-store", headers: { Accept: "application/json" } });
    } catch (error) {
      throw new StoreApiError(error?.message || String(error), { unavailable: true });
    }
    const type = response.headers.get("content-type") || "";
    const body = type.includes("json") ? await response.json().catch(() => null) : null;
    if (!response.ok || !body) {
      throw new StoreApiError(body?.error || `${response.status} ${response.statusText}`.trim(), {
        status: response.status,
        unavailable: !body || response.status === 404 || response.status === 503,
      });
    }
    return body;
  }

  // ----------------------------------------------------------- page state --

  const page = {
    app: null,
    mounted: false,
    mode: "",
    panes: {},
    rendered: { files: false, sql: false },
    // Per root: { ok, payload, error, unavailable } once probed.
    roots: { current: null, previous: null },
    probing: null,
    lastAppliedLink: "",
  };

  const files = {
    root: "current",
    store: "",
    group: "",
    field: "name",
    query: "",
    total: 0,
    offset: 0,
    rows: [],
    loading: false,
    error: "",
    reqToken: 0,
    pager: null,
    filterPanel: null,
    selected: null,
    autoSelect: "",
    autoSelectSingle: false,
    pathIdHits: null,
    doc: null,
    docToken: 0,
    qTimer: 0,
    renderFrame: 0,
  };

  const sql = {
    root: "current",
    store: "unity",
    text: "",
    running: false,
    result: null,
    error: "",
    token: 0,
  };

  function storeLabel(id) {
    if (id === "unity") return ui("Unity objects", "Unity 对象");
    if (id === "game-files") return ui("Packed game files", "打包的游戏文件");
    return id;
  }

  function rootPayload(root) {
    const probe = page.roots[root];
    return probe && probe.ok ? probe.payload : null;
  }

  function storesFor(root) {
    return rootPayload(root)?.stores || [];
  }

  function hasPreviousStores() {
    return storesFor("previous").length > 0;
  }

  function apiAvailable() {
    return !!page.roots.current?.ok;
  }

  function storeHasGroup(root, store, group) {
    return storesFor(root).some((entry) => entry.id === store && entry.groups.some((item) => item.name === group));
  }

  function unityStoreIn(root) {
    return storesFor(root).some((entry) => entry.id === "unity");
  }

  // -------------------------------------------------------------- mode UI --

  function modeSwitchHtml(active) {
    const labels = { files: ui("Files", "文件"), sql: "SQL", decoded: ui("Decoded", "解码") };
    const titles = {
      files: ui("Browse export-store rows and view their documents", "浏览导出存储中的行并查看文档"),
      sql: ui("Run one read-only SQL statement over a store", "对存储执行一条只读 SQL 语句"),
      decoded: ui("Generated decoder datasets (Decoded Data Inspector)", "生成的解码数据集（解码数据检查器）"),
    };
    return `<div class="data-page-modes" role="tablist" aria-label="${esc(ui("Data page mode", "数据页模式"))}">${MODES
      .map((mode) => `<button type="button" role="tab" data-data-mode="${mode}" title="${esc(titles[mode])}"
        class="${mode === active ? "is-active" : ""}" aria-selected="${mode === active}">${esc(labels[mode])}</button>`)
      .join("")}</div>`;
  }

  function messagePaneHtml(mode, html, { error = false } = {}) {
    return `<div class="data-page-message">${modeSwitchHtml(mode)}
      <div class="data-inspector-empty${error ? " is-error" : ""}">${html}</div></div>`;
  }

  function unavailableHtml() {
    const probe = page.roots.current;
    if (probe && !probe.ok && !probe.unavailable) {
      return `${esc(ui("The export stores could not be read:", "无法读取导出存储："))}<br><code>${esc(probe.error)}</code>`;
    }
    return `${esc(ui(
      "Files and SQL read the export's SQLite stores (game/Unity.sqlite, game/GameFiles.sqlite) through the local server's store API, which a static package does not have. Start the WebUI from the repository with",
      "文件与 SQL 模式通过本地服务器的存储 API 读取导出的 SQLite 存储（game/Unity.sqlite、game/GameFiles.sqlite），静态包中没有该 API。请在仓库中运行",
    ))} <code>python serve.py</code>${esc(ui(
      ", or restart a server that predates the store API. Decoded mode works without it.",
      " 启动 WebUI；若服务器早于存储 API，请重启。解码模式不需要它。",
    ))}${probe?.error ? `<br><code>${esc(probe.error)}</code>` : ""}`;
  }

  function setMode(mode, { updateUrl = true } = {}) {
    if (!MODES.includes(mode) || !page.app) return;
    page.mode = mode;
    for (const [name, pane] of Object.entries(page.panes)) pane.hidden = name !== mode;
    page.app.querySelector(".data-page")?.setAttribute("data-mode", mode);
    if (mode === "files") ensureFilesPane();
    else if (mode === "sql") ensureSqlPane();
    else if (mode === "decoded") WebUI.decodedInspector?.load(page.panes.decoded);
    if (updateUrl) syncModeUrl();
    requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
  }

  function pageIsActive() {
    return document.body.dataset.activeView === "data-inspector";
  }

  function replaceUrl(mutate) {
    if (!pageIsActive()) return;
    const url = new URL(window.location.href);
    mutate(url.searchParams);
    const next = `${url.pathname}${url.search}${url.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      history.replaceState(history.state, "", next);
    }
    page.lastAppliedLink = linkKey(readLinkParams());
  }

  // Each mode owns its own parameters; switching clears the others so a
  // copied URL reopens exactly what is on screen.
  function syncModeUrl() {
    if (page.mode === "files") {
      syncFilesUrl();
      return;
    }
    replaceUrl((params) => {
      for (const key of WebUI.DATA_PAGE_PARAMS || []) params.delete(key);
      params.set("dataMode", page.mode);
      if (page.mode !== "decoded") {
        params.delete("inspectDataset");
        params.delete("inspect");
      }
    });
    if (page.mode === "decoded") WebUI.decodedInspector?.syncQuery();
  }

  function syncFilesUrl() {
    replaceUrl((params) => {
      for (const key of WebUI.DATA_PAGE_PARAMS || []) params.delete(key);
      params.delete("inspectDataset");
      params.delete("inspect");
      params.set("dataMode", "files");
      if (files.root !== "current") params.set("dataRoot", files.root);
      if (files.store) params.set("dataStore", files.store);
      if (files.group) params.set("dataGroup", files.group);
      const selected = files.selected;
      if (selected && selected.root === files.root && selected.store === files.store && selected.group === files.group) {
        params.set("dataName", selected.row.name);
      }
      if (files.query) {
        params.set("dataQ", files.query);
        if (files.field !== "name") params.set("dataField", files.field);
      }
    });
  }

  function readLinkParams() {
    const params = new URLSearchParams(window.location.search);
    return {
      mode: params.get("dataMode") || "",
      root: params.get("dataRoot") === "previous" ? "previous" : "current",
      store: params.get("dataStore") || "",
      group: params.get("dataGroup") || "",
      name: params.get("dataName") || "",
      query: params.get("dataQ") || "",
      field: params.get("dataField") || "",
      decoded: !!(params.get("inspect") || params.get("inspectDataset")),
    };
  }

  function linkKey(link) {
    return JSON.stringify([link.mode, link.root, link.store, link.group, link.name, link.query, link.field, link.decoded]);
  }

  // --------------------------------------------------------------- mount --

  async function probeRoot(root) {
    try {
      return { ok: true, payload: await storeApi("", { root }) };
    } catch (error) {
      return { ok: false, error: error.message, unavailable: !!error.unavailable };
    }
  }

  function initialMode(link) {
    if (link.decoded) return "decoded";
    const hasStores = storesFor("current").length > 0 || hasPreviousStores();
    if (MODES.includes(link.mode)) return link.mode === "decoded" || apiAvailable() ? link.mode : "decoded";
    if (link.store || link.group || link.name) return apiAvailable() ? "files" : "decoded";
    return apiAvailable() && hasStores ? "files" : "decoded";
  }

  async function mount() {
    if (page.mounted) return;
    const app = $("#data-inspector-app");
    if (!app) return;
    page.mounted = true;
    page.app = app;
    app.innerHTML = `
      <div class="data-page" data-mode="">
        <div id="data-page-files" class="data-page-pane" data-pane="files"></div>
        <div id="data-page-sql" class="data-page-pane" data-pane="sql" hidden></div>
        <div id="data-page-decoded" class="data-page-pane" data-pane="decoded" hidden></div>
      </div>`;
    page.panes = {
      files: $("#data-page-files", app),
      sql: $("#data-page-sql", app),
      decoded: $("#data-page-decoded", app),
    };
    app.addEventListener("click", (event) => {
      const button = event.target.closest("[data-data-mode]");
      if (!button || !app.contains(button)) return;
      event.preventDefault();
      setMode(button.dataset.dataMode);
    });
    page.panes.files.innerHTML = messagePaneHtml("files", esc(ui("Reading the export stores…", "正在读取导出存储…")));

    const link = readLinkParams();
    page.roots.current = await probeRoot("current");
    const previousProbe = probeRoot("previous").then((result) => {
      page.roots.previous = result;
      syncRootSelects();
    });
    // The previous root decides the first view when it is asked for, or when
    // the current export has no stores to show.
    if (link.root === "previous" || !storesFor("current").length) await previousProbe;
    // A mode picked while the probe ran rendered without its result.
    page.rendered = { files: false, sql: false };
    applyLink(link, { initial: true });
  }

  // Apply a deep link. Files links set the search to the row name so the
  // list shows it, and select the exact row once the page arrives.
  function applyLink(link, { initial = false } = {}) {
    page.lastAppliedLink = linkKey(link);
    const mode = initial ? initialMode(link) : (link.decoded ? "decoded" : (MODES.includes(link.mode) ? link.mode : "files"));
    if (mode === "files" && (link.store || link.group || link.name || link.query)) {
      files.root = link.root === "previous" && hasPreviousStores() ? "previous" : "current";
      if (link.store) files.store = link.store;
      if (link.group) files.group = link.group;
      files.field = ["name", "object", "pathId", "cab"].includes(link.field) ? link.field : "name";
      files.query = link.name || link.query;
      if (link.name) files.field = "name";
      files.autoSelect = link.name;
      files.pathIdHits = null;
      files.offset = 0;
      files.rows = [];
      files.error = "";
      if (page.rendered.files) renderFilesPane();
    }
    setMode(mode);
  }

  function onViewChanged(view) {
    if (view !== "data-inspector") return;
    if (!page.mounted) {
      mount();
      return;
    }
    const link = readLinkParams();
    if (linkKey(link) !== page.lastAppliedLink && (link.store || link.group || link.name || link.mode)) applyLink(link);
    else requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
  }

  // In-page navigation for links carrying `data-data-page-link`: push the URL
  // and switch views without reloading. A modified click keeps the browser's
  // own behavior (new tab, etc.).
  function openDataPageUrl(href) {
    const url = new URL(href, window.location.href);
    history.pushState(null, "", `${url.pathname}${url.search}${url.hash}`);
    // pushState fires no hashchange; tell the view router directly.
    if (typeof WebUI.setActiveView === "function") WebUI.setActiveView("data-inspector");
    else window.dispatchEvent(new HashChangeEvent("hashchange"));
  }

  document.addEventListener("click", (event) => {
    const link = event.target.closest?.("a[data-data-page-link]");
    if (!link || event.defaultPrevented || event.button !== 0
        || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    openDataPageUrl(link.href);
  });

  // ============================================================== FILES ====

  function pickDefaultGroup() {
    const stores = storesFor(files.root);
    if (files.store && files.group && storeHasGroup(files.root, files.store, files.group)) return;
    const remembered = String(WebUI.storageGet?.(FILES_GROUP_KEY) || "");
    const [rememberedStore, rememberedGroup] = remembered.split("|");
    if (rememberedStore && storeHasGroup(files.root, rememberedStore, rememberedGroup)) {
      files.store = rememberedStore;
      files.group = rememberedGroup;
      return;
    }
    const store = stores.find((entry) => entry.id === files.store && entry.groups.length)
      || stores.find((entry) => entry.groups.length);
    files.store = store?.id || "";
    files.group = store?.groups[0]?.name || "";
  }

  function ensureFilesPane() {
    if (page.rendered.files) return;
    renderFilesPane();
  }

  function fieldOptions() {
    const options = [["name", ui("Row name", "行名称")]];
    if (files.store === "unity") {
      options.push(["object", ui("Object name", "对象名称")], ["pathId", "PathID"], ["cab", "CAB"]);
    }
    return options;
  }

  function fieldHint(field) {
    return {
      name: ui("Case-insensitive substring; * and ? make it a glob.", "不区分大小写的子串；含 * 或 ? 时按通配符匹配。"),
      object: ui("Object-name substring.", "对象名称子串。"),
      pathId: ui("A PathID in decimal or as 16 hex digits.", "十进制或 16 位十六进制 PathID。"),
      cab: ui("The exact source CAB, e.g. CAB-0123…", "完整的来源 CAB，例如 CAB-0123…"),
    }[field] || "";
  }

  // `fetch: false` re-renders from the rows already read (a locale change).
  function renderFilesPane({ fetch = true } = {}) {
    const pane = page.panes.files;
    if (!pane) return;
    page.rendered.files = true;
    if (!apiAvailable()) {
      pane.innerHTML = messagePaneHtml("files", unavailableHtml(), { error: !!page.roots.current && !page.roots.current.unavailable });
      return;
    }
    if (files.root === "previous" && !hasPreviousStores()) files.root = "current";
    if (files.root === "current" && !storesFor("current").length && hasPreviousStores()) files.root = "previous";
    pickDefaultGroup();
    if (files.store !== "unity" && files.field !== "name") files.field = "name";
    pane.innerHTML = `
      <div class="data-inspector-shell data-page-shell">
        <aside id="data-files-left" class="data-page-left">
          ${modeSwitchHtml("files")}
          <header>
            <h1>${esc(ui("Export stores", "导出存储"))}</h1>
            <div id="data-files-stats" class="data-page-stats"></div>
            <div class="sidebar-header-actions">
              <button id="data-files-filter-toggle" class="panel-toggle" type="button" aria-controls="data-files-filter-panel" aria-expanded="true"></button>
              <button id="data-files-reset" class="data-page-reset" type="button">${esc(ui("Clear search", "清除搜索"))}</button>
            </div>
          </header>
          <div id="data-files-filter-panel" class="filters">
            <section class="filter-section filter-section-basic" data-filter-section="data-files-basic" data-fixed-open="1">
              <div class="filter-section-title"><span data-filter-section-label>${esc(ui("Search", "搜索"))}</span></div>
              <div class="filter-section-body filter-section-body-stack">
                <div id="data-files-root-row" class="filter-control-row" hidden>
                  <label for="data-files-root">${esc(ui("Export", "导出"))}</label>
                  <select id="data-files-root"></select>
                </div>
                <input id="data-files-q" type="search" autocomplete="off" spellcheck="false" value="${esc(files.query)}"
                  placeholder="${esc(ui("Search this group", "在当前分组中搜索"))}">
                <div class="filter-control-row">
                  <label for="data-files-field">${esc(ui("Match", "匹配"))}</label>
                  <select id="data-files-field"></select>
                </div>
                <p id="data-files-hint" class="data-page-hint"></p>
              </div>
            </section>
            <section class="filter-section" data-filter-section="data-files-groups">
              <button class="filter-section-toggle" type="button" aria-expanded="true" aria-controls="data-files-groups-body">
                <span data-filter-section-label>${esc(ui("Stores and groups", "存储与分组"))}</span>
              </button>
              <div id="data-files-groups-body" class="filter-section-body">
                <div id="data-files-groups" class="data-files-groups"></div>
              </div>
            </section>
          </div>
          <div id="data-files-filter-splitter" class="filter-splitter" role="separator" aria-label="${esc(ui("Resize filters", "调整筛选区高度"))}" aria-orientation="horizontal" tabindex="0"></div>
          <div id="data-files-hits" class="data-files-hits" hidden></div>
          <div id="data-files-list-meta" class="data-page-list-meta"></div>
          <div id="data-files-list-wrap" class="data-page-list-wrap">
            <div id="data-files-list-spacer"></div>
            <div id="data-files-list" class="data-page-list" role="listbox" aria-label="${esc(ui("Store rows", "存储行"))}"></div>
          </div>
          <footer id="data-files-pager"></footer>
        </aside>
        <div id="data-files-splitter" class="pane-splitter" role="separator" aria-label="${esc(ui("Resize sidebar", "调整侧栏宽度"))}" aria-orientation="vertical" tabindex="0"></div>
        <main id="data-files-right" class="data-page-right"></main>
      </div>`;
    bindFilesEvents(pane);
    shell().bindFilterSections?.(pane);
    files.filterPanel = WebUI.filters?.createPanelToggle?.({
      panel: "#data-files-filter-panel",
      toggle: "#data-files-filter-toggle",
      left: "#data-files-left",
      storageKey: FILES_FILTER_PANEL_KEY,
      isMobile: isMobileLayout,
      labels: (collapsed) => (collapsed ? ui("Show filters", "显示筛选") : ui("Hide filters", "隐藏筛选")),
      onChange: () => window.dispatchEvent(new Event("resize")),
    }) || null;
    shell().setupListShellSplitters?.({
      shell: $(".data-page-shell", pane),
      sidebar: $("#data-files-left", pane),
      pane: $("#data-files-splitter", pane),
      panel: $("#data-files-filter-panel", pane),
      filter: $("#data-files-filter-splitter", pane),
      list: $("#data-files-list-wrap", pane),
      paneStorageKey: PANE_STORAGE_KEY,
      filterStorageKey: FILES_FILTER_HEIGHT_KEY,
    });
    files.pager = WebUI.pagination?.createPager({
      container: $("#data-files-pager", pane),
      storageKey: FILES_PAGE_SIZE_KEY,
      defaultPageSize: 200,
      onChange: () => fetchRows(),
    }) || null;
    syncRootSelects();
    syncFieldSelect();
    renderStats();
    renderGroups();
    renderHits();
    renderViewer();
    if (!fetch) {
      files.pager?.setTotal(files.total);
      files.pager?.showIndex(files.offset);
      renderListMeta();
      applyListRows({ resetScroll: false });
    } else {
      fetchRows();
    }
  }

  function bindFilesEvents(pane) {
    $("#data-files-q", pane)?.addEventListener("input", (event) => {
      clearTimeout(files.qTimer);
      const value = event.target.value;
      files.qTimer = setTimeout(() => {
        files.query = value.trim();
        files.pathIdHits = null;
        files.autoSelect = "";
        files.pager?.reset();
        renderHits();
        fetchRows();
      }, SEARCH_DEBOUNCE_MS);
    });
    $("#data-files-field", pane)?.addEventListener("change", (event) => {
      files.field = event.target.value;
      files.pathIdHits = null;
      syncFieldSelect();
      renderHits();
      files.pager?.reset();
      if (files.query) fetchRows();
      else syncFilesUrl();
    });
    $("#data-files-root", pane)?.addEventListener("change", (event) => {
      files.root = event.target.value === "previous" ? "previous" : "current";
      files.pathIdHits = null;
      pickDefaultGroup();
      syncFieldSelect();
      renderStats();
      renderGroups();
      renderHits();
      files.pager?.reset();
      fetchRows();
    });
    $("#data-files-reset", pane)?.addEventListener("click", () => {
      files.query = "";
      files.field = "name";
      files.pathIdHits = null;
      files.autoSelect = "";
      const input = $("#data-files-q", pane);
      if (input) input.value = "";
      syncFieldSelect();
      renderHits();
      files.pager?.reset();
      fetchRows();
    });
    $("#data-files-list-wrap", pane)?.addEventListener("scroll", scheduleListRender, { passive: true });
    $("#data-files-list", pane)?.addEventListener("click", (event) => {
      const button = event.target.closest(".data-files-row[data-row-index]");
      if (!button) return;
      const row = files.rows[Number(button.dataset.rowIndex)];
      if (row) selectRow(row);
    });
    $("#data-files-list", pane)?.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      const index = files.rows.findIndex((row) => rowKey(row) === selectedKey());
      const next = index + (event.key === "ArrowDown" ? 1 : -1);
      if (next < 0 || next >= files.rows.length) return;
      event.preventDefault();
      selectRow(files.rows[next]);
      scrollRowIntoView(next);
      requestAnimationFrame(() => $(`.data-files-row[data-row-index="${next}"]`, pane)?.focus());
    });
    $("#data-files-right", pane)?.addEventListener("click", onViewerClick);
    $("#data-files-hits", pane)?.addEventListener("click", (event) => {
      if (event.target.closest("[data-hits-close]")) {
        files.pathIdHits = null;
        renderHits();
      }
    });
  }

  function syncRootSelects() {
    const previous = hasPreviousStores();
    const current = rootPayload("current");
    const prior = rootPayload("previous");
    const options = `<option value="current">${esc(ui("Current", "当前"))}${current?.root ? ` · ${esc(current.root)}` : ""}</option>
      <option value="previous">${esc(ui("Previous", "上一版"))}${prior?.root ? ` · ${esc(prior.root)}` : ""}</option>`;
    for (const [rowId, selectId, value] of [
      ["data-files-root-row", "data-files-root", files.root],
      ["data-sql-root-row", "data-sql-root", sql.root],
    ]) {
      const row = document.getElementById(rowId);
      const select = document.getElementById(selectId);
      if (!row || !select) continue;
      row.hidden = !previous;
      select.innerHTML = options;
      select.value = previous ? value : "current";
    }
  }

  function syncFieldSelect() {
    const select = $("#data-files-field", page.panes.files);
    if (!select) return;
    const options = fieldOptions();
    if (!options.some(([value]) => value === files.field)) files.field = "name";
    select.innerHTML = options.map(([value, label]) => `<option value="${value}">${esc(label)}</option>`).join("");
    select.value = files.field;
    const hint = $("#data-files-hint", page.panes.files);
    if (hint) hint.textContent = fieldHint(files.field);
    const input = $("#data-files-q", page.panes.files);
    if (input && input.value !== files.query) input.value = files.query;
    WebUI.setFilterSectionActiveCounts?.({ "data-files-basic": files.query ? 1 : 0 });
  }

  function renderStats() {
    const host = $("#data-files-stats", page.panes.files);
    if (!host) return;
    const stores = storesFor(files.root);
    const rows = stores.reduce((sum, entry) => sum + (Number(entry.rows) || 0), 0);
    host.textContent = `${formatNumber(rows)} ${ui("rows", "行")} · ${formatNumber(stores.length)} ${ui("stores", "个存储")}`
      + (rootPayload(files.root)?.root ? ` · ${rootPayload(files.root).root}` : "");
  }

  function renderGroups() {
    const host = $("#data-files-groups", page.panes.files);
    if (!host) return;
    const stores = storesFor(files.root);
    if (!stores.length) {
      host.innerHTML = `<p class="data-page-hint">${esc(ui(
        "This export has no store files (game/Unity.sqlite, game/GameFiles.sqlite).",
        "该导出没有存储文件（game/Unity.sqlite、game/GameFiles.sqlite）。",
      ))}</p>`;
      return;
    }
    host.innerHTML = stores.map((entry) => {
      const lost = Array.isArray(entry.unreadableAtPack) ? entry.unreadableAtPack : [];
      const lostTitle = lost.slice(0, 20).map((item) => (item && typeof item === "object"
        ? `${[item.type, item.name].filter(Boolean).join("/") || item.path || ""}${item.error ? `: ${item.error}` : ""}`
        : String(item))).join("\n");
      return `<div class="data-files-store">
        <div class="data-files-store-head" title="${esc(entry.file || "")}">
          <span class="data-files-store-name">${esc(storeLabel(entry.id))}</span>
          <span class="data-files-store-meta"><code>${esc(entry.file || entry.id)}</code> · ${esc(formatBytes(entry.bytes))} · ${esc(formatNumber(entry.rows))} ${esc(ui("rows", "行"))}</span>
          ${lost.length ? `<span class="data-inspector-chip is-warn" title="${esc(lostTitle)}">${esc(formatNumber(lost.length))} ${esc(ui("unreadable at pack, not stored", "打包时不可读，未存入"))}</span>` : ""}
        </div>
        <div class="chips data-files-group-chips" data-store-chips="${esc(entry.id)}"></div>
      </div>`;
    }).join("");
    for (const entry of stores) {
      const container = host.querySelector(`[data-store-chips="${CSS.escape(entry.id)}"]`);
      WebUI.filters?.buildChips(container, entry.groups.map((group) => ({
        value: `${entry.id}|${group.name}`,
        label: group.name,
        count: group.count,
        className: "kind-chip is-path-chip",
      })), {
        single: true,
        active: `${files.store}|${files.group}`,
        onToggle: (_next, info) => selectGroup(entry.id, info.value.slice(entry.id.length + 1)),
      });
    }
  }

  function selectGroup(store, group, { keepQuery = false } = {}) {
    if (store === files.store && group === files.group) return;
    files.store = store;
    files.group = group;
    WebUI.storageSet?.(FILES_GROUP_KEY, `${store}|${group}`);
    if (!keepQuery) {
      files.pathIdHits = null;
      files.autoSelect = "";
    }
    syncFieldSelect();
    renderGroups();
    renderHits();
    files.pager?.reset();
    fetchRows();
  }

  function renderHits() {
    const host = $("#data-files-hits", page.panes.files);
    if (!host) return;
    const hits = files.pathIdHits;
    if (!hits) {
      host.hidden = true;
      host.innerHTML = "";
      return;
    }
    host.hidden = false;
    const close = `<button type="button" class="data-files-hits-close" data-hits-close aria-label="${esc(ui("Close", "关闭"))}">×</button>`;
    if (hits.error) {
      host.innerHTML = `${close}<div class="is-error">${esc(hits.error)}</div>`;
      return;
    }
    if (!hits.types.length) {
      host.innerHTML = `${close}<div>${esc(ui("No Unity object in this export has PathID", "该导出中没有 PathID 为"))} <code>${esc(hits.pathId)}</code>${esc(ui(".", " 的 Unity 对象。"))}</div>`;
      return;
    }
    host.innerHTML = `${close}
      <div>PathID <code>${esc(hits.pathId)}</code> ${esc(ui("occurs in", "出现在"))}</div>
      <div class="chips" id="data-files-hit-chips"></div>
      <p class="data-page-hint">${esc(ui(
        "A PathID is unique only within one CAB; compare the CAB of each row.",
        "PathID 仅在同一 CAB 内唯一；请比较各行的 CAB。",
      ))}</p>`;
    WebUI.filters?.buildChips($("#data-files-hit-chips", host), hits.types.map((item) => ({
      value: item.type,
      label: item.type,
      count: item.rows,
      className: "kind-chip is-path-chip",
    })), {
      single: true,
      active: files.store === "unity" ? files.group : "",
      onToggle: (_next, info) => selectGroup("unity", info.value, { keepQuery: true }),
    });
  }

  // One page of rows. The API caps a request at 1,000 rows, so a larger page
  // size is read in consecutive requests.
  async function fetchRows() {
    syncFilesUrl();
    const token = ++files.reqToken;
    if (!files.store || !files.group) {
      files.rows = [];
      files.total = 0;
      files.error = "";
      files.pager?.setTotal(0);
      renderListMeta();
      applyListRows({ resetScroll: true });
      return;
    }
    const pageSize = files.pager?.pageSize || 200;
    const offset = (files.pager?.page || 0) * pageSize;
    files.loading = true;
    renderListMeta();
    let rows = [];
    let total = 0;
    try {
      while (rows.length < pageSize) {
        const limit = Math.min(MAX_API_ROWS, pageSize - rows.length);
        const result = await storeApi("rows", {
          root: files.root,
          store: files.store,
          group: files.group,
          q: files.query,
          field: files.query ? files.field : "name",
          offset: offset + rows.length,
          limit,
        });
        if (token !== files.reqToken) return;
        total = Number(result.total) || 0;
        rows = rows.concat(result.rows || []);
        if ((result.rows || []).length < limit) break;
      }
      files.error = "";
    } catch (error) {
      if (token !== files.reqToken) return;
      files.error = error.message;
      rows = [];
      total = 0;
    }
    files.loading = false;
    files.rows = rows;
    files.total = total;
    files.offset = offset;
    files.pager?.setTotal(total);
    if (files.pager && files.pager.page * pageSize !== offset && total > 0) {
      // The total shrank below this page; the pager moved back, so refetch.
      fetchRows();
      return;
    }
    renderListMeta();
    applyListRows({ resetScroll: true });
    resolveAutoSelect();
  }

  function resolveAutoSelect() {
    if (files.autoSelect) {
      const wanted = files.autoSelect;
      files.autoSelect = "";
      const index = Math.max(
        files.rows.findIndex((row) => row.name === wanted),
        files.rows.findIndex((row) => row.name.toLowerCase() === wanted.toLowerCase()),
      );
      if (index >= 0) {
        selectRow(files.rows[index]);
        scrollRowIntoView(index);
      } else if (!files.error) {
        showViewerMessage(`${esc(ui("No row named", "未找到名为"))} <code>${esc(wanted)}</code> ${esc(ui(
          `in ${files.store} / ${files.group}.`,
          `的行（${files.store} / ${files.group}）。`,
        ))}`, { error: true });
      }
    } else if (files.autoSelectSingle) {
      files.autoSelectSingle = false;
      if (files.rows.length === 1) selectRow(files.rows[0]);
    }
  }

  function renderListMeta() {
    const host = $("#data-files-list-meta", page.panes.files);
    if (!host) return;
    if (files.loading) {
      host.textContent = ui("Loading…", "正在加载…");
      return;
    }
    const group = files.group ? `${storeLabel(files.store)} / ${files.group}` : "";
    host.innerHTML = `<span>${esc(formatNumber(files.total))}</span> ${esc(files.query ? ui("matching rows", "条匹配行") : ui("rows", "行"))}${
      group ? ` · <span class="data-page-list-group">${esc(group)}</span>` : ""}`;
  }

  function applyListRows({ resetScroll = false } = {}) {
    const spacer = $("#data-files-list-spacer", page.panes.files);
    if (spacer) spacer.style.height = `${files.rows.length * ROW_HEIGHT}px`;
    const wrap = $("#data-files-list-wrap", page.panes.files);
    if (resetScroll && wrap) wrap.scrollTop = 0;
    renderList();
  }

  function scheduleListRender() {
    if (files.renderFrame) return;
    files.renderFrame = requestAnimationFrame(() => {
      files.renderFrame = 0;
      renderList();
    });
  }

  function rowKey(row, root = files.root, store = files.store, group = files.group) {
    return `${root}\n${store}\n${group}\n${row.name}`;
  }

  function selectedKey() {
    const selected = files.selected;
    return selected ? rowKey(selected.row, selected.root, selected.store, selected.group) : "";
  }

  function rowMetaText(row) {
    const parts = [];
    if (files.store === "unity") {
      const stem = row.name.replace(/\.[^.]+$/, "").replace(/_p[0-9A-Fa-f]{16}$/, "");
      if (row.objectName && row.objectName !== stem) parts.push(row.objectName);
      if (row.pathIdHex) parts.push(`0x${row.pathIdHex}`);
    }
    parts.push(formatBytes(row.size));
    if (files.store !== "unity" && row.sha256) parts.push(String(row.sha256).slice(0, 12));
    return parts.join(" · ");
  }

  function renderList() {
    const wrap = $("#data-files-list-wrap", page.panes.files);
    const list = $("#data-files-list", page.panes.files);
    if (!wrap || !list) return;
    if (files.error) {
      list.innerHTML = `<div class="data-inspector-empty-list is-error">${esc(files.error)}</div>`;
      return;
    }
    if (!files.rows.length) {
      list.innerHTML = `<div class="data-inspector-empty-list">${esc(files.loading ? ui("Loading…", "正在加载…")
        : files.group ? ui("No matching rows.", "没有匹配的行。") : ui("Select a group.", "请选择一个分组。"))}</div>`;
      return;
    }
    const current = selectedKey();
    const startTop = Math.max(0, wrap.scrollTop - OVERSCAN_PX);
    const endTop = wrap.scrollTop + wrap.clientHeight + OVERSCAN_PX;
    const fragment = document.createDocumentFragment();
    let index = Math.max(0, Math.min(files.rows.length, Math.floor(startTop / ROW_HEIGHT)));
    for (; index < files.rows.length && index * ROW_HEIGHT < endTop; index += 1) {
      const row = files.rows[index];
      const selected = rowKey(row) === current;
      const button = document.createElement("button");
      button.type = "button";
      button.className = `data-inspector-row data-files-row${selected ? " is-selected" : ""}`;
      button.dataset.rowIndex = String(index);
      button.style.top = `${index * ROW_HEIGHT}px`;
      button.style.height = `${ROW_HEIGHT}px`;
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", String(selected));
      button.innerHTML = `<span class="data-inspector-row-title" title="${esc(row.name)}">${esc(row.name)}</span>
        <span class="data-inspector-row-path">${esc(rowMetaText(row))}</span>`;
      fragment.appendChild(button);
    }
    list.replaceChildren(fragment);
  }

  function scrollRowIntoView(index) {
    const wrap = $("#data-files-list-wrap", page.panes.files);
    if (!wrap) return;
    const top = index * ROW_HEIGHT;
    if (top < wrap.scrollTop || top + ROW_HEIGHT > wrap.scrollTop + wrap.clientHeight) {
      wrap.scrollTop = Math.max(0, top - wrap.clientHeight / 2);
    }
    renderList();
  }

  // -------------------------------------------------------------- viewer --

  function selectRow(row) {
    files.selected = { root: files.root, store: files.store, group: files.group, row };
    files.doc = null;
    renderList();
    syncFilesUrl();
    renderViewer();
    loadDocument();
  }

  function showViewerMessage(html, { error = false } = {}) {
    const host = $("#data-files-right", page.panes.files);
    if (host) host.innerHTML = `<div class="data-inspector-empty${error ? " is-error" : ""}">${html}</div>`;
  }

  function factCard(label, valueHtml, { title = "", wide = false } = {}) {
    return `<div class="data-inspector-fact${wide ? " is-wide" : ""}">
      <div class="data-inspector-fact-label"${title ? ` title="${esc(title)}"` : ""}>${esc(label)}</div>
      <div class="data-inspector-fact-value">${valueHtml}</div>
    </div>`;
  }

  function findPathIdButton(value) {
    if (!unityStoreIn(files.root) || !/^-?\d+$/.test(String(value)) || String(value) === "0") return "";
    return `<button type="button" class="data-page-inline-action" data-find-path-id="${esc(value)}"
      title="${esc(ui("Find Unity rows with this PathID", "查找具有此 PathID 的 Unity 行"))}">${esc(ui("find", "查找"))}</button>`;
  }

  function renderViewer() {
    const host = $("#data-files-right", page.panes.files);
    if (!host) return;
    const selected = files.selected;
    if (!selected) {
      host.innerHTML = `<div class="data-inspector-empty">${esc(ui(
        "Select a row to view its document.",
        "选择一行以查看其文档。",
      ))}</div>`;
      return;
    }
    const { row, store, group, root } = selected;
    const unity = store === "unity";
    const cards = [
      factCard(ui("Size", "大小"), `${esc(formatBytes(row.size))}<span class="data-inspector-alt-form">${esc(formatNumber(row.size))} B</span>`),
      factCard("SHA-256", `<code class="data-page-hash">${esc(row.sha256 || "")}</code>`, { wide: true }),
    ];
    if (unity) {
      if (row.objectName) cards.push(factCard(ui("Object name", "对象名称"), `<code>${esc(row.objectName)}</code>`));
      if (row.pathId != null) {
        cards.push(factCard("PathID", `<code>${esc(row.pathId)}</code><span class="data-inspector-alt-form">0x${esc(row.pathIdHex || "")}</span>${findPathIdButton(row.pathId)}`));
      }
      if (row.sourceFile) {
        cards.push(factCard("CAB", `<code>${esc(row.sourceFile)}</code><button type="button" class="data-page-inline-action" data-filter-cab="${esc(row.sourceFile)}"
          title="${esc(ui("List rows of this group from the same CAB", "列出本分组中来自同一 CAB 的行"))}">${esc(ui("filter", "筛选"))}</button>`, { wide: true }));
      }
      if (row.scriptPathId != null) {
        cards.push(factCard(ui("Script PathID", "脚本 PathID"), `<code>${esc(row.scriptPathId)}</code>${findPathIdButton(row.scriptPathId)}`));
      }
    } else {
      cards.push(factCard(ui("Packed folder", "打包目录"), `<code>${esc(group)}</code>`));
    }
    host.innerHTML = `
      <article class="data-inspector-record data-files-record">
        <header class="data-inspector-detail-header">
          <div class="data-inspector-eyebrow">
            <span class="data-inspector-row-family is-tone-${unity ? 0 : 1}">${esc(storeLabel(store))}</span>
            <span class="data-inspector-chip is-tag">${esc(group)}</span>
            ${root !== "current" ? `<span class="data-inspector-chip is-warn">${esc(ui("previous export", "上一版导出"))}</span>` : ""}
          </div>
          <h1>${esc(row.name)}</h1>
          <div class="data-inspector-detail-path"><code>${esc(row.ref)}</code></div>
          <div class="data-inspector-actions">
            <button type="button" data-copy-text="${esc(row.ref)}">${esc(ui("Copy ref", "复制引用"))}</button>
            <a href="${esc(row.url)}" target="_blank" rel="noopener">${esc(ui("Open raw", "打开原始文件"))}</a>
            <button type="button" data-copy-text="${esc(WebUI.dataPageUrl?.({ root, store, group, name: row.name }) || window.location.href)}">${esc(ui("Copy link", "复制链接"))}</button>
          </div>
        </header>
        <div class="data-inspector-detail-body">
          <section class="data-inspector-section">
            <h3>${esc(ui("Store row", "存储行"))}</h3>
            <div class="data-inspector-facts data-files-facts">${cards.join("")}</div>
          </section>
          <section class="data-inspector-section data-inspector-structure">
            <div class="data-inspector-structure-head">
              <div>
                <h3>${esc(ui("Document", "文档"))}</h3>
                <p id="data-files-doc-note" class="data-inspector-description"></p>
              </div>
              <div id="data-files-doc-tools" class="data-inspector-structure-tools"></div>
            </div>
            <div id="data-files-doc" class="data-inspector-tree data-files-doc"></div>
          </section>
        </div>
      </article>`;
    renderDocument();
  }

  // ------------------------------------------------------------ documents --

  async function readBytes(url, { limit = Infinity } = {}) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`.trim());
    if (!Number.isFinite(limit) || !response.body?.getReader) {
      return { bytes: new Uint8Array(await response.arrayBuffer()), complete: true };
    }
    const reader = response.body.getReader();
    const chunks = [];
    let total = 0;
    let complete = false;
    while (total < limit) {
      const { done, value } = await reader.read();
      if (done) {
        complete = true;
        break;
      }
      chunks.push(value);
      total += value.length;
    }
    if (!complete) reader.cancel().catch(() => {});
    const bytes = new Uint8Array(Math.min(total, complete ? total : limit));
    let offset = 0;
    for (const chunk of chunks) {
      const part = chunk.subarray(0, Math.min(chunk.length, bytes.length - offset));
      bytes.set(part, offset);
      offset += part.length;
      if (offset >= bytes.length) break;
    }
    return { bytes, complete };
  }

  function looksBinary(text) {
    const sample = text.slice(0, 8192);
    if (!sample) return false;
    let control = 0;
    for (let index = 0; index < sample.length; index += 1) {
      const code = sample.charCodeAt(index);
      if (code === 0) return true;
      if (code < 32 && code !== 9 && code !== 10 && code !== 13 && code !== 12) control += 1;
    }
    return control / sample.length > 0.01;
  }

  // An integer JSON.parse would round (a 64-bit PathID) is kept as its digits.
  class ExactInt {
    constructor(text) {
      this.text = text;
    }
  }

  const PARSE_WITH_SOURCE = (() => {
    try {
      let supported = false;
      JSON.parse("1", (_key, value, context) => {
        supported = !!context && context.source === "1";
        return value;
      });
      return supported;
    } catch (_error) {
      return false;
    }
  })();
  const BIG_INT_SENTINEL = "\u0001ExactInt:";

  function parseJsonExact(text) {
    if (!/\d{16}/.test(text)) return JSON.parse(text);
    if (PARSE_WITH_SOURCE) {
      return JSON.parse(text, (_key, value, context) => (
        typeof value === "number" && Number.isInteger(value) && !Number.isSafeInteger(value)
          && context && /^-?\d+$/.test(context.source) ? new ExactInt(context.source) : value
      ));
    }
    // Quote long integer literals outside strings, then restore them.
    const quoted = text.replace(/"(?:[^"\\]|\\.)*"|(?<![\w.+-])-?\d{16,}(?![\d.eE])/g, (match) => (
      match.charCodeAt(0) === 34 ? match : `"${BIG_INT_SENTINEL}${match}"`
    ));
    return JSON.parse(quoted, (_key, value) => {
      if (typeof value !== "string" || !value.startsWith(BIG_INT_SENTINEL)) return value;
      const digits = value.slice(BIG_INT_SENTINEL.length);
      return Number.isSafeInteger(Number(digits)) ? Number(digits) : new ExactInt(digits);
    });
  }

  function classify(bytes, complete, name) {
    let text = null;
    try {
      text = new TextDecoder("utf-8", { fatal: true }).decode(bytes, { stream: !complete });
    } catch (_error) {
      text = null;
    }
    if (text !== null && looksBinary(text)) text = null;
    if (text === null) return { kind: "binary" };
    if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
    const jsonLike = /\.json$/i.test(name) || /^\s*[[{]/.test(text);
    if (jsonLike && complete) {
      try {
        return { kind: "json", text, value: parseJsonExact(text), view: "tree" };
      } catch (error) {
        return { kind: "text", text, note: `${ui("Not valid JSON", "不是有效的 JSON")}: ${error.message}` };
      }
    }
    return { kind: "text", text, jsonLike };
  }

  async function loadDocument({ full = false } = {}) {
    const selected = files.selected;
    if (!selected) return;
    const token = ++files.docToken;
    const key = selectedKey();
    const size = Number(selected.row.size) || 0;
    files.doc = { key, status: "loading", full };
    renderDocument();
    try {
      const limit = full || size <= FULL_FETCH_BYTES ? Infinity : PREFIX_FETCH_BYTES;
      const { bytes, complete } = await readBytes(selected.row.url, { limit });
      if (token !== files.docToken) return;
      files.doc = { key, status: "ready", bytes, complete, showAllText: false, hexBytes: HEX_PREVIEW_BYTES,
        ...classify(bytes, complete, selected.row.name) };
    } catch (error) {
      if (token !== files.docToken) return;
      files.doc = { key, status: "error", error: error.message };
    }
    renderDocument();
  }

  function renderDocument() {
    const host = $("#data-files-doc", page.panes.files);
    const note = $("#data-files-doc-note", page.panes.files);
    const tools = $("#data-files-doc-tools", page.panes.files);
    if (!host || !note || !tools) return;
    const doc = files.doc;
    const size = Number(files.selected?.row.size) || 0;
    tools.innerHTML = "";
    resetTreeRegistry();
    if (!doc || doc.status === "loading") {
      note.textContent = formatBytes(size);
      host.innerHTML = `<div class="data-inspector-empty">${esc(ui("Loading document…", "正在加载文档…"))}</div>`;
      return;
    }
    if (doc.status === "error") {
      note.textContent = formatBytes(size);
      host.innerHTML = `<div class="data-inspector-empty is-error">${esc(ui("Document could not be loaded", "无法加载文档"))}: ${esc(doc.error)}</div>`;
      return;
    }
    const partial = !doc.complete
      ? ` · ${ui(`showing the first ${formatBytes(doc.bytes.length)}`, `仅显示前 ${formatBytes(doc.bytes.length)}`)}`
      : "";
    const loadAll = !doc.complete
      ? `<button type="button" data-doc-load-all>${esc(doc.jsonLike
        ? ui("Load whole document as a tree", "加载完整文档并显示为树")
        : ui("Load whole document", "加载完整文档"))}</button>`
      : "";
    if (doc.kind === "binary") {
      note.textContent = `${formatBytes(size)} · ${ui("binary (not UTF-8 text)", "二进制（非 UTF-8 文本）")}${partial}`;
      const shown = doc.bytes.subarray(0, doc.hexBytes);
      const more = doc.bytes.length > shown.length && doc.hexBytes < HEX_MORE_BYTES;
      host.innerHTML = `<pre class="data-page-hex">${esc(hexDump(shown))}</pre>
        <p class="data-inspector-description">${esc(ui(
          `First ${formatNumber(shown.length)} of ${formatNumber(size)} bytes. Open raw to download the whole file.`,
          `前 ${formatNumber(shown.length)} / ${formatNumber(size)} 字节。可打开原始文件下载完整内容。`,
        ))}</p>${more ? `<button type="button" class="data-page-more" data-doc-more-hex>${esc(ui(
          `Show the first ${formatNumber(Math.min(HEX_MORE_BYTES, doc.bytes.length))} bytes`,
          `显示前 ${formatNumber(Math.min(HEX_MORE_BYTES, doc.bytes.length))} 字节`,
        ))}</button>` : ""}`;
      return;
    }
    if (doc.kind === "json") {
      note.textContent = `${formatBytes(size)} · JSON`;
      tools.innerHTML = `
        ${doc.view === "tree" ? `<button type="button" data-doc-expand>${esc(ui("Expand all", "全部展开"))}</button>
        <button type="button" data-doc-collapse>${esc(ui("Collapse all", "全部折叠"))}</button>` : ""}
        <div class="data-inspector-view-switch" role="group" aria-label="${esc(ui("Document view", "文档视图"))}">
          <button type="button" data-doc-view="tree" class="${doc.view === "tree" ? "is-active" : ""}" aria-pressed="${doc.view === "tree"}">${esc(ui("Tree", "树"))}</button>
          <button type="button" data-doc-view="text" class="${doc.view === "text" ? "is-active" : ""}" aria-pressed="${doc.view === "text"}">${esc(ui("Text", "文本"))}</button>
        </div>`;
      if (doc.view === "tree") {
        host.innerHTML = rootTreeHtml(doc.value);
        return;
      }
    } else {
      note.textContent = `${formatBytes(size)} · ${ui("text", "文本")}${partial}${doc.note ? ` · ${doc.note}` : ""}`;
    }
    const text = doc.text || "";
    const shown = doc.showAllText ? text : text.slice(0, TEXT_PREVIEW_CHARS);
    host.innerHTML = `<pre class="data-page-text">${esc(shown)}</pre>${
      shown.length < text.length
        ? `<button type="button" class="data-page-more" data-doc-show-text>${esc(ui(
          `Show all ${formatNumber(text.length)} characters`,
          `显示全部 ${formatNumber(text.length)} 个字符`,
        ))}</button>`
        : ""}${loadAll}`;
  }

  function hexDump(bytes) {
    const lines = [];
    for (let offset = 0; offset < bytes.length; offset += 16) {
      const slice = bytes.subarray(offset, offset + 16);
      const hex = Array.from(slice, (byte) => byte.toString(16).padStart(2, "0")).join(" ");
      const ascii = Array.from(slice, (byte) => (byte >= 32 && byte < 127 ? String.fromCharCode(byte) : ".")).join("");
      lines.push(`${offset.toString(16).padStart(8, "0")}  ${hex.padEnd(47, " ")}  ${ascii}`);
    }
    return lines.join("\n");
  }

  // --------------------------------------------------------- JSON tree ----
  //
  // A plain tree of the document as stored: keys verbatim, lazy branches,
  // long arrays in chunks. The only affordances are shape-generic: exact
  // 64-bit integers, a "find" action on PathID-like keys, and automatic
  // base64 decoding of base64-looking strings (text inline, binary as a
  // collapsed hex dump, so a false positive stays out of the way).

  const tree = { nodes: new Map(), seq: 0 };

  function resetTreeRegistry() {
    tree.nodes.clear();
  }

  function register(value) {
    const token = `t${++tree.seq}`;
    tree.nodes.set(token, value);
    return token;
  }

  function isBranch(value) {
    return value !== null && typeof value === "object" && !(value instanceof ExactInt);
  }

  function keyLabel(key, isIndex) {
    return `<span class="data-inspector-key">${esc(isIndex ? `[${key}]` : key)}</span>`;
  }

  function integerText(value) {
    if (value instanceof ExactInt) return value.text;
    if (typeof value === "number" && Number.isInteger(value)) return String(value);
    if (typeof value === "string" && /^-?\d+$/.test(value)) return value;
    return "";
  }

  // A PathID's 64-bit two's-complement hex: the form of the `_p<hex>` suffix
  // in store row names.
  function pathIdHex(text) {
    try {
      return `0x${BigInt.asUintN(64, BigInt(text)).toString(16).toUpperCase().padStart(16, "0")}`;
    } catch (_error) {
      return "";
    }
  }

  function scalarHtml(key, value) {
    if (value === null) return '<span class="json-null">null</span>';
    if (value instanceof ExactInt || typeof value === "number") {
      const text = value instanceof ExactInt ? value.text : String(value);
      const hex = PATH_ID_KEY.test(String(key)) && /^-?\d+$/.test(text) && text !== "0" ? pathIdHex(text) : "";
      return `<span class="json-number">${esc(text)}</span>${hex ? `<span class="data-inspector-alt-form">${esc(hex)}</span>` : ""}`;
    }
    if (typeof value === "boolean") return `<span class="json-boolean is-${value}">${value}</span>`;
    const textValue = String(value);
    if (textValue === "") return `<span class="json-string is-empty">""</span>`;
    if (textValue.length <= STRING_PREVIEW_CHARS) return `<span class="json-string">${esc(JSON.stringify(textValue))}</span>`;
    return `<span class="json-string">${esc(JSON.stringify(textValue.slice(0, STRING_PREVIEW_CHARS)).slice(0, -1))}…"</span>`;
  }

  function leafActions(key, value) {
    const actions = [];
    const integer = integerText(value);
    if (integer && PATH_ID_KEY.test(String(key))) actions.push(findPathIdButton(integer));
    if (typeof value === "string") {
      const token = value.length > STRING_PREVIEW_CHARS || looksLikeBase64(value) ? register(value) : "";
      if (value.length > STRING_PREVIEW_CHARS) {
        actions.push(`<button type="button" class="data-page-inline-action" data-string-full="${token}">${esc(ui(
          `show all ${formatNumber(value.length)} chars`, `显示全部 ${formatNumber(value.length)} 个字符`,
        ))}</button>`);
      }
      if (looksLikeBase64(value) && !autoDecodesBase64(value)) {
        actions.push(`<button type="button" class="data-page-inline-action" data-base64="${token}">${esc(ui("decode base64", "base64 解码"))}</button>`);
      }
    }
    return actions.join("");
  }

  function autoDecodesBase64(value) {
    return typeof value === "string" && value.length <= BASE64_AUTO_DECODE_CHARS && looksLikeBase64(value);
  }

  function looksLikeBase64(value) {
    if (value.length < 24) return false;
    const compact = value.replace(/\s+/g, "");
    return compact.length % 4 !== 1 && BASE64_TEXT.test(compact) && /[+/=0-9]/.test(compact) && /[A-Z]/.test(compact) && /[a-z]/.test(compact);
  }

  function previewHtml(value) {
    const entries = Array.isArray(value) ? value.slice(0, 8).map((item, index) => [index, item]) : Object.entries(value).slice(0, 6);
    const shown = entries.filter(([, child]) => !isBranch(child)).slice(0, 5).map(([name, child]) => {
      const text = child instanceof ExactInt ? child.text
        : typeof child === "string" ? JSON.stringify(child.length > 40 ? `${child.slice(0, 40)}…` : child)
          : String(child);
      return Array.isArray(value) ? text : `${name}=${text}`;
    });
    return shown.length ? `<span class="data-inspector-preview">${esc(shown.join(", "))}</span>` : "";
  }

  function shapeLabel(value) {
    const count = Array.isArray(value) ? value.length : Object.keys(value).length;
    return `${Array.isArray(value) ? ui("list", "列表") : ui("object", "对象")} · ${formatNumber(count)}`;
  }

  function nodeHtml(key, value, isIndex, depth) {
    if (!isBranch(value)) {
      const leaf = `<div class="data-inspector-leaf">${keyLabel(key, isIndex)}<span class="data-inspector-value">${scalarHtml(key, value)}</span>${leafActions(key, value)}</div>`;
      return autoDecodesBase64(value) ? leaf + decodedBase64Html(value, { auto: true }) : leaf;
    }
    const count = Array.isArray(value) ? value.length : Object.keys(value).length;
    const head = `${keyLabel(key, isIndex)}<span class="data-inspector-shape">${esc(shapeLabel(value))}</span>${previewHtml(value)}`;
    if (!count) {
      return `<div class="data-inspector-leaf">${head}<span class="data-inspector-value"><span class="json-null">${esc(ui("empty", "空"))}</span></span></div>`;
    }
    const token = register(value);
    const open = depth < 1;
    return `<details class="data-inspector-branch" data-tree-token="${token}" data-depth="${depth}"${open ? " open" : ""}${open ? ' data-loaded="1"' : ""}>
      <summary><button class="data-inspector-fold" type="button" aria-expanded="${open}">${open ? "−" : "+"}</button>${head}</summary>
      <div class="data-inspector-children">${open ? childrenHtml(value, depth + 1, 0, token) : ""}</div>
    </details>`;
  }

  function childrenHtml(value, depth, start, token) {
    const isArray = Array.isArray(value);
    const keys = isArray ? null : Object.keys(value);
    const count = isArray ? value.length : keys.length;
    const end = Math.min(count, start + CHILD_CHUNK);
    const parts = [];
    for (let index = start; index < end; index += 1) {
      const key = isArray ? index : keys[index];
      parts.push(nodeHtml(String(key), value[key], isArray, depth));
    }
    if (end < count) {
      parts.push(`<button type="button" class="data-page-more" data-tree-more="${token}" data-start="${end}" data-depth="${depth}">${esc(ui(
        `Show ${formatNumber(Math.min(CHILD_CHUNK, count - end))} more (${formatNumber(count - end)} remaining)`,
        `再显示 ${formatNumber(Math.min(CHILD_CHUNK, count - end))} 项（剩余 ${formatNumber(count - end)}）`,
      ))}</button>`);
    }
    return parts.join("");
  }

  function rootTreeHtml(value) {
    if (!isBranch(value)) {
      return `<div class="data-inspector-leaf">${keyLabel("$", false)}<span class="data-inspector-value">${scalarHtml("", value)}</span></div>`;
    }
    return nodeHtml("$", value, false, 0);
  }

  function setBranchOpen(node, open) {
    node.open = open;
    const button = node.firstElementChild?.querySelector(".data-inspector-fold");
    if (button) {
      button.textContent = open ? "−" : "+";
      button.setAttribute("aria-expanded", String(open));
    }
    if (open && !node.dataset.loaded) {
      node.dataset.loaded = "1";
      const value = tree.nodes.get(node.dataset.treeToken);
      const depth = Number(node.dataset.depth || 0) + 1;
      const children = node.querySelector(":scope > .data-inspector-children");
      if (value && children) children.innerHTML = childrenHtml(value, depth, 0, node.dataset.treeToken);
    }
  }

  // Opens branches breadth-first from `start` until the budget is spent, so
  // "expand all" on a large document stays responsive. False when stopped.
  function expandAll(start, budget = EXPAND_ALL_BUDGET) {
    const queue = [...start];
    let opened = 0;
    while (queue.length && opened < budget) {
      const node = queue.shift();
      if (!node.open) {
        setBranchOpen(node, true);
        opened += 1;
      }
      const children = node.querySelector(":scope > .data-inspector-children");
      if (children) queue.push(...children.querySelectorAll(":scope > details.data-inspector-branch"));
    }
    return queue.length === 0;
  }

  // ------------------------------------------------------- viewer events --

  function onViewerClick(event) {
    const target = event.target;
    const summary = target.closest("summary");
    if (summary && summary.parentElement?.matches("details.data-inspector-branch[data-tree-token]")) {
      if (target.closest(".data-page-inline-action")) return;
      event.preventDefault();
      const node = summary.parentElement;
      if (event.altKey && !node.open) {
        expandAll([node]);
      } else {
        setBranchOpen(node, !node.open);
      }
      return;
    }
    const more = target.closest("[data-tree-more]");
    if (more) {
      const value = tree.nodes.get(more.dataset.treeMore);
      if (value) more.outerHTML = childrenHtml(value, Number(more.dataset.depth), Number(more.dataset.start), more.dataset.treeMore);
      return;
    }
    const findButton = target.closest("[data-find-path-id]");
    if (findButton) {
      findPathId(findButton.dataset.findPathId);
      return;
    }
    const cab = target.closest("[data-filter-cab]");
    if (cab) {
      files.field = "cab";
      files.query = cab.dataset.filterCab;
      files.pathIdHits = null;
      syncFieldSelect();
      renderHits();
      files.pager?.reset();
      fetchRows();
      return;
    }
    const copy = target.closest("[data-copy-text]");
    if (copy) {
      shell().copyToClipboard?.(copy, copy.dataset.copyText);
      return;
    }
    const full = target.closest("[data-string-full]");
    if (full) {
      const value = tree.nodes.get(full.dataset.stringFull);
      const leaf = full.closest(".data-inspector-leaf");
      if (typeof value === "string" && leaf) {
        leaf.insertAdjacentHTML("afterend", `<pre class="data-page-text data-page-inline-text">${esc(value)}</pre>`);
        full.remove();
      }
      return;
    }
    const base64 = target.closest("[data-base64]");
    if (base64) {
      const value = tree.nodes.get(base64.dataset.base64);
      const leaf = base64.closest(".data-inspector-leaf");
      if (typeof value === "string" && leaf) {
        leaf.insertAdjacentHTML("afterend", decodedBase64Html(value));
        base64.remove();
      }
      return;
    }
    if (!files.doc || files.doc.status !== "ready") return;
    if (target.closest("[data-doc-load-all]")) {
      loadDocument({ full: true });
    } else if (target.closest("[data-doc-show-text]")) {
      files.doc.showAllText = true;
      renderDocument();
    } else if (target.closest("[data-doc-more-hex]")) {
      files.doc.hexBytes = HEX_MORE_BYTES;
      renderDocument();
    } else if (target.closest("[data-doc-view]")) {
      files.doc.view = target.closest("[data-doc-view]").dataset.docView;
      renderDocument();
    } else if (target.closest("[data-doc-expand]")) {
      const host = $("#data-files-doc", page.panes.files);
      if (host && !expandAll(host.querySelectorAll(":scope > details.data-inspector-branch"))) {
        host.insertAdjacentHTML("afterbegin", `<p class="data-inspector-description">${esc(ui(
          `Opened the first ${formatNumber(EXPAND_ALL_BUDGET)} branches; open deeper ones individually.`,
          `已展开前 ${formatNumber(EXPAND_ALL_BUDGET)} 个分支；更深的分支请逐个展开。`,
        ))}</p>`);
      }
    } else if (target.closest("[data-doc-collapse]")) {
      renderDocument();
    }
  }

  function decodedBase64Html(value, { auto = false } = {}) {
    let bytes;
    try {
      const compact = value.replace(/\s+/g, "");
      const padded = compact + "=".repeat((4 - (compact.length % 4)) % 4);
      const binary = atob(padded);
      bytes = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    } catch (error) {
      // A string that only looked like base64 is left as it is when decoding was automatic.
      if (auto) return "";
      return `<div class="data-inspector-empty is-error">${esc(ui("Not valid base64", "不是有效的 base64"))}: ${esc(error.message)}</div>`;
    }
    let text = null;
    try {
      text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    } catch (_error) {
      text = null;
    }
    const label = `<div class="data-page-decoded-label">${esc(ui("Decoded base64", "base64 解码结果"))} · ${esc(formatBytes(bytes.length))}</div>`;
    if (text !== null && !looksBinary(text)) {
      const shown = text.slice(0, TEXT_PREVIEW_CHARS);
      return `<div class="data-page-decoded">${label}<pre class="data-page-text data-page-inline-text">${esc(shown)}${
        shown.length < text.length ? esc(`\n… (${formatNumber(text.length - shown.length)} ${ui("more characters", "个字符未显示")})`) : ""}</pre></div>`;
    }
    const hex = `<pre class="data-page-hex">${esc(hexDump(bytes.subarray(0, HEX_PREVIEW_BYTES)))}</pre>`;
    if (auto) {
      return `<details class="data-page-decoded is-binary"><summary class="data-page-decoded-label">${esc(ui(
        "Decoded base64 (binary)", "base64 解码结果（二进制）",
      ))} · ${esc(formatBytes(bytes.length))}</summary>${hex}</details>`;
    }
    return `<div class="data-page-decoded">${label}${hex}</div>`;
  }

  // Where does this PathID occur? One indexed query over the Unity store,
  // then the ordinary pathId filter inside the chosen group.
  async function findPathId(value) {
    const text = String(value || "").trim();
    if (!/^-?\d+$/.test(text) || !unityStoreIn(files.root)) return;
    if (page.mode !== "files") setMode("files");
    let types = [];
    let error = "";
    try {
      const result = await storeApi("sql", {
        root: files.root,
        store: "unity",
        q: `SELECT type, COUNT(*) AS rows FROM objects WHERE path_id = ${text} GROUP BY type ORDER BY rows DESC, type`,
      });
      types = (result.rows || []).map(([type, rows]) => ({ type, rows }));
    } catch (failure) {
      error = failure.message;
    }
    files.pathIdHits = { pathId: text, types, error };
    files.field = "pathId";
    files.query = text;
    files.autoSelect = "";
    files.autoSelectSingle = true;
    const preferred = types.find((item) => files.store === "unity" && item.type === files.group) || types[0];
    if (preferred && (files.store !== "unity" || files.group !== preferred.type)) {
      files.store = "unity";
      files.group = preferred.type;
      renderGroups();
    }
    syncFieldSelect();
    renderHits();
    files.pager?.reset();
    fetchRows();
  }

  // ================================================================ SQL ====

  function sqlExamples() {
    return [
      {
        store: "",
        title: ui("Rows per group", "每个分组的行数"),
        sql: "SELECT type, COUNT(*) AS rows FROM objects GROUP BY type ORDER BY rows DESC",
      },
      {
        store: "unity",
        title: ui("TextAsset names with their m_Name", "TextAsset 名称及其 m_Name"),
        sql: "SELECT type, name, doc(data, '$.m_Name') AS m_Name, size\nFROM objects\nWHERE type = 'TextAsset'\nLIMIT 100",
      },
      {
        store: "unity",
        title: ui("MonoBehaviours whose document mentions a string", "文档中包含某字符串的 MonoBehaviour"),
        sql: "SELECT type, name, object_name, size\nFROM objects\nWHERE type = 'MonoBehaviour'\n  AND inflate(data) LIKE '%chr_0003%'\nLIMIT 50",
      },
      {
        store: "unity",
        title: ui("Largest documents of one type", "某类型中最大的文档"),
        sql: "SELECT type, name, size\nFROM objects\nWHERE type = 'TextAsset'\nORDER BY size DESC\nLIMIT 50",
      },
      {
        store: "unity",
        title: ui("Objects by object name, with PathID and CAB", "按对象名称查找，含 PathID 与 CAB"),
        sql: "SELECT type, name, object_name, path_id, source_file\nFROM objects\nWHERE type = 'MonoBehaviour' AND object_name LIKE 'data_chr%'\nLIMIT 100",
      },
      {
        store: "game-files",
        title: ui("Packed files under one sub-folder", "某子目录下的打包文件"),
        sql: "SELECT type, name, size\nFROM objects\nWHERE name LIKE 'English/%'\nLIMIT 100",
      },
    ];
  }

  function ensureSqlPane() {
    if (page.rendered.sql) return;
    renderSqlPane();
  }

  function sqlStores() {
    return storesFor(sql.root);
  }

  function renderSqlPane() {
    const pane = page.panes.sql;
    if (!pane) return;
    page.rendered.sql = true;
    if (!apiAvailable()) {
      pane.innerHTML = messagePaneHtml("sql", unavailableHtml(), { error: !!page.roots.current && !page.roots.current.unavailable });
      return;
    }
    if (sql.root === "previous" && !hasPreviousStores()) sql.root = "current";
    if (sql.root === "current" && !storesFor("current").length && hasPreviousStores()) sql.root = "previous";
    if (!sql.text) sql.text = String(WebUI.storageGet?.(SQL_DRAFT_KEY) || "") || sqlExamples()[0].sql;
    const stores = sqlStores();
    if (!stores.some((entry) => entry.id === sql.store)) sql.store = stores[0]?.id || "unity";
    pane.innerHTML = `
      <div class="data-inspector-shell data-page-shell">
        <aside id="data-sql-left" class="data-page-left data-sql-left">
          ${modeSwitchHtml("sql")}
          <header>
            <h1>${esc(ui("SQL query", "SQL 查询"))}</h1>
            <div class="data-page-stats">${esc(ui(
              "One read-only statement · first 500 rows · stopped after 15 s",
              "一条只读语句 · 最多 500 行 · 15 秒后停止",
            ))}</div>
          </header>
          <div class="filters data-sql-panel">
            <section class="filter-section filter-section-basic" data-filter-section="data-sql-query" data-fixed-open="1">
              <div class="filter-section-title"><span data-filter-section-label>${esc(ui("Query", "查询"))}</span></div>
              <div class="filter-section-body filter-section-body-stack">
                <div id="data-sql-root-row" class="filter-control-row" hidden>
                  <label for="data-sql-root">${esc(ui("Export", "导出"))}</label>
                  <select id="data-sql-root"></select>
                </div>
                <div class="filter-control-row">
                  <label for="data-sql-store">${esc(ui("Store", "存储"))}</label>
                  <select id="data-sql-store">${stores.map((entry) => `<option value="${esc(entry.id)}">${esc(storeLabel(entry.id))} · ${esc(entry.file || "")}</option>`).join("")}</select>
                </div>
                <textarea id="data-sql-q" class="data-sql-input" rows="9" spellcheck="false" autocomplete="off"
                  aria-label="${esc(ui("SQL statement", "SQL 语句"))}">${esc(sql.text)}</textarea>
                <div class="data-sql-run-row">
                  <button id="data-sql-run" class="data-page-primary" type="button">${esc(ui("Run", "运行"))}</button>
                  <span class="data-page-hint">Ctrl+Enter</span>
                </div>
              </div>
            </section>
            <section class="filter-section" data-filter-section="data-sql-examples">
              <button class="filter-section-toggle" type="button" aria-expanded="true" aria-controls="data-sql-examples-body">
                <span data-filter-section-label>${esc(ui("Examples", "示例"))}</span>
              </button>
              <div id="data-sql-examples-body" class="filter-section-body">
                <div id="data-sql-examples" class="data-sql-examples"></div>
              </div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="data-sql-schema">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="data-sql-schema-body">
                <span data-filter-section-label>${esc(ui("Table and functions", "表与函数"))}</span>
              </button>
              <div id="data-sql-schema-body" class="filter-section-body" hidden>
                <pre class="data-sql-schema">objects(type, name, object_name, path_id,
        source_file, script_path_id, size,
        mtime_ns, sha256, data)

inflate(data)          ${esc(ui("-> document text", "-> 文档文本"))}
doc(data, '$.a.b')     ${esc(ui("-> one JSON value", "-> 单个 JSON 值"))}</pre>
                <p class="data-page-hint">${esc(ui(
                  "In the Unity store `type` is the Unity type and `name` the document name. In the packed game-file store `type` is the packed folder (e.g. Json/LipSync) and `name` the path inside it. A result with `type` and `name` columns links each row to Files mode. Filter on `type` first: inflating every row of a large store takes longer than the time limit.",
                  "在 Unity 存储中，`type` 为 Unity 类型，`name` 为文档名称；在打包游戏文件存储中，`type` 为打包目录（如 Json/LipSync），`name` 为其中的路径。含 `type` 与 `name` 列的结果会链接到文件模式。请先按 `type` 过滤：对大型存储的所有行执行 inflate 会超出时间限制。",
                ))}</p>
              </div>
            </section>
          </div>
        </aside>
        <div id="data-sql-splitter" class="pane-splitter" role="separator" aria-label="${esc(ui("Resize sidebar", "调整侧栏宽度"))}" aria-orientation="vertical" tabindex="0"></div>
        <main id="data-sql-right" class="data-page-right"><div id="data-sql-result" class="data-sql-result"></div></main>
      </div>`;
    const storeSelect = $("#data-sql-store", pane);
    if (storeSelect) storeSelect.value = sql.store;
    syncRootSelects();
    renderSqlExamples();
    renderSqlResult();
    shell().bindFilterSections?.(pane);
    shell().setupListShellSplitters?.({
      shell: $(".data-page-shell", pane),
      sidebar: $("#data-sql-left", pane),
      pane: $("#data-sql-splitter", pane),
      paneStorageKey: PANE_STORAGE_KEY,
    });
    const input = $("#data-sql-q", pane);
    input?.addEventListener("input", () => {
      sql.text = input.value;
      WebUI.storageSet?.(SQL_DRAFT_KEY, sql.text);
    });
    input?.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        runSql();
      }
    });
    $("#data-sql-run", pane)?.addEventListener("click", runSql);
    storeSelect?.addEventListener("change", (event) => {
      sql.store = event.target.value;
      renderSqlExamples();
    });
    $("#data-sql-root", pane)?.addEventListener("change", (event) => {
      sql.root = event.target.value === "previous" ? "previous" : "current";
      renderSqlPane();
    });
    $("#data-sql-examples", pane)?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-sql-example]");
      if (!button) return;
      const example = sqlExamples()[Number(button.dataset.sqlExample)];
      if (!example) return;
      sql.text = example.sql;
      WebUI.storageSet?.(SQL_DRAFT_KEY, sql.text);
      if (input) {
        input.value = sql.text;
        input.focus();
      }
    });
    $("#data-sql-right", pane)?.addEventListener("click", (event) => {
      const find = event.target.closest("[data-find-path-id]");
      if (find) {
        files.root = sql.root;
        ensureFilesPane();
        findPathId(find.dataset.findPathId);
      }
    });
  }

  function renderSqlExamples() {
    const host = $("#data-sql-examples", page.panes.sql);
    if (!host) return;
    host.innerHTML = sqlExamples()
      .map((example, index) => ({ example, index }))
      .filter(({ example }) => !example.store || example.store === sql.store)
      .map(({ example, index }) => `<button type="button" data-sql-example="${index}">
        <strong>${esc(example.title)}</strong><code>${esc(example.sql)}</code></button>`)
      .join("");
  }

  async function runSql() {
    const statement = sql.text.trim();
    if (!statement || sql.running) return;
    const token = ++sql.token;
    sql.running = true;
    sql.error = "";
    renderSqlResult();
    try {
      const result = await storeApi("sql", { root: sql.root, store: sql.store, q: statement });
      if (token !== sql.token) return;
      sql.result = { ...result, root: sql.root, store: sql.store };
    } catch (error) {
      if (token !== sql.token) return;
      sql.result = null;
      sql.error = error.message;
    }
    sql.running = false;
    renderSqlResult();
  }

  function sqlCellHtml(value, column, row, links) {
    if (value === null || value === undefined) return '<span class="json-null">NULL</span>';
    if (typeof value === "number") return `<span class="json-number">${esc(String(value))}</span>`;
    const text = String(value);
    if (links.name === column && links.type >= 0 && typeof row[links.type] === "string") {
      const href = WebUI.dataPageUrl?.({ root: links.root, store: links.store, group: row[links.type], name: text });
      if (href) return `<a href="${esc(href)}" data-data-page-link="1" title="${esc(ui("Open in Files mode", "在文件模式中打开"))}">${esc(text)}</a>`;
    }
    return `<div class="data-sql-cell">${esc(text)}</div>`;
  }

  function renderSqlResult() {
    const host = $("#data-sql-result", page.panes.sql);
    if (!host) return;
    if (sql.running) {
      host.innerHTML = `<div class="data-inspector-empty">${esc(ui("Running…", "正在运行…"))}</div>`;
      return;
    }
    if (sql.error) {
      host.innerHTML = `<div class="data-sql-error"><strong>${esc(ui("Query failed", "查询失败"))}</strong><pre>${esc(sql.error)}</pre></div>`;
      return;
    }
    const result = sql.result;
    if (!result) {
      host.innerHTML = `<div class="data-inspector-empty">${esc(ui(
        "Run a query to see its rows. Pick an example on the left to start.",
        "运行查询以查看结果。可从左侧示例开始。",
      ))}</div>`;
      return;
    }
    const columns = result.columns || [];
    const rows = result.rows || [];
    const links = {
      type: columns.indexOf("type"),
      name: columns.includes("name") && columns.includes("type") ? "name" : "",
      root: result.root,
      store: result.store,
    };
    const pathIdColumns = new Set(result.store === "unity"
      ? columns.map((column, index) => (PATH_ID_KEY.test(column) ? index : -1)).filter((index) => index >= 0)
      : []);
    const unityInRoot = unityStoreIn(result.root);
    const body = rows.map((row, rowIndex) => `<tr><td class="data-sql-index">${rowIndex + 1}</td>${row.map((value, index) => {
      const cell = sqlCellHtml(value, columns[index], row, links);
      const find = pathIdColumns.has(index) && unityInRoot && /^-?\d+$/.test(String(value ?? "")) && String(value) !== "0"
        ? `<button type="button" class="data-page-inline-action" data-find-path-id="${esc(value)}">${esc(ui("find", "查找"))}</button>`
        : "";
      return `<td class="${typeof value === "number" ? "is-number" : ""}">${cell}${find}</td>`;
    }).join("")}</tr>`).join("");
    host.innerHTML = `
      <div class="data-sql-meta">
        <span>${esc(formatNumber(rows.length))} ${esc(ui("rows", "行"))}</span>
        <span>${esc(formatNumber(result.elapsedMs))} ms</span>
        <span>${esc(storeLabel(result.store))}${result.root !== "current" ? ` · ${esc(ui("previous export", "上一版导出"))}` : ""}</span>
        ${result.truncated ? `<span class="data-inspector-chip is-warn">${esc(ui(
          `Stopped at ${formatNumber(result.limit)} rows; narrow the query or add LIMIT/OFFSET.`,
          `已在 ${formatNumber(result.limit)} 行处截断；请缩小查询或使用 LIMIT/OFFSET。`,
        ))}</span>` : ""}
      </div>
      ${columns.length ? `<div class="data-sql-table-wrap"><table class="data-sql-table">
        <thead><tr><th>#</th>${columns.map((column) => `<th>${esc(column)}</th>`).join("")}</tr></thead>
        <tbody>${body}</tbody>
      </table></div>` : `<div class="data-inspector-empty">${esc(ui("The statement returned no columns.", "该语句未返回任何列。"))}</div>`}`;
  }

  // ------------------------------------------------------------- wiring ---

  function relocalize() {
    if (!page.mounted) return;
    if (page.rendered.files) renderFilesPane({ fetch: false });
    if (page.rendered.sql) renderSqlPane();
    WebUI.decodedInspector?.relocalize();
  }

  WebUI.dataPage = {
    modeSwitchHtml,
    activeMode: () => page.mode,
    open: openDataPageUrl,
  };

  window.addEventListener("webui:view-changed", (event) => onViewChanged(event.detail?.view));
  window.addEventListener("webui:ui-locale-changed", relocalize);
  window.addEventListener("popstate", () => {
    if (!page.mounted || !pageIsActive()) return;
    const link = readLinkParams();
    if (linkKey(link) !== page.lastAppliedLink) applyLink(link);
  });

  function init() {
    if (pageIsActive()) mount();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
