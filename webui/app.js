// Endfield conversation browser - single-file vanilla JS.
// Loads data/index.json once, lazy-loads data/conv/<key>.json on demand.
// Left pane is a 3-level tree (kind / story-line / mission) with a
// virtualized scroll that supports mixed row heights.

const ROW_GROUP_H = 28;
const ROW_ITEM_H = 50;
const OVERSCAN_PX = 200;
const WIKI_MEDIA_MAX_IMAGES = 12;
const WIKI_MEDIA_MAX_VIDEOS = 8;
// Change to "raw" to show source text with angle-bracket tags instead of rendered rich text.
const DEFAULT_INLINE_TAG_DISPLAY_MODE = "rendered";
var WEBUI_INLINE_TAG_DISPLAY_MODE = DEFAULT_INLINE_TAG_DISPLAY_MODE;
const INLINE_TAG_DISPLAY_MODE_STORAGE_KEY = "webui_inline_tag_mode";
const LANGUAGE_STORAGE_KEY = "webui_lang";
const UI_LOCALE_STORAGE_KEY = "webui_ui_locale";
const GENDER_VARIANT_STORAGE_KEY = "webui_gender_variant";
const FILTER_PANEL_STORAGE_KEY = "webui_filters_collapsed";
const STORY_SPLITTER_STORAGE_KEY = "webui_story_splitter_width";
const ASSET_SPLITTER_STORAGE_KEY = "webui_asset_splitter_width";
const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
const LEGACY_LANGUAGE = {
  code: "CN",
  label: "Chinese (Simplified)",
  nativeLabel: "\u7b80\u4f53\u4e2d\u6587",
  htmlLang: "zh-CN",
  uiLocale: "zh",
};
const STATE = {
  manifest: null,
  index: null,
  language: null,
  languageInfo: LEGACY_LANGUAGE,
  uiLocale: "zh",
  actorNames: {},        // aid -> [name, ...]
  missionNames: {},      // mission id -> display name
  simActorIds: new Set(),
  rawStoryTypes: new Set(),
  prtsCategoryLabels: {},
  entries: [],
  entryByKey: new Map(),
  filtered: [],
  rows: [],              // flattened tree rows for the virtual list
  totalH: 0,
  selectedKey: null,
  convCache: new Map(),
  missionCache: new Map(),
  archiveMetadataByKey: new Map(),
  archiveResearchById: new Map(),
  archiveMetadataLanguage: "",
  expanded: new Set(),   // group paths the user opened
  filters: createDefaultFilters(),
  sortMode: "natural",
  showEmpty: false,
  showRaw: false,
  filtersCollapsed: false,
  indexRequestToken: 0,
  inlineImageLookupLoaded: false,
  inlineImageLookupPromise: null,
  inlineImageAssetByStem: new Map(),
  inlineImageAssetByNumber: new Map(),
  inlineImageSourceRoots: {},
  inlineImageExportRoot: "export_full",
  wikiVideoLookupLoaded: false,
  wikiVideoLookupPromise: null,
  wikiVideoAssetByStem: new Map(),
  genderVariant: null,
  inlineTagDisplayMode: DEFAULT_INLINE_TAG_DISPLAY_MODE,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function createDefaultFilters() {
  return {
    q: "",
    kinds: new Set(),
    dataTypes: new Set(),
    issues: new Set(),
  };
}

function shouldHideLoadedEntry(entry) {
  return !!(entry && entry.omitSimDuplicate);
}

function normalizeLoadedEntries(entries) {
  return (entries || []).filter((entry) => !shouldHideLoadedEntry(entry));
}

function isMobileLayout() {
  return window.matchMedia(MOBILE_LAYOUT_QUERY).matches;
}

function parseCssPixels(value, fallback = 0) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clampNumber(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function initPaneSplitters() {
  setupPaneSplitter({
    container: "#app",
    pane: "#left",
    splitter: "#story-splitter",
    storageKey: STORY_SPLITTER_STORAGE_KEY,
  });
  setupPaneSplitter({
    container: "#asset-app",
    pane: "#asset-left",
    splitter: "#asset-splitter",
    storageKey: ASSET_SPLITTER_STORAGE_KEY,
  });
}

function setupPaneSplitter({ container, pane, splitter, storageKey, minRightWidth = 0 }) {
  const shell = $(container);
  const sidebar = $(pane);
  const handle = $(splitter);
  if (!shell || !sidebar || !handle) return;

  let activePointerId = null;
  let startX = 0;
  let startWidth = 0;
  let wasMobile = isMobileLayout();
  let resizeQueued = false;

  const queueLayoutResize = () => {
    if (resizeQueued) return;
    resizeQueued = true;
    requestAnimationFrame(() => {
      resizeQueued = false;
      window.dispatchEvent(new Event("resize"));
    });
  };

  const readStoredWidth = () => {
    if (!storageKey) return null;
    const raw = storageGet(storageKey);
    const width = Number.parseFloat(raw || "");
    return Number.isFinite(width) ? width : null;
  };

  const writeStoredWidth = (width) => {
    if (!storageKey) return;
    storageSet(storageKey, String(Math.round(width)));
  };

  const currentBounds = () => {
    const paneStyles = window.getComputedStyle(sidebar);
    const handleStyles = window.getComputedStyle(handle);
    const minWidth = parseCssPixels(paneStyles.minWidth, 240);
    const cssMaxWidth = parseCssPixels(paneStyles.maxWidth, Number.POSITIVE_INFINITY);
    const splitterWidth = Math.max(1, parseCssPixels(handleStyles.width, handle.getBoundingClientRect().width || 12));
    const containerWidth = shell.getBoundingClientRect().width;
    const maxByViewport = Math.max(minWidth, containerWidth - splitterWidth - minRightWidth);
    const maxWidth = Number.isFinite(cssMaxWidth)
      ? Math.max(minWidth, Math.min(cssMaxWidth, maxByViewport))
      : maxByViewport;
    return {
      minWidth,
      maxWidth,
    };
  };

  const applyWidth = (width, { persist = true, dispatchResize = true } = {}) => {
    if (isMobileLayout()) {
      sidebar.style.removeProperty("width");
      handle.removeAttribute("aria-valuenow");
      handle.removeAttribute("aria-valuemin");
      handle.removeAttribute("aria-valuemax");
      if (dispatchResize) queueLayoutResize();
      return;
    }

    const bounds = currentBounds();
    const nextWidth = clampNumber(width, bounds.minWidth, bounds.maxWidth);
    sidebar.style.width = `${Math.round(nextWidth)}px`;
    handle.setAttribute("aria-valuemin", String(Math.round(bounds.minWidth)));
    handle.setAttribute("aria-valuemax", String(Math.round(bounds.maxWidth)));
    handle.setAttribute("aria-valuenow", String(Math.round(nextWidth)));
    if (persist) writeStoredWidth(nextWidth);
    if (dispatchResize) queueLayoutResize();
  };

  const syncWidth = () => {
    const mobile = isMobileLayout();
    if (mobile) {
      wasMobile = true;
      applyWidth(sidebar.getBoundingClientRect().width, { persist: false, dispatchResize: false });
      return;
    }

    if (shell.getBoundingClientRect().width < 48) {
      return;
    }

    let targetWidth = parseCssPixels(sidebar.style.width, sidebar.getBoundingClientRect().width);
    if (wasMobile || !sidebar.style.width) {
      const stored = readStoredWidth();
      if (stored !== null) targetWidth = stored;
    }
    wasMobile = false;
    applyWidth(targetWidth, { persist: false, dispatchResize: false });
  };

  const stopDragging = () => {
    if (activePointerId === null) return;
    const pointerId = activePointerId;
    activePointerId = null;
    handle.classList.remove("is-dragging");
    document.body.classList.remove("is-resizing-pane");
    try {
      handle.releasePointerCapture(pointerId);
    } catch (_error) {
      // Ignore capture cleanup failures.
    }
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerUp);
    window.removeEventListener("pointercancel", onPointerUp);
    writeStoredWidth(parseCssPixels(sidebar.style.width, sidebar.getBoundingClientRect().width));
  };

  const onPointerMove = (event) => {
    if (event.pointerId !== activePointerId) return;
    applyWidth(startWidth + (event.clientX - startX), { persist: false });
  };

  const onPointerUp = (event) => {
    if (activePointerId !== null && event.pointerId !== activePointerId) return;
    stopDragging();
  };

  handle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || isMobileLayout()) return;
    event.preventDefault();
    activePointerId = event.pointerId;
    startX = event.clientX;
    startWidth = sidebar.getBoundingClientRect().width;
    handle.classList.add("is-dragging");
    document.body.classList.add("is-resizing-pane");
    handle.setPointerCapture?.(event.pointerId);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
  });

  handle.addEventListener("keydown", (event) => {
    if (isMobileLayout()) return;
    const bounds = currentBounds();
    const currentWidth = parseCssPixels(sidebar.style.width, sidebar.getBoundingClientRect().width);
    const step = event.shiftKey ? 48 : 16;
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      applyWidth(currentWidth - step);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      applyWidth(currentWidth + step);
    } else if (event.key === "Home") {
      event.preventDefault();
      applyWidth(bounds.minWidth);
    } else if (event.key === "End") {
      event.preventDefault();
      applyWidth(bounds.maxWidth);
    }
  });

  window.addEventListener("resize", syncWidth);
  syncWidth();
}

function storageGet(key) {
  try { return localStorage.getItem(key); } catch (_) { return null; }
}
function storageSet(key, value) {
  try { localStorage.setItem(key, value); } catch (_) {}
}

function persistFiltersCollapsed(collapsed) {
  storageSet(FILTER_PANEL_STORAGE_KEY, collapsed ? "1" : "0");
}

function resolveInitialFiltersCollapsed() {
  const stored = storageGet(FILTER_PANEL_STORAGE_KEY);
  if (stored === "1") return true;
  if (stored === "0") return false;
  return isMobileLayout();
}


function getLanguageInfo(code) {
  if (!STATE.manifest || !Array.isArray(STATE.manifest.languages)) return LEGACY_LANGUAGE;
  return STATE.manifest.languages.find((lang) => lang.code === code) || LEGACY_LANGUAGE;
}

function resolveUiLocale(info) {
  return info && info.uiLocale ? info.uiLocale : "en";
}

function normalizeUiLocale(locale) {
  const value = String(locale || "").toLowerCase();
  return value === "zh" || value === "en" ? value : "";
}

function persistUiLocaleSelection(locale) {
  storageSet(UI_LOCALE_STORAGE_KEY, locale);
}

function resolveInitialUiLocale(languageCode) {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = normalizeUiLocale(params.get("ui") || params.get("uiLang"));
  if (fromQuery) return fromQuery;

  const stored = normalizeUiLocale(storageGet(UI_LOCALE_STORAGE_KEY));
  if (stored) return stored;

  return resolveUiLocale(getLanguageInfo(languageCode || STATE.language));
}

function applyUiLocaleSideEffects() {
  window.WEBUI_UI_LOCALE = STATE.uiLocale;
  window.dispatchEvent(new CustomEvent("webui:ui-locale-changed", {
    detail: { locale: STATE.uiLocale },
  }));
}

function setUiLocale(locale, { persist = true, refresh = true } = {}) {
  const nextLocale = normalizeUiLocale(locale) || resolveUiLocale(STATE.languageInfo);
  STATE.uiLocale = nextLocale || "en";

  const select = $("#ui-language");
  if (select) select.value = STATE.uiLocale;
  if (persist) persistUiLocaleSelection(STATE.uiLocale);

  applyUiStrings();
  applyUiLocaleSideEffects();

  if (!refresh || !STATE.entries.length) return;

  buildKindChips();
  buildDataTypeChips();
  buildStoryIssueChips();
  applyFilters();

  if (STATE.selectedKey) {
    const cached = STATE.convCache.get(STATE.selectedKey);
    if (cached) renderConv(cached);
  }
}


function dataPath(relativePath, languageCode = STATE.language) {
  if (STATE.manifest && STATE.manifest.legacyRoot) {
    return `data/${relativePath}`;
  }
  return `data/lang/${encodeURIComponent(languageCode)}/${relativePath}`;
}

function clearArchiveClassificationCaches(entries = STATE.entries) {
  for (const entry of entries || []) {
    if (!entry || !isPrtsArchiveEntry(entry)) continue;
    delete entry._prtsCategoryKey;
    delete entry._dataTypesNormalized;
  }
}

function archivePageFromSummary(conv) {
  for (const row of (conv && conv.summary) || []) {
    const text = String(row && row.text || "");
    const match = text.match(/^\s*Page:\s*([A-Za-z0-9_]+)/i);
    const page = match ? normalizePrtsPageCategoryKey(match[1]) : "";
    if (page) return page;
  }
  return "";
}

function uniqueArchiveResearchLinks(links) {
  const out = [];
  const seen = new Set();
  for (const link of links || []) {
    const id = normalizeArchiveResearchId(link && link.id);
    if (!id || seen.has(id)) continue;
    seen.add(id);
    out.push({
      id,
      title: String(link && link.title || "").trim(),
      desc: String(link && link.desc || "").trim(),
      role: String(link && link.role || "").trim(),
    });
  }
  return out;
}

function inferArchiveMetadataFromEntry(entry) {
  const inferredResearchId = inferArchiveResearchId(entry);
  const researchLinks = inferredResearchId
    ? [{ id: inferredResearchId, title: "", desc: "", role: "inferred" }]
    : [];
  return {
    key: String(entry && entry.k || ""),
    page: entryPrtsTagPageKey(entry) || entryPrtsKeyPageKey(entry),
    title: String(entry && (entry.title || entry.k) || ""),
    researchLinks,
    researchIds: researchLinks.map((link) => link.id),
    primaryResearchId: inferredResearchId,
    researchTitle: "",
    researchDesc: "",
  };
}

function archiveMetadataFromConv(entry, conv) {
  const debug = conv && conv._debug ? conv._debug : {};
  const firstLevelSource = debug.firstLevel && debug.firstLevel.source ? debug.firstLevel.source : {};
  const page =
    normalizePrtsPageCategoryKey(firstLevelSource.categoryId) ||
    archivePageFromSummary(conv) ||
    entryPrtsTagPageKey(entry) ||
    entryPrtsKeyPageKey(entry);

  const researchLinks = [];
  for (const row of Array.isArray(debug.linkedResearch) ? debug.linkedResearch : []) {
    const id = normalizeArchiveResearchId(row && row.researchId);
    if (!id) continue;
    researchLinks.push({
      id,
      title: String(row && row.title || "").trim(),
      desc: String(row && row.desc || "").trim(),
      role: "research",
    });
  }
  for (const row of Array.isArray(debug.linkedNotes) ? debug.linkedNotes : []) {
    const id = normalizeArchiveResearchId(row && row.researchId);
    if (!id) continue;
    researchLinks.push({
      id,
      title: "",
      desc: "",
      role: "note",
    });
  }

  const uniqueLinks = uniqueArchiveResearchLinks(researchLinks);
  if (!uniqueLinks.length) {
    const inferredResearchId = inferArchiveResearchId(entry);
    if (inferredResearchId) {
      uniqueLinks.push({ id: inferredResearchId, title: "", desc: "", role: "inferred" });
    }
  }

  const primaryResearch =
    uniqueLinks.find((link) => link.role === "research") ||
    uniqueLinks[0] ||
    null;
  return {
    key: String(entry && entry.k || conv && conv.key || ""),
    page,
    title: String(entry && entry.title || conv && conv.title || entry && entry.k || ""),
    researchLinks: uniqueLinks,
    researchIds: uniqueLinks.map((link) => link.id),
    primaryResearchId: primaryResearch ? primaryResearch.id : "",
    researchTitle: primaryResearch && primaryResearch.role === "research" ? primaryResearch.title : "",
    researchDesc: primaryResearch && primaryResearch.role === "research" ? primaryResearch.desc : "",
  };
}

function archiveMetadataSortKey(meta) {
  const entry = STATE.entryByKey.get(meta && meta.key) || {};
  return [
    String(entry.m || ""),
    String(entry.s || "").padStart(8, "0"),
    String(entry.k || meta && meta.key || ""),
  ].join("\n");
}

function compareArchiveMetadataRows(a, b) {
  return archiveMetadataSortKey(a).localeCompare(archiveMetadataSortKey(b), undefined, { numeric: true });
}

function buildArchiveMetadataIndexes(metadataRows) {
  const byKey = new Map();
  const byResearchId = new Map();

  for (const meta of metadataRows || []) {
    if (!meta || !meta.key) continue;
    byKey.set(meta.key, meta);
    for (const link of meta.researchLinks || []) {
      const id = normalizeArchiveResearchId(link && link.id);
      if (!id) continue;
      const group = byResearchId.get(id) || {
        id,
        title: "",
        desc: "",
        entries: [],
        reports: [],
        materials: [],
      };
      if (link.role === "research" && link.title && !group.title) group.title = link.title;
      if (link.role === "research" && link.desc && !group.desc) group.desc = link.desc;
      if (!group.entries.some((row) => row.key === meta.key)) group.entries.push(meta);
      byResearchId.set(id, group);
    }
  }

  for (const group of byResearchId.values()) {
    group.entries.sort(compareArchiveMetadataRows);
    if (!group.title) {
      const reportWithTitle = group.entries.find((meta) => meta.page === "report" && meta.researchTitle);
      if (reportWithTitle) group.title = reportWithTitle.researchTitle;
    }
    if (!group.desc) {
      const reportWithDesc = group.entries.find((meta) => meta.page === "report" && meta.researchDesc);
      if (reportWithDesc) group.desc = reportWithDesc.researchDesc;
    }
    group.reports = group.entries.filter((meta) => meta.page === "report");
    group.materials = group.entries.filter((meta) => meta.page !== "report");
    for (const meta of group.entries) {
      if (!meta.researchTitle && group.title) meta.researchTitle = group.title;
      if (!meta.researchDesc && group.desc) meta.researchDesc = group.desc;
    }
  }

  return { byKey, byResearchId };
}

async function mapWithConcurrency(items, limit, worker) {
  const rows = new Array(items.length);
  let nextIndex = 0;
  const workerCount = Math.min(Math.max(1, limit || 1), items.length || 1);
  async function runWorker() {
    for (;;) {
      const index = nextIndex++;
      if (index >= items.length) return;
      rows[index] = await worker(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: workerCount }, runWorker));
  return rows;
}

async function ensureArchiveMetadataIndex(languageCode, token = STATE.indexRequestToken) {
  const archiveEntries = STATE.entries.filter(isPrtsArchiveEntry);
  if (!archiveEntries.length) {
    STATE.archiveMetadataLanguage = languageCode;
    STATE.archiveMetadataByKey = new Map();
    STATE.archiveResearchById = new Map();
    return true;
  }

  const rows = await mapWithConcurrency(archiveEntries, 16, async (entry) => {
    try {
      const cached = STATE.convCache.get(entry.k);
      if (cached) return archiveMetadataFromConv(entry, cached);
      const res = await fetch(dataPath(`conv/${encodeURIComponent(entry.k)}.json`, languageCode));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const conv = await res.json();
      return archiveMetadataFromConv(entry, conv);
    } catch (_error) {
      return inferArchiveMetadataFromEntry(entry);
    }
  });

  if (token !== STATE.indexRequestToken || STATE.language !== languageCode) return false;
  const indexes = buildArchiveMetadataIndexes(rows);
  STATE.archiveMetadataLanguage = languageCode;
  STATE.archiveMetadataByKey = indexes.byKey;
  STATE.archiveResearchById = indexes.byResearchId;
  clearArchiveClassificationCaches(archiveEntries);
  return true;
}

function missionDataFile(mission) {
  const files = STATE.index && STATE.index.missionData && STATE.index.missionData.files;
  return files && mission ? (files[mission] || "") : "";
}

function indexedMissionExtras(mission) {
  const extras = STATE.index && STATE.index.missionExtras;
  return extras && mission ? (extras[mission] || null) : null;
}

function cachedMissionData(mission) {
  if (!mission) return null;
  if (STATE.missionCache.has(mission)) return STATE.missionCache.get(mission);
  return null;
}

function getMissionExtras(mission) {
  const indexed = indexedMissionExtras(mission);
  if (indexed) return indexed;
  const cached = cachedMissionData(mission);
  return cached && cached.extras ? cached.extras : null;
}

function getMissionTimelineRecovery(mission) {
  const cached = cachedMissionData(mission);
  return cached && cached.timelineRecovery ? cached.timelineRecovery : null;
}

function getMissionFlow(mission) {
  const cached = cachedMissionData(mission);
  if (cached && cached.flow) return cached.flow;
  const flows = STATE.index && STATE.index.missionFlows;
  return flows && mission ? (flows[mission] || null) : null;
}

async function ensureMissionData(mission, languageCode = STATE.language) {
  if (!mission) return;
  if (STATE.missionCache.has(mission)) return;

  const file = missionDataFile(mission);
  if (!file) {
    STATE.missionCache.set(mission, null);
    return;
  }

  try {
    const res = await fetch(dataPath(file, languageCode));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (STATE.language === languageCode) {
      STATE.missionCache.set(mission, data || null);
    }
  } catch (_error) {
    if (STATE.language === languageCode) {
      STATE.missionCache.set(mission, null);
    }
  }
}

function cleanInlineImageIdValue(value) {
  let text = String(value || "")
    .trim()
    .replace(/&quot;|&#34;/gi, "\"")
    .replace(/&apos;|&#39;/gi, "'")
    .replace(/\\"/g, "\"")
    .replace(/\\'/g, "'");
  for (let i = 0; i < 3; i += 1) {
    const unwrapped = text.replace(/^["']+|["']+$/g, "").trim();
    if (unwrapped === text) break;
    text = unwrapped;
  }
  return text;
}

function normalizeInlineImageId(value) {
  const trimmed = cleanInlineImageIdValue(value).replace(/\\/g, "/");
  if (!trimmed) return "";
  const withoutPrefix = trimmed.replace(/^SNS\/Emoji\//i, "");
  const lastSegment = withoutPrefix.split("/").pop() || withoutPrefix;
  return lastSegment.replace(/\.[^.]+$/i, "").toLowerCase();
}

function inlineImageNumberKey(value) {
  const match = String(value || "").match(/(?:^|[_-])(\d{1,3})$/);
  if (!match) return "";
  return String(Number(match[1]));
}

function scoreInlineImageAsset(rel, stem) {
  const relLower = String(rel || "").toLowerCase();
  let score = 1;
  if (relLower.includes("/sprite/")) score += 40;
  else if (relLower.includes("/texture2d/")) score += 20;
  if (stem.startsWith("deco_sns_tweet_decorate_")) score += 140;
  else if (stem.startsWith("bg_sns_tweet_decorate_")) score += 120;
  else if (stem.startsWith("sns_sticker_")) score += 90;
  else if (stem.startsWith("emoji_")) score += 60;
  else if (stem.includes("sns")) score += 40;
  else if (stem.includes("emoji")) score += 30;
  return score;
}

function rememberBestInlineImageAsset(map, key, candidate) {
  if (!key || !candidate) return;
  const current = map.get(key);
  if (!current || candidate.score > current.score || (
    candidate.score === current.score && candidate.rel.localeCompare(current.rel) < 0
  )) {
    map.set(key, candidate);
  }
}

function isSnsInlineImageStem(stem) {
  const normalized = String(stem || "").toLowerCase();
  return normalized.includes("sns") || normalized.includes("emoji");
}

function ensureInlineImageAssetLookup() {
  if (STATE.inlineImageLookupLoaded) return Promise.resolve();
  if (STATE.inlineImageLookupPromise) return STATE.inlineImageLookupPromise;

  STATE.inlineImageLookupPromise = fetch("data/assets/index.json")
    .then((res) => {
      if (!res.ok) throw new Error(`assets/index.json HTTP ${res.status}`);
      return res.json();
    })
    .then((payload) => {
      const byStem = new Map();
      const byNumber = new Map();
      STATE.inlineImageSourceRoots = payload && payload.sourceRoots ? payload.sourceRoots : {};
      STATE.inlineImageExportRoot = String(payload && payload.root ? payload.root : "export_full");

      for (const raw of payload.entries || []) {
        if (!raw || raw.k !== "image" || !raw.r) continue;
        const rel = String(raw.r || "");
        const parts = rel.split("/").filter(Boolean);
        const name = parts[parts.length - 1] || rel;
        const stem = name.replace(/\.[^.]+$/i, "").toLowerCase();
        if (!stem) continue;

        const score = scoreInlineImageAsset(rel, stem);
        if (score <= 0) continue;

        const candidate = { rel, name, stem, score };
        rememberBestInlineImageAsset(byStem, stem, candidate);

        const numberKey = inlineImageNumberKey(stem);
        if (numberKey && isSnsInlineImageStem(stem)) {
          rememberBestInlineImageAsset(byNumber, numberKey, candidate);
        }
      }

      STATE.inlineImageAssetByStem = byStem;
      STATE.inlineImageAssetByNumber = byNumber;
      STATE.inlineImageLookupLoaded = true;

      if (STATE.selectedKey) {
        const cached = STATE.convCache.get(STATE.selectedKey);
        if (cached) renderConv(cached);
      }
    })
    .catch((_error) => {
      // Keep the story browser usable even if asset lookup fails.
    });

  return STATE.inlineImageLookupPromise;
}

function videoDeviceFolders(deviceType) {
  const normalized = String(deviceType || "").trim().toLowerCase();
  if (normalized === "mouseandkeyboard" || normalized === "pc") return ["PC", "Common"];
  if (normalized === "controller" || normalized === "ct") return ["CT", "Common"];
  if (normalized === "touch" || normalized === "mobile" || normalized === "mb") return ["CT", "Common", "PC"];
  return ["Common", "PC", "CT"];
}

function isBrowserPlayableVideo(rel) {
  return /\.(?:mp4|webm|ogv|ogg|mov|m4v)$/i.test(String(rel || ""));
}

function scoreWikiVideoAsset(asset, deviceType = "") {
  const rel = String(asset && asset.rel || "").replace(/\\/g, "/");
  const relLower = rel.toLowerCase();
  let score = 1;
  const folders = videoDeviceFolders(deviceType).map((folder) => folder.toLowerCase());
  for (let i = 0; i < folders.length; i += 1) {
    if (relLower.includes(`/guide/${folders[i]}/`)) {
      score += 100 - i * 10;
      break;
    }
  }
  if (isBrowserPlayableVideo(rel)) score += 40;
  if (relLower.startsWith("streamingassets-structured/") || relLower.startsWith("persistent-structured/")) score += 10;
  else if (relLower.startsWith("raw_vfs/")) score += 1;
  return score;
}

function ensureWikiVideoAssetLookup() {
  if (STATE.wikiVideoLookupLoaded) return Promise.resolve();
  if (STATE.wikiVideoLookupPromise) return STATE.wikiVideoLookupPromise;

  STATE.wikiVideoLookupPromise = fetch("data/assets/videos.json")
    .then((res) => {
      if (!res.ok) throw new Error(`assets/videos.json HTTP ${res.status}`);
      return res.json();
    })
    .then((payload) => {
      const byStem = new Map();
      if (payload && payload.sourceRoots) {
        STATE.inlineImageSourceRoots = {
          ...(STATE.inlineImageSourceRoots || {}),
          ...payload.sourceRoots,
        };
      }
      STATE.inlineImageExportRoot = String(payload && payload.root ? payload.root : STATE.inlineImageExportRoot || "export_full");

      for (const raw of payload.entries || []) {
        if (!raw || raw.k !== "video" || !raw.r) continue;
        const rel = String(raw.r || "");
        const parts = rel.split("/").filter(Boolean);
        const name = parts[parts.length - 1] || rel;
        const stem = name.replace(/\.[^.]+$/i, "").toLowerCase();
        if (!stem) continue;
        const candidate = { rel, name, stem, size: Number(raw.s) || 0 };
        if (!byStem.has(stem)) byStem.set(stem, []);
        byStem.get(stem).push(candidate);
      }

      for (const list of byStem.values()) {
        list.sort((a, b) => scoreWikiVideoAsset(b) - scoreWikiVideoAsset(a) || a.rel.localeCompare(b.rel));
      }
      STATE.wikiVideoAssetByStem = byStem;
      STATE.wikiVideoLookupLoaded = true;

      if (STATE.selectedKey) {
        const cached = STATE.convCache.get(STATE.selectedKey);
        if (cached) renderConv(cached);
      }
    })
    .catch((_error) => {
      STATE.wikiVideoLookupLoaded = true;
    });

  return STATE.wikiVideoLookupPromise;
}

function resolveInlineImageAsset(imageId) {
  const normalized = normalizeInlineImageId(imageId);
  if (!normalized) return null;

  const exact = STATE.inlineImageAssetByStem.get(normalized);
  if (exact) return exact;

  const gender = resolveGenderVariant();
  const gendered = STATE.inlineImageAssetByStem.get(`${normalized}_${gender}`);
  if (gendered) return gendered;
  for (const suffix of ["m", "f"]) {
    const fallback = STATE.inlineImageAssetByStem.get(`${normalized}_${suffix}`);
    if (fallback) return fallback;
  }

  if (normalized.startsWith("sns_image_")) {
    const cgImage = STATE.inlineImageAssetByStem.get(`cg_image_${normalized.slice("sns_image_".length)}`);
    if (cgImage) return cgImage;
  }

  const numberKey = inlineImageNumberKey(normalized);
  if (!numberKey) return null;

  const padded2 = numberKey.padStart(2, "0");
  const preferredStems = [
    `deco_sns_tweet_decorate_${padded2}`,
    `bg_sns_tweet_decorate_${padded2}`,
    `sns_sticker_${padded2}`,
    `emoji_02_${numberKey.padStart(3, "0")}`,
    `emoji_01_${numberKey.padStart(3, "0")}`,
  ];
  for (const stem of preferredStems) {
    const match = STATE.inlineImageAssetByStem.get(stem);
    if (match) return match;
  }

  return STATE.inlineImageAssetByNumber.get(numberKey) || null;
}

function resolveExactImageAsset(imageId) {
  const normalized = normalizeInlineImageId(imageId);
  if (!normalized) return null;

  const exact = STATE.inlineImageAssetByStem.get(normalized);
  if (exact) return exact;

  const gender = resolveGenderVariant();
  const gendered = STATE.inlineImageAssetByStem.get(`${normalized}_${gender}`);
  if (gendered) return gendered;
  for (const suffix of ["m", "f"]) {
    const fallback = STATE.inlineImageAssetByStem.get(`${normalized}_${suffix}`);
    if (fallback) return fallback;
  }

  return null;
}

function wikiMediaCandidateIds(value) {
  const normalized = normalizeInlineImageId(value);
  if (!normalized) return [];

  const ids = [];
  const push = (id) => {
    const key = normalizeInlineImageId(id);
    if (key && !ids.includes(key)) ids.push(key);
  };

  push(normalized);

  if (normalized.startsWith("wiki_")) {
    push(normalized.slice("wiki_".length));
  }
  if (normalized.startsWith("wiki_item_")) {
    push(`item_${normalized.slice("wiki_item_".length)}`);
  } else if (normalized.startsWith("wiki_wpn_")) {
    push(`wpn_${normalized.slice("wiki_wpn_".length)}`);
  } else if (normalized.startsWith("wiki_eny_")) {
    push(`eny_${normalized.slice("wiki_eny_".length)}`);
  }

  const guidePrefixes = [
    "sketch_guide_video_",
    "guide_video_",
    "wiki_video_tut_adv_",
    "wiki_video_",
    "video_",
  ];
  for (const prefix of guidePrefixes) {
    if (!normalized.startsWith(prefix)) continue;
    const suffix = normalized.slice(prefix.length);
    if (!suffix) continue;
    push(suffix);
    push(`image_${suffix}`);
    push(`wiki_pic_${suffix}`);
    push(`guide_pic_${suffix}`);
    for (let i = 1; i <= 5; i += 1) {
      push(`guide_pic_${suffix}_${i}`);
      push(`wiki_pic_${suffix}_${i}`);
    }
  }

  return ids;
}

function wikiDebugSourceSource(debug) {
  if (!debug || !debug.source) return {};
  if (debug.source.source && typeof debug.source.source === "object") {
    return debug.source.source;
  }
  return debug.table && typeof debug.source === "object"
    ? debug.source
    : {};
}

function collectWikiMediaCandidates(conv) {
  if (!conv || conv.kind !== "wiki") return [];
  const candidates = [];
  const seen = new Set();

  const add = (value, label = "") => {
    for (const id of wikiMediaCandidateIds(value)) {
      if (seen.has(id)) continue;
      seen.add(id);
      candidates.push({ id, label: label || String(value || id) });
    }
  };

  add(conv.key);
  const convSource = wikiDebugSourceSource(conv._debug);
  add(convSource.refItemId, convSource.refItemId);
  add(convSource.refMonsterTemplateId, convSource.refMonsterTemplateId);

  for (const line of conv.lines || []) {
    const debugSource = wikiDebugSourceSource(line && line._debug);
    add(debugSource.image, debugSource.image || (line && line.hint));
    add(debugSource.video, debugSource.video || (line && line.hint));
    add(debugSource.id, line && line.hint);
    if (Array.isArray(debugSource.refWikiEntryIds)) {
      for (const refId of debugSource.refWikiEntryIds) add(refId, refId);
    }
    if (line && Array.isArray(line.images)) {
      for (const imageId of line.images) add(imageId, imageId);
    }
    if (line && line.image) add(line.image, line.image);
  }

  return candidates;
}

function wikiImageAssetsForConv(conv) {
  if (!STATE.inlineImageLookupLoaded) return [];

  const out = [];
  const seenRel = new Set();
  for (const candidate of collectWikiMediaCandidates(conv)) {
    const asset = resolveExactImageAsset(candidate.id);
    if (!asset || seenRel.has(asset.rel)) continue;
    seenRel.add(asset.rel);
    out.push({ ...asset, label: candidate.label || asset.name });
    if (out.length >= WIKI_MEDIA_MAX_IMAGES) break;
  }
  return out;
}

function collectWikiVideoCandidates(conv) {
  if (!conv || conv.kind !== "wiki") return [];
  const candidates = [];
  const seen = new Set();

  const add = (value, { label = "", deviceType = "" } = {}) => {
    const id = normalizeInlineImageId(value);
    if (!id || seen.has(`${id}\u0000${deviceType}`)) return;
    seen.add(`${id}\u0000${deviceType}`);
    candidates.push({ id, label: label || String(value || id), deviceType });
  };

  for (const line of conv.lines || []) {
    const debugSource = wikiDebugSourceSource(line && line._debug);
    add(debugSource.video, {
      label: (line && line.hint) || debugSource.video,
      deviceType: debugSource.videoDeviceType || "",
    });
  }

  return candidates;
}

function wikiVideoCandidateStems(videoId) {
  const normalized = normalizeInlineImageId(videoId);
  if (!normalized) return [];
  const stems = [normalized];
  const push = (stem) => {
    const key = normalizeInlineImageId(stem);
    if (key && !stems.includes(key)) stems.push(key);
  };

  if (normalized.endsWith("_mb")) {
    const base = normalized.slice(0, -3);
    push(`${base}_ct`);
    push(base);
    push(`${base}_pc`);
  } else if (normalized.endsWith("_ct") || normalized.endsWith("_pc")) {
    push(normalized.replace(/_(?:ct|pc)$/i, ""));
  }

  return stems;
}

function resolveExactVideoAsset(videoId, deviceType = "") {
  const matches = [];
  const seenRel = new Set();
  for (const stem of wikiVideoCandidateStems(videoId)) {
    for (const match of STATE.wikiVideoAssetByStem.get(stem) || []) {
      if (seenRel.has(match.rel)) continue;
      seenRel.add(match.rel);
      matches.push(match);
    }
  }
  if (!matches.length) return null;
  return matches
    .sort((a, b) => scoreWikiVideoAsset(b, deviceType) - scoreWikiVideoAsset(a, deviceType) || a.rel.localeCompare(b.rel))[0] || null;
}

function wikiVideoAssetsForConv(conv) {
  if (!STATE.wikiVideoLookupLoaded) return [];

  const out = [];
  const seenRel = new Set();
  for (const candidate of collectWikiVideoCandidates(conv)) {
    const asset = resolveExactVideoAsset(candidate.id, candidate.deviceType);
    if (!asset || seenRel.has(asset.rel)) continue;
    seenRel.add(asset.rel);
    out.push({
      ...asset,
      label: candidate.label || asset.name,
      deviceType: candidate.deviceType || "",
    });
    if (out.length >= WIKI_MEDIA_MAX_VIDEOS) break;
  }
  return out;
}

function renderWikiVideoItem(asset) {
  const src = exportedAssetHref(asset.rel);
  const item = document.createElement("figure");
  item.className = "wiki-video-item";

  if (isBrowserPlayableVideo(asset.rel)) {
    const video = document.createElement("video");
    video.className = "wiki-video-player";
    video.src = src;
    video.controls = true;
    video.preload = "metadata";
    video.setAttribute("playsinline", "");
    item.appendChild(video);
  } else {
    const link = document.createElement("a");
    link.className = "wiki-video-file";
    link.href = src;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = asset.name || asset.label || asset.rel;
    item.appendChild(link);
  }

  const caption = document.createElement("figcaption");
  caption.className = "wiki-image-caption";
  caption.textContent = asset.deviceType
    ? `${asset.label || asset.name} (${asset.deviceType})`
    : (asset.label || asset.name || asset.rel);
  item.appendChild(caption);
  return item;
}

function renderWikiMediaBlock(conv) {
  const imageAssets = wikiImageAssetsForConv(conv);
  const videoAssets = wikiVideoAssetsForConv(conv);
  if (!imageAssets.length && !videoAssets.length) return null;

  const box = document.createElement("div");
  box.className = "summary-box wiki-media-box";

  const label = document.createElement("div");
  label.className = "summary-label";
  label.textContent = uiText("wikiMedia");
  box.appendChild(label);

  const grid = document.createElement("div");
  grid.className = "wiki-image-grid";
  for (const asset of imageAssets) {
    const src = exportedAssetHref(asset.rel);
    const item = document.createElement("figure");
    item.className = "wiki-image-item inline-image-tag has-preview";
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.title = asset.name || asset.label || asset.rel;
    item.setAttribute("aria-label", asset.name || asset.label || asset.rel);
    item.dataset.inlineImageId = asset.stem || asset.label || asset.name || asset.rel;
    item.dataset.inlineImageSrc = src;
    item.dataset.inlineImageName = asset.name || asset.label || asset.rel;

    const img = document.createElement("img");
    img.className = "wiki-image-thumb";
    img.src = src;
    img.alt = asset.label || asset.name || asset.rel;
    img.loading = "lazy";
    item.appendChild(img);

    const caption = document.createElement("figcaption");
    caption.className = "wiki-image-caption";
    caption.textContent = asset.label || asset.name || asset.rel;
    item.appendChild(caption);
    grid.appendChild(item);
  }
  for (const asset of videoAssets) {
    grid.appendChild(renderWikiVideoItem(asset));
  }
  box.appendChild(grid);
  return box;
}

function persistLanguageSelection(languageCode) {
  storageSet(LANGUAGE_STORAGE_KEY, languageCode);
}

function resolveInitialLanguage() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = (params.get("lang") || "").toUpperCase();
  if (fromQuery && getLanguageInfo(fromQuery).code === fromQuery) return fromQuery;

  const stored = (storageGet(LANGUAGE_STORAGE_KEY) || "").toUpperCase();
  if (stored && getLanguageInfo(stored).code === stored) return stored;

  return (STATE.manifest && STATE.manifest.defaultLanguage) || LEGACY_LANGUAGE.code;
}

function applyUiStrings() {
  document.documentElement.lang = STATE.uiLocale === "zh" ? "zh-CN" : "en";

  $("#shell-title").textContent = uiText("suiteTitle");
  $("#shell-subtitle").textContent = uiText("suiteSubtitle");
  $("#story-tab").textContent = uiText("storyTab");
  $("#assets-tab").textContent = uiText("assetsTab");
  $("#ui-language-label").textContent = uiText("uiLanguage");

  const uiLanguageSelect = $("#ui-language");
  if (uiLanguageSelect) {
    const zhOption = uiLanguageSelect.querySelector('option[value="zh"]');
    const enOption = uiLanguageSelect.querySelector('option[value="en"]');
    if (zhOption) zhOption.textContent = uiText("uiLanguageChinese");
    if (enOption) enOption.textContent = uiText("uiLanguageEnglish");
  }

  if (!document.body.dataset.activeView || document.body.dataset.activeView === "story") {
    document.title = uiText("pageTitle");
  }
  $("#app-title").textContent = uiText("appTitle");
  $("#count-label").textContent = uiText("countLabel");
  $("#language-label").textContent = uiText("language");
  $("#kind-label").textContent = uiText("kind");
  $("#type-label").textContent = uiText("type");
  $("#story-issue-label").textContent = uiText("storyIssueFilter");
  $("#sort-label").textContent = uiText("sort");
  $("#reset").textContent = uiText("reset");
  const sortSelect = $("#sort");
  if (sortSelect) sortSelect.value = STATE.sortMode || "natural";
  $("#list-meta-label").textContent = uiText("listUnit");
  $("#conv-empty").textContent = uiText("emptyConversation");
  $("#reveal-current").textContent = uiText("revealCurrent");
  $("#show-empty-label").textContent = uiText("showEmpty");
  $("#show-raw-label").textContent = uiText("showRaw");
  const inlineTagMode = $("#inline-tag-mode");
  if (inlineTagMode) {
    $("#inline-tag-mode-label").textContent = uiText("inlineTagMode");
    inlineTagMode.checked = resolveInlineTagDisplayMode() === "raw";
  }
  syncGenderVariantControl();
  $("#q").placeholder = uiText("searchPlaceholder");
  syncRevealCurrentButton();
  syncFilterPanel();
}


function syncFilterPanel() {
  const panel = $("#filter-panel");
  const toggle = $("#filter-toggle");
  const left = $("#left");
  if (!panel || !toggle || !left) return;

  panel.hidden = STATE.filtersCollapsed;
  left.classList.toggle("filters-collapsed", STATE.filtersCollapsed);
  toggle.setAttribute("aria-expanded", String(!STATE.filtersCollapsed));
  toggle.textContent = uiText(STATE.filtersCollapsed ? "showFilters" : "hideFilters");
}

function setFiltersCollapsed(collapsed, { persist = true } = {}) {
  STATE.filtersCollapsed = !!collapsed;
  if (persist) persistFiltersCollapsed(STATE.filtersCollapsed);
  syncFilterPanel();
  requestAnimationFrame(renderList);
}

function buildLanguageSelect() {

  const select = $("#language");
  select.innerHTML = "";
  const languages = (STATE.manifest && STATE.manifest.languages && STATE.manifest.languages.length)
    ? STATE.manifest.languages
    : [LEGACY_LANGUAGE];

  for (const language of languages) {
    const option = document.createElement("option");
    option.value = language.code;
    option.textContent = language.nativeLabel === language.label
      ? language.nativeLabel
      : `${language.nativeLabel} / ${language.label}`;
    select.appendChild(option);
  }
}

function scrollConversationIntoView() {
  if (!isMobileLayout()) return;
  const pane = $("#right");
  if (!pane) return;

  const rect = pane.getBoundingClientRect();
  const threshold = Math.max(96, Math.round(window.innerHeight * 0.18));
  if (rect.top < 0 || rect.top > threshold) {
    pane.scrollIntoView({ block: "start", behavior: "smooth" });
  }
}

function clearConversationPane() {
  STATE.selectedKey = null;
  $("#conv-empty").hidden = false;
  $("#conv").hidden = true;
  $("#conv-title").textContent = "";
  $("#conv-line-order").replaceChildren();
  $("#conv-line-order").hidden = true;
  $("#conv-warnings").replaceChildren();
  $("#conv-warnings").hidden = true;
  $("#conv-related").replaceChildren();
  $("#conv-related").hidden = true;
  $("#conv-meta").textContent = "";
  $("#conv-lines").replaceChildren();
  syncRevealCurrentButton();
}

function showFatalError(error) {
  document.body.innerHTML =
    `<div style="padding:32px;font:14px sans-serif;color:#d6deea;background:#0f1419;height:100vh">
      <h2>Unable to load the webui data bundle</h2>
      <p>${escapeHtml(String(error))}</p>
        <p>Use a local HTTP server to open this page, for example <code>python serve.py</code>.</p>
     </div>`;
}

async function loadManifest() {
  try {
    const res = await fetch("data/manifest.json");
    if (!res.ok) throw new Error(`manifest.json HTTP ${res.status}`);
    const manifest = await res.json();
    if (!manifest.languages || !manifest.languages.length) {
      manifest.languages = [LEGACY_LANGUAGE];
    }
    return manifest;
  } catch (_error) {
    return {
      defaultLanguage: LEGACY_LANGUAGE.code,
      languages: [LEGACY_LANGUAGE],
      legacyRoot: true,
    };
  }
}

async function switchLanguage(languageCode, { preserveSelection = true } = {}) {
  const info = getLanguageInfo(languageCode);
  const previousKey = preserveSelection ? STATE.selectedKey : null;
  const token = ++STATE.indexRequestToken;

  STATE.language = info.code;
  STATE.languageInfo = info;
  STATE.convCache.clear();
  STATE.missionCache.clear();
  persistLanguageSelection(info.code);
  $("#language").value = info.code;
  applyUiStrings();

  try {
    const res = await fetch(dataPath("index.json", info.code));
    if (!res.ok) throw new Error(`index.json HTTP ${res.status}`);
    const index = await res.json();
    if (token !== STATE.indexRequestToken) return;

    STATE.index = index;
    STATE.actorNames = normalizeActorNames(index.actorNames || {});
    STATE.missionNames = index.missionNames || {};
    STATE.entries = normalizeLoadedEntries(index.entries || []);
    STATE.entryByKey = new Map(STATE.entries.map((entry) => [entry.k, entry]));
    STATE.archiveMetadataByKey = new Map();
    STATE.archiveResearchById = new Map();
    STATE.archiveMetadataLanguage = "";
    STATE.simActorIds = computeSimActorIds(STATE.entries);
    STATE.rawStoryTypes = computeRawStoryTypes(STATE.entries);
    await ensureArchiveMetadataIndex(info.code, token);
    if (token !== STATE.indexRequestToken) return;
    STATE.prtsCategoryLabels = computePrtsCategoryLabels(STATE.entries);
    STATE.selectedKey = previousKey && STATE.entries.some((entry) => entry.k === previousKey)
      ? previousKey
      : null;

    $("#count").textContent = STATE.entries.length.toLocaleString();
    buildKindChips();
    buildDataTypeChips();
    buildStoryIssueChips();
    applyFilters();
    window.dispatchEvent(new CustomEvent("webui:language-changed", {
      detail: { language: info.code },
    }));

    if (STATE.selectedKey) {
      await loadConv(STATE.selectedKey);
    } else {
      clearConversationPane();
    }
  } catch (error) {
    if (token !== STATE.indexRequestToken) return;
    showFatalError(error);
  }
}


async function init() {
  try {
    initPaneSplitters();
    STATE.manifest = await loadManifest();
    buildLanguageSelect();
    bindEvents();
    setFiltersCollapsed(resolveInitialFiltersCollapsed(), { persist: false });

    const initialLanguage = resolveInitialLanguage();
    setUiLocale(resolveInitialUiLocale(initialLanguage), { persist: false, refresh: false });
    void ensureInlineImageAssetLookup();
    void ensureWikiVideoAssetLookup();
    await switchLanguage(initialLanguage, { preserveSelection: false });
  } catch (error) {
    showFatalError(error);
  }
}




function sumLeaves(node) {
  let n = 0;
  for (const v of Object.values(node)) {
    n += Array.isArray(v) ? v.length : ((v && Array.isArray(v.items)) ? v.items.length : 0);
  }
  return n;
}

function togglePath(path) {
  // Preserve scroll on expand/collapse.
  const wrap = $("#list-wrap");
  const prevScroll = wrap.scrollTop;
  if (STATE.expanded.has(path)) STATE.expanded.delete(path);
  else STATE.expanded.add(path);

  // Rebuild row offsets without re-running filters.
  // Need to fully rebuild because hidden rows must drop out. The simplest
  // approach is to re-run rebuildTree without going through applyFilters.
  rebuildTree({ resetScroll: false });
  wrap.scrollTop = Math.min(prevScroll, STATE.totalH);
  renderList();
}

function getSelectedEntry() {
  if (!STATE.selectedKey) return null;
  return STATE.entryByKey.get(STATE.selectedKey) || STATE.entries.find((entry) => entry.k === STATE.selectedKey) || null;
}

function entryTreePaths(entry) {
  if (!entry) return [];
  const family = cutsceneFamilyInfo(entry);
  const paths = [];
  for (const dataType of entryTreeDataTypes(entry)) {
    const group = treeGroupInfo(entry, dataType);
    if (dataType) paths.push(dataType);
    if (dataType && group.key) paths.push(`${dataType}/${group.key}`);
    if (dataType && group.key && family && family.pathKey) {
      paths.push(`${dataType}/${group.key}/${family.pathKey}`);
    }
  }
  return paths;
}

function scrollRowIntoView(row) {
  const wrap = $("#list-wrap");
  if (!wrap || !row) return;
  const viewTop = wrap.scrollTop;
  const viewBottom = viewTop + wrap.clientHeight;
  const rowTop = row.top;
  const rowBottom = row.top + row.h;

  if (rowTop < viewTop) {
    wrap.scrollTop = rowTop;
  } else if (rowBottom > viewBottom) {
    wrap.scrollTop = Math.max(0, rowBottom - wrap.clientHeight);
  }
}

function syncRevealCurrentButton() {
  const button = $("#reveal-current");
  if (!button) return;
  button.disabled = !STATE.selectedKey;
}

function revealEntryInTree(entry) {
  if (!entry) return false;

  let expandedChanged = false;
  for (const path of entryTreePaths(entry)) {
    if (!STATE.expanded.has(path)) {
      STATE.expanded.add(path);
      expandedChanged = true;
    }
  }

  if (expandedChanged) {
    rebuildTree({ resetScroll: false });
  }

  const row = STATE.rows.find((candidate) => candidate.type === "item" && candidate.entry.k === entry.k);
  if (!row) return false;

  scrollRowIntoView(row);
  renderList();

  if (isMobileLayout()) {
    const left = $("#left");
    if (left) left.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  return true;
}

// ---------- virtualized rendering with mixed-height rows ----------
function findFirstVisible(scrollTop) {
  const rows = STATE.rows;
  let lo = 0, hi = rows.length - 1, ans = 0;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (rows[mid].top + rows[mid].h <= scrollTop) lo = mid + 1;
    else { ans = mid; hi = mid - 1; }
  }
  return ans;
}

function renderList() {
  const wrap = $("#list-wrap");
  const list = $("#list");
  const total = STATE.rows.length;
  if (!total) { list.replaceChildren(); return; }

  const viewH = wrap.clientHeight;
  const scrollTop = wrap.scrollTop;
  const startTop = Math.max(0, scrollTop - OVERSCAN_PX);
  const endTop = scrollTop + viewH + OVERSCAN_PX;

  let i = findFirstVisible(startTop);
  const frag = document.createDocumentFragment();

  while (i < total && STATE.rows[i].top < endTop) {
    frag.appendChild(renderRow(STATE.rows[i]));
    i++;
  }
  list.replaceChildren(frag);
}

function renderRow(row) {
  if (row.type === "group") return renderGroup(row);
  return renderItem(row);
}

function renderGroup(row) {
  const div = document.createElement("div");
  div.className = `row group lvl-${row.level}` + (row.expanded ? " expanded" : "");
  div.style.top = row.top + "px";
  div.style.height = row.h + "px";
  div.style.paddingLeft = (8 + row.level * 14) + "px";
  div.dataset.path = row.path;
  const labelCls = row.mono ? "label mono" : "label";
  const twisty = row.expanded ? "v" : ">";
  div.innerHTML =
    `<span class="twisty">${twisty}</span>` +
    `<span class="group-main">` +
      `<span class="${labelCls}" title="${escapeHtml(row.label)}">${escapeHtml(row.label)}</span>` +
      (row.raw ? `<span class="sub mono" title="${escapeHtml(row.raw)}">${escapeHtml(row.raw)}</span>` : "") +
    `</span>` +
    `<span class="group-count">${row.count}</span>`;
  return div;
}

function renderItem(row) {
  const e = row.entry;
  const meta = kindMeta(entryGroupedKindKey(e) || e.d);
  const div = document.createElement("div");
  div.className = "row item" + (e.k === STATE.selectedKey ? " selected" : "");
  div.style.top = row.top + "px";
  div.style.height = row.h + "px";
  div.style.paddingLeft = (8 + 2 * 14) + "px";
  div.dataset.key = e.k;

  const kindCls = meta.cls;
  const kindNm = meta.name;
  const actorTxt = e.c.slice(0, 3).map(actorDisplay).join(" / ")
                 + (e.c.length > 3 ? `+${e.c.length - 3}` : "");

  div.innerHTML =
    `<div class="item-line1">` +
      `<span class="badge ${kindCls}">${escapeHtml(kindNm)}</span>` +
      `<span class="item-key">${highlightTextFragment(displayEntryTitle(e), STATE.filters.q)}</span>` +
      `<span class="item-meta">${e.n} ${uiText("lineUnit")}${actorTxt ? " | " + escapeHtml(actorTxt) : ""}</span>` +
    `</div>` +
    `<div class="item-preview">${highlightTextFragment(e.p || uiText("emptyPreview"), STATE.filters.q)}</div>`;
  return div;
}

// ---------- conversation pane ----------
async function loadConv(key) {
  const languageCode = STATE.language;
  STATE.selectedKey = key;
  $$(".item").forEach((n) => n.classList.toggle("selected", n.dataset.key === key));
  syncRevealCurrentButton();

  if (STATE.convCache.has(key)) {
    const cached = STATE.convCache.get(key);
    await ensureMissionData(cached && cached.mission, languageCode);
    if (STATE.selectedKey === key && STATE.language === languageCode) {
      renderConv(cached);
      scrollConversationIntoView();
    }
    return;
  }
  showConvPane();
  scrollConversationIntoView();
  $("#conv-title").textContent = key;
  $("#conv-line-order").replaceChildren();
  $("#conv-line-order").hidden = true;
  $("#conv-warnings").replaceChildren();
  $("#conv-warnings").hidden = true;
  $("#conv-related").replaceChildren();
  $("#conv-related").hidden = true;
  $("#conv-meta").textContent = uiText("loading");
  $("#conv-lines").innerHTML = "";

  try {
    const res = await fetch(dataPath(`conv/${encodeURIComponent(key)}.json`, languageCode));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const conv = await res.json();
    if (STATE.selectedKey === key && STATE.language === languageCode) {
      STATE.convCache.set(key, conv);
      await ensureMissionData(conv && conv.mission, languageCode);
    }
    if (STATE.selectedKey === key && STATE.language === languageCode) {
      renderConv(conv);
    }
  } catch (e) {
    if (STATE.selectedKey === key && STATE.language === languageCode) {
      $("#conv-meta").textContent = uiText("loadErrorPrefix") + (e && e.message ? e.message : String(e));
    }
  }
}

function showConvPane() {
  $("#conv-empty").hidden = true;
  $("#conv").hidden = false;
}

function toContentId(value) {
  const n = Number(value);
  return Number.isInteger(n) ? n : null;
}

function snsLinkMeta(line) {
  const source = line && line._debug ? line._debug.source : null;
  return {
    next: toContentId(source && source.nextContentId),
    pre: toContentId(source && source.preContentId),
  };
}

function collectSnsBranchPath(startCid, lineByCid) {
  const path = [];
  const seen = new Set();
  let cur = startCid;
  while (Number.isInteger(cur) && cur > 0 && !seen.has(cur)) {
    const line = lineByCid.get(cur);
    if (!line) break;
    seen.add(cur);
    path.push(cur);
    const { next } = snsLinkMeta(line);
    if (!Number.isInteger(next) || next <= 0) break;
    cur = next;
  }
  return path;
}

function firstCommonCid(paths) {
  const nonEmpty = paths.filter((path) => path.length);
  if (nonEmpty.length < 2) return null;
  for (const cid of nonEmpty[0]) {
    if (nonEmpty.every((path) => path.includes(cid))) return cid;
  }
  return null;
}

function buildSnsBranchGroups(conv) {
  const byAnchorCid = new Map();
  const skipCids = new Set();
  if (!conv || conv.kind !== "sns" || !Array.isArray(conv.lines)) {
    return { byAnchorCid, skipCids };
  }

  const lineByCid = new Map();
  for (const line of conv.lines) {
    if (Number.isInteger(line.cid)) lineByCid.set(line.cid, line);
  }

  for (const line of conv.lines) {
    if (!line || !Number.isInteger(line.cid) || !line.options || line.options.length < 2) continue;

    const rawPaths = line.options.map((opt) => collectSnsBranchPath(toContentId(opt.next), lineByCid));
    const mergeCid = firstCommonCid(rawPaths);
    const branches = line.options.map((opt, idx) => {
      const branchLines = [];
      for (const cid of rawPaths[idx]) {
        if (mergeCid !== null && cid === mergeCid) break;
        const branchLine = lineByCid.get(cid);
        if (!branchLine) break;
        branchLines.push(branchLine);
        skipCids.add(cid);
      }
      return { option: opt, lines: branchLines };
    });

    byAnchorCid.set(line.cid, { branches, mergeCid });
  }

  return { byAnchorCid, skipCids };
}

function renderSnsBranchLine(line) {
  const item = document.createElement("div");
  item.className = "branch-line";

  const speaker = document.createElement("div");
  speaker.className = "branch-line-speaker";
  const sp = line.speaker || "";
  const display = sp ? speakerName(sp) : uiText("systemSpeaker");
  speaker.innerHTML = escapeHtml(display) +
    (sp ? `<span class="branch-line-speaker-id">${escapeHtml(sp)}</span>` : "");
  item.appendChild(speaker);

  if (line.text) {
    const text = document.createElement("div");
    text.className = "branch-line-text";
    text.innerHTML = highlight(line.text, STATE.filters.q);
    item.appendChild(text);
  } else if (line.linkMission) {
    const system = document.createElement("div");
    system.className = "branch-line-system";
    system.textContent = `-> ${uiText("linkedMission")}: ${line.linkMission}`;
    item.appendChild(system);
  }

  if (line.options && line.options.length) {
    const opts = document.createElement("div");
    opts.className = "options";
    for (const opt of line.options) {
      const o = document.createElement("div");
      o.className = "option";
      o.innerHTML = `- ${highlight(opt.text || "(empty)", STATE.filters.q)} -> #${opt.next}`;
      appendOptionId(o, opt);
      appendDebugTrace(o, opt._debug, "reply option");
      opts.appendChild(o);
    }
    item.appendChild(opts);
  }

  appendLineId(item, line, "branch-line-id");
  appendDebugTrace(item, line._debug, "branch line");
  return item;
}

function renderSnsBranchGroup(group) {
  const block = document.createElement("div");
  block.className = "opt-block opt-block-inline opt-block-sns";

  const optGroup = document.createElement("div");
  optGroup.className = "opt-group opt-group-branches";

  const cols = document.createElement("div");
  cols.className = "branch-columns";
  cols.style.gridTemplateColumns = `repeat(${group.branches.length}, minmax(0, 1fr))`;

  for (const branch of group.branches) {
    const col = document.createElement("div");
    col.className = "branch-column branch-column-sns";

    const head = document.createElement("div");
    head.className = "branch-head";
    head.innerHTML = `- ${highlight(branch.option.text || "(empty)", STATE.filters.q)}`;
    appendOptionId(head, branch.option);
    col.appendChild(head);

    if (branch.lines.length) {
      const lines = document.createElement("div");
      lines.className = "branch-lines";
      for (const line of branch.lines) lines.appendChild(renderSnsBranchLine(line));
      col.appendChild(lines);
    }

    appendDebugTrace(col, branch.option._debug, "reply option");
    cols.appendChild(col);
  }

  optGroup.appendChild(cols);

  if (group.mergeCid !== null) {
    const merge = document.createElement("div");
    merge.className = "branch-merge";
      merge.textContent = "-> " + uiText("commonContinues");
    optGroup.appendChild(merge);
  }

  block.appendChild(optGroup);
  return block;
}

function optionGroupHasBranchContent(grp) {
  const opts = grp && Array.isArray(grp.options) ? grp.options : [];
  if (opts.length < 2) return false;
  const paths = opts.map((opt) => Array.isArray(opt.branchLines) ? opt.branchLines : []);
  if (!paths.some((path) => path.length)) return false;
  return new Set(paths.map((path) => path.join("\u0001"))).size > 1;
}

function optionGroupAnchorId(convKey, g) {
  return `optg-${convKey}-${g}`;
}

function conversationAliasBaseKey(key) {
  const raw = String(key || "");
  if (raw.startsWith("misc_")) return raw.slice(5);
  if (raw.startsWith("env_envTalk_")) return `dlg_${raw.slice("env_envTalk_".length)}`;
  return raw;
}

function resolveConversationEntryKey(rawKey) {
  const key = String(rawKey || "");
  if (!key) return "";
  return resolveFlowConversationKey(key, buildFlowConversationKeyMap()) || "";
}

function isSameConversationSceneKey(sceneKey, conv) {
  const raw = String(sceneKey || "");
  const current = String((conv && conv.key) || "");
  if (!raw || !current) return false;
  if (raw === current) return true;
  const resolved = resolveConversationEntryKey(raw);
  if (resolved && resolved === current) return true;
  return conversationAliasBaseKey(raw) === conversationAliasBaseKey(current);
}

function optionGroupNumberFromOptionId(optionId, convKey) {
  const raw = String(optionId || "");
  const candidates = new Set([
    String(convKey || ""),
    conversationAliasBaseKey(convKey),
  ]);
  for (const key of candidates) {
    if (!key) continue;
    const prefix = `option_${key}_`;
    if (!raw.startsWith(prefix)) continue;
    const m = /^(\d+)_\d+$/.exec(raw.slice(prefix.length));
    if (m) return parseInt(m[1], 10);
  }
  return null;
}

function summarizeOptionTargets(option, conv, outcomesByOptionId) {
  if (!option || !outcomesByOptionId) return [];
  const outcomes = outcomesByOptionId.get(option.id) || [];
  const targets = [];
  const seen = new Set();
  const push = (key, target) => {
    if (seen.has(key)) return;
    seen.add(key);
    targets.push(target);
  };

  const currentGroup = optionGroupNumberFromOptionId(option.id, conv.key);
  const optionBranchLineIds = Array.isArray(option.branchLines) ? option.branchLines : [];

  for (const outcome of outcomes) {
    const firstSceneKey = String(outcome.firstSceneKey || "");
    if (firstSceneKey && !isSameConversationSceneKey(firstSceneKey, conv)) {
      push(`scene:${firstSceneKey}`, { kind: "scene", sceneKey: firstSceneKey });
      continue;
    }

    for (const sk of outcome.submenuSceneKeys || []) {
      if (sk && !isSameConversationSceneKey(sk, conv)) {
        push(`submenu:${sk}`, { kind: "sceneSubmenu", sceneKey: sk });
      }
    }

    const loop = outcome.loop || {};
    const debug = outcome._debug || {};
    const returnOptionIds = (debug.returnOptionIds || []).filter(Boolean);
    // A menu chip is only meaningful when picking the option opens that menu
    // immediately; no dialog lines play in between. If pathLineIds is non-empty
    // or the option has its own branch lines, those lines represent the
    // intervening story, and a "jumps to Menu N" chip on the option header
    // would be misleading. Skip the chip in that case; the next menu still
    // renders inline as a followup of the calling group.
    const pathLineIds = (outcome.pathLineIds || []).filter(Boolean);
    const isDirectMenuJump = pathLineIds.length === 0 && optionBranchLineIds.length === 0;

    if (loop.kind === "sameOptionMenuReturn") {
      if (isDirectMenuJump) push("self", { kind: "selfMenu" });
    } else if (returnOptionIds.length && isDirectMenuJump) {
      const targetGroup = optionGroupNumberFromOptionId(returnOptionIds[0], conv.key);
      if (targetGroup !== null && targetGroup !== currentGroup) {
        const isReturn = currentGroup !== null && targetGroup < currentGroup;
        push(`menu:${targetGroup}`, { kind: "menu", g: targetGroup, isReturn });
      } else if (targetGroup !== null && targetGroup === currentGroup) {
        push("self", { kind: "selfMenu" });
      }
    }

    // Only a direct FinishNode target is the authored "[exit]" choice. If the
    // option plays dialog lines and then reaches a finish node, that is normal
    // story continuation and should not get an end-story chip.
    const terminalKind = String(outcome.terminal || "");
    const outcomeKind = String(outcome.outcomeKind || "");
    const isExplicitExit = terminalKind === "finish"
      && (!outcomeKind || outcomeKind === "terminalOnly")
      && pathLineIds.length === 0
      && optionBranchLineIds.length === 0;
    if (isExplicitExit) push("terminal", { kind: "terminal" });
  }

  return targets;
}

// Forward outcomes including indirect (story-then-menu) paths. Used by the
// layout/pull logic so a sub-menu still renders inline below the group whose
// option ultimately leads into it, even when the chip on that option is
// suppressed because the path plays dialog lines first.
function findOptionForwardMenuOutcomes(option, conv, outcomesByOptionId) {
  if (!option || !outcomesByOptionId) return [];
  const outcomes = outcomesByOptionId.get(option.id) || [];
  const currentGroup = optionGroupNumberFromOptionId(option.id, conv.key);
  const out = [];
  const seen = new Set();
  for (const outcome of outcomes) {
    const firstSceneKey = String(outcome.firstSceneKey || "");
    if (firstSceneKey && !isSameConversationSceneKey(firstSceneKey, conv)) continue;
    const loop = outcome.loop || {};
    if (loop.kind === "sameOptionMenuReturn") continue;
    const debug = outcome._debug || {};
    const returnOptionIds = (debug.returnOptionIds || []).filter(Boolean);
    if (!returnOptionIds.length) continue;
    const targetGroup = optionGroupNumberFromOptionId(returnOptionIds[0], conv.key);
    if (targetGroup === null || targetGroup === currentGroup) continue;
    if (seen.has(targetGroup)) continue;
    seen.add(targetGroup);
    out.push({ g: targetGroup, isReturn: currentGroup !== null && targetGroup < currentGroup });
  }
  return out;
}

function scrollToOptionGroupAnchor(convKey, g) {
  const anchor = document.getElementById(optionGroupAnchorId(convKey, g));
  if (!anchor) return false;
  anchor.scrollIntoView({ block: "center", behavior: "smooth" });
  anchor.classList.remove("opt-group-flash");
  void anchor.offsetWidth;
  anchor.classList.add("opt-group-flash");
  return true;
}

function createOptionGroupAnchorLink(convKey, g, label, extraClass) {
  const link = document.createElement("a");
  link.className = extraClass;
  link.textContent = label;
  link.href = `#${optionGroupAnchorId(convKey, g)}`;
  link.addEventListener("click", (event) => {
    event.preventDefault();
    scrollToOptionGroupAnchor(convKey, g);
  });
  return link;
}

function renderOptionTargetChips(option, conv, outcomesByOptionId, options = {}) {
  const targets = summarizeOptionTargets(option, conv, outcomesByOptionId);
  if (!targets.length) return null;

  // Caller can override the static g-comparison heuristic with the actual
  // render-order signal (a target is a "return" iff it has already rendered or
  // is currently being rendered as an ancestor). This keeps loop arrows correct
  // even when group numbering does not align with visit order.
  const groupByG = new Map();
  for (const grp of conv.optionGroups || []) {
    if (grp && grp.g != null) groupByG.set(grp.g, grp);
  }
  const isReturnOverride = typeof options.isReturnTarget === "function" ? options.isReturnTarget : null;

  const wrap = document.createElement("div");
  wrap.className = "opt-target-chips";

  for (const target of targets) {
    let chip = null;
    if (target.kind === "menu") {
      const targetGroup = groupByG.get(target.g);
      const isReturn = isReturnOverride && targetGroup ? isReturnOverride(targetGroup) : target.isReturn;
      const label = (isReturn ? uiText("optTargetReturnsToMenu") : uiText("optTargetMenu"))
        .replace("{g}", String(target.g));
      chip = createOptionGroupAnchorLink(
        conv.key,
        target.g,
        label,
        "opt-target-chip opt-target-chip-menu" + (isReturn ? " is-return" : "")
      );
    } else if (target.kind === "selfMenu") {
      chip = document.createElement("span");
      chip.className = "opt-target-chip opt-target-chip-self";
      chip.textContent = uiText("optTargetSelfMenu");
    } else if (target.kind === "scene" || target.kind === "sceneSubmenu") {
      const rawSceneKey = String(target.sceneKey || "");
      const resolvedSceneKey = resolveConversationEntryKey(rawSceneKey) || rawSceneKey;
      chip = document.createElement("a");
      chip.className = "opt-target-chip opt-target-chip-scene";
      chip.textContent = (target.kind === "sceneSubmenu" ? uiText("optTargetSceneSubmenu") : uiText("optTargetScene"))
        .replace("{key}", rawSceneKey);
      chip.href = `#${encodeURIComponent(resolvedSceneKey)}`;
      if (resolvedSceneKey && resolvedSceneKey !== rawSceneKey) {
        chip.title = `${rawSceneKey} -> ${resolvedSceneKey}`;
      }
      chip.addEventListener("click", (event) => {
        event.preventDefault();
        loadConv(resolvedSceneKey);
      });
    } else if (target.kind === "terminal") {
      chip = document.createElement("span");
      chip.className = "opt-target-chip opt-target-chip-terminal";
      chip.textContent = uiText("optTargetTerminal");
    }
    if (chip) wrap.appendChild(chip);
  }

  return wrap.childNodes.length ? wrap : null;
}

function renderOptionRiskTags(option) {
  const tags = Array.isArray(option && option.riskTags) ? option.riskTags : [];
  if (!tags.length) return null;
  const wrap = document.createElement("div");
  wrap.className = "opt-risk-tags";
  for (const tag of tags) {
    if (!tag || tag.code !== "inferredFollowingLine") continue;
    const node = document.createElement("span");
    node.className = "opt-risk-tag opt-risk-tag-inferred";
    node.textContent = uiText("optRiskInferredFollowingLine");
    const lineId = String(tag.lineId || "");
    node.title = uiText("optRiskInferredFollowingLineTitle").replace("{line}", lineId || "?");
    wrap.appendChild(node);
  }
  return wrap.childNodes.length ? wrap : null;
}

function findOptionGroupOutcomeBacklinks(group, conv, outcomesByOptionId) {
  const sources = new Map();
  if (!group || !outcomesByOptionId) return sources;
  for (const otherGroup of conv.optionGroups || []) {
    if (otherGroup === group) continue;
    const otherG = otherGroup.g;
    for (const opt of otherGroup.options || []) {
      // The source tag is a direct navigation hint. Indirect story-then-menu
      // paths are useful for layout/pull decisions, but tagging an anchored
      // later group with that source makes normal trunk continuation look like
      // an adjacent submenu jump.
      const hits = summarizeOptionTargets(opt, conv, outcomesByOptionId)
        .filter((target) => target.kind === "menu" && target.g === group.g);
      if (!hits.length) continue;
      const isReturn = hits.some((target) => target.isReturn);
      const existing = sources.get(otherG);
      if (!existing) sources.set(otherG, { g: otherG, isReturn });
      else if (isReturn) existing.isReturn = true;
    }
  }
  return sources;
}

function optionGroupHasForwardOutcomeBacklink(group, conv, outcomesByOptionId) {
  for (const src of findOptionGroupOutcomeBacklinks(group, conv, outcomesByOptionId).values()) {
    if (!src.isReturn) return true;
  }
  return false;
}

function findOutcomeMenuTargetGroups(group, conv, outcomesByOptionId) {
  if (!group || !outcomesByOptionId) return [];
  const groupByG = new Map();
  for (const g of conv.optionGroups || []) {
    if (g && g.g != null) groupByG.set(g.g, g);
  }
  const result = [];
  const seen = new Set();
  for (const opt of group.options || []) {
    for (const target of findOptionForwardMenuOutcomes(opt, conv, outcomesByOptionId)) {
      if (target.isReturn) continue;
      const candidate = groupByG.get(target.g);
      if (!candidate || candidate === group || seen.has(candidate)) continue;
      seen.add(candidate);
      result.push(candidate);
    }
  }
  return result;
}

function renderOptionGroupBacklinks(group, conv, outcomesByOptionId) {
  const sources = findOptionGroupOutcomeBacklinks(group, conv, outcomesByOptionId);
  if (!sources.size) return null;

  const wrap = document.createElement("div");
  wrap.className = "opt-group-sources";
  const label = document.createElement("span");
  label.className = "opt-group-sources-label";
  label.textContent = uiText("optTargetAccessedFrom");
  wrap.appendChild(label);

  const list = Array.from(sources.values()).sort((a, b) => a.g - b.g);
  for (const src of list) {
    wrap.appendChild(createOptionGroupAnchorLink(
      conv.key,
      src.g,
      uiText("optionGroup").replace("{group}", String(src.g)),
      "opt-target-chip opt-target-chip-source" + (src.isReturn ? " is-return" : "")
    ));
  }

  return wrap;
}

function getConvWarnings(conv) {
  return Array.isArray(conv && conv.warnings)
    ? conv.warnings.filter((warning) => warning && warning.code)
    : [];
}

function findConvWarning(conv, code) {
  return getConvWarnings(conv).find((warning) => warning.code === code) || null;
}

function getConvPartialLineOrderWarning(conv) {
  const warning = findConvWarning(conv, "sceneOrderDisorder");
  const lineOrder = warning && warning.lineOrder && typeof warning.lineOrder === "object"
    ? warning.lineOrder
    : null;
  return lineOrder && lineOrder.status === "partial" ? lineOrder : null;
}

function getConvUncoveredLineIds(conv) {
  const lineOrder = getConvPartialLineOrderWarning(conv);
  return lineOrder ? normalizeLineOrderIdList(lineOrder.uncoveredLineIds) : [];
}

function getConvUncoveredLineIdSet(conv) {
  return new Set(getConvUncoveredLineIds(conv));
}

function getConvDuplicateTimestampWarning(conv) {
  return findConvWarning(conv, "duplicateTimestamps");
}

function getConvDuplicateTimestampLineIds(conv) {
  const warning = getConvDuplicateTimestampWarning(conv);
  if (!warning || typeof warning !== "object") return [];
  const direct = normalizeLineOrderIdList(warning.lineIds);
  if (direct.length) return direct;
  const out = [];
  const seen = new Set();
  for (const group of warning.groups || []) {
    for (const lineId of normalizeLineOrderIdList(group && group.lineIds)) {
      if (seen.has(lineId)) continue;
      seen.add(lineId);
      out.push(lineId);
    }
  }
  return out;
}

function getConvDuplicateTimestampLineIdSet(conv) {
  return new Set(getConvDuplicateTimestampLineIds(conv));
}

function warningStatusText(aspect, status) {
  if (status === "direct") return uiText("warningStatusDirect");
  if (status === "partial") return uiText("warningStatusPartial");
  if (status === "fallback") return uiText("warningStatusFallback");
  if (status === "missing") return uiText("warningStatusMissing");
  if (status === "authored") return uiText("warningStatusAuthored");
  if (status === "inferred") return uiText("warningStatusInferred");
  if (status === "notNeeded") return uiText("warningStatusNotNeeded");
  return aspect === "lineOrder" ? uiText("warningStatusFallback") : uiText("warningStatusInferred");
}

function appendWarningDetail(parent, className, text) {
  if (!text) return;
  const node = document.createElement("div");
  node.className = className;
  node.textContent = text;
  parent.appendChild(node);
}

function appendWarningEvidence(parent, evidence) {
  if (!Array.isArray(evidence) || !evidence.length) return;
  const list = document.createElement("ul");
  list.className = "conv-warning-evidence";
  for (const item of evidence) {
    if (!item) continue;
    const li = document.createElement("li");
    li.textContent = String(item);
    list.appendChild(li);
  }
  if (list.childElementCount) parent.appendChild(list);
}

function appendLineIdTagList(parent, labelText, lineIds) {
  const ids = normalizeLineOrderIdList(lineIds);
  if (!ids.length) return;

  const wrap = document.createElement("div");
  wrap.className = "line-id-tag-list";

  if (labelText) {
    const label = document.createElement("div");
    label.className = "line-id-tag-list-label";
    label.textContent = labelText;
    wrap.appendChild(label);
  }

  const row = document.createElement("div");
  row.className = "line-id-tag-list-row";
  for (const lineId of ids) {
    const tag = document.createElement("code");
    tag.className = "line-id-tag";
    tag.textContent = lineId;
    row.appendChild(tag);
  }
  wrap.appendChild(row);
  parent.appendChild(wrap);
}

function sceneOrderWarningAspectCopy(aspectKey, data) {
  if (!data) return { summary: "", detail: "" };
  if (aspectKey === "lineOrder") {
    if (data.reasonCode === "lineIdSuffix" || data.mode === "lineIdSuffix") {
      return {
        summary: uiText("warningLineOrderSummaryLineIdSuffix"),
        detail: uiText("warningLineOrderDetailLineIdSuffix"),
      };
    }
    if (data.status === "missing") {
      return {
        summary: uiText("warningLineOrderSummaryMissing"),
        detail: uiText("warningLineOrderDetailMissing"),
      };
    }
    if (data.status === "fallback") {
      return {
        summary: data.mode ? lineOrderModeText(data.mode) : uiText("warningLineOrderSummaryFallback"),
        detail: uiText("warningLineOrderDetailFallback"),
      };
    }
    if (data.status === "partial") {
      return {
        summary: uiText("warningLineOrderSummaryPartial"),
        detail: uiText("warningLineOrderDetailPartial").replace("{count}", String(data.uncoveredLineCount || 0)),
      };
    }
    return {
      summary: lineOrderModeText(data.mode),
      detail: data.mode ? lineOrderModeDetailText(data.mode) : "",
    };
  }

  if (data.reasonCode === "noTreeReference") {
    return {
      summary: uiText("warningOptionLayoutSummaryNoTreeReference"),
      detail: uiText("warningOptionLayoutDetailNoTreeReference"),
    };
  }
  if (data.reasonCode === "noAuthoredGroupAnchor") {
    return {
      summary: uiText("warningOptionLayoutSummaryNoAuthoredGroupAnchor"),
      detail: uiText("warningOptionLayoutDetailNoAuthoredGroupAnchor"),
    };
  }
  if (data.reasonCode === "partialAuthoredCoverage") {
    return {
      summary: uiText("warningOptionLayoutSummaryPartialAuthoredCoverage"),
      detail: uiText("warningOptionLayoutDetailPartialAuthoredCoverage"),
    };
  }
  return {
    summary: uiText("warningOptionLayoutSummaryInferred"),
    detail: uiText("warningOptionLayoutDetailInferred"),
  };
}

function renderSceneOrderWarningAspect(aspectKey, data) {
  if (!data) return null;
  const section = document.createElement("section");
  section.className = "conv-warning-section";
  const copy = sceneOrderWarningAspectCopy(aspectKey, data);

  const head = document.createElement("div");
  head.className = "conv-warning-section-head";

  const title = document.createElement("div");
  title.className = "conv-warning-section-title";
  title.textContent = uiText(
    aspectKey === "lineOrder" ? "warningAspectLineOrder" : "warningAspectOptionLayout"
  );
  head.appendChild(title);

  const status = document.createElement("span");
  status.className = `conv-warning-status is-${data.status || "unknown"}`;
  status.textContent = warningStatusText(aspectKey, data.status);
  head.appendChild(status);

  section.appendChild(head);
  appendWarningDetail(section, "conv-warning-section-summary", copy.summary || "");
  appendWarningDetail(section, "conv-warning-section-detail", copy.detail || "");
  if (aspectKey === "lineOrder" && Number(data.uncoveredLineCount) > 0) {
    appendWarningDetail(
      section,
      "conv-warning-section-detail conv-warning-section-detail-emphasis",
      uiText("lineOrderUncoveredCount").replace("{count}", String(data.uncoveredLineCount))
    );
    appendLineIdTagList(section, "", data.uncoveredLineIds);
  }
  return section;
}

function shouldRenderSceneOrderWarningAspect(warning, aspectKey) {
  const aspects = Array.isArray(warning && warning.problematicAspects)
    ? warning.problematicAspects
    : [];
  if (aspects.length) return aspects.includes(aspectKey);

  const data = warning && warning[aspectKey];
  if (!data) return false;
  if (aspectKey === "lineOrder") return data.status !== "direct";
  if (aspectKey === "optionLayout") return data.status === "inferred";
  return true;
}

function renderConvWarning(warning) {
  if (!warning || !warning.code) return null;
  let title = uiText("warningTitle");
  let body = "";
  let detailSections = [];
  if (warning.code === "sceneOrderDisorder") {
    title = uiText("warningSceneOrderDisorderTitle");
    body = uiText("warningSceneOrderDisorderBody");
    if (shouldRenderSceneOrderWarningAspect(warning, "lineOrder")) {
      detailSections.push(renderSceneOrderWarningAspect("lineOrder", warning.lineOrder));
    }
    if (shouldRenderSceneOrderWarningAspect(warning, "optionLayout")) {
      detailSections.push(renderSceneOrderWarningAspect("optionLayout", warning.optionLayout));
    }
    detailSections = detailSections.filter(Boolean);
  }
  if (warning.code === "inferredOptionLayout") {
    title = uiText("warningInferredOptionLayoutTitle");
    body = uiText("warningInferredOptionLayoutBody");
  }
  if (warning.code === "duplicateTimestamps") {
    title = uiText("warningDuplicateTimestampsTitle");
    body = uiText("warningDuplicateTimestampsBody");
    detailSections = [];
    for (const group of warning.groups || []) {
      const lineIds = normalizeLineOrderIdList(group && group.lineIds);
      if (!lineIds.length) continue;
      const section = document.createElement("section");
      section.className = "conv-warning-section";
      appendWarningDetail(
        section,
        "conv-warning-section-summary",
        `${group.timestamp || ""} (${lineIds.length})`
      );
      appendLineIdTagList(section, uiText("warningDuplicateTimestampLines"), lineIds);
      detailSections.push(section);
    }
  }
  if (!body) return null;

  const box = document.createElement("div");
  box.className = "conv-warning";

  const label = document.createElement("div");
  label.className = "conv-warning-label";
  label.textContent = title;
  box.appendChild(label);

  const text = document.createElement("div");
  text.className = "conv-warning-text";
  text.textContent = body;
  box.appendChild(text);

  if (detailSections.length) {
    const detail = document.createElement("div");
    detail.className = "conv-warning-details";
    for (const section of detailSections) detail.appendChild(section);
    box.appendChild(detail);
  }

  return box;
}

function convHasWarning(conv, code) {
  return !!findConvWarning(conv, code);
}

function renderableConvWarnings(conv) {
  const warnings = getConvWarnings(conv);
  if (warnings.some((warning) => warning.code === "sceneOrderDisorder")) {
    return warnings.filter((warning) => warning.code !== "inferredOptionLayout");
  }
  return warnings;
}

function lineOrderModeText(mode) {
  if (mode === "dialogTree") return uiText("lineOrderModeDialogTree");
  if (mode === "dialogTreeFragment") return uiText("lineOrderModeDialogTreeFragment");
  if (mode === "dialogTreeExtraConfig") return uiText("lineOrderModeDialogTreeExtraConfig");
  if (mode === "authoredBlend") return uiText("lineOrderModeAuthoredBlend");
  if (mode === "dialogTimeline") return uiText("lineOrderModeDialogTimeline");
  if (mode === "lineIdSuffix") return uiText("lineOrderModeLineIdSuffix");
  if (mode) return `${uiText("lineOrderModeFallback")}: ${mode}`;
  return uiText("lineOrderModeMissing");
}

function lineOrderTone(mode) {
  if (
    mode === "dialogTree"
    || mode === "dialogTreeFragment"
    || mode === "dialogTreeExtraConfig"
    || mode === "authoredBlend"
    || mode === "dialogTimeline"
  ) return "authored";
  if (mode === "lineIdSuffix") return "fallback";
  if (mode) return "fallback";
  return "missing";
}

function lineOrderModeDetailText(mode) {
  if (mode === "dialogTree") return uiText("lineOrderModeDetailDialogTree");
  if (mode === "dialogTreeFragment") return uiText("lineOrderModeDetailDialogTreeFragment");
  if (mode === "dialogTreeExtraConfig") return uiText("lineOrderModeDetailDialogTreeExtraConfig");
  if (mode === "authoredBlend") return uiText("lineOrderModeDetailAuthoredBlend");
  if (mode === "dialogTimeline") return uiText("lineOrderModeDetailDialogTimeline");
  if (mode === "lineIdSuffix") return uiText("lineOrderModeDetailLineIdSuffix");
  if (mode) return uiText("lineOrderModeDetailFallback").replace("{mode}", mode);
  return uiText("lineOrderMissing");
}

function buildLineIdReferenceOrder(lineIds) {
  const rows = normalizeLineOrderIdList(lineIds).map((lineId, idx) => ({
    lineId,
    idx,
    suffix: lineOrderNumericSuffix(lineId),
  }));
  const hasUniqueNumericSuffixes =
    rows.length
    && rows.every((row) => row.suffix !== null)
    && new Set(rows.map((row) => row.suffix)).size === rows.length;
  rows.sort((left, right) => {
    if (hasUniqueNumericSuffixes) {
      if (left.suffix !== right.suffix) return left.suffix - right.suffix;
      return left.idx - right.idx;
    }
    const byId = left.lineId.localeCompare(right.lineId);
    return byId || (left.idx - right.idx);
  });
  return rows.map((row) => row.lineId);
}

function createLineOrderStatChip(text, tone = "") {
  const chip = document.createElement("span");
  chip.className = "line-order-chip" + (tone ? ` is-${tone}` : "");
  chip.textContent = text;
  return chip;
}

function lineOrderNumericSuffix(raw) {
  const match = /_(\d+)$/.exec(String(raw || ""));
  return match ? parseInt(match[1], 10) : null;
}

function normalizeLineOrderIdList(values) {
  return Array.isArray(values)
    ? values.map((value) => String(value || "").trim()).filter(Boolean)
    : [];
}

function lineOrderIdListEquals(left, right) {
  const a = normalizeLineOrderIdList(left);
  const b = normalizeLineOrderIdList(right);
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

function lineOrderUniqueList(values) {
  return Array.from(new Set(normalizeLineOrderIdList(values)));
}

function lineOrderGroupOptionIdSet(group) {
  return new Set(
    (Array.isArray(group && group.options) ? group.options : [])
      .map((option) => String(option && option.id || ""))
      .filter(Boolean)
  );
}

function lineOrderReturnOptionIds(outcome) {
  const debug = outcome && outcome._debug && typeof outcome._debug === "object"
    ? outcome._debug
    : null;
  return normalizeLineOrderIdList(debug && debug.returnOptionIds);
}

function isLineOrderSharedContinuationGroup(group, candidate, outcomesByOptionId, convKey) {
  const options = Array.isArray(group && group.options) ? group.options : [];
  const candidateOptionIds = lineOrderGroupOptionIdSet(candidate);
  if (!options.length || !candidateOptionIds.size) return false;

  return options.every((option) => {
    const outcomes = (outcomesByOptionId.get(option.id) || []).filter((outcome) => {
      const firstSceneKey = String(outcome.firstSceneKey || "");
      return !firstSceneKey || isSameConversationSceneKey(firstSceneKey, { key: convKey });
    });
    return outcomes.some((outcome) => {
      return lineOrderReturnOptionIds(outcome).some((optionId) => candidateOptionIds.has(optionId));
    });
  });
}

function findLineOrderContinuationGroups(group, ctx) {
  if (!optionGroupHasBranchContent(group) || !ctx || !ctx.groupsByLineId || !ctx.outcomesByOptionId) {
    return [];
  }
  const groups = [];
  const seen = new Set();
  for (const option of group.options || []) {
    for (const lineId of normalizeLineOrderIdList(option.branchLines)) {
      for (const candidate of ctx.groupsByLineId.get(lineId) || []) {
        if (!candidate || candidate === group || seen.has(candidate)) continue;
        if (!isLineOrderSharedContinuationGroup(group, candidate, ctx.outcomesByOptionId, ctx.conv.key)) continue;
        groups.push(candidate);
        seen.add(candidate);
      }
    }
  }
  return groups;
}

function buildLineOrderOutcomeIndex(conv) {
  const index = new Map();
  for (const link of conv.sceneGraphLinks || []) {
    for (const option of link.options || []) {
      const optionId = String(option && option.optionId || "");
      if (!optionId) continue;
      const signature = JSON.stringify({
        after: link.after || "",
        firstLineId: option.firstLineId || "",
        firstSceneKey: option.firstSceneKey || "",
        pathLineIds: normalizeLineOrderIdList(option.pathLineIds),
        sceneKeys: lineOrderUniqueList(option.sceneKeys),
        submenuSceneKeys: lineOrderUniqueList(option.submenuSceneKeys),
        terminal: option.terminal || "",
        outcomeKind: option.outcomeKind || "",
      });
      const entries = index.get(optionId) || [];
      if (!entries.some((entry) => entry._signature === signature)) {
        entries.push({
          ...option,
          _after: link.after || "",
          _file: link.file || "",
          _sourceKey: link.sourceKey || "",
          _signature: signature,
        });
      }
      index.set(optionId, entries);
    }
  }
  return index;
}

function renderCutsceneInfoPanel(conv) {
  const cs = conv.cutscene;
  if (!cs) return null;

  const box = document.createElement("div");
  box.className = "summary-box cutscene-info-box";

  const label = document.createElement("div");
  label.className = "summary-label";
  label.textContent = uiText("cutsceneInfo") || "Cutscene";
  box.appendChild(label);

  // Flag badges
  const flags = [];
  if (cs.isTransition) flags.push(["Transition", "cs-flag-transition"]);
  if (cs.useBlackScreen) flags.push(["Black Screen", "cs-flag-black"]);
  if (cs.hasSubtitleTrack) flags.push(["Subtitle Track", "cs-flag-sub"]);
  if (cs.keepCameraPaths && cs.keepCameraPaths.length) flags.push(["Keep Camera", "cs-flag-cam"]);
  const rootVars = (cs.variants || []).filter((v) => v.part === "root");
  const hasF = rootVars.some((v) => v.name.startsWith("f_"));
  const hasM = rootVars.some((v) => v.name.startsWith("m_"));
  if (hasF && hasM) flags.push(["M/F Variants", "cs-flag-gender"]);
  else if (hasF) flags.push(["Female", "cs-flag-gender"]);
  else if (hasM) flags.push(["Male", "cs-flag-gender"]);
  const meta = cs.metadata || {};
  const skipType = Array.isArray(meta.skipType) ? meta.skipType[0] : meta.skipType;
  if (skipType === 1) flags.push(["Skippable", "cs-flag-skip"]);
  if (flags.length) {
    const row = document.createElement("div");
    row.className = "cs-flags-row";
    for (const [text, cls] of flags) {
      const chip = document.createElement("span");
      chip.className = `cs-flag ${cls}`;
      chip.textContent = text;
      row.appendChild(chip);
    }
    box.appendChild(row);
  }

  const cutsceneTags = Array.from(new Set((cs.tags || []).map((tag) => String(tag || "").trim()).filter(Boolean)));
  if (cutsceneTags.length) {
    const row = document.createElement("div");
    row.className = "cs-pill-row cs-tag-row";
    const lbl = document.createElement("span");
    lbl.className = "cs-row-label";
    lbl.textContent = uiText("tag") || "Tags";
    row.appendChild(lbl);
    for (const tag of cutsceneTags) {
      const pill = document.createElement("span");
      pill.className = "cs-pill cs-tag-pill";
      pill.textContent = tag;
      row.appendChild(pill);
    }
    box.appendChild(row);
  }

  // Technical info row
  const metaParts = [];
  const fps = Array.isArray(meta.targetFrameRate) ? meta.targetFrameRate[0] : meta.targetFrameRate;
  if (fps) metaParts.push(`${fps}fps`);
  const ntt = Array.isArray(meta.narrativeTypeTag) ? meta.narrativeTypeTag[0] : meta.narrativeTypeTag;
  if (ntt != null) metaParts.push(`narrativeType=${ntt}`);
  if (cs.variantCount) metaParts.push(`${cs.variantCount} files`);
  if (conv.lines && conv.lines.length) {
    const n = conv.lines.length;
    metaParts.push(`${n} subtitle line${n === 1 ? "" : "s"}`);
  }
  if (metaParts.length) {
    const row = document.createElement("div");
    row.className = "summary-text cs-meta-row";
    row.textContent = metaParts.join("  ·  ");
    box.appendChild(row);
  }

  // Component breakdown
  const cc = cs.componentCounts || {};
  const ccParts = Object.entries(cc).filter(([, v]) => v > 0).map(([k, v]) => `${k} ×${v}`);
  if (ccParts.length) {
    const row = document.createElement("div");
    row.className = "summary-text cs-components";
    row.textContent = ccParts.join("  ");
    box.appendChild(row);
  }

  // Audio events
  if (cs.audioEvents && cs.audioEvents.length) {
    const row = document.createElement("div");
    row.className = "cs-pill-row";
    const lbl = document.createElement("span");
    lbl.className = "cs-row-label";
    lbl.textContent = "Audio";
    row.appendChild(lbl);
    for (const ev of cs.audioEvents) {
      const pill = document.createElement("span");
      pill.className = "cs-pill";
      pill.textContent = ev;
      row.appendChild(pill);
    }
    box.appendChild(row);
  }

  // Actor labels
  if (cs.actorLabels && cs.actorLabels.length) {
    const row = document.createElement("div");
    row.className = "cs-pill-row";
    const lbl = document.createElement("span");
    lbl.className = "cs-row-label";
    lbl.textContent = "Actors";
    row.appendChild(lbl);
    for (const actor of cs.actorLabels) {
      const pill = document.createElement("span");
      pill.className = "cs-pill";
      pill.textContent = actor;
      row.appendChild(pill);
    }
    box.appendChild(row);
  }

  // Asset path
  if (cs.paths && cs.paths[0]) {
    const row = document.createElement("div");
    row.className = "summary-text cs-path";
    row.textContent = cs.paths[0];
    box.appendChild(row);
  }

  return box;
}

function summaryLabelForConv(conv) {
  return conv && (
    ["wiki", "mail", "prts", "responsive"].includes(conv.kind)
    || String(conv.kind || "").startsWith("table_")
  )
    ? uiText("metadata")
    : uiText("summary");
}

function resolveRenderedSpeaker(line, {
  fallback = "",
  allowFallback = false,
} = {}) {
  const aid = line && line.aid ? String(line.aid) : "";
  const rawName = line && line.actor ? String(line.actor) : "";
  const name = rawName || (aid ? actorDisplay(aid) : (allowFallback ? fallback : ""));
  if (!name) return { aid, display: "", original: "" };
  const speaker = formatDlgSpeakerName(name, allowFallback ? fallback : "");
  return {
    aid,
    display: speaker.display || "",
    original: speaker.original || "",
  };
}

function renderLineOrderRecovery(conv) {
  const lineOrder = conv && conv._debug ? conv._debug.lineOrder : null;
  if (!lineOrder) return null;
  const lineOrderWarning = getConvPartialLineOrderWarning(conv);
  const uncoveredLineIds = getConvUncoveredLineIds(conv);
  const uncoveredLineCount = lineOrderWarning
    ? Number(lineOrderWarning.uncoveredLineCount) || uncoveredLineIds.length
    : 0;

  const sources = Array.isArray(lineOrder.sources)
    ? lineOrder.sources.filter((source) => source && typeof source === "object")
    : [];
  const originalLineIds = normalizeLineOrderIdList(lineOrder.originalLineIds);
  const orderedLineIds = normalizeLineOrderIdList(lineOrder.orderedLineIds);
  const finalLineIds = orderedLineIds.length ? orderedLineIds : originalLineIds;
  if (!sources.length && !finalLineIds.length) return null;
  const referenceLineIds = buildLineIdReferenceOrder(finalLineIds);
  const differsFromLineIdOrder =
    finalLineIds.length
    && referenceLineIds.length
    && !lineOrderIdListEquals(finalLineIds, referenceLineIds);

  const strip = document.createElement("div");
  strip.className = "line-order-summary line-order-summary-flat";
  strip.appendChild(createLineOrderStatChip(lineOrderModeText(lineOrder.mode), lineOrderTone(lineOrder.mode)));
  if (differsFromLineIdOrder) {
    strip.appendChild(createLineOrderStatChip(uiText("lineOrderDiffersFromLineIdOrder"), "success"));
  }
  if (uncoveredLineCount > 0) {
    strip.appendChild(
      createLineOrderStatChip(
        uiText("lineOrderUncoveredCount").replace("{count}", String(uncoveredLineCount)),
        "fallback"
      )
    );
  }
  return strip;
}

function renderDialogBranchLine(line, inlineGroups = [], renderOptGroup = null) {
  const item = document.createElement("div");
  item.className = "branch-line";

  const actor = document.createElement("div");
  actor.className = "branch-line-speaker";
  const speaker = resolveRenderedSpeaker(line);
  if (speaker.display || speaker.aid) {
    appendSpeakerLabel(actor, speaker.display, {
      originalName: speaker.original,
      aid: speaker.aid,
      nameClass: "speaker-name",
      aidClass: "branch-line-speaker-id",
    });
  }
  item.appendChild(actor);

  if (line.text) {
    const text = document.createElement("div");
    text.className = "branch-line-text";
    text.innerHTML = highlight(line.text, STATE.filters.q);
    item.appendChild(text);
  }

  appendLineId(item, line, "branch-line-id");

  appendDebugTrace(item, line._debug, "branch line");

  if (inlineGroups.length && typeof renderOptGroup === "function") {
    const block = document.createElement("div");
    block.className = "opt-block opt-block-branch-inline";
    for (const group of inlineGroups) {
      block.appendChild(renderOptGroup(group));
    }
    if (block.childNodes.length) item.appendChild(block);
  }

  return item;
}

function conversationHintRows(conv) {
  const rows = [];
  const seen = new Set();
  for (const line of (conv && conv.lines) || []) {
    const title = String(line && line.hint || "").trim();
    if (!title) continue;
    const isResearch = isResearchHintLine(line);
    const body = isResearch ? String(line && line.text || "").trim() : "";
    const key = [line && line.id || "", title, body].join("\n");
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push({ title, body, isResearch, line });
  }
  return rows;
}

function isResearchHintLine(line) {
  return String(line && line.id || "").startsWith("hint_research");
}

function renderConversationHints(conv) {
  const rows = conversationHintRows(conv);
  if (!rows.length) return null;

  const box = document.createElement("div");
  box.className = "summary-box hint-summary-box";
  const label = document.createElement("div");
  label.className = "summary-label";
  label.textContent = uiText("hints");
  box.appendChild(label);

  for (const row of rows) {
    const entry = document.createElement("div");
    entry.className = "hint-summary-entry";

    const title = document.createElement("div");
    title.className = "summary-text hint-summary-title";
    title.innerHTML = highlight(row.title, STATE.filters.q);
    entry.appendChild(title);

    if (row.body) {
      const body = document.createElement("div");
      body.className = "summary-text hint-summary-text";
      if (isDocumentStyleKind(conv.kind)) body.classList.add("doc-text");
      body.innerHTML = isDocumentStyleKind(conv.kind)
        ? renderDocumentTextHtml(conv.kind, row.body, STATE.filters.q)
        : highlight(row.body, STATE.filters.q);
      entry.appendChild(body);
    }

    box.appendChild(entry);
    appendDebugTrace(entry, row.line && row.line._debug, "hint");
  }

  return box;
}

function archiveLinkTitle(meta) {
  const entry = STATE.entryByKey.get(meta && meta.key) || null;
  if (entry) return displayEntryTitle(entry);
  return String(meta && (meta.title || meta.key) || "");
}

function addArchiveLinkRows(targetMap, rows, currentKey) {
  for (const meta of rows || []) {
    if (!meta || !meta.key || meta.key === currentKey) continue;
    targetMap.set(meta.key, meta);
  }
}

function renderArchiveLinkSection(label, rows) {
  if (!rows.length) return null;
  const section = document.createElement("div");
  section.className = "archive-link-section";

  const heading = document.createElement("div");
  heading.className = "archive-link-heading";
  heading.textContent = label;
  section.appendChild(heading);

  const list = document.createElement("div");
  list.className = "archive-link-list";
  for (const meta of rows) {
    const item = document.createElement("span");
    item.className = "archive-link-entry";

    const link = document.createElement("a");
    link.className = "archive-link";
    link.href = `#${encodeURIComponent(meta.key)}`;
    link.textContent = archiveLinkTitle(meta) || meta.key;
    link.title = meta.key;
    link.addEventListener("click", (event) => {
      event.preventDefault();
      loadConv(meta.key);
    });
    item.appendChild(link);

    const pageLabel = meta.page ? dataTypeLabel(`prtscat:${meta.page}`) : "";
    if (pageLabel) {
      const type = document.createElement("span");
      type.className = "archive-link-type";
      type.textContent = pageLabel;
      item.appendChild(type);
    }
    list.appendChild(item);
  }
  section.appendChild(list);
  return section;
}

function renderArchiveLinksBlock(entry, conv) {
  const key = String(entry && entry.k || conv && conv.key || "");
  if (!key) return null;
  const metadata = entryArchiveMetadata(key);
  if (!metadata || !metadata.researchIds || !metadata.researchIds.length) return null;

  const reportsByKey = new Map();
  const materialsByKey = new Map();
  for (const researchId of metadata.researchIds) {
    const group = STATE.archiveResearchById.get(researchId);
    if (!group) continue;
    addArchiveLinkRows(reportsByKey, group.reports, key);
    addArchiveLinkRows(materialsByKey, group.materials, key);
  }

  const reports = Array.from(reportsByKey.values()).sort(compareArchiveMetadataRows);
  const materials = Array.from(materialsByKey.values()).sort(compareArchiveMetadataRows);
  if (!reports.length && !materials.length) return null;

  const box = document.createElement("div");
  box.className = "summary-box archive-links-box";

  const label = document.createElement("div");
  label.className = "summary-label";
  label.textContent = uiText("archiveLinksHeading");
  box.appendChild(label);

  const reportSection = renderArchiveLinkSection(uiText("archiveReports"), reports);
  if (reportSection) box.appendChild(reportSection);

  const materialSection = renderArchiveLinkSection(uiText("archiveMaterials"), materials);
  if (materialSection) box.appendChild(materialSection);

  return box;
}

function renderConv(conv) {
  if (!conv) return;
  showConvPane();
  $("#conv-title").textContent = displayConvTitle(conv);
  const lineOrderWrap = $("#conv-line-order");
  const lineOrderBlock = renderLineOrderRecovery(conv);
  lineOrderWrap.replaceChildren();
  lineOrderWrap.hidden = !lineOrderBlock;
  if (lineOrderBlock) lineOrderWrap.appendChild(lineOrderBlock);
  const missionExtras = getMissionExtras(conv.mission);

  const meta = [];
  const entry = getSelectedEntry();
  meta.push(`kind=${conv.kind}`);
  if (conv.mission) meta.push(`mission=${conv.mission}`);
  if (conv.scene !== undefined) meta.push(`scene=${conv.scene}`);
  if (conv.chatId) meta.push(`chat=${conv.chatId}`);
  if (conv.relatedMissionId) meta.push(`related=${conv.relatedMissionId}`);
  if (conv.cooldown !== undefined) meta.push(`cooldown=${conv.cooldown}`);
  meta.push(`lines=${conv.lines.length}`);
  if (entry) {
    const metadataTagSummary = entryMetadataTagSummary(entry);
    if (metadataTagSummary) meta.push(`tags=${metadataTagSummary}`);
  }
  if (missionExtras && missionExtras.levelRefs && missionExtras.levelRefs.length) {
    meta.push(`level_refs=${missionExtras.levelRefs.map(formatLevelRef).join(", ")}`);
  }
  $("#conv-meta").textContent = meta.join(" | ");

  const warningWrap = $("#conv-warnings");
  warningWrap.replaceChildren();
  const visibleWarnings = renderableConvWarnings(conv);
  for (const warning of visibleWarnings) {
    const warningNode = renderConvWarning(warning);
    if (warningNode) warningWrap.appendChild(warningNode);
  }
  warningWrap.hidden = warningWrap.childElementCount === 0;

  const relatedWrap = $("#conv-related");
  if (relatedWrap) {
    relatedWrap.replaceChildren();
    const related = Array.isArray(conv.relatedScenes) ? conv.relatedScenes : [];
    if (related.length) {
      const banner = document.createElement("div");
      banner.className = "conv-related-banner";
      const heading = document.createElement("div");
      heading.className = "conv-related-heading";
      heading.textContent = uiText("relatedScenesHeading") || "Shared Unity Timeline";
      banner.appendChild(heading);
      const detail = document.createElement("div");
      detail.className = "conv-related-detail";
      const timelineNames = Array.from(new Set(related.map((r) => r.timeline).filter(Boolean)));
      if (timelineNames.length) {
        const tl = document.createElement("span");
        tl.className = "conv-related-timeline";
        tl.textContent = timelineNames.join(", ");
        detail.appendChild(tl);
      }
      const list = document.createElement("div");
      list.className = "conv-related-list";
      for (const item of related) {
        const link = document.createElement("a");
        link.className = "conv-related-link";
        link.href = `#${encodeURIComponent(item.key)}`;
        link.textContent = item.key;
        link.addEventListener("click", (event) => {
          event.preventDefault();
          loadConv(item.key);
        });
        const count = document.createElement("span");
        count.className = "conv-related-count";
        const own = Number(item.ownLineCount) || 0;
        const sib = Number(item.siblingLineCount) || 0;
        count.textContent = ` (${own + sib} line${(own + sib) === 1 ? "" : "s"} on shared timeline)`;
        const wrap = document.createElement("span");
        wrap.className = "conv-related-entry";
        wrap.appendChild(link);
        wrap.appendChild(count);
        list.appendChild(wrap);
      }
      banner.appendChild(detail);
      banner.appendChild(list);
      relatedWrap.appendChild(banner);
      relatedWrap.hidden = false;
    } else {
      relatedWrap.hidden = true;
    }
  }

  const wrap = $("#conv-lines");
  const frag = document.createDocumentFragment();
  const sceneEnvTalk = missionExtras && missionExtras.sceneEnvTalk
    ? missionExtras.sceneEnvTalk[conv.key]
    : null;
  const snsBranchData = buildSnsBranchGroups(conv);
  const dlgLineById = new Map(conv.lines.map((ln) => [ln.id, ln]));
  const dlgBranchSkipIds = new Set();
  const uncertainOptionLayout = convHasWarning(conv, "inferredOptionLayout");
  const uncoveredLineIdSet = getConvUncoveredLineIdSet(conv);
  const duplicateTimestampLineIdSet = getConvDuplicateTimestampLineIdSet(conv);

  const missionContextBlock = renderMissionContext(missionExtras);
  if (missionContextBlock) frag.appendChild(missionContextBlock);
  const missionTimelineBlock = renderMissionTimelineRecovery(
    getMissionTimelineRecovery(conv.mission),
    conv,
    getMissionFlow(conv.mission)
  );
  if (missionTimelineBlock) frag.appendChild(missionTimelineBlock);

  const hintBlock = renderConversationHints(conv);
  if (hintBlock) frag.appendChild(hintBlock);

  const archiveLinksBlock = renderArchiveLinksBlock(entry, conv);
  if (archiveLinksBlock) frag.appendChild(archiveLinksBlock);

  const wikiMediaBlock = renderWikiMediaBlock(conv);
  if (wikiMediaBlock) frag.appendChild(wikiMediaBlock);

  // Scene summary: display above the lines when present.
  // Cutscenes get a dedicated structured info panel; all other kinds use the
  // generic summary text block.
  if (conv.kind === "cutscene") {
    const csPanel = renderCutsceneInfoPanel(conv);
    if (csPanel) frag.appendChild(csPanel);
  } else if (conv.summary && conv.summary.length) {
    const box = document.createElement("div");
    box.className = "summary-box";
    const label = document.createElement("div");
    label.className = "summary-label";
    label.textContent = summaryLabelForConv(conv);
    box.appendChild(label);
    for (const s of conv.summary) {
      const p = document.createElement("div");
      p.className = "summary-text";
      if (isDocumentStyleKind(conv.kind)) p.classList.add("doc-text");
      p.innerHTML = isDocumentStyleKind(conv.kind)
        ? renderDocumentTextHtml(conv.kind, s.text || "", STATE.filters.q)
        : highlight(s.text || "", STATE.filters.q);
      box.appendChild(p);
      appendDebugTrace(p, s._debug, "summary");
    }
    frag.appendChild(box);
  }

  // Attach option groups to the dialog line after which they render. The
  // authoritative signal is the server-provided `after` field (built from the
  // gap positions in the sparse line numbering: reserved slots with no
  // DialogTextTable entry are player-response slots, so a group `g` lands on
  // the g-th gap). Fall back to the legacy `g == lineIndex` heuristic for old
  // conv files without `after`, and to pre- / orphan-block positions when no
  // attach point matches.
  const lineRawIdx = (ln) => {
    if (!ln || !ln.id) return null;
    const m = /_(\d+)$/.exec(ln.id);
    return m ? parseInt(m[1], 10) : null;
  };
  const lineIdxs = conv.lines.map(lineRawIdx).filter((x) => x !== null);
  const lineIdxSet = new Set(lineIdxs);
  const lineIdSet = new Set(conv.lines.map((ln) => ln && ln.id).filter(Boolean));
  const minLineIdx = lineIdxs.length ? Math.min(...lineIdxs) : 0;
  const groupsByLineId = new Map(); // line id -> [group, ...]
  const preGroups = [];
  const uncertainGroups = [];
  const orphanGroups = [];

  const outcomesByOptionId = buildLineOrderOutcomeIndex(conv);

  for (const grp of conv.optionGroups || []) {
    if (uncertainOptionLayout) {
      uncertainGroups.push(grp);
      continue;
    }
    // Authoritative: when another option's scene-graph outcome forwards into
    // this group, treat it as orphan-positioned regardless of `position` or
    // any g-equals-line-suffix fallback. The builder mislabels sub-menus as
    // "pre" (and the suffix fallback pins them to early intro lines), but the
    // graph data is unambiguous about how they're entered. Renderer pulls
    // these inline below their caller.
    if (!grp.after && optionGroupHasForwardOutcomeBacklink(grp, conv, outcomesByOptionId)) {
      orphanGroups.push(grp);
      continue;
    }
    if (grp.position === "pre") {
      preGroups.push(grp);
      continue;
    }
    if (grp.after) {
      if (lineIdSet.has(grp.after)) {
        if (!groupsByLineId.has(grp.after)) groupsByLineId.set(grp.after, []);
        groupsByLineId.get(grp.after).push(grp);
      } else {
        orphanGroups.push(grp);
      }
      continue;
    }
    if (lineIdxSet.has(grp.g)) {
      const fallbackId = `${conv.key}_${String(grp.g).padStart(3, "0")}`;
      if (!groupsByLineId.has(fallbackId)) groupsByLineId.set(fallbackId, []);
      groupsByLineId.get(fallbackId).push(grp);
    } else if (lineIdxs.length && grp.g < minLineIdx) {
      preGroups.push(grp);
    } else {
      orphanGroups.push(grp);
    }
  }

  const continuationOptGroups = new Set();
  const renderedOptGroups = new Set();
  // Groups pinned to a specific dialog line by `after`; these always render at
  // their anchor, so other callers should never pull them inline (which would
  // otherwise duplicate the group at the caller's position).
  const anchoredOptGroups = new Set();
  for (const grps of groupsByLineId.values()) for (const g of grps) anchoredOptGroups.add(g);
  const optionLayoutCtx = {
    conv,
    groupsByLineId,
    outcomesByOptionId,
  };
  const isPullEligible = (target) => {
    return target
      && !anchoredOptGroups.has(target)
      && !continuationOptGroups.has(target)
      && !renderedOptGroups.has(target);
  };
  const isAnchorRenderEligible = (target) => {
    return target
      && !continuationOptGroups.has(target)
      && !renderedOptGroups.has(target);
  };
  const attachedGroupsForLine = (lineId) => {
    return (groupsByLineId.get(lineId) || []).filter(isAnchorRenderEligible);
  };
  const chipOptions = { isReturnTarget: (target) => renderedOptGroups.has(target) };

  const renderOptGroup = (grp) => {
    const frag = document.createDocumentFragment();
    if (!grp || renderedOptGroups.has(grp)) return frag;
    renderedOptGroups.add(grp);

    const g = document.createElement("div");
    g.className = "opt-group";
    if (grp && grp.g != null) g.id = optionGroupAnchorId(conv.key, grp.g);
    frag.appendChild(g);

    const h = document.createElement("div");
    h.className = "opt-group-title";
    h.textContent = uiText("optionGroup").replace("{group}", grp.g);
    g.appendChild(h);

    const backlinks = renderOptionGroupBacklinks(grp, conv, outcomesByOptionId);
    if (backlinks) g.appendChild(backlinks);

    const branchHint = grp.branchHint;
    if (branchHint && Array.isArray(branchHint.scenes) && branchHint.scenes.length) {
      const hint = document.createElement("div");
      hint.className = "opt-group-branch-hint";
      const label = document.createElement("span");
      label.className = "opt-group-branch-label";
      label.textContent = uiText("branchHintLabel") || "jumps to";
      hint.appendChild(label);
      const list = document.createElement("span");
      list.className = "opt-group-branch-targets";
      for (let i = 0; i < branchHint.scenes.length; i++) {
        if (i > 0) {
          const sep = document.createTextNode(", ");
          list.appendChild(sep);
        }
        const sceneKey = branchHint.scenes[i];
        const resolvedSceneKey = resolveConversationEntryKey(sceneKey) || sceneKey;
        const link = document.createElement("a");
        link.className = "opt-group-branch-link";
        link.href = `#${encodeURIComponent(resolvedSceneKey)}`;
        link.textContent = sceneKey;
        if (resolvedSceneKey && resolvedSceneKey !== sceneKey) {
          link.title = `${sceneKey} -> ${resolvedSceneKey}`;
        }
        link.addEventListener("click", (event) => {
          event.preventDefault();
          loadConv(resolvedSceneKey);
        });
        list.appendChild(link);
      }
      hint.appendChild(list);
      if (branchHint.timeline) {
        const meta = document.createElement("span");
        meta.className = "opt-group-branch-meta";
        meta.textContent = ` | ${branchHint.timeline}`;
        hint.appendChild(meta);
      }
      g.appendChild(hint);
    }

    const opts = grp.options || [];
    const multi = opts.length >= 2;
    const showBranchContent = optionGroupHasBranchContent(grp);

    if (!multi) {
      const singleFollowups = findOutcomeMenuTargetGroups(grp, conv, outcomesByOptionId)
        .filter(isPullEligible);
      for (const followup of singleFollowups) continuationOptGroups.add(followup);
      for (const opt of opts) {
        const o = document.createElement("div");
        o.className = "option";
        const icon = opt.icon && opt.icon !== "Default"
          ? ` <span class="opt-icon">[${escapeHtml(opt.icon)}]</span>` : "";
        o.innerHTML = `- ${highlight(opt.text || "(empty)", STATE.filters.q)}${icon}`;
        const targetChips = renderOptionTargetChips(opt, conv, outcomesByOptionId, chipOptions);
        if (targetChips) o.appendChild(targetChips);
        const riskTags = renderOptionRiskTags(opt);
        if (riskTags) o.appendChild(riskTags);
        appendOptionId(o, opt);
        appendDebugTrace(o, opt._debug, "option");
        g.appendChild(o);
      }
      for (const followup of singleFollowups) {
        frag.appendChild(renderOptGroup(followup));
      }
      return frag;
    }

    g.classList.add("opt-group-branches");
    const continuationGroups = findLineOrderContinuationGroups(grp, optionLayoutCtx);
    const continuationGroupSet = new Set(continuationGroups);
    const outcomeMenuTargets = findOutcomeMenuTargetGroups(grp, conv, outcomesByOptionId)
      .filter((target) => !continuationGroupSet.has(target) && isPullEligible(target));
    const allFollowupGroups = continuationGroups.concat(outcomeMenuTargets);
    for (const group of allFollowupGroups) continuationOptGroups.add(group);

    const cols = document.createElement("div");
    cols.className = "branch-columns";
    cols.style.gridTemplateColumns = `repeat(${opts.length}, minmax(0, 1fr))`;
    for (const opt of opts) {
      const col = document.createElement("div");
      col.className = "branch-column";
      const icon = opt.icon && opt.icon !== "Default"
        ? ` <span class="opt-icon">[${escapeHtml(opt.icon)}]</span>` : "";
      const head = document.createElement("div");
      head.className = "branch-head";
      head.innerHTML = `- ${highlight(opt.text || "(empty)", STATE.filters.q)}${icon}`;
      const targetChips = renderOptionTargetChips(opt, conv, outcomesByOptionId, chipOptions);
      if (targetChips) head.appendChild(targetChips);
      const riskTags = renderOptionRiskTags(opt);
      if (riskTags) head.appendChild(riskTags);
      appendOptionId(head, opt);
      col.appendChild(head);
      if (showBranchContent && opt.branchLines && opt.branchLines.length) {
        const lines = document.createElement("div");
        lines.className = "branch-lines";
        for (const lid of opt.branchLines) {
          const line = dlgLineById.get(lid);
          if (!line) continue;
          // If this branchLine is another group's anchor (e.g. a back-loop
          // pointing at a menu's lead-in line), skip it: the line already
          // renders in the trunk where that group is anchored, so duplicating
          // it inside this column would just clutter the column.
          const anchorsOtherGroup = (groupsByLineId.get(lid) || [])
            .some((other) => other && other !== grp);
          if (anchorsOtherGroup) continue;
          lines.appendChild(renderDialogBranchLine(
            line,
            attachedGroupsForLine(lid),
            renderOptGroup
          ));
        }
        if (lines.childNodes.length) col.appendChild(lines);
      }
      appendDebugTrace(col, opt._debug, "option");
      cols.appendChild(col);
    }
    g.appendChild(cols);

    if (!showBranchContent || grp.branchMerge) {
      const merge = document.createElement("div");
      merge.className = "branch-merge";
      merge.textContent = "-> " + uiText("commonContinues");
      g.appendChild(merge);
    }

    for (const group of allFollowupGroups) {
      frag.appendChild(renderOptGroup(group));
    }
    return frag;
  };

  // Pre-dialog option groups (g below the first line index).
  if (preGroups.length) {
    const block = document.createElement("div");
    block.className = "opt-block";
    const label = document.createElement("div");
    label.className = "section-label";
    label.textContent = uiText("preDialogOptions");
    block.appendChild(label);
    for (const grp of preGroups) block.appendChild(renderOptGroup(grp));
    frag.appendChild(block);
  }

  if (conv.kind === "dlg") {
    for (const grp of conv.optionGroups || []) {
      if (!optionGroupHasBranchContent(grp)) continue;
      const afterIdx = lineRawIdx({ id: grp.after || "" }) ?? -1;
      for (const opt of grp.options || []) {
        for (const lid of opt.branchLines || []) {
          const lidIdx = lineRawIdx({ id: lid }) ?? -1;
          if (lidIdx <= afterIdx) continue;
          // A branchLine that points at *another* group's anchor is a
          // back-loop indicator (the option returns the player to that menu's
          // prompt). Skipping the anchor line from the trunk would prevent
          // the anchored group from ever rendering at its real position.
          const anchorsOtherGroup = (groupsByLineId.get(lid) || [])
            .some((other) => other && other !== grp);
          if (anchorsOtherGroup) continue;
          dlgBranchSkipIds.add(lid);
        }
      }
    }
  }

  for (const ln of conv.lines) {
    if (isResearchHintLine(ln)) {
      continue;
    }
    if (conv.kind === "dlg" && ln.id && dlgBranchSkipIds.has(ln.id)) {
      continue;
    }
    if (conv.kind === "sns" && Number.isInteger(ln.cid) && snsBranchData.skipCids.has(ln.cid)) {
      continue;
    }

    const inlineGroups = ln.id ? attachedGroupsForLine(ln.id) : null;
    const snsBranchGroup = conv.kind === "sns" && Number.isInteger(ln.cid)
      ? snsBranchData.byAnchorCid.get(ln.cid)
      : null;
    if (!STATE.showEmpty && !ln.text && !(ln.options && ln.options.length)
        && !ln.linkMission && !(inlineGroups && inlineGroups.length)) continue;
    const branchOnlyNode = Boolean(snsBranchGroup && !ln.text && !ln.hint && !ln.linkMission);

    if (!branchOnlyNode) {
      const row = document.createElement("div");
      row.className = "line"
        + (conv.kind === "radio" ? " radio-line" : "")
        + (conv.kind === "cutscene" ? " cutscene-line" : "")
        + (ln.text ? "" : " empty")
        + (ln.id && uncoveredLineIdSet.has(ln.id) ? " line-uncovered" : "")
        + (ln.id && duplicateTimestampLineIdSet.has(ln.id) ? " line-duplicate-timestamp" : "");

    const actor = document.createElement("div");
    actor.className = "actor";
    if (conv.kind === "cutscene" && ln.cid != null) {
      actor.classList.add("cs-cid");
      actor.textContent = String(ln.cid);
    } else if (conv.kind === "sns") {
      const sp = ln.speaker || "";
      const display = sp ? speakerName(sp) : uiText("systemSpeaker");
      actor.innerHTML = escapeHtml(display) +
        (sp ? `<span class="actor-id">${escapeHtml(sp)}</span>` : "");
    } else {
      // Use the per-line resolved name from the source JSON verbatim.
      // This preserves unrevealed-identity lines and other line-specific forms.
      // Fall back to the aggregated actor display only if needed.
      const speaker = resolveRenderedSpeaker(ln, {
        fallback: conv.kind === "radio" ? uiText("radioSpeaker") : "",
        allowFallback: conv.kind === "radio",
      });
      if (speaker.display || speaker.aid) {
        appendSpeakerLabel(actor, speaker.display, {
          originalName: speaker.original,
          aid: speaker.aid,
        });
      }
    }
    row.appendChild(actor);

    const body = document.createElement("div");
    body.className = "body";
    if (typeof ln.ts === "number") {
      const ts = document.createElement("div");
      ts.className = "line-timestamp";
      ts.title = `${formatTimelineSeconds(ln.ts)}` + (typeof ln.dur === "number" ? `  +${formatTimelineSeconds(ln.dur)}` : "");
      ts.textContent = formatTimelineSeconds(ln.ts);
      body.appendChild(ts);
    }
    if (ln.text) {
      const t = document.createElement("div");
      t.className = "text";
      if (isDocumentStyleKind(conv.kind)) t.classList.add("doc-text");
      t.innerHTML = isDocumentStyleKind(conv.kind)
        ? renderDocumentTextHtml(conv.kind, ln.text, STATE.filters.q)
        : highlight(ln.text, STATE.filters.q);
      body.appendChild(t);
      appendDebugTrace(body, ln._debug, "line");
    } else if (conv.kind === "sns" && ln.linkMission) {
      const t = document.createElement("div");
      t.className = "system";
      t.textContent = `-> ${uiText("linkedMission")}: ${ln.linkMission}`;
      body.appendChild(t);
      appendDebugTrace(body, ln._debug, "line");
    }
    if (ln.options && ln.options.length && !snsBranchGroup) {
      const opts = document.createElement("div");
      opts.className = "options";
      for (const opt of ln.options) {
        const o = document.createElement("div");
        o.className = "option";
        o.innerHTML = `- ${highlight(opt.text || "(empty)", STATE.filters.q)} -> #${opt.next}`;
        appendOptionId(o, opt);
        appendDebugTrace(o, opt._debug, "reply option");
        opts.appendChild(o);
      }
      body.appendChild(opts);
    }
    appendLineId(body, ln);
    if (ln.id && uncoveredLineIdSet.has(ln.id)) {
      appendUncoveredLineBadge(body);
    }
    if (ln.id && duplicateTimestampLineIdSet.has(ln.id)) {
      appendDuplicateTimestampBadge(body);
    }
      row.appendChild(body);
      frag.appendChild(row);
    }

    if (snsBranchGroup) {
      frag.appendChild(renderSnsBranchGroup(snsBranchGroup));
    }

    if (branchOnlyNode) {
      continue;
    }

    // Inline option groups attached to this line (heuristic: option group
    // number matches the line's raw index).
    if (inlineGroups && inlineGroups.length) {
      const block = document.createElement("div");
      block.className = "opt-block opt-block-inline";
      for (const grp of inlineGroups) block.appendChild(renderOptGroup(grp));
      frag.appendChild(block);
    }
  }

  if (sceneEnvTalk && sceneEnvTalk.length) {
    const block = document.createElement("div");
    block.className = "radio-block";
    const label = document.createElement("div");
    label.className = "section-label";
    label.textContent = uiText("envTalk");
    block.appendChild(label);
    for (const env of sceneEnvTalk) {
      const group = document.createElement("div");
      group.className = "radio-group";
      const h = document.createElement("div");
      h.className = "radio-id mono";
      const envNpcName = env.npc && env.npc.name
        ? (stripBraceSegments(env.npc.name) || env.npc.name)
        : "";
      h.textContent = envNpcName ? `${env.id} (${envNpcName})` : env.id;
      group.appendChild(h);
      for (const it of env.lines || []) {
        const row = document.createElement("div");
        row.className = "line radio-line" + (it.text ? "" : " empty");
        const actor = document.createElement("div");
        actor.className = "actor";
        const speaker = resolveRenderedSpeaker(it);
        if (speaker.display || speaker.aid) {
          appendSpeakerLabel(actor, speaker.display, {
            originalName: speaker.original,
            aid: speaker.aid,
          });
        }
        row.appendChild(actor);
        const body = document.createElement("div");
        body.className = "body";
        if (it.text) {
          const t = document.createElement("div");
          t.className = "text";
          t.innerHTML = highlight(it.text, STATE.filters.q);
          body.appendChild(t);
        }
        appendLineId(body, it);
        appendDebugTrace(body, it._debug, "env talk line");
        row.appendChild(body);
        group.appendChild(row);
      }
      if (env.npc) appendDebugTrace(group, env.npc._debug, "env npc");
      if (env._debug && env._debug.sceneBinding) {
        appendDebugTrace(group, env._debug.sceneBinding, "env scene binding");
      }
      appendDebugTrace(group, env._debug, "env talk");
      block.appendChild(group);
    }
    frag.appendChild(block);
  }

  if (uncertainGroups.length) {
    const block = document.createElement("div");
    block.className = "opt-block";
    const label = document.createElement("div");
    label.className = "section-label";
    label.textContent = uiText("uncertainDialogOptions");
    block.appendChild(label);
    for (const grp of uncertainGroups) block.appendChild(renderOptGroup(grp));
    frag.appendChild(block);
  }

  // Orphan option groups: `g` did not match any dialog line index and is not
  // below the first line either, so render a fallback scene-level block.
  // Exclude any group already rendered inline as a continuation/menu target
  // of another group, otherwise the same sub-menu would appear twice.
  const remainingOrphans = orphanGroups.filter((grp) => !continuationOptGroups.has(grp));
  if (remainingOrphans.length) {
    const block = document.createElement("div");
    block.className = "opt-block";
    const label = document.createElement("div");
    label.className = "section-label";
    label.textContent = uiText("orphanDialogOptions");
    block.appendChild(label);
    for (const grp of remainingOrphans) block.appendChild(renderOptGroup(grp));
    frag.appendChild(block);
  }

  wrap.replaceChildren(frag);
  $("#right").scrollTop = 0;
}

function renderMissionContext(missionExtras) {
  if (!missionExtras || !(missionExtras.notes && missionExtras.notes.length)) {
    return null;
  }

  const box = document.createElement("div");
  box.className = "summary-box";

  const label = document.createElement("div");
  label.className = "summary-label";
  label.textContent = uiText("missionNotes");
  box.appendChild(label);

  if (missionExtras.notes && missionExtras.notes.length) {
    for (const note of missionExtras.notes) {
      const p = document.createElement("div");
      p.className = "summary-text";
      p.innerHTML = highlight(note.text || "", STATE.filters.q);
      box.appendChild(p);
      appendDebugTrace(p, note._debug, "mission note");
    }
  }

  return box;
}

function missionTimelineArray(value) {
  return Array.isArray(value) ? value : [];
}

function missionTimelineUniqueStrings(values) {
  const out = [];
  const seen = new Set();
  for (const value of values) {
    const text = String(value || "").trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    out.push(text);
  }
  return out;
}

function missionTimelinePushQuestResourceRef(refs, value, kind = "") {
  const key = String(value || "").trim();
  if (!key) return;
  refs.push({ key, kind: kind || "" });
}

function missionTimelineQuestRefs(quest, flowQuest = null) {
  const refs = [];
  const pushRef = (ref) => {
    if (!ref || typeof ref !== "object") return;
    const key = String(ref.sceneKey || ref.rawId || ref.value || "").trim();
    if (!key) return;
    refs.push({ key, kind: String(ref.kind || "") });
  };

  for (const ref of missionTimelineArray(quest && quest.storyRefs)) pushRef(ref);
  for (const action of missionTimelineArray(quest && quest.clientActions)) {
    for (const ref of missionTimelineArray(action && action.storyRefs)) pushRef(ref);
  }
  for (const objective of missionTimelineArray(quest && quest.objectives)) {
    for (const leaf of missionTimelineArray(objective && objective.conditionLeaves)) {
      for (const ref of missionTimelineArray(leaf && leaf.storyRefs)) pushRef(ref);
    }
  }
  if (flowQuest && typeof flowQuest === "object") {
    for (const key of missionTimelineArray(flowQuest.dialogs)) missionTimelinePushQuestResourceRef(refs, key, "dlg");
    for (const key of missionTimelineArray(flowQuest.cutscenes)) missionTimelinePushQuestResourceRef(refs, key, "cutscene");
    for (const key of missionTimelineArray(flowQuest.remotecomms)) missionTimelinePushQuestResourceRef(refs, key, "remotecomm");
    for (const key of missionTimelineArray(flowQuest.radios)) missionTimelinePushQuestResourceRef(refs, key, "radio");
    for (const anchor of missionTimelineArray(flowQuest.objectiveAnchors)) {
      for (const key of missionTimelineArray(anchor && anchor.storyRefs)) {
        missionTimelinePushQuestResourceRef(refs, key);
      }
    }
  }

  const seen = new Set();
  return refs.filter((ref) => {
    const dedup = ref.kind + "\0" + ref.key;
    if (seen.has(dedup)) return false;
    seen.add(dedup);
    return true;
  });
}

function missionTimelineQuestHasCurrent(quest, flowQuest, flowKeyMap, currentKey) {
  if (!currentKey) return false;
  return missionTimelineQuestRefs(quest, flowQuest).some((ref) => {
    const resolved = resolveFlowConversationKey(ref.key, flowKeyMap);
    return ref.key === currentKey || resolved === currentKey;
  });
}

function missionTimelineSourceTitle(source) {
  if (!source || typeof source !== "object") return "";
  return [source.file, source.field].filter(Boolean).join(" :: ");
}

function appendMissionTimelineChip(row, text, extraClass = "") {
  if (!text) return null;
  const chip = createGraphTextChip(text, extraClass);
  row.appendChild(chip);
  return chip;
}

function missionTimelineAddByQuest(map, questId, value) {
  const key = String(questId || "").trim();
  if (!key) return;
  if (!map.has(key)) map.set(key, []);
  map.get(key).push(value);
}

function buildMissionTimelineResourceContext(flow, timeline) {
  const context = {
    flowQuestById: new Map(),
    mapPinsByQuest: new Map(),
    sceneGraphEdgesByQuest: new Map(),
    sourceEdgesByQuest: new Map(),
  };
  if (flow && typeof flow === "object") {
    for (const quest of missionTimelineArray(flow.quests)) {
      if (quest && quest.id) context.flowQuestById.set(String(quest.id), quest);
    }
    for (const pin of [
      ...missionTimelineArray(flow.mapPins),
      ...missionTimelineArray(flow.scenePins),
    ]) {
      for (const questId of missionTimelineArray(pin && pin.questIds)) {
        missionTimelineAddByQuest(context.mapPinsByQuest, questId, pin);
      }
    }
    for (const edge of missionTimelineArray(flow.sceneGraph && flow.sceneGraph.edges)) {
      for (const questId of missionTimelineArray(edge && edge.questIds)) {
        missionTimelineAddByQuest(context.sceneGraphEdgesByQuest, questId, edge);
      }
    }
  }
  for (const edge of missionTimelineArray(timeline && timeline.sourceBackedSceneEdges)) {
    for (const questId of missionTimelineArray(edge && edge.questIds)) {
      missionTimelineAddByQuest(context.sourceEdgesByQuest, questId, edge);
    }
  }
  return context;
}

function missionTimelinePinLabel(pin) {
  if (!pin || typeof pin !== "object") return "";
  const name = pin.missionAreaId || pin.npcProxyId || pin.scene || pin.trackingType || "";
  const position = pin.position || {};
  const hasPosition = ["x", "y", "z"].some((axis) => position[axis] !== undefined);
  if (!hasPosition) return String(name || "");
  const coords = ["x", "y", "z"].map((axis) => {
    const value = Number(position[axis]);
    return Number.isFinite(value) ? value.toFixed(1) : "?";
  }).join(", ");
  return `${name || pin.scene || "pin"} @ ${coords}`;
}

function missionTimelineFlowLocations(flowQuest, pins) {
  const values = [];
  const push = (value) => {
    const text = String(value || "").trim();
    if (text) values.push(text);
  };
  if (flowQuest && typeof flowQuest === "object") {
    for (const scene of missionTimelineArray(flowQuest.scenes)) push(scene);
    for (const proxy of missionTimelineArray(flowQuest.proxies)) push(proxy);
    for (const tracking of missionTimelineArray(flowQuest.tracking)) {
      push(tracking && tracking.scene);
      push(tracking && tracking.missionAreaId);
      push(tracking && tracking.npcProxyId);
      push(tracking && tracking.jumpId);
    }
    for (const anchor of missionTimelineArray(flowQuest.objectiveAnchors)) {
      for (const scene of missionTimelineArray(anchor && anchor.sceneIds)) push(scene);
      for (const area of missionTimelineArray(anchor && anchor.missionAreaIds)) push(area);
      for (const proxy of missionTimelineArray(anchor && anchor.npcProxyIds)) push(proxy);
      for (const jump of missionTimelineArray(anchor && anchor.jumpIds)) push(jump);
    }
  }
  for (const pin of missionTimelineArray(pins)) {
    push(pin && pin.scene);
    push(pin && pin.missionAreaId);
    push(pin && pin.npcProxyId);
  }
  return missionTimelineUniqueStrings(values);
}

function appendMissionTimelineTextLine(container, label, values, { limit = 8 } = {}) {
  const cleaned = missionTimelineUniqueStrings(values);
  if (!cleaned.length) return;
  const line = document.createElement("div");
  line.className = "mission-timeline-line";
  const labelNode = document.createElement("span");
  labelNode.className = "mission-timeline-line-label";
  labelNode.textContent = label;
  line.appendChild(labelNode);
  for (const value of cleaned.slice(0, limit)) appendMissionTimelineChip(line, value);
  if (cleaned.length > limit) appendMissionTimelineChip(line, `+${cleaned.length - limit}`);
  container.appendChild(line);
}

function renderMissionTimelineSceneRefs(refs, flowKeyMap, currentKey) {
  const cleaned = [];
  const seen = new Set();
  for (const ref of refs) {
    const key = String(ref && ref.key || "").trim();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    cleaned.push(key);
  }
  if (!cleaned.length) return null;

  const row = document.createElement("div");
  row.className = "mission-timeline-line mission-timeline-scenes";
  const label = document.createElement("span");
  label.className = "mission-timeline-line-label";
  label.textContent = uiText("missionTimelineResources");
  row.appendChild(label);
  for (const key of cleaned.slice(0, 12)) {
    row.appendChild(createFlowSceneChip(key, flowKeyMap, currentKey));
  }
  if (cleaned.length > 12) appendMissionTimelineChip(row, `+${cleaned.length - 12}`);
  return row;
}

function renderMissionTimelineTreeNode(node, questById, resourceContext, flowKeyMap, currentKey) {
  const questId = String(node && node.questId || "");
  const quest = questById.get(questId) || {};
  const flowQuest = resourceContext.flowQuestById.get(questId) || null;
  const questPins = resourceContext.mapPinsByQuest.get(questId) || missionTimelineArray(flowQuest && flowQuest.pins);
  const directGraphEdges = [
    ...missionTimelineArray(resourceContext.sceneGraphEdgesByQuest.get(questId)),
    ...missionTimelineArray(resourceContext.sourceEdgesByQuest.get(questId)),
  ];
  const li = document.createElement("li");
  li.className = "mission-timeline-node";
  if (node && node.loop) li.classList.add("is-loop");
  if (node && node.reused) li.classList.add("is-reused");
  if (missionTimelineQuestHasCurrent(quest, flowQuest, flowKeyMap, currentKey)) li.classList.add("is-current");

  const panel = document.createElement("div");
  panel.className = "mission-timeline-node-panel";
  const sourceTitle = missionTimelineSourceTitle(quest.source || node.source);
  if (sourceTitle) panel.title = sourceTitle;

  const head = document.createElement("div");
  head.className = "mission-timeline-node-head";
  const title = document.createElement("span");
  title.className = "mission-timeline-quest-id";
  title.textContent = questId || "?";
  head.appendChild(title);
  const tags = document.createElement("span");
  tags.className = "mission-timeline-tags";
  if (quest.flowIndex !== undefined) appendMissionTimelineChip(tags, `${uiText("missionTimelineFlow")} ${quest.flowIndex}`);
  if (quest.questType !== undefined) appendMissionTimelineChip(tags, `type ${quest.questType}`);
  const prev = missionTimelineArray(quest.prevQuestIds);
  if (prev.length) appendMissionTimelineChip(tags, `${uiText("missionTimelinePrev")} ${prev.join(", ")}`);
  if (quest.failedCondition) appendMissionTimelineChip(tags, uiText("missionTimelineGuard"), "mission-timeline-chip-warn");
  if (node && node.loop) appendMissionTimelineChip(tags, uiText("missionTimelineLoop"), "mission-timeline-chip-warn");
  if (node && node.reused) appendMissionTimelineChip(tags, uiText("missionTimelineReused"));
  head.appendChild(tags);
  panel.appendChild(head);

  const sceneRefs = renderMissionTimelineSceneRefs(
    missionTimelineQuestRefs(quest, flowQuest),
    flowKeyMap,
    currentKey
  );
  if (sceneRefs) panel.appendChild(sceneRefs);

  appendMissionTimelineTextLine(
    panel,
    uiText("missionTimelineLocations"),
    missionTimelineFlowLocations(flowQuest, questPins),
    { limit: 10 }
  );
  appendMissionTimelineTextLine(
    panel,
    uiText("missionTimelineMapPins"),
    missionTimelineArray(questPins).map(missionTimelinePinLabel),
    { limit: 5 }
  );

  appendMissionTimelineTextLine(
    panel,
    uiText("missionTimelineObjectives"),
    missionTimelineArray(quest.objectives).map((objective) => objective && objective.descriptionKey)
  );
  appendMissionTimelineTextLine(
    panel,
    uiText("missionTimelineTracking"),
    missionTimelineArray(quest.objectives).flatMap((objective) =>
      missionTimelineArray(objective && objective.tracking).map((tracking) =>
        tracking && (tracking.missionAreaId || tracking.npcProxyId || tracking.scene || tracking.type)
      )
    )
  );
  appendMissionTimelineTextLine(
    panel,
    uiText("missionTimelineActions"),
    missionTimelineArray(quest.clientActions).map((action) =>
      action && `${action.actionSlot !== undefined ? action.actionSlot + ": " : ""}${action.actionType || "ClientAction"}`
    ),
    { limit: 6 }
  );

  if (node && node.loopPath && node.loopPath.length) {
    appendMissionTimelineTextLine(panel, uiText("missionTimelineLoop"), [node.loopPath.join(" -> ")], { limit: 1 });
  }
  const graphBlock = renderMissionTimelineInlineEdges(directGraphEdges, flowKeyMap, currentKey);
  if (graphBlock) panel.appendChild(graphBlock);

  li.appendChild(panel);
  const children = missionTimelineArray(node && node.children);
  if (children.length) {
    const childList = document.createElement("ul");
    childList.className = "mission-timeline-children";
    for (const child of children) {
      childList.appendChild(renderMissionTimelineTreeNode(child, questById, resourceContext, flowKeyMap, currentKey));
    }
    li.appendChild(childList);
  }
  return li;
}

function renderMissionTimelineTree(nodes, questById, resourceContext, flowKeyMap, currentKey) {
  const list = document.createElement("ul");
  list.className = "mission-timeline-tree";
  for (const node of nodes) {
    list.appendChild(renderMissionTimelineTreeNode(node, questById, resourceContext, flowKeyMap, currentKey));
  }
  return list;
}

const SCENE_ORDER_UNKNOWN = 1_000_000;

function buildMissionTimelineSceneOrderMap(sceneGraph) {
  const map = new Map();
  for (const node of missionTimelineArray(sceneGraph && sceneGraph.nodes)) {
    const key = String(node && node.key || "").trim();
    const order = Number(node && node.order);
    if (key && Number.isFinite(order) && !map.has(key)) {
      map.set(key, order);
    }
  }
  return map;
}

function missionTimelineSceneOrderValue(key, flowKeyMap, sceneOrderMap) {
  const raw = String(key || "").trim();
  if (!raw || !sceneOrderMap || !sceneOrderMap.size) return SCENE_ORDER_UNKNOWN;
  const direct = sceneOrderMap.get(raw);
  if (Number.isFinite(direct)) return direct;
  const resolved = resolveFlowConversationKey(raw, flowKeyMap);
  const resolvedOrder = sceneOrderMap.get(resolved);
  return Number.isFinite(resolvedOrder) ? resolvedOrder : SCENE_ORDER_UNKNOWN;
}

function compareMissionTimelineSceneKeys(a, b, flowKeyMap, sceneOrderMap) {
  return (
    missionTimelineSceneOrderValue(a, flowKeyMap, sceneOrderMap) -
    missionTimelineSceneOrderValue(b, flowKeyMap, sceneOrderMap)
  ) || String(a || "").localeCompare(String(b || ""), undefined, { numeric: true });
}

function renderMissionTimelineSceneOrder(sceneGraph, flowKeyMap, currentKey) {
  const allNodes = missionTimelineArray(sceneGraph && sceneGraph.nodes)
    .filter((node) => node && String(node.key || "").trim());
  if (!allNodes.length) return null;

  const confirmed = allNodes
    .filter((node) => node.orderConfirmed !== false)
    .sort((a, b) => (
      Number(a.order) - Number(b.order)
    ) || String(a.key || "").localeCompare(String(b.key || ""), undefined, { numeric: true }));
  const unconfirmed = allNodes
    .filter((node) => node.orderConfirmed === false)
    .sort((a, b) => String(a.key || "").localeCompare(String(b.key || ""), undefined, { numeric: true }));

  const details = document.createElement("details");
  details.className = "mission-timeline-details";
  details.open = true;
  const summary = document.createElement("summary");
  summary.textContent = `${uiText("missionTimelineSceneOrder")} (${confirmed.length}${unconfirmed.length ? ` + ${unconfirmed.length} ${uiText("missionTimelineOrderUnknown")}` : ""})`;
  details.appendChild(summary);

  const row = document.createElement("div");
  row.className = "mission-timeline-edge";
  for (const [index, node] of confirmed.entries()) {
    if (index) {
      const arrow = document.createElement("span");
      arrow.className = "mission-timeline-arrow";
      arrow.textContent = "->";
      row.appendChild(arrow);
    }
    const chip = createFlowSceneChip(node.key || "?", flowKeyMap, currentKey);
    if (node.kind) chip.title = [chip.title, node.kind].filter(Boolean).join("\n");
    row.appendChild(chip);
  }
  details.appendChild(row);

  if (unconfirmed.length) {
    const unknownRow = document.createElement("div");
    unknownRow.className = "mission-timeline-edge mission-timeline-order-unknown";
    const label = document.createElement("span");
    label.className = "mission-timeline-unknown-label";
    label.textContent = uiText("missionTimelineOrderUnknown");
    unknownRow.appendChild(label);
    for (const node of unconfirmed) {
      const chip = createFlowSceneChip(node.key || "?", flowKeyMap, currentKey);
      if (node.kind) chip.title = [chip.title, node.kind].filter(Boolean).join("\n");
      unknownRow.appendChild(chip);
    }
    details.appendChild(unknownRow);
  }

  return details;
}

function renderMissionTimelineSceneEdges(edges, flowKeyMap, currentKey, { sceneOrderMap = null } = {}) {
  if (!edges.length) return null;
  const details = document.createElement("details");
  details.className = "mission-timeline-details";
  const summary = document.createElement("summary");
  summary.textContent = `${uiText("missionTimelineSceneGraph")} (${edges.length})`;
  details.appendChild(summary);

  const touchesCurrent = (edge) => {
    const from = resolveFlowConversationKey(edge.from || "", flowKeyMap) || edge.from;
    const to = resolveFlowConversationKey(edge.to || "", flowKeyMap) || edge.to;
    return from === currentKey || to === currentKey;
  };
  const edgeOrder = (edge) => Math.min(
    missionTimelineSceneOrderValue(edge && edge.from, flowKeyMap, sceneOrderMap),
    missionTimelineSceneOrderValue(edge && edge.to, flowKeyMap, sceneOrderMap)
  );
  const ordered = [...edges].sort((a, b) => (
    Number(touchesCurrent(b)) - Number(touchesCurrent(a))
  ) || (
    edgeOrder(a) - edgeOrder(b)
  ) || compareMissionTimelineSceneKeys(a && a.from, b && b.from, flowKeyMap, sceneOrderMap)
    || compareMissionTimelineSceneKeys(a && a.to, b && b.to, flowKeyMap, sceneOrderMap)
    || String(a && a.kind || "").localeCompare(String(b && b.kind || ""), undefined, { numeric: true }));
  const graph = renderMissionTimelineSceneEdgeGraph(ordered, flowKeyMap, currentKey, { sceneOrderMap });
  if (graph) details.appendChild(graph);

  const listLabel = document.createElement("div");
  listLabel.className = "mission-timeline-subheading";
  listLabel.textContent = uiText("missionTimelineEdgeList");
  details.appendChild(listLabel);
  for (const edge of ordered.slice(0, 120)) {
    const row = document.createElement("div");
    row.className = "mission-timeline-edge";
    row.appendChild(createFlowSceneChip(edge.from || "?", flowKeyMap, currentKey));
    const arrow = document.createElement("span");
    arrow.className = "mission-timeline-arrow";
    arrow.textContent = "->";
    row.appendChild(arrow);
    row.appendChild(createFlowSceneChip(edge.to || "?", flowKeyMap, currentKey));
    appendMissionTimelineChip(row, edge.kind || "edge");
    const sourceCount = missionTimelineArray(edge.sourceFiles).length + missionTimelineArray(edge.sourceKeys).length;
    if (sourceCount) appendMissionTimelineChip(row, `${uiText("missionTimelineSource")} ${sourceCount}`);
    const title = [
      ...missionTimelineArray(edge.sourceFiles),
      ...missionTimelineArray(edge.sourceKeys),
    ].join("\n");
    if (title) row.title = title;
    details.appendChild(row);
  }
  if (ordered.length > 120) {
    const more = document.createElement("div");
    more.className = "mission-timeline-more";
    more.textContent = `+${ordered.length - 120}`;
    details.appendChild(more);
  }
  return details;
}

function renderMissionTimelineSceneEdgeGraph(edges, flowKeyMap, currentKey, { sceneOrderMap = null } = {}) {
  const graphEdges = [];
  const seen = new Set();
  for (const edge of missionTimelineArray(edges)) {
    if (!edge || typeof edge !== "object") continue;
    const from = String(edge.from || "").trim();
    const to = String(edge.to || "").trim();
    if (!from || !to) continue;
    const kind = String(edge.kind || "edge");
    const dedup = [from, to, kind].join("\0");
    if (seen.has(dedup)) continue;
    seen.add(dedup);
    graphEdges.push({ ...edge, from, to, kind });
  }
  if (!graphEdges.length) return null;

  const outgoing = new Map();
  const undirected = new Map();
  const noteNode = (key) => {
    if (!undirected.has(key)) undirected.set(key, new Set());
    if (!outgoing.has(key)) outgoing.set(key, []);
  };
  for (const edge of graphEdges) {
    noteNode(edge.from);
    noteNode(edge.to);
    outgoing.get(edge.from).push(edge);
    undirected.get(edge.from).add(edge.to);
    undirected.get(edge.to).add(edge.from);
  }

  const components = [];
  const visited = new Set();
  for (const start of Array.from(undirected.keys()).sort((a, b) => compareMissionTimelineSceneKeys(a, b, flowKeyMap, sceneOrderMap))) {
    if (visited.has(start)) continue;
    const nodes = [];
    const stack = [start];
    visited.add(start);
    while (stack.length) {
      const cur = stack.pop();
      nodes.push(cur);
      for (const next of undirected.get(cur) || []) {
        if (visited.has(next)) continue;
        visited.add(next);
        stack.push(next);
      }
    }
    nodes.sort((a, b) => compareMissionTimelineSceneKeys(a, b, flowKeyMap, sceneOrderMap));
    const edgeCount = nodes.reduce((count, node) => count + missionTimelineArray(outgoing.get(node)).length, 0);
    components.push({ nodes, edgeCount });
  }
  const componentOrder = (component) => Math.min(
    ...component.nodes.map((node) => missionTimelineSceneOrderValue(node, flowKeyMap, sceneOrderMap))
  );
  components.sort((a, b) => (
    componentOrder(a) - componentOrder(b)
  ) || b.edgeCount - a.edgeCount || b.nodes.length - a.nodes.length);

  const wrap = document.createElement("div");
  wrap.className = "mission-scene-edge-graph";
  let renderedEdges = 0;
  const maxGraphEdges = 160;
  for (const [componentIndex, component] of components.entries()) {
    if (renderedEdges >= maxGraphEdges) break;
    const section = document.createElement("div");
    section.className = "mission-scene-edge-component";
    const title = document.createElement("div");
    title.className = "mission-scene-edge-component-title";
    title.textContent = `${uiText("missionTimelineComponent")} ${componentIndex + 1} | ${component.nodes.length} ${uiText("missionTimelineNodes")} | ${component.edgeCount} ${uiText("missionTimelineEdges")}`;
    section.appendChild(title);

    for (const source of component.nodes) {
      const sourceEdges = missionTimelineArray(outgoing.get(source)).sort((a, b) =>
        compareMissionTimelineSceneKeys(a && a.to, b && b.to, flowKeyMap, sceneOrderMap)
          || String(a && a.kind || "").localeCompare(String(b && b.kind || ""), undefined, { numeric: true })
      );
      if (!sourceEdges.length) continue;
      const visibleEdges = sourceEdges.slice(0, Math.max(0, maxGraphEdges - renderedEdges));
      if (!visibleEdges.length) break;

      const row = document.createElement("div");
      row.className = "mission-scene-edge-graph-row";
      const sourceCell = document.createElement("div");
      sourceCell.className = "mission-scene-edge-source";
      sourceCell.appendChild(createFlowSceneChip(source, flowKeyMap, currentKey));
      row.appendChild(sourceCell);
      const arrow = document.createElement("span");
      arrow.className = "mission-timeline-arrow";
      arrow.textContent = "->";
      row.appendChild(arrow);

      const targets = document.createElement("div");
      targets.className = "mission-scene-edge-targets";
      for (const edge of visibleEdges) {
        const target = document.createElement("span");
        target.className = "mission-scene-edge-target";
        target.appendChild(createFlowSceneChip(edge.to, flowKeyMap, currentKey));
        appendMissionTimelineChip(target, edge.kind || "edge");
        const titleText = [
          ...missionTimelineArray(edge.sourceFiles),
          ...missionTimelineArray(edge.sourceKeys),
          missionTimelineSourceTitle(edge.source),
        ].filter(Boolean).join("\n");
        if (titleText) target.title = titleText;
        targets.appendChild(target);
      }
      renderedEdges += visibleEdges.length;
      if (sourceEdges.length > visibleEdges.length) appendMissionTimelineChip(targets, `+${sourceEdges.length - visibleEdges.length}`);
      row.appendChild(targets);
      section.appendChild(row);
    }
    wrap.appendChild(section);
  }
  if (graphEdges.length > renderedEdges) {
    const more = document.createElement("div");
    more.className = "mission-timeline-more";
    more.textContent = `+${graphEdges.length - renderedEdges}`;
    wrap.appendChild(more);
  }
  return wrap;
}

function renderMissionTimelineInlineEdges(edges, flowKeyMap, currentKey, { limit = 6 } = {}) {
  const cleaned = [];
  const seen = new Set();
  for (const edge of edges) {
    if (!edge || typeof edge !== "object") continue;
    const from = String(edge.from || "");
    const to = String(edge.to || "");
    const kind = String(edge.kind || "");
    const dedup = [from, to, kind].join("\0");
    if (!from && !to) continue;
    if (seen.has(dedup)) continue;
    seen.add(dedup);
    cleaned.push(edge);
  }
  if (!cleaned.length) return null;

  const wrap = document.createElement("div");
  wrap.className = "mission-timeline-inline-edges";
  const label = document.createElement("div");
  label.className = "mission-timeline-line-label mission-timeline-inline-label";
  label.textContent = uiText("missionTimelineGraphLinks");
  wrap.appendChild(label);

  for (const edge of cleaned.slice(0, limit)) {
    const row = document.createElement("div");
    row.className = "mission-timeline-edge mission-timeline-edge-inline";
    row.appendChild(createFlowSceneChip(edge.from || "?", flowKeyMap, currentKey));
    const arrow = document.createElement("span");
    arrow.className = "mission-timeline-arrow";
    arrow.textContent = "->";
    row.appendChild(arrow);
    row.appendChild(createFlowSceneChip(edge.to || "?", flowKeyMap, currentKey));
    appendMissionTimelineChip(row, edge.kind || "edge");
    const title = [
      ...missionTimelineArray(edge.sourceFiles),
      ...missionTimelineArray(edge.sourceKeys),
      missionTimelineSourceTitle(edge.source),
    ].filter(Boolean).join("\n");
    if (title) row.title = title;
    wrap.appendChild(row);
  }
  if (cleaned.length > limit) {
    const more = document.createElement("div");
    more.className = "mission-timeline-more";
    more.textContent = `+${cleaned.length - limit}`;
    wrap.appendChild(more);
  }
  return wrap;
}

function renderMissionTimelineEvidence(evidence, flowKeyMap, currentKey) {
  const rows = Object.entries(evidence || {}).filter(([, entries]) => missionTimelineArray(entries).length);
  if (!rows.length) return null;
  const details = document.createElement("details");
  details.className = "mission-timeline-details";
  const summary = document.createElement("summary");
  summary.textContent = `${uiText("missionTimelineEvidence")} (${rows.length})`;
  details.appendChild(summary);
  for (const [sceneKey, entries] of rows.sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }))) {
    const row = document.createElement("div");
    row.className = "mission-timeline-edge";
    row.appendChild(createFlowSceneChip(sceneKey, flowKeyMap, currentKey));
    const timelines = missionTimelineUniqueStrings(missionTimelineArray(entries).map((entry) => entry.timeline || entry.sourceKey));
    for (const name of timelines.slice(0, 4)) appendMissionTimelineChip(row, name);
    if (timelines.length > 4) appendMissionTimelineChip(row, `+${timelines.length - 4}`);
    details.appendChild(row);
  }
  return details;
}

function renderMissionTimelineUnresolved(unresolved, flowKeyMap, currentKey) {
  if (!unresolved.length) return null;
  const details = document.createElement("details");
  details.className = "mission-timeline-details";
  const summary = document.createElement("summary");
  summary.textContent = `${uiText("missionTimelineUnresolved")} (${unresolved.length})`;
  details.appendChild(summary);
  for (const item of unresolved.slice(0, 80)) {
    const row = document.createElement("div");
    row.className = "mission-timeline-edge";
    appendMissionTimelineChip(row, item.kind || "unresolved", "mission-timeline-chip-warn");
    if (item.sceneKey) row.appendChild(createFlowSceneChip(item.sceneKey, flowKeyMap, currentKey));
    if (item.questId) appendMissionTimelineChip(row, item.questId);
    if (item.prevQuestId) appendMissionTimelineChip(row, item.prevQuestId);
    const title = missionTimelineSourceTitle(item.source);
    if (title) row.title = title;
    details.appendChild(row);
  }
  if (unresolved.length > 80) {
    const more = document.createElement("div");
    more.className = "mission-timeline-more";
    more.textContent = `+${unresolved.length - 80}`;
    details.appendChild(more);
  }
  return details;
}

function renderMissionTimelineRecovery(timeline, conv, missionFlow = null) {
  if (!timeline || !missionTimelineArray(timeline.quests).length) return null;
  const box = document.createElement("div");
  box.className = "summary-box mission-timeline-box";

  const label = document.createElement("div");
  label.className = "summary-label";
  label.textContent = uiText("missionTimelineRecovery");
  box.appendChild(label);

  const stats = document.createElement("div");
  stats.className = "mission-timeline-stats";
  const questCount = missionTimelineArray(timeline.quests).length;
  const treeLoops = missionTimelineArray(timeline.questTree && timeline.questTree.loops).length;
  appendMissionTimelineChip(stats, `${uiText("missionTimelineQuests")} ${questCount}`);
  appendMissionTimelineChip(stats, `${uiText("missionTimelineBranches")} ${missionTimelineArray(timeline.branchPoints).length}`);
  appendMissionTimelineChip(stats, `${uiText("missionTimelineEdges")} ${missionTimelineArray(timeline.sourceBackedSceneEdges).length}`);
  appendMissionTimelineChip(stats, `${uiText("missionTimelineEvidence")} ${Object.keys(timeline.sceneTimelineEvidence || {}).length}`);
  appendMissionTimelineChip(stats, `${uiText("missionTimelineUnresolved")} ${missionTimelineArray(timeline.unresolved).length}`);
  if (treeLoops) appendMissionTimelineChip(stats, `${uiText("missionTimelineLoop")} ${treeLoops}`, "mission-timeline-chip-warn");
  box.appendChild(stats);

  const flowKeyMap = buildFlowConversationKeyMap();
  const currentKey = conv && conv.key ? conv.key : "";
  const questById = new Map(missionTimelineArray(timeline.quests).map((quest) => [quest.questId, quest]));
  const resourceContext = buildMissionTimelineResourceContext(missionFlow, timeline);
  const sceneOrderMap = buildMissionTimelineSceneOrderMap(missionFlow && missionFlow.sceneGraph);
  const tree = timeline.questTree || {};
  const roots = missionTimelineArray(tree.roots);
  const unrootedRoots = missionTimelineArray(tree.unrootedRoots);

  if (roots.length || unrootedRoots.length) {
    const details = document.createElement("details");
    details.className = "mission-timeline-details mission-timeline-tree-details";
    const summary = document.createElement("summary");
    summary.textContent = `${uiText("missionTimelineTree")} (${(tree.rootQuestIds || []).length || roots.length})`;
    details.appendChild(summary);
    if (roots.length) details.appendChild(renderMissionTimelineTree(roots, questById, resourceContext, flowKeyMap, currentKey));
    if (unrootedRoots.length) {
      const unrootedLabel = document.createElement("div");
      unrootedLabel.className = "mission-timeline-subheading";
      unrootedLabel.textContent = uiText("missionTimelineUnrooted");
      details.appendChild(unrootedLabel);
      details.appendChild(renderMissionTimelineTree(unrootedRoots, questById, resourceContext, flowKeyMap, currentKey));
    }
    box.appendChild(details);
  }

  const sceneOrderBlock = renderMissionTimelineSceneOrder(missionFlow && missionFlow.sceneGraph, flowKeyMap, currentKey);
  if (sceneOrderBlock) box.appendChild(sceneOrderBlock);
  const evidenceBlock = renderMissionTimelineEvidence(timeline.sceneTimelineEvidence || {}, flowKeyMap, currentKey);
  if (evidenceBlock) box.appendChild(evidenceBlock);
  const edgeBlock = renderMissionTimelineSceneEdges(
    missionTimelineArray(timeline.sourceBackedSceneEdges),
    flowKeyMap,
    currentKey,
    { sceneOrderMap }
  );
  if (edgeBlock) box.appendChild(edgeBlock);
  const unresolvedBlock = renderMissionTimelineUnresolved(missionTimelineArray(timeline.unresolved), flowKeyMap, currentKey);
  if (unresolvedBlock) box.appendChild(unresolvedBlock);

  return box;
}

function createGraphTextChip(text, extraClass = "") {
  const chip = document.createElement("span");
  chip.className = "binding-chip" + (extraClass ? ` ${extraClass}` : "");
  chip.textContent = text;
  return chip;
}

let _flowKeyMapCache = null;
let _flowKeyMapCacheToken = null;

function buildFlowConversationKeyMap() {
  const entries = STATE.entries || [];
  if (_flowKeyMapCacheToken === entries && _flowKeyMapCache) {
    return _flowKeyMapCache;
  }

  const map = new Map();
  const aliases = new Map();

  const noteAlias = (raw, key) => {
    if (!raw || raw === key) return;
    if (!aliases.has(raw)) aliases.set(raw, key);
  };

  for (const entry of entries) {
    const key = entry && entry.k;
    if (!key) continue;
    if (!map.has(key)) map.set(key, key);
    if (key.startsWith("misc_")) noteAlias(key.slice(5), key);
    if (key.startsWith("env_envTalk_")) noteAlias("dlg_" + key.slice(12), key);
  }

  for (const [raw, key] of aliases) {
    if (!map.has(raw)) map.set(raw, key);
  }

  _flowKeyMapCache = map;
  _flowKeyMapCacheToken = entries;
  return map;
}

function resolveFlowConversationKey(rawKey, flowKeyMap) {
  const key = String(rawKey || "");
  return flowKeyMap.get(key) || "";
}

function createFlowSceneChip(rawKey, flowKeyMap, currentKey) {
  const raw = String(rawKey || "");
  const isUiNode = raw.startsWith("ui:");
  const isRuntimeNode =
    isUiNode ||
    raw.startsWith("remotecomm_") ||
    raw.startsWith("radio_") ||
    raw.startsWith("black_") ||
    raw.startsWith("cutscene_") ||
    /^dlg_.+_(OpenUI|NewSeries)$/.test(raw);
  const resolvedKey = isUiNode ? "" : resolveFlowConversationKey(raw, flowKeyMap);
  const chip = document.createElement(resolvedKey ? "button" : "span");
  chip.className = "flow-dlg-ref";
  chip.textContent = isUiNode ? raw.slice(3) : raw;

  if (resolvedKey) {
    chip.type = "button";
    if (resolvedKey === currentKey) chip.classList.add("current");
    if (resolvedKey !== raw) chip.title = `${raw} -> ${resolvedKey}`;
    chip.addEventListener("click", () => loadConv(resolvedKey));
  } else if (isRuntimeNode) {
    chip.classList.add("binding-chip-muted");
    chip.title = raw;
  } else {
    chip.classList.add("missing");
  }

  return chip;
}

function speakerName(speaker) {
  if (!speaker) return uiText("systemSpeaker");
  if (STATE.actorNames[speaker]) return actorDisplay(speaker);
  // try the trailing token (e.g. sns_chr_0004_pelica -> "pelica")
  const parts = speaker.split("_");
  const tail = parts[parts.length - 1];
  if (STATE.actorNames[tail]) return actorDisplay(tail);
  return stripBraceSegments(speaker) || speaker;
}

// ---------- helpers ----------
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function formatTimelineSeconds(value) {
  if (typeof value !== "number" || !isFinite(value)) return "";
  const seconds = Math.max(0, value);
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds - minutes * 60;
  return `${minutes}:${remaining.toFixed(1).padStart(4, "0")}`;
}

function exportedAssetHref(relPath) {
  const normalizedRel = String(relPath || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  if (!normalizedRel) return "/exported/";

  const [source, ...rest] = normalizedRel.split("/").filter(Boolean);
  const relWithinSource = rest.join("/");
  let exportedRel = normalizedRel;
  const sourceRoot = STATE.inlineImageSourceRoots && STATE.inlineImageSourceRoots[source];
  if (sourceRoot) {
    let normalizedRoot = String(sourceRoot || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
    const exportRoot = String(STATE.inlineImageExportRoot || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
    if (exportRoot && normalizedRoot.startsWith(`${exportRoot}/`)) {
      normalizedRoot = normalizedRoot.slice(exportRoot.length + 1);
    } else if (normalizedRoot === exportRoot) {
      normalizedRoot = "";
    }
    exportedRel = [normalizedRoot, relWithinSource].filter(Boolean).join("/");
  }

  return `/exported/${exportedRel.split("/").map(encodeURIComponent).join("/")}`;
}

function highlightTextFragment(text, q) {
  let safe = escapeHtml(text || "");
  if (q) {
    const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "ig");
    safe = safe.replace(re, (m) => `<mark>${m}</mark>`);
  }
  return safe;
}

function extractInlineImageIdFromTag(rawTag) {
  const raw = String(rawTag || "").trim();
  if (!raw) return "";

  const bodyMatch = raw.match(/^<image\b(?!\s*=)[^>]*>([\s\S]*?)<\/image>$/i);
  if (bodyMatch) return cleanInlineImageIdValue(bodyMatch[1]);

  const quotedDirect = raw.match(/^<image\s*=\s*(["'])([\s\S]*?)\1/i);
  if (quotedDirect) return cleanInlineImageIdValue(quotedDirect[2]);

  const looseDirect = raw.match(/^<image\s*=\s*([^>\s]+)/i);
  if (looseDirect) return cleanInlineImageIdValue(looseDirect[1]);

  const quotedAttr = raw.match(/\b(?:src|source|path|name|id)\s*=\s*(["'])([\s\S]*?)\1/i);
  if (quotedAttr) return cleanInlineImageIdValue(quotedAttr[2]);

  const looseAttr = raw.match(/\b(?:src|source|path|name|id)\s*=\s*([^>\s]+)/i);
  return looseAttr ? cleanInlineImageIdValue(looseAttr[1]) : "";
}

function isInlineEmojiImageId(imageId, asset = null) {
  const normalized = normalizeInlineImageId(imageId);
  const rel = String(asset && asset.rel ? asset.rel : "").toLowerCase();
  return normalized.includes("emoji") || normalized.includes("emoiji") || rel.includes("emoji") || rel.includes("emoiji");
}

function isInlineContentImageId(rawId, normalized, asset = null) {
  const raw = cleanInlineImageIdValue(rawId).replace(/\\/g, "/").toLowerCase();
  const stem = normalizeInlineImageId(normalized || rawId);
  const rel = String(asset && asset.rel ? asset.rel : "").toLowerCase();
  return (
    raw.includes("reading/")
    || raw.includes("/reading/")
    || /^(?:collection|document|reading|read)_/.test(stem)
    || /\/(?:collection|document|reading|read)_/.test(rel)
  );
}

function renderInlineImageTagHtml(imageId, q, rawTag = "") {
  const rawId = cleanInlineImageIdValue(imageId);
  const normalized = normalizeInlineImageId(rawId);
  const asset = resolveInlineImageAsset(normalized);
  const classes = ["inline-image-tag"];
  const attrs = [`data-inline-image-id="${escapeHtml(normalized || rawId)}"`];
  const src = asset ? exportedAssetHref(asset.rel) : "";

  if (asset) {
    classes.push("has-preview");
    if (isInlineEmojiImageId(normalized, asset)) classes.push("is-emoji");
    if (/^(?:sns_image|cg_image)_/i.test(normalized)) classes.push("is-sns-image");
    if (isInlineContentImageId(rawId, normalized, asset)) classes.push("is-content-image");
    attrs.push(`tabindex="0"`);
    attrs.push(`title="${escapeHtml(asset.name)}"`);
    attrs.push(`data-inline-image-src="${escapeHtml(src)}"`);
    attrs.push(`data-inline-image-name="${escapeHtml(asset.name)}"`);
  }

  const label = asset ? "" : highlightTextFragment(rawTag || `<image="${rawId}">`, q);
  const thumb = asset
    ? `<img class="inline-image-thumb" src="${escapeHtml(src)}" alt="${escapeHtml(rawId)}" loading="lazy">`
    : "";
  const preview = asset
    ? `<span class="inline-image-popover"><img src="${escapeHtml(src)}" alt="${escapeHtml(rawId)}" loading="lazy"></span>`
    : "";

  return `<span class="${classes.join(" ")}" ${attrs.join(" ")}>${thumb}${label}${preview}</span>`;
}

function ensureInlineImageModal() {
  let modal = $("#inline-image-modal");
  if (modal) return modal;

  modal = document.createElement("div");
  modal.id = "inline-image-modal";
  modal.className = "inline-image-modal";
  modal.hidden = true;
  modal.innerHTML = `
    <div class="inline-image-modal-panel" role="dialog" aria-modal="true" aria-label="Image preview">
      <button class="inline-image-modal-close" type="button" aria-label="Close image preview">&times;</button>
      <img class="inline-image-modal-img" alt="">
      <div class="inline-image-modal-caption"></div>
    </div>
  `;
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeInlineImageModal();
  });
  modal.querySelector(".inline-image-modal-close").addEventListener("click", closeInlineImageModal);
  document.body.appendChild(modal);
  return modal;
}

function closeInlineImageModal() {
  const modal = $("#inline-image-modal");
  if (!modal) return;
  modal.hidden = true;
  document.body.classList.remove("inline-image-modal-open");
}

function openInlineImageModal(imageTag) {
  if (!imageTag || imageTag.classList.contains("is-emoji")) return false;
  const src = imageTag.dataset.inlineImageSrc || "";
  if (!src) return false;

  const modal = ensureInlineImageModal();
  const img = modal.querySelector(".inline-image-modal-img");
  const caption = modal.querySelector(".inline-image-modal-caption");
  const imageId = imageTag.dataset.inlineImageId || "";
  const imageName = imageTag.dataset.inlineImageName || imageId;
  img.src = src;
  img.alt = imageName || imageId || "Image preview";
  caption.textContent = imageName || imageId;
  modal.hidden = false;
  document.body.classList.add("inline-image-modal-open");
  const close = modal.querySelector(".inline-image-modal-close");
  if (close) close.focus({ preventScroll: true });
  return true;
}

function handleInlineImageModalActivate(target) {
  const imageTag = target && target.closest(".inline-image-tag.has-preview");
  if (!imageTag || imageTag.classList.contains("is-emoji")) return false;
  return openInlineImageModal(imageTag);
}

function parseGenderVariantText(text) {
  const source = String(text || "");
  const match = source.match(/^\s*\{([MF])\}\s*([\s\S]*?)\s*\{([MF])\}\s*([\s\S]*?)\s*$/i);
  if (!match) return null;

  const firstKey = String(match[1] || "").toUpperCase();
  const firstText = (match[2] || "").trim();
  const secondKey = String(match[3] || "").toUpperCase();
  const secondText = (match[4] || "").trim();
  if (!firstText || !secondText || firstKey === secondKey || firstText === secondText) return null;

  const variants = {
    [firstKey]: firstText,
    [secondKey]: secondText,
  };
  if (!variants.M || !variants.F) return null;

  return {
    male: variants.M,
    female: variants.F,
    initial: firstKey === "F" ? "f" : "m",
  };
}

function encodeInlineTextData(text) {
  return encodeURIComponent(String(text || ""));
}

function decodeInlineTextData(text) {
  try {
    return decodeURIComponent(String(text || ""));
  } catch {
    return String(text || "");
  }
}

function normalizeGenderVariant(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return normalized === "f" || normalized === "m" ? normalized : "";
}

function persistGenderVariant(value) {
  storageSet(GENDER_VARIANT_STORAGE_KEY, normalizeGenderVariant(value) || "m");
}

function resolveStoredGenderVariant() {
  return normalizeGenderVariant(storageGet(GENDER_VARIANT_STORAGE_KEY));
}

function syncGenderVariantControl() {
  const active = resolveGenderVariant();
  const checkbox = $("#gender-variant");
  if (checkbox) checkbox.checked = active === "f";
  const label = $("#gender-variant-label");
  if (label) label.textContent = uiText("genderVariant").replace("{gender}", active.toUpperCase());
}

function setGenderVariant(value, { persist = true, refresh = true } = {}) {
  const next = normalizeGenderVariant(value) || "m";
  STATE.genderVariant = next;
  if (persist) persistGenderVariant(next);
  syncGenderVariantControl();
  if (refresh) {
    const cached = STATE.selectedKey ? STATE.convCache.get(STATE.selectedKey) : null;
    if (cached) renderConv(cached);
    else syncAllGenderToggles($("#conv-lines"));
  }
  return next;
}

function parseInlineTagDisplayMode(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return normalized === "raw" || normalized === "rendered" ? normalized : "";
}

function persistInlineTagDisplayMode(mode) {
  storageSet(INLINE_TAG_DISPLAY_MODE_STORAGE_KEY, normalizeInlineTagDisplayMode(mode));
}

function resolveStoredInlineTagDisplayMode() {
  return parseInlineTagDisplayMode(storageGet(INLINE_TAG_DISPLAY_MODE_STORAGE_KEY) || "");
}

function normalizeInlineTagDisplayMode(value) {
  return parseInlineTagDisplayMode(value) || DEFAULT_INLINE_TAG_DISPLAY_MODE;
}

function readGlobalInlineTagDisplayMode() {
  const fromWindow = typeof window !== "undefined"
    ? parseInlineTagDisplayMode(window.WEBUI_INLINE_TAG_DISPLAY_MODE)
    : "";
  const fromVar = parseInlineTagDisplayMode(WEBUI_INLINE_TAG_DISPLAY_MODE);
  return fromWindow || fromVar || "";
}

function resolveInlineTagDisplayMode(preferred = "") {
  const globalMode = readGlobalInlineTagDisplayMode();
  if (globalMode) {
    STATE.inlineTagDisplayMode = globalMode;
    return globalMode;
  }
  const storedMode = resolveStoredInlineTagDisplayMode();
  if (storedMode) {
    STATE.inlineTagDisplayMode = storedMode;
    return storedMode;
  }
  const current = parseInlineTagDisplayMode(STATE.inlineTagDisplayMode);
  if (current) return current;
  return normalizeInlineTagDisplayMode(preferred || DEFAULT_INLINE_TAG_DISPLAY_MODE);
}

function refreshInlineTagDisplayMode() {
  if (!STATE.entries.length) return;
  applyFilters();
  if (!STATE.selectedKey) return;
  const cached = STATE.convCache.get(STATE.selectedKey);
  if (cached) renderConv(cached);
}

function setInlineTagDisplayMode(mode, { refresh = true } = {}) {
  const next = normalizeInlineTagDisplayMode(mode);
  STATE.inlineTagDisplayMode = next;
  WEBUI_INLINE_TAG_DISPLAY_MODE = next;
  if (typeof window !== "undefined") window.WEBUI_INLINE_TAG_DISPLAY_MODE = next;
  persistInlineTagDisplayMode(next);
  const checkbox = $("#inline-tag-mode");
  if (checkbox) checkbox.checked = next === "raw";
  if (refresh) refreshInlineTagDisplayMode();
  return STATE.inlineTagDisplayMode;
}

function installInlineTagDisplayModeGlobal() {
  if (typeof window === "undefined") return;
  window.WEBUI_INLINE_TAG_DISPLAY_MODE = resolveInlineTagDisplayMode();
  window.setWebuiInlineTagDisplayMode = (mode) => setInlineTagDisplayMode(mode);
  window.setInterval(() => {
    const globalMode = readGlobalInlineTagDisplayMode();
    if (!globalMode || globalMode === STATE.inlineTagDisplayMode) return;
    STATE.inlineTagDisplayMode = globalMode;
    refreshInlineTagDisplayMode();
  }, 250);
}

function resolveGenderVariant(preferred = "") {
  const current = normalizeGenderVariant(STATE.genderVariant);
  if (current) return current;

  const stored = resolveStoredGenderVariant();
  if (stored) {
    STATE.genderVariant = stored;
    return stored;
  }

  const fallback = normalizeGenderVariant(preferred);
  if (fallback) {
    STATE.genderVariant = fallback;
    return fallback;
  }

  STATE.genderVariant = "m";
  return "m";
}

function hasInlineRichTextTag(text) {
  return /<[^>]+>/.test(String(text || ""));
}

function renderHighlightedRichTextHtml(text, q) {
  const source = String(text || "");
  const parts = [];
  const tokenRe = /<image\b(?!\s*=)[^>]*>[\s\S]*?<\/image>|<image\s*=[^>]+>|<image\b(?=[^>]*(?:src|source|path|name|id)\s*=)[^>]*>|<@[^>]*>([\s\S]*?)<\/>|<s>([\s\S]*?)<\/s>/gi;
  let lastIndex = 0;
  let match;

  while ((match = tokenRe.exec(source))) {
    if (match.index > lastIndex) {
      parts.push(highlightTextFragment(source.slice(lastIndex, match.index), q));
    }

    const rawToken = match[0] || "";
    if (/^<image/i.test(rawToken)) {
      parts.push(renderInlineImageTagHtml(extractInlineImageIdFromTag(rawToken), q, rawToken));
    } else if (match[2] !== undefined) {
      parts.push(`<span class="rich-strike">${renderHighlightedRichTextHtml(match[2] || "", q)}</span>`);
    } else {
      parts.push(`<span class="rich-tag">${highlightTextFragment(match[1] || "", q)}</span>`);
    }

    lastIndex = tokenRe.lastIndex;
  }

  if (lastIndex < source.length) {
    parts.push(highlightTextFragment(source.slice(lastIndex), q));
  }

  return parts.join("");
}

function renderDisplayedTextHtml(text, q) {
  const source = String(text || "");
  if (resolveInlineTagDisplayMode() === "raw" && hasInlineRichTextTag(source)) {
    return highlightTextFragment(source, q);
  }
  return renderHighlightedRichTextHtml(source, q);
}

function isDocumentStyleKind(kind) {
  return kind === "wiki" || kind === "mail" || kind === "prts" || String(kind || "").startsWith("table_");
}

function normalizeDocumentDisplayText(text) {
  return String(text || "").replace(/<@profile\.key>([\s\S]*?)<\/>/g, "$1");
}

function visualizeInvisibleText(text) {
  return String(text || "")
    .replace(/\r\n/g, "\\r\\n\n")
    .replace(/\r/g, "\\r")
    .replace(/\n/g, "\\n\n")
    .replace(/\t/g, "\\t");
}

function renderDocumentTextHtml(kind, text, q) {
  const source = String(text || "");
  if (!isDocumentStyleKind(kind)) return highlight(text, q);
  if (resolveInlineTagDisplayMode() === "raw") {
    return highlightTextFragment(visualizeInvisibleText(source), q);
  }
  return renderDisplayedTextHtml(normalizeDocumentDisplayText(source), q);
}

function renderGenderVariantHtml(text, q) {
  const variant = parseGenderVariantText(text);
  if (!variant) return null;

  const active = resolveGenderVariant(variant.initial);
  const visibleText = active === "f" ? variant.female : variant.male;
  return `<span class="gender-toggle" role="button" tabindex="0" aria-pressed="${active === "f" ? "true" : "false"}" data-gender-active="${active}" data-gender-initial="${variant.initial}" data-gender-text-m="${encodeInlineTextData(variant.male)}" data-gender-text-f="${encodeInlineTextData(variant.female)}">${renderDisplayedTextHtml(visibleText, q)}</span>`;
}

function syncGenderToggle(node) {
  if (!node) return;
  const active = resolveGenderVariant(node.dataset.genderInitial || node.dataset.genderActive || "m");
  const encoded = active === "f" ? node.dataset.genderTextF : node.dataset.genderTextM;
  node.dataset.genderActive = active;
  node.setAttribute("aria-pressed", active === "f" ? "true" : "false");
  node.innerHTML = renderDisplayedTextHtml(decodeInlineTextData(encoded), STATE.filters.q);
}

function syncAllGenderToggles(root = $("#conv-lines")) {
  if (!root) return;
  for (const toggle of root.querySelectorAll(".gender-toggle")) {
    syncGenderToggle(toggle);
  }
}

function toggleGenderToggle(node) {
  const active = resolveGenderVariant(node && (node.dataset.genderInitial || node.dataset.genderActive || "m"));
  setGenderVariant(active === "f" ? "m" : "f");
}

function handleGenderToggleActivate(target) {
  if (!target || target.closest(".inline-image-tag")) return false;
  const toggle = target.closest(".gender-toggle");
  if (!toggle) return false;
  toggleGenderToggle(toggle);
  return true;
}



function appendDebugTrace(parent, debug, label = "source") {
  if (!STATE.showRaw || !debug) return;

  const details = document.createElement("details");
  details.className = "raw-trace";

  const summary = document.createElement("summary");
  summary.className = "raw-trace-summary";

  const title = document.createElement("span");
  title.className = "raw-trace-title";
  title.textContent = label;
  summary.appendChild(title);

  for (const badge of traceBadges(debug)) {
    const chip = document.createElement("span");
    chip.className = "trace-badge";
    chip.textContent = badge;
    summary.appendChild(chip);
  }

  details.appendChild(summary);

  const body = document.createElement("div");
  body.className = "raw-trace-body";

  if (debug.source !== undefined) {
    body.appendChild(renderJsonBlock("source", debug.source));
  }

  if (debug.fields) {
    for (const [name, trace] of Object.entries(debug.fields)) {
      if (!trace) continue;
      body.appendChild(renderFieldTrace(name, trace));
    }
  }

  if (debug.trace) {
    body.appendChild(renderFieldTrace("lookup", debug.trace));
  }

  details.appendChild(body);
  parent.appendChild(details);
}

function traceBadges(debug) {
  const badges = [];
  if (debug.table) badges.push(`table: ${debug.table}`);
  if (debug.rowId) badges.push(`row: ${debug.rowId}`);
  if (debug.nodeId !== undefined) badges.push(`node: ${debug.nodeId}`);
  if (debug.order !== undefined) badges.push(`order: ${debug.order}`);
  return badges;
}

function renderFieldTrace(name, trace) {
  const wrap = document.createElement("section");
  wrap.className = "trace-field";

  const head = document.createElement("div");
  head.className = "trace-field-head";

  const title = document.createElement("div");
  title.className = "trace-field-title";
  title.textContent = name;
  head.appendChild(title);

  const meta = [];
  if (trace.lookup && trace.lookup.length) meta.push(`${trace.lookup.length} step${trace.lookup.length === 1 ? "" : "s"}`);
  if (trace.braceText !== undefined) meta.push("brace text");
  if (trace.raw !== undefined) meta.push(typeof trace.raw === "string" ? "text" : "json");
  if (meta.length) {
    const summary = document.createElement("div");
    summary.className = "trace-field-meta";
    summary.textContent = meta.join(" | ");
    head.appendChild(summary);
  }

  wrap.appendChild(head);

  if (trace.raw !== undefined) {
    wrap.appendChild(renderJsonBlock("raw", trace.raw));
  }

  if (trace.lookup && trace.lookup.length) {
    const steps = document.createElement("div");
    steps.className = "trace-steps";
    for (const step of trace.lookup) {
      const row = document.createElement("div");
      row.className = "trace-step";

      const from = document.createElement("div");
      from.className = "trace-step-from";
      from.textContent = step.from;
      row.appendChild(from);

      const arrow = document.createElement("div");
      arrow.className = "trace-step-arrow";
      arrow.textContent = "->";
      row.appendChild(arrow);

      const value = document.createElement("div");
      value.className = "trace-step-value";
      value.textContent = stringifyTraceValue(step.value);
      row.appendChild(value);

      steps.appendChild(row);
    }
    wrap.appendChild(steps);
  }

  if (trace.braceText !== undefined) {
    wrap.appendChild(renderJsonBlock("brace_text", trace.braceText));
  }

  return wrap;
}

function renderJsonBlock(label, value) {
  const wrap = document.createElement("div");
  wrap.className = "trace-json";

  const title = document.createElement("div");
  title.className = "trace-json-label";
  title.textContent = label;
  wrap.appendChild(title);

  const pre = document.createElement("pre");
  pre.className = "trace-json-code";
  pre.textContent = formatTraceValue(value);
  wrap.appendChild(pre);

  return wrap;
}

function formatTraceValue(value) {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function stringifyTraceValue(value) {
  if (typeof value === "string") return value;
  const json = JSON.stringify(value);
  return json && json.length > 140 ? json.slice(0, 137) + "..." : json;
}

// Render inline rich-text tags such as <@xxx.key>...</> and <image="...">,
// then apply search-term highlight only to the human-visible text fragments.
function highlight(text, q) {
  return renderGenderVariantHtml(text, q) || renderDisplayedTextHtml(text, q);
}

function countBy(arr, fn) {
  const out = {};
  for (const x of arr) {
    const k = fn(x);
    out[k] = (out[k] || 0) + 1;
  }
  return out;
}

installInlineTagDisplayModeGlobal();
init();
