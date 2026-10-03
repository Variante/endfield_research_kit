// Data page controller: the mode switch (Files | SQL), deep links, view
// events, and both modes.
//
// Files lists rows from every data source in one list shell:
//   * the export's SQLite stores (game/Unity.sqlite, game/GameFiles.sqlite),
//     read through the local server's read-only /api/stores API
//     (scripts/webui/data_inspector/store_browser.py); a row's bytes are
//     fetched from its own /export_* URL, exactly like any exported file;
//   * the loose decoded files under game/ that no other page shows (tables,
//     JsonData, Lua, Terrain, converted Shader/Font/TextAsset), listed by the
//     same API as the `loose` source; it has no SQL;
//   * the undecoded final VFS files under raw/ (Streaming, DynamicStreaming,
//     IV, ExtendData, IFixPatch, the bundle manifest), the `undecoded` source,
//     whose rows are always shown as a hex dump;
//   * the generated decoded datasets (webui/data/data_inspector), whose
//     catalog, matching and record viewer live in index.js
//     (WebUI.decodedInspector).
// Sources and their groups (Unity types, packed folders, datasets) are
// WebUI.facets chips. A source is listed when its source chip or any of its
// group chips is on, or when nothing is selected at all; within a listed
// source, selected groups narrow it and no selected group means all of them.
// The list is the listed sources in order (Unity, packed, loose, undecoded, decoded),
// paged as one sequence. Decode status, source folder and tag filters apply to
// decoded records and are shown only while decoded datasets are selected.
//
// SQL runs one read-only statement over a store. A static package has no
// store API: Files then lists only the decoded datasets, and SQL explains that
// it needs `python serve.py`.
//
// The store viewer is generic. It knows the store vocabulary the API
// publishes (store, group, row name, object name, PathID, CAB) and nothing
// about any Unity type's schema: a JSON document is rendered as its own tree,
// text as text, and anything that is not UTF-8 text as a hex dump.
(() => {
  const API_PREFIX = "/api/stores";
  const MODES = ["files", "sql"];
  const STORE_SOURCES = ["unity", "game-files", "loose", "undecoded"];
  // File sources list files on disk rather than rows of a SQLite store.
  const FILE_SOURCES = ["loose", "undecoded"];
  const SOURCES = [...STORE_SOURCES, "decoded"];
  const DECODED_FILTER_GROUPS = ["status", "folder", "tag"];
  const MAX_API_ROWS = 1000;
  const STORE_ROW_HEIGHT = 50;
  const DECODED_ROW_HEIGHT = 72;
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
  const FILES_SELECTION_KEY = "data_files_selection";
  const FILES_PAGE_SIZE_KEY = "data_files_page_size";
  const SQL_DRAFT_KEY = "data_sql_draft";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const PATH_ID_KEY = /path_?id$/i;
  const BASE64_TEXT = /^[A-Za-z0-9+/]+={0,2}$/;
  const FIELDS = ["name", "object", "pathId", "cab"];
  const SORTS = ["path", "title", "dataset", "status"];

  const WebUI = window.WebUI;
  const { $ } = WebUI;
  const esc = WebUI.escapeHtml;
  const formatNumber = WebUI.formatNumber;
  const zh = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh")
    .toLowerCase().startsWith("zh");
  const ui = (en, cn) => (zh() ? cn : en);
  const isMobileLayout = () => !!(window.matchMedia && window.matchMedia(MOBILE_LAYOUT_QUERY).matches);
  const shell = () => WebUI.dataInspectorShell || {};
  const decodedApi = () => WebUI.decodedInspector || null;
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
  // An array parameter value is sent as a repeated parameter.
  async function storeApi(endpoint, params = {}) {
    let response;
    try {
      const url = new URL(`${API_PREFIX}${endpoint ? `/${endpoint}` : ""}`, window.location.href);
      for (const [key, value] of Object.entries(params)) {
        for (const item of Array.isArray(value) ? value : [value]) {
          if (item !== undefined && item !== null && item !== "") url.searchParams.append(key, String(item));
        }
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
    // The decoded datasets: status idle | loading | ready | error.
    decoded: { status: "idle", datasets: [], records: [], error: "" },
    lastAppliedLink: "",
  };

  const files = {
    root: "current",
    field: "name",
    query: "",
    catalogTerm: "",
    sort: "path",
    facets: null,
    selectionRestored: false,
    decodedMatcher: () => true,
    total: 0,
    offset: 0,
    rows: [],
    tops: [],
    height: 0,
    segments: [],
    loading: false,
    error: "",
    reqToken: 0,
    pager: null,
    filterPanel: null,
    selected: null,
    autoSelect: null,
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

  function sourceLabel(id) {
    if (id === "unity") return ui("Unity objects", "Unity 对象");
    if (id === "game-files") return ui("Packed game files", "打包的游戏文件");
    if (id === "loose") return ui("Loose export files", "独立导出文件");
    if (id === "undecoded") return ui("Undecoded files", "未解码文件");
    if (id === "decoded") return ui("Decoded datasets", "解码数据集");
    return id;
  }

  const storeLabel = sourceLabel;

  function rootPayload(root) {
    const probe = page.roots[root];
    return probe && probe.ok ? probe.payload : null;
  }

  function storesFor(root) {
    return rootPayload(root)?.stores || [];
  }

  function storeEntry(root, store) {
    return storesFor(root).find((entry) => entry.id === store) || null;
  }

  function hasPreviousStores() {
    return storesFor("previous").length > 0;
  }

  function apiAvailable() {
    return !!page.roots.current?.ok;
  }

  function unityStoreIn(root) {
    return !!storeEntry(root, "unity");
  }

  function decodedReady() {
    return page.decoded.status === "ready";
  }

  // Sources the Files list can show for the selected export root.
  function availableSources() {
    const out = STORE_SOURCES.filter((id) => storeEntry(files.root, id));
    if (page.decoded.status !== "error") out.push("decoded");
    return out;
  }

  function sourceRowCount(id) {
    if (id === "decoded") return decodedReady() ? page.decoded.records.length : undefined;
    return Number(storeEntry(files.root, id)?.rows) || 0;
  }

  // Which sources the current selection lists (see the header comment).
  function includedSources() {
    const facets = files.facets;
    const available = availableSources();
    if (!facets) return available;
    const any = ["source", ...SOURCES].some((id) => facets.isFiltered(id));
    return available.filter((id) => !any || facets.has("source", id) || facets.isFiltered(id));
  }

  function decodedFiltersShown() {
    const facets = files.facets;
    return !!facets && (facets.has("source", "decoded") || facets.isFiltered("decoded"));
  }

  // -------------------------------------------------------------- mode UI --

  function modeSwitchHtml(active) {
    const labels = { files: ui("Files", "文件"), sql: "SQL" };
    const titles = {
      files: ui("Browse export-store rows, loose export files and decoded datasets", "浏览导出存储中的行、独立导出文件与解码数据集"),
      sql: ui("Run one read-only SQL statement over a store", "对存储执行一条只读 SQL 语句"),
    };
    return `<div class="data-page-modes page-mode-switch" role="tablist" aria-label="${esc(ui("Data page mode", "数据页模式"))}">${MODES
      .map((mode) => `<button type="button" role="tab" data-data-mode="${mode}" title="${esc(titles[mode])}"
        class="page-mode-button ${mode === active ? "is-active" : ""}" aria-selected="${mode === active}">${esc(labels[mode])}</button>`)
      .join("")}</div>`;
  }

  function messagePaneHtml(mode, html, { error = false } = {}) {
    return `<div class="data-page-message">${modeSwitchHtml(mode)}
      <div class="data-inspector-empty${error ? " is-error" : ""}">${html}</div></div>`;
  }

  function unavailableHtml({ files: forFiles = false } = {}) {
    const probe = page.roots.current;
    if (probe && !probe.ok && !probe.unavailable) {
      return `${esc(ui("The export stores could not be read:", "无法读取导出存储："))}<br><code>${esc(probe.error)}</code>`;
    }
    return `${esc(forFiles ? ui(
      "Export-store rows (game/Unity.sqlite, game/GameFiles.sqlite) and loose export files are read through the local server's store API, which a static package does not have; only the decoded datasets are listed. Start the WebUI from the repository with",
      "导出存储中的行（game/Unity.sqlite、game/GameFiles.sqlite）与独立导出文件通过本地服务器的存储 API 读取，静态包中没有该 API，因此仅列出解码数据集。请在仓库中运行",
    ) : ui(
      "SQL reads the export's SQLite stores (game/Unity.sqlite, game/GameFiles.sqlite) through the local server's store API, which a static package does not have. Start the WebUI from the repository with",
      "SQL 模式通过本地服务器的存储 API 读取导出的 SQLite 存储（game/Unity.sqlite、game/GameFiles.sqlite），静态包中没有该 API。请在仓库中运行",
    ))} <code>python serve.py</code>${esc(ui(
      ", or restart a server that predates the store API.",
      " 启动 WebUI；若服务器早于存储 API，请重启。",
    ))}${probe?.error ? `<br><code>${esc(probe.error)}</code>` : ""}`;
  }

  function setMode(mode, { updateUrl = true } = {}) {
    if (mode === "decoded") mode = "files";
    if (!MODES.includes(mode) || !page.app) return;
    page.mode = mode;
    for (const [name, pane] of Object.entries(page.panes)) pane.hidden = name !== mode;
    page.app.querySelector(".data-page")?.setAttribute("data-mode", mode);
    if (mode === "files") ensureFilesPane();
    else if (mode === "sql") ensureSqlPane();
    if (updateUrl) syncModeUrl();
    requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
  }

  function pageIsActive() {
    return document.body.dataset.activeView === "data-inspector";
  }

  function clearDataParams(params) {
    for (const key of WebUI.DATA_PAGE_PARAMS || []) params.delete(key);
    params.delete("inspectDataset");
    params.delete("inspect");
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
      clearDataParams(params);
      params.set("dataMode", page.mode);
    });
  }

  // Files deep link: dataStore (repeated) = source chips; dataGroup (repeated)
  // = `<source>:<group>` group chips; dataStatus/dataFolder/dataTag
  // (repeated) = decoded filters; dataQ/dataField = search; dataSort = decoded
  // order; dataName = the selected store row, or inspectDataset + inspect =
  // the selected decoded record.
  function syncFilesUrl() {
    if (!page.rendered.files && !files.facets) return;
    replaceUrl((params) => {
      clearDataParams(params);
      params.set("dataMode", "files");
      if (files.root !== "current") params.set("dataRoot", files.root);
      const facets = files.facets;
      if (facets) {
        for (const source of facets.active("source")) params.append("dataStore", source);
        for (const source of SOURCES) {
          for (const group of facets.active(source)) params.append("dataGroup", `${source}:${group}`);
        }
        facets.toParams(params);
      }
      if (files.query) {
        params.set("dataQ", files.query);
        if (files.field !== "name") params.set("dataField", files.field);
      }
      if (files.sort !== "path") params.set("dataSort", files.sort);
      const selected = files.selected;
      if (selected?.kind === "store" && selected.root === files.root) params.set("dataName", selected.row.name);
      if (selected?.kind === "decoded") {
        params.set("inspectDataset", selected.entry._datasetId);
        params.set("inspect", selected.entry.id);
      }
    });
  }

  function readLinkParams() {
    const params = new URLSearchParams(window.location.search);
    const all = (key) => params.getAll(key).filter(Boolean);
    return {
      mode: params.get("dataMode") || "",
      root: params.get("dataRoot") === "previous" ? "previous" : "current",
      stores: all("dataStore"),
      groups: all("dataGroup"),
      statuses: all("dataStatus"),
      folders: all("dataFolder"),
      tags: all("dataTag"),
      name: params.get("dataName") || "",
      query: params.get("dataQ") || "",
      field: params.get("dataField") || "",
      sort: params.get("dataSort") || "",
      inspectDataset: params.get("inspectDataset") || "",
      inspect: params.get("inspect") || "",
    };
  }

  function linkKey(link) {
    return JSON.stringify(link);
  }

  function linkHasTarget(link) {
    return !!(link.stores.length || link.groups.length || link.statuses.length || link.folders.length
      || link.tags.length || link.name || link.query || link.inspect);
  }

  // `unity:MonoBehaviour`, `game-files:Json/LipSync`, `loose:Lua`, `undecoded:Streaming` and `decoded:<dataset>`
  // name their source. An unqualified group (the older single-store form)
  // belongs to the link's store, or to whichever store has a group of that
  // name.
  function selectionFromLink(link) {
    const snapshot = { source: link.stores.filter((id) => SOURCES.includes(id)) };
    const add = (source, group) => {
      (snapshot[source] ||= []);
      if (!snapshot[source].includes(group)) snapshot[source].push(group);
    };
    for (const raw of link.groups) {
      const match = raw.match(/^(unity|game-files|loose|undecoded|decoded):(.+)$/);
      if (match) {
        add(match[1], match[2]);
        continue;
      }
      const owner = link.stores.find((id) => STORE_SOURCES.includes(id))
        || STORE_SOURCES.find((id) => storeEntry(files.root, id)?.groups.some((group) => group.name === raw))
        || "unity";
      add(owner, raw);
    }
    if (link.statuses.length) snapshot.status = link.statuses;
    if (link.folders.length) snapshot.folder = link.folders;
    if (link.tags.length) snapshot.tag = link.tags;
    if (link.inspect && !link.stores.length && !link.groups.length) {
      if (link.inspectDataset) add("decoded", link.inspectDataset);
      else snapshot.source.push("decoded");
    }
    return snapshot;
  }

  // --------------------------------------------------------------- mount --

  async function probeRoot(root) {
    try {
      return { ok: true, payload: await storeApi("", { root }) };
    } catch (error) {
      return { ok: false, error: error.message, unavailable: !!error.unavailable };
    }
  }

  function startDecodedLoad() {
    if (page.decoded.status !== "idle") return;
    const api = decodedApi();
    if (!api) {
      page.decoded = { status: "error", datasets: [], records: [], error: "decoded inspector module is not loaded" };
      return;
    }
    page.decoded.status = "loading";
    api.load().then((result) => {
      page.decoded = result.ok
        ? { status: "ready", datasets: result.datasets, records: result.records, error: "" }
        : { status: "error", datasets: [], records: [], error: result.error || "" };
      onDecodedLoaded();
    });
  }

  function onDecodedLoaded() {
    if (!page.rendered.files) return;
    if (!apiAvailable() && page.decoded.status === "error") {
      renderFilesPane();
      return;
    }
    updateMatcher();
    renderStats();
    renderSources();
    syncFieldSelect();
    if (includedSources().includes("decoded") || files.autoSelect?.kind === "decoded") fetchRows();
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
      </div>`;
    page.panes = {
      files: $("#data-page-files", app),
      sql: $("#data-page-sql", app),
    };
    app.addEventListener("click", (event) => {
      const button = event.target.closest("[data-data-mode]");
      if (!button || !app.contains(button)) return;
      event.preventDefault();
      setMode(button.dataset.dataMode);
    });
    page.panes.files.innerHTML = messagePaneHtml("files", esc(ui("Reading the export stores…", "正在读取导出存储…")));

    const link = readLinkParams();
    startDecodedLoad();
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
    applyLink(link);
  }

  // Apply a deep link: its selection, search and target row. A store row is
  // found by setting the search to its name; a decoded record by listing its
  // dataset. The exact row is selected once its page arrives.
  function applyLink(link) {
    page.lastAppliedLink = linkKey(link);
    const mode = link.mode === "sql" && apiAvailable() ? "sql" : "files";
    if (mode === "files" && linkHasTarget(link)) {
      files.root = link.root === "previous" && hasPreviousStores() ? "previous" : "current";
      ensureFacets().restore(selectionFromLink(link));
      files.selectionRestored = true;
      files.field = FIELDS.includes(link.field) ? link.field : "name";
      files.query = link.name || link.query;
      if (link.name) files.field = "name";
      files.catalogTerm = "";
      files.sort = SORTS.includes(link.sort) ? link.sort : "path";
      files.autoSelect = link.inspect
        ? { kind: "decoded", datasetId: link.inspectDataset, recordId: link.inspect }
        : link.name ? { kind: "store", name: link.name } : null;
      files.pathIdHits = null;
      files.offset = 0;
      files.rows = [];
      files.error = "";
      files.pager?.reset();
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
    if (linkKey(link) !== page.lastAppliedLink && (linkHasTarget(link) || link.mode)) applyLink(link);
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

  function ensureFacets() {
    if (files.facets) return files.facets;
    const storeGroup = (id) => ({
      id,
      container: `[data-source-chips="${id}"]`,
      section: "data-files-sources",
      items: () => (storeEntry(files.root, id)?.groups || []).map((group) => ({ value: group.name, count: group.count })),
      order: "none",
      className: "kind-chip is-path-chip",
    });
    files.facets = WebUI.facets.create({
      groups: [
        {
          id: "source",
          container: "#data-files-source-chips",
          section: "data-files-sources",
          items: () => availableSources().map((id) => ({ value: id, count: sourceRowCount(id) })),
          label: sourceLabel,
          order: "none",
          className: "kind-chip",
        },
        storeGroup("unity"),
        storeGroup("game-files"),
        storeGroup("loose"),
        storeGroup("undecoded"),
        {
          id: "decoded",
          container: '[data-source-chips="decoded"]',
          section: "data-files-sources",
          values: (entry) => entry._datasetId,
          items: () => page.decoded.datasets.map((dataset) => ({
            value: dataset.id, label: dataset.title, title: dataset.description,
          })),
          order: "none",
          className: (id) => `kind-chip ${decodedApi()?.toneClass(id) || ""}`,
        },
        {
          id: "status",
          container: "#data-files-status-filter",
          section: "data-files-status",
          param: "dataStatus",
          values: (entry) => entry.status,
          label: (value) => decodedApi()?.statusLabel(value) || value,
          title: (value) => value,
          className: (value) => `kind-chip is-status-${decodedApi()?.statusClass(value) || "unknown"}`,
        },
        {
          id: "folder",
          container: "#data-files-folder-filter",
          section: "data-files-folder",
          param: "dataFolder",
          values: (entry) => entry._folder,
          className: "kind-chip is-path-chip",
        },
        {
          id: "tag",
          container: "#data-files-tag-filter",
          section: "data-files-tag",
          param: "dataTag",
          values: (entry) => entry.tags || [],
        },
      ],
      predicate: (entry) => files.decodedMatcher(entry),
      onChange: onFacetChange,
    });
    return files.facets;
  }

  function renderFacets() {
    ensureFacets().render(page.decoded.records);
  }

  function updateMatcher() {
    const api = decodedApi();
    // PathID, CAB and object-name searches are Unity-only: they match no
    // decoded record.
    if (files.query && files.field !== "name") files.decodedMatcher = () => false;
    else files.decodedMatcher = api ? api.queryMatcher(files.query, files.catalogTerm) : () => true;
  }

  function persistSelection() {
    if (!files.facets) return;
    WebUI.storageSet?.(FILES_SELECTION_KEY, JSON.stringify(files.facets.snapshot()));
  }

  function restoreSelection() {
    if (files.selectionRestored) return;
    files.selectionRestored = true;
    let saved = null;
    try {
      saved = JSON.parse(String(WebUI.storageGet?.(FILES_SELECTION_KEY) || "null"));
    } catch (_error) {
      saved = null;
    }
    if (saved && typeof saved === "object") ensureFacets().restore(saved);
  }

  // Store groups the new export root does not have are dropped on a root
  // switch, so a hidden group cannot empty the list.
  function pruneStoreGroups() {
    const facets = ensureFacets();
    for (const id of STORE_SOURCES) {
      const names = new Set((storeEntry(files.root, id)?.groups || []).map((group) => group.name));
      const kept = [...facets.active(id)].filter((name) => names.has(name));
      if (kept.length !== facets.activeCount(id)) facets.set(id, kept, { silent: true });
    }
  }

  function onFacetChange() {
    if (!decodedFiltersShown() && DECODED_FILTER_GROUPS.some((id) => files.facets.isFiltered(id))) {
      files.facets.reset({ silent: true, only: DECODED_FILTER_GROUPS });
    }
    syncDecodedFilterSections();
    persistSelection();
    files.autoSelect = null;
    syncFieldSelect();
    renderHits();
    files.pager?.reset();
    fetchRows();
  }

  function ensureFilesPane() {
    if (page.rendered.files) return;
    renderFilesPane();
  }

  function fieldOptions() {
    const options = [["name", ui("Row name", "行名称")]];
    if (unityStoreIn(files.root) && includedSources().includes("unity")) {
      options.push(["object", ui("Object name", "对象名称")], ["pathId", "PathID"], ["cab", "CAB"]);
    }
    return options;
  }

  function fieldHint(field) {
    return {
      name: ui(
        "Store rows: case-insensitive name substring; * and ? make it a glob. Decoded records: name, path, status and tags.",
        "存储行：不区分大小写的名称子串，含 * 或 ? 时按通配符匹配。解码记录：名称、路径、状态与标签。",
      ),
      object: ui("Object-name substring (Unity rows only).", "对象名称子串（仅 Unity 行）。"),
      pathId: ui("A PathID in decimal or as 16 hex digits (Unity rows only).", "十进制或 16 位十六进制 PathID（仅 Unity 行）。"),
      cab: ui("The exact source CAB, e.g. CAB-0123… (Unity rows only).", "完整的来源 CAB，例如 CAB-0123…（仅 Unity 行）。"),
    }[field] || "";
  }

  function filterSectionHtml(key, label, body, { collapsed = true } = {}) {
    return `<section class="filter-section${collapsed ? " is-collapsed" : ""}" data-filter-section="${key}"${collapsed ? ' data-default-collapsed="1"' : ""}>
      <button class="filter-section-toggle" type="button" aria-expanded="${!collapsed}" aria-controls="${key}-body">
        <span data-filter-section-label>${esc(label)}</span>
      </button>
      <div id="${key}-body" class="filter-section-body"${collapsed ? " hidden" : ""}>${body}</div>
    </section>`;
  }

  // `fetch: false` re-renders from the rows already read (a locale change).
  function renderFilesPane({ fetch = true } = {}) {
    const pane = page.panes.files;
    if (!pane) return;
    page.rendered.files = true;
    if (!apiAvailable() && page.decoded.status === "error") {
      pane.innerHTML = messagePaneHtml("files", `${unavailableHtml({ files: true })}<br><br>${esc(ui(
        "The decoded datasets could not be loaded either; run the data-inspector builder.",
        "解码数据集也无法加载，请运行数据检查器构建器。",
      ))}${page.decoded.error ? `<br><code>${esc(page.decoded.error)}</code>` : ""}`, { error: true });
      return;
    }
    if (files.root === "previous" && !hasPreviousStores()) files.root = "current";
    if (files.root === "current" && !storesFor("current").length && hasPreviousStores()) files.root = "previous";
    ensureFacets();
    restoreSelection();
    updateMatcher();
    pane.innerHTML = `
      <div class="data-inspector-shell data-page-shell">
        <aside id="data-files-left" class="data-page-left">
          <header>
            <h1>${esc(ui("Data", "数据"))}</h1>
            ${modeSwitchHtml("files")}
            <div id="data-files-stats" class="data-page-stats"></div>
            <div class="sidebar-header-actions">
              <button id="data-files-filter-toggle" class="panel-toggle" type="button" aria-controls="data-files-filter-panel" aria-expanded="true"></button>
              <button id="data-files-reset" class="data-page-reset" type="button">${esc(ui("Reset filters", "重置筛选"))}</button>
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
                  placeholder="${esc(ui("Search the selected sources", "在所选来源中搜索"))}">
                <div class="filter-control-row">
                  <label for="data-files-field">${esc(ui("Match", "匹配"))}</label>
                  <select id="data-files-field"></select>
                </div>
                <p id="data-files-hint" class="data-page-hint"></p>
              </div>
            </section>
            <section class="filter-section" data-filter-section="data-files-sources">
              <button class="filter-section-toggle" type="button" aria-expanded="true" aria-controls="data-files-sources-body">
                <span data-filter-section-label>${esc(ui("Sources and groups", "来源与分组"))}</span>
              </button>
              <div id="data-files-sources-body" class="filter-section-body">
                <div id="data-files-groups" class="data-files-groups"></div>
              </div>
            </section>
            <div id="data-files-decoded-filters" class="data-files-decoded-filters" hidden>
              ${filterSectionHtml("data-files-decoded-sort", ui("Decoded record order", "解码记录排序"), `
                <div class="filter-control-row">
                  <label for="data-files-sort">${esc(ui("Sort", "排序"))}</label>
                  <select id="data-files-sort"></select>
                </div>`, { collapsed: false })}
              ${filterSectionHtml("data-files-status", ui("Decode status", "解码状态"), '<div id="data-files-status-filter" class="chips" data-multi="1"></div>')}
              ${filterSectionHtml("data-files-folder", ui("Source folder", "源文件目录"), '<div id="data-files-folder-filter" class="chips" data-multi="1"></div>')}
              ${filterSectionHtml("data-files-tag", ui("Tags", "标签"), '<div id="data-files-tag-filter" class="chips" data-multi="1"></div>')}
            </div>
          </div>
          <div id="data-files-filter-splitter" class="filter-splitter" role="separator" aria-label="${esc(ui("Resize filters", "调整筛选区高度"))}" aria-orientation="horizontal" tabindex="0"></div>
          <div id="data-files-hits" class="data-files-hits" hidden></div>
          <div id="data-files-list-meta" class="data-page-list-meta"></div>
          <div id="data-files-list-wrap" class="data-page-list-wrap">
            <div id="data-files-list-spacer"></div>
            <div id="data-files-list" class="data-page-list" role="listbox" aria-label="${esc(ui("Rows", "行"))}" tabindex="-1"></div>
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
      onChange: () => fetchRows(),
    }) || null;
    syncRootSelects();
    syncSortSelect();
    renderStats();
    renderSources();
    syncFieldSelect();
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

  function resetSearchState() {
    files.pathIdHits = null;
    files.autoSelect = null;
    updateMatcher();
    renderFacets();
    renderHits();
    files.pager?.reset();
  }

  function bindFilesEvents(pane) {
    $("#data-files-q", pane)?.addEventListener("input", (event) => {
      clearTimeout(files.qTimer);
      const value = event.target.value;
      files.qTimer = setTimeout(() => {
        files.query = value.trim();
        files.catalogTerm = "";
        resetSearchState();
        syncFieldSelect();
        fetchRows();
      }, SEARCH_DEBOUNCE_MS);
    });
    $("#data-files-field", pane)?.addEventListener("change", (event) => {
      files.field = event.target.value;
      syncFieldSelect();
      resetSearchState();
      if (files.query) fetchRows();
      else syncFilesUrl();
    });
    $("#data-files-sort", pane)?.addEventListener("change", (event) => {
      files.sort = SORTS.includes(event.target.value) ? event.target.value : "path";
      files.pager?.reset();
      fetchRows();
    });
    $("#data-files-root", pane)?.addEventListener("change", (event) => {
      files.root = event.target.value === "previous" ? "previous" : "current";
      pruneStoreGroups();
      persistSelection();
      renderStats();
      renderSources();
      syncFieldSelect();
      resetSearchState();
      fetchRows();
    });
    $("#data-files-reset", pane)?.addEventListener("click", () => {
      clearTimeout(files.qTimer);
      files.query = "";
      files.catalogTerm = "";
      files.field = "name";
      files.sort = "path";
      const input = $("#data-files-q", pane);
      if (input) input.value = "";
      ensureFacets().reset({ silent: true });
      persistSelection();
      syncSortSelect();
      syncDecodedFilterSections();
      syncFieldSelect();
      resetSearchState();
      fetchRows();
    });
    $("#data-files-list-wrap", pane)?.addEventListener("scroll", scheduleListRender, { passive: true });
    $("#data-files-list", pane)?.addEventListener("click", (event) => {
      const button = event.target.closest(".data-inspector-row[data-row-index]");
      if (!button) return;
      const item = files.rows[Number(button.dataset.rowIndex)];
      if (item) selectItem(item);
    });
    $("#data-files-list", pane)?.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      const index = files.rows.findIndex((item) => rowKey(item) === selectedKey());
      const next = index + (event.key === "ArrowDown" ? 1 : -1);
      if (next < 0 || next >= files.rows.length) return;
      event.preventDefault();
      selectItem(files.rows[next]);
      scrollRowIntoView(next);
      requestAnimationFrame(() => $(`.data-inspector-row[data-row-index="${next}"]`, pane)?.focus());
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

  function syncSortSelect() {
    const select = $("#data-files-sort", page.panes.files);
    if (!select) return;
    select.innerHTML = (decodedApi()?.sortOptions() || [])
      .map(([value, label]) => `<option value="${value}">${esc(label)}</option>`).join("");
    select.value = files.sort;
  }

  function syncFieldSelect() {
    const select = $("#data-files-field", page.panes.files);
    if (!select) return;
    const options = fieldOptions();
    if (!options.some(([value]) => value === files.field)) {
      files.field = "name";
      updateMatcher();
    }
    select.innerHTML = options.map(([value, label]) => `<option value="${value}">${esc(label)}</option>`).join("");
    select.value = files.field;
    select.disabled = options.length < 2;
    const hint = $("#data-files-hint", page.panes.files);
    if (hint) hint.textContent = fieldHint(files.field);
    const input = $("#data-files-q", page.panes.files);
    if (input && input.value !== files.query) input.value = files.query;
    WebUI.setFilterSectionActiveCounts?.({ "data-files-basic": files.query ? 1 : 0 });
  }

  function syncDecodedFilterSections() {
    const host = $("#data-files-decoded-filters", page.panes.files);
    if (!host) return;
    const shown = decodedFiltersShown() && decodedReady();
    if (host.hidden === !shown) return;
    host.hidden = !shown;
    window.dispatchEvent(new Event("resize"));
  }

  function renderStats() {
    const host = $("#data-files-stats", page.panes.files);
    if (!host) return;
    const sources = availableSources();
    const rows = sources.reduce((sum, id) => sum + (sourceRowCount(id) || 0), 0);
    host.textContent = `${formatNumber(rows)} ${ui("rows", "行")} · ${formatNumber(sources.length)} ${ui("sources", "个来源")}`
      + (rootPayload(files.root)?.root ? ` · ${rootPayload(files.root).root}` : "");
  }

  function sourceBlockHtml(id) {
    let meta = "";
    let extra = "";
    if (id === "decoded") {
      const state = page.decoded;
      meta = state.status === "ready"
        ? `<code>webui/data/data_inspector</code> · ${esc(formatNumber(state.datasets.length))} ${esc(ui("datasets", "个数据集"))} · ${esc(formatNumber(state.records.length))} ${esc(ui("records", "条记录"))}`
        : esc(ui("Loading…", "正在加载…"));
      if (state.status === "ready" && !state.datasets.length) {
        extra = `<p class="data-page-hint">${esc(ui("No decoded datasets are published. Run the data-inspector builder.", "尚未发布解码数据集，请运行数据检查器构建器。"))}</p>`;
      }
    } else {
      const entry = storeEntry(files.root, id);
      const lost = Array.isArray(entry.unreadableAtPack) ? entry.unreadableAtPack : [];
      const lostTitle = lost.slice(0, 20).map((item) => (item && typeof item === "object"
        ? `${[item.type, item.name].filter(Boolean).join("/") || item.path || ""}${item.error ? `: ${item.error}` : ""}`
        : String(item))).join("\n");
      const unit = FILE_SOURCES.includes(id) ? ui("files", "个文件") : ui("rows", "行");
      meta = `<code>${esc(entry.file || entry.id)}</code> · ${esc(formatBytes(entry.bytes))} · ${esc(formatNumber(entry.rows))} ${esc(unit)}`;
      if (lost.length) {
        extra = `<span class="data-inspector-chip is-warn" title="${esc(lostTitle)}">${esc(formatNumber(lost.length))} ${esc(ui("unreadable at pack, not stored", "打包时不可读，未存入"))}</span>`;
      }
    }
    return `<div class="data-files-store" data-source="${esc(id)}">
      <div class="data-files-store-head">
        <span class="data-files-store-name">${esc(sourceLabel(id))}</span>
        <span class="data-files-store-meta">${meta}</span>
        ${extra}
      </div>
      <div class="chips data-files-group-chips" data-source-chips="${esc(id)}" data-multi="1"></div>
    </div>`;
  }

  function renderSources() {
    const host = $("#data-files-groups", page.panes.files);
    if (!host) return;
    const sources = availableSources();
    const notes = [];
    if (!apiAvailable()) {
      notes.push(`<p class="data-page-hint data-files-api-note">${unavailableHtml({ files: true })}</p>`);
    } else if (!storesFor(files.root).length) {
      notes.push(`<p class="data-page-hint">${esc(ui(
        "This export has no store files (game/Unity.sqlite, game/GameFiles.sqlite).",
        "该导出没有存储文件（game/Unity.sqlite、game/GameFiles.sqlite）。",
      ))}</p>`);
    }
    if (page.decoded.status === "error") {
      notes.push(`<p class="data-page-hint is-error">${esc(ui("Decoded datasets are unavailable:", "解码数据集不可用："))} <code>${esc(page.decoded.error)}</code></p>`);
    }
    host.innerHTML = `
      <p class="data-page-hint">${esc(ui(
        "Select sources or groups; several at once list them together. Nothing selected lists every source.",
        "选择来源或分组，可多选并一起列出。未选择时列出所有来源。",
      ))}</p>
      <div id="data-files-source-chips" class="chips data-files-source-chips" data-multi="1"></div>
      ${sources.map(sourceBlockHtml).join("")}
      ${notes.join("")}`;
    renderFacets();
    syncDecodedFilterSections();
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
        "A PathID is unique only within one CAB; compare the CAB of each row. Select types to narrow the list.",
        "PathID 仅在同一 CAB 内唯一；请比较各行的 CAB。可选择类型以缩小列表。",
      ))}</p>`;
    WebUI.filters?.buildChips($("#data-files-hit-chips", host), hits.types.map((item) => ({
      value: item.type,
      label: item.type,
      count: item.rows,
      className: "kind-chip is-path-chip",
    })), {
      active: files.facets ? files.facets.active("unity") : new Set(),
      prune: false,
      onToggle: (value, info) => ensureFacets().toggle("unity", value, info.on),
    });
  }

  // ------------------------------------------------------------ list data --

  function decodedRows() {
    if (!decodedReady() || (files.query && files.field !== "name")) return [];
    const rows = ensureFacets().filter(page.decoded.records);
    const compare = decodedApi()?.comparator(files.sort);
    return compare ? rows.sort(window.WebUI.sorting.comparator("data-files-sort", compare)) : rows;
  }

  // One page of the listed sources, read as one sequence: each store segment
  // is one /api/stores/rows request (the API caps a request at 1,000 rows, so
  // a larger remainder is read in consecutive requests), and a segment the
  // page does not reach is still asked for one row to learn its total.
  async function fetchRows() {
    syncFilesUrl();
    const token = ++files.reqToken;
    const facets = ensureFacets();
    const sources = includedSources();
    const pageSize = files.pager?.pageSize || WebUI.pagination?.DEFAULT_PAGE_SIZE || MAX_API_ROWS;
    const start = (files.pager?.page || 0) * pageSize;
    files.loading = true;
    renderListMeta();
    let rows = [];
    let cumulative = 0;
    const segments = [];
    const errors = [];
    for (const source of sources) {
      const offset = Math.max(0, start - cumulative);
      if (source === "decoded") {
        const list = decodedRows();
        const want = pageSize - rows.length;
        if (want > 0) rows = rows.concat(list.slice(offset, offset + want).map((entry) => ({ kind: "decoded", entry })));
        segments.push({ source, start: cumulative, total: list.length, pending: page.decoded.status === "loading" });
        cumulative += list.length;
        continue;
      }
      if (files.query && files.field !== "name" && source !== "unity") {
        segments.push({ source, start: cumulative, total: 0, skipped: true });
        continue;
      }
      try {
        let total = 0;
        let read = 0;
        for (;;) {
          const want = pageSize - rows.length;
          const limit = Math.max(1, Math.min(MAX_API_ROWS, want));
          const result = await storeApi("rows", {
            root: files.root,
            store: source,
            group: [...facets.active(source)],
            q: files.query,
            field: files.query ? files.field : "name",
            offset: offset + read,
            limit,
          });
          if (token !== files.reqToken) return;
          total = Number(result.total) || 0;
          const batch = want > 0 ? (result.rows || []) : [];
          rows = rows.concat(batch.map((row) => ({ kind: "store", store: source, row })));
          read += batch.length;
          if (want <= 0 || batch.length < limit) break;
        }
        segments.push({ source, start: cumulative, total });
        cumulative += total;
      } catch (error) {
        if (token !== files.reqToken) return;
        errors.push(`${sourceLabel(source)}: ${error.message}`);
        segments.push({ source, start: cumulative, total: 0, error: error.message });
      }
    }
    files.loading = false;
    files.rows = rows;
    files.total = cumulative;
    files.segments = segments;
    files.offset = start;
    files.error = errors.join("\n");
    files.pager?.setTotal(cumulative);
    if (files.pager && files.pager.page * pageSize !== start && cumulative > 0) {
      // The total shrank below this page; the pager moved back, so refetch.
      fetchRows();
      return;
    }
    computeTops();
    renderListMeta();
    applyListRows({ resetScroll: true });
    resolveAutoSelect();
  }

  function computeTops() {
    let top = 0;
    files.tops = files.rows.map((item) => {
      const current = top;
      top += item.kind === "decoded" ? DECODED_ROW_HEIGHT : STORE_ROW_HEIGHT;
      return current;
    });
    files.height = top;
  }

  function rowHeight(index) {
    return files.rows[index]?.kind === "decoded" ? DECODED_ROW_HEIGHT : STORE_ROW_HEIGHT;
  }

  function resolveAutoSelect() {
    const wanted = files.autoSelect;
    if (wanted) {
      if (wanted.kind === "decoded" && page.decoded.status === "loading") return;
      files.autoSelect = null;
      let index = -1;
      if (wanted.kind === "decoded") {
        const entry = decodedApi()?.find(wanted.datasetId, wanted.recordId);
        index = entry ? files.rows.findIndex((item) => item.kind === "decoded" && item.entry._key === entry._key) : -1;
        if (index < 0 && entry && !wanted.moved) {
          // The record is listed on another page: move there once.
          const segment = files.segments.find((item) => item.source === "decoded");
          const position = decodedRows().findIndex((candidate) => candidate._key === entry._key);
          if (segment && position >= 0 && files.pager?.showIndex(segment.start + position)) {
            files.autoSelect = { ...wanted, moved: true };
            fetchRows();
            return;
          }
        }
        if (index < 0) {
          showViewerMessage(`${esc(ui("No decoded record", "未找到解码记录"))} <code>${esc(wanted.recordId)}</code>${
            wanted.datasetId ? ` (<code>${esc(wanted.datasetId)}</code>)` : ""} ${esc(ui("in the current list.", "（当前列表中）。"))}`, { error: true });
          return;
        }
      } else {
        index = files.rows.findIndex((item) => item.kind === "store" && item.row.name === wanted.name);
        if (index < 0) {
          index = files.rows.findIndex((item) => item.kind === "store"
            && item.row.name.toLowerCase() === wanted.name.toLowerCase());
        }
        if (index < 0) {
          if (!files.error) {
            showViewerMessage(`${esc(ui("No row named", "未找到名为"))} <code>${esc(wanted.name)}</code> ${esc(ui(
              `in ${selectionText()}.`,
              `的行（${selectionText()}）。`,
            ))}`, { error: true });
          }
          return;
        }
      }
      selectItem(files.rows[index]);
      scrollRowIntoView(index);
    } else if (files.autoSelectSingle) {
      files.autoSelectSingle = false;
      if (files.rows.length === 1) selectItem(files.rows[0]);
    }
  }

  function selectionText() {
    const facets = files.facets;
    const parts = includedSources().map((source) => {
      const groups = facets ? [...facets.active(source)] : [];
      const names = source === "decoded"
        ? groups.map((id) => page.decoded.datasets.find((dataset) => dataset.id === id)?.title || id)
        : groups;
      if (!names.length) return sourceLabel(source);
      const shown = names.slice(0, 3).join(", ");
      return `${sourceLabel(source)} / ${shown}${names.length > 3 ? ` +${names.length - 3}` : ""}`;
    });
    return parts.join(" · ") || ui("nothing", "无");
  }

  function renderListMeta() {
    const host = $("#data-files-list-meta", page.panes.files);
    if (!host) return;
    if (files.loading) {
      host.textContent = ui("Loading…", "正在加载…");
      return;
    }
    const pending = files.segments.some((segment) => segment.pending);
    const skipped = files.segments.filter((segment) => segment.skipped).map((segment) => sourceLabel(segment.source));
    host.innerHTML = `<span>${esc(formatNumber(files.total))}</span> ${esc(files.query ? ui("matching rows", "条匹配行") : ui("rows", "行"))}`
      + ` · <span class="data-page-list-group">${esc(selectionText())}</span>`
      + (pending ? ` · ${esc(ui("decoded datasets loading…", "解码数据集加载中…"))}` : "")
      + (skipped.length ? ` · ${esc(ui(`${skipped.join(", ")}: not searchable by this field`, `${skipped.join("、")}：不支持按此字段搜索`))}` : "")
      + (files.error && files.rows.length ? `<div class="is-error">${esc(files.error)}</div>` : "");
  }

  function applyListRows({ resetScroll = false } = {}) {
    const spacer = $("#data-files-list-spacer", page.panes.files);
    if (spacer) spacer.style.height = `${files.height}px`;
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

  function rowKey(item, root = files.root) {
    return item.kind === "decoded"
      ? `d\n${item.entry._key}`
      : `s\n${root}\n${item.store}\n${item.row.group}\n${item.row.name}`;
  }

  function selectedKey() {
    const selected = files.selected;
    if (!selected) return "";
    return selected.kind === "decoded"
      ? rowKey(selected)
      : rowKey({ kind: "store", store: selected.store, row: selected.row }, selected.root);
  }

  function rowMetaText(item) {
    const { row, store } = item;
    const parts = [row.group];
    if (store === "unity") {
      const stem = row.name.replace(/\.[^.]+$/, "").replace(/_p[0-9A-Fa-f]{16}$/, "");
      if (row.objectName && row.objectName !== stem) parts.push(row.objectName);
      if (row.pathIdHex) parts.push(`0x${row.pathIdHex}`);
    }
    parts.push(formatBytes(row.size));
    if (store !== "unity" && row.sha256) parts.push(String(row.sha256).slice(0, 12));
    return parts.join(" · ");
  }

  function firstVisibleIndex(top) {
    let low = 0;
    let high = files.tops.length;
    while (low < high) {
      const mid = (low + high) >> 1;
      if (files.tops[mid] + rowHeight(mid) <= top) low = mid + 1;
      else high = mid;
    }
    return low;
  }

  function renderList() {
    const wrap = $("#data-files-list-wrap", page.panes.files);
    const list = $("#data-files-list", page.panes.files);
    if (!wrap || !list) return;
    if (files.error && !files.rows.length) {
      list.innerHTML = `<div class="data-inspector-empty-list is-error">${esc(files.error)}</div>`;
      return;
    }
    if (!files.rows.length) {
      const pending = files.segments.some((segment) => segment.pending) || files.loading;
      list.innerHTML = `<div class="data-inspector-empty-list">${esc(pending ? ui("Loading…", "正在加载…")
        : includedSources().length ? ui("No matching rows.", "没有匹配的行。") : ui("No source is available.", "没有可用的来源。"))}</div>`;
      return;
    }
    const current = selectedKey();
    const startTop = Math.max(0, wrap.scrollTop - OVERSCAN_PX);
    const endTop = wrap.scrollTop + wrap.clientHeight + OVERSCAN_PX;
    const fragment = document.createDocumentFragment();
    const decoded = decodedApi();
    for (let index = firstVisibleIndex(startTop); index < files.rows.length && files.tops[index] < endTop; index += 1) {
      const item = files.rows[index];
      const selected = rowKey(item) === current;
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.rowIndex = String(index);
      button.style.top = `${files.tops[index]}px`;
      button.style.height = `${rowHeight(index)}px`;
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", String(selected));
      if (item.kind === "decoded") {
        button.className = `data-inspector-row${selected ? " is-selected" : ""}`;
        button.innerHTML = decoded ? decoded.rowHtml(item.entry) : esc(item.entry.title);
      } else {
        button.className = `data-inspector-row data-files-row${selected ? " is-selected" : ""}`;
        button.innerHTML = `<span class="data-inspector-row-title" title="${esc(item.row.name)}">${esc(item.row.name)}</span>
          <span class="data-inspector-row-path">${esc(rowMetaText(item))}</span>`;
      }
      fragment.appendChild(button);
    }
    list.replaceChildren(fragment);
  }

  function scrollRowIntoView(index) {
    const wrap = $("#data-files-list-wrap", page.panes.files);
    if (!wrap) return;
    const top = files.tops[index] || 0;
    const height = rowHeight(index);
    if (top < wrap.scrollTop || top + height > wrap.scrollTop + wrap.clientHeight) {
      wrap.scrollTop = Math.max(0, top - wrap.clientHeight / 2);
    }
    renderList();
  }

  // -------------------------------------------------------------- viewer --

  function selectItem(item) {
    files.selected = item.kind === "decoded"
      ? { kind: "decoded", entry: item.entry }
      : { kind: "store", root: files.root, store: item.store, group: item.row.group, row: item.row };
    files.doc = null;
    // A decoded record still loading must not render over a store row.
    if (item.kind === "store") decodedApi()?.clearSelection();
    renderList();
    syncFilesUrl();
    renderViewer();
    if (item.kind === "store") loadDocument();
  }

  // Navigation handed back by the decoded record viewer.
  const decodedHooks = {
    // A catalog term lists the records of this record's dataset carrying it.
    onCatalogTerm(term, entry) {
      clearTimeout(files.qTimer);
      files.query = term;
      files.catalogTerm = term;
      files.field = "name";
      ensureFacets().restore({ decoded: [entry._datasetId] });
      persistSelection();
      syncDecodedFilterSections();
      syncFieldSelect();
      resetSearchState();
      fetchRows();
    },
    // A resolved stored reference opens its target record, widening the list
    // to that record's dataset when the current filters hide it.
    onOpenRecord(key) {
      const entry = decodedApi()?.byKey(key);
      if (!entry) return;
      const listed = includedSources().includes("decoded") && decodedRows().some((item) => item._key === key);
      if (!listed) {
        clearTimeout(files.qTimer);
        files.query = "";
        files.catalogTerm = "";
        files.field = "name";
        ensureFacets().restore({ decoded: [entry._datasetId] });
        persistSelection();
        syncDecodedFilterSections();
        syncFieldSelect();
        resetSearchState();
      }
      files.autoSelect = { kind: "decoded", datasetId: entry._datasetId, recordId: entry.id };
      fetchRows();
    },
  };

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
        "Select a row to view its document or decoded record.",
        "选择一行以查看其文档或解码记录。",
      ))}</div>`;
      return;
    }
    if (selected.kind === "decoded") {
      decodedApi()?.showRecord(host, selected.entry, decodedHooks);
      return;
    }
    const { row, store, group, root } = selected;
    const unity = store === "unity";
    const cards = [
      factCard(ui("Size", "大小"), `${esc(formatBytes(row.size))}<span class="data-inspector-alt-form">${esc(formatNumber(row.size))} B</span>`),
    ];
    // Loose files are not hashed by the listing; the stores record a SHA-256 per row.
    if (row.sha256) cards.push(factCard("SHA-256", `<code class="data-page-hash">${esc(row.sha256)}</code>`, { wide: true }));
    if (unity) {
      if (row.objectName) cards.push(factCard(ui("Object name", "对象名称"), `<code>${esc(row.objectName)}</code>`));
      if (row.pathId != null) {
        cards.push(factCard("PathID", `<code>${esc(row.pathId)}</code><span class="data-inspector-alt-form">0x${esc(row.pathIdHex || "")}</span>${findPathIdButton(row.pathId)}`));
      }
      if (row.sourceFile) {
        cards.push(factCard("CAB", `<code>${esc(row.sourceFile)}</code><button type="button" class="data-page-inline-action" data-filter-cab="${esc(row.sourceFile)}"
          title="${esc(ui("List Unity rows of the selected groups from the same CAB", "列出所选分组中来自同一 CAB 的 Unity 行"))}">${esc(ui("filter", "筛选"))}</button>`, { wide: true }));
      }
      if (row.scriptPathId != null) {
        cards.push(factCard(ui("Script PathID", "脚本 PathID"), `<code>${esc(row.scriptPathId)}</code>${findPathIdButton(row.scriptPathId)}`));
      }
    } else {
      const folderLabel = FILE_SOURCES.includes(store) ? ui("Folder", "目录") : ui("Packed folder", "打包目录");
      cards.push(factCard(folderLabel, `<code>${esc(group)}</code>`));
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
            <h3>${esc(FILE_SOURCES.includes(store) ? ui("Export file", "导出文件") : ui("Store row", "存储行"))}</h3>
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

  function classify(bytes, complete, name, { undecoded = false } = {}) {
    // Undecoded files are shown as bytes even when they happen to be text.
    if (undecoded) return { kind: "binary", undecoded: true };
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
      const undecoded = !!selected.row.binary;
      // A hex dump shows a prefix, so an undecoded file never needs more.
      const limit = undecoded ? Math.min(size || PREFIX_FETCH_BYTES, PREFIX_FETCH_BYTES)
        : full || size <= FULL_FETCH_BYTES ? Infinity : PREFIX_FETCH_BYTES;
      const { bytes, complete } = await readBytes(selected.row.url, { limit });
      if (token !== files.docToken) return;
      files.doc = { key, status: "ready", bytes, complete, showAllText: false, hexBytes: HEX_PREVIEW_BYTES,
        ...classify(bytes, complete, selected.row.name, { undecoded }) };
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
      const kindText = doc.undecoded
        ? ui("undecoded, shown as bytes", "未解码，按字节显示")
        : ui("binary (not UTF-8 text)", "二进制（非 UTF-8 文本）");
      note.textContent = `${formatBytes(size)} · ${kindText}${partial}`;
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
    // A decoded record binds its own viewer events (index.js).
    if (files.selected?.kind === "decoded") return;
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
      clearTimeout(files.qTimer);
      files.field = "cab";
      files.query = cab.dataset.filterCab;
      files.catalogTerm = "";
      syncFieldSelect();
      resetSearchState();
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

  // Where does this PathID occur? One indexed query over the Unity store for
  // the per-type counts, then the ordinary pathId filter over the whole Unity
  // store (the type chips of the hit panel narrow it).
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
    clearTimeout(files.qTimer);
    files.field = "pathId";
    files.query = text;
    files.catalogTerm = "";
    ensureFacets().restore({ source: ["unity"] });
    persistSelection();
    syncDecodedFilterSections();
    syncFieldSelect();
    resetSearchState();
    files.pathIdHits = { pathId: text, types, error };
    files.autoSelectSingle = true;
    renderHits();
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

  // Loose files have no SQLite behind them, so SQL offers only the stores.
  function sqlStores() {
    return storesFor(sql.root).filter((entry) => entry.sql !== false);
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
          <header>
            <h1>${esc(ui("SQL query", "SQL 查询"))}</h1>
            ${modeSwitchHtml("sql")}
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
