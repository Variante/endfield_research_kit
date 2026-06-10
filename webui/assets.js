(() => {
  const ASSET_GROUP_ROW_H = 28;
  const ASSET_ITEM_ROW_H = 70;
  const ASSET_OVERSCAN_PX = 240;
  const FILTER_PANEL_STORAGE_KEY = "asset_browser_filters_collapsed";
  const UI_LOCALE_STORAGE_KEY = "webui_ui_locale";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const SHARED_ASSET_NAME_PREFIXES = new Set(["S", "T", "P", "M"]);
  const KNOWN_TEXTURE_SUFFIXES = new Set([
    "A", "AO", "B", "BC", "C", "D", "DA", "DIFF", "DIFFUSE", "DISP",
    "E", "EM", "EMI", "EMISSIVE", "G", "GL", "GLOSS", "H", "HM", "ID",
    "M", "MA", "MASK", "MC", "MSK", "N", "NH", "NM", "NORMAL", "NRM",
    "O", "OP", "ORM", "P", "PACK", "R", "RM", "ROUGH", "ROUGHNESS",
    "S", "SM", "SPEC", "ST", "T",
  ]);
  const {
    $,
    $$,
    applyTemplate,
    escapeHtml,
    exportFullHref,
    normalizeUiLocale,
    splitPathIdExportStem,
    relRequiresPathIdExportName,
    storageGet,
    storageSet,
  } = window.WebUI;
  const ASSET_UI_TEXTS = {
    zh: {
      showFilters: "\u663e\u793a\u7b5b\u9009",
      hideFilters: "\u9690\u85cf\u7b5b\u9009",
      title: "\u5bfc\u51fa\u8d44\u6e90\u6d4f\u89c8\u5668",
      countLabel: "\u9879\u8d44\u6e90",
      searchPlaceholder: "\u641c\u7d22\u8def\u5f84 / \u540d\u79f0 / \u6587\u4ef6\u5939 / \u5206\u7ec4",
      type: "\u7c7b\u578b",
      source: "\u6765\u6e90",
      allSources: "\u5168\u90e8\u6765\u6e90",
      sort: "\u6392\u5e8f",
      sortPath: "\u8def\u5f84 (A-Z)",
      sortSizeDesc: "\u6587\u4ef6\u5927\u5c0f\u4ece\u5927\u5230\u5c0f",
      sortSizeAsc: "\u6587\u4ef6\u5927\u5c0f\u4ece\u5c0f\u5230\u5927",
      sortName: "\u6587\u4ef6\u540d (A-Z)",
      reset: "\u91cd\u7f6e\u7b5b\u9009",
      listUnit: "\u6761\u76ee",
      empty: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u5f20\u56fe\u7247\u6216\u6a21\u578b\u6587\u4ef6\u3002",
      openRawFile: "\u6253\u5f00\u539f\u59cb\u6587\u4ef6",
      downloadCurrentFile: "\u4e0b\u8f7d\u5f53\u524d\u6587\u4ef6",
      downloadBundle: "\u4e00\u952e\u4e0b\u8f7d\u6574\u5305",
      copyRelativePath: "\u590d\u5236\u76f8\u5bf9\u8def\u5f84",
      copiedPath: "\u5df2\u590d\u5236\u8def\u5f84",
      copyFailed: "\u590d\u5236\u5931\u8d25",
      preview: "\u9884\u89c8",
      previewPlaceholder: "\u9884\u89c8\u4f1a\u663e\u793a\u5728\u8fd9\u91cc\u3002",
      inspector: "\u8d44\u6e90\u68c0\u67e5\u5668",
      relatedFiles: "\u76f8\u5173\u6587\u4ef6",
      lodVariants: "\u53d8\u4f53",
      linkedMaterials: "\u5173\u8054\u6750\u8d28",
      linkedTextures: "\u5173\u8054\u8d34\u56fe",
      referencedBy: "\u5f15\u7528\u6b64\u8d44\u6e90\u7684\u6587\u4ef6",
      modelStats: "\u6a21\u578b\u7edf\u8ba1",
      images: "\u56fe\u7247",
      models: "\u6a21\u578b",
      rootFolder: "(\u6839\u76ee\u5f55)",
      none: "(\u65e0)",
      unresolved: "\u672a\u89e3\u6790",
      variantsCount: "{count} \u4e2a\u53d8\u4f53",
      copiesCount: "{count} \u4e2a\u526f\u672c",
      assetIndexError: "\u65e0\u6cd5\u52a0\u8f7d\u8d44\u6e90\u7d22\u5f15: {error}",
      relatedMeta: "{kind} / {size}",
      factKind: "\u7c7b\u578b",
      factSource: "\u6765\u6e90",
      factFolder: "\u5206\u7ec4",
      factSize: "\u5927\u5c0f",
      factCopies: "\u526f\u672c",
      factLodVariants: "\u53d8\u4f53",
      factSelectedRawFile: "\u5f53\u524d\u539f\u59cb\u6587\u4ef6",
      factLodSet: "\u7ec4\u5185\u6587\u4ef6",
      factRelativePath: "\u76f8\u5bf9\u8def\u5f84",
      factLod: "LOD",
      factFamily: "\u7cfb\u5217",
      factPreviewProxy: "\u5ba1\u9605\u4ee3\u7406",
      materialJson: "{name}.json",
      relationTextureResolved: "{slots} / {name}",
      relationTextureUnresolved: "{slots} / {name} / \u672a\u89e3\u6790",
      relationMaterial: "\u6750\u8d28 / {slots}",
      relationModel: "\u6a21\u578b",
      loadingImagePreview: "\u6b63\u5728\u52a0\u8f7d\u56fe\u7247\u9884\u89c8...",
      imagePreviewUnavailable: "\u65e0\u6cd5\u9884\u89c8\u8fd9\u5f20\u56fe\u7247\u3002",
      rawLinkAvailable: "\u4e0a\u65b9\u4ecd\u53ef\u6253\u5f00\u539f\u59cb\u6587\u4ef6\u3002",
      imagePixels: "{width} x {height} \u50cf\u7d20",
      loadingObjPreview: "\u6b63\u5728\u52a0\u8f7d OBJ \u9884\u89c8...",
      loadingFbxSummary: "\u6b63\u5728\u8bfb\u53d6 FBX \u7ed3\u6784...",
      noModelFile: "\u6ca1\u6709\u53ef\u7528\u7684\u6a21\u578b\u6587\u4ef6\u3002",
      previewingModel: "\u6b63\u5728\u9884\u89c8 {name}\u3002\u62d6\u52a8\u53ef\u65cb\u8f6c\uff0c\u6eda\u8f6e\u53ef\u7f29\u653e\u3002",
      previewingModelViaObj: "\u6b63\u5728\u901a\u8fc7\u914d\u5957 OBJ \u5ba1\u9605 {name}\u3002\u62d6\u52a8\u53ef\u65cb\u8f6c\uff0c\u6eda\u8f6e\u53ef\u7f29\u653e\u3002",
      objPreviewUnavailable: "\u65e0\u6cd5\u9884\u89c8\u6b64 OBJ \u6587\u4ef6\u3002",
      fbxSummaryLoaded: "FBX \u6682\u65f6\u6ca1\u6709\u9875\u5185\u7f51\u683c\u9884\u89c8\uff0c\u5df2\u5c55\u793a\u6587\u4ef6\u7ed3\u6784\u6458\u8981\u3002",
      fbxSummaryUnavailable: "\u65e0\u6cd5\u8bfb\u53d6\u8fd9\u4e2a FBX \u6587\u4ef6\u7684\u7ed3\u6784\u6458\u8981\u3002",
      fbxSummaryPlaceholder: "FBX \u7ed3\u6784\u6458\u8981\u4f1a\u663e\u793a\u5728\u4e0b\u65b9\u7684\u7edf\u8ba1\u9762\u677f\u91cc\u3002",
      selectedLod: "\u5f53\u524d LOD",
      sampledPoints: "\u91c7\u6837\u70b9",
      vertices: "\u9876\u70b9",
      faces: "\u9762",
      objectsGroups: "\u5bf9\u8c61 / \u7ec4",
      fbxFormat: "FBX \u683c\u5f0f",
      fbxVersion: "FBX \u7248\u672c",
      fbxNodes: "\u8282\u70b9",
      fbxModels: "\u6a21\u578b\u8282\u70b9",
      fbxGeometries: "\u7f51\u683c\u8282\u70b9",
      fbxMaterials: "\u6750\u8d28\u8282\u70b9",
      fbxTextures: "\u8d34\u56fe\u8282\u70b9",
      fbxAnimations: "\u52a8\u753b\u6811",
      fbxSampleNames: "\u793a\u4f8b\u540d\u79f0",
    },
    en: {
      showFilters: "Show filters",
      hideFilters: "Hide filters",
      title: "Exported Asset Browser",
      countLabel: "assets",
      searchPlaceholder: "Search path / name / folder / group",
      type: "Type",
      source: "Source",
      allSources: "All sources",
      sort: "Sort",
      sortPath: "Path (A-Z)",
      sortSizeDesc: "File size (high to low)",
      sortSizeAsc: "File size (low to high)",
      sortName: "File name (A-Z)",
      reset: "Reset filters",
      listUnit: "items",
      empty: "Choose an image or model file from the left.",
      openRawFile: "Open raw file",
      downloadCurrentFile: "Download current file",
      downloadBundle: "Download bundle",
      copyRelativePath: "Copy relative path",
      copiedPath: "Copied path",
      copyFailed: "Copy failed",
      preview: "Preview",
      previewPlaceholder: "Preview will appear here.",
      inspector: "Inspector",
      relatedFiles: "Related files",
      lodVariants: "Variants",
      linkedMaterials: "Linked materials",
      linkedTextures: "Linked textures",
      referencedBy: "Referenced by",
      modelStats: "Model stats",
      images: "Images",
      models: "Models",
      rootFolder: "(root)",
      none: "(none)",
      unresolved: "unresolved",
      variantsCount: "{count} variants",
      copiesCount: "{count} copies",
      assetIndexError: "Unable to load asset index: {error}",
      relatedMeta: "{kind} / {size}",
      factKind: "Kind",
      factSource: "Source",
      factFolder: "Group",
      factSize: "Size",
      factCopies: "Copies",
      factLodVariants: "Variants",
      factSelectedRawFile: "Selected raw file",
      factLodSet: "Files in group",
      factRelativePath: "Relative path",
      factLod: "LOD",
      factFamily: "Family",
      factPreviewProxy: "Review proxy",
      materialJson: "{name}.json",
      relationTextureResolved: "{slots} / {name}",
      relationTextureUnresolved: "{slots} / {name} / unresolved",
      relationMaterial: "Material / {slots}",
      relationModel: "Model",
      loadingImagePreview: "Loading image preview...",
      imagePreviewUnavailable: "Unable to preview this image.",
      rawLinkAvailable: "The raw file link is still available above.",
      imagePixels: "{width} x {height} pixels",
      loadingObjPreview: "Loading OBJ preview...",
      loadingFbxSummary: "Reading FBX structure...",
      noModelFile: "No model file is available.",
      previewingModel: "Previewing {name}. Drag to rotate. Use the mouse wheel to zoom.",
      previewingModelViaObj: "Reviewing {name} through a paired OBJ preview. Drag to rotate. Use the mouse wheel to zoom.",
      objPreviewUnavailable: "Unable to preview this OBJ file.",
      fbxSummaryLoaded: "This FBX does not have an in-browser mesh preview yet, so the panel below shows its structure summary.",
      fbxSummaryUnavailable: "Unable to read a structure summary for this FBX file.",
      fbxSummaryPlaceholder: "The FBX structure summary appears in the stats panel below.",
      selectedLod: "Selected LOD",
      sampledPoints: "Sampled points",
      vertices: "Vertices",
      faces: "Faces",
      objectsGroups: "Objects / groups",
      fbxFormat: "FBX format",
      fbxVersion: "FBX version",
      fbxNodes: "Nodes",
      fbxModels: "Model nodes",
      fbxGeometries: "Geometry nodes",
      fbxMaterials: "Material nodes",
      fbxTextures: "Texture nodes",
      fbxAnimations: "Animation stacks",
      fbxSampleNames: "Sample names",
    },
  };

  const ASSET_STATE = {
    activeView: "story",
    uiLocale: "zh",
    loaded: false,
    loadPromise: null,
    entries: [],
    entryByRel: new Map(),
    rawEntryByRel: new Map(),
    bundles: [],
    bundleById: new Map(),
    bundleIdsByAssetRel: new Map(),
    filtered: [],
    rows: [],
    totalH: 0,
    expanded: new Set(),
    relations: {},
    exportRoot: "",
    sourceRoots: {},
    selectedRel: null,
    selectedEntry: null,
    selectedVariantRel: null,
    initialAssetHandled: false,
    filtersCollapsed: false,
    qTimer: null,
    detailToken: 0,
    imageObjectUrl: "",
    filters: createDefaultFilters(),
    modelCache: new Map(),
    fbxSummaryCache: new Map(),
    viewer: {
      rotationX: -0.35,
      rotationY: 0.75,
      zoom: 1,
      dragging: false,
      lastX: 0,
      lastY: 0,
      renderQueued: false,
      model: null,
      canvas: null,
      ctx: null,
      bound: false,
    },
  };

  function stripAssetLodSuffix(value) {
    return String(value || "").replace(/(?:[_-])lod\d+$/i, "");
  }

  function exportedAssetStemInfo(rel, name) {
    const rawStem = String(name || "").replace(/\.[^.]+$/i, "");
    const split = splitPathIdExportStem(rawStem);
    if (relRequiresPathIdExportName(rel)) {
      return split ? { stem: split.base, rawStem, pathId: split.pathId } : null;
    }
    return {
      stem: split ? split.base : rawStem,
      rawStem,
      pathId: split ? split.pathId : "",
    };
  }

  function assetGroupStem(kind, stem) {
    return kind === "model" ? stripAssetLodSuffix(stem) : String(stem || "");
  }

  function stripSharedAssetPrefix(value = "") {
    const normalized = String(value || "").trim();
    const match = normalized.match(/^([A-Za-z])[_-](.+)$/);
    if (!match) return normalized;
    if (!SHARED_ASSET_NAME_PREFIXES.has(String(match[1] || "").toUpperCase())) return normalized;
    return String(match[2] || "").trim();
  }

  function inferTextureVariantStem(stem = "", ext = "") {
    if (String(ext || "").toLowerCase() !== "png") return null;
    const match = String(stem || "").match(/^(.*?)(?:[_-])([A-Za-z]{1,10})$/);
    if (!match) return null;
    const parentStem = String(match[1] || "").trim();
    const suffixLabel = String(match[2] || "").toUpperCase();
    if (!parentStem || !suffixLabel || !/^[A-Z]{1,10}$/.test(suffixLabel)) return null;

    const looksLikeTexture = /^t[_-]/i.test(stem) || /^tex(?:ture)?[_-]/i.test(stem);
    if (!KNOWN_TEXTURE_SUFFIXES.has(suffixLabel) && !looksLikeTexture) return null;

    return { parentStem, suffixLabel };
  }

  function inferGroupedFamily(entry) {
    if (!entry) return null;
    if (entry.kind === "image") return inferTextureVariantStem(entry.stem, entry.ext);

    const match = String(entry.stem || "").match(/^(.*?)(?:[_-])([^-_]+)$/);
    if (!match) return null;
    const parentStem = String(match[1] || "").trim();
    const suffixLabel = String(match[2] || "").trim();
    if (!parentStem || !suffixLabel) return null;
    return { parentStem, suffixLabel };
  }

  function createDefaultFilters() {
    return {
      q: "",
      types: new Set(),
      source: "",
      sort: "path",
    };
  }

  function isMobileLayout() {
    return window.matchMedia(MOBILE_LAYOUT_QUERY).matches;
  }

  function resolveInitialFiltersCollapsed() {
    const stored = storageGet(FILTER_PANEL_STORAGE_KEY);
    if (stored === "1") return true;
    if (stored === "0") return false;
    return isMobileLayout();
  }

  function persistFiltersCollapsed(collapsed) {
    storageSet(FILTER_PANEL_STORAGE_KEY, collapsed ? "1" : "0");
  }

  function resolveInitialUiLocale() {
    const fromWindow = normalizeUiLocale(window.WEBUI_UI_LOCALE);
    if (fromWindow) return fromWindow;
    const stored = normalizeUiLocale(storageGet(UI_LOCALE_STORAGE_KEY));
    if (stored) return stored;
    return document.documentElement.lang.toLowerCase().startsWith("zh") ? "zh" : "en";
  }

  function assetUiText(key, replacements = {}) {
    const locale = ASSET_UI_TEXTS[ASSET_STATE.uiLocale] || ASSET_UI_TEXTS.en;
    const template = locale[key] || ASSET_UI_TEXTS.en[key] || key;
    return applyTemplate(template, replacements);
  }

  function assetKindLabel(kind) {
    return kind === "image" ? assetUiText("images") : assetUiText("models");
  }

  function assetTypeLabel(type) {
    return String(type || "").toUpperCase() || assetUiText("none");
  }

  function applyAssetUiStrings() {
    $("#asset-app-title").textContent = assetUiText("title");
    $("#asset-count-label").textContent = assetUiText("countLabel");
    $("#asset-filter-toggle").textContent = assetUiText(ASSET_STATE.filtersCollapsed ? "showFilters" : "hideFilters");
    $("#asset-q").placeholder = assetUiText("searchPlaceholder");
    $("#asset-type-label").textContent = assetUiText("type");
    $("#asset-source-label").textContent = assetUiText("source");
    $("#asset-source-all-option").textContent = assetUiText("allSources");
    $("#asset-sort-label").textContent = assetUiText("sort");
    $("#asset-sort-path").textContent = assetUiText("sortPath");
    $("#asset-sort-size-desc").textContent = assetUiText("sortSizeDesc");
    $("#asset-sort-size-asc").textContent = assetUiText("sortSizeAsc");
    $("#asset-sort-name").textContent = assetUiText("sortName");
    $("#asset-reset").textContent = assetUiText("reset");
    $("#asset-list-meta-label").textContent = assetUiText("listUnit");
    if (!ASSET_STATE.selectedEntry) $("#asset-empty").textContent = assetUiText("empty");
    $("#asset-open-raw").textContent = assetUiText("openRawFile");
    $("#asset-download-current").textContent = assetUiText("downloadCurrentFile");
    $("#asset-download-bundle").textContent = assetUiText("downloadBundle");
    $("#asset-copy-path").textContent = assetUiText("copyRelativePath");
    $("#asset-preview-label").textContent = assetUiText("preview");
    $("#asset-preview-placeholder").textContent = assetUiText("previewPlaceholder");
    $("#asset-inspector-label").textContent = assetUiText("inspector");
    $("#asset-related-label").textContent = assetUiText("relatedFiles");
    $("#asset-variants-label").textContent = assetUiText("lodVariants");
    $("#asset-materials-label").textContent = assetUiText("linkedMaterials");
    $("#asset-textures-label").textContent = assetUiText("linkedTextures");
    $("#asset-references-label").textContent = assetUiText("referencedBy");
    $("#asset-model-stats-label").textContent = assetUiText("modelStats");
  }

  function setAssetUiLocale(locale, { refresh = true } = {}) {
    ASSET_STATE.uiLocale = normalizeUiLocale(locale) || "en";
    applyAssetUiStrings();

    if (!refresh || !ASSET_STATE.loaded) return;
    buildTypeChips();
    buildSourceSelect();
    applyAssetFilters();
    if (ASSET_STATE.selectedEntry) renderSelectedAsset();
  }

  function setFiltersCollapsed(collapsed, { persist = true } = {}) {
    ASSET_STATE.filtersCollapsed = !!collapsed;
    if (persist) persistFiltersCollapsed(ASSET_STATE.filtersCollapsed);
    syncFilterPanel();
    renderAssetList();
  }

  function syncFilterPanel() {
    const panel = $("#asset-filter-panel");
    const toggle = $("#asset-filter-toggle");
    const left = $("#asset-left");
    if (!panel || !toggle || !left) return;

    panel.hidden = ASSET_STATE.filtersCollapsed;
    left.classList.toggle("filters-collapsed", ASSET_STATE.filtersCollapsed);
    toggle.setAttribute("aria-expanded", String(!ASSET_STATE.filtersCollapsed));
    toggle.textContent = assetUiText(ASSET_STATE.filtersCollapsed ? "showFilters" : "hideFilters");
  }

  function resolveViewFromHash() {
    const hash = (window.location.hash || "").replace(/^#/, "").toLowerCase();
    if (hash === "assets" || hash === "reference" || hash === "updates") return hash;
    return "story";
  }

  function updateHashForView(view) {
    const nextHash =
      view === "assets" ? "#assets"
        : view === "reference" ? "#reference"
          : view === "updates" ? "#updates"
            : "#story";
    if (window.location.hash === nextHash) return;
    const url = `${window.location.pathname}${window.location.search}${nextHash}`;
    history.replaceState(null, "", url);
  }

  function setDocumentTitleForView(view) {
    if (view === "assets") {
      document.title = assetUiText("title");
      return;
    }
    if (view === "reference") {
      const referenceTitle = ($("#reference-title") && $("#reference-title").textContent) || "Endfield Text Reference";
      document.title = referenceTitle;
      return;
    }
    if (view === "updates") {
      const updatesTitle = ($("#updates-title") && $("#updates-title").textContent) || "Endfield WebUI Content Updates";
      document.title = updatesTitle;
      return;
    }
    const storyTitle = ($("#app-title") && $("#app-title").textContent) || "Endfield Story Browser";
    document.title = storyTitle;
  }

  function setActiveView(view, { updateHash = true } = {}) {
    ASSET_STATE.activeView = view === "assets" || view === "reference" || view === "updates" ? view : "story";
    document.body.dataset.activeView = ASSET_STATE.activeView;

    $$(".view-tab").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.view === ASSET_STATE.activeView);
    });
    $$(".page-view").forEach((page) => {
      const isActive = page.dataset.view === ASSET_STATE.activeView;
      page.hidden = !isActive;
      page.classList.toggle("is-active", isActive);
    });

    if (updateHash) updateHashForView(ASSET_STATE.activeView);
    setDocumentTitleForView(ASSET_STATE.activeView);

    if (ASSET_STATE.activeView === "assets") {
      ensureAssetsLoaded().then(() => {
        renderAssetList();
        if (ASSET_STATE.selectedEntry) renderSelectedAsset();
        queueModelRender();
      });
    }

    window.dispatchEvent(new CustomEvent("webui:view-changed", {
      detail: { view: ASSET_STATE.activeView },
    }));

    requestAnimationFrame(() => {
      window.dispatchEvent(new Event("resize"));
    });
  }

  function bindViewTabs() {
    $$(".view-tab").forEach((button) => {
      button.addEventListener("click", () => setActiveView(button.dataset.view));
    });
    window.addEventListener("hashchange", () => {
      setActiveView(resolveViewFromHash(), { updateHash: false });
    });
  }

  function bindAssetEvents() {
    $("#asset-filter-toggle").addEventListener("click", () => {
      setFiltersCollapsed(!ASSET_STATE.filtersCollapsed);
    });

    $("#asset-q").addEventListener("input", (ev) => {
      clearTimeout(ASSET_STATE.qTimer);
      const value = ev.target.value;
      ASSET_STATE.qTimer = setTimeout(() => {
        ASSET_STATE.filters.q = value.trim().toLowerCase();
        applyAssetFilters();
      }, 120);
    });

    $("#asset-source").addEventListener("change", (ev) => {
      ASSET_STATE.filters.source = ev.target.value;
      applyAssetFilters();
    });

    $("#asset-sort").addEventListener("change", (ev) => {
      ASSET_STATE.filters.sort = ev.target.value;
      applyAssetFilters();
    });

    $("#asset-reset").addEventListener("click", () => {
      ASSET_STATE.filters = createDefaultFilters();
      $("#asset-q").value = "";
      $("#asset-source").value = "";
      $("#asset-sort").value = "path";
      $$(".asset-filter-chip.on").forEach((chip) => chip.classList.remove("on"));
      applyAssetFilters();
    });

    $("#asset-list-wrap").addEventListener("scroll", renderAssetList);
    window.addEventListener("resize", () => {
      renderAssetList();
      queueModelRender();
    });

    $("#asset-list").addEventListener("click", (ev) => {
      const groupRow = ev.target.closest(".asset-group-row");
      if (groupRow) {
        toggleAssetPath(groupRow.dataset.path || "");
        return;
      }

      const itemRow = ev.target.closest(".asset-item-row");
      if (!itemRow) return;
      const entry = ASSET_STATE.entryByRel.get(itemRow.dataset.rel || "");
      if (entry) selectAsset(entry, { scrollIntoView: false });
    });

    $("#asset-copy-path").addEventListener("click", async () => {
      const rel = getSelectedAssetRelForUrl();
      if (!rel) return;
      const ok = await copyTextToClipboard(rel);
      $("#asset-copy-path").textContent = ok ? assetUiText("copiedPath") : assetUiText("copyFailed");
      window.setTimeout(() => {
        $("#asset-copy-path").textContent = assetUiText("copyRelativePath");
      }, 1200);
    });
  }

  function ensureAssetsLoaded() {
    if (ASSET_STATE.loaded) return Promise.resolve();
    if (ASSET_STATE.loadPromise) return ASSET_STATE.loadPromise;

    ASSET_STATE.loadPromise = Promise.all([
      fetch("data/assets/index.json")
        .then((res) => {
          if (!res.ok) throw new Error(`assets/index.json HTTP ${res.status}`);
          return res.json();
        }),
      loadAssetBundleIndex(),
    ])
      .then(([payload]) => {
        const hydrated = hydrateEntries(payload.entries || []);
        ASSET_STATE.entries = hydrated.entries;
        ASSET_STATE.entryByRel = hydrated.entryByRel;
        ASSET_STATE.rawEntryByRel = hydrated.rawEntryByRel;
        ASSET_STATE.relations = payload.relations || {};
        ASSET_STATE.exportRoot = String(payload.root || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
        ASSET_STATE.sourceRoots = payload.sourceRoots && typeof payload.sourceRoots === "object"
          ? Object.fromEntries(
              Object.entries(payload.sourceRoots).map(([key, value]) => [
                key,
                String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
              ])
            )
          : {};
        ASSET_STATE.loaded = true;
        $("#asset-count").textContent = ASSET_STATE.entries.length.toLocaleString();
        buildTypeChips();
        buildSourceSelect();
        seedAssetExpansions();
        applyAssetFilters();
        applyInitialAssetSelection();
      })
      .catch((error) => {
        $("#asset-empty").textContent = assetUiText("assetIndexError", { error: String(error) });
        throw error;
      });

    return ASSET_STATE.loadPromise;
  }

  function loadAssetBundleIndex() {
    return fetch("data/assets/bundles/index.json")
      .then((res) => {
        if (res.status === 404) return null;
        if (!res.ok) throw new Error(`assets/bundles/index.json HTTP ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        hydrateAssetBundles(payload || {});
      })
      .catch((error) => {
        console.warn("Unable to load asset bundles:", error);
        hydrateAssetBundles({});
      });
  }

  function hydrateAssetBundles(payload) {
    const bundles = Array.isArray(payload?.bundles)
      ? payload.bundles.map((bundle) => ({
          id: String(bundle.id || ""),
          label: String(bundle.label || bundle.id || ""),
          description: String(bundle.description || ""),
          download: String(bundle.download || ""),
          bytes: Number(bundle.bytes || 0),
          fileCount: Number(bundle.fileCount || 0),
          materialRel: String(bundle.materialRel || ""),
          assetRels: Array.isArray(bundle.assetRels) ? bundle.assetRels.map((rel) => String(rel || "")) : [],
        })).filter((bundle) => bundle.id && bundle.download)
      : [];

    ASSET_STATE.bundles = bundles;
    ASSET_STATE.bundleById = new Map(bundles.map((bundle) => [bundle.id, bundle]));

    const bundleIdsByAssetRel = new Map();
    if (payload?.byAssetRel && typeof payload.byAssetRel === "object") {
      for (const [rel, ids] of Object.entries(payload.byAssetRel)) {
        const normalizedIds = Array.isArray(ids)
          ? ids.map((id) => String(id || "")).filter((id) => ASSET_STATE.bundleById.has(id))
          : [];
        if (normalizedIds.length) bundleIdsByAssetRel.set(String(rel || ""), normalizedIds);
      }
    } else {
      for (const bundle of bundles) {
        for (const rel of bundle.assetRels) {
          if (!bundleIdsByAssetRel.has(rel)) bundleIdsByAssetRel.set(rel, []);
          bundleIdsByAssetRel.get(rel).push(bundle.id);
        }
      }
    }
    ASSET_STATE.bundleIdsByAssetRel = bundleIdsByAssetRel;
  }

  function hydrateEntries(entries) {
    const hydrated = entries.map((raw) => {
      const kind = raw.k === "model" ? "model" : "image";
      const rel = String(raw.r || "");
      const parts = rel.split("/").filter(Boolean);
      const name = parts[parts.length - 1] || rel;
      const source = parts[0] || "";
      const dirParts = parts.slice(1, -1);
      const dir = dirParts.join("/");
      const extIndex = name.lastIndexOf(".");
      const ext = extIndex >= 0 ? name.slice(extIndex + 1).toLowerCase() : "";
      const stemInfo = exportedAssetStemInfo(rel, name);
      if (!stemInfo || !stemInfo.stem) return null;
      const stem = stemInfo.stem;
      const groupInfo = deriveAssetGroupInfo(kind, stem);
      const textureVariant = kind === "image" ? inferTextureVariantStem(stem, ext) : null;
      const variantScope = kind === "model" || textureVariant ? source : dir;
      const lodMatch = stem.match(/(?:^|[_-])lod(\d+)$/i);
      const lod = lodMatch ? Number(lodMatch[1]) : null;
      return {
        kind,
        rel,
        size: Number(raw.s || 0),
        name,
        dir,
        variantScope,
        source,
        ext,
        stem,
        rawStem: stemInfo.rawStem,
        pathId: stemInfo.pathId || String(raw.pid || ""),
        family: stripAssetLodSuffix(stem),
        familyKey: `${source}::${groupInfo.key}`.toLowerCase(),
        groupKey: groupInfo.key,
        groupLabel: groupInfo.label,
        groupRaw: groupInfo.raw,
        lod,
        previewRel: String(raw.p || ""),
        searchText: "",
        variantLabel: "",
        grouped: false,
        duplicateCount: 1,
        rawRels: [rel],
      };
    }).filter(Boolean);

    const stemsByScope = new Map();
    for (const entry of hydrated) {
      const scopeKey = `${entry.kind}::${entry.variantScope || entry.dir}`.toLowerCase();
      let scope = stemsByScope.get(scopeKey);
      if (!scope) {
        scope = new Set();
        stemsByScope.set(scopeKey, scope);
      }
      scope.add(entry.stem.toLowerCase());
    }

    const groupedFamilies = new Set();
    const suffixedEntries = new Map();
    const suffixedFamilyVariants = new Map();
    for (const entry of hydrated) {
      const scopeKey = `${entry.kind}::${entry.variantScope || entry.dir}`.toLowerCase();
      const suffixFamily = inferGroupedFamily(entry);
      if (!suffixFamily) continue;
      const familyKey = `${scopeKey}::${suffixFamily.parentStem}`.toLowerCase();
      let labels = suffixedFamilyVariants.get(familyKey);
      if (!labels) {
        labels = new Set();
        suffixedFamilyVariants.set(familyKey, labels);
      }
      labels.add(String(suffixFamily.suffixLabel || "").toLowerCase());
    }

    for (const entry of hydrated) {
      const scopeKey = `${entry.kind}::${entry.variantScope || entry.dir}`.toLowerCase();
      if (entry.lod !== null) {
        groupedFamilies.add(`${scopeKey}::${entry.family}`.toLowerCase());
        continue;
      }

      const suffixFamily = inferGroupedFamily(entry);
      if (!suffixFamily) continue;
      const parentStem = suffixFamily.parentStem;
      const suffixLabel = suffixFamily.suffixLabel;
      if (!parentStem || !suffixLabel) continue;

      const scope = stemsByScope.get(scopeKey);
      const familyKey = `${scopeKey}::${parentStem}`.toLowerCase();
      const hasBaseEntry = !!(scope && scope.has(parentStem.toLowerCase()));
      const siblingSuffixes = suffixedFamilyVariants.get(familyKey);
      const hasTextureSet = !!(siblingSuffixes && siblingSuffixes.size > 1);
      if (!hasBaseEntry && !hasTextureSet) continue;
      groupedFamilies.add(familyKey);
      suffixedEntries.set(entry.rel, { parentStem, suffixLabel });
    }

    for (const entry of hydrated) {
      const scopeKey = `${entry.kind}::${entry.variantScope || entry.dir}`.toLowerCase();
      const suffixed = suffixedEntries.get(entry.rel);
      const ownFamilyKey = `${scopeKey}::${entry.stem}`.toLowerCase();
      const lodFamilyKey = `${scopeKey}::${entry.family}`.toLowerCase();
      const suffixFamilyKey = suffixed ? `${scopeKey}::${suffixed.parentStem}`.toLowerCase() : "";

      if (entry.lod !== null && groupedFamilies.has(lodFamilyKey)) {
        entry.family = entry.family;
        entry.grouped = true;
        entry.variantLabel = `LOD ${entry.lod}`;
      } else if (suffixed && groupedFamilies.has(suffixFamilyKey)) {
        entry.family = suffixed.parentStem;
        entry.grouped = true;
        entry.variantLabel = suffixed.suffixLabel;
      } else if (groupedFamilies.has(ownFamilyKey)) {
        entry.family = entry.stem;
        entry.grouped = true;
        entry.variantLabel = entry.name;
      } else {
        entry.family = entry.stem;
        entry.grouped = false;
        entry.variantLabel = entry.name;
      }

      const familyGroupInfo = deriveAssetGroupInfo(entry.kind, entry.family);
      entry.groupKey = familyGroupInfo.key;
      entry.groupLabel = familyGroupInfo.label;
      entry.groupRaw = familyGroupInfo.raw;
      entry.familyKey = `${entry.source}::${familyGroupInfo.key}`.toLowerCase();
      entry.searchText = [
        entry.rel,
        entry.name,
        entry.dir,
        entry.source,
        entry.groupKey,
        entry.groupLabel,
        entry.groupRaw,
        entry.rawStem,
        entry.pathId,
        entry.family,
        entry.variantLabel,
        entry.ext,
        entry.kind,
      ].join(" ").toLowerCase();
    }

    const rawEntryByRel = new Map(hydrated.map((entry) => [entry.rel, entry]));
    return groupAssetEntries(collapseDuplicateAssetEntries(hydrated), rawEntryByRel);
  }

  function collapseDuplicateAssetEntries(entries) {
    const buckets = new Map();
    for (const entry of entries) {
      const key = `${entry.kind}::${entry.ext}::${entry.source}::${entry.stem}`.toLowerCase();
      let bucket = buckets.get(key);
      if (!bucket) {
        bucket = [];
        buckets.set(key, bucket);
      }
      bucket.push(entry);
    }

    const deduped = [];
    for (const bucket of buckets.values()) {
      bucket.sort((a, b) => compareAssets(a, b, "path"));
      const primary = bucket[0];
      primary.duplicateCount = bucket.length;
      primary.rawRels = bucket.map((entry) => entry.rel);
      if (bucket.length > 1) {
        primary.searchText = [
          primary.searchText,
          ...bucket.slice(1).flatMap((entry) => [entry.rel, entry.dir]),
        ].join(" ").toLowerCase();
      }
      deduped.push(primary);
    }

    return deduped;
  }

  function groupAssetEntries(entries, rawEntryByRel = new Map()) {
    const groupedEntries = [];
    const entryByRel = new Map();
    const assetGroups = new Map();

    for (const entry of entries) {
      if (!entry.grouped) {
        groupedEntries.push(entry);
        for (const rel of entry.rawRels || [entry.rel]) {
          entryByRel.set(rel, entry);
        }
        continue;
      }

      const scopeDir = entry.variantScope || entry.dir;
      const key = `${entry.kind}::${entry.ext}::${scopeDir.toLowerCase()}::${entry.family.toLowerCase()}`;
      let group = assetGroups.get(key);
      if (!group) {
        group = {
          kind: entry.kind,
          rel: entry.rel,
          size: 0,
          name: `${entry.family}.${entry.ext}`,
          dir: scopeDir,
          variantScope: scopeDir,
          source: entry.source,
          ext: entry.ext,
          stem: entry.family,
          family: entry.family,
          familyKey: entry.familyKey,
          groupKey: entry.groupKey,
          groupLabel: entry.groupLabel,
          groupRaw: entry.groupRaw,
          lod: null,
          variantCount: 0,
          duplicateCount: 0,
          variantSummary: "",
          searchText: "",
          rawRels: [],
          variants: [],
        };
        assetGroups.set(key, group);
      }
      group.variants.push(entry);
    }

    for (const group of assetGroups.values()) {
      group.variants.sort(compareVariants);
      group.rel = group.variants[0].rel;
      group.size = group.variants.reduce((sum, variant) => sum + variant.size, 0);
      group.variantCount = group.variants.length;
      group.rawRels = group.variants.flatMap((variant) => variant.rawRels || [variant.rel]);
      group.duplicateCount = group.rawRels.length;
      group.variantSummary = summarizeVariantLabels(group.variants);
      group.searchText = [
        group.name,
        group.dir,
        group.source,
        group.groupKey,
        group.groupLabel,
        group.groupRaw,
        group.family,
        ...group.variants.map((variant) => variant.searchText),
      ].join(" ").toLowerCase();
      groupedEntries.push(group);
      for (const rel of group.rawRels) {
        entryByRel.set(rel, group);
      }
    }

    return {
      entries: groupedEntries,
      entryByRel,
      rawEntryByRel,
    };
  }

  function compareVariants(a, b) {
    const aIsBase = a.lod === null && a.stem.toLowerCase() === a.family.toLowerCase();
    const bIsBase = b.lod === null && b.stem.toLowerCase() === b.family.toLowerCase();
    if (aIsBase !== bIsBase) return aIsBase ? -1 : 1;
    const lodA = a.lod === null ? Number.POSITIVE_INFINITY : a.lod;
    const lodB = b.lod === null ? Number.POSITIVE_INFINITY : b.lod;
    return (lodA - lodB) || a.variantLabel.localeCompare(b.variantLabel) || a.rel.localeCompare(b.rel);
  }

  function summarizeVariantLabels(variants) {
    const labels = variants.map((variant) => {
      return variant.variantLabel || variant.name;
    });
    return labels.join(", ");
  }

  function hasHiddenDuplicateFiles(entry) {
    if (!entry) return false;
    const visibleCount = Array.isArray(entry.variants) ? entry.variants.length : 1;
    return Number(entry.duplicateCount || visibleCount) > visibleCount;
  }

  function deriveAssetGroupInfo(kind = "", stem = "") {
    const originalStem = assetGroupStem(kind, stem).trim();
    const groupStem = stripSharedAssetPrefix(originalStem);
    if (!groupStem) {
      return { key: "(root)", label: "(root)", raw: "" };
    }
    return {
      key: groupStem.toLowerCase(),
      label: groupStem,
      raw: originalStem && originalStem !== groupStem ? originalStem : "",
    };
  }

  function buildTypeChips() {
    const counts = countBy(ASSET_STATE.entries, (entry) => entry.ext || entry.kind);
    const wrap = $("#asset-type-filter");
    wrap.innerHTML = "";
    const types = Object.keys(counts).sort((a, b) => counts[b] - counts[a] || naturalCompare(a, b));
    for (const type of types) {
      const count = counts[type] || 0;
      if (!count) continue;
      const chip = document.createElement("span");
      chip.className = "chip asset-filter-chip";
      chip.dataset.value = type;
      chip.textContent = `${assetTypeLabel(type)} (${count})`;
      chip.addEventListener("click", () => toggleFilterSet(ASSET_STATE.filters.types, type, chip));
      wrap.appendChild(chip);
    }
  }

  function buildSourceSelect() {
    const counts = countBy(ASSET_STATE.entries, (entry) => entry.source);
    const select = $("#asset-source");
    select.length = 1;
    const names = Object.keys(counts).sort((a, b) => counts[b] - counts[a] || naturalCompare(a, b));
    for (const name of names) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = `${name} (${counts[name]})`;
      select.appendChild(option);
    }
  }

  function seedAssetExpansions() {
    if (ASSET_STATE.expanded.size) return;
    const sources = Array.from(new Set(ASSET_STATE.entries.map((entry) => entry.source).filter(Boolean)));
    for (const source of sources) {
      ASSET_STATE.expanded.add(source);
    }
  }

  function toggleFilterSet(set, value, el) {
    if (set.has(value)) set.delete(value);
    else set.add(value);
    el.classList.toggle("on");
    applyAssetFilters();
  }

  function applyAssetFilters() {
    const filters = ASSET_STATE.filters;
    const q = filters.q;

    ASSET_STATE.filtered = ASSET_STATE.entries.filter((entry) => {
      if (q && !entry.searchText.includes(q)) return false;
      if (filters.source && entry.source !== filters.source) return false;
      if (filters.types.size && !filters.types.has(entry.ext || entry.kind)) return false;
      return true;
    });

    ASSET_STATE.filtered.sort((a, b) => compareAssets(a, b, filters.sort));
    $("#asset-shown").textContent = ASSET_STATE.filtered.length.toLocaleString();
    $("#asset-total").textContent = ASSET_STATE.entries.length.toLocaleString();
    rebuildAssetTree();
  }

  function compareAssets(a, b, sort) {
    if (sort === "size-desc") {
      return (b.size - a.size) || a.rel.localeCompare(b.rel);
    }
    if (sort === "size-asc") {
      return (a.size - b.size) || a.rel.localeCompare(b.rel);
    }
    if (sort === "name") {
      return a.name.localeCompare(b.name) || a.rel.localeCompare(b.rel);
    }
    return a.rel.localeCompare(b.rel);
  }

  function naturalCompare(a, b) {
    const ax = String(a || "").match(/(\D+|\d+)/g) || [];
    const bx = String(b || "").match(/(\D+|\d+)/g) || [];
    for (let index = 0; index < Math.max(ax.length, bx.length); index += 1) {
      const ai = ax[index];
      const bi = bx[index];
      if (ai === undefined) return -1;
      if (bi === undefined) return 1;
      const an = Number(ai);
      const bn = Number(bi);
      if (!Number.isNaN(an) && !Number.isNaN(bn)) {
        if (an !== bn) return an - bn;
      } else if (ai !== bi) {
        return ai < bi ? -1 : 1;
      }
    }
    return 0;
  }

  function sumAssetLeaves(node) {
    let count = 0;
    for (const group of Object.values(node)) {
      count += (group && Array.isArray(group.items)) ? group.items.length : 0;
    }
    return count;
  }

  function rebuildAssetTree({ resetScroll = true } = {}) {
    const tree = {};
    for (const entry of ASSET_STATE.filtered) {
      const source = entry.source || assetUiText("rootFolder");
      (tree[source] ??= {});
      const bucket = (tree[source][entry.groupKey] ??= {
        label: entry.groupLabel || assetUiText("rootFolder"),
        raw: entry.groupRaw || "",
        items: [],
      });
      bucket.items.push(entry);
    }

    const rows = [];
    let offset = 0;
    const autoExpand = !!ASSET_STATE.filters.q;

    const pushGroup = (level, path, label, count, raw = "") => {
      const expanded = autoExpand || ASSET_STATE.expanded.has(path);
      rows.push({
        type: "group",
        level,
        path,
        label,
        count,
        raw,
        top: offset,
        h: ASSET_GROUP_ROW_H,
        expanded,
      });
      offset += ASSET_GROUP_ROW_H;
      return expanded;
    };

    const pushItem = (entry) => {
      rows.push({
        type: "item",
        entry,
        top: offset,
        h: ASSET_ITEM_ROW_H,
      });
      offset += ASSET_ITEM_ROW_H;
    };

    const sources = Object.keys(tree).sort(naturalCompare);
    for (const source of sources) {
      const sourcePath = source;
      if (!pushGroup(0, sourcePath, source, sumAssetLeaves(tree[source]))) continue;

      const groups = Object.keys(tree[source]).sort(naturalCompare);
      for (const groupKey of groups) {
        const group = tree[source][groupKey];
        const groupPath = `${source}/${groupKey}`;
        if (!pushGroup(1, groupPath, group.label, group.items.length, group.raw)) continue;
        for (const entry of group.items) {
          pushItem(entry);
        }
      }
    }

    ASSET_STATE.rows = rows;
    ASSET_STATE.totalH = offset;
    $("#asset-list-spacer").style.height = `${offset}px`;
    if (resetScroll) $("#asset-list-wrap").scrollTop = 0;
    renderAssetList();
  }

  function findFirstVisibleAssetRow(scrollTop) {
    const rows = ASSET_STATE.rows;
    let lo = 0;
    let hi = rows.length - 1;
    let answer = 0;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (rows[mid].top + rows[mid].h <= scrollTop) {
        lo = mid + 1;
      } else {
        answer = mid;
        hi = mid - 1;
      }
    }
    return answer;
  }

  function renderAssetList() {
    const wrap = $("#asset-list-wrap");
    const spacer = $("#asset-list-spacer");
    const list = $("#asset-list");
    if (!wrap || !spacer || !list) return;

    const total = ASSET_STATE.rows.length;
    spacer.style.height = `${ASSET_STATE.totalH}px`;
    if (!total) {
      list.replaceChildren();
      return;
    }

    const viewportHeight = wrap.clientHeight || 0;
    const scrollTop = wrap.scrollTop || 0;
    const startTop = Math.max(0, scrollTop - ASSET_OVERSCAN_PX);
    const endTop = scrollTop + viewportHeight + ASSET_OVERSCAN_PX;

    const fragment = document.createDocumentFragment();
    let index = findFirstVisibleAssetRow(startTop);
    while (index < total && ASSET_STATE.rows[index].top < endTop) {
      fragment.appendChild(renderAssetRow(ASSET_STATE.rows[index]));
      index += 1;
    }
    list.replaceChildren(fragment);
  }

  function renderAssetRow(row) {
    if (row.type === "group") return renderAssetGroupRow(row);
    return renderAssetItemRow(row);
  }

  function renderAssetGroupRow(row) {
    const div = document.createElement("div");
    div.className = `row group lvl-${row.level} asset-group-row` + (row.expanded ? " expanded" : "");
    div.dataset.path = row.path;
    div.style.top = `${row.top}px`;
    div.style.height = `${row.h}px`;
    div.style.paddingLeft = `${8 + row.level * 14}px`;
    const twisty = row.expanded ? "v" : ">";
    const label = row.label === "(root)" ? assetUiText("rootFolder") : row.label;
    div.innerHTML =
      `<span class="twisty">${twisty}</span>` +
      `<span class="group-main">` +
        `<span class="label" title="${escapeHtml(label)}">${escapeHtml(label)}</span>` +
        (row.raw ? `<span class="sub mono" title="${escapeHtml(row.raw)}">${escapeHtml(row.raw)}</span>` : "") +
      `</span>` +
      `<span class="group-count">${row.count}</span>`;
    return div;
  }

  function renderAssetItemRow(row) {
    const entry = row.entry;
    const div = document.createElement("div");
    div.className = "row asset-item-row";
    if (ASSET_STATE.selectedRel === entry.rel) div.classList.add("is-selected");
    div.dataset.rel = entry.rel;
    div.style.top = `${row.top}px`;
    div.style.height = `${row.h}px`;
    div.style.paddingLeft = `${8 + 2 * 14}px`;

    const line1 = document.createElement("div");
    line1.className = "asset-row-line1";

    const badge = document.createElement("span");
    badge.className = `asset-badge ${entry.kind === "image" ? "asset-badge-image" : "asset-badge-model"}`;
    badge.textContent = assetTypeLabel(entry.ext || entry.kind);
    line1.appendChild(badge);

    const name = document.createElement("div");
    name.className = "asset-row-name";
    name.textContent = entry.name;
    line1.appendChild(name);

    const size = document.createElement("div");
    size.className = "asset-row-size";
    size.textContent = formatBytes(entry.size);
    line1.appendChild(size);

    const line2 = document.createElement("div");
    line2.className = "asset-row-line2";

    const dir = document.createElement("div");
    dir.className = "asset-row-dir";
    dir.textContent = entry.dir || assetUiText("rootFolder");
    line2.appendChild(dir);

    const extra = document.createElement("div");
    extra.className = "asset-row-extra";
    if (Array.isArray(entry.variants)) {
      extra.textContent = [
        entry.source,
        assetUiText("variantsCount", { count: entry.variantCount }),
        hasHiddenDuplicateFiles(entry) ? assetUiText("copiesCount", { count: entry.duplicateCount }) : "",
      ]
        .filter(Boolean)
        .join(" / ");
    } else {
      extra.textContent = [
        entry.source,
        hasHiddenDuplicateFiles(entry) ? assetUiText("copiesCount", { count: entry.duplicateCount }) : "",
        entry.lod === null ? "" : `LOD ${entry.lod}`,
      ]
        .filter(Boolean)
        .join(" / ");
    }
    line2.appendChild(extra);

    div.appendChild(line1);
    div.appendChild(line2);
    return div;
  }

  function selectAsset(entry, { scrollIntoView = true, updateUrl = true, variantRel = "" } = {}) {
    ASSET_STATE.selectedRel = entry.rel;
    ASSET_STATE.selectedEntry = entry;
    ASSET_STATE.selectedVariantRel = resolveInitialVariantRel(entry, variantRel);
    expandAssetEntryPaths(entry);
    renderAssetList();
    if (scrollIntoView) scrollSelectedAssetIntoView(entry);
    if (updateUrl) updateUrlForSelectedAsset(getSelectedAssetRelForUrl());
    renderSelectedAsset();
  }

  function assetEntryTreePaths(entry) {
    if (!entry) return [];
    const source = entry.source || assetUiText("rootFolder");
    return [source, `${source}/${entry.groupKey}`];
  }

  function expandAssetEntryPaths(entry) {
    let changed = false;
    for (const path of assetEntryTreePaths(entry)) {
      if (!ASSET_STATE.expanded.has(path)) {
        ASSET_STATE.expanded.add(path);
        changed = true;
      }
    }
    if (changed) rebuildAssetTree({ resetScroll: false });
  }

  function toggleAssetPath(path) {
    const wrap = $("#asset-list-wrap");
    const prevScroll = wrap.scrollTop;
    if (ASSET_STATE.expanded.has(path)) ASSET_STATE.expanded.delete(path);
    else ASSET_STATE.expanded.add(path);
    rebuildAssetTree({ resetScroll: false });
    wrap.scrollTop = Math.min(prevScroll, ASSET_STATE.totalH);
    renderAssetList();
  }

  function applyInitialAssetSelection() {
    if (ASSET_STATE.initialAssetHandled) return;
    ASSET_STATE.initialAssetHandled = true;

    const rel = getAssetRelFromQuery();
    if (!rel) return;
    const entry = ASSET_STATE.entryByRel.get(rel);
    if (!entry) return;
    selectAsset(entry, { scrollIntoView: true, updateUrl: false, variantRel: rel });
  }

  function getAssetRelFromQuery() {
    const params = new URLSearchParams(window.location.search);
    return params.get("asset") || "";
  }

  function updateUrlForSelectedAsset(rel) {
    const url = new URL(window.location.href);
    if (rel) url.searchParams.set("asset", rel);
    else url.searchParams.delete("asset");
    if (ASSET_STATE.activeView === "assets") url.hash = "#assets";
    history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }

  function resolveInitialVariantRel(entry, requestedRel = "") {
    if (!entry || !Array.isArray(entry.variants)) return null;
    if (requestedRel && entry.variants.some((variant) => variant.rel === requestedRel)) {
      return requestedRel;
    }
    if (ASSET_STATE.selectedVariantRel && entry.variants.some((variant) => variant.rel === ASSET_STATE.selectedVariantRel)) {
      return ASSET_STATE.selectedVariantRel;
    }
    return entry.variants[0]?.rel || null;
  }

  function isVariantGroup(entry) {
    return !!(entry && Array.isArray(entry.variants) && entry.variants.length);
  }

  function getActiveVariant(entry = ASSET_STATE.selectedEntry) {
    if (!isVariantGroup(entry)) return null;
    return entry.variants.find((variant) => variant.rel === ASSET_STATE.selectedVariantRel) || entry.variants[0] || null;
  }

  function getActiveAssetFile(entry = ASSET_STATE.selectedEntry) {
    if (!entry) return null;
    if (isVariantGroup(entry)) return getActiveVariant(entry);
    return entry;
  }

  function getActiveModelFile(entry = ASSET_STATE.selectedEntry) {
    if (!entry || entry.kind !== "model") return null;
    if (isVariantGroup(entry)) return getActiveVariant(entry);
    return entry;
  }

  function getSelectedAssetRelForUrl() {
    const entry = ASSET_STATE.selectedEntry;
    if (!entry) return "";
    return getActiveAssetFile(entry)?.rel || entry.rel;
  }

  function scrollSelectedAssetIntoView(entry) {
    const wrap = $("#asset-list-wrap");
    if (!wrap) return;

    const row = ASSET_STATE.rows.find((candidate) => candidate.type === "item" && candidate.entry.rel === entry.rel);
    if (!row) return;

    const top = row.top;
    const bottom = row.top + row.h;
    if (top < wrap.scrollTop) {
      wrap.scrollTop = top;
    } else if (bottom > wrap.scrollTop + wrap.clientHeight) {
      wrap.scrollTop = bottom - wrap.clientHeight;
    }
  }

  function renderSelectedAsset() {
    const entry = ASSET_STATE.selectedEntry;
    if (!entry) {
      $("#asset-empty").hidden = false;
      $("#asset-detail").hidden = true;
      return;
    }

    $("#asset-empty").hidden = true;
    $("#asset-detail").hidden = false;
    const activeVariant = getActiveAssetFile(entry);
    $("#asset-detail-title").textContent = entry.name;
    $("#asset-detail-meta").textContent = activeVariant ? activeVariant.rel : entry.rel;
    $("#asset-open-raw").href = assetHref(activeVariant ? activeVariant.rel : entry.rel);
    renderCurrentFileDownload(entry);
    renderBundleDownload(entry);
    renderFacts(entry);
    renderRelated(entry);
    renderVariants(entry);
    renderRelations(entry);

    if (entry.kind === "image") {
      renderImagePreview(activeVariant || entry);
    } else {
      renderModelPreview(entry);
    }
  }

  function formatAssetKindValue(entry, activeVariant = null) {
    const file = activeVariant || entry;
    const type = assetTypeLabel(file?.ext || entry.ext || entry.kind);
    return `${type} / ${assetKindLabel(entry.kind)}`;
  }

  function getSelectedAssetBundles(entry = ASSET_STATE.selectedEntry) {
    if (!entry) return [];

    const candidateRels = new Set();
    if (entry.rel) candidateRels.add(entry.rel);
    const active = getActiveAssetFile(entry);
    if (active?.rel) candidateRels.add(active.rel);
    if (Array.isArray(entry.variants)) {
      for (const variant of entry.variants) {
        if (variant?.rel) candidateRels.add(variant.rel);
      }
    }

    const bundles = [];
    const seenIds = new Set();
    for (const rel of candidateRels) {
      const bundleIds = ASSET_STATE.bundleIdsByAssetRel.get(rel) || [];
      for (const bundleId of bundleIds) {
        if (seenIds.has(bundleId)) continue;
        const bundle = ASSET_STATE.bundleById.get(bundleId);
        if (!bundle) continue;
        seenIds.add(bundleId);
        bundles.push(bundle);
      }
    }
    return bundles;
  }

  function renderCurrentFileDownload(entry) {
    const link = $("#asset-download-current");
    if (!link) return;

    const activeFile = getActiveAssetFile(entry);
    const rel = activeFile?.rel || entry?.rel || "";
    if (!rel) {
      link.hidden = true;
      link.removeAttribute("href");
      link.removeAttribute("download");
      link.removeAttribute("title");
      return;
    }

    link.hidden = false;
    link.href = assetHref(rel);
    link.download = rel.split("/").pop() || "";
    link.title = rel;
    link.textContent = assetUiText("downloadCurrentFile");
  }

  function renderBundleDownload(entry) {
    const link = $("#asset-download-bundle");
    if (!link) return;

    const bundle = getSelectedAssetBundles(entry)[0] || null;
    if (!bundle) {
      link.hidden = true;
      link.removeAttribute("href");
      link.removeAttribute("download");
      link.removeAttribute("title");
      return;
    }

    link.hidden = false;
    link.href = String(bundle.download || "#");
    link.download = bundle.download.split("/").pop() || "";
    link.title = bundle.description || bundle.label || "";
    link.textContent = assetUiText("downloadBundle");
  }

  function renderFacts(entry) {
    const activeVariant = getActiveAssetFile(entry);
    const facts = [
      [assetUiText("factKind"), formatAssetKindValue(entry, activeVariant)],
      [assetUiText("factSource"), entry.source || assetUiText("none")],
      [assetUiText("factFolder"), entry.groupLabel || entry.groupRaw || (entry.groupKey === "(root)" ? assetUiText("rootFolder") : entry.groupKey)],
      [assetUiText("factSize"), formatBytes(entry.size)],
    ];
    if (hasHiddenDuplicateFiles(entry)) {
      facts.push([assetUiText("factCopies"), String(entry.duplicateCount)]);
    }
    if (isVariantGroup(entry)) {
      facts.push([assetUiText("factLodVariants"), String(entry.variantCount)]);
      facts.push([assetUiText("factSelectedRawFile"), activeVariant ? activeVariant.rel : entry.rel]);
      facts.push([assetUiText("factLodSet"), entry.variantSummary || assetUiText("none")]);
    }
    facts.push([assetUiText("factRelativePath"), activeVariant ? activeVariant.rel : entry.rel]);
    if (activeVariant?.previewRel && activeVariant.previewRel !== activeVariant.rel) {
      facts.push([assetUiText("factPreviewProxy"), activeVariant.previewRel]);
    }
    if ((activeVariant || entry).lod !== null) facts.push([assetUiText("factLod"), String((activeVariant || entry).lod)]);
    if (entry.family && entry.family !== entry.stem) facts.push([assetUiText("factFamily"), entry.family]);

    const wrap = $("#asset-facts");
    const fragment = document.createDocumentFragment();
    for (const [label, value] of facts) {
      const item = document.createElement("div");
      item.className = "asset-fact";

      const factLabel = document.createElement("div");
      factLabel.className = "asset-fact-label";
      factLabel.textContent = label;
      item.appendChild(factLabel);

      const factValue = document.createElement("div");
      factValue.className = "asset-fact-value";
      factValue.textContent = value;
      item.appendChild(factValue);

      fragment.appendChild(item);
    }
    wrap.replaceChildren(fragment);
  }

  function renderVariants(entry) {
    const outer = $("#asset-variants-wrap");
    const wrap = $("#asset-variants");
    if (!outer || !wrap) return;

    if (!isVariantGroup(entry) || entry.variants.length <= 1) {
      outer.hidden = true;
      wrap.replaceChildren();
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const variant of entry.variants) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "asset-variant-chip";
      if (variant.rel === ASSET_STATE.selectedVariantRel) button.classList.add("is-active");
      button.textContent = variant.variantLabel || variant.name;
      button.title = [
        `${variant.rel} (${formatBytes(variant.size)})`,
        hasHiddenDuplicateFiles(variant) ? assetUiText("copiesCount", { count: variant.duplicateCount }) : "",
      ].filter(Boolean).join(" / ");
      button.addEventListener("click", () => {
        ASSET_STATE.selectedVariantRel = variant.rel;
        updateUrlForSelectedAsset(variant.rel);
        renderSelectedAsset();
      });
      fragment.appendChild(button);
    }

    wrap.replaceChildren(fragment);
    outer.hidden = false;
  }

  function renderRelated(entry) {
    const related = ASSET_STATE.entries
      .filter((item) => item.familyKey === entry.familyKey && item.rel !== entry.rel)
      .sort((a, b) => compareAssets(a, b, "path"))
      .slice(0, 12);

    const wrap = $("#asset-related");
    const outer = $("#asset-related-wrap");
    if (!related.length) {
      outer.hidden = true;
      wrap.replaceChildren();
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const item of related) {
      const block = document.createElement("div");
      block.className = "asset-related-item";

      const link = document.createElement("a");
      link.href = "#assets";
      link.textContent = item.rel;
      link.addEventListener("click", (ev) => {
        ev.preventDefault();
        selectAsset(item, { scrollIntoView: true });
      });
      block.appendChild(link);

      const meta = document.createElement("div");
      meta.className = "asset-related-meta";
      meta.textContent = assetUiText("relatedMeta", {
        kind: assetTypeLabel(item.ext || item.kind),
        size: formatBytes(item.size),
      });
      block.appendChild(meta);

      fragment.appendChild(block);
    }

    wrap.replaceChildren(fragment);
    outer.hidden = false;
  }

  function renderRelations(entry) {
    const relation = collectEntryRelations(entry);

    renderRelationList(
      "#asset-materials-wrap",
      "#asset-materials",
      relation.materials || [],
      renderMaterialRelationItem,
    );
    renderRelationList(
      "#asset-textures-wrap",
      "#asset-textures",
      coalesceTextureRelations(relation.textures || []),
      renderTextureRelationItem,
    );

    const references = [
      ...(relation.referencedByModels || []).map((item) => ({ ...item, kind: "model" })),
      ...(relation.referencedByMaterials || []).map((item) => ({ ...item, kind: "material" })),
    ];
    renderRelationList(
      "#asset-references-wrap",
      "#asset-references",
      coalesceReferenceRelations(references),
      renderReferenceRelationItem,
    );
  }

  function collectEntryRelations(entry) {
    if (!isVariantGroup(entry)) {
      return ASSET_STATE.relations[entry?.rel] || {};
    }

    if (entry.kind !== "model") {
      return ASSET_STATE.relations[getActiveAssetFile(entry)?.rel] || {};
    }

    const merged = {
      materials: [],
      textures: [],
      referencedByModels: [],
      referencedByMaterials: [],
    };

    for (const variant of entry.variants) {
      const relation = ASSET_STATE.relations[variant.rel] || {};
      for (const field of Object.keys(merged)) {
        for (const item of relation[field] || []) {
          if (!merged[field].some((existing) => JSON.stringify(existing) === JSON.stringify(item))) {
            merged[field].push(item);
          }
        }
      }
    }

    return merged;
  }

  function renderRelationList(outerSelector, wrapSelector, items, renderItem) {
    const outer = $(outerSelector);
    const wrap = $(wrapSelector);
    if (!outer || !wrap) return;

    if (!items || !items.length) {
      outer.hidden = true;
      wrap.replaceChildren();
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const item of items) {
      fragment.appendChild(renderItem(item));
    }
    wrap.replaceChildren(fragment);
    outer.hidden = false;
  }

  function coalesceTextureRelations(items) {
    const grouped = new Map();
    for (const item of items) {
      const key = `${item.rel || ""}\u0000${item.name || ""}`;
      let current = grouped.get(key);
      if (!current) {
        current = {
          ...item,
          slots: [],
        };
        grouped.set(key, current);
      }
      if (item.slot && !current.slots.includes(item.slot)) {
        current.slots.push(item.slot);
      }
    }
    return Array.from(grouped.values());
  }

  function coalesceReferenceRelations(items) {
    const grouped = new Map();
    for (const item of items) {
      const key = `${item.kind || ""}\u0000${item.rel || ""}\u0000${item.name || ""}`;
      let current = grouped.get(key);
      if (!current) {
        current = {
          ...item,
          slots: [],
        };
        grouped.set(key, current);
      }
      if (item.slot && !current.slots.includes(item.slot)) {
        current.slots.push(item.slot);
      }
    }
    return Array.from(grouped.values());
  }

  function renderMaterialRelationItem(item) {
    const block = document.createElement("div");
    block.className = "asset-related-item";

    const link = document.createElement("a");
    link.href = assetHref(item.rel);
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = item.rel;
    block.appendChild(link);

    const meta = document.createElement("div");
    meta.className = "asset-related-meta";
      meta.textContent = assetUiText("materialJson", { name: item.name });
    block.appendChild(meta);
    return block;
  }

  function renderTextureRelationItem(item) {
    const block = document.createElement("div");
    block.className = "asset-related-item";

    if (item.rel && ASSET_STATE.entryByRel.has(item.rel)) {
      block.appendChild(createAssetSelectLink(item.rel));
    } else if (item.rel) {
      const link = document.createElement("a");
      link.href = assetHref(item.rel);
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = item.rel;
      block.appendChild(link);
    } else {
      const label = document.createElement("div");
      label.textContent = item.name;
      block.appendChild(label);
    }

    const meta = document.createElement("div");
    meta.className = "asset-related-meta";
      meta.textContent = item.rel
      ? assetUiText("relationTextureResolved", {
          slots: (item.slots && item.slots.length ? item.slots : [item.slot]).join(", "),
          name: item.name,
        })
      : assetUiText("relationTextureUnresolved", {
          slots: (item.slots && item.slots.length ? item.slots : [item.slot]).join(", "),
          name: item.name,
        });
    block.appendChild(meta);
    return block;
  }

  function renderReferenceRelationItem(item) {
    const block = document.createElement("div");
    block.className = "asset-related-item";

    if (item.kind === "model" && item.rel && ASSET_STATE.entryByRel.has(item.rel)) {
      block.appendChild(createAssetSelectLink(item.rel));
    } else if (item.rel) {
      const link = document.createElement("a");
      link.href = assetHref(item.rel);
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = item.rel;
      block.appendChild(link);
    } else {
      const label = document.createElement("div");
      label.textContent = item.name || "(unknown)";
      block.appendChild(label);
    }

    const meta = document.createElement("div");
    meta.className = "asset-related-meta";
    if (item.kind === "material") {
      meta.textContent = assetUiText("relationMaterial", {
        slots: (item.slots && item.slots.length ? item.slots : [item.slot]).join(", "),
      });
    } else {
      meta.textContent = assetUiText("relationModel");
    }
    block.appendChild(meta);
    return block;
  }

  function createAssetSelectLink(rel) {
    const entry = ASSET_STATE.entryByRel.get(rel);
    const link = document.createElement("a");
    link.href = "#assets";
    link.textContent = rel;
    link.addEventListener("click", (ev) => {
      ev.preventDefault();
      if (!entry) return;
      selectAsset(entry, { scrollIntoView: true, variantRel: rel });
    });
    return link;
  }

  function renderImagePreview(entry) {
    const img = $("#asset-preview-image");
    const canvas = $("#asset-model-canvas");
    const placeholder = $("#asset-preview-placeholder");
    const note = $("#asset-preview-note");
    const modelWrap = $("#asset-model-stats-wrap");

    ASSET_STATE.viewer.model = null;
    modelWrap.hidden = true;
    $("#asset-model-stats").replaceChildren();

    canvas.hidden = true;
    img.hidden = false;
    placeholder.hidden = true;
    note.hidden = false;
    note.textContent = assetUiText("loadingImagePreview");

    img.onload = () => {
      note.textContent = assetUiText("imagePixels", {
        width: img.naturalWidth.toLocaleString(),
        height: img.naturalHeight.toLocaleString(),
      });
    };
    img.onerror = () => {
      img.hidden = true;
      placeholder.hidden = false;
      placeholder.textContent = assetUiText("imagePreviewUnavailable");
      note.textContent = assetUiText("rawLinkAvailable");
    };
    img.src = assetHref(entry.rel);
    img.alt = entry.name;
  }

  async function loadObjModel(rel) {
    let model = ASSET_STATE.modelCache.get(rel);
    if (model) return model;

    const res = await fetch(assetHref(rel));
    if (!res.ok) throw new Error(`OBJ HTTP ${res.status}`);
    const text = await res.text();
    model = parseObj(text);
    ASSET_STATE.modelCache.set(rel, model);
    return model;
  }

  function resolveReviewModelFile(activeVariant) {
    if (!activeVariant) return null;
    if (activeVariant.ext === "obj") return activeVariant;
    if (activeVariant.previewRel) {
      return ASSET_STATE.rawEntryByRel.get(activeVariant.previewRel) || null;
    }
    return null;
  }

  function renderModelStatGrid(stats) {
    const wrap = $("#asset-model-stats");
    const fragment = document.createDocumentFragment();
    for (const [label, value] of stats) {
      const block = document.createElement("div");
      block.className = "asset-model-stat";

      const statLabel = document.createElement("div");
      statLabel.className = "asset-model-stat-label";
      statLabel.textContent = label;
      block.appendChild(statLabel);

      const statValue = document.createElement("div");
      statValue.className = "asset-model-stat-value";
      statValue.textContent = value;
      block.appendChild(statValue);

      fragment.appendChild(block);
    }

    wrap.replaceChildren(fragment);
  }

  function renderObjModelStats(model, activeVariant, reviewVariant) {
    const stats = [
      [assetUiText("selectedLod"), activeVariant && activeVariant.lod !== null ? `LOD ${activeVariant.lod}` : activeVariant?.name || assetUiText("none")],
      [assetUiText("sampledPoints"), model.points.length.toLocaleString()],
      [assetUiText("vertices"), model.vertexCount.toLocaleString()],
      [assetUiText("faces"), model.faceCount.toLocaleString()],
      [assetUiText("objectsGroups"), model.objectCount.toLocaleString()],
    ];
    if (reviewVariant && reviewVariant.rel !== activeVariant?.rel) {
      stats.splice(1, 0, [assetUiText("factPreviewProxy"), reviewVariant.rel]);
    }
    renderModelStatGrid(stats);
  }

  function renderFbxSummaryStats(summary, activeVariant) {
    const stats = [
      [assetUiText("factSelectedRawFile"), activeVariant?.rel || assetUiText("none")],
      [assetUiText("fbxFormat"), summary.format || assetUiText("none")],
      [assetUiText("fbxVersion"), summary.version ? String(summary.version) : assetUiText("none")],
      [assetUiText("fbxNodes"), Number(summary.nodeCount || 0).toLocaleString()],
      [assetUiText("fbxModels"), Number(summary.counts?.Model || 0).toLocaleString()],
      [assetUiText("fbxGeometries"), Number(summary.counts?.Geometry || 0).toLocaleString()],
      [assetUiText("fbxMaterials"), Number(summary.counts?.Material || 0).toLocaleString()],
      [assetUiText("fbxTextures"), Number(summary.counts?.Texture || 0).toLocaleString()],
      [assetUiText("fbxAnimations"), Number(summary.counts?.AnimationStack || 0).toLocaleString()],
    ];
    if (activeVariant?.lod !== null) {
      stats.splice(1, 0, [assetUiText("factLod"), String(activeVariant.lod)]);
    }
    if (summary.sampleNames && summary.sampleNames.length) {
      stats.push([assetUiText("fbxSampleNames"), summary.sampleNames.join(", ")]);
    }
    renderModelStatGrid(stats);
  }

  async function renderModelPreview(entry) {
    const img = $("#asset-preview-image");
    const canvas = $("#asset-model-canvas");
    const placeholder = $("#asset-preview-placeholder");
    const note = $("#asset-preview-note");
    const modelWrap = $("#asset-model-stats-wrap");
    const activeVariant = getActiveModelFile(entry);

    img.hidden = true;
    canvas.hidden = true;
    placeholder.hidden = true;
    note.hidden = false;
    note.textContent = assetUiText("previewPlaceholder");
    modelWrap.hidden = true;
    ASSET_STATE.viewer.model = null;
    $("#asset-model-stats").replaceChildren();

    initModelViewer(canvas);

    const token = ++ASSET_STATE.detailToken;
    try {
      if (!activeVariant) throw new Error(assetUiText("noModelFile"));
      const reviewVariant = resolveReviewModelFile(activeVariant);

      if (reviewVariant && reviewVariant.ext === "obj") {
        try {
          canvas.hidden = false;
          placeholder.hidden = true;
          note.textContent = assetUiText("loadingObjPreview");

          const model = await loadObjModel(reviewVariant.rel);
          if (token !== ASSET_STATE.detailToken) return;

          ASSET_STATE.viewer.model = model;
          ASSET_STATE.viewer.rotationX = -0.35;
          ASSET_STATE.viewer.rotationY = 0.75;
          ASSET_STATE.viewer.zoom = 1;
          renderObjModelStats(model, activeVariant, reviewVariant);
          modelWrap.hidden = false;
          note.textContent = reviewVariant.rel === activeVariant.rel
            ? assetUiText("previewingModel", { name: activeVariant.name })
            : assetUiText("previewingModelViaObj", { name: activeVariant.name });
          queueModelRender();
          return;
        } catch (error) {
          if (activeVariant.ext !== "fbx") throw error;
          ASSET_STATE.viewer.model = null;
          canvas.hidden = true;
          placeholder.hidden = true;
        }
      }

      if (activeVariant.ext === "fbx") {
        placeholder.hidden = false;
        placeholder.textContent = assetUiText("previewPlaceholder");
        note.textContent = assetUiText("loadingFbxSummary");

        const summary = await loadFbxSummary(activeVariant.rel);
        if (token !== ASSET_STATE.detailToken) return;

        placeholder.textContent = assetUiText("fbxSummaryPlaceholder");
        renderFbxSummaryStats(summary, activeVariant);
        modelWrap.hidden = false;
        note.textContent = assetUiText("fbxSummaryLoaded");
        return;
      }

      throw new Error(assetUiText("objPreviewUnavailable"));
    } catch (error) {
      if (token !== ASSET_STATE.detailToken) return;
      canvas.hidden = true;
      placeholder.hidden = false;
      placeholder.textContent = activeVariant?.ext === "fbx"
        ? assetUiText("fbxSummaryUnavailable")
        : assetUiText("objPreviewUnavailable");
      note.textContent = String(error);
      ASSET_STATE.viewer.model = null;
      modelWrap.hidden = true;
    }
  }

  function initModelViewer(canvas) {
    if (ASSET_STATE.viewer.bound) return;
    ASSET_STATE.viewer.canvas = canvas;
    ASSET_STATE.viewer.ctx = canvas.getContext("2d");
    ASSET_STATE.viewer.bound = true;

    canvas.addEventListener("pointerdown", (ev) => {
      ASSET_STATE.viewer.dragging = true;
      ASSET_STATE.viewer.lastX = ev.clientX;
      ASSET_STATE.viewer.lastY = ev.clientY;
      canvas.setPointerCapture(ev.pointerId);
    });

    canvas.addEventListener("pointermove", (ev) => {
      if (!ASSET_STATE.viewer.dragging || !ASSET_STATE.viewer.model) return;
      const dx = ev.clientX - ASSET_STATE.viewer.lastX;
      const dy = ev.clientY - ASSET_STATE.viewer.lastY;
      ASSET_STATE.viewer.lastX = ev.clientX;
      ASSET_STATE.viewer.lastY = ev.clientY;
      ASSET_STATE.viewer.rotationY += dx * 0.01;
      ASSET_STATE.viewer.rotationX += dy * 0.01;
      queueModelRender();
    });

    const endDrag = () => {
      ASSET_STATE.viewer.dragging = false;
    };
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);
    canvas.addEventListener("pointerleave", endDrag);

    canvas.addEventListener("wheel", (ev) => {
      if (!ASSET_STATE.viewer.model) return;
      ev.preventDefault();
      const nextZoom = ASSET_STATE.viewer.zoom * (ev.deltaY > 0 ? 0.92 : 1.08);
      ASSET_STATE.viewer.zoom = clamp(nextZoom, 0.35, 4.5);
      queueModelRender();
    }, { passive: false });
  }

  function queueModelRender() {
    if (ASSET_STATE.activeView !== "assets") return;
    if (!ASSET_STATE.viewer.model || !ASSET_STATE.viewer.canvas || ASSET_STATE.viewer.renderQueued) return;
    ASSET_STATE.viewer.renderQueued = true;
    requestAnimationFrame(() => {
      ASSET_STATE.viewer.renderQueued = false;
      renderModelCanvas();
    });
  }

  function renderModelCanvas() {
    const { canvas, ctx, model } = ASSET_STATE.viewer;
    if (!canvas || !ctx || !model || canvas.hidden) return;

    const width = Math.max(1, canvas.clientWidth);
    const height = Math.max(1, canvas.clientHeight);
    const dpr = window.devicePixelRatio || 1;
    const pixelWidth = Math.max(1, Math.round(width * dpr));
    const pixelHeight = Math.max(1, Math.round(height * dpr));

    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    drawModelBackdrop(ctx, width, height);

    const projected = [];
    const rx = ASSET_STATE.viewer.rotationX;
    const ry = ASSET_STATE.viewer.rotationY;
    const cosX = Math.cos(rx);
    const sinX = Math.sin(rx);
    const cosY = Math.cos(ry);
    const sinY = Math.sin(ry);
    const cameraZ = 3.4;
    const scale = model.scale * ASSET_STATE.viewer.zoom;

    const sourceVertices = model.vertices.length ? model.vertices : model.points;
    for (const point of sourceVertices) {
      let x = (point[0] - model.center[0]) * scale;
      let y = (point[1] - model.center[1]) * scale;
      let z = (point[2] - model.center[2]) * scale;

      const xz = x * cosY - z * sinY;
      const zz = x * sinY + z * cosY;
      x = xz;
      z = zz;

      const yz = y * cosX - z * sinX;
      z = y * sinX + z * cosX;
      y = yz;

      const perspective = cameraZ / Math.max(0.35, cameraZ - z);
      projected.push({
        x,
        y,
        z,
        screenX: width * 0.5 + x * perspective * width * 0.28,
        screenY: height * 0.5 - y * perspective * width * 0.28,
        depth: cameraZ - z,
        perspective,
        radius: Math.max(0.7, perspective * 1.7),
      });
    }

    if (model.triangles.length && projected.length === model.vertices.length) {
      const lightDir = [0.35, 0.55, 1];
      const lightLen = Math.hypot(lightDir[0], lightDir[1], lightDir[2]) || 1;
      const faces = [];

      for (const triangle of model.triangles) {
        const a = projected[triangle[0]];
        const b = projected[triangle[1]];
        const c = projected[triangle[2]];
        if (!a || !b || !c) continue;
        if (a.depth <= 0.08 || b.depth <= 0.08 || c.depth <= 0.08) continue;

        const ux = b.x - a.x;
        const uy = b.y - a.y;
        const uz = b.z - a.z;
        const vx = c.x - a.x;
        const vy = c.y - a.y;
        const vz = c.z - a.z;
        const nx = uy * vz - uz * vy;
        const ny = uz * vx - ux * vz;
        const nz = ux * vy - uy * vx;
        const normalLen = Math.hypot(nx, ny, nz);
        if (normalLen <= 1e-6) continue;

        const screenArea = Math.abs(
          (b.screenX - a.screenX) * (c.screenY - a.screenY) -
          (b.screenY - a.screenY) * (c.screenX - a.screenX)
        );
        if (screenArea <= 0.08) continue;

        const light =
          Math.abs((nx * lightDir[0] + ny * lightDir[1] + nz * lightDir[2]) / (normalLen * lightLen));
        const facing = clamp((nz / normalLen + 1) * 0.5, 0, 1);
        const depth = clamp(((a.z + b.z + c.z) / 3 + 1.6) / 3.2, 0, 1);
        const intensity = clamp(0.22 + light * 0.42 + facing * 0.24 + depth * 0.12, 0.18, 0.95);

        faces.push({
          points: [a, b, c],
          z: (a.z + b.z + c.z) / 3,
          fill: `rgba(${Math.round(22 + intensity * 52)}, ${Math.round(84 + intensity * 78)}, ${Math.round(148 + intensity * 92)}, 0.9)`,
          stroke: `rgba(${Math.round(110 + intensity * 60)}, ${Math.round(170 + intensity * 50)}, 255, 0.3)`,
        });
      }

      if (faces.length) {
        const drawEdges = faces.length <= 12000;
        faces.sort((a, b) => a.z - b.z);
        for (const face of faces) {
          ctx.beginPath();
          ctx.moveTo(face.points[0].screenX, face.points[0].screenY);
          ctx.lineTo(face.points[1].screenX, face.points[1].screenY);
          ctx.lineTo(face.points[2].screenX, face.points[2].screenY);
          ctx.closePath();
          ctx.fillStyle = face.fill;
          ctx.fill();
          if (drawEdges) {
            ctx.strokeStyle = face.stroke;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
        return;
      }
    }

    projected.sort((a, b) => a.z - b.z);
    for (const point of projected) {
      const depth = clamp((point.z + 1.5) / 3.0, 0, 1);
      ctx.fillStyle = `rgba(108, 182, 255, ${0.16 + depth * 0.7})`;
      ctx.beginPath();
      ctx.arc(point.screenX, point.screenY, point.radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function drawModelBackdrop(ctx, width, height) {
    ctx.fillStyle = "#0b1015";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(108, 182, 255, 0.08)";
    ctx.lineWidth = 1;
    const step = Math.max(42, Math.round(width / 10));
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

    ctx.strokeStyle = "rgba(240, 163, 107, 0.22)";
    ctx.beginPath();
    ctx.moveTo(width * 0.5, 0);
    ctx.lineTo(width * 0.5, height);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, height * 0.5);
    ctx.lineTo(width, height * 0.5);
    ctx.stroke();
  }

  function parseObj(text) {
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

    const lines = text.split(/\r?\n/);
    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;
      if (line.startsWith("v ")) {
        const parts = line.split(/\s+/);
        if (parts.length < 4) continue;
        const x = Number(parts[1]);
        const y = Number(parts[2]);
        const z = Number(parts[3]);
        if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) continue;
        vertices.push([x, y, z]);
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (z < minZ) minZ = z;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
        if (z > maxZ) maxZ = z;
      } else if (line.startsWith("f ")) {
        faceCount += 1;
        const parts = line.split(/\s+/).slice(1);
        const face = [];
        for (const token of parts) {
          const indexText = token.split("/")[0];
          if (!indexText) continue;
          const rawIndex = Number(indexText);
          if (!Number.isInteger(rawIndex) || rawIndex === 0) continue;
          const resolved = rawIndex > 0 ? rawIndex - 1 : vertices.length + rawIndex;
          if (resolved < 0 || resolved >= vertices.length) continue;
          face.push(resolved);
        }
        if (face.length >= 3) {
          const triangleLimit = 60000;
          for (let i = 1; i + 1 < face.length && triangles.length < triangleLimit; i += 1) {
            const a = face[0];
            const b = face[i];
            const c = face[i + 1];
            if (a === b || b === c || a === c) continue;
            triangles.push([a, b, c]);
          }
        }
      } else if (line.startsWith("o ") || line.startsWith("g ")) {
        objectCount += 1;
      }
    }

    if (!vertices.length) {
      return {
        points: [],
        vertices: [],
        triangles: [],
        vertexCount: 0,
        faceCount,
        objectCount,
        center: [0, 0, 0],
        scale: 1,
      };
    }

    const pointLimit = 16000;
    const step = vertices.length > pointLimit ? Math.ceil(vertices.length / pointLimit) : 1;
    const points = [];
    for (let index = 0; index < vertices.length; index += step) {
      points.push(vertices[index]);
    }

    const spanX = maxX - minX;
    const spanY = maxY - minY;
    const spanZ = maxZ - minZ;
    const maxSpan = Math.max(spanX || 1, spanY || 1, spanZ || 1);

    return {
      points,
      vertices,
      triangles,
      vertexCount: vertices.length,
      faceCount,
      objectCount,
      center: [
        (minX + maxX) * 0.5 || 0,
        (minY + maxY) * 0.5 || 0,
        (minZ + maxZ) * 0.5 || 0,
      ],
      scale: 2 / maxSpan,
    };
  }

  async function loadFbxSummary(rel) {
    let summary = ASSET_STATE.fbxSummaryCache.get(rel);
    if (summary) return summary;

    const res = await fetch(assetHref(rel));
    if (!res.ok) throw new Error(`FBX HTTP ${res.status}`);
    summary = parseFbxSummary(await res.arrayBuffer());
    ASSET_STATE.fbxSummaryCache.set(rel, summary);
    return summary;
  }

  function parseFbxSummary(buffer) {
    const bytes = new Uint8Array(buffer);
    const ascii = new TextDecoder("ascii");
    const header = bytes.length >= 21 ? ascii.decode(bytes.slice(0, 21)) : "";
    if (header.startsWith("Kaydara FBX Binary")) {
      return parseBinaryFbxSummary(buffer);
    }
    return parseAsciiFbxSummary(new TextDecoder("utf-8").decode(bytes.slice(0, Math.min(bytes.length, 512000))));
  }

  function parseAsciiFbxSummary(text) {
    const summary = {
      format: "ASCII",
      version: 0,
      nodeCount: 0,
      counts: {},
      sampleNames: [],
    };

    const versionMatch = text.match(/FBXVersion:\s*(\d+)/);
    if (versionMatch) summary.version = Number(versionMatch[1]) || 0;

    const sampleSet = new Set();
    const nodeRe = /^\s*([A-Za-z][A-Za-z0-9_]+)\s*:/gm;
    let match;
    while ((match = nodeRe.exec(text))) {
      const name = match[1];
      summary.nodeCount += 1;
      summary.counts[name] = (summary.counts[name] || 0) + 1;
    }

    const sampleRe = /^\s*(Model|Geometry|Material|Texture|AnimationStack)\s*:\s*"([^"]+)"/gm;
    while ((match = sampleRe.exec(text)) && summary.sampleNames.length < 6) {
      const cleaned = cleanFbxSampleName(match[2]);
      if (!cleaned || sampleSet.has(cleaned)) continue;
      sampleSet.add(cleaned);
      summary.sampleNames.push(cleaned);
    }

    return summary;
  }

  function parseBinaryFbxSummary(buffer) {
    const bytes = new Uint8Array(buffer);
    const view = new DataView(buffer);
    const decoder = new TextDecoder("utf-8");
    const version = bytes.length >= 27 ? view.getUint32(23, true) : 0;
    const is64 = version >= 7500;
    const nullRecordLen = is64 ? 25 : 13;
    const summary = {
      format: "Binary",
      version,
      nodeCount: 0,
      counts: {},
      sampleNames: [],
    };
    const sampleSet = new Set();

    function addNode(name, propStrings) {
      if (!name) return;
      summary.nodeCount += 1;
      summary.counts[name] = (summary.counts[name] || 0) + 1;
      if (!["Model", "Geometry", "Material", "Texture", "AnimationStack"].includes(name)) return;
      for (const value of propStrings) {
        const cleaned = cleanFbxSampleName(value);
        if (!cleaned || sampleSet.has(cleaned)) continue;
        sampleSet.add(cleaned);
        summary.sampleNames.push(cleaned);
        if (summary.sampleNames.length >= 6) break;
      }
    }

    function isNullRecord(offset) {
      if (offset + nullRecordLen > bytes.length) return false;
      for (let index = 0; index < nullRecordLen; index += 1) {
        if (bytes[offset + index] !== 0) return false;
      }
      return true;
    }

    function readLength(offset) {
      return is64 ? Number(view.getBigUint64(offset, true)) : view.getUint32(offset, true);
    }

    function readProperty(offset) {
      if (offset >= bytes.length) return { nextOffset: bytes.length, value: "" };
      const type = String.fromCharCode(view.getUint8(offset));
      let cursor = offset + 1;
      let value = "";

      switch (type) {
        case "Y": cursor += 2; break;
        case "C": cursor += 1; break;
        case "I":
        case "F": cursor += 4; break;
        case "D":
        case "L": cursor += 8; break;
        case "R": {
          const length = view.getUint32(cursor, true);
          cursor += 4 + length;
          break;
        }
        case "S": {
          const length = view.getUint32(cursor, true);
          cursor += 4;
          const end = Math.min(bytes.length, cursor + length);
          value = decoder.decode(bytes.slice(cursor, end));
          cursor += length;
          break;
        }
        case "b":
        case "c":
        case "d":
        case "f":
        case "i":
        case "l": {
          const compressedLength = view.getUint32(cursor + 8, true);
          cursor += 12 + compressedLength;
          break;
        }
        default:
          throw new Error(`Unsupported FBX property type: ${type}`);
      }

      return { nextOffset: cursor, value };
    }

    function parseNode(offset) {
      if (isNullRecord(offset)) return { nextOffset: offset + nullRecordLen };

      let cursor = offset;
      const endOffset = readLength(cursor);
      cursor += is64 ? 8 : 4;
      const propertyCount = readLength(cursor);
      cursor += is64 ? 8 : 4;
      const propertyListLen = readLength(cursor);
      cursor += is64 ? 8 : 4;
      const nameLen = view.getUint8(cursor);
      cursor += 1;

      if (!endOffset || endOffset <= offset) {
        return { nextOffset: bytes.length };
      }

      const name = decoder.decode(bytes.slice(cursor, Math.min(bytes.length, cursor + nameLen)));
      cursor += nameLen;

      const propEnd = Math.min(bytes.length, cursor + propertyListLen);
      const propStrings = [];
      for (let index = 0; index < propertyCount && cursor < propEnd; index += 1) {
        const prop = readProperty(cursor);
        cursor = Math.min(prop.nextOffset, propEnd);
        if (prop.value) propStrings.push(prop.value);
      }
      cursor = propEnd;

      addNode(name, propStrings);

      const finalOffset = Math.min(bytes.length, endOffset);
      while (cursor + nullRecordLen <= finalOffset) {
        if (isNullRecord(cursor)) {
          cursor += nullRecordLen;
          break;
        }
        const child = parseNode(cursor);
        if (!child || child.nextOffset <= cursor) break;
        cursor = child.nextOffset;
      }

      return { nextOffset: Math.max(cursor, finalOffset) };
    }

    try {
      let cursor = 27;
      while (cursor + nullRecordLen <= bytes.length) {
        if (isNullRecord(cursor)) break;
        const node = parseNode(cursor);
        if (!node || node.nextOffset <= cursor) break;
        cursor = node.nextOffset;
      }
    } catch (error) {
      if (!summary.nodeCount) throw error;
    }

    return summary;
  }

  function cleanFbxSampleName(value) {
    return String(value || "")
      .replace(/\u0000/g, " ")
      .replace(/^[A-Za-z]+::/, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function assetHref(relPath) {
    return exportFullHref(relPath, ASSET_STATE.sourceRoots, ASSET_STATE.exportRoot);
  }

  function countBy(arr, fn) {
    const out = {};
    for (const item of arr) {
      const key = fn(item);
      out[key] = (out[key] || 0) + 1;
    }
    return out;
  }

  function formatBytes(bytes) {
    const units = ["B", "KB", "MB", "GB"];
    let value = Number(bytes || 0);
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex += 1;
    }
    const digits = value >= 100 || unitIndex === 0 ? 0 : value >= 10 ? 1 : 2;
    return `${value.toFixed(digits)} ${units[unitIndex]}`;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  async function copyTextToClipboard(text) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (_error) {
      // Fall through to the legacy path.
    }

    const input = document.createElement("textarea");
    input.value = text;
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.focus();
    input.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (_error) {
      ok = false;
    }
    input.remove();
    return ok;
  }

  function init() {
    setAssetUiLocale(resolveInitialUiLocale(), { refresh: false });
    bindViewTabs();
    bindAssetEvents();
    window.addEventListener("webui:ui-locale-changed", (event) => {
      setAssetUiLocale(event.detail && event.detail.locale);
    });
    setFiltersCollapsed(resolveInitialFiltersCollapsed(), { persist: false });
    setActiveView(resolveViewFromHash(), { updateHash: false });
  }

  init();
})();
