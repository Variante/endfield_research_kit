(() => {
  const ROW_HEIGHT = 66;
  const OVERSCAN_PX = 260;
  const INDEX_PATH = (language) => `data/lang/${encodeURIComponent(language)}/audio/index.json`;
  const PANE_STORAGE_KEY = "webui_audio_splitter_width";
  const FILTER_HEIGHT_STORAGE_KEY = "webui_filter_splitter_height_audio";
  const FILTER_PANEL_STORAGE_KEY = "audio_browser_filters_collapsed";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";

  const TEXT = {
    en: {
      title: "Audio System",
      countLabel: "records",
      events: "Events",
      media: "Media",
      hideFilters: "Hide filters",
      showFilters: "Show filters",
      reset: "Reset filters",
      basicFilters: "Basic filters",
      search: "Search event / media / bank / category",
      category: "Category",
      context: "Context",
      relation: "Media relation",
      scope: "Scope",
      source: "Source",
      shown: "shown",
      event: "event",
      mediaItem: "media",
      loading: "Loading audio-system data…",
      loadingEvents: "Loading audio event shards…",
      loadingMedia: "Loading audio media shards…",
      loadError: "Audio-system data could not be loaded.",
      shardError: "This audio dataset could not be loaded.",
      retry: "Retry",
      noMatches: "No audio records match these filters.",
      noData: "No records were emitted for this audio dataset.",
      runtimeSystem: "Runtime system",
      runtimeBoundary: "Evidence boundary",
      runtimeComponents: "Runtime components",
      hircInventory: "Wwise HIRC inventory",
      corpus: "Corpus",
      selectRecord: "Select an event or media record from the left.",
      overview: "Overview",
      details: "Details",
      playableMedia: "Playable media",
      noPlayableMedia: "No browser-playable media path is attached to this record.",
      mediaIds: "Media IDs",
      eventIds: "Event IDs",
      actions: "Actions / objects",
      recordType: "Record type",
      playbackEvent: "Playback event",
      controlEvent: "Control event",
      decodedMedia: "Decoded media",
      contextGroups: "Semantic contexts",
      contextEvidence: "Context evidence",
      contextGameplay: "Gameplay",
      contextCutscene: "Cutscene / story",
      contextAnimation: "Animation",
      contextSharedPlayableAnimation: "Shared playable-character animation",
      contextFootstepSystem: "Footstep / material system",
      contextAuthoredConfig: "Authored config",
      contextManagedRuntime: "Managed runtime",
      contextDialogMedia: "Dialog media",
      contextNone: "No linked authored context",
      relationRuntimeSelected: "Typed runtime-selected branches",
      relationMultipleUnknown: "Multiple possible files; relation unresolved",
      relationSingle: "Single possible file",
      relationNoDecodedMedia: "Wwise event; no decoded media leaf",
      relationUnresolvedEvent: "Event unresolved in Wwise",
      relationEventCandidate: "Wwise event media leaf",
      relationDirectDialogMedia: "Direct dialog media",
      relationUnlinkedMedia: "No recovered event relation",
      relationPartialGraph: "Partial typed graph",
      relationMultipleRoots: "Multiple Play roots",
      relationRandom: "Random alternatives",
      relationSequence: "Sequence items",
      relationSwitch: "Switch / State branches",
      relationLayer: "Layer branches",
      relationDirectSound: "Direct Sound leaf",
      possibleMedia: "Possible media",
      playRoots: "Play roots",
      typedTraversal: "Typed traversal",
      selectorEvidence: "Selector evidence",
      uniqueContent: "Unique decoded content",
      equivalentContent: "Content-equivalent leaves",
      rawRecord: "Raw record",
      id: "ID",
      hash: "Hash",
      bank: "Bank",
      path: "Path",
      format: "Format",
      bytes: "Bytes",
      generated: "Generated",
      language: "Language",
      unknown: "unknown",
    },
    zh: {
      title: "\u97f3\u9891\u7cfb\u7edf",
      countLabel: "\u6761\u8bb0\u5f55",
      events: "\u4e8b\u4ef6",
      media: "\u5a92\u4f53",
      hideFilters: "\u9690\u85cf\u7b5b\u9009",
      showFilters: "\u663e\u793a\u7b5b\u9009",
      reset: "\u91cd\u7f6e\u7b5b\u9009",
      basicFilters: "\u57fa\u7840\u7b5b\u9009",
      search: "\u641c\u7d22\u4e8b\u4ef6 / \u5a92\u4f53 / \u97f3\u9891\u5305 / \u5206\u7c7b",
      category: "\u5206\u7c7b",
      context: "\u4e0a\u4e0b\u6587",
      relation: "\u5a92\u4f53\u5173\u7cfb",
      scope: "\u8303\u56f4",
      source: "\u6765\u6e90",
      shown: "\u5df2\u663e\u793a",
      event: "\u4e8b\u4ef6",
      mediaItem: "\u5a92\u4f53",
      loading: "\u6b63\u5728\u52a0\u8f7d\u97f3\u9891\u7cfb\u7edf\u6570\u636e…",
      loadingEvents: "\u6b63\u5728\u52a0\u8f7d\u97f3\u9891\u4e8b\u4ef6\u5206\u7247…",
      loadingMedia: "\u6b63\u5728\u52a0\u8f7d\u97f3\u9891\u5a92\u4f53\u5206\u7247…",
      loadError: "\u65e0\u6cd5\u52a0\u8f7d\u97f3\u9891\u7cfb\u7edf\u6570\u636e\u3002",
      shardError: "\u65e0\u6cd5\u52a0\u8f7d\u8be5\u97f3\u9891\u6570\u636e\u96c6\u3002",
      retry: "\u91cd\u8bd5",
      noMatches: "\u6ca1\u6709\u97f3\u9891\u8bb0\u5f55\u7b26\u5408\u5f53\u524d\u7b5b\u9009\u3002",
      noData: "\u8be5\u97f3\u9891\u6570\u636e\u96c6\u6ca1\u6709\u751f\u6210\u8bb0\u5f55\u3002",
      runtimeSystem: "\u8fd0\u884c\u65f6\u7cfb\u7edf",
      runtimeBoundary: "\u8bc1\u636e\u8fb9\u754c",
      runtimeComponents: "\u8fd0\u884c\u65f6\u7ec4\u4ef6",
      hircInventory: "Wwise HIRC \u5e93\u5b58",
      corpus: "\u6570\u636e\u96c6",
      selectRecord: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u4e2a\u4e8b\u4ef6\u6216\u5a92\u4f53\u8bb0\u5f55\u3002",
      overview: "\u6982\u89c8",
      details: "\u8be6\u7ec6\u4fe1\u606f",
      playableMedia: "\u53ef\u64ad\u653e\u5a92\u4f53",
      noPlayableMedia: "\u8be5\u8bb0\u5f55\u672a\u9644\u52a0\u6d4f\u89c8\u5668\u53ef\u64ad\u653e\u7684\u5a92\u4f53\u8def\u5f84\u3002",
      mediaIds: "\u5a92\u4f53 ID",
      eventIds: "\u4e8b\u4ef6 ID",
      actions: "\u52a8\u4f5c / \u5bf9\u8c61",
      recordType: "\u8bb0\u5f55\u7c7b\u578b",
      playbackEvent: "\u64ad\u653e\u4e8b\u4ef6",
      controlEvent: "\u63a7\u5236\u4e8b\u4ef6",
      decodedMedia: "\u5df2\u89e3\u7801\u5a92\u4f53",
      contextGroups: "\u8bed\u4e49\u4e0a\u4e0b\u6587",
      contextEvidence: "\u4e0a\u4e0b\u6587\u8bc1\u636e",
      contextGameplay: "\u73a9\u6cd5",
      contextCutscene: "\u8fc7\u573a / \u5267\u60c5",
      contextAnimation: "\u52a8\u753b",
      contextSharedPlayableAnimation: "\u53ef\u73a9\u89d2\u8272\u5171\u7528\u52a8\u753b",
      contextFootstepSystem: "\u811a\u6b65 / \u6750\u8d28\u7cfb\u7edf",
      contextAuthoredConfig: "\u914d\u7f6e\u8868",
      contextManagedRuntime: "\u6258\u7ba1\u8fd0\u884c\u65f6",
      contextDialogMedia: "\u5bf9\u8bdd\u5a92\u4f53",
      contextNone: "\u65e0\u5df2\u94fe\u63a5\u7684\u521b\u4f5c\u4e0a\u4e0b\u6587",
      relationRuntimeSelected: "\u7c7b\u578b\u5316\u8fd0\u884c\u65f6\u5206\u652f",
      relationMultipleUnknown: "\u591a\u4e2a\u53ef\u80fd\u6587\u4ef6\uff0c\u5173\u7cfb\u672a\u89e3\u6790",
      relationSingle: "\u5355\u4e00\u53ef\u80fd\u6587\u4ef6",
      relationNoDecodedMedia: "Wwise \u4e8b\u4ef6\uff0c\u65e0\u5df2\u89e3\u7801\u5a92\u4f53\u53f6",
      relationUnresolvedEvent: "\u4e8b\u4ef6\u672a\u5728 Wwise \u4e2d\u89e3\u6790",
      relationEventCandidate: "Wwise \u4e8b\u4ef6\u5a92\u4f53\u53f6",
      relationDirectDialogMedia: "\u76f4\u63a5\u5bf9\u8bdd\u5a92\u4f53",
      relationUnlinkedMedia: "\u65e0\u5df2\u6062\u590d\u4e8b\u4ef6\u5173\u7cfb",
      relationPartialGraph: "\u90e8\u5206\u7c7b\u578b\u5316\u56fe",
      relationMultipleRoots: "\u591a\u4e2a Play \u6839",
      relationRandom: "\u968f\u673a\u5907\u9009",
      relationSequence: "\u5e8f\u5217\u9879",
      relationSwitch: "Switch / State \u5206\u652f",
      relationLayer: "Layer \u5206\u652f",
      relationDirectSound: "\u76f4\u63a5 Sound \u53f6",
      possibleMedia: "\u53ef\u80fd\u5a92\u4f53",
      playRoots: "Play \u6839",
      typedTraversal: "\u7c7b\u578b\u5316\u904d\u5386",
      selectorEvidence: "\u9009\u62e9\u5668\u8bc1\u636e",
      uniqueContent: "\u552f\u4e00\u89e3\u7801\u5185\u5bb9",
      equivalentContent: "\u5185\u5bb9\u7b49\u4ef7\u53f6",
      rawRecord: "\u539f\u59cb\u8bb0\u5f55",
      id: "ID",
      hash: "\u54c8\u5e0c",
      bank: "\u97f3\u9891\u5305",
      path: "\u8def\u5f84",
      format: "\u683c\u5f0f",
      bytes: "\u5b57\u8282",
      generated: "\u751f\u6210\u65f6\u95f4",
      language: "\u8bed\u8a00",
      unknown: "\u672a\u77e5",
    },
  };

  const state = {
    initialized: false,
    container: null,
    language: "CN",
    uiLocale: "zh",
    index: null,
    indexPromise: null,
    indexController: null,
    loadToken: 0,
    datasets: { events: null, media: null },
    datasetPromises: { events: null, media: null },
    datasetControllers: { events: [], media: [] },
    mode: "events",
    filtered: [],
    rows: [],
    selected: null,
    query: "",
    filters: { categories: new Set(), contexts: new Set(), relations: new Set(), scopes: new Set(), sources: new Set() },
    eventTaxonomyById: new Map(),
    eventDetailCache: new Map(),
    eventDetailPromises: new Map(),
    filterPanel: null,
    renderFrame: 0,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const locale = () => String(window.WEBUI_UI_LOCALE || state.uiLocale || document.documentElement.lang || "zh").toLowerCase().startsWith("en") ? "en" : "zh";
  const t = (key) => (TEXT[locale()] || TEXT.en)[key] || TEXT.en[key] || key;
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const normalize = (value) => String(value ?? "").trim();
  const normalizeLower = (value) => normalize(value).toLowerCase();
  const asArray = (value) => Array.isArray(value) ? value : (value === undefined || value === null || value === "" ? [] : [value]);
  const isMobileLayout = () => !!window.matchMedia?.(MOBILE_LAYOUT_QUERY).matches;
  const parsePixels = (value, fallback = 0) => {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  };

  function currentLanguage() {
    return String($("#language")?.value || state.language || "CN").toUpperCase();
  }

  function formatNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number.toLocaleString() : normalize(value);
  }

  function formatBytes(value) {
    let bytes = Number(value);
    if (!Number.isFinite(bytes) || bytes < 0) return normalize(value);
    const units = ["B", "KB", "MB", "GB"];
    let unit = 0;
    while (bytes >= 1024 && unit < units.length - 1) {
      bytes /= 1024;
      unit += 1;
    }
    const digits = unit === 0 || bytes >= 100 ? 0 : bytes >= 10 ? 1 : 2;
    return `${bytes.toFixed(digits)} ${units[unit]}`;
  }

  function recordId(record, kind = state.mode) {
    const raw = kind === "events"
      ? (record?.eventId ?? record?.id ?? record?.name ?? record?.eventHash ?? record?.hash)
      : (record?.mediaId ?? record?.id ?? record?.name ?? record?.rel ?? record?.src);
    return normalize(raw);
  }

  function recordTitle(record, kind = state.mode) {
    if (kind === "events") return normalize(record?.eventName ?? record?.name ?? record?.eventId ?? record?.id ?? record?.eventHash) || t("unknown");
    return normalize(record?.name ?? record?.title ?? record?.mediaId ?? record?.id ?? fileName(record?.rel ?? record?.path ?? record?.src)) || t("unknown");
  }

  function recordCategory(record) {
    return normalize(record?.eventCategory ?? record?.audioCategory ?? record?.category ?? record?.kind) || t("unknown");
  }

  function recordScope(record) {
    const direct = normalize(record?.audioScope ?? record?.scope ?? record?.storageRoot);
    if (direct) return direct;
    const values = [...new Set(asArray(record?.media).map((row) => normalize(row?.audioScope ?? row?.storageRoot)).filter(Boolean))];
    return values.length === 1 ? values[0] : values.length > 1 ? "mixed" : t("unknown");
  }

  function recordSource(record) {
    const direct = normalize(record?.sourceBlockLabel ?? record?.sourceBlock ?? record?.sourceBank ?? record?.source);
    if (direct) return direct;
    const evidenceSource = asArray(record?.evidence).map((row) => normalize(row?.source)).find(Boolean);
    if (evidenceSource) return evidenceSource;
    const mediaSource = asArray(record?.media).map((row) => normalize(row?.sourceBlockLabel ?? row?.sourceBlock ?? row?.sourceBank)).find(Boolean);
    return mediaSource || t("unknown");
  }

  const CONTEXT_LABEL_KEYS = {
    gameplay: "contextGameplay",
    cutscene: "contextCutscene",
    animation: "contextAnimation",
    sharedPlayableAnimation: "contextSharedPlayableAnimation",
    footstepSystem: "contextFootstepSystem",
    authoredConfig: "contextAuthoredConfig",
    managedRuntime: "contextManagedRuntime",
    dialogMedia: "contextDialogMedia",
    none: "contextNone",
  };

  const RELATION_LABEL_KEYS = {
    runtimeSelected: "relationRuntimeSelected",
    multipleUnknown: "relationMultipleUnknown",
    single: "relationSingle",
    noDecodedMedia: "relationNoDecodedMedia",
    unresolvedEvent: "relationUnresolvedEvent",
    eventCandidate: "relationEventCandidate",
    directDialogMedia: "relationDirectDialogMedia",
    unlinkedMedia: "relationUnlinkedMedia",
    partialGraph: "relationPartialGraph",
    multipleRoots: "relationMultipleRoots",
    randomAlternative: "relationRandom",
    sequenceItem: "relationSequence",
    switchCandidate: "relationSwitch",
    layerChild: "relationLayer",
    directSound: "relationDirectSound",
  };

  function taxonomyLabel(value) {
    return t(CONTEXT_LABEL_KEYS[value] || RELATION_LABEL_KEYS[value] || value);
  }

  function recordType(record, kind) {
    if (kind === "media") return "decodedMedia";
    return recordCategory(record) === "control" ? "controlEvent" : "playbackEvent";
  }

  function contextGroup(kind) {
    if (["characterSkill", "enemySkill"].includes(kind)) return "gameplay";
    if (kind === "cutsceneTimeline") return "cutscene";
    if (["characterAnimation", "enemyAnimation"].includes(kind)) return "animation";
    if (["table", "tableEventHash"].includes(kind)) return "authoredConfig";
    if (kind === "binaryManagedLiteral") return "managedRuntime";
    return "";
  }

  function recordContextTags(record, kind) {
    const tags = new Set(asArray(record?.contextGroups).filter(Boolean));
    for (const context of asArray(record?.contexts)) {
      if (!context || typeof context !== "object") continue;
      const group = contextGroup(normalize(context.kind));
      if (group) tags.add(group);
    }
    if (Number(record?.playableCharacterAnimationOwnerCount || 0) > 1 || record?.animationContextScope === "sharedPlayableCharacters") {
      tags.add("sharedPlayableAnimation");
    }
    if (asArray(record?.animationFunctions).includes("OnCustomFootStep")) tags.add("footstepSystem");
    if (kind === "media") {
      if (record?.audioDialogKey || record?.audioDialogPath) tags.add("dialogMedia");
      for (const eventId of asArray(record?.eventIds)) {
        for (const tag of state.eventTaxonomyById.get(normalizeLower(eventId)) || []) tags.add(tag);
      }
    }
    if (!tags.size) tags.add("none");
    return [...tags];
  }

  function recordRelationTags(record, kind) {
    if (kind === "media") {
      if (record?.audioDialogKey || record?.audioDialogPath) return ["directDialogMedia"];
      if (asArray(record?.eventIds).length || Number(record?.eventCount) > 0) return ["eventCandidate"];
      return ["unlinkedMedia"];
    }
    const evidence = asArray(record?.evidence).filter((value) => value && typeof value === "object");
    const foundInWwise = record?.foundInWwise === true || (record?.foundInWwise !== false && evidence.length > 0);
    const candidates = Number(record?.possibleMediaCount ?? record?.candidateCount ?? record?.resolvedMediaCount ?? record?.mediaCount)
      || asArray(record?.media).length;
    if (!foundInWwise) return ["unresolvedEvent"];
    if (!candidates) return ["noDecodedMedia"];
    const tags = [];
    if (record?.traversalStatus === "partial") tags.push("partialGraph");
    if (Number(record?.playRootCount) > 1) tags.push("multipleRoots");
    for (const relation of asArray(record?.mediaRelationTypes)) {
      if (RELATION_LABEL_KEYS[relation]) tags.push(relation);
    }
    if (asArray(record?.selectionContainerTypes).length && !tags.some((value) => ["randomAlternative", "sequenceItem", "switchCandidate", "layerChild"].includes(value))) tags.push("runtimeSelected");
    if (!tags.length) tags.push(candidates === 1 ? "single" : "multipleUnknown");
    return [...new Set(tags)];
  }

  function recordMeta(record, kind = state.mode, taxonomy = {}) {
    const parts = [t(taxonomy.objectType || recordType(record, kind)), recordCategory(record)];
    const contexts = asArray(taxonomy.contextTags).filter((value) => value !== "none");
    if (contexts.length) parts.push(contexts.map(taxonomyLabel).join(" + "));
    const relations = asArray(taxonomy.relationTags);
    if (relations.length) parts.push(relations.slice(0, 2).map(taxonomyLabel).join(" + "));
    if (kind === "events") {
      const count = Number(record?.possibleMediaCount ?? record?.resolvedMediaCount ?? record?.mediaCount ?? record?.candidateCount)
        || asArray(record?.mediaIds).length
        || asArray(record?.media).length;
      if (count) parts.push(`${formatNumber(count)} ${t("media")}`);
    } else if (record?.bytes !== undefined) {
      parts.push(formatBytes(record.bytes));
    }
    return [...new Set(parts.filter(Boolean))].join(" · ");
  }

  function searchText(record, kind, taxonomy = {}) {
    const values = [
      recordTitle(record, kind), recordId(record, kind), recordCategory(record), recordScope(record), recordSource(record),
      record?.eventHash, record?.mediaId, record?.bankId, record?.bank, record?.rel, record?.path, record?.src,
      ...asArray(record?.eventIds), ...asArray(record?.mediaIds), ...asArray(record?.actionIds), ...asArray(record?.visitedObjectIds),
      ...asArray(record?.contextSearch), ...asArray(record?.bankPackages),
      ...asArray(taxonomy.contextTags).flatMap((value) => [value, taxonomyLabel(value)]),
      ...asArray(taxonomy.relationTags).flatMap((value) => [value, taxonomyLabel(value)]),
      ...asArray(record?.contexts).flatMap((context) => context && typeof context === "object" ? [
        context.kind, context.ownerId, context.groupId, context.storyKey, context.table, context.path,
        context.semanticRole, context.confidence, context.animationOwnershipScope, context.possibleMediaScope,
        context.clipReachability, ...asArray(context.skillIds), ...asArray(context.actionKinds),
        ...asArray(context.animationFunctions), ...asArray(context.animationClipContexts), ...asArray(context.animationClips),
      ] : []),
    ];
    return values.filter((value) => value !== undefined && value !== null).join("\n").toLowerCase();
  }

  function normalizeRecord(record, kind, index) {
    const raw = record && typeof record === "object" ? record : { id: record };
    const contextTags = recordContextTags(raw, kind);
    const relationTags = recordRelationTags(raw, kind);
    const objectType = recordType(raw, kind);
    const taxonomy = { contextTags, relationTags, objectType };
    return {
      raw,
      kind,
      key: recordId(raw, kind) || `${kind}-${index}`,
      title: recordTitle(raw, kind),
      category: recordCategory(raw),
      scope: recordScope(raw),
      source: recordSource(raw),
      contextTags,
      relationTags,
      objectType,
      meta: recordMeta(raw, kind, taxonomy),
      search: searchText(raw, kind, taxonomy),
    };
  }

  function rebuildEventTaxonomy(records) {
    state.eventTaxonomyById = new Map();
    for (const record of records || []) {
      const keys = [recordId(record.raw, "events"), record.raw?.name, record.raw?.eventId, record.raw?.id]
        .map(normalizeLower).filter(Boolean);
      for (const key of keys) state.eventTaxonomyById.set(key, record.contextTags || ["none"]);
    }
  }

  function dedupeRecords(records, kind) {
    const seen = new Set();
    const output = [];
    for (const [index, record] of records.entries()) {
      const normalized = normalizeRecord(record, kind, index);
      let key = normalized.key;
      if (seen.has(key)) key = `${key}#${index}`;
      seen.add(key);
      normalized.key = key;
      output.push(normalized);
    }
    return output;
  }

  function recordsFromPayload(payload, kind) {
    if (Array.isArray(payload)) return payload;
    if (!payload || typeof payload !== "object") return [];
    for (const key of [kind, "entries", "records", "items", "data"]) {
      if (Array.isArray(payload[key])) return payload[key];
    }
    return [];
  }

  function shardSpecs(value) {
    if (!value) return [];
    if (typeof value === "string") return [{ path: value }];
    if (Array.isArray(value)) return value.flatMap(shardSpecs);
    if (typeof value !== "object") return [];
    const path = value.path || value.file || value.url || value.src;
    if (path) return [{ ...value, path: String(path) }];
    for (const key of ["files", "parts", "shards"]) {
      if (value[key]) return shardSpecs(value[key]);
    }
    return [];
  }

  function shardUrl(path, indexPath) {
    const value = normalize(path).replace(/\\/g, "/");
    if (!value) return "";
    if (/^(?:https?:)?\/\//i.test(value) || value.startsWith("/") || value.startsWith("data/")) return value;
    return new URL(value, new URL(indexPath, window.location.href)).toString();
  }

  async function ensureEventDetail(record) {
    const shard = normalize(record?.raw?.detailShard);
    if (!shard || record?.raw?._detailLoaded) return record?.raw;
    let records = state.eventDetailCache.get(shard);
    if (!records) {
      let promise = state.eventDetailPromises.get(shard);
      if (!promise) {
        const token = state.loadToken;
        const url = shardUrl(shard, INDEX_PATH(state.language));
        promise = fetch(url).then((response) => {
          if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
          return response.json();
        }).then((payload) => {
          if (token !== state.loadToken) return new Map();
          const rows = new Map(recordsFromPayload(payload, "events").map((row) => [normalizeLower(recordId(row, "events")), row]));
          state.eventDetailCache.set(shard, rows);
          return rows;
        }).finally(() => state.eventDetailPromises.delete(shard));
        state.eventDetailPromises.set(shard, promise);
      }
      records = await promise;
    }
    const detail = records?.get(normalizeLower(recordId(record.raw, "events")));
    if (!detail) return record.raw;
    record.raw = { ...record.raw, ...detail, _detailLoaded: true };
    record.contextTags = recordContextTags(record.raw, record.kind);
    record.relationTags = recordRelationTags(record.raw, record.kind);
    record.meta = recordMeta(record.raw, record.kind, record);
    record.search = searchText(record.raw, record.kind, record);
    if (state.selected === record) renderDetail();
    return record.raw;
  }

  function abortDataset(kind) {
    for (const controller of state.datasetControllers[kind] || []) controller.abort();
    state.datasetControllers[kind] = [];
    state.datasetPromises[kind] = null;
  }

  function abortAll() {
    state.indexController?.abort();
    abortDataset("events");
    abortDataset("media");
  }

  async function ensureDataset(kind, { token = state.loadToken, force = false, progressBase = 0, progressSpan = 1 } = {}) {
    if (!force && state.datasets[kind]) return state.datasets[kind];
    if (!force && state.datasetPromises[kind]) return state.datasetPromises[kind];
    abortDataset(kind);

    const inline = recordsFromPayload(state.index?.[kind], kind);
    const specs = shardSpecs(state.index?.shards?.[kind]);
    if (!specs.length) {
      const records = dedupeRecords(inline, kind);
      if (kind === "events") rebuildEventTaxonomy(records);
      state.datasets[kind] = records;
      return records;
    }

    const indexPath = INDEX_PATH(state.language);
    const progress = specs.map(() => 0);
    const controllers = specs.map(() => new AbortController());
    state.datasetControllers[kind] = controllers;
    const label = t(kind === "events" ? "loadingEvents" : "loadingMedia");
    const updateProgress = () => {
      const ratio = progress.reduce((total, value) => total + value, 0) / Math.max(1, progress.length);
      window.WebUI?.updateLoader?.("audio", progressBase + ratio * progressSpan, label);
    };

    const promise = Promise.all(specs.map(async (spec, index) => {
      const url = shardUrl(spec.path, indexPath);
      if (!url) return [];
      const response = await window.WebUI.fetchWithProgress(url, {
        signal: controllers[index].signal,
        cache: force ? "reload" : "default",
        onProgress: (ratio) => {
          if (ratio !== null && Number.isFinite(ratio)) progress[index] = Math.max(progress[index], Math.min(0.98, ratio));
          updateProgress();
        },
      });
      if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
      const payload = await response.json();
      progress[index] = 1;
      updateProgress();
      return recordsFromPayload(payload, kind);
    })).then((parts) => {
      if (token !== state.loadToken) return null;
      const records = dedupeRecords([...inline, ...parts.flat()], kind);
      if (kind === "events") rebuildEventTaxonomy(records);
      state.datasets[kind] = records;
      return records;
    }).finally(() => {
      if (token === state.loadToken) {
        state.datasetPromises[kind] = null;
        state.datasetControllers[kind] = [];
      }
    });
    state.datasetPromises[kind] = promise;
    return promise;
  }

  async function load(language = currentLanguage(), { force = false } = {}) {
    init();
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && state.index && state.language === nextLanguage && state.datasets.events) return state.index;
    if (!force && state.indexPromise && state.language === nextLanguage) return state.indexPromise;

    abortAll();
    const token = ++state.loadToken;
    state.language = nextLanguage;
    state.mode = "events";
    state.index = null;
    state.datasets = { events: null, media: null };
    state.datasetPromises = { events: null, media: null };
    state.eventTaxonomyById = new Map();
    state.eventDetailCache = new Map();
    state.eventDetailPromises = new Map();
    state.selected = null;
    state.indexController = new AbortController();
    resetFilters({ render: false });
    syncModeButtons();
    renderLoadingList();
    renderDetail();
    window.WebUI?.clearShellStatus?.("audio");
    window.WebUI?.setViewBusy?.("audio", true);
    window.WebUI?.showLoader?.("audio", t("loading"));

    const promise = (async () => {
      try {
        const path = INDEX_PATH(nextLanguage);
        const response = await window.WebUI.fetchWithProgress(path, {
          signal: state.indexController.signal,
          cache: force ? "reload" : "default",
          onProgress: (ratio) => window.WebUI?.updateLoader?.("audio", ratio === null ? null : ratio * 0.25, t("loading")),
        });
        if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
        const payload = await response.json();
        if (token !== state.loadToken) return null;
        state.index = payload && typeof payload === "object" ? payload : {};
        applyIndexHeader();
        renderDetail();
        await ensureDataset("events", { token, force, progressBase: 0.25, progressSpan: 0.75 });
        if (token !== state.loadToken) return null;
        buildFilterChips();
        applyFilters({ resetScroll: true });
        applyRequestedSelection();
        window.WebUI?.updateLoader?.("audio", 1, t("loadingEvents"));
        return state.index;
      } catch (error) {
        if (token !== state.loadToken || error?.name === "AbortError") return null;
        renderLoadError(error, { index: true });
        throw error;
      } finally {
        if (token === state.loadToken) {
          state.indexPromise = null;
          state.indexController = null;
          window.WebUI?.setViewBusy?.("audio", false);
          window.WebUI?.hideLoader?.("audio");
        }
      }
    })();
    state.indexPromise = promise;
    return promise;
  }

  async function switchMode(kind) {
    if (!["events", "media"].includes(kind) || state.mode === kind) return;
    state.mode = kind;
    state.selected = null;
    resetFilters({ render: false });
    syncModeButtons();
    renderLoadingList();
    renderDetail();
    clearSelectionFromUrl();
    if (state.datasets[kind]) {
      buildFilterChips();
      applyFilters({ resetScroll: true });
      return;
    }
    window.WebUI?.setViewBusy?.("audio", true);
    window.WebUI?.showLoader?.("audio", t(kind === "events" ? "loadingEvents" : "loadingMedia"));
    try {
      const records = await ensureDataset(kind, { token: state.loadToken });
      if (state.mode !== kind || !records) return;
      buildFilterChips();
      applyFilters({ resetScroll: true });
    } catch (error) {
      if (error?.name !== "AbortError") renderLoadError(error, { index: false });
    } finally {
      window.WebUI?.setViewBusy?.("audio", false);
      window.WebUI?.hideLoader?.("audio");
    }
  }

  function renderShell() {
    if (!state.container) return;
    state.container.innerHTML = `
      <div class="audio-shell">
        <aside id="audio-left">
          <header>
            <h1 id="audio-title"></h1>
            <div id="audio-stats"><span id="audio-count">?</span> <span id="audio-count-label"></span></div>
            <div class="sidebar-header-actions">
              <button id="audio-filter-toggle" class="panel-toggle" type="button" aria-controls="audio-filter-panel" aria-expanded="true"></button>
              <button id="audio-reset" type="button"></button>
            </div>
          </header>
          <div class="audio-mode-switch" role="group" aria-label="Audio dataset">
            <button id="audio-events-mode" class="audio-mode-button is-active" type="button" data-audio-mode="events" aria-pressed="true"></button>
            <button id="audio-media-mode" class="audio-mode-button" type="button" data-audio-mode="media" aria-pressed="false"></button>
          </div>
          <div id="audio-filter-panel" class="filters">
            <section class="filter-section filter-section-basic" data-filter-section="audio-basic" data-fixed-open="1">
              <div class="filter-section-title"><span id="audio-basic-filter-label"></span></div>
              <div class="filter-section-body filter-section-body-stack">
                <input id="audio-q" type="search" autocomplete="off">
              </div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-category" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-category-filter-body"><span id="audio-category-label"></span></button>
              <div id="audio-category-filter-body" class="filter-section-body" hidden><div id="audio-category-filter" class="chips" data-multi="1"></div></div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-context" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-context-filter-body"><span id="audio-context-label"></span></button>
              <div id="audio-context-filter-body" class="filter-section-body" hidden><div id="audio-context-filter" class="chips" data-multi="1"></div></div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-relation" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-relation-filter-body"><span id="audio-relation-label"></span></button>
              <div id="audio-relation-filter-body" class="filter-section-body" hidden><div id="audio-relation-filter" class="chips" data-multi="1"></div></div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-scope" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-scope-filter-body"><span id="audio-scope-label"></span></button>
              <div id="audio-scope-filter-body" class="filter-section-body" hidden><div id="audio-scope-filter" class="chips" data-multi="1"></div></div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-source" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-source-filter-body"><span id="audio-source-label"></span></button>
              <div id="audio-source-filter-body" class="filter-section-body" hidden><div id="audio-source-filter" class="chips" data-multi="1"></div></div>
            </section>
          </div>
          <div id="audio-filter-splitter" class="filter-splitter" role="separator" aria-label="Resize audio filters" aria-orientation="horizontal" tabindex="0"></div>
          <div id="audio-list-meta"><span id="audio-shown">0</span> / <span id="audio-total">0</span> <span id="audio-shown-label"></span></div>
          <div id="audio-list-wrap"><div id="audio-list-spacer"></div><div id="audio-list"></div></div>
        </aside>
        <div id="audio-splitter" class="pane-splitter" role="separator" aria-label="Resize audio sidebar" aria-orientation="vertical" tabindex="0"></div>
        <main id="audio-right">
          <header class="audio-detail-header">
            <div id="audio-detail-eyebrow" class="audio-detail-eyebrow"></div>
            <h1 id="audio-detail-title"></h1>
            <div id="audio-detail-subtitle"></div>
          </header>
          <div id="audio-detail-body"></div>
        </main>
      </div>`;
    bindShellEvents();
    bindFilterSections();
    setupFilterPanel();
    setupSplitters();
    applyUiText();
    syncModeButtons();
  }

  function bindShellEvents() {
    $("#audio-q", state.container)?.addEventListener("input", (event) => {
      state.query = event.target.value;
      applyFilters({ resetScroll: true });
    });
    $("#audio-reset", state.container)?.addEventListener("click", () => resetFilters());
    state.container.querySelectorAll("[data-audio-mode]").forEach((button) => {
      button.addEventListener("click", () => switchMode(button.dataset.audioMode));
    });
    $("#audio-list-wrap", state.container)?.addEventListener("scroll", scheduleListRender, { passive: true });
    $("#audio-list", state.container)?.addEventListener("click", (event) => {
      const row = event.target.closest(".audio-row[data-index]");
      if (!row) return;
      selectRecord(state.filtered[Number(row.dataset.index)]);
    });
    $("#audio-list", state.container)?.addEventListener("keydown", (event) => {
      if (!["Enter", " "].includes(event.key)) return;
      const row = event.target.closest(".audio-row[data-index]");
      if (!row) return;
      event.preventDefault();
      selectRecord(state.filtered[Number(row.dataset.index)]);
    });
  }

  function bindFilterSections() {
    state.container.querySelectorAll(".filter-section-toggle").forEach((button) => {
      button.addEventListener("click", () => {
        const section = button.closest(".filter-section");
        const body = section?.querySelector(".filter-section-body");
        if (!section || !body) return;
        const collapsed = !section.classList.contains("is-collapsed");
        section.classList.toggle("is-collapsed", collapsed);
        body.hidden = collapsed;
        button.setAttribute("aria-expanded", String(!collapsed));
        window.dispatchEvent(new Event("resize"));
      });
    });
  }

  function setupFilterPanel() {
    state.filterPanel = window.WebUI?.filters?.createPanelToggle?.({
      panel: "#audio-filter-panel",
      toggle: "#audio-filter-toggle",
      left: "#audio-left",
      storageKey: FILTER_PANEL_STORAGE_KEY,
      isMobile: isMobileLayout,
      labels: (collapsed) => t(collapsed ? "showFilters" : "hideFilters"),
      onChange: () => window.dispatchEvent(new Event("resize")),
    }) || null;
  }

  function setupSplitters() {
    const setup = window.WebUI?.setupSplitter;
    const utils = window.WebUI?.splitterUtils;
    const shell = $(".audio-shell", state.container);
    const sidebar = $("#audio-left", state.container);
    const pane = $("#audio-splitter", state.container);
    const panel = $("#audio-filter-panel", state.container);
    const filter = $("#audio-filter-splitter", state.container);
    const list = $("#audio-list-wrap", state.container);
    if (!setup || !utils || !shell || !sidebar || !pane || !panel || !filter || !list) return;

    let paneWasMobile = isMobileLayout();
    setup({
      handle: pane,
      storageKey: PANE_STORAGE_KEY,
      bodyDragClass: "is-resizing-pane",
      client: (event) => event.clientX,
      keys: { decrease: ["ArrowLeft"], increase: ["ArrowRight"] },
      enabled: () => !isMobileLayout(),
      bounds: () => {
        const min = parsePixels(getComputedStyle(sidebar).minWidth, 300);
        return { min, max: Math.max(min, shell.getBoundingClientRect().width - pane.getBoundingClientRect().width - 320) };
      },
      read: () => parsePixels(sidebar.style.width, sidebar.getBoundingClientRect().width),
      write: (width) => { sidebar.style.width = `${Math.round(width)}px`; },
      clear: () => { sidebar.style.removeProperty("width"); },
      sync: (controller) => {
        if (isMobileLayout()) {
          paneWasMobile = true;
          controller.clear({ commit: false });
          return;
        }
        if (shell.getBoundingClientRect().width < 48) return;
        let width = parsePixels(sidebar.style.width, sidebar.getBoundingClientRect().width);
        if (paneWasMobile || !sidebar.style.width) width = utils.readStoredNumber(PANE_STORAGE_KEY) ?? width;
        paneWasMobile = false;
        controller.set(width, { persist: false, commit: false });
      },
    });

    const minPanelHeight = 56;
    const minListHeight = 160;
    let filterWasMobile = isMobileLayout();
    const naturalHeight = () => {
      const previous = panel.style.height;
      const resized = panel.classList.contains("is-filter-resized");
      panel.style.removeProperty("height");
      panel.classList.remove("is-filter-resized");
      const height = Math.ceil(panel.getBoundingClientRect().height);
      if (previous) panel.style.height = previous;
      panel.classList.toggle("is-filter-resized", resized);
      return Math.max(minPanelHeight, height);
    };
    const controller = setup({
      handle: filter,
      storageKey: FILTER_HEIGHT_STORAGE_KEY,
      bodyDragClass: "is-resizing-filter",
      client: (event) => event.clientY,
      keys: { decrease: ["ArrowUp"], increase: ["ArrowDown"] },
      enabled: () => !isMobileLayout() && !panel.hidden,
      bounds: () => {
        let fixed = 0;
        for (const child of sidebar.children) if (child !== panel && child !== list) fixed += child.getBoundingClientRect().height;
        const available = Math.max(minPanelHeight, sidebar.getBoundingClientRect().height - fixed - minListHeight);
        return { min: minPanelHeight, max: Math.max(minPanelHeight, Math.min(available, naturalHeight())) };
      },
      read: () => panel.getBoundingClientRect().height,
      write: (height) => {
        panel.style.height = `${Math.round(height)}px`;
        panel.classList.add("is-filter-resized");
      },
      clear: () => {
        panel.style.removeProperty("height");
        panel.classList.remove("is-filter-resized");
      },
      sync: (ctrl) => {
        if (isMobileLayout() || panel.hidden) {
          filterWasMobile = isMobileLayout();
          ctrl.clear({ commit: false });
          return;
        }
        if (sidebar.getBoundingClientRect().height < 48) return;
        const stored = utils.readStoredNumber(FILTER_HEIGHT_STORAGE_KEY);
        if (stored !== null) {
          filterWasMobile = false;
          ctrl.set(stored, { persist: false, commit: false });
        } else {
          if (filterWasMobile) ctrl.clear({ commit: false });
          filterWasMobile = false;
          ctrl.syncAria();
        }
      },
    });
    if (window.MutationObserver && controller) {
      const observer = new MutationObserver(controller.requestSync);
      observer.observe(panel, { attributes: true, attributeFilter: ["hidden"] });
      observer.observe(panel, { childList: true, subtree: true });
    }
  }

  function applyUiText() {
    const pairs = {
      "audio-title": "title", "audio-count-label": "countLabel", "audio-filter-toggle": state.filterPanel?.collapsed ? "showFilters" : "hideFilters",
      "audio-reset": "reset", "audio-events-mode": "events", "audio-media-mode": "media", "audio-basic-filter-label": "basicFilters",
      "audio-category-label": "category", "audio-context-label": "context", "audio-relation-label": "relation",
      "audio-scope-label": "scope", "audio-source-label": "source", "audio-shown-label": "shown",
    };
    for (const [id, key] of Object.entries(pairs)) {
      const node = $(`#${id}`, state.container);
      if (node) node.textContent = t(key);
    }
    const search = $("#audio-q", state.container);
    if (search) search.placeholder = t("search");
    for (const records of Object.values(state.datasets)) {
      for (const record of records || []) {
        record.meta = recordMeta(record.raw, record.kind, record);
        record.search = searchText(record.raw, record.kind, record);
      }
    }
    applyIndexHeader();
    buildFilterChips();
    renderList();
    renderDetail();
  }

  function applyIndexHeader() {
    const records = state.datasets[state.mode];
    const count = records ? records.length : indexCount(state.mode);
    const node = $("#audio-count", state.container);
    if (node) node.textContent = count === null ? "?" : formatNumber(count);
  }

  function indexCount(kind) {
    const counts = state.index?.counts || state.index?.summary?.counts || {};
    const keys = kind === "events"
      ? ["events", "eventCount", "namedEvents", "audioEvents"]
      : ["media", "mediaCount", "decodedMedia", "files", "audioFiles"];
    for (const key of keys) {
      const value = counts[key] ?? state.index?.shards?.[kind]?.count;
      if (Number.isFinite(Number(value))) return Number(value);
    }
    return null;
  }

  function syncModeButtons() {
    state.container?.querySelectorAll("[data-audio-mode]").forEach((button) => {
      const active = button.dataset.audioMode === state.mode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    applyIndexHeader();
  }

  function resetFilters({ render = true } = {}) {
    state.query = "";
    state.filters.categories.clear();
    state.filters.contexts.clear();
    state.filters.relations.clear();
    state.filters.scopes.clear();
    state.filters.sources.clear();
    const search = $("#audio-q", state.container);
    if (search) search.value = "";
    if (render) {
      buildFilterChips();
      applyFilters({ resetScroll: true });
    }
  }

  function countValues(records, field) {
    const counts = new Map();
    for (const record of records || []) {
      for (const value of new Set(asArray(record[field]).filter(Boolean))) counts.set(value, (counts.get(value) || 0) + 1);
    }
    return counts;
  }

  function buildFilterChips() {
    const records = state.datasets[state.mode] || [];
    const build = window.WebUI?.filters?.buildChips;
    if (!build) return;
    const groups = [
      ["#audio-category-filter", "category", state.filters.categories, null],
      ["#audio-context-filter", "contextTags", state.filters.contexts, taxonomyLabel],
      ["#audio-relation-filter", "relationTags", state.filters.relations, taxonomyLabel],
      ["#audio-scope-filter", "scope", state.filters.scopes, null],
      ["#audio-source-filter", "source", state.filters.sources, null],
    ];
    for (const [selector, field, active, label] of groups) {
      const counts = countValues(records, field);
      const values = [...counts.keys()].filter(Boolean).sort((a, b) => (label ? label(a) : a).localeCompare(label ? label(b) : b, undefined, { numeric: true }));
      build(selector, values, {
        active,
        count: counts,
        className: "audio-filter-chip",
        label: label || undefined,
        onToggle: () => applyFilters({ resetScroll: true }),
      });
    }
  }

  function syncFilterCounts() {
    window.WebUI?.setFilterSectionActiveCounts?.({
      "audio-basic": state.query.trim() ? 1 : 0,
      "audio-category": state.filters.categories.size,
      "audio-context": state.filters.contexts.size,
      "audio-relation": state.filters.relations.size,
      "audio-scope": state.filters.scopes.size,
      "audio-source": state.filters.sources.size,
    });
  }

  function applyFilters({ resetScroll = false } = {}) {
    const records = state.datasets[state.mode] || [];
    const tokens = normalizeLower(state.query).split(/\s+/).filter(Boolean);
    state.filtered = records.filter((record) => {
      if (tokens.length && !tokens.every((token) => record.search.includes(token))) return false;
      if (state.filters.categories.size && !state.filters.categories.has(record.category)) return false;
      if (state.filters.contexts.size && !record.contextTags.some((value) => state.filters.contexts.has(value))) return false;
      if (state.filters.relations.size && !record.relationTags.some((value) => state.filters.relations.has(value))) return false;
      if (state.filters.scopes.size && !state.filters.scopes.has(record.scope)) return false;
      if (state.filters.sources.size && !state.filters.sources.has(record.source)) return false;
      return true;
    }).sort((a, b) => a.title.localeCompare(b.title, undefined, { numeric: true }) || a.key.localeCompare(b.key, undefined, { numeric: true }));
    state.rows = state.filtered.map((record, index) => ({ record, index, top: index * ROW_HEIGHT }));
    const spacer = $("#audio-list-spacer", state.container);
    if (spacer) spacer.style.height = `${state.rows.length * ROW_HEIGHT}px`;
    const wrap = $("#audio-list-wrap", state.container);
    if (resetScroll && wrap) wrap.scrollTop = 0;
    $("#audio-shown", state.container).textContent = formatNumber(state.filtered.length);
    $("#audio-total", state.container).textContent = formatNumber(records.length);
    applyIndexHeader();
    syncFilterCounts();
    renderList();
  }

  function scheduleListRender() {
    if (state.renderFrame) return;
    state.renderFrame = requestAnimationFrame(() => {
      state.renderFrame = 0;
      renderList();
    });
  }

  function firstVisibleRow(top) {
    return Math.max(0, Math.min(state.rows.length, Math.floor(top / ROW_HEIGHT)));
  }

  function renderList() {
    const wrap = $("#audio-list-wrap", state.container);
    const list = $("#audio-list", state.container);
    if (!wrap || !list) return;
    if (!state.datasets[state.mode]) return;
    if (!state.rows.length) {
      list.innerHTML = `<div class="audio-empty-list">${esc((state.datasets[state.mode] || []).length ? t("noMatches") : t("noData"))}</div>`;
      return;
    }
    const startTop = Math.max(0, wrap.scrollTop - OVERSCAN_PX);
    const endTop = wrap.scrollTop + wrap.clientHeight + OVERSCAN_PX;
    const fragment = document.createDocumentFragment();
    let index = firstVisibleRow(startTop);
    while (index < state.rows.length && state.rows[index].top < endTop) {
      const row = state.rows[index];
      const button = document.createElement("button");
      button.type = "button";
      button.className = `audio-row${state.selected?.kind === state.mode && state.selected?.key === row.record.key ? " is-selected" : ""}`;
      button.dataset.index = String(row.index);
      button.style.top = `${row.top}px`;
      button.style.height = `${ROW_HEIGHT}px`;
      button.innerHTML = `<span class="audio-row-title-line"><span class="audio-row-kind">${esc(state.mode === "events" ? t("event") : t("mediaItem"))}</span><span class="audio-row-title">${esc(row.record.title)}</span></span><span class="audio-row-meta">${esc(row.record.meta)}</span>`;
      fragment.appendChild(button);
      index += 1;
    }
    list.replaceChildren(fragment);
  }

  function renderLoadingList() {
    const list = $("#audio-list", state.container);
    const spacer = $("#audio-list-spacer", state.container);
    if (spacer) spacer.style.height = "0px";
    if (list) list.innerHTML = `<div class="audio-empty-list">${esc(t(state.mode === "events" ? "loadingEvents" : "loadingMedia"))}</div>`;
    const shown = $("#audio-shown", state.container);
    const total = $("#audio-total", state.container);
    if (shown) shown.textContent = "0";
    if (total) total.textContent = "?";
  }

  function selectRecord(record, { updateUrl = true } = {}) {
    if (!record) return;
    state.selected = record;
    if (updateUrl) updateSelectionUrl(record);
    const detail = $("#audio-right", state.container);
    if (detail) detail.scrollTop = 0;
    renderList();
    renderDetail();
    if (record.kind === "events") ensureEventDetail(record).catch((error) => {
      if (state.selected === record) window.WebUI?.showShellStatus?.("audio", `${t("shardError")} ${error.message || error}`, "error");
    });
  }

  function requestedSelection() {
    const params = new URLSearchParams(window.location.search || "");
    return normalize(params.get("audio"));
  }

  function applyRequestedSelection() {
    const requested = requestedSelection();
    if (!requested || state.mode !== "events") return;
    const record = (state.datasets.events || []).find((candidate) => candidate.key === requested || recordId(candidate.raw, "events") === requested);
    if (record) selectRecord(record, { updateUrl: false });
  }

  function updateSelectionUrl(record) {
    const url = new URL(window.location.href);
    url.searchParams.set("audio", record.key);
    url.searchParams.set("audioKind", record.kind);
    url.hash = "#audio";
    history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }

  function clearSelectionFromUrl() {
    const url = new URL(window.location.href);
    url.searchParams.delete("audio");
    url.searchParams.delete("audioKind");
    if (document.body.dataset.activeView === "audio") url.hash = "#audio";
    history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }

  function renderDetail() {
    const eyebrow = $("#audio-detail-eyebrow", state.container);
    const title = $("#audio-detail-title", state.container);
    const subtitle = $("#audio-detail-subtitle", state.container);
    const body = $("#audio-detail-body", state.container);
    if (!eyebrow || !title || !subtitle || !body) return;
    const selected = state.selected;
    eyebrow.textContent = selected ? (selected.kind === "events" ? t("event") : t("mediaItem")) : t("overview");
    title.textContent = selected ? selected.title : t("runtimeSystem");
    subtitle.textContent = selected ? selected.meta : indexSubtitle();
    body.replaceChildren();
    if (selected) {
      body.append(recordPanel(selected), runtimePanel());
    } else {
      body.appendChild(runtimePanel());
      const empty = document.createElement("p");
      empty.className = "audio-detail-note";
      empty.textContent = t("selectRecord");
      body.appendChild(empty);
    }
  }

  function indexSubtitle() {
    const parts = [state.index?.language || state.language, state.index?.generated].filter(Boolean);
    return parts.join(" · ");
  }

  function runtimePanel() {
    const runtimeCandidate = state.index?.runtimeSystem || state.index?.runtimeModel;
    const runtime = runtimeCandidate && typeof runtimeCandidate === "object" ? runtimeCandidate : {};
    const panel = document.createElement("section");
    panel.className = "audio-panel audio-boundary";
    const heading = document.createElement("h2");
    heading.textContent = t("runtimeSystem");
    panel.appendChild(heading);
    const descriptionCandidate = runtime.overview ?? runtime.description ?? runtime.summary ?? runtime.evidenceBoundary;
    const description = ["string", "number", "boolean"].includes(typeof descriptionCandidate) ? normalize(descriptionCandidate) : "";
    if (description) {
      const note = document.createElement("p");
      note.className = "audio-runtime-note";
      note.textContent = description;
      panel.appendChild(note);
    }

    const stats = runtime.counts && typeof runtime.counts === "object"
      ? runtime.counts
      : (runtime.stats && typeof runtime.stats === "object" ? runtime.stats : (state.index?.counts || {}));
    const statEntries = Object.entries(stats).filter(([, value]) => ["string", "number", "boolean"].includes(typeof value)).slice(0, 18);
    if (statEntries.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      if (description) grid.style.marginTop = "12px";
      for (const [label, value] of statEntries) grid.appendChild(statNode(humanize(label), typeof value === "number" ? formatNumber(value) : value));
      panel.appendChild(grid);
    }

    const components = asArray(runtime.components ?? runtime.layers).map((value) => typeof value === "object" ? (value.name ?? value.id ?? value.type) : value).filter(Boolean);
    if (components.length) panel.appendChild(chipSection(t("runtimeComponents"), components));
    const hirc = state.index?.hircSummary;
    if (hirc && typeof hirc === "object" && Object.keys(hirc).length) panel.appendChild(hircInventorySection(hirc));
    const systems = asArray(runtime.systems).filter((value) => value && typeof value === "object");
    if (systems.length) panel.appendChild(runtimeSystemsSection(systems));
    const boundaryCandidate = runtime.boundary ?? state.index?.evidenceBoundary;
    const boundary = ["string", "number", "boolean"].includes(typeof boundaryCandidate) ? normalize(boundaryCandidate) : "";
    if (boundary && boundary !== description) panel.appendChild(noteSection(t("runtimeBoundary"), boundary));
    if (boundaryCandidate && typeof boundaryCandidate === "object" && !Array.isArray(boundaryCandidate)) {
      const boundaryEntries = Object.entries(boundaryCandidate).filter(([, value]) => ["string", "number", "boolean"].includes(typeof value));
      if (boundaryEntries.length) panel.appendChild(boundaryGrid(boundaryEntries));
    }
    if (!description && !statEntries.length && !components.length && !boundary) {
      const note = document.createElement("p");
      note.className = "audio-runtime-note";
      note.textContent = t("noData");
      panel.appendChild(note);
    }
    return panel;
  }

  function hircInventorySection(hirc) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("hircInventory");
    const grid = document.createElement("div");
    grid.className = "audio-stat-grid";
    const versions = Object.entries(hirc.bankVersions || {}).map(([version, count]) => `${version}: ${formatNumber(count)}`).join(", ");
    const facts = [
      ["PCK packages", hirc.packageCount],
      ["Embedded banks", hirc.embeddedBankCount],
      ["HIRC objects", hirc.hircObjectCount],
      ["Bank versions", versions],
    ];
    for (const [label, value] of facts) if (value !== undefined && value !== null && value !== "") grid.appendChild(statNode(label, typeof value === "number" ? formatNumber(value) : value));
    section.append(heading, grid);
    const labels = hirc.objectTypeLabels || {};
    const typeCounts = Object.entries(hirc.objectTypeCounts || {}).map(([type, count]) => `${labels[type] || `type${type}`} (${type}): ${formatNumber(count)}`);
    if (typeCounts.length) section.appendChild(chipSection("Object families", typeCounts));
    if (hirc.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), hirc.evidenceBoundary));
    return section;
  }

  function boundaryGrid(entries) {
    const section = document.createElement("div");
    section.style.marginTop = "12px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("runtimeBoundary");
    const grid = document.createElement("div");
    grid.className = "audio-runtime-boundaries";
    for (const [key, value] of entries.slice(0, 12)) {
      const item = document.createElement("div");
      item.className = "audio-runtime-boundary";
      item.innerHTML = `<strong>${esc(humanize(key))}</strong><span>${esc(value)}</span>`;
      grid.appendChild(item);
    }
    section.append(heading, grid);
    return section;
  }

  function runtimeSystemsSection(systems) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("runtimeComponents");
    const list = document.createElement("div");
    list.className = "audio-runtime-systems";
    for (const system of systems.slice(0, 40)) {
      const card = document.createElement("article");
      card.className = "audio-runtime-system";
      const type = normalize(system.type ?? system.name ?? system.id) || t("unknown");
      const layer = normalize(system.layer);
      const meaning = normalize(system.meaning ?? system.description);
      const counts = [];
      if (asArray(system.fields).length) counts.push(`${asArray(system.fields).length} fields`);
      if (asArray(system.methods).length) counts.push(`${asArray(system.methods).length} methods`);
      card.innerHTML = `<div class="audio-runtime-system-head"><code>${esc(type)}</code>${layer ? `<span>${esc(layer)}</span>` : ""}</div>${meaning ? `<p>${esc(meaning)}</p>` : ""}${counts.length ? `<small>${esc(counts.join(" · "))}</small>` : ""}`;
      list.appendChild(card);
    }
    section.append(heading, list);
    return section;
  }

  function contextEvidenceLabel(context) {
    const kind = normalize(context?.kind);
    const group = contextGroup(kind);
    const parts = [group ? taxonomyLabel(group) : humanize(kind), humanize(kind)];
    if (context?.ownerId) parts.push(context.ownerId);
    if (context?.groupId) parts.push(context.groupId);
    if (context?.storyKey) parts.push(context.storyKey);
    if (context?.table) parts.push(context.table);
    if (context?.path) parts.push(context.path);
    if (context?.semanticRole) parts.push(humanize(context.semanticRole));
    if (context?.confidence) parts.push(context.confidence);
    const skillIds = asArray(context?.skillIds).filter(Boolean);
    if (skillIds.length) parts.push(skillIds.length === 1 ? skillIds[0] : `${skillIds[0]} +${skillIds.length - 1}`);
    const actionKinds = asArray(context?.actionKinds).filter(Boolean);
    if (actionKinds.length) parts.push(actionKinds.map(humanize).join(" / "));
    if (Number(context?.animationOwnerCount || 0) > 1) {
      parts.push(`${context.animationOwnerCount} ${kind === "characterAnimation" ? "playable character" : "enemy template"} animation owners`);
    }
    if (context?.animationOwnershipScope) parts.push(humanize(context.animationOwnershipScope));
    if (context?.possibleMediaScope) parts.push(humanize(context.possibleMediaScope));
    const functions = asArray(context?.animationFunctions).filter(Boolean);
    if (functions.length) parts.push(functions.join(" / "));
    const clipContexts = asArray(context?.animationClipContexts).filter(Boolean);
    if (clipContexts.length) parts.push(clipContexts.map(humanize).join(" / "));
    if (context?.clipReachability) parts.push(`clip reachability: ${context.clipReachability}`);
    const clips = asArray(context?.animationClips).filter(Boolean);
    if (clips.length) parts.push(clips.length === 1 ? clips[0] : `${clips[0]} +${clips.length - 1}`);
    return [...new Set(parts.filter(Boolean))].join(" · ");
  }

  function selectorEvidenceSummary(record) {
    const actions = new Map();
    const containers = new Map();
    let unresolved = 0;
    for (const evidence of asArray(record?.evidence)) {
      for (const action of asArray(evidence?.actionEvidence)) {
        const operation = humanize(action?.operation || "unknown action");
        actions.set(operation, (actions.get(operation) || 0) + 1);
      }
      for (const container of asArray(evidence?.containerEvidence)) {
        const relation = normalize(container?.edgeKind) || "unknown";
        const current = containers.get(relation) || { count: 0, children: 0 };
        current.count += Number(container?.nodeCount || 1);
        current.children += Number(container?.childCount || 0);
        containers.set(relation, current);
      }
      unresolved += asArray(evidence?.unresolvedNodes).length;
    }
    const values = [...actions].map(([operation, count]) => `${operation} × ${formatNumber(count)}`);
    for (const [relation, value] of containers) {
      values.push(`${taxonomyLabel(relation)}: ${formatNumber(value.count)} nodes / ${formatNumber(value.children)} child edges`);
    }
    if (unresolved) values.push(`${t("relationPartialGraph")}: ${formatNumber(unresolved)} unresolved nodes`);
    return values;
  }

  function recordPanel(record) {
    const panel = document.createElement("section");
    panel.className = "audio-panel";
    const heading = document.createElement("h2");
    heading.textContent = t("details");
    panel.appendChild(heading);
    const raw = record.raw;
    const facts = record.kind === "events"
      ? [
          [t("recordType"), t(record.objectType)], [t("id"), raw.eventId ?? raw.id], [t("hash"), raw.eventHash ?? raw.hash], [t("category"), record.category],
          ["Category evidence", raw.categoryEvidence],
          [t("scope"), record.scope], [t("source"), record.source], [t("bank"), raw.bank ?? raw.sourceBank ?? raw.bankId ?? raw.evidence?.[0]?.bank],
          ["Wwise", raw.foundInWwise], [t("typedTraversal"), raw.traversalStatus], [t("playRoots"), raw.playRootCount],
          [t("possibleMedia"), raw.possibleMediaCount ?? raw.candidateCount], [t("uniqueContent"), raw.uniqueDecodedContentCount],
          [t("equivalentContent"), raw.contentEquivalentLeafCount], ["Runtime selection", raw.runtimeSelection], ["Contexts", raw.contextCount],
          ["Playable animation owners", raw.playableCharacterAnimationOwnerCount], ["Animation scope", raw.animationContextScope],
          ["Animation callbacks", asArray(raw.animationFunctions).join(" / ")],
        ]
      : [
          [t("recordType"), t(record.objectType)], [t("id"), raw.mediaId ?? raw.id], [t("category"), record.category], [t("scope"), record.scope],
          [t("source"), record.source], [t("path"), raw.rel ?? raw.path ?? raw.src], [t("format"), raw.format],
          [t("bytes"), raw.bytes !== undefined ? formatBytes(raw.bytes) : ""], [t("bank"), raw.bank ?? raw.sourceBank ?? raw.bankId],
        ];
    const grid = document.createElement("div");
    grid.className = "audio-facts";
    for (const [label, value] of facts) if (value !== undefined && value !== null && value !== "") grid.appendChild(factNode(label, value));
    panel.appendChild(grid);

    if (record.contextTags.length) panel.appendChild(chipSection(t("contextGroups"), record.contextTags.map(taxonomyLabel)));
    if (record.relationTags.length) panel.appendChild(chipSection(t("relation"), record.relationTags.map(taxonomyLabel)));
    const selectorEvidence = selectorEvidenceSummary(raw);
    if (selectorEvidence.length) panel.appendChild(chipSection(t("selectorEvidence"), selectorEvidence));

    const evidence = asArray(raw.evidence).filter((value) => value && typeof value === "object");
    const mediaIds = [...new Set([
      ...collectIds(raw, ["mediaIds", "mediaId"]),
      ...evidence.flatMap((row) => collectIds(row, ["mediaIds", "mediaId"])),
    ])];
    const eventIds = collectIds(raw, ["eventIds", "events", "eventId"]);
    const actionIds = [...new Set([
      ...collectIds(raw, ["actionIds", "visitedObjectIds", "actions"]),
      ...evidence.flatMap((row) => collectIds(row, ["actionIds", "visitedObjectIds", "actions"])),
    ])];
    if (mediaIds.length) panel.appendChild(chipSection(t("mediaIds"), mediaIds));
    if (record.kind === "media" && eventIds.length) panel.appendChild(chipSection(t("eventIds"), eventIds));
    if (actionIds.length) panel.appendChild(chipSection(t("actions"), actionIds));
    const contexts = asArray(raw.contexts).filter((value) => value && typeof value === "object").map(contextEvidenceLabel).filter(Boolean);
    if (contexts.length) panel.appendChild(chipSection(t("contextEvidence"), contexts));

    const players = playableRecords(raw, record.kind);
    const playerSection = document.createElement("section");
    playerSection.style.marginTop = "14px";
    const playerHeading = document.createElement("h3");
    playerHeading.textContent = t("playableMedia");
    playerSection.appendChild(playerHeading);
    if (raw.detailShard && !raw._detailLoaded) {
      const note = document.createElement("p");
      note.className = "audio-detail-note";
      note.textContent = t("loadingEvents");
      playerSection.appendChild(note);
    } else if (players.length) renderPlayers(playerSection, players);
    else {
      const note = document.createElement("p");
      note.className = "audio-detail-note";
      note.textContent = t("noPlayableMedia");
      playerSection.appendChild(note);
    }
    panel.appendChild(playerSection);

    const details = document.createElement("details");
    details.style.marginTop = "14px";
    const summary = document.createElement("summary");
    summary.textContent = t("rawRecord");
    const pre = document.createElement("pre");
    pre.className = "audio-raw-record";
    const json = JSON.stringify(raw, null, 2) || "{}";
    pre.textContent = json.length > 50000 ? `${json.slice(0, 50000)}\n…` : json;
    details.append(summary, pre);
    panel.appendChild(details);
    return panel;
  }

  function collectIds(record, keys) {
    const values = [];
    for (const key of keys) {
      for (const value of asArray(record?.[key])) {
        const id = typeof value === "object" ? (value.id ?? value.eventId ?? value.mediaId ?? value.actionId ?? value.objectId) : value;
        if (id !== undefined && id !== null && id !== "") values.push(String(id));
      }
    }
    return [...new Set(values)].slice(0, 120);
  }

  function playableRecords(raw, kind) {
    const candidates = [];
    const add = (value) => {
      if (!value) return;
      if (typeof value === "string") candidates.push({ src: value });
      else if (typeof value === "object") candidates.push(value);
    };
    if (kind === "media") add(raw);
    for (const key of ["media", "mediaEntries", "playableMedia", "audio", "candidates", "outputs"]) asArray(raw?.[key]).forEach(add);
    const seen = new Set();
    return candidates.map((candidate) => {
      const src = audioSource(candidate, raw);
      const id = normalize(candidate.mediaId ?? candidate.id ?? fileName(src));
      const wwise = asArray(candidate?.wwiseMediaEvidence).filter((row) => row && typeof row === "object");
      const rootActionIds = [...new Set(wwise.flatMap((row) => asArray(row.rootActionIds)).filter((value) => Number.isInteger(value)))].sort((a, b) => a - b);
      const relationTypes = [...new Set(wwise.flatMap((row) => asArray(row.relationTypes)).filter(Boolean))].sort();
      const soundObjectCount = wwise.reduce((total, row) => total + Number(row.soundObjectCount || 0), 0);
      return {
        raw: candidate, src, id, bytes: candidate.bytes, format: candidate.format,
        rootActionIds, relationTypes, soundObjectCount,
        contentSha256: normalize(candidate.contentSha256),
        contentEquivalentCount: Number(candidate.contentEquivalentCount || 0),
      };
    }).filter((candidate) => candidate.src && !seen.has(candidate.src) && seen.add(candidate.src));
  }

  function audioSource(candidate, parent = {}) {
    let raw = normalize(candidate?.src ?? candidate?.audioSrc ?? candidate?.path ?? candidate?.rel);
    if (!raw) return "";
    raw = raw.replace(/\\/g, "/");
    if (/^(?:https?:|blob:|data:)/i.test(raw) || raw.startsWith("/")) return raw;
    raw = raw.replace(/^\.\//, "").replace(/^\/+/, "");
    if (raw.startsWith("export_full/")) return `/${raw}`;
    if (raw.startsWith("structured/Audio/")) return `/export_full/${raw}`;
    const root = normalize(candidate?.storageRoot ?? parent?.storageRoot ?? candidate?.audioScope ?? parent?.audioScope);
    if (root === "shared") return `/export_full/structured/Audio/shared/${encodePath(raw)}`;
    return `/export_full/structured/Audio/${encodeURIComponent(state.language)}/${encodePath(raw)}`;
  }

  function encodePath(path) {
    return String(path || "").split("/").filter(Boolean).map(encodeURIComponent).join("/");
  }

  function renderPlayers(parent, players) {
    const list = document.createElement("div");
    list.className = "audio-player-list";
    const groups = new Map();
    for (const candidate of players) {
      const groupKey = `${candidate.rootActionIds.join(",")}|${candidate.relationTypes.join(",")}`;
      if (!groups.has(groupKey)) groups.set(groupKey, []);
      groups.get(groupKey).push(candidate);
    }
    for (const candidates of groups.values()) {
      const exemplar = candidates[0];
      const groupTitle = document.createElement("div");
      groupTitle.className = "audio-fact-label";
      const rootLabel = exemplar.rootActionIds.length
        ? `${t("playRoots")}: ${exemplar.rootActionIds.join(" / ")}`
        : t("relationDirectDialogMedia");
      const relationLabel = exemplar.relationTypes.map(taxonomyLabel).join(" + ");
      groupTitle.textContent = [rootLabel, relationLabel, `${formatNumber(candidates.length)} ${t("possibleMedia")}`].filter(Boolean).join(" · ");
      list.appendChild(groupTitle);
      for (const candidate of candidates) {
      const card = document.createElement("div");
      card.className = "audio-player-card";
      const head = document.createElement("div");
      head.className = "audio-player-head";
      const title = document.createElement("div");
      title.className = "audio-player-title";
      title.textContent = candidate.id || fileName(candidate.src);
      const meta = document.createElement("div");
      meta.className = "audio-player-meta";
      meta.textContent = [
        candidate.format,
        candidate.bytes !== undefined ? formatBytes(candidate.bytes) : "",
        candidate.soundObjectCount ? `${candidate.soundObjectCount} Sound objects` : "",
        candidate.contentEquivalentCount > 1 ? `${t("equivalentContent")} × ${candidate.contentEquivalentCount}` : "",
        ...candidate.relationTypes.map(taxonomyLabel),
      ].filter(Boolean).join(" · ");
      head.append(title, meta);
      const audio = document.createElement("audio");
      audio.preload = "none";
      audio.controls = true;
      audio.src = candidate.src;
      const player = players.length <= 200 && window.WebUI?.createMediaPlayer ? window.WebUI.createMediaPlayer(audio) : audio;
      card.append(head, player);
      list.appendChild(card);
      }
    }
    parent.appendChild(list);
  }

  function statNode(label, value) {
    const node = document.createElement("div");
    node.className = "audio-stat";
    node.innerHTML = `<span class="audio-stat-label">${esc(label)}</span><span class="audio-stat-value">${esc(value)}</span>`;
    return node;
  }

  function factNode(label, value) {
    const node = document.createElement("div");
    node.className = "audio-fact";
    node.innerHTML = `<span class="audio-fact-label">${esc(label)}</span><span class="audio-fact-value">${esc(value)}</span>`;
    return node;
  }

  function chipSection(label, values) {
    const wrap = document.createElement("div");
    wrap.style.marginTop = "12px";
    const title = document.createElement("div");
    title.className = "audio-fact-label";
    title.textContent = label;
    const list = document.createElement("div");
    list.className = "audio-chip-list";
    for (const value of values) {
      const chip = document.createElement("span");
      chip.className = "audio-data-chip";
      chip.textContent = String(value);
      list.appendChild(chip);
    }
    wrap.append(title, list);
    return wrap;
  }

  function noteSection(label, value) {
    const wrap = document.createElement("div");
    wrap.style.marginTop = "12px";
    const title = document.createElement("div");
    title.className = "audio-fact-label";
    title.textContent = label;
    const note = document.createElement("p");
    note.className = "audio-runtime-note";
    note.textContent = value;
    wrap.append(title, note);
    return wrap;
  }

  function renderLoadError(error, { index = false } = {}) {
    const message = `${t(index ? "loadError" : "shardError")} ${normalize(error?.message || error)}`.trim();
    const html = `<div class="audio-inline-error" role="alert"><strong>${esc(message)}</strong><br><button class="audio-retry" type="button">${esc(t("retry"))}</button></div>`;
    const list = $("#audio-list", state.container);
    if (list) list.innerHTML = html;
    const body = $("#audio-detail-body", state.container);
    if (body) body.innerHTML = html;
    state.container.querySelectorAll(".audio-retry").forEach((button) => {
      button.addEventListener("click", () => window.dispatchEvent(new CustomEvent("webui:retry-view", { detail: { view: "audio", language: state.language } })));
    });
  }

  function humanize(value) {
    return String(value || "").replace(/[_-]+/g, " ").replace(/([a-z0-9])([A-Z])/g, "$1 $2").trim();
  }

  function fileName(value) {
    const clean = normalize(value).replace(/\\/g, "/").split(/[?#]/)[0];
    return clean.split("/").pop() || "";
  }

  function init() {
    if (state.initialized) return true;
    state.container = $("#audio-app");
    if (!state.container) return false;
    state.initialized = true;
    state.uiLocale = locale();
    renderShell();
    renderLoadingList();
    renderDetail();
    window.addEventListener("webui:ui-locale-changed", (event) => {
      state.uiLocale = normalize(event.detail?.locale) || state.uiLocale;
      applyUiText();
    });
    window.addEventListener("resize", scheduleListRender);
    return true;
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.audio = { init, load, retry: () => load(state.language, { force: true }) };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
