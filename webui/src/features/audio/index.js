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
      controlCatalog: "Audio controls / cue catalog",
      physicsAudioCatalog: "Physics / environment audio definitions",
      modelViewStateAudioCatalog: "ModelView state audio behaviors",
      cueOperands: "Cue expression operands",
      globalMusicCues: "Global music cue references",
      rtpcParameters: "RTPC parameters",
      physicsAudioRtpcParameters: "Physics / environment RTPC parameters",
      modelViewStateRtpcParameters: "ModelView state RTPC parameters",
      modelViewStateSpatialControls: "ModelView state spatial controls",
      modelViewStateCustomAudioControls: "ModelView custom-audio controls (unresolved)",
      levelScriptCueInvocations: "LevelScript cue invocations",
      levelScriptDynamicBindings: "LevelScript dynamic Event bindings",
      levelScriptControls: "LevelScript audio controls",
      levelScriptDynamicControls: "LevelScript dynamic control bindings",
      levelEventConditions: "LevelEvent audio conditions",
      levelScriptRadioCatalog: "LevelScript radio triggers",
      unresolvedRadioIds: "Unresolved radio IDs",
      unresolvedRadioLines: "Unresolved radio lines",
      dynamicRadioBindings: "Dynamic radio ID bindings",
      radioTableLines: "RadioTable dialog lines",
      radioTriggerContexts: "Exact LevelScript radio contexts",
      radioTriggerContextCoverage: "Radio trigger context coverage",
      corpus: "Corpus",
      selectRecord: "Select an event or media record from the left.",
      overview: "Overview",
      details: "Details",
      playableMedia: "Playable media",
      expandToLoadPlayer: "expand to load player",
      noPlayableMedia: "No browser-playable media path is attached to this record.",
      mediaIds: "Media IDs",
      eventIds: "Event IDs",
      actions: "Actions / objects",
      recordType: "Record type",
      playbackEvent: "Playback event",
      wwiseEvent: "Wwise Event",
      authoredEventReference: "Authored Event reference (bank object unresolved)",
      controlEvent: "Control event",
      decodedMedia: "Decoded media",
      contextGroups: "Semantic contexts",
      contextEvidence: "Context evidence",
      contextGameplay: "Gameplay",
      contextCutscene: "Cutscene / story",
      contextAnimation: "Animation",
      contextSharedPlayableAnimation: "Shared playable-character animation",
      contextFootstepSystem: "Footstep / material system",
      customFootstepParameters: "OnCustomFootStep parameters",
      customFootstepRuntime: "Footstep runtime boundary",
      customFootstepNativeAnchors: "Current-build native anchors",
      contextOwnerUnresolvedAnimation: "Animation owner unresolved",
      contextScripted: "LevelScript",
      contextLevelScriptTrigger: "Scripted audio trigger",
      contextRadioTrigger: "Exact LevelScript radio trigger",
      contextExactSkillTrigger: "Exact skill-config Event reference",
      contextInferredSkillTrigger: "Inferred skill ownership",
      contextAuthoredPlaySoundAction: "Authored PlaySound action",
      contextProjectileTrigger: "Projectile lifecycle sound",
      contextSpawnerPreWarn: "Enemy-spawner pre-warning",
      contextNpcPatrolTrigger: "NPC patrol-point audio",
      contextCharacterInteraction: "Character interaction perform",
      contextPhysicsEnvironment: "Physics / environment",
      contextModelViewState: "ModelView state behavior",
      contextInteractiveTrigger: "Interactive object trigger",
      contextGlobalLifecycle: "Global audio lifecycle",
      contextAudioCueTrigger: "Audio cue behavior Event",
      contextAuthoredConfig: "Authored config",
      contextManagedRuntime: "Managed-code literal",
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
      relationMusicSwitch: "Music Switch branches",
      relationMusicPlaylist: "Music playlist branches",
      relationMusicTrack: "Music tracks",
      relationMusicSource: "Music track sources",
      musicSwitchContainer: "Music Switch container",
      musicRandomSequenceContainer: "Music Random / Sequence container",
      musicSegment: "Music segment",
      musicTrack: "Music track",
      possibleMedia: "Possible media",
      playRoots: "Play roots",
      typedTraversal: "Typed traversal",
      selectorEvidence: "Selector evidence",
      actionDispatch: "Action dispatch",
      actionOrdinal: "Action",
      serializedNoDelay: "no serialized delay",
      probabilityGate: "probability gate",
      transitionTime: "transition",
      fadeCurve: "fade curve",
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
      controlCatalog: "\u97f3\u9891\u63a7\u5236 / Cue \u76ee\u5f55",
      physicsAudioCatalog: "\u7269\u7406 / \u73af\u5883\u97f3\u9891\u5b9a\u4e49",
      modelViewStateAudioCatalog: "ModelView \u72b6\u6001\u97f3\u9891\u884c\u4e3a",
      cueOperands: "Cue \u8868\u8fbe\u5f0f\u64cd\u4f5c\u6570",
      globalMusicCues: "\u5168\u5c40\u97f3\u4e50 Cue \u5f15\u7528",
      rtpcParameters: "RTPC \u53c2\u6570",
      physicsAudioRtpcParameters: "\u7269\u7406 / \u73af\u5883 RTPC \u53c2\u6570",
      modelViewStateRtpcParameters: "ModelView \u72b6\u6001 RTPC \u53c2\u6570",
      modelViewStateSpatialControls: "ModelView \u72b6\u6001\u7a7a\u95f4\u97f3\u9891\u63a7\u5236",
      modelViewStateCustomAudioControls: "ModelView \u81ea\u5b9a\u4e49\u97f3\u9891\u63a7\u5236\uff08\u672a\u89e3\u6790\uff09",
      levelScriptCueInvocations: "LevelScript Cue \u8c03\u7528",
      levelScriptDynamicBindings: "LevelScript \u52a8\u6001 Event \u7ed1\u5b9a",
      levelScriptControls: "LevelScript \u97f3\u9891\u63a7\u5236",
      levelScriptDynamicControls: "LevelScript \u52a8\u6001\u63a7\u5236\u7ed1\u5b9a",
      levelEventConditions: "LevelEvent \u97f3\u9891\u6761\u4ef6",
      levelScriptRadioCatalog: "LevelScript \u65e0\u7ebf\u7535\u89e6\u53d1",
      unresolvedRadioIds: "\u672a\u89e3\u6790\u7684\u65e0\u7ebf\u7535 ID",
      unresolvedRadioLines: "\u672a\u89e3\u6790\u7684\u65e0\u7ebf\u7535\u53f0\u8bcd",
      dynamicRadioBindings: "\u52a8\u6001\u65e0\u7ebf\u7535 ID \u7ed1\u5b9a",
      radioTableLines: "RadioTable \u5bf9\u8bdd\u884c",
      radioTriggerContexts: "\u7cbe\u786e LevelScript \u65e0\u7ebf\u7535\u4e0a\u4e0b\u6587",
      radioTriggerContextCoverage: "\u65e0\u7ebf\u7535\u89e6\u53d1\u4e0a\u4e0b\u6587\u8986\u76d6",
      corpus: "\u6570\u636e\u96c6",
      selectRecord: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u4e2a\u4e8b\u4ef6\u6216\u5a92\u4f53\u8bb0\u5f55\u3002",
      overview: "\u6982\u89c8",
      details: "\u8be6\u7ec6\u4fe1\u606f",
      playableMedia: "\u53ef\u64ad\u653e\u5a92\u4f53",
      expandToLoadPlayer: "\u5c55\u5f00\u540e\u52a0\u8f7d\u64ad\u653e\u5668",
      noPlayableMedia: "\u8be5\u8bb0\u5f55\u672a\u9644\u52a0\u6d4f\u89c8\u5668\u53ef\u64ad\u653e\u7684\u5a92\u4f53\u8def\u5f84\u3002",
      mediaIds: "\u5a92\u4f53 ID",
      eventIds: "\u4e8b\u4ef6 ID",
      actions: "\u52a8\u4f5c / \u5bf9\u8c61",
      recordType: "\u8bb0\u5f55\u7c7b\u578b",
      playbackEvent: "\u64ad\u653e\u4e8b\u4ef6",
      wwiseEvent: "Wwise Event",
      authoredEventReference: "\u521b\u4f5c Event \u5f15\u7528\uff08\u672a\u89e3\u6790\u5230\u97f3\u9891\u5e93\u5bf9\u8c61\uff09",
      controlEvent: "\u63a7\u5236\u4e8b\u4ef6",
      decodedMedia: "\u5df2\u89e3\u7801\u5a92\u4f53",
      contextGroups: "\u8bed\u4e49\u4e0a\u4e0b\u6587",
      contextEvidence: "\u4e0a\u4e0b\u6587\u8bc1\u636e",
      contextGameplay: "\u73a9\u6cd5",
      contextCutscene: "\u8fc7\u573a / \u5267\u60c5",
      contextAnimation: "\u52a8\u753b",
      contextSharedPlayableAnimation: "\u53ef\u73a9\u89d2\u8272\u5171\u7528\u52a8\u753b",
      contextFootstepSystem: "\u811a\u6b65 / \u6750\u8d28\u7cfb\u7edf",
      customFootstepParameters: "OnCustomFootStep \u53c2\u6570",
      customFootstepRuntime: "\u811a\u6b65\u8fd0\u884c\u65f6\u8bc1\u636e\u8fb9\u754c",
      customFootstepNativeAnchors: "\u5f53\u524d\u7248\u672c\u539f\u751f\u951a\u70b9",
      contextOwnerUnresolvedAnimation: "\u52a8\u753b\u5f52\u5c5e\u672a\u89e3\u6790",
      contextScripted: "LevelScript \u811a\u672c",
      contextLevelScriptTrigger: "\u811a\u672c\u97f3\u9891\u89e6\u53d1",
      contextRadioTrigger: "\u7cbe\u786e LevelScript \u65e0\u7ebf\u7535\u89e6\u53d1",
      contextExactSkillTrigger: "\u7cbe\u786e\u6280\u80fd\u914d\u7f6e Event \u5f15\u7528",
      contextInferredSkillTrigger: "\u63a8\u65ad\u6280\u80fd\u5f52\u5c5e",
      contextAuthoredPlaySoundAction: "\u521b\u4f5c PlaySound \u52a8\u4f5c",
      contextProjectileTrigger: "\u6295\u5c04\u7269\u751f\u547d\u5468\u671f\u97f3\u6548",
      contextSpawnerPreWarn: "\u654c\u4eba\u751f\u6210\u5668\u9884\u8b66\u97f3\u6548",
      contextNpcPatrolTrigger: "NPC \u5de1\u903b\u70b9\u97f3\u9891",
      contextCharacterInteraction: "\u89d2\u8272\u4ea4\u4e92\u8868\u6f14",
      contextPhysicsEnvironment: "\u7269\u7406 / \u73af\u5883",
      contextModelViewState: "ModelView \u72b6\u6001\u884c\u4e3a",
      contextInteractiveTrigger: "\u4ea4\u4e92\u7269\u4ef6\u89e6\u53d1",
      contextGlobalLifecycle: "\u5168\u5c40\u97f3\u9891\u751f\u547d\u5468\u671f",
      contextAudioCueTrigger: "Audio Cue \u884c\u4e3a Event",
      contextAuthoredConfig: "\u914d\u7f6e\u8868",
      contextManagedRuntime: "\u6258\u7ba1\u4ee3\u7801\u5b57\u9762\u91cf",
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
      relationMusicSwitch: "\u97f3\u4e50 Switch \u5206\u652f",
      relationMusicPlaylist: "\u97f3\u4e50\u64ad\u653e\u5217\u8868\u5206\u652f",
      relationMusicTrack: "\u97f3\u4e50\u8f68\u9053",
      relationMusicSource: "\u97f3\u4e50\u8f68\u9053\u97f3\u6e90",
      musicSwitchContainer: "\u97f3\u4e50 Switch \u5bb9\u5668",
      musicRandomSequenceContainer: "\u97f3\u4e50\u968f\u673a / \u5e8f\u5217\u5bb9\u5668",
      musicSegment: "\u97f3\u4e50\u7247\u6bb5",
      musicTrack: "\u97f3\u4e50\u8f68\u9053",
      possibleMedia: "\u53ef\u80fd\u5a92\u4f53",
      playRoots: "Play \u6839",
      typedTraversal: "\u7c7b\u578b\u5316\u904d\u5386",
      selectorEvidence: "\u9009\u62e9\u5668\u8bc1\u636e",
      actionDispatch: "Action \u6d3e\u53d1",
      actionOrdinal: "Action",
      serializedNoDelay: "\u672a\u5e8f\u5217\u5316\u5ef6\u8fdf",
      probabilityGate: "\u6982\u7387\u95e8",
      transitionTime: "\u8fc7\u6e21",
      fadeCurve: "\u6de1\u5165\u66f2\u7ebf",
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
    ownerUnresolvedAnimation: "contextOwnerUnresolvedAnimation",
    scripted: "contextScripted",
    levelScriptTrigger: "contextLevelScriptTrigger",
    radioTrigger: "contextRadioTrigger",
    exactSkillTrigger: "contextExactSkillTrigger",
    inferredSkillTrigger: "contextInferredSkillTrigger",
    authoredPlaySoundAction: "contextAuthoredPlaySoundAction",
    projectileTrigger: "contextProjectileTrigger",
    spawnerPreWarnTrigger: "contextSpawnerPreWarn",
    npcPatrolTrigger: "contextNpcPatrolTrigger",
    characterInteraction: "contextCharacterInteraction",
    physicsEnvironment: "contextPhysicsEnvironment",
    modelViewState: "contextModelViewState",
    interactiveTrigger: "contextInteractiveTrigger",
    globalLifecycle: "contextGlobalLifecycle",
    audioCueTrigger: "contextAudioCueTrigger",
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
    musicSwitchCandidate: "relationMusicSwitch",
    musicPlaylistCandidate: "relationMusicPlaylist",
    musicTrack: "relationMusicTrack",
    musicTrackSource: "relationMusicSource",
  };

  function taxonomyLabel(value) {
    return t(CONTEXT_LABEL_KEYS[value] || RELATION_LABEL_KEYS[value] || value);
  }

  function recordType(record, kind) {
    if (kind === "media") return "decodedMedia";
    if (recordCategory(record) === "control") return "controlEvent";
    return record?.foundInWwise ? "wwiseEvent" : "authoredEventReference";
  }

  function contextGroup(kind) {
    if (["characterSkill", "enemySkill", "buffPlaySoundAction", "projectileSoundField"].includes(kind)) return "gameplay";
    if (kind === "cutsceneTimeline") return "cutscene";
    if (["characterAnimation", "enemyAnimation", "animationCallbackOwnerUnresolved"].includes(kind)) return "animation";
    if (["levelScriptAudioAction", "levelScriptAudioCueBehaviorEvent", "levelScriptRadioTrigger"].includes(kind)) return "scripted";
    if (["table", "tableEventHash", "interactiveAudioTrigger", "interactiveComponentTrigger", "physicsAudioComponentEvent", "modelViewStateAudioEvent", "modelViewStatePositionAudioEvent", "audioGlobalConfigEvent", "audioGlobalConfigEventHash", "audioCueBehaviorEvent", "audioGlobalMusicCueBehaviorEvent", "spawnerPreWarnAudio", "patrolSubActionPlayAudio", "charInteractAudioEvent"].includes(kind)) return "authoredConfig";
    if (kind === "binaryManagedLiteral") return "managedRuntime";
    return "";
  }

  function recordContextTags(record, kind) {
    const tags = new Set(asArray(record?.contextGroups).filter(Boolean));
    const addContextKindTags = (contextKind) => {
      if (contextKind === "projectileSoundField") tags.add("projectileTrigger");
      if (contextKind === "spawnerPreWarnAudio") tags.add("spawnerPreWarnTrigger");
      if (contextKind === "patrolSubActionPlayAudio") tags.add("npcPatrolTrigger");
      if (contextKind === "charInteractAudioEvent") tags.add("characterInteraction");
      if (contextKind === "physicsAudioComponentEvent") tags.add("physicsEnvironment");
      if (["modelViewStateAudioEvent", "modelViewStatePositionAudioEvent"].includes(contextKind)) tags.add("modelViewState");
      if (["audioCueBehaviorEvent", "audioGlobalMusicCueBehaviorEvent", "levelScriptAudioCueBehaviorEvent"].includes(contextKind)) tags.add("audioCueTrigger");
      if (["interactiveAudioTrigger", "interactiveComponentTrigger"].includes(contextKind)) tags.add("interactiveTrigger");
      if (["audioGlobalConfigEvent", "audioGlobalConfigEventHash", "audioGlobalMusicCueBehaviorEvent"].includes(contextKind)) tags.add("globalLifecycle");
      if (contextKind === "animationCallbackOwnerUnresolved") tags.add("ownerUnresolvedAnimation");
      if (["levelScriptAudioAction", "levelScriptAudioCueBehaviorEvent", "levelScriptRadioTrigger"].includes(contextKind)) tags.add("levelScriptTrigger");
      if (contextKind === "levelScriptRadioTrigger") tags.add("radioTrigger");
    };
    for (const contextKind of asArray(record?.contextKinds)) addContextKindTags(contextKind);
    for (const status of asArray(record?.triggerBindingStatuses)) {
      if (status === "exactSkillConfig") tags.add("exactSkillTrigger");
      else if (status === "inferredSkillConfigOwner") tags.add("inferredSkillTrigger");
    }
    if (Number(record?.triggerPlaySoundActionCount || 0) > 0) tags.add("authoredPlaySoundAction");
    for (const context of asArray(record?.contexts)) {
      if (!context || typeof context !== "object") continue;
      const group = contextGroup(normalize(context.kind));
      if (group) tags.add(group);
      if (context.triggerBindingStatus === "exactSkillConfig") tags.add("exactSkillTrigger");
      else if (context.triggerBindingStatus === "inferredSkillConfigOwner") tags.add("inferredSkillTrigger");
      if (Number(context.triggerPlaySoundActionCount || 0) > 0) tags.add("authoredPlaySoundAction");
      addContextKindTags(context.kind);
    }
    for (const context of asArray(record?.radioTriggerContexts)) {
      if (!context || typeof context !== "object") continue;
      const group = contextGroup(normalize(context.kind));
      if (group) tags.add(group);
      addContextKindTags(context.kind);
    }
    if (Number(record?.radioTriggerContextCount || 0) > 0) {
      tags.add("scripted");
      tags.add("levelScriptTrigger");
      tags.add("radioTrigger");
    }
    if (Number(record?.playableCharacterAnimationOwnerCount || 0) > 1 || record?.animationContextScope === "sharedPlayableCharacters") {
      tags.add("sharedPlayableAnimation");
    }
    if (asArray(record?.animationFunctions).includes("OnCustomFootStep")) tags.add("footstepSystem");
    if (kind === "media") {
      if (record?.audioDialogKey || record?.audioDialogPath) tags.add("dialogMedia");
      const inheritedMediaTags = new Set([
        "gameplay", "cutscene", "animation", "scripted", "authoredConfig", "managedRuntime",
        "sharedPlayableAnimation", "footstepSystem", "ownerUnresolvedAnimation", "levelScriptTrigger", "radioTrigger", "projectileTrigger", "spawnerPreWarnTrigger", "npcPatrolTrigger", "characterInteraction", "physicsEnvironment", "modelViewState", "interactiveTrigger", "globalLifecycle", "audioCueTrigger",
      ]);
      for (const eventId of asArray(record?.eventIds)) {
        for (const tag of state.eventTaxonomyById.get(normalizeLower(eventId)) || []) {
          if (inheritedMediaTags.has(tag)) tags.add(tag);
        }
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
    const numericHashes = [record?.hash, record?.eventHash].filter((value) => Number.isInteger(Number(value)));
    const values = [
      recordTitle(record, kind), recordId(record, kind), recordCategory(record), recordScope(record), recordSource(record),
      record?.hash, record?.eventHash, ...numericHashes.map((value) => `0x${(Number(value) >>> 0).toString(16).padStart(8, "0")}`),
      record?.mediaId, record?.bankId, record?.bank, record?.rel, record?.path, record?.src,
      ...asArray(record?.eventIds), ...asArray(record?.mediaIds), ...asArray(record?.actionIds), ...asArray(record?.visitedObjectIds),
      ...asArray(record?.contextSearch), ...asArray(record?.radioTriggerSearch), ...asArray(record?.radioTriggerActions),
      ...asArray(record?.radioTriggerRoles), ...asArray(record?.bankPackages),
      ...asArray(taxonomy.contextTags).flatMap((value) => [value, taxonomyLabel(value)]),
      ...asArray(taxonomy.relationTags).flatMap((value) => [value, taxonomyLabel(value)]),
      ...asArray(record?.contexts).flatMap((context) => context && typeof context === "object" ? [
        context.kind, context.ownerId, context.groupId, context.storyKey, context.table, context.path,
        context.semanticRole, context.confidence, context.animationOwnershipScope, context.possibleMediaScope,
        context.modelId, context.subTemplateId, context.triggerStateId, context.triggerStateName,
        context.triggerCustomState, context.ownerKind, context.stateDirection, context.audioStateMask, context.description,
        context.componentIndex, context.sourceOffset, context.sourceFingerprint, ...asArray(context.sourcePaths),
        context.authoredEventId, context.spawnerConfigId, context.enemyLibraryIndex, context.enemyId,
        context.bornTemplateId, context.enemyLevel, context.spawnerEnemyKey, context.preWarnTime,
        context.preWarnEffectKey, ...asArray(context.preWarnEffectFixedRotation), ...asArray(context.bornBuffIds),
        context.charInteractPerformId, context.actionPhase, context.actionIndex, context.logicId,
        context.attachedActorType, context.charIndex, context.runtimeOwnerStatus,
        context.attachedActorResolutionStatus,
        context.definitionOwnerId, context.templatePath, context.componentTag, context.componentTagHex,
        context.componentOccurrenceIndex,
        context.propertyCount, context.authoredProperty, context.runtimeField,
        ...asArray(context.consumerIds), ...asArray(context.consumerAliasIds),
        ...asArray(context.interactiveTableSourcePaths), context.interactiveTableSha256,
        context.action, context.levelScriptId, context.sourcePath, context.sourceSha256,
        context.recordUid, context.recordLocalId, context.actionMapRole, context.eventName,
        context.triggerRole, context.sourceField,
        context.clipReachability, context.triggerBindingStatus, ...asArray(context.skillIds), ...asArray(context.actionKinds),
        ...asArray(context.triggerRequestEvidence), ...asArray(context.triggerRuntimeActivationStatuses),
        ...asArray(context.triggerRelationTypes), ...asArray(context.triggerOwnershipMethods),
        ...asArray(context.triggerEvidenceKinds), ...asArray(context.triggerBuffIds), ...asArray(context.triggerSourcePaths),
        ...asArray(context.triggerPlaySoundActions).flatMap((action) => action && typeof action === "object" ? Object.values(action).flat() : []),
        ...asArray(context.animationFunctions), ...asArray(context.animationClipContexts), ...asArray(context.animationClips),
      ] : []),
      ...asArray(record?.radioTableLineIdentities).flatMap((line) => line && typeof line === "object" ? [
        line.radioId, line.lineId, line.lineOrdinal, line.authoredIndex, line.audioOverride,
        line.actorNameId, line.is3D === true ? "3D" : (line.is3D === false ? "2D" : ""),
        line.source, line.audioOverrideIdentityKind, line.wwiseEventStatus,
      ] : []),
      ...asArray(record?.radioTriggerContexts).flatMap((context) => context && typeof context === "object" ? [
        context.kind, context.radioId, context.action, context.triggerRole, context.levelScriptId,
        context.sourcePath, context.sourceField, context.actionMapRole, context.audioDialogMatchEvidence,
        context.runtimeActivationStatus, context.wwiseEventStatus,
        ...Object.values(context.radioDefinition || {}), ...Object.values(context.radioLine || {}),
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
    const controlCatalog = state.index?.controlCatalog;
    if (controlCatalog && typeof controlCatalog === "object") panel.appendChild(controlCatalogSection(controlCatalog));
    const physicsAudioCatalog = state.index?.triggerCatalog?.physicsAudio;
    if (physicsAudioCatalog && typeof physicsAudioCatalog === "object") panel.appendChild(physicsAudioCatalogSection(physicsAudioCatalog));
    const modelViewStateCatalog = state.index?.triggerCatalog?.modelViewStateAudio;
    if (modelViewStateCatalog && typeof modelViewStateCatalog === "object") panel.appendChild(modelViewStateAudioCatalogSection(modelViewStateCatalog));
    const levelScriptRadioCatalog = state.index?.triggerCatalog?.levelScriptRadio;
    if (levelScriptRadioCatalog && typeof levelScriptRadioCatalog === "object") panel.appendChild(levelScriptRadioCatalogSection(levelScriptRadioCatalog));
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

  function controlCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("controlCatalog");
    section.appendChild(heading);
    const counts = catalog.counts && typeof catalog.counts === "object" ? catalog.counts : {};
    if (Object.keys(counts).length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [key, value] of Object.entries(counts)) grid.appendChild(statNode(humanize(key), typeof value === "number" ? formatNumber(value) : value));
      section.appendChild(grid);
    }
    const formatControlFields = (row) => Object.entries(row.fields || {}).map(([name, field]) => {
      let value = field?.value;
      if (field?.bindingKind === "dynamic" || field?.bindingKind === "output") {
        value = field.path || `${humanize(field.bindingKind)} source ${field.paramSource ?? "?"}`;
      } else if (field?.present === false) {
        value = "null";
      } else if (value && typeof value === "object") {
        value = JSON.stringify(value);
      }
      return `${name}=${value ?? "?"}`;
    }).join(", ");
    const groups = [
      ["rtpcParameters", asArray(catalog.rtpcParameters), (row) => `${row.parameterName || t("unknown")} / ${row.field || humanize(row.evidence || "")}`],
      ["physicsAudioRtpcParameters", asArray(catalog.physicsAudioRtpcParameters), (row) => `${row.parameterName || t("unknown")} / ${humanize(row.controlRole || "")} / ${row.definitionOwnerId || row.ownerId || "?"} / ${row.authoredProperty || "?"} -> ${row.runtimeField || "?"}`],
      ["modelViewStateRtpcParameters", asArray(catalog.modelViewStateRtpcParameters), (row) => `${row.parameterName || t("unknown")} / ${row.behaviorTagHex || "tag ?"} / ${row.controllerId || "?"} / ${row.modelAnimatorName || "?"} / ${row.layerName || "?"} / ${row.stateName || "?"} / mode ${row.rtpcBehaviourType ?? "?"} / ${row.dependFloatKey || "no blackboard key"}`],
      ["modelViewStateSpatialControls", asArray(catalog.modelViewStateSpatialControls), (row) => `${row.behaviorTagHex || "tag ?"} / ${row.controllerId || "?"} / ${row.modelAnimatorName || "?"} / ${row.layerName || "?"} / ${row.stateName || "?"} / direct ${String(Boolean(row.directSet))} / target ${row.targetClosePercentage ?? "?"} / ${row.dependFloatKey || "no blackboard key"}`],
      ["modelViewStateCustomAudioControls", asArray(catalog.modelViewStateCustomAudioControls), (row) => `${row.controlValue || '""'} / ${row.behaviorTagHex || "tag ?"} / ${row.controllerId || "?"} / ${row.modelAnimatorName || "?"} / ${row.layerName || "?"} / ${row.stateName || "?"} / ${humanize(row.wwiseEventStatus || "unresolved")}`],
      ["globalMusicCues", asArray(catalog.audioGlobalMusicCueRefs), (row) => `${row.field || t("unknown")} / ${row.cueHex || row.cueId || "?"} / ${humanize(row.definitionStatus || "unknown")}`],
      ["cueOperands", asArray(catalog.audioCueExpressionOperands), (row) => `${row.stringValue || t("unknown")} / ${row.cueHex || "?"} / ${humanize(row.expressionSide || "")} / ${row.expressionPath || ""}`],
      ["levelScriptCueInvocations", asArray(catalog.levelScriptAudioCueInvocations), (row) => `${row.cueName || t("unknown")} / ${row.cueHex || "?"} / ${humanize(row.definitionStatus || "unknown")} / ${row.levelScriptId || "?"} / ${humanize(row.action || "")}`],
      ["levelScriptDynamicBindings", asArray(catalog.levelScriptDynamicAudioBindings), (row) => `${row.levelScriptId || "?"} / ${humanize(row.action || "")} / ${row.sourceField || "?"} / ${row.binding?.path || humanize(row.resolutionStatus || "")}`],
      ["levelScriptControls", asArray(catalog.levelScriptAudioControls), (row) => `${humanize(row.action || "")} / ${humanize(row.controlRole || "")} / ${row.levelScriptId || "?"} / ${formatControlFields(row)}`],
      ["levelScriptDynamicControls", asArray(catalog.levelScriptDynamicControlBindings), (row) => `${row.levelScriptId || "?"} / ${humanize(row.action || "")} / ${row.sourceField || "?"} / ${row.binding?.path || humanize(row.resolutionStatus || "")}`],
      ["levelEventConditions", asArray(catalog.levelEventAudioConditions), (row) => `${row.type || row.id || t("unknown")} / union ${row.unionTagHex || "?"} / event key ${row.eventKey ?? "?"} / ${humanize(row.relationType || "")} / ${row.predicate || "?"} / authored occurrences ${formatNumber(row.authoredOccurrenceCount || 0)} / ${humanize(row.playbackRequestStatus || "")}`],
    ];
    for (const [labelKey, rows, formatRow] of groups) {
      if (!rows.length) continue;
      const details = document.createElement("details");
      details.className = "audio-runtime-system";
      const summary = document.createElement("summary");
      summary.textContent = `${t(labelKey)} (${formatNumber(rows.length)})`;
      const values = document.createElement("div");
      values.className = "audio-chip-list";
      for (const row of rows) {
        const chip = document.createElement("span");
        chip.textContent = formatRow(row);
        values.appendChild(chip);
      }
      details.append(summary, values);
      section.appendChild(details);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
    return section;
  }

  function physicsAudioCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("physicsAudioCatalog");
    section.appendChild(heading);
    const facts = [
      ["Definitions", catalog.physicsAudioDefinitions],
      ["Event requests", catalog.physicsAudioEventContexts],
      ["RTPC controls", catalog.physicsAudioRtpcControls],
      ["Configured consumers", catalog.physicsAudioConsumerIdentities],
      ["Aliases", catalog.physicsAudioAliasIdentities],
    ].filter(([, value]) => value !== undefined && value !== null);
    if (facts.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [label, value] of facts) grid.appendChild(statNode(label, formatNumber(value)));
      section.appendChild(grid);
    }
    for (const definition of asArray(catalog.definitions)) {
      if (!definition || typeof definition !== "object") continue;
      const details = document.createElement("details");
      details.className = "audio-runtime-system";
      const summary = document.createElement("summary");
      const consumers = asArray(definition.consumerIds).filter(Boolean);
      summary.textContent = `${definition.definitionOwnerId || t("unknown")} / ${definition.componentTagHex || definition.componentTag || "?"} / ${formatNumber(definition.propertyCount || 0)} properties / ${formatNumber(consumers.length)} consumers`;
      const values = document.createElement("div");
      values.className = "audio-chip-list";
      for (const property of asArray(definition.properties)) {
        if (!property || typeof property !== "object") continue;
        const chip = document.createElement("span");
        const rawValue = property.value === "" ? '""' : property.value;
        chip.textContent = `${property.authoredKey || "?"} -> ${property.runtimeField || "?"} = ${rawValue ?? "null"}`;
        values.appendChild(chip);
      }
      const evidence = document.createElement("p");
      evidence.className = "audio-detail-note";
      evidence.textContent = [
        consumers.length ? `consumers ${consumers.join(", ")}` : "",
        definition.sourceSha256 ? `SHA-256 ${definition.sourceSha256}` : "",
        definition.sourceOffset !== undefined ? `component 0x${Number(definition.sourceOffset).toString(16)}-0x${Number(definition.endOffset).toString(16)}` : "",
        ...asArray(definition.sourcePaths),
      ].filter(Boolean).join(" / ");
      details.append(summary, values, evidence);
      section.appendChild(details);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
    return section;
  }

  function modelViewStateAudioCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("modelViewStateAudioCatalog");
    section.appendChild(heading);
    const facts = [
      ["Controllers decoded", catalog.controllersDecoded],
      ["Controllers with audio", catalog.controllersWithAudio],
      ["Event behaviors (tag 0x0001)", catalog.eventBehaviorCount],
      ["Position Event behaviors (tag 0x0002)", catalog.positionEventBehaviorCount],
      ["RTPC behaviors (tag 0x0003)", catalog.rtpcBehaviorCount],
      ["Spatial behaviors (tag 0x0004)", catalog.spatialBehaviorCount],
      ["Custom-audio controls", catalog.customAudioControlCount],
      ["Exact InteractiveData associations", catalog.controllersWithTemplateAssociations],
    ].filter(([, value]) => value !== undefined && value !== null);
    if (facts.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [label, value] of facts) grid.appendChild(statNode(label, typeof value === "number" ? formatNumber(value) : value));
      section.appendChild(grid);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
    return section;
  }

  function levelScriptRadioCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("levelScriptRadioCatalog");
    section.appendChild(heading);
    const counts = catalog.counts && typeof catalog.counts === "object" ? catalog.counts : {};
    if (Object.keys(counts).length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [key, value] of Object.entries(counts)) {
        grid.appendChild(statNode(humanize(key), typeof value === "number" ? formatNumber(value) : value));
      }
      section.appendChild(grid);
    }
    const boundedGroups = [
      ["unresolvedRadioIds", catalog.unresolvedRadioIds, (row) => `${row.radioId || t("unknown")} / ${formatNumber(row.invocationCount || 0)} invocations / ${asArray(row.triggerRoles).map(humanize).join(", ") || "role unknown"}`],
      ["unresolvedRadioLines", catalog.unresolvedRadioLines, (row) => `${row.radioId || t("unknown")} / line ${Number(row.lineOrdinal ?? 0) + 1} / ${row.audioOverride || "audioOverride missing"} / ${humanize(row.resolutionStatus || "")}`],
      ["dynamicRadioBindings", catalog.dynamicRadioBindings, (row) => `${row.levelScriptId || "?"} / ${humanize(row.action || "")} / ${humanize(row.triggerRole || "")} / ${row.sourceField || "?"} / ${row.binding?.path || humanize(row.resolutionStatus || "")}`],
    ];
    for (const [labelKey, bounded, formatRow] of boundedGroups) {
      if (!bounded || typeof bounded !== "object") continue;
      const rows = asArray(bounded.items).filter((row) => row && typeof row === "object");
      const total = Number(bounded.totalCount || 0);
      if (!rows.length && !total) continue;
      const details = document.createElement("details");
      details.className = "audio-runtime-system";
      const summary = document.createElement("summary");
      summary.textContent = `${t(labelKey)} (${formatNumber(rows.length)} / ${formatNumber(total)}${bounded.truncated ? ", truncated" : ""})`;
      const values = document.createElement("div");
      values.className = "audio-chip-list";
      for (const row of rows) {
        const chip = document.createElement("span");
        chip.textContent = formatRow(row);
        values.appendChild(chip);
      }
      details.append(summary, values);
      section.appendChild(details);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
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
    for (const system of systems) {
      const card = document.createElement("article");
      card.className = "audio-runtime-system";
      const type = normalize(system.type ?? system.name ?? system.id) || t("unknown");
      const layer = normalize(system.layer);
      const meaning = normalize(system.meaning ?? system.description);
      const counts = [];
      if (asArray(system.fields).length) counts.push(`${asArray(system.fields).length} fields`);
      if (asArray(system.methods).length) counts.push(`${asArray(system.methods).length} methods`);
      if (system.enumValues && typeof system.enumValues === "object") counts.push(`${Object.keys(system.enumValues).length} enum values`);
      if (asArray(system.nativeAnchors).length) counts.push(`${asArray(system.nativeAnchors).length} native anchors`);
      if (asArray(system.nativeCallChains).length) counts.push(`${asArray(system.nativeCallChains).length} native call chains`);
      if (asArray(system.nativeStateGroups).length) counts.push(`${asArray(system.nativeStateGroups).length} Wwise state groups`);
      if (asArray(system.nativeStateTransitions).length) counts.push(`${asArray(system.nativeStateTransitions).length} audio-state masks`);
      card.innerHTML = `<div class="audio-runtime-system-head"><code>${esc(type)}</code>${layer ? `<span>${esc(layer)}</span>` : ""}</div>${meaning ? `<p>${esc(meaning)}</p>` : ""}${counts.length ? `<small>${esc(counts.join(" · "))}</small>` : ""}`;
      const layout = system.serializedLayout && typeof system.serializedLayout === "object" ? system.serializedLayout : null;
      const anchors = asArray(system.nativeAnchors).filter((row) => row && typeof row === "object");
      const callChains = asArray(system.nativeCallChains).filter((row) => row && typeof row === "object");
      const stateGroups = asArray(system.nativeStateGroups).filter((row) => row && typeof row === "object");
      const stateTransitions = asArray(system.nativeStateTransitions).filter((row) => row && typeof row === "object");
      const enumEntries = system.enumValues && typeof system.enumValues === "object"
        ? Object.entries(system.enumValues)
        : [];
      if (layout || anchors.length || callChains.length || stateGroups.length || stateTransitions.length || enumEntries.length) {
        const values = document.createElement("div");
        values.className = "audio-chip-list";
        if (layout) {
          const chip = document.createElement("span");
          chip.textContent = `${layout.unionTagHex || `tag ${layout.unionTag ?? "?"}`} / mc${layout.memberCount ?? "?"} / behavior type ${layout.behaviorType ?? "?"} / ${layout.dataType || "serialized data"}`;
          values.appendChild(chip);
        }
        for (const [name, value] of enumEntries) {
          const chip = document.createElement("span");
          const numeric = Number(value);
          const hex = Number.isFinite(numeric) ? ` / 0x${(numeric >>> 0).toString(16).padStart(8, "0")}` : "";
          chip.textContent = `${name} = ${value}${hex}`;
          values.appendChild(chip);
        }
        for (const anchor of anchors) {
          const chip = document.createElement("span");
          chip.textContent = `${anchor.role || "native"} / method ${anchor.methodIndex ?? "?"} / ${anchor.token || "token ?"} / VA ${anchor.virtualAddress || "?"}${anchor.type ? ` / ${anchor.type}` : ""}`;
          values.appendChild(chip);
        }
        if (system.runtimeExecutionStatus) {
          const chip = document.createElement("span");
          chip.textContent = `runtime execution ${humanize(system.runtimeExecutionStatus)}`;
          values.appendChild(chip);
        }
        if (system.nativeAnchorStatus) {
          const chip = document.createElement("span");
          chip.textContent = `native anchors ${humanize(system.nativeAnchorStatus)}`;
          values.appendChild(chip);
        }
        if (system.nativeCallChainStatus) {
          const chip = document.createElement("span");
          chip.textContent = `native call chains ${humanize(system.nativeCallChainStatus)}`;
          values.appendChild(chip);
        }
        if (system.nativeStateGroupStatus) {
          const chip = document.createElement("span");
          chip.textContent = `native state groups ${humanize(system.nativeStateGroupStatus)}`;
          values.appendChild(chip);
        }
        if (system.nativeStateTransitionStatus) {
          const chip = document.createElement("span");
          chip.textContent = `native state transitions ${humanize(system.nativeStateTransitionStatus)}`;
          values.appendChild(chip);
        }
        card.appendChild(values);
        for (const group of stateGroups) {
          const groupCard = document.createElement("div");
          groupCard.className = "audio-runtime-state-group";
          const recoveredName = normalize(group.recoveredName);
          const identity = recoveredName || normalize(group.field) || humanize(group.role || "state group");
          const title = document.createElement("strong");
          title.textContent = `${humanize(group.role || "state group")} · ${identity} · ${group.groupIdHex || group.groupId || "unknown id"}`;
          const detail = document.createElement("small");
          detail.textContent = [
            normalize(group.enumType),
            normalize(group.setterMethod),
            group.methodIndex !== undefined ? `method ${group.methodIndex}` : "",
            normalize(group.virtualAddress) ? `VA ${group.virtualAddress}` : "",
            humanize(group.nameEvidence || ""),
          ].filter(Boolean).join(" · ");
          groupCard.append(title, detail);
          card.appendChild(groupCard);
        }
        for (const transition of stateTransitions) {
          const transitionCard = document.createElement("div");
          transitionCard.className = "audio-runtime-state-group";
          const names = asArray(transition.stateNames).map(normalize).filter(Boolean);
          const title = document.createElement("strong");
          title.textContent = `${names.length ? names.join(" + ") : "audio state mask"} / ${transition.stateMaskHex || transition.stateMask || "unknown mask"}`;
          const detail = document.createElement("small");
          detail.textContent = [
            `${transition.registrationCount || 0} registrations`,
            asArray(transition.actionOrders).length ? `orders ${asArray(transition.actionOrders).join(" / ")}` : "",
            transition.isOneShot === false ? "persistent" : "",
            asArray(transition.registrationCallOffsets).length ? `call offsets ${asArray(transition.registrationCallOffsets).join(" / ")}` : "",
            humanize(transition.callbackTargetStatus || ""),
            humanize(transition.conditionInterpretationStatus || ""),
          ].filter(Boolean).join(" / ");
          transitionCard.append(title, detail);
          const registrations = asArray(transition.registrations).filter((row) => row && typeof row === "object");
          if (registrations.length) {
            const callbackList = document.createElement("div");
            callbackList.className = "audio-chip-list";
            for (const registration of registrations) {
              const chip = document.createElement("span");
              chip.textContent = [
                humanize(registration.conditionType || `condition ${registration.conditionTypeRaw ?? "?"}`),
                `order ${registration.actionOrder ?? "?"}`,
                normalize(registration.callbackMethod),
                registration.callbackMethodIndex !== undefined ? `method ${registration.callbackMethodIndex}` : "",
                normalize(registration.callbackVirtualAddress) ? `VA ${registration.callbackVirtualAddress}` : "",
                asArray(registration.directStateSetters).length
                  ? `direct setters ${asArray(registration.directStateSetters).join(" / ")}`
                  : "",
              ].filter(Boolean).join(" / ");
              callbackList.appendChild(chip);
            }
            transitionCard.appendChild(callbackList);
          }
          card.appendChild(transitionCard);
        }
        for (const chain of callChains) {
          const chainCard = document.createElement("div");
          chainCard.className = "audio-runtime-call-chain";
          const label = normalize(chain.label ?? chain.id) || "Native call chain";
          const stages = asArray(chain.stages).filter((row) => row && typeof row === "object");
          const branches = asArray(chain.branches).filter((row) => row && typeof row === "object");
          const title = document.createElement("strong");
          title.textContent = `${label}${stages.length ? ` · ${stages.length} stages` : ""}`;
          chainCard.appendChild(title);
          const stageList = document.createElement("div");
          stageList.className = "audio-chip-list";
          for (const stage of stages) {
            const chip = document.createElement("span");
            const identity = [normalize(stage.type), normalize(stage.method)].filter(Boolean).join(".");
            const anchor = [
              stage.methodIndex !== undefined ? `method ${stage.methodIndex}` : "",
              normalize(stage.virtualAddress) ? `VA ${stage.virtualAddress}` : "",
            ].filter(Boolean).join(" / ");
            chip.textContent = [
              humanize(stage.role || "stage"), identity, anchor, normalize(stage.relation),
            ].filter(Boolean).join(" · ");
            stageList.appendChild(chip);
          }
          for (const branch of branches) {
            const chip = document.createElement("span");
            chip.textContent = [
              `branch ${normalize(branch.label ?? branch.id) || "unknown"}`,
              normalize(branch.relation),
            ].filter(Boolean).join(" / ");
            stageList.appendChild(chip);
          }
          chainCard.appendChild(stageList);
          if (chain.boundary) {
            const boundary = document.createElement("small");
            boundary.textContent = normalize(chain.boundary);
            chainCard.appendChild(boundary);
          }
          card.appendChild(chainCard);
        }
      }
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
    if (context?.modelId) parts.push(`model ${context.modelId}`);
    if (context?.subTemplateId) parts.push(`sub-template ${context.subTemplateId}`);
    if (context?.triggerStateName || context?.triggerStateId !== undefined) {
      parts.push(`trigger state ${context.triggerStateName || "unknown"} (${context.triggerStateId ?? "?"})`);
    }
    if (context?.triggerCustomState) parts.push(`custom state ${context.triggerCustomState}`);
    if (context?.ownerKind) parts.push(`${context.ownerKind} ${context.ownerId || ""}`.trim());
    if (context?.componentIndex !== undefined) parts.push(`component ${context.componentIndex}`);
    if (context?.sourceOffset !== undefined) parts.push(`source offset 0x${Number(context.sourceOffset).toString(16)}`);
    if (context?.stateDirection) parts.push(`${context.stateDirection} state mask ${context.audioStateMask ?? "?"}`);
    if (context?.description) parts.push(context.description);
    if (context?.cueHex || context?.cueId !== undefined) parts.push(`cue ${context.cueHex || context.cueId}`);
    if (context?.globalMusicCueField) parts.push(`global cue ${context.globalMusicCueField}`);
    if (context?.handlerScope) parts.push(`${context.handlerScope} handler${context.levelId ? ` / level ${context.levelId}` : ""}`);
    if (context?.expressionPath) parts.push(`${context.expressionSide || "expression"} type ${context.exprType ?? "?"} / ${context.expressionPath}`);
    if (context?.projectileId) parts.push(`projectile ${context.projectileId}`);
    if (context?.projectileKey) parts.push(context.projectileKey);
    if (context?.soundField) parts.push(`${humanize(context.soundField)} / ${humanize(context.triggerPhase || "")}`);
    if (context?.spawnerConfigId) parts.push(`spawner ${context.spawnerConfigId}`);
    if (context?.enemyId) parts.push(`enemy ${context.enemyId}`);
    if (context?.bornTemplateId) parts.push(`born template ${context.bornTemplateId}`);
    if (context?.enemyLevel !== undefined) parts.push(`enemy level ${context.enemyLevel}`);
    if (context?.spawnerEnemyKey) parts.push(`spawn key ${context.spawnerEnemyKey}`);
    if (context?.preWarnTime !== undefined) parts.push(`pre-warning time ${context.preWarnTime}`);
    if (context?.preWarnEffectKey) parts.push(`effect ${context.preWarnEffectKey}`);
    if (context?.patrolId !== undefined) parts.push(`NPC patrol ${context.patrolId}`);
    if (context?.pointIndex !== undefined) parts.push(`point ${context.pointIndex} / action ${context.actionIndex ?? "?"}`);
    if (context?.patrolSubActionType !== undefined) parts.push(`patrol action type ${context.patrolSubActionType} / union ${context.subActionUnionTagHex || context.subActionUnionTag || "?"}`);
    if (context?.nativeConsumer) parts.push(context.nativeConsumer);
    if (context?.charInteractPerformId) parts.push(`perform ${context.charInteractPerformId}`);
    if (context?.actionPhase) parts.push(`${humanize(context.actionPhase)} action ${context.actionIndex ?? "?"}`);
    if (context?.logicId !== undefined) parts.push(`logic ${context.logicId}`);
    if (context?.attachedActorType !== undefined) parts.push(`attached actor type ${context.attachedActorType} / char index ${context.charIndex ?? "?"}`);
    if (context?.endStop !== undefined || context?.is2D !== undefined) parts.push(`end stop ${String(Boolean(context.endStop))} / 2D ${String(Boolean(context.is2D))}`);
    const preWarnRotation = asArray(context?.preWarnEffectFixedRotation);
    if (preWarnRotation.length) parts.push(`effect rotation ${preWarnRotation.join(", ")}`);
    if (context?.definitionOwnerId) parts.push(`physics definition ${context.definitionOwnerId}`);
    if (context?.templatePath) parts.push(context.templatePath);
    const physicsConsumers = asArray(context?.consumerIds).filter(Boolean);
    if (physicsConsumers.length) parts.push(`configured consumers ${physicsConsumers.join(", ")}`);
    if (context?.componentTagHex || context?.componentTag !== undefined) {
      parts.push(`component tag ${context.componentTagHex || context.componentTag} / mc${context.serializedMemberCount ?? "?"}`);
    }
    if (context?.componentOccurrenceIndex !== undefined) parts.push(`PhysicsAudio occurrence ${context.componentOccurrenceIndex}`);
    if (context?.authoredProperty) parts.push(`${context.authoredProperty} -> ${context.runtimeField || "runtime field unknown"}`);
    if (context?.propertySourceOffset !== undefined) parts.push(`property offset 0x${Number(context.propertySourceOffset).toString(16)}`);
    if (context?.interactiveTableSha256) parts.push(`InteractiveTable SHA-256 ${context.interactiveTableSha256}`);
    if (context?.controllerId) parts.push(`ModelView controller ${context.controllerId}`);
    if (context?.modelAnimatorName) parts.push(`model animator ${context.modelAnimatorName}`);
    if (context?.layerName || context?.layerFsmIndex !== undefined) parts.push(`layer ${context.layerName || "?"} / FSM ${context.layerFsmIndex ?? "?"}`);
    if (context?.stateName || context?.stateIndex !== undefined) parts.push(`state ${context.stateName || "?"} / index ${context.stateIndex ?? "?"} / type ${context.stateType ?? "?"}`);
    if (context?.behaviorTagHex || context?.behaviorTag !== undefined) parts.push(`behavior ${context.behaviorTagHex || context.behaviorTag} / mc${context.serializedMemberCount ?? "?"} / type ${context.behaviorType ?? "?"} / index ${context.behaviorIndex ?? "?"}`);
    if (context?.behaviorTime !== undefined) parts.push(`authored behavior time ${context.behaviorTime} / time-flow switch ${context.timeFlowSwitch ?? "?"}`);
    if (context?.audioNodeName) parts.push(`audio node ${context.audioNodeName}`);
    if (context?.normalAudioId !== undefined) parts.push(`normalAudioId int32 ${context.normalAudioId}`);
    if (context?.eAudioTriggerState !== undefined) parts.push(`audio trigger state ${context.eAudioTriggerState}`);
    const modelViewTemplates = asArray(context?.interactiveTemplateIds).filter(Boolean);
    if (modelViewTemplates.length) parts.push(`serialized InteractiveData associations ${modelViewTemplates.length === 1 ? modelViewTemplates[0] : `${modelViewTemplates[0]} +${modelViewTemplates.length - 1}`}`);
    const modelViewConsumers = asArray(context?.interactiveConsumerIds).filter(Boolean);
    if (modelViewConsumers.length) parts.push(`associated interactive identities ${modelViewConsumers.length === 1 ? modelViewConsumers[0] : `${modelViewConsumers[0]} +${modelViewConsumers.length - 1}`}`);
    if (context?.templateAssociationStatus) parts.push(humanize(context.templateAssociationStatus));
    const modelViewFingerprints = asArray(context?.sourceFingerprints).filter(Boolean);
    if (modelViewFingerprints.length) parts.push(`controller SHA-256 ${modelViewFingerprints.join(" / ")}`);
    if (kind === "levelScriptRadioTrigger") {
      const radioDefinition = context?.radioDefinition && typeof context.radioDefinition === "object" ? context.radioDefinition : {};
      const radioLine = context?.radioLine && typeof context.radioLine === "object" ? context.radioLine : {};
      if (context?.radioId) parts.push(`radio ${context.radioId}`);
      if (context?.action || context?.triggerRole) parts.push(`${humanize(context.action || "radio action")} / ${humanize(context.triggerRole || "role unknown")}`);
      if (context?.levelScriptId) parts.push(`LevelScript ${context.levelScriptId}`);
      const lifecycle = [];
      if (radioDefinition.radioType !== undefined) lifecycle.push(`type ${radioDefinition.radioType}`);
      if (radioDefinition.priority !== undefined) lifecycle.push(`priority ${radioDefinition.priority}`);
      if (radioDefinition.continueAfterDialog !== undefined) lifecycle.push(`continue after dialog ${String(Boolean(radioDefinition.continueAfterDialog))}`);
      if (radioDefinition.continueAfterRadio !== undefined) lifecycle.push(`continue after radio ${String(Boolean(radioDefinition.continueAfterRadio))}`);
      if (lifecycle.length) parts.push(`authored lifecycle ${lifecycle.join(" / ")}`);
      if (radioLine.is3D !== undefined) parts.push(`authored routing ${radioLine.is3D ? "3D" : "2D"}`);
      if (radioLine.actorNameId) parts.push(`actor ${radioLine.actorNameId}`);
      if (radioLine.lineOrdinal !== undefined) {
        const lineCount = Number(radioDefinition.lineCount);
        parts.push(`line order ${Number(radioLine.lineOrdinal) + 1}${Number.isFinite(lineCount) && lineCount > 0 ? ` / ${lineCount}` : ""} / ordinal ${radioLine.lineOrdinal}`);
      }
      if (radioLine.authoredIndex !== undefined) parts.push(`authored line index ${radioLine.authoredIndex}`);
      if (radioLine.lineId) parts.push(`line ${radioLine.lineId}`);
      if (radioLine.audioOverride) parts.push(`direct dialog media ${radioLine.audioOverride}`);
      if (context?.audioDialogMatchEvidence) parts.push(humanize(context.audioDialogMatchEvidence));
      if (context?.radioIdentityKind) parts.push(humanize(context.radioIdentityKind));
      if (context?.wwiseEventStatus || radioLine.wwiseEventStatus) parts.push(`Wwise Event ${humanize(context.wwiseEventStatus || radioLine.wwiseEventStatus)}`);
      if (radioDefinition.source) parts.push(radioDefinition.source);
      if (radioLine.source && radioLine.source !== radioDefinition.source) parts.push(radioLine.source);
    } else {
      if (context?.levelScriptId) parts.push(`LevelScript ${context.levelScriptId}`);
      if (context?.action) parts.push(humanize(context.action));
      if (context?.triggerRole) parts.push(`request role ${humanize(context.triggerRole)}`);
    }
    if (context?.sourceField) parts.push(context.sourceField);
    if (context?.actionMapRole) parts.push(context.actionMapRole);
    if (context?.recordUid || context?.recordLocalId !== undefined) parts.push(`record ${context.recordUid || "?"} / local ${context.recordLocalId ?? "?"}`);
    if (context?.sourcePath) parts.push(context.sourcePath);
    if (context?.sourceSha256) parts.push(`SHA-256 ${context.sourceSha256}`);
    for (const [fieldName, field] of Object.entries(context?.fields || {})) {
      if (!field || typeof field !== "object") continue;
      const value = field.value !== undefined
        ? (typeof field.value === "object" ? JSON.stringify(field.value) : String(field.value))
        : field.path || "";
      parts.push(`${field.sourceField || fieldName}: ${humanize(field.bindingKind || "unknown")}${value ? ` = ${value}` : ""}`);
    }
    if (context?.eventHash !== undefined) parts.push(`Event 0x${Number(context.eventHash).toString(16).padStart(8, "0")}`);
    if (context?.signedValue !== undefined) parts.push(`serialized int32 ${context.signedValue}`);
    if (context?.runtimeActivationStatus) parts.push(humanize(context.runtimeActivationStatus));
    const authoredSkillIds = asArray(context?.authoredSkillIds).filter(Boolean);
    if (authoredSkillIds.length) parts.push(`projectile template skills: ${authoredSkillIds.length === 1 ? authoredSkillIds[0] : `${authoredSkillIds[0]} +${authoredSkillIds.length - 1}`}`);
    if (context?.skillOwnershipStatus) parts.push(humanize(context.skillOwnershipStatus));
    if (context?.sourceJsonPath) parts.push(context.sourceJsonPath);
    if (context?.sourceRoot || context?.sourcePathId) parts.push(`${context.sourceRoot || "source"} PathID ${context.sourcePathId || "?"}`);
    if (context?.sourceFile) parts.push(`CAB ${context.sourceFile}`);
    if (context?.sourceVfsPath) parts.push(context.sourceVfsPath);
    if (context?.sourceFingerprint) parts.push(`source SHA-256 ${context.sourceFingerprint}`);
    if (context?.semanticPath) parts.push(context.semanticPath);
    const sourcePaths = asArray(context?.sourcePaths).filter(Boolean);
    if (sourcePaths.length) parts.push(sourcePaths.length === 1 ? sourcePaths[0] : `${sourcePaths[0]} +${sourcePaths.length - 1}`);
    if (context?.triggerBindingStatus) parts.push(humanize(context.triggerBindingStatus));
    const requestEvidence = asArray(context?.triggerRequestEvidence).filter(Boolean);
    if (requestEvidence.length) parts.push(requestEvidence.map(humanize).join(" / "));
    const activationStatuses = asArray(context?.triggerRuntimeActivationStatuses).filter(Boolean);
    if (activationStatuses.length) parts.push(activationStatuses.map(humanize).join(" / "));
    const triggerRelations = asArray(context?.triggerRelationTypes).filter(Boolean);
    if (triggerRelations.length) parts.push(triggerRelations.map(humanize).join(" / "));
    const triggerMethods = asArray(context?.triggerOwnershipMethods).filter(Boolean);
    if (triggerMethods.length) parts.push(triggerMethods.map(humanize).join(" / "));
    const triggerKinds = asArray(context?.triggerEvidenceKinds).filter(Boolean);
    if (triggerKinds.length) parts.push(triggerKinds.map(humanize).join(" / "));
    const triggerBuffIds = asArray(context?.triggerBuffIds).filter(Boolean);
    if (triggerBuffIds.length) parts.push(triggerBuffIds.length === 1 ? triggerBuffIds[0] : `${triggerBuffIds[0]} +${triggerBuffIds.length - 1}`);
    const triggerSourcePaths = asArray(context?.triggerSourcePaths).filter(Boolean);
    if (triggerSourcePaths.length) parts.push(triggerSourcePaths.length === 1 ? triggerSourcePaths[0] : `${triggerSourcePaths[0]} +${triggerSourcePaths.length - 1}`);
    const playSoundActions = asArray(context?.triggerPlaySoundActions).filter((value) => value && typeof value === "object");
    for (const action of playSoundActions) {
      const actionParts = [
        `PlaySound frame ${action.startFrame ?? "?"}-${action.endFrame ?? "?"}`,
        action.stopOnEnd ? `stop on end / ${action.stopFadeDurationMs ?? 0} ms fade` : "not stopped by this action's end",
        action.useTempEmitter ? "temporary emitter" : "",
        action.followMountPoint ? `follow mount ${action.mountPoint || "(unnamed)"}` : "",
        action.useWeaponMountPoint ? `weapon ${action.weaponIndex ?? "?"} / ${action.weaponMountPoint || "mount"}` : "",
        action.targetSelector ? `target ${action.targetSelector}` : "target settings unresolved",
        action.useTimeDilationPauseAndSeek ? "time-dilation pause/seek" : "",
      ].filter(Boolean);
      parts.push(actionParts.join(" / "));
    }
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
    if (Number(context?.customFootstepOccurrenceCount || 0) > 0) {
      parts.push(`OnCustomFootStep ${formatNumber(context.customFootstepOccurrenceCount)} callbacks / ${asArray(context.customFootstepParameterVariants).length} parameter variants`);
    }
    const clipContexts = asArray(context?.animationClipContexts).filter(Boolean);
    if (clipContexts.length) parts.push(clipContexts.map(humanize).join(" / "));
    if (context?.clipReachability) parts.push(`clip reachability: ${context.clipReachability}`);
    const clips = asArray(context?.animationClips).filter(Boolean);
    if (clips.length) parts.push(clips.length === 1 ? clips[0] : `${clips[0]} +${clips.length - 1}`);
    return [...new Set(parts.filter(Boolean))].join(" · ");
  }

  function radioTableLineLabel(line) {
    const parts = [];
    if (line?.radioId) parts.push(`radio ${line.radioId}`);
    if (line?.lineOrdinal !== undefined) parts.push(`line order ${Number(line.lineOrdinal) + 1} / ordinal ${line.lineOrdinal}`);
    if (line?.authoredIndex !== undefined) parts.push(`authored index ${line.authoredIndex}`);
    if (line?.lineId) parts.push(`line ${line.lineId}`);
    if (line?.actorNameId) parts.push(`actor ${line.actorNameId}`);
    if (line?.is3D !== undefined) parts.push(`authored routing ${line.is3D ? "3D" : "2D"}`);
    if (line?.audioOverride) parts.push(`direct dialog media ${line.audioOverride}`);
    if (line?.audioOverrideIdentityKind) parts.push(humanize(line.audioOverrideIdentityKind));
    if (line?.wwiseEventStatus) parts.push(`Wwise Event ${humanize(line.wwiseEventStatus)}`);
    if (line?.source) parts.push(line.source);
    return parts.join(" / ");
  }

  function selectorEvidenceSummary(record) {
    const actions = new Map();
    const containers = new Map();
    const musicNodes = new Map();
    const actionDetails = [];
    const selector = {
      nodes: 0, exact: 0, unresolved: 0, continuous: 0,
      packages: 0, nonEmptyPackages: 0, strictSubsetPackages: 0,
      packageChildRefs: 0, associations: 0, continuePlayback: 0,
      isFirstOnly: 0, nonzeroFadeOut: 0, nonzeroFadeIn: 0,
      defaultMissing: 0, outsideChildren: 0, unmappedChildren: 0,
      groupTypes: new Map(), switchModes: new Map(), parserStatuses: new Map(),
      groupIds: new Set(), groupIdsTruncated: false,
    };
    const randomSequence = {
      nodes: 0, exact: 0, unresolved: 0, playlistItems: 0,
      orderDiffers: 0, nonDefaultWeightItems: 0, nonDefaultWeightNodes: 0,
      nonUniformWeightNodes: 0, nonDefaultAvoid: 0, maxAvoid: 0,
      nonDefaultLoop: 0, globalScope: 0, continuous: 0, resetPlaylist: 0,
      modes: new Map(), randomModes: new Map(), transitions: new Map(), statuses: new Map(),
    };
    let unresolved = 0;
    for (const evidence of asArray(record?.evidence)) {
      const dispatch = evidence?.actionDispatchEvidence;
      if (dispatch && typeof dispatch === "object" && dispatch.timingClass) {
        actionDetails.push([
          `${t("actionDispatch")}: ${humanize(dispatch.timingClass)}`,
          `${formatNumber(dispatch.playbackActionCount || 0)} playback actions`,
          dispatch.explicitDelayActionCount ? `${formatNumber(dispatch.explicitDelayActionCount)} delayed` : "",
          dispatch.explicitTransitionActionCount ? `${formatNumber(dispatch.explicitTransitionActionCount)} transitions` : "",
          dispatch.probabilityGatedActionCount ? `${formatNumber(dispatch.probabilityGatedActionCount)} probability gates` : "",
        ].filter(Boolean).join(" / "));
      }
      for (const action of asArray(evidence?.actionEvidence)) {
        const operation = humanize(action?.operation || "unknown action");
        actions.set(operation, (actions.get(operation) || 0) + 1);
        if (action?.actionParserStatus !== "typedExactV150" || !["play", "playEvent"].includes(action?.operation)) continue;
        const delay = asArray(action?.delay?.baseValuesMs);
        const delayRanges = asArray(action?.delay?.modifierRangesMs);
        const transition = asArray(action?.transition?.baseValuesMs);
        const probability = asArray(action?.probability?.baseValuesPercent);
        const detail = [
          delay.length ? `delay ${delay.join(" / ")} ms` : t("serializedNoDelay"),
          delayRanges.length ? `delay range ${delayRanges.map((row) => `${row.minimum}-${row.maximum} ms`).join(" / ")}` : "",
          transition.length ? `${t("transitionTime")} ${transition.join(" / ")} ms` : "",
          probability.length ? `${t("probabilityGate")} ${probability.join(" / ")}%` : "",
          action?.fade?.curveLabel ? `${t("fadeCurve")} ${action.fade.curveLabel}` : "",
        ].filter(Boolean).join(" / ");
        actionDetails.push(`${t("actionOrdinal")} ${Number(action.eventActionOrdinal || 0) + 1} (${operation}): ${detail}`);
      }
      for (const container of asArray(evidence?.containerEvidence)) {
        const relation = normalize(container?.edgeKind) || "unknown";
        const current = containers.get(relation) || { count: 0, children: 0 };
        current.count += Number(container?.nodeCount || 1);
        current.children += Number(container?.childCount || 0);
        containers.set(relation, current);
        selector.nodes += Number(container?.selectorNodeCount || 0);
        selector.exact += Number(container?.typedSelectorNodeCount || 0);
        selector.unresolved += Number(container?.unresolvedSelectorNodeCount || 0);
        selector.continuous += Number(container?.continuousValidationNodeCount || 0);
        selector.packages += Number(container?.selectorPackageCount || 0);
        selector.nonEmptyPackages += Number(container?.nonEmptySelectorPackageCount || 0);
        selector.strictSubsetPackages += Number(container?.strictSubsetSelectorPackageCount || 0);
        selector.packageChildRefs += Number(container?.selectorPackageChildReferenceCount || 0);
        selector.associations += Number(container?.selectorAssociationCount || 0);
        selector.continuePlayback += Number(container?.continuePlaybackAssociationCount || 0);
        selector.isFirstOnly += Number(container?.isFirstOnlyAssociationCount || 0);
        selector.nonzeroFadeOut += Number(container?.nonzeroFadeOutAssociationCount || 0);
        selector.nonzeroFadeIn += Number(container?.nonzeroFadeInAssociationCount || 0);
        selector.defaultMissing += Number(container?.defaultValueMissingPackageCount || 0);
        selector.outsideChildren += Number(container?.mappedChildOutsideChildrenCount || 0)
          + Number(container?.associationChildOutsideChildrenCount || 0);
        selector.unmappedChildren += Number(container?.unmappedSelectorChildCount || 0);
        for (const [key, count] of Object.entries(container?.selectorGroupTypes || {})) {
          selector.groupTypes.set(key, (selector.groupTypes.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.selectorSwitchModes || {})) {
          selector.switchModes.set(key, (selector.switchModes.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.selectorParserStatuses || {})) {
          selector.parserStatuses.set(key, (selector.parserStatuses.get(key) || 0) + Number(count || 0));
        }
        for (const groupId of asArray(container?.selectorGroupIdsHex)) selector.groupIds.add(groupId);
        selector.groupIdsTruncated ||= !!container?.selectorGroupIdsTruncated;
        randomSequence.nodes += Number(container?.randomSequenceNodeCount || 0);
        randomSequence.exact += Number(container?.typedRandomSequenceNodeCount || 0);
        randomSequence.unresolved += Number(container?.unresolvedRandomSequenceNodeCount || 0);
        randomSequence.playlistItems += Number(container?.randomSequencePlaylistItemCount || 0);
        randomSequence.orderDiffers += Number(container?.playlistOrderDiffersFromChildrenCount || 0);
        randomSequence.nonDefaultWeightItems += Number(container?.nonDefaultWeightItemCount || 0);
        randomSequence.nonDefaultWeightNodes += Number(container?.nonDefaultWeightNodeCount || 0);
        randomSequence.nonUniformWeightNodes += Number(container?.nonUniformWeightNodeCount || 0);
        randomSequence.nonDefaultAvoid += Number(container?.nonDefaultAvoidRepeatNodeCount || 0);
        randomSequence.maxAvoid = Math.max(randomSequence.maxAvoid, Number(container?.maxAvoidRepeatCount || 0));
        randomSequence.nonDefaultLoop += Number(container?.nonDefaultLoopNodeCount || 0);
        randomSequence.globalScope += Number(container?.globalScopeRandomSequenceNodeCount || 0);
        randomSequence.continuous += Number(container?.continuousRandomSequenceNodeCount || 0);
        randomSequence.resetPlaylist += Number(container?.resetPlaylistNodeCount || 0);
        for (const [key, count] of Object.entries(container?.randomSequenceModes || {})) {
          randomSequence.modes.set(key, (randomSequence.modes.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.randomModes || {})) {
          randomSequence.randomModes.set(key, (randomSequence.randomModes.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.randomTransitionModes || {})) {
          randomSequence.transitions.set(key, (randomSequence.transitions.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.randomSequenceParserStatuses || {})) {
          randomSequence.statuses.set(key, (randomSequence.statuses.get(key) || 0) + Number(count || 0));
        }
      }
      for (const node of asArray(evidence?.musicNodeEvidence)) {
        const kind = normalize(node?.nodeKind) || `musicType${node?.objectType ?? "?"}`;
        const current = musicNodes.get(kind) || {
          count: 0, children: 0, sources: 0, selectionTypes: new Set(),
        };
        current.count += 1;
        current.children += Number(node?.childCount || 0);
        current.sources += Number(node?.sourceCount || 0);
        for (const label of asArray(node?.selectionTypeLabels).filter(Boolean)) current.selectionTypes.add(humanize(label));
        musicNodes.set(kind, current);
      }
      unresolved += asArray(evidence?.unresolvedNodes).length;
    }
    const values = [...actions].map(([operation, count]) => `${operation} × ${formatNumber(count)}`);
    for (const [relation, value] of containers) {
      values.push(`${taxonomyLabel(relation)}: ${formatNumber(value.count)} nodes / ${formatNumber(value.children)} child edges`);
    }
    if (selector.nodes) {
      const groupTypes = [...selector.groupTypes]
        .map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`)
        .join(" / ");
      const statuses = [...selector.parserStatuses]
        .map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`)
        .join(" / ");
      const groupIds = [...selector.groupIds];
      values.push([
        `Wwise Switch/State selectors: ${formatNumber(selector.nodes)} nodes`,
        `${formatNumber(selector.exact)} typed exact`,
        selector.unresolved ? `${formatNumber(selector.unresolved)} unresolved` : "",
        groupTypes,
        selector.continuous ? `${formatNumber(selector.continuous)} continuous-validation` : "",
        statuses,
      ].filter(Boolean).join(" / "));
      values.push([
        `Selector packages: ${formatNumber(selector.packages)}`,
        `${formatNumber(selector.nonEmptyPackages)} non-empty`,
        `${formatNumber(selector.strictSubsetPackages)} strict child subsets`,
        `${formatNumber(selector.packageChildRefs)} mapped child references`,
        selector.defaultMissing ? `${formatNumber(selector.defaultMissing)} defaults absent from packages` : "",
        selector.outsideChildren ? `${formatNumber(selector.outsideChildren)} references outside reciprocal Children` : "",
        selector.unmappedChildren ? `${formatNumber(selector.unmappedChildren)} reciprocal Children unmapped` : "",
      ].filter(Boolean).join(" / "));
      values.push([
        `Selector associations: ${formatNumber(selector.associations)}`,
        [...selector.switchModes].map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`).join(" / "),
        selector.continuePlayback ? `${formatNumber(selector.continuePlayback)} continue playback` : "",
        selector.isFirstOnly ? `${formatNumber(selector.isFirstOnly)} first-only` : "",
        selector.nonzeroFadeOut ? `${formatNumber(selector.nonzeroFadeOut)} nonzero fade-out` : "",
        selector.nonzeroFadeIn ? `${formatNumber(selector.nonzeroFadeIn)} nonzero fade-in` : "",
      ].filter(Boolean).join(" / "));
      if (groupIds.length) {
        values.push(`Selector group ids: ${groupIds.slice(0, 12).join(" / ")}${selector.groupIdsTruncated || groupIds.length > 12 ? " / more omitted" : ""}`);
      }
      values.push("Runtime selector value and audio-object state were not observed; every mapped child remains only a possible branch.");
    }
    if (randomSequence.nodes) {
      const summarizeCounts = (counts) => [...counts]
        .map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`)
        .join(" / ");
      values.push([
        `Wwise Random/Sequence policy: ${formatNumber(randomSequence.nodes)} nodes`,
        `${formatNumber(randomSequence.exact)} typed exact`,
        randomSequence.unresolved ? `${formatNumber(randomSequence.unresolved)} unresolved` : "",
        summarizeCounts(randomSequence.modes),
        summarizeCounts(randomSequence.randomModes),
        summarizeCounts(randomSequence.transitions),
        summarizeCounts(randomSequence.statuses),
      ].filter(Boolean).join(" / "));
      values.push([
        `Playlists: ${formatNumber(randomSequence.playlistItems)} weighted items`,
        randomSequence.orderDiffers ? `${formatNumber(randomSequence.orderDiffers)} playlist orders differ from Children` : "",
        randomSequence.nonDefaultWeightItems ? `${formatNumber(randomSequence.nonDefaultWeightItems)} non-default weights across ${formatNumber(randomSequence.nonDefaultWeightNodes)} nodes` : "",
        randomSequence.nonUniformWeightNodes ? `${formatNumber(randomSequence.nonUniformWeightNodes)} non-uniform pools` : "",
        randomSequence.nonDefaultAvoid ? `${formatNumber(randomSequence.nonDefaultAvoid)} non-default avoid-repeat nodes (max ${formatNumber(randomSequence.maxAvoid)})` : "",
        randomSequence.nonDefaultLoop ? `${formatNumber(randomSequence.nonDefaultLoop)} non-default loop nodes` : "",
        randomSequence.globalScope ? `${formatNumber(randomSequence.globalScope)} global-scope nodes` : "",
        randomSequence.continuous ? `${formatNumber(randomSequence.continuous)} continuous nodes` : "",
        randomSequence.resetPlaylist ? `${formatNumber(randomSequence.resetPlaylist)} reset-on-play nodes` : "",
      ].filter(Boolean).join(" / "));
      values.push("Runtime random seed, shuffle history, avoid-repeat history, Sequence cursor, and reset timing were not observed; playlist rows describe policy, not a selected leaf.");
    }
    for (const detail of actionDetails) values.push(detail);
    for (const [kind, value] of musicNodes) {
      const detail = [
        `${formatNumber(value.count)} nodes`,
        value.children ? `${formatNumber(value.children)} children` : "",
        value.sources ? `${formatNumber(value.sources)} sources` : "",
        value.selectionTypes.size ? [...value.selectionTypes].join(" / ") : "",
      ].filter(Boolean).join(" / ");
      values.push(`${taxonomyLabel(kind)}: ${detail}`);
    }
    if (unresolved) values.push(`${t("relationPartialGraph")}: ${formatNumber(unresolved)} unresolved nodes`);
    return values;
  }

  function customFootstepParameterSummary(record) {
    return asArray(record?.customFootstepParameterVariants)
      .filter((variant) => variant && typeof variant === "object")
      .map((variant) => {
        const fields = [
          `${formatNumber(variant.occurrenceCount || 0)} callbacks`,
          `raw int ${variant.rawInt ?? "?"}`,
          `raw float ${variant.rawFloat ?? "?"}`,
          `foot ${variant.footSide || "?"}`,
          `VFX ${variant.vfxType || "?"}`,
          `filter ${variant.playbackFilter || "?"}`,
          variant.customWeightThreshold !== null && variant.customWeightThreshold !== undefined
            ? `custom weight >= ${variant.customWeightThreshold}`
            : "float inactive for playback filter",
          `VFX weight >= ${variant.runtimeVfxWeightThreshold ?? 0.5}`,
        ];
        if (variant.decodeStatus && variant.decodeStatus !== "exactCurrentBuild") fields.push(humanize(variant.decodeStatus));
        return fields.join(" / ");
      });
  }

  function customFootstepRuntimeSummary() {
    const model = state.index?.customFootstepModel;
    if (!model || typeof model !== "object") return [];
    const corpus = model.corpus || {};
    const values = [
      `${formatNumber(corpus.occurrenceCount || 0)} callbacks / ${formatNumber(corpus.eventCount || 0)} canonical Events / ${formatNumber(corpus.parameterVariantCount || 0)} raw parameter variants`,
    ];
    for (const anchor of asArray(model.nativeAnchors)) {
      if (!anchor || typeof anchor !== "object") continue;
      values.push(`${anchor.type || "native"}.${anchor.method || "?"} ${anchor.token || ""} @ ${anchor.virtualAddress || "?"}`.trim());
    }
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
          [t("radioTableLines"), raw.radioTableLineCount],
          [t("radioTriggerContextCoverage"), raw.radioTriggerContextCount !== undefined
            ? `${formatNumber(raw.radioTriggerContextStoredCount || 0)} stored / ${formatNumber(raw.radioTriggerContextCount || 0)} total${raw.radioTriggerContextsTruncated ? " / truncated" : ""}`
            : ""],
        ];
    const grid = document.createElement("div");
    grid.className = "audio-facts";
    for (const [label, value] of facts) if (value !== undefined && value !== null && value !== "") grid.appendChild(factNode(label, value));
    panel.appendChild(grid);

    if (record.contextTags.length) panel.appendChild(chipSection(t("contextGroups"), record.contextTags.map(taxonomyLabel)));
    if (record.relationTags.length) panel.appendChild(chipSection(t("relation"), record.relationTags.map(taxonomyLabel)));
    const selectorEvidence = selectorEvidenceSummary(raw);
    if (selectorEvidence.length) panel.appendChild(chipSection(t("selectorEvidence"), selectorEvidence));
    const customFootstepParameters = customFootstepParameterSummary(raw);
    if (customFootstepParameters.length) {
      panel.appendChild(chipSection(t("customFootstepParameters"), customFootstepParameters));
      panel.appendChild(chipSection(t("customFootstepNativeAnchors"), customFootstepRuntimeSummary()));
      const boundary = state.index?.customFootstepModel?.runtimeSelectorBoundary;
      if (boundary) panel.appendChild(noteSection(t("customFootstepRuntime"), boundary));
    }

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
    const radioTableLines = asArray(raw.radioTableLineIdentities)
      .filter((value) => value && typeof value === "object")
      .map(radioTableLineLabel)
      .filter(Boolean);
    if (radioTableLines.length) panel.appendChild(chipSection(t("radioTableLines"), radioTableLines));
    const radioTriggerContexts = asArray(raw.radioTriggerContexts)
      .filter((value) => value && typeof value === "object")
      .map(contextEvidenceLabel)
      .filter(Boolean);
    if (radioTriggerContexts.length) panel.appendChild(chipSection(t("radioTriggerContexts"), radioTriggerContexts));
    if (radioTableLines.length || Number(raw.radioTriggerContextCount || 0) > 0) {
      const radioBoundary = state.index?.triggerCatalog?.levelScriptRadio?.evidenceBoundary;
      if (radioBoundary) panel.appendChild(noteSection(t("runtimeBoundary"), radioBoundary));
    }

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
    }).filter((candidate) => {
      if (!candidate.src) return false;
      const identity = `${candidate.id}\u0000${candidate.src}`;
      if (seen.has(identity)) return false;
      seen.add(identity);
      return true;
    });
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
      const card = document.createElement("details");
      card.className = "audio-player-card";
      const head = document.createElement("summary");
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
        t("expandToLoadPlayer"),
      ].filter(Boolean).join(" · ");
      head.append(title, meta);
      const playerHost = document.createElement("div");
      let materialized = false;
      card.addEventListener("toggle", () => {
        if (!card.open || materialized) return;
        materialized = true;
        const audio = document.createElement("audio");
        audio.preload = "none";
        audio.controls = true;
        audio.src = candidate.src;
        const player = window.WebUI?.createMediaPlayer ? window.WebUI.createMediaPlayer(audio) : audio;
        playerHost.appendChild(player);
      });
      card.append(head, playerHost);
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
