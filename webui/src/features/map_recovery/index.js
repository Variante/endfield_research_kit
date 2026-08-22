(() => {
  // The SVG world projection below is authoritative: viewBox size, padding and
  // plot() must stay byte-identical to the published coordinate contract.
  // Zoom/pan is layered strictly on top of it as a group transform, so screen
  // navigation never rewrites world coordinates.
  const WIDTH = 1024;
  const HEIGHT = 1280;
  const PAD = 64;
  const MIN_SCALE = 0.3; // a whole region can span several zone maps of canvas
  const MAX_SCALE = 48;
  const ENTITY_SCALE_MIN = 0.5;
  const ENTITY_SCALE_MAX = 3;
  const ENTITY_SCALE_STEP = 1.25;
  const MAP_ASSET_VERSION = "20260822-map69";
  const PAN_OVERHANG = 96; // px of surface a pan may run past the content edge
  const LABEL_ZOOM = 1.7; // minor entity labels stay hidden below this zoom
  const GEO_LABEL_ZOOM = 0.3; // keep one primary name per sibling at region view
  const GEO_LOCAL_ZOOM = 1.25; // reveal local place names after the map is readable
  const GEO_ALL_ZOOM = 2.2; // allow dense local names only when zoomed in
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
    // npc used to share the quest green, which made the two layers
    // indistinguishable on the map. It now owns the yellow-green slot.
    npc: "#4d8a1f",
    spawn: "#367f84",
    narrative: "#a03c86",
    collectible: "#8a7b1f",
    waypoint: "#4a6b8a",
  };
  const QUEST_COLOR = "#2f7d4f";
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
    modelLayers: new Set(["elevation", "surface", "water", "points"]),
    showMinimap: true,
    showQuests: false,
    storyOnly: false,
    mission: "", // "" means every mission this level hosts
    bound: false,
    transform: { x: 0, y: 0, scale: 1 },
    entityScale: 1,
    nodes: [],
    locationLabels: [],
    selectedId: "",
    previewId: "",
    inspectorKey: "",
    filePath: "",
    filePathLabel: "",
    pendingFit: false,
    // A map switch should frame the selected map screen even when the clean
    // geographic view intentionally has no entity nodes enabled. Keep this
    // target separate from pendingFit so mission changes still fit nodes.
    pendingFitTarget: "nodes",
    dragging: null,
    pointers: new Map(),
    pinch: null,
    animation: 0,
    suppressClickUntil: 0,
    observer: null,
    fileCache: new Map(),
    fileFlight: new Map(),
    payloads: new Map(), // levelId -> payload; siblings of a region share the cache
    backgrounds: [], // every region zone's map screen, in stable draw order
    modelBackgrounds: [], // recovered geometry, retained even when a minimap is authoritative
    layerBackgrounds: [], // transparent tier overlays, kept separate from base screens
    floorHitAreas: [], // tier rectangles, including overlays not currently selected
    pointCloudOpacity: 0.82, // only affects scan PNGs that expose an elevation underlay
    pointHeightRange: null, // exact world-Y bounds and the active two-thumb interval
    contentBox: null, // plotted content extent in viewBox units, for the pan clamp
    selectedMapBox: null, // selected level's fitted background rectangle
    lastNodeScale: null, // skip per-node writes while a pan keeps the same scale
    lastLocationScale: null,
    loadRequest: 0,
    loadController: null,
  };

  // The page re-renders its whole DOM on every filter change, so floating panel
  // positions and collapsed states live outside the element tree.
  const panelUi = new Map();
  const pointPixelCache = new Map();
  const pointSampleCache = new Map();
  let pointFilterTimer = 0;
  let pointFilterToken = 0;

  const root = () => document.querySelector("#map-recovery-app");
  const mapEl = () => root()?.querySelector(".mr-map");
  const svgEl = () => root()?.querySelector(".mr-canvas");
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
  const clamp = (value, low, high) => Math.min(high, Math.max(low, value));
  const pointHeightMasks = () => state.modelBackgrounds
    .map((row) => row.pointCloudOverlay?.sampleSet || row.pointCloudOverlay?.heightMask)
    .filter((row) => row?.src && Number.isFinite(Number(row.elevationRange?.min)) && Number.isFinite(Number(row.elevationRange?.max)));
  const resetPointHeightRange = () => {
    const masks = pointHeightMasks();
    if (!masks.length) {
      state.pointHeightRange = null;
      return;
    }
    const min = Math.min(...masks.map((row) => Number(row.elevationRange.min)));
    const max = Math.max(...masks.map((row) => Number(row.elevationRange.max)));
    state.pointHeightRange = { min, max, low: min, high: max };
  };
  const formatHeight = (value) => `${Math.round(Number(value) * 10) / 10}m`;
  // Mission text carries inline rich-text tags such as <@qu.key>; strip them
  // the same way the mission-pipeline view does instead of rendering markup.
  const plainText = (value) => String(value ?? "").replace(/<@[^>]*>/g, "").replace(/<\/[^>]+>/g, "").replace(/<[^>]+>/g, "").replaceAll("\\n", " ").trim();
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
  const KIND_LABELS = {
    en: { story: "Story", travel: "Travel", device: "Device", scenery: "Scenery", trigger: "Trigger zone", enemy: "Enemy", npc: "NPC", spawn: "Spawn", narrative: "Narrative", collectible: "Collectible", waypoint: "Waypoint", quest: "Quest" },
    zh: { story: "剧情", travel: "移动设施", device: "交互装置", scenery: "场景物件", trigger: "触发区域", enemy: "敌人", npc: "NPC", spawn: "出生点", narrative: "叙事锚点", collectible: "收集物", waypoint: "任务坐标", quest: "任务点" },
  };
  const kindLabel = (kind) => (isZh() ? KIND_LABELS.zh : KIND_LABELS.en)[kind] || kind;
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

  const mapFloorNumber = (layer) => {
    const key = String(layer?.nameKey || "");
    const match = key.match(/_layer_tips_([0-9]+)$/i);
    return match ? match[1] : "";
  };

  const mapLayerLabel = (layer) => {
    const number = mapFloorNumber(layer);
    const tier = layer?.tierId ?? layer?.id;
    if (number) return `${t("mapFloor")} ${number} / ${t("mapTier")} ${tier}`;
    return layer?.displayName ? `${layer.displayName} / ${t("mapTier")} ${tier}` : `${t("mapTier")} ${tier}`;
  };

  const mapLayerRange = (layer) => {
    const range = layer?.heightRange;
    if (!range || !Number.isFinite(Number(range.minY)) || !Number.isFinite(Number(range.maxY))) return "";
    return `Y ${Number(range.minY).toFixed(1)} - ${Number(range.maxY).toFixed(1)}`;
  };

  const orderedMapLayers = (rows) => [...rows].sort((a, b) => {
    const floorA = Number(mapFloorNumber(a));
    const floorB = Number(mapFloorNumber(b));
    if (floorA && floorB) return floorA - floorB;
    if (floorA) return -1;
    if (floorB) return 1;
    return Number(a.tierId) - Number(b.tierId) || String(a.id).localeCompare(String(b.id));
  });

  const modelLayerControlsHtml = () => {
    const hasMinimap = state.backgrounds.some((row) => row.sourceKind === "minimap");
    if (!state.modelBackgrounds.length && !hasMinimap) return "";
    const rows = [
      ["elevation", "modelElevation", state.modelBackgrounds.some((row) => row.elevationUnderlay?.src)],
      ["surface", "modelSurface", state.modelBackgrounds.some((row) => row.status !== "inferred_registry_point_cloud_preview")],
      ["water", "modelWater", state.modelBackgrounds.some((row) => row.waterOverlay?.src)],
      ["points", "modelPoints", state.modelBackgrounds.some((row) => row.pointCloudOverlay?.src)],
    ];
    const minimap = hasMinimap
      ? `<label><input type="checkbox" data-map-minimap ${state.showMinimap ? "checked" : ""}>${esc(t("minimapLayer"))}</label>`
      : "";
    return `<fieldset class="mr-model-layers"><legend>${esc(t("modelLayers"))}</legend>${minimap}${rows.filter(([, , available]) => available).map(([id, label]) => (
      `<label><input type="checkbox" data-map-model-layer="${id}" ${state.modelLayers.has(id) ? "checked" : ""}>${esc(t(label))}</label>`
    )).join("")}</fieldset>`;
  };

  // Every level in LevelBasicInfoTable that owns a plottable node is published,
  // which is far too many for a flat list to be readable. The options are
  // grouped by the level family the builder assigns and annotated with the two
  // numbers that decide whether a map is worth opening: how many nodes it plots
  // and how many distinct story keys those nodes reach.
  // A level id alone does not say which place the reader is looking at, so
  // every level carries the display name the builder recovered from the
  // level's own table rows (LevelDescTable + per-language I18nTextTable),
  // keeping the id as the stable handle next to it.
  const missionTitle = (id, detail = {}) => detail.name ? `${id} · ${detail.name}` : id;
  const mapTitle = (row) => {
    if (row.name) return `${row.name} (${row.id})`;
    const missions = row.missions || [];
    if (missions.length === 1) {
      const mission = missions[0];
      const name = row.missionNames?.[mission] || row.missionDetails?.[mission]?.name || "";
      return `${missionTitle(mission, { name })} (${row.id})`;
    }
    return row.label;
  };

  const mapTreeHtml = () => {
    const groups = new Map();
    for (const row of state.index?.maps || []) {
      const family = row.family || "Other";
      if (!groups.has(family)) groups.set(family, []);
      groups.get(family).push(row);
    }
    return [...groups.entries()].map(([family, rows]) => `<section class="mr-map-group"><h3>${esc(family)}</h3>${rows.map((row) => (
      `<button type="button" class="mr-map-item${row.id === state.selected ? " is-active" : ""}" data-map-id="${esc(row.id)}" title="${esc(mapTitle(row))}"><b>${esc(mapTitle(row))}</b><span>${row.storyKeyCount || 0}${esc(t("countStories"))}</span></button>`
    )).join("")}</section>`).join("");
  };

  const mapOptions = () => {
    const groups = new Map();
    for (const row of state.index?.maps || []) {
      const family = row.family || "—";
      if (!groups.has(family)) groups.set(family, []);
      groups.get(family).push(row);
    }
    const familyPriority = (rows) => {
      const key = regionKey(rows[0]?.id || "");
      return key === "base01" ? 0 : key === "map01" ? 1 : key === "map02" ? 2 : 3;
    };
    return [...groups.entries()]
      .sort((a, b) => familyPriority(a[1]) - familyPriority(b[1]) || a[0].localeCompare(b[0]))
      .map(([family, rows]) => {
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
      // The chip carries its layer's own hue when checked (--mr-chip), so a
      // green swatch never sits on an orange "on" tint.
      const color = KIND_COLORS[kind] || "#8b9298";
      const swatch = `<span class="mr-swatch" style="background:${esc(color)}"></span>`;
      const head = `<label class="mr-layer" style="--mr-chip:${esc(color)}" title="${esc(`${info.count}${t("countMarkers")}${info.storyCount ? ` · ${info.storyCount}${t("countStories")}` : ""}`)}">`
        + `<input type="checkbox" data-map-kind="${esc(kind)}" ${state.kinds.has(kind) ? "checked" : ""}>`
        + `${swatch}${esc(kindLabel(kind))}<span class="mr-layer-count">${info.count}${info.storyCount ? `<i>+${info.storyCount}</i>` : ""}</span></label>`;
      const subs = Object.entries(info.subKinds || {});
      if (subs.length < 2) return `<div class="mr-layer-group">${head}</div>`;
      const rows = subs
        .sort((a, b) => b[1].count - a[1].count)
        .map(([subKind, sub]) => {
          // The recovered labels are Chinese, so an English reader is better
          // served by the subKind slug. Both are always in the tooltip.
          const shown = isZh() ? (sub.label || kindLabel(subKind)) : kindLabel(subKind);
          const title = sub.label && sub.label !== subKind ? `${sub.label} / ${subKind}` : subKind;
          return `<label class="mr-layer mr-sublayer" style="--mr-chip:${esc(color)}" title="${esc(title)}"><input type="checkbox" data-map-subkind="${esc(subKind)}" ${state.subKinds.has(subKind) ? "checked" : ""}>`
            + `${esc(shown)}<span class="mr-layer-count">${sub.count}</span></label>`;
        })
        .join("");
      return `<div class="mr-layer-group">${head}<div class="mr-sublayers">${rows}</div></div>`;
    }).join("");
  };

  // Missions use the same expandable-list shape as Story: select the mission
  // from its summary, then inspect the files owned by that mission in place.
  const missionSelectHtml = (data) => {
    const details = data.missionDetails || {};
    const missions = Object.entries(data.facets?.missions || {}).map(([id, counts]) => [id, { ...counts, ...(details[id] || {}) }]);
    if (!missions.length) return `<p class="mr-note">${esc(t("missionNone"))}</p>`;
    const rows = missions
      .sort((a, b) => (b[1].markers + b[1].questPoints) - (a[1].markers + a[1].questPoints) || a[0].localeCompare(b[0]))
      .map(([id, counts]) => {
        const active = id === state.mission;
        const files = (counts.files || []).map((path) => `<li><a href="/${esc(path)}" target="_blank" rel="noreferrer" title="${esc(path)}">${esc(fileName(path))}</a>${storyLink(path)}</li>`).join("");
        const linkedMap = id === "e0m0" && data.levelId === "indie_dg002"
          ? (state.index?.maps || []).find((row) => row.id === "indie_dg004")
          : null;
        return `<details class="mr-mission-item${active ? " is-active" : ""}" ${active ? "open" : ""}>
          <summary data-map-mission="${esc(id)}"><b>${esc(missionTitle(id, counts))}</b><span>${counts.stories || 0}${esc(t("countStories"))}</span></summary>
          <div class="mr-mission-files">${linkedMap ? `<button type="button" class="mr-map-transition" data-map-id="${esc(linkedMap.id)}"><b>${esc(id)} → dg004</b><span>${esc(t("missionNextMap"))}</span></button>` : ""}<details><summary>${esc(`${t("missionFiles")} (${counts.files?.length || 0})`)}</summary>${files ? `<ul>${files}</ul>` : `<p>${esc(t("noFiles"))}</p>`}</details></div>
        </details>`;
      }).join("");
    return `<div class="mr-mission-list"><button type="button" class="mr-mission-all${state.mission ? "" : " is-active"}" data-map-mission="">${esc(`${t("missionAll")} (${missions.length})`)}</button>${rows}</div>`;
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
      title: "Map",
      layers: "Layers",
      objectFilters: "Object display",
      mapLayers: "Map floors",
      mapLayersNone: "No tier overlays are declared by this level's UILevelMapLoadConfig.",
      mapFloor: "Floor",
      mapTier: "tier",
      mapFloorNone: "Base map",
      mapFloorNoneHint: "Show the stitched geographic base without a floor overlay.",
      mapFloorChoose: "Displayed floor",
      mapFloorHover: "More floors here",
      mapFloorClickCycle: "Click to cycle",
      mapFloorCurrent: "Current",
      pointCloudOpacity: "Point cloud opacity",
      pointCloudHeight: "Point height",
      pointCloudHeightRange: "Visible point height range",
      pointCloudHeightMin: "Minimum visible point height",
      pointCloudHeightMax: "Maximum visible point height",
      evidence: "Evidence",
      controls: "Controls",
      collapse: "Collapse panel",
      expand: "Expand panel",
      regionSurface: "zone map screens stitched into one seamless surface",
      selectedSurface: "selected zone map screen loaded; choose another zone to load the stitched region",
      loading: "Loading map recovery data...",
      mapSurface: "World map, pan and zoom surface",
      zoomIn: "Zoom in",
      zoomOut: "Zoom out",
      entitySize: "Entity size",
      entityZoomIn: "Enlarge entities",
      entityZoomOut: "Shrink entities",
      entityReset: "Reset entity size",
      modelLayers: "Recovered model layers",
      minimapLayer: "In-game minimap",
      modelSurface: "Material / surface",
      modelElevation: "Grayscale elevation",
      modelWater: "Recovered water",
      modelPoints: "Colored point cloud",
      fit: "Fit",
      fitLong: "Fit all plotted nodes",
      reset: "Reset",
      resetLong: "Reset to full declared world bounds",
      zoomLevel: "Zoom",
      help: "Wheel or +/- zooms, drag or arrows pan, Tab walks the nodes, Enter pins one, Esc clears, 0 resets, F fits. Hover multi-floor areas and click to cycle.",
      questPoint: "Quest point",
      missionStart: "Mission start",
      missionEnd: "Mission end",
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
      missionFiles: "Mission files",
      missionNextMap: "e0m0 finishes in this linked map",
      layersAll: "All",
      layersNone: "None",
      layersStory: "With dialog",
      layerSelectionHint: "The overview starts as a clean geographic map. Enable quests, dialog markers, or other layers when needed.",
      loadError: "Map recovery data could not be loaded",
      retry: "Retry",
      questRoute: "Quest route",
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
      noStoryAtNode: "No story information is linked to this map item.",
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
      streamingSceneHint: "The instance transform is exact, and matched static OBJ geometry is rasterized into the top-down background.",
      scene3dUnplacedHint: "These level-matched OBJ exports have no recovered scene transform. Open them in Assets for inspection; they are not placed on this map.",
      scene3dUnavailable: "No safe OBJ model is published for this level; the map stays marker-only.",
    },
    zh: {
      objectFilters: "\u5bf9\u8c61\u663e\u793a",
      mapFloor: "\u697c\u5c42",
      mapTier: "\u5c42\u7ea7",
      mapFloorNone: "\u4ec5\u663e\u793a\u5e95\u56fe",
      mapFloorNoneHint: "\u663e\u793a\u62fc\u63a5\u540e\u7684\u5730\u7406\u5e95\u56fe\uff0c\u4e0d\u53e0\u52a0\u697c\u5c42\u56fe\u3002",
      mapFloorChoose: "\u5f53\u524d\u663e\u793a\u697c\u5c42",
      mapFloorHover: "\u6b64\u5904\u8fd8\u6709\u66f4\u591a\u697c\u5c42",
      mapFloorClickCycle: "\u70b9\u51fb\u5faa\u73af\u5207\u6362",
      mapFloorCurrent: "\u5f53\u524d",
      pointCloudOpacity: "\u70b9\u4e91\u900f\u660e\u5ea6",
      pointCloudHeight: "\u70b9\u4e91\u9ad8\u5ea6",
      pointCloudHeightRange: "\u53ef\u89c1\u70b9\u4e91\u9ad8\u5ea6\u533a\u95f4",
      pointCloudHeightMin: "\u6700\u4f4e\u53ef\u89c1\u70b9\u4e91\u9ad8\u5ea6",
      pointCloudHeightMax: "\u6700\u9ad8\u53ef\u89c1\u70b9\u4e91\u9ad8\u5ea6",
      mapLayers: "地图楼层",
      mapLayersNone: "该关卡的 UILevelMapLoadConfig 未声明楼层叠图。",
      layerSelectionHint: "\u9ed8\u8ba4\u4ee5\u5e72\u51c0\u7684\u5730\u7406\u5730\u56fe\u663e\u793a\u3002\u9700\u8981\u65f6\u518d\u5f00\u542f\u4efb\u52a1\u3001\u5267\u60c5\u6216\u5176\u5b83\u6807\u8bb0\u3002",
      loadError: "\u65e0\u6cd5\u52a0\u8f7d\u5730\u56fe\u6062\u590d\u6570\u636e",
      retry: "\u91cd\u8bd5",
      title: "地图",
      layers: "图层",
      evidence: "证据",
      controls: "控制面板",
      collapse: "收起面板",
      expand: "展开面板",
      regionSurface: "张区域地图屏按世界坐标拼成无缝整面",
      selectedSurface: "\u5df2\u52a0\u8f7d\u5f53\u524d\u533a\u57df\u5730\u56fe\u5c4f\uff1b\u9009\u62e9\u5176\u4ed6\u533a\u57df\u540e\u52a0\u8f7d\u62fc\u63a5\u5730\u56fe",
      loading: "正在加载地图数据...",
      mapSurface: "世界地图，可平移缩放",
      zoomIn: "放大",
      zoomOut: "缩小",
      entitySize: "实体大小",
      entityZoomIn: "放大实体",
      entityZoomOut: "缩小实体",
      entityReset: "重置实体大小",
      modelLayers: "重建模型图层",
      minimapLayer: "游戏小地图",
      modelSurface: "材质 / 表面",
      modelElevation: "灰度高程",
      modelWater: "恢复水体",
      modelPoints: "彩色点云",
      fit: "适配",
      fitLong: "适配全部节点",
      reset: "复位",
      resetLong: "复位到完整声明世界边界",
      zoomLevel: "缩放",
      help: "滚轮或 +/- 缩放，拖拽或方向键平移，Tab 遍历节点，Enter 固定，Esc 取消，0 复位，F 适配。悬浮多层区域可查看提示，点击循环切换楼层。",
      questPoint: "任务点",
      missionStart: "任务开始",
      missionEnd: "任务结束",
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
      missionFiles: "任务文件",
      missionNextMap: "e0m0 在此关联地图结束",
      layersAll: "全选",
      layersNone: "全不选",
      layersStory: "含剧情",
      questRoute: "任务路线",
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
      noStoryAtNode: "此地图项目没有关联的剧情信息。",
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
      streamingSceneHint: "实例变换为精确恢复，已匹配的静态 OBJ 网格已栅格化进俯视背景。",
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
        [t("mission"), node.endpointRole ? t(node.endpointRole === "start" ? "missionStart" : "missionEnd") : ""],
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
  const nodeRole = (node) => (node.type === "quest"
    ? (node.endpointRole ? t(node.endpointRole === "start" ? "missionStart" : "missionEnd") : t("questPoint"))
    : t("entityNode"));
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

  function fitTransform(targetMode = state.pendingFitTarget) {
    const target = targetMode === "map" ? state.selectedMapBox : null;
    if (!state.nodes.length && !target) return { x: 0, y: 0, scale: 1 };
    if (target) {
      const width = Math.max(1, Number(target.w) || 1);
      const height = Math.max(1, Number(target.h) || 1);
      const scale = clamp(Math.min((WIDTH - 2 * PAD) / width, (HEIGHT - 2 * PAD) / height), MIN_SCALE, MAX_SCALE);
      return clamped({
        scale,
        x: WIDTH / 2 - scale * (Number(target.x) + width / 2),
        y: HEIGHT / 2 - scale * (Number(target.y) + height / 2),
      });
    }
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
    if (state.pendingFit && (state.nodes.length || (state.pendingFitTarget === "map" && state.selectedMapBox))) {
      state.pendingFit = false;
      const fitTarget = state.pendingFitTarget;
      state.pendingFitTarget = "nodes";
      state.transform = fitTransform(fitTarget);
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
    const nodeScale = clamp(state.entityScale / (m.k * scale), 0.025, 24);
    const locationScale = clamp(1 / (m.k * scale), 0.05, 8);
    const nodeScaleChanged = nodeScale !== state.lastNodeScale;
    const locationScaleChanged = locationScale !== state.lastLocationScale;
    if (nodeScaleChanged) state.lastNodeScale = nodeScale;
    if (locationScaleChanged) state.lastLocationScale = locationScale;
    state.nodes.forEach((node) => {
      node.px = toPixel(m, node.plot);
      if (nodeScaleChanged && node.el) {
        node.el.setAttribute("transform", `translate(${node.plot.x.toFixed(3)} ${node.plot.y.toFixed(3)}) scale(${nodeScale.toFixed(5)})`);
      }
    });
    state.locationLabels.forEach((label) => {
      label.px = toPixel(m, label.plot);
      if (locationScaleChanged && label.el) {
        // Geographic labels use the same counter-scale as pins. They remain
        // readable while zooming, and their collision boxes stay in screen px.
        label.el.setAttribute("transform", `translate(${label.plot.x.toFixed(3)} ${label.plot.y.toFixed(3)}) scale(${locationScale.toFixed(5)})`);
      }
    });
    const labelBoxes = layoutLocationLabels(m);
    layoutLabels(m, labelBoxes);
    const readout = host.querySelector(".mr-zoom-readout");
    if (readout) readout.textContent = `${t("zoomLevel")} ${Math.round(scale * 100)}%`;
    const entityReadout = host.querySelector(".mr-entity-readout");
    if (entityReadout) entityReadout.textContent = `${Math.round(state.entityScale * 100)}%`;
    syncTip(m);
  }

  function layoutLocationLabels(m) {
    const boxes = [];
    const scale = state.transform.scale;
    const hasMajor = state.locationLabels.some((label) => label.major);
    const ranked = state.locationLabels.slice().sort((a, b) => {
      // Major geographic labels claim space before local names. Stable
      // position ordering prevents labels from flickering during a pan.
      return Number(b.major) - Number(a.major) || b.labelPx - a.labelPx || a.id.localeCompare(b.id);
    });
    ranked.forEach((label) => {
      if (!label.el || !label.px) return;
      const onScreen = label.px.x > -100 && label.px.x < m.width + 100 && label.px.y > -80 && label.px.y < m.height + 80;
      // At region scale keep only major anchors. A map that has no explicit
      // region-tier labels still gets useful names, but only one collision-free
      // set of local names is admitted until the reader zooms in.
      // A family without explicit region-tier labels (for example map01's
      // local `sub01_location_tips`) still needs a readable anchor at the
      // initial fitted scale, so allow the collision pass from the minimum
      // zoom instead of making that otherwise valid map nameless.
      const threshold = label.major ? GEO_LABEL_ZOOM : (!hasMajor ? MIN_SCALE : GEO_LOCAL_ZOOM);
      let visible = onScreen && scale >= threshold;
      if (visible) {
        const box = {
          x: label.px.x - label.labelPx / 2,
          y: label.px.y - LABEL_LINE,
          w: label.labelPx,
          h: LABEL_LINE,
        };
        if (boxes.some((other) => box.x < other.x + other.w + 4 && other.x < box.x + box.w + 4 && box.y < other.y + other.h + 4 && other.y < box.y + box.h + 4)) visible = false;
        else boxes.push(box);
      }
      label.el.classList.toggle("is-hidden", !visible);
      label.el.classList.toggle("is-major", !!label.major);
    });
    // At close zoom, the labels are still deliberately collision-filtered, but
    // a denser set is permitted. This second pass only affects the visibility
    // threshold; the same boxes keep the rendering deterministic.
    if (scale >= GEO_ALL_ZOOM) {
      ranked.forEach((label) => {
        if (!label.el || !label.px || !label.el.classList.contains("is-hidden")) return;
        const box = { x: label.px.x - label.labelPx / 2, y: label.px.y - LABEL_LINE, w: label.labelPx, h: LABEL_LINE };
        if (label.px.x > -100 && label.px.x < m.width + 100 && label.px.y > -80 && label.px.y < m.height + 80
          && !boxes.some((other) => box.x < other.x + other.w + 4 && other.x < box.x + box.w + 4 && box.y < other.y + other.h + 4 && other.y < box.y + box.h + 4)) {
          boxes.push(box);
          label.el.classList.remove("is-hidden");
        }
      });
    }
    return boxes;
  }

  function layoutLabels(m, seedBoxes = []) {
    const boxes = seedBoxes;
    const targetId = inspectorTargetId();
    const ranked = state.nodes.slice().sort((a, b) => priority(b) - priority(a));
    ranked.forEach((node) => {
      if (!node.labelEl) return;
      const onScreen = node.px.x > -80 && node.px.x < m.width + 80 && node.px.y > -60 && node.px.y < m.height + 60;
      const nodePriority = priority(node);
      // The geographic layer is the map's primary language. Entity names are
      // interaction aids: reveal them on selection/hover, then progressively
      // at closer zooms instead of turning a regional surface into a text wall.
      const threshold = node.type === "quest" ? 1.25 : LABEL_ZOOM;
      let visible = onScreen && (nodePriority >= 4 || state.transform.scale >= threshold);
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
        // Explicitly selected/hovered nodes stay readable even over a place
        // name; ordinary labels yield to geographic labels and earlier pins.
        if (nodePriority < 4 && boxes.some((other) => box.x < other.x + other.w + 2 && other.x < box.x + box.w + 2 && box.y < other.y + other.h + 2 && other.y < box.y + box.h + 2)) visible = false;
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

  function mapFloorChoice(event) {
    const m = metrics();
    if (!m || !state.floorHitAreas.length) return null;
    const canvas = {
      x: (((event.clientX - m.originX) - m.ox) / m.k - state.transform.x) / state.transform.scale,
      y: (((event.clientY - m.originY) - m.oy) / m.k - state.transform.y) / state.transform.scale,
    };
    const hits = state.floorHitAreas.filter((row) => (
      canvas.x >= row.x && canvas.x <= row.x + row.w
      && canvas.y >= row.y && canvas.y <= row.y + row.h
    ));
    if (!hits.length) return null;
    const levelId = hits.some((row) => row.levelId === state.selected)
      ? state.selected
      : [...new Set(hits.map((row) => row.levelId))].sort()[0];
    const hitIds = new Set(hits.filter((row) => row.levelId === levelId).map((row) => row.id));
    const layers = orderedMapLayers((state.map?.mapLayers || []).filter((row) => hitIds.has(String(row.id))));
    if (!layers.length) return null;
    const choices = [{ id: "", label: t("mapFloorNone") }, ...layers.map((layer) => ({
      id: String(layer.id),
      label: `${mapLayerLabel(layer)}${mapLayerRange(layer) ? ` · ${mapLayerRange(layer)}` : ""}`,
    }))];
    const selectedId = [...state.mapLayers].find((id) => hitIds.has(String(id))) || "";
    const index = Math.max(0, choices.findIndex((row) => row.id === selectedId));
    return { choices, index, m };
  }

  function hideMapFloorTip() {
    const tip = root()?.querySelector(".mr-floor-tip");
    if (tip) tip.hidden = true;
    mapEl()?.classList.remove("has-floor-choice");
  }

  function previewMapFloors(event) {
    if (state.dragging?.moved || event.target.closest(".mr-node, .mr-float, .mr-tools, .mr-entity-tools")) {
      hideMapFloorTip();
      return;
    }
    const choice = mapFloorChoice(event);
    const tip = root()?.querySelector(".mr-floor-tip");
    if (!choice || !tip) {
      hideMapFloorTip();
      return;
    }
    const current = choice.choices[choice.index];
    tip.innerHTML = `<strong>${esc(`${t("mapFloorHover")} · ${choice.choices.length}`)}</strong>`
      + `<span>${esc(`${t("mapFloorCurrent")}: ${current.label}`)}</span>`
      + `<span>${esc(t("mapFloorClickCycle"))}</span>`;
    tip.hidden = false;
    mapEl()?.classList.add("has-floor-choice");
    const width = tip.offsetWidth || 210;
    const height = tip.offsetHeight || 62;
    const x = event.clientX - choice.m.originX;
    const y = event.clientY - choice.m.originY;
    tip.style.left = `${clamp(x + 14, 6, Math.max(6, choice.m.width - width - 6))}px`;
    tip.style.top = `${clamp(y - height - 12, 6, Math.max(6, choice.m.height - height - 6))}px`;
  }

  function cycleMapFloor(event) {
    if (performance.now() < state.suppressClickUntil) return;
    if (event.target.closest(".mr-node, .mr-float, .mr-tools, button, input, select, a")) return;
    const choice = mapFloorChoice(event);
    if (!choice) return;
    const next = choice.choices[(choice.index + 1) % choice.choices.length];
    state.mapLayers = next.id ? new Set([next.id]) : new Set();
    event.preventDefault();
    render();
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
      head.innerHTML = `<p class="mr-role">${esc(t("inspector"))}</p><h2>${esc(mapTitle(state.map || {}))}</h2>`;
      body.innerHTML = `<p class="mr-placeholder">${esc(t("inspectorHint"))}</p>${mapFilesHtml()}<div class="mr-viewer-slot"></div>`;
      bindFilePicks(body);
      renderViewer();
      return;
    }

    head.innerHTML = `<p class="mr-role" style="color:${esc(kindColor(node))}">${esc(nodeRole(node))}${node.kind ? ` / ${esc(kindLabel(node.kind))}` : ""}</p>
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

  // ---------------------------------------------------------------- selection

  function setPreview(id) {
    if (state.previewId === id) return;
    state.previewId = id;
    layoutLabelsSafely();
    syncTip();
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
    if (m) layoutLabels(m, layoutLocationLabels(m));
  }

  async function pointPixels(src) {
    if (!pointPixelCache.has(src)) pointPixelCache.set(src, (async () => {
      const response = await fetch(src);
      if (!response.ok) throw new Error(`point filter asset ${response.status}: ${src}`);
      const bitmap = await createImageBitmap(await response.blob());
      const canvas = document.createElement("canvas");
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      context.drawImage(bitmap, 0, 0);
      bitmap.close?.();
      return context.getImageData(0, 0, canvas.width, canvas.height);
    })());
    return pointPixelCache.get(src);
  }

  async function pointSamples(src) {
    if (!pointSampleCache.has(src)) pointSampleCache.set(src, (async () => {
      const response = await fetch(src);
      if (!response.ok) throw new Error(`point sample asset ${response.status}: ${src}`);
      const buffer = await response.arrayBuffer();
      const view = new DataView(buffer);
      if (buffer.byteLength < 16
          || view.getUint8(0) !== 77 || view.getUint8(1) !== 82
          || view.getUint8(2) !== 80 || view.getUint8(3) !== 83
          || view.getUint16(4, true) !== 1 || view.getUint16(6, true) !== 12
          || (buffer.byteLength - 16) % 12 !== 0) {
        throw new Error(`invalid point sample asset: ${src}`);
      }
      return {
        view,
        width: view.getUint32(8, true),
        height: view.getUint32(12, true),
        recordCount: (buffer.byteLength - 16) / 12,
      };
    })());
    return pointSampleCache.get(src);
  }

  function revokePointFilter(image) {
    const url = image?.dataset?.pointFilterUrl;
    if (url) URL.revokeObjectURL(url);
    if (image?.dataset) delete image.dataset.pointFilterUrl;
  }

  async function filterPointImage(image, token) {
    const sourceUrl = image.dataset.pointSrc;
    const maskUrl = image.dataset.pointHeightMask;
    const sampleUrl = image.dataset.pointSamples;
    const range = state.pointHeightRange;
    if (!sourceUrl || (!maskUrl && !sampleUrl) || !range) return;
    const fullRange = range.low <= range.min && range.high >= range.max;
    if (fullRange) {
      revokePointFilter(image);
      image.setAttribute("href", sourceUrl);
      return;
    }
    try {
      if (sampleUrl) {
        const samples = await pointSamples(sampleUrl);
        if (token !== pointFilterToken || !image.isConnected) return;
        const pixels = new Uint8ClampedArray(samples.width * samples.height * 4);
        for (let cursor = 16; cursor < samples.view.byteLength; cursor += 12) {
          const height = samples.view.getFloat32(cursor + 4, true);
          if (height < range.low || height > range.high) continue;
          const offset = samples.view.getUint32(cursor, true) * 4;
          if (offset + 3 >= pixels.length) continue;
          pixels[offset] = samples.view.getUint8(cursor + 8);
          pixels[offset + 1] = samples.view.getUint8(cursor + 9);
          pixels[offset + 2] = samples.view.getUint8(cursor + 10);
          pixels[offset + 3] = samples.view.getUint8(cursor + 11);
        }
        const canvas = document.createElement("canvas");
        canvas.width = samples.width;
        canvas.height = samples.height;
        canvas.getContext("2d").putImageData(new ImageData(pixels, samples.width, samples.height), 0, 0);
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
        if (!blob || token !== pointFilterToken || !image.isConnected) return;
        const url = URL.createObjectURL(blob);
        revokePointFilter(image);
        image.dataset.pointFilterUrl = url;
        image.setAttribute("href", url);
        return;
      }
      const [source, mask] = await Promise.all([pointPixels(sourceUrl), pointPixels(maskUrl)]);
      if (token !== pointFilterToken || !image.isConnected || source.width !== mask.width || source.height !== mask.height) return;
      const maskMin = Number(image.dataset.pointHeightMin);
      const maskMax = Number(image.dataset.pointHeightMax);
      const maskSpan = Math.max(maskMax - maskMin, 1e-9);
      const pixels = new Uint8ClampedArray(source.data);
      for (let offset = 0; offset < pixels.length; offset += 4) {
        if (!mask.data[offset + 3]) {
          pixels[offset + 3] = 0;
          continue;
        }
        const encoded = mask.data[offset] * 256 + mask.data[offset + 1];
        const height = maskMin + encoded / 65535 * maskSpan;
        if (height < range.low || height > range.high) pixels[offset + 3] = 0;
      }
      const canvas = document.createElement("canvas");
      canvas.width = source.width;
      canvas.height = source.height;
      canvas.getContext("2d").putImageData(new ImageData(pixels, source.width, source.height), 0, 0);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
      if (!blob || token !== pointFilterToken || !image.isConnected) return;
      const url = URL.createObjectURL(blob);
      revokePointFilter(image);
      image.dataset.pointFilterUrl = url;
      image.setAttribute("href", url);
    } catch (error) {
      console.warn("Map point-height filter failed", error);
    }
  }

  function applyPointHeightFilter() {
    const token = ++pointFilterToken;
    root()?.querySelectorAll(".mr-bg-point-cloud[data-point-height-mask], .mr-bg-point-cloud[data-point-samples]").forEach((image) => {
      filterPointImage(image, token);
    });
  }

  function queuePointHeightFilter() {
    if (pointFilterTimer) clearTimeout(pointFilterTimer);
    pointFilterTimer = setTimeout(() => {
      pointFilterTimer = 0;
      applyPointHeightFilter();
    }, 40);
  }

  // ---------------------------------------------------------------- rendering

  function render() {
    const host = root();
    const data = state.map;
    if (!host || !data) return;
    host.querySelectorAll(".mr-bg-point-cloud[data-point-filter-url]").forEach(revokePointFilter);

    // A level pools every mission that plays in it, so isolating one mission is
    // the difference between a readable route and a wall of markers. A node with
    // no mission of its own is level art: it is only shown when no mission is
    // selected, because claiming it for the selected mission would be a lie.
    const inMission = (row) => !state.mission || (row.missions || []).includes(state.mission);
    const inMapLayer = (row) => {
      const ids = row.mapLayerIds || [];
      return ids.length ? ids.some((id) => state.mapLayers.has(id)) : true;
    };
    const missionSelected = !!state.mission;
    const questRows = ((state.showQuests || missionSelected) ? (data.questPoints || []) : [])
      .filter((row) => inMission(row) && (missionSelected || inMapLayer(row)))
      .map((row) => ({ ...row, type: "quest", position: finitePosition(row.position) }))
      .filter((row) => row.position);
    const markerRows = (data.markers || [])
      .filter((row) => inMission(row))
      .filter((row) => missionSelected || (state.kinds.has(row.kind) && state.subKinds.has(row.subKind || row.kind)))
      .filter((row) => missionSelected || inMapLayer(row))
      .filter((row) => missionSelected || !state.storyOnly || Number(row.storyCount || 0) > 0)
      .map((row) => ({ ...row, type: "marker", position: finitePosition(row.position) }))
      .filter((row) => row.position);

    // Start/end pins are derived strictly from each mission's authored
    // questOrder.  They describe the endpoints of the published tracking
    // route, not an inferred spawn, trigger, or runtime completion position.
    const endpointRoles = new Map();
    const endpointGroups = new Map();
    for (const row of questRows) {
      const key = `${row.levelId}:${row.missionId || ""}`;
      if (!endpointGroups.has(key)) endpointGroups.set(key, []);
      endpointGroups.get(key).push(row);
    }
    for (const rows of endpointGroups.values()) {
      const ordered = [...rows].sort((a, b) => {
        const left = Number.isFinite(Number(a.questOrder)) ? Number(a.questOrder) : Number.MAX_SAFE_INTEGER;
        const right = Number.isFinite(Number(b.questOrder)) ? Number(b.questOrder) : Number.MAX_SAFE_INTEGER;
        return left - right || String(a.questId).localeCompare(String(b.questId));
      });
      if (!ordered.length) continue;
      const keyOf = (row) => `${row.levelId}:${row.missionId || ""}:${row.questId}`;
      endpointRoles.set(keyOf(ordered[0]), "start");
      endpointRoles.set(keyOf(ordered.at(-1)), ordered.length === 1 ? "start" : "end");
    }

    // The background is the game's own map-screen composite when the level
    // publishes one, else the HLOD preview. Whichever source is chosen also
    // supplies the declared world bounds, so the markers and the picture are
    // always projected by the same rectangle.
    const minimapBg = data.minimap || {};
    const hlodBg = data.renderBackground || {};
    const backgroundSource = minimapBg.src && minimapBg.worldBounds
      ? minimapBg
      : (hlodBg.src && hlodBg.worldBounds ? hlodBg : null);
    // The loaded background rectangles are the current projection contract.
    // Their union keeps stitched siblings in one coordinate space without a
    // second copy of region bounds in the index or map payload.
    const backgroundBounds = [...state.backgrounds, ...state.modelBackgrounds]
      .map((row) => row.worldBounds)
      .filter((bounds) => ["minX", "maxX", "minZ", "maxZ"].every((key) => Number.isFinite(Number(bounds?.[key]))));
    const declaredBounds = backgroundBounds.length
      ? {
        minX: Math.min(...backgroundBounds.map((bounds) => Number(bounds.minX))),
        maxX: Math.max(...backgroundBounds.map((bounds) => Number(bounds.maxX))),
        minZ: Math.min(...backgroundBounds.map((bounds) => Number(bounds.minZ))),
        maxZ: Math.max(...backgroundBounds.map((bounds) => Number(bounds.maxZ))),
      }
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
    // `needInverseXZ` is a quarter-turn axis conversion, not an image flip.
    // The in-game Dijiang reference has its prow/bridge on the left and the
    // base area on the right. Raw bridge (X~0,Z~-71) and base-area
    // (X~-1,Z~120) therefore prove X'=Z and Z'=-X around the map centre.
    const oriented = (p, row) => {
      if (!row?.mapInverted) return p;
      const centreX = (minX + maxX) / 2;
      const centreZ = (minZ + maxZ) / 2;
      return { ...p, x: centreX + (p.z - centreZ), z: centreZ - (p.x - centreX) };
    };
    const plot = (p) => ({ x: viewX + (p.x - minX) * fitScale, y: viewY + viewH - (p.z - minZ) * fitScale });

    state.nodes = [
      // A map now carries the quests of every mission that plays in the level,
      // and a region surface merges several levels, so both the mission and the
      // level are part of the node id: quest ids are only unique inside their
      // own mission and marker identities stay scoped to their level.
      ...questRows.map((row) => ({
        ...row,
        id: `q:${row.levelId}:${row.missionId || ""}:${row.questId}`,
        endpointRole: endpointRoles.get(`${row.levelId}:${row.missionId || ""}:${row.questId}`) || "",
        plot: plot(oriented(row.position, row)),
        px: { x: 0, y: 0 },
      })),
      ...markerRows.map((row) => ({ ...row, id: `m:${row.levelId}:${row.identity}`, plot: plot(oriented(row.position, row)), px: { x: 0, y: 0 } })),
    ].map((node) => {
      const labelText = nodeDisplayLabel(node);
      return {
        ...node,
        labelText,
        labelPx: labelWidth(labelText),
        labelOffset: node.type === "quest" ? { x: 10, y: 18 } : { x: 11, y: -10 },
      };
    });

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
      const points = ordered.map((row) => plot(oriented(row.position, row))).map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
      return `<polyline class="mr-route" points="${points}" vector-effect="non-scaling-stroke"><title>${esc(`${t("questRoute")}: ${mission}`)}</title></polyline>`;
    }).join("");
    // The selected zone's bounds define the fitted rectangle; every sibling
    // zone of the region projects through the same world -> canvas mapping, so
    // each zone's map screen lands exactly where the terrain it depicts is
    // plotted. Zone screens overlap by design (each one shows its neighbours),
    // which is what makes the surfaces tile into one seamless region: the
    // neighbours are drawn first, the selected zone on top, and no outline is
    // drawn between them.
    const visibleBackgrounds = state.showMinimap
      ? state.backgrounds
      : state.backgrounds.filter((bg) => bg.sourceKind !== "minimap");
    const visibleFloorBackgrounds = state.showMinimap
      ? state.layerBackgrounds.filter((bg) => state.mapLayers.has(bg.id))
      : [];
    const bgRects = [...visibleBackgrounds, ...visibleFloorBackgrounds]
      .filter((bg) => ["minX", "maxX", "minZ", "maxZ"].every((key) => Number.isFinite(Number(bg.worldBounds?.[key]))))
      .map((bg) => {
        const x = viewX + (Number(bg.worldBounds.minX) - minX) * fitScale;
        // `plot()` maps +Z toward the top: screenY = maxZ - worldZ.
        // A background rectangle must use that exact projection for its top
        // edge. Using `bg.maxZ - minZ` mirrored every sibling screen north /
        // south while markers still used `maxZ - z`, which made both seams
        // and task coordinates visibly disagree.
        const y = viewY + (maxZ - Number(bg.worldBounds.maxZ)) * fitScale;
        return {
          bg,
          x,
          y,
          w: (Number(bg.worldBounds.maxX) - Number(bg.worldBounds.minX)) * fitScale,
          h: (Number(bg.worldBounds.maxZ) - Number(bg.worldBounds.minZ)) * fitScale,
        };
      });
    const modelRects = state.modelBackgrounds
      .filter((bg) => ["minX", "maxX", "minZ", "maxZ"].every((key) => Number.isFinite(Number(bg.worldBounds?.[key]))))
      .map((bg) => ({
        bg,
        x: viewX + (Number(bg.worldBounds.minX) - minX) * fitScale,
        y: viewY + (maxZ - Number(bg.worldBounds.maxZ)) * fitScale,
        w: (Number(bg.worldBounds.maxX) - Number(bg.worldBounds.minX)) * fitScale,
        h: (Number(bg.worldBounds.maxZ) - Number(bg.worldBounds.minZ)) * fitScale,
      }));
    const layerInfo = new Map((data.mapLayers || []).map((row) => [String(row.id), row]));
    state.floorHitAreas = (state.showMinimap ? state.layerBackgrounds : [])
      .filter((bg) => ["minX", "maxX", "minZ", "maxZ"].every((key) => Number.isFinite(Number(bg.worldBounds?.[key]))))
      .map((bg) => ({
        id: String(bg.id),
        levelId: bg.levelId,
        layer: layerInfo.get(String(bg.id)) || bg,
        x: viewX + (Number(bg.worldBounds.minX) - minX) * fitScale,
        y: viewY + (maxZ - Number(bg.worldBounds.maxZ)) * fitScale,
        w: (Number(bg.worldBounds.maxX) - Number(bg.worldBounds.minX)) * fitScale,
        h: (Number(bg.worldBounds.maxZ) - Number(bg.worldBounds.minZ)) * fitScale,
      }));
    const selectedBackground = bgRects.find(({ bg }) => bg.levelId === state.selected)
      || modelRects.find(({ bg }) => bg.levelId === state.selected);
    state.selectedMapBox = selectedBackground
      ? { x: selectedBackground.x, y: selectedBackground.y, w: selectedBackground.w, h: selectedBackground.h }
      : null;
    // Minimap PNGs already carry the game's alpha mask.  Applying an extra
    // .9 opacity here made every opaque pixel blend with the dark canvas and
    // made overlapping sibling screens visibly darker than their neighbours.
    // Keep the source alpha intact so the region surface has one consistent
    // tone; transparency still exposes the map background below.
    const modelImages = ({ bg, x, y, w, h }, overMinimap = false, part = "all") => {
        const orientation = bg.mapInverted
          ? ` transform="rotate(90 ${(x + w / 2).toFixed(2)} ${(y + h / 2).toFixed(2)})"`
          : "";
        const geometry = `x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${w.toFixed(2)}" height="${h.toFixed(2)}"${orientation}`;
        const underlay = state.modelLayers.has("elevation") && bg.elevationUnderlay?.src
          ? `<image class="mr-bg-image mr-bg-elevation" href="data/map_recovery/${esc(bg.elevationUnderlay.src)}?v=${MAP_ASSET_VERSION}" ${geometry}><title>${esc(`${bg.levelId} elevation`)}</title></image>`
          : "";
        const pointSrc = bg.pointCloudOverlay?.src || "";
        const mainIsPointCloud = bg.status === "inferred_registry_point_cloud_preview";
        const surface = state.modelLayers.has("surface") && !mainIsPointCloud
          ? `<image class="mr-bg-image mr-bg-model-surface${overMinimap ? " is-overlay" : ""}" href="data/map_recovery/${esc(bg.src)}?v=${MAP_ASSET_VERSION}" ${geometry}><title>${esc(bg.levelId)}</title></image>`
          : "";
        const water = state.modelLayers.has("water") && bg.waterOverlay?.src
          ? `<image class="mr-bg-image mr-bg-water" href="data/map_recovery/${esc(bg.waterOverlay.src)}?v=${MAP_ASSET_VERSION}" ${geometry}><title>${esc(`${bg.levelId} water`)}</title></image>`
          : "";
        const visiblePointSrc = pointSrc;
        const pointUrl = visiblePointSrc ? `data/map_recovery/${visiblePointSrc}?v=${MAP_ASSET_VERSION}` : "";
        const heightMask = bg.pointCloudOverlay?.heightMask;
        const sampleSet = bg.pointCloudOverlay?.sampleSet;
        const heightMaskUrl = heightMask?.src ? `data/map_recovery/${heightMask.src}?v=${MAP_ASSET_VERSION}` : "";
        const sampleUrl = sampleSet?.src ? `data/map_recovery/${sampleSet.src}?v=${MAP_ASSET_VERSION}` : "";
        const pointRange = sampleSet?.elevationRange || heightMask?.elevationRange;
        const heightAttrs = (heightMaskUrl || sampleUrl) && pointRange
          ? ` data-point-src="${esc(pointUrl)}"${heightMaskUrl ? ` data-point-height-mask="${esc(heightMaskUrl)}"` : ""}${sampleUrl ? ` data-point-samples="${esc(sampleUrl)}"` : ""} data-point-height-min="${Number(pointRange.min)}" data-point-height-max="${Number(pointRange.max)}"`
          : "";
        const points = state.modelLayers.has("points") && visiblePointSrc
          ? `<image class="mr-bg-image mr-bg-point-cloud" href="${esc(pointUrl)}"${heightAttrs} ${geometry} style="opacity:${state.pointCloudOpacity.toFixed(2)}"><title>${esc(`${bg.levelId} point cloud`)}</title></image>`
          : "";
        if (part === "base") return `${underlay}${surface}`;
        if (part === "water") return water;
        if (part === "points") return points;
        return `${underlay}${surface}${water}${points}`;
      };
    const modelBaseLevels = new Set(state.backgrounds.filter((bg) => bg.sourceKind === "model").map((bg) => bg.levelId));
    const modelOverlayRects = [
      ...bgRects.filter(({ bg }) => bg.sourceKind === "model").map((rect) => ({ ...rect, overMinimap: false })),
      ...modelRects.filter(({ bg }) => !modelBaseLevels.has(bg.levelId)).map((rect) => ({ ...rect, overMinimap: true })),
    ];
    const minimapImages = bgRects
      .filter(({ bg }) => bg.sourceKind !== "model")
      .map(({ bg, x, y, w, h }) => {
        const geometry = `x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${w.toFixed(2)}" height="${h.toFixed(2)}"`;
        return `<image class="mr-bg-image" href="data/map_recovery/${esc(bg.src)}?v=${MAP_ASSET_VERSION}" ${geometry}><title>${esc(bg.levelId)}</title></image>`;
      })
      .join("");
    const modelBaseImages = modelOverlayRects.map((rect) => modelImages(rect, rect.overMinimap, "base")).join("");
    const waterImages = modelOverlayRects.map((rect) => modelImages(rect, rect.overMinimap, "water")).join("");
    // Regional minimaps overlap by design. Rendering each semi-transparent
    // water PNG independently made overlap counts visible as darker blocks.
    // SVG filters a group offscreen before compositing it, so normalize every
    // covered output pixel to the one authored overlay alpha and draw the
    // union exactly once regardless of how many sibling screens cover it.
    const waterUnion = waterImages
      ? `<defs><filter id="mr-water-union-alpha" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncA type="discrete" tableValues="0 0.6588235"/></feComponentTransfer></filter></defs><g class="mr-bg-water-union" filter="url(#mr-water-union-alpha)">${waterImages}</g>`
      : "";
    const pointImages = modelOverlayRects.map((rect) => modelImages(rect, rect.overMinimap, "points")).join("");
    const backgroundImages = `${minimapImages}${modelBaseImages}${waterUnion}${pointImages}`;
    // Level display names describe gameplay scenes, not geographic ownership
    // of the whole (overlapping) map-screen rectangle. Location labels come
    // from the map UI's own staticElements text anchors instead. Keep them as
    // a separate, low-density layer: geographic names are always preferable
    // to entity ids when the reader is looking at a regional surface.
    // Each sibling config's `_tips_1` is its primary place anchor. Treating
    // every `regiontoast` row as major made the region overview a wall of 70+
    // equally loud labels.
    const locationMajor = (row) => /_tips_1$/i.test(String(row.textId || ""));
    state.locationLabels = (data.locationLabels || []).map((row, index) => {
      const position = finitePosition(row.position);
      if (!position || !row.text) return null;
      const p = plot(oriented(position, row));
      const labelText = String(row.text).trim();
      return {
        ...row,
        id: String(row.id || `${row.textId || "location"}:${index}`),
        position,
        plot: p,
        labelText,
        labelPx: labelWidth(labelText),
        major: locationMajor(row),
        px: { x: 0, y: 0 },
        el: null,
      };
    }).filter(Boolean);
    const locationLabelSvg = state.locationLabels.map((row, index) => `<text class="mr-location-label${row.major ? " is-major" : ""}" data-location-label="${index}" x="0" y="4" aria-label="${esc(row.labelText)}"><title>${esc(row.labelText)}</title>${esc(row.labelText)}</text>`).join("");
    state.contentBox = state.nodes.length || bgRects.length || modelRects.length
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
        modelRects.forEach(({ x, y, w, h }) => {
          minXc = Math.min(minXc, x);
          minYc = Math.min(minYc, y);
          maxXc = Math.max(maxXc, x + w);
          maxYc = Math.max(maxYc, y + h);
        });
        return { minX: minXc, minY: minYc, maxX: maxXc, maxY: maxYc };
      })()
      : null;
    state.lastNodeScale = null;
    state.lastLocationScale = null;

    const nodeSvg = state.nodes.map((node) => {
      const quest = node.type === "quest";
      // A node reads as a story node when dialog is actually pinned to it, not
      // when its structural kind happens to be `story`: on a full map most
      // recovered dialog sits on NPC proxies, triggers and narrative anchors.
      const hasStory = quest ? false : (node.storyCount || 0) > 0;
      const endpoint = quest && node.endpointRole;
      const endpointLabel = endpoint ? t(endpoint === "start" ? "missionStart" : "missionEnd") : "";
      const shape = endpoint === "start"
        ? `<circle class="mr-endpoint-halo" r="11"/><circle class="mr-shape" r="7"/><path class="mr-endpoint-glyph" d="M-2.5,-4 L4,0 L-2.5,4 Z"/>`
        : endpoint === "end"
          ? `<circle class="mr-endpoint-halo" r="11"/><rect class="mr-shape" x="-6" y="-6" width="12" height="12" transform="rotate(45)"/><path class="mr-endpoint-glyph" d="M-3,-3 H3 V3 H-3 Z"/>`
          : quest
            ? `<rect class="mr-shape" x="-5.5" y="-5.5" width="11" height="11"/>`
        : `<circle class="mr-shape" r="${hasStory || node.kind === "story" ? 9 : 6}" fill="${esc(kindColor(node))}"/>`;
      return `<g class="mr-node${quest ? " mr-quest" : " mr-marker"}${endpoint ? ` is-mission-${endpoint}` : ""}${hasStory || node.kind === "story" ? " is-story" : ""}" data-node="${esc(node.id)}" data-kind="${esc(node.kind || "quest")}" role="button" tabindex="0" aria-pressed="${node.id === state.selectedId ? "true" : "false"}" aria-label="${esc(accessibleName(node))}">`
        + `<circle class="mr-hit" r="15" fill="none" pointer-events="all"/>${shape}`
        + (endpoint ? `<text class="mr-endpoint-label" x="0" y="-17">${esc(endpointLabel)}</text>` : "")
        + `<text class="mr-label" x="${node.labelOffset.x}" y="${node.labelOffset.y}">${esc(node.labelText)}</text></g>`;
    }).join("");

    const layerControls = layerTreeHtml(data);
    const modelLayerControls = modelLayerControlsHtml();
    const hasPointCloudUnderlay = state.modelBackgrounds.some((bg) => bg.pointCloudOverlay?.src);
    const pointCloudOpacity = Math.round(state.pointCloudOpacity * 100);
    const opacityControl = hasPointCloudUnderlay
      ? `<label class="mr-opacity-dock"><span>${esc(t("pointCloudOpacity"))}</span><input type="range" min="0" max="100" step="1" value="${pointCloudOpacity}" data-map-point-opacity><output>${pointCloudOpacity}%</output></label>`
      : "";
    const height = state.pointHeightRange;
    const heightSpan = height ? Math.max(height.max - height.min, 1e-9) : 1;
    const heightLowPercent = height ? (height.low - height.min) / heightSpan * 100 : 0;
    const heightHighPercent = height ? (height.high - height.min) / heightSpan * 100 : 100;
    const heightControl = height
      ? `<div class="mr-height-dock"><span>${esc(t("pointCloudHeight"))}</span><div class="mr-height-range" style="--height-low:${heightLowPercent.toFixed(2)}%;--height-high:${heightHighPercent.toFixed(2)}%"><input type="range" min="${height.min}" max="${height.max}" step="any" value="${height.low}" aria-label="${esc(t("pointCloudHeightMin"))}" data-map-point-height="low"><input type="range" min="${height.min}" max="${height.max}" step="any" value="${height.high}" aria-label="${esc(t("pointCloudHeightMax"))}" data-map-point-height="high"></div><output aria-label="${esc(t("pointCloudHeightRange"))}">${esc(`${formatHeight(height.low)} – ${formatHeight(height.high)}`)}</output></div>`
      : "";
    const missionControls = missionSelectHtml(data);
    const mapMetrics = `<p class="mr-coords">${esc(data.coordinateSystem)}</p>
      <section class="mr-metrics">
        ${state.nodes.length === (data.questPoints || []).length + (data.markers || []).length
          ? ""
          : `<span class="mr-metric-active"><b>${state.nodes.length}</b>${esc(t("shownNodes"))}</span>`}
        <span><b>${(data.questPoints || []).length}</b>${esc(t("questPoints"))}</span>
        <span><b>${(data.markers || []).length}</b>${esc(t("entityMarkers"))}</span>
        <span><b>${(data.markers || []).filter((row) => (row.storyCount || 0) > 0).length}</b>${esc(t("storyNodes"))}</span>
        <span><b>${data.pinnedFileCount ?? 0}</b>${esc(t("pinnedFiles"))}</span>
        <span><b>${data.npcCoverage?.exactProxyCount ?? 0}</b>${esc(t("exactNpcs"))}</span>
      </section>`;
    const objectFilters = `<section class="mr-object-filters" aria-label="${esc(t("objectFilters"))}">
      <h2>${esc(t("objectFilters"))}</h2>
      <div class="mr-layer-actions">
        <button type="button" data-map-layers="all">${esc(t("layersAll"))}</button>
        <button type="button" data-map-layers="none">${esc(t("layersNone"))}</button>
        <button type="button" data-map-layers="story">${esc(t("layersStory"))}</button>
      </div>
      <p class="mr-note mr-layer-selection-hint">${esc(t("layerSelectionHint"))}</p>
      <div class="mr-layers">${(data.questPoints || []).length ? `<label class="mr-layer" style="--mr-chip:${QUEST_COLOR}"><input type="checkbox" data-map-quests ${state.showQuests ? "checked" : ""}><span class="mr-swatch" style="background:${QUEST_COLOR}"></span>${esc(kindLabel("quest"))}<span class="mr-layer-count">${data.questPoints.length}</span></label>` : ""}${layerControls}</div>
      ${modelLayerControls}${opacityControl}${heightControl}<p class="mr-floor-help">${esc(t("help"))}</p>
    </section>`;
    const unlinked = (data.unlinkedMissionFiles || []).filter((path) => String(path || "").trim()).sort((a, b) => a.localeCompare(b));
    const unresolvedSlots = data.unresolvedTriggerSlots || { count: 0 };
    const unplaced = data.unplacedStories || { count: 0 };
    const bg = data.renderBackground || {};
    const regionLevelCount = state.index?.maps?.filter((row) => regionKey(row.id) === regionKey(state.selected)).length
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
    const sceneHint = scene.positionStatus === "unplaced"
      ? t("scene3dUnplacedHint")
      : (scene.positionStatus === "exact_streaming_matrix" ? t("streamingSceneHint") : t("scene3dHint"));
    const sceneBlock = sceneMeshes.length
      ? `<details><summary>${esc(`${t("scene3d")} (${scene.meshCount || sceneMeshes.length})`)}</summary><p class="mr-note">${esc(sceneHint)}</p><ul class="mr-file-list">${sceneFiles}</ul></details>`
      : `<p class="mr-note"><code>${esc(scene.status || "obj_cluster_files_unavailable")}</code> ${esc(t("scene3dUnavailable"))}</p>`;

    host.innerHTML = `<div class="mr-map${hasPointCloudUnderlay ? " has-point-opacity" : ""}" tabindex="0" role="group" aria-label="${esc(`${mapTitle(data)} - ${t("mapSurface")}`)}">
        <svg class="mr-canvas" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="group" aria-label="${esc(mapTitle(data))}"><rect width="100%" height="100%" class="mr-map-bg"/><g class="mr-viewport">${backgroundImages}<g class="mr-location-labels">${locationLabelSvg}</g><g class="mr-routes">${routeSvg}</g><g class="mr-nodes">${nodeSvg}</g></g></svg>
        <div class="mr-tip" hidden></div>
        <div class="mr-floor-tip" hidden></div>
        <div class="mr-tools" role="toolbar" aria-label="${esc(t("mapSurface"))}">
          <div class="mr-tool-group" role="group" aria-label="${esc(t("zoomLevel"))}">
            <button type="button" data-map-zoom="out" aria-label="${esc(t("zoomOut"))}" title="${esc(t("zoomOut"))}">-</button>
            <button type="button" data-map-zoom="in" aria-label="${esc(t("zoomIn"))}" title="${esc(t("zoomIn"))}">+</button>
            <button type="button" data-map-fit aria-label="${esc(t("fitLong"))}" title="${esc(t("fitLong"))}">${esc(t("fit"))}</button>
            <button type="button" data-map-reset aria-label="${esc(t("resetLong"))}" title="${esc(t("resetLong"))}">${esc(t("reset"))}</button>
            <span class="mr-zoom-readout" role="status" aria-live="polite"></span>
          </div>
          <span class="mr-tool-sep" aria-hidden="true"></span>
          <div class="mr-tool-group mr-entity-tools" role="group" aria-label="${esc(t("entitySize"))}">
            <span>${esc(t("entitySize"))}</span>
            <button type="button" data-map-entity-size="out" aria-label="${esc(t("entityZoomOut"))}" title="${esc(t("entityZoomOut"))}">−</button>
            <button type="button" data-map-entity-size="in" aria-label="${esc(t("entityZoomIn"))}" title="${esc(t("entityZoomIn"))}">+</button>
            <button type="button" data-map-entity-size="reset" aria-label="${esc(t("entityReset"))}" title="${esc(t("entityReset"))}">${esc(t("reset"))}</button>
            <span class="mr-entity-readout" role="status" aria-live="polite"></span>
          </div>
          <span class="mr-tool-sep" aria-hidden="true"></span>
          <span class="mr-axis">+Z -> X -></span>
        </div>
        ${state.nodes.length || bgRects.length || modelRects.length || state.locationLabels.length ? "" : `<p class="mr-empty">${esc(t("noNodes"))}</p>`}
      </div>
      <aside class="mr-float mr-float--controls" data-panel="controls" aria-label="${esc(t("controls"))}">
        <div class="mr-float-head" data-panel-drag>
          <h2 class="mr-float-title">${esc(t("controls"))}</h2>
          <button type="button" class="mr-float-toggle" data-panel-toggle aria-label="${esc(t("collapse"))}">–</button>
        </div>
        <div class="mr-float-body">
          <div class="mr-browser-tree">
            <nav class="mr-map-column" aria-label="${esc(t("title"))}">${mapTreeHtml()}</nav>
            <section class="mr-task-column" aria-label="${esc(t("mission"))}"><h2>${esc(t("mission"))}</h2>${missionControls}<div class="mr-task-map-status">${mapMetrics}</div></section>
            ${objectFilters}
          </div>
          <div class="mr-technical-evidence" hidden>
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
          </details></div>
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
    renderInspector();
    applyTransform();
  }

  // ---------------------------------------------------------------- events

  function bindMap(host) {
    host.querySelector("#map-recovery-select")?.addEventListener("change", (event) => {
      void switchMap(event.target.value);
    });
    host.querySelectorAll("[data-map-id]").forEach((button) => button.addEventListener("click", () => {
      void switchMap(button.dataset.mapId);
    }));
    host.querySelectorAll("[data-map-mission]").forEach((button) => button.addEventListener("click", () => {
      state.mission = button.dataset.mapMission || "";
      // A selected mission always exposes its complete footprint, regardless
      // of the ordinary marker and floor filters.
      state.pendingFit = true;
      state.pendingFitTarget = "nodes";
      render();
    }));
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
    host.querySelector("[data-map-point-opacity]")?.addEventListener("input", (event) => {
      state.pointCloudOpacity = clamp(Number(event.currentTarget.value) / 100, 0, 1);
      host.querySelectorAll(".mr-bg-point-cloud").forEach((image) => {
        image.style.opacity = state.pointCloudOpacity.toFixed(2);
      });
      const output = event.currentTarget.parentElement?.querySelector("output");
      if (output) output.textContent = `${Math.round(state.pointCloudOpacity * 100)}%`;
    });
    host.querySelectorAll("[data-map-point-height]").forEach((input) => input.addEventListener("input", (event) => {
      const range = state.pointHeightRange;
      if (!range) return;
      const value = clamp(Number(event.currentTarget.value), range.min, range.max);
      if (event.currentTarget.dataset.mapPointHeight === "low") range.low = Math.min(value, range.high);
      else range.high = Math.max(value, range.low);
      const dock = event.currentTarget.closest(".mr-height-dock");
      const lowInput = dock?.querySelector('[data-map-point-height="low"]');
      const highInput = dock?.querySelector('[data-map-point-height="high"]');
      if (lowInput) lowInput.value = String(range.low);
      if (highInput) highInput.value = String(range.high);
      const span = Math.max(range.max - range.min, 1e-9);
      const track = dock?.querySelector(".mr-height-range");
      track?.style.setProperty("--height-low", `${(range.low - range.min) / span * 100}%`);
      track?.style.setProperty("--height-high", `${(range.high - range.min) / span * 100}%`);
      const output = dock?.querySelector("output");
      if (output) output.textContent = `${formatHeight(range.low)} – ${formatHeight(range.high)}`;
      queuePointHeightFilter();
    }));
    host.querySelectorAll("[data-map-model-layer]").forEach((input) => input.addEventListener("change", () => {
      state.modelLayers = new Set([...host.querySelectorAll("[data-map-model-layer]:checked")].map((row) => row.dataset.mapModelLayer));
      render();
    }));
    host.querySelector("[data-map-minimap]")?.addEventListener("change", (event) => {
      state.showMinimap = event.currentTarget.checked;
      render();
    });
    host.querySelectorAll("[data-map-layers]").forEach((button) => button.addEventListener("click", () => {
      const mode = button.dataset.mapLayers;
      const kinds = state.map?.facets?.kinds || {};
      const keep = ([kind, info]) => (mode === "all" ? true : mode === "story" ? info.storyCount > 0 : false);
      state.storyOnly = mode === "story";
      state.showQuests = mode === "all";
      state.kinds = new Set(Object.entries(kinds).filter(keep).map(([kind]) => kind));
      state.subKinds = allSubKinds(state.map);
      render();
    }));
    host.querySelector("[data-map-quests]")?.addEventListener("change", (event) => {
      state.showQuests = event.currentTarget.checked;
      render();
    });

    const map = host.querySelector(".mr-map");
    if (!map) return;
    host.querySelectorAll("[data-map-zoom]").forEach((button) => button.addEventListener("click", () => {
      animateTo(zoomed(button.dataset.mapZoom === "in" ? 1.35 : 1 / 1.35, null));
    }));
    host.querySelectorAll("[data-map-entity-size]").forEach((button) => button.addEventListener("click", () => {
      const mode = button.dataset.mapEntitySize;
      state.entityScale = mode === "reset"
        ? 1
        : clamp(state.entityScale * (mode === "in" ? ENTITY_SCALE_STEP : 1 / ENTITY_SCALE_STEP), ENTITY_SCALE_MIN, ENTITY_SCALE_MAX);
      state.lastNodeScale = null;
      applyTransform();
    }));
    host.querySelector("[data-map-fit]")?.addEventListener("click", () => animateTo(fitTransform(state.nodes.length ? "nodes" : "map")));
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
    host.querySelectorAll("[data-location-label]").forEach((label) => {
      const index = Number(label.dataset.locationLabel);
      if (Number.isInteger(index) && state.locationLabels[index]) state.locationLabels[index].el = label;
    });

    map.addEventListener("pointerdown", beginPan);
    map.addEventListener("selectstart", (event) => event.preventDefault());
    map.addEventListener("pointermove", movePan);
    map.addEventListener("pointermove", previewMapFloors);
    map.addEventListener("pointerup", endPan);
    map.addEventListener("pointercancel", endPan);
    map.addEventListener("pointerleave", hideMapFloorTip);
    map.addEventListener("click", cycleMapFloor);
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
    applyPointHeightFilter();
  }

  // The page is one full-bleed map surface; every piece of chrome is a
  // floating panel. Panels drag by their header and collapse onto it, and both
  // states survive render() through panelUi.
  function bindFloatPanels(host) {
    host.querySelectorAll(".mr-float").forEach((panel) => {
      const key = panel.dataset.panel;
      const saved = panelUi.get(key) || {};
      const toggle = panel.querySelector("[data-panel-toggle]");
      const paintToggle = (collapsed) => {
        panel.classList.toggle("is-collapsed", collapsed);
        if (!toggle) return;
        toggle.textContent = collapsed ? "+" : "–";
        toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
        toggle.setAttribute("aria-label", t(collapsed ? "expand" : "collapse"));
        toggle.setAttribute("title", t(collapsed ? "expand" : "collapse"));
      };
      paintToggle(!!saved.collapsed);
      if (Number.isFinite(saved.x) && Number.isFinite(saved.y)) {
        panel.style.left = `${saved.x}px`;
        panel.style.top = `${saved.y}px`;
        panel.style.right = "auto";
        panel.classList.add("is-placed");
      }
      toggle?.addEventListener("click", () => {
        const flags = panelUi.get(key) || {};
        flags.collapsed = !flags.collapsed;
        panelUi.set(key, flags);
        paintToggle(flags.collapsed);
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
    window.getSelection?.()?.removeAllRanges();
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
  // neighbours. The main regional surfaces (map01 / map02) are loaded as a
  // complete set on first open, so opening 武陵城 or 四号谷地 cannot show an
  // isolated island. The two authored blackbox art scenes follow the same
  // contract; unrelated standalone levels remain on-demand.
  const regionKey = (id) => {
    const value = String(id || "");
    const published = (state.index?.maps || []).find((row) => row.id === value)?.regionKey;
    return published || value;
  };
  const stitchOnInitialOpen = (id) => ["map01", "map02", "blackbox01_dg001", "blackbox02_dg001"].includes(regionKey(id));

  async function ensurePayload(row) {
    if (!state.payloads.has(row.id)) {
      state.payloads.set(row.id, await fetchJson(`data/map_recovery/${row.src}`, { cache: "no-store" }));
    }
    return state.payloads.get(row.id);
  }

  function zoneBackground(payload) {
    const minimap = payload.minimap || {};
    const hlod = payload.renderBackground || {};
    return (minimap.src && minimap.worldBounds) ? { ...minimap, sourceKind: "minimap" }
      : (hlod.src && hlod.worldBounds ? { ...hlod, sourceKind: "model" } : null);
  }

  // Merges a whole region's payloads into the shape render() always consumed,
  // with every row tagged by its level so node ids, registry pins and mission
  // filters stay unambiguous across levels.
  function mergeRegion(members, selectedId) {
    const selected = members.find((member) => member.id === selectedId)?.payload;
    if (!selected) return null;
    const kinds = {};
    const missions = {};
    const missionDetails = {};
    const questPoints = [];
    const markers = [];
    const unlinked = new Set();
    const unplaced = [];
    const unplacedReasons = {};
    const unresolved = [];
    const backgrounds = [];
    const modelBackgrounds = [];
    const mapLayers = [];
    const layerBackgrounds = [];
    const locationLabels = new Map();
    let pinnedFileCount = 0;
    let exactProxyCount = 0;
    for (const member of members) {
      const payload = member.payload;
      if (!payload) continue;
      const mapInverted = !!payload.mapConfig?.needInverseXZ;
      for (const row of payload.questPoints || []) questPoints.push({ ...row, levelId: member.id, mapInverted, mapLayerIds: (row.mapLayerIds || []).map((id) => `${member.id}:${id}`) });
      for (const row of payload.markers || []) markers.push({ ...row, levelId: member.id, mapInverted, mapLayerIds: (row.mapLayerIds || []).map((id) => `${member.id}:${id}`) });
      for (const layer of payload.mapConfig?.layers || []) {
        const id = `${member.id}:${layer.id}`;
        const displayName = (payload.mapConfig?.staticElements || [])
          .find((row) => row.textId && row.textId === layer.nameKey)?.text || "";
        mapLayers.push({
          ...layer,
          id,
          levelId: member.id,
          levelName: member.payload.name || member.payload.label || member.id,
          displayName,
        });
        const rendered = (payload.minimap?.layers || []).find((row) => row.id === layer.id);
        if (rendered?.src && rendered.worldBounds) layerBackgrounds.push({ ...rendered, id, levelId: member.id });
      }
      for (const row of payload.mapConfig?.staticElements || []) {
        if (!row?.text || !row.position) continue;
        // The same named place can be present in several overlapping level
        // screens. Keep one stable authored anchor instead of drawing stacked
        // duplicates that look like conflicting region assignments.
        const key = `${row.text}:${Math.round(Number(row.position.x))}:${Math.round(Number(row.position.z))}`;
        if (!locationLabels.has(key)) locationLabels.set(key, { ...row, levelId: member.id, mapInverted });
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
      for (const [missionId, detail] of Object.entries(payload.missionDetails || {})) {
        const entry = (missionDetails[missionId] ||= { files: new Set(), name: "" });
        if (detail.name && !entry.name) entry.name = detail.name;
        for (const path of detail.files || []) if (path) entry.files.add(path);
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
      if (background) backgrounds.push({
        levelId: member.id,
        src: background.src,
        worldBounds: background.worldBounds,
        elevationUnderlay: background.elevationUnderlay || null,
        pointCloudOverlay: background.pointCloudOverlay || null,
        waterOverlay: background.waterOverlay || null,
        sourceKind: background.sourceKind,
        status: background.status || "",
        mapInverted,
      });
      const model = payload.renderBackground || {};
      if (model.src && model.worldBounds) modelBackgrounds.push({
        levelId: member.id,
        src: model.src,
        worldBounds: model.worldBounds,
        elevationUnderlay: model.elevationUnderlay || null,
        pointCloudOverlay: model.pointCloudOverlay || null,
        waterOverlay: model.waterOverlay || null,
        status: model.status || "",
        mapInverted,
      });
    }
    // These are overlapping map screens, not disjoint rectangles owned by
    // the selected gameplay level. A stable order prevents selection changes
    // from making whole geographic areas appear to exchange positions.
    backgrounds.sort((a, b) => a.levelId.localeCompare(b.levelId));
    // Variant maps can publish the same cropped shared-scene image and bounds.
    // Drawing that alpha image repeatedly would darken it without adding any
    // geometry, so identical slices are represented once in the stitched set.
    state.backgrounds = [...new Map(backgrounds.map((row) => [
      `${row.src}|${["minX", "maxX", "minZ", "maxZ"].map((key) => Number(row.worldBounds?.[key])).join(",")}`,
      row,
    ])).values()];
    state.modelBackgrounds = [...new Map(modelBackgrounds.map((row) => [
      `${row.src}|${["minX", "maxX", "minZ", "maxZ"].map((key) => Number(row.worldBounds?.[key])).join(",")}`,
      row,
    ])).values()];
    state.layerBackgrounds = layerBackgrounds;
    return {
      ...selected,
      mapLayers,
      locationLabels: [...locationLabels.values()],
      questPoints,
      markers,
      facets: { kinds, missions },
      missionDetails: Object.fromEntries(Object.entries(missionDetails).map(([missionId, detail]) => [missionId, {
        ...(missions[missionId] || { markers: 0, questPoints: 0, stories: 0 }),
        name: detail.name || "",
        files: [...detail.files].sort(),
      }])),
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

  async function loadMap(id, { includeRegion = stitchOnInitialOpen(id) } = {}) {
    const row = (state.index?.maps || []).find((item) => item.id === id) || state.index?.maps?.[0];
    if (!row) return false;
    const key = regionKey(row.id);
    // Only explicitly published region keys are stitched. Similar prefixes can
    // denote separate states or decks with identical bounds.
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
    // Start as a geographic map. A region can contain thousands of entities
    // and quest points; the explicit layer controls opt those overlays in.
    // Start with recovered geography only. Streaming instances are now drawn
    // as static geometry in the background; their optional evidence nodes no
    // longer need to cover that render with hundreds of location dots.
    state.kinds = new Set();
    state.subKinds = allSubKinds(state.map);
    state.showQuests = false;
    // Multi-floor maps must not begin as a stack of every transparent tier.
    // Start on one authored floor and let the reader opt into comparisons.
    // Prefer the selected sub-map's first authored tier even though region
    // members are merged in stable id order for rendering and caching.
    const renderedLayerIds = new Set(state.layerBackgrounds.map((row) => String(row.id)));
    const initialMapLayer = state.map.mapLayers?.find((row) => row.levelId === state.selected && renderedLayerIds.has(String(row.id)))
      || state.map.mapLayers?.find((row) => renderedLayerIds.has(String(row.id)));
    state.mapLayers = initialMapLayer
      ? new Set([String(initialMapLayer.id)])
      : new Set();
    // Preserve the in-game map as the readable base when it exists, and show
    // the colored point scan as the least-obscuring recovered model overlay.
    // Geometry-only scenes begin with all three aligned model layers visible.
    const hasMinimapBase = state.backgrounds.some((background) => background.sourceKind === "minimap");
    state.showMinimap = true;
    state.modelLayers = state.modelBackgrounds.length
      ? new Set(hasMinimapBase ? ["points"] : ["elevation", "surface", "water", "points"])
      : new Set();
    resetPointHeightRange();
    state.storyOnly = false;
    state.mission = state.map.defaultMission || "";
    state.transform = { x: 0, y: 0, scale: 1 };
    state.pendingFit = true;
    state.pendingFitTarget = "map";
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
      const initialId = state.selected || state.index.defaultMap;
      const loaded = await loadMap(initialId, { includeRegion: stitchOnInitialOpen(initialId) });
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
