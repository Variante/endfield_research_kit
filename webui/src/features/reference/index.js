(() => {
  const REF_TEXTS = {
    zh: {
      tab: "\u6587\u672c",
      title: "\u6587\u672c",
      countLabel: "\u5f20\u8868",
      search: "\u641c\u7d22\u8868 / ID / \u6587\u672c",
      showFilters: "\u663e\u793a\u7b5b\u9009",
      hideFilters: "\u9690\u85cf\u7b5b\u9009",
      reset: "\u91cd\u7f6e\u7b5b\u9009",
      basicFilters: "\u57fa\u7840\u7b5b\u9009",
      source: "\u6765\u6e90",
      group: "\u5206\u7ec4",
      empty: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u5f20\u8868",
      loading: "\u52a0\u8f7d\u4e2d...",
      loadError: "\u52a0\u8f7d\u5931\u8d25: ",
      tables: "\u5f20\u8868",
      rows: "\u884c",
      texts: "\u6587\u672c",
      noRows: "\u6ca1\u6709\u5339\u914d\u6587\u672c",
      showingFirst: "\u663e\u793a\u524d",
      contentMatch: "\u5185\u5bb9\u5339\u914d",
      rendered: "\u6e32\u67d3\u6587\u672c",
      rawJson: "\u539f\u59cb JSON",
      rawLoading: "\u52a0\u8f7d\u539f\u59cb\u6587\u4ef6\u4e2d...",
      rawUnavailable: "\u6ca1\u6709\u539f\u59cb\u6587\u4ef6",
      sourceFile: "\u6e90\u6587\u4ef6",
      overlayFile: "\u8986\u76d6\u6587\u4ef6",
      baseFile: "\u57fa\u7840\u6587\u4ef6",
      hash: "\u54c8\u5e0c",
      sameHashFiles: "\u76f8\u540c\u54c8\u5e0c\u6587\u4ef6",
    },
    en: {
      tab: "Text",
      title: "Text",
      countLabel: "tables",
      search: "Search table / ID / text",
      showFilters: "Show filters",
      hideFilters: "Hide filters",
      reset: "Reset filters",
      basicFilters: "Basic filters",
      source: "Source",
      group: "Group",
      empty: "Select a table",
      loading: "Loading...",
      loadError: "Load failed: ",
      tables: "tables",
      rows: "rows",
      texts: "texts",
      noRows: "No matching text",
      showingFirst: "Showing first",
      contentMatch: "content match",
      rendered: "Rendered text",
      rawJson: "Raw JSON",
      rawLoading: "Loading raw file...",
      rawUnavailable: "No raw file",
      sourceFile: "Source file",
      overlayFile: "Overlay file",
      baseFile: "Base file",
      hash: "Hash",
      sameHashFiles: "Same-hash files",
    },
  };
  const ROW_RENDER_LIMIT = 500;
  const FILTER_PANEL_STORAGE_KEY = "reference_browser_filters_collapsed";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const RAW_EXPORT_SOURCE_ROOTS = {
    streaming: "StreamingAssets",
    persistent: "Persistent",
  };
  const {
    $,
    escapeHtml,
    storageGet,
    storageSet,
    textIncludes,
  } = window.WebUI;
  const REF_STATE = {
    index: null,
    tables: [],
    selectedTable: null,
    selectedPayload: null,
    tableCache: new Map(),
    tableLoads: new Map(),
    rawTextCache: new Map(),
    rawTextLoads: new Map(),
    i18nCache: new Map(),
    i18nLoads: new Map(),
    contentMatches: new Map(),
    contentScansDone: new Set(),
    contentScanTimer: 0,
    contentScanKey: "",
    contentScanToken: 0,
    loadingIndex: null,
    activeGroup: "",
    sourceFilters: new Set(),
    collapsedTablePrefixes: new Set(),
  };

  const ref$ = $;

  function isReferenceMobileLayout() {
    return !!(window.matchMedia && window.matchMedia(MOBILE_LAYOUT_QUERY).matches);
  }

  let referencePanel = null;

  function ensureReferencePanelToggle() {
    if (referencePanel) return referencePanel;
    referencePanel = window.WebUI.filters.createPanelToggle({
      panel: "#reference-filter-panel",
      toggle: "#reference-filter-toggle",
      left: "#reference-left",
      storageKey: FILTER_PANEL_STORAGE_KEY,
      isMobile: isReferenceMobileLayout,
      labels: (collapsed) => refText(collapsed ? "showFilters" : "hideFilters"),
    });
    return referencePanel;
  }

  function syncReferenceFilterPanel() {
    referencePanel?.sync();
  }

  function refLocale() {
    const raw = String(window.WEBUI_UI_LOCALE || "zh").toLowerCase();
    return raw === "en" ? "en" : "zh";
  }

  function refText(key) {
    return (REF_TEXTS[refLocale()] || REF_TEXTS.en)[key] || key;
  }

  function currentLanguage() {
    const select = ref$("#language");
    return (select && select.value) || "CN";
  }

  function referenceDataPath(relativePath) {
    return dataPath(`reference/${relativePath}`, currentLanguage());
  }

  function referenceSourceKey(value) {
    const raw = String(value || "").trim().toLowerCase();
    return raw.includes("persistent") ? "persistent" : "streaming";
  }

  function exportFullPath(parts) {
    return `/export_full/${parts.map((part) => encodeURIComponent(String(part || ""))).join("/")}`;
  }

  function exportTablePath(sourceKey, tableName) {
    const root = RAW_EXPORT_SOURCE_ROOTS[referenceSourceKey(sourceKey)];
    const name = String(tableName || "").trim();
    return root && name ? exportFullPath(["structured", root, "Table", name]) : "";
  }

  function rawDisplayPath(path) {
    return String(path || "").replace(/^\/+/, "");
  }

  function referenceTableKey(table) {
    return [
      table && table.source ? table.source : "",
      table && table.table ? table.table : "",
      table && table.file ? table.file : "",
    ].join("\u0000");
  }
  function tableContentHash(table) {
    return String(table && (table.hash || table.sha256 || "") || "").trim();
  }

  function referenceTableFileRecord(table) {
    return {
      source: String(table && table.source || ""),
      sourceLabel: String(table && table.sourceLabel || table && table.source || ""),
      table: String(table && table.table || ""),
      label: String(table && table.label || table && table.table || ""),
      file: String(table && table.file || ""),
      baseFile: String(table && table.baseFile || ""),
      storage: String(table && table.storage || ""),
      rows: Number(table && table.rows || 0),
      texts: Number(table && table.texts || 0),
      bytes: Number(table && table.bytes || 0),
      hash: tableContentHash(table),
    };
  }

  function referenceSameHashFiles(table) {
    if (Array.isArray(table && table.sameHashFiles) && table.sameHashFiles.length) return table.sameHashFiles;
    const file = referenceTableFileRecord(table || {});
    return file.file ? [file] : [];
  }

  function aggregateReferenceTables(tables) {
    const out = [];
    const byHash = new Map();
    for (const table of tables || []) {
      const hash = tableContentHash(table);
      if (!hash) {
        out.push(table);
        continue;
      }
      const file = referenceTableFileRecord(table);
      const existing = byHash.get(hash);
      if (!existing) {
        const copy = { ...table, sameHashFiles: file.file ? [file] : [], fileCount: file.file ? 1 : 0 };
        byHash.set(hash, copy);
        out.push(copy);
        continue;
      }
      const key = `${file.source}\u0000${file.table}\u0000${file.file}`;
      if (file.file && !existing.sameHashFiles.some((item) => `${item.source}\u0000${item.table}\u0000${item.file}` === key)) {
        existing.sameHashFiles.push(file);
        existing.fileCount = existing.sameHashFiles.length;
      }
    }
    return out;
  }

  function tableSourceEntries(table) {
    return referenceSameHashFiles(table).length ? referenceSameHashFiles(table) : [referenceTableFileRecord(table)];
  }

  function tableSourceKeys(table) {
    return [...new Set(tableSourceEntries(table).map((file) => file.source).filter(Boolean))];
  }

  function sameHashFileCount(table) {
    return referenceSameHashFiles(table).length;
  }

  function sameHashFileSummary(table, limit = 20) {
    const files = referenceSameHashFiles(table).map((file) => `${file.source || "?"}/${file.file || file.table}`).filter(Boolean);
    if (files.length <= limit) return files.join(", ");
    return `${files.slice(0, limit).join(", ")} ... +${files.length - limit}`;
  }

  function referenceSearchKey(q, source) {
    return `${source || ""}\u0000${q || ""}`;
  }

  async function fetchReferenceJson(relativePath) {
    const res = await fetch(referenceDataPath(relativePath));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }


  async function fetchAbsoluteJson(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${path} HTTP ${res.status}`);
    return res.json();
  }

  function parseRawReferenceJson(text) {
    return JSON.parse(String(text || "").replace(/("id"\s*:\s*)(-?\d{15,})(?=\s*[,}])/g, "$1\"$2\""));
  }

  async function fetchRawReferenceJson(relativePath) {
    const res = await fetch(referenceDataPath(relativePath));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return parseRawReferenceJson(await res.text());
  }

  async function fetchRawExportJson(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${path} HTTP ${res.status}`);
    return parseRawReferenceJson(await res.text());
  }

  function applyReferenceTableMetadata(payload, table) {
    return {
      ...(payload || {}),
      source: table.sourceLabel || table.source || (payload && payload.source) || "",
      sourceKey: table.source || "",
      table: table.table || (payload && payload.table) || "",
      label: table.label || (payload && payload.label) || "",
    };
  }

  function mergeReferenceOverlay(basePayload, overlayPayload) {
    const byId = new Map();
    for (const row of (basePayload && basePayload.rows) || []) {
      const id = String(row && row.id || "");
      if (id) byId.set(id, row);
    }
    for (const id of overlayPayload.removedRows || []) {
      byId.delete(String(id || ""));
    }
    for (const row of overlayPayload.rows || []) {
      const id = String(row && row.id || "");
      if (id) byId.set(id, row);
    }

    const rowOrder = Array.isArray(overlayPayload.rowOrder)
      ? overlayPayload.rowOrder.map((id) => String(id || "")).filter(Boolean)
      : [];
    const rows = rowOrder.length
      ? rowOrder.map((id) => byId.get(id)).filter(Boolean)
      : Array.from(byId.values());

    return {
      ...(basePayload || {}),
      ...(overlayPayload || {}),
      rows,
    };
  }

  function tableMetadataMatches(table, q) {
    return [
      table.label,
      table.table,
      table.source,
      table.sourceLabel,
      tablePrefix(table),
    ].some((value) => textIncludes(value, q));
  }

  function tableContentMatches(table, q, source) {
    const matches = REF_STATE.contentMatches.get(referenceSearchKey(q, source));
    return !!(matches && matches.has(referenceTableKey(table)));
  }

  async function loadReferencePayload(table) {
    const cacheKey = referenceTableKey(table);
    const cached = REF_STATE.tableCache.get(cacheKey);
    if (cached) return cached;

    const pending = REF_STATE.tableLoads.get(cacheKey);
    if (pending) return pending;

    const promise = fetchReferenceJson(table.file)
      .then(async (payload) => {
        if (payload && payload.baseFile) {
          const basePayload = await fetchReferenceJson(payload.baseFile);
          return mergeReferenceOverlay(basePayload, payload);
        }
        return payload;
      })
      .then((payload) => {
        const normalized = applyReferenceTableMetadata(payload, table);
        REF_STATE.tableCache.set(cacheKey, normalized);
        REF_STATE.tableLoads.delete(cacheKey);
        return normalized;
      })
      .catch((error) => {
        REF_STATE.tableLoads.delete(cacheKey);
        throw error;
      });

    REF_STATE.tableLoads.set(cacheKey, promise);
    return promise;
  }

  function referenceI18nSourceOrder(preferredSource) {
    const preferred = referenceSourceKey(preferredSource);
    const order = [preferred];
    for (const source of ["persistent", "streaming"]) {
      if (!order.includes(source)) order.push(source);
    }
    return order;
  }

  async function loadReferenceI18nMap(sourceKey) {
    const source = referenceSourceKey(sourceKey);
    const cacheKey = `${currentLanguage()}\u0000${source}`;
    const cached = REF_STATE.i18nCache.get(cacheKey);
    if (cached) return cached;

    const pending = REF_STATE.i18nLoads.get(cacheKey);
    if (pending) return pending;

    const path = exportTablePath(source, `I18nTextTable_${currentLanguage()}.json`);
    const promise = fetchAbsoluteJson(path)
      .catch(() => ({}))
      .then((payload) => {
        const map = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
        REF_STATE.i18nCache.set(cacheKey, map);
        REF_STATE.i18nLoads.delete(cacheKey);
        return map;
      });
    REF_STATE.i18nLoads.set(cacheKey, promise);
    return promise;
  }

  async function loadReferenceI18nMaps(preferredSource) {
    const maps = {};
    await Promise.all(referenceI18nSourceOrder(preferredSource).map(async (source) => {
      maps[source] = await loadReferenceI18nMap(source);
    }));
    return maps;
  }

  function resolveReferenceI18nText(idValue, maps, preferredSource) {
    const key = String(idValue == null ? "" : idValue);
    if (!key) return "";
    for (const source of referenceI18nSourceOrder(preferredSource)) {
      const text = maps && maps[source] && maps[source][key];
      if (text) return String(text);
    }
    return "";
  }

  function resolveRawReferenceStructure(value, maps, preferredSource) {
    if (Array.isArray(value)) {
      return value.map((item) => resolveRawReferenceStructure(item, maps, preferredSource));
    }
    if (!value || typeof value !== "object") return value;

    const isI18nText = Object.prototype.hasOwnProperty.call(value, "id")
      && Object.prototype.hasOwnProperty.call(value, "text");
    const resolvedText = isI18nText ? resolveReferenceI18nText(value.id, maps, preferredSource) : "";
    const out = {};
    for (const [key, child] of Object.entries(value)) {
      out[key] = isI18nText && key === "text" && resolvedText
        ? resolvedText
        : resolveRawReferenceStructure(child, maps, preferredSource);
    }
    return out;
  }

  function bundledRawReferencePayload(payload) {
    if (payload && payload.rawRows && typeof payload.rawRows === "object" && !Array.isArray(payload.rawRows)) {
      if ((Array.isArray(payload.rowOrder) && payload.rowOrder.length)
        || (Array.isArray(payload.removedRows) && payload.removedRows.length)) {
        const out = {};
        if (Array.isArray(payload.rowOrder)) out.rowOrder = payload.rowOrder;
        if (Array.isArray(payload.removedRows) && payload.removedRows.length) out.removedRows = payload.removedRows;
        out.rows = payload.rawRows;
        return out;
      }
      return payload.rawRows;
    }
    return payload;
  }

  function formatRawReferencePayload(payload) {
    return JSON.stringify(payload == null ? null : payload, null, 2);
  }

  async function loadReferenceRawDisplay(file) {
    let sourceError = null;
    if (file && file.exportPath) {
      try {
        const payload = await fetchRawExportJson(file.exportPath);
        const maps = await loadReferenceI18nMaps(file.sourceKey);
        return {
          text: formatRawReferencePayload(resolveRawReferenceStructure(payload, maps, file.sourceKey)),
          displayPath: rawDisplayPath(file.exportPath),
          href: file.exportPath,
        };
      } catch (error) {
        sourceError = error;
      }
    }

    if (file && file.fallbackPath) {
      const payload = await fetchRawReferenceJson(file.fallbackPath);
      return {
        text: formatRawReferencePayload(bundledRawReferencePayload(payload)),
        displayPath: file.fallbackPath,
        href: referenceDataPath(file.fallbackPath),
      };
    }
    throw sourceError || new Error(refText("rawUnavailable"));
  }

  async function loadReferenceRawText(file) {
    const cacheKey = JSON.stringify([
      currentLanguage(),
      file && file.sourceKey || "",
      file && file.tableName || "",
      file && file.exportPath || "",
      file && file.fallbackPath || "",
    ]);
    const cached = REF_STATE.rawTextCache.get(cacheKey);
    if (cached != null) return cached;

    const pending = REF_STATE.rawTextLoads.get(cacheKey);
    if (pending) return pending;

    const promise = loadReferenceRawDisplay(file)
      .then((display) => {
        REF_STATE.rawTextCache.set(cacheKey, display);
        REF_STATE.rawTextLoads.delete(cacheKey);
        return display;
      })
      .catch((error) => {
        REF_STATE.rawTextLoads.delete(cacheKey);
        throw error;
      });

    REF_STATE.rawTextLoads.set(cacheKey, promise);
    return promise;
  }

  function applyReferenceStrings() {
    const labels = [
      ["#reference-tab", "tab"],
      ["#reference-title", "title"],
      ["#reference-count-label", "countLabel"],
      ["#reference-basic-filter-label", "basicFilters"],
      ["#reference-group-label", "group"],
      ["#reference-source-label", "source"],
      ["#reference-empty", "empty"],
      ["#reference-list-unit", "tables"],
      ["#reference-rendered-title", "rendered"],
      ["#reference-raw-title", "rawJson"],
    ];
    for (const [sel, key] of labels) {
      const node = ref$(sel);
      if (node) node.textContent = refText(key);
    }
    const q = ref$("#reference-q");
    if (q) q.placeholder = refText("search");
    const reset = ref$("#reference-reset");
    if (reset) reset.textContent = refText("reset");
    syncReferenceFilterPanel();
  }

  async function ensureReferenceIndex() {
    if (REF_STATE.index) return REF_STATE.index;
    if (REF_STATE.loadingIndex) return REF_STATE.loadingIndex;

    window.WebUI.showLoader("reference");
    REF_STATE.loadingIndex = window.WebUI.fetchWithProgress(referenceDataPath("index.json"), {
      // Downloading is only part of the work; reserve the last 10% for parsing
      // and rendering so the bar does not sit at 100% while the page is busy.
      onProgress: (ratio) => window.WebUI.updateLoader("reference", ratio == null ? null : ratio * 0.9),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        REF_STATE.index = payload || {};
        REF_STATE.tables = aggregateReferenceTables(Array.isArray(payload && payload.tables) ? payload.tables : []);
        REF_STATE.loadingIndex = null;
        buildReferenceGroupChips();
        buildSourceChips();
        renderReferenceList();
        window.WebUI.updateLoader("reference", 1);
        window.WebUI.hideLoader("reference");
        return REF_STATE.index;
      })
      .catch((error) => {
        REF_STATE.loadingIndex = null;
        window.WebUI.hideLoader("reference");
        showReferenceError(error);
        return null;
      });
    return REF_STATE.loadingIndex;
  }

  function resetReferenceData() {
    REF_STATE.index = null;
    REF_STATE.tables = [];
    REF_STATE.selectedTable = null;
    REF_STATE.selectedPayload = null;
    REF_STATE.activeGroup = "";
    REF_STATE.tableCache.clear();
    REF_STATE.tableLoads.clear();
    REF_STATE.rawTextCache.clear();
    REF_STATE.rawTextLoads.clear();
    REF_STATE.i18nCache.clear();
    REF_STATE.i18nLoads.clear();
    REF_STATE.contentMatches.clear();
    REF_STATE.contentScansDone.clear();
    REF_STATE.collapsedTablePrefixes.clear();
    clearTimeout(REF_STATE.contentScanTimer);
    REF_STATE.contentScanTimer = 0;
    REF_STATE.contentScanKey = "";
    REF_STATE.contentScanToken += 1;
    REF_STATE.loadingIndex = null;
    const list = ref$("#reference-list");
    if (list) list.replaceChildren();
    const rows = ref$("#reference-rows");
    if (rows) rows.replaceChildren();
    const raw = ref$("#reference-raw");
    if (raw) raw.replaceChildren();
    const detail = ref$("#reference-detail");
    const empty = ref$("#reference-empty");
    if (detail) detail.hidden = true;
    if (empty) empty.hidden = false;
  }

  function showReferenceError(error) {
    const detail = ref$("#reference-detail");
    const empty = ref$("#reference-empty");
    if (detail) detail.hidden = true;
    if (empty) {
      empty.hidden = false;
      empty.textContent = refText("loadError") + (error && error.message ? error.message : String(error));
    }
  }

  function activeReferenceGroup() {
    return String(REF_STATE.activeGroup || "");
  }

  function tableGroupCounts() {
    const counts = new Map();
    for (const table of REF_STATE.tables) {
      const prefix = tablePrefix(table);
      counts.set(prefix, (counts.get(prefix) || 0) + 1);
    }
    return counts;
  }

  function setReferenceGroupFilter(group) {
    REF_STATE.activeGroup = String(group || "");
    buildReferenceGroupChips();
    renderReferenceList();
    renderReferenceRows();
  }

  function resetReferenceFilters() {
    const q = ref$("#reference-q");
    if (q) q.value = "";
    REF_STATE.activeGroup = "";
    REF_STATE.sourceFilters.clear();
    clearTimeout(REF_STATE.contentScanTimer);
    REF_STATE.contentScanTimer = 0;
    REF_STATE.contentScanKey = "";
    REF_STATE.contentScanToken += 1;
    buildReferenceGroupChips();
    buildSourceChips();
    renderReferenceList();
    renderReferenceRows();
  }

  function buildReferenceGroupChips() {
    const counts = tableGroupCounts();
    if (REF_STATE.activeGroup && !counts.has(REF_STATE.activeGroup)) REF_STATE.activeGroup = "";
    const items = [...counts.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([prefix, count]) => ({ value: prefix, label: prefix, count, title: prefix }));
    window.WebUI.filters.buildChips("#reference-group-filter", items, {
      active: activeReferenceGroup(),
      single: true,
      className: "reference-filter-chip reference-group-chip",
      onToggle: (next) => setReferenceGroupFilter(next),
    });
  }

  function buildSourceChips() {
    const sources = new Map();
    for (const table of REF_STATE.tables) {
      sources.set(table.source || "", table.sourceLabel || table.source || "");
    }
    const items = [...sources.entries()]
      .filter(([source]) => source)
      .sort((a, b) => a[1].localeCompare(b[1]))
      .map(([source, label]) => ({ value: source, label: label || source }));
    window.WebUI.filters.buildChips("#reference-source-filter", items, {
      active: REF_STATE.sourceFilters,
      className: "reference-filter-chip",
      onToggle: () => {
        renderReferenceList();
        renderReferenceRows();
      },
    });
  }

  function referenceQuery() {
    const q = ref$("#reference-q");
    return String(q && q.value || "").trim().toLowerCase();
  }

  function sourceFilters() {
    return REF_STATE.sourceFilters;
  }

  function sourceFilterKey(sources = sourceFilters()) {
    return [...sources].sort().join(",");
  }

  function tableNameStem(table) {
    return String(table && (table.table || table.label) || "")
      .replace(/\.json$/i, "")
      .replace(/Table$/i, "")
      .trim();
  }

  function splitTableNameParts(value) {
    return String(value || "").match(/[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z]+|[0-9]+/g) || [];
  }

  function tablePrefix(table) {
    const stem = tableNameStem(table);
    const parts = splitTableNameParts(stem);
    return parts[0] || stem || "[root]";
  }

  function tablePrefixCollapseKey(prefix) {
    return `${sourceFilterKey()}::${prefix}`;
  }

  function tablePrefixIsCollapsed(prefix) {
    return !referenceQuery() && REF_STATE.collapsedTablePrefixes.has(tablePrefixCollapseKey(prefix));
  }

  function toggleTablePrefix(prefix) {
    const key = tablePrefixCollapseKey(prefix);
    if (REF_STATE.collapsedTablePrefixes.has(key)) REF_STATE.collapsedTablePrefixes.delete(key);
    else REF_STATE.collapsedTablePrefixes.add(key);
    renderReferenceList();
  }

  function compareReferenceTablesForList(a, b) {
    const prefixDiff = tablePrefix(a).localeCompare(tablePrefix(b));
    if (prefixDiff) return prefixDiff;
    const nameDiff = String(a.label || a.table || "").localeCompare(String(b.label || b.table || ""));
    if (nameDiff) return nameDiff;
    return String(a.source || "").localeCompare(String(b.source || ""));
  }

  function renderReferencePrefixHeading(prefix, count, collapsed) {
    const heading = document.createElement("button");
    heading.type = "button";
    heading.className = "reference-table-prefix-heading group" + (collapsed ? "" : " expanded");
    heading.dataset.prefix = prefix;
    heading.setAttribute("aria-expanded", String(!collapsed));
    heading.innerHTML =
      `<span class="twisty">${collapsed ? "&gt;" : "v"}</span>` +
      `<span class="group-main">` +
        `<span class="label" title="${escapeHtml(prefix)}">${escapeHtml(prefix)}</span>` +
      `</span>` +
      `<span class="group-count">${count}</span>`;
    heading.addEventListener("click", () => toggleTablePrefix(prefix));
    return heading;
  }

  function renderReferenceTableRow(table, q, sourceKey) {
    const contentOnlyMatch = q
      && !tableMetadataMatches(table, q)
      && tableContentMatches(table, q, sourceKey);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "reference-table-row";
    button.classList.toggle(
      "is-selected",
      !!(REF_STATE.selectedTable && referenceTableKey(REF_STATE.selectedTable) === referenceTableKey(table)),
    );
    button.innerHTML =
      `<div class="reference-table-name">` +
        `<span class="reference-table-label">${escapeHtml(table.label || table.table)}</span>` +
        `<span class="reference-table-source">${escapeHtml(table.source || "")}</span>` +
      `</div>` +
      `<div class="reference-table-meta">${escapeHtml([
        table.table,
        `${table.rows || 0} ${refText("rows")}`,
        `${table.texts || 0} ${refText("texts")}`,
        contentOnlyMatch ? refText("contentMatch") : "",
      ].filter(Boolean).join(" | "))}</div>`;
    button.addEventListener("click", () => selectReferenceTable(table));
    return button;
  }

  function tableMatches(table, q, sources, sourceKey) {
    const activeGroup = activeReferenceGroup();
    if (activeGroup && tablePrefix(table) !== activeGroup) return false;
    if (sources.size && !tableSourceKeys(table).some((source) => sources.has(source))) return false;
    if (!q) return true;
    return tableMetadataMatches(table, q) || tableContentMatches(table, q, sourceKey);
  }

  function scheduleReferenceContentScan(q, sources, sourceKey) {
    if (!q || !REF_STATE.tables.length) return;

    const key = referenceSearchKey(q, sourceKey);
    if (REF_STATE.contentScansDone.has(key) || REF_STATE.contentScanKey === key) return;
    const scanSources = new Set(sources);

    clearTimeout(REF_STATE.contentScanTimer);
    REF_STATE.contentScanTimer = setTimeout(() => {
      scanReferenceContent(q, scanSources, key);
    }, 180);
  }

  async function scanReferenceContent(q, sources, key) {
    const token = REF_STATE.contentScanToken + 1;
    REF_STATE.contentScanToken = token;
    REF_STATE.contentScanKey = key;

    const matches = REF_STATE.contentMatches.get(key) || new Set();
    REF_STATE.contentMatches.set(key, matches);

    const tables = REF_STATE.tables.filter((table) => !sources.size || sources.has(table.source));
    let cursor = 0;
    let renderQueued = false;

    const queueRender = () => {
      if (renderQueued) return;
      renderQueued = true;
      setTimeout(() => {
        renderQueued = false;
        if (REF_STATE.contentScanKey === key && referenceSearchKey(referenceQuery(), sourceFilterKey()) === key) {
          renderReferenceList();
        }
      }, 0);
    };

    const worker = async () => {
      while (cursor < tables.length && REF_STATE.contentScanToken === token) {
        const table = tables[cursor++];
        if (tableMetadataMatches(table, q)) continue;
        try {
          const payload = await loadReferencePayload(table);
          if ((payload.rows || []).some((row) => rowMatches(row, q))) {
            matches.add(referenceTableKey(table));
            queueRender();
          }
        } catch (_error) {
          // Individual table load errors are shown when that table is selected.
        }
      }
    };

    await Promise.all(Array.from({ length: Math.min(6, tables.length) }, worker));

    if (REF_STATE.contentScanToken === token && REF_STATE.contentScanKey === key) {
      REF_STATE.contentScansDone.add(key);
      REF_STATE.contentScanKey = "";
      renderReferenceList();
    }
  }

  function filteredTables() {
    const q = referenceQuery();
    const sources = sourceFilters();
    const sourceKey = sourceFilterKey(sources);
    scheduleReferenceContentScan(q, sources, sourceKey);
    return REF_STATE.tables.filter((table) => tableMatches(table, q, sources, sourceKey));
  }

  function syncReferenceFilterSectionActiveCounts() {
    window.WebUI.setFilterSectionActiveCounts?.({
      "reference-basic": referenceQuery() ? 1 : 0,
      "reference-group": REF_STATE.activeGroup ? 1 : 0,
      "reference-source": REF_STATE.sourceFilters.size,
    });
  }

  function renderReferenceList() {
    const list = ref$("#reference-list");
    if (!list) return;
    const q = referenceQuery();
    syncReferenceFilterSectionActiveCounts();
    const sourceKey = sourceFilterKey();
    const rows = filteredTables();
    list.replaceChildren();
    ref$("#reference-count").textContent = String(REF_STATE.tables.length || 0);
    ref$("#reference-shown").textContent = String(rows.length);
    ref$("#reference-total").textContent = String(REF_STATE.tables.length || 0);

    const sections = [];
    let current = null;
    for (const table of rows.slice().sort(compareReferenceTablesForList)) {
      const prefix = tablePrefix(table);
      if (!current || current.prefix !== prefix) {
        current = { prefix, tables: [] };
        sections.push(current);
      }
      current.tables.push(table);
    }

    const fragment = document.createDocumentFragment();
    for (const section of sections) {
      const collapsed = tablePrefixIsCollapsed(section.prefix);
      fragment.appendChild(renderReferencePrefixHeading(section.prefix, section.tables.length, collapsed));
      if (collapsed) continue;
      for (const table of section.tables) {
        fragment.appendChild(renderReferenceTableRow(table, q, sourceKey));
      }
    }
    list.appendChild(fragment);
  }

  async function selectReferenceTable(table) {
    REF_STATE.selectedTable = table;
    REF_STATE.selectedPayload = null;
    renderReferenceList();
    const detail = ref$("#reference-detail");
    const empty = ref$("#reference-empty");
    if (empty) empty.hidden = true;
    if (detail) detail.hidden = false;
    ref$("#reference-detail-title").textContent = table.label || table.table;
    ref$("#reference-detail-meta").textContent = refText("loading");
    ref$("#reference-rows").replaceChildren();
    renderReferenceRaw(table);

    try {
      const payload = await loadReferencePayload(table);
      if (!REF_STATE.selectedTable || referenceTableKey(REF_STATE.selectedTable) !== referenceTableKey(table)) return;
      REF_STATE.selectedPayload = payload;
      renderReferenceRows();
    } catch (error) {
      ref$("#reference-detail-meta").textContent =
        refText("loadError") + (error && error.message ? error.message : String(error));
    }
  }

  function rowMatches(row, q) {
    if (!q) return true;
    if ([row.id, row.title, row.bucket].some((value) => textIncludes(value, q))) return true;
    return (row.texts || []).some((item) => [
      item.field,
      item.hint,
      item.path,
      item.i18nId,
      item.text,
    ].some((value) => textIncludes(value, q)));
  }

  function renderReferenceRows() {
    const payload = REF_STATE.selectedPayload;
    const table = REF_STATE.selectedTable;
    if (!payload || !table) return;

    const q = referenceQuery();
    const rows = (payload.rows || []).filter((row) => rowMatches(row, q));
    const shownRows = rows.slice(0, ROW_RENDER_LIMIT);
    const metaParts = [
      payload.table || table.table,
      table.sourceLabel || table.source,
      `${rows.length} ${refText("rows")}`,
      `${table.texts || 0} ${refText("texts")}`,
    ];
    if (rows.length > shownRows.length) {
      metaParts.push(`${refText("showingFirst")} ${shownRows.length}`);
    }
    ref$("#reference-detail-meta").textContent = metaParts.filter(Boolean).join(" | ");

    const wrap = ref$("#reference-rows");
    wrap.replaceChildren();
    if (!shownRows.length) {
      const empty = document.createElement("div");
      empty.className = "reference-row";
      empty.textContent = refText("noRows");
      wrap.appendChild(empty);
      return;
    }

    for (const row of shownRows) {
      const item = document.createElement("div");
      item.className = "reference-row";
      const title = row.title && row.title !== row.id ? row.title : row.id;
      item.innerHTML =
        `<div class="reference-row-head">` +
          `<span class="reference-row-title">${escapeHtml(title)}</span>` +
          `<span class="reference-row-id">${escapeHtml(row.id || "")}</span>` +
        `</div>`;
      for (const text of row.texts || []) {
        const textNode = document.createElement("div");
        textNode.className = "reference-text";
        const label = text.hint || text.field || "text";
        textNode.innerHTML =
          `<div class="reference-text-field">${escapeHtml(label)}</div>` +
          `<div class="reference-text-path">${escapeHtml(text.path || "")}${text.i18nId ? " | " + escapeHtml(text.i18nId) : ""}</div>` +
          `<div class="reference-text-body">${escapeHtml(text.text || "")}</div>`;
        item.appendChild(textNode);
      }
      wrap.appendChild(item);
    }
  }

  function referenceRawFiles(table) {
    const files = [];
    const seen = new Set();
    const defaultTableName = String(table && table.table || "").trim();
    const add = (sourceKey, fallbackPath, labelKey, sourceTableName = defaultTableName) => {
      const source = referenceSourceKey(sourceKey);
      const tableName = String(sourceTableName || defaultTableName || "").trim();
      const key = `${source}\u0000${tableName}\u0000${fallbackPath || ""}\u0000${labelKey || ""}`;
      if ((!tableName && !fallbackPath) || seen.has(key)) return;
      seen.add(key);
      files.push({
        sourceKey: source,
        tableName,
        exportPath: tableName ? exportTablePath(source, tableName) : "",
        fallbackPath: String(fallbackPath || ""),
        labelKey,
      });
    };

    const sameHashFiles = referenceSameHashFiles(table);
    if (sameHashFiles.length > 1) {
      for (const file of sameHashFiles) {
        add(file.source, file.file, file.file === table.file ? "sourceFile" : "sameHashFiles", file.table);
        if (file.baseFile && file.baseFile !== file.file) add("streaming", file.baseFile, "baseFile", file.table);
      }
      return files;
    }

    const primarySource = referenceSourceKey(table && table.source);
    add(primarySource, table && table.file, table && table.baseFile && table.baseFile !== table.file ? "overlayFile" : "sourceFile");
    if (table && table.baseFile && table.baseFile !== table.file) {
      add("streaming", table.baseFile, "baseFile");
    }
    return files;
  }
  async function renderReferenceRaw(table) {
    const wrap = ref$("#reference-raw");
    if (!wrap) return;
    wrap.replaceChildren();
    if (!table) return;

    const selectedKey = referenceTableKey(table);
    const files = referenceRawFiles(table);
    if (!files.length) {
      const empty = document.createElement("div");
      empty.className = "reference-raw-message";
      empty.textContent = refText("rawUnavailable");
      wrap.appendChild(empty);
      return;
    }

    const loading = document.createElement("div");
    loading.className = "reference-raw-message";
    loading.textContent = refText("rawLoading");
    wrap.appendChild(loading);

    const results = await Promise.all(files.map(async (file) => {
      try {
        return { ...file, ...(await loadReferenceRawText(file)) };
      } catch (error) {
        return {
          ...file,
          error: error && error.message ? error.message : String(error),
        };
      }
    }));
    if (!REF_STATE.selectedTable || referenceTableKey(REF_STATE.selectedTable) !== selectedKey) return;

    wrap.replaceChildren();
    for (const result of results) {
      const section = document.createElement("section");
      section.className = "reference-raw-file";

      const head = document.createElement("div");
      head.className = "reference-raw-head";

      const label = document.createElement("span");
      label.className = "reference-raw-label";
      label.textContent = refText(result.labelKey);
      head.appendChild(label);

      const link = document.createElement("a");
      link.className = "reference-raw-path";
      link.href = result.href || "#";
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = result.displayPath || result.exportPath || result.fallbackPath || "";
      head.appendChild(link);
      section.appendChild(head);

      const body = document.createElement("pre");
      body.className = "reference-raw-body";
      body.textContent = result.error ? `${refText("loadError")}${result.error}` : result.text;
      section.appendChild(body);
      wrap.appendChild(section);
    }
  }

  function refreshReference() {
    applyReferenceStrings();
    buildReferenceGroupChips();
    buildSourceChips();
    renderReferenceList();
    renderReferenceRows();
    renderReferenceRaw(REF_STATE.selectedTable);
  }

  function maybeLoadReference() {
    if (document.body.dataset.activeView === "reference" || window.location.hash === "#reference") {
      ensureReferenceIndex();
    }
  }

  function bindReferenceEvents() {
    const reset = ref$("#reference-reset");
    if (reset) reset.addEventListener("click", resetReferenceFilters);
    const q = ref$("#reference-q");
    if (q) q.addEventListener("input", () => {
      renderReferenceList();
      renderReferenceRows();
    });
    document.querySelectorAll(".view-tab").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.view === "reference") setTimeout(maybeLoadReference, 0);
      });
    });
    window.addEventListener("hashchange", () => setTimeout(maybeLoadReference, 0));
    window.addEventListener("webui:ui-locale-changed", refreshReference);
    window.addEventListener("webui:language-changed", () => {
      resetReferenceData();
      applyReferenceStrings();
      setTimeout(maybeLoadReference, 0);
    });
  }

  function initReference() {
    ensureReferencePanelToggle();
    applyReferenceStrings();
    bindReferenceEvents();
    maybeLoadReference();
  }

  initReference();
})();
