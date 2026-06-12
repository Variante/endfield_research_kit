(() => {
  const UPDATE_TEXTS = {
    zh: {
      tab: "\u66f4\u65b0",
      title: "WebUI \u5185\u5bb9\u66f4\u65b0",
      countLabel: "\u9879\u53d8\u5316",
      search: "\u641c\u7d22\u8def\u5f84 / \u6269\u5c55\u540d",
      gameFile: "\u6e38\u620f\u6587\u4ef6",
      textJson: "\u6587\u672c JSON",
      exportedAsset: "\u5bfc\u51fa\u8d44\u6e90",
      domain: "\u8303\u56f4",
      assetKind: "\u8d44\u6e90\u7c7b\u578b",
      assetPath: "\u8d44\u6e90\u8def\u5f84",
      openAsset: "\u5728\u8d44\u6e90\u9875\u6253\u5f00",
      assetSummary: "\u8d44\u6e90\u53d8\u5316",
      mediaPreview: "\u9884\u89c8",
      mediaComparison: "\u5a92\u4f53\u5bf9\u6bd4",
      previousAsset: "\u65e7\u7248\u672c",
      currentAsset: "\u65b0\u7248\u672c",
      assetFile: "\u8d44\u6e90\u6587\u4ef6",
      oldAssetPath: "\u539f\u5bfc\u51fa\u6587\u4ef6",
      newAssetPath: "\u65b0\u5bfc\u51fa\u6587\u4ef6",
      openFile: "\u6253\u5f00\u6587\u4ef6",
      loadingObjPreview: "\u6b63\u5728\u52a0\u8f7d OBJ \u9884\u89c8...",
      objPreviewUnavailable: "\u65e0\u6cd5\u9884\u89c8\u6b64 OBJ \u6587\u4ef6\u3002",
      objPreviewReady: "{vertices} \u9876\u70b9 / {faces} \u9762",
      visualDiff: "\u5dee\u5f02\u9ad8\u4eae",
      diffLoading: "\u6b63\u5728\u751f\u6210\u5dee\u5f02\u9884\u89c8...",
      diffUnavailable: "\u65e0\u6cd5\u751f\u6210\u5dee\u5f02\u9884\u89c8\u3002",
      diffChanged: "\u7ea6 {percent} \u50cf\u7d20\u53d8\u5316",
      textDiff: "\u6587\u672c\u5dee\u5f02",
      decodedImpact: "\u89e3\u7801\u5f71\u54cd",
      displayImpact: "WebUI \u5f71\u54cd",
      decodedFiles: "\u89e3\u7801\u6587\u4ef6",
      decodedFileCount: "\u89e3\u7801\u6587\u4ef6",
      decodedTags: "\u5173\u8054\u7c7b\u578b",
      decodedExtensions: "\u6269\u5c55\u5206\u5e03",
      decodedTruncated: "\u53e6\u6709 {count} \u4e2a\u89e3\u7801\u6587\u4ef6\u672a\u5728\u6b64\u5217\u51fa\u3002",
      decodedNote: "\u8bf4\u660e",
      decodedConfidence: "\u5339\u914d\u65b9\u5f0f",
      diffTruncated: "\u5dee\u5f02\u8fc7\u957f\uff0c\u5df2\u622a\u65ad\u663e\u793a\u3002",
      status: "\u72b6\u6001",
      category: "\u5206\u7c7b",
      extension: "\u6269\u5c55\u540d",
      sort: "\u6392\u5e8f",
      all: "\u5168\u90e8",
      sortPath: "\u8def\u5f84 (A-Z)",
      sortStatus: "\u72b6\u6001",
      sortSizeDelta: "\u5927\u5c0f\u53d8\u5316",
      sortLineDelta: "\u884c\u6570\u53d8\u5316",
      listUnit: "\u6761",
      added: "\u65b0\u589e",
      modified: "\u4fee\u6539",
      deleted: "\u5220\u9664",
      total: "\u603b\u8ba1",
      empty: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u9879\u53d8\u5316",
      noFeed: "\u5c1a\u672a\u6784\u5efa\u66f4\u65b0\u6458\u8981",
      baselineReady: "\u5df2\u5efa\u7acb\u57fa\u7ebf\uff1b\u540e\u7eed\u6587\u672c JSON \u6216\u8d44\u6e90\u53d8\u5316\u4f1a\u663e\u793a\u5728\u8fd9\u91cc\u3002",
      noChanges: "\u672a\u68c0\u6d4b\u5230\u8ffd\u8e2a\u7684\u6587\u672c JSON \u6216\u8d44\u6e90\u53d8\u5316",
      loadError: "\u52a0\u8f7d\u5931\u8d25: ",
      sourceRoot: "\u6e90\u76ee\u5f55",
      generatedAt: "\u751f\u6210\u65f6\u95f4",
      scannedFiles: "\u626b\u63cf\u6587\u4ef6",
      path: "\u8def\u5f84",
      oldSize: "\u539f\u5927\u5c0f",
      newSize: "\u65b0\u5927\u5c0f",
      sizeDelta: "\u5927\u5c0f\u53d8\u5316",
      oldLines: "\u539f\u884c\u6570",
      newLines: "\u65b0\u884c\u6570",
      lineDelta: "\u884c\u6570\u53d8\u5316",
      none: "\u65e0",
      truncated: "\u53e6\u6709 {count} \u9879\u672a\u5728\u9875\u5185\u5217\u51fa",
    },
    en: {
      tab: "Updates",
      title: "WebUI Content Updates",
      countLabel: "changes",
      search: "Search path / extension",
      gameFile: "Game file",
      textJson: "Text JSON",
      exportedAsset: "Exported asset",
      domain: "Domain",
      assetKind: "Asset kind",
      assetPath: "Asset path",
      openAsset: "Open in Assets",
      assetSummary: "Asset changes",
      mediaPreview: "Preview",
      mediaComparison: "Media comparison",
      previousAsset: "Old version",
      currentAsset: "New version",
      assetFile: "Asset file",
      oldAssetPath: "Old export file",
      newAssetPath: "New export file",
      openFile: "Open file",
      loadingObjPreview: "Loading OBJ preview...",
      objPreviewUnavailable: "Unable to preview this OBJ file.",
      objPreviewReady: "{vertices} vertices / {faces} faces",
      visualDiff: "Diff highlight",
      diffLoading: "Building diff preview...",
      diffUnavailable: "Unable to build diff preview.",
      diffChanged: "About {percent} pixels changed",
      textDiff: "Text diff",
      decodedImpact: "Decoded impact",
      displayImpact: "WebUI impact",
      decodedFiles: "Decoded files",
      decodedFileCount: "Decoded files",
      decodedTags: "Related types",
      decodedExtensions: "Extension mix",
      decodedTruncated: "{count} decoded files are not listed here.",
      decodedNote: "Note",
      decodedConfidence: "Mapping",
      diffTruncated: "Diff is long, so only the first lines are shown.",
      status: "Status",
      category: "Category",
      extension: "Ext",
      sort: "Sort",
      all: "All",
      sortPath: "Path (A-Z)",
      sortStatus: "Status",
      sortSizeDelta: "Size delta",
      sortLineDelta: "Line delta",
      listUnit: "items",
      added: "Added",
      modified: "Modified",
      deleted: "Deleted",
      total: "Total",
      empty: "Select a changed item",
      noFeed: "No update summary has been built yet",
      baselineReady: "Baseline is ready. Future text JSON or asset changes will appear here.",
      noChanges: "No tracked text JSON or asset changes detected",
      loadError: "Load failed: ",
      sourceRoot: "Source root",
      generatedAt: "Generated",
      scannedFiles: "Files scanned",
      path: "Path",
      oldSize: "Old size",
      newSize: "New size",
      sizeDelta: "Size delta",
      oldLines: "Old lines",
      newLines: "New lines",
      lineDelta: "Line delta",
      none: "None",
      truncated: "{count} more items are not listed in this feed",
    },
  };

  const {
    $,
    applyTemplate,
    escapeHtml,
    exportFullHref,
    formatNumber,
    formatSignedNumber,
    enhanceMediaPlayers,
    normalizeUiLocale,
  } = window.WebUI;
  const STATUS_ORDER = { added: 0, modified: 1, deleted: 2 };
  const UPDATE_STATE = {
    uiLocale: "zh",
    loaded: false,
    loading: null,
    payload: null,
    entries: [],
    filtered: [],
    selectedPath: "",
    selectedEntry: null,
    filters: {
      statuses: new Set(),
      categories: new Set(),
      extensions: new Set(),
    },
    modelCache: new Map(),
  };

  const up$ = $;

  function resolveInitialUiLocale() {
    const fromWindow = normalizeUiLocale(window.WEBUI_UI_LOCALE);
    if (fromWindow) return fromWindow;
    return document.documentElement.lang.toLowerCase().startsWith("zh") ? "zh" : "en";
  }

  function updateText(key, replacements = {}) {
    const locale = UPDATE_TEXTS[UPDATE_STATE.uiLocale] || UPDATE_TEXTS.en;
    const template = locale[key] || UPDATE_TEXTS.en[key] || key;
    return applyTemplate(template, replacements);
  }

  function normalizeExtension(value) {
    return String(value || "").trim() || "[no extension]";
  }

  function statusLabel(status) {
    return updateText(String(status || ""));
  }

  function categoryLabel(category) {
    const value = String(category || "other");
    if (value === "asset_image") return `${updateText("exportedAsset")} / image`;
    if (value === "asset_model") return `${updateText("exportedAsset")} / model`;
    if (value === "asset_video") return `${updateText("exportedAsset")} / video`;
    return value.replace(/_/g, " ");
  }

  function domainLabel(entry) {
    if (entry && entry.domain === "asset") return updateText("exportedAsset");
    if (entry && entry.domain === "text") return updateText("textJson");
    return updateText("gameFile");
  }

  function formatBytes(bytes) {
    const number = Number(bytes);
    if (!Number.isFinite(number)) return "";
    const sign = number < 0 ? "-" : "";
    let value = Math.abs(number);
    const units = ["B", "KiB", "MiB", "GiB", "TiB"];
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit += 1;
    }
    const decimals = unit === 0 ? 0 : value >= 10 ? 1 : 2;
    return `${sign}${value.toFixed(decimals)} ${units[unit]}`;
  }

  function countBy(items, keyFn) {
    const counts = {};
    for (const item of items || []) {
      const key = keyFn(item);
      counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
  }

  function statusFilters() {
    return UPDATE_STATE.filters.statuses;
  }

  function categoryFilters() {
    return UPDATE_STATE.filters.categories;
  }

  function extensionFilters() {
    return UPDATE_STATE.filters.extensions;
  }

  function updateQuery() {
    const node = up$("#updates-q");
    return String(node && node.value || "").trim().toLowerCase();
  }

  function sortMode() {
    const node = up$("#updates-sort");
    return String(node && node.value || "path");
  }

  function entrySearchText(entry) {
    const decoded = entry.decodedImpact || {};
    return [
      entry.path,
      entry.status,
      entry.category,
      entry.domain,
      entry.asset_kind,
      entry.asset_rel,
      entry.old_asset_rel,
      entry.new_asset_rel,
      entry.old_asset_export_rel,
      entry.new_asset_export_rel,
      normalizeExtension(entry.extension),
      Object.keys(decoded.tags || {}).join(" "),
      Object.keys(decoded.byExtension || {}).join(" "),
      decoded.note,
    ].join(" ").toLowerCase();
  }

  function matchesFilters(entry) {
    const statuses = statusFilters();
    const categories = categoryFilters();
    const extensions = extensionFilters();
    const q = updateQuery();
    if (statuses.size && !statuses.has(entry.status)) return false;
    if (categories.size && !categories.has(entry.category)) return false;
    if (extensions.size && !extensions.has(normalizeExtension(entry.extension))) return false;
    if (q && !entrySearchText(entry).includes(q)) return false;
    return true;
  }

  function compareEntries(a, b) {
    const mode = sortMode();
    if (mode === "status") {
      const statusDiff = (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99);
      if (statusDiff) return statusDiff;
    } else if (mode === "size-delta") {
      const diff = Math.abs(Number(b.size_delta || 0)) - Math.abs(Number(a.size_delta || 0));
      if (diff) return diff;
    } else if (mode === "line-delta") {
      const diff = Math.abs(Number(b.line_delta || 0)) - Math.abs(Number(a.line_delta || 0));
      if (diff) return diff;
    }
    return String(a.path || "").localeCompare(String(b.path || ""));
  }

  function applyUpdateStrings() {
    const pairs = [
      ["#updates-tab", "tab"],
      ["#updates-title", "title"],
      ["#updates-count-label", "countLabel"],
      ["#updates-status-label", "status"],
      ["#updates-category-label", "category"],
      ["#updates-extension-label", "extension"],
      ["#updates-sort-label", "sort"],
      ["#updates-sort-path", "sortPath"],
      ["#updates-sort-status", "sortStatus"],
      ["#updates-sort-size-delta", "sortSizeDelta"],
      ["#updates-sort-line-delta", "sortLineDelta"],
      ["#updates-list-meta-label", "listUnit"],
      ["#updates-summary-total-label", "total"],
      ["#updates-summary-added-label", "added"],
      ["#updates-summary-modified-label", "modified"],
      ["#updates-summary-deleted-label", "deleted"],
    ];
    for (const [sel, key] of pairs) {
      const node = up$(sel);
      if (node) node.textContent = updateText(key);
    }
    const q = up$("#updates-q");
    if (q) q.placeholder = updateText("search");
    if (!UPDATE_STATE.selectedEntry) {
      const empty = up$("#updates-empty");
      if (empty) empty.textContent = emptyText();
    }
  }

  function emptyText() {
    if (!UPDATE_STATE.loaded) return updateText("noFeed");
    const payload = UPDATE_STATE.payload || {};
    if (payload.missingFeed) return updateText("noFeed");
    if (payload.baselineInitialized) return updateText("baselineReady");
    if (!UPDATE_STATE.entries.length) return updateText("noChanges");
    return updateText("empty");
  }

  async function ensureUpdatesLoaded() {
    if (UPDATE_STATE.loaded) return UPDATE_STATE.payload;
    if (UPDATE_STATE.loading) return UPDATE_STATE.loading;

    UPDATE_STATE.loading = fetch("data/updates/latest.json")
      .then((res) => {
        if (res.status === 404) {
          return {
            missingFeed: true,
            totals: { added: 0, modified: 0, deleted: 0, changed: 0 },
            entries: [],
          };
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        UPDATE_STATE.loaded = true;
        UPDATE_STATE.loading = null;
        UPDATE_STATE.payload = payload || {};
        UPDATE_STATE.entries = Array.isArray(payload && payload.entries) ? payload.entries : [];
        populateUpdateFilters();
        applyUpdateFilters();
        return UPDATE_STATE.payload;
      })
      .catch((error) => {
        UPDATE_STATE.loaded = true;
        UPDATE_STATE.loading = null;
        UPDATE_STATE.payload = null;
        UPDATE_STATE.entries = [];
        populateUpdateFilters();
        showUpdatesError(error);
        return null;
      });
    return UPDATE_STATE.loading;
  }

  function showUpdatesError(error) {
    const empty = up$("#updates-empty");
    const detail = up$("#updates-detail");
    if (detail) detail.hidden = true;
    if (empty) {
      empty.hidden = false;
      empty.textContent = updateText("loadError") + (error && error.message ? error.message : String(error));
    }
    renderUpdateSummary();
    renderUpdateList();
  }

  function populateUpdateFilters() {
    const entries = UPDATE_STATE.entries;
    const statusCounts = countBy(entries, (entry) => String(entry.status || ""));
    buildUpdateFilterChips(
      "#updates-status-filter",
      ["added", "modified", "deleted"].filter((status) => statusCounts[status]),
      statusLabel,
      UPDATE_STATE.filters.statuses,
      statusCounts,
    );

    const categories = Array.from(new Set(entries.map((entry) => String(entry.category || "other")))).sort();
    const extensions = Array.from(new Set(entries.map((entry) => normalizeExtension(entry.extension)))).sort();
    buildUpdateFilterChips(
      "#updates-category-filter",
      categories,
      categoryLabel,
      UPDATE_STATE.filters.categories,
      countBy(entries, (entry) => String(entry.category || "other")),
    );
    buildUpdateFilterChips(
      "#updates-extension-filter",
      extensions,
      (value) => value,
      UPDATE_STATE.filters.extensions,
      countBy(entries, (entry) => normalizeExtension(entry.extension)),
    );
  }

  function buildUpdateFilterChips(selector, values, labeler, activeSet, counts = {}) {
    const wrap = up$(selector);
    if (!wrap) return;
    const available = new Set(values);
    for (const value of [...activeSet]) {
      if (!available.has(value)) activeSet.delete(value);
    }

    const fragment = document.createDocumentFragment();
    for (const value of values) {
      const count = Number(counts[value] || 0);
      const chip = document.createElement("span");
      chip.className = "chip updates-filter-chip";
      chip.dataset.value = value;
      chip.textContent = `${labeler ? labeler(value) : value}${count ? ` (${formatNumber(count)})` : ""}`;
      chip.classList.toggle("on", activeSet.has(value));
      chip.addEventListener("click", () => {
        if (activeSet.has(value)) activeSet.delete(value);
        else activeSet.add(value);
        applyUpdateFilters();
      });
      fragment.appendChild(chip);
    }
    wrap.replaceChildren(fragment);
  }

  function applyUpdateFilters() {
    UPDATE_STATE.filtered = UPDATE_STATE.entries.filter(matchesFilters).sort(compareEntries);
    if (
      UPDATE_STATE.selectedEntry
      && !UPDATE_STATE.filtered.some((entry) => entry.path === UPDATE_STATE.selectedEntry.path && entry.status === UPDATE_STATE.selectedEntry.status)
    ) {
      UPDATE_STATE.selectedEntry = null;
      UPDATE_STATE.selectedPath = "";
    }
    renderUpdateSummary();
    renderUpdateList();
    renderUpdateDetail();
  }

  function renderUpdateSummary() {
    const payload = UPDATE_STATE.payload || {};
    const totals = payload.totals || {};
    const total = Number(totals.changed || 0);
    up$("#updates-count").textContent = formatNumber(total) || "0";
    up$("#updates-summary-total").textContent = formatNumber(total) || "0";
    up$("#updates-summary-added").textContent = formatNumber(totals.added || 0) || "0";
    up$("#updates-summary-modified").textContent = formatNumber(totals.modified || 0) || "0";
    up$("#updates-summary-deleted").textContent = formatNumber(totals.deleted || 0) || "0";

    const tracker = payload.tracker || {};
    const assets = payload.assets || {};
    const decodedImpacts = payload.decodedImpacts || {};
    const gameTotals = payload.gameTotals || {};
    const textTotals = payload.textTotals || (payload.source === "webui_text_json_export_diff" ? gameTotals : null);
    const assetTotals = payload.assetTotals || {};
    const meta = [];
    if (payload.generatedAt) meta.push(`${updateText("generatedAt")}: ${payload.generatedAt}`);
    if (tracker.scannedFiles !== undefined && tracker.scannedFiles !== null) {
      meta.push(`${updateText("scannedFiles")}: ${formatNumber(tracker.scannedFiles)}`);
    }
    if (textTotals && textTotals.changed !== undefined) {
      meta.push(`${updateText("textJson")}: ${formatNumber(textTotals.changed || 0)}`);
    } else if (gameTotals.changed !== undefined) {
      meta.push(`${updateText("gameFile")}: ${formatNumber(gameTotals.changed || 0)}`);
    }
    if (assets.scannedAssets !== undefined && assets.scannedAssets !== null) {
      meta.push(`${updateText("assetSummary")}: ${formatNumber(assetTotals.changed || 0)} / ${formatNumber(assets.scannedAssets)}`);
    }
    if (Number(decodedImpacts.decodedFileMentions || 0) > 0) {
      const impactTags = Object.entries(decodedImpacts.byTag || {})
        .slice(0, 4)
        .map(([tag, count]) => `${tag} ${formatNumber(count)}`)
        .join(", ");
      meta.push(`${updateText("decodedImpact")}: ${formatNumber(decodedImpacts.decodedFileMentions || 0)}${impactTags ? ` (${impactTags})` : ""}`);
    }
    if (payload.sourceRoot) meta.push(`${updateText("sourceRoot")}: ${payload.sourceRoot}`);
    up$("#updates-run-meta").textContent = meta.join(" | ");

    const truncated =
      Object.values(tracker.truncated || {}).reduce((sum, value) => sum + Number(value || 0), 0)
      + Object.values(assets.truncated || {}).reduce((sum, value) => sum + Number(value || 0), 0);
    const note = up$("#updates-truncated-note");
    if (note) {
      note.hidden = truncated <= 0;
      note.textContent = truncated > 0 ? updateText("truncated", { count: formatNumber(truncated) }) : "";
    }
  }

  function renderUpdateList() {
    const list = up$("#updates-list");
    if (!list) return;
    list.replaceChildren();
    up$("#updates-shown").textContent = String(UPDATE_STATE.filtered.length);
    up$("#updates-total").textContent = String(UPDATE_STATE.entries.length);

    const fragment = document.createDocumentFragment();
    for (const entry of UPDATE_STATE.filtered) {
      const row = document.createElement("button");
      row.type = "button";
      row.className = `updates-row updates-row-${entry.status || "unknown"}`;
      row.classList.toggle(
        "is-selected",
        !!(UPDATE_STATE.selectedEntry && UPDATE_STATE.selectedEntry.path === entry.path && UPDATE_STATE.selectedEntry.status === entry.status),
      );
      const delta = entry.size_delta !== undefined
        ? formatSignedNumber(entry.size_delta)
        : entry.line_delta !== undefined
          ? formatSignedNumber(entry.line_delta)
          : "";
      const rowDomainLabel = domainLabel(entry);
      const decoded = entry.decodedImpact || {};
      const decodedCount = Number(decoded.count || 0);
      const decodedTags = Object.keys(decoded.tags || {}).slice(0, 3);
      const decodedMeta = decodedCount > 0
        ? `${updateText("decodedFiles")}: ${formatNumber(decodedCount)}${decodedTags.length ? ` (${decodedTags.join(", ")})` : ""}`
        : "";
      row.innerHTML =
        `<div class="updates-row-main">` +
          `<span class="updates-status-pill updates-status-${escapeHtml(entry.status || "unknown")}">${escapeHtml(statusLabel(entry.status))}</span>` +
          `<span class="updates-domain-pill">${escapeHtml(rowDomainLabel)}</span>` +
          `<span class="updates-row-path">${escapeHtml(entry.path || "")}</span>` +
        `</div>` +
        `<div class="updates-row-meta">${escapeHtml([
          rowDomainLabel,
          categoryLabel(entry.category),
          normalizeExtension(entry.extension),
          delta,
          decodedMeta,
        ].filter(Boolean).join(" | "))}</div>`;
      row.addEventListener("click", () => selectUpdateEntry(entry));
      fragment.appendChild(row);
    }
    list.appendChild(fragment);
  }

  function selectUpdateEntry(entry) {
    UPDATE_STATE.selectedEntry = entry;
    UPDATE_STATE.selectedPath = entry.path || "";
    renderUpdateList();
    renderUpdateDetail();
  }

  function factRow(label, value, { mono = false } = {}) {
    if (value === undefined || value === null || value === "") return "";
    return (
      `<div class="updates-fact">` +
        `<div class="updates-fact-label">${escapeHtml(label)}</div>` +
        `<div class="updates-fact-value${mono ? " mono" : ""}">${escapeHtml(value)}</div>` +
      `</div>`
    );
  }

  function assetUrl(rel) {
    const url = new URL(window.location.href);
    url.searchParams.set("asset", rel);
    url.hash = "#assets";
    return url.toString();
  }

  function fallbackAssetSourceRoots() {
    return {
      StreamingAssets: "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type",
      "StreamingAssets-maps": "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps",
      "StreamingAssets-structured": "export_full/structured/StreamingAssets",
      Persistent: "export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type",
      "Persistent-maps": "export_full/recovered/AnimeStudio-cli/Persistent/maps",
      "Persistent-structured": "export_full/structured/Persistent",
    };
  }

  function updateAssetHref(rel) {
    const payload = UPDATE_STATE.payload || {};
    const assets = payload.assets || {};
    return exportFullHref(
      rel,
      { ...fallbackAssetSourceRoots(), ...(assets.sourceRoots || {}) },
      assets.sourceRoot || "export_full",
    );
  }

  function normalizeExportRouteRel(value) {
    return String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  }

  function defaultExportSourceRoot(source) {
    const match = String(source || "").match(/^(.+)-structured$/i);
    return match ? `structured/${match[1]}` : "";
  }

  function exportRouteHref(rel, sourceRoots = {}, exportRoot = "", routeRoot = "export_full") {
    const normalizedRel = normalizeExportRouteRel(rel);
    const normalizedRoute = normalizeExportRouteRel(routeRoot) || "export_full";
    if (!normalizedRel) return "";

    const [source, ...rest] = normalizedRel.split("/").filter(Boolean);
    const sourceRoot = (sourceRoots && sourceRoots[source]) || defaultExportSourceRoot(source);
    let exportRel = normalizedRel;
    if (sourceRoot) {
      let normalizedRoot = normalizeExportRouteRel(sourceRoot);
      const rootPrefix = normalizeExportRouteRel(exportRoot);
      if (rootPrefix && normalizedRoot.startsWith(`${rootPrefix}/`)) {
        normalizedRoot = normalizedRoot.slice(rootPrefix.length + 1);
      } else if (normalizedRoot === rootPrefix) {
        normalizedRoot = "";
      }
      exportRel = [normalizedRoot, rest.join("/")].filter(Boolean).join("/");
    }

    return `/${normalizedRoute}/${exportRel.split("/").map(encodeURIComponent).join("/")}`;
  }

  function currentAssetHref(entry) {
    const payload = UPDATE_STATE.payload || {};
    const assets = payload.assets || {};
    if (entry && entry.new_asset_export_rel) {
      return exportRouteHref(entry.new_asset_export_rel, {}, assets.sourceRoot || "export_full", "export_full");
    }
    const rel = entry && (entry.new_asset_rel || entry.asset_rel);
    return rel ? updateAssetHref(rel) : "";
  }

  function previousAssetHref(entry) {
    const payload = UPDATE_STATE.payload || {};
    const assets = payload.assets || {};
    if (entry && entry.old_asset_export_rel) {
      return exportRouteHref(entry.old_asset_export_rel, {}, assets.previousSourceRoot || "export_122", "export_previous");
    }
    const rel = entry && entry.old_asset_rel;
    if (!rel) return "";
    return exportRouteHref(
      rel,
      { ...fallbackAssetSourceRoots(), ...(assets.previousSourceRoots || {}) },
      assets.previousSourceRoot || "export_122",
      "export_previous",
    );
  }

  function factLinkRow(label, href, text) {
    if (!href || !text) return "";
    return (
      `<div class="updates-fact">` +
        `<div class="updates-fact-label">${escapeHtml(label)}</div>` +
        `<div class="updates-fact-value"><a class="updates-detail-link" href="${escapeHtml(href)}">${escapeHtml(text)}</a></div>` +
      `</div>`
    );
  }

  function textDiffHtml(entry) {
    const lines = Array.isArray(entry && entry.text_diff) ? entry.text_diff : [];
    if (!lines.length) return "";
    const rows = lines.map((line) => {
      const value = String(line || "");
      let cls = "ctx";
      if (value.startsWith("+") && !value.startsWith("+++")) cls = "add";
      else if (value.startsWith("-") && !value.startsWith("---")) cls = "del";
      else if (value.startsWith("@@")) cls = "hunk";
      else if (value.startsWith("---") || value.startsWith("+++")) cls = "file";
      return `<div class="updates-diff-line updates-diff-${cls}">${escapeHtml(value || " ")}</div>`;
    }).join("");
    const note = entry.text_diff_truncated
      ? `<div class="updates-detail-note">${escapeHtml(updateText("diffTruncated"))}</div>`
      : "";
    return (
      `<section class="updates-detail-panel updates-text-diff">` +
        `<h2>${escapeHtml(updateText("textDiff"))}</h2>` +
        `<div class="updates-diff-code" role="region" aria-label="${escapeHtml(updateText("textDiff"))}">${rows}</div>` +
        note +
      `</section>`
    );
  }

  function changedAssetMediaKind(entry) {
    const kind = String(entry && entry.asset_kind || "");
    return ["image", "video", "model"].includes(kind) ? kind : "";
  }

  function filenameFromRel(rel) {
    const parts = String(rel || "").split("/");
    return parts[parts.length - 1] || rel || "";
  }

  function extensionFromRel(rel) {
    const filename = filenameFromRel(rel);
    const dot = filename.lastIndexOf(".");
    return dot >= 0 ? filename.slice(dot + 1).toUpperCase() : "MODEL";
  }

  function isObjRel(rel) {
    return /\.obj$/i.test(filenameFromRel(rel));
  }

  function assetMediaItems(entry) {
    const kind = changedAssetMediaKind(entry);
    if (!kind || !entry || entry.domain !== "asset") return [];
    if (entry.status === "modified") {
      return [
        {
          label: updateText("previousAsset"),
          href: previousAssetHref(entry),
          rel: entry.old_asset_export_rel || entry.old_asset_rel || entry.asset_rel,
          kind,
          size: entry.old_size,
        },
        {
          label: updateText("currentAsset"),
          href: currentAssetHref(entry),
          rel: entry.new_asset_export_rel || entry.new_asset_rel || entry.asset_rel,
          kind,
          size: entry.new_size,
        },
      ].filter((item) => item.href && item.rel);
    }
    if (entry.status === "deleted") {
      return [{
        label: updateText("previousAsset"),
        href: previousAssetHref(entry),
        rel: entry.old_asset_export_rel || entry.old_asset_rel || entry.asset_rel,
        kind,
        size: entry.old_size,
      }].filter((item) => item.href && item.rel);
    }
    return [{
      label: updateText("currentAsset"),
      href: currentAssetHref(entry),
      rel: entry.new_asset_export_rel || entry.new_asset_rel || entry.asset_rel,
      kind,
      size: entry.new_size,
    }].filter((item) => item.href && item.rel);
  }

  function mediaItemHtml(item) {
    const href = String(item && item.href || "");
    const rel = String(item && item.rel || "");
    const kind = String(item && item.kind || "");
    if (!href || !rel) return "";
    const size = formatBytes(item.size);
    let media = "";
    if (kind === "video") {
      media = `<video class="updates-media-video" src="${escapeHtml(href)}" preload="metadata" playsinline data-update-sync-video="1"></video>`;
    } else if (kind === "image") {
      media = (
        `<a class="updates-media-link" href="${escapeHtml(href)}" target="_blank" rel="noopener">` +
          `<img class="updates-media-image" src="${escapeHtml(href)}" alt="${escapeHtml(rel)}" loading="lazy">` +
        `</a>`
      );
    } else if (isObjRel(rel)) {
      media = (
        `<div class="updates-model-preview">` +
          `<canvas class="updates-model-canvas" data-model-src="${escapeHtml(href)}" role="img" aria-label="${escapeHtml(rel)}"></canvas>` +
          `<div class="updates-model-note">${escapeHtml(updateText("loadingObjPreview"))}</div>` +
        `</div>`
      );
    } else {
      media = (
        `<a class="updates-model-file" href="${escapeHtml(href)}" target="_blank" rel="noopener">` +
          `<span class="updates-model-file-kind">${escapeHtml(extensionFromRel(rel))}</span>` +
          `<span class="updates-model-file-name">${escapeHtml(filenameFromRel(rel))}</span>` +
          `<span class="updates-model-file-caption">${escapeHtml(updateText("assetFile"))}</span>` +
        `</a>`
      );
    }
    return (
      `<div class="updates-media-item">` +
        `<div class="updates-media-label">` +
          `<span>${escapeHtml(item.label || "")}</span>` +
          (size ? `<span>${escapeHtml(size)}</span>` : "") +
        `</div>` +
        media +
        `<a class="updates-media-open" href="${escapeHtml(href)}" target="_blank" rel="noopener">` +
          `${escapeHtml(updateText("openFile"))}: ${escapeHtml(rel)}` +
        `</a>` +
      `</div>`
    );
  }

  function mediaPreviewHtml(entry) {
    const items = assetMediaItems(entry);
    if (!items.length) return "";
    return (
      `<section class="updates-detail-panel updates-media-preview">` +
        `<h2>${escapeHtml(updateText(items.length > 1 ? "mediaComparison" : "mediaPreview"))}</h2>` +
        `<div class="updates-media-comparison${items.length > 1 ? " is-comparison" : ""}">` +
          items.map(mediaItemHtml).join("") +
        `</div>` +
      `</section>`
    );
  }

  function diffMediaItems(entry) {
    const items = assetMediaItems(entry);
    if (!entry || entry.status !== "modified" || items.length < 2) return [];
    const kind = String(entry.asset_kind || "");
    if (kind !== "image" && kind !== "video") return [];
    const oldItem = items.find((item) => item.label === updateText("previousAsset")) || items[0];
    const newItem = items.find((item) => item.label === updateText("currentAsset")) || items[1];
    if (!oldItem || !newItem || !oldItem.href || !newItem.href) return [];
    return [oldItem, newItem];
  }

  function mediaDiffHtml(entry) {
    const [oldItem, newItem] = diffMediaItems(entry);
    if (!oldItem || !newItem) return "";
    const kind = String(entry.asset_kind || "");
    const canvasAttrs = [
      `class="updates-media-diff-canvas"`,
      `data-diff-kind="${escapeHtml(kind)}"`,
      `data-old-src="${escapeHtml(oldItem.href)}"`,
      `data-new-src="${escapeHtml(newItem.href)}"`,
    ].join(" ");
    const hiddenVideos = kind === "video"
      ? (
        `<video class="updates-diff-source-video" src="${escapeHtml(oldItem.href)}" preload="auto" playsinline muted data-media-player="diff-source" data-update-sync-video="1" data-diff-role="old"></video>` +
        `<video class="updates-diff-source-video" src="${escapeHtml(newItem.href)}" preload="auto" playsinline muted data-media-player="diff-source" data-update-sync-video="1" data-diff-role="new"></video>`
      )
      : "";
    return (
      `<section class="updates-detail-panel updates-media-diff">` +
        `<h2>${escapeHtml(updateText("visualDiff"))}</h2>` +
        `<div class="updates-media-diff-stage updates-${escapeHtml(kind)}-diff">` +
          `<canvas ${canvasAttrs} role="img" aria-label="${escapeHtml(updateText("visualDiff"))}"></canvas>` +
          hiddenVideos +
        `</div>` +
        `<div class="updates-detail-note updates-media-diff-note">${escapeHtml(updateText("diffLoading"))}</div>` +
      `</section>`
    );
  }

  function diffCanvasSize(oldWidth, oldHeight, newWidth, newHeight, maxEdge = 960) {
    const sourceWidth = Math.max(Number(oldWidth) || 0, Number(newWidth) || 0, 1);
    const sourceHeight = Math.max(Number(oldHeight) || 0, Number(newHeight) || 0, 1);
    const scale = Math.min(1, maxEdge / Math.max(sourceWidth, sourceHeight));
    return {
      width: Math.max(1, Math.round(sourceWidth * scale)),
      height: Math.max(1, Math.round(sourceHeight * scale)),
    };
  }

  function drawSourceFrame(source, width, height) {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;
    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(source, 0, 0, width, height);
    return ctx.getImageData(0, 0, width, height);
  }

  function drawMediaDiff(canvas, oldSource, newSource, oldWidth, oldHeight, newWidth, newHeight) {
    if (!canvas || !oldSource || !newSource) return null;
    const { width, height } = diffCanvasSize(oldWidth, oldHeight, newWidth, newHeight);
    const oldFrame = drawSourceFrame(oldSource, width, height);
    const newFrame = drawSourceFrame(newSource, width, height);
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!oldFrame || !newFrame || !ctx) return null;

    canvas.width = width;
    canvas.height = height;
    canvas.style.aspectRatio = `${width} / ${height}`;

    const out = ctx.createImageData(width, height);
    const oldData = oldFrame.data;
    const newData = newFrame.data;
    const outData = out.data;
    let changed = 0;
    for (let i = 0; i < newData.length; i += 4) {
      const dr = Math.abs(newData[i] - oldData[i]);
      const dg = Math.abs(newData[i + 1] - oldData[i + 1]);
      const db = Math.abs(newData[i + 2] - oldData[i + 2]);
      const da = Math.abs(newData[i + 3] - oldData[i + 3]);
      const delta = dr + dg + db + da;
      const base = Math.round((newData[i] * 0.2126 + newData[i + 1] * 0.7152 + newData[i + 2] * 0.0722) * 0.62 + 34);
      if (delta > 42) {
        changed += 1;
        const heat = Math.min(255, 96 + delta * 0.55);
        outData[i] = heat;
        outData[i + 1] = Math.max(0, base - delta * 0.14);
        outData[i + 2] = Math.max(0, base - delta * 0.18);
        outData[i + 3] = 255;
      } else {
        outData[i] = base;
        outData[i + 1] = base;
        outData[i + 2] = base;
        outData[i + 3] = Math.max(newData[i + 3], 220);
      }
    }
    ctx.putImageData(out, 0, 0);
    return {
      changed,
      total: width * height,
      percent: width * height ? changed / (width * height) * 100 : 0,
    };
  }

  function setDiffNote(section, text, isError = false) {
    const note = section && section.querySelector(".updates-media-diff-note");
    if (!note) return;
    note.textContent = text || "";
    note.classList.toggle("is-error", Boolean(isError));
  }

  function diffCompleteText(result) {
    if (!result) return "";
    const percent = result.percent >= 0.1 ? result.percent.toFixed(1) : result.percent.toFixed(2);
    return updateText("diffChanged", { percent: `${percent}%` });
  }

  function loadDiffImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.decoding = "async";
      img.addEventListener("load", () => resolve(img), { once: true });
      img.addEventListener("error", () => reject(new Error("image load failed")), { once: true });
      img.src = src;
    });
  }

  async function initImageDiff(section, canvas) {
    try {
      const [oldImg, newImg] = await Promise.all([
        loadDiffImage(canvas.dataset.oldSrc || ""),
        loadDiffImage(canvas.dataset.newSrc || ""),
      ]);
      if (!canvas.isConnected) return;
      const result = drawMediaDiff(
        canvas,
        oldImg,
        newImg,
        oldImg.naturalWidth,
        oldImg.naturalHeight,
        newImg.naturalWidth,
        newImg.naturalHeight,
      );
      setDiffNote(section, diffCompleteText(result));
    } catch (error) {
      setDiffNote(section, updateText("diffUnavailable"), true);
    }
  }

  function videoFrameReady(video) {
    return video && video.readyState >= 2 && Number(video.videoWidth || 0) > 0 && Number(video.videoHeight || 0) > 0;
  }

  function initVideoDiff(section, canvas) {
    const oldVideo = section.querySelector("video[data-diff-role='old']");
    const newVideo = section.querySelector("video[data-diff-role='new']");
    if (!oldVideo || !newVideo) {
      setDiffNote(section, updateText("diffUnavailable"), true);
      return;
    }

    let frameQueued = false;
    const render = () => {
      frameQueued = false;
      if (!canvas.isConnected) return;
      if (!videoFrameReady(oldVideo) || !videoFrameReady(newVideo)) {
        if (!oldVideo.error && !newVideo.error) setDiffNote(section, updateText("diffLoading"));
        return;
      }
      try {
        const result = drawMediaDiff(
          canvas,
          oldVideo,
          newVideo,
          oldVideo.videoWidth,
          oldVideo.videoHeight,
          newVideo.videoWidth,
          newVideo.videoHeight,
        );
        setDiffNote(section, diffCompleteText(result));
      } catch (error) {
        setDiffNote(section, updateText("diffUnavailable"), true);
      }
      if (!oldVideo.paused || !newVideo.paused) queueFrame();
    };
    const queueFrame = () => {
      if (frameQueued || !canvas.isConnected) return;
      frameQueued = true;
      requestAnimationFrame(render);
    };
    for (const video of [oldVideo, newVideo]) {
      video.addEventListener("loadeddata", queueFrame);
      video.addEventListener("loadedmetadata", queueFrame);
      video.addEventListener("play", queueFrame);
      video.addEventListener("timeupdate", queueFrame);
      video.addEventListener("seeked", queueFrame);
      video.addEventListener("error", () => setDiffNote(section, updateText("diffUnavailable"), true), { once: true });
    }
    queueFrame();
  }

  function initMediaDiffModules(root) {
    if (!root) return;
    root.querySelectorAll(".updates-media-diff-canvas").forEach((canvas) => {
      const section = canvas.closest(".updates-media-diff");
      if (canvas.dataset.diffInitialized === "1") return;
      canvas.dataset.diffInitialized = "1";
      if (canvas.dataset.diffKind === "image") initImageDiff(section, canvas);
      else if (canvas.dataset.diffKind === "video") initVideoDiff(section, canvas);
    });
  }

  function safeVideoTime(video, targetTime) {
    const duration = Number(video.duration);
    if (Number.isFinite(duration) && duration > 0) {
      return Math.min(Math.max(0, targetTime), Math.max(0, duration - 0.04));
    }
    return Math.max(0, targetTime);
  }

  function seekVideoNear(video, targetTime) {
    if (!video || Number.isNaN(Number(targetTime))) return;
    const nextTime = safeVideoTime(video, Number(targetTime));
    if (Math.abs(Number(video.currentTime || 0) - nextTime) < 0.18) return;
    try {
      video.currentTime = nextTime;
    } catch (error) {
      // Some media cannot seek until metadata is available; the next user event will retry.
    }
  }

  function setupUpdatesVideoSync(root) {
    if (!root) return;
    const videos = Array.from(root.querySelectorAll("video[data-update-sync-video='1']"));
    if (videos.length < 2) return;
    let syncing = false;
    const releaseSync = () => {
      window.setTimeout(() => {
        syncing = false;
      }, 80);
    };
    const syncGroup = (target, { play = false, pause = false, time = true, rate = true } = {}) => {
      if (!target || syncing) return;
      syncing = true;
      const currentTime = Number(target.currentTime || 0);
      const playbackRate = Number(target.playbackRate || 1);
      for (const video of videos) {
        if (video === target) continue;
        if (rate && Number.isFinite(playbackRate)) video.playbackRate = playbackRate;
        if (time) seekVideoNear(video, currentTime);
        if (pause && !video.paused) video.pause();
      }
      if (play) {
        const playCalls = videos.map((video) => {
          if (video === target || !video.paused) return null;
          return video.play().catch(() => {});
        });
        Promise.all(playCalls.filter(Boolean)).finally(releaseSync);
      } else {
        releaseSync();
      }
    };
    for (const video of videos) {
      if (video.dataset.updateSyncBound === "1") continue;
      video.dataset.updateSyncBound = "1";
      video.addEventListener("play", () => syncGroup(video, { play: true }));
      video.addEventListener("pause", () => {
        if (!video.ended) syncGroup(video, { pause: true, time: false, rate: false });
      });
      video.addEventListener("seeking", () => syncGroup(video, { time: true, rate: false }));
      video.addEventListener("ratechange", () => syncGroup(video, { time: false, rate: true }));
      video.addEventListener("loadedmetadata", () => {
        const playing = videos.find((candidate) => candidate !== video && !candidate.paused);
        if (playing) syncGroup(playing, { play: true });
      });
    }
  }

  async function loadObjPreviewModel(src) {
    let model = UPDATE_STATE.modelCache.get(src);
    if (model) return model;
    const res = await fetch(src);
    if (!res.ok) throw new Error(`OBJ HTTP ${res.status}`);
    model = parseObjPreviewModel(await res.text());
    UPDATE_STATE.modelCache.set(src, model);
    return model;
  }

  function parseObjPreviewModel(text) {
    const vertices = [];
    const triangles = [];
    let faceCount = 0;
    let objectCount = 0;
    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let minZ = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    let maxZ = Number.NEGATIVE_INFINITY;

    for (const rawLine of String(text || "").split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;
      if (line.startsWith("v ")) {
        const parts = line.split(/\s+/);
        const x = Number(parts[1]);
        const y = Number(parts[2]);
        const z = Number(parts[3]);
        if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) continue;
        vertices.push([x, y, z]);
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        minZ = Math.min(minZ, z);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
        maxZ = Math.max(maxZ, z);
      } else if (line.startsWith("f ")) {
        faceCount += 1;
        const indices = line.split(/\s+/).slice(1).map((token) => {
          const raw = Number(String(token || "").split("/")[0]);
          if (!Number.isInteger(raw) || raw === 0) return -1;
          return raw > 0 ? raw - 1 : vertices.length + raw;
        }).filter((index) => index >= 0 && index < vertices.length);
        for (let index = 1; index + 1 < indices.length && triangles.length < 28000; index += 1) {
          const a = indices[0];
          const b = indices[index];
          const c = indices[index + 1];
          if (a !== b && b !== c && a !== c) triangles.push([a, b, c]);
        }
      } else if (line.startsWith("o ") || line.startsWith("g ")) {
        objectCount += 1;
      }
    }

    const spanX = maxX - minX;
    const spanY = maxY - minY;
    const spanZ = maxZ - minZ;
    const maxSpan = Math.max(spanX || 1, spanY || 1, spanZ || 1);
    const pointLimit = 14000;
    const pointStep = vertices.length > pointLimit ? Math.ceil(vertices.length / pointLimit) : 1;
    const points = [];
    for (let index = 0; index < vertices.length; index += pointStep) {
      points.push(vertices[index]);
    }

    return {
      vertices,
      triangles,
      points,
      vertexCount: vertices.length,
      faceCount,
      objectCount,
      center: [
        Number.isFinite(minX) ? (minX + maxX) * 0.5 : 0,
        Number.isFinite(minY) ? (minY + maxY) * 0.5 : 0,
        Number.isFinite(minZ) ? (minZ + maxZ) * 0.5 : 0,
      ],
      scale: 2 / maxSpan,
    };
  }

  function projectObjPoint(point, model, width, height) {
    const rx = -0.42;
    const ry = 0.72;
    const cosX = Math.cos(rx);
    const sinX = Math.sin(rx);
    const cosY = Math.cos(ry);
    const sinY = Math.sin(ry);
    let x = (point[0] - model.center[0]) * model.scale;
    let y = (point[1] - model.center[1]) * model.scale;
    let z = (point[2] - model.center[2]) * model.scale;

    const xz = x * cosY - z * sinY;
    const zz = x * sinY + z * cosY;
    x = xz;
    z = zz;

    const yz = y * cosX - z * sinX;
    z = y * sinX + z * cosX;
    y = yz;

    const cameraZ = 3.5;
    const perspective = cameraZ / Math.max(0.35, cameraZ - z);
    const visualScale = Math.min(width, height) * 0.38;
    return {
      x,
      y,
      z,
      sx: width * 0.5 + x * perspective * visualScale,
      sy: height * 0.52 - y * perspective * visualScale,
      depth: z,
      radius: Math.max(0.75, perspective * 1.45),
    };
  }

  function drawObjBackdrop(ctx, width, height) {
    ctx.fillStyle = "#0b1015";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "rgba(118, 171, 174, 0.12)";
    ctx.lineWidth = 1;
    const step = Math.max(44, Math.round(width / 9));
    for (let x = step; x < width; x += step) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = step; y < height; y += step) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }

  function renderObjPreviewCanvas(canvas, model) {
    if (!canvas || !model) return;
    const width = Math.max(260, Math.round(canvas.clientWidth || canvas.parentElement?.clientWidth || 640));
    const height = Math.max(220, Math.round(canvas.clientHeight || 360));
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawObjBackdrop(ctx, width, height);

    const projectedVertices = model.vertices.map((point) => projectObjPoint(point, model, width, height));
    if (model.triangles.length && model.triangles.length <= 16000) {
      const faces = [];
      for (const triangle of model.triangles) {
        const a = projectedVertices[triangle[0]];
        const b = projectedVertices[triangle[1]];
        const c = projectedVertices[triangle[2]];
        if (!a || !b || !c) continue;
        const area = Math.abs((b.sx - a.sx) * (c.sy - a.sy) - (b.sy - a.sy) * (c.sx - a.sx));
        if (area < 0.1) continue;
        faces.push({ a, b, c, z: (a.depth + b.depth + c.depth) / 3 });
      }
      faces.sort((a, b) => a.z - b.z);
      for (const face of faces) {
        const depth = Math.max(0, Math.min(1, (face.z + 1.5) / 3));
        ctx.fillStyle = `rgba(${Math.round(60 + depth * 64)}, ${Math.round(120 + depth * 72)}, ${Math.round(140 + depth * 70)}, 0.78)`;
        ctx.strokeStyle = "rgba(230, 244, 246, 0.16)";
        ctx.beginPath();
        ctx.moveTo(face.a.sx, face.a.sy);
        ctx.lineTo(face.b.sx, face.b.sy);
        ctx.lineTo(face.c.sx, face.c.sy);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }
      return;
    }

    const projectedPoints = model.points
      .map((point) => projectObjPoint(point, model, width, height))
      .sort((a, b) => a.depth - b.depth);
    for (const point of projectedPoints) {
      const depth = Math.max(0, Math.min(1, (point.depth + 1.5) / 3));
      ctx.fillStyle = `rgba(118, 171, 174, ${0.24 + depth * 0.6})`;
      ctx.beginPath();
      ctx.arc(point.sx, point.sy, point.radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function setObjPreviewNote(canvas, text, isError = false) {
    const note = canvas?.closest(".updates-model-preview")?.querySelector(".updates-model-note");
    if (!note) return;
    note.textContent = text;
    note.classList.toggle("is-error", Boolean(isError));
  }

  function initObjPreviewModules(root) {
    if (!root) return;
    root.querySelectorAll(".updates-model-canvas[data-model-src]").forEach((canvas) => {
      if (canvas.dataset.modelInitialized === "1") return;
      canvas.dataset.modelInitialized = "1";
      const src = canvas.dataset.modelSrc || "";
      setObjPreviewNote(canvas, updateText("loadingObjPreview"));
      loadObjPreviewModel(src)
        .then((model) => {
          if (!canvas.isConnected) return;
          renderObjPreviewCanvas(canvas, model);
          setObjPreviewNote(canvas, updateText("objPreviewReady", {
            vertices: formatNumber(model.vertexCount),
            faces: formatNumber(model.faceCount),
          }));
        })
        .catch(() => {
          if (!canvas.isConnected) return;
          setObjPreviewNote(canvas, updateText("objPreviewUnavailable"), true);
        });
    });
  }

  function decodedFileHref(path) {
    const rel = String(path || "").replace(/^export_full\//, "");
    return exportFullHref(rel, {}, "export_full");
  }

  function labeledCountsHtml(counts) {
    const entries = Object.entries(counts || {}).filter(([, value]) => Number(value || 0) > 0);
    if (!entries.length) return "";
    return entries
      .map(([label, value]) => `<span class="updates-impact-chip">${escapeHtml(label)} ${escapeHtml(formatNumber(value) || String(value))}</span>`)
      .join("");
  }

  function decodedImpactHtml(entry) {
    const impact = entry && entry.decodedImpact;
    if (!impact) return "";
    const count = Number(impact.count || 0);
    const sample = Array.isArray(impact.sample) ? impact.sample : [];
    const tagHtml = labeledCountsHtml(impact.tags);
    const extHtml = labeledCountsHtml(impact.byExtension);
    const rows = sample
      .map((path) => `<li><a href="${escapeHtml(decodedFileHref(path))}" target="_blank" rel="noopener">${escapeHtml(path)}</a></li>`)
      .join("");
    const truncated = Number(impact.truncated || 0);
    const summaryFacts = [
      factRow(updateText("decodedFileCount"), formatNumber(count)),
      factRow(updateText("decodedConfidence"), impact.confidence),
      impact.note ? factRow(updateText("decodedNote"), impact.note) : "",
    ].filter(Boolean).join("");
    const list = sample.length
      ? `<ul class="updates-decoded-list">${rows}</ul>`
      : `<div class="updates-detail-note">${escapeHtml(updateText("none"))}</div>`;
    return (
      `<section class="updates-detail-panel updates-decoded-impact">` +
        `<h2>${escapeHtml(updateText("decodedImpact"))}</h2>` +
        `<div class="updates-impact-grid">${summaryFacts}</div>` +
        (tagHtml ? `<div class="updates-impact-chips"><span>${escapeHtml(updateText("displayImpact"))}</span>${tagHtml}</div>` : "") +
        (extHtml ? `<div class="updates-impact-chips"><span>${escapeHtml(updateText("decodedExtensions"))}</span>${extHtml}</div>` : "") +
        `<h3>${escapeHtml(updateText("decodedFiles"))}</h3>` +
        list +
        (truncated > 0 ? `<div class="updates-detail-note">${escapeHtml(updateText("decodedTruncated", { count: formatNumber(truncated) }))}</div>` : "") +
      `</section>`
    );
  }

  function ensureDetailExtra() {
    let extra = up$("#updates-detail-extra");
    if (extra) return extra;
    extra = document.createElement("div");
    extra.id = "updates-detail-extra";
    const facts = up$("#updates-detail-facts");
    if (facts && facts.parentNode) facts.parentNode.insertBefore(extra, facts.nextSibling);
    return extra;
  }

  function renderUpdateDetail() {
    const detail = up$("#updates-detail");
    const empty = up$("#updates-empty");
    const entry = UPDATE_STATE.selectedEntry;
    if (!detail || !empty) return;

    if (!entry) {
      detail.hidden = true;
      empty.hidden = false;
      empty.textContent = emptyText();
      const extra = up$("#updates-detail-extra");
      if (extra) extra.replaceChildren();
      return;
    }

    empty.hidden = true;
    detail.hidden = false;
    up$("#updates-detail-title").textContent = entry.path || "";
    up$("#updates-detail-meta").textContent = [
      statusLabel(entry.status),
      domainLabel(entry),
      categoryLabel(entry.category),
      normalizeExtension(entry.extension),
    ].filter(Boolean).join(" | ");

    const facts = [
      factRow(updateText("path"), entry.path, { mono: true }),
      factRow(updateText("domain"), domainLabel(entry)),
      factRow(updateText("status"), statusLabel(entry.status)),
      factRow(updateText("category"), categoryLabel(entry.category)),
      factRow(updateText("assetKind"), entry.asset_kind),
      factRow(updateText("assetPath"), entry.asset_rel, { mono: true }),
      factRow(updateText("oldAssetPath"), entry.old_asset_export_rel, { mono: true }),
      factRow(updateText("newAssetPath"), entry.new_asset_export_rel, { mono: true }),
      entry.asset_rel ? factLinkRow(updateText("openAsset"), assetUrl(entry.asset_rel), entry.asset_rel) : "",
      factRow(updateText("extension"), normalizeExtension(entry.extension)),
      factRow(updateText("oldSize"), formatBytes(entry.old_size)),
      factRow(updateText("newSize"), formatBytes(entry.new_size)),
      factRow(updateText("sizeDelta"), formatSignedNumber(entry.size_delta)),
      factRow(updateText("oldLines"), formatNumber(entry.old_line_count)),
      factRow(updateText("newLines"), formatNumber(entry.new_line_count)),
      factRow(updateText("lineDelta"), formatSignedNumber(entry.line_delta)),
    ].filter(Boolean);
    up$("#updates-detail-facts").innerHTML = facts.join("") || factRow(updateText("none"), updateText("none"));
    ensureDetailExtra().innerHTML = [
      decodedImpactHtml(entry),
      mediaPreviewHtml(entry),
      mediaDiffHtml(entry),
      textDiffHtml(entry),
    ].filter(Boolean).join("");
    const extra = up$("#updates-detail-extra");
    if (extra) {
      enhanceMediaPlayers(extra);
      setupUpdatesVideoSync(extra);
      initMediaDiffModules(extra);
      initObjPreviewModules(extra);
    }
  }

  function refreshUpdates() {
    applyUpdateStrings();
    populateUpdateFilters();
    applyUpdateFilters();
  }

  function maybeLoadUpdates() {
    if (document.body.dataset.activeView === "updates" || window.location.hash === "#updates") {
      ensureUpdatesLoaded();
    }
  }

  function bindUpdateEvents() {
    for (const sel of ["#updates-q", "#updates-sort"]) {
      const node = up$(sel);
      if (node) node.addEventListener(sel === "#updates-q" ? "input" : "change", applyUpdateFilters);
    }
    document.querySelectorAll(".view-tab").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.view === "updates") setTimeout(maybeLoadUpdates, 0);
      });
    });
    window.addEventListener("hashchange", () => setTimeout(maybeLoadUpdates, 0));
    window.addEventListener("webui:view-changed", (event) => {
      if (event.detail && event.detail.view === "updates") maybeLoadUpdates();
    });
    window.addEventListener("webui:ui-locale-changed", (event) => {
      UPDATE_STATE.uiLocale = normalizeUiLocale(event.detail && event.detail.locale) || UPDATE_STATE.uiLocale;
      refreshUpdates();
    });
  }

  function initUpdates() {
    UPDATE_STATE.uiLocale = resolveInitialUiLocale();
    applyUpdateStrings();
    bindUpdateEvents();
    renderUpdateSummary();
    renderUpdateDetail();
    maybeLoadUpdates();
  }

  initUpdates();
})();
