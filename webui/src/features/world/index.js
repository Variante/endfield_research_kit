(() => {
  "use strict";

  const DEFAULT_CONTAINER = "#world-app";
  const DEFAULT_LANGUAGE = "CN";
  const DEFAULT_LEVEL = "base01_lv001";
  const LIST_PAGE_SIZE = 200;
  const RELATION_PAGE_SIZE = 80;
  const MAP_POINT_LIMIT = 600;
  const UI = {
    clearFilters: "Clear filters", retry: "Retry", kind: "Record type", level: "Map / level", confidence: "Link evidence",
    showing: "Showing", of: "of", results: "results", total: "total", filters: "filters", showMore: "Show more", selected: "Selected", evidence: "Evidence",
    searchLabel: "Search world data",
  };
  const KINDS = ["all", "map", "level", "worldEntity", "interactive", "npcProxy", "spawner", "enemy", "model", "audioCollection", "audioSlot", "levelScript"];
  const TEXT = {
    en: {
      title: "World placements & evidence", search: "Search names, IDs, maps, levels, models, audio, or sources", allKinds: "All record types",
      allLevels: "All levels", allConfidence: "All evidence", loading: "Loading world data…",
      eyebrow: "A searchable index of maps, placed objects, encounters, scripts, models, and audio references",
      purpose: "Find where something is declared in the game's world data and inspect the saved coordinates and records that connect it to a map or level.",
      whyCare: "Why care? It helps researchers locate NPCs and interactive objects, understand an encounter setup, and verify which source file supports a claimed world connection.",
      startHere: "Start with a question", startHint: "Authored level groups are the friendliest overview. The default opens the O.M.V. Dijiang group; use the level filter to move elsewhere.",
      questionMap: "What is placed in one level?", answerMap: "Begin with O.M.V. Dijiang, where coordinate-bearing NPC records can be compared with the level's scripts and other records.", actionMap: "Browse a level group",
      questionPlace: "Where is an NPC declared?", answerPlace: "NPC placement records carry direct level IDs and saved X/Z coordinates that can be plotted together.", actionPlace: "Browse NPC placements",
      questionSpawn: "Which enemies can appear in an encounter?", answerSpawn: "Spawn setup records list the enemy definitions referenced by a level encounter.", actionSpawn: "Browse spawn setups",
      limits: "What this page can and cannot prove", limitsBody: "This is an evidence browser, not an in-game map or live simulation. Saved coordinates have no guaranteed player-facing orientation or units. The data cannot prove whether something is currently spawned, visible, reachable, or active for a particular mission or account.",
      terms: "What the record types mean", termsBody: "Placed object: an object saved into world configuration. NPC placement: an indirect record that assigns an NPC identity or behavior to a place. Spawn setup: rules naming what an encounter may create. Scripted level object: a configuration record used by mission or level logic. A link marked inferred is a plausible match, not a directly declared connection.",
      unavailable: "World data is unavailable. Run scripts/build_world_data.py.", empty: "No records match. Try clearing filters or choosing another record type.",
      source: "Game-data source", authoredPosition: "Saved source coordinates", configuration: "Original fields (advanced)",
      relations: "Connected records", noRelations: "No connected records are available for this entry.",
      scope: "Static authored placement and references only; runtime state and behavior are not inferred.",
      entries: "records", relationsCount: "links", selectPrompt: "Choose a record on the left to inspect its position, connections, and source evidence.",
      kindMap: "Map overview", kindLevel: "Level / scene", kindWorldEntity: "Placed object", kindInteractive: "Interactive object", kindNpcProxy: "NPC placement",
      kindSpawner: "Spawn setup", kindEnemy: "Enemy definition", kindModel: "Model reference", kindAudioCollection: "Audio group", kindAudioSlot: "Audio reference", kindLevelScript: "Scripted level object",
      searchLabel: "Search world records", clearFilters: "Clear filters", kind: "Record type", level: "Map / level", confidence: "Link evidence", filters: "filters", total: "total",
      evidenceAuthored: "Direct in source", evidenceDirect: "Direct in source", evidenceExact: "Exact match", evidenceInferred: "Inferred match", evidenceProvisional: "Provisional match",
      levelGroup: "Level group", otherGroup: "Other records", unassignedGroup: "No exported level", mapTitle: "Authored 2D placement map",
      mapAxes: "X runs left to right; Z runs bottom to top. Points are normalized to the visible records, not an in-game map image or a fixed world scale.",
      mapShowing: "coordinate-bearing records", mapMissing: "records in this level have no usable X/Z coordinates", mapEmpty: "No shared 2D map is available for this selection.",
      mapNoLevel: "This record has coordinates but no exported level ID, so it is shown alone. Its position cannot be safely combined with another level.",
      mapPointHint: "Focus, hover, or select a point to identify it.", mapLimited: "The plot is sampled for browser performance; filters and the list still cover every record.",
    },
    zh: {
      filters: "\u7b5b\u9009", total: "\u603b\u8ba1",
      title: "世界放置与证据", search: "搜索名称、ID、地图、关卡、模型、音频或来源", allKinds: "全部记录类型",
      allLevels: "全部关卡", allConfidence: "全部证据", loading: "正在加载世界数据…",
      eyebrow: "地图、放置物体、遭遇、脚本、模型与音频引用的可搜索索引",
      purpose: "查找某个内容在游戏世界数据中的声明位置，并检查将它连接到地图或关卡的坐标和记录。",
      whyCare: "为什么值得看？研究者可以借此定位 NPC 和交互物体、理解遭遇配置，并核验世界连接由哪个源文件支持。",
      startHere: "先选择一个问题", startHint: "按原始关卡分组最容易理解。默认打开 O.M.V. 帝江号分组；可以用关卡筛选切换。",
      questionMap: "一个关卡里放置了什么？", answerMap: "先查看 O.M.V. 帝江号，把带坐标的 NPC 记录与同关卡脚本及其他记录放在一起比较。", actionMap: "浏览关卡分组",
      questionPlace: "NPC 在哪里声明？", answerPlace: "NPC 放置记录带有直接关卡 ID 和保存的 X/Z 坐标，因此可以绘制在一起。", actionPlace: "浏览 NPC 放置",
      questionSpawn: "一次遭遇可能出现哪些敌人？", answerSpawn: "生成配置会列出关卡遭遇所引用的敌人定义。", actionSpawn: "浏览生成配置",
      limits: "本页能证明什么、不能证明什么", limitsBody: "这是证据浏览器，不是游戏地图或实时模拟。保存的坐标不保证与玩家视角方向或单位一致；数据也不能证明某对象当前是否已生成、可见、可到达，或对特定任务与账号生效。",
      terms: "记录类型是什么意思", termsBody: "“放置物体”是保存到世界配置中的对象；“NPC 放置”是把 NPC 身份或行为间接分配到位置的记录；“生成配置”是声明遭遇可能创建哪些对象的规则；“关卡脚本对象”供任务或关卡逻辑使用；标记为“推断”的链接只是合理匹配，并非直接声明。",
      unavailable: "世界数据不可用。请运行 scripts/build_world_data.py。", empty: "没有匹配记录。请清空筛选或选择其他记录类型。",
      source: "游戏数据来源", authoredPosition: "保存的源坐标", configuration: "原始字段（进阶）",
      relations: "连接记录", noRelations: "该条目没有可用的连接记录。",
      scope: "仅显示静态原始配置和引用；不推断运行时状态或行为。",
      entries: "记录", relationsCount: "链接", selectPrompt: "选择左侧记录，查看位置、连接和来源证据。",
      kindMap: "地图总览", kindLevel: "关卡／场景", kindWorldEntity: "放置物体", kindInteractive: "交互物体", kindNpcProxy: "NPC 放置",
      kindSpawner: "生成配置", kindEnemy: "敌人定义", kindModel: "模型引用", kindAudioCollection: "音频组", kindAudioSlot: "音频引用", kindLevelScript: "关卡脚本对象",
      searchLabel: "搜索世界记录", clearFilters: "清空筛选", kind: "记录类型", level: "地图／关卡", confidence: "链接证据", evidence: "证据",
      retry: "重试", showing: "显示", of: "/", results: "条结果", showMore: "显示更多", selected: "已选择",
      evidenceAuthored: "来源直接声明", evidenceDirect: "来源直接声明", evidenceExact: "精确匹配", evidenceInferred: "推断匹配", evidenceProvisional: "暂定匹配",
      levelGroup: "关卡分组", otherGroup: "其他记录", unassignedGroup: "没有导出关卡", mapTitle: "原始二维放置图",
      mapAxes: "X 轴从左到右，Z 轴从下到上。点位按当前可见记录归一化；这不是游戏内地图图片，也不是固定世界比例。",
      mapShowing: "条带坐标记录", mapMissing: "条同关卡记录没有可用的 X/Z 坐标", mapEmpty: "当前选择没有可共用的二维地图。",
      mapNoLevel: "该记录有坐标，但没有导出的关卡 ID，因此只能单独显示；不能可靠地将它与其他关卡合并。",
      mapPointHint: "聚焦、悬停或选择点位即可识别记录。", mapLimited: "为保证浏览器性能，图中会抽样显示；筛选与列表仍包含全部记录。",
    },
  };

  const state = {
    container: null,
    language: DEFAULT_LANGUAGE,
    uiLocale: "en",
    payload: null,
    entries: [],
    relations: [],
    byId: new Map(),
    relationsByEntry: new Map(),
    entryMeta: new Map(),
    levelNames: new Map(),
    positionsByLevel: new Map(),
    levels: [],
    kindCounts: new Map(),
    query: "",
    kind: "all",
    level: DEFAULT_LEVEL,
    confidence: "all",
    selectedId: "",
    visibleLimit: LIST_PAGE_SIZE,
    relationLimit: RELATION_PAGE_SIZE,
    loading: null,
    lastError: "",
    abortController: null,
    loadToken: 0,
    initialized: false,
    listeners: [],
    options: {},
  };

  const text = (key) => (TEXT[state.uiLocale] || TEXT.en)[key] || TEXT.en[key] || UI[key] || key;
  const string = (value) => value == null ? "" : String(value);
  const array = (value) => Array.isArray(value) ? value : (value == null || value === "" ? [] : [value]);
  const compact = (values) => values.map(string).map((value) => value.trim()).filter(Boolean);
  const unique = (values) => [...new Set(compact(values))];

  function element(tag, className = "", content = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== "") node.textContent = string(content);
    return node;
  }

  function detectLocale() {
    const raw = string(window.WEBUI_UI_LOCALE || document.documentElement.lang || "en").toLowerCase();
    return raw.startsWith("zh") ? "zh" : "en";
  }

  function currentLanguage() {
    return string(document.querySelector("#language")?.value || state.language || DEFAULT_LANGUAGE).toUpperCase();
  }

  function dataPath(language = currentLanguage()) {
    return `data/lang/${encodeURIComponent(string(language || DEFAULT_LANGUAGE).toUpperCase())}/world/index.json`;
  }

  function isActive() {
    const hashView = location.hash.replace(/^#/, "").split(/[/?&]/, 1)[0].toLowerCase();
    return document.body.dataset.activeView === "world" || hashView === "world";
  }

  function listen(target, name, handler) {
    if (!target) return;
    target.addEventListener(name, handler);
    state.listeners.push(() => target.removeEventListener(name, handler));
  }

  function normalizeKind(value) {
    const raw = string(value || "entry").trim();
    const key = raw.toLowerCase().replace(/[\s_-]+/g, "");
    const aliases = {
      entity: "worldEntity", placedentity: "worldEntity", placement: "worldEntity", worldentity: "worldEntity",
      interactable: "interactive", interaction: "interactive", interactive: "interactive",
      npcproxy: "npcProxy", spawn: "spawner", enemyspawner: "spawner", spawner: "spawner", enemy: "enemy",
      levelmap: "level", level: "level", scene: "map", map: "map", mesh: "model", model: "model",
      audiocollection: "audioCollection", audioslot: "audioSlot", sound: "audioSlot", levelscript: "levelScript",
    };
    return aliases[key] || raw || "entry";
  }

  function entryId(entry, index = 0) {
    return string(entry?.id || entry?.key || entry?.entryId || entry?.sourceId || `${normalizeKind(entry?.kind)}:${index}`);
  }

  function entryTitle(entry) {
    return string(entry?.name || entry?.title || entry?.label || entry?.displayName || entryId(entry));
  }

  function entryLevels(entry) {
    return unique([
      ...array(entry?.levelIds), ...array(entry?.levels), entry?.levelId, entry?.level,
      entry?.mapId, entry?.map, entry?.placement?.levelId, entry?.position?.levelId,
    ].flatMap(array).map((value) => typeof value === "object" ? value.id || value.key || value.name : value));
  }

  function levelLabel(value) {
    const levelId = string(value);
    const friendly = string(state.levelNames.get(levelId));
    return friendly && friendly !== levelId ? `${friendly} · ${levelId}` : levelId;
  }

  function primaryLevel(entry) {
    const levels = state.entryMeta.get(entry.id)?.levels || entryLevels(entry);
    return levels.find((value) => /^base\d+_lv\d+$/i.test(value))
      || levels.find((value) => /_lv\d+$/i.test(value))
      || levels[0]
      || "";
  }

  function authoredCoordinates(entry) {
    const value = entry?.authoredPosition || entry?.position || entry?.transform?.position || entry?.placement?.position;
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    const x = Number(value.x);
    const z = Number(value.z);
    return Number.isFinite(x) && Number.isFinite(z) ? { x, z } : null;
  }

  function sourceIds(entry) {
    const source = entry?.source || entry?.evidence || {};
    return unique([
      ...array(entry?.sourceIds), entry?.sourceId, source?.id, source?.sourceId, source?.assetId,
      source?.table, source?.path, typeof source === "object" ? "" : source, entry?.assetId, entry?.templateId,
    ].flatMap(array).map((value) => typeof value === "object" ? value.id || value.path || value.key : value));
  }

  function relatedValues(entry, key) {
    const singular = key.replace(/Ids$/, "Id");
    return unique([...array(entry?.[key]), ...array(entry?.[singular]), ...array(entry?.references?.[key]), ...array(entry?.references?.[singular])]
      .flatMap(array).map((value) => typeof value === "object" ? value.id || value.key || value.name : value));
  }

  function normalizeEntry(entry, index) {
    const normalized = entry && typeof entry === "object" ? entry : { id: string(entry) };
    return { ...normalized, id: entryId(normalized, index), kind: normalizeKind(normalized.kind || normalized.type || normalized.category) };
  }

  function endpointId(value) {
    return string(value && typeof value === "object" ? value.id || value.key || value.entryId : value);
  }

  function relationSource(relation) {
    return endpointId(relation?.sourceId || relation?.fromId || relation?.sourceEntryId || relation?.from || relation?.subjectId
      || (typeof relation?.source === "object" ? "" : relation?.source));
  }

  function relationTarget(relation) {
    return endpointId(relation?.targetId || relation?.toId || relation?.targetEntryId || relation?.target || relation?.to || relation?.objectId);
  }

  function relationType(relation) {
    return string(relation?.type || relation?.kind || relation?.relation || relation?.predicate || "related_to");
  }

  function relationConfidence(relation) {
    return string(relation?.confidence || relation?.evidence?.confidence || "authored").toLowerCase();
  }

  function readable(value) {
    return string(value).replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function kindLabel(value) {
    if (value === "all") return text("allKinds");
    const key = `kind${string(value).charAt(0).toUpperCase()}${string(value).slice(1)}`;
    return text(key) === key ? readable(value) : text(key);
  }

  function confidenceText(value) {
    const normalized = string(value).toLowerCase();
    const key = `evidence${normalized.charAt(0).toUpperCase()}${normalized.slice(1)}`;
    return text(key) === key ? readable(value) : text(key);
  }

  function formatValue(value) {
    if (value == null || value === "") return "";
    if (typeof value === "number") return Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 6 }) : string(value);
    if (typeof value === "boolean") return value ? "true" : "false";
    if (Array.isArray(value)) return value.map(formatValue).filter(Boolean).join(", ");
    if (typeof value === "object") {
      try { return JSON.stringify(value, null, 2); } catch (_) { return string(value); }
    }
    return string(value);
  }

  function searchText(entry) {
    return [
      entry.id, entryTitle(entry), entry.kind, entry.description, entry.subtitle, entryLevels(entry), sourceIds(entry),
      relatedValues(entry, "modelIds"), relatedValues(entry, "audioIds"), relatedValues(entry, "enemyIds"),
      entry?.interactiveType, entry?.spawnerType, entry?.templateId, entry?.prefabId,
    ].flat(Infinity).map(string).join(" ").toLowerCase();
  }

  function filteredEntries() {
    const tokens = state.query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const rows = state.entries.filter((entry) => {
      const meta = state.entryMeta.get(entry.id);
      if (state.kind !== "all" && entry.kind !== state.kind) return false;
      if (state.level !== "all" && !meta?.levels.includes(state.level)) return false;
      if (tokens.length && !tokens.every((token) => meta?.searchText.includes(token))) return false;
      return true;
    });
    rows.sort((left, right) => {
      const leftGroup = primaryLevel(left) || "\uffff";
      const rightGroup = primaryLevel(right) || "\uffff";
      return leftGroup.localeCompare(rightGroup) || left.id.localeCompare(right.id);
    });
    return rows;
  }

  function resetVisibleRows() {
    state.visibleLimit = LIST_PAGE_SIZE;
  }

  function resetVisibleRelations() {
    state.relationLimit = RELATION_PAGE_SIZE;
  }

  function countFor(kind) {
    const explicit = state.payload?.counts?.[kind] ?? state.payload?.counts?.kinds?.[kind];
    if (typeof explicit === "number") return explicit;
    if (kind === "all") return state.entries.length;
    return state.kindCounts.get(kind) || 0;
  }

  function badge(value, modifier = "") {
    const label = modifier === "kind" ? kindLabel(value) : (modifier === string(value).toLowerCase() ? confidenceText(value) : readable(value));
    const node = element("span", `world-badge${modifier ? ` world-badge-${modifier}` : ""}`, label);
    return node;
  }

  function renderHeader(root) {
    const header = element("header", "world-header");
    const heading = element("div", "world-heading");
    heading.append(element("span", "world-eyebrow", text("eyebrow")));
    heading.append(element("h2", "world-title", text("title")));
    heading.append(element("p", "world-purpose", text("purpose")));
    heading.append(element("p", "world-why", text("whyCare")));
    header.append(heading);
    const counts = state.payload?.counts || {};
    const relationCount = typeof counts.relations === "number" ? counts.relations : state.relations.length;
    header.append(badge(`${state.entries.length.toLocaleString()} ${text("entries")} / ${relationCount.toLocaleString()} ${text("relationsCount")}`, "count"));
    root.append(header);
  }

  function questionCard(kind, questionKey, answerKey, actionKey, level = "all") {
    const card = element("article", "world-question");
    card.append(element("h3", "", text(questionKey)), element("p", "", text(answerKey)));
    const action = element("button", "world-start-action", `${text(actionKey)} →`);
    action.type = "button";
    action.dataset.worldStart = kind;
    action.dataset.worldLevel = level;
    card.append(action);
    return card;
  }

  function renderGuide(root) {
    const guide = element("section", "world-guide");
    guide.setAttribute("aria-labelledby", "world-start-title");
    const heading = element("div", "world-guide-heading");
    const title = element("h3", "", text("startHere"));
    title.id = "world-start-title";
    heading.append(title, element("p", "", text("startHint")));
    const questions = element("div", "world-question-grid");
    questions.append(
      questionCard("all", "questionMap", "answerMap", "actionMap", DEFAULT_LEVEL),
      questionCard("npcProxy", "questionPlace", "answerPlace", "actionPlace"),
      questionCard("spawner", "questionSpawn", "answerSpawn", "actionSpawn"),
    );
    const notes = element("div", "world-guide-notes");
    const limits = element("details");
    limits.append(element("summary", "", text("limits")), element("p", "", text("limitsBody")), element("p", "world-source-scope", state.uiLocale === "en" ? (state.payload?.scopeNote || text("scope")) : text("scope")));
    const terms = element("details");
    terms.append(element("summary", "", text("terms")), element("p", "", text("termsBody")));
    notes.append(limits, terms);
    guide.append(heading, questions, notes);
    root.append(guide);
  }

  function appendOption(select, value, label, selected = false) {
    const option = element("option", "", label);
    option.value = value;
    option.selected = selected;
    select.append(option);
  }

  function renderToolbar(root) {
    const toolbar = element("div", "world-toolbar");
    toolbar.setAttribute("aria-label", `${text("title")} ${text("filters")}`);
    toolbar.setAttribute("role", "search");
    const searchLabel = element("label", "world-control world-control-search");
    searchLabel.append(element("span", "world-control-label", text("searchLabel")));
    const search = element("input", "world-search");
    search.type = "search";
    search.placeholder = text("search");
    search.value = state.query;
    search.dataset.worldControl = "query";
    search.autocomplete = "off";
    search.setAttribute("aria-controls", "world-results");
    searchLabel.append(search);

    const kindControlLabel = element("label", "world-control");
    kindControlLabel.append(element("span", "world-control-label", text("kind")));
    const kind = element("select", "world-kind-filter");
    kind.dataset.worldControl = "kind";
    const availableKinds = unique([...KINDS, ...state.entries.map((entry) => entry.kind)]);
    availableKinds.forEach((value) => appendOption(kind, value, value === "all" ? text("allKinds") : `${kindLabel(value)} (${countFor(value)})`, value === state.kind));
    kindControlLabel.append(kind);

    const levelControlLabel = element("label", "world-control");
    levelControlLabel.append(element("span", "world-control-label", text("level")));
    const level = element("select", "world-level-filter");
    level.dataset.worldControl = "level";
    appendOption(level, "all", text("allLevels"), state.level === "all");
    state.levels.forEach((value) => appendOption(level, value, levelLabel(value), value === state.level));
    levelControlLabel.append(level);

    const clear = element("button", "world-clear-filters", text("clearFilters"));
    clear.type = "button";
    clear.dataset.worldClear = "";
    clear.disabled = !state.query && state.kind === "all" && state.level === "all";

    toolbar.append(searchLabel, kindControlLabel, levelControlLabel, clear);
    root.append(toolbar);
  }

  function renderList(root) {
    const list = element("aside", "world-list");
    list.dataset.worldList = "";
    list.id = "world-results";
    list.setAttribute("role", "region");
    list.setAttribute("aria-label", text("entries"));
    const rows = filteredEntries();
    if (!rows.length) {
      const count = element("div", "world-list-count", `0 ${text("results")} / ${state.entries.length.toLocaleString()}`);
      count.setAttribute("role", "status");
      count.setAttribute("aria-live", "polite");
      list.append(count);
      list.append(element("div", "world-empty", text("empty")));
      return list;
    }
    if (!rows.some((entry) => entry.id === state.selectedId)) {
      const friendlyMap = state.kind === "map" && !state.query && state.level === "all"
        ? rows.find((entry) => entry.id === "map:map01") || rows.find((entry) => entry.id === "map:map02")
        : null;
      state.selectedId = (friendlyMap || rows[0]).id;
    }
    const selected = rows.find((entry) => entry.id === state.selectedId);
    const visible = rows.slice(0, state.visibleLimit);
    const selectedIsPinned = selected && !visible.includes(selected);
    if (selectedIsPinned) {
      if (visible.length >= LIST_PAGE_SIZE) visible[visible.length - 1] = selected;
      else visible.push(selected);
    }
    const count = element("div", "world-list-count", `${text("showing")} ${Math.min(state.visibleLimit, rows.length).toLocaleString()} ${text("of")} ${rows.length.toLocaleString()} ${text("results")}${rows.length !== state.entries.length ? ` / ${state.entries.length.toLocaleString()} ${text("total")}` : ""}`);
    count.setAttribute("role", "status");
    count.setAttribute("aria-live", "polite");
    list.append(count);
    const groupCounts = new Map();
    rows.forEach((entry) => {
      const group = primaryLevel(entry) || "__unassigned__";
      groupCounts.set(group, (groupCounts.get(group) || 0) + 1);
    });
    let currentGroup = null;
    let groupNode = null;
    visible.forEach((entry) => {
      const group = primaryLevel(entry) || "__unassigned__";
      if (group !== currentGroup) {
        currentGroup = group;
        groupNode = element("section", "world-list-group");
        groupNode.dataset.worldLevelGroup = group;
        const heading = element("h3", "world-list-group-title");
        heading.append(
          element("span", "", group === "__unassigned__" ? text("unassignedGroup") : levelLabel(group)),
          element("span", "world-list-group-count", groupCounts.get(group).toLocaleString()),
        );
        groupNode.append(heading);
        list.append(groupNode);
      }
      const isSelected = entry.id === state.selectedId;
      const button = element("button", `world-row${isSelected ? " is-selected" : ""}`);
      button.type = "button";
      button.dataset.worldId = entry.id;
      if (isSelected) button.setAttribute("aria-current", "true");
      const top = element("span", "world-row-top");
      const title = element("span", "world-row-title", entryTitle(entry));
      if (selectedIsPinned && isSelected) title.append(element("small", "world-selected-note", text("selected")));
      top.append(title, badge(entry.kind, "kind"));
      button.append(top, element("span", "world-row-id", entry.id));
      const levels = entryLevels(entry);
      if (levels.length) button.append(element("span", "world-row-meta", levels.join(" · ")));
      groupNode.append(button);
    });
    if (state.visibleLimit < rows.length) {
      const more = element("button", "world-show-more", `${text("showMore")} (${Math.min(LIST_PAGE_SIZE, rows.length - state.visibleLimit).toLocaleString()})`);
      more.type = "button";
      more.dataset.worldMore = "";
      list.append(more);
    }
    return list;
  }

  function positionValues(entry) {
    const value = entry?.authoredPosition || entry?.position || entry?.transform?.position || entry?.placement?.position;
    const rotation = entry?.rotation || entry?.transform?.rotation || entry?.placement?.rotation;
    const values = [];
    if (value) {
      if (Array.isArray(value) || typeof value !== "object") values.push(["position", value]);
      else Object.entries(value).filter(([, child]) => child != null && child !== "").forEach(([axis, child]) => values.push([`position ${axis}`, child]));
    }
    if (rotation) values.push(["rotation", rotation]);
    return values;
  }

  function facts(entries, className = "world-facts") {
    const dl = element("dl", className);
    entries.filter(([, value]) => value != null && value !== "" && (!Array.isArray(value) || value.length)).forEach(([label, value]) => {
      const item = element("div");
      item.append(element("dt", "", readable(label)), element("dd", "", formatValue(value)));
      dl.append(item);
    });
    return dl;
  }

  function section(title, content, open = true) {
    if (!content || (content.childNodes && !content.childNodes.length)) return null;
    const details = element("details", "world-section");
    details.open = open;
    details.append(element("summary", "", title), content);
    return details;
  }

  function entryRelations(entry) {
    return (state.relationsByEntry.get(entry.id) || []).filter((relation) => {
      if (state.confidence !== "all" && relationConfidence(relation) !== state.confidence) return false;
      return true;
    });
  }

  function evidenceText(relation) {
    const evidence = relation?.evidence;
    if (Array.isArray(evidence)) return evidence.map(evidenceText).filter(Boolean).join(" · ");
    if (evidence && typeof evidence === "object") {
      return compact([evidence.source, evidence.table, evidence.path, evidence.field, evidence.id, evidence.note]).join(" · ");
    }
    return string(evidence || relation?.sourcePath || relation?.note);
  }

  function relationCard(relation, entry) {
    const source = relationSource(relation);
    const target = relationTarget(relation);
    const otherId = source === entry.id ? target : source;
    const other = state.byId.get(otherId);
    const card = element("article", "world-relation");
    card.tabIndex = -1;
    const line = element("div", "world-relation-line");
    const button = element("button", "world-relation-target", other ? entryTitle(other) : otherId || "—");
    button.type = "button";
    if (other) {
      button.dataset.worldId = other.id;
      button.setAttribute("aria-label", `${readable(relationType(relation))}: ${entryTitle(other)}`);
    }
    else button.disabled = true;
    line.append(badge(relationType(relation), "relation"), button, badge(relationConfidence(relation), relationConfidence(relation)));
    card.append(line);
    if (otherId) card.append(element("code", "world-relation-id", otherId));
    const evidence = evidenceText(relation);
    if (evidence) {
      const evidenceNode = element("p", "world-evidence");
      evidenceNode.append(element("strong", "", `${text("evidence")}: `), element("span", "", evidence));
      card.append(evidenceNode);
    }
    return card;
  }

  function configurationFacts(entry) {
    const omitted = new Set(["id", "key", "entryId", "kind", "type", "category", "name", "title", "label", "displayName", "description", "subtitle", "source", "evidence", "sourceId", "sourceIds", "position", "authoredPosition", "rotation", "relations"]);
    return Object.entries(entry).filter(([key, value]) => !omitted.has(key) && value != null && value !== "");
  }

  function svgElement(tag, attributes = {}) {
    const node = typeof document.createElementNS === "function"
      ? document.createElementNS("http://www.w3.org/2000/svg", tag)
      : document.createElement(tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, string(value)));
    return node;
  }

  function mapLevel(entry) {
    if (state.level !== "all" && state.levels.includes(state.level)) return state.level;
    const selectedLevels = state.entryMeta.get(entry?.id)?.levels || [];
    return selectedLevels.find((value) => /_lv\d+$/i.test(value)) || selectedLevels[0] || "";
  }

  function sampledPoints(points, selectedId) {
    if (points.length <= MAP_POINT_LIMIT) return points;
    const stride = points.length / MAP_POINT_LIMIT;
    const sampled = [];
    for (let index = 0; index < MAP_POINT_LIMIT; index += 1) sampled.push(points[Math.floor(index * stride)]);
    const selected = points.find((point) => point.entry.id === selectedId);
    if (selected && !sampled.some((point) => point.entry.id === selectedId)) sampled[sampled.length - 1] = selected;
    return sampled;
  }

  function renderPlacementMap(root, entry) {
    const panel = element("section", "world-map-panel");
    panel.setAttribute("aria-labelledby", "world-map-title");
    const heading = element("div", "world-map-heading");
    const title = element("div");
    const titleNode = element("h3", "", text("mapTitle"));
    titleNode.id = "world-map-title";
    const levelId = mapLevel(entry);
    title.append(titleNode, element("p", "world-map-level", levelId ? levelLabel(levelId) : text("unassignedGroup")));
    heading.append(title);
    panel.append(heading);

    let candidates = levelId ? (state.positionsByLevel.get(levelId) || []) : [];
    const selectedCoordinates = authoredCoordinates(entry);
    const isolated = !levelId && selectedCoordinates ? [{ entry, coordinates: selectedCoordinates }] : [];
    if (!candidates.length) candidates = isolated;
    const levelRows = levelId ? state.entries.filter((candidate) => state.entryMeta.get(candidate.id)?.levels.includes(levelId)) : [];
    const missingCount = Math.max(0, levelRows.length - candidates.length);

    if (!candidates.length) {
      panel.append(element("div", "world-map-empty", text("mapEmpty")));
      if (entry && !selectedCoordinates) panel.append(element("p", "world-map-note", `${entryTitle(entry)}: ${text("mapMissing")}`));
      root.append(panel);
      return;
    }

    const points = sampledPoints(candidates, entry?.id);
    const xs = candidates.map((point) => point.coordinates.x);
    const zs = candidates.map((point) => point.coordinates.z);
    let minX = Math.min(...xs); let maxX = Math.max(...xs);
    let minZ = Math.min(...zs); let maxZ = Math.max(...zs);
    if (minX === maxX) { minX -= 1; maxX += 1; }
    if (minZ === maxZ) { minZ -= 1; maxZ += 1; }
    const padX = (maxX - minX) * 0.06;
    const padZ = (maxZ - minZ) * 0.06;
    minX -= padX; maxX += padX; minZ -= padZ; maxZ += padZ;
    const width = 1000; const height = 610; const inset = 46;
    const plotWidth = width - inset * 2; const plotHeight = height - inset * 2;
    const project = (coordinates) => ({
      x: inset + ((coordinates.x - minX) / (maxX - minX)) * plotWidth,
      y: inset + (1 - ((coordinates.z - minZ) / (maxZ - minZ))) * plotHeight,
    });
    const svg = svgElement("svg", { class: "world-map", viewBox: `0 0 ${width} ${height}`, role: "group", "aria-label": `${text("mapTitle")}: ${levelId ? levelLabel(levelId) : text("unassignedGroup")}` });
    svg.append(svgElement("rect", { class: "world-map-background", x: inset, y: inset, width: plotWidth, height: plotHeight, rx: 9 }));
    for (let step = 0; step <= 4; step += 1) {
      const x = inset + plotWidth * (step / 4);
      const y = inset + plotHeight * (step / 4);
      svg.append(svgElement("line", { class: "world-map-grid", x1: x, y1: inset, x2: x, y2: height - inset }));
      svg.append(svgElement("line", { class: "world-map-grid", x1: inset, y1: y, x2: width - inset, y2: y }));
    }
    const xLabel = svgElement("text", { class: "world-map-axis", x: width - inset, y: height - 12, "text-anchor": "end" });
    xLabel.textContent = `X  ${formatValue(minX)} \u2192 ${formatValue(maxX)}`;
    const zLabel = svgElement("text", { class: "world-map-axis", x: 12, y: inset, transform: `rotate(-90 12 ${inset})`, "text-anchor": "end" });
    zLabel.textContent = `Z  ${formatValue(minZ)} \u2192 ${formatValue(maxZ)}`;
    svg.append(xLabel, zLabel);
    points.forEach((point) => {
      const plotted = project(point.coordinates);
      const selected = point.entry.id === entry?.id;
      const label = `${entryTitle(point.entry)} \u00b7 ${kindLabel(point.entry.kind)} \u00b7 X ${formatValue(point.coordinates.x)}, Z ${formatValue(point.coordinates.z)}`;
      const hitTarget = svgElement("circle", {
        class: `world-map-hit${selected ? " is-selected" : ""}`,
        cx: plotted.x, cy: plotted.y, r: 18, tabindex: 0, role: "button",
        "aria-label": label, "aria-pressed": selected ? "true" : "false",
      });
      hitTarget.dataset.worldId = point.entry.id;
      hitTarget.dataset.worldMapId = point.entry.id;
      hitTarget.dataset.worldMapLabel = label;
      const tooltip = svgElement("title");
      tooltip.textContent = label;
      hitTarget.append(tooltip);
      const circle = svgElement("circle", {
        class: `world-map-point world-map-point-${point.entry.kind}${selected ? " is-selected" : ""}`,
        cx: plotted.x, cy: plotted.y, r: selected ? 8 : 5, "aria-hidden": "true",
      });
      svg.append(hitTarget, circle);
    });
    panel.append(svg);
    const readout = element("output", "world-map-readout", entry && selectedCoordinates
      ? `${entryTitle(entry)} \u00b7 X ${formatValue(selectedCoordinates.x)}, Z ${formatValue(selectedCoordinates.z)}`
      : text("mapPointHint"));
    readout.dataset.worldMapReadout = "";
    panel.append(readout);
    const summary = element("p", "world-map-note", `${candidates.length.toLocaleString()} ${text("mapShowing")} \u00b7 ${missingCount.toLocaleString()} ${text("mapMissing")}`);
    panel.append(summary, element("p", "world-map-note", text("mapAxes")));
    if (isolated.length) panel.append(element("p", "world-map-warning", text("mapNoLevel")));
    if (candidates.length > MAP_POINT_LIMIT) panel.append(element("p", "world-map-warning", text("mapLimited")));
    root.append(panel);
  }

  function renderDetail(root, entry) {
    const detail = element("main", "world-detail");
    detail.dataset.worldDetail = "";
    detail.tabIndex = -1;
    if (!entry) {
      detail.append(element("div", "world-empty", text("selectPrompt")));
      return detail;
    }
    renderPlacementMap(detail, entry);
    const card = element("article", "world-detail-card");
    const header = element("header", "world-detail-header");
    const title = element("div");
    const heading = element("h3", "", entryTitle(entry));
    heading.id = "world-detail-title";
    title.append(badge(entry.kind, "kind"), heading);
    if (entry.description || entry.subtitle) title.append(element("p", "", entry.description || entry.subtitle));
    header.append(title, element("code", "world-detail-id", entry.id));
    card.append(header);
    card.setAttribute("aria-labelledby", heading.id);

    const position = section(text("authoredPosition"), facts(positionValues(entry)), true);
    if (position) card.append(position);

    const relationBox = element("div", "world-relation-box");
    const confidenceLabel = element("label", "world-relation-filter");
    confidenceLabel.append(element("span", "world-control-label", text("confidence")));
    const confidence = element("select", "world-confidence-filter");
    confidence.dataset.worldControl = "confidence";
    const confidences = unique(["all", ...state.relations.map(relationConfidence)]);
    confidences.forEach((value) => appendOption(confidence, value, value === "all" ? text("allConfidence") : confidenceText(value), value === state.confidence));
    confidenceLabel.append(confidence);
    relationBox.append(confidenceLabel);
    const relations = entryRelations(entry);
    const visibleRelations = relations.slice(0, state.relationLimit);
    if (visibleRelations.length) visibleRelations.forEach((relation) => relationBox.append(relationCard(relation, entry)));
    else relationBox.append(element("div", "world-empty", text("noRelations")));
    if (state.relationLimit < relations.length) {
      const more = element("button", "world-show-more world-relations-more", `${text("showMore")} (${Math.min(RELATION_PAGE_SIZE, relations.length - state.relationLimit).toLocaleString()})`);
      more.type = "button";
      more.dataset.worldRelationsMore = "";
      relationBox.append(more);
    }
    card.append(section(`${text("relations")} (${relations.length})`, relationBox, true));

    const source = entry.source || entry.evidence || {};
    const sourceSection = section(text("source"), facts([
      ["source", typeof source === "object" ? "" : source], ["source ids", unique([...array(entry.sourceIds), entry.sourceId])], ["table", source.table],
      ["path", source.path], ["asset", source.asset], ["file", source.file],
    ]), false);
    if (sourceSection) card.append(sourceSection);

    const configSection = section(text("configuration"), facts(configurationFacts(entry)), false);
    if (configSection) card.append(configSection);
    detail.append(card);
    return detail;
  }

  function ingestPayload(payload) {
    state.payload = payload;
    state.entries = array(payload.entries).map(normalizeEntry);
    state.relations = array(payload.relations).filter((relation) => relation && typeof relation === "object");
    state.byId = new Map(state.entries.map((entry) => [entry.id, entry]));
    state.entryMeta = new Map();
    state.levelNames = new Map();
    state.positionsByLevel = new Map();
    state.kindCounts = new Map();
    state.entries.filter((entry) => entry.kind === "level").forEach((entry) => {
      const levelId = entry.id.startsWith("level:") ? entry.id.slice(6) : primaryLevel(entry);
      if (levelId) state.levelNames.set(levelId, entryTitle(entry));
    });
    state.entries.filter((entry) => entry.kind === "map").forEach((entry) => {
      const mapId = string(entry.mapId || (entry.id.startsWith("map:") ? entry.id.slice(4) : ""));
      if (mapId && !state.levelNames.has(mapId)) state.levelNames.set(mapId, entryTitle(entry));
    });
    state.entries.forEach((entry) => {
      const levels = entryLevels(entry);
      state.entryMeta.set(entry.id, { levels, searchText: searchText(entry) });
      state.kindCounts.set(entry.kind, (state.kindCounts.get(entry.kind) || 0) + 1);
      const coordinates = authoredCoordinates(entry);
      if (coordinates) levels.forEach((levelId) => {
        if (!state.positionsByLevel.has(levelId)) state.positionsByLevel.set(levelId, []);
        state.positionsByLevel.get(levelId).push({ entry, coordinates });
      });
    });
    state.levels = unique([...state.entryMeta.values()].flatMap((meta) => meta.levels)).sort((a, b) => a.localeCompare(b));
    if (state.level !== "all" && !state.levels.includes(state.level)) state.level = state.levels.includes(DEFAULT_LEVEL) ? DEFAULT_LEVEL : "all";
    const requestedId = string(state.options.selectedId || state.selectedId);
    const requested = state.byId.get(requestedId);
    if (requested && state.options.selectedId) {
      state.selectedId = requestedId;
      state.query = "";
      state.kind = "all";
      state.level = primaryLevel(requested) || "all";
      state.options.selectedId = "";
    }
    state.relationsByEntry = new Map();
    state.relations.forEach((relation) => {
      const source = relationSource(relation);
      const target = relationTarget(relation);
      if (source) {
        if (!state.relationsByEntry.has(source)) state.relationsByEntry.set(source, []);
        state.relationsByEntry.get(source).push(relation);
      }
      if (target && target !== source) {
        if (!state.relationsByEntry.has(target)) state.relationsByEntry.set(target, []);
        state.relationsByEntry.get(target).push(relation);
      }
    });
    if (payload.language) state.language = string(payload.language).toUpperCase();
    resetVisibleRows();
    resetVisibleRelations();
  }

  function focusWorldRow(id) {
    const row = [...(state.container?.querySelectorAll("[data-world-id]") || [])].find((node) => node.dataset.worldId === id);
    row?.focus();
  }

  function focusWorldMapPoint(id) {
    const point = [...(state.container?.querySelectorAll("[data-world-map-id]") || [])].find((node) => node.dataset.worldMapId === id);
    point?.focus();
  }

  function render(payload) {
    if (!state.container) return state;
    if (payload) ingestPayload(payload);
    state.container.replaceChildren();
    state.container.classList.add("world-explorer");
    if (!state.payload) {
      const status = element("div", "world-empty world-state");
      status.setAttribute("role", state.lastError ? "alert" : "status");
      status.append(element("strong", "", state.loading ? text("loading") : text("unavailable")));
      if (state.lastError) {
        status.append(element("small", "", state.lastError));
        const retry = element("button", "world-retry", text("retry"));
        retry.type = "button";
        retry.dataset.worldRetry = "";
        status.append(retry);
      }
      state.container.append(status);
      return state;
    }
    renderHeader(state.container);
    renderGuide(state.container);
    renderToolbar(state.container);
    const workspace = element("div", "world-workspace");
    const list = renderList(workspace);
    workspace.append(list, renderDetail(workspace, state.byId.get(state.selectedId)));
    state.container.append(workspace);
    return state;
  }

  function select(id, focusTarget = "row") {
    const target = string(id);
    if (!state.byId.has(target)) return false;
    if (!filteredEntries().some((entry) => entry.id === target)) {
      state.query = "";
      state.kind = "all";
      state.level = primaryLevel(state.byId.get(target)) || "all";
      resetVisibleRows();
    }
    state.selectedId = target;
    resetVisibleRelations();
    render();
    if (focusTarget === "map") focusWorldMapPoint(target);
    else if (focusTarget === "row") focusWorldRow(target);
    state.container?.dispatchEvent(new CustomEvent("worldselect", { detail: { id: target, entry: state.byId.get(target) } }));
    return true;
  }

  async function load(language = currentLanguage(), force = false, url = "") {
    const nextLanguage = string(language || DEFAULT_LANGUAGE).toUpperCase();
    if (!force && state.payload && state.language === nextLanguage) return state.payload;
    if (!force && state.loading && state.language === nextLanguage) return state.loading;
    state.abortController?.abort();
    const controller = new AbortController();
    const token = ++state.loadToken;
    state.abortController = controller;
    state.language = nextLanguage;
    state.lastError = "";
    state.payload = null;
    state.loading = Promise.resolve(null);
    render();
    state.loading = (async () => {
      try {
        const response = await fetch(url || state.options.dataUrl || dataPath(nextLanguage), { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        if (!payload || !Array.isArray(payload.entries) || !Array.isArray(payload.relations)) throw new Error("Unsupported world data payload");
        if (token !== state.loadToken) return null;
        state.payload = payload;
        render(payload);
        return payload;
      } catch (error) {
        if (error?.name === "AbortError") return null;
        if (token === state.loadToken) {
          state.payload = null;
          state.lastError = error instanceof Error ? error.message : string(error);
          console.warn("World data load failed", error);
        }
        return null;
      } finally {
        if (token === state.loadToken) {
          state.loading = null;
          state.abortController = null;
          if (!state.payload) render();
        }
      }
    })();
    return state.loading;
  }

  function bindEvents() {
    listen(state.container, "input", (event) => {
      if (event.target?.dataset.worldControl !== "query") return;
      state.query = event.target.value || "";
      resetVisibleRows();
      resetVisibleRelations();
      render();
      const next = state.container?.querySelector('[data-world-control="query"]');
      if (next) { next.focus(); next.setSelectionRange(state.query.length, state.query.length); }
    });
    listen(state.container, "change", (event) => {
      const control = event.target?.dataset.worldControl;
      if (control === "kind") {
        state.kind = event.target.value || "all"; state.selectedId = ""; resetVisibleRows(); resetVisibleRelations(); render();
        state.container?.querySelector('[data-world-control="kind"]')?.focus();
      }
      else if (control === "level") {
        state.level = event.target.value || "all"; state.selectedId = ""; resetVisibleRows(); resetVisibleRelations(); render();
        state.container?.querySelector('[data-world-control="level"]')?.focus();
      }
      else if (control === "confidence") {
        state.confidence = event.target.value || "all";
        resetVisibleRelations();
        render();
        state.container?.querySelector('[data-world-control="confidence"]')?.focus();
      }
    });
    listen(state.container, "click", (event) => {
      if (event.target.closest?.("[data-world-retry]")) {
        const retry = window.WebUI?.retryViewLoad || window.WebUI?.retryView;
        if (typeof retry === "function") retry("world", currentLanguage());
        else load(currentLanguage(), true);
        return;
      }
      if (event.target.closest?.("[data-world-clear]")) {
        state.query = "";
        state.kind = "all";
        state.level = "all";
        state.selectedId = "";
        resetVisibleRows();
        resetVisibleRelations();
        render();
        state.container?.querySelector('[data-world-control="query"]')?.focus();
        return;
      }
      const start = event.target.closest?.("[data-world-start]");
      if (start) {
        state.query = "";
        state.kind = start.dataset.worldStart || "map";
        state.level = start.dataset.worldLevel || "all";
        state.selectedId = "";
        resetVisibleRows();
        resetVisibleRelations();
        render();
        state.container?.querySelector('[data-world-control="level"]')?.focus();
        return;
      }
      if (event.target.closest?.("[data-world-more]")) {
        const previousLimit = state.visibleLimit;
        state.visibleLimit += LIST_PAGE_SIZE;
        render();
        const nextMore = state.container?.querySelector("[data-world-more]");
        const rows = [...(state.container?.querySelectorAll(".world-row") || [])];
        (nextMore || rows[Math.min(previousLimit, rows.length - 1)])?.focus();
        return;
      }
      if (event.target.closest?.("[data-world-relations-more]")) {
        const previousLimit = state.relationLimit;
        state.relationLimit += RELATION_PAGE_SIZE;
        render();
        const nextMore = state.container?.querySelector("[data-world-relations-more]");
        const relations = [...(state.container?.querySelectorAll(".world-relation") || [])];
        (nextMore || relations[Math.min(previousLimit, relations.length - 1)])?.focus();
        return;
      }
      const target = event.target.closest?.("[data-world-id]");
      if (target) select(target.dataset.worldId, target.dataset.worldMapId ? "map" : "row");
    });
    const updateMapReadout = (event) => {
      const point = event.target.closest?.("[data-world-map-id]");
      const readout = state.container?.querySelector("[data-world-map-readout]");
      if (point && readout) readout.textContent = point.dataset.worldMapLabel || point.getAttribute("aria-label") || text("mapPointHint");
    };
    listen(state.container, "pointerover", updateMapReadout);
    listen(state.container, "focusin", updateMapReadout);
    listen(state.container, "keydown", (event) => {
      const point = event.target.closest?.("[data-world-map-id][data-world-id]");
      if (point && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        select(point.dataset.worldId, "map");
        return;
      }
      const row = event.target.closest?.(".world-row[data-world-id]");
      if (!row || !["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const rows = filteredEntries();
      const current = rows.findIndex((entry) => entry.id === row.dataset.worldId);
      const next = event.key === "Home" ? 0 : event.key === "End" ? rows.length - 1 : Math.max(0, Math.min(rows.length - 1, current + (event.key === "ArrowDown" ? 1 : -1)));
      if (rows[next]) select(rows[next].id);
    });
    listen(window, "webui:view-changed", (event) => { if (event.detail?.view === "world") load(currentLanguage()); });
    listen(window, "webui:language-changed", (event) => { if (isActive()) load(event.detail?.language || currentLanguage(), true); });
    listen(window, "webui:ui-locale-changed", (event) => {
      state.uiLocale = string(event.detail?.locale || "en").toLowerCase().startsWith("zh") ? "zh" : "en";
      render();
    });
    listen(window, "hashchange", () => { if (isActive()) load(currentLanguage()); });
  }

  function destroy() {
    state.abortController?.abort();
    state.loadToken += 1;
    state.listeners.splice(0).forEach((remove) => remove());
    if (state.container) {
      state.container.classList.remove("world-explorer");
      state.container.replaceChildren();
    }
    state.container = null;
    state.payload = null;
    state.entries = [];
    state.relations = [];
    state.byId = new Map();
    state.relationsByEntry = new Map();
    state.entryMeta = new Map();
    state.levels = [];
    state.kindCounts = new Map();
    state.loading = null;
    state.lastError = "";
    state.abortController = null;
    resetVisibleRows();
    resetVisibleRelations();
    state.options = {};
    state.initialized = false;
  }

  function init(options = {}) {
    if (state.initialized) return state;
    const container = options.container instanceof Element ? options.container : document.querySelector(options.container || DEFAULT_CONTAINER);
    if (!container) return state;
    state.container = container;
    state.options = { ...options };
    if (options.selectedId) state.selectedId = string(options.selectedId);
    state.initialized = true;
    state.language = string(options.language || currentLanguage()).toUpperCase();
    state.uiLocale = string(options.uiLocale || detectLocale()).toLowerCase().startsWith("zh") ? "zh" : "en";
    bindEvents();
    if (options.payload) render(options.payload);
    else {
      render();
      if (options.load !== false && isActive()) load(state.language, false, options.dataUrl || "");
    }
    return state;
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.world = { init, load, render, select, destroy, state, containerId: "world-app", dataPath };

  const autoInit = () => { if (document.querySelector(DEFAULT_CONTAINER)) init(); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoInit, { once: true });
  else autoInit();
})();
