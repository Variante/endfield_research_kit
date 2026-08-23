(() => {
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const PANE_STORAGE_KEY = "webui_characters_splitter_width";
  const FILTER_HEIGHT_STORAGE_KEY = "webui_filter_splitter_height_characters";
  const FILTER_PANEL_STORAGE_KEY = "webui_characters_filters_collapsed";
  const MERGE_OVERRIDE_PATH = "overrides/character_merges.json";
  const MERGE_OVERRIDE_SCHEMA = "characterMerges.v1";
  const NAME_OVERRIDE_PATH = "overrides/character_name_overrides.json";
  const NAME_OVERRIDE_SCHEMA = "characterNameOverrides.v1";
  const state = {
    container: null,
    data: null,
    language: "",
    query: "",
    kind: "all",
    source: "all",
    evidenceType: "all",
    identitiesRange: [0, Infinity],
    evidenceGroupsRange: [0, Infinity],
    assetCountRange: [0, Infinity],
    specialFilters: new Set(),
    selectedId: "",
    loadToken: 0,
    filterPanel: null,
    mergeOverrides: null,
    flaggedIds: new Set(),
    nameOverrides: null,
    showDebug: false,
    sortKey: "default",
    sortDirection: "asc",
  };

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
  const currentLanguage = () => String(document.querySelector("#language")?.value || "CN").toUpperCase();
  const zh = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").toLowerCase().startsWith("zh");
  const ui = (en, cn) => zh() ? cn : en;
  const sourceLabel = (source) => ({
    TextTable: "TextTable npcName_*",
    CharacterTable: "CharacterTable",
    NpcTable: "NpcTable",
    SNSChatTable: "SNSChatTable",
    "Story actor registry": ui("Story sources", "剧情角色来源"),
    "Exported assets": ui("Exported assets", "导出资源"),
  }[source] || source);
  const EVIDENCE_TYPE_FILTERS = ["major_npc_asset", "npc_animal_asset", "dlg_npc_asset", "icon_npc_asset", "sns_npc_asset", "actor_asset", "npc_asset"];
  const evidenceTypeLabel = (type) => ({
    actor_asset: ui("Story actor", "剧情角色"),
    major_npc_asset: ui("Major NPC", "重要 NPC"),
    dlg_npc_asset: ui("Dialogue NPC", "对话 NPC"),
    icon_npc_asset: ui("Icon NPC", "图标 NPC"),
    sns_npc_asset: ui("SNS NPC", "社交 NPC"),
    npc_animal_asset: ui("Animal NPC", "动物 NPC"),
    npc_asset: ui("Asset NPC", "资源 NPC"),
  }[type] || type);
  const SPECIAL_FILTERS = ["no_i18n", "merged", "needs_merge", "name_overridden"];
  const SORT_KEYS = ["default", "alphabet", "identities", "evidence_groups", "assets", "names", "sources"];
  const DEFAULT_SORT_DIRECTIONS = {
    default: "asc",
    alphabet: "asc",
    identities: "desc",
    evidence_groups: "desc",
    assets: "desc",
    names: "desc",
    sources: "desc",
  };
  const sortKeyLabel = (key) => ({
    default: ui("Default order", "原有默认排序"),
    alphabet: ui("Alphabetical", "字母顺序"),
    identities: ui("Identities", "身份数量"),
    evidence_groups: ui("Evidence groups", "证据组数量"),
    assets: ui("Assets", "资源数量"),
    names: ui("Observed names", "已发现名称数量"),
    sources: ui("Evidence sources", "证据来源数量"),
  }[key] || key);
  const specialFilterLabel = (key) => ({
    no_i18n: ui("No official name", "无官方译名"),
    merged: ui("Manually merged", "已合并"),
    needs_merge: ui("Flagged: needs merge", "已标记：待合并"),
    name_overridden: ui("Name overridden", "已覆盖名称"),
  }[key] || key);
  // A group has no official name when every observed name came from the
  // "Exported asset identifier" fallback (i.e. no CharacterTable/NpcTable/
  // TextTable/SNSChatTable/Story actor registry entry ever named it).
  function hasOfficialName(row) {
    return (row.names || []).some((name) => name.source !== "Exported asset identifier");
  }
  const IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]);
  function isImagePath(path) {
    const name = String(path || "").split(/[?#]/)[0];
    const dotIdx = name.lastIndexOf(".");
    if (dotIdx < 0) return false;
    return IMAGE_EXTENSIONS.has(name.slice(dotIdx).toLowerCase());
  }
  // Same fallback used by the Updates feature: the full sourceRoots map lives
  // in the ~150MB assets/index.json, so this mirrors its convert_by_type
  // layout instead of loading that file just to preview a thumbnail.
  const ASSET_SOURCE_ROOTS = {
    StreamingAssets: "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type",
    "StreamingAssets-maps": "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps",
    "StreamingAssets-structured": "export_full/structured/StreamingAssets",
    Persistent: "export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type",
    "Persistent-maps": "export_full/recovered/AnimeStudio-cli/Persistent/maps",
    "Persistent-structured": "export_full/structured/Persistent",
    Audio: "export_full/structured/Audio",
  };
  function assetImageHref(rel) {
    const exportFullHref = window.WebUI?.exportFullHref;
    return exportFullHref ? exportFullHref(rel, ASSET_SOURCE_ROOTS, "export_full") : "";
  }
  const kindLabel = (kind) => ({
    character: ui("Playable character", "可玩角色"),
    npc: "NPC",
    actor: ui("Story actor", "剧情角色"),
    asset_npc: ui("Asset NPC", "资源 NPC"),
  }[kind] || kind);

  function dataPath(language) {
    return `data/lang/${encodeURIComponent(language)}/characters/index.json`;
  }

  function normalizedName(value) {
    return String(value || "").trim().normalize("NFKC").toLocaleLowerCase();
  }

  function isUnknownName(value) {
    return /^\?+$/.test(String(value || "").trim().normalize("NFKC"));
  }

  function knownNames(row) {
    return [...new Set((row.names || [])
      .map((name) => String(name.text || "").trim())
      .filter((name) => name && !isUnknownName(name))
      .map(normalizedName))]
      .sort();
  }

  // A stable, language-independent id for an auto-grouped identity: the
  // smallest of its constituent record ids (table/asset keys, e.g.
  // "chr_0017_yvonne" or "aglina"). Those ids come from table keys and
  // English filename markers, not localized text, so — unlike the display
  // name used below to detect which records belong together — this id stays
  // the same across every language build, and is safe to persist in manual
  // merge overrides.
  function canonicalGroupId(records) {
    const ids = (records || []).map((r) => normalizedName(r.id)).filter(Boolean).sort();
    return ids[0] || "";
  }

  function groupedRecords() {
    const byName = new Map();
    for (const row of state.data?.records || []) {
      const primaryName = String(row.primaryName || row.id || "").trim();
      const nameKey = normalizedName(primaryName) || normalizedName(row.id);
      let group = byName.get(nameKey);
      if (!group) {
        group = {
          primaryName,
          knownNames: [],
          records: [],
          kinds: [],
          sourceTypes: [],
          aliases: [],
          names: [],
        };
        byName.set(nameKey, group);
      }
      const foundNames = knownNames(row);
      for (const fn of foundNames) {
        if (!group.knownNames.includes(fn)) group.knownNames.push(fn);
      }
      group.records.push(row);
      if (row.kind && !group.kinds.includes(row.kind)) group.kinds.push(row.kind);
      for (const source of row.sourceTypes || []) {
        if (!group.sourceTypes.includes(source)) group.sourceTypes.push(source);
      }
      for (const alias of [row.id, ...(row.aliases || [])]) {
        if (alias && !group.aliases.includes(alias)) group.aliases.push(alias);
      }
      for (const name of row.names || []) {
        const identity = [name.text, name.source, name.language, name.key].join("\u0000");
        if (!group.names.some((item) => item._identity === identity)) {
          group.names.push({ ...name, _identity: identity });
        }
      }
    }

    // Re-key by the stable canonical id now that each group's full member
    // list is known — this id (not the localized nameKey used above just to
    // detect co-membership) is what gets exposed and persisted.
    const groups = new Map();
    for (const group of byName.values()) {
      const id = canonicalGroupId(group.records) || normalizedName(group.primaryName);
      groups.set(id, { ...group, id });
    }

    const merges = state.mergeOverrides || {};
    if (!Object.keys(merges).length) {
      return applyNameOverrides([...groups.values()].map(finalizeGroup));
    }

    // Fold merged-away groups into their resolved root last, so a root group
    // (one that isn't itself a merge source) always seeds the merged primaryName.
    const order = [...groups.keys()].sort((a, b) => {
      const aRoot = resolveMergeTarget(a, merges) === a ? 0 : 1;
      const bRoot = resolveMergeTarget(b, merges) === b ? 0 : 1;
      return aRoot - bRoot;
    });
    const merged = new Map();
    for (const id of order) {
      const group = groups.get(id);
      const targetId = resolveMergeTarget(id, merges);
      let target = merged.get(targetId);
      if (!target) {
        target = { id: targetId, primaryName: group.primaryName, knownNames: [], records: [], kinds: [], sourceTypes: [], aliases: [], names: [], mergedIds: [] };
        merged.set(targetId, target);
      }
      if (id !== targetId) {
        target.mergedIds.push(id);
        target.aliases.push(group.primaryName, id);
      }
      target.knownNames.push(...group.knownNames);
      target.records.push(...group.records);
      target.kinds.push(...group.kinds);
      target.sourceTypes.push(...group.sourceTypes);
      target.aliases.push(...group.aliases);
      target.names.push(...group.names);
    }
    return applyNameOverrides([...merged.values()].map(finalizeGroup));
  }

  function finalizeGroup(group) {
    return {
      ...group,
      knownNames: [...new Set(group.knownNames)].sort(),
      kinds: [...new Set(group.kinds)].sort(),
      sourceTypes: [...new Set(group.sourceTypes)].sort(),
      aliases: [...new Set(group.aliases)].sort(),
      mergedIds: [...new Set(group.mergedIds || [])].sort(),
      names: group.names.map(({ _identity, ...name }) => name),
    };
  }

  // Applies a manual display-name override on top of an already-merged group:
  // keyed by the same canonical id space character_merges.json targets use, so
  // an override survives regrouping regardless of merge state. The detected
  // name is preserved as `detectedName` and folded into aliases so it stays
  // searchable even after being overridden.
  function applyNameOverrides(rows) {
    const overrides = state.nameOverrides || {};
    return rows.map((row) => {
      const override = String(overrides[row.id] || "").trim();
      if (!override || override === row.primaryName) return row;
      return {
        ...row,
        primaryName: override,
        detectedName: row.primaryName,
        nameOverridden: true,
        aliases: [...new Set([...row.aliases, row.primaryName])].sort(),
      };
    });
  }

  function resolveMergeTarget(id, merges) {
    let current = id;
    const seen = new Set();
    while (merges[current] && merges[current] !== current && !seen.has(current)) {
      seen.add(current);
      current = merges[current];
    }
    return current;
  }

  function allSources() {
    return [...new Set(groupedRecords().flatMap((row) => row.sourceTypes || []))].sort();
  }

  function allEvidenceTypes() {
    const types = new Set();
    for (const row of groupedRecords()) {
      for (const record of row.records) {
        for (const ev of (record.evidence || [])) {
          if (ev.type && EVIDENCE_TYPE_FILTERS.includes(ev.type)) types.add(ev.type);
        }
      }
    }
    return EVIDENCE_TYPE_FILTERS.filter((t) => types.has(t));
  }

  function rowStats(row) {
    let evidenceGroups = 0;
    let assetPathSamples = 0;
    let assetCount = 0;
    for (const record of row.records || []) {
      const evidence = record.evidence || [];
      evidenceGroups += evidence.length;
      for (const item of evidence) {
        assetPathSamples += (item.paths || []).length;
        // `count` is the true number of matching exported files (paths[] is
        // just a capped sample of it); table-row evidence has no `count`.
        assetCount += Number(item.count) || 0;
      }
    }
    return { identities: (row.records || []).length, evidenceGroups, assetPathSamples, assetCount };
  }

  function sortValue(row, key) {
    if (key === "identities") return rowStats(row).identities;
    if (key === "evidence_groups") return rowStats(row).evidenceGroups;
    if (key === "assets") return rowStats(row).assetCount;
    if (key === "names") return (row.names || []).length;
    if (key === "sources") return (row.sourceTypes || []).length;
    return 0;
  }

  function compareCharacterNames(a, b) {
    const aName = String(a.primaryName || a.id || "");
    const bName = String(b.primaryName || b.id || "");
    const locale = ({ CN: "zh-Hans-CN", EN: "en", JP: "ja", KR: "ko" })[state.language];
    return aName.localeCompare(bName, locale, { numeric: true, sensitivity: "base" })
      || String(a.id || "").localeCompare(String(b.id || ""), locale, { numeric: true, sensitivity: "base" });
  }

  function sortRecords(rows) {
    const direction = state.sortDirection === "desc" ? -1 : 1;
    if (state.sortKey === "default") return direction === 1 ? rows : [...rows].reverse();
    const ranked = rows.map((row, index) => ({
      row,
      index,
      value: sortValue(row, state.sortKey),
    }));
    ranked.sort((a, b) => {
      if (state.sortKey === "alphabet") {
        return direction * compareCharacterNames(a.row, b.row) || a.index - b.index;
      }
      return direction * (a.value - b.value)
        || compareCharacterNames(a.row, b.row)
        || a.index - b.index;
    });
    return ranked.map((entry) => entry.row);
  }

  // Renders a dual-handle range slider into `containerSel` for `state[stateKey]`,
  // a [min, max] pair where max === Infinity means "no upper bound". The slider's
  // own max is the largest observed value across `records`; dragging the upper
  // handle all the way to that end is what represents "infinity", so the bound
  // widens automatically as new data raises the ceiling.
  function renderCountRangeFilter(containerSel, stateKey, metricKey, records, labelText) {
    const container = state.container?.querySelector(containerSel);
    if (!container) return;
    const dataMax = records.reduce((best, row) => Math.max(best, rowStats(row)[metricKey]), 0);
    const safeMax = Math.max(1, dataMax);
    const range = state[stateKey];
    const lo = Math.min(Math.max(0, range[0]), safeMax);
    const hi = Number.isFinite(range[1]) ? Math.min(Math.max(lo, range[1]), safeMax) : safeMax;
    const loPct = (lo / safeMax) * 100;
    const hiPct = (hi / safeMax) * 100;
    const infinityLabel = ui("∞", "∞");
    const hiText = hi >= safeMax ? infinityLabel : hi.toLocaleString();
    container.innerHTML = `
      <label>${esc(labelText)}</label>
      <div class="characters-range-value">${lo.toLocaleString()} – ${hiText}</div>
      <div class="characters-range-slider" style="--characters-range-lo:${loPct}%;--characters-range-hi:${hiPct}%">
        <div class="characters-range-track"></div>
        <div class="characters-range-fill"></div>
        <input type="range" class="characters-range-input characters-range-min" min="0" max="${safeMax}" step="1" value="${lo}" aria-label="${esc(labelText)} ${esc(ui("minimum", "最小值"))}">
        <input type="range" class="characters-range-input characters-range-max" min="0" max="${safeMax}" step="1" value="${hi}" aria-label="${esc(labelText)} ${esc(ui("maximum", "最大值"))}">
      </div>`;
    const sliderEl = container.querySelector(".characters-range-slider");
    const minInput = container.querySelector(".characters-range-min");
    const maxInput = container.querySelector(".characters-range-max");
    const valueEl = container.querySelector(".characters-range-value");
    let renderScheduled = false;
    const scheduleListRender = () => {
      if (renderScheduled) return;
      renderScheduled = true;
      requestAnimationFrame(() => {
        renderScheduled = false;
        renderList();
      });
    };
    const sync = (moved) => {
      let loVal = Number(minInput.value);
      let hiVal = Number(maxInput.value);
      if (loVal > hiVal) {
        if (moved === "min") { hiVal = loVal; maxInput.value = String(hiVal); }
        else { loVal = hiVal; minInput.value = String(loVal); }
      }
      sliderEl.style.setProperty("--characters-range-lo", `${(loVal / safeMax) * 100}%`);
      sliderEl.style.setProperty("--characters-range-hi", `${(hiVal / safeMax) * 100}%`);
      valueEl.textContent = `${loVal.toLocaleString()} – ${hiVal >= safeMax ? infinityLabel : hiVal.toLocaleString()}`;
      state[stateKey] = [loVal, hiVal >= safeMax ? Infinity : hiVal];
      scheduleListRender();
    };
    minInput.addEventListener("input", () => sync("min"));
    maxInput.addEventListener("input", () => sync("max"));
  }

  // Each entry drives one range slider in the "Evidence counts" filter group:
  // stateKey holds the [min, max] pair (max === Infinity means unbounded),
  // metricKey looks the current value up on rowStats(row).
  const COUNT_RANGE_FILTERS = [
    { stateKey: "identitiesRange", metricKey: "identities" },
    { stateKey: "evidenceGroupsRange", metricKey: "evidenceGroups" },
    { stateKey: "assetCountRange", metricKey: "assetCount" },
  ];

  // A range filter counts as "active" once it's been narrowed off its
  // full-span default — shared by the list filter and the active-count badge
  // so the two never disagree about which ranges are actually constraining.
  function activeCountRangeFilters() {
    return COUNT_RANGE_FILTERS.filter(({ stateKey }) => {
      const range = state[stateKey];
      return range[0] > 0 || Number.isFinite(range[1]);
    });
  }

  function filteredRecords() {
    const tokens = window.WebUI.parseQuery(state.query);
    const activeCountFilters = activeCountRangeFilters();
    const rows = groupedRecords().filter((row) => {
      if (state.kind !== "all" && !(row.kinds || []).includes(state.kind)) return false;
      if (state.source !== "all" && !(row.sourceTypes || []).includes(state.source)) return false;
      if (state.evidenceType !== "all") {
        const hasType = row.records.some((r) => (r.evidence || []).some((e) => e.type === state.evidenceType));
        if (!hasType) return false;
      }
      if (activeCountFilters.length) {
        const stats = rowStats(row);
        for (const { stateKey, metricKey } of activeCountFilters) {
          const [min, max] = state[stateKey];
          const value = stats[metricKey];
          if (value < min) return false;
          if (Number.isFinite(max) && value > max) return false;
        }
      }
      if (state.specialFilters.has("no_i18n") && hasOfficialName(row)) return false;
      if (state.specialFilters.has("merged") && !(row.mergedIds || []).length) return false;
      if (state.specialFilters.has("needs_merge") && !state.flaggedIds.has(row.id)) return false;
      if (state.specialFilters.has("name_overridden") && !row.nameOverridden) return false;
      if (!tokens.length) return true;
      const haystack = [
        row.id,
        row.primaryName,
        ...(row.aliases || []),
        ...(row.names || []).map((item) => `${item.text} ${item.key}`),
        ...(row.records || []).flatMap((identity) => [
          identity.id,
          ...(identity.evidence || []).flatMap((item) => [item.key, ...(item.paths || [])]),
        ]),
      ].join(" ");
      return window.WebUI.queryMatches(haystack, tokens);
    });
    return sortRecords(rows);
  }

  function isMobileLayout() {
    return !!window.matchMedia?.(MOBILE_LAYOUT_QUERY).matches;
  }

  function parsePixels(value, fallback = 0) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function renderFilterChips() {
    const buildChips = window.WebUI?.filters?.buildChips;
    if (!buildChips) return;
    const records = groupedRecords();
    const kindCounts = new Map();
    const sourceCounts = new Map();
    for (const row of records) {
      for (const kind of row.kinds || []) {
        kindCounts.set(kind, (kindCounts.get(kind) || 0) + 1);
      }
      for (const source of row.sourceTypes || []) {
        sourceCounts.set(source, (sourceCounts.get(source) || 0) + 1);
      }
    }
    buildChips("#characters-kind-filter", ["character", "npc", "actor", "asset_npc"], {
      active: state.kind === "all" ? "" : state.kind,
      single: true,
      label: (kind) => kindLabel(kind),
      count: kindCounts,
      onToggle: (next) => {
        state.kind = next || "all";
        renderFilterChips();
        renderList();
      },
    });
    buildChips("#characters-source-filter", allSources(), {
      active: state.source === "all" ? "" : state.source,
      single: true,
      label: (source) => sourceLabel(source),
      count: sourceCounts,
      onToggle: (next) => {
        state.source = next || "all";
        renderFilterChips();
        renderList();
      },
    });
    const evidenceTypeCounts = new Map();
    for (const row of records) {
      const rowTypes = new Set();
      for (const record of row.records) {
        for (const ev of (record.evidence || [])) {
          if (ev.type && EVIDENCE_TYPE_FILTERS.includes(ev.type)) rowTypes.add(ev.type);
        }
      }
      for (const t of rowTypes) {
        evidenceTypeCounts.set(t, (evidenceTypeCounts.get(t) || 0) + 1);
      }
    }
    buildChips("#characters-evidence-type-filter", allEvidenceTypes(), {
      active: state.evidenceType === "all" ? "" : state.evidenceType,
      single: true,
      label: (type) => evidenceTypeLabel(type),
      count: evidenceTypeCounts,
      onToggle: (next) => {
        state.evidenceType = next || "all";
        renderFilterChips();
        renderList();
      },
    });
    renderCountRangeFilter("#characters-identities-range", "identitiesRange", "identities", records, ui("Identities", "身份数"));
    renderCountRangeFilter("#characters-evidence-range", "evidenceGroupsRange", "evidenceGroups", records, ui("Evidence groups", "证据组数"));
    renderCountRangeFilter("#characters-asset-count-range", "assetCountRange", "assetCount", records, ui("Assets", "资源数量"));
    const specialCounts = new Map([
      ["no_i18n", records.filter((row) => !hasOfficialName(row)).length],
      ["merged", records.filter((row) => (row.mergedIds || []).length).length],
      ["needs_merge", records.filter((row) => state.flaggedIds.has(row.id)).length],
      ["name_overridden", records.filter((row) => row.nameOverridden).length],
    ]);
    buildChips("#characters-special-filter", SPECIAL_FILTERS, {
      active: state.specialFilters,
      label: (key) => specialFilterLabel(key),
      count: specialCounts,
      onToggle: () => {
        renderFilterChips();
        renderList();
      },
    });
  }

  function bindFilterSections() {
    state.container?.querySelectorAll(".filter-section-toggle").forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const section = toggle.closest(".filter-section");
        const body = section?.querySelector(".filter-section-body");
        if (!section || !body) return;
        const collapsed = !section.classList.contains("is-collapsed");
        section.classList.toggle("is-collapsed", collapsed);
        body.hidden = collapsed;
        toggle.setAttribute("aria-expanded", String(!collapsed));
        window.dispatchEvent(new Event("resize"));
      });
    });
  }

  function setupFilterPanel() {
    state.filterPanel = window.WebUI?.filters?.createPanelToggle?.({
      panel: "#characters-filter-panel",
      toggle: "#characters-filter-toggle",
      left: "#characters-left",
      storageKey: FILTER_PANEL_STORAGE_KEY,
      isMobile: isMobileLayout,
      labels: (collapsed) => ui(collapsed ? "Show filters" : "Hide filters", collapsed ? "显示筛选" : "隐藏筛选"),
      onChange: () => window.dispatchEvent(new Event("resize")),
    }) || null;
  }

  function setupSplitters() {
    const setupSplitter = window.WebUI?.setupSplitter;
    const utils = window.WebUI?.splitterUtils;
    const shell = state.container;
    const sidebar = shell?.querySelector("#characters-left");
    const paneHandle = shell?.querySelector("#characters-splitter");
    const filterPanel = shell?.querySelector("#characters-filter-panel");
    const filterHandle = shell?.querySelector("#characters-filter-splitter");
    const list = shell?.querySelector("#characters-list");
    if (!setupSplitter || !utils || !shell || !sidebar || !paneHandle || !filterPanel || !filterHandle || !list) return;

    let paneWasMobile = isMobileLayout();
    setupSplitter({
      handle: paneHandle,
      storageKey: PANE_STORAGE_KEY,
      bodyDragClass: "is-resizing-pane",
      client: (event) => event.clientX,
      keys: { decrease: ["ArrowLeft"], increase: ["ArrowRight"] },
      enabled: () => !isMobileLayout(),
      bounds: () => {
        const min = parsePixels(getComputedStyle(sidebar).minWidth, 320);
        const handleWidth = Math.max(1, paneHandle.getBoundingClientRect().width);
        return { min, max: Math.max(min, shell.getBoundingClientRect().width - handleWidth - 320) };
      },
      read: () => parsePixels(sidebar.style.width, sidebar.getBoundingClientRect().width),
      write: (width) => { sidebar.style.width = `${Math.round(width)}px`; },
      clear: () => { sidebar.style.removeProperty("width"); },
      sync: (ctrl) => {
        if (isMobileLayout()) {
          paneWasMobile = true;
          ctrl.clear({ commit: false });
          return;
        }
        if (shell.getBoundingClientRect().width < 48) return;
        let width = parsePixels(sidebar.style.width, sidebar.getBoundingClientRect().width);
        if (paneWasMobile || !sidebar.style.width) {
          const stored = utils.readStoredNumber(PANE_STORAGE_KEY);
          if (stored !== null) width = stored;
        }
        paneWasMobile = false;
        ctrl.set(width, { persist: false, commit: false });
      },
    });

    const minPanelHeight = 56;
    const minListHeight = 160;
    let filterWasMobile = isMobileLayout();
    const naturalFilterHeight = () => {
      const previous = filterPanel.style.height;
      const resized = filterPanel.classList.contains("is-filter-resized");
      filterPanel.style.removeProperty("height");
      filterPanel.classList.remove("is-filter-resized");
      const height = Math.ceil(filterPanel.getBoundingClientRect().height);
      if (previous) filterPanel.style.height = previous;
      filterPanel.classList.toggle("is-filter-resized", resized);
      return Math.max(minPanelHeight, height);
    };
    const filterBounds = () => {
      let fixedHeight = 0;
      for (const child of sidebar.children) {
        if (child === filterPanel || child === list) continue;
        fixedHeight += child.getBoundingClientRect().height;
      }
      const available = Math.max(minPanelHeight, sidebar.getBoundingClientRect().height - fixedHeight - minListHeight);
      return { min: minPanelHeight, max: Math.max(minPanelHeight, Math.min(available, naturalFilterHeight())) };
    };
    const filterController = setupSplitter({
      handle: filterHandle,
      storageKey: FILTER_HEIGHT_STORAGE_KEY,
      bodyDragClass: "is-resizing-filter",
      client: (event) => event.clientY,
      keys: { decrease: ["ArrowUp"], increase: ["ArrowDown"] },
      enabled: () => !isMobileLayout() && !filterPanel.hidden,
      bounds: filterBounds,
      read: () => filterPanel.getBoundingClientRect().height,
      write: (height) => {
        filterPanel.style.height = `${Math.round(height)}px`;
        filterPanel.classList.add("is-filter-resized");
      },
      clear: () => {
        filterPanel.style.removeProperty("height");
        filterPanel.classList.remove("is-filter-resized");
      },
      sync: (ctrl) => {
        if (isMobileLayout() || filterPanel.hidden) {
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
    if (window.MutationObserver && filterController) {
      const observer = new MutationObserver(filterController.requestSync);
      observer.observe(filterPanel, { attributes: true, attributeFilter: ["hidden"] });
      observer.observe(filterPanel, { childList: true, subtree: true });
    }
  }

  function renderShell() {
    if (!state.container) return;
    const groupCount = groupedRecords().length;
    state.container.innerHTML = `
      <aside id="characters-left">
        <header>
          <h1>${ui("Characters & NPCs", "人物")}</h1>
          <div class="characters-count">${groupCount.toLocaleString()} ${ui("names", "个名称")}</div>
          <div class="sidebar-header-actions">
            <button id="characters-filter-toggle" class="panel-toggle" type="button" aria-controls="characters-filter-panel" aria-expanded="true"></button>
            <button id="characters-reset" type="button">${ui("Reset filters", "重置筛选")}</button>
          </div>
        </header>

        <div id="characters-filter-panel" class="filters">
          <section class="filter-section filter-section-basic" data-filter-section="characters-basic" data-fixed-open="1">
            <div class="filter-section-title"><span id="characters-basic-filter-label">${ui("Basic filters", "基础筛选")}</span></div>
            <div class="filter-section-body filter-section-body-stack">
              <div class="filter-control-row">
                <label for="characters-q">${ui("Search", "搜索")}</label>
                <input id="characters-q" type="search" value="${esc(state.query)}" placeholder="${ui("Name, ID, table key, or asset path", "名称、ID、表键或资源路径")}">
              </div>
              <div class="filter-control-row">
                <label for="characters-sort">${ui("Sort", "排序")}</label>
                <div class="characters-sort-controls">
                  <select id="characters-sort">${SORT_KEYS.map((key) => `<option value="${esc(key)}"${state.sortKey === key ? " selected" : ""}>${esc(sortKeyLabel(key))}</option>`).join("")}</select>
                  <select id="characters-sort-direction" aria-label="${esc(ui("Sort direction", "排序方向"))}" title="${esc(ui("Sort direction", "排序方向"))}"${state.sortKey === "default" ? " disabled" : ""}>
                    <option value="asc"${state.sortDirection === "asc" ? " selected" : ""}>${ui("Ascending ↑", "正序 ↑")}</option>
                    <option value="desc"${state.sortDirection === "desc" ? " selected" : ""}>${ui("Descending ↓", "倒序 ↓")}</option>
                  </select>
                </div>
              </div>
            </div>
          </section>
          <section class="filter-section is-collapsed" data-filter-section="characters-kind">
            <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="characters-kind-filter-body">
              <span id="characters-kind-filter-label">${ui("Kind", "类型")}</span>
            </button>
            <div id="characters-kind-filter-body" class="filter-section-body" hidden>
              <div id="characters-kind-filter" class="chips" data-multi="1"></div>
            </div>
          </section>
          <section class="filter-section is-collapsed" data-filter-section="characters-source">
            <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="characters-source-filter-body">
              <span id="characters-source-filter-label">${ui("Evidence source", "证据来源")}</span>
            </button>
            <div id="characters-source-filter-body" class="filter-section-body" hidden>
              <div id="characters-source-filter" class="chips" data-multi="1"></div>
            </div>
          </section>
          <section class="filter-section is-collapsed" data-filter-section="characters-evidence-type">
            <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="characters-evidence-type-filter-body">
              <span id="characters-evidence-type-filter-label">${ui("NPC type", "NPC类型")}</span>
            </button>
            <div id="characters-evidence-type-filter-body" class="filter-section-body" hidden>
              <div id="characters-evidence-type-filter" class="chips" data-multi="1"></div>
            </div>
          </section>
          <section class="filter-section is-collapsed" data-filter-section="characters-counts">
            <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="characters-counts-filter-body">
              <span id="characters-counts-filter-label">${ui("Evidence counts", "证据数量")}</span>
            </button>
            <div id="characters-counts-filter-body" class="filter-section-body filter-section-body-stack" hidden>
              <div class="filter-control-row characters-range-row" id="characters-identities-range"></div>
              <div class="filter-control-row characters-range-row" id="characters-evidence-range"></div>
              <div class="filter-control-row characters-range-row" id="characters-asset-count-range"></div>
            </div>
          </section>
          <section class="filter-section is-collapsed" data-filter-section="characters-special">
            <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="characters-special-filter-body">
              <span id="characters-special-filter-label">${ui("Other", "其他筛选")}</span>
            </button>
            <div id="characters-special-filter-body" class="filter-section-body" hidden>
              <div id="characters-special-filter" class="chips" data-multi="1"></div>
            </div>
          </section>
        </div>
        <div id="characters-filter-splitter" class="filter-splitter" role="separator" aria-label="Resize character filters" aria-orientation="horizontal" tabindex="0"></div>
        <div id="characters-list-meta" class="characters-list-meta"></div>
        <div id="characters-list" class="characters-list"></div>
      </aside>
      <div id="characters-splitter" class="pane-splitter" role="separator" aria-label="Resize character sidebar" aria-orientation="vertical" tabindex="0"></div>
      <main id="characters-detail" class="characters-detail"></main>`;
    state.container.querySelector("#characters-q")?.addEventListener("input", (event) => {
      state.query = event.target.value;
      renderList();
    });
    state.container.querySelector("#characters-sort")?.addEventListener("change", (event) => {
      const nextKey = SORT_KEYS.includes(event.target.value) ? event.target.value : "default";
      state.sortKey = nextKey;
      state.sortDirection = DEFAULT_SORT_DIRECTIONS[nextKey] || "asc";
      const direction = state.container.querySelector("#characters-sort-direction");
      if (direction) {
        direction.value = state.sortDirection;
        direction.disabled = nextKey === "default";
      }
      renderList();
    });
    state.container.querySelector("#characters-sort-direction")?.addEventListener("change", (event) => {
      state.sortDirection = event.target.value === "desc" ? "desc" : "asc";
      renderList();
    });
    state.container.querySelector("#characters-reset")?.addEventListener("click", () => {
      state.query = "";
      state.kind = "all";
      state.source = "all";
      state.evidenceType = "all";
      state.identitiesRange = [0, Infinity];
      state.evidenceGroupsRange = [0, Infinity];
      state.assetCountRange = [0, Infinity];
      state.specialFilters.clear();
      state.sortKey = "default";
      state.sortDirection = "asc";
      const search = state.container.querySelector("#characters-q");
      if (search) search.value = "";
      const sort = state.container.querySelector("#characters-sort");
      if (sort) sort.value = state.sortKey;
      const direction = state.container.querySelector("#characters-sort-direction");
      if (direction) {
        direction.value = state.sortDirection;
        direction.disabled = true;
      }
      renderFilterChips();
      renderList();
    });
    bindFilterSections();
    renderFilterChips();
    setupFilterPanel();
    setupSplitters();
    renderList();
  }

  // Mirrors the (N) active-filter badge the Story and Text Tables pages show
  // on each filter section title — same shared helper, same section keys as
  // the `data-filter-section` attributes in renderShell().
  function syncFilterSectionActiveCounts() {
    window.WebUI?.setFilterSectionActiveCounts?.({
      "characters-basic": (state.query.trim() ? 1 : 0) + (state.sortKey === "default" ? 0 : 1),
      "characters-kind": state.kind === "all" ? 0 : 1,
      "characters-source": state.source === "all" ? 0 : 1,
      "characters-evidence-type": state.evidenceType === "all" ? 0 : 1,
      "characters-counts": activeCountRangeFilters().length,
      "characters-special": state.specialFilters.size,
    });
  }

  function renderList() {
    const list = state.container?.querySelector("#characters-list");
    const meta = state.container?.querySelector("#characters-list-meta");
    if (!list || !meta) return;
    syncFilterSectionActiveCounts();
    const rows = filteredRecords();
    if (state.selectedId && !rows.some((row) => row.id === state.selectedId)) state.selectedId = "";
    if (!state.selectedId && rows.length) state.selectedId = rows[0].id;
    const sortSummary = state.sortKey === "default"
      ? ""
      : ` · ${sortKeyLabel(state.sortKey)} ${state.sortDirection === "desc" ? "↓" : "↑"}`;
    meta.textContent = `${rows.length.toLocaleString()} ${ui("matching names", "个匹配名称")}${sortSummary}`;
    list.innerHTML = rows.map((row) => {
      const evidenceTypes = [...new Set(row.records.flatMap((r) => (r.evidence || []).map((e) => e.type).filter(Boolean)))].sort();
      const typeTags = evidenceTypes.map((t) => `<span class="characters-evidence-type" data-evidence-type="${esc(t)}">${esc(evidenceTypeLabel(t))}</span>`).join("");
      const stats = rowStats(row);
      return `
      <button class="characters-list-row${row.id === state.selectedId ? " is-selected" : ""}" type="button" data-character-id="${esc(row.id)}">
        <span class="characters-row-name">${(row.kinds || []).map((kind) => `<span class="characters-kind">${esc(kindLabel(kind))}</span>`).join(" ")} ${esc(row.primaryName || row.id)}</span>
        ${typeTags ? `<span class="characters-row-sources">${typeTags}</span>` : ""}
        <span class="characters-row-meta">
          <span>${(row.kinds || []).map((kind) => esc(kindLabel(kind))).join(" · ")}</span>
          <code>${stats.identities.toLocaleString()} ${ui(stats.identities === 1 ? "identity" : "identities", "身份")}</code>
          <code>${stats.evidenceGroups.toLocaleString()} ${ui(stats.evidenceGroups === 1 ? "evidence group" : "evidence groups", "组证据")}</code>
          <code title="${esc(`${stats.assetPathSamples.toLocaleString()} ${ui("asset path samples", "资源路径示例")}`)}">${stats.assetCount.toLocaleString()} ${ui(stats.assetCount === 1 ? "asset" : "assets", "个资源")}</code>
        </span>
      </button>`;
    }).join("");
    list.querySelectorAll("[data-character-id]").forEach((button) => {
      button.addEventListener("click", () => {
        state.selectedId = button.dataset.characterId || "";
        list.querySelector(".characters-list-row.is-selected")?.classList.remove("is-selected");
        button.classList.add("is-selected");
        renderDetail();
      });
    });
    renderDetail();
  }

  function evidenceDetails(item) {
    const facts = [];
    if (item.textId !== undefined) facts.push(`text id: ${item.textId}`);
    if (item.nameTextId !== undefined) facts.push(`name text id: ${item.nameTextId}`);
    if (item.dataKey) facts.push(`data key: ${item.dataKey}`);
    if (item.npcGroupId) facts.push(`NPC group: ${item.npcGroupId}`);
    if (item.assetKind) facts.push(`asset kind: ${item.assetKind}`);
    if (item.matchedIdentity) facts.push(`${ui("matched existing identity", "匹配现有身份")}: ${item.matchedIdentity}`);
    if (item.matchRule) facts.push(`${ui("match rule", "匹配规则")}: ${String(item.matchRule).replaceAll("_", " ")}`);
    if (item.count) facts.push(`${Number(item.count).toLocaleString()} ${ui("matching exported files", "个匹配的导出文件")}`);
    return facts;
  }

  function assetPageUrl(rel) {
    const url = new URL(window.location.href);
    url.searchParams.set("asset", String(rel || ""));
    url.hash = "#assets";
    return url.toString();
  }

  function renderAssetPathLink(rel) {
    const url = assetPageUrl(rel);
    const title = esc(ui("Open in Assets", "在资源页打开"));
    if (isImagePath(rel)) {
      const imgPath = assetImageHref(rel);
      return `<a class="characters-asset-link has-preview" href="${esc(url)}" title="${title}">
        <code>${esc(rel)}</code>
        <span class="characters-asset-preview"><img src="${esc(imgPath)}" alt="${esc(rel)}" loading="lazy" onerror="this.closest('.has-preview').classList.remove('has-preview')"/></span>
      </a>`;
    }
    return `<a class="characters-asset-link" href="${esc(url)}" title="${title}"><code>${esc(rel)}</code></a>`;
  }

  function renderEvidence(item) {
    const facts = evidenceDetails(item);
    const paths = Array.isArray(item.paths) ? item.paths : [];
    const evidenceKey = paths.length
      ? `<a class="characters-evidence-key characters-asset-key-link" href="${esc(assetPageUrl(paths[0]))}" title="${esc(ui("Open first matching asset", "打开首个匹配资源"))}"><code>${esc(item.key)}</code></a>`
      : `<code class="characters-evidence-key">${esc(item.key)}</code>`;
    return `
      <article class="characters-evidence">
        <header>
          <span class="characters-evidence-source">${esc(sourceLabel(item.source))}</span>
          ${item.type ? `<span class="characters-evidence-type" title="${esc(String(item.type).replaceAll("_", " "))}">${esc(evidenceTypeLabel(item.type))}</span>` : ""}
        </header>
        ${evidenceKey}
        ${facts.length ? `<ul>${facts.map((fact) => `<li>${esc(fact)}</li>`).join("")}</ul>` : ""}
        ${item.note ? `<p>${esc(item.note)}</p>` : ""}
        ${paths.length ? (item.count < 20 ? `<div class="characters-paths" style="margin-top:.5rem">${paths.map((path) => renderAssetPathLink(path)).join("")}</div>` : `<details><summary>${ui("Asset path samples", "资源路径示例")} (${paths.length}${item.count > paths.length ? ` / ${item.count}` : ""})</summary><div class="characters-paths">${paths.map((path) => renderAssetPathLink(path)).join("")}</div></details>`) : ""}
      </article>`;
  }

  function mergeTargetOptions(excludeId) {
    return groupedRecords()
      .filter((row) => row.id !== excludeId)
      .map((row) => ({ id: row.id, label: row.primaryName || row.id }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }

  function renderDetail() {
    const detail = state.container?.querySelector("#characters-detail");
    if (!detail) return;
    const row = groupedRecords().find((item) => item.id === state.selectedId);
    if (!row) {
      detail.innerHTML = `<div class="characters-empty">${ui("Select an identity to inspect its names and evidence.", "选择一个身份以查看名称与证据。")}</div>`;
      return;
    }
    const stats = rowStats(row);
    const isFlagged = state.flaggedIds.has(row.id);
    detail.innerHTML = `
      <header class="characters-detail-header">
        <div>
          ${(row.kinds || []).map((kind) => `<span class="characters-kind">${esc(kindLabel(kind))}</span>`).join(" ")}
          ${row.nameOverridden ? `<span class="characters-kind characters-name-override-badge">${esc(ui("Renamed", "已改名"))}</span>` : ""}
          <h2>${esc(row.primaryName || row.id)}</h2>
          <code>${stats.identities.toLocaleString()} ${ui(stats.identities === 1 ? "grouped identity" : "grouped identities", "已合并身份")}</code>
        </div>
        <div class="characters-detail-count">
          <div>${stats.evidenceGroups.toLocaleString()} ${ui("evidence groups", "组证据")}</div>
          <div>${stats.assetPathSamples.toLocaleString()} ${ui("asset path samples", "资源路径示例")}</div>
        </div>
      </header>
      <section class="characters-section">
        <h3>${ui("Grouped identities", "已合并的身份")}</h3>
        <div class="characters-identity-list">${row.records.map((identity) => `
          <div class="characters-identity">
            <span class="characters-kind">${esc(kindLabel(identity.kind))}</span>
            <code>${esc(identity.id)}</code>
            <span>${(identity.sourceTypes || []).map((source) => esc(sourceLabel(source))).join(" · ")}</span>
          </div>`).join("")}
        </div>
      </section>
      <section class="characters-section">
        <h3>${ui("Observed names", "已发现的名称")}</h3>
        <div class="characters-name-grid">${(row.names || []).map((name) => `
          <div class="characters-name">
            <strong>${esc(name.text)}</strong>
            <span>${esc(sourceLabel(name.source))}${name.language ? ` · ${esc(name.language)}` : ""}</span>
            <code>${esc(name.key)}</code>
          </div>`).join("") || `<p>${ui("No localized name was found; this identity comes from an exported asset marker.", "未找到本地化名称；该身份来自导出资源标识。")}</p>`}
        </div>
      </section>
      <section class="characters-section">
        <h3>${ui("Identifiers and aliases", "标识与别名")}</h3>
        <div class="characters-aliases">${(row.aliases || []).map((alias) => `<code>${esc(alias)}</code>`).join("")}</div>
      </section>
      ${state.showDebug ? `<section class="characters-section characters-merge-section">
        <h3>${ui("Display name override", "覆盖显示名称")}</h3>
        ${row.nameOverridden ? `
          <div class="characters-name-detected-row">
            <span class="characters-merge-list-label">${ui("Detected name:", "自动识别名称：")}</span>
            <span class="characters-merge-chip">
              <code>${esc(row.detectedName)}</code>
              <button type="button" class="characters-merge-undo" data-name-reset="${esc(row.id)}" title="${esc(ui("Reset to detected name", "重置为识别名称"))}">&times;</button>
            </span>
          </div>` : ""}
        <form class="characters-merge-form characters-name-form" data-name-source="${esc(row.id)}">
          <label for="characters-name-input">${ui("Custom display name", "自定义显示名称")}</label>
          <div class="characters-merge-form-row">
            <input id="characters-name-input" type="text" value="${esc(row.primaryName || row.id)}" placeholder="${esc(ui("Display name…", "显示名称…"))}" autocomplete="off">
            <button type="submit">${ui("Save", "保存")}</button>
          </div>
          <p id="characters-name-status" class="characters-merge-status"></p>
        </form>
      </section>
      <section class="characters-section characters-merge-section">
        <h3>${ui("Manual identity merge", "手动合并身份")}</h3>
        <div class="characters-merge-flag-row">
          <button type="button" class="characters-flag-toggle${isFlagged ? " is-active" : ""}" data-flag-id="${esc(row.id)}">
            ${isFlagged ? ui("✓ Flagged: needs merge", "✓ 已标记：待合并") : ui("Flag: needs merge (target unknown)", "标记：待合并（合并对象未知）")}
          </button>
        </div>
        ${(row.mergedIds || []).length ? `
          <p class="characters-merge-list-label">${ui("Merged into this identity:", "已合并到此身份：")}</p>
          <div class="characters-merge-list">${row.mergedIds.map((id) => `
            <span class="characters-merge-chip">
              <code>${esc(id)}</code>
              <button type="button" class="characters-merge-undo" data-unmerge-id="${esc(id)}" title="${esc(ui("Undo merge", "撤销合并"))}">&times;</button>
            </span>`).join("")}
          </div>` : ""}
        <form class="characters-merge-form" data-merge-source="${esc(row.id)}">
          <label for="characters-merge-target">${ui("Merge this identity into", "将此身份合并到")}</label>
          <div class="characters-merge-form-row">
            <input id="characters-merge-target" list="characters-merge-target-options" placeholder="${ui("Type a name or id…", "输入名称或 ID…")}" autocomplete="off">
            <button type="submit">${ui("Merge", "合并")}</button>
          </div>
          <datalist id="characters-merge-target-options">${mergeTargetOptions(row.id).map((opt) => `<option value="${esc(opt.label)}">${esc(opt.id)}</option>`).join("")}</datalist>
          <p id="characters-merge-status" class="characters-merge-status"></p>
        </form>
      </section>` : ""}
      <section class="characters-section">
        <h3>${ui("Evidence", "证据")}</h3>
        <div class="characters-identity-evidence-list">${row.records.map((identity) => `
          <section class="characters-identity-evidence">
            <header>
              <span class="characters-kind">${esc(kindLabel(identity.kind))}</span>
              <code>${esc(identity.id)}</code>
              <span>${(identity.evidence || []).length} ${ui("evidence groups", "组证据")}</span>
            </header>
            <div class="characters-evidence-list">${(identity.evidence || []).map(renderEvidence).join("")}</div>
          </section>`).join("")}
        </div>
      </section>`;
    detail.querySelectorAll("[data-unmerge-id]").forEach((button) => {
      button.addEventListener("click", () => unmergeCharacter(button.dataset.unmergeId || ""));
    });
    detail.querySelector("[data-flag-id]")?.addEventListener("click", (event) => {
      toggleNeedsMerge(event.currentTarget.dataset.flagId || "");
    });
    detail.querySelector("[data-name-reset]")?.addEventListener("click", (event) => {
      clearNameOverride(event.currentTarget.dataset.nameReset || "");
    });
    const nameForm = detail.querySelector("[data-name-source]");
    nameForm?.addEventListener("submit", (event) => {
      event.preventDefault();
      const sourceId = nameForm.dataset.nameSource || "";
      const input = nameForm.querySelector("#characters-name-input");
      const typed = String(input?.value || "").trim();
      if (!typed) {
        setNameStatus(ui("Enter a name.", "请输入名称。"), "error");
        return;
      }
      const detected = row.nameOverridden ? row.detectedName : row.primaryName;
      if (typed === String(detected || "").trim()) {
        clearNameOverride(sourceId);
        return;
      }
      setNameOverride(sourceId, typed);
    });
    const mergeForm = detail.querySelector("[data-merge-source]");
    mergeForm?.addEventListener("submit", (event) => {
      event.preventDefault();
      const sourceId = mergeForm.dataset.mergeSource || "";
      const input = mergeForm.querySelector("#characters-merge-target");
      const typed = String(input?.value || "").trim().toLocaleLowerCase();
      if (!typed) return;
      const options = mergeTargetOptions(sourceId);
      const match = options.find((opt) => opt.label.toLocaleLowerCase() === typed)
        || options.find((opt) => opt.id.toLocaleLowerCase() === typed);
      if (!match) {
        setMergeStatus(ui("No matching identity found. Pick one from the list.", "未找到匹配身份，请从列表中选择。"), "error");
        return;
      }
      mergeCharacterInto(sourceId, match.id);
    });
  }

  function setMergeStatus(text, cls) {
    const node = state.container?.querySelector("#characters-merge-status");
    if (!node) return;
    node.textContent = text || "";
    node.className = "characters-merge-status" + (cls ? ` is-${cls}` : "");
  }

  function mergeCharacterInto(sourceId, targetId) {
    if (!sourceId || !targetId || sourceId === targetId) return;
    const merges = { ...(state.mergeOverrides || {}) };
    let probe = targetId;
    const seen = new Set();
    while (merges[probe]) {
      if (probe === sourceId || seen.has(probe)) {
        setMergeStatus(ui("That merge would create a cycle.", "该合并会形成循环。"), "error");
        return;
      }
      seen.add(probe);
      probe = merges[probe];
    }
    merges[sourceId] = targetId;
    state.mergeOverrides = merges;
    // The merge resolves whatever review was pending — clear the flag now
    // that it has an actual target instead of leaving a stale "needs merge".
    state.flaggedIds.delete(sourceId);
    const resolvedTarget = resolveMergeTarget(targetId, merges);
    // The source id stops being a top-level group id once merged away, so a
    // name override keyed on it would otherwise go silently unapplied —
    // carry it over to the target (without clobbering a target override).
    let nameOverridesChanged = false;
    if (state.nameOverrides && sourceId in state.nameOverrides) {
      const overrides = { ...state.nameOverrides };
      const carried = overrides[sourceId];
      delete overrides[sourceId];
      if (!(resolvedTarget in overrides)) overrides[resolvedTarget] = carried;
      state.nameOverrides = overrides;
      nameOverridesChanged = true;
    }
    state.selectedId = resolvedTarget;
    renderFilterChips();
    renderList();
    setMergeStatus(ui("Saving…", "正在保存…"), "saving");
    Promise.all([saveMergeOverrides(), nameOverridesChanged ? saveNameOverrides() : Promise.resolve()])
      .then(() => setMergeStatus(ui("Saved", "已保存"), "saved"))
      .catch((error) => {
        console.warn("Unable to save character overrides", error);
        setMergeStatus(ui("Failed to save merge", "保存合并失败"), "error");
      });
  }

  function toggleNeedsMerge(id) {
    if (!id) return;
    if (state.flaggedIds.has(id)) state.flaggedIds.delete(id);
    else state.flaggedIds.add(id);
    renderFilterChips();
    renderList();
    setMergeStatus(ui("Saving…", "正在保存…"), "saving");
    saveMergeOverrides()
      .then(() => setMergeStatus(ui("Saved", "已保存"), "saved"))
      .catch((error) => {
        console.warn("Unable to save overrides/character_merges.json", error);
        setMergeStatus(ui("Failed to save flag", "保存标记失败"), "error");
      });
  }

  function unmergeCharacter(sourceId) {
    if (!sourceId || !state.mergeOverrides || !(sourceId in state.mergeOverrides)) return;
    const merges = { ...state.mergeOverrides };
    delete merges[sourceId];
    state.mergeOverrides = merges;
    renderFilterChips();
    renderList();
    setMergeStatus(ui("Saving…", "正在保存…"), "saving");
    saveMergeOverrides()
      .then(() => setMergeStatus(ui("Saved", "已保存"), "saved"))
      .catch((error) => {
        console.warn("Unable to save overrides/character_merges.json", error);
        setMergeStatus(ui("Failed to save merge", "保存合并失败"), "error");
      });
  }

  function setNameStatus(text, cls) {
    const node = state.container?.querySelector("#characters-name-status");
    if (!node) return;
    node.textContent = text || "";
    node.className = "characters-merge-status" + (cls ? ` is-${cls}` : "");
  }

  function setNameOverride(id, name) {
    if (!id) return;
    const trimmed = String(name || "").trim();
    if (!trimmed) {
      setNameStatus(ui("Enter a name.", "请输入名称。"), "error");
      return;
    }
    state.nameOverrides = { ...(state.nameOverrides || {}), [id]: trimmed };
    renderFilterChips();
    renderList();
    setNameStatus(ui("Saving…", "正在保存…"), "saving");
    saveNameOverrides()
      .then(() => setNameStatus(ui("Saved", "已保存"), "saved"))
      .catch((error) => {
        console.warn("Unable to save overrides/character_name_overrides.json", error);
        setNameStatus(ui("Failed to save name", "保存名称失败"), "error");
      });
  }

  function clearNameOverride(id) {
    if (!id || !state.nameOverrides || !(id in state.nameOverrides)) return;
    const overrides = { ...state.nameOverrides };
    delete overrides[id];
    state.nameOverrides = overrides;
    renderFilterChips();
    renderList();
    setNameStatus(ui("Saving…", "正在保存…"), "saving");
    saveNameOverrides()
      .then(() => setNameStatus(ui("Saved", "已保存"), "saved"))
      .catch((error) => {
        console.warn("Unable to save overrides/character_name_overrides.json", error);
        setNameStatus(ui("Failed to reset name", "重置名称失败"), "error");
      });
  }

  async function loadNameOverrides(force = false) {
    if (state.nameOverrides && !force) return state.nameOverrides;
    try {
      const response = await fetch(NAME_OVERRIDE_PATH, { cache: "no-store" });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const payload = await response.json();
      const names = payload && payload.names && typeof payload.names === "object" ? payload.names : {};
      state.nameOverrides = { ...names };
    } catch (error) {
      console.warn("Unable to load overrides/character_name_overrides.json", error);
      state.nameOverrides = state.nameOverrides || {};
    }
    return state.nameOverrides;
  }

  function saveNameOverrides() {
    const payload = {
      _schema: NAME_OVERRIDE_SCHEMA,
      _note: "Manual display name overrides for the Characters page. Each key is a character id (the canonical grouped identity id, same id space as character_merges.json) mapped to the display name that replaces its detected primaryName. Edited from the Characters page UI.",
      names: state.nameOverrides || {},
    };
    return fetch(NAME_OVERRIDE_PATH, {
      method: "PUT",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload, null, 2) + "\n",
    }).then(async (res) => {
      if (!res.ok) {
        let message = "";
        try {
          const body = await res.json();
          message = body && body.error ? String(body.error) : "";
        } catch (_error) {
          message = "";
        }
        throw new Error(message || `HTTP ${res.status}`);
      }
      return true;
    });
  }

  async function loadMergeOverrides(force = false) {
    if (state.mergeOverrides && !force) return state.mergeOverrides;
    try {
      const response = await fetch(MERGE_OVERRIDE_PATH, { cache: "no-store" });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const payload = await response.json();
      const merges = payload && payload.merges && typeof payload.merges === "object" ? payload.merges : {};
      state.mergeOverrides = { ...merges };
      const flagged = Array.isArray(payload?.flagged) ? payload.flagged : [];
      state.flaggedIds = new Set(flagged.filter((id) => typeof id === "string" && id));
    } catch (error) {
      console.warn("Unable to load overrides/character_merges.json", error);
      state.mergeOverrides = state.mergeOverrides || {};
    }
    return state.mergeOverrides;
  }

  function saveMergeOverrides() {
    const payload = {
      _schema: MERGE_OVERRIDE_SCHEMA,
      _note: "Manual identity merges for the Characters page. Each key is a character id (as shown in the app) folded into the value's id; the target inherits all names, evidence, and aliases from the merged key. `flagged` lists ids the user has marked as needing a merge whose target isn't known yet. Edited from the Characters page UI.",
      merges: state.mergeOverrides || {},
      flagged: [...state.flaggedIds].sort(),
    };
    return fetch(MERGE_OVERRIDE_PATH, {
      method: "PUT",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload, null, 2) + "\n",
    }).then(async (res) => {
      if (!res.ok) {
        let message = "";
        try {
          const body = await res.json();
          message = body && body.error ? String(body.error) : "";
        } catch (_error) {
          message = "";
        }
        throw new Error(message || `HTTP ${res.status}`);
      }
      return true;
    });
  }

  async function load(language = currentLanguage(), force = false) {
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && state.data && state.language === nextLanguage) {
      renderShell();
      return state.data;
    }
    const token = ++state.loadToken;
    state.language = nextLanguage;
    if (state.container) state.container.innerHTML = `<div class="characters-empty">${ui("Loading character evidence…", "正在加载人物证据…")}</div>`;
    try {
      const [response] = await Promise.all([
        fetch(dataPath(nextLanguage), { cache: "no-store" }),
        loadMergeOverrides(force),
        loadNameOverrides(force),
      ]);
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const data = await response.json();
      if (token !== state.loadToken) return null;
      state.data = data;
      state.selectedId = "";
      renderShell();
      return data;
    } catch (error) {
      if (token !== state.loadToken) return null;
      if (state.container) state.container.innerHTML = `<div class="characters-empty characters-error">${ui("Character data could not be loaded. Rebuild it with scripts/build_character_data.py.", "无法加载人物数据。请运行 scripts/build_character_data.py 重新生成。")}<br><code>${esc(error.message)}</code></div>`;
      return null;
    }
  }

  function init() {
    state.container = document.querySelector("#characters-app");
    if (!state.container) return;
    state.showDebug = document.body.classList.contains("show-debug")
      || document.querySelector("#show-debug")?.getAttribute("aria-pressed") === "true";
    if (document.body.dataset.activeView === "characters" || location.hash === "#characters") load();
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.characters = { init, load };
  window.addEventListener("webui:view-changed", (event) => {
    if (event.detail?.view === "characters") load();
  });
  window.addEventListener("webui:language-changed", (event) => {
    if (document.body.dataset.activeView === "characters") load(event.detail?.language || currentLanguage());
    else state.language = "";
  });
  window.addEventListener("webui:ui-locale-changed", () => {
    if (state.data && state.container) renderShell();
  });
  window.addEventListener("webui:debug-changed", (event) => {
    const enabled = Boolean(event.detail?.enabled);
    if (state.showDebug === enabled) return;
    state.showDebug = enabled;
    if (state.data && state.container) renderDetail();
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
