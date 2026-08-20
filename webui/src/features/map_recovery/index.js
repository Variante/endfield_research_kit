(() => {
  // The SVG world projection below is authoritative: viewBox size, padding and
  // plot() must stay byte-identical to the published coordinate contract.
  // Zoom/pan is layered strictly on top of it as a group transform, so screen
  // navigation never rewrites world coordinates.
  const WIDTH = 1024;
  const HEIGHT = 1280;
  const PAD = 64;
  const MIN_SCALE = 0.3; // a whole region can span several zone maps of canvas
  const MAX_SCALE = 14;
  const PAN_OVERHANG = 96; // px of surface a pan may run past the content edge
  const LABEL_ZOOM = 1.7; // minor labels stay hidden below this zoom
  const LABEL_CHAR = 7.3; // 12px monospace advance, used for overlap boxes
  const LABEL_LINE = 14;
  // Entity names are Chinese, and a CJK glyph fills a full-width monospace cell.
  // Counting it as one advance under-measures the box and lets labels overlap.
  const WIDE_GLYPH = /[⺀-⿟぀-ヿ㐀-䶿一-鿿가-힯]/;
  const PAN_STEP = 48; // px moved per arrow key press
  // Kept in sync with the --mr-* custom properties in style.css.
  const KIND_COLORS = {
    story: "#c8410f",
    travel: "#2b6cb0",
    device: "#a2660a",
    scenery: "#7a6a52",
    trigger: "#7759a8",
    enemy: "#b0342c",
    npc: "#2f7d4f",
    spawn: "#367f84",
    narrative: "#a03c86",
    collectible: "#8a7b1f",
    waypoint: "#4a6b8a",
  };
  const QUEST_COLOR = "#2f7d4f";
  const EDGE_STYLES = {
    same_file: { stroke: "#93b8d6", dash: "6 4", width: 1.4 },
    same_script: { stroke: "#b9a8e0", dash: "2 4", width: 1.1 },
  };
  const MAX_EDGE_GROUP = 24; // nodes sharing one file/script before the clique is dropped
  const MAX_EDGES = 4000; // total relation lines drawn on one map
  const MAX_PREVIEW_BYTES = 200000; // conv payloads carry large _debug blocks
  const MAX_DIALOG_LINES = 120;
  const MAX_RAW_CHARS = 12000;
  const MAX_TOKENS = 400;

  const state = {
    index: null,
    map: null,
    selected: "",
    kinds: new Set(),
    subKinds: new Set(),
    mapLayers: new Set(), // raw UILevelMapLoadConfig tier ids in the loaded region
    storyOnly: false,
    mission: "", // "" means every mission this level hosts
    // Relation lines are cliques: every pair of markers sharing a level-script
    // file gets one, so a group of n draws n(n-1)/2 lines that all say the same
    // thing. Showing them only for the focused node keeps the evidence without
    // the permanent web.
    relations: "focus",
    bound: false,
    transform: { x: 0, y: 0, scale: 1 },
    nodes: [],
    selectedId: "",
    previewId: "",
    inspectorKey: "",
    filePath: "",
    filePathLabel: "",
    pendingFit: false,
    dragging: null,
    pointers: new Map(),
    pinch: null,
    animation: 0,
    suppressClickUntil: 0,
    observer: null,
    fileCache: new Map(),
    fileFlight: new Map(),
    edges: [],
    payloads: new Map(), // levelId -> payload; siblings of a region share the cache
    backgrounds: [], // every region zone's map screen, in draw order (selected last)
    layerBackgrounds: [], // transparent tier overlays, kept separate from base screens
    contentBox: null, // plotted content extent in viewBox units, for the pan clamp
    lastNodeScale: null, // skip per-node writes while a pan keeps the same scale
    loadRequest: 0,
    loadController: null,
  };

  // The page re-renders its whole DOM on every filter change, so floating panel
  // positions and collapsed states live outside the element tree.
  const panelUi = new Map();

  const root = () => document.querySelector("#map-recovery-app");
  const mapEl = () => root()?.querySelector(".mr-map");
  const svgEl = () => root()?.querySelector(".mr-canvas");
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
  const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
  // Mission text carries inline rich-text tags such as <@qu.key>; strip them
  // the same way the mission-pipeline view does instead of rendering markup.
  const plainText = (value) => String(value ?? "").replace(/<@[^>]*>/g, "").replace(/<\/[^>]+>/g, "").replace(/<[^>]+>/g, "").replaceAll("\\n", " ").trim();
  const uniq = (values) => [...new Set(values.map((value) => String(value || "").trim()).filter(Boolean))];
  const sourcePaths = (node) => uniq([...(node?.sourceFiles || []), ...(node?.source ? [node.source] : [])]);
  // The builder marks registry-placed nodes with `registryBacked` instead of
  // repeating one identical 7 MB registry path on thousands of markers. The pin
  // is rebuilt here from the node's own level entry, so the inspector shows the
  // same evidence it always did without the payload carrying it per node. In a
  // region surface a marker may come from any sibling level, so the pin comes
  // from that level's payload, not from the selected one.
  const registryPin = (node) => {
    const source = state.payloads.get(node?.levelId) || state.map;
    return ((source?.relatedFiles) || []).find((row) => row?.relation === "entity_registry");
  };
  const relatedFiles = (node) => {
    const rows = (node?.relatedFiles || []).filter((row) => row && row.path);
    const registry = node?.registryBacked ? registryPin(node) : null;
    if (!registry || rows.some((row) => row.path === registry.path)) return rows;
    return [...rows, { ...registry, note: t("registryBacked") }];
  };
  const fileName = (path) => String(path || "").replace(/\\/g, "/").split("/").filter(Boolean).pop() || String(path || "");
  const kindColor = (node) => (node?.type === "quest" ? QUEST_COLOR : KIND_COLORS[node?.kind] || "#8b9298");
  // Re-plotting a full map is a few hundred milliseconds of SVG layout, and the
  // two-level layer tree invites several clicks in a row, so filter changes
  // coalesce into a single render. This deliberately uses a timer rather than
  // requestAnimationFrame: rAF does not fire while the tab is hidden, which
  // would leave a toggled filter silently unapplied until the tab is focused.
  let filterTimer = 0;
  function scheduleRender() {
    if (filterTimer) return;
    filterTimer = setTimeout(() => {
      filterTimer = 0;
      render();
    }, 0);
  }

  const allSubKinds = (map) => new Set(
    Object.values(map?.facets?.kinds || {}).flatMap((info) => Object.keys(info.subKinds || {}))
  );

  const allMapLayers = (map) => new Set(
    (map?.mapLayers || []).map((row) => String(row.id)).filter(Boolean)
  );

  const mapLayerTreeHtml = (data) => {
    const layers = data.mapLayers || [];
    if (!layers.length) return `<p class="mr-note">${esc(t("mapLayersNone"))}</p>`;
    return layers.map((layer) => {
      const label = layer.nameKey || String(layer.tierId ?? layer.id);
      const range = layer.heightRange && Number.isFinite(Number(layer.heightRange.minY))
        ? ` · Y ${Number(layer.heightRange.minY).toFixed(1)}..${Number(layer.heightRange.maxY).toFixed(1)}` : "";
      return `<label class="mr-layer" title="${esc(`${label}${range}`)}"><input type="checkbox" data-map-tier="${esc(layer.id)}" ${state.mapLayers.has(String(layer.id)) ? "checked" : ""}>${esc(label)}<span class="mr-layer-count">${layer.tileCount || 0}</span></label>`;
    }).join("");
  };

  // A full region can contain thousands of entity markers. Keep the first
  // view useful (quest points plus markers that carry dialog) without asking
  // the browser to lay out every collectible, prop and scenery marker before
  // the reader has chosen a layer. The layer controls remain the explicit way
  // to widen or narrow this initial view.
  const storyKinds = (map) => new Set(
    Object.entries(map?.facets?.kinds || {})
      .filter(([, info]) => Number(info?.storyCount || 0) > 0)
      .map(([kind]) => kind)
  );

  // Every level in LevelBasicInfoTable that owns a plottable node is published,
  // which is far too many for a flat list to be readable. The options are
  // grouped by the level family the builder assigns and annotated with the two
  // numbers that decide whether a map is worth opening: how many nodes it plots
  // and how many distinct story keys those nodes reach.
  // A level id alone does not say which place the reader is looking at, so
  // every level carries the display name the builder recovered from the
  // level's own table rows (LevelDescTable + per-language I18nTextTable),
  // keeping the id as the stable handle next to it.
  const mapTitle = (row) => (row.name ? `${row.name} (${row.id})` : row.label);

  const mapOptions = () => {
    const groups = new Map();
    for (const row of state.index?.maps || []) {
      const family = row.family || "—";
      if (!groups.has(family)) groups.set(family, []);
      groups.get(family).push(row);
    }
    return [...groups.entries()].map(([family, rows]) => {
      const options = rows.map((row) => {
        const counts = [
          row.markerCount ? `${row.markerCount}${t("countMarkers")}` : "",
          row.storyKeyCount ? `${row.storyKeyCount}${t("countStories")}` : "",
        ].filter(Boolean).join(" · ");
        const label = counts ? `${mapTitle(row)} — ${counts}` : mapTitle(row);
        return `<option value="${esc(row.id)}" ${row.id === state.selected ? "selected" : ""}>${esc(label)}</option>`;
      }).join("");
      return `<optgroup label="${esc(family)}">${options}</optgroup>`;
    }).join("");
  };

  // The layer tree is two levels deep because "collectible" is not one thing:
  // chests, ore nodes and currency pickups are separate answers to separate
  // questions. A kind with a single subKind stays a plain row - nesting it would
  // be noise. Counts come from the published facets rather than a node scan, so
  // a hidden layer still shows how much it is hiding.
  const layerTreeHtml = (data) => {
    const kinds = data.facets?.kinds || {};
    return Object.entries(kinds).map(([kind, info]) => {
      const swatch = `<span class="mr-swatch" style="background:${esc(KIND_COLORS[kind] || "#8b9298")}"></span>`;
      const head = `<label class="mr-layer" title="${esc(`${info.count}${t("countMarkers")}${info.storyCount ? ` · ${info.storyCount}${t("countStories")}` : ""}`)}">`
        + `<input type="checkbox" data-map-kind="${esc(kind)}" ${state.kinds.has(kind) ? "checked" : ""}>`
        + `${swatch}${esc(kind)}<span class="mr-layer-count">${info.count}${info.storyCount ? `<i>+${info.storyCount}</i>` : ""}</span></label>`;
      const subs = Object.entries(info.subKinds || {});
      if (subs.length < 2) return `<div class="mr-layer-group">${head}</div>`;
      const rows = subs
        .sort((a, b) => b[1].count - a[1].count)
        .map(([subKind, sub]) => {
          // The recovered labels are Chinese, so an English reader is better
          // served by the subKind slug. Both are always in the tooltip.
          const shown = isZh() ? (sub.label || subKind) : subKind;
          const title = sub.label && sub.label !== subKind ? `${sub.label} / ${subKind}` : subKind;
          return `<label class="mr-layer mr-sublayer" title="${esc(title)}"><input type="checkbox" data-map-subkind="${esc(subKind)}" ${state.subKinds.has(subKind) ? "checked" : ""}>`
            + `${esc(shown)}<span class="mr-layer-count">${sub.count}</span></label>`;
        })
        .join("");
      return `<div class="mr-layer-group">${head}<div class="mr-sublayers">${rows}</div></div>`;
    }).join("");
  };

  // Missions are ordered by how much of the map they account for, so the ones
  // worth isolating are at the top rather than in alphabetical order.
  const missionSelectHtml = (data) => {
    const missions = Object.entries(data.facets?.missions || {});
    if (!missions.length) return `<p class="mr-note">${esc(t("missionNone"))}</p>`;
    const options = missions
      .sort((a, b) => (b[1].markers + b[1].questPoints) - (a[1].markers + a[1].questPoints) || a[0].localeCompare(b[0]))
      .map(([id, counts]) => {
        const weight = `${counts.markers + counts.questPoints}${t("countMarkers")}${counts.stories ? ` · ${counts.stories}${t("countStories")}` : ""}`;
        return `<option value="${esc(id)}" ${id === state.mission ? "selected" : ""}>${esc(`${id} — ${weight}`)}</option>`;
      }).join("");
    return `<select id="map-recovery-mission" aria-label="${esc(t("mission"))}">`
      + `<option value="" ${state.mission ? "" : "selected"}>${esc(`${t("missionAll")} (${missions.length})`)}</option>${options}</select>`;
  };

  // A pinned dialog file is the same payload the Story view renders, so its
  // path carries everything the Story deep link needs. Deriving the data
  // language from the path keeps this view from having to track it separately.
  const CONV_PATH = /^webui\/data\/lang\/([^/]+)\/conv\/(.+)\.json$/;
  function storyRef(path) {
    const match = CONV_PATH.exec(String(path || "").replace(/\\/g, "/"));
    if (!match) return null;
    const params = new URLSearchParams();
    params.set("lang", match[1]);
    params.set("ui", isZh() ? "zh" : "en");
    params.set("story", match[2]);
    return { key: match[2], href: `?${params.toString()}#story` };
  }

  const storyLink = (path, label) => {
    const ref = storyRef(path);
    return ref ? `<a class="mr-story-link" href="${esc(ref.href)}" title="${esc(`${t("openInStory")}: ${ref.key}`)}">${esc(label || t("story"))}</a>` : "";
  };

  const nodeDisplayLabel = (node) => {
    if (node.type === "quest") return String(node.questId).replace("e0m0_", "");
    const alias = node.detailAlias && (isZh() ? node.detailAlias.zh : node.detailAlias.en);
    if (alias && alias !== node.label) return `${alias} / ${node.label}`;
    return String(node.label || node.identity);
  };

  function labelWidth(text) {
    let cells = 0;
    for (const ch of String(text)) cells += WIDE_GLYPH.test(ch) ? 2 : 1;
    return cells * LABEL_CHAR;
  }

  const TEXT = {
    en: {
      title: "Map Recovery",
      layers: "Layers",
      mapLayers: "Map floors",
      mapLayersNone: "No tier overlays are declared by this level's UILevelMapLoadConfig.",
      evidence: "Evidence",
      controls: "Controls",
      collapse: "Collapse panel",
      regionSurface: "zone map screens stitched into one seamless surface",
      selectedSurface: "selected zone map screen loaded; choose another zone to load the stitched region",
      loading: "Loading map recovery data...",
      mapSurface: "World map, pan and zoom surface",
      zoomIn: "Zoom in",
      zoomOut: "Zoom out",
      fit: "Fit",
      fitLong: "Fit all plotted nodes",
      reset: "Reset",
      resetLong: "Reset to full declared world bounds",
      zoomLevel: "Zoom",
      help: "Wheel or +/- zooms, drag or arrows pan, Tab walks the nodes, Enter pins one, Esc clears, 0 resets, F fits.",
      questPoint: "Quest point",
      entityNode: "Entity node",
      noNodes: "No plotted nodes for current layers.",
      questPoints: "quest points",
      entityMarkers: "markers",
      pinnedFiles: "pinned files",
      exactNpcs: "exact NPCs",
      storyNodes: "nodes with dialog",
      shownNodes: "shown by filters",
      countMarkers: " nodes",
      countStories: " stories",
      registryBacked: "Placed by the WorldEntityRegistry row for this level.",
      mission: "Mission",
      missionAll: "All missions",
      missionNone: "No mission plots content in this level.",
      layersAll: "All",
      layersNone: "None",
      layersStory: "With dialog",
      layerSelectionHint: "Only layers with dialog are shown initially. Use All, None, or the layer chips to choose what appears on the map.",
      loadError: "Map recovery data could not be loaded",
      retry: "Retry",
      questRoute: "Quest route",
      relations: "Relation lines",
      relations_focus: "Focused",
      relations_all: "All",
      relations_off: "Off",
      relationsHint: "Lines join markers that share a level-script file or script entity. Every pair in a group is joined, so a group of n draws n(n-1)/2 lines; Focused shows only the lines of the node under the pointer.",
      gridFit: "Background grid fit",
      gridFitOf: "of",
      gridFitMarkers: "marker transforms",
      inspector: "Inspector",
      inspectorHint: "Hover or Tab to a node to read it here; click to pin it and open its first file.",
      questId: "Quest id",
      questOrder: "Order",
      objective: "Objective",
      coordinates: "Coordinates",
      name: "Label",
      kind: "Kind",
      identity: "Identity",
      detailId: "detailId",
      interaction: "Interaction",
      evidenceField: "Evidence",
      storyKey: "Story key",
      eventName: "Event",
      action: "Action",
      scenes: "Scenes",
      relatedFiles: "Related files",
      weakerLinks: "Weaker links",
      noFiles: "No file is pinned to this node.",
      openRaw: "raw",
      loadingFile: "Loading file...",
      fileError: "Failed to load file",
      emptyDialog: "This scene publishes no dialog lines (camera or timeline only).",
      moreLines: "more lines in the source file",
      sceneNotes: "Scene metadata",
      binaryNote: "Binary level-script payload; the readable identifiers it contains are listed below.",
      hexHead: "First bytes (hex)",
      mapFiles: "Map-wide files",
      story: "story",
      openInStory: "Open in Story",
      unplacedStories: "Mission stories not on the map",
      reason_mission_scope_only: "Scoped to the whole mission",
      reason_cross_level_binding: "Driven from another level",
      reason_graph_evidence_only: "Ordering evidence only",
      reason_no_placement_evidence: "No spatial evidence",
      unplacedTriggers: "Stories on unplaced triggers",
      unlinkedFiles: "Unpinned mission files",
      noFilesLinked: "Every referenced mission file is pinned to a node.",
      boundsOutline: "Declared world bounds outline",
      minimapFrom: "in-game map texture",
      minimapTiles: "tiles",
      minimapLayer: "layer",
      scene3d: "Recovered 3D models",
      scene3dHint: "Open a representative OBJ in the existing Assets 3D viewer. Mesh placement is inferred and diagnostic only.",
      scene3dUnplacedHint: "These level-matched OBJ exports have no recovered scene transform. Open them in Assets for inspection; they are not placed on this map.",
      scene3dUnavailable: "No safe OBJ model is published for this level; the map stays marker-only.",
    },
    zh: {
      mapLayers: "地图楼层",
      mapLayersNone: "该关卡的 UILevelMapLoadConfig 未声明楼层叠图。",
      layerSelectionHint: "\u9ed8\u8ba4\u4ec5\u663e\u793a\u542b\u5bf9\u8bdd\u7684\u56fe\u5c42\u3002\u8bf7\u4f7f\u7528\u6309\u94ae\u6216\u56fe\u5c42\u6807\u7b7e\u9009\u62e9\u8981\u663e\u793a\u7684\u5185\u5bb9\u3002",
      loadError: "\u65e0\u6cd5\u52a0\u8f7d\u5730\u56fe\u6062\u590d\u6570\u636e",
      retry: "\u91cd\u8bd5",
      title: "地图恢复",
      layers: "图层",
      evidence: "证据",
      controls: "控制面板",
      collapse: "收起面板",
      regionSurface: "张区域地图屏按世界坐标拼成无缝整面",
      selectedSurface: "\u5df2\u52a0\u8f7d\u5f53\u524d\u533a\u57df\u5730\u56fe\u5c4f\uff1b\u9009\u62e9\u5176\u4ed6\u533a\u57df\u540e\u52a0\u8f7d\u62fc\u63a5\u5730\u56fe",
      loading: "正在加载地图恢复数据...",
      mapSurface: "世界地图，可平移缩放",
      zoomIn: "放大",
      zoomOut: "缩小",
      fit: "适配",
      fitLong: "适配全部节点",
      reset: "复位",
      resetLong: "复位到完整声明世界边界",
      zoomLevel: "缩放",
      help: "滚轮或 +/- 缩放，拖拽或方向键平移，Tab 遍历节点，Enter 固定，Esc 取消，0 复位，F 适配。",
      questPoint: "任务点",
      entityNode: "实体节点",
      noNodes: "当前图层没有可绘制节点。",
      questPoints: "任务点",
      entityMarkers: "实体标记",
      pinnedFiles: "关联文件",
      exactNpcs: "精确 NPC",
      storyNodes: "含剧情节点",
      shownNodes: "当前筛选显示",
      countMarkers: " 节点",
      countStories: " 剧情",
      registryBacked: "由本关卡的 WorldEntityRegistry 行确定坐标。",
      mission: "任务",
      missionAll: "全部任务",
      missionNone: "本关卡没有任务内容。",
      layersAll: "全选",
      layersNone: "全不选",
      layersStory: "含剧情",
      questRoute: "任务路线",
      relations: "关系连线",
      relations_focus: "仅当前",
      relations_all: "全部",
      relations_off: "关闭",
      relationsHint: "连线表示两个标记共用同一份关卡脚本文件或脚本实体。同组内每两点都会连线，n 个点即 n(n-1)/2 条；“仅当前”只显示指针所指节点的连线。",
      gridFit: "底图网格拟合",
      gridFitOf: "／共",
      gridFitMarkers: "个实体坐标",
      inspector: "详情",
      inspectorHint: "悬停或用 Tab 选中节点即可在此查看；点击可固定并打开首个文件。",
      questId: "任务 ID",
      questOrder: "顺序",
      objective: "目标",
      coordinates: "坐标",
      name: "名称",
      kind: "类型",
      identity: "标识",
      detailId: "detailId",
      interaction: "交互状态",
      evidenceField: "证据",
      storyKey: "剧情键",
      eventName: "事件",
      action: "动作",
      scenes: "关联场景",
      relatedFiles: "关联文件",
      weakerLinks: "弱关联",
      noFiles: "该节点没有关联文件。",
      openRaw: "原文件",
      loadingFile: "正在加载文件…",
      fileError: "文件读取失败",
      emptyDialog: "该场景没有对白文本（仅镜头或时间轴）。",
      moreLines: "行未显示，请打开原文件",
      sceneNotes: "场景元数据",
      binaryNote: "二进制关卡脚本负载；下方列出其中可读的标识符。",
      hexHead: "起始字节（十六进制）",
      mapFiles: "地图级文件",
      story: "剧情",
      openInStory: "在剧情页打开",
      unplacedStories: "未出现在地图上的任务剧情",
      reason_mission_scope_only: "仅限定到整个任务范围",
      reason_cross_level_binding: "由其他关卡驱动",
      reason_graph_evidence_only: "仅有顺序证据",
      reason_no_placement_evidence: "没有空间证据",
      unplacedTriggers: "触发体未定位的剧情",
      unlinkedFiles: "未固定的任务文件",
      noFilesLinked: "所有被引用的任务文件都已固定到节点。",
      boundsOutline: "声明世界边界轮廓",
      minimapFrom: "游戏内地图贴图",
      minimapTiles: "块",
      minimapLayer: "图层",
      scene3d: "Recovered 3D models",
      scene3dHint: "Open a representative OBJ in the existing Assets 3D viewer. Mesh placement is inferred and diagnostic only.",
      scene3dUnavailable: "No safe OBJ model is published for this level; the map stays marker-only.",
    },
  };
  const isZh = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").toLowerCase().startsWith("zh");
  const t = (key) => (isZh() ? TEXT.zh[key] : TEXT.en[key]) ?? TEXT.en[key] ?? key;

  async function fetchJson(path, { cache = "no-store", signal, onProgress } = {}) {
    const response = window.WebUI?.fetchWithProgress
      ? await window.WebUI.fetchWithProgress(path, { cache, signal, onProgress })
      : await fetch(path, { cache, signal });
    if (!response.ok) throw new Error(`${response.status} ${path}`);
    return response.json();
  }

  function finitePosition(value) {
    if (!value || !Number.isFinite(Number(value.x)) || !Number.isFinite(Number(value.z))) return null;
    return { x: Number(value.x), y: Number.isFinite(Number(value.y)) ? Number(value.y) : null, z: Number(value.z) };
  }

  // ---------------------------------------------------------------- payload

  // Inspector and accessible name share this single field list, so a screen
  // reader never gets less than the visible panel. Empty payload fields are
  // dropped rather than rendered as placeholders.
  function fields(node) {
    const p = node.position;
    const coords = `X ${p.x} / Y ${p.y ?? "?"} / Z ${p.z}`;
    const rows = node.type === "quest"
      ? [
        [t("questId"), node.questId],
        [t("questOrder"), Number.isFinite(Number(node.questOrder)) ? String(node.questOrder) : ""],
        [t("objective"), plainText(node.objective)],
        [t("coordinates"), coords],
      ]
      : [
        [t("name"), node.label],
        [t("kind"), node.kind],
        [t("identity"), node.identity],
        [t("detailId"), node.detailId],
        [t("interaction"), node.interactionStatus],
        [t("storyKey"), node.storyKey],
        [t("eventName"), node.eventName],
        [t("action"), node.action],
        [t("evidenceField"), node.evidence],
        [t("coordinates"), coords],
      ];
    rows.push([t("scenes"), (node.sceneKeys || []).join(", ")]);
    return rows.filter(([, value]) => value !== null && value !== undefined && String(value) !== "");
  }

  const nodeTitle = (node) => (node.type === "quest" ? String(node.questId) : nodeDisplayLabel(node));
  const nodeRole = (node) => (node.type === "quest" ? t("questPoint") : t("entityNode"));
  const accessibleName = (node) => `${nodeRole(node)}: ${fields(node).map(([label, value]) => `${label} ${value}`).join(", ")}`;

  function priority(node) {
    if (node.id === inspectorTargetId()) return 5;
    // A pinned node outranks story/quest so hovering elsewhere never culls the
    // label of the node whose details the reader deliberately kept open.
    if (node.id === state.selectedId) return 4;
    if (node.kind === "story") return 3;
    if (node.type === "quest") return 2;
    return 1;
  }

  // ---------------------------------------------------------------- file load

  // LevelScriptData files carry a `.json` name but hold a binary payload whose
  // readable content is its embedded identifier strings (sequence names, event
  // names, entity keys). A hex dump hides exactly that, so the viewer lists the
  // printable runs and keeps the hex as a secondary, collapsed view.
  function asciiTokens(buffer) {
    const tokens = [];
    const seen = new Set();
    let current = "";
    const flush = () => {
      if (current.length >= 4 && !seen.has(current)) {
        seen.add(current);
        tokens.push(current);
      }
      current = "";
    };
    for (const byte of buffer) {
      if (byte >= 0x20 && byte <= 0x7e) current += String.fromCharCode(byte);
      else flush();
      if (tokens.length >= MAX_TOKENS) break;
    }
    flush();
    return tokens;
  }

  async function getFile(href) {
    const url = String(href || "");
    if (!url) return { kind: "error", error: t("fileError") };
    if (state.fileCache.has(url)) return state.fileCache.get(url);
    if (state.fileFlight.has(url)) return state.fileFlight.get(url);

    const worker = (async () => {
      try {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) return { kind: "error", error: `${response.status} ${response.statusText}` };
        const buffer = new Uint8Array(await response.arrayBuffer());
        const text = new TextDecoder("utf-8", { fatal: false }).decode(buffer);
        const hasNull = text.includes("\u0000");
        const controls = [...buffer].filter((byte) => byte < 9 || byte === 11 || byte === 12 || (byte > 13 && byte < 32)).length;
        if (hasNull || (buffer.length && controls / buffer.length > 0.04)) {
          const hex = [...buffer.slice(0, 256)].map((byte) => byte.toString(16).padStart(2, "0")).join(" ");
          return { kind: "binary", byteLength: buffer.length, data: hex, tokens: asciiTokens(buffer) };
        }
        // A conv payload is rendered as dialog rather than as JSON, so it is
        // parsed here once and cached in its parsed form.
        if (text.length <= MAX_PREVIEW_BYTES) {
          try {
            const parsed = JSON.parse(text);
            if (parsed && Array.isArray(parsed.lines) && parsed.key) {
              return { kind: "conv", byteLength: buffer.length, conv: parsed };
            }
          } catch { /* not JSON, fall through to the text preview */ }
        }
        return {
          kind: "text",
          byteLength: buffer.length,
          text: text.slice(0, MAX_RAW_CHARS),
          truncated: text.length > MAX_RAW_CHARS,
        };
      } catch (error) {
        return { kind: "error", error: String(error || t("fileError")) };
      } finally {
        state.fileFlight.delete(url);
      }
    })();

    state.fileFlight.set(url, worker);
    const result = await worker;
    state.fileCache.set(url, result);
    return result;
  }

  // ---------------------------------------------------------------- geometry

  function metrics() {
    const svg = svgEl();
    const map = mapEl();
    if (!svg || !map) return null;
    const svgRect = svg.getBoundingClientRect();
    const mapRect = map.getBoundingClientRect();
    if (!svgRect.width || !svgRect.height) return null;
    // All container pixels are measured from the padding-box origin, because
    // the tooltip is placed with absolute left/top against the padding box.
    const originX = mapRect.left + map.clientLeft;
    const originY = mapRect.top + map.clientTop;
    // The viewBox is letterboxed by preserveAspectRatio="xMidYMid meet", so k
    // and the offsets convert viewBox units to container pixels exactly.
    const k = Math.min(svgRect.width / WIDTH, svgRect.height / HEIGHT) || 1;
    return {
      k,
      ox: (svgRect.left - originX) + (svgRect.width - WIDTH * k) / 2,
      oy: (svgRect.top - originY) + (svgRect.height - HEIGHT * k) / 2,
      width: map.clientWidth,
      height: map.clientHeight,
      originX,
      originY,
    };
  }

  const toPixel = (m, point) => ({
    x: m.ox + m.k * (state.transform.x + state.transform.scale * point.x),
    y: m.oy + m.k * (state.transform.y + state.transform.scale * point.y),
  });

  function clamped(transform) {
    const scale = clamp(transform.scale, MIN_SCALE, MAX_SCALE);
    // A region surface extends past the canvas, so the pan limit is the plotted
    // content plus a fixed screen overhang, not the canvas edges: the whole
    // region stays reachable at any zoom without an arbitrary dead stop.
    const box = state.contentBox || { minX: 0, minY: 0, maxX: WIDTH, maxY: HEIGHT };
    const xMin = WIDTH - box.maxX * scale - PAN_OVERHANG;
    const xMax = PAN_OVERHANG - box.minX * scale;
    const yMin = HEIGHT - box.maxY * scale - PAN_OVERHANG;
    const yMax = PAN_OVERHANG - box.minY * scale;
    return {
      scale,
      x: clamp(transform.x, Math.min(xMin, xMax), Math.max(xMin, xMax)),
      y: clamp(transform.y, Math.min(yMin, yMax), Math.max(yMin, yMax)),
    };
  }

  function zoomed(factor, originPx) {
    const m = metrics();
    const current = state.transform;
    if (!m) return clamped({ ...current, scale: current.scale * factor });
    const point = originPx || { x: m.width / 2, y: m.height / 2 };
    const viewX = (point.x - m.ox) / m.k;
    const viewY = (point.y - m.oy) / m.k;
    const scale = clamp(current.scale * factor, MIN_SCALE, MAX_SCALE);
    const worldX = (viewX - current.x) / current.scale;
    const worldY = (viewY - current.y) / current.scale;
    return clamped({ scale, x: viewX - worldX * scale, y: viewY - worldY * scale });
  }

  function fitTransform() {
    if (!state.nodes.length) return { x: 0, y: 0, scale: 1 };
    const xs = state.nodes.map((node) => node.plot.x);
    const ys = state.nodes.map((node) => node.plot.y);
    // plot() normalises against the extremes, so on a sparse map the outermost
    // nodes land exactly on the plot box edge and their markers and labels get
    // clipped. The margin scales with the occupied span, with a floor that
    // clears a marker plus its label on any map.
    const spanX = Math.max(...xs) - Math.min(...xs);
    const spanY = Math.max(...ys) - Math.min(...ys);
    const pad = Math.max(48, spanX * 0.08, spanY * 0.08);
    const minX = Math.min(...xs) - pad;
    const maxX = Math.max(...xs) + pad;
    const minY = Math.min(...ys) - pad;
    const maxY = Math.max(...ys) + pad;
    const scale = clamp(Math.min(WIDTH / Math.max(1, maxX - minX), HEIGHT / Math.max(1, maxY - minY)), MIN_SCALE, MAX_SCALE);
    return clamped({ scale, x: WIDTH / 2 - scale * (minX + maxX) / 2, y: HEIGHT / 2 - scale * (minY + maxY) / 2 });
  }

  function stopAnimation() {
    if (state.animation) cancelAnimationFrame(state.animation);
    state.animation = 0;
  }

  function animateTo(target, requested = 190) {
    stopAnimation();
    const duration = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? 0 : requested;
    const from = { ...state.transform };
    const start = performance.now();
    const step = (now) => {
      const progress = duration <= 0 ? 1 : Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      state.transform = {
        x: from.x + (target.x - from.x) * eased,
        y: from.y + (target.y - from.y) * eased,
        scale: from.scale + (target.scale - from.scale) * eased,
      };
      applyTransform();
      state.animation = progress < 1 ? requestAnimationFrame(step) : 0;
    };
    state.animation = requestAnimationFrame(step);
  }

  // ---------------------------------------------------------------- view sync

  function applyTransform() {
    const host = root();
    const m = metrics();
    if (!host || !m) return;
    // The declared world bounds are much larger than the area the mission
    // actually occupies, so an identity transform wastes most of the surface.
    // The first measurable paint frames the plotted nodes instead. The flag is
    // cleared before re-entering so this can only ever run once per load.
    if (state.pendingFit && state.nodes.length) {
      state.pendingFit = false;
      state.transform = fitTransform();
      applyTransform();
      return;
    }
    const { x, y, scale } = state.transform;
    host.querySelector(".mr-viewport")?.setAttribute("transform", `translate(${x.toFixed(3)} ${y.toFixed(3)}) scale(${scale.toFixed(5)})`);
    // Counter-scaling every node by 1/(k*scale) makes its local units render as
    // container pixels, so glyphs and markers keep one constant on-screen size
    // at any zoom or container width. Panning keeps the scale, so the per-node
    // attribute only changes on zoom or resize - a region holds up to 11k nodes
    // and panning must not rewrite all of them on every pointer move.
    const nodeScale = clamp(1 / (m.k * scale), 0.05, 8);
    const nodeScaleChanged = nodeScale !== state.lastNodeScale;
    if (nodeScaleChanged) state.lastNodeScale = nodeScale;
    state.nodes.forEach((node) => {
      node.px = toPixel(m, node.plot);
      if (nodeScaleChanged && node.el) {
        node.el.setAttribute("transform", `translate(${node.plot.x.toFixed(3)} ${node.plot.y.toFixed(3)}) scale(${nodeScale.toFixed(5)})`);
      }
    });
    layoutLabels(m);
    const readout = host.querySelector(".mr-zoom-readout");
    if (readout) readout.textContent = `${t("zoomLevel")} ${Math.round(scale * 100)}%`;
    syncTip(m);
  }

  function layoutLabels(m) {
    const boxes = [];
    const targetId = inspectorTargetId();
    const ranked = state.nodes.slice().sort((a, b) => priority(b) - priority(a));
    ranked.forEach((node) => {
      if (!node.labelEl) return;
      const onScreen = node.px.x > -80 && node.px.x < m.width + 80 && node.px.y > -60 && node.px.y < m.height + 60;
      let visible = onScreen && (priority(node) >= 2 || state.transform.scale >= LABEL_ZOOM);
      // Labels sit to the right of their marker by default. Near the right edge
      // that clips them, so they flip to the other side instead. Node contents
      // are counter-scaled to container pixels, so the offset is in px.
      const flip = node.px.x + node.labelOffset.x + node.labelPx > m.width - 6;
      node.labelEl.setAttribute("x", String(flip ? -node.labelOffset.x : node.labelOffset.x));
      node.labelEl.setAttribute("text-anchor", flip ? "end" : "start");
      if (visible) {
        const left = flip ? node.px.x - node.labelOffset.x - node.labelPx : node.px.x + node.labelOffset.x;
        const box = {
          x: left,
          y: node.px.y + node.labelOffset.y - LABEL_LINE + 3,
          w: node.labelPx,
          h: LABEL_LINE,
        };
        // Highest-priority labels claim their box first, so the selected,
        // hovered and story labels are never the ones culled.
        if (boxes.some((other) => box.x < other.x + other.w + 2 && other.x < box.x + box.w + 2 && box.y < other.y + other.h + 2 && other.y < box.y + box.h + 2)) visible = false;
        else boxes.push(box);
      }
      node.labelEl.classList.toggle("is-hidden", !visible);
      node.el?.classList.toggle("is-target", node.id === targetId);
    });
  }

  const inspectorTargetId = () => state.previewId || state.selectedId;
  const targetNode = () => state.nodes.find((row) => row.id === inspectorTargetId()) || null;

  // The tooltip follows the hovered node only. The pinned node keeps the
  // inspector, so a tooltip for it would just repeat the panel over the map.
  function syncTip(known) {
    const host = root();
    const tip = host?.querySelector(".mr-tip");
    if (!tip) return;
    const node = state.nodes.find((row) => row.id === state.previewId);
    const m = known || metrics();
    if (!node || !m) {
      tip.hidden = true;
      return;
    }
    if (tip.dataset.node !== node.id) {
      tip.dataset.node = node.id;
      const files = relatedFiles(node).length;
      tip.innerHTML = `<strong>${esc(nodeTitle(node))}</strong>`
        + `<span>${esc(node.type === "quest" ? t("questPoint") : node.kind || t("entityNode"))} · X ${esc(node.position.x)} / Z ${esc(node.position.z)}</span>`
        + (files ? `<span>${esc(`${files} ${t("relatedFiles")}`)}</span>` : "");
    }
    tip.hidden = false;
    const width = tip.offsetWidth || 200;
    const height = tip.offsetHeight || 60;
    const right = node.px.x + 16 + width <= m.width - 6;
    tip.style.left = `${clamp(right ? node.px.x + 16 : node.px.x - 16 - width, 6, Math.max(6, m.width - width - 6))}px`;
    tip.style.top = `${clamp(node.px.y - height - 12, 6, Math.max(6, m.height - height - 6))}px`;
  }

  // ---------------------------------------------------------------- inspector

  function fileRow(pin, active) {
    return `<div class="mr-file${pin.strength === "weak" ? " is-weak" : ""}${active ? " is-active" : ""}">
      <button type="button" class="mr-file-pick" data-map-file="${esc(pin.href)}" data-map-file-path="${esc(pin.path)}" aria-pressed="${active ? "true" : "false"}">
        <b>${esc(fileName(pin.path))}</b><small>${esc(pin.note || pin.relation)}</small>
      </button>
      <span class="mr-file-actions">${storyLink(pin.path)}<a class="mr-file-open" href="${esc(pin.href)}" target="_blank" rel="noreferrer">${esc(t("openRaw"))}</a></span>
    </div>`;
  }

  function fileListHtml(pins) {
    if (!pins.length) return `<p class="mr-placeholder">${esc(t("noFiles"))}</p>`;
    const strong = pins.filter((pin) => pin.strength !== "weak");
    const weak = pins.filter((pin) => pin.strength === "weak");
    const render = (rows) => rows.map((pin) => fileRow(pin, pin.href === state.filePath)).join("");
    const activeWeak = weak.some((pin) => pin.href === state.filePath);
    return `${strong.length ? `<div class="mr-files">${render(strong)}</div>` : ""}`
      + (weak.length
        ? `<details class="mr-weak-files"${activeWeak ? " open" : ""}><summary>${esc(`${t("weakerLinks")} (${weak.length})`)}</summary><div class="mr-files">${render(weak)}</div></details>`
        : "");
  }

  function renderInspector() {
    const host = root();
    const head = host?.querySelector(".mr-inspector-head");
    const body = host?.querySelector(".mr-inspector-body");
    if (!head || !body) return;
    const node = targetNode();
    const key = `${node?.id || ""}|${isZh() ? "zh" : "en"}`;
    if (key === state.inspectorKey) {
      syncFileSelection();
      return;
    }
    state.inspectorKey = key;

    if (!node) {
      head.innerHTML = `<p class="mr-role">${esc(t("inspector"))}</p><h2>${esc(t("title"))}</h2>`;
      body.innerHTML = `<p class="mr-placeholder">${esc(t("inspectorHint"))}</p>${mapFilesHtml()}<div class="mr-viewer-slot"></div>`;
      bindFilePicks(body);
      renderViewer();
      return;
    }

    head.innerHTML = `<p class="mr-role" style="color:${esc(kindColor(node))}">${esc(nodeRole(node))}${node.kind ? ` / ${esc(node.kind)}` : ""}</p>
      <h2>${esc(nodeTitle(node))}</h2>`;
    body.innerHTML = `<dl class="mr-fields">${fields(node).map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`).join("")}</dl>
      <h3 class="mr-section-title">${esc(`${t("relatedFiles")} (${relatedFiles(node).length})`)}</h3>
      ${fileListHtml(relatedFiles(node))}
      <div class="mr-viewer-slot"></div>`;
    bindFilePicks(body);
    renderViewer();
  }

  function mapFilesHtml() {
    const pins = (state.map?.relatedFiles || []).filter((row) => row && row.path);
    if (!pins.length) return "";
    return `<h3 class="mr-section-title">${esc(`${t("mapFiles")} (${pins.length})`)}</h3>${fileListHtml(pins)}`;
  }

  function bindFilePicks(scope) {
    scope.querySelectorAll("[data-map-file]").forEach((button) => {
      button.addEventListener("click", () => openFile(button.dataset.mapFile, button.dataset.mapFilePath));
    });
  }

  function syncFileSelection() {
    root()?.querySelectorAll("[data-map-file]").forEach((button) => {
      const active = button.dataset.mapFile === state.filePath;
      button.setAttribute("aria-pressed", active ? "true" : "false");
      button.closest(".mr-file")?.classList.toggle("is-active", active);
    });
  }

  function openFile(href, path) {
    state.filePath = href === state.filePath ? "" : href;
    state.filePathLabel = path || "";
    syncFileSelection();
    renderViewer();
  }

  function renderViewer() {
    const host = root();
    const slot = host?.querySelector(".mr-viewer-slot");
    if (!slot) return;
    if (!state.filePath) {
      slot.innerHTML = "";
      return;
    }
    const href = state.filePath;
    const label = state.filePathLabel || href;
    slot.innerHTML = `<section class="mr-viewer"><div class="mr-viewer-head"><b>${esc(fileName(label))}</b>${storyLink(label, t("openInStory"))}<span></span></div>
      <div class="mr-viewer-body"><p class="mr-viewer-state">${esc(t("loadingFile"))}</p></div></section>`;
    // The pinned-file list can be long enough to push the viewer below the
    // fold, so opening a file brings its content into view.
    slot.scrollIntoView({ block: "nearest" });
    getFile(href).then((result) => {
      // The reader can pick another file (or another node) while a fetch is in
      // flight; only the still-current selection is allowed to paint.
      if (state.filePath !== href) return;
      const current = host.querySelector(".mr-viewer-slot .mr-viewer");
      if (!current) return;
      const meta = current.querySelector(".mr-viewer-head span");
      const target = current.querySelector(".mr-viewer-body");
      if (result.kind === "error") {
        target.innerHTML = `<p class="mr-viewer-state is-error">${esc(t("fileError"))}: ${esc(result.error || "")}</p>`;
        return;
      }
      if (meta) meta.textContent = `${result.byteLength ?? 0} B`;
      if (result.kind === "binary") {
        const tokens = result.tokens || [];
        target.innerHTML = `<p class="mr-viewer-state">${esc(t("binaryNote"))}</p>`
          + (tokens.length ? `<ul class="mr-tokens">${tokens.map((token) => `<li>${esc(token)}</li>`).join("")}</ul>` : "")
          + `<details class="mr-hex"><summary>${esc(t("hexHead"))}</summary><pre class="mr-raw is-hex">${esc(result.data || "")}</pre></details>`;
        return;
      }
      if (result.kind === "conv") {
        target.innerHTML = convHtml(result.conv);
        return;
      }
      target.innerHTML = `<pre class="mr-raw">${esc(result.text || "")}</pre>`
        + (result.truncated ? `<p class="mr-viewer-state">${esc(`+ ${t("moreLines")}`)}</p>` : "");
    });
  }

  function convHtml(conv) {
    const lines = Array.isArray(conv.lines) ? conv.lines : [];
    const shown = lines.slice(0, MAX_DIALOG_LINES);
    // `summary` is a list of {text} rows carrying authoring metadata (prefab
    // path, tags, components), not story text, so it is kept collapsed under
    // the scene title rather than presented as the scene's opening line.
    const notes = (Array.isArray(conv.summary) ? conv.summary : [])
      .map((row) => plainText(row && row.text))
      .filter(Boolean);
    const title = plainText(conv.title);
    const head = (title ? `<p class="mr-dialog-summary">${esc(title)}</p>` : "")
      + (notes.length
        ? `<details class="mr-dialog-notes"><summary>${esc(`${t("sceneNotes")} (${notes.length})`)}</summary>${notes.map((note) => `<p>${esc(note)}</p>`).join("")}</details>`
        : "");
    if (!shown.length) return `<div class="mr-dialog">${head}<p class="mr-viewer-state">${esc(t("emptyDialog"))}</p></div>`;
    const rows = shown.map((line) => {
      const text = plainText(line.text);
      const hint = plainText(line.hint);
      if (!text && !hint) return "";
      return `<div class="mr-dialog-line"><b>${esc(plainText(line.actor) || "-")}</b>`
        + `<p>${esc(text)}${hint ? `<i>${esc(hint)}</i>` : ""}</p></div>`;
    }).join("");
    const more = lines.length > shown.length ? `<p class="mr-dialog-more">+${lines.length - shown.length} ${esc(t("moreLines"))}</p>` : "";
    if (!rows) return `<div class="mr-dialog">${head}<p class="mr-viewer-state">${esc(t("emptyDialog"))}</p></div>`;
    return `<div class="mr-dialog">${head}${rows}${more}</div>`;
  }

  // ---------------------------------------------------------------- relations

  // Rewriting one stylesheet rule is O(1) no matter how many lines are drawn,
  // so relation focus can follow the pointer without touching thousands of
  // SVG nodes on every hover.
  const cssString = (value) => String(value).replace(/["\\]/g, "\\$&");

  function applyEdgeFocus() {
    const host = root();
    if (!host) return;
    const style = host.querySelector("#map-recovery-edge-style");
    if (!style) return;
    if (state.relations === "all") {
      style.textContent = "";
      return;
    }
    if (state.relations === "off") {
      style.textContent = ".mr-edge { display: none; }";
      return;
    }
    const focused = state.selectedId || state.previewId;
    if (!focused) {
      style.textContent = ".mr-edge { display: none; }";
      return;
    }
    const id = cssString(focused);
    style.textContent = `.mr-edge { display: none; }\n`
      + `.mr-edge[data-from="${id}"], .mr-edge[data-to="${id}"] { display: inline; }`;
  }

  // ---------------------------------------------------------------- selection

  function setPreview(id) {
    if (state.previewId === id) return;
    state.previewId = id;
    layoutLabelsSafely();
    syncTip();
    applyEdgeFocus();
    renderInspector();
  }

  function selectNode(id) {
    const next = state.selectedId === id ? "" : id;
    state.selectedId = next;
    if (!next) {
      state.filePath = "";
      state.filePathLabel = "";
    }
    syncSelection();
    layoutLabelsSafely();
    applyEdgeFocus();
    renderInspector();
    // Pinning a node opens its strongest file straight away, so the common case
    // (click a marker, read the dialog it triggers) takes one interaction.
    if (!next) return;
    // A story file is what the reader is usually after, so it wins the auto-open
    // even when a stronger placement file is listed above it.
    const pins = relatedFiles(state.nodes.find((row) => row.id === next));
    const first = pins.find((pin) => pin.relation.startsWith("story"))
      || pins.find((pin) => pin.strength !== "weak")
      || pins[0];
    if (first && first.href !== state.filePath) openFile(first.href, first.path);
  }

  // Selection lives in state, so the pressed state and the pinned styling have
  // to be pushed onto the existing elements; render() only seeds them once.
  function syncSelection() {
    state.nodes.forEach((node) => {
      const selected = node.id === state.selectedId;
      node.el?.classList.toggle("is-selected", selected);
      node.el?.setAttribute("aria-pressed", selected ? "true" : "false");
    });
  }

  function clearSelection() {
    state.selectedId = "";
    state.previewId = "";
    state.filePath = "";
    syncSelection();
    layoutLabelsSafely();
    syncTip();
    renderInspector();
  }

  function layoutLabelsSafely() {
    const m = metrics();
    if (m) layoutLabels(m);
  }

  // ---------------------------------------------------------------- rendering

  function render() {
    const host = root();
    const data = state.map;
    if (!host || !data) return;

    // A level pools every mission that plays in it, so isolating one mission is
    // the difference between a readable route and a wall of markers. A node with
    // no mission of its own is level art: it is only shown when no mission is
    // selected, because claiming it for the selected mission would be a lie.
    const inMission = (row) => !state.mission || (row.missions || []).includes(state.mission);
    const inMapLayer = (row) => {
      const ids = row.mapLayerIds || [];
      return ids.length ? ids.some((id) => state.mapLayers.has(id)) : true;
    };
    const questRows = (data.questPoints || [])
      .filter((row) => inMission(row) && inMapLayer(row))
      .map((row) => ({ ...row, type: "quest", position: finitePosition(row.position) }))
      .filter((row) => row.position);
    const markerRows = (data.markers || [])
      .filter((row) => state.kinds.has(row.kind) && state.subKinds.has(row.subKind || row.kind) && inMission(row))
      .filter(inMapLayer)
      .filter((row) => !state.storyOnly || Number(row.storyCount || 0) > 0)
      .map((row) => ({ ...row, type: "marker", position: finitePosition(row.position) }))
      .filter((row) => row.position);

    // The background is the game's own map-screen composite when the level
    // publishes one, else the HLOD preview. Whichever source is chosen also
    // supplies the declared world bounds, so the markers and the picture are
    // always projected by the same rectangle.
    const minimapBg = data.minimap || {};
    const hlodBg = data.renderBackground || {};
    const backgroundSource = minimapBg.src && minimapBg.worldBounds
      ? minimapBg
      : (hlodBg.src && hlodBg.worldBounds ? hlodBg : null);
    // Region payloads publish one shared world rectangle for all stitched
    // sibling screens. Prefer it over the selected screen's local minimap
    // bounds so markers keep one projection when the region is loaded on
    // demand or when a sibling has a wider rendered surface.
    // A single on-demand zone should still fit its own screen. The region
    // union becomes authoritative only after sibling screens are actually
    // loaded; otherwise the first screen would be rendered as a tiny island
    // inside the bounds of content the user has not chosen to display.
    const declaredBounds = state.backgrounds.length > 1
      ? (data.region?.worldBounds || data.regionBounds || backgroundSource?.worldBounds)
      : backgroundSource?.worldBounds;
    const hasDeclaredBounds = ["minX", "maxX", "minZ", "maxZ"].every((key) => Number.isFinite(Number(declaredBounds?.[key])));
    const positions = [...questRows, ...markerRows].map((row) => row.position);
    const minX = hasDeclaredBounds ? Number(declaredBounds.minX) : (positions.length ? Math.min(...positions.map((p) => p.x)) : 0);
    const maxX = hasDeclaredBounds ? Number(declaredBounds.maxX) : (positions.length ? Math.max(...positions.map((p) => p.x)) : 1);
    const minZ = hasDeclaredBounds ? Number(declaredBounds.minZ) : (positions.length ? Math.min(...positions.map((p) => p.z)) : 0);
    const maxZ = hasDeclaredBounds ? Number(declaredBounds.maxZ) : (positions.length ? Math.max(...positions.map((p) => p.z)) : 1);
    const rangeX = maxX - minX || 1;
    const rangeZ = maxZ - minZ || 1;
    // The picture and the world share one square scale: the declared rectangle
    // is fitted into the canvas at its true aspect (letterboxed) instead of
    // being stretched onto the landscape canvas, so a portrait zone is not
    // squashed and a wide one is not pulled. Markers, routes, the bounds
    // outline and the background all use the same fitted rectangle, so they
    // stay aligned with the terrain at any zoom.
    const fitScale = Math.min((WIDTH - 2 * PAD) / rangeX, (HEIGHT - 2 * PAD) / rangeZ);
    const viewW = rangeX * fitScale;
    const viewH = rangeZ * fitScale;
    const viewX = (WIDTH - viewW) / 2;
    const viewY = (HEIGHT - viewH) / 2;
    const plot = (p) => ({ x: viewX + (p.x - minX) * fitScale, y: viewY + viewH - (p.z - minZ) * fitScale });

    state.nodes = [
      // A map now carries the quests of every mission that plays in the level,
      // and a region surface merges several levels, so both the mission and the
      // level are part of the node id: quest ids are only unique inside their
      // own mission and marker identities stay scoped to their level.
      ...questRows.map((row) => ({ ...row, id: `q:${row.levelId}:${row.missionId || ""}:${row.questId}`, plot: plot(row.position), px: { x: 0, y: 0 } })),
      ...markerRows.map((row) => ({ ...row, id: `m:${row.levelId}:${row.identity}`, plot: plot(row.position), px: { x: 0, y: 0 } })),
    ].map((node) => {
      const labelText = nodeDisplayLabel(node);
      return {
        ...node,
        labelText,
        labelPx: labelWidth(labelText),
        labelOffset: node.type === "quest" ? { x: 10, y: 18 } : { x: 11, y: -10 },
      };
    });

    const markerIndex = new Map(state.nodes.filter((row) => row.type === "marker").map((row) => [row.id, row]));
    state.edges = inferredEdges(markerIndex);
    if (!state.nodes.some((node) => node.id === state.selectedId)) state.selectedId = "";
    if (!state.nodes.some((node) => node.id === state.previewId)) state.previewId = "";

    // One route per mission, in the mission's own quest order. A single
    // polyline over every quest point drew a false leg from the last quest of
    // one mission to the first of the next, and `questId` sorts lexicographic
    // so `q#10` landed between `q#1` and `q#2`; `questOrder` is the authored
    // sequence and every published quest point carries one.
    const routeGroups = new Map();
    for (const row of questRows) {
      const key = row.missionId || "";
      if (!routeGroups.has(key)) routeGroups.set(key, []);
      routeGroups.get(key).push(row);
    }
    const routeSvg = [...routeGroups.entries()].map(([mission, rows]) => {
      if (rows.length < 2) return "";
      const ordered = [...rows].sort((a, b) => {
        const left = Number.isFinite(a.questOrder) ? a.questOrder : Number.MAX_SAFE_INTEGER;
        const right = Number.isFinite(b.questOrder) ? b.questOrder : Number.MAX_SAFE_INTEGER;
        return left - right || String(a.questId).localeCompare(String(b.questId));
      });
      const points = ordered.map((row) => plot(row.position)).map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
      return `<polyline class="mr-route" points="${points}" vector-effect="non-scaling-stroke"><title>${esc(`${t("questRoute")}: ${mission}`)}</title></polyline>`;
    }).join("");
    // The selected zone's bounds define the fitted rectangle; every sibling
    // zone of the region projects through the same world -> canvas mapping, so
    // each zone's map screen lands exactly where the terrain it depicts is
    // plotted. Zone screens overlap by design (each one shows its neighbours),
    // which is what makes the surfaces tile into one seamless region: the
    // neighbours are drawn first, the selected zone on top, and no outline is
    // drawn between them.
    const bgRects = [...state.backgrounds, ...state.layerBackgrounds.filter((bg) => state.mapLayers.has(bg.id))]
      .filter((bg) => ["minX", "maxX", "minZ", "maxZ"].every((key) => Number.isFinite(Number(bg.worldBounds?.[key]))))
      .map((bg) => {
        const x = viewX + (Number(bg.worldBounds.minX) - minX) * fitScale;
        const y = viewY + (Number(bg.worldBounds.maxZ) - minZ) * fitScale;
        return {
          bg,
          x,
          y,
          w: (Number(bg.worldBounds.maxX) - Number(bg.worldBounds.minX)) * fitScale,
          h: (Number(bg.worldBounds.maxZ) - Number(bg.worldBounds.minZ)) * fitScale,
        };
      });
    const backgroundImages = bgRects
      .map(({ bg, x, y, w, h }) => `<image class="mr-bg-image" href="data/map_recovery/${esc(bg.src)}" x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${w.toFixed(2)}" height="${h.toFixed(2)}" opacity=".9"><title>${esc(bg.levelId)}</title></image>`)
      .join("");
    // Level display names describe gameplay scenes, not geographic ownership
    // of the whole (overlapping) map-screen rectangle. Location labels come
    // from the map UI's own staticElements text anchors instead.
    const locationLabelSvg = (data.locationLabels || []).map((row) => {
      const position = finitePosition(row.position);
      if (!position || !row.text) return "";
      const p = plot(position);
      return `<text class="mr-location-label" x="${p.x.toFixed(2)}" y="${p.y.toFixed(2)}">${esc(row.text)}</text>`;
    }).join("");
    state.contentBox = state.nodes.length || bgRects.length
      ? (() => {
        let minXc = Infinity;
        let minYc = Infinity;
        let maxXc = -Infinity;
        let maxYc = -Infinity;
        state.nodes.forEach((node) => {
          minXc = Math.min(minXc, node.plot.x);
          minYc = Math.min(minYc, node.plot.y);
          maxXc = Math.max(maxXc, node.plot.x);
          maxYc = Math.max(maxYc, node.plot.y);
        });
        bgRects.forEach(({ x, y, w, h }) => {
          minXc = Math.min(minXc, x);
          minYc = Math.min(minYc, y);
          maxXc = Math.max(maxXc, x + w);
          maxYc = Math.max(maxYc, y + h);
        });
        return { minX: minXc, minY: minYc, maxX: maxXc, maxY: maxYc };
      })()
      : null;
    state.lastNodeScale = null;

    const edgeSvg = state.edges.map((edge) => {
      const from = markerIndex.get(edge.from);
      const to = markerIndex.get(edge.to);
      if (!from || !to) return "";
      const style = EDGE_STYLES[edge.kind] || { stroke: "#a8b0b4", dash: "4 4", width: 1 };
      return `<line class="mr-edge" data-from="${esc(edge.from)}" data-to="${esc(edge.to)}" x1="${from.plot.x.toFixed(2)}" y1="${from.plot.y.toFixed(2)}" x2="${to.plot.x.toFixed(2)}" y2="${to.plot.y.toFixed(2)}" stroke="${style.stroke}" stroke-width="${style.width}" stroke-dasharray="${style.dash}"><title>${esc(edge.label || edge.kind)}</title></line>`;
    }).join("");

    const nodeSvg = state.nodes.map((node) => {
      const quest = node.type === "quest";
      // A node reads as a story node when dialog is actually pinned to it, not
      // when its structural kind happens to be `story`: on a full map most
      // recovered dialog sits on NPC proxies, triggers and narrative anchors.
      const hasStory = quest ? false : (node.storyCount || 0) > 0;
      const shape = quest
        ? `<rect class="mr-shape" x="-5.5" y="-5.5" width="11" height="11"/>`
        : `<circle class="mr-shape" r="${hasStory || node.kind === "story" ? 9 : 6}" fill="${esc(kindColor(node))}"/>`;
      return `<g class="mr-node${quest ? " mr-quest" : " mr-marker"}${hasStory || node.kind === "story" ? " is-story" : ""}" data-node="${esc(node.id)}" data-kind="${esc(node.kind || "quest")}" role="button" tabindex="0" aria-pressed="${node.id === state.selectedId ? "true" : "false"}" aria-label="${esc(accessibleName(node))}">`
        + `<circle class="mr-hit" r="15" fill="none" pointer-events="all"/>${shape}`
        + `<text class="mr-label" x="${node.labelOffset.x}" y="${node.labelOffset.y}">${esc(node.labelText)}</text></g>`;
    }).join("");

    const layerControls = layerTreeHtml(data);
    const mapLayerControls = mapLayerTreeHtml(data);
    const missionControls = missionSelectHtml(data);
    const unlinked = (data.unlinkedMissionFiles || []).filter((path) => String(path || "").trim()).sort((a, b) => a.localeCompare(b));
    const unresolvedSlots = data.unresolvedTriggerSlots || { count: 0 };
    const unplaced = data.unplacedStories || { count: 0 };
    const bg = data.renderBackground || {};
    const regionLevelCount = data.region?.levelIds?.length
      || state.index?.maps?.filter((row) => regionKey(row.id) === regionKey(state.selected)).length
      || state.backgrounds.length;
    const surfaceLabel = state.backgrounds.length < regionLevelCount ? t("selectedSurface") : t("regionSurface");
    // A minimap may be authoritative for the surface while the render
    // background carries only an asset-only OBJ fallback (base01 is the
    // common case). Prefer a spatial HLOD scene when present, then retain the
    // unplaced Assets links instead of hiding them behind the minimap choice.
    const scene = bg.modelScene && typeof bg.modelScene === "object"
      ? bg.modelScene
      : (minimapBg.modelScene && typeof minimapBg.modelScene === "object" ? minimapBg.modelScene : {});
    const sceneMeshes = Array.isArray(scene.meshes) ? scene.meshes.filter((row) => row && row.assetRel) : [];
    const sceneFiles = sceneMeshes.slice(0, 6).map((row) => {
      const rel = String(row.assetRel || "");
      const href = `?asset=${encodeURIComponent(rel)}#assets`;
      return `<li><a href="${esc(href)}">${esc(row.name || rel)}</a></li>`;
    }).join("");
    const sceneHint = scene.positionStatus === "unplaced" ? t("scene3dUnplacedHint") : t("scene3dHint");
    const sceneBlock = sceneMeshes.length
      ? `<details><summary>${esc(`${t("scene3d")} (${scene.meshCount || sceneMeshes.length})`)}</summary><p class="mr-note">${esc(sceneHint)}</p><ul class="mr-file-list">${sceneFiles}</ul></details>`
      : `<p class="mr-note"><code>${esc(scene.status || "obj_cluster_files_unavailable")}</code> ${esc(t("scene3dUnavailable"))}</p>`;

    host.innerHTML = `<style id="map-recovery-edge-style"></style>
      <div class="mr-map" tabindex="0" role="group" aria-label="${esc(`${mapTitle(data)} - ${t("mapSurface")}`)}">
        <svg class="mr-canvas" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="group" aria-label="${esc(mapTitle(data))}"><rect width="100%" height="100%" class="mr-map-bg"/><g class="mr-viewport">${backgroundImages}<g class="mr-location-labels">${locationLabelSvg}</g><g class="mr-routes">${routeSvg}</g><g class="mr-links">${edgeSvg}</g><g class="mr-nodes">${nodeSvg}</g></g></svg>
        <div class="mr-tip" hidden></div>
        <div class="mr-tools" role="group" aria-label="${esc(t("zoomLevel"))}">
          <button type="button" data-map-zoom="out" aria-label="${esc(t("zoomOut"))}" title="${esc(t("zoomOut"))}">-</button>
          <button type="button" data-map-zoom="in" aria-label="${esc(t("zoomIn"))}" title="${esc(t("zoomIn"))}">+</button>
          <button type="button" data-map-fit aria-label="${esc(t("fitLong"))}" title="${esc(t("fitLong"))}">${esc(t("fit"))}</button>
          <button type="button" data-map-reset aria-label="${esc(t("resetLong"))}" title="${esc(t("resetLong"))}">${esc(t("reset"))}</button>
          <span class="mr-zoom-readout" role="status" aria-live="polite"></span>
        </div>
        <p class="mr-help">${esc(t("help"))}</p>
        <div class="mr-axis">+Z -> X -></div>
        ${state.nodes.length ? "" : `<p class="mr-empty">${esc(t("noNodes"))}</p>`}
      </div>
      <section class="mr-float mr-float--header" data-panel="header" aria-label="${esc(t("title"))}">
        <div class="mr-float-head" data-panel-drag>
          <span class="mr-kicker">EXPERIMENTAL</span>
          <h1 class="mr-float-title">${esc(t("title"))}</h1>
          <button type="button" class="mr-float-toggle" data-panel-toggle aria-label="${esc(t("collapse"))}">–</button>
        </div>
        <div class="mr-float-body">
          <p class="mr-coords">${esc(data.coordinateSystem)}</p>
          <section class="mr-metrics">
            ${state.nodes.length === (data.questPoints || []).length + (data.markers || []).length
              ? ""
              : `<span class="mr-metric-active"><b>${state.nodes.length}</b>${esc(t("shownNodes"))}</span>`}
            <span><b>${(data.questPoints || []).length}</b>${esc(t("questPoints"))}</span>
            <span><b>${(data.markers || []).length}</b>${esc(t("entityMarkers"))}</span>
            <span><b>${(data.markers || []).filter((row) => (row.storyCount || 0) > 0).length}</b>${esc(t("storyNodes"))}</span>
            <span><b>${data.pinnedFileCount ?? 0}</b>${esc(t("pinnedFiles"))}</span>
            <span><b>${data.npcCoverage?.exactProxyCount ?? 0}</b>${esc(t("exactNpcs"))}</span>
          </section>
        </div>
      </section>
      <aside class="mr-float mr-float--controls" data-panel="controls" aria-label="${esc(t("controls"))}">
        <div class="mr-float-head" data-panel-drag>
          <h2 class="mr-float-title">${esc(t("controls"))}</h2>
          <button type="button" class="mr-float-toggle" data-panel-toggle aria-label="${esc(t("collapse"))}">–</button>
        </div>
        <div class="mr-float-body">
          <select id="map-recovery-select" aria-label="${esc(t("title"))}">${mapOptions()}</select>
          <h2>${esc(t("mission"))}</h2>
          ${missionControls}
          <h2>${esc(t("layers"))}</h2>
           <div class="mr-layer-actions">
             <button type="button" data-map-layers="all">${esc(t("layersAll"))}</button>
             <button type="button" data-map-layers="none">${esc(t("layersNone"))}</button>
             <button type="button" data-map-layers="story">${esc(t("layersStory"))}</button>
           </div>
           <p class="mr-note mr-layer-selection-hint">${esc(t("layerSelectionHint"))}</p>
           ${data.mapLayers?.length ? `<h2>${esc(t("mapLayers"))}</h2><div class="mr-layer-actions"><button type="button" data-map-elevation="all">${esc(t("layersAll"))}</button><button type="button" data-map-elevation="none">${esc(t("layersNone"))}</button></div><div class="mr-layers">${mapLayerControls}</div>` : ""}
           <h2>${esc(t("relations"))}</h2>
          <div class="mr-layer-actions" role="group" aria-label="${esc(t("relations"))}">
            ${["focus", "all", "off"].map((mode) => `<button type="button" data-map-relations="${mode}" aria-pressed="${state.relations === mode ? "true" : "false"}">${esc(t(`relations_${mode}`))}</button>`).join("")}
          </div>
          <p class="mr-note">${esc(t("relationsHint"))}</p>
          <div class="mr-layers">${(data.questPoints || []).length ? `<label class="mr-layer"><input type="checkbox" checked disabled><span class="mr-swatch" style="background:${QUEST_COLOR}"></span>quest</label>` : ""}${layerControls}</div>
          <h2>${esc(t("evidence"))}</h2>
           <p class="mr-note"><b>${state.backgrounds.length}</b> ${esc(surfaceLabel)}</p>
          <p class="mr-note"><code>${esc(minimapBg.status || "unknown")}</code>${minimapBg.src
            ? ` · ${t("minimapFrom")}: <b>${minimapBg.tileCount}</b> ${t("minimapTiles")} / ${t("minimapLayer")} <b>${minimapBg.layer}</b>`
            : ""}${esc(minimapBg.boundary || "")}</p>
          <p class="mr-note"><code>${esc(bg.status || "unknown")}</code>${esc(bg.boundary || "")}</p>
          ${sceneBlock}
          ${bg.gridFit ? `<p class="mr-note">${esc(t("gridFit"))}: <b>${Math.round((bg.gridFit.coverage || 0) * 100)}%</b> ${esc(t("gridFitOf"))} ${bg.gridFit.samplePoints} ${esc(t("gridFitMarkers"))} — <code>origin ${bg.gridFit.originX}, ${bg.gridFit.originZ}</code> / <code>${bg.gridFit.baseCellSize}m</code></p>` : ""}
          <p class="mr-note">${esc(data.npcCoverage?.boundary || "")}</p>
          ${unplaced.count
            ? `<details><summary>${esc(`${t("unplacedStories")} (${unplaced.count})`)}</summary>
                <p class="mr-note">${esc(unplaced.boundary || "")}</p>
                ${Object.entries(unplaced.reasonCounts || {}).map(([reason, count]) => `
                  <p class="mr-reason-head">${esc(t(`reason_${reason}`))} <b>${count}</b></p>
                  <ul class="mr-file-list">${(unplaced.stories || []).filter((row) => row.reason === reason).map((row) => `<li><code>${esc(row.key)}</code> ${storyLink(row.path)}</li>`).join("")}</ul>`).join("")}
              </details>`
            : ""}
          ${unresolvedSlots.count
            ? `<details><summary>${esc(`${t("unplacedTriggers")} (${unresolvedSlots.count})`)}</summary>
                <p class="mr-note">${esc(unresolvedSlots.boundary || "")}</p>
                <ul class="mr-file-list">${(unresolvedSlots.stories || []).map((row) => `<li><code>${esc(row.key)}</code> ${esc((row.triggerSlotIds || []).join(", "))}</li>`).join("")}</ul>
              </details>`
            : ""}
          <details><summary>${esc(`${t("unlinkedFiles")} (${unlinked.length})`)}</summary>
            ${unlinked.length
              ? `<ul class="mr-file-list">${unlinked.map((path) => `<li><a href="/${esc(path)}" target="_blank" rel="noreferrer">${esc(path)}</a></li>`).join("")}</ul>`
              : `<p class="mr-note">${esc(t("noFilesLinked"))}</p>`}
          </details>
        </div>
      </aside>
      <aside class="mr-float mr-float--inspector" data-panel="inspector" aria-label="${esc(t("inspector"))}">
        <div class="mr-float-head" data-panel-drag>
          <h2 class="mr-float-title">${esc(t("inspector"))}</h2>
          <button type="button" class="mr-float-toggle" data-panel-toggle aria-label="${esc(t("collapse"))}">–</button>
        </div>
        <div class="mr-inspector-head"></div>
        <div class="mr-inspector-body"></div>
      </aside>`;
    bindMap(host);
    state.inspectorKey = "";
    applyEdgeFocus();
    renderInspector();
    applyTransform();
  }

  // Two markers are drawn as related when they provably share a source file or
  // a script entity. Both are identity matches in the published payload, not
  // inferences about gameplay.
  function inferredEdges(markerIndex) {
    const rows = [];
    const seen = new Set();
    const addEdge = (from, to, kind, label) => {
      if (!from || !to || from === to) return;
      const key = [from, to].sort().join("::");
      if (seen.has(key)) return;
      seen.add(key);
      rows.push({ from, to, kind, label });
    };
    const groups = new Map();
    const group = (key, node) => {
      const list = groups.get(key) || [];
      list.push(node);
      groups.set(key, list);
    };
    markerIndex.forEach((node) => {
      sourcePaths(node).forEach((path) => group(`same_file:${path}`, node));
      const match = /^script:(\d+):/.exec(node.identity);
      if (match) group(`same_script:${match[1]}`, node);
    });
    for (const [key, nodes] of groups) {
      // A clique is quadratic in the group size. On a full world map one level
      // script can own hundreds of entity slots, which would draw tens of
      // thousands of lines that say only "same file" - unreadable and slow. A
      // group that large is dropped rather than thinned, because a partial
      // clique would misrepresent which members are related.
      if (nodes.length > MAX_EDGE_GROUP) continue;
      const kind = key.startsWith("same_file:") ? "same_file" : "same_script";
      const label = kind === "same_file" ? "shared source file" : "same script entity";
      for (let i = 0; i < nodes.length; i += 1) {
        for (let j = i + 1; j < nodes.length; j += 1) addEdge(nodes[i].id, nodes[j].id, kind, label);
      }
      if (rows.length > MAX_EDGES) return rows.slice(0, MAX_EDGES);
    }
    return rows;
  }

  // ---------------------------------------------------------------- events

  function bindMap(host) {
    host.querySelector("#map-recovery-select")?.addEventListener("change", (event) => {
      void switchMap(event.target.value);
    });
    host.querySelector("#map-recovery-mission")?.addEventListener("change", (event) => {
      state.mission = event.target.value;
      state.pendingFit = true; // an isolated mission occupies a different area
      render();
    });
    host.querySelectorAll("[data-map-kind]").forEach((input) => input.addEventListener("change", () => {
      state.kinds = new Set([...host.querySelectorAll("[data-map-kind]:checked")].map((row) => row.dataset.mapKind));
      scheduleRender();
    }));
    host.querySelectorAll("[data-map-subkind]").forEach((input) => input.addEventListener("change", () => {
      // Only the rendered subKinds are in the DOM, so the set is rebuilt from
      // the boxes plus every subKind whose kind has no nested rows.
      const shown = new Set([...host.querySelectorAll("[data-map-subkind]")].map((row) => row.dataset.mapSubkind));
      const checked = [...host.querySelectorAll("[data-map-subkind]:checked")].map((row) => row.dataset.mapSubkind);
      state.subKinds = new Set([...[...state.subKinds].filter((key) => !shown.has(key)), ...checked]);
      scheduleRender();
    }));
    host.querySelectorAll("[data-map-tier]").forEach((input) => input.addEventListener("change", () => {
      state.mapLayers = new Set([...host.querySelectorAll("[data-map-tier]:checked")].map((row) => row.dataset.mapTier));
      scheduleRender();
    }));
    host.querySelectorAll("[data-map-elevation]").forEach((button) => button.addEventListener("click", () => {
      state.mapLayers = button.dataset.mapElevation === "all" ? allMapLayers(state.map) : new Set();
      render();
    }));
    host.querySelectorAll("[data-map-relations]").forEach((button) => button.addEventListener("click", () => {
      state.relations = button.dataset.mapRelations;
      host.querySelectorAll("[data-map-relations]").forEach((row) => {
        row.setAttribute("aria-pressed", row.dataset.mapRelations === state.relations ? "true" : "false");
      });
      applyEdgeFocus();
    }));
    host.querySelectorAll("[data-map-layers]").forEach((button) => button.addEventListener("click", () => {
      const mode = button.dataset.mapLayers;
      const kinds = state.map?.facets?.kinds || {};
      const keep = ([kind, info]) => (mode === "all" ? true : mode === "story" ? info.storyCount > 0 : false);
      state.storyOnly = mode === "story";
      state.kinds = new Set(Object.entries(kinds).filter(keep).map(([kind]) => kind));
      state.subKinds = allSubKinds(state.map);
      render();
    }));

    const map = host.querySelector(".mr-map");
    if (!map) return;
    host.querySelectorAll("[data-map-zoom]").forEach((button) => button.addEventListener("click", () => {
      animateTo(zoomed(button.dataset.mapZoom === "in" ? 1.35 : 1 / 1.35, null));
    }));
    host.querySelector("[data-map-fit]")?.addEventListener("click", () => animateTo(fitTransform()));
    host.querySelector("[data-map-reset]")?.addEventListener("click", () => animateTo({ x: 0, y: 0, scale: 1 }));

    map.querySelectorAll(".mr-node").forEach((node) => {
      const id = node.dataset.node;
      const entry = state.nodes.find((row) => row.id === id);
      if (entry) {
        entry.el = node;
        entry.labelEl = node.querySelector(".mr-label");
      }
      node.addEventListener("pointerenter", () => { if (!state.dragging?.moved) setPreview(id); });
      node.addEventListener("pointerleave", () => { if (state.previewId === id && document.activeElement !== node) setPreview(""); });
      node.addEventListener("focus", () => setPreview(id));
      node.addEventListener("blur", () => { if (state.previewId === id) setPreview(""); });
      node.addEventListener("click", () => {
        if (performance.now() < state.suppressClickUntil) return;
        selectNode(id);
      });
      node.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " " && event.key !== "Spacebar") return;
        event.preventDefault();
        event.stopPropagation();
        selectNode(id);
      });
    });

    map.addEventListener("pointerdown", beginPan);
    map.addEventListener("pointermove", movePan);
    map.addEventListener("pointerup", endPan);
    map.addEventListener("pointercancel", endPan);
    // Non-passive so the page never scrolls behind a wheel zoom over the map.
    map.addEventListener("wheel", mapWheel, { passive: false });
    map.addEventListener("keydown", mapKeydown);
    // render() replaces the map element, so the observer is re-pointed at the
    // fresh one. It also recovers the layout when the view goes from hidden
    // (zero-sized, unmeasurable) to visible.
    if (state.observer) {
      state.observer.disconnect();
      state.observer.observe(map);
    }
    bindFloatPanels(host);
  }

  // The page is one full-bleed map surface; every piece of chrome is a
  // floating panel. Panels drag by their header and collapse onto it, and both
  // states survive render() through panelUi.
  function bindFloatPanels(host) {
    host.querySelectorAll(".mr-float").forEach((panel) => {
      const key = panel.dataset.panel;
      const saved = panelUi.get(key) || {};
      panel.classList.toggle("is-collapsed", !!saved.collapsed);
      if (Number.isFinite(saved.x) && Number.isFinite(saved.y)) {
        panel.style.left = `${saved.x}px`;
        panel.style.top = `${saved.y}px`;
        panel.style.right = "auto";
        panel.classList.add("is-placed");
      }
      panel.querySelector("[data-panel-toggle]")?.addEventListener("click", () => {
        const flags = panelUi.get(key) || {};
        flags.collapsed = !flags.collapsed;
        panelUi.set(key, flags);
        panel.classList.toggle("is-collapsed", flags.collapsed);
      });
      const head = panel.querySelector("[data-panel-drag]");
      if (!head) return;
      let drag = null;
      head.addEventListener("pointerdown", (event) => {
        if (event.pointerType === "mouse" && event.button !== 0) return;
        if (event.target.closest("button, input, select, a")) return;
        const rect = panel.getBoundingClientRect();
        const hostRect = host.getBoundingClientRect();
        drag = { id: event.pointerId, dx: event.clientX - rect.left - hostRect.left, dy: event.clientY - rect.top - hostRect.top };
        // Capture only keeps events flowing once the pointer leaves the panel;
        // it throws if the pointer is already gone, and the drag must survive.
        try { head.setPointerCapture(event.pointerId); } catch { /* drag without capture */ }
        event.preventDefault();
      });
      head.addEventListener("pointermove", (event) => {
        if (!drag || event.pointerId !== drag.id) return;
        const hostRect = host.getBoundingClientRect();
        const x = clamp(event.clientX - hostRect.left - drag.dx, 0, Math.max(0, hostRect.width - 60));
        const y = clamp(event.clientY - hostRect.top - drag.dy, 0, Math.max(0, hostRect.height - 40));
        panel.style.left = `${x}px`;
        panel.style.top = `${y}px`;
        panel.style.right = "auto";
        panel.classList.add("is-placed");
        const flags = panelUi.get(key) || {};
        flags.x = x;
        flags.y = y;
        panelUi.set(key, flags);
      });
      const endDrag = (event) => { if (drag && event.pointerId === drag.id) drag = null; };
      head.addEventListener("pointerup", endDrag);
      head.addEventListener("pointercancel", endDrag);
    });
  }

  const localPoint = (event, m) => ({ x: event.clientX - m.originX, y: event.clientY - m.originY });

  function mapWheel(event) {
    const m = metrics();
    if (!m) return;
    event.preventDefault();
    stopAnimation();
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? m.height : 1;
    const delta = clamp(event.deltaY * unit, -240, 240);
    state.transform = zoomed(Math.exp(-delta * 0.00125), localPoint(event, m));
    applyTransform();
  }

  function beginPan(event) {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    if (event.target.closest("input, select, label, button, summary, details")) return;
    stopAnimation();
    state.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (state.pointers.size === 2) {
      const [a, b] = [...state.pointers.values()];
      state.pinch = { distance: Math.hypot(a.x - b.x, a.y - b.y) || 1 };
      state.dragging = null;
      return;
    }
    if (state.pointers.size > 2) return;
    state.dragging = { id: event.pointerId, x: event.clientX, y: event.clientY, originX: state.transform.x, originY: state.transform.y, moved: false };
  }

  function movePan(event) {
    if (!state.pointers.has(event.pointerId)) return;
    const m = metrics();
    if (!m) return;
    state.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (state.pinch && state.pointers.size >= 2) {
      event.preventDefault();
      const [a, b] = [...state.pointers.values()];
      const distance = Math.hypot(a.x - b.x, a.y - b.y) || 1;
      const origin = { x: (a.x + b.x) / 2 - m.originX, y: (a.y + b.y) / 2 - m.originY };
      state.transform = zoomed(distance / state.pinch.distance, origin);
      state.pinch.distance = distance;
      state.suppressClickUntil = performance.now() + 350;
      applyTransform();
      return;
    }
    if (!state.dragging || state.dragging.id !== event.pointerId) return;
    const dx = event.clientX - state.dragging.x;
    const dy = event.clientY - state.dragging.y;
    if (!state.dragging.moved && Math.hypot(dx, dy) < 5) return;
    if (!state.dragging.moved) {
      state.dragging.moved = true;
      // Capture only keeps events flowing once the pointer leaves the map; it
      // throws if the pointer is already gone, and panning must survive that.
      try { mapEl()?.setPointerCapture?.(event.pointerId); } catch { /* pan without capture */ }
      mapEl()?.classList.add("is-panning");
    }
    event.preventDefault();
    state.transform = clamped({ scale: state.transform.scale, x: state.dragging.originX + dx / m.k, y: state.dragging.originY + dy / m.k });
    applyTransform();
  }

  function endPan(event) {
    state.pointers.delete(event.pointerId);
    if (state.pointers.size < 2) state.pinch = null;
    if (!state.dragging || state.dragging.id !== event.pointerId) return;
    const moved = state.dragging.moved;
    state.dragging = null;
    mapEl()?.classList.remove("is-panning");
    if (moved) state.suppressClickUntil = performance.now() + 350;
  }

  function mapKeydown(event) {
    if (event.target.closest("input, select, button")) return;
    const m = metrics();
    const step = m ? PAN_STEP / m.k : PAN_STEP;
    const pan = { ArrowLeft: [step, 0], ArrowRight: [-step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] }[event.key];
    if (pan) {
      event.preventDefault();
      stopAnimation();
      state.transform = clamped({ scale: state.transform.scale, x: state.transform.x + pan[0], y: state.transform.y + pan[1] });
      applyTransform();
      return;
    }
    if (event.key === "+" || event.key === "=") { event.preventDefault(); animateTo(zoomed(1.35, null)); return; }
    if (event.key === "-" || event.key === "_") { event.preventDefault(); animateTo(zoomed(1 / 1.35, null)); return; }
    if (event.key === "0") { event.preventDefault(); animateTo({ x: 0, y: 0, scale: 1 }); return; }
    if (event.key === "f" || event.key === "F") { event.preventDefault(); animateTo(fitTransform()); return; }
    if (event.key === "Escape") {
      event.preventDefault();
      clearSelection();
    }
  }

  // ---------------------------------------------------------------- region

  // Every level of one region (map01, map02, base01, ...) is authored in the
  // same world coordinate space, and each zone's map screen also depicts its
  // neighbours. The first view loads only the selected zone; choosing another
  // zone explicitly loads the rest of that region and restores the seamless
  // stitched surface without making the initial page pay for every sibling.
  const regionKey = (id) => (String(id).includes("_lv") ? String(id).split("_lv")[0] : String(id));

  async function ensurePayload(row) {
    if (!state.payloads.has(row.id)) {
      state.payloads.set(row.id, await fetchJson(`data/map_recovery/${row.src}`));
    }
    return state.payloads.get(row.id);
  }

  function zoneBackground(payload) {
    const minimap = payload.minimap || {};
    const hlod = payload.renderBackground || {};
    return (minimap.src && minimap.worldBounds) ? minimap
      : (hlod.src && hlod.worldBounds ? hlod : null);
  }

  // Merges a whole region's payloads into the shape render() always consumed,
  // with every row tagged by its level so node ids, registry pins and mission
  // filters stay unambiguous across levels.
  function mergeRegion(members, selectedId) {
    const selected = members.find((member) => member.id === selectedId)?.payload;
    if (!selected) return null;
    const kinds = {};
    const missions = {};
    const questPoints = [];
    const markers = [];
    const unlinked = new Set();
    const unplaced = [];
    const unplacedReasons = {};
    const unresolved = [];
    const backgrounds = [];
    const mapLayers = [];
    const layerBackgrounds = [];
    const locationLabels = new Map();
    let pinnedFileCount = 0;
    let exactProxyCount = 0;
    for (const member of members) {
      const payload = member.payload;
      if (!payload) continue;
      for (const row of payload.questPoints || []) questPoints.push({ ...row, levelId: member.id, mapLayerIds: (row.mapLayerIds || []).map((id) => `${member.id}:${id}`) });
      for (const row of payload.markers || []) markers.push({ ...row, levelId: member.id, mapLayerIds: (row.mapLayerIds || []).map((id) => `${member.id}:${id}`) });
      for (const layer of payload.mapConfig?.layers || []) {
        const id = `${member.id}:${layer.id}`;
        mapLayers.push({ ...layer, id, levelId: member.id });
        const rendered = (payload.minimap?.layers || []).find((row) => row.id === layer.id);
        if (rendered?.src && rendered.worldBounds) layerBackgrounds.push({ ...rendered, id, levelId: member.id });
      }
      for (const row of payload.mapConfig?.staticElements || []) {
        if (!row?.text || !row.position) continue;
        // The same named place can be present in several overlapping level
        // screens. Keep one stable authored anchor instead of drawing stacked
        // duplicates that look like conflicting region assignments.
        const key = `${row.text}:${Math.round(Number(row.position.x))}:${Math.round(Number(row.position.z))}`;
        if (!locationLabels.has(key)) locationLabels.set(key, { ...row, levelId: member.id });
      }
      (payload.unlinkedMissionFiles || []).forEach((path) => { if (path) unlinked.add(path); });
      pinnedFileCount += payload.pinnedFileCount || 0;
      exactProxyCount += payload.npcCoverage?.exactProxyCount || 0;
      for (const [kind, info] of Object.entries(payload.facets?.kinds || {})) {
        const merged = (kinds[kind] ||= { count: 0, storyCount: 0, subKinds: {} });
        merged.count += info.count || 0;
        merged.storyCount += info.storyCount || 0;
        for (const [subKind, sub] of Object.entries(info.subKinds || {})) {
          const entry = (merged.subKinds[subKind] ||= { count: 0, storyCount: 0, label: sub.label || subKind });
          entry.count += sub.count || 0;
          entry.storyCount += sub.storyCount || 0;
          if (sub.label) entry.label = sub.label;
        }
      }
      for (const [missionId, counts] of Object.entries(payload.facets?.missions || {})) {
        const entry = (missions[missionId] ||= { markers: 0, questPoints: 0, stories: 0 });
        entry.markers += counts.markers || 0;
        entry.questPoints += counts.questPoints || 0;
        entry.stories += counts.stories || 0;
      }
      const unplacedStories = payload.unplacedStories;
      if (unplacedStories?.count) {
        unplaced.push(...(unplacedStories.stories || []));
        for (const [reason, count] of Object.entries(unplacedStories.reasonCounts || {})) {
          unplacedReasons[reason] = (unplacedReasons[reason] || 0) + count;
        }
      }
      const unresolvedSlots = payload.unresolvedTriggerSlots;
      if (unresolvedSlots?.count) unresolved.push(...(unresolvedSlots.stories || []));
      const background = zoneBackground(payload);
      if (background) backgrounds.push({ levelId: member.id, src: background.src, worldBounds: background.worldBounds });
    }
    // These are overlapping map screens, not disjoint rectangles owned by
    // the selected gameplay level. A stable order prevents selection changes
    // from making whole geographic areas appear to exchange positions.
    backgrounds.sort((a, b) => a.levelId.localeCompare(b.levelId));
    state.backgrounds = backgrounds;
    state.layerBackgrounds = layerBackgrounds;
    return {
      ...selected,
      mapLayers,
      locationLabels: [...locationLabels.values()],
      questPoints,
      markers,
      facets: { kinds, missions },
      pinnedFileCount,
      npcCoverage: { exactProxyCount, boundary: selected.npcCoverage?.boundary || "" },
      unplacedStories: {
        count: unplaced.length,
        boundary: selected.unplacedStories?.boundary || "",
        reasonCounts: unplacedReasons,
        stories: unplaced,
      },
      unresolvedTriggerSlots: {
        count: unresolved.length,
        boundary: selected.unresolvedTriggerSlots?.boundary || "",
        stories: unresolved,
      },
      unlinkedMissionFiles: [...unlinked],
    };
  }

  // ---------------------------------------------------------------- lifecycle

  async function loadMap(id, { includeRegion = !!state.map } = {}) {
    const row = (state.index?.maps || []).find((item) => item.id === id) || state.index?.maps?.[0];
    if (!row) return false;
    const key = regionKey(row.id);
    // Keep initial activation on demand. Once the reader explicitly changes
    // zones, load the siblings in parallel so the existing stitched-region
    // behavior remains available for deliberate navigation.
    const memberRows = includeRegion
      ? (state.index?.maps || []).filter((item) => regionKey(item.id) === key)
      : [row];
    const members = memberRows
      .sort((a, b) => a.id.localeCompare(b.id))
      .map((item) => ({ id: item.id, row: item }));
    await Promise.all(members.map(async (member) => {
      member.payload = await ensurePayload(member.row);
    }));
    // A few regions at most should stay resident; the rest are re-fetchable.
    if (state.payloads.size > 40) {
      for (const cached of [...state.payloads.keys()]) {
        if (regionKey(cached) !== key) state.payloads.delete(cached);
      }
    }
    state.selected = row.id;
    state.map = mergeRegion(members, row.id);
    if (!state.map) return false;
    // New indexes may carry region bounds without repeating the region object
    // in every payload. Keep that compact catalog fallback compatible with
    // payloads produced before the region metadata was added.
    const regionBounds = row.regionBounds
      || state.index?.regionBounds?.[regionKey(row.id)]
      || state.index?.regions?.[regionKey(row.id)]?.worldBounds;
    if (!state.map.region?.worldBounds && regionBounds) {
      state.map.region = {
        key: regionKey(row.id),
        worldBounds: regionBounds,
      };
    }
    // Do not render every marker on first open. Large levels can contain
    // several thousand entities; dialog-bearing layers are the smallest
    // useful starting point and the layer controls make the broader views
    // explicit user choices.
    state.kinds = storyKinds(state.map);
    state.subKinds = allSubKinds(state.map);
    // Multi-floor maps must not begin as a stack of every transparent tier.
    // Start on one authored floor and let the reader opt into comparisons.
    // Prefer the selected sub-map's first authored tier even though region
    // members are merged in stable id order for rendering and caching.
    const initialMapLayer = state.map.mapLayers?.find((row) => row.levelId === state.selected)
      || state.map.mapLayers?.[0];
    state.mapLayers = initialMapLayer
      ? new Set([String(initialMapLayer.id)])
      : new Set();
    state.storyOnly = true;
    state.mission = "";
    state.transform = { x: 0, y: 0, scale: 1 };
    state.pendingFit = true;
    state.selectedId = "";
    state.previewId = "";
    state.filePath = "";
    state.inspectorKey = "";
    render();
    return true;
  }

  async function switchMap(id) {
    window.WebUI?.setViewBusy?.("map-recovery", true);
    window.WebUI?.showLoader?.("map-recovery", t("loading"));
    try {
      return await loadMap(id);
    } catch (error) {
      renderLoadError(error);
      return false;
    } finally {
      window.WebUI?.setViewBusy?.("map-recovery", false);
      window.WebUI?.hideLoader?.("map-recovery");
    }
  }

  function renderLoadError(error) {
    const host = root();
    if (!host) return;
    const detail = error?.message ? `: ${error.message}` : "";
    host.innerHTML = `<div class="mr-load-state mr-load-state--error" role="alert"><strong>${esc(t("loadError"))}</strong><span>${esc(detail)}</span><button type="button" data-map-retry>${esc(t("retry"))}</button></div>`;
    host.querySelector("[data-map-retry]")?.addEventListener("click", () => {
      // Keep retry inline with the other data views. The promise is handled
      // here because the next-view tracker only owns the first activation.
      load({ force: true }).catch(() => {});
    });
  }

  async function load({ force = false } = {}) {
    const host = root();
    if (!host) return false;
    const request = ++state.loadRequest;
    state.loadController?.abort();
    state.loadController = new AbortController();
    host.innerHTML = `<div class="mr-load-state" role="status" aria-live="polite"><span>${esc(t("loading"))}</span></div>`;
    window.WebUI?.clearShellStatus?.("map-recovery");
    window.WebUI?.setViewBusy?.("map-recovery", true);
    window.WebUI?.showLoader?.("map-recovery", t("loading"));
    try {
      state.index = force || !state.index
        ? await fetchJson("data/map_recovery/index.json", {
          cache: force ? "reload" : "no-store",
          signal: state.loadController.signal,
          onProgress: (ratio) => window.WebUI?.updateLoader?.("map-recovery", ratio == null ? null : ratio * 0.3, t("loading")),
        })
        : state.index;
      if (request !== state.loadRequest) return null;
      window.WebUI?.updateLoader?.("map-recovery", 0.35, t("loading"));
      await window.WebUI?.nextPaint?.();
      // Payloads are fetched in parallel by loadMap. Keep the shared loader
      // indeterminate while those files are being decoded and merged.
      window.WebUI?.updateLoader?.("map-recovery", null, t("loading"));
      const loaded = await loadMap(state.selected || state.index.defaultMap, { includeRegion: false });
      if (request !== state.loadRequest) return null;
      window.WebUI?.updateLoader?.("map-recovery", 1, t("loading"));
      return loaded;
    } catch (error) {
      if (request !== state.loadRequest || error?.name === "AbortError") return null;
      renderLoadError(error);
      throw error;
    } finally {
      if (request === state.loadRequest) {
        state.loadController = null;
        window.WebUI?.setViewBusy?.("map-recovery", false);
        window.WebUI?.hideLoader?.("map-recovery");
      }
    }
  }

  function init() {
    if (state.bound) return;
    state.bound = true;
    // A UI-locale switch only re-renders chrome; the map selection, layer
    // filters and current view transform are all kept in state.
    window.addEventListener("webui:ui-locale-changed", () => {
      state.inspectorKey = "";
      render();
    });
    const resync = () => { if (state.map && metrics()) applyTransform(); };
    window.addEventListener("resize", resync);
    if (typeof ResizeObserver === "function") state.observer = new ResizeObserver(resync);
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.mapRecovery = { init, load };
})();
