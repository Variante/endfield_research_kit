// Endfield conversation browser - single-file vanilla JS.
// Loads data/manifest.json and language sidecars, then lazy-loads conversations.
// Left pane is a 3-level tree (kind / story-line / mission) with a
// virtualized scroll that supports mixed row heights.

const ROW_GROUP_H = 28;
const ROW_ITEM_H = 50;
const OVERSCAN_PX = 200;
const WIKI_MEDIA_MAX_IMAGES = 12;
const WIKI_MEDIA_MAX_VIDEOS = 8;
const NARRATIVE_VIDEO_DISPLAY_LIMIT = 4;
// Change to "raw" to show source text with angle-bracket tags instead of rendered rich text.
const DEFAULT_INLINE_TAG_DISPLAY_MODE = "rendered";
var WEBUI_INLINE_TAG_DISPLAY_MODE = DEFAULT_INLINE_TAG_DISPLAY_MODE;
const INLINE_TAG_DISPLAY_MODE_STORAGE_KEY = "webui_inline_tag_mode";
const LANGUAGE_STORAGE_KEY = "webui_lang";
const UI_LOCALE_STORAGE_KEY = "webui_ui_locale";
const GENDER_VARIANT_STORAGE_KEY = "webui_gender_variant";
const DEFAULT_GENDER_VARIANT = "f";
const FILTER_PANEL_STORAGE_KEY = "webui_filters_collapsed";
const FILTER_SECTION_STORAGE_KEY = "webui_filter_sections_collapsed_v2";
const STORY_SPLITTER_STORAGE_KEY = "webui_story_splitter_width";
const ASSET_SPLITTER_STORAGE_KEY = "webui_asset_splitter_width";
const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
const WEBUI_DATA_CACHE_TAG = "20260513-merged-line-order-tags";
const DEFAULT_LANGUAGE_INFO = {
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
  languageInfo: DEFAULT_LANGUAGE_INFO,
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
  storySearchLoaded: false,
  storySearchPromise: null,
  storySearchLanguage: "",
  storyMediaPayload: null,
  storyMediaPromise: null,
  expanded: new Set(),   // group paths the user opened
  filters: createDefaultFilters(),
  sortMode: "natural",
  showEmpty: false,
  showRaw: false,
  filtersCollapsed: false,
  filterSectionsCollapsed: new Set(),
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

const { $, $$, storageGet, storageSet, normalizeUiLocale, escapeHtml, exportFullHref } = window.WebUI;

function createDefaultFilters() {
  return {
    q: "",
    kinds: new Set(),
    dataTypes: new Set(),
    media: new Set(),
    issues: new Set(),
    recoveryMethods: new Set(),
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

function persistFiltersCollapsed(collapsed) {
  storageSet(FILTER_PANEL_STORAGE_KEY, collapsed ? "1" : "0");
}

function resolveInitialFiltersCollapsed() {
  const stored = storageGet(FILTER_PANEL_STORAGE_KEY);
  if (stored === "1") return true;
  if (stored === "0") return false;
  return isMobileLayout();
}

function availableFilterSectionKeys() {
  return new Set($$(".filter-section[data-filter-section]:not([data-fixed-open='1'])").map((section) => section.dataset.filterSection).filter(Boolean));
}

function defaultCollapsedFilterSectionKeys() {
  return new Set($$(".filter-section[data-default-collapsed='1']:not([data-fixed-open='1'])").map((section) => section.dataset.filterSection).filter(Boolean));
}

function resolveInitialFilterSectionsCollapsed() {
  const available = availableFilterSectionKeys();
  const stored = storageGet(FILTER_SECTION_STORAGE_KEY);
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        return new Set(parsed.filter((key) => available.has(key)));
      }
    } catch (_error) {
      // Fall back to the markup defaults.
    }
  }
  return defaultCollapsedFilterSectionKeys();
}

function persistFilterSectionsCollapsed() {
  storageSet(FILTER_SECTION_STORAGE_KEY, JSON.stringify([...STATE.filterSectionsCollapsed]));
}

function syncFilterSection(section) {
  if (!section) return;
  const key = section.dataset.filterSection || "";
  const fixedOpen = section.dataset.fixedOpen === "1";
  const collapsed = !fixedOpen && STATE.filterSectionsCollapsed.has(key);
  const button = section.querySelector(".filter-section-toggle");
  const bodyId = button ? button.getAttribute("aria-controls") : "";
  const body = bodyId ? document.getElementById(bodyId) : section.querySelector(".filter-section-body");

  section.classList.toggle("is-collapsed", collapsed);
  if (button) button.setAttribute("aria-expanded", String(!collapsed));
  if (body) body.hidden = collapsed;
}

function syncFilterSections() {
  for (const section of $$(".filter-section[data-filter-section]")) {
    syncFilterSection(section);
  }
}

function setFilterSectionCollapsed(key, collapsed, { persist = true } = {}) {
  if (!key) return;
  const section = $$(".filter-section[data-filter-section]")
    .find((candidate) => candidate.dataset.filterSection === key);
  if (section && section.dataset.fixedOpen === "1") {
    STATE.filterSectionsCollapsed.delete(key);
    syncFilterSection(section);
    if (persist) persistFilterSectionsCollapsed();
    return;
  }
  if (collapsed) STATE.filterSectionsCollapsed.add(key);
  else STATE.filterSectionsCollapsed.delete(key);
  syncFilterSection(section);
  if (persist) persistFilterSectionsCollapsed();
  requestAnimationFrame(renderList);
}

function initFilterSections() {
  STATE.filterSectionsCollapsed = resolveInitialFilterSectionsCollapsed();
  for (const button of $$(".filter-section-toggle")) {
    const section = button.closest(".filter-section[data-filter-section]");
    if (!section) continue;
    button.addEventListener("click", () => {
      const key = section.dataset.filterSection || "";
      setFilterSectionCollapsed(key, !STATE.filterSectionsCollapsed.has(key));
    });
  }
  syncFilterSections();
}


function getLanguageInfo(code) {
  if (!STATE.manifest || !Array.isArray(STATE.manifest.languages)) return DEFAULT_LANGUAGE_INFO;
  return STATE.manifest.languages.find((lang) => lang.code === code) || STATE.manifest.languages[0] || DEFAULT_LANGUAGE_INFO;
}

function resolveUiLocale(info) {
  return info && info.uiLocale ? info.uiLocale : "en";
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
  buildMediaChips();
  buildStoryIssueChips();
  buildRecoveryMethodChips();
  applyFilters();

  if (STATE.selectedKey) {
    const cached = STATE.convCache.get(STATE.selectedKey);
    if (cached) renderConv(cached);
  }
}


function dataPath(relativePath, languageCode = STATE.language) {
  return `data/lang/${encodeURIComponent(languageCode)}/${relativePath}`;
}

function cacheBustedPath(path, token = WEBUI_DATA_CACHE_TAG) {
  const sep = String(path).includes("?") ? "&" : "?";
  return `${path}${sep}v=${encodeURIComponent(token)}`;
}

function fetchJson(path, { fresh = false } = {}) {
  const token = fresh ? `${WEBUI_DATA_CACHE_TAG}-${Date.now()}` : WEBUI_DATA_CACHE_TAG;
  return fetch(cacheBustedPath(path, token), {
    cache: fresh ? "no-store" : "no-cache",
  });
}

async function loadLanguageSidecar(index, key, languageCode) {
  const rel = index && typeof index[key] === "string" ? index[key] : "";
  if (!rel) throw new Error(`index.json missing ${key} sidecar`);
  const res = await fetchJson(dataPath(rel, languageCode), { fresh: true });
  if (!res.ok) throw new Error(`${rel} HTTP ${res.status}`);
  return res.json();
}

function applyStorySearchPayload(payload) {
  const byKey = new Map();
  for (const row of (payload && payload.entries) || []) {
    const key = String(row && row.k || "");
    const text = String(row && row.x || "").trim();
    if (key && text) byKey.set(key, text);
  }

  if (!byKey.size) return;
  for (const entry of STATE.entries || []) {
    const text = byKey.get(String(entry && entry.k || ""));
    if (text) entry.x = text;
  }
}

async function ensureStorySearchIndexLoaded(languageCode = STATE.language, token = STATE.indexRequestToken) {
  if (STATE.storySearchLoaded && STATE.storySearchLanguage === languageCode) return true;
  if (STATE.storySearchPromise) return STATE.storySearchPromise;

  const rel = STATE.index && typeof STATE.index.search === "string" ? STATE.index.search : "";
  if (!rel) {
    STATE.storySearchLoaded = true;
    STATE.storySearchLanguage = languageCode;
    return true;
  }

  STATE.storySearchPromise = fetchJson(dataPath(rel, languageCode), { fresh: true })
    .then((res) => {
      if (!res.ok) throw new Error(`${rel} HTTP ${res.status}`);
      return res.json();
    })
    .then((payload) => {
      if (token !== STATE.indexRequestToken || STATE.language !== languageCode) return false;
      applyStorySearchPayload(payload);
      STATE.storySearchLoaded = true;
      STATE.storySearchLanguage = languageCode;
      STATE.storySearchPromise = null;
      return true;
    })
    .catch((_error) => {
      if (token === STATE.indexRequestToken && STATE.language === languageCode) {
        STATE.storySearchLoaded = true;
        STATE.storySearchLanguage = languageCode;
      }
      STATE.storySearchPromise = null;
      return false;
    });

  return STATE.storySearchPromise;
}

function loadStoryMediaPayload() {
  if (STATE.storyMediaPayload) return Promise.resolve(STATE.storyMediaPayload);
  if (STATE.storyMediaPromise) return STATE.storyMediaPromise;
  STATE.storyMediaPromise = fetchJson("data/assets/story_media.json")
    .then((res) => {
      if (!res.ok) throw new Error(`assets/story_media.json HTTP ${res.status}`);
      return res.json();
    })
    .then((payload) => {
      STATE.storyMediaPayload = payload || {};
      STATE.storyMediaPromise = null;
      return STATE.storyMediaPayload;
    })
    .catch((error) => {
      STATE.storyMediaPromise = null;
      throw error;
    });
  return STATE.storyMediaPromise;
}

function storyMediaEntries(payload, kind) {
  return ((payload && payload.entries) || []).filter((entry) => entry && entry.k === kind && entry.r);
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
      const res = await fetchJson(dataPath(`conv/${encodeURIComponent(entry.k)}.json`, languageCode));
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
    const res = await fetchJson(dataPath(file, languageCode));
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

  STATE.inlineImageLookupPromise = loadStoryMediaPayload()
    .then((payload) => {
      const byStem = new Map();
      const byNumber = new Map();
      STATE.inlineImageSourceRoots = payload && payload.sourceRoots ? payload.sourceRoots : {};
      STATE.inlineImageExportRoot = String(payload && payload.root ? payload.root : "export_full");

      for (const raw of storyMediaEntries(payload, "image")) {
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

  STATE.wikiVideoLookupPromise = loadStoryMediaPayload()
    .then((payload) => {
      const byStem = new Map();
      if (payload && payload.sourceRoots) {
        STATE.inlineImageSourceRoots = {
          ...(STATE.inlineImageSourceRoots || {}),
          ...payload.sourceRoots,
        };
      }
      STATE.inlineImageExportRoot = String(payload && payload.root ? payload.root : STATE.inlineImageExportRoot || "export_full");

      for (const raw of storyMediaEntries(payload, "video")) {
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

function formatAssetBytes(size) {
  const bytes = Number(size) || 0;
  if (bytes <= 0) return "";
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function scoreNarrativeVideoRef(ref) {
  const rel = String(ref && ref.rel || "");
  const source = String(ref && ref.source || "");
  const format = String(ref && ref.format || "").toLowerCase();
  const gender = String(ref && ref.gender || "").toLowerCase();
  const activeGender = resolveGenderVariant();
  let score = 0;
  if (isBrowserPlayableVideo(rel)) score += 1000;
  if (format === "mp4") score += 100;
  else if (format === "webm" || format === "ogv") score += 80;
  else if (format === "usm") score += 10;
  if (source === "StreamingAssets-structured") score += 60;
  else if (source === "Persistent-structured") score += 50;
  else if (source === "raw_vfs") score += 5;
  if (gender === activeGender) score += 90;
  else if (!gender) score += 60;
  return score;
}

function narrativeVideoRefsForConv(conv) {
  const refs = Array.isArray(conv && conv.narrativeVideos)
    ? conv.narrativeVideos.filter((ref) => ref && ref.rel)
    : [];
  return narrativeVideoSelectionForRefs(refs).refs;
}

function narrativeVideoSelectionForRefs(refs) {
  if (!Array.isArray(refs) || !refs.length) {
    return { refs: [], omitted: 0 };
  }

  const byStem = new Map();
  for (const ref of refs) {
    const key = String(ref.baseStem || ref.stem || ref.name || ref.rel);
    const current = byStem.get(key);
    if (!current || scoreNarrativeVideoRef(ref) > scoreNarrativeVideoRef(current)) {
      byStem.set(key, ref);
    }
  }
  const distinctRefs = Array.from(byStem.values())
    .sort((a, b) => scoreNarrativeVideoRef(b) - scoreNarrativeVideoRef(a)
      || String(a.name || a.rel).localeCompare(String(b.name || b.rel)));
  return {
    refs: distinctRefs.slice(0, NARRATIVE_VIDEO_DISPLAY_LIMIT),
    omitted: Math.max(0, distinctRefs.length - NARRATIVE_VIDEO_DISPLAY_LIMIT),
  };
}

function narrativeVideoSelectionForConv(conv) {
  const refs = Array.isArray(conv && conv.narrativeVideos)
    ? conv.narrativeVideos.filter((ref) => ref && ref.rel)
    : [];
  return narrativeVideoSelectionForRefs(refs);
}

function renderNarrativeVideosBlock(conv) {
  if (!STATE.wikiVideoLookupLoaded) return null;
  const selection = narrativeVideoSelectionForConv(conv);
  const refs = selection.refs;
  if (!refs.length) return null;

  const box = document.createElement("div");
  box.className = "summary-box narrative-video-box";

  const label = document.createElement("div");
  label.className = "summary-label";
  label.textContent = uiText("narrativeVideo");
  box.appendChild(label);

  const grid = document.createElement("div");
  grid.className = "wiki-image-grid narrative-video-grid";
  for (const ref of refs) {
    const size = formatAssetBytes(ref.size);
    const gender = ref.gender ? ref.gender.toUpperCase() : "";
    const suffix = [gender, size].filter(Boolean).join(", ");
    grid.appendChild(renderWikiVideoItem({
      rel: ref.rel,
      name: ref.name,
      label: suffix ? `${ref.name} (${suffix})` : ref.name,
      size: ref.size,
    }));
  }
  box.appendChild(grid);

  const omitted = selection.omitted;
  if (omitted > 0) {
    const row = document.createElement("div");
    row.className = "summary-text narrative-video-more";
    row.textContent = uiText("narrativeVideoMore").replace("{count}", String(omitted));
    box.appendChild(row);
  }

  appendDebugTrace(box, conv && conv._debug && conv._debug.narrativeVideos, "narrative videos");
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

  return (STATE.manifest && STATE.manifest.defaultLanguage) || DEFAULT_LANGUAGE_INFO.code;
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
  const basicFilterLabel = $("#basic-filter-label");
  if (basicFilterLabel) basicFilterLabel.textContent = uiText("basicFilters");
  $("#language-label").textContent = uiText("language");
  $("#kind-label").textContent = uiText("kind");
  $("#type-label").textContent = uiText("type");
  const mediaLabel = $("#media-label");
  if (mediaLabel) mediaLabel.textContent = uiText("mediaFilter");
  $("#story-issue-label").textContent = uiText("storyIssueFilter");
  $("#recovery-method-label").textContent = uiText("recoveryMethodFilter");
  const searchLabel = $("#search-label");
  if (searchLabel) searchLabel.textContent = uiText("searchFilter");
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
  const languages = STATE.manifest.languages;

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
  const res = await fetchJson("data/manifest.json", { fresh: true });
  if (!res.ok) throw new Error(`manifest.json HTTP ${res.status}`);
  const manifest = await res.json();
  if (!Array.isArray(manifest.languages) || !manifest.languages.length) {
    throw new Error("manifest.json does not list any languages");
  }
  return manifest;
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
    const res = await fetchJson(dataPath("index.json", info.code), { fresh: true });
    if (!res.ok) throw new Error(`index.json HTTP ${res.status}`);
    const index = await res.json();
    if (token !== STATE.indexRequestToken) return;

    const [actorsPayload, missionsPayload] = await Promise.all([
      loadLanguageSidecar(index, "actors", info.code),
      loadLanguageSidecar(index, "missions", info.code),
    ]);
    if (token !== STATE.indexRequestToken) return;

    STATE.index = index;
    STATE.actorNames = normalizeActorNames(actorsPayload.actorNames || {});
    STATE.missionNames = missionsPayload.missionNames || {};
    STATE.entries = normalizeLoadedEntries(index.entries || []);
    STATE.entryByKey = new Map(STATE.entries.map((entry) => [entry.k, entry]));
    STATE.archiveMetadataByKey = new Map();
    STATE.archiveResearchById = new Map();
    STATE.archiveMetadataLanguage = "";
    STATE.storySearchLoaded = false;
    STATE.storySearchPromise = null;
    STATE.storySearchLanguage = "";
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
    buildMediaChips();
    buildStoryIssueChips();
    buildRecoveryMethodChips();
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
    initFilterSections();
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
async function loadConv(key, { force = false } = {}) {
  const languageCode = STATE.language;
  const wasSelected = STATE.selectedKey === key;
  STATE.selectedKey = key;
  $$(".item").forEach((n) => n.classList.toggle("selected", n.dataset.key === key));
  syncRevealCurrentButton();

  if (!force && !wasSelected && STATE.convCache.has(key)) {
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
    const res = await fetchJson(dataPath(`conv/${encodeURIComponent(key)}.json`, languageCode), {
      fresh: force || wasSelected,
    });
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

function renderSnsBranchLine(line, convKey = "") {
  const item = document.createElement("div");
  item.className = "line branch-flow-line branch-sns-line" + (line && line.text ? "" : " empty");
  setLineAnchor(item, convKey, resolveLineId(line));

  const speaker = document.createElement("div");
  speaker.className = "actor";
  const sp = line.speaker || "";
  const display = sp ? speakerName(sp) : uiText("systemSpeaker");
  speaker.innerHTML = escapeHtml(display) +
    (sp ? `<span class="actor-id">${escapeHtml(sp)}</span>` : "");
  item.appendChild(speaker);

  const body = document.createElement("div");
  body.className = "body";
  if (line.text) {
    const text = document.createElement("div");
    text.className = "text";
    text.innerHTML = highlight(line.text, STATE.filters.q);
    body.appendChild(text);
  } else if (line.linkMission) {
    const system = document.createElement("div");
    system.className = "system";
    system.textContent = `-> ${uiText("linkedMission")}: ${line.linkMission}`;
    body.appendChild(system);
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
    body.appendChild(opts);
  }

  appendLineId(body, line);
  appendDebugTrace(body, line._debug, "branch line");
  item.appendChild(body);
  return item;
}

function renderSnsBranchGroup(group, convKey = "") {
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
      for (const line of branch.lines) lines.appendChild(renderSnsBranchLine(line, convKey));
      col.appendChild(lines);
    }

    appendDebugTrace(col, branch.option._debug, "reply option");
    cols.appendChild(col);
  }

  optGroup.appendChild(cols);

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

function lineAnchorId(convKey, lineId) {
  const convPart = encodeURIComponent(String(convKey || ""));
  const linePart = encodeURIComponent(String(lineId || ""));
  return `line-${convPart}-${linePart}`;
}

function setLineAnchor(node, convKey, lineId) {
  const id = String(lineId || "");
  if (!node || !convKey || !id) return;
  node.id = lineAnchorId(convKey, id);
  node.dataset.lineId = id;
}

function scrollToLineAnchor(convKey, lineId) {
  const anchor = document.getElementById(lineAnchorId(convKey, lineId));
  if (!anchor) return false;
  anchor.scrollIntoView({ block: "center", behavior: "smooth" });
  anchor.classList.remove("line-flash");
  void anchor.offsetWidth;
  anchor.classList.add("line-flash");
  return true;
}

function createLineJumpChip(conv, lineId, labelKey, className, titleKey) {
  const line = String(lineId || "");
  if (!line) return null;
  const chip = document.createElement("a");
  chip.className = className;
  chip.textContent = uiText(labelKey).replace("{line}", line);
  chip.href = `#${lineAnchorId(conv && conv.key, line)}`;
  chip.title = uiText(titleKey || "optJumpLineTitle").replace("{line}", line);
  chip.addEventListener("click", (event) => {
    event.preventDefault();
    scrollToLineAnchor(conv && conv.key, line);
  });
  return chip;
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

function sameSceneOptionOutcomes(option, conv, outcomesByOptionId) {
  if (!option || !outcomesByOptionId) return [];
  return (outcomesByOptionId.get(option.id) || []).filter((outcome) => {
    const firstSceneKey = String(outcome.firstSceneKey || "");
    return !firstSceneKey || isSameConversationSceneKey(firstSceneKey, conv);
  });
}

function optionRiskLineInfos(option) {
  const out = [];
  for (const tag of Array.isArray(option && option.riskTags) ? option.riskTags : []) {
    const lineId = String(tag && tag.lineId || "");
    if (!lineId || out.some((item) => item.lineId === lineId)) continue;
    const branchRiskCode = String(tag.branchRiskCode || "");
    const source = branchRiskCode === "cosmeticChoice"
      ? "shared"
      : (branchRiskCode === "inferredFollowingLines" || tag.source === "dialogTimeline" ? "inferred" : "tree");
    out.push({ lineId, source });
  }
  return out;
}

function optionGroupHasTimelineRouteBranches(group) {
  const risk = group && group.optionBranchRisk;
  return Boolean(risk && risk.code === "timelineRouteBranches");
}

function optionBranchRiskJumpInfo(risk) {
  const lineId = String(risk && risk.commonContinuationLineId || "");
  if (!lineId) return null;
  const code = String(risk && risk.code || "");
  const sharedCodes = new Set(["cosmeticChoice", "sharedTimelineContinuation"]);
  return {
    lineId,
    source: sharedCodes.has(code) ? "shared" : "inferred",
  };
}

function firstOptionJumpInfo(option, group, conv, outcomesByOptionId) {
  const branchLines = normalizeLineOrderIdList(option && option.branchLines);
  if (branchLines.length) {
    return {
      lineId: branchLines[0],
      source: optionGroupHasTimelineRouteBranches(group) ? "timeline" : "tree",
    };
  }

  for (const outcome of sameSceneOptionOutcomes(option, conv, outcomesByOptionId)) {
    const lineId = String(outcome.firstLineId || "");
    if (lineId) return { lineId, source: "tree" };
  }

  const riskLineInfos = optionRiskLineInfos(option);
  if (riskLineInfos.length) return riskLineInfos[0];

  return optionBranchRiskJumpInfo(group && group.optionBranchRisk) || { lineId: "", source: "" };
}

function optionJumpLabelKey(source) {
  if (source === "tree") return "optJumpLineTree";
  if (source === "timeline") return "optJumpLineTimeline";
  if (source === "shared") return "optJumpLineShared";
  if (source === "inferred") return "optJumpLineInferred";
  return "optJumpLine";
}

function optionJumpTitleKey(source) {
  if (source === "tree") return "optJumpLineTitleTree";
  if (source === "timeline") return "optJumpLineTitleTimeline";
  if (source === "shared") return "optJumpLineTitleShared";
  if (source === "inferred") return "optJumpLineTitleInferred";
  return "optJumpLineTitle";
}

function optionJumpSourceClass(source) {
  return source ? ` is-${source}` : "";
}

function optionGroupForOptionId(conv, optionId) {
  const targetGroup = optionGroupNumberFromOptionId(optionId, conv && conv.key);
  if (targetGroup === null) return null;
  for (const group of (conv && conv.optionGroups) || []) {
    if (Number(group && group.g) === targetGroup) return group;
  }
  return null;
}

function timelineReverseRangeLineIdsForOption(option, group) {
  const optionId = String(option && option.id || "");
  const risk = group && group.optionBranchRisk && typeof group.optionBranchRisk === "object"
    ? group.optionBranchRisk
    : null;
  if (!optionId || !risk || risk.code !== "timelineRouteBranches") return [];
  const byOption = risk.reverseRangeLineIdsByOption && typeof risk.reverseRangeLineIdsByOption === "object"
    ? risk.reverseRangeLineIdsByOption
    : null;
  return lineOrderUniqueList(byOption && byOption[optionId]);
}

function optionLoopLineIds(option, group, conv, outcomesByOptionId, lineOrderIndexById = null) {
  const out = [];
  const currentGroup = group && group.g != null
    ? Number(group.g)
    : optionGroupNumberFromOptionId(option && option.id, conv && conv.key);
  const currentAfterLineId = String(group && group.after || "");
  if (currentAfterLineId && timelineReverseRangeLineIdsForOption(option, group).length) {
    out.push(currentAfterLineId);
  }
  const hasCurrentLineIdx = lineOrderIndexById instanceof Map && lineOrderIndexById.has(currentAfterLineId);
  const currentLineIdx = hasCurrentLineIdx ? lineOrderIndexById.get(currentAfterLineId) : null;
  for (const outcome of sameSceneOptionOutcomes(option, conv, outcomesByOptionId)) {
    if (!outcome.loop) continue;
    const debug = outcome._debug || {};
    const returnOptionIds = (debug.returnOptionIds || []).filter(Boolean);
    const targetGroupInfo = returnOptionIds.length ? optionGroupForOptionId(conv, returnOptionIds[0]) : null;
    const targetGroup = returnOptionIds.length
      ? optionGroupNumberFromOptionId(returnOptionIds[0], conv && conv.key)
      : null;
    const targetAfterLineId = String(targetGroupInfo && targetGroupInfo.after || "");
    const hasTargetLineIdx = lineOrderIndexById instanceof Map && lineOrderIndexById.has(targetAfterLineId);
    const targetLineIdx = hasTargetLineIdx ? lineOrderIndexById.get(targetAfterLineId) : null;
    const sameMenuLoop = outcome.loop.kind === "sameOptionMenuReturn";
    const backwardByLine = hasCurrentLineIdx && hasTargetLineIdx && targetLineIdx <= currentLineIdx;
    const backwardByGroup = !hasCurrentLineIdx && !hasTargetLineIdx && targetGroup !== null
      && currentGroup !== null
      && targetGroup <= currentGroup;
    const backwardLoop = backwardByLine || backwardByGroup;
    if (!sameMenuLoop && !backwardLoop) continue;
    const pathLineIds = normalizeLineOrderIdList(outcome.pathLineIds);
    const lineId = String(targetGroupInfo && targetGroupInfo.after || "")
      || pathLineIds[0]
      || String(outcome.firstLineId || "");
    if (lineId && !out.includes(lineId)) out.push(lineId);
  }
  return out;
}

function renderOptionJumpTags(option, group, conv, outcomesByOptionId) {
  const jumpInfo = firstOptionJumpInfo(option, group, conv, outcomesByOptionId);
  const jumpLineId = String(jumpInfo.lineId || "");
  if (!jumpLineId) return null;

  const wrap = document.createElement("div");
  wrap.className = "opt-jump-tags";
  const jumpChip = createLineJumpChip(
    conv,
    jumpLineId,
    optionJumpLabelKey(jumpInfo.source),
    "opt-target-chip opt-target-chip-line" + optionJumpSourceClass(jumpInfo.source),
    optionJumpTitleKey(jumpInfo.source)
  );
  if (jumpChip) wrap.appendChild(jumpChip);
  return wrap.childNodes.length ? wrap : null;
}

function renderOptionLoopTagsForLineIds(conv, loopLineIds) {
  if (!loopLineIds.length) return null;

  const wrap = document.createElement("div");
  wrap.className = "branch-loop-tags";
  for (const lineId of loopLineIds) {
    const loopChip = createLineJumpChip(
      conv,
      lineId,
      "optJumpLoopLine",
      "opt-target-chip opt-target-chip-loop",
      "optJumpLoopLineTitle"
    );
    if (loopChip) wrap.appendChild(loopChip);
  }
  return wrap.childNodes.length ? wrap : null;
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

    if (isDirectMenuJump) {
      const seenSubmenuScenes = new Set();
      for (const submenuTarget of outcome.submenuTargets || []) {
        if (!submenuTarget || typeof submenuTarget !== "object") continue;
        const sk = String(submenuTarget.sceneKey || "");
        if (!sk || isSameConversationSceneKey(sk, conv)) continue;
        const optionId = String(submenuTarget.optionId || "");
        const optionText = String(submenuTarget.text || "");
        seenSubmenuScenes.add(sk);
        push(`submenu:${sk}:${optionId || optionText}`, {
          kind: "sceneSubmenu",
          sceneKey: sk,
          optionId,
          optionText,
        });
      }
      for (const sk of outcome.submenuSceneKeys || []) {
        if (sk && !seenSubmenuScenes.has(sk) && !isSameConversationSceneKey(sk, conv)) {
          push(`submenu:${sk}`, { kind: "sceneSubmenu", sceneKey: sk });
        }
      }
    }

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
  const hideSelfMenu = Boolean(options.hideSelfMenu);

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
    } else if (target.kind === "selfMenu" && !hideSelfMenu) {
      chip = document.createElement("span");
      chip.className = "opt-target-chip opt-target-chip-self";
      chip.textContent = uiText("optTargetSelfMenu");
    } else if (target.kind === "scene" || target.kind === "sceneSubmenu") {
      const rawSceneKey = String(target.sceneKey || "");
      const resolvedSceneKey = resolveConversationEntryKey(rawSceneKey) || rawSceneKey;
      chip = document.createElement("a");
      chip.className = "opt-target-chip opt-target-chip-scene";
      const sceneLabel = (target.kind === "sceneSubmenu" ? uiText("optTargetSceneSubmenu") : uiText("optTargetScene"))
        .replace("{key}", rawSceneKey);
      chip.textContent = target.kind === "sceneSubmenu" && target.optionText
        ? `${target.optionText} ${sceneLabel}`
        : sceneLabel;
      chip.href = `#${encodeURIComponent(resolvedSceneKey)}`;
      if (target.optionId) {
        chip.title = `${target.optionId} -> ${rawSceneKey}`;
      }
      if (resolvedSceneKey && resolvedSceneKey !== rawSceneKey) {
        chip.title = chip.title
          ? `${chip.title} (${resolvedSceneKey})`
          : `${rawSceneKey} -> ${resolvedSceneKey}`;
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
    if (!tag) continue;
    const node = document.createElement("span");
    const lineId = String(tag.lineId || "");
    if (tag.code === "rawOptionIndexMatchedLine") {
      node.className = "opt-risk-tag opt-risk-tag-indexed";
      node.textContent = uiText("optRiskRawIndexMatchedLine");
      node.title = uiText("optRiskRawIndexMatchedLineTitle").replace("{line}", lineId || "?");
    } else if (tag.code === "inferredFollowingLine") {
      node.className = "opt-risk-tag opt-risk-tag-inferred";
      node.textContent = uiText("optRiskInferredFollowingLine");
      node.title = uiText("optRiskInferredFollowingLineTitle").replace("{line}", lineId || "?");
    } else {
      continue;
    }
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

function getConvLineOrderCoverageWarning(conv) {
  const warning = findConvWarning(conv, "sceneOrderDisorder");
  const lineOrder = warning && warning.lineOrder && typeof warning.lineOrder === "object"
    ? warning.lineOrder
    : null;
  if (!lineOrder) return null;
  const ids = normalizeLineOrderIdList(lineOrder.uncoveredLineIds);
  return ids.length || Number(lineOrder.uncoveredLineCount) > 0 ? lineOrder : null;
}

function getConvPartialLineOrderWarning(conv) {
  const lineOrder = getConvLineOrderCoverageWarning(conv);
  return lineOrder && lineOrder.status === "partial" ? lineOrder : null;
}

function getConvUncoveredLineIds(conv) {
  const lineOrder = getConvLineOrderCoverageWarning(conv);
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
  appendWarningEvidence(section, data.evidence);
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
  if (warning.code === "inferredOptionResponse") {
    title = uiText("warningInferredOptionResponseTitle");
    body = uiText("warningInferredOptionResponseBody");
    const lineIds = normalizeLineOrderIdList(warning.lineIds);
    if (lineIds.length) {
      const section = document.createElement("section");
      section.className = "conv-warning-section";
      appendLineIdTagList(section, "", lineIds);
      detailSections.push(section);
    }
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
  let visible = warnings;
  if (warnings.some((warning) => warning.code === "sceneOrderDisorder")) {
    visible = warnings.filter((warning) => warning.code !== "inferredOptionLayout");
  }
  return visible;
}

function convRuntimeRegistry(conv) {
  const debug = conv && conv._debug && typeof conv._debug === "object"
    ? conv._debug
    : null;
  const registry = debug && debug.runtimeRegistry && typeof debug.runtimeRegistry === "object"
    ? debug.runtimeRegistry
    : null;
  return registry;
}

function runtimeRegistryLinesByTrunk(registry) {
  const raw = registry && registry.linesByTrunk && typeof registry.linesByTrunk === "object"
    ? registry.linesByTrunk
    : null;
  if (!raw) return [];
  return Object.entries(raw)
    .map(([trunk, values]) => {
      const lineIds = Array.isArray(values)
        ? values.map((value) => String(value || "").trim()).filter(Boolean)
        : [];
      if (!lineIds.length) return "";
      return `trunk ${trunk}: ${lineIds.join(", ")}`;
    })
    .filter(Boolean);
}

function runtimeRegistryOptionsByGroup(registry) {
  const raw = registry && registry.optionsByGroup && typeof registry.optionsByGroup === "object"
    ? registry.optionsByGroup
    : null;
  if (!raw) return [];
  return Object.entries(raw)
    .map(([group, values]) => {
      const optionIds = Array.isArray(values)
        ? values.map((value) => String(value || "").trim()).filter(Boolean)
        : [];
      if (!optionIds.length) return "";
      return `option group ${group}: ${optionIds.join(", ")}`;
    })
    .filter(Boolean);
}

function lineOrderRegistryTitle(registry, fallback = "") {
  if (!registry) return "";
  const parts = [];
  const primary = fallback
    ? String(fallback)
    : (registry.reason ? String(registry.reason) : "");
  if (primary) parts.push(primary);
  if (registry.sceneKey) parts.push(`sceneKey: ${registry.sceneKey}`);
  if (registry.webuiKey && registry.webuiKey !== registry.sceneKey) {
    parts.push(`webuiKey: ${registry.webuiKey}`);
  }
  for (const line of runtimeRegistryLinesByTrunk(registry)) parts.push(line);
  for (const line of runtimeRegistryOptionsByGroup(registry)) parts.push(line);
  return parts.join("\n");
}

function lineOrderModeText(mode) {
  if (mode === "dialogTree") return uiText("lineOrderModeDialogTree");
  if (mode === "dialogTreeFragment") return uiText("lineOrderModeDialogTreeFragment");
  if (mode === "dialogTreeExtraConfig") return uiText("lineOrderModeDialogTreeExtraConfig");
  if (mode === "dialogTreeCinematicTimeline") return uiText("lineOrderModeDialogTreeCinematicTimeline");
  if (mode === "authoredBlend") return uiText("lineOrderModeAuthoredBlend");
  if (mode === "authoredNumericStitch") return uiText("lineOrderModeAuthoredNumericStitch");
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
    || mode === "authoredNumericStitch"
    || mode === "dialogTimeline"
  ) return "authored";
  if (mode === "lineIdSuffix") return "fallback";
  if (mode) return "fallback";
  return "missing";
}

function lineOrderRuntimeMode(conv, lineOrder, originalLineIds, orderedLineIds) {
  const registry = convRuntimeRegistry(conv);
  if (!registry || !lineOrder || lineOrder.mode !== "lineIdSuffix") return null;
  if (!originalLineIds.length || !orderedLineIds.length) return null;
  if (!lineOrderIdListEquals(originalLineIds, orderedLineIds)) return null;
  const title = lineOrderRegistryTitle(registry);
  if (registry.registered === false) {
    return {
      text: uiText("lineOrderModeUnregisteredScene"),
      tone: "neutral",
      title,
    };
  }
  if (registry.registered === true) {
    return {
      text: uiText("lineOrderModeRuntimeRowIteration"),
      tone: "success",
      title,
    };
  }
  return null;
}

function lineOrderRegistryChip(registry) {
  if (!registry) return null;
  const title = lineOrderRegistryTitle(registry);
  if (registry.registered === false) {
    return {
      text: uiText("lineOrderRegistryUnregistered"),
      tone: "neutral",
      title,
    };
  }
  if (registry.registered === true) {
    const trunks = Number(registry.trunkCount) || 0;
    const lines = Number(registry.lineCount) || 0;
    if (trunks || lines) {
      return {
        text: uiText("lineOrderRegistryTrunks")
          .replace("{trunks}", String(trunks))
          .replace("{lines}", String(lines)),
        tone: "success",
        title,
      };
    }
    return {
      text: uiText("lineOrderRegistryRegistered"),
      tone: "success",
      title,
    };
  }
  return null;
}

function lineOrderRegistryDeltaChip(registry) {
  if (!registry || registry.registered !== true) return null;
  const raw = registry.lineCountDelta;
  if (typeof raw !== "number" || !Number.isFinite(raw) || raw === 0) return null;
  const absText = String(Math.abs(raw));
  const labelKey = raw > 0
    ? "lineOrderRegistryDeltaPositive"
    : "lineOrderRegistryDeltaNegative";
  const text = uiText(labelKey).replace("{count}", absText);
  const title = lineOrderRegistryTitle(registry, registry.note || registry.reason || "");
  // Negative delta = webui shows fewer lines than the runtime registry
  // addresses. That's a stronger signal (something missing) than positive
  // delta (extra summary/hint rows in webui that the runtime doesn't
  // address by trunk id), so colour them differently.
  return {
    text,
    tone: raw > 0 ? "neutral" : "fallback",
    title,
  };
}

function lineOrderModeDetailText(mode) {
  if (mode === "dialogTree") return uiText("lineOrderModeDetailDialogTree");
  if (mode === "dialogTreeFragment") return uiText("lineOrderModeDetailDialogTreeFragment");
  if (mode === "dialogTreeExtraConfig") return uiText("lineOrderModeDetailDialogTreeExtraConfig");
  if (mode === "dialogTreeCinematicTimeline") return uiText("lineOrderModeDetailDialogTreeCinematicTimeline");
  if (mode === "authoredBlend") return uiText("lineOrderModeDetailAuthoredBlend");
  if (mode === "authoredNumericStitch") return uiText("lineOrderModeDetailAuthoredNumericStitch");
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

function createLineOrderStatChip(text, tone = "", title = "") {
  const chip = document.createElement("span");
  chip.className = "line-order-chip" + (tone ? ` is-${tone}` : "");
  chip.textContent = text;
  if (title) chip.title = title;
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
  const pushGroup = (candidate) => {
    if (!candidate || candidate === group || seen.has(candidate)) return;
    groups.push(candidate);
    seen.add(candidate);
  };
  for (const optionId of normalizeLineOrderIdList(group.continuationOptionIds)) {
    pushGroup(optionGroupForOptionId(ctx.conv, optionId));
  }
  for (const optionId of normalizeLineOrderIdList(group.optionBranchRisk && group.optionBranchRisk.continuationOptionIds)) {
    pushGroup(optionGroupForOptionId(ctx.conv, optionId));
  }
  for (const option of group.options || []) {
    for (const lineId of normalizeLineOrderIdList(option.branchLines)) {
      for (const candidate of ctx.groupsByLineId.get(lineId) || []) {
        if (!candidate || candidate === group || seen.has(candidate)) continue;
        if (!isLineOrderSharedContinuationGroup(group, candidate, ctx.outcomesByOptionId, ctx.conv.key)) continue;
        pushGroup(candidate);
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

function renderSourceLinksBlock(conv) {
  const links = Array.isArray(conv && conv.sourceLinks)
    ? conv.sourceLinks.filter((link) => link && typeof link === "object")
    : [];
  if (!links.length) return null;

  const box = document.createElement("div");
  box.className = "summary-box source-links-box";

  const label = document.createElement("div");
  label.className = "summary-label";
  label.textContent = uiText("sourceEvidence");
  box.appendChild(label);

  for (const link of links.slice(0, 8)) {
    const row = document.createElement("div");
    row.className = "summary-text source-link-row";
    const bits = [];
    if (link.source) bits.push(String(link.source));
    if (link.file) bits.push(String(link.file));
    if (link.path) bits.push(String(link.path));
    if (link.raw) bits.push(String(link.raw));
    row.textContent = bits.join(" · ");
    box.appendChild(row);
    appendDebugTrace(row, link._debug, "source link");
  }

  const omitted = Number(conv.sourceLinksOmitted || 0);
  if (omitted > 0) {
    const row = document.createElement("div");
    row.className = "summary-text source-link-row source-link-more";
    row.textContent = uiText("sourceEvidenceMore").replace("{count}", String(omitted));
    box.appendChild(row);
  }

  appendDebugTrace(box, conv && conv._debug && conv._debug.sourceLinks, "source links");
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
  const registry = convRuntimeRegistry(conv);
  const runtimeMode = lineOrderRuntimeMode(conv, lineOrder, originalLineIds, orderedLineIds);
  strip.appendChild(createLineOrderStatChip(
    runtimeMode ? runtimeMode.text : lineOrderModeText(lineOrder.mode),
    runtimeMode ? runtimeMode.tone : lineOrderTone(lineOrder.mode),
    runtimeMode ? runtimeMode.title : ""
  ));
  const registryChip = lineOrderRegistryChip(registry);
  if (registryChip && !(runtimeMode && registry && registry.registered === false)) {
    strip.appendChild(createLineOrderStatChip(
      registryChip.text,
      registryChip.tone,
      registryChip.title
    ));
  }
  const deltaChip = lineOrderRegistryDeltaChip(registry);
  if (deltaChip) {
    strip.appendChild(createLineOrderStatChip(deltaChip.text, deltaChip.tone, deltaChip.title));
  }
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
  if (conv.chatTitle) meta.push(`chatTitle=${conv.chatTitle}`);
  if (conv.chatType !== undefined) meta.push(`chatType=${conv.chatType}`);
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
  const lineOrderIndexById = new Map(
    conv.lines
      .map((ln, idx) => [String(ln && ln.id || ""), idx])
      .filter(([lineId]) => lineId)
  );
  const dlgBranchSkipIds = new Set();
  const renderedDlgLineIds = new Set();
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

  const sourceLinksBlock = renderSourceLinksBlock(conv);
  if (sourceLinksBlock) frag.appendChild(sourceLinksBlock);

  const narrativeVideoBlock = renderNarrativeVideosBlock(conv);
  if (narrativeVideoBlock) frag.appendChild(narrativeVideoBlock);

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
  const lineRenderIdx = (lineOrId) => {
    const id = typeof lineOrId === "string"
      ? lineOrId
      : String(lineOrId && lineOrId.id || "");
    if (id && lineOrderIndexById.has(id)) return lineOrderIndexById.get(id);
    return lineRawIdx({ id });
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
  // Groups pinned to a specific dialog line by `after`; trunk anchors render
  // inline, while branch-owned anchors render as flat siblings in the owning
  // branch chain so option columns show evidence order without nested menus.
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
  const uniqueOptionGroups = (groups) => {
    const out = [];
    const seen = new Set();
    for (const group of groups || []) {
      if (!group || seen.has(group)) continue;
      out.push(group);
      seen.add(group);
    }
    return out;
  };
  const isBackLoopAnchorLineForGroup = (ownerGroup, lineId) => {
    if (!lineId) return false;
    const anchorsOtherGroup = (groupsByLineId.get(lineId) || [])
      .some((other) => other && other !== ownerGroup);
    if (!anchorsOtherGroup) return false;
    const afterIdx = lineRenderIdx((ownerGroup && ownerGroup.after) || "") ?? -1;
    const lidIdx = lineRenderIdx(lineId) ?? -1;
    return lidIdx <= afterIdx;
  };
  const branchAnchoredGroupsForLineIds = (lineIds, ownerGroup) => {
    const out = [];
    const seen = new Set();
    for (const lineId of lineIds || []) {
      if (isBackLoopAnchorLineForGroup(ownerGroup, lineId)) continue;
      for (const group of groupsByLineId.get(lineId) || []) {
        if (!group || group === ownerGroup || seen.has(group)) continue;
        out.push(group);
        seen.add(group);
      }
    }
    return out;
  };
  const isBranchAnchoredPullEligible = (target, lineIds) => {
    if (!target || continuationOptGroups.has(target) || renderedOptGroups.has(target)) return false;
    if (isPullEligible(target)) return true;
    return anchoredOptGroups.has(target)
      && lineIds.has(String(target.after || ""));
  };
  const chipOptions = { isReturnTarget: (target) => renderedOptGroups.has(target) };

  const renderDialogFlowLine = (ln, options = {}) => {
    const row = document.createElement("div");
    row.className = "line"
      + (options.branchColumn ? " branch-flow-line" : "")
      + (ln.text ? "" : " empty")
      + (ln.id && uncoveredLineIdSet.has(ln.id) ? " line-uncovered" : "")
      + (ln.id && duplicateTimestampLineIdSet.has(ln.id) ? " line-duplicate-timestamp" : "");
    setLineAnchor(row, conv.key, ln.id);

    const actor = document.createElement("div");
    actor.className = "actor";
    const speaker = resolveRenderedSpeaker(ln);
    if (speaker.display || speaker.aid) {
      appendSpeakerLabel(actor, speaker.display, {
        originalName: speaker.original,
        aid: speaker.aid,
      });
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
      const text = document.createElement("div");
      text.className = "text";
      text.innerHTML = highlight(ln.text, STATE.filters.q);
      body.appendChild(text);
      appendDebugTrace(body, ln._debug, "line");
    }
    appendLineId(body, ln);
    if (ln.id && uncoveredLineIdSet.has(ln.id)) {
      appendUncoveredLineBadge(body);
    }
    if (ln.id && duplicateTimestampLineIdSet.has(ln.id)) {
      appendDuplicateTimestampBadge(body);
    }
    row.appendChild(body);
    return row;
  };

  const optionLineUsageByGroup = new WeakMap();
  const optionCandidateLineIdsByOption = new WeakMap();
  const branchColumnLineIdsByOption = new WeakMap();
  const branchDisplayModelByGroup = new WeakMap();

  const optionListForGroup = (grp) => {
    const opts = grp && grp.options ? grp.options : [];
    return Array.isArray(opts) ? opts : (opts ? [opts] : []);
  };

  const optionPathLineIds = (opt) => {
    const out = [];
    for (const outcome of sameSceneOptionOutcomes(opt, conv, outcomesByOptionId)) {
      for (const lineId of normalizeLineOrderIdList(outcome.pathLineIds)) {
        if (lineIdSet.has(lineId) && !out.includes(lineId)) out.push(lineId);
      }
    }
    return out;
  };

  const optionRiskMappedLineIds = (grp, opt) => {
    const risk = grp && grp.optionBranchRisk && typeof grp.optionBranchRisk === "object"
      ? grp.optionBranchRisk
      : null;
    const optionId = String(opt && opt.id || "");
    if (!risk || !optionId) return [];
    if (risk.code !== "inferredFollowingLines" || risk.candidateMapping !== "trunkClipOptionIndex") {
      return [];
    }
    const byOption = risk.candidateLineIdsByOption && typeof risk.candidateLineIdsByOption === "object"
      ? risk.candidateLineIdsByOption
      : null;
    const mapped = byOption && byOption[optionId];
    if (Array.isArray(mapped)) return lineOrderUniqueList(mapped);
    return mapped ? [String(mapped)] : [];
  };

  const optionCandidateLineIds = (opt, grp = null) => {
    if (optionCandidateLineIdsByOption.has(opt)) return optionCandidateLineIdsByOption.get(opt);
    const out = [];
    const push = (lineId) => {
      if (lineId && lineIdSet.has(lineId) && !out.includes(lineId)) out.push(lineId);
    };
    for (const lineId of normalizeLineOrderIdList(opt && opt.branchLines)) push(lineId);
    for (const lineId of optionRiskMappedLineIds(grp, opt)) push(lineId);
    for (const lineId of optionPathLineIds(opt)) push(lineId);
    optionCandidateLineIdsByOption.set(opt, out);
    return out;
  };

  const optionLineUsageForGroup = (grp) => {
    if (optionLineUsageByGroup.has(grp)) return optionLineUsageByGroup.get(grp);
    const usage = new Map();
    for (const opt of optionListForGroup(grp)) {
      for (const lineId of optionCandidateLineIds(opt, grp)) {
        usage.set(lineId, (usage.get(lineId) || 0) + 1);
      }
    }
    optionLineUsageByGroup.set(grp, usage);
    return usage;
  };

  const branchColumnLineIdsForOption = (grp, opt) => {
    if (branchColumnLineIdsByOption.has(opt)) return branchColumnLineIdsByOption.get(opt);
    const out = [];
    const push = (lineId) => {
      if (lineId && lineIdSet.has(lineId) && !out.includes(lineId)) out.push(lineId);
    };
    const usage = optionLineUsageForGroup(grp);
    for (const lineId of optionCandidateLineIds(opt, grp)) {
      if ((usage.get(lineId) || 0) === 1) push(lineId);
    }
    branchColumnLineIdsByOption.set(opt, out);
    return out;
  };

  const sharedSuffixLineIdsFromLists = (lists) => {
    if (!lists.length) return [];
    if (lists.some((list) => !list.length)) return [];
    const suffix = [];
    let offset = 1;
    while (true) {
      const candidate = lists[0][lists[0].length - offset];
      if (!candidate) break;
      if (!lists.every((list) => list[list.length - offset] === candidate)) break;
      suffix.unshift(candidate);
      offset += 1;
    }
    return suffix;
  };

  const sharedRouteSuffixLineIds = (opts, grp = null) => {
    if (!opts.length) return [];
    return sharedSuffixLineIdsFromLists(opts.map((opt) => optionCandidateLineIds(opt, grp)));
  };

  const collectBranchColumnLineIds = (grp, opt, seenGroups = new Set()) => {
    const out = [];
    const push = (lineId) => {
      if (lineId && lineIdSet.has(lineId) && !out.includes(lineId)) out.push(lineId);
    };
    if (!grp || seenGroups.has(grp)) return out;
    seenGroups.add(grp);
    for (const lineId of optionCandidateLineIds(opt, grp)) {
      push(lineId);
      for (const childGroup of groupsByLineId.get(lineId) || []) {
        if (!childGroup || childGroup === grp || seenGroups.has(childGroup)) continue;
        if (isLineOrderSharedContinuationGroup(grp, childGroup, outcomesByOptionId, conv.key)) continue;
        for (const childOpt of optionListForGroup(childGroup)) {
          for (const childLineId of collectBranchColumnLineIds(childGroup, childOpt, seenGroups)) {
            push(childLineId);
          }
        }
      }
    }
    seenGroups.delete(grp);
    return out;
  };

  const collectSingleOptionClosureLineIds = (grp, seenGroups = new Set()) => {
    const out = [];
    const push = (lineId) => {
      if (lineId && lineIdSet.has(lineId) && !out.includes(lineId)) out.push(lineId);
    };
    if (!grp || seenGroups.has(grp)) return out;
    const opts = optionListForGroup(grp);
    if (opts.length !== 1) return out;
    seenGroups.add(grp);
    for (const lineId of optionCandidateLineIds(opts[0], grp)) {
      push(lineId);
      for (const childGroup of groupsByLineId.get(lineId) || []) {
        if (!childGroup || childGroup === grp || seenGroups.has(childGroup)) continue;
        if (optionListForGroup(childGroup).length !== 1) continue;
        for (const childLineId of collectSingleOptionClosureLineIds(childGroup, seenGroups)) {
          push(childLineId);
        }
      }
    }
    seenGroups.delete(grp);
    return out;
  };

  const branchDisplayModelForGroup = (grp) => {
    if (branchDisplayModelByGroup.has(grp)) return branchDisplayModelByGroup.get(grp);
    const opts = optionListForGroup(grp);
    if (optionGroupHasTimelineRouteBranches(grp)) {
      const commonLineIds = sharedRouteSuffixLineIds(opts, grp);
      const commonCount = commonLineIds.length;
      const optionLineIds = new WeakMap();
      for (const opt of opts) {
        const routeLineIds = optionCandidateLineIds(opt, grp);
        optionLineIds.set(opt, commonCount ? routeLineIds.slice(0, routeLineIds.length - commonCount) : routeLineIds);
      }
      const model = { optionLineIds, commonLineIds };
      branchDisplayModelByGroup.set(grp, model);
      return model;
    }
    const usage = optionLineUsageForGroup(grp);
    const commonDirect = new Set(
      [...usage.entries()]
        .filter(([, count]) => count > 1)
        .map(([lineId]) => lineId)
    );
    const recursiveByOption = new WeakMap();
    const recursiveUsage = new Map();
    for (const opt of opts) {
      const recursive = [];
      const push = (lineId) => {
        if (lineId && lineIdSet.has(lineId) && !recursive.includes(lineId)) recursive.push(lineId);
      };
      for (const lineId of optionCandidateLineIds(opt, grp)) {
        if (commonDirect.has(lineId)) continue;
        for (const childGroup of groupsByLineId.get(lineId) || []) {
          if (!childGroup || childGroup === grp) continue;
          if (isLineOrderSharedContinuationGroup(grp, childGroup, outcomesByOptionId, conv.key)) continue;
          for (const childOpt of optionListForGroup(childGroup)) {
            for (const childLineId of collectBranchColumnLineIds(childGroup, childOpt)) {
              push(childLineId);
            }
          }
        }
      }
      recursiveByOption.set(opt, recursive);
      for (const lineId of recursive) {
        recursiveUsage.set(lineId, (recursiveUsage.get(lineId) || 0) + 1);
      }
    }
    const commonRecursive = new Set(
      [...recursiveUsage.entries()]
        .filter(([, count]) => count > 1)
        .map(([lineId]) => lineId)
    );
    const optionLineIds = new WeakMap();
    const commonLineIds = [];
    const pushCommon = (lineId) => {
      if (lineId && lineIdSet.has(lineId) && !commonLineIds.includes(lineId)) commonLineIds.push(lineId);
    };
    for (const opt of opts) {
      const direct = [];
      for (const lineId of optionCandidateLineIds(opt, grp)) {
        if (commonDirect.has(lineId)) {
          pushCommon(lineId);
        } else if ((usage.get(lineId) || 0) === 1 && !direct.includes(lineId)) {
          direct.push(lineId);
        }
      }
      for (const lineId of recursiveByOption.get(opt) || []) {
        if (commonRecursive.has(lineId)) pushCommon(lineId);
      }
      optionLineIds.set(opt, direct);
    }
    if (
      commonLineIds.length
      && !optionGroupHasBranchContent(grp)
      && !opts.some((opt) => (optionLineIds.get(opt) || []).length)
    ) {
      const model = { optionLineIds, commonLineIds: [] };
      branchDisplayModelByGroup.set(grp, model);
      return model;
    }
    const model = { optionLineIds, commonLineIds };
    branchDisplayModelByGroup.set(grp, model);
    return model;
  };

  const renderBranchPathLines = (lineIds, ownerGroup, renderCtx) => {
    const lines = document.createElement("div");
    lines.className = "branch-lines";
    const suppressedLineIds = renderCtx && renderCtx.suppressedLineIds
      ? renderCtx.suppressedLineIds
      : new Set();
    for (const lid of lineIds) {
      if (suppressedLineIds.has(lid)) continue;
      if (renderedDlgLineIds.has(lid)) continue;
      const line = dlgLineById.get(lid);
      if (!line) continue;
      if (isBackLoopAnchorLineForGroup(ownerGroup, lid)) continue;
      renderedDlgLineIds.add(lid);
      lines.appendChild(renderDialogFlowLine(line, { branchColumn: true }));
    }
    return lines.childNodes.length ? lines : null;
  };

  const renderSingleOptionPathLines = (lineIds, ownerGroup, renderCtx) => {
    const lines = document.createDocumentFragment();
    const suppressedLineIds = renderCtx && renderCtx.suppressedLineIds
      ? renderCtx.suppressedLineIds
      : new Set();
    const stopBeforeLineIds = renderCtx && renderCtx.stopBeforeLineIds
      ? renderCtx.stopBeforeLineIds
      : new Set();
    for (const lid of lineIds) {
      if (suppressedLineIds.has(lid)) continue;
      if (stopBeforeLineIds.has(lid)) continue;
      if (renderedDlgLineIds.has(lid)) continue;
      if (isBackLoopAnchorLineForGroup(ownerGroup, lid)) continue;
      const line = dlgLineById.get(lid);
      if (!line || isResearchHintLine(line)) continue;
      renderedDlgLineIds.add(lid);
      lines.appendChild(
        renderCtx && renderCtx.branchColumn
          ? renderDialogFlowLine(line, { branchColumn: true })
          : renderDialogFlowLine(line)
      );
    }
    return lines.childNodes.length ? lines : null;
  };

  const renderCommonContinuationLines = (lineIds, ownerGroup, renderCtx) => {
    if (renderCtx && renderCtx.branchColumn) {
      return renderBranchPathLines(lineIds, ownerGroup, renderCtx);
    }
    const lines = document.createDocumentFragment();
    const suppressedLineIds = renderCtx && renderCtx.suppressedLineIds
      ? renderCtx.suppressedLineIds
      : new Set();
    for (const lid of lineIds) {
      if (suppressedLineIds.has(lid)) continue;
      if (renderedDlgLineIds.has(lid)) continue;
      if (isBackLoopAnchorLineForGroup(ownerGroup, lid)) continue;
      const line = dlgLineById.get(lid);
      if (!line || isResearchHintLine(line)) continue;
      renderedDlgLineIds.add(lid);
      lines.appendChild(renderDialogFlowLine(line));
    }
    return lines.childNodes.length ? lines : null;
  };

  const renderOptGroup = (grp, renderCtx = {}) => {
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

    const opts = optionListForGroup(grp);
    const multi = opts.length >= 2;
    const branchModel = branchDisplayModelForGroup(grp);
    const showBranchContent = optionGroupHasBranchContent(grp)
      || opts.some((opt) => (branchModel.optionLineIds.get(opt) || []).length)
      || branchModel.commonLineIds.length;

    if (!multi) {
      const singleOutcomeTargets = findOutcomeMenuTargetGroups(grp, conv, outcomesByOptionId);
      const singleRenderedBranchLineIds = new Set();
      const singlePathLineFragments = [];
      for (const opt of opts) {
        const o = document.createElement("div");
        o.className = "option";
        const icon = opt.icon && opt.icon !== "Default"
          ? ` <span class="opt-icon">[${escapeHtml(opt.icon)}]</span>` : "";
        o.innerHTML = `- ${highlight(opt.text || "(empty)", STATE.filters.q)}${icon}`;
        const loopLineIds = optionLoopLineIds(opt, grp, conv, outcomesByOptionId, lineOrderIndexById);
        const showLoopTags = renderCtx.branchColumn || !optionCandidateLineIds(opt, grp).length;
        const targetChips = renderOptionTargetChips(
          opt,
          conv,
          outcomesByOptionId,
          { ...chipOptions, hideSelfMenu: showLoopTags && loopLineIds.length > 0 }
        );
        if (targetChips) o.appendChild(targetChips);
        const jumpTags = renderOptionJumpTags(opt, grp, conv, outcomesByOptionId);
        if (jumpTags) o.appendChild(jumpTags);
        const riskTags = renderOptionRiskTags(opt);
        if (riskTags) o.appendChild(riskTags);
        appendOptionId(o, opt);
        appendDebugTrace(o, opt._debug, "option");
        g.appendChild(o);
        if (renderCtx.branchColumn) {
          // Single-option prompts should only absorb lines that the trunk has
          // already hidden as branch-specific content.
          const branchLineIds = branchColumnLineIdsForOption(grp, opt)
            .filter((lineId) => dlgBranchSkipIds.has(lineId))
            .filter((lineId) => !(renderCtx.stopBeforeLineIds && renderCtx.stopBeforeLineIds.has(lineId)));
          for (const lineId of branchLineIds) singleRenderedBranchLineIds.add(lineId);
          const pathLines = renderSingleOptionPathLines(branchLineIds, grp, renderCtx);
          if (pathLines) singlePathLineFragments.push(pathLines);
        }
        if (showLoopTags) {
          const loopTags = renderOptionLoopTagsForLineIds(conv, loopLineIds);
          if (loopTags) g.appendChild(loopTags);
        }
      }
      for (const pathLines of singlePathLineFragments) {
        frag.appendChild(pathLines);
      }
      const singleBranchFollowups = branchAnchoredGroupsForLineIds(singleRenderedBranchLineIds, grp)
        .filter((target) => isBranchAnchoredPullEligible(target, singleRenderedBranchLineIds));
      const singleBranchFollowupSet = new Set(singleBranchFollowups);
      const singleFollowups = uniqueOptionGroups(
        singleOutcomeTargets.filter(isPullEligible).concat(singleBranchFollowups)
      );
      for (const followup of singleFollowups) continuationOptGroups.add(followup);
      for (const followup of singleFollowups) {
        const followupCtx = singleBranchFollowupSet.has(followup)
          ? { ...renderCtx, branchColumn: true }
          : renderCtx;
        frag.appendChild(renderOptGroup(followup, followupCtx));
      }
      return frag;
    }

    g.classList.add("opt-group-branches");
    const renderedBranchLineIds = new Set(branchModel.commonLineIds);
    for (const opt of opts) {
      for (const lineId of branchModel.optionLineIds.get(opt) || []) {
        renderedBranchLineIds.add(lineId);
      }
    }
    const isContinuationPullEligible = (target) => {
      if (!target || continuationOptGroups.has(target) || renderedOptGroups.has(target)) return false;
      if (isPullEligible(target)) return true;
      const targetAnchor = String(target.after || "");
      return anchoredOptGroups.has(target)
        && renderedBranchLineIds.has(targetAnchor)
        && !isBackLoopAnchorLineForGroup(grp, targetAnchor);
    };
    const continuationGroups = findLineOrderContinuationGroups(grp, optionLayoutCtx)
      .filter(isContinuationPullEligible);
    const continuationGroupSet = new Set(continuationGroups);
    const outcomeMenuTargets = findOutcomeMenuTargetGroups(grp, conv, outcomesByOptionId)
      .filter((target) => !continuationGroupSet.has(target) && isPullEligible(target));
    const branchAnchoredFollowupGroups = branchAnchoredGroupsForLineIds(renderedBranchLineIds, grp)
      .filter((target) => !continuationGroupSet.has(target))
      .filter((target) => isBranchAnchoredPullEligible(target, renderedBranchLineIds));
    const branchAnchoredFollowupSet = new Set(branchAnchoredFollowupGroups);
    const branchFollowupMergeLineIds = branchAnchoredFollowupGroups.length >= 2
      ? sharedSuffixLineIdsFromLists(
          branchAnchoredFollowupGroups.map((group) => collectSingleOptionClosureLineIds(group))
        )
      : [];
    const branchFollowupStopLineIds = branchFollowupMergeLineIds.length
      ? new Set([branchFollowupMergeLineIds[0]])
      : new Set();
    const allFollowupGroups = uniqueOptionGroups(
      continuationGroups.concat(outcomeMenuTargets)
        .filter((group) => !branchAnchoredFollowupSet.has(group))
    );
    for (const group of allFollowupGroups) continuationOptGroups.add(group);
    for (const group of branchAnchoredFollowupGroups) continuationOptGroups.add(group);
    const commonLineIdSet = new Set(branchModel.commonLineIds);
    const isCommonTailFollowup = (group) => {
      if (!commonLineIdSet.size) return false;
      const groupLineIds = [];
      const push = (lineId) => {
        if (lineId && !groupLineIds.includes(lineId)) groupLineIds.push(lineId);
      };
      for (const opt of optionListForGroup(group)) {
        for (const lineId of collectBranchColumnLineIds(group, opt)) push(lineId);
      }
      return groupLineIds.length > 0 && groupLineIds.every((lineId) => commonLineIdSet.has(lineId));
    };
    const followupGroupsToRender = [];
    const absorbedFollowupGroups = new Set();
    for (const group of allFollowupGroups) {
      if (isCommonTailFollowup(group)) {
        absorbedFollowupGroups.add(group);
      } else {
        followupGroupsToRender.push(group);
      }
    }

    const inheritedSuppressedLineIds = renderCtx.suppressedLineIds || new Set();
    const branchSuppressedLineIds = new Set(inheritedSuppressedLineIds);
    for (const lineId of branchModel.commonLineIds) branchSuppressedLineIds.add(lineId);
    const branchRenderCtx = {
      ...renderCtx,
      branchColumn: true,
      suppressedLineIds: branchSuppressedLineIds,
    };

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
      const loopLineIds = optionLoopLineIds(opt, grp, conv, outcomesByOptionId, lineOrderIndexById);
      const targetChips = renderOptionTargetChips(
        opt,
        conv,
        outcomesByOptionId,
        { ...chipOptions, hideSelfMenu: loopLineIds.length > 0 }
      );
      if (targetChips) head.appendChild(targetChips);
      const jumpTags = renderOptionJumpTags(opt, grp, conv, outcomesByOptionId);
      if (jumpTags) head.appendChild(jumpTags);
      const riskTags = renderOptionRiskTags(opt);
      if (riskTags) head.appendChild(riskTags);
      appendOptionId(head, opt);
      col.appendChild(head);
      const branchLineIds = branchModel.optionLineIds.get(opt) || [];
      if (showBranchContent && branchLineIds.length) {
        const lines = renderBranchPathLines(branchLineIds, grp, branchRenderCtx);
        if (lines) col.appendChild(lines);
      }
      const branchLineIdSet = new Set(branchLineIds);
      const optionFollowups = branchAnchoredGroupsForLineIds(branchLineIdSet, grp)
        .filter((target) => branchAnchoredFollowupSet.has(target));
      for (const followup of optionFollowups) {
        col.appendChild(renderOptGroup(followup, {
          ...branchRenderCtx,
          stopBeforeLineIds: branchFollowupStopLineIds,
        }));
      }
      const loopTags = renderOptionLoopTagsForLineIds(conv, loopLineIds);
      if (loopTags) col.appendChild(loopTags);
      appendDebugTrace(col, opt._debug, "option");
      cols.appendChild(col);
    }
    g.appendChild(cols);

    let commonLinesAfterGroup = null;
    if (branchModel.commonLineIds.length) {
      commonLinesAfterGroup = renderCommonContinuationLines(
        branchModel.commonLineIds,
        grp,
        renderCtx
      );
      if (commonLinesAfterGroup && commonLinesAfterGroup.nodeType === 1) {
        commonLinesAfterGroup.classList.add("branch-common-lines");
      }
    }

    for (const group of absorbedFollowupGroups) renderedOptGroups.add(group);
    if (commonLinesAfterGroup) frag.appendChild(commonLinesAfterGroup);
    for (const group of followupGroupsToRender) {
      const followupCtx = branchAnchoredFollowupSet.has(group)
        ? { ...renderCtx, branchColumn: true, stopBeforeLineIds: branchFollowupStopLineIds }
        : {};
      frag.appendChild(renderOptGroup(group, followupCtx));
    }
    if (branchFollowupMergeLineIds.length) {
      const mergeLineId = branchFollowupMergeLineIds[0];
      const mergeLine = dlgLineById.get(mergeLineId);
      if (mergeLine && !renderedDlgLineIds.has(mergeLineId)) {
        renderedDlgLineIds.add(mergeLineId);
        frag.appendChild(renderDialogFlowLine(mergeLine));
      }
      for (const group of attachedGroupsForLine(mergeLineId)) {
        frag.appendChild(renderOptGroup(group));
      }
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
      const opts = optionListForGroup(grp);
      if (opts.length < 2) continue;
      const branchModel = branchDisplayModelForGroup(grp);
      const groupHasColumnContent = optionGroupHasBranchContent(grp)
        || opts.some((opt) => (branchModel.optionLineIds.get(opt) || []).length)
        || branchModel.commonLineIds.length;
      if (!groupHasColumnContent) continue;
      const afterIdx = lineRenderIdx(grp.after || "") ?? -1;
      for (const opt of opts) {
        for (const lid of collectBranchColumnLineIds(grp, opt)) {
          const lidIdx = lineRenderIdx(lid) ?? -1;
          // A branchLine that points at *another* group's anchor is a
          // back-loop indicator (the option returns the player to that menu's
          // prompt). Skipping the anchor line from the trunk would prevent
          // the anchored group from ever rendering at its real position.
          const anchorsOtherGroup = (groupsByLineId.get(lid) || [])
            .some((other) => other && other !== grp);
          const isBackLoopAnchor = anchorsOtherGroup && lidIdx <= afterIdx;
          if (isBackLoopAnchor) continue;
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
    if (conv.kind === "dlg" && ln.id && renderedDlgLineIds.has(ln.id)) {
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
      setLineAnchor(row, conv.key, ln.id);
      if (conv.kind === "dlg" && ln.id) renderedDlgLineIds.add(ln.id);

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
      frag.appendChild(renderSnsBranchGroup(snsBranchGroup, conv.key));
    }

    if (branchOnlyNode) {
      continue;
    }

    // Inline option groups attached to this line (heuristic: option group
    // number matches the line's raw index). The option widget is indented
    // under its anchor line, but recovered dialogue rows emitted by nested
    // single-option follow-ups are regular rows and must escape that wrapper.
    if (inlineGroups && inlineGroups.length) {
      let block = null;
      const ensureBlock = () => {
        if (!block) {
          block = document.createElement("div");
          block.className = "opt-block opt-block-inline";
        }
        return block;
      };
      const flushBlock = () => {
        if (block && block.childNodes.length) frag.appendChild(block);
        block = null;
      };
      for (const grp of inlineGroups) {
        const rendered = renderOptGroup(grp);
        while (rendered.firstChild) {
          const child = rendered.firstChild;
          if (child.nodeType === 1 && child.classList.contains("line")) {
            flushBlock();
            frag.appendChild(child);
          } else {
            ensureBlock().appendChild(child);
          }
        }
      }
      flushBlock();
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
  const sceneEdges = missionTimelineArray(sceneGraph && sceneGraph.edges)
    .filter((edge) => edge && String(edge.from || "").trim() && String(edge.to || "").trim());

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
  const summary = document.createElement("summary");
  summary.textContent = `${uiText("missionTimelineSceneOrder")} (${confirmed.length}${unconfirmed.length ? ` + ${unconfirmed.length} ${uiText("missionTimelineOrderUnknown")}` : ""})`;
  details.appendChild(summary);

  const sceneOrderMap = buildMissionTimelineSceneOrderMap(sceneGraph);
  const graph = renderMissionTimelineSceneEdgeGraph(sceneEdges, flowKeyMap, currentKey, { sceneOrderMap });
  if (graph) {
    details.appendChild(graph);
  }

  if (!graph || confirmed.length <= 30) {
    const row = document.createElement("div");
    row.className = "mission-timeline-edge" + (graph ? " mission-timeline-order-reference" : "");
    if (graph) {
      const label = document.createElement("span");
      label.className = "mission-timeline-unknown-label";
      label.textContent = uiText("missionTimelineOrderReference");
      row.appendChild(label);
    }
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
  } else if (confirmed.length) {
    const more = document.createElement("div");
    more.className = "mission-timeline-more";
    more.textContent = uiText("missionTimelineOrderReferenceHidden").replace("{count}", String(confirmed.length));
    details.appendChild(more);
  }

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

function formatTimelineSeconds(value) {
  if (typeof value !== "number" || !isFinite(value)) return "";
  const seconds = Math.max(0, value);
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds - minutes * 60;
  return `${minutes}:${remaining.toFixed(1).padStart(4, "0")}`;
}

function exportedAssetHref(relPath) {
  return exportFullHref(relPath, STATE.inlineImageSourceRoots, STATE.inlineImageExportRoot);
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
  const stem = String(asset && asset.stem ? asset.stem : "").toLowerCase();
  return (
    normalized.includes("emoji")
    || normalized.includes("emoiji")
    || stem.includes("emoji")
    || stem.includes("emoiji")
    || rel.includes("emoji")
    || rel.includes("emoiji")
  );
}

function isInlineSnsMediaImageId(rawId, normalized, asset = null) {
  if (isInlineEmojiImageId(normalized || rawId, asset)) return false;

  const raw = cleanInlineImageIdValue(rawId).replace(/\\/g, "/").toLowerCase();
  const stem = String(asset && asset.stem ? asset.stem : normalizeInlineImageId(normalized || rawId)).toLowerCase();
  const rel = String(asset && asset.rel ? asset.rel : "").toLowerCase();
  return (
    raw.startsWith("sns_")
    || raw.startsWith("cg_image_")
    || stem.startsWith("sns_")
    || stem.startsWith("cg_image_")
    || stem.startsWith("deco_sns_tweet_decorate_")
    || stem.startsWith("bg_sns_tweet_decorate_")
    || rel.includes("/sns_")
    || rel.includes("/cg_image_")
    || rel.includes("/deco_sns_tweet_decorate_")
    || rel.includes("/bg_sns_tweet_decorate_")
  );
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
  const isEmoji = asset ? isInlineEmojiImageId(normalized, asset) : false;

  if (asset) {
    classes.push("has-preview");
    if (isEmoji) classes.push("is-emoji");
    if (isInlineSnsMediaImageId(rawId, normalized, asset)) classes.push("is-sns-image");
    if (isInlineContentImageId(rawId, normalized, asset)) classes.push("is-content-image");
    if (!isEmoji) {
      attrs.push(`tabindex="0"`);
      attrs.push(`title="${escapeHtml(asset.name)}"`);
    }
    attrs.push(`data-inline-image-src="${escapeHtml(src)}"`);
    attrs.push(`data-inline-image-name="${escapeHtml(asset.name)}"`);
  }

  const label = asset ? "" : highlightTextFragment(rawTag || `<image="${rawId}">`, q);
  const thumb = asset
    ? `<img class="inline-image-thumb" src="${escapeHtml(src)}" alt="${escapeHtml(rawId)}" loading="lazy">`
    : "";
  const preview = asset && !isEmoji
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
  storageSet(GENDER_VARIANT_STORAGE_KEY, normalizeGenderVariant(value) || DEFAULT_GENDER_VARIANT);
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
  const next = normalizeGenderVariant(value) || DEFAULT_GENDER_VARIANT;
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

  const fallback = normalizeGenderVariant(DEFAULT_GENDER_VARIANT) || normalizeGenderVariant(preferred);
  if (fallback) {
    STATE.genderVariant = fallback;
    return fallback;
  }

  STATE.genderVariant = "f";
  return "f";
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
  const active = resolveGenderVariant(node.dataset.genderInitial || node.dataset.genderActive || DEFAULT_GENDER_VARIANT);
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
  const active = resolveGenderVariant(node && (node.dataset.genderInitial || node.dataset.genderActive || DEFAULT_GENDER_VARIANT));
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
