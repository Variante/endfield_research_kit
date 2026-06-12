(() => {
  const REF_TEXTS = {
    zh: {
      tab: "\u53c2\u8003",
      title: "\u6587\u672c\u53c2\u8003",
      countLabel: "\u5f20\u8868",
      search: "\u641c\u7d22\u8868 / ID / \u6587\u672c",
      source: "\u6765\u6e90",
      all: "\u5168\u90e8",
      empty: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u5f20\u8868",
      loading: "\u52a0\u8f7d\u4e2d...",
      loadError: "\u52a0\u8f7d\u5931\u8d25: ",
      tables: "\u5f20\u8868",
      rows: "\u884c",
      texts: "\u6587\u672c",
      noRows: "\u6ca1\u6709\u5339\u914d\u6587\u672c",
      showingFirst: "\u663e\u793a\u524d",
      contentMatch: "\u5185\u5bb9\u5339\u914d",
    },
    en: {
      tab: "Reference",
      title: "Text Reference",
      countLabel: "tables",
      search: "Search table / ID / text",
      source: "Source",
      all: "All",
      empty: "Select a table",
      loading: "Loading...",
      loadError: "Load failed: ",
      tables: "tables",
      rows: "rows",
      texts: "texts",
      noRows: "No matching text",
      showingFirst: "Showing first",
      contentMatch: "content match",
    },
  };
  const ROW_RENDER_LIMIT = 500;
  const { $, escapeHtml, textIncludes } = window.WebUI;
  const REF_STATE = {
    index: null,
    tables: [],
    selectedTable: null,
    selectedPayload: null,
    tableCache: new Map(),
    tableLoads: new Map(),
    contentMatches: new Map(),
    contentScansDone: new Set(),
    contentScanTimer: 0,
    contentScanKey: "",
    contentScanToken: 0,
    loadingIndex: null,
    sourceFilters: new Set(),
  };

  const ref$ = $;

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

  function referenceTableKey(table) {
    return [
      table && table.source ? table.source : "",
      table && table.table ? table.table : "",
      table && table.file ? table.file : "",
    ].join("\u0000");
  }

  function referenceSearchKey(q, source) {
    return `${source || ""}\u0000${q || ""}`;
  }

  async function fetchReferenceJson(relativePath) {
    const res = await fetch(referenceDataPath(relativePath));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
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

  function applyReferenceStrings() {
    const labels = [
      ["#reference-tab", "tab"],
      ["#reference-title", "title"],
      ["#reference-count-label", "countLabel"],
      ["#reference-source-label", "source"],
      ["#reference-empty", "empty"],
      ["#reference-list-unit", "tables"],
    ];
    for (const [sel, key] of labels) {
      const node = ref$(sel);
      if (node) node.textContent = refText(key);
    }
    const q = ref$("#reference-q");
    if (q) q.placeholder = refText("search");
  }

  async function ensureReferenceIndex() {
    if (REF_STATE.index) return REF_STATE.index;
    if (REF_STATE.loadingIndex) return REF_STATE.loadingIndex;

    REF_STATE.loadingIndex = fetch(referenceDataPath("index.json"))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        REF_STATE.index = payload || {};
        REF_STATE.tables = Array.isArray(payload && payload.tables) ? payload.tables : [];
        REF_STATE.loadingIndex = null;
        buildSourceChips();
        renderReferenceList();
        return REF_STATE.index;
      })
      .catch((error) => {
        REF_STATE.loadingIndex = null;
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
    REF_STATE.tableCache.clear();
    REF_STATE.tableLoads.clear();
    REF_STATE.contentMatches.clear();
    REF_STATE.contentScansDone.clear();
    clearTimeout(REF_STATE.contentScanTimer);
    REF_STATE.contentScanTimer = 0;
    REF_STATE.contentScanKey = "";
    REF_STATE.contentScanToken += 1;
    REF_STATE.loadingIndex = null;
    const list = ref$("#reference-list");
    if (list) list.replaceChildren();
    const rows = ref$("#reference-rows");
    if (rows) rows.replaceChildren();
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

  function buildSourceChips() {
    const wrap = ref$("#reference-source-filter");
    if (!wrap) return;
    wrap.replaceChildren();
    const sources = new Map();
    for (const table of REF_STATE.tables) {
      sources.set(table.source || "", table.sourceLabel || table.source || "");
    }
    const available = new Set([...sources.keys()].filter(Boolean));
    for (const value of [...REF_STATE.sourceFilters]) {
      if (!available.has(value)) REF_STATE.sourceFilters.delete(value);
    }
    for (const [source, label] of [...sources.entries()].sort((a, b) => a[1].localeCompare(b[1]))) {
      if (!source) continue;
      const chip = document.createElement("span");
      chip.className = "chip reference-filter-chip";
      chip.dataset.value = source;
      chip.textContent = label || source;
      chip.classList.toggle("on", REF_STATE.sourceFilters.has(source));
      chip.addEventListener("click", () => {
        if (REF_STATE.sourceFilters.has(source)) REF_STATE.sourceFilters.delete(source);
        else REF_STATE.sourceFilters.add(source);
        chip.classList.toggle("on", REF_STATE.sourceFilters.has(source));
        renderReferenceList();
        renderReferenceRows();
      });
      wrap.appendChild(chip);
    }
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

  function tableMatches(table, q, sources, sourceKey) {
    if (sources.size && !sources.has(table.source)) return false;
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

  function renderReferenceList() {
    const list = ref$("#reference-list");
    if (!list) return;
    const q = referenceQuery();
    const sourceKey = sourceFilterKey();
    const rows = filteredTables();
    list.replaceChildren();
    ref$("#reference-count").textContent = String(REF_STATE.tables.length || 0);
    ref$("#reference-shown").textContent = String(rows.length);
    ref$("#reference-total").textContent = String(REF_STATE.tables.length || 0);

    for (const table of rows) {
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
      list.appendChild(button);
    }
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

  function refreshReference() {
    applyReferenceStrings();
    buildSourceChips();
    renderReferenceList();
    renderReferenceRows();
  }

  function maybeLoadReference() {
    if (document.body.dataset.activeView === "reference" || window.location.hash === "#reference") {
      ensureReferenceIndex();
    }
  }

  function bindReferenceEvents() {
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
    applyReferenceStrings();
    bindReferenceEvents();
    maybeLoadReference();
  }

  initReference();
})();
