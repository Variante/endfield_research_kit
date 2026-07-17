(() => {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const CARD_W = 252;
  const CARD_H = 164;
  const state = {
    initialized: false,
    language: "CN",
    index: null,
    names: {},
    filtered: [],
    missionId: "e7m3",
    mission: null,
    localized: null,
    selectedQuestId: "",
    missionCache: new Map(),
    localizedCache: new Map(),
    indexPromise: null,
    request: 0,
    missionRequest: 0,
    controller: null,
    transform: { x: 24, y: 24, scale: 1 },
    layout: null,
    dragging: null,
    suppressGraphClickUntil: 0,
    expandedMissionTypes: new Set(["e"]),
  };

  const TEXT = {
    en: {
      eyebrow: "EXPERIMENTAL · CLIENT / SERVER EVIDENCE",
      title: "Mission Pipeline",
      scope: "Authored quest structure with an explicit native client/server boundary.",
      warning: "Predecessor arrows are client-visible prerequisites. The server still decides which quest state to synchronize next.",
      missions: "missions",
      quests: "quests",
      search: "Search missions",
      searchPlaceholder: "Mission id, name, level, or condition",
      structure: "Structure",
      anyStructure: "Any structure",
      caseStudies: "Evidence case studies",
      fanout: "Has fan-out",
      joins: "Has joins",
      exactFinish: "Exact dialog finish",
      serverOwned: "Server placeholder",
      failure: "Failure condition",
      shown: "shown",
      selectMission: "Select a mission to inspect its pipeline.",
      showHidden: "Show internal/hidden quests",
      dependencies: "Show quest-state condition edges",
      edgeLabels: "Show edge meaning labels",
      controlHelp: "Internal/hidden includes showMode=1000 quests. Quest-state condition edges are dashed CheckQuestState references, not progression arrows. Edge meaning labels name prerequisite and condition edges.",
      orientation: "Orientation",
      auto: "Auto",
      leftRight: "Left → right",
      topBottom: "Top → bottom",
      fit: "Fit graph",
      zoomOut: "Zoom out",
      zoomIn: "Zoom in",
      center: "Center selected",
      dragHint: "Drag anywhere on the graph to pan. Scroll to zoom.",
      serverGateway: "S",
      serverGatewayTitle: "Server-authoritative transition: completion does not prove which successor the server will start.",
      predecessor: "authored predecessor",
      conditionDependency: "quest-state condition",
      externalDependency: "external mission",
      main: "main",
      hidden: "hidden",
      flow: "flow",
      flowCaveat: "Authored lane tag; not proof of exclusivity.",
      clientToServerDialog: "C→S dialog",
      clientToServerProgress: "C→S progress",
      serverGate: "server gate",
      unresolvedSend: "C→S ?",
      serverToClient: "S→C state",
      noObjective: "No exported objective",
      inspectQuest: "Quest runtime trace",
      authority: "Condition authority",
      authoredFields: "Authored fields",
      objectives: "Objectives and gates",
      clientActions: "Client actions after synchronized state",
      source: "Source",
      protocol: "Selected quest network pipeline",
      asyncCaveat: "These are asynchronous state messages, not a proven synchronous request/response pair.",
      playerWorld: "Player / world",
      client: "Unity client",
      server: "Game server",
      activation: "Activation",
      observe: "Observe / act",
      outbound: "Outbound",
      resolve: "Authoritative decision",
      returnState: "Return state",
      successor: "Next activation",
      activationMessage: "SC_QUEST_STATE_UPDATE { questId, questState = 2 }",
      activationHandler: "StartQuest binds objectives and callbacks",
      worldEvent: "Player/world event satisfies or changes an objective condition.",
      synchronizedHistory: "Reads server-synchronized dialog history.",
      synchronizedState: "Reads server-synchronized quest/mission state.",
      clientObserved: "A client evaluator observes this condition; final completion remains server-authoritative.",
      mixedAuthority: "Combines conditions from more than one authority source.",
      unknownAuthority: "Evaluation ownership is not proven.",
      dialogSend: "CS_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
      dialogSendDetail: "Exact outbound payload shape proven in the native client.",
      serverOwnedDetail: "GameConditionServerPlaceHolder is owned by the server; no condition-specific client send is expected here.",
      unresolvedDetail: "The exact condition-specific progress/request packet has not been mapped. Do not infer it from a local callback.",
      opaquePolicy: "Validate progress and choose successor(s). Policy is not present in the examined client methods.",
      succeedMessage: "SC_QUEST_STATE_UPDATE { questId, questState = 3 }",
      succeedHandler: "SucceedQuest marks the local quest complete",
      failMessage: "SC_QUEST_FAILED → FailQuest when applicable",
      successorDetail: "A later state = 2 update starts each server-selected successor.",
      exact: "exact",
      anyFinish: "any finish",
      finish: "finish",
      dialog: "dialog",
      state: "state",
      condition: "condition",
      evidence: "Evidence overlay",
      confidence: "confidence",
      noCase: "No curated playback/native case note for this mission; the authored graph remains available.",
      missionHandshake: "Mission-level handshake",
      acceptRequest: "C→S  CS_ACCEPT_MISSION { missionId }",
      acceptReturn: "S→C  SC_MISSION_STATE_UPDATE { missionState, succeedId, properties… }",
      acceptCaveat: "No paired SC_ACCEPT_MISSION exists in this protocol; wait for the asynchronous mission-state push.",
      loading: "Loading mission pipeline…",
      loadingMission: "Loading mission…",
      loadError: "Mission pipeline data could not be loaded.",
      retry: "Retry",
      noMatches: "No missions match these filters.",
      noVisibleQuests: "No quests are visible with the current graph filters.",
      join: "join",
      activeJoin: "active AND",
      roots: "entries",
      branches: "fan-outs",
      exactFinishes: "exact finishes",
      serverPlaceholders: "server gates",
      graph: "Quest graph",
      nativeBoundary: "Native boundary",
      exchanges: "exchanges",
      openEvidence: "Show native evidence",
      nativeConfidence: "native-proven",
      dialogExchange: "Dialog history",
      dialogEcho: "SC_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
      progressSend: "CS_UPDATE_QUEST_OBJECTIVE { questId, conditionId, value, isAdd=false }",
      progressReturn: "SC_QUEST_OBJECTIVES_UPDATE { conditionId, values, isComplete, descriptionIndex }",
      progressCaveat: "Sent when a bound client-side subcondition callback changes; the later state=3 push remains authoritative completion.",
      progressNative: "OnSubConditionProgressChanged (0x183a6fc20) constructs and sends this absolute-value operation.",
      missionDescription: "Mission description",
      descriptionInherited: "mission-level text",
      descriptionOverride: "quest-specific override",
      noDescription: "No localized mission description is exported.",
      storyFiles: "Attached Story files",
      storyCount: "Story",
      openInStory: "Open in Story",
      storyEvidence: "Only direct quest references and uniquely resolved LevelData/NPC links are attached; same-mission files are not assigned to a block without evidence.",
      noStoryFiles: "No Story file is directly attached to this quest block.",
    },
    zh: {
      eyebrow: "实验视图 · 客户端 / 服务器证据",
      title: "任务管线",
      scope: "展示任务节点结构，并明确标出原生客户端与服务器之间的边界。",
      warning: "前置箭头只表示客户端可见的条件关系；下一个同步到客户端的任务状态仍由服务器决定。",
      missions: "个任务",
      quests: "个任务节点",
      search: "搜索任务",
      searchPlaceholder: "任务 ID、名称、关卡或条件",
      structure: "结构",
      anyStructure: "全部结构",
      caseStudies: "证据案例",
      fanout: "包含分流",
      joins: "包含汇合",
      exactFinish: "精确对话结局",
      serverOwned: "服务器占位条件",
      failure: "失败条件",
      shown: "已显示",
      selectMission: "选择一个任务以检查其执行管线。",
      showHidden: "显示内部/隐藏节点",
      dependencies: "显示任务状态条件线",
      edgeLabels: "显示连线含义标签",
      controlHelp: "内部/隐藏节点包含 showMode=1000 的作者节点；任务状态条件线是 CheckQuestState 产生的紫色虚线，不是任务推进箭头；连线含义标签会标明前置关系或条件引用。",
      orientation: "方向",
      auto: "自动",
      leftRight: "从左到右",
      topBottom: "从上到下",
      fit: "适配画布",
      zoomOut: "缩小",
      zoomIn: "放大",
      center: "居中当前节点",
      dragHint: "拖动图中任意位置平移；直接滚动鼠标滚轮缩放。",
      serverGateway: "服",
      serverGatewayTitle: "服务器控制的状态转换：完成前置节点不等于客户端能够决定后继节点。",
      predecessor: "前置任务关系",
      conditionDependency: "任务状态条件",
      externalDependency: "外部任务",
      main: "主线",
      hidden: "隐藏",
      flow: "流",
      flowCaveat: "这是作者设置的分层标签，不代表互斥。",
      clientToServerDialog: "客→服 对话",
      clientToServerProgress: "客→服 进度",
      serverGate: "服务端条件",
      unresolvedSend: "客→服 ?",
      serverToClient: "服→客 状态",
      noObjective: "没有导出的目标",
      inspectQuest: "任务运行轨迹",
      authority: "条件归属",
      authoredFields: "原始字段",
      objectives: "目标与条件门",
      clientActions: "状态同步后的客户端动作",
      source: "来源",
      protocol: "所选任务节点的网络管线",
      asyncCaveat: "这些是异步状态消息，不应理解为已证明的同步请求/响应对。",
      playerWorld: "玩家 / 世界",
      client: "Unity 客户端",
      server: "游戏服务器",
      activation: "激活",
      observe: "观察 / 操作",
      outbound: "发往服务器",
      resolve: "权威判定",
      returnState: "返回状态",
      successor: "后继激活",
      activationMessage: "SC_QUEST_STATE_UPDATE { questId, questState = 2 }",
      activationHandler: "StartQuest 绑定目标和回调",
      worldEvent: "玩家或世界事件满足、改变任务条件。",
      synchronizedHistory: "读取服务器同步的对话完成历史。",
      synchronizedState: "读取服务器同步的任务/使命状态。",
      clientObserved: "客户端条件器观察此条件；最终完成状态仍由服务器决定。",
      mixedAuthority: "组合了多个不同归属来源的条件。",
      unknownAuthority: "尚未证明条件的执行归属。",
      dialogSend: "CS_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
      dialogSendDetail: "原生客户端已证明的精确出站字段。",
      serverOwnedDetail: "GameConditionServerPlaceHolder 由服务器判定，此处不预期特定的客户端条件消息。",
      unresolvedDetail: "尚未定位该条件对应的精确进度/请求消息；不能从本地回调推断网络协议。",
      opaquePolicy: "验证进度并选择后继节点；检查过的客户端方法中没有这项策略。",
      succeedMessage: "SC_QUEST_STATE_UPDATE { questId, questState = 3 }",
      succeedHandler: "SucceedQuest 在客户端标记完成",
      failMessage: "适用时：SC_QUEST_FAILED → FailQuest",
      successorDetail: "服务器之后为每个选中的后继节点发送 state = 2。",
      exact: "精确",
      anyFinish: "任意结局",
      finish: "结局",
      dialog: "对话",
      state: "状态",
      condition: "条件",
      evidence: "证据叠加",
      confidence: "置信度",
      noCase: "此任务没有整理好的录像/原生案例注释，但原始结构仍可查看。",
      missionHandshake: "任务级握手",
      acceptRequest: "客→服  CS_ACCEPT_MISSION { missionId }",
      acceptReturn: "服→客  SC_MISSION_STATE_UPDATE { missionState, succeedId, properties… }",
      acceptCaveat: "协议中没有配对的 SC_ACCEPT_MISSION；客户端异步等待任务状态推送。",
      loading: "正在加载任务管线…",
      loadingMission: "正在加载任务…",
      loadError: "无法加载任务管线数据。",
      retry: "重试",
      noMatches: "没有匹配筛选条件的任务。",
      noVisibleQuests: "当前图筛选条件下没有可见节点。",
      join: "汇合",
      activeJoin: "主动 AND",
      roots: "入口",
      branches: "分流",
      exactFinishes: "精确结局",
      serverPlaceholders: "服务端条件",
      graph: "任务节点图",
      nativeBoundary: "原生实现边界",
      exchanges: "项消息",
      openEvidence: "显示原生证据",
      nativeConfidence: "原生代码已证明",
      dialogExchange: "对话历史同步",
      dialogEcho: "SC_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
      progressSend: "CS_UPDATE_QUEST_OBJECTIVE { questId, conditionId, value, isAdd=false }",
      progressReturn: "SC_QUEST_OBJECTIVES_UPDATE { conditionId, values, isComplete, descriptionIndex }",
      progressCaveat: "绑定的客户端子条件回调变化时发送；之后的 state=3 推送仍是权威完成状态。",
      progressNative: "OnSubConditionProgressChanged（0x183a6fc20）构造并发送这个绝对值操作。",
      missionDescription: "任务详细描述",
      descriptionInherited: "任务级描述",
      descriptionOverride: "节点专用描述",
      noDescription: "没有导出本地化的任务详细描述。",
      storyFiles: "关联的剧情文件",
      storyCount: "剧情",
      openInStory: "在剧情页打开",
      storyEvidence: "只附加该任务节点直接引用、或由 LevelData/NPC 唯一解析出的剧情文件；没有证据时，不会把同任务的所有文件都塞进每个节点。",
      noStoryFiles: "这个任务节点没有直接关联的剧情文件。",
    },
  };

  const app = () => document.querySelector("#mission-pipeline-app");
  const byId = (id) => document.querySelector(`#${id}`);
  const locale = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").toLowerCase().startsWith("en") ? "en" : "zh";
  const t = (key) => (TEXT[locale()] || TEXT.en)[key] || TEXT.en[key] || key;
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const normalize = (value) => String(value || "").trim().toLowerCase();
  const plainText = (value) => String(value || "")
    .replace(/<@[^>]*>/g, "")
    .replace(/<\/[^>]+>/g, "")
    .replace(/<[^>]+>/g, "")
    .replaceAll("\\n", " ")
    .trim();

  function naturalQuestNumber(id) {
    const match = String(id || "").match(/_q#(\d+)/);
    return match ? Number(match[1]) : Number.MAX_SAFE_INTEGER;
  }

  function questShortLabel(id) {
    const suffix = String(id || "").split("_q#")[1];
    if (!suffix) return String(id || "?");
    return /^\d+$/.test(suffix) ? `Q${suffix}` : suffix;
  }

  function init() {
    if (state.initialized || !app()) return Boolean(app());
    state.initialized = true;
    app().innerHTML = `
      <div class="mp-shell">
        <header class="mp-hero">
          <div class="mp-hero-copy">
            <p id="mp-eyebrow" class="mp-eyebrow"></p>
            <div class="mp-title-line"><h1 id="mp-title"></h1><span class="mp-experimental">EXPERIMENTAL</span></div>
            <p id="mp-scope" class="mp-scope"></p>
          </div>
          <div id="mp-corpus" class="mp-corpus" role="status" aria-live="polite"></div>
        </header>
        <div id="mp-warning" class="mp-boundary-warning" role="note"></div>
        <div class="mp-layout">
          <aside class="mp-browser" aria-label="Mission browser">
            <div class="mp-browser-controls">
              <label class="mp-field"><span id="mp-search-label"></span><input id="mp-search" type="search" autocomplete="off"></label>
              <label class="mp-field"><span id="mp-structure-label"></span><select id="mp-structure"></select></label>
            </div>
            <p id="mp-results" class="mp-results" role="status" aria-live="polite"></p>
            <div id="mp-mission-list" class="mp-mission-list" role="tree" aria-label="Mission tree"></div>
          </aside>
          <main class="mp-workspace">
            <section id="mp-mission-summary" class="mp-mission-summary"></section>
            <section class="mp-graph-panel" aria-labelledby="mp-graph-title">
              <div class="mp-graph-toolbar">
                <div class="mp-graph-heading"><h2 id="mp-graph-title"></h2><span id="mp-graph-meta"></span></div>
                <div class="mp-toolbar-controls">
                  <label class="mp-check"><input id="mp-show-hidden" type="checkbox" checked><span id="mp-show-hidden-label"></span></label>
                  <label class="mp-check"><input id="mp-show-dependencies" type="checkbox" checked><span id="mp-show-dependencies-label"></span></label>
                  <label class="mp-check"><input id="mp-show-edge-labels" type="checkbox"><span id="mp-show-edge-labels-label"></span></label>
                  <label class="mp-orientation"><span id="mp-orientation-label"></span><select id="mp-orientation"></select></label>
                  <div class="mp-zoom-buttons" role="group" aria-label="Graph zoom">
                    <button id="mp-zoom-out" type="button" aria-label="Zoom out">−</button>
                    <button id="mp-fit" type="button"></button>
                    <button id="mp-zoom-in" type="button" aria-label="Zoom in">+</button>
                    <button id="mp-center" type="button"></button>
                  </div>
                </div>
              </div>
              <p id="mp-control-help" class="mp-control-help"></p>
              <div class="mp-graph-body">
                <div id="mp-viewport" class="mp-viewport" tabindex="0" aria-label="Mission quest flow graph">
                  <div id="mp-plane" class="mp-plane">
                    <div id="mp-lanes" class="mp-lanes"></div>
                    <svg id="mp-edges" class="mp-edges" aria-hidden="true"></svg>
                    <div id="mp-nodes" class="mp-nodes"></div>
                  </div>
                  <div id="mp-empty-graph" class="mp-empty" hidden></div>
                </div>
                <aside id="mp-inspector" class="mp-inspector" aria-live="polite"></aside>
              </div>
              <p id="mp-drag-hint" class="mp-drag-hint"></p>
            </section>
          </main>
        </div>
      </div>`;
    bind();
    applyUiText();
    return true;
  }

  function bind() {
    byId("mp-search")?.addEventListener("input", applyMissionFilters);
    byId("mp-structure")?.addEventListener("change", applyMissionFilters);
    byId("mp-mission-list")?.addEventListener("click", (event) => {
      const group = event.target.closest("button[data-mission-type]");
      if (group) {
        toggleMissionType(group.dataset.missionType);
        return;
      }
      const button = event.target.closest("button[data-mission]");
      if (button) selectMission(button.dataset.mission);
    });
    byId("mp-mission-list")?.addEventListener("keydown", listKeydown);
    ["mp-show-hidden", "mp-show-dependencies", "mp-show-edge-labels", "mp-orientation"].forEach((id) => {
      byId(id)?.addEventListener("change", () => {
        if (id === "mp-show-hidden" || id === "mp-orientation") {
          const plane = byId("mp-plane");
          if (plane) plane.dataset.fittedMission = "";
        }
        renderGraph();
      });
    });
    byId("mp-fit")?.addEventListener("click", fitGraph);
    byId("mp-zoom-out")?.addEventListener("click", () => zoomGraph(0.82));
    byId("mp-zoom-in")?.addEventListener("click", () => zoomGraph(1.22));
    byId("mp-center")?.addEventListener("click", centerSelected);
    byId("mp-nodes")?.addEventListener("click", (event) => {
      if (performance.now() < state.suppressGraphClickUntil) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      const button = event.target.closest("button[data-quest]");
      if (button) selectQuest(button.dataset.quest, { focus: false });
    });
    byId("mp-nodes")?.addEventListener("keydown", graphKeydown);
    const viewport = byId("mp-viewport");
    viewport?.addEventListener("pointerdown", beginPan);
    viewport?.addEventListener("pointermove", movePan);
    viewport?.addEventListener("pointerup", endPan);
    viewport?.addEventListener("pointercancel", endPan);
    viewport?.addEventListener("wheel", graphWheel, { passive: false });
    window.addEventListener("resize", () => {
      if (document.body.dataset.activeView === "mission-pipeline" && state.layout) applyTransform();
    });
    window.addEventListener("webui:ui-locale-changed", () => {
      applyUiText();
      renderMissionList();
      if (state.mission) renderMission();
    });
  }

  function applyUiText() {
    const values = {
      "mp-eyebrow": t("eyebrow"), "mp-title": t("title"), "mp-scope": t("scope"),
      "mp-warning": t("warning"), "mp-search-label": t("search"), "mp-structure-label": t("structure"),
      "mp-show-hidden-label": t("showHidden"), "mp-show-dependencies-label": t("dependencies"),
      "mp-show-edge-labels-label": t("edgeLabels"), "mp-orientation-label": t("orientation"),
      "mp-fit": t("fit"), "mp-center": t("center"), "mp-graph-title": t("graph"), "mp-drag-hint": t("dragHint"),
      "mp-control-help": t("controlHelp"),
    };
    Object.entries(values).forEach(([id, value]) => { const node = byId(id); if (node) node.textContent = value; });
    const search = byId("mp-search");
    if (search) search.placeholder = t("searchPlaceholder");
    const structure = byId("mp-structure");
    if (structure) {
      const selected = structure.value;
      structure.innerHTML = [
        ["", "anyStructure"], ["case", "caseStudies"], ["fanout", "fanout"], ["joins", "joins"],
        ["finish", "exactFinish"], ["server", "serverOwned"], ["failure", "failure"],
      ].map(([value, key]) => `<option value="${value}">${esc(t(key))}</option>`).join("");
      structure.value = selected;
    }
    const orientation = byId("mp-orientation");
    if (orientation) {
      const selected = orientation.value || "auto";
      orientation.innerHTML = [["auto", "auto"], ["lr", "leftRight"], ["tb", "topBottom"]]
        .map(([value, key]) => `<option value="${value}">${esc(t(key))}</option>`).join("");
      orientation.value = selected;
    }
    const zoomOut = byId("mp-zoom-out");
    const zoomIn = byId("mp-zoom-in");
    if (zoomOut) zoomOut.title = t("zoomOut");
    if (zoomIn) zoomIn.title = t("zoomIn");
  }

  async function fetchJson(url, signal, cache = "default") {
    const response = await fetch(url, { signal, cache });
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return response.json();
  }

  async function load(language = "CN", { force = false } = {}) {
    init();
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && state.index && state.language === nextLanguage) return state.index;
    if (!force && state.indexPromise && state.language === nextLanguage) return state.indexPromise;
    const request = ++state.request;
    state.controller?.abort();
    state.controller = new AbortController();
    state.language = nextLanguage;
    renderLoading();
    const cache = force ? "reload" : "default";
    const promise = Promise.all([
      state.index && !force ? Promise.resolve(state.index) : fetchJson("data/mission_pipeline/index.json", state.controller.signal, cache),
      fetchJson(`data/lang/${encodeURIComponent(nextLanguage)}/missions.json`, state.controller.signal, cache).catch(() => ({ missionNames: {} })),
    ]).then(async ([index, names]) => {
      if (request !== state.request) return null;
      state.index = index;
      state.names = names?.missionNames || {};
      state.missionCache.clear();
      state.localizedCache.clear();
      updateCorpus();
      applyMissionFilters();
      const preferred = index.missions?.some((row) => row.id === state.missionId) ? state.missionId : (index.missions?.[0]?.id || "");
      if (preferred) await selectMission(preferred, { force });
      return index;
    }).catch((error) => {
      if (request !== state.request || error?.name === "AbortError") return null;
      renderError(error);
      throw error;
    }).finally(() => {
      if (request === state.request) state.indexPromise = null;
    });
    state.indexPromise = promise;
    return promise;
  }

  function renderLoading() {
    const list = byId("mp-mission-list");
    if (list) list.innerHTML = `<div class="mp-loading">${esc(t("loading"))}</div>`;
    const summary = byId("mp-mission-summary");
    if (summary) summary.innerHTML = `<div class="mp-loading">${esc(t("loading"))}</div>`;
    const inspector = byId("mp-inspector");
    if (inspector) inspector.innerHTML = `<div class="mp-loading">${esc(t("loading"))}</div>`;
  }

  function renderError(error) {
    const message = `${t("loadError")} ${error?.message || ""}`.trim();
    const html = `<div class="mp-error" role="alert"><strong>${esc(message)}</strong><button id="mp-retry" type="button">${esc(t("retry"))}</button></div>`;
    const list = byId("mp-mission-list");
    if (list) list.innerHTML = html;
    byId("mp-retry")?.addEventListener("click", () => load(state.language, { force: true }));
  }

  function updateCorpus() {
    const counts = state.index?.counts || {};
    const node = byId("mp-corpus");
    if (node) node.innerHTML = `<strong>${Number(counts.missions || 0).toLocaleString()}</strong> ${esc(t("missions"))}<span></span><strong>${Number(counts.quests || 0).toLocaleString()}</strong> ${esc(t("quests"))}`;
  }

  function missionName(id) {
    return state.names[id] || id;
  }

  function missionTypeKey(id) {
    if (typeof storyMissionTypeFromId === "function") {
      const storyType = storyMissionTypeFromId(id);
      if (storyType) return storyType;
    }
    return String(id || "").match(/^([a-z]+)/i)?.[1]?.toLowerCase() || "other";
  }

  function missionTypeLabel(type) {
    if (typeof dataTypeLabel === "function") return dataTypeLabel(type);
    return type === "other" ? "Other" : type.toUpperCase();
  }

  function compareMissionTypes(a, b) {
    if (typeof compareDataTypeKeys === "function") return compareDataTypeKeys(a, b);
    return String(a).localeCompare(String(b), undefined, { numeric: true });
  }

  function compareMissions(a, b) {
    if (typeof missionSort === "function") return missionSort(a.id, b.id);
    return String(a.id).localeCompare(String(b.id), undefined, { numeric: true });
  }

  function toggleMissionType(type) {
    if (!type) return;
    if (state.expandedMissionTypes.has(type)) state.expandedMissionTypes.delete(type);
    else state.expandedMissionTypes.add(type);
    renderMissionList();
    byId("mp-mission-list")?.querySelector(`button[data-mission-type="${CSS.escape(type)}"]`)?.focus();
  }

  function missionMatchesStructure(row, value) {
    if (value === "case") return Boolean(row.caseStudy);
    if (value === "fanout") return Number(row.fanoutCount) > 0;
    if (value === "joins") return Number(row.multiPrevJoinCount) > 0 || Number(row.activeJoinCount) > 0;
    if (value === "finish") return Number(row.exactFinishCount) > 0;
    if (value === "server") return Number(row.serverPlaceholderCount) > 0;
    if (value === "failure") return Number(row.failureConditionCount) > 0;
    return true;
  }

  function applyMissionFilters() {
    if (!state.index) return;
    const query = normalize(byId("mp-search")?.value);
    const structure = byId("mp-structure")?.value || "";
    state.filtered = (state.index.missions || []).filter((row) => {
      if (!missionMatchesStructure(row, structure)) return false;
      if (!query) return true;
      return normalize([row.id, missionName(row.id), row.levelId, ...(row.conditionTypes || [])].join(" ")).includes(query);
    });
    renderMissionList();
  }

  function missionBadges(row) {
    const badges = [];
    if (row.caseStudy) badges.push(`<span class="mp-list-badge is-evidence">${esc(t("evidence"))}</span>`);
    if (row.fanoutCount) badges.push(`<span class="mp-list-badge">${row.fanoutCount} ${esc(t("branches"))}</span>`);
    if (row.multiPrevJoinCount || row.activeJoinCount) badges.push(`<span class="mp-list-badge">${row.multiPrevJoinCount + row.activeJoinCount} ${esc(t("join"))}</span>`);
    if (row.exactFinishCount) badges.push(`<span class="mp-list-badge is-dialog">${row.exactFinishCount} ${esc(t("exactFinishes"))}</span>`);
    if (row.serverPlaceholderCount) badges.push(`<span class="mp-list-badge is-server">${row.serverPlaceholderCount} ${esc(t("serverPlaceholders"))}</span>`);
    return badges.join("");
  }

  function renderMissionList() {
    const list = byId("mp-mission-list");
    if (!list) return;
    const results = byId("mp-results");
    if (results) results.textContent = `${state.filtered.length.toLocaleString()} ${t("shown")}`;
    if (!state.filtered.length) {
      list.innerHTML = `<div class="mp-empty-list">${esc(t("noMatches"))}</div>`;
      return;
    }
    const queryActive = Boolean(normalize(byId("mp-search")?.value));
    const grouped = new Map();
    for (const row of state.filtered) {
      const type = missionTypeKey(row.id);
      if (!grouped.has(type)) grouped.set(type, []);
      grouped.get(type).push(row);
    }
    list.innerHTML = [...grouped.keys()].sort(compareMissionTypes).map((type) => {
      const rows = grouped.get(type).sort(compareMissions);
      const expanded = queryActive || state.expandedMissionTypes.has(type);
      const missions = expanded ? rows.map((row) => {
        const selected = row.id === state.missionId;
        return `<button class="mp-mission-row${selected ? " is-selected" : ""}" type="button" role="treeitem" aria-level="2" aria-selected="${selected}" data-mission="${esc(row.id)}">
          <span class="mp-mission-row-head"><strong>${esc(missionName(row.id))}</strong><code>${esc(row.id)}</code></span>
          <span class="mp-mission-row-meta">${esc(row.levelId || "—")} · ${row.questCount} ${esc(t("quests"))}</span>
          <span class="mp-list-badges">${missionBadges(row)}</span>
        </button>`;
      }).join("") : "";
      return `<section class="mp-mission-type${expanded ? " is-expanded" : ""}" role="none">
        <button class="mp-mission-type-row" type="button" role="treeitem" aria-level="1" aria-expanded="${expanded}" data-mission-type="${esc(type)}">
          <span class="mp-mission-type-twisty" aria-hidden="true">${expanded ? "v" : ">"}</span>
          <span class="mp-mission-type-main"><strong>${esc(missionTypeLabel(type))}</strong><code>${esc(type)}</code></span>
          <span class="mp-mission-type-count">${rows.length}</span>
        </button>
        ${expanded ? `<div class="mp-mission-type-items" role="group">${missions}</div>` : ""}
      </section>`;
    }).join("");
  }

  function listKeydown(event) {
    if (!event.target.matches("button[data-mission]")) return;
    const buttons = Array.from(byId("mp-mission-list")?.querySelectorAll("button[data-mission]") || []);
    const index = buttons.indexOf(event.target);
    let target = null;
    if (event.key === "ArrowDown") target = buttons[index + 1] || buttons[0];
    else if (event.key === "ArrowUp") target = buttons[index - 1] || buttons.at(-1);
    else if (event.key === "Home") target = buttons[0];
    else if (event.key === "End") target = buttons.at(-1);
    if (target) { event.preventDefault(); target.focus(); target.scrollIntoView({ block: "nearest" }); }
  }

  async function selectMission(id, { force = false } = {}) {
    if (!id || !state.index) return null;
    state.missionId = id;
    state.expandedMissionTypes.add(missionTypeKey(id));
    renderMissionList();
    const summary = byId("mp-mission-summary");
    if (summary) summary.innerHTML = `<div class="mp-loading">${esc(t("loadingMission"))}</div>`;
    const request = ++state.missionRequest;
    const coreKey = id;
    const localizedKey = `${state.language}:${id}`;
    try {
      const corePromise = !force && state.missionCache.has(coreKey)
        ? Promise.resolve(state.missionCache.get(coreKey))
        : fetchJson(`data/mission_pipeline/missions/${encodeURIComponent(id)}.json`, null, force ? "reload" : "default");
      const localizedPromise = !force && state.localizedCache.has(localizedKey)
        ? Promise.resolve(state.localizedCache.get(localizedKey))
        : fetchJson(`data/lang/${encodeURIComponent(state.language)}/mission/${encodeURIComponent(id)}.json`, null, force ? "reload" : "default").catch(() => null);
      const [mission, localized] = await Promise.all([corePromise, localizedPromise]);
      if (request !== state.missionRequest || id !== state.missionId) return null;
      state.missionCache.set(coreKey, mission);
      state.localizedCache.set(localizedKey, localized);
      state.mission = mission;
      state.localized = localized;
      const visibleIds = new Set((mission.nodes || []).map((row) => row.id));
      state.selectedQuestId = visibleIds.has(state.selectedQuestId)
        ? state.selectedQuestId
        : (mission.mission?.mainPath?.find((questId) => visibleIds.has(questId)) || mission.nodes?.[0]?.id || "");
      renderMission();
      return mission;
    } catch (error) {
      if (request !== state.missionRequest) return null;
      if (summary) summary.innerHTML = `<div class="mp-error" role="alert">${esc(t("loadError"))} ${esc(error?.message || "")}</div>`;
      throw error;
    }
  }

  function localizedQuestMap() {
    const map = new Map();
    for (const quest of state.localized?.flow?.quests || []) map.set(quest.id, quest);
    return map;
  }

  function objectiveText(node, localizedMap = localizedQuestMap()) {
    const localized = localizedMap.get(node.id);
    const texts = (localized?.objectiveInstructions || []).map((row) => plainText(row.text)).filter(Boolean);
    if (texts.length) return [...new Set(texts)].join(" / ");
    const keys = (node.objectives || []).map((row) => row.descriptionKey).filter(Boolean);
    return keys.join(" / ") || t("noObjective");
  }

  function missionDescriptionInfo(node, localizedMap = localizedQuestMap()) {
    const localizedQuest = localizedMap.get(node.id);
    const row = localizedQuest?.missionDescription || state.localized?.flow?.missionDescription || null;
    return {
      key: String(row?.key || ""),
      text: plainText(row?.text || ""),
      source: String(row?.source || "mission"),
    };
  }

  function questStoryFiles(node, localizedMap = localizedQuestMap()) {
    const rows = localizedMap.get(node.id)?.storyFiles || [];
    return rows.filter((row) => row && row.key);
  }

  function storyHref(key) {
    const params = new URLSearchParams();
    params.set("lang", state.language || "CN");
    params.set("ui", locale());
    params.set("story", key);
    return `?${params.toString()}#story`;
  }

  function renderMission() {
    renderMissionSummary();
    renderGraph();
    renderInspector();
  }

  function renderMissionSummary() {
    const target = byId("mp-mission-summary");
    if (!target || !state.mission) return;
    const mission = state.mission.mission || {};
    const row = state.index?.missions?.find((item) => item.id === mission.id) || {};
    const caseStudy = state.mission.caseStudy;
    const metrics = [
      [row.questCount || state.mission.nodes?.length || 0, t("quests")],
      [row.entryCount || 0, t("roots")],
      [row.fanoutCount || 0, t("branches")],
      [(row.multiPrevJoinCount || 0) + (row.activeJoinCount || 0), t("join")],
      [row.exactFinishCount || 0, t("exactFinishes")],
    ];
    target.innerHTML = `<div class="mp-summary-head">
        <div><p class="mp-summary-kicker">${esc(mission.levelId || "—")}</p><h2>${esc(missionName(mission.id))}</h2><code>${esc(mission.id)}</code></div>
        <div class="mp-summary-metrics">${metrics.map(([value, label]) => `<span><strong>${value}</strong>${esc(label)}</span>`).join("")}</div>
      </div>
      <div class="mp-case${caseStudy ? " has-case" : ""}">
        <span class="mp-case-icon" aria-hidden="true">${caseStudy ? "◎" : "○"}</span>
        <div><strong>${esc(caseStudy?.title || t("evidence"))}</strong><p>${esc(caseStudy?.summary || t("noCase"))}</p>${caseStudy ? `<span class="mp-confidence">${esc(t("confidence"))}: ${esc(caseStudy.confidence)}</span>` : ""}</div>
      </div>
      <div class="mp-mission-handshake">
        <strong>${esc(t("missionHandshake"))}</strong>
        <span class="is-outbound">${esc(t("acceptRequest"))}</span>
        <i aria-hidden="true">⇄</i>
        <span class="is-inbound">${esc(t("acceptReturn"))}</span>
        <small>${esc(t("acceptCaveat"))}</small>
      </div>
      ${runtimeContractHtml()}`;
  }

  function runtimeContractHtml() {
    const contract = state.index?.runtimeContract || {};
    const rows = [...(contract.outbound || []), ...(contract.inbound || [])];
    return `<details class="mp-contract-details"><summary>${esc(t("nativeBoundary"))} · ${rows.length} ${esc(t("exchanges"))}</summary>
      <div class="mp-contract-grid">${rows.map((row) => `<article class="mp-contract-card is-${esc(row.direction)}">
        <span>${row.direction === "client_to_server" ? "C → S" : "S → C"} · ${esc(row.confidence)}</span>
        <strong>${esc(row.message)}</strong>
        <code>${esc(row.handler)}${row.address ? ` @ ${esc(row.address)}` : ""}</code>
        <p>${esc(row.effect)}</p>
      </article>`).join("")}</div>
      <p class="mp-contract-boundary">${esc(contract.authority?.boundary || "")}</p>
    </details>`;
  }

  function isHiddenQuest(node) {
    return Number(node.showMode) === 1000;
  }

  function graphNodes() {
    const showHidden = Boolean(byId("mp-show-hidden")?.checked);
    return (state.mission?.nodes || []).filter((node) => showHidden || !isHiddenQuest(node));
  }

  function computeRanks(nodes, edges) {
    const ids = new Set(nodes.map((node) => node.id));
    const incoming = new Map(nodes.map((node) => [node.id, []]));
    const outgoing = new Map(nodes.map((node) => [node.id, []]));
    for (const edge of edges) {
      if (edge.type !== "predecessor" || !ids.has(edge.source) || !ids.has(edge.target)) continue;
      incoming.get(edge.target).push(edge.source);
      outgoing.get(edge.source).push(edge.target);
    }
    const indegree = new Map([...incoming].map(([id, values]) => [id, values.length]));
    const rank = new Map(nodes.map((node) => [node.id, 0]));
    const queue = nodes.filter((node) => indegree.get(node.id) === 0).sort(nodeSort).map((node) => node.id);
    const visited = new Set();
    while (queue.length) {
      const id = queue.shift();
      if (visited.has(id)) continue;
      visited.add(id);
      for (const target of outgoing.get(id) || []) {
        rank.set(target, Math.max(rank.get(target) || 0, (rank.get(id) || 0) + 1));
        indegree.set(target, (indegree.get(target) || 1) - 1);
        if (indegree.get(target) === 0) queue.push(target);
      }
    }
    for (const node of nodes) {
      if (visited.has(node.id)) continue;
      const parentRanks = (incoming.get(node.id) || []).map((id) => rank.get(id) || 0);
      rank.set(node.id, parentRanks.length ? Math.max(...parentRanks) + 1 : 0);
    }
    return rank;
  }

  function nodeSort(a, b) {
    const aMain = Number.isFinite(a.mainPathOrder) ? a.mainPathOrder : Number.MAX_SAFE_INTEGER;
    const bMain = Number.isFinite(b.mainPathOrder) ? b.mainPathOrder : Number.MAX_SAFE_INTEGER;
    return aMain - bMain || Number(a.flowIndex || 0) - Number(b.flowIndex || 0) || naturalQuestNumber(a.id) - naturalQuestNumber(b.id) || String(a.id).localeCompare(String(b.id));
  }

  function computeLayout(nodes, edges) {
    const rankMap = computeRanks(nodes, edges);
    const maxRank = Math.max(0, ...rankMap.values());
    const requested = byId("mp-orientation")?.value || "auto";
    const orientation = requested === "auto" ? (maxRank > 14 ? "tb" : "lr") : requested;
    const lanes = [...new Set(nodes.map((node) => Number(node.flowIndex || 0)))].sort((a, b) => a - b);
    const groups = new Map();
    for (const node of [...nodes].sort(nodeSort)) {
      const key = `${rankMap.get(node.id) || 0}:${Number(node.flowIndex || 0)}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(node);
    }
    const positions = new Map();
    const bands = [];
    let width = 0;
    let height = 0;
    if (orientation === "lr") {
      const laneHeights = new Map();
      for (const lane of lanes) {
        let maxInRank = 1;
        for (let rank = 0; rank <= maxRank; rank += 1) maxInRank = Math.max(maxInRank, (groups.get(`${rank}:${lane}`) || []).length);
        laneHeights.set(lane, Math.max(186, maxInRank * (CARD_H + 18) + 66));
      }
      const laneTop = new Map();
      let top = 30;
      for (const lane of lanes) { laneTop.set(lane, top); top += laneHeights.get(lane); }
      width = Math.max(780, 150 + (maxRank + 1) * (CARD_W + 56));
      height = top + 30;
      for (const lane of lanes) bands.push({ lane, x: 20, y: laneTop.get(lane), width: width - 40, height: laneHeights.get(lane), orientation });
      for (const node of nodes) {
        const rank = rankMap.get(node.id) || 0;
        const lane = Number(node.flowIndex || 0);
        const group = groups.get(`${rank}:${lane}`) || [];
        const index = group.findIndex((item) => item.id === node.id);
        positions.set(node.id, { x: 126 + rank * (CARD_W + 56), y: laneTop.get(lane) + 48 + index * (CARD_H + 18), rank, lane });
      }
    } else {
      const laneWidths = new Map();
      for (const lane of lanes) {
        let maxInRank = 1;
        for (let rank = 0; rank <= maxRank; rank += 1) maxInRank = Math.max(maxInRank, (groups.get(`${rank}:${lane}`) || []).length);
        laneWidths.set(lane, Math.max(268, maxInRank * (CARD_W + 22) + 68));
      }
      const laneLeft = new Map();
      let left = 30;
      for (const lane of lanes) { laneLeft.set(lane, left); left += laneWidths.get(lane); }
      width = left + 30;
      height = Math.max(680, 130 + (maxRank + 1) * (CARD_H + 54));
      for (const lane of lanes) bands.push({ lane, x: laneLeft.get(lane), y: 20, width: laneWidths.get(lane), height: height - 40, orientation });
      for (const node of nodes) {
        const rank = rankMap.get(node.id) || 0;
        const lane = Number(node.flowIndex || 0);
        const group = groups.get(`${rank}:${lane}`) || [];
        const index = group.findIndex((item) => item.id === node.id);
        positions.set(node.id, { x: laneLeft.get(lane) + 42 + index * (CARD_W + 22), y: 112 + rank * (CARD_H + 54), rank, lane });
      }
    }
    return { orientation, positions, bands, width, height, maxRank };
  }

  function renderGraph() {
    const plane = byId("mp-plane");
    const nodesTarget = byId("mp-nodes");
    const edgesTarget = byId("mp-edges");
    const lanesTarget = byId("mp-lanes");
    const empty = byId("mp-empty-graph");
    if (!plane || !nodesTarget || !edgesTarget || !lanesTarget || !state.mission) return;
    const nodes = graphNodes();
    const ids = new Set(nodes.map((node) => node.id));
    if (nodes.length && !ids.has(state.selectedQuestId)) {
      state.selectedQuestId = nodes.find((node) => node.mainPath)?.id || nodes[0].id;
      requestAnimationFrame(renderInspector);
    }
    const showDependencies = Boolean(byId("mp-show-dependencies")?.checked);
    const edges = (state.mission.edges || []).filter((edge) => ids.has(edge.source) && ids.has(edge.target) && (showDependencies || edge.type !== "condition_dependency"));
    if (!nodes.length) {
      plane.hidden = true;
      empty.hidden = false;
      empty.textContent = t("noVisibleQuests");
      return;
    }
    plane.hidden = false;
    empty.hidden = true;
    const layout = computeLayout(nodes, edges);
    state.layout = layout;
    plane.style.width = `${layout.width}px`;
    plane.style.height = `${layout.height}px`;
    edgesTarget.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
    edgesTarget.setAttribute("width", String(layout.width));
    edgesTarget.setAttribute("height", String(layout.height));
    lanesTarget.innerHTML = layout.bands.map((band) => `<div class="mp-lane-band is-${band.orientation}" style="left:${band.x}px;top:${band.y}px;width:${band.width}px;height:${band.height}px"><span>${esc(t("flow"))} ${band.lane}<small>${esc(t("flowCaveat"))}</small></span></div>`).join("");
    renderEdges(edges, layout);
    const localizedMap = localizedQuestMap();
    nodesTarget.innerHTML = nodes.map((node) => renderQuestCard(node, layout.positions.get(node.id), localizedMap)).join("");
    const meta = byId("mp-graph-meta");
    if (meta) meta.textContent = `${nodes.length} ${t("quests")} · ${edges.length} edges · ${layout.orientation.toUpperCase()}`;
    requestAnimationFrame(() => {
      if (!state.transform.scale || state.missionId !== plane.dataset.fittedMission) {
        plane.dataset.fittedMission = state.missionId;
        fitGraph();
        if (state.transform.scale < 0.32) {
          state.transform.scale = 0.55;
          centerSelected();
        }
      } else applyTransform();
    });
  }

  function renderQuestCard(node, position, localizedMap) {
    const selected = node.id === state.selectedQuestId;
    const classes = ["mp-quest-card"];
    if (selected) classes.push("is-selected");
    if (node.mainPath) classes.push("is-main");
    if (isHiddenQuest(node)) classes.push("is-hidden-quest");
    if (node.annotation) classes.push("has-annotation");
    if (node.authority === "server") classes.push("is-server-owned");
    const conditions = (node.conditionTypes || []).slice(0, 3);
    const description = missionDescriptionInfo(node, localizedMap);
    const storyFiles = questStoryFiles(node, localizedMap);
    const network = node.network?.outbound;
    const networkLabel = network === "dialog_finish" ? t("clientToServerDialog") : network === "objective_progress" ? t("clientToServerProgress") : network === "server_owned" ? t("serverGate") : t("unresolvedSend");
    const networkClass = network === "dialog_finish" || network === "objective_progress" ? "is-dialog" : network === "server_owned" ? "is-server" : "is-unknown";
    const tooltip = [objectiveText(node, localizedMap), description.text].filter(Boolean).join("\n\n");
    return `<button class="${classes.join(" ")}" type="button" data-quest="${esc(node.id)}" aria-pressed="${selected}" style="left:${position.x}px;top:${position.y}px" title="${esc(tooltip)}">
      <span class="mp-card-top"><code>${esc(questShortLabel(node.id))}</code><span class="mp-card-badges">${node.mainPath ? `<span>${esc(t("main"))}</span>` : ""}${isHiddenQuest(node) ? `<span class="is-hidden">${esc(t("hidden"))}</span>` : ""}${storyFiles.length ? `<span class="is-story">${esc(t("storyCount"))} ${storyFiles.length}</span>` : ""}<span>${esc(t("flow"))} ${Number(node.flowIndex || 0)}</span></span></span>
      <strong>${esc(objectiveText(node, localizedMap))}</strong>
      <span class="mp-card-description">${esc(description.text || t("noDescription"))}</span>
      <span class="mp-condition-row">${conditions.map((value) => `<span>${esc(value)}</span>`).join("")}${(node.conditionTypes || []).length > 3 ? `<span>+${node.conditionTypes.length - 3}</span>` : ""}</span>
      <span class="mp-network-row"><span class="mp-network is-inbound">${esc(t("serverToClient"))}</span><span class="mp-network ${networkClass}">${esc(networkLabel)}</span></span>
      ${node.annotation ? `<span class="mp-annotation-dot" aria-label="${esc(node.annotation)}">◎</span>` : ""}
    </button>`;
  }

  function svg(tag, attrs = {}) {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
    return node;
  }

  function renderEdges(edges, layout) {
    const target = byId("mp-edges");
    if (!target) return;
    target.replaceChildren();
    const defs = svg("defs");
    const marker = svg("marker", { id: "mp-arrow", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto", markerUnits: "strokeWidth" });
    marker.appendChild(svg("path", { d: "M0,0 L8,4 L0,8 z", class: "mp-arrow-head" }));
    const depMarker = svg("marker", { id: "mp-arrow-dep", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto", markerUnits: "strokeWidth" });
    depMarker.appendChild(svg("path", { d: "M0,0 L8,4 L0,8 z", class: "mp-arrow-head-dep" }));
    defs.append(marker, depMarker);
    target.appendChild(defs);
    const showLabels = Boolean(byId("mp-show-edge-labels")?.checked);
    for (const edge of edges) {
      const from = layout.positions.get(edge.source);
      const to = layout.positions.get(edge.target);
      if (!from || !to) continue;
      const dependency = edge.type === "condition_dependency";
      let start;
      let end;
      let d;
      if (layout.orientation === "lr") {
        start = { x: from.x + CARD_W, y: from.y + CARD_H / 2 };
        end = { x: to.x, y: to.y + CARD_H / 2 };
        const bend = Math.max(50, Math.abs(end.x - start.x) * 0.46);
        d = `M${start.x},${start.y} C${start.x + bend},${start.y} ${end.x - bend},${end.y} ${end.x},${end.y}`;
      } else {
        start = { x: from.x + CARD_W / 2, y: from.y + CARD_H };
        end = { x: to.x + CARD_W / 2, y: to.y };
        const bend = Math.max(42, Math.abs(end.y - start.y) * 0.46);
        d = `M${start.x},${start.y} C${start.x},${start.y + bend} ${end.x},${end.y - bend} ${end.x},${end.y}`;
      }
      const selected = edge.source === state.selectedQuestId || edge.target === state.selectedQuestId;
      const path = svg("path", {
        d,
        class: `mp-edge ${dependency ? "is-dependency" : "is-predecessor"}${selected ? " is-selected" : ""}`,
        "marker-end": dependency ? "url(#mp-arrow-dep)" : "url(#mp-arrow)",
      });
      target.appendChild(path);
      const midpoint = { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 };
      if (!dependency) {
        const gateway = svg("g", { class: `mp-gateway${selected ? " is-selected" : ""}` });
        gateway.appendChild(svg("path", { d: `M${midpoint.x},${midpoint.y - 12} L${midpoint.x + 12},${midpoint.y} L${midpoint.x},${midpoint.y + 12} L${midpoint.x - 12},${midpoint.y} Z` }));
        const label = svg("text", { x: midpoint.x, y: midpoint.y + 4, "text-anchor": "middle" });
        label.textContent = t("serverGateway");
        gateway.appendChild(label);
        const title = svg("title"); title.textContent = t("serverGatewayTitle"); gateway.appendChild(title);
        target.appendChild(gateway);
      }
      if (showLabels) {
        const label = svg("text", { x: midpoint.x + 16, y: midpoint.y - 14, class: `mp-edge-label${dependency ? " is-dependency" : ""}` });
        label.textContent = dependency ? `${t("conditionDependency")} = ${edge.targetState ?? "?"}` : t("predecessor");
        target.appendChild(label);
      }
    }
  }

  function selectQuest(id, { focus = true } = {}) {
    if (!state.mission?.nodes?.some((node) => node.id === id)) return;
    state.selectedQuestId = id;
    renderGraph();
    renderInspector();
    if (focus) byId("mp-nodes")?.querySelector(`button[data-quest="${CSS.escape(id)}"]`)?.focus();
  }

  function graphKeydown(event) {
    const button = event.target.closest("button[data-quest]");
    if (!button || !state.mission) return;
    const node = state.mission.nodes.find((row) => row.id === button.dataset.quest);
    if (!node) return;
    let target = "";
    if (event.key === "ArrowRight" || event.key === "ArrowDown") target = node.successors?.[0] || "";
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") target = node.prev?.[0] || "";
    if (target) { event.preventDefault(); selectQuest(target); centerSelected(); }
  }

  function conditionAuthorityText(authority) {
    if (authority === "synchronized_history") return t("synchronizedHistory");
    if (authority === "synchronized_state") return t("synchronizedState");
    if (authority === "client_observed") return t("clientObserved");
    if (authority === "server") return t("serverOwnedDetail");
    if (authority === "mixed") return t("mixedAuthority");
    return t("unknownAuthority");
  }

  function renderConditionTree(condition) {
    if (!condition) return "";
    const facts = condition.facts || {};
    const factHtml = Object.entries(facts).map(([key, value]) => `<span><b>${esc(key)}</b>: ${esc(typeof value === "object" ? JSON.stringify(value) : value)}</span>`).join("");
    const children = (condition.children || []).map((child) => renderConditionTree(child)).join("");
    return `<div class="mp-condition-tree"><code>${esc(condition.type)}</code>${factHtml ? `<div class="mp-condition-facts">${factHtml}</div>` : ""}${children ? `<div class="mp-condition-children">${children}</div>` : ""}</div>`;
  }

  function objectiveHtml(objective) {
    const finishRows = (objective.dialogFinishes || []).map((row) => `<span class="mp-finish-chip"><b>${esc(row.dialogId)}</b> · ${row.finishId < 0 ? esc(t("anyFinish")) : `${esc(t("finish"))} ${esc(row.finishId)}`}</span>`).join("");
    const localIds = new Set((state.mission?.nodes || []).map((node) => node.id));
    const stateRows = (objective.questStateRefs || []).map((row) => `<span class="mp-state-chip${localIds.has(row.questId) ? "" : " is-external"}"><b>${esc(row.questId)}</b> · ${esc(t("state"))} ${esc(row.state ?? "?")}${localIds.has(row.questId) ? "" : ` · ${esc(t("externalDependency"))}`}</span>`).join("");
    return `<article class="mp-objective"><header><strong>${esc(t("objectives"))} ${objective.index}</strong><span class="mp-authority is-${esc(objective.authority)}">${esc(objective.authority)}</span></header>
      <p>${esc(objective.descriptionKey || t("noObjective"))}</p>
      <div class="mp-objective-special">${finishRows}${stateRows}</div>
      ${renderConditionTree(objective.condition)}
    </article>`;
  }

  function protocolRow(step, player, client, server, tone = "") {
    return `<div class="mp-protocol-row ${tone}"><div class="mp-step-label">${esc(step)}</div><div class="mp-lane-cell is-player">${player || ""}</div><div class="mp-lane-cell is-client">${client || ""}</div><div class="mp-lane-cell is-server">${server || ""}</div></div>`;
  }

  function protocolHtml(node) {
    const dialogRows = (node.objectives || []).flatMap((objective) => objective.dialogFinishes || []);
    const conditionIds = (node.objectives || []).map((objective) => objective.conditionId).filter(Boolean);
    let observeClient = `<strong>${esc(t("condition"))}</strong><span>${esc(conditionAuthorityText(node.authority))}</span>`;
    let observeServer = "";
    if (node.authority === "server") { observeServer = observeClient; observeClient = `<span>${esc(t("serverOwnedDetail"))}</span>`; }
    const exchangeRows = [];
    if (node.network?.outbound === "dialog_finish") {
      const fields = dialogRows.map((row) => `${row.dialogId} / ${row.finishId < 0 ? t("anyFinish") : `${t("finish")} ${row.finishId}`}`).join("; ");
      exchangeRows.push(protocolRow(t("outbound"), "", `<strong>${esc(t("dialogSend"))}</strong><span>${esc(fields)}</span>`, `<span>${esc(t("dialogSendDetail"))}</span>`, "is-known-send"));
      exchangeRows.push(protocolRow(t("dialogExchange"), "", `<span>${esc(t("synchronizedHistory"))}</span>`, `<strong>→ ${esc(t("dialogEcho"))}</strong>`, "is-inbound-step"));
    } else if (node.network?.outbound === "server_owned") {
      exchangeRows.push(protocolRow(t("outbound"), "", `<span>${esc(t("serverOwnedDetail"))}</span>`, `<strong>${esc(t("serverGate"))}</strong>`, "is-server-step"));
    }
    if (node.network?.outbound !== "server_owned" && (node.objectives || []).length) {
      const ids = conditionIds.length ? conditionIds.join(", ") : "conditionId";
      exchangeRows.push(protocolRow(t("outbound"), "", `<strong>${esc(t("progressSend"))}</strong><span>${esc(ids)} · ${esc(t("progressCaveat"))}</span>`, `<span>${esc(t("progressNative"))}</span>`, "is-known-send"));
      exchangeRows.push(protocolRow(t("returnState"), "", `<span>${esc(t("progressCaveat"))}</span>`, `<strong>→ ${esc(t("progressReturn"))}</strong>`, "is-inbound-step"));
    } else if (node.network?.outbound !== "server_owned") {
      exchangeRows.push(protocolRow(t("outbound"), "", `<strong>${esc(t("unresolvedSend"))}</strong><span>${esc(t("unresolvedDetail"))}</span>`, `<span>?</span>`, "is-unknown-send"));
    }
    return `<section class="mp-protocol">
      <header><div><h3>${esc(t("protocol"))}</h3><p>${esc(t("asyncCaveat"))}</p></div><span class="mp-native-badge">${esc(t("nativeConfidence"))}</span></header>
      <div class="mp-protocol-grid">
        <div class="mp-protocol-head"><span></span><strong>${esc(t("playerWorld"))}</strong><strong>${esc(t("client"))}</strong><strong>${esc(t("server"))}</strong></div>
        ${protocolRow(t("activation"), "", `<strong>${esc(t("activationHandler"))}</strong>`, `<strong>→ ${esc(t("activationMessage"))}</strong>`, "is-inbound-step")}
        ${protocolRow(t("observe"), `<span>${esc(t("worldEvent"))}</span>`, observeClient, observeServer)}
        ${exchangeRows.join("")}
        ${protocolRow(t("resolve"), "", "", `<strong>${esc(t("opaquePolicy"))}</strong>`, "is-opaque-step")}
        ${protocolRow(t("returnState"), "", `<strong>${esc(t("succeedHandler"))}</strong>${node.failedCondition ? `<span>${esc(t("failMessage"))}</span>` : ""}`, `<strong>→ ${esc(t("succeedMessage"))}</strong>`, "is-inbound-step")}
        ${protocolRow(t("successor"), "", `<span>${esc(t("successorDetail"))}</span>`, `<strong>${esc((node.successors || []).join(", ") || "—")}</strong>`, "is-opaque-step")}
      </div>
    </section>`;
  }

  function storyFilesHtml(node, localizedMap = localizedQuestMap()) {
    const files = questStoryFiles(node, localizedMap);
    const body = files.length ? `<div class="mp-story-files">${files.map((row) => `<a href="${esc(storyHref(row.key))}" title="${esc(`${t("openInStory")} · ${row.evidence || "direct quest reference"}`)}">
      <span>${esc(row.kind || "story")}</span><code>${esc(row.key)}</code><b aria-hidden="true">↗</b>
    </a>`).join("")}</div>` : `<p>${esc(t("noStoryFiles"))}</p>`;
    return `<section class="mp-inspector-section mp-story-section"><h3>${esc(t("storyFiles"))}</h3>${body}<small>${esc(t("storyEvidence"))}</small></section>`;
  }

  function renderInspector() {
    const target = byId("mp-inspector");
    if (!target || !state.mission) return;
    const node = state.mission.nodes.find((row) => row.id === state.selectedQuestId);
    if (!node) { target.innerHTML = `<div class="mp-empty-inspector">${esc(t("selectMission"))}</div>`; return; }
    const actionHtml = (node.clientActions || []).map((action) => `<div class="mp-action"><code>${esc(action.type)}</code><span>ID ${esc(action.id ?? "?")} · trigger ${esc(action.trigger ?? "?")}</span></div>`).join("");
    const nativeEvidence = (state.index?.runtimeContract?.nativeEvidence || []).map((row) => `<li><code>${esc(row.symbol)}</code><span>${esc(row.finding)}</span></li>`).join("");
    const description = missionDescriptionInfo(node);
    target.innerHTML = `<div class="mp-inspector-head">
        <p>${esc(t("inspectQuest"))}</p><h2>${esc(questShortLabel(node.id))}</h2><code>${esc(node.id)}</code>
        <strong>${esc(objectiveText(node))}</strong>
        ${node.annotation ? `<span class="mp-inspector-annotation">◎ ${esc(node.annotation)}</span>` : ""}
      </div>
      <div class="mp-fact-grid">
        <span><b>${esc(t("flow"))}</b>${esc(node.flowIndex)}</span>
        <span><b>showMode</b>${esc(node.showMode ?? "—")}</span>
        <span><b>prev</b>${esc((node.prev || []).length)}</span>
        <span><b>next</b>${esc((node.successors || []).length)}</span>
      </div>
      <p class="mp-flow-caveat">${esc(t("flowCaveat"))}</p>
      <section class="mp-inspector-section mp-description-section"><h3>${esc(t("missionDescription"))}</h3><p>${esc(description.text || t("noDescription"))}</p>${description.text ? `<small>${esc(description.source === "quest_override" ? t("descriptionOverride") : t("descriptionInherited"))} · <code>${esc(description.key)}</code></small>` : ""}</section>
      <section class="mp-inspector-section"><h3>${esc(t("authority"))}</h3><p>${esc(conditionAuthorityText(node.authority))}</p></section>
      <section class="mp-inspector-section"><h3>${esc(t("objectives"))}</h3>${(node.objectives || []).map(objectiveHtml).join("") || `<p>${esc(t("noObjective"))}</p>`}${node.failedCondition ? `<div class="mp-failed-condition"><strong>failedCondition</strong>${renderConditionTree(node.failedCondition)}</div>` : ""}</section>
      ${storyFilesHtml(node)}
      ${actionHtml ? `<section class="mp-inspector-section"><h3>${esc(t("clientActions"))}</h3>${actionHtml}</section>` : ""}
      ${protocolHtml(node)}
      <details class="mp-native-details"><summary>${esc(t("openEvidence"))}</summary><ul>${nativeEvidence}</ul><p><strong>${esc(t("source"))}:</strong> <code>${esc(state.mission.mission?.source || "")}</code></p></details>`;
  }

  function applyTransform() {
    const plane = byId("mp-plane");
    if (!plane) return;
    const { x, y, scale } = state.transform;
    plane.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
    const viewport = byId("mp-viewport");
    if (viewport) viewport.dataset.scale = scale.toFixed(2);
  }

  function fitGraph() {
    const viewport = byId("mp-viewport");
    if (!viewport || !state.layout) return;
    const pad = 38;
    const scale = Math.max(0.04, Math.min(1.05, (viewport.clientWidth - pad * 2) / state.layout.width, (viewport.clientHeight - pad * 2) / state.layout.height));
    state.transform = {
      scale,
      x: (viewport.clientWidth - state.layout.width * scale) / 2,
      y: (viewport.clientHeight - state.layout.height * scale) / 2,
    };
    applyTransform();
  }

  function zoomGraph(factor, origin = null) {
    const viewport = byId("mp-viewport");
    if (!viewport || !state.layout) return;
    const old = state.transform.scale;
    const next = Math.max(0.04, Math.min(2.2, old * factor));
    const point = origin || { x: viewport.clientWidth / 2, y: viewport.clientHeight / 2 };
    const worldX = (point.x - state.transform.x) / old;
    const worldY = (point.y - state.transform.y) / old;
    state.transform.scale = next;
    state.transform.x = point.x - worldX * next;
    state.transform.y = point.y - worldY * next;
    applyTransform();
  }

  function centerSelected() {
    const viewport = byId("mp-viewport");
    const position = state.layout?.positions?.get(state.selectedQuestId);
    if (!viewport || !position) return;
    state.transform.x = viewport.clientWidth / 2 - (position.x + CARD_W / 2) * state.transform.scale;
    state.transform.y = viewport.clientHeight / 2 - (position.y + CARD_H / 2) * state.transform.scale;
    applyTransform();
  }

  function beginPan(event) {
    if (event.button !== 0 || event.target.closest("input, select, label, summary, details")) return;
    const viewport = byId("mp-viewport");
    state.dragging = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      originX: state.transform.x,
      originY: state.transform.y,
      moved: false,
    };
  }

  function movePan(event) {
    if (!state.dragging || state.dragging.id !== event.pointerId) return;
    const dx = event.clientX - state.dragging.x;
    const dy = event.clientY - state.dragging.y;
    if (!state.dragging.moved && Math.hypot(dx, dy) < 5) return;
    if (!state.dragging.moved) {
      state.dragging.moved = true;
      const viewport = byId("mp-viewport");
      viewport?.setPointerCapture(event.pointerId);
      viewport?.classList.add("is-panning");
    }
    event.preventDefault();
    state.transform.x = state.dragging.originX + dx;
    state.transform.y = state.dragging.originY + dy;
    applyTransform();
  }

  function endPan(event) {
    if (!state.dragging || state.dragging.id !== event.pointerId) return;
    const moved = state.dragging.moved;
    state.dragging = null;
    byId("mp-viewport")?.classList.remove("is-panning");
    if (moved) state.suppressGraphClickUntil = performance.now() + 350;
  }

  function graphWheel(event) {
    event.preventDefault();
    const viewport = byId("mp-viewport");
    const rect = viewport?.getBoundingClientRect();
    if (!rect) return;
    const unit = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? 16 : event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? viewport.clientHeight : 1;
    const delta = Math.max(-240, Math.min(240, event.deltaY * unit));
    zoomGraph(Math.exp(-delta * 0.00125), { x: event.clientX - rect.left, y: event.clientY - rect.top });
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.missionPipeline = { init, load, retry: () => load(state.language, { force: true }) };
})();
