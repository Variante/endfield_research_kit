(() => {
  const ROW_RENDER_LIMIT = 900;
  const JSON_PREVIEW_CHAR_LIMIT = 260000;
  const HEADER_PREVIEW_BYTES = 4096;
  const FILTER_PANEL_STORAGE_KEY = "game_data_filters_collapsed";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const DATA_TEXTS = {
    zh: {
      tab: "\u6570\u636e",
      title: "\u6e38\u620f\u6570\u636e",
      countLabel: "\u4e2a\u6587\u4ef6",
      search: "\u641c\u7d22\u8def\u5f84 / \u7c7b\u578b / \u5173\u952e\u5b57",
      showFilters: "\u663e\u793a\u7b5b\u9009",
      hideFilters: "\u9690\u85cf\u7b5b\u9009",
      reset: "\u91cd\u7f6e\u7b5b\u9009",
      basicFilters: "\u57fa\u7840\u7b5b\u9009",
      group: "\u5206\u7ec4",
      kind: "\u683c\u5f0f",
      extension: "\u6269\u5c55\u540d",
      sort: "\u6392\u5e8f",
      sortPath: "\u8def\u5f84 (A-Z)",
      sortSizeDesc: "\u6587\u4ef6\u5927\u5c0f\u4ece\u5927\u5230\u5c0f",
      sortSizeAsc: "\u6587\u4ef6\u5927\u5c0f\u4ece\u5c0f\u5230\u5927",
      listUnit: "\u6761",
      empty: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u4e2a\u6570\u636e\u6587\u4ef6",
      noIndex: "\u5c1a\u672a\u6784\u5efa\u6e38\u620f\u6570\u636e\u7d22\u5f15",
      loading: "\u52a0\u8f7d\u4e2d...",
      loadError: "\u52a0\u8f7d\u5931\u8d25: ",
      openRaw: "\u6253\u5f00\u539f\u59cb\u6587\u4ef6",
      file: "\u6587\u4ef6",
      folder: "\u76ee\u5f55",
      prefix: "\u524d\u7f00",
      size: "\u5927\u5c0f",
      signature: "\u6587\u4ef6\u5934",
      hash: "\u54c8\u5e0c",
      duplicateFiles: "\u76f8\u540c\u54c8\u5e0c\u6587\u4ef6",
      parser: "\u89e3\u6790",
      summary: "\u6458\u8981",
      keys: "\u952e",
      rows: "\u884c / \u6761\u76ee",
      samples: "\u6837\u672c",
      preview: "\u9884\u89c8",
      jsonPreview: "JSON \u9884\u89c8",
      binaryPreview: "\u4e8c\u8fdb\u5236\u6587\u4ef6\u5934",
      previewUnavailable: "\u6ca1\u6709\u53ef\u7528\u7684\u9875\u5185\u9884\u89c8",
      truncated: "\u9884\u89c8\u5df2\u622a\u65ad",
      showingFirst: "\u4ec5\u663e\u793a\u524d",
      generated: "\u751f\u6210\u65f6\u95f4",
      sourceRoot: "\u6e90\u76ee\u5f55",
    },
    en: {
      tab: "Data",
      title: "Game Data",
      countLabel: "files",
      search: "Search path / format / keyword",
      showFilters: "Show filters",
      hideFilters: "Hide filters",
      reset: "Reset filters",
      basicFilters: "Basic filters",
      group: "Group",
      kind: "Format",
      extension: "Ext",
      sort: "Sort",
      sortPath: "Path (A-Z)",
      sortSizeDesc: "File size (high to low)",
      sortSizeAsc: "File size (low to high)",
      listUnit: "items",
      empty: "Select a data file",
      noIndex: "Game data index has not been built",
      loading: "Loading...",
      loadError: "Load failed: ",
      openRaw: "Open raw file",
      file: "File",
      folder: "Folder",
      prefix: "Prefix",
      size: "Size",
      signature: "Signature",
      hash: "Hash",
      duplicateFiles: "Same-hash files",
      parser: "Parser",
      summary: "Summary",
      keys: "Keys",
      rows: "Rows / items",
      samples: "Samples",
      preview: "Preview",
      jsonPreview: "JSON preview",
      binaryPreview: "Binary header",
      previewUnavailable: "No in-page preview is available",
      truncated: "Preview truncated",
      showingFirst: "Showing first",
      generated: "Generated",
      sourceRoot: "Source root",
    },
  };

  const {
    $,
    applyTemplate,
    escapeHtml,
    exportDataHref,
    formatNumber,
    normalizeUiLocale,
    storageGet,
    storageSet,
    textIncludes,
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
    collapsedPrefixes: new Set(),
    filters: {
      kinds: new Set(),
      extensions: new Set(),
    },
  };

  const gd$ = $;

  function isMobileLayout() {
    return !!(window.matchMedia && window.matchMedia(MOBILE_LAYOUT_QUERY).matches);
  }

  let gameDataPanel = null;

  function ensureGameDataPanelToggle() {
    if (gameDataPanel) return gameDataPanel;
    gameDataPanel = window.WebUI.filters.createPanelToggle({
      panel: "#game-data-filter-panel",
      toggle: "#game-data-filter-toggle",
      left: "#game-data-left",
      storageKey: FILTER_PANEL_STORAGE_KEY,
      isMobile: isMobileLayout,
      labels: (collapsed) => dataText(collapsed ? "showFilters" : "hideFilters"),
    });
    return gameDataPanel;
  }

  function syncFilterPanel() {
    gameDataPanel?.sync();
  }

  function resolveInitialUiLocale() {
    return normalizeUiLocale(window.WEBUI_UI_LOCALE)
      || (document.documentElement.lang.toLowerCase().startsWith("zh") ? "zh" : "en");
  }

  function dataText(key, replacements = {}) {
    const locale = DATA_TEXTS[STATE.uiLocale] || DATA_TEXTS.en;
    return applyTemplate(locale[key] || DATA_TEXTS.en[key] || key, replacements);
  }

  function gameDataPath(relativePath) {
    return `data/game_data/${String(relativePath || "").replace(/^\/+/, "")}`;
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
    const parts = String(entry && entry.p || "").split("/");
    return parts[parts.length - 1] || "";
  }

  function rawEntryPrefix(entry) {
    return String(entry && (entry.g || entry.d) || "[root]").trim() || "[root]";
  }

  function limitedNamePrefix(value, maxParts) {
    const raw = String(value || "").trim() || "[root]";
    if (raw === "[root]") return raw;
    const parts = raw.split(/[_\-.]+/).filter(Boolean);
    if (parts.length <= maxParts) return raw;
    return parts.slice(0, maxParts).join("_");
  }

  function entryPrefix(entry) {
    const raw = rawEntryPrefix(entry);
    return activeGroupUsesPrefixes() ? limitedNamePrefix(raw, 2) : raw;
  }

  function compactJsonGroupId(groupId) {
    const raw = String(groupId || "").trim();
    const parts = raw.split("/").filter(Boolean);
    if (parts[0] !== "Json" || parts.length <= 2) return raw;
    return parts.slice(0, 2).join("/");
  }

  function addCountMap(target, source) {
    if (!source || typeof source !== "object") return;
    for (const [key, value] of Object.entries(source)) {
      target[key] = (Number(target[key]) || 0) + (Number(value) || 0);
    }
  }

  function coalesceIndexGroups(groups) {
    const byId = new Map();
    for (const group of groups || []) {
      if (!group || typeof group !== "object") continue;
      const id = compactJsonGroupId(group.id) || String(group.id || "");
      let bucket = byId.get(id);
      if (!bucket) {
        bucket = {
          ...group,
          id,
          files: 0,
          bytes: 0,
          extensions: {},
          kinds: {},
          categories: {},
          groupFiles: [],
          groupIds: [],
        };
        byId.set(id, bucket);
      }
      bucket.files += Number(group.files) || 0;
      bucket.bytes += Number(group.bytes) || 0;
      addCountMap(bucket.extensions, group.extensions);
      addCountMap(bucket.kinds, group.kinds);
      addCountMap(bucket.categories, group.categories);
      if (group.id && !bucket.groupIds.includes(group.id)) bucket.groupIds.push(group.id);
      if (group.file && !bucket.groupFiles.includes(group.file)) bucket.groupFiles.push(group.file);
      if (!bucket.file && group.file) bucket.file = group.file;
    }
    return [...byId.values()].sort((a, b) => String(a.id || "").localeCompare(String(b.id || "")));
  }

  function groupDisplayName(groupId) {
    return String(groupId || "").replace(/\//g, " / ");
  }

  function activeGroupUsesPrefixes() {
    const groupId = String(STATE.activeGroup || "");
    if (!groupId) return true;
    return groupId === "Json" || groupId.startsWith("Json/");
  }

  function prefixCollapseKey(prefix) {
    return `${STATE.activeGroup || "[group]"}::${prefix}`;
  }

  function prefixIsCollapsed(prefix) {
    return !queryText() && STATE.collapsedPrefixes.has(prefixCollapseKey(prefix));
  }

  function togglePrefix(prefix) {
    const key = prefixCollapseKey(prefix);
    const nextCollapsed = !STATE.collapsedPrefixes.has(key);
    if (nextCollapsed) STATE.collapsedPrefixes.add(key);
    else STATE.collapsedPrefixes.delete(key);
    if (nextCollapsed && STATE.selected && entryPrefix(STATE.selected) === prefix) {
      STATE.selected = null;
    }
    renderList();
    renderDetail();
  }

  function entrySearchText(entry) {
    return [
      entry.p,
      entry.d,
      entry.g,
      entry.e,
      entry.k,
      entry.q,
      entry.h,
      entry.x,
      entryContentHash(entry),
      aggregatePathSearch(entry),
      Array.isArray(entry.a) ? entry.a.join(" ") : "",
      entry.t,
    ].join(" ").toLowerCase();
  }

  function queryText() {
    const node = gd$("#game-data-q");
    return String(node && node.value || "").trim().toLowerCase();
  }

  function sortMode() {
    const node = gd$("#game-data-sort");
    return String(node && node.value || "path");
  }

  function compareEntries(a, b) {
    const mode = sortMode();
    if (mode === "size-desc") {
      const diff = Number(b.s || 0) - Number(a.s || 0);
      if (diff) return diff;
    } else if (mode === "size-asc") {
      const diff = Number(a.s || 0) - Number(b.s || 0);
      if (diff) return diff;
    }
    return String(a.p || "").localeCompare(String(b.p || ""));
  }

  function compareEntriesForList(a, b) {
    if (activeGroupUsesPrefixes()) {
      const prefixDiff = entryPrefix(a).localeCompare(entryPrefix(b));
      if (prefixDiff) return prefixDiff;
    }
    return compareEntries(a, b);
  }

  function matchesFilters(entry) {
    const q = queryText();
    if (STATE.filters.kinds.size && !STATE.filters.kinds.has(String(entry.k || ""))) return false;
    if (STATE.filters.extensions.size && !STATE.filters.extensions.has(String(entry.e || ""))) return false;
    if (q && !entrySearchText(entry).includes(q)) return false;
    return true;
  }

  function countBy(entries, keyFn) {
    const counts = {};
    for (const entry of entries || []) {
      const key = keyFn(entry);
      counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
  }

  function buildChipSet(selector, values, activeSet, counts, onChange) {
    window.WebUI.filters.buildChips(selector, values, {
      active: activeSet,
      className: "game-data-filter-chip",
      count: counts,
      onToggle: () => onChange(),
    });
  }

  function applyStrings() {
    const labels = [
      ["#game-data-tab", "tab"],
      ["#game-data-title", "title"],
      ["#game-data-count-label", "countLabel"],
      ["#game-data-basic-filter-label", "basicFilters"],
      ["#game-data-group-label", "group"],
      ["#game-data-kind-label", "kind"],
      ["#game-data-extension-label", "extension"],
      ["#game-data-sort-label", "sort"],
      ["#game-data-sort-path", "sortPath"],
      ["#game-data-sort-size-desc", "sortSizeDesc"],
      ["#game-data-sort-size-asc", "sortSizeAsc"],
      ["#game-data-list-meta-label", "listUnit"],
    ];
    for (const [selector, key] of labels) {
      const node = gd$(selector);
      if (node) node.textContent = dataText(key);
    }
    const q = gd$("#game-data-q");
    if (q) q.placeholder = dataText("search");
    const reset = gd$("#game-data-reset");
    if (reset) reset.textContent = dataText("reset");
    syncFilterPanel();
    if (!STATE.selected) {
      const empty = gd$("#game-data-empty");
      if (empty) empty.textContent = STATE.index ? dataText("empty") : dataText("noIndex");
    }
  }

  async function ensureIndex() {
    if (STATE.index) return STATE.index;
    if (STATE.loadingIndex) return STATE.loadingIndex;

    window.WebUI.showLoader("game-data");
    STATE.loadingIndex = window.WebUI.fetchWithProgress(gameDataPath("index.json"), {
      onProgress: (ratio) => window.WebUI.updateLoader("game-data", ratio == null ? null : ratio * 0.75),
    })
      .then((res) => {
        if (res.status === 404) {
          return { missing: true, groups: [], counts: { files: 0, bytes: 0 } };
        }
        if (!res.ok) throw new Error(`game_data/index.json HTTP ${res.status}`);
        return res.json();
      })
      .then(async (payload) => {
        STATE.index = payload || {};
        STATE.groups = coalesceIndexGroups(Array.isArray(payload && payload.groups) ? payload.groups : []);
        buildGroupChips();
        renderSummary();
        window.WebUI.updateLoader("game-data", 0.85);
        await window.WebUI.nextPaint();
        await loadGroup(STATE.activeGroup);
        window.WebUI.updateLoader("game-data", 1);
        window.WebUI.hideLoader("game-data");
        return STATE.index;
      })
      .catch((error) => {
        window.WebUI.hideLoader("game-data");
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
  function activeGroupIds() {
    const active = String(STATE.activeGroup || "");
    if (active) return [active];
    return STATE.groups.map((group) => String(group.id || "")).filter(Boolean);
  }

  function activeGroupCacheKey() {
    return String(STATE.activeGroup || "") || "[unfiltered]";
  }

  function entryContentHash(entry) {
    return String(entry && (entry.hash || entry.sha256 || entry.H || "") || "").trim();
  }

  function aggregateFileRecord(entry) {
    return {
      p: String(entry && entry.p || ""),
      d: String(entry && entry.d || ""),
      g: String(entry && entry.g || ""),
      e: String(entry && entry.e || ""),
    };
  }

  function aggregateFiles(entry) {
    if (Array.isArray(entry && entry.sameHashFiles) && entry.sameHashFiles.length) return entry.sameHashFiles;
    const file = aggregateFileRecord(entry || {});
    return file.p ? [file] : [];
  }

  function duplicateFileCount(entry) {
    return aggregateFiles(entry).length;
  }

  function aggregatePathSearch(entry) {
    return aggregateFiles(entry)
      .map((file) => [file.p, file.d, file.g, file.e].filter(Boolean).join(" "))
      .join(" ");
  }

  function aggregatePathSummary(entry, limit = 18) {
    const paths = aggregateFiles(entry).map((file) => file.p).filter(Boolean);
    if (paths.length <= limit) return paths.join(", ");
    return `${paths.slice(0, limit).join(", ")} ... +${formatNumber(paths.length - limit)}`;
  }

  function aggregateEntriesByHash(entries) {
    const result = [];
    const byHash = new Map();
    for (const entry of entries || []) {
      const hash = entryContentHash(entry);
      if (!hash) {
        result.push(entry);
        continue;
      }
      const file = aggregateFileRecord(entry);
      const existing = byHash.get(hash);
      if (!existing) {
        const copy = { ...entry, sameHashFiles: file.p ? [file] : [], fileCount: file.p ? 1 : 0 };
        byHash.set(hash, copy);
        result.push(copy);
        continue;
      }
      if (file.p && !existing.sameHashFiles.some((item) => item.p === file.p)) {
        existing.sameHashFiles.push(file);
        existing.fileCount = existing.sameHashFiles.length;
      }
      if (!String(existing.p || "") && entry.p) existing.p = entry.p;
    }
    return result;
  }

  function buildGroupChips() {
    const available = new Set(STATE.groups.map((group) => String(group.id || "")).filter(Boolean));
    if (STATE.activeGroup && !available.has(String(STATE.activeGroup || ""))) STATE.activeGroup = "";
    const items = STATE.groups.map((group) => {
      const value = String(group.id || "");
      return { value, label: groupDisplayName(value), count: group.files, title: groupDisplayName(value) };
    });
    window.WebUI.filters.buildChips("#game-data-group-filter", items, {
      active: String(STATE.activeGroup || ""),
      single: true,
      className: "game-data-filter-chip game-data-group-chip",
      onToggle: (next) => {
        STATE.activeGroup = next;
        buildGroupChips();
        loadGroup(STATE.activeGroup);
      },
    });
  }
  function groupFileList(group) {
    const files = Array.isArray(group && group.groupFiles) ? group.groupFiles.filter(Boolean) : [];
    if (files.length) return files;
    return group && group.file ? [group.file] : [];
  }

  async function fetchGroupPayload(file) {
    const res = await fetch(gameDataPath(file));
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
    const loadedGroups = [];
    const seenFiles = new Set();
    const groupFiles = [];
    for (const id of groupIds) {
      const group = activeGroupInfo(id);
      if (!group) continue;
      loadedGroups.push(id);
      for (const file of groupFileList(group)) {
        if (!file || seenFiles.has(file)) continue;
        seenFiles.add(file);
        groupFiles.push(file);
      }
    }
    if (!groupFiles.length) {
      setGroupEntries([]);
      return null;
    }

    const isCurrentRequest = () => activeGroupCacheKey() === cacheKey;
    STATE.loadingGroupKey = cacheKey;
    window.WebUI.showLoader("game-data", dataText("loading"));
    window.WebUI.updateLoader("game-data", groupFiles.length === 1 ? 0.1 : null);
    STATE.loadingGroup = Promise.all(groupFiles.map(fetchGroupPayload))
      .then(async (payloads) => {
        const entries = [];
        for (const payload of payloads) {
          if (Array.isArray(payload && payload.entries)) entries.push(...payload.entries);
        }
        const payload = groupFiles.length === 1
          ? (payloads[0] || {})
          : { entries, groups: loadedGroups, files: groupFiles };
        STATE.loadedGroups.set(cacheKey, payload || {});
        if (isCurrentRequest()) window.WebUI.updateLoader("game-data", 0.9);
        await window.WebUI.nextPaint();
        if (isCurrentRequest()) {
          setGroupEntries(entries);
          window.WebUI.updateLoader("game-data", 1);
          window.WebUI.hideLoader("game-data");
        }
        return payload;
      })
      .catch((error) => {
        if (isCurrentRequest()) {
          window.WebUI.hideLoader("game-data");
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
    STATE.entries = aggregateEntriesByHash(entries);
    STATE.selected = null;
    populateEntryFilters();
    applyFilters();
    renderDetail();
  }

  function populateEntryFilters() {
    const kindCounts = countBy(STATE.entries, (entry) => String(entry.k || "unknown"));
    const extensionCounts = countBy(STATE.entries, (entry) => String(entry.e || "[none]"));
    buildChipSet(
      "#game-data-kind-filter",
      Object.keys(kindCounts).sort(),
      STATE.filters.kinds,
      kindCounts,
      applyFilters,
    );
    buildChipSet(
      "#game-data-extension-filter",
      Object.keys(extensionCounts).sort(),
      STATE.filters.extensions,
      extensionCounts,
      applyFilters,
    );
  }

  function resetFilters() {
    const q = gd$("#game-data-q");
    if (q) q.value = "";
    const sort = gd$("#game-data-sort");
    if (sort) sort.value = "path";
    STATE.activeGroup = "";
    STATE.filters.kinds.clear();
    STATE.filters.extensions.clear();
    buildGroupChips();
    if (STATE.index) {
      loadGroup("");
    } else {
      STATE.entries = [];
      STATE.filtered = [];
      populateEntryFilters();
      applyFilters();
    }
  }

  function syncFilterSectionActiveCounts() {
    window.WebUI.setFilterSectionActiveCounts?.({
      "game-data-basic": queryText() ? 1 : 0,
      "game-data-group": STATE.activeGroup ? 1 : 0,
      "game-data-kind": STATE.filters.kinds.size,
      "game-data-extension": STATE.filters.extensions.size,
      "game-data-sort-section": sortMode() === "path" ? 0 : 1,
    });
  }

  function renderSummary() {
    const counts = STATE.index && STATE.index.counts || {};
    const group = activeGroupInfo();
    gd$("#game-data-count").textContent = formatNumber(counts.files || 0) || "0";
    const meta = [];
    if (STATE.index && STATE.index.sourceRoot) meta.push(`${dataText("sourceRoot")}: ${STATE.index.sourceRoot}`);
    if (STATE.index && STATE.index.generated) {
      meta.push(`${dataText("generated")}: ${new Date(Number(STATE.index.generated) * 1000).toLocaleString()}`);
    }
    if (group) meta.push(`${groupDisplayName(group.id)}: ${formatNumber(group.files)} / ${formatBytes(group.bytes)}`);
    const metaNode = gd$("#game-data-run-meta");
    if (metaNode) metaNode.textContent = meta.join(" | ");
  }

  function applyFilters() {
    syncFilterSectionActiveCounts();
    STATE.filtered = STATE.entries.filter(matchesFilters).sort(compareEntriesForList);
    if (STATE.selected && !STATE.filtered.includes(STATE.selected)) {
      STATE.selected = null;
    }
    renderSummary();
    renderList();
    renderDetail();
  }

  function renderPrefixHeading(prefix, count, collapsed) {
    const heading = document.createElement("button");
    heading.type = "button";
    heading.className = "game-data-prefix-heading group" + (collapsed ? "" : " expanded");
    heading.dataset.prefix = prefix;
    heading.setAttribute("aria-expanded", String(!collapsed));
    heading.innerHTML =
      `<span class="twisty">${collapsed ? "&gt;" : "v"}</span>` +
      `<span class="group-main">` +
        `<span class="label mono" title="${escapeHtml(prefix)}">${escapeHtml(prefix)}</span>` +
      `</span>` +
      `<span class="group-count">${formatNumber(count)}</span>`;
    heading.addEventListener("click", () => togglePrefix(prefix));
    return heading;
  }

  function renderEntryRow(entry) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "game-data-row";
    button.classList.toggle("is-selected", STATE.selected === entry);
    const fileCount = duplicateFileCount(entry);
    const duplicateBadge = fileCount > 1
      ? `<span class="game-data-kind-badge">${formatNumber(fileCount)} ${escapeHtml(dataText("countLabel"))}</span>`
      : "";
    const pathText = fileCount > 1
      ? `${entry.p || ""} (+${formatNumber(fileCount - 1)})`
      : (entry.p || "");
    const hash = entryContentHash(entry);
    button.innerHTML =
      `<div class="game-data-row-head">` +
        `<span class="game-data-row-name">${escapeHtml(entryName(entry))}</span>` +
        `<span class="game-data-kind-badge">${escapeHtml(entry.k || "")}</span>` +
        duplicateBadge +
      `</div>` +
      `<div class="game-data-row-path">${escapeHtml(pathText)}</div>` +
      `<div class="game-data-row-meta">${escapeHtml([entry.d, entry.e, formatBytes(entry.s), hash ? hash.slice(0, 12) : "", entry.h].filter(Boolean).join(" | "))}</div>`;
    button.addEventListener("click", () => {
      STATE.selected = entry;
      renderList();
      renderDetail();
    });
    return button;
  }
  function renderList() {
    const list = gd$("#game-data-list");
    if (!list) return;
    list.replaceChildren();
    gd$("#game-data-shown").textContent = formatNumber(STATE.filtered.length) || "0";
    gd$("#game-data-total").textContent = formatNumber(STATE.entries.length) || "0";

    const fragment = document.createDocumentFragment();
    let renderedEntries = 0;
    let totalVisibleEntries = 0;

    if (activeGroupUsesPrefixes()) {
      const sections = [];
      let current = null;
      for (const entry of STATE.filtered) {
        const prefix = entryPrefix(entry);
        if (!current || current.prefix !== prefix) {
          current = { prefix, entries: [] };
          sections.push(current);
        }
        current.entries.push(entry);
      }

      for (const section of sections) {
        const collapsed = prefixIsCollapsed(section.prefix);
        fragment.appendChild(renderPrefixHeading(section.prefix, section.entries.length, collapsed));
        if (collapsed) continue;
        totalVisibleEntries += section.entries.length;
        for (const entry of section.entries) {
          if (renderedEntries >= ROW_RENDER_LIMIT) continue;
          fragment.appendChild(renderEntryRow(entry));
          renderedEntries += 1;
        }
      }
    } else {
      totalVisibleEntries = STATE.filtered.length;
      for (const entry of STATE.filtered.slice(0, ROW_RENDER_LIMIT)) {
        fragment.appendChild(renderEntryRow(entry));
        renderedEntries += 1;
      }
    }

    if (totalVisibleEntries > renderedEntries) {
      const note = document.createElement("div");
      note.className = "game-data-list-note";
      note.textContent = `${dataText("showingFirst")} ${formatNumber(renderedEntries)} / ${formatNumber(totalVisibleEntries)}`;
      fragment.appendChild(note);
    }
    list.appendChild(fragment);
  }

  function factRow(label, value, { mono = false } = {}) {
    if (value === undefined || value === null || value === "") return "";
    return `<div class="game-data-fact"><span>${escapeHtml(label)}</span><b class="${mono ? "mono" : ""}">${escapeHtml(value)}</b></div>`;
  }

  function renderDetail() {
    const detail = gd$("#game-data-detail");
    const empty = gd$("#game-data-empty");
    const entry = STATE.selected;
    if (!detail || !empty) return;
    if (!entry) {
      detail.hidden = true;
      empty.hidden = false;
      empty.textContent = STATE.index ? dataText("empty") : dataText("noIndex");
      return;
    }

    empty.hidden = true;
    detail.hidden = false;
    gd$("#game-data-detail-title").textContent = entryName(entry);
    const fileCount = duplicateFileCount(entry);
    gd$("#game-data-detail-meta").textContent = [entry.k, entry.q, entry.e, formatBytes(entry.s), fileCount > 1 ? `${formatNumber(fileCount)} ${dataText("countLabel")}` : ""].filter(Boolean).join(" | ");
    const rawHref = exportDataHref(entry.p);
    const rawLink = gd$("#game-data-open-raw");
    if (rawLink) rawLink.href = rawHref;
    gd$("#game-data-detail-facts").innerHTML = [
      factRow(dataText("file"), entry.p, { mono: true }),
      fileCount > 1 ? factRow(dataText("duplicateFiles"), aggregatePathSummary(entry, 48), { mono: true }) : "",
      factRow(dataText("folder"), entry.d),
      factRow(dataText("prefix"), entry.g),
      factRow(dataText("size"), formatBytes(entry.s)),
      factRow(dataText("parser"), [entry.k, entry.q].filter(Boolean).join(" / ")),
      factRow(dataText("hash"), entryContentHash(entry), { mono: true }),
      factRow(dataText("signature"), entry.x, { mono: true }),
      factRow(dataText("summary"), entry.h),
      factRow(dataText("rows"), entry.r),
      factRow(dataText("keys"), Array.isArray(entry.a) ? entry.a.join(", ") : ""),
      factRow(dataText("samples"), entry.t),
    ].filter(Boolean).join("");
    renderPreview(entry);
  }

  function decodeText(buffer) {
    const bytes = new Uint8Array(buffer);
    if (bytes[0] === 0xff && bytes[1] === 0xfe) return new TextDecoder("utf-16le").decode(bytes.slice(2));
    if (bytes[0] === 0xfe && bytes[1] === 0xff) return new TextDecoder("utf-16be").decode(bytes.slice(2));
    return new TextDecoder("utf-8").decode(bytes);
  }

  async function renderJsonPreview(entry, wrap) {
    wrap.innerHTML = `<div class="game-data-preview-label">${escapeHtml(dataText("jsonPreview"))}</div><pre class="game-data-preview-pre">${escapeHtml(dataText("loading"))}</pre>`;
    const pre = wrap.querySelector("pre");
    try {
      const res = await fetch(exportDataHref(entry.p));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const text = decodeText(await res.arrayBuffer());
      const formatted = JSON.stringify(JSON.parse(text), null, 2);
      const truncated = formatted.length > JSON_PREVIEW_CHAR_LIMIT;
      pre.textContent = truncated ? formatted.slice(0, JSON_PREVIEW_CHAR_LIMIT) : formatted;
      if (truncated) {
        const note = document.createElement("div");
        note.className = "game-data-preview-note";
        note.textContent = dataText("truncated");
        wrap.appendChild(note);
      }
    } catch (error) {
      pre.textContent = dataText("loadError") + (error && error.message ? error.message : String(error));
    }
  }

  function hexDump(bytes) {
    const rows = [];
    const limit = Math.min(bytes.length, 512);
    for (let offset = 0; offset < limit; offset += 16) {
      const slice = bytes.slice(offset, Math.min(offset + 16, limit));
      const hex = Array.from(slice).map((byte) => byte.toString(16).padStart(2, "0").toUpperCase()).join(" ");
      const ascii = Array.from(slice).map((byte) => (byte >= 32 && byte < 127) ? String.fromCharCode(byte) : ".").join("");
      rows.push(`${offset.toString(16).padStart(8, "0")}  ${hex.padEnd(47, " ")}  ${ascii}`);
    }
    return rows.join("\n");
  }

  function extractAscii(bytes) {
    const decoder = new TextDecoder("ascii");
    const text = decoder.decode(bytes);
    const matches = text.match(/[\x20-\x7e]{5,}/g) || [];
    return [...new Set(matches.map((item) => item.trim()).filter(Boolean))].slice(0, 12);
  }

  async function renderBinaryPreview(entry, wrap) {
    wrap.innerHTML = `<div class="game-data-preview-label">${escapeHtml(dataText("binaryPreview"))}</div><pre class="game-data-preview-pre">${escapeHtml(dataText("loading"))}</pre>`;
    const pre = wrap.querySelector("pre");
    try {
      const res = await fetch(exportDataHref(entry.p), {
        headers: { Range: `bytes=0-${HEADER_PREVIEW_BYTES - 1}` },
      });
      if (!res.ok && res.status !== 206) throw new Error(`HTTP ${res.status}`);
      const bytes = new Uint8Array(await res.arrayBuffer());
      const strings = extractAscii(bytes);
      pre.textContent = hexDump(bytes) + (strings.length ? `\n\nASCII strings:\n${strings.join("\n")}` : "");
    } catch (error) {
      pre.textContent = dataText("loadError") + (error && error.message ? error.message : String(error));
    }
  }


  function renderPreview(entry) {
    const wrap = gd$("#game-data-preview");
    if (!wrap) return;
    wrap.replaceChildren();
    if (entry.k === "text-json") {
      renderJsonPreview(entry, wrap);
    } else {
      renderBinaryPreview(entry, wrap);
    }
  }

  function showError(error) {
    const detail = gd$("#game-data-detail");
    const empty = gd$("#game-data-empty");
    if (detail) detail.hidden = true;
    if (empty) {
      empty.hidden = false;
      empty.textContent = dataText("loadError") + (error && error.message ? error.message : String(error));
    }
  }

  function maybeLoadGameData() {
    if (document.body.dataset.activeView === "game-data" || window.location.hash === "#game-data") {
      ensureIndex();
    }
  }

  function bindEvents() {
    const reset = gd$("#game-data-reset");
    if (reset) reset.addEventListener("click", resetFilters);
    const q = gd$("#game-data-q");
    if (q) q.addEventListener("input", applyFilters);
    const sort = gd$("#game-data-sort");
    if (sort) sort.addEventListener("change", applyFilters);
    document.querySelectorAll(".view-tab").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.view === "game-data") setTimeout(maybeLoadGameData, 0);
      });
    });
    window.addEventListener("hashchange", () => setTimeout(maybeLoadGameData, 0));
    window.addEventListener("webui:view-changed", (event) => {
      if (event.detail && event.detail.view === "game-data") maybeLoadGameData();
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
    ensureGameDataPanelToggle();
    applyStrings();
    bindEvents();
    maybeLoadGameData();
  }

  init();
})();
