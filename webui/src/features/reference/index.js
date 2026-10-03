// Text page behavior contract (webui/README.md links here; evidence limits
// are in memory/webui/text.md).
//   * Search plus filter sections basic, group and source. Known row shapes
//     render as rows; every row keeps its raw JSON beside the rendered view,
//     so an unsupported shape stays searchable instead of being dropped.
//   * A row may carry `fields`, rendered above its localized text as
//     Structured fields: maintained label, verbatim exported value, and the
//     owning `table / row` when the builder resolved an exact lookup. A
//     resolved reference whose table is in the index is a button that selects
//     that table and scrolls to the row inside Text; an unresolved one shows
//     `unresolved` and is never linked. Field values join the row search, a
//     table covered by a maintained renderer carries renderer: "structured" in
//     the Text index, and a table with structured fields but no localized text
//     is still listed.
//   * Authored activity/achievement guides use `guide.sections`, with exact
//     references rendered by the same field/link controls. Every guide value
//     is searchable; the shared row pager does not truncate loaded data.
(() => {
  const REF_TEXTS = {
    zh: {
      tab: "\u6587\u672c",
      title: "\u6587\u672c\u8868",
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
      fields: "\u7ed3\u6784\u5b57\u6bb5",
      fieldUnresolved: "\u672a\u89e3\u6790",
      fieldOpenRow: "\u5728\u6587\u672c\u8868\u4e2d\u6253\u5f00",
      fieldRefMissing: "\u672a\u5bfc\u51fa\u6b64\u8868",
      guideAchievement: "成就指南",
      guideActivity: "活动指南",
      guideReward: "奖励明细",
      guideBoundary: "这里展示已配置的目标和奖励；不判断当前开放状态或玩家进度。",
      guideCodes: "条件配置字段",
      guideTexts: "其他本地化文本",
      showingRows: "当前显示",
    },
    en: {
      tab: "Text",
      title: "Text Tables",
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
      fields: "Structured fields",
      fieldUnresolved: "unresolved",
      fieldOpenRow: "Open in Text Tables",
      fieldRefMissing: "table not exported",
      guideAchievement: "Achievement guide",
      guideActivity: "Activity guide",
      guideReward: "Reward breakdown",
      guideBoundary: "Configured targets and rewards; current availability and player progress are not evaluated.",
      guideCodes: "Stored condition fields",
      guideTexts: "Additional localized text",
      showingRows: "Showing",
    },
  };
  const FILTER_PANEL_STORAGE_KEY = "reference_browser_filters_collapsed";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  // The export keeps one effective table set under game/Table (layout v2).
  const RAW_EXPORT_SOURCE_ROOTS = {
    game: "game",
  };
  const {
    $,
    escapeHtml,
    storageGet,
    storageSet,
  } = window.WebUI;
  const REF_STATE = {
    language: "",
    dataGeneration: 0,
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
    facets: null,
    collapsedTablePrefixes: new Set(),
    pager: null,
    rowPager: null,
    rowPagerKey: "",
    // Row id a maintained structured-field reference asked to focus after the
    // next row render. Cleared once the row is scrolled into view.
    focusRowId: "",
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
    return String((select && select.value) || "CN").toUpperCase();
  }

  function referenceDataPath(relativePath, language = REF_STATE.language || currentLanguage()) {
    return dataPath(`reference/${relativePath}`, language);
  }

  function referenceSourceKey() {
    return "game";
  }

  function exportFullPath(parts) {
    return `/export_full/${parts.map((part) => encodeURIComponent(String(part || ""))).join("/")}`;
  }

  function exportTablePath(sourceKey, tableName) {
    const root = RAW_EXPORT_SOURCE_ROOTS[referenceSourceKey(sourceKey)];
    const name = String(tableName || "").trim();
    return root && name ? exportFullPath([root, "Table", name]) : "";
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

  async function fetchReferenceJson(relativePath, language = REF_STATE.language || currentLanguage()) {
    const res = await fetch(referenceDataPath(relativePath, language));
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

  async function fetchRawReferenceJson(relativePath, language) {
    const res = await fetch(referenceDataPath(relativePath, language));
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
    return window.WebUI.queryMatches([
      window.WebUI.linkedFileSearchText(table, referenceSameHashFiles(table)),
      table.label,
      table.table,
      table.source,
      table.sourceLabel,
      tablePrefix(table),
    ], window.WebUI.parseQuery(q));
  }

  function tableContentMatches(table, q, source) {
    const matches = REF_STATE.contentMatches.get(referenceSearchKey(q, source));
    return !!(matches && matches.has(referenceTableKey(table)));
  }

  async function loadReferencePayload(table) {
    const generation = REF_STATE.dataGeneration;
    const language = REF_STATE.language || currentLanguage();
    const cacheKey = referenceTableKey(table);
    const cached = REF_STATE.tableCache.get(cacheKey);
    if (cached) return cached;

    const pending = REF_STATE.tableLoads.get(cacheKey);
    if (pending) return pending;

    const promise = fetchReferenceJson(table.file, language)
      .then(async (payload) => {
        if (payload && payload.baseFile) {
          const basePayload = await fetchReferenceJson(payload.baseFile, language);
          return mergeReferenceOverlay(basePayload, payload);
        }
        return payload;
      })
      .then(async (payload) => {
        await Promise.all([window.WebUI.updateBadges.load("reference"), window.WebUI.updateBadges.loadFiles()]);
        const normalized = applyReferenceTableMetadata(payload, table);
        if (generation === REF_STATE.dataGeneration) {
          REF_STATE.tableCache.set(cacheKey, normalized);
          REF_STATE.tableLoads.delete(cacheKey);
        }
        return normalized;
      })
      .catch((error) => {
        if (generation === REF_STATE.dataGeneration) REF_STATE.tableLoads.delete(cacheKey);
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

  async function loadReferenceI18nMap(sourceKey, language) {
    const generation = REF_STATE.dataGeneration;
    const source = referenceSourceKey(sourceKey);
    const cacheKey = `${language}\u0000${source}`;
    const cached = REF_STATE.i18nCache.get(cacheKey);
    if (cached) return cached;

    const pending = REF_STATE.i18nLoads.get(cacheKey);
    if (pending) return pending;

    const path = exportTablePath(source, `I18nTextTable_${language}.json`);
    const promise = fetchAbsoluteJson(path)
      .catch(() => ({}))
      .then((payload) => {
        const map = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
        if (generation === REF_STATE.dataGeneration) {
          REF_STATE.i18nCache.set(cacheKey, map);
          REF_STATE.i18nLoads.delete(cacheKey);
        }
        return map;
      });
    REF_STATE.i18nLoads.set(cacheKey, promise);
    return promise;
  }

  async function loadReferenceI18nMaps(preferredSource, language) {
    const maps = {};
    await Promise.all(referenceI18nSourceOrder(preferredSource).map(async (source) => {
      maps[source] = await loadReferenceI18nMap(source, language);
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

  async function loadReferenceRawDisplay(file, language) {
    let sourceError = null;
    if (file && file.exportPath) {
      try {
        const payload = await fetchRawExportJson(file.exportPath);
        const maps = await loadReferenceI18nMaps(file.sourceKey, language);
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
      const payload = await fetchRawReferenceJson(file.fallbackPath, language);
      return {
        text: formatRawReferencePayload(bundledRawReferencePayload(payload)),
        displayPath: file.fallbackPath,
        href: referenceDataPath(file.fallbackPath, language),
      };
    }
    throw sourceError || new Error(refText("rawUnavailable"));
  }

  async function loadReferenceRawText(file) {
    const generation = REF_STATE.dataGeneration;
    const language = REF_STATE.language || currentLanguage();
    const cacheKey = JSON.stringify([
      language,
      file && file.sourceKey || "",
      file && file.tableName || "",
      file && file.exportPath || "",
      file && file.fallbackPath || "",
    ]);
    const cached = REF_STATE.rawTextCache.get(cacheKey);
    if (cached != null) return cached;

    const pending = REF_STATE.rawTextLoads.get(cacheKey);
    if (pending) return pending;

    const promise = loadReferenceRawDisplay(file, language)
      .then((display) => {
        if (generation === REF_STATE.dataGeneration) {
          REF_STATE.rawTextCache.set(cacheKey, display);
          REF_STATE.rawTextLoads.delete(cacheKey);
        }
        return display;
      })
      .catch((error) => {
        if (generation === REF_STATE.dataGeneration) REF_STATE.rawTextLoads.delete(cacheKey);
        throw error;
      });

    REF_STATE.rawTextLoads.set(cacheKey, promise);
    return promise;
  }

  function applyReferenceStrings() {
    // #reference-tab is owned by the shared data-i18n loop in app.js
    // (referenceTab in app_labels.js) — not repeated here.
    const labels = [
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

  async function ensureReferenceIndex(language = currentLanguage()) {
    // app.js announces a language only after its Story load completes. Text
    // may already be in use, so the event must not erase the same publication.
    if (language !== REF_STATE.language) resetReferenceData(language);
    if (REF_STATE.index) return REF_STATE.index;
    if (REF_STATE.loadingIndex) return REF_STATE.loadingIndex;

    const generation = REF_STATE.dataGeneration;
    window.WebUI.showLoader("reference");
    REF_STATE.loadingIndex = window.WebUI.fetchWithProgress(referenceDataPath("index.json", language), {
      // Downloading is only part of the work; reserve the last 10% for parsing
      // and rendering so the bar does not sit at 100% while the page is busy.
      onProgress: (ratio) => {
        if (generation === REF_STATE.dataGeneration) window.WebUI.updateLoader("reference", ratio == null ? null : ratio * 0.9);
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        if (generation !== REF_STATE.dataGeneration) return null;
        REF_STATE.index = payload || {};
        REF_STATE.tables = aggregateReferenceTables(Array.isArray(payload && payload.tables) ? payload.tables : []);
        REF_STATE.loadingIndex = null;
        renderReferenceFacets();
        renderReferenceList();
        window.WebUI.updateLoader("reference", 1);
        window.WebUI.hideLoader("reference");
        return REF_STATE.index;
      })
      .catch((error) => {
        if (generation !== REF_STATE.dataGeneration) return null;
        REF_STATE.loadingIndex = null;
        window.WebUI.hideLoader("reference");
        showReferenceError(error);
        return null;
      });
    return REF_STATE.loadingIndex;
  }

  function resetReferenceData(language = currentLanguage()) {
    REF_STATE.language = language;
    REF_STATE.dataGeneration += 1;
    REF_STATE.index = null;
    REF_STATE.tables = [];
    REF_STATE.selectedTable = null;
    REF_STATE.selectedPayload = null;
    referenceFacets().reset({ silent: true, only: ["group"] });
    REF_STATE.tableCache.clear();
    REF_STATE.tableLoads.clear();
    REF_STATE.rawTextCache.clear();
    REF_STATE.rawTextLoads.clear();
    REF_STATE.i18nCache.clear();
    REF_STATE.i18nLoads.clear();
    REF_STATE.contentMatches.clear();
    REF_STATE.contentScansDone.clear();
    REF_STATE.collapsedTablePrefixes.clear();
    REF_STATE.focusRowId = "";
    REF_STATE.rowPagerKey = "";
    REF_STATE.rowPager?.setTotal(0, { reset: true });
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

  // Table-name prefix (single) and export source (multi) chips over the tables.
  function referenceFacets() {
    if (REF_STATE.facets) return REF_STATE.facets;
    REF_STATE.facets = window.WebUI.facets.create({
      countMode: "total", // chip counts are dataset totals, as on every other page
      groups: [
        { id: "group", container: "#reference-group-filter", section: "reference-group",
          values: tablePrefix, title: (prefix) => prefix, single: true,
          className: "reference-group-chip" },
        { id: "source", container: "#reference-source-filter", section: "reference-source",
          values: tableSourceKeys, label: sourceLabel },
      ],
      chipClassName: "reference-filter-chip",
      onChange: () => {
        REF_STATE.pager?.reset();
        renderReferenceList();
        renderReferenceRows();
      },
    });
    return REF_STATE.facets;
  }

  function sourceLabel(source) {
    const table = REF_STATE.tables.find((entry) => entry.source === source);
    return (table && table.sourceLabel) || source;
  }

  function renderReferenceFacets() {
    referenceFacets().render(REF_STATE.tables);
  }

  function resetReferenceFilters() {
    const sort = ref$("#reference-sort");
    if (sort) sort.value = "default";
    const q = ref$("#reference-q");
    if (q) q.value = "";
    clearTimeout(REF_STATE.contentScanTimer);
    REF_STATE.contentScanTimer = 0;
    REF_STATE.contentScanKey = "";
    REF_STATE.contentScanToken += 1;
    referenceFacets().reset();
  }

  function referenceQuery() {
    const q = ref$("#reference-q");
    return String(q && q.value || "").trim().toLowerCase();
  }

  function sourceFilters() {
    return referenceFacets().active("source");
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
    const key = ref$("#reference-sort")?.value || "default";
    if (key === "rows") return Number(b.rows || b.rowCount || 0) - Number(a.rows || a.rowCount || 0);
    if (key === "name") return String(a.label || a.table || "").localeCompare(String(b.label || b.table || ""), undefined, { numeric: true });
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
    if (!referenceFacets().matches(table)) return false;
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
        if (REF_STATE.contentScanToken === token && REF_STATE.contentScanKey === key && referenceSearchKey(referenceQuery(), sourceFilterKey()) === key) {
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
          if (REF_STATE.contentScanToken !== token) return;
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
    });
  }

  function renderReferenceList() {
    const list = ref$("#reference-list");
    if (!list) return;
    const q = referenceQuery();
    syncReferenceFilterSectionActiveCounts();
    const sourceKey = sourceFilterKey();
    const rows = filteredTables().slice().sort(window.WebUI.sorting.comparator("reference-sort", compareReferenceTablesForList));
    REF_STATE.pager?.setTotal(rows.length);
    const pageRows = REF_STATE.pager ? REF_STATE.pager.slice(rows) : rows;
    list.replaceChildren();
    ref$("#reference-count").textContent = String(REF_STATE.tables.length || 0);
    ref$("#reference-shown").textContent = String(rows.length);
    ref$("#reference-total").textContent = String(REF_STATE.tables.length || 0);

    const sections = [];
    let current = null;
    for (const table of pageRows) {
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
    const generation = REF_STATE.dataGeneration;
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
      if (generation !== REF_STATE.dataGeneration || REF_STATE.selectedTable !== table) return;
      REF_STATE.selectedPayload = payload;
      renderReferenceRows();
    } catch (error) {
      if (generation !== REF_STATE.dataGeneration || REF_STATE.selectedTable !== table) return;
      ref$("#reference-detail-meta").textContent =
        refText("loadError") + (error && error.message ? error.message : String(error));
    }
  }

  // --- Maintained structured-field renderer --------------------------------
  // A row payload may carry `fields`, produced by
  // scripts/webui/story/reference_structured_fields.py. Each entry names the
  // raw exported field, its maintained label, the verbatim exported value and,
  // when the builder proved an exact row lookup, a `ref` naming the owning
  // table and row. Nothing here matches by name; an entry with
  // `resolved === false` is shown as unresolved rather than linked.

  function referenceTableByStem(stem) {
    const wanted = `${String(stem || "")}.json`.toLowerCase();
    return REF_STATE.tables.find((table) => String(table.table || "").toLowerCase() === wanted) || null;
  }

  function focusReferenceRow(table, rowId) {
    REF_STATE.focusRowId = String(rowId || "");
    selectReferenceTable(table);
  }

  function applyReferenceRowFocus(wrap) {
    const rowId = REF_STATE.focusRowId;
    if (!rowId || !wrap) return;
    const target = wrap.querySelector(`.reference-row[data-row-id="${CSS.escape(rowId)}"]`);
    REF_STATE.focusRowId = "";
    if (!target) return;
    target.classList.add("is-focused");
    target.scrollIntoView({ block: "center" });
  }

  function renderReferenceFieldValue(field) {
    const node = document.createElement("div");
    node.className = "reference-field-value";
    const ref = field && field.ref;
    const value = String(field?.value ?? "");
    const display = field && field.name ? String(field.name) : value;
    const quantity = field && field.quantity !== undefined ? ` × ${field.quantity}` : "";
    if (!ref) {
      node.textContent = value + quantity;
      return node;
    }
    const target = referenceTableByStem(ref.table);
    const resolved = field.resolved === true;
    if (resolved && target) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "reference-field-link";
      button.title = `${refText("fieldOpenRow")}: ${ref.table} / ${ref.row}`;
      button.textContent = display + quantity;
      button.addEventListener("click", () => focusReferenceRow(target, ref.row));
      node.appendChild(button);
    } else {
      const text = document.createElement("span");
      text.textContent = display + quantity;
      node.appendChild(text);
    }
    const note = document.createElement("span");
    note.className = "reference-field-ref";
    const parts = [`${ref.table} / ${ref.row}`];
    if (value !== String(ref.row || "")) parts.push(value);
    if (!resolved) parts.push(refText("fieldUnresolved"));
    else if (!target) parts.push(refText("fieldRefMissing"));
    note.textContent = parts.join(" | ");
    if (!resolved) note.classList.add("is-unresolved");
    node.appendChild(note);
    return node;
  }

  function renderReferenceFields(item, row) {
    const fields = Array.isArray(row && row.fields) ? row.fields : [];
    if (!fields.length) return;
    const section = document.createElement("div");
    section.className = "reference-fields";

    const heading = document.createElement("div");
    heading.className = "reference-fields-title";
    heading.textContent = refText("fields");
    section.appendChild(heading);

    for (const field of fields) {
      const line = document.createElement("div");
      line.className = "reference-field";
      const label = document.createElement("div");
      label.className = "reference-field-label";
      label.textContent = referenceFieldLabel(field);
      label.title = String(field && field.field || "");
      line.appendChild(label);
      line.appendChild(renderReferenceFieldValue(field));
      section.appendChild(line);
    }
    item.appendChild(section);
  }

  function referenceFieldLabel(field) {
    return String((refLocale() === "zh" && field?.labelZh) || field?.label || field?.field || "");
  }

  function renderReferenceGuide(item, row) {
    const guide = row && row.guide;
    if (!Array.isArray(guide?.sections) || !guide.sections.length) return false;
    const block = document.createElement("div");
    block.className = "reference-guide";
    const heading = document.createElement("div");
    heading.className = "reference-fields-title";
    heading.textContent = refText(guide.kind === "achievement" ? "guideAchievement" : guide.kind === "reward" ? "guideReward" : "guideActivity");
    block.appendChild(heading);
    const note = document.createElement("p");
    note.className = "reference-field-ref";
    note.textContent = refText("guideBoundary");
    block.appendChild(note);
    for (const group of guide.sections) {
      const section = document.createElement("section");
      section.className = "reference-fields reference-guide-section";
      const title = document.createElement("div");
      title.className = "reference-fields-title";
      title.textContent = referenceFieldLabel(group);
      title.title = String(group.path || "");
      section.appendChild(title);
      if (group.title) {
        const description = document.createElement("p");
        description.textContent = group.title;
        section.appendChild(description);
      }
      let technical = null;
      for (const field of group.fields || []) {
        const line = document.createElement("div");
        line.className = "reference-field";
        const label = document.createElement("div");
        label.className = "reference-field-label";
        label.textContent = referenceFieldLabel(field);
        label.title = String(field.field || "");
        line.append(label, renderReferenceFieldValue(field));
        if (field.technical) {
          if (!technical) {
            technical = document.createElement("details");
            const summary = document.createElement("summary");
            summary.textContent = refText("guideCodes");
            technical.appendChild(summary);
            section.appendChild(technical);
          }
          technical.appendChild(line);
        } else {
          section.appendChild(line);
        }
      }
      block.appendChild(section);
    }
    item.appendChild(block);
    return true;
  }

  function ensureReferenceRowPager(wrap) {
    if (REF_STATE.rowPager) return REF_STATE.rowPager;
    const host = document.createElement("div");
    host.id = "reference-row-pager";
    wrap.before(host);
    REF_STATE.rowPager = window.WebUI.pagination.createPager({
      container: host,
      storageKey: "reference_rows_page_size",
      defaultPageSize: 100,
      onChange: renderReferenceRows,
    });
    return REF_STATE.rowPager;
  }

  function referenceRowFieldHaystack(row) {
    const out = [];
    for (const field of (row && row.fields) || []) {
      out.push(field.field, field.label, field.value, field.name);
      if (field.ref) out.push(field.ref.table, field.ref.row);
    }
    for (const section of row?.guide?.sections || []) {
      out.push(section.label, section.labelZh, section.title, section.path);
      for (const field of section.fields || []) {
        out.push(field.field, field.label, field.labelZh, field.value, field.name, field.quantity);
        if (field.ref) out.push(field.ref.table, field.ref.row);
      }
    }
    return out;
  }

  function rowMatches(row, q) {
    const tokens = window.WebUI.parseQuery(q);
    if (!tokens.length) return true;
    const haystack = [row.id, row.title, row.bucket];
    haystack.push(window.WebUI.linkedFileSearchText(row));
    for (const item of row.texts || []) {
      haystack.push(item.field, item.hint, item.path, item.i18nId, item.text);
    }
    haystack.push(...referenceRowFieldHaystack(row));
    return window.WebUI.queryMatches(haystack, tokens);
  }

  function renderReferenceRows() {
    const payload = REF_STATE.selectedPayload;
    const table = REF_STATE.selectedTable;
    if (!payload || !table) return;

    const q = referenceQuery();
    // A row a maintained reference asked to focus stays visible even when the
    // active search would hide it, so following a reference never lands on an
    // empty pane. The filter is otherwise untouched.
    const focusRowId = REF_STATE.focusRowId;
    const rows = (payload.rows || []).filter(
      (row) => rowMatches(row, q) || (focusRowId && String(row.id || "") === focusRowId),
    );
    const wrap = ref$("#reference-rows");
    const pager = ensureReferenceRowPager(wrap);
    const pagerKey = `${table.file}\u0000${q}`;
    pager.setTotal(rows.length, { reset: REF_STATE.rowPagerKey !== pagerKey });
    REF_STATE.rowPagerKey = pagerKey;
    if (focusRowId) pager.showIndex(rows.findIndex((row) => String(row.id || "") === focusRowId));
    const shownRows = pager.slice(rows);
    const metaParts = [
      payload.table || table.table,
      table.sourceLabel || table.source,
      `${rows.length} ${refText("rows")}`,
      `${table.texts || 0} ${refText("texts")}`,
    ];
    if (rows.length > shownRows.length) {
      const start = pager.page * pager.pageSize + 1;
      metaParts.push(`${refText("showingRows")} ${start}–${start + shownRows.length - 1}`);
    }
    ref$("#reference-detail-meta").textContent = metaParts.filter(Boolean).join(" | ");

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
      item.dataset.rowId = String(row.id || "");
      const updateId = `${String(table.table || "").replace(/\.json$/, "")}/${row.id}`;
      item.dataset.updateSource = updateId;
      const title = row.title && row.title !== row.id ? row.title : row.id;
      item.innerHTML =
        `<div class="reference-row-head">` +
          `<span class="reference-row-title">${escapeHtml(title)}${window.WebUI.updateBadges.sourceHtml(updateId)}</span>` +
          `<span class="reference-row-id">${escapeHtml(row.id || "")}</span>` +
        `</div>`;
      const hasGuide = renderReferenceGuide(item, row);
      renderReferenceFields(item, row);
      let textsHost = item;
      if (hasGuide && (row.texts || []).length) {
        textsHost = document.createElement("details");
        const summary = document.createElement("summary");
        summary.textContent = refText("guideTexts");
        textsHost.appendChild(summary);
        item.appendChild(textsHost);
      }
      for (const text of row.texts || []) {
        const textNode = document.createElement("div");
        textNode.className = "reference-text";
        const label = text.hint || text.field || "text";
        textNode.innerHTML =
          `<div class="reference-text-field">${escapeHtml(label)}</div>` +
          `<div class="reference-text-path">${escapeHtml(text.path || "")}${text.i18nId ? " | " + escapeHtml(text.i18nId) : ""}</div>` +
          `<div class="reference-text-body">${escapeHtml(text.text || "")}</div>`;
        textsHost.appendChild(textNode);
      }
      wrap.appendChild(item);
      window.WebUI.updateBadges.decorate(item, "reference", updateId);
      item.insertAdjacentHTML("beforeend", window.WebUI.updateBadges.panel("reference", updateId));
    }
    applyReferenceRowFocus(wrap);
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
    const generation = REF_STATE.dataGeneration;
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
    if (generation !== REF_STATE.dataGeneration || !REF_STATE.selectedTable || referenceTableKey(REF_STATE.selectedTable) !== selectedKey) return;

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
    renderReferenceFacets();
    renderReferenceList();
    renderReferenceRows();
    renderReferenceRaw(REF_STATE.selectedTable);
  }

  function maybeLoadReference(language = currentLanguage()) {
    if (document.body.dataset.activeView === "reference" || window.location.hash === "#reference") {
      ensureReferenceIndex(language);
    }
  }

  function bindReferenceEvents() {
    const reset = ref$("#reference-reset");
    if (reset) reset.addEventListener("click", resetReferenceFilters);
    const q = ref$("#reference-q");
    if (q) q.addEventListener("input", () => {
      REF_STATE.pager?.reset();
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
    window.addEventListener("webui:language-changed", (event) => {
      const language = String(event.detail?.language || currentLanguage()).toUpperCase();
      if (language !== REF_STATE.language) resetReferenceData(language);
      applyReferenceStrings();
      setTimeout(() => {
        if (language === REF_STATE.language) maybeLoadReference(language);
      }, 0);
    });
  }

  function initReference() {
    const sort = document.createElement("select");
    sort.id = "reference-sort";
    const refreshSortLabels = () => {
      const en = window.WEBUI_UI_LOCALE === "en";
      sort.replaceChildren(new Option(en ? "Type and name" : "类型和名称", "default"), new Option(en ? "Name" : "名称", "name"));
    };
    refreshSortLabels();
    ref$("#reference-q")?.parentElement.after(sort);
    sort.addEventListener("change", () => { REF_STATE.pager?.reset(); renderReferenceList(); });
    window.addEventListener("webui:ui-locale-changed", () => { const value = sort.value; refreshSortLabels(); sort.value = value; });
    ensureReferencePanelToggle();
    REF_STATE.pager = window.WebUI.pagination?.createPager({
      container: "#reference-pager",
      storageKey: "reference_browser_page_size",
      onChange: renderReferenceList,
    });
    applyReferenceStrings();
    bindReferenceEvents();
    maybeLoadReference();
  }

  initReference();
})();
