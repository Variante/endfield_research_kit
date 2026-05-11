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

  function referenceSearchKey(q, source) {
    return `${source || ""}\u0000${q || ""}`;
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
    return !!(matches && matches.has(table.file));
  }

  async function loadReferencePayload(table) {
    const cached = REF_STATE.tableCache.get(table.file);
    if (cached) return cached;

    const pending = REF_STATE.tableLoads.get(table.file);
    if (pending) return pending;

    const promise = fetch(referenceDataPath(table.file))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        REF_STATE.tableCache.set(table.file, payload);
        REF_STATE.tableLoads.delete(table.file);
        return payload;
      })
      .catch((error) => {
        REF_STATE.tableLoads.delete(table.file);
        throw error;
      });

    REF_STATE.tableLoads.set(table.file, promise);
    return promise;
  }

  function applyReferenceStrings() {
    const labels = [
      ["#reference-tab", "tab"],
      ["#reference-title", "title"],
      ["#reference-count-label", "countLabel"],
      ["#reference-source-label", "source"],
      ["#reference-source-all", "all"],
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
        buildSourceSelect();
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

  function buildSourceSelect() {
    const select = ref$("#reference-source");
    if (!select) return;
    const current = select.value;
    select.replaceChildren();
    const all = document.createElement("option");
    all.id = "reference-source-all";
    all.value = "";
    all.textContent = refText("all");
    select.appendChild(all);
    const sources = new Map();
    for (const table of REF_STATE.tables) {
      sources.set(table.source || "", table.sourceLabel || table.source || "");
    }
    for (const [source, label] of [...sources.entries()].sort((a, b) => a[1].localeCompare(b[1]))) {
      if (!source) continue;
      const option = document.createElement("option");
      option.value = source;
      option.textContent = label || source;
      select.appendChild(option);
    }
    select.value = [...select.options].some((option) => option.value === current) ? current : "";
  }

  function referenceQuery() {
    const q = ref$("#reference-q");
    return String(q && q.value || "").trim().toLowerCase();
  }

  function sourceFilter() {
    const source = ref$("#reference-source");
    return String(source && source.value || "");
  }

  function tableMatches(table, q, source) {
    if (source && table.source !== source) return false;
    if (!q) return true;
    return tableMetadataMatches(table, q) || tableContentMatches(table, q, source);
  }

  function scheduleReferenceContentScan(q, source) {
    if (!q || !REF_STATE.tables.length) return;

    const key = referenceSearchKey(q, source);
    if (REF_STATE.contentScansDone.has(key) || REF_STATE.contentScanKey === key) return;

    clearTimeout(REF_STATE.contentScanTimer);
    REF_STATE.contentScanTimer = setTimeout(() => {
      scanReferenceContent(q, source, key);
    }, 180);
  }

  async function scanReferenceContent(q, source, key) {
    const token = REF_STATE.contentScanToken + 1;
    REF_STATE.contentScanToken = token;
    REF_STATE.contentScanKey = key;

    const matches = REF_STATE.contentMatches.get(key) || new Set();
    REF_STATE.contentMatches.set(key, matches);

    const tables = REF_STATE.tables.filter((table) => !source || table.source === source);
    let cursor = 0;
    let renderQueued = false;

    const queueRender = () => {
      if (renderQueued) return;
      renderQueued = true;
      setTimeout(() => {
        renderQueued = false;
        if (REF_STATE.contentScanKey === key && referenceSearchKey(referenceQuery(), sourceFilter()) === key) {
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
            matches.add(table.file);
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
    const source = sourceFilter();
    scheduleReferenceContentScan(q, source);
    return REF_STATE.tables.filter((table) => tableMatches(table, q, source));
  }

  function renderReferenceList() {
    const list = ref$("#reference-list");
    if (!list) return;
    const q = referenceQuery();
    const source = sourceFilter();
    const rows = filteredTables();
    list.replaceChildren();
    ref$("#reference-count").textContent = String(REF_STATE.tables.length || 0);
    ref$("#reference-shown").textContent = String(rows.length);
    ref$("#reference-total").textContent = String(REF_STATE.tables.length || 0);

    for (const table of rows) {
      const contentOnlyMatch = q
        && !tableMetadataMatches(table, q)
        && tableContentMatches(table, q, source);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "reference-table-row";
      button.classList.toggle(
        "is-selected",
        !!(REF_STATE.selectedTable && REF_STATE.selectedTable.file === table.file),
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
      if (!REF_STATE.selectedTable || REF_STATE.selectedTable.file !== table.file) return;
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
    buildSourceSelect();
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
    const source = ref$("#reference-source");
    if (source) source.addEventListener("change", renderReferenceList);
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
