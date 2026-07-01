(() => {
  const ROW_RENDER_LIMIT = 900;
  const JSON_PREVIEW_CHAR_LIMIT = 360000;
  const FILTER_PANEL_STORAGE_KEY = "decoded_browser_filters_collapsed";
  const RAW_JSON_VISIBLE_STORAGE_KEY = "decoded_raw_json_visible";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const TEXTS = {
    zh: {
      tab: "\u89e3\u7801",
      title: "\u89e3\u7801\u6587\u4ef6",
      countLabel: "\u4e2a\u6587\u4ef6",
      search: "\u641c\u7d22\u8bed\u4e49\u57df / \u6a21\u5f0f / \u7c7b / \u524d\u7f00 / \u8def\u5f84",
      showFilters: "\u663e\u793a\u7b5b\u9009",
      hideFilters: "\u9690\u85cf\u7b5b\u9009",
      reset: "\u91cd\u7f6e\u7b5b\u9009",
      basicFilters: "\u57fa\u7840\u7b5b\u9009",
      group: "\u5206\u7ec4",
      source: "\u6765\u6e90",
      type: "\u7c7b\u578b",
      status: "\u72b6\u6001",
      managedClass: "\u6258\u7ba1\u7c7b",
      sort: "\u6392\u5e8f",
      sortName: "\u540d\u79f0 (A-Z)",
      sortSizeDesc: "\u6587\u4ef6\u5927\u5c0f\u4ece\u5927\u5230\u5c0f",
      sortSizeAsc: "\u6587\u4ef6\u5927\u5c0f\u4ece\u5c0f\u5230\u5927",
      sortStatus: "\u72b6\u6001",
      listUnit: "\u6761",
      empty: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u4e2a\u89e3\u7801\u6587\u4ef6",
      selectGroup: "\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a\u89e3\u7801\u5206\u7ec4",
      noIndex: "\u5c1a\u672a\u6784\u5efa\u89e3\u7801\u6587\u4ef6\u7d22\u5f15",
      loading: "\u52a0\u8f7d\u4e2d...",
      loadError: "\u52a0\u8f7d\u5931\u8d25: ",
      openJson: "\u6253\u5f00 JSON",
      structure: "\u7ed3\u6784",
      rawJson: "\u539f\u59cb JSON",
      showRawJson: "\u663e\u793a\u539f\u59cb JSON",
      prefix: "\u6587\u4ef6\u524d\u7f00",
      filenameStem: "\u6587\u4ef6\u540d",
      meaning: "\u8bed\u4e49",
      domain: "\u8bed\u4e49\u57df",
      schema: "\u6a21\u5f0f",
      schemaKind: "\u6a21\u5f0f\u6765\u6e90",
      fieldSet: "\u5b57\u6bb5\u96c6",
      fieldSetId: "\u5b57\u6bb5\u96c6 ID",
      tags: "\u6807\u7b7e",
      format: "\u6570\u636e\u683c\u5f0f",
      metadata: "$animestudio",
      unityFields: "Unity fields",
      managedRefs: "references.RefIds",
      managedRefsEmpty: "\u6ca1\u6709\u6258\u7ba1\u5f15\u7528",
      topFields: "\u9876\u5c42\u5b57\u6bb5",
      file: "\u6587\u4ef6",
      folder: "\u76ee\u5f55",
      size: "\u5927\u5c0f",
      rawSize: "\u539f\u59cb\u5b57\u8282",
      pathId: "PathID",
      pathIdHex: "\u6587\u4ef6 PathID",
      sourceFile: "\u6e90 AssetBundle",
      chunk: "VFS chunk",
      registry: "\u5f15\u7528\u8868",
      refCount: "\u5f15\u7528\u6570",
      flags: "\u6807\u8bb0",
      classes: "\u6258\u7ba1\u7c7b",
      layouts: "\u5e03\u5c40",
      fields: "\u5b57\u6bb5",
      error: "\u9519\u8bef",
      generated: "\u751f\u6210\u65f6\u95f4",
      sourceRoot: "\u6e90\u76ee\u5f55",
      showingFirst: "\u4ec5\u663e\u793a\u524d",
      truncated: "\u9884\u89c8\u5df2\u622a\u65ad",
      copiedPath: "\u5df2\u590d\u5236\u8def\u5f84",
    },
    en: {
      tab: "Decoded",
      title: "Decoded Files",
      countLabel: "files",
      search: "Search domain / schema / class / prefix / path",
      showFilters: "Show filters",
      hideFilters: "Hide filters",
      reset: "Reset filters",
      basicFilters: "Basic filters",
      group: "Group",
      source: "Source",
      type: "Type",
      status: "Status",
      managedClass: "Managed class",
      sort: "Sort",
      sortName: "Name (A-Z)",
      sortSizeDesc: "File size (high to low)",
      sortSizeAsc: "File size (low to high)",
      sortStatus: "Status",
      listUnit: "items",
      empty: "Select a decoded file",
      selectGroup: "Select a decoded group first",
      noIndex: "Decoded index has not been built",
      loading: "Loading...",
      loadError: "Load failed: ",
      openJson: "Open JSON",
      structure: "Structure",
      rawJson: "Raw JSON",
      showRawJson: "Show raw JSON",
      prefix: "Filename prefix",
      filenameStem: "Filename stem",
      meaning: "Semantic meaning",
      domain: "Semantic domain",
      schema: "Schema",
      schemaKind: "Schema source",
      fieldSet: "Field set",
      fieldSetId: "Field set ID",
      tags: "Tags",
      format: "Data format",
      metadata: "$animestudio",
      unityFields: "Unity fields",
      managedRefs: "references.RefIds",
      managedRefsEmpty: "No managed references",
      topFields: "Top-level fields",
      file: "File",
      folder: "Folder",
      size: "Size",
      rawSize: "Raw bytes",
      pathId: "PathID",
      pathIdHex: "Filename PathID",
      sourceFile: "Source AssetBundle",
      chunk: "VFS chunk",
      registry: "Registry",
      refCount: "Reference count",
      flags: "Markers",
      classes: "Managed classes",
      layouts: "Layouts",
      fields: "Fields",
      error: "Error",
      generated: "Generated",
      sourceRoot: "Source root",
      showingFirst: "Showing first",
      truncated: "Preview truncated",
      copiedPath: "Path copied",
    },
  };

  const {
    $,
    applyTemplate,
    escapeHtml,
    exportFullHref,
    formatNumber,
    normalizeUiLocale,
  } = window.WebUI;

  const STATE = {
    uiLocale: "zh",
    index: null,
    groups: [],
    activeGroup: "",
    loadedGroups: new Map(),
    loadingIndex: null,
    loadingGroup: null,
    loadingGroupKey: "",
    entries: [],
    filtered: [],
    selected: null,
    filters: {
      sources: new Set(),
      types: new Set(),
      statuses: new Set(),
      classes: new Set(),
    },
    detailToken: 0,
    showRawJson: false,
  };

  const dec$ = $;
  let decodedPanel = null;

  function isMobileLayout() {
    return !!(window.matchMedia && window.matchMedia(MOBILE_LAYOUT_QUERY).matches);
  }

  function ensureDecodedPanelToggle() {
    if (decodedPanel) return decodedPanel;
    decodedPanel = window.WebUI.filters.createPanelToggle({
      panel: "#decoded-filter-panel",
      toggle: "#decoded-filter-toggle",
      left: "#decoded-left",
      storageKey: FILTER_PANEL_STORAGE_KEY,
      isMobile: isMobileLayout,
      labels: (collapsed) => text(collapsed ? "showFilters" : "hideFilters"),
    });
    return decodedPanel;
  }

  function resolveInitialUiLocale() {
    return normalizeUiLocale(window.WEBUI_UI_LOCALE)
      || (document.documentElement.lang.toLowerCase().startsWith("zh") ? "zh" : "en");
  }

  function text(key, replacements = {}) {
    const locale = TEXTS[STATE.uiLocale] || TEXTS.en;
    return applyTemplate(locale[key] || TEXTS.en[key] || key, replacements);
  }

  function decodedDataPath(relativePath) {
    return `data/decoded/${String(relativePath || "").replace(/^\/+/, "")}`;
  }

  function readStoredBool(key, fallback = false) {
    try {
      const value = window.localStorage && window.localStorage.getItem(key);
      if (value === "1") return true;
      if (value === "0") return false;
    } catch (_) {
      return fallback;
    }
    return fallback;
  }

  function writeStoredBool(key, value) {
    try {
      if (window.localStorage) window.localStorage.setItem(key, value ? "1" : "0");
    } catch (_) {
      // Ignore private-mode or file:// storage failures.
    }
  }

  function formatBytes(bytes) {
    let value = Number(bytes || 0);
    const units = ["B", "KiB", "MiB", "GiB", "TiB"];
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit += 1;
    }
    const digits = unit === 0 ? 0 : value >= 10 ? 1 : 2;
    return `${value.toFixed(digits)} ${units[unit]}`;
  }

  function entryName(entry) {
    return String(entry && (entry.name || entry.file || "") || "");
  }

  function groupDisplayName(groupId) {
    const parts = String(groupId || "").split("/").filter(Boolean);
    if (parts.length <= 3) return parts.join(" / ");
    return `${parts[0]} / ${parts[1]} / ${parts[2]} / ${parts.slice(3).join("/")}`;
  }

  function queryText() {
    const node = dec$("#decoded-q");
    return String(node && node.value || "").trim().toLowerCase();
  }

  function sortMode() {
    const node = dec$("#decoded-sort");
    return String(node && node.value || "name");
  }

  function arrayText(values) {
    return Array.isArray(values) ? values.join(" ") : "";
  }

  function flagsText(flags) {
    if (!flags || typeof flags !== "object") return "";
    return Object.entries(flags)
      .map(([key, value]) => `${key}:${value}`)
      .join(" ");
  }

  function entrySearchText(entry) {
    return [
      entry.p,
      entry.source,
      entry.type,
      entry.file,
      entry.name,
      entry.filenameStem,
      entry.prefix,
      entry.family,
      entry.meaning,
      entry.domain,
      entry.schemaKind,
      entry.schema,
      entry.schemaGroup,
      entry.fieldSet,
      entry.fieldSetId,
      entry.status,
      entry.registry,
      entry.pathId,
      entry.pathIdHex,
      entry.sourceFile,
      entry.chunk,
      entry.error,
      arrayText(entry.classes),
      arrayText(entry.layouts),
      arrayText(entry.fields),
      arrayText(entry.tags),
      flagsText(entry.flags),
    ].join(" ").toLowerCase();
  }

  function matchesFilters(entry) {
    const q = queryText();
    if (STATE.filters.sources.size && !STATE.filters.sources.has(String(entry.source || ""))) return false;
    if (STATE.filters.types.size && !STATE.filters.types.has(String(entry.type || ""))) return false;
    if (STATE.filters.statuses.size && !STATE.filters.statuses.has(String(entry.status || ""))) return false;
    if (STATE.filters.classes.size) {
      const classes = new Set(Array.isArray(entry.classes) ? entry.classes : []);
      let found = false;
      for (const item of STATE.filters.classes) {
        if (classes.has(item)) {
          found = true;
          break;
        }
      }
      if (!found) return false;
    }
    if (q && !entrySearchText(entry).includes(q)) return false;
    return true;
  }

  function compareEntries(a, b) {
    const mode = sortMode();
    if (mode === "size-desc") {
      const diff = Number(b.size || 0) - Number(a.size || 0);
      if (diff) return diff;
    } else if (mode === "size-asc") {
      const diff = Number(a.size || 0) - Number(b.size || 0);
      if (diff) return diff;
    } else if (mode === "status") {
      const diff = String(a.status || "").localeCompare(String(b.status || ""));
      if (diff) return diff;
    }
    return entryName(a).localeCompare(entryName(b)) || String(a.p || "").localeCompare(String(b.p || ""));
  }

  function buildChipSet(selector, values, activeSet, counts, onChange) {
    window.WebUI.filters.buildChips(selector, values, {
      active: activeSet,
      className: "decoded-filter-chip",
      count: counts,
      onToggle: () => onChange(),
    });
  }

  function countBy(entries, valuesFn) {
    const counts = {};
    for (const entry of entries || []) {
      const values = valuesFn(entry);
      const list = Array.isArray(values) ? values : [values];
      for (const value of list) {
        const key = String(value || "");
        if (!key) continue;
        counts[key] = (counts[key] || 0) + 1;
      }
    }
    return counts;
  }

  function tagList(entry) {
    return Array.isArray(entry && entry.tags) ? entry.tags.join(", ") : "";
  }

  function syncRawVisibility() {
    const show = !!STATE.showRawJson;
    const toggle = dec$("#decoded-show-raw");
    const panel = dec$("#decoded-json-panel");
    const body = dec$("#decoded-detail-body");
    const pre = dec$("#decoded-json");
    if (toggle) toggle.checked = show;
    if (panel) panel.hidden = !show;
    if (body) body.classList.toggle("raw-hidden", !show);
    if (!show && pre) pre.textContent = "";
  }

  function applyStrings() {
    const labels = [
      ["#decoded-tab", "tab"],
      ["#decoded-title", "title"],
      ["#decoded-count-label", "countLabel"],
      ["#decoded-basic-filter-label", "basicFilters"],
      ["#decoded-group-label", "group"],
      ["#decoded-source-label", "source"],
      ["#decoded-type-label", "type"],
      ["#decoded-status-label", "status"],
      ["#decoded-class-label", "managedClass"],
      ["#decoded-sort-label", "sort"],
      ["#decoded-sort-name", "sortName"],
      ["#decoded-sort-size-desc", "sortSizeDesc"],
      ["#decoded-sort-size-asc", "sortSizeAsc"],
      ["#decoded-sort-status", "sortStatus"],
      ["#decoded-list-meta-label", "listUnit"],
      ["#decoded-structure-label", "structure"],
      ["#decoded-json-label", "rawJson"],
      ["#decoded-show-raw-label", "showRawJson"],
    ];
    for (const [selector, key] of labels) {
      const node = dec$(selector);
      if (node) node.textContent = text(key);
    }
    const q = dec$("#decoded-q");
    if (q) q.placeholder = text("search");
    const reset = dec$("#decoded-reset");
    if (reset) reset.textContent = text("reset");
    const raw = dec$("#decoded-open-raw");
    if (raw) raw.textContent = text("openJson");
    syncRawVisibility();
    decodedPanel?.sync();
    if (!STATE.selected) {
      const empty = dec$("#decoded-empty");
      if (empty) empty.textContent = emptyDetailText();
    }
  }

  async function ensureIndex() {
    if (STATE.index) return STATE.index;
    if (STATE.loadingIndex) return STATE.loadingIndex;

    window.WebUI.showLoader("decoded");
    STATE.loadingIndex = window.WebUI.fetchWithProgress(decodedDataPath("index.json"), {
      onProgress: (ratio) => window.WebUI.updateLoader("decoded", ratio == null ? null : ratio * 0.75),
    })
      .then((res) => {
        if (res.status === 404) return { missing: true, groups: [], counts: { files: 0, bytes: 0 } };
        if (!res.ok) throw new Error(`decoded/index.json HTTP ${res.status}`);
        return res.json();
      })
      .then(async (payload) => {
        STATE.index = payload || {};
        STATE.groups = Array.isArray(payload && payload.groups)
          ? payload.groups.slice().sort((a, b) => String(a.id || "").localeCompare(String(b.id || "")))
          : [];
        buildGroupChips();
        renderSummary();
        window.WebUI.updateLoader("decoded", 0.85);
        await window.WebUI.nextPaint();
        await loadGroup(STATE.activeGroup);
        window.WebUI.updateLoader("decoded", 1);
        window.WebUI.hideLoader("decoded");
        return STATE.index;
      })
      .catch((error) => {
        window.WebUI.hideLoader("decoded");
        showError(error);
        return null;
      })
      .finally(() => {
        STATE.loadingIndex = null;
      });
    return STATE.loadingIndex;
  }

  function activeGroupInfo(groupId = STATE.activeGroup) {
    return STATE.groups.find((group) => group.id === groupId) || null;
  }

  function indexRequiresGroupSelection() {
    if (!STATE.index) return false;
    if (STATE.index.requiresGroupSelection) return true;
    const count = Number(STATE.index.counts && STATE.index.counts.files || 0);
    const limit = Number(STATE.index.autoLoadAllLimit || 50000);
    return count > limit;
  }

  function activeGroupIds() {
    const active = String(STATE.activeGroup || "");
    if (active) return [active];
    if (indexRequiresGroupSelection()) return [];
    return STATE.groups.map((group) => String(group.id || "")).filter(Boolean);
  }

  function activeGroupCacheKey() {
    return String(STATE.activeGroup || "") || "[unfiltered]";
  }

  function emptyDetailText() {
    if (!STATE.index) return text("noIndex");
    if (indexRequiresGroupSelection() && !STATE.activeGroup) return text("selectGroup");
    return text("empty");
  }

  function buildGroupChips() {
    const available = new Set(STATE.groups.map((group) => String(group.id || "")).filter(Boolean));
    if (STATE.activeGroup && !available.has(String(STATE.activeGroup || ""))) STATE.activeGroup = "";
    const items = STATE.groups.map((group) => {
      const value = String(group.id || "");
      return { value, label: groupDisplayName(value), count: group.files, title: groupDisplayName(value) };
    });
    window.WebUI.filters.buildChips("#decoded-group-filter", items, {
      active: String(STATE.activeGroup || ""),
      single: true,
      className: "decoded-filter-chip decoded-group-chip",
      onToggle: (next) => {
        STATE.activeGroup = next;
        buildGroupChips();
        loadGroup(STATE.activeGroup);
      },
    });
  }

  function groupFileList(group) {
    return group && group.file ? [group.file] : [];
  }

  async function fetchGroupPayload(file) {
    const res = await fetch(decodedDataPath(file));
    if (!res.ok) throw new Error(`${file} HTTP ${res.status}`);
    return res.json();
  }

  async function loadGroup(groupId) {
    STATE.activeGroup = String(groupId || "");
    const cacheKey = activeGroupCacheKey();
    const cached = STATE.loadedGroups.get(cacheKey);
    if (cached) {
      setGroupEntries(cached.entries || []);
      return cached;
    }
    if (STATE.loadingGroup && STATE.loadingGroupKey === cacheKey) return STATE.loadingGroup;

    const groupIds = activeGroupIds();
    const groupFiles = [];
    for (const id of groupIds) {
      const group = activeGroupInfo(id);
      for (const file of groupFileList(group)) {
        if (file) groupFiles.push(file);
      }
    }
    if (!groupFiles.length) {
      setGroupEntries([]);
      return null;
    }

    const isCurrentRequest = () => activeGroupCacheKey() === cacheKey;
    STATE.loadingGroupKey = cacheKey;
    window.WebUI.showLoader("decoded", text("loading"));
    window.WebUI.updateLoader("decoded", groupFiles.length === 1 ? 0.1 : null);
    STATE.loadingGroup = Promise.all(groupFiles.map(fetchGroupPayload))
      .then(async (payloads) => {
        const entries = [];
        for (const payload of payloads) {
          if (Array.isArray(payload && payload.entries)) entries.push(...payload.entries);
        }
        const payload = groupFiles.length === 1 ? (payloads[0] || {}) : { entries, files: groupFiles };
        STATE.loadedGroups.set(cacheKey, payload || {});
        if (isCurrentRequest()) window.WebUI.updateLoader("decoded", 0.9);
        await window.WebUI.nextPaint();
        if (isCurrentRequest()) {
          setGroupEntries(entries);
          window.WebUI.updateLoader("decoded", 1);
          window.WebUI.hideLoader("decoded");
        }
        return payload;
      })
      .catch((error) => {
        if (isCurrentRequest()) {
          window.WebUI.hideLoader("decoded");
          showError(error);
        }
        return null;
      })
      .finally(() => {
        if (STATE.loadingGroupKey === cacheKey) {
          STATE.loadingGroup = null;
          STATE.loadingGroupKey = "";
        }
      });
    return STATE.loadingGroup;
  }

  function setGroupEntries(entries) {
    STATE.entries = entries || [];
    STATE.selected = null;
    populateEntryFilters();
    applyFilters();
    renderDetail();
  }

  function populateEntryFilters() {
    const sourceCounts = countBy(STATE.entries, (entry) => entry.source);
    const typeCounts = countBy(STATE.entries, (entry) => entry.type);
    const statusCounts = countBy(STATE.entries, (entry) => entry.status);
    const classCounts = countBy(STATE.entries, (entry) => Array.isArray(entry.classes) ? entry.classes : []);
    buildChipSet("#decoded-source-filter", Object.keys(sourceCounts).sort(), STATE.filters.sources, sourceCounts, applyFilters);
    buildChipSet("#decoded-type-filter", Object.keys(typeCounts).sort(), STATE.filters.types, typeCounts, applyFilters);
    buildChipSet("#decoded-status-filter", Object.keys(statusCounts).sort(), STATE.filters.statuses, statusCounts, applyFilters);
    buildChipSet("#decoded-class-filter", Object.keys(classCounts).sort().slice(0, 120), STATE.filters.classes, classCounts, applyFilters);
  }

  function resetFilters() {
    const q = dec$("#decoded-q");
    if (q) q.value = "";
    const sort = dec$("#decoded-sort");
    if (sort) sort.value = "name";
    STATE.activeGroup = "";
    STATE.filters.sources.clear();
    STATE.filters.types.clear();
    STATE.filters.statuses.clear();
    STATE.filters.classes.clear();
    buildGroupChips();
    if (STATE.index) loadGroup("");
    else {
      STATE.entries = [];
      STATE.filtered = [];
      populateEntryFilters();
      applyFilters();
    }
  }

  function syncFilterSectionActiveCounts() {
    window.WebUI.setFilterSectionActiveCounts?.({
      "decoded-basic": queryText() ? 1 : 0,
      "decoded-group": STATE.activeGroup ? 1 : 0,
      "decoded-source": STATE.filters.sources.size,
      "decoded-type": STATE.filters.types.size,
      "decoded-status": STATE.filters.statuses.size,
      "decoded-class": STATE.filters.classes.size,
      "decoded-sort-section": sortMode() === "name" ? 0 : 1,
    });
  }

  function countSummary(counts, key, limit = 6) {
    const values = counts && counts[key] || {};
    return Object.entries(values)
      .sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0) || String(a[0]).localeCompare(String(b[0])))
      .slice(0, limit)
      .map(([name, count]) => `${name} ${formatNumber(count)}`)
      .join(", ");
  }

  function renderSummary() {
    const counts = STATE.index && STATE.index.counts || {};
    const group = activeGroupInfo();
    const countNode = dec$("#decoded-count");
    if (countNode) countNode.textContent = formatNumber(counts.files || 0) || "0";
    const meta = [];
    if (STATE.index && STATE.index.sourceRoot) meta.push(`${text("sourceRoot")}: ${STATE.index.sourceRoot}`);
    if (STATE.index && STATE.index.generated) {
      meta.push(`${text("generated")}: ${new Date(Number(STATE.index.generated) * 1000).toLocaleString()}`);
    }
    const typeSummary = countSummary(counts, "types");
    if (typeSummary) meta.push(typeSummary);
    const domainSummary = countSummary(counts, "domains", 4);
    if (domainSummary) meta.push(domainSummary);
    const schemaSummary = countSummary(counts, "schemas", 3);
    if (schemaSummary) meta.push(schemaSummary);
    const statusSummary = countSummary(counts, "statuses");
    if (statusSummary) meta.push(statusSummary);
    if (group) meta.push(`${groupDisplayName(group.id)}: ${formatNumber(group.files)} / ${formatBytes(group.bytes)}`);
    const metaNode = dec$("#decoded-run-meta");
    if (metaNode) metaNode.textContent = meta.join(" | ");
  }

  function applyFilters() {
    syncFilterSectionActiveCounts();
    STATE.filtered = STATE.entries.filter(matchesFilters).sort(compareEntries);
    if (STATE.selected && !STATE.filtered.includes(STATE.selected)) STATE.selected = null;
    renderSummary();
    renderList();
    renderDetail();
  }

  function statusClass(status) {
    return String(status || "unknown").replace(/[^a-z0-9_-]+/ig, "-").toLowerCase();
  }

  function renderEntryRow(entry) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "decoded-row";
    button.classList.toggle("is-selected", STATE.selected === entry);
    const classes = Array.isArray(entry.classes) ? entry.classes.slice(0, 3).join(" / ") : "";
    const prefix = entry.prefix || entry.family || "";
    const meaning = entry.meaning || "";
    const semanticLine = [entry.domain, entry.schema || entry.fieldSet, meaning].filter(Boolean).join(" · ");
    button.innerHTML =
      `<div class="decoded-row-head">` +
        `<span class="decoded-row-name">${escapeHtml(entryName(entry))}</span>` +
        `<span class="decoded-status-badge decoded-status-${escapeHtml(statusClass(entry.status))}">${escapeHtml(entry.status || "")}</span>` +
        `<span class="decoded-kind-badge">${escapeHtml(entry.type || "")}</span>` +
      `</div>` +
      (semanticLine ? `<div class="decoded-row-meaning">${escapeHtml(semanticLine)}</div>` : "") +
      `<div class="decoded-row-path">${escapeHtml(entry.p || "")}</div>` +
      `<div class="decoded-row-meta">${escapeHtml([entry.source, prefix, entry.schemaKind, formatBytes(entry.size), classes].filter(Boolean).join(" | "))}</div>`;
    button.addEventListener("click", () => {
      STATE.selected = entry;
      renderList();
      renderDetail();
    });
    return button;
  }
  function renderList() {
    const list = dec$("#decoded-list");
    if (!list) return;
    list.replaceChildren();
    dec$("#decoded-shown").textContent = formatNumber(STATE.filtered.length) || "0";
    dec$("#decoded-total").textContent = formatNumber(STATE.entries.length) || "0";
    const fragment = document.createDocumentFragment();
    const rendered = STATE.filtered.slice(0, ROW_RENDER_LIMIT);
    for (const entry of rendered) fragment.appendChild(renderEntryRow(entry));
    if (STATE.filtered.length > rendered.length) {
      const note = document.createElement("div");
      note.className = "decoded-list-note";
      note.textContent = `${text("showingFirst")} ${formatNumber(rendered.length)} / ${formatNumber(STATE.filtered.length)}`;
      fragment.appendChild(note);
    }
    list.appendChild(fragment);
  }

  function factRow(label, value, { mono = false } = {}) {
    if (value === undefined || value === null || value === "") return "";
    return `<div class="decoded-fact"><span>${escapeHtml(label)}</span><b class="${mono ? "mono" : ""}">${escapeHtml(value)}</b></div>`;
  }

  function detailFlags(entry) {
    return flagsText(entry && entry.flags);
  }

  function renderDetail() {
    const detail = dec$("#decoded-detail");
    const empty = dec$("#decoded-empty");
    const entry = STATE.selected;
    if (!detail || !empty) return;
    STATE.detailToken += 1;
    if (!entry) {
      detail.hidden = true;
      empty.hidden = false;
      empty.textContent = emptyDetailText();
      return;
    }

    empty.hidden = true;
    detail.hidden = false;
    dec$("#decoded-detail-title").textContent = entryName(entry);
    dec$("#decoded-detail-meta").textContent = [entry.status, entry.type, entry.source, entry.domain, entry.schema || entry.fieldSet, entry.prefix || entry.family, formatBytes(entry.size)].filter(Boolean).join(" | ");
    const rawLink = dec$("#decoded-open-raw");
    if (rawLink) rawLink.href = exportFullHref(entry.p);
    syncRawVisibility();
    dec$("#decoded-detail-facts").innerHTML = [
      factRow(text("meaning"), entry.meaning),
      factRow(text("domain"), entry.domain),
      factRow(text("schema"), entry.schema),
      factRow(text("schemaKind"), entry.schemaKind),
      factRow(text("fieldSet"), entry.fieldSet),
      factRow(text("fieldSetId"), entry.fieldSetId, { mono: true }),
      factRow(text("tags"), tagList(entry)),
      factRow(text("prefix"), entry.prefix || entry.family),
      factRow(text("filenameStem"), entry.filenameStem, { mono: true }),
      factRow(text("file"), entry.p, { mono: true }),
      factRow(text("source"), entry.source),
      factRow(text("type"), entry.type),
      factRow(text("status"), entry.status),
      factRow(text("size"), formatBytes(entry.size)),
      factRow(text("rawSize"), entry.rawSize ? formatBytes(entry.rawSize) : ""),
      factRow(text("pathId"), entry.pathId, { mono: true }),
      factRow(text("pathIdHex"), entry.pathIdHex, { mono: true }),
      factRow(text("sourceFile"), entry.sourceFile, { mono: true }),
      factRow(text("chunk"), entry.chunk, { mono: true }),
      factRow(text("registry"), entry.registry),
      factRow(text("refCount"), entry.refCount != null ? formatNumber(entry.refCount) : ""),
      factRow(text("flags"), detailFlags(entry), { mono: true }),
      factRow(text("classes"), Array.isArray(entry.classes) ? entry.classes.join(", ") : ""),
      factRow(text("layouts"), Array.isArray(entry.layouts) ? entry.layouts.join(", ") : ""),
      factRow(text("fields"), Array.isArray(entry.fields) ? entry.fields.join(", ") : ""),
      factRow(text("error"), entry.error),
    ].filter(Boolean).join("");
    renderDecodedJson(entry, STATE.detailToken);
  }

  function decodeText(buffer) {
    const bytes = new Uint8Array(buffer);
    if (bytes[0] === 0xff && bytes[1] === 0xfe) return new TextDecoder("utf-16le").decode(bytes.slice(2));
    if (bytes[0] === 0xfe && bytes[1] === 0xff) return new TextDecoder("utf-16be").decode(bytes.slice(2));
    return new TextDecoder("utf-8").decode(bytes);
  }

  function markerBadge(label, value) {
    if (!value) return "";
    return `<span class="decoded-marker-badge">${escapeHtml(label)}${value === true ? "" : ` ${escapeHtml(value)}`}</span>`;
  }

  function dataMarkers(data) {
    if (!data || typeof data !== "object") return "";
    return [
      markerBadge("decoded", data.$decoded),
      markerBadge("partial", data.$partial),
      markerBadge("unparsed", data.$unparsed),
      markerBadge("heuristic", data.$heuristic),
    ].filter(Boolean).join("");
  }

  function refTypeLabel(ref) {
    const typeInfo = ref && ref.type;
    if (!typeInfo || typeof typeInfo !== "object") return "";
    return [typeInfo.ns, typeInfo.class].filter(Boolean).join(".") || String(typeInfo.class || "");
  }

  function renderStructure(payload, entry) {
    const wrap = dec$("#decoded-structure");
    if (!wrap) return;
    wrap.replaceChildren();
    const meta = payload && payload.$animestudio && typeof payload.$animestudio === "object" ? payload.$animestudio : {};
    const refs = payload && payload.references && Array.isArray(payload.references.RefIds) ? payload.references.RefIds : [];
    const fields = payload && typeof payload === "object"
      ? Object.keys(payload).filter((key) => key !== "$animestudio")
      : [];

    const blocks = [];
    blocks.push(
      `<section class="decoded-structure-block">` +
        `<h2>${escapeHtml(text("format"))}</h2>` +
        `<div class="decoded-format-grid">` +
          factRow(text("meaning"), entry.meaning) +
          factRow(text("domain"), entry.domain) +
          factRow(text("schema"), entry.schema) +
          factRow(text("fieldSet"), entry.fieldSet) +
          factRow(text("fieldSetId"), entry.fieldSetId, { mono: true }) +
          factRow(text("tags"), tagList(entry)) +
          factRow(text("prefix"), entry.prefix || entry.family) +
          factRow(text("metadata"), meta.type ? `${meta.type} / classId ${meta.classId ?? ""}` : "$animestudio") +
          factRow(text("unityFields"), fields.join(", ")) +
          factRow(text("managedRefs"), refs.length ? `${formatNumber(refs.length)} RefIds` : text("managedRefsEmpty")) +
        `</div>` +
      `</section>`
    );
    if (Object.keys(meta).length) {
      blocks.push(
        `<section class="decoded-structure-block">` +
          `<h2>${escapeHtml(text("metadata"))}</h2>` +
          `<div class="decoded-format-grid">` +
            factRow(text("pathId"), meta.pathId, { mono: true }) +
            factRow(text("sourceFile"), meta.sourceFile, { mono: true }) +
            factRow(text("rawSize"), meta.rawDataLength ? formatBytes(meta.rawDataLength) : "") +
            factRow(text("registry"), entry.registry || "") +
          `</div>` +
        `</section>`
      );
    }
    if (refs.length) {
      const rows = refs.slice(0, 120).map((ref) => {
        const data = ref && ref.data;
        const layout = data && typeof data === "object" ? data.layout : "";
        const remaining = data && typeof data === "object"
          ? (data.remainingRawWordCount ?? (Array.isArray(data.remainingRawWords) ? data.remainingRawWords.length : ""))
          : "";
        return (
          `<div class="decoded-ref-row">` +
            `<div class="decoded-ref-main">` +
              `<span class="decoded-ref-class">${escapeHtml(refTypeLabel(ref))}</span>` +
              `<span class="decoded-ref-rid">${escapeHtml(ref && ref.rid != null ? String(ref.rid) : "")}</span>` +
            `</div>` +
            `<div class="decoded-ref-meta">` +
              dataMarkers(data) +
              (layout ? `<span>${escapeHtml(layout)}</span>` : "") +
              (remaining !== "" ? `<span>raw ${escapeHtml(remaining)}</span>` : "") +
            `</div>` +
          `</div>`
        );
      }).join("");
      const omitted = refs.length > 120
        ? `<div class="decoded-list-note">${escapeHtml(text("showingFirst"))} 120 / ${escapeHtml(formatNumber(refs.length))}</div>`
        : "";
      blocks.push(
        `<section class="decoded-structure-block">` +
          `<h2>${escapeHtml(text("managedRefs"))}</h2>` +
          `<div class="decoded-ref-list">${rows}${omitted}</div>` +
        `</section>`
      );
    }
    wrap.innerHTML = blocks.join("");
  }

  async function renderDecodedJson(entry, token) {
    const pre = dec$("#decoded-json");
    const structure = dec$("#decoded-structure");
    syncRawVisibility();
    if (pre && STATE.showRawJson) pre.textContent = text("loading");
    if (structure) structure.textContent = text("loading");
    try {
      const res = await fetch(exportFullHref(entry.p));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const raw = decodeText(await res.arrayBuffer());
      const payload = JSON.parse(raw);
      if (token !== STATE.detailToken) return;
      renderStructure(payload, entry);
      if (pre && STATE.showRawJson) {
        const truncated = raw.length > JSON_PREVIEW_CHAR_LIMIT;
        pre.textContent = truncated ? raw.slice(0, JSON_PREVIEW_CHAR_LIMIT) : raw;
        if (truncated) pre.textContent += `\n\n[${text("truncated")}]`;
      }
    } catch (error) {
      if (token !== STATE.detailToken) return;
      const message = text("loadError") + (error && error.message ? error.message : String(error));
      if (pre && STATE.showRawJson) pre.textContent = message;
      if (structure) structure.textContent = message;
    }
  }
  function showError(error) {
    const detail = dec$("#decoded-detail");
    const empty = dec$("#decoded-empty");
    if (detail) detail.hidden = true;
    if (empty) {
      empty.hidden = false;
      empty.textContent = text("loadError") + (error && error.message ? error.message : String(error));
    }
  }

  function maybeLoadDecoded() {
    if (document.body.dataset.activeView === "decoded" || window.location.hash === "#decoded") {
      ensureIndex();
    }
  }

  function bindEvents() {
    const reset = dec$("#decoded-reset");
    if (reset) reset.addEventListener("click", resetFilters);
    const q = dec$("#decoded-q");
    if (q) q.addEventListener("input", applyFilters);
    const sort = dec$("#decoded-sort");
    if (sort) sort.addEventListener("change", applyFilters);
    const rawToggle = dec$("#decoded-show-raw");
    if (rawToggle) {
      rawToggle.addEventListener("change", () => {
        STATE.showRawJson = !!rawToggle.checked;
        writeStoredBool(RAW_JSON_VISIBLE_STORAGE_KEY, STATE.showRawJson);
        syncRawVisibility();
        if (STATE.selected) renderDecodedJson(STATE.selected, ++STATE.detailToken);
      });
    }
    document.querySelectorAll(".view-tab").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.view === "decoded") setTimeout(maybeLoadDecoded, 0);
      });
    });
    window.addEventListener("hashchange", () => setTimeout(maybeLoadDecoded, 0));
    window.addEventListener("webui:view-changed", (event) => {
      if (event.detail && event.detail.view === "decoded") maybeLoadDecoded();
    });
    window.addEventListener("webui:ui-locale-changed", (event) => {
      STATE.uiLocale = normalizeUiLocale(event.detail && event.detail.locale) || STATE.uiLocale;
      applyStrings();
      buildGroupChips();
      populateEntryFilters();
      applyFilters();
    });
  }

  function init() {
    STATE.uiLocale = resolveInitialUiLocale();
    STATE.showRawJson = readStoredBool(RAW_JSON_VISIBLE_STORAGE_KEY, false);
    ensureDecodedPanelToggle();
    applyStrings();
    bindEvents();
    maybeLoadDecoded();
  }

  init();
})();
