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
    rebuildSelect,
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

  function statusFilter() {
    const node = up$("#updates-status");
    return String(node && node.value || "");
  }

  function categoryFilter() {
    const node = up$("#updates-category");
    return String(node && node.value || "");
  }

  function extensionFilter() {
    const node = up$("#updates-extension");
    return String(node && node.value || "");
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
      normalizeExtension(entry.extension),
      Object.keys(decoded.tags || {}).join(" "),
      Object.keys(decoded.byExtension || {}).join(" "),
      decoded.note,
    ].join(" ").toLowerCase();
  }

  function matchesFilters(entry) {
    const status = statusFilter();
    const category = categoryFilter();
    const extension = extensionFilter();
    const q = updateQuery();
    if (status && entry.status !== status) return false;
    if (category && entry.category !== category) return false;
    if (extension && normalizeExtension(entry.extension) !== extension) return false;
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
      ["#updates-status-all", "all"],
      ["#updates-status-added", "added"],
      ["#updates-status-modified", "modified"],
      ["#updates-status-deleted", "deleted"],
      ["#updates-category-all", "all"],
      ["#updates-extension-all", "all"],
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
    const categories = Array.from(new Set(entries.map((entry) => String(entry.category || "other")))).sort();
    const extensions = Array.from(new Set(entries.map((entry) => normalizeExtension(entry.extension)))).sort();
    rebuildSelect(up$("#updates-category"), categories, categoryLabel);
    rebuildSelect(up$("#updates-extension"), extensions, (value) => value);
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

  function mediaPreviewHtml(entry) {
    const rel = entry && entry.asset_rel;
    const kind = String(entry && entry.asset_kind || "");
    if (!rel || entry.status === "deleted" || (kind !== "image" && kind !== "video")) return "";
    const href = updateAssetHref(rel);
    const media = kind === "video"
      ? `<video class="updates-media-video" src="${escapeHtml(href)}" preload="metadata" playsinline></video>`
      : `<a class="updates-media-link" href="${escapeHtml(href)}" target="_blank" rel="noopener"><img class="updates-media-image" src="${escapeHtml(href)}" alt="${escapeHtml(rel)}" loading="lazy"></a>`;
    return (
      `<section class="updates-detail-panel updates-media-preview">` +
        `<h2>${escapeHtml(updateText("mediaPreview"))}</h2>` +
        media +
        `<a class="updates-media-open" href="${escapeHtml(href)}" target="_blank" rel="noopener">${escapeHtml(rel)}</a>` +
      `</section>`
    );
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
      textDiffHtml(entry),
    ].filter(Boolean).join("");
    const extra = up$("#updates-detail-extra");
    if (extra) enhanceMediaPlayers(extra);
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
    for (const sel of ["#updates-q", "#updates-status", "#updates-category", "#updates-extension", "#updates-sort"]) {
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
