(() => {
  const FILTER_PANEL_STORAGE_KEY = "gameplay_filters_collapsed";
  const COLLAPSED_KINDS_STORAGE_KEY = "gameplay_collapsed_kinds";
  const LEVEL_FRACTION_STORAGE_KEY = "gameplay_level_fraction";
  const GAMEPLAY_DATA_VERSION = "20260701-gp5";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  // Fixed display order for the data-type groups in the list.
  const KIND_ORDER = ["character", "weapon", "equipment", "item", "enemy"];
  // Enemy display types, ordered 领袖 > 头目 > 精英 > 进阶 > 普通 (by displayType id).
  const ENEMY_TYPE_RANK = { "2": 0, "4": 1, "1": 2, "3": 3, "0": 4 };
  // Reuse the story page's badge color sets for the kind filter chips, so each
  // data type reads with the same palette as the story badges (badge-env, ...).
  const KIND_CHIP_CLASS = {
    weapon: "kind-chip badge-cutscene",
    equipment: "kind-chip badge-radio",
    character: "kind-chip badge-env",
    enemy: "kind-chip badge-reading",
    item: "kind-chip badge-mail",
  };
  // Same palette as a plain badge chip for the list rows (story item style).
  const KIND_BADGE_CLASS = {
    weapon: "badge-cutscene",
    equipment: "badge-radio",
    character: "badge-env",
    enemy: "badge-reading",
    item: "badge-mail",
  };
  const TEXTS = window.WebUI.gameplayTexts;

  const {
    $,
    applyTemplate,
    escapeHtml,
    fetchWithProgress,
    formatNumber,
    normalizeUiLocale,
    parseQuery,
    queryScore,
    highlightRegex,
    storageGet,
    storageSet,
  } = window.WebUI;

  // Escape a value and wrap any active search tokens in <mark>, matching the
  // story page's search-term highlighting.
  function highlightText(value) {
    const safe = escapeHtml(value == null ? "" : String(value));
    const re = highlightRegex(STATE.searchTokens || []);
    return re ? safe.replace(re, (match) => `<mark>${match}</mark>`) : safe;
  }

  function loadCollapsedKinds() {
    try {
      const raw = storageGet(COLLAPSED_KINDS_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(parsed) ? parsed : []);
    } catch (_) {
      return new Set();
    }
  }

  function persistCollapsedKinds() {
    try {
      storageSet(COLLAPSED_KINDS_STORAGE_KEY, JSON.stringify([...STATE.collapsedKinds]));
    } catch (_) {}
  }

  // Level sliders remember the user's last position as a fraction (0..1) so the
  // preference carries across entries with different level counts. Default 1 =
  // max level.
  function loadLevelFraction() {
    const raw = Number(storageGet(LEVEL_FRACTION_STORAGE_KEY));
    return Number.isFinite(raw) && raw >= 0 && raw <= 1 ? raw : 1;
  }

  function saveLevelFraction(fraction) {
    const clamped = Math.max(0, Math.min(1, Number(fraction)));
    if (!Number.isFinite(clamped)) return;
    STATE.levelFraction = clamped;
    try { storageSet(LEVEL_FRACTION_STORAGE_KEY, String(clamped)); } catch (_) {}
  }

  function sliderIndexForFraction(max) {
    if (!(max > 0)) return 0;
    return Math.max(0, Math.min(max, Math.round((STATE.levelFraction ?? 1) * max)));
  }

  function toggleKindGroup(kind) {
    if (!kind) return;
    if (STATE.collapsedKinds.has(kind)) STATE.collapsedKinds.delete(kind);
    else STATE.collapsedKinds.add(kind);
    persistCollapsedKinds();
    renderList();
  }

  const STATE = {
    uiLocale: "zh",
    language: "CN",
    index: null,
    entries: [],
    filtered: [],
    selected: null,
    loading: null,
    searchTokens: [],
    collapsedKinds: new Set(),
    levelFraction: 1,
    filters: {
      kinds: new Set(),
      jobs: new Set(),
      characterProperties: new Set(),
      weaponTypes: new Set(),
      equipmentTypes: new Set(),
      enemyTypes: new Set(),
      rarities: new Set(),
    },
  };

  const gp$ = $;
  let gameplayPanel = null;

  function isMobileLayout() {
    return !!(window.matchMedia && window.matchMedia(MOBILE_LAYOUT_QUERY).matches);
  }

  function ensurePanelToggle() {
    if (gameplayPanel) return gameplayPanel;
    gameplayPanel = window.WebUI.filters.createPanelToggle({
      panel: "#gameplay-filter-panel",
      toggle: "#gameplay-filter-toggle",
      left: "#gameplay-left",
      storageKey: FILTER_PANEL_STORAGE_KEY,
      isMobile: isMobileLayout,
      labels: (collapsed) => text(collapsed ? "showFilters" : "hideFilters"),
    });
    return gameplayPanel;
  }

  function resolveInitialUiLocale() {
    return normalizeUiLocale(window.WEBUI_UI_LOCALE)
      || (document.documentElement.lang.toLowerCase().startsWith("zh") ? "zh" : "en");
  }

  function text(key, replacements = {}) {
    const locale = TEXTS[STATE.uiLocale] || TEXTS.en;
    return applyTemplate(locale[key] || TEXTS.en[key] || key, replacements);
  }

  function currentLanguage() {
    const select = gp$("#language");
    return String((select && select.value) || STATE.language || "CN").toUpperCase();
  }

  function gameplayDataPath(language) {
    // Cache-bust so a rebuilt index.json is picked up (bump on data changes).
    return `data/lang/${encodeURIComponent(language)}/gameplay/index.json?v=${GAMEPLAY_DATA_VERSION}`;
  }

  function normalizeGameplaySelection(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    let decoded = raw;
    try { decoded = decodeURIComponent(raw); }
    catch (_) {}
    if (decoded.includes(":")) decoded = decoded.split(":").pop();
    if (decoded.startsWith("wiki_chr_")) return `chr_${decoded.slice("wiki_chr_".length)}`;
    if (decoded.startsWith("wiki_wpn_")) return `wpn_${decoded.slice("wiki_wpn_".length)}`;
    if (decoded.startsWith("wiki_eny_")) return `eny_${decoded.slice("wiki_eny_".length)}`;
    if (decoded.startsWith("wiki_item_")) return `item_${decoded.slice("wiki_item_".length)}`;
    if (decoded.startsWith("wiki_")) return decoded.slice("wiki_".length);
    return decoded;
  }

  function requestedGameplaySelection() {
    const params = new URLSearchParams(window.location.search || "");
    return normalizeGameplaySelection(params.get("gameplay") || params.get("gameplayId") || params.get("entry") || "");
  }

  function findGameplayEntry(value) {
    const id = normalizeGameplaySelection(value);
    if (!id) return null;
    const candidates = new Set([id]);
    if (!id.startsWith("wiki_")) candidates.add(`wiki_${id}`);
    return STATE.entries.find((entry) => entry && (
      candidates.has(entry.id)
      || candidates.has(`${entry.kind}:${entry.id}`)
      || storyWikiKeys(entry).some((key) => candidates.has(key))
    )) || null;
  }

  function isGameplayActive() {
    return document.body.dataset.activeView === "gameplay"
      || (window.location.hash || "").replace(/^#/, "").toLowerCase() === "gameplay";
  }

  function formatValue(value) {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value === "number") return Number.isFinite(value) ? value.toLocaleString() : String(value);
    if (typeof value === "boolean") return value ? "true" : "false";
    if (typeof value === "object") {
      try { return JSON.stringify(value); }
      catch (_) { return String(value); }
    }
    return String(value);
  }

  function kindLabel(kind) {
    if (kind === "weapon") return text("weapon");
    if (kind === "equipment") return text("equipment");
    if (kind === "character") return text("character");
    if (kind === "enemy") return text("enemy");
    if (kind === "item") return text("item");
    return String(kind || "");
  }

  function entrySubtitle(entry) {
    const parts = [];
    if (entry.rarity) parts.push(`${text("rarity")} ${entry.rarity}`);
    if (entry.kind === "weapon" && entry.weaponTypeLabel) parts.push(entry.weaponTypeLabel);
    if (entry.kind === "equipment") {
      if (entry.partTypeLabel) parts.push(entry.partTypeLabel);
      if (entry.suit && entry.suit.name) parts.push(entry.suit.name);
    }
    if (entry.kind === "character") {
      if (entry.professionLabel) parts.push(entry.professionLabel);
      if (entry.elementLabel) parts.push(entry.elementLabel);
    }
    if (entry.kind === "enemy") {
      if (entry.displayTypeLabel) parts.push(entry.displayTypeLabel);
      if (entry.templateName && entry.templateName !== entry.title) parts.push(entry.templateName);
      if (entry.isDangerous) parts.push(text("dangerous"));
    }
    if (entry.kind === "item") {
      if (entry.showingTypeLabel) parts.push(entry.showingTypeLabel);
      if (entry.itemTypeLabel && entry.itemTypeLabel !== entry.showingTypeLabel) parts.push(entry.itemTypeLabel);
    }
    return parts.join(" / ");
  }

  function fact(label, value, opts = {}) {
    const display = formatValue(value);
    if (!display) return null;
    return { label, value: display, mono: !!opts.mono, kind: opts.kind || "" };
  }

  function dedupeDetailTags(tags) {
    const seen = new Set();
    return (tags || []).filter((tag) => {
      if (!tag || tag.value === undefined || tag.value === null || tag.value === "") return false;
      const key = `${String(tag.label || "").trim().toLowerCase()}\u0000${String(tag.value || "").trim().toLowerCase()}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function section(title, body, opts = {}) {
    if (!body) return "";
    const open = opts.open === false ? "" : " open";
    return `<details class="gameplay-section"${open}><summary><span>${escapeHtml(title)}</span></summary><div class="gameplay-section-body">${body}</div></details>`;
  }

  function storyWikiKeys(entry) {
    const keys = [];
    const seen = new Set();
    const add = (value) => {
      const key = String(value || "").trim();
      if (!key || seen.has(key)) return;
      seen.add(key);
      keys.push(key);
    };
    if (entry && Array.isArray(entry.storyWikiKeys)) entry.storyWikiKeys.forEach(add);
    if (entry && entry.storyWikiKey) add(entry.storyWikiKey);
    return keys;
  }

  function storyWikiKey(entry) {
    return storyWikiKeys(entry)[0] || "";
  }

  function storyWikiHrefForKey(key) {
    if (!key) return "";
    const params = new URLSearchParams();
    params.set("lang", STATE.language || currentLanguage());
    params.set("ui", STATE.uiLocale || "zh");
    params.set("story", key);
    return `?${params.toString()}#story`;
  }

  function storyWikiHref(entry) {
    return storyWikiHrefForKey(storyWikiKey(entry));
  }

  function renderStoryWikiLink(entry) {
    const keys = storyWikiKeys(entry);
    return keys.map((key) => {
      const href = storyWikiHrefForKey(key);
      if (!href) return "";
      return `<a class="gameplay-detail-tag gameplay-detail-wiki-link gameplay-wiki-link" href="${escapeHtml(href)}"><span>${escapeHtml(text("storyWiki"))}</span></a>`;
    }).filter(Boolean).join("");
  }
  function renderDescription(value) {
    const textValue = String(value || "").trim();
    if (!textValue) return "";
    return `<p class="gameplay-description">${escapeHtml(textValue).replace(/\n/g, "<br>")}</p>`;
  }

  function renderBlackboard(items) {
    const pairs = (items || [])
      .filter((item) => item && item.key)
      .map((item) => `<span class="gameplay-value-chip"><b>${escapeHtml(item.key)}</b>${escapeHtml(formatValue(item.value))}</span>`);
    return pairs.length ? `<div class="gameplay-blackboard">${pairs.join("")}</div>` : "";
  }

  function renderSubDesc(items) {
    const rows = (items || [])
      .filter((item) => item && (item.label || item.value))
      .map((item) => `<span class="gameplay-value-chip"><b>${escapeHtml(item.label || "-")}</b>${escapeHtml(item.value || "")}</span>`);
    return rows.length ? `<div class="gameplay-blackboard">${rows.join("")}</div>` : "";
  }

  function renderIdChips(items, opts = {}) {
    const highlight = opts.highlight;
    const rows = (items || [])
      .filter(Boolean)
      .map((item) => {
        const cls = highlight && highlight.has(item) ? " gameplay-diff" : "";
        return `<span class="gameplay-value-chip${cls}"><b>${escapeHtml(text("id"))}</b>${escapeHtml(item)}</span>`;
      });
    return rows.length ? `<div class="gameplay-blackboard">${rows.join("")}</div>` : "";
  }

  function materialChipRows(items) {
    return (items || [])
      .filter((item) => item && (item.name || item.id))
      .map((item) => {
        const label = item.name || item.id;
        const count = item.count !== undefined && item.count !== null && item.count !== "" ? formatValue(item.count) : "";
        return `<span class="gameplay-value-chip"><b>${escapeHtml(label)}</b>${escapeHtml(count)}</span>`;
      })
      .join("");
  }

  function renderMaterialChips(items) {
    const rows = materialChipRows(items);
    return rows ? `<div class="gameplay-blackboard">${rows}</div>` : "";
  }

  function renderUpgradeCost(row) {
    if (!row) return "";
    const chips = [];
    if (row.goldCost !== undefined && row.goldCost !== null && row.goldCost !== "") {
      chips.push(`<span class="gameplay-value-chip"><b>${escapeHtml(text("gold"))}</b>${escapeHtml(formatValue(row.goldCost))}</span>`);
    }
    const materials = materialChipRows(row.itemBundle || []);
    if (materials) chips.push(materials);
    if (!chips.length) return "";
    return `<div class="gameplay-level-cost">
      <div class="gameplay-subheading">${escapeHtml(text("levelUpCosts"))}</div>
      <div class="gameplay-blackboard">${chips.join("")}</div>
    </div>`;
  }

  function levelUpForLevel(level, rows) {
    const levelValue = level && level.level !== undefined && level.level !== null ? String(level.level) : "";
    if (!levelValue) return null;
    return (rows || []).find((row) => row && row.level !== undefined && row.level !== null && String(row.level) === levelValue) || null;
  }

  function levelLabel(level) {
    return `${text("level")} ${formatValue(level && level.level || "")}`.trim();
  }

  // Numeric attribute-type -> canonical stat key (mirrors the exporter's
  // STAT_ATTR_KEYS, plus 0 = level). Some data paths emit a bare "attr_<type>"
  // even for types that do have a name, so we recover the name here.
  const ATTR_TYPE_KEYS = {
    0: "level", 1: "hp", 2: "atk", 3: "def",
    4: "physical_damage_taken", 5: "fire_damage_taken", 6: "pulse_damage_taken", 7: "cryst_damage_taken",
    9: "critical_rate", 17: "normal_attack_efficiency", 28: "ultimate_skill_efficiency",
    29: "heal_output", 30: "heal_taken", 31: "healing_taken_scalar",
    32: "skill_damage", 33: "combo_skill_damage", 34: "normal_attack_damage",
    35: "fire_burst_damage", 36: "pulse_burst_damage", 37: "cryst_burst_damage", 38: "natural_burst_damage",
    39: "str", 40: "agi", 41: "wis", 42: "will",
    44: "ultimate_sp_gain", 48: "natural_damage_taken",
    50: "physical_damage", 51: "fire_damage", 52: "pulse_damage", 53: "cryst_damage", 54: "natural_damage",
    60: "ether_damage_taken", 61: "broken_unit_damage",
    80: "physical_damage_taken_scalar", 81: "natural_damage_taken_scalar", 82: "cryst_damage_taken_scalar",
    83: "pulse_damage_taken_scalar", 84: "fire_damage_taken_scalar", 85: "ether_damage_taken_scalar",
    87: "infliction",
  };

  function statAttrLabel(attr) {
    let key = String((attr && attr.key) || "");
    const type = attr && attr.type;
    const numeric = typeof type === "number" ? type : /^attr_(\d+)$/.test(key) ? Number(key.slice(5)) : null;
    if (numeric != null && ATTR_TYPE_KEYS[numeric]) key = ATTR_TYPE_KEYS[numeric];
    const translated = text(`stat_${key}`);
    if (translated !== `stat_${key}`) return translated;
    // Prefer an exporter-provided label, unless it is just the raw "attr_N" key.
    const label = attr && attr.label;
    if (label && !/^attr_\d+$/.test(String(label))) return String(label);
    const unnamed = /^attr_(\d+)$/.exec(key);
    return unnamed ? `Attr ${unnamed[1]}` : key;
  }

  function statLevelLabel(row) {
    const parts = [];
    if (row && row.level !== undefined && row.level !== null) parts.push(`${text("level")} ${formatValue(row.level)}`);
    if (row && row.breakStage !== undefined && row.breakStage !== null) parts.push(`${text("breakStage")} ${formatValue(row.breakStage)}`);
    return parts.join(" / ");
  }


  // Sum a set of {gold, items} cost rows into one aggregate (item counts merged
  // by id). Gold that the source carried as an item (characters) stays in items;
  // gold carried separately (weapons) is returned as `gold`.
  function aggregateCosts(rows) {
    const byId = new Map();
    let gold = 0;
    for (const row of rows) {
      if (!row) continue;
      if (Number(row.gold) > 0) gold += Number(row.gold);
      for (const item of row.items || []) {
        if (!item) continue;
        const id = String(item.id || item.name || "");
        if (!id) continue;
        const prev = byId.get(id) || { id: item.id, name: item.name, count: 0 };
        prev.count += Number(item.count) || 0;
        byId.set(id, prev);
      }
    }
    return { gold, items: [...byId.values()] };
  }

  // Build a per-level cost lookup for weapon and character stat sliders. Every
  // level shows the CUMULATIVE breakthrough materials for its stage plus the
  // cumulative level-up exp/gold up to that level.
  function statCostIndex(entry, kind) {
    const perStage = new Map(); // stage -> { gold, items } for that stage's breakthrough
    const levelUpItemsByStage = new Map();
    const levelUpByLevel = new Map(); // exact per-level cumulative { exp, gold }
    let checkpoints = [];
    let breakLabel;
    let perLevel = [];
    if (kind === "weapon") {
      for (const row of (entry.breakthrough && entry.breakthrough.rows) || []) {
        perStage.set(Number(row.showLevel), { gold: row.goldCost, items: row.items || [] });
      }
      checkpoints = ((entry.upgrade && entry.upgrade.checkpoints) || []).map((cp) => ({
        level: Number(cp.level), exp: cp.lvUpExpSum, gold: cp.lvUpGoldSum,
      }));
      perLevel = (entry.upgrade && entry.upgrade.perLevel) || [];
      breakLabel = text("weaponBreakthroughs");
    } else {
      for (const stage of entry.breakStages || []) {
        if ((stage.availableExpItems || []).length) levelUpItemsByStage.set(Number(stage.stage), stage.availableExpItems);
      }
      for (const bt of entry.breakthroughs || []) {
        perStage.set(Number(bt.stage), { items: bt.requiredItem || [] });
      }
      checkpoints = ((entry.levelCurve && entry.levelCurve.checkpoints) || []).map((cp) => {
        const hasCumulative = cp.expSum != null || cp.goldSum != null;
        return { level: Number(cp.level), exp: hasCumulative ? cp.expSum : cp.exp, gold: hasCumulative ? cp.goldSum : cp.gold };
      });
      perLevel = (entry.levelCurve && entry.levelCurve.perLevel) || [];
      breakLabel = text("characterBreakthroughs");
    }
    for (const row of perLevel) {
      levelUpByLevel.set(Number(row.level), { exp: row.expSum, gold: row.goldSum, expItems: row.expItems || [] });
    }
    // Cumulative breakthrough cost for every stage: sum of all breakthroughs at
    // stages 1..stage.
    const maxStage = Math.max(0, ...perStage.keys());
    const cumulativeBreakByStage = new Map();
    for (let stage = 1; stage <= maxStage; stage += 1) {
      const rows = [];
      for (let s = 1; s <= stage; s += 1) {
        if (perStage.has(s)) rows.push(perStage.get(s));
      }
      cumulativeBreakByStage.set(stage, aggregateCosts(rows));
    }
    checkpoints.sort((a, b) => a.level - b.level);
    return { cumulativeBreakByStage, levelUpItemsByStage, levelUpByLevel, checkpoints, breakLabel };
  }

  // The cumulative level-up cost at `level` = the highest checkpoint at or below it.
  function cumulativeLevelUpAt(checkpoints, level) {
    let best = null;
    for (const cp of checkpoints) {
      if (cp.level <= level) best = cp;
      else break;
    }
    return best;
  }

  function renderStatCost(row, costIndex) {
    if (!costIndex || !row) return "";
    const parts = [];
    const stage = Number(row.breakStage);
    // Cumulative breakthrough materials up to this level's stage.
    const brk = stage >= 1 ? costIndex.cumulativeBreakByStage.get(stage) : null;
    if (brk && ((brk.items || []).length || Number(brk.gold) > 0)) {
      const chips = [
        Number(brk.gold) > 0 ? renderChipPairs([{ label: text("gold"), value: brk.gold }]) : "",
        renderMaterialChips(brk.items || []),
      ].filter(Boolean).join("");
      if (chips) parts.push(`<div class="gameplay-subheading">${escapeHtml(costIndex.breakLabel)}</div>${chips}`);
    }
    // Cumulative level-up cost up to this exact level (falls back to the nearest
    // checkpoint when a per-level curve isn't available), plus the stage's EXP items.
    const cp = costIndex.levelUpByLevel.get(Number(row.level)) || cumulativeLevelUpAt(costIndex.checkpoints, Number(row.level));
    const cumulativeExpItems = cp && (cp.expItems || []).length ? cp.expItems : null;
    let upPairs = cp && Number(cp.gold) > 0
      ? [{ label: text("cumulativeGold"), value: cp.gold }]
      : null;
    if (cp && !cumulativeExpItems && Number(cp.exp) > 0) {
      (upPairs || (upPairs = [])).unshift({ label: text("cumulativeExp"), value: cp.exp });
    }
    const expItems = costIndex.levelUpItemsByStage.get(stage);
    const upChips = [
      cumulativeExpItems ? renderMaterialChips(cumulativeExpItems) : "",
      upPairs ? renderChipPairs(upPairs) : "",
      expItems ? renderMaterialChips(expItems) : "",
    ].filter(Boolean).join("");
    if (upChips) parts.push(`<div class="gameplay-subheading">${escapeHtml(text("levelUpCosts"))}</div>${upChips}`);
    return parts.length ? `<div class="gameplay-level-cost">${parts.join("")}</div>` : "";
  }

  function renderStatPane(row, active, costIndex) {
    return `<div class="gameplay-level-pane gameplay-stat-pane" data-level-label="${escapeHtml(statLevelLabel(row))}"${active ? "" : " hidden"}>
      <div class="gameplay-level-effect">${renderStatAttrs(row) || `<span class="muted">-</span>`}</div>
      ${renderStatCost(row, costIndex)}
    </div>`;
  }

  function renderStats(stats, costIndex) {
    const rows = ((stats && (stats.rows || stats.checkpoints)) || []).filter((row) => row && (row.attrs || []).length);
    if (!rows.length) return "";
    const body = rows.length > 1
      ? `<div class="gameplay-level-slider-wrap gameplay-stat-slider" data-level-card>
        <div class="gameplay-level-slider-control">
          <span>${escapeHtml(text("selectedLevel"))}</span>
          <input class="gameplay-level-slider" type="range" min="0" max="${rows.length - 1}" step="1" value="0" aria-label="${escapeHtml(text("selectedLevel"))}">
          <output class="gameplay-level-slider-output">${escapeHtml(statLevelLabel(rows[0]))}</output>
        </div>
        <div class="gameplay-level-panes">${rows.map((row, index) => renderStatPane(row, index === 0, costIndex)).join("")}</div>
      </div>`
      : `<div class="gameplay-level-table">${rows.map((row) => `<div class="gameplay-level-row gameplay-stat-row">
        <div class="gameplay-level-num">${escapeHtml(statLevelLabel(row))}</div>
        <div class="gameplay-level-effect">${renderStatAttrs(row) || `<span class="muted">-</span>`}${renderStatCost(row, costIndex)}</div>
        <div class="gameplay-level-values"></div>
      </div>`).join("")}</div>`;
    return `<article class="gameplay-skill-card gameplay-stat-card">
      <header>
        <div class="gameplay-skill-title">${escapeHtml(text("statCheckpoints"))}</div>
        <div class="gameplay-skill-meta">${escapeHtml(statCurveMeta(stats))}</div>
      </header>
      ${body}
    </article>`;
  }

  function renderLevelPane(level, active, costRow) {
    const values = [renderBlackboard(level.blackboard), renderSubDesc(level.subDesc)].filter(Boolean).join("");
    const cost = renderUpgradeCost(costRow);
    return `<div class="gameplay-level-pane" data-level-label="${escapeHtml(levelLabel(level))}"${active ? "" : " hidden"}>
      <div class="gameplay-level-effect">${renderDescription(level.description) || `<span class="muted">-</span>`}</div>
      <div class="gameplay-level-values">${values || `<span class="muted">-</span>`}</div>
      ${cost}
    </div>`;
  }

  function renderLevelRows(skill, opts = {}) {
    const levelUpRows = opts.levelUp || [];
    const levels = (skill.levels || []).filter((level) => level && (level.description || (level.blackboard || []).length || (level.subDesc || []).length || levelUpForLevel(level, levelUpRows)));
    if (!levels.length) return "";
    if (opts.slider && levels.length > 1) {
      return `<div class="gameplay-level-slider-wrap" data-level-card>
        <div class="gameplay-level-slider-control">
          <span>${escapeHtml(text("selectedLevel"))}</span>
          <input class="gameplay-level-slider" type="range" min="0" max="${levels.length - 1}" step="1" value="0" aria-label="${escapeHtml(text("selectedLevel"))}">
          <output class="gameplay-level-slider-output">${escapeHtml(levelLabel(levels[0]))}</output>
        </div>
        <div class="gameplay-level-panes">${levels.map((level, index) => renderLevelPane(level, index === 0, levelUpForLevel(level, levelUpRows))).join("")}</div>
      </div>`;
    }
    return `<div class="gameplay-level-table">${levels.map((level) => {
      const values = [renderBlackboard(level.blackboard), renderSubDesc(level.subDesc)].filter(Boolean).join("");
      const cost = renderUpgradeCost(levelUpForLevel(level, levelUpRows));
      return `<div class="gameplay-level-row">
        <div class="gameplay-level-num">${escapeHtml(formatValue(level.level || ""))}</div>
        <div class="gameplay-level-effect">${renderDescription(level.description) || `<span class="muted">-</span>`}</div>
        <div class="gameplay-level-values">${values || `<span class="muted">-</span>`}</div>
        ${cost}
      </div>`;
    }).join("")}</div>`;
  }
  function renderSkillCard(skill, opts = {}) {
    if (!skill) return "";
    const levels = skill.levels || [];
    const hasSlider = !!opts.slider && levels.length > 1;
    const maxDifferent = !hasSlider && skill.maxDescription && skill.maxDescription !== skill.description;
    return `<article class="gameplay-skill-card">
      <header>
        <div class="gameplay-skill-title">${escapeHtml(skill.name || skill.id || "")}</div>
        <div class="gameplay-skill-meta">${escapeHtml(skill.id || "")}${skill.levelCount ? ` / ${formatNumber(skill.levelCount)} Lv` : ""}</div>
      </header>
      ${hasSlider ? "" : renderDescription(skill.description)}
      ${maxDifferent ? `<div class="gameplay-max-effect"><span>${escapeHtml(text("maxEffect"))}</span>${renderDescription(skill.maxDescription)}</div>` : ""}
      ${renderLevelRows(skill, opts)}
    </article>`;
  }
  function renderTalentCard(talent) {
    if (!talent) return "";
    const meta = [talent.typeLabel, talent.breakStage ? `Break ${talent.breakStage}` : "", talent.level ? `Lv ${talent.level}` : ""]
      .filter(Boolean)
      .join(" / ");
    const attr = talent.attributeModifier && Object.keys(talent.attributeModifier).length
      ? renderBlackboard(Object.entries(talent.attributeModifier).map(([key, value]) => ({ key, value })))
      : "";
    return `<article class="gameplay-skill-card">
      <header>
        <div class="gameplay-skill-title">${escapeHtml(talent.title || talent.id || "")}</div>
        <div class="gameplay-skill-meta">${escapeHtml([talent.id, meta].filter(Boolean).join(" / "))}</div>
      </header>
      ${renderDescription(talent.description)}
      ${attr}
    </article>`;
  }

  function talentKindLabel(kind) {
    if (kind === "passive") return text("passiveSkill");
    if (kind === "factory") return text("factorySkill");
    if (kind === "upgrade") return text("upgradeNodes");
    if (kind === "equipmentBreak") return text("equipmentBreak");
    if (kind === "attribute") return text("attributeNode");
    return kind || "";
  }

  function renderRequiredItems(items) {
    return renderMaterialChips(items);
  }

  function renderTalentLevelCell(level, groupTitle) {
    const title = level.name || (level.title !== groupTitle ? level.title : "") || `${text("level")} ${formatValue(level.level || "")}`;
    const meta = [
      level.level ? `${text("level")} ${formatValue(level.level)}` : "",
      level.breakStage ? `Break ${formatValue(level.breakStage)}` : "",
      level.equipTierLimit ? `T${formatValue(level.equipTierLimit)}` : "",
      level.unlockHint ? `${text("unlockHint")}: ${level.unlockHint}` : "",
      level.id,
    ].filter(Boolean).join(" / ");
    const attr = level.attributeModifier && Object.keys(level.attributeModifier).length
      ? renderBlackboard(Object.entries(level.attributeModifier).map(([key, value]) => ({ key, value })))
      : "";
    const required = renderRequiredItems(level.requiredItem || []);
    const values = [renderBlackboard(level.blackboard), attr].filter(Boolean).join("");
    return `<div class="gameplay-talent-level">
      <div class="gameplay-talent-level-title">${escapeHtml(title)}</div>
      <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
      ${renderDescription(level.description)}
      ${values}
      ${required ? `<div class="gameplay-subheading">${escapeHtml(text("requiredItems"))}</div>${required}` : ""}
    </div>`;
  }

  function renderTalentGroupRow(group) {
    if (!group) return "";
    const levels = group.levels || [];
    const meta = [talentKindLabel(group.kind), group.rank ? `${text("rank")} ${formatValue(group.rank)}` : "", group.id]
      .filter(Boolean)
      .join(" / ");
    const title = (group.kind === "attribute" || group.kind === "upgrade") ? talentKindLabel(group.kind) : (group.title || group.id || "");
    return `<article class="gameplay-talent-row gameplay-talent-${escapeHtml(group.kind || "other")}">
      <header class="gameplay-talent-row-header">
        <div>
          <div class="gameplay-group-title">${escapeHtml(title)}</div>
          <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
        </div>
      </header>
      <div class="gameplay-talent-levels">${levels.map((level) => renderTalentLevelCell(level, group.title)).join("")}</div>
    </article>`;
  }

  function renderTalentGroups(groups) {
    const rows = (groups || []).map(renderTalentGroupRow).filter(Boolean);
    return rows.length ? `<div class="gameplay-talent-table">${rows.join("")}</div>` : "";
  }

  function renderChipPairs(pairs, opts = {}) {
    const diff = opts.diffLabels;
    const rows = (pairs || [])
      .filter((item) => item && item.value !== undefined && item.value !== null && item.value !== "")
      .map((item) => {
        const cls = diff && diff.has(String(item.label || "")) ? " gameplay-diff" : "";
        return `<span class="gameplay-value-chip${cls}"><b>${escapeHtml(item.label)}</b>${escapeHtml(formatValue(item.value))}</span>`;
      });
    return rows.length ? `<div class="gameplay-blackboard">${rows.join("")}</div>` : "";
  }

  function levelRangeLabel(range) {
    if (!Array.isArray(range) || range.length < 2) return "";
    const start = formatValue(range[0]);
    const end = formatValue(range[1]);
    return start && end ? `${start}-${end}` : start || end;
  }

  function renderBounds(bounds) {
    const rows = (bounds || [])
      .map((bound, index) => {
        if (!bound || typeof bound !== "object") return null;
        const lower = bound.lowerBound;
        const upper = bound.upperBound;
        if ((lower === undefined || lower === null) && (upper === undefined || upper === null)) return null;
        const value = String(lower) === String(upper) ? formatValue(lower) : `${formatValue(lower)}-${formatValue(upper)}`;
        return { label: `${text("skillBounds")} ${index + 1}`, value };
      })
      .filter(Boolean);
    return renderChipPairs(rows);
  }

  function progressionCard(title, meta, body) {
    if (!body) return "";
    return `<article class="gameplay-skill-card">
      <header>
        <div class="gameplay-skill-title">${escapeHtml(title)}</div>
        <div class="gameplay-skill-meta">${escapeHtml(meta || "")}</div>
      </header>
      ${body}
    </article>`;
  }

  function renderProgressionRows(rows, renderValues) {
    const out = (rows || []).filter(Boolean).map((row) => {
      const level = row.level !== undefined && row.level !== null ? row.level : row.stage;
      return `<div class="gameplay-level-row">
        <div class="gameplay-level-num">${escapeHtml(formatValue(level === undefined || level === null ? "" : level))}</div>
        <div class="gameplay-level-effect">${renderValues(row) || `<span class="muted">-</span>`}</div>
        <div class="gameplay-level-values"></div>
      </div>`;
    });
    return out.length ? `<div class="gameplay-level-table">${out.join("")}</div>` : "";
  }

  function formatStatValue(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      if (Number.isInteger(value)) return value.toLocaleString();
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
    return formatValue(value);
  }

  function renderStatAttrs(rowOrAttrs) {
    const attrs = Array.isArray(rowOrAttrs) ? rowOrAttrs : (rowOrAttrs && rowOrAttrs.attrs || []);
    const rows = attrs
      .filter((item) => item && item.value !== undefined && item.value !== null && item.value !== "")
      .map((item) => `<span class="gameplay-value-chip"><b>${escapeHtml(statAttrLabel(item))}</b>${escapeHtml(formatStatValue(item.value))}</span>`);
    return rows.length ? `<div class="gameplay-blackboard">${rows.join("")}</div>` : "";
  }

  function statCurveMeta(stats) {
    if (!stats) return "";
    return [
      stats.source,
      stats.maxLevel ? `${text("maxLevel")} ${formatValue(stats.maxLevel)}` : "",
      stats.rawMaxLevel && String(stats.rawMaxLevel) !== String(stats.maxLevel) ? `${text("rawMaxLevel")} ${formatValue(stats.rawMaxLevel)}` : "",
      stats.extraRowsBeyondPlayable ? `${text("extraRawRows")} ${formatValue(stats.extraRowsBeyondPlayable)}` : "",
    ].filter(Boolean).join(" / ");
  }

  function renderWeaponProgression(entry) {
    const cards = [];
    const upgrade = entry.upgrade || {};
    const upgradeRows = renderProgressionRows(upgrade.checkpoints || [], (row) => renderChipPairs([
      { label: text("baseAtk"), value: row.baseAtk },
      { label: text("exp"), value: row.lvUpExp },
      { label: text("gold"), value: row.lvUpGold },
      { label: text("cumulativeExp"), value: row.lvUpExpSum },
      { label: text("cumulativeGold"), value: row.lvUpGoldSum },
    ]));
    cards.push(progressionCard(text("upgradeCurve"), [upgrade.templateId, `${formatValue(upgrade.rowCount)} ${text("level")}`].filter(Boolean).join(" / "), upgradeRows));

    const breakthroughRows = (entry.breakthrough && entry.breakthrough.rows || []).map((row) => {
      const meta = [row.showLevel ? `${text("showLevel")} ${formatValue(row.showLevel)}` : "", row.goldCost ? `${text("gold")} ${formatValue(row.goldCost)}` : ""].filter(Boolean).join(" / ");
      const bounds = renderBounds(row.skillLevelBounds || []);
      const items = renderRequiredItems(row.items || []);
      return `<div class="gameplay-talent-level">
        <div class="gameplay-talent-level-title">${escapeHtml(`${text("level")} ${formatValue(row.level === undefined || row.level === null ? "" : row.level)}`)}</div>
        <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
        ${bounds}
        ${items ? `<div class="gameplay-subheading">${escapeHtml(text("requiredItems"))}</div>${items}` : ""}
      </div>`;
    }).join("");
    cards.push(progressionCard(text("weaponBreakthroughs"), entry.breakthrough && entry.breakthrough.templateId, breakthroughRows ? `<div class="gameplay-talent-levels">${breakthroughRows}</div>` : ""));

    const talentRows = renderProgressionRows(entry.talentTemplate && entry.talentTemplate.rows || [], (row) => renderBounds(row.skillLevelExtraBounds || []));
    cards.push(progressionCard(text("weaponTalentBounds"), entry.talentTemplate && entry.talentTemplate.templateId, talentRows));
    const body = cards.filter(Boolean).join("");
    return body ? `<div class="gameplay-card-grid">${body}</div>` : "";
  }

  function renderCharacterProgression(entry) {
    const cards = [];
    const curve = entry.levelCurve || {};
    const levelRows = renderProgressionRows(curve.checkpoints || [], (row) => renderChipPairs([
      { label: text("exp"), value: row.exp },
      { label: text("gold"), value: row.gold },
    ]));
    cards.push(progressionCard(text("characterLevelCurve"), [curve.table, curve.maxLevel ? `${text("maxLevel")} ${formatValue(curve.maxLevel)}` : ""].filter(Boolean).join(" / "), levelRows));

    const stageRows = (entry.breakStages || []).map((row) => {
      const caps = row.skillCaps && Object.keys(row.skillCaps).length
        ? renderBlackboard(Object.entries(row.skillCaps).map(([key, value]) => ({ key, value })))
        : "";
      const facts = renderChipPairs([
        { label: text("levelRange"), value: levelRangeLabel(row.levelRange) },
        { label: text("breakStatus"), value: row.breakStatus },
        { label: text("gold"), value: row.goldCost },
      ]);
      const expItems = renderRequiredItems(row.availableExpItems || []);
      return `<div class="gameplay-talent-level">
        <div class="gameplay-talent-level-title">${escapeHtml(`${text("stage")} ${formatValue(row.stage === undefined || row.stage === null ? "" : row.stage)}`)}</div>
        ${facts}
        ${caps ? `<div class="gameplay-subheading">${escapeHtml(text("skillCaps"))}</div>${caps}` : ""}
        ${expItems ? `<div class="gameplay-subheading">${escapeHtml(text("expItems"))}</div>${expItems}` : ""}
      </div>`;
    }).join("");
    cards.push(progressionCard(text("characterBreakStages"), "CharBreakStageTable.json", stageRows ? `<div class="gameplay-talent-levels">${stageRows}</div>` : ""));

    const breakthroughRows = (entry.breakthroughs || []).map((row) => {
      const meta = [row.id, row.stage ? `${text("stage")} ${formatValue(row.stage)}` : "", row.equipTierLimit ? `T${formatValue(row.equipTierLimit)}` : ""].filter(Boolean).join(" / ");
      const required = renderRequiredItems(row.requiredItem || []);
      return `<div class="gameplay-talent-level">
        <div class="gameplay-talent-level-title">${escapeHtml(row.name || row.id || "")}</div>
        <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
        ${renderDescription(row.description)}
        ${required ? `<div class="gameplay-subheading">${escapeHtml(text("requiredItems"))}</div>${required}` : ""}
      </div>`;
    }).join("");
    cards.push(progressionCard(text("characterBreakthroughs"), "CharGrowthTable.json", breakthroughRows ? `<div class="gameplay-talent-levels">${breakthroughRows}</div>` : ""));

    const potentialRows = (entry.potentials && entry.potentials.levels || []).map((row) => {
      const meta = [row.potentialEffectId, row.level ? `${text("level")} ${formatValue(row.level)}` : ""].filter(Boolean).join(" / ");
      const required = renderRequiredItems(row.requiredItem || []);
      const values = renderBlackboard(row.blackboard || []);
      return `<div class="gameplay-talent-level">
        <div class="gameplay-talent-level-title">${escapeHtml(row.name || `${text("potential")} ${formatValue(row.level === undefined || row.level === null ? "" : row.level)}`)}</div>
        <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
        ${renderDescription(row.description)}
        ${values}
        ${required ? `<div class="gameplay-subheading">${escapeHtml(text("requiredItems"))}</div>${required}` : ""}
      </div>`;
    }).join("");
    cards.push(progressionCard(text("characterPotentials"), entry.potentials && entry.potentials.firstItemId, potentialRows ? `<div class="gameplay-talent-levels">${potentialRows}</div>` : ""));

    const body = cards.filter(Boolean).join("");
    return body ? `<div class="gameplay-card-grid">${body}</div>` : "";
  }



  function sortedSkillLevelsForGroup(group) {
    const levels = new Set();
    for (const skill of group.skills || []) {
      for (const level of skill.levels || []) {
        if (level && level.level !== undefined && level.level !== null) levels.add(String(level.level));
      }
    }
    for (const row of group.levelUp || []) {
      if (row && row.level !== undefined && row.level !== null) levels.add(String(row.level));
    }
    return [...levels].sort((a, b) => Number(a) - Number(b));
  }

  function levelForSkill(skill, levelValue) {
    const wanted = String(levelValue || "");
    return (skill.levels || []).find((level) => level && String(level.level) === wanted) || null;
  }

  function renderMergedSkillAction(skill, levelValue) {
    const level = levelForSkill(skill, levelValue) || {};
    const values = [renderBlackboard(level.blackboard), renderSubDesc(level.subDesc)].filter(Boolean).join("");
    const desc = renderDescription(level.description || skill.description || "");
    if (!values && !desc) return "";
    return `<div class="gameplay-action-row">
      <div class="gameplay-action-title">${escapeHtml(skill.name || skill.id || "")}</div>
      ${desc}
      ${values}
    </div>`;
  }

  function renderSkillGroupPane(group, levelValue, active) {
    const actionRows = (group.skills || []).map((skill) => renderMergedSkillAction(skill, levelValue)).filter(Boolean).join("");
    const cost = renderUpgradeCost(levelUpForLevel({ level: levelValue }, group.levelUp || []));
    return `<div class="gameplay-level-pane gameplay-merged-skill-pane" data-level-label="${escapeHtml(levelLabel({ level: levelValue }))}"${active ? "" : " hidden"}>
      <div class="gameplay-action-group"><div class="gameplay-action-stack">${actionRows || `<span class="muted">-</span>`}</div></div>
      ${cost}
    </div>`;
  }

  function renderMergedSkillGroupLevels(group) {
    const levels = sortedSkillLevelsForGroup(group);
    if (!levels.length) return "";
    if (levels.length === 1) {
      return `<div class="gameplay-level-table">${renderSkillGroupPane(group, levels[0], true)}</div>`;
    }
    return `<div class="gameplay-level-slider-wrap" data-level-card>
      <div class="gameplay-level-slider-control">
        <span>${escapeHtml(text("selectedLevel"))}</span>
        <input class="gameplay-level-slider" type="range" min="0" max="${levels.length - 1}" step="1" value="0" aria-label="${escapeHtml(text("selectedLevel"))}">
        <output class="gameplay-level-slider-output">${escapeHtml(levelLabel({ level: levels[0] }))}</output>
      </div>
      <div class="gameplay-level-panes">${levels.map((level, index) => renderSkillGroupPane(group, level, index === 0)).join("")}</div>
    </div>`;
  }
  function renderCharacterPotentials(entry) {
    const potentialRows = (entry.potentials && entry.potentials.levels || []).map((row) => {
      const meta = [row.potentialEffectId, row.level ? `${text("level")} ${formatValue(row.level)}` : ""].filter(Boolean).join(" / ");
      const required = renderRequiredItems(row.requiredItem || []);
      const values = renderBlackboard(row.blackboard || []);
      return `<div class="gameplay-talent-level">
        <div class="gameplay-talent-level-title">${escapeHtml(row.name || `${text("potential")} ${formatValue(row.level === undefined || row.level === null ? "" : row.level)}`)}</div>
        <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
        ${renderDescription(row.description)}
        ${values}
        ${required ? `<div class="gameplay-subheading">${escapeHtml(text("requiredItems"))}</div>${required}` : ""}
      </div>`;
    }).join("");
    return potentialRows ? `<div class="gameplay-talent-levels">${potentialRows}</div>` : "";
  }
  function renderWeaponDetail(entry) {
    const facts = [
      fact(text("id"), entry.id, { mono: true }),
      fact(text("fileName"), entry.fileName || entry.title),
      fact(text("internalName"), entry.internalName),
      fact(text("rarity"), entry.rarity),
      fact(text("weaponType"), entry.weaponTypeLabel || entry.weaponType),
      fact(text("maxLevel"), entry.maxLv),
      fact(text("baseAtkMax"), entry.upgrade && entry.upgrade.baseAtkAtMax),
      fact(text("modelPath"), entry.modelPath, { mono: true }),
      fact(text("source"), `${entry.source && entry.source.table || ""} / ${entry.source && entry.source.id || ""}`, { mono: true }),
    ].filter(Boolean);
    const skills = (entry.skills || []).map((skill) => renderSkillCard(skill, { slider: true })).join("");
    return {
      facts,
      body: [
        section(text("weaponStats"), renderStats(entry.stats, statCostIndex(entry, "weapon"))),
        section(text("weaponSkills"), skills ? `<div class="gameplay-card-grid">${skills}</div>` : ""),
      ].join(""),
    };
  }
  function renderCharacterDetail(entry) {
    const facts = [
      fact(text("id"), entry.id, { mono: true }),
      fact(text("rarity"), entry.rarity),
      fact(text("profession"), entry.professionLabel || entry.profession),
      fact(text("element"), entry.elementLabel || entry.element),
      fact(text("weaponType"), entry.weaponTypeLabel || entry.weaponType),
      fact(text("defaultWeapon"), entry.defaultWeaponName || entry.defaultWeaponId),
      fact(text("source"), `${entry.source && entry.source.table || ""} / ${entry.source && entry.source.id || ""}`, { mono: true }),
    ].filter(Boolean);
    const groups = (entry.skillGroups || []).map((group) => {
      const actionIds = renderIdChips(group.actionSkillIds || []);
      const mergedLevels = renderMergedSkillGroupLevels(group);
      return `<section class="gameplay-group-card">
        <header>
          <div class="gameplay-group-title">${escapeHtml(group.name || group.id || "")}</div>
          <div class="gameplay-skill-meta">${escapeHtml([group.typeLabel, group.id].filter(Boolean).join(" / "))}</div>
        </header>
        ${renderDescription(group.description)}
        ${actionIds ? `<div class="gameplay-subheading">${escapeHtml(text("actionSkillIds"))}</div>${actionIds}` : ""}
        ${mergedLevels ? `<div class="gameplay-subheading">${escapeHtml(text("actionData"))}</div>${mergedLevels}` : ""}
      </section>`;
    }).join("");
    const talentGroups = renderTalentGroups(entry.talentGroups || []);
    const talentCards = (entry.talents || []).map(renderTalentCard).join("");
    return {
      facts,
      body: [
        section(text("characterStats"), renderStats(entry.stats, statCostIndex(entry, "character"))),
        section(text("characterSkills"), groups ? `<div class="gameplay-character-skill-grid">${groups}</div>` : ""),
        section(text("talents"), talentGroups || (talentCards ? `<div class="gameplay-card-grid">${talentCards}</div>` : "")),
        section(text("characterPotentials"), renderCharacterPotentials(entry)),
      ].join(""),
    };
  }
  function renderEquipmentSuit(entry) {
    const suit = entry.suit || {};
    const effects = (suit.effects || []).map((effect) => {
      const skill = effect.skill || {};
      const meta = [
        effect.equipCount ? `${text("equipCount")} ${formatValue(effect.equipCount)}` : "",
        effect.skillLevel ? `${text("level")} ${formatValue(effect.skillLevel)}` : "",
      ].filter(Boolean).join(" / ");
      return `<article class="gameplay-skill-card">
        <header>
          <div class="gameplay-skill-title">${escapeHtml(skill.name || suit.name || text("equipmentSuit"))}</div>
          <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
        </header>
        ${renderLevelRows(skill, { slider: true })}
      </article>`;
    }).join("");
    return effects ? `<div class="gameplay-card-grid">${effects}</div>` : "";
  }

  function renderEquipmentPropertyStats(stats) {
    const curves = (stats && stats.propertyCurves || []).filter((curve) => curve && (curve.rows || []).length);
    if (!curves.length) return renderStats(stats);
    const cards = curves.map((curve) => {
      const rows = (curve.rows || []).filter((row) => row && (row.attrs || []).length);
      if (!rows.length) return "";
      const body = rows.length > 1
        ? `<div class="gameplay-level-slider-wrap gameplay-stat-slider" data-level-card>
          <div class="gameplay-level-slider-control">
            <span>${escapeHtml(text("selectedLevel"))}</span>
            <input class="gameplay-level-slider" type="range" min="0" max="${rows.length - 1}" step="1" value="0" aria-label="${escapeHtml(text("selectedLevel"))}">
            <output class="gameplay-level-slider-output">${escapeHtml(statLevelLabel(rows[0]))}</output>
          </div>
          <div class="gameplay-level-panes">${rows.map((row, index) => renderStatPane(row, index === 0)).join("")}</div>
        </div>`
        : `<div class="gameplay-level-table"><div class="gameplay-level-row gameplay-stat-row">
          <div class="gameplay-level-num">${escapeHtml(statLevelLabel(rows[0]))}</div>
          <div class="gameplay-level-effect">${renderStatAttrs(rows[0]) || `<span class="muted">-</span>`}</div>
          <div class="gameplay-level-values"></div>
        </div></div>`;
      return `<article class="gameplay-skill-card gameplay-stat-card">
        <header>
          <div class="gameplay-skill-title">${escapeHtml(statAttrLabel(curve))}</div>
          <div class="gameplay-skill-meta">${escapeHtml(stats.source || "")}</div>
        </header>
        ${body}
      </article>`;
    }).filter(Boolean).join("");
    return cards ? `<div class="gameplay-equipment-property-grid">${cards}</div>` : "";
  }
  function renderEquipmentDetail(entry) {
    const facts = [
      fact(text("id"), entry.id, { mono: true }),
      fact(text("rarity"), entry.rarity),
      fact(text("partType"), entry.showingTypeLabel || entry.partTypeLabel || entry.partType),
      fact(text("minWearLevel"), entry.minWearLv),
      fact(text("domain"), entry.domainName || (entry.domain && entry.domain.name) || entry.domainId),
      fact(text("suit"), entry.suit && (entry.suit.name || entry.suit.id)),
      fact(text("source"), `${entry.source && entry.source.table || ""} / ${entry.source && entry.source.id || ""}`, { mono: true }),
    ].filter(Boolean);
    return {
      facts,
      body: [
        section(text("equipmentStats"), renderEquipmentPropertyStats(entry.stats)),
        section(text("equipmentSuit"), renderEquipmentSuit(entry)),
        section(text("equipmentFormula"), renderEquipmentFormula(entry)),
      ].join(""),
    };
  }
  function renderEnemyAbilities(entry) {
    const rows = (entry.abilities || []).map((ability) => {
      if (!ability) return "";
      return `<article class="gameplay-skill-card">
        <header>
          <div class="gameplay-skill-title">${escapeHtml(ability.name || ability.id || "")}</div>
          <div class="gameplay-skill-meta">${escapeHtml(ability.id || "")}</div>
        </header>
        ${renderDescription(ability.description)}
      </article>`;
    }).filter(Boolean).join("");
    return rows ? `<div class="gameplay-card-grid">${rows}</div>` : "";
  }

  function enemyModifierPairs(source) {
    return (source.attrModifiers || []).map((modifier) => {
      if (!modifier) return null;
      const label = [statAttrLabel(modifier), modifier.modifierType !== undefined ? `type ${formatValue(modifier.modifierType)}` : ""].filter(Boolean).join(" / ");
      return { label, value: modifier.value };
    }).filter(Boolean);
  }

  function renderEnemyModifierRows(entry, diffLabels) {
    return renderChipPairs(enemyModifierPairs(entry), { diffLabels });
  }

  function variantDetailPairs(variant) {
    return [
      { label: text("attrTemplateId"), value: variant.attrTemplateId },
      { label: text("modelId"), value: variant.modelId },
      { label: text("aiTemplateId"), value: variant.aiTemplateId },
      { label: text("displayType"), value: variant.displayTypeLabel || variant.displayType },
      { label: text("dangerous"), value: variant.isDangerous ? text("dangerous") : "" },
    ];
  }

  // Labels whose value is not shared by every variant (differs, or is missing
  // from some). Used to highlight what actually changes between enemy variants.
  function variantDiffLabels(variants) {
    const info = new Map();
    variants.forEach((variant) => {
      const pairs = [...variantDetailPairs(variant), ...enemyModifierPairs(variant)];
      for (const pair of pairs) {
        const label = String(pair.label || "");
        if (!label || pair.value === undefined || pair.value === null || pair.value === "") continue;
        if (!info.has(label)) info.set(label, { values: new Set(), present: 0 });
        const rec = info.get(label);
        rec.values.add(String(pair.value));
        rec.present += 1;
      }
    });
    const diff = new Set();
    for (const [label, rec] of info) {
      if (rec.values.size > 1 || rec.present !== variants.length) diff.add(label);
    }
    return diff;
  }

  // Born-buff ids not present on every variant.
  function variantBuffDiff(variants) {
    const counts = new Map();
    for (const variant of variants) {
      for (const buff of new Set(variant.bornBuffs || [])) counts.set(buff, (counts.get(buff) || 0) + 1);
    }
    const diff = new Set();
    for (const [buff, count] of counts) if (count !== variants.length) diff.add(buff);
    return diff;
  }

  function renderEnemyDetails(entry) {
    const blocks = [];
    const tags = renderChipPairs((entry.tags || []).map((tag) => ({ label: tag.label || tag.id, value: tag.id })));
    if (tags) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("tags"))}</div>${tags}`);
    const drops = renderMaterialChips(entry.dropItems || []);
    if (drops) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("dropItems"))}</div>${drops}`);
    const distributions = renderIdChips(entry.distributionIds || []);
    if (distributions) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("distribution"))}</div>${distributions}`);
    return blocks.join("");
  }

  function variantPaneBody(variant, diffLabels, buffDiff) {
    const details = renderChipPairs(variantDetailPairs(variant), { diffLabels });
    const buffs = renderIdChips(variant.bornBuffs || [], { highlight: buffDiff });
    const modifiers = renderEnemyModifierRows(variant, diffLabels);
    const wiki = variant.storyWikiKey
      ? `<a class="gameplay-detail-tag gameplay-detail-wiki-link gameplay-wiki-link" href="${escapeHtml(storyWikiHrefForKey(variant.storyWikiKey))}"><span>${escapeHtml(text("storyWiki"))}</span></a>`
      : "";
    return `<div class="gameplay-skill-meta">${escapeHtml([variant.id, variant.displayTypeLabel].filter(Boolean).join(" / "))}</div>
      ${wiki ? `<div class="gameplay-variant-links">${wiki}</div>` : ""}
      ${details}
      ${buffs ? `<div class="gameplay-subheading">${escapeHtml(text("bornBuffs"))}</div>${buffs}` : ""}
      ${modifiers ? `<div class="gameplay-subheading">${escapeHtml(text("attrModifiers"))}</div>${modifiers}` : ""}`;
  }

  function variantChipLabel(variant, index) {
    return variant.name || variant.displayTypeLabel || variant.id || `#${index + 1}`;
  }

  function renderEnemyVariants(entry) {
    const variants = (entry.variants || []).filter(Boolean);
    if (!variants.length) return "";
    // A single variant renders inline; multiple variants become a switcher so the
    // user can flip between them (their modifiers / base numbers differ), with the
    // differing fields highlighted.
    if (variants.length === 1) {
      const v = variants[0];
      return `<article class="gameplay-skill-card gameplay-enemy-variant-card">
        <header><div class="gameplay-skill-title">${escapeHtml(v.name || v.id || "")}</div></header>
        ${variantPaneBody(v, null, null)}
      </article>`;
    }
    const diffLabels = variantDiffLabels(variants);
    const buffDiff = variantBuffDiff(variants);
    const chips = variants.map((v, i) =>
      `<button type="button" class="gameplay-variant-chip${i === 0 ? " is-active" : ""}" data-variant-index="${i}">${escapeHtml(variantChipLabel(v, i))}</button>`).join("");
    const panes = variants.map((v, i) =>
      `<div class="gameplay-variant-pane" data-variant-index="${i}"${i === 0 ? "" : " hidden"}>${variantPaneBody(v, diffLabels, buffDiff)}</div>`).join("");
    return `<div class="gameplay-variant-switch" data-variant-card>
      <div class="gameplay-variant-chips">${chips}</div>
      <div class="gameplay-variant-panes">${panes}</div>
    </div>`;
  }

  function bindVariantSwitches(root) {
    root.querySelectorAll(".gameplay-variant-switch").forEach((card) => {
      const chips = [...card.querySelectorAll(".gameplay-variant-chip")];
      const panes = [...card.querySelectorAll(".gameplay-variant-pane")];
      chips.forEach((chip) => {
        chip.addEventListener("click", () => {
          const index = Number(chip.dataset.variantIndex || 0);
          chips.forEach((c) => c.classList.toggle("is-active", Number(c.dataset.variantIndex) === index));
          panes.forEach((p) => { p.hidden = Number(p.dataset.variantIndex) !== index; });
        });
      });
    });
  }

  function renderEnemyCombatValues(entry) {
    const blocks = [];
    const damage = renderChipPairs(entry.damageScalars || []);
    if (damage) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("damageScalars"))}</div>${damage}`);
    const resilience = renderChipPairs(entry.resilience || []);
    if (resilience) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("resilience"))}</div>${resilience}`);
    const independent = renderStatAttrs(entry.independentAttributes || []);
    if (independent) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("independentAttributes"))}</div>${independent}`);
    const modifiers = renderEnemyModifierRows(entry);
    if (modifiers) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("attrModifiers"))}</div>${modifiers}`);
    const bornBuffs = renderIdChips(entry.bornBuffs || []);
    if (bornBuffs) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("bornBuffs"))}</div>${bornBuffs}`);
    return blocks.join("");
  }

  function renderEnemyDetail(entry) {
    const facts = [
      fact(text("id"), entry.id, { mono: true }),
      fact(text("templateId"), entry.templateId, { mono: true }),
      fact(text("attrTemplateId"), entry.attrTemplateId, { mono: true }),
      fact(text("displayType"), entry.displayTypeLabel || entry.displayType),
      fact(text("variantCount"), entry.variantCount || ((entry.variants || []).length || "")),
      fact(text("nickname"), entry.nickname),
      fact(text("modelId"), entry.modelId, { mono: true }),
      fact(text("aiTemplateId"), entry.aiTemplateId, { mono: true }),
      fact(text("dangerous"), entry.isDangerous ? text("dangerous") : ""),
      fact(text("source"), `${entry.source && entry.source.table || ""} / ${entry.source && entry.source.id || ""}`, { mono: true }),
    ].filter(Boolean);
    return {
      facts,
      body: [
        section(text("enemyVariants"), renderEnemyVariants(entry)),
        section(text("enemyStats"), renderStats(entry.stats)),
        section(text("enemyAbilities"), renderEnemyAbilities(entry)),
        section(text("combatValues"), renderEnemyCombatValues(entry)),
        section(text("enemyDetails"), renderEnemyDetails(entry)),
      ].join(""),
    };
  }

  function renderItemUse(entry) {
    const use = entry.useData || {};
    if (!use.description && !(use.actions || []).length) return "";
    const details = renderChipPairs([
      { label: text("duration"), value: use.duration },
      { label: text("effectType"), value: use.effectType },
      { label: text("uiType"), value: use.uiType },
      { label: text("targetNumType"), value: use.targetNumType },
      { label: text("persistentBuff"), value: use.isPersistentBuff ? "true" : "" },
      { label: text("valuableDepot"), value: use.isValuableDepot ? "true" : "" },
      { label: text("stackKey"), value: use.stackingKey },
    ]);
    return [renderDescription(use.description), details].filter(Boolean).join("");
  }

  function renderItemActions(entry) {
    const rows = (((entry.useData || {}).actions) || []).map((action, index) => {
      if (!action) return "";
      const title = action.buffId || action.skillId || `${text("actionData")} ${index + 1}`;
      const details = renderChipPairs([
        { label: text("useType"), value: action.useType },
        { label: text("buffId"), value: action.buffId },
        { label: text("skillId"), value: action.skillId },
        { label: text("skillPath"), value: action.skillPath },
      ]);
      const buffValues = renderBlackboard(action.buffBlackboard || []);
      const skillValues = renderBlackboard(action.skillBlackboard || []);
      return `<article class="gameplay-skill-card">
        <header>
          <div class="gameplay-skill-title">${escapeHtml(title)}</div>
          <div class="gameplay-skill-meta">${escapeHtml(`${text("actionData")} ${index + 1}`)}</div>
        </header>
        ${details}
        ${buffValues ? `<div class="gameplay-subheading">${escapeHtml(text("buffId"))}</div>${buffValues}` : ""}
        ${skillValues ? `<div class="gameplay-subheading">${escapeHtml(text("skillId"))}</div>${skillValues}` : ""}
      </article>`;
    }).filter(Boolean).join("");
    return rows ? `<div class="gameplay-card-grid">${rows}</div>` : "";
  }

  function renderItemRewardCards(entry) {
    const chest = entry.chestData || {};
    const blocks = [];
    const chestDetails = renderChipPairs([
      { label: text("chestType"), value: chest.type },
      { label: text("selectedCount"), value: chest.selectedCount },
    ]);
    if (chestDetails) blocks.push(chestDetails);
    const randomItems = renderMaterialChips(chest.randomItems || []);
    if (randomItems) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("randomItems"))}</div>${randomItems}`);
    const rewardCards = (chest.rewards || []).map((reward) => {
      if (!reward) return "";
      const fixed = renderMaterialChips(reward.items || []);
      const probable = renderMaterialChips(reward.probableItems || []);
      return `<article class="gameplay-skill-card">
        <header>
          <div class="gameplay-skill-title">${escapeHtml(reward.id || text("rewardId"))}</div>
          <div class="gameplay-skill-meta">${escapeHtml(text("rewardId"))}</div>
        </header>
        ${fixed ? `<div class="gameplay-subheading">${escapeHtml(text("fixedRewards"))}</div>${fixed}` : ""}
        ${probable ? `<div class="gameplay-subheading">${escapeHtml(text("probableRewards"))}</div>${probable}` : ""}
      </article>`;
    }).filter(Boolean).join("");
    if (rewardCards) blocks.push(`<div class="gameplay-card-grid">${rewardCards}</div>`);
    return blocks.join("");
  }

  function renderItemDetail(entry) {
    const facts = [
      fact(text("id"), entry.id, { mono: true }),
      fact(text("rarity"), entry.rarity),
      fact(text("itemType"), entry.itemTypeLabel || entry.itemType),
      fact(text("showingType"), entry.showingTypeLabel || entry.showingType),
      fact(text("useCategory"), entry.useCategory),
      fact(text("iconId"), entry.iconId || entry.iconCompositeId, { mono: true }),
      fact(text("maxStack"), entry.maxStackCount),
      fact(text("backpackStack"), entry.maxBackpackStackCount),
      fact(text("source"), `${entry.source && entry.source.table || ""} / ${entry.source && entry.source.id || ""}`, { mono: true }),
    ].filter(Boolean);
    const description = [renderDescription(entry.description), renderDescription(entry.decoDescription)].filter(Boolean).join("");
    return {
      facts,
      body: [
        section(text("description"), description),
        section(text("itemUse"), renderItemUse(entry)),
        section(text("itemActions"), renderItemActions(entry)),
        section(text("itemRewards"), renderItemRewardCards(entry)),
      ].join(""),
    };
  }
  function renderEquipmentFormula(entry) {
    const formula = entry.formula || {};
    if (!formula.formulaName && !(formula.costs || []).length) return "";
    const details = renderChipPairs([
      { label: text("formula"), value: formula.formulaName || formula.name },
      { label: text("pack"), value: formula.packName },
      { label: text("unlock"), value: formula.unlockName || formula.unlockValue || formula.unlockType },
    ]);
    const costs = renderMaterialChips(formula.costs || []);
    return `<article class="gameplay-skill-card">
      <header>
        <div class="gameplay-skill-title">${escapeHtml(formula.formulaName || formula.name || text("equipmentFormula"))}</div>
        <div class="gameplay-skill-meta">${escapeHtml([formula.packName, formula.unlockName].filter(Boolean).join(" / "))}</div>
      </header>
      ${details}
      ${costs ? `<div class="gameplay-subheading">${escapeHtml(text("materials"))}</div>${costs}` : ""}
    </article>`;
  }
  function syncLevelCard(input) {
    const card = input.closest("[data-level-card]");
    if (!card) return;
    const index = Number(input.value || 0);
    const panes = [...card.querySelectorAll(".gameplay-level-pane")];
    panes.forEach((pane, paneIndex) => {
      pane.hidden = paneIndex !== index;
    });
    const output = card.querySelector(".gameplay-level-slider-output");
    if (output && panes[index]) output.textContent = panes[index].dataset.levelLabel || "";
  }
  function syncLevelSlider(input) {
    const group = input.closest("[data-linked-level-group]");
    const sliders = group ? [...group.querySelectorAll(".gameplay-level-slider")] : [input];
    const requested = Number(input.value || 0);
    const inputMax = Number(input.max || 0);
    saveLevelFraction(inputMax > 0 ? requested / inputMax : 1);
    sliders.forEach((slider) => {
      const max = Number(slider.max || requested);
      slider.value = String(Math.max(0, Math.min(requested, max)));
      syncLevelCard(slider);
    });
  }

  function bindLevelSliders(root) {
    root.querySelectorAll(".gameplay-level-slider").forEach((input) => {
      // Default to the cached position (max level on first use).
      input.value = String(sliderIndexForFraction(Number(input.max || 0)));
      input.addEventListener("input", () => syncLevelSlider(input));
      syncLevelCard(input);
    });
  }

  function syncLocateCurrentButton() {
    const button = gp$("#gameplay-reveal-current");
    if (button) button.disabled = !STATE.selected;
  }

  function revealSelectedInList() {
    if (!STATE.selected) return false;
    const list = gp$("#gameplay-list");
    if (!list) return false;
    // Expand the selected entry's group if the user had collapsed it.
    if (STATE.collapsedKinds.has(STATE.selected.kind)) {
      STATE.collapsedKinds.delete(STATE.selected.kind);
      persistCollapsedKinds();
      renderList();
    }
    const key = `${STATE.selected.kind}:${STATE.selected.id}`;
    const row = [...list.querySelectorAll(".gameplay-row")].find((candidate) => candidate.dataset.key === key);
    if (!row) return false;
    row.scrollIntoView({ block: "center", behavior: "smooth" });
    if (isMobileLayout()) {
      const left = gp$("#gameplay-left");
      if (left) left.scrollIntoView({ block: "start", behavior: "smooth" });
    }
    return true;
  }

  function renderDetail(entry) {
    const empty = gp$("#gameplay-empty");
    const detail = gp$("#gameplay-detail");
    if (!entry || !detail) {
      if (empty) empty.hidden = false;
      if (detail) detail.hidden = true;
      syncLocateCurrentButton();
      return;
    }
    if (empty) empty.hidden = true;
    detail.hidden = false;
    const title = entry.title || entry.id || "";
    gp$("#gameplay-detail-title").innerHTML = highlightText(title);
    const rendered = entry.kind === "weapon" ? renderWeaponDetail(entry) : entry.kind === "equipment" ? renderEquipmentDetail(entry) : entry.kind === "enemy" ? renderEnemyDetail(entry) : entry.kind === "item" ? renderItemDetail(entry) : renderCharacterDetail(entry);
    // The header already shows the title; drop any fact that merely repeats it
    // (e.g. file/internal name equal to the title) to avoid duplicated info.
    const detailTags = dedupeDetailTags([
      fact(text("kind"), kindLabel(entry.kind), { kind: entry.kind }),
      ...(rendered.facts || []),
    ].filter((tag) => tag && String(tag.value) !== title));
    // Facts render as a conv-meta-style "label=value | ..." text line.
    gp$("#gameplay-detail-meta").textContent = detailTags
      .map((tag) => `${tag.label}=${formatValue(tag.value)}`).join(" | ");
    // The story-wiki link sits in its own slot, mirroring the story page's
    // gameplay link under the header meta.
    const wikiSlot = gp$("#gameplay-detail-wiki");
    if (wikiSlot) {
      const wiki = renderStoryWikiLink(entry);
      wikiSlot.innerHTML = wiki;
      wikiSlot.hidden = !wiki;
    }
    gp$("#gameplay-detail-body").innerHTML = rendered.body || "";
    bindLevelSliders(detail);
    bindVariantSwitches(detail);
    syncLocateCurrentButton();
  }

  function renderListNote(message) {
    const list = gp$("#gameplay-list");
    if (list) list.innerHTML = `<div class="gameplay-list-note">${escapeHtml(message)}</div>`;
    gp$("#gameplay-shown").textContent = "0";
    gp$("#gameplay-total").textContent = formatNumber(STATE.entries.length || 0);
    renderDetail(null);
  }

  function rowPathText(entry) {
    if (entry.kind === "weapon") return entry.fileName || entry.id || "";
    if (entry.kind === "enemy" || entry.kind === "item") return entry.fileName || entry.title || entry.id || "";
    return entry.id || "";
  }

  // A single list row, copying the story file-list item style: a colored kind
  // badge chip, then the readable name, with the subtitle below.
  function renderRow(entry, selectedId) {
    const key = `${entry.kind}:${entry.id}`;
    const selected = key === selectedId ? " is-selected" : "";
    const badgeClass = KIND_BADGE_CLASS[entry.kind] || "";
    return `<button class="gameplay-row${selected}" type="button" data-key="${escapeHtml(key)}">
      <div class="gameplay-row-line1">
        <span class="badge ${badgeClass}">${escapeHtml(kindLabel(entry.kind))}</span>
        <span class="gameplay-row-name">${highlightText(entry.title || entry.id || "")}</span>
      </div>
      <div class="gameplay-row-meta">${highlightText(entrySubtitle(entry) || rowPathText(entry) || "")}</div>
    </button>`;
  }

  function renderList() {
    const list = gp$("#gameplay-list");
    if (!list) return;
    gp$("#gameplay-shown").textContent = formatNumber(STATE.filtered.length);
    gp$("#gameplay-total").textContent = formatNumber(STATE.entries.length);
    if (!STATE.filtered.length) {
      renderListNote(text(STATE.entries.length ? "noResults" : "noData"));
      return;
    }

    const selectedId = STATE.selected && `${STATE.selected.kind}:${STATE.selected.id}`;
    // While searching, force every group open so matches are never hidden.
    const searching = (STATE.searchTokens || []).length > 0;

    // Bucket by data type (kind), preserving the sorted order within each group.
    const buckets = new Map();
    for (const entry of STATE.filtered) {
      const kind = entry.kind || "other";
      if (!buckets.has(kind)) buckets.set(kind, []);
      buckets.get(kind).push(entry);
    }
    const kinds = [...buckets.keys()].sort((a, b) => kindRank(a) - kindRank(b) || a.localeCompare(b));

    list.innerHTML = kinds.map((kind) => {
      const entries = buckets.get(kind);
      const collapsed = !searching && STATE.collapsedKinds.has(kind);
      const body = collapsed ? "" : entries.map((entry) => renderRow(entry, selectedId)).join("");
      return `<section class="gameplay-list-group${collapsed ? " is-collapsed" : ""}">
        <button class="gameplay-list-group-header" type="button" data-group="${escapeHtml(kind)}" aria-expanded="${!collapsed}">
          <span class="gameplay-group-twisty" aria-hidden="true"></span>
          <span class="gameplay-kind-badge" data-kind="${escapeHtml(kind)}">${escapeHtml(kindLabel(kind))}</span>
          <span class="gameplay-group-count">${formatNumber(entries.length)}</span>
        </button>
        <div class="gameplay-list-group-body"${collapsed ? " hidden" : ""}>${body}</div>
      </section>`;
    }).join("");

    list.querySelectorAll(".gameplay-list-group-header").forEach((header) => {
      header.addEventListener("click", () => toggleKindGroup(header.dataset.group || ""));
    });
    list.querySelectorAll(".gameplay-row").forEach((row) => {
      row.addEventListener("click", () => {
        const key = row.dataset.key || "";
        STATE.selected = STATE.filtered.find((entry) => `${entry.kind}:${entry.id}` === key) || null;
        renderList();
        renderDetail(STATE.selected);
      });
    });

    if (!STATE.selected || !STATE.filtered.includes(STATE.selected)) {
      STATE.selected = STATE.filtered[0] || null;
    }
    renderDetail(STATE.selected);
  }

  function countBy(entries, getter) {
    const map = new Map();
    for (const entry of entries) {
      const value = getter(entry);
      if (!value) continue;
      map.set(value, (map.get(value) || 0) + 1);
    }
    return map;
  }


  function jobFilterKey(entry) {
    if (!entry || entry.kind !== "character") return "";
    return String(entry.profession !== undefined && entry.profession !== null && entry.profession !== "" ? entry.profession : (entry.professionLabel || ""));
  }

  function jobFilterLabel(entry) {
    return entry && (entry.professionLabel || entry.profession || "");
  }

  function characterPropertyFilterKey(entry) {
    if (!entry || entry.kind !== "character") return "";
    return String(entry.element || entry.elementLabel || "");
  }

  function characterPropertyFilterLabel(entry) {
    return entry && (entry.elementLabel || entry.element || "");
  }

  function rarityFilterKey(entry) {
    return entry && entry.rarity !== undefined && entry.rarity !== null && entry.rarity !== "" ? String(entry.rarity) : "";
  }

  function rarityFilterLabel(value) {
    return `${text("rareLevel")} ${formatValue(value)}`;
  }

  function weaponTypeFilterKey(entry) {
    if (!entry || entry.kind !== "weapon") return "";
    return String(entry.weaponTypeKey || entry.weaponTypeLabel || entry.weaponType || "");
  }

  function weaponTypeFilterLabel(entry) {
    return entry && (entry.weaponTypeLabel || entry.weaponTypeKey || entry.weaponType || "");
  }

  function equipmentTypeFilterKey(entry) {
    if (!entry || entry.kind !== "equipment") return "";
    return String(entry.showingType !== undefined && entry.showingType !== null && entry.showingType !== "" ? entry.showingType : (entry.showingTypeLabel || entry.partTypeLabel || entry.partType || ""));
  }

  function equipmentTypeFilterLabel(entry) {
    return entry && (entry.showingTypeLabel || entry.partTypeLabel || entry.partType || "");
  }

  function enemyTypeFilterKey(entry) {
    if (!entry || entry.kind !== "enemy") return "";
    return String(entry.displayType !== undefined && entry.displayType !== null && entry.displayType !== "" ? entry.displayType : (entry.displayTypeLabel || ""));
  }

  function enemyTypeFilterLabel(entry) {
    return entry && (entry.displayTypeLabel || entry.displayType || "");
  }

  function listTypeLabel(entry) {
    if (!entry) return "";
    if (entry.kind === "enemy") return enemyTypeFilterLabel(entry);
    if (entry.kind === "item") return entry.showingTypeLabel || entry.itemTypeLabel || "";
    if (entry.kind === "weapon") return weaponTypeFilterLabel(entry);
    if (entry.kind === "equipment") return equipmentTypeFilterLabel(entry);
    if (entry.kind === "character") return characterPropertyFilterLabel(entry) || jobFilterLabel(entry);
    return "";
  }

  function listGroupLabel(entry) {
    return [kindLabel(entry && entry.kind), listTypeLabel(entry)].filter(Boolean).join(" / ");
  }

  function typeFiltersMatch(entry) {
    const hasCharacterProperties = STATE.filters.characterProperties.size > 0;
    const hasWeaponTypes = STATE.filters.weaponTypes.size > 0;
    const hasEquipmentTypes = STATE.filters.equipmentTypes.size > 0;
    const hasEnemyTypes = STATE.filters.enemyTypes.size > 0;
    if (!hasCharacterProperties && !hasWeaponTypes && !hasEquipmentTypes && !hasEnemyTypes) return true;
    if (entry && entry.kind === "character") return hasCharacterProperties && STATE.filters.characterProperties.has(characterPropertyFilterKey(entry));
    if (entry && entry.kind === "weapon") return hasWeaponTypes && STATE.filters.weaponTypes.has(weaponTypeFilterKey(entry));
    if (entry && entry.kind === "equipment") return hasEquipmentTypes && STATE.filters.equipmentTypes.has(equipmentTypeFilterKey(entry));
    if (entry && entry.kind === "enemy") return hasEnemyTypes && STATE.filters.enemyTypes.has(enemyTypeFilterKey(entry));
    return false;
  }
  function buildFilterChips() {
    const kindCounts = countBy(STATE.entries, (entry) => entry.kind);
    const jobCounts = countBy(STATE.entries, (entry) => jobFilterKey(entry));
    const propertyCounts = countBy(STATE.entries, (entry) => characterPropertyFilterKey(entry));
    const weaponTypeCounts = countBy(STATE.entries, (entry) => weaponTypeFilterKey(entry));
    const equipmentTypeCounts = countBy(STATE.entries, (entry) => equipmentTypeFilterKey(entry));
    const enemyTypeCounts = countBy(STATE.entries, (entry) => enemyTypeFilterKey(entry));
    const rarityCounts = countBy(STATE.entries, (entry) => rarityFilterKey(entry));
    const jobLabels = new Map(STATE.entries.map((entry) => [jobFilterKey(entry), jobFilterLabel(entry)]).filter(([value]) => value));
    const propertyLabels = new Map(STATE.entries.map((entry) => [characterPropertyFilterKey(entry), characterPropertyFilterLabel(entry)]).filter(([value]) => value));
    const weaponTypeLabels = new Map(STATE.entries.map((entry) => [weaponTypeFilterKey(entry), weaponTypeFilterLabel(entry)]).filter(([value]) => value));
    const equipmentTypeLabels = new Map(STATE.entries.map((entry) => [equipmentTypeFilterKey(entry), equipmentTypeFilterLabel(entry)]).filter(([value]) => value));
    const enemyTypeLabels = new Map(STATE.entries.map((entry) => [enemyTypeFilterKey(entry), enemyTypeFilterLabel(entry)]).filter(([value]) => value));
    const kindItems = [...kindCounts.keys()].sort((a, b) => kindRank(a) - kindRank(b) || a.localeCompare(b)).map((value) => ({ value, label: kindLabel(value), count: kindCounts.get(value), className: KIND_CHIP_CLASS[value] || "kind-chip" }));
    const jobItems = [...jobCounts.keys()].sort((a, b) => String(jobLabels.get(a) || a).localeCompare(String(jobLabels.get(b) || b))).map((value) => ({ value, label: jobLabels.get(value) || value, count: jobCounts.get(value) }));
    const propertyItems = [...propertyCounts.keys()].sort((a, b) => String(propertyLabels.get(a) || a).localeCompare(String(propertyLabels.get(b) || b))).map((value) => ({ value, label: propertyLabels.get(value) || value, count: propertyCounts.get(value) }));
    const weaponTypeItems = [...weaponTypeCounts.keys()].sort((a, b) => String(weaponTypeLabels.get(a) || a).localeCompare(String(weaponTypeLabels.get(b) || b))).map((value) => ({ value, label: weaponTypeLabels.get(value) || value, count: weaponTypeCounts.get(value) }));
    const equipmentTypeItems = [...equipmentTypeCounts.keys()].sort((a, b) => String(equipmentTypeLabels.get(a) || a).localeCompare(String(equipmentTypeLabels.get(b) || b))).map((value) => ({ value, label: equipmentTypeLabels.get(value) || value, count: equipmentTypeCounts.get(value) }));
    const enemyTypeItems = [...enemyTypeCounts.keys()].sort((a, b) => ((ENEMY_TYPE_RANK[a] ?? 99) - (ENEMY_TYPE_RANK[b] ?? 99)) || String(enemyTypeLabels.get(a) || a).localeCompare(String(enemyTypeLabels.get(b) || b))).map((value) => ({ value, label: enemyTypeLabels.get(value) || value, count: enemyTypeCounts.get(value) }));
    const rarityItems = [...rarityCounts.keys()].sort((a, b) => Number(b) - Number(a)).map((value) => ({ value, label: rarityFilterLabel(value), count: rarityCounts.get(value) }));
    window.WebUI.filters.buildChips("#gameplay-kind-filter", kindItems, {
      active: STATE.filters.kinds,
      onToggle: () => applyFilters(),
    });
    window.WebUI.filters.buildChips("#gameplay-job-filter", jobItems, {
      active: STATE.filters.jobs,
      onToggle: () => applyFilters(),
    });
    window.WebUI.filters.buildChips("#gameplay-character-property-filter", propertyItems, {
      active: STATE.filters.characterProperties,
      onToggle: () => applyFilters(),
    });
    window.WebUI.filters.buildChips("#gameplay-weapon-type-filter", weaponTypeItems, {
      active: STATE.filters.weaponTypes,
      onToggle: () => applyFilters(),
    });
    window.WebUI.filters.buildChips("#gameplay-equipment-type-filter", equipmentTypeItems, {
      active: STATE.filters.equipmentTypes,
      onToggle: () => applyFilters(),
    });
    window.WebUI.filters.buildChips("#gameplay-enemy-type-filter", enemyTypeItems, {
      active: STATE.filters.enemyTypes,
      onToggle: () => applyFilters(),
    });
    window.WebUI.filters.buildChips("#gameplay-rarity-filter", rarityItems, {
      active: STATE.filters.rarities,
      onToggle: () => applyFilters(),
    });
  }
  function kindRank(kind) {
    const index = KIND_ORDER.indexOf(kind);
    return index === -1 ? KIND_ORDER.length : index;
  }

  function enemyTypeRank(entry) {
    return ENEMY_TYPE_RANK[enemyTypeFilterKey(entry)] ?? 99;
  }

  function compareGameplayEntries(a, b) {
    const ak = kindRank(a.kind);
    const bk = kindRank(b.kind);
    if (ak !== bk) return ak - bk;
    // Within enemies, order by display type (领袖 > 头目 > 精英 > 进阶 > 普通).
    if (a.kind === "enemy" && b.kind === "enemy") {
      const ae = enemyTypeRank(a);
      const be = enemyTypeRank(b);
      if (ae !== be) return ae - be;
    }
    const ag = listGroupLabel(a);
    const bg = listGroupLabel(b);
    if (ag !== bg) return ag.localeCompare(bg);
    const ar = Number(a.rarity || 0);
    const br = Number(b.rarity || 0);
    if (ar !== br) return br - ar;
    return String(a.title || a.id || "").localeCompare(String(b.title || b.id || ""));
  }

  function applyFilters() {
    const tokens = parseQuery(gp$("#gameplay-q") && gp$("#gameplay-q").value);
    const scores = new Map();
    STATE.searchTokens = tokens;
    STATE.filtered = STATE.entries.filter((entry) => {
      if (STATE.filters.kinds.size && !STATE.filters.kinds.has(entry.kind)) return false;
      if (STATE.filters.jobs.size && !STATE.filters.jobs.has(jobFilterKey(entry))) return false;
      if (STATE.filters.rarities.size && !STATE.filters.rarities.has(rarityFilterKey(entry))) return false;
      if (!typeFiltersMatch(entry)) return false;
      if (tokens.length) {
        const score = queryScore([entry.search, entry.title, entry.id, entry.group, entry.subtitle], tokens);
        if (score <= 0) return false;
        scores.set(entry, score);
      }
      return true;
    });
    // A multi-word query ranks entries by keyword-match count first; ties (and
    // single-word / no query) fall back to the stable kind/type ordering.
    const rankByScore = tokens.length > 1;
    STATE.filtered.sort((a, b) => {
      if (rankByScore) {
        const delta = (scores.get(b) || 0) - (scores.get(a) || 0);
        if (delta) return delta;
      }
      return compareGameplayEntries(a, b);
    });
    if (STATE.selected && !STATE.filtered.includes(STATE.selected)) STATE.selected = null;
    renderList();
  }

  function resetFilters() {
    const q = gp$("#gameplay-q");
    if (q) q.value = "";
    STATE.filters.kinds.clear();
    STATE.filters.jobs.clear();
    STATE.filters.characterProperties.clear();
    STATE.filters.weaponTypes.clear();
    STATE.filters.equipmentTypes.clear();
    STATE.filters.enemyTypes.clear();
    STATE.filters.rarities.clear();
    buildFilterChips();
    applyFilters();
  }

  function applyUiStrings() {
    const pairs = [
      ["#gameplay-tab", "tab"],
      ["#gameplay-title", "title"],
      ["#gameplay-count-label", "countLabel"],
      ["#gameplay-basic-filter-label", "basicFilters"],
      ["#gameplay-kind-label", "kind"],
      ["#gameplay-job-label", "job"],
      ["#gameplay-character-property-label", "characterPropertyFilter"],
      ["#gameplay-weapon-type-label", "weaponTypeFilter"],
      ["#gameplay-equipment-type-label", "equipmentTypeFilter"],
      ["#gameplay-enemy-type-label", "enemyTypeFilter"],
      ["#gameplay-rarity-label", "rareLevel"],
      ["#gameplay-reset", "reset"],
      ["#gameplay-reveal-current", "locateCurrent"],
      ["#gameplay-list-meta-label", "listUnit"],
      ["#gameplay-empty", "empty"],
    ];
    for (const [selector, key] of pairs) {
      const el = gp$(selector);
      if (el) el.textContent = text(key);
    }
    const q = gp$("#gameplay-q");
    if (q) q.placeholder = text("search");
    ensurePanelToggle().sync();
    buildFilterChips();
    if (STATE.entries.length) renderList();
  }
  async function loadGameplay(force = false) {
    const language = currentLanguage();
    if (!force && STATE.index && STATE.language === language) return;
    if (STATE.loading) return STATE.loading;
    STATE.language = language;
    window.WebUI.showLoader?.("gameplay", text("loading"));
    STATE.loading = (async () => {
      try {
        const res = await fetchWithProgress(gameplayDataPath(language), {
          onProgress: (ratio) => window.WebUI.updateLoader?.("gameplay", ratio, text("loading")),
        });
        if (!res.ok) {
          if (res.status === 404) throw new Error(text("noData"));
          throw new Error(`${res.status} ${res.statusText}`.trim());
        }
        const data = await res.json();
        STATE.index = data || {};
        STATE.entries = Array.isArray(data.entries) ? data.entries : [];
        STATE.selected = findGameplayEntry(requestedGameplaySelection());
        gp$("#gameplay-count").textContent = formatNumber(STATE.entries.length);
        buildFilterChips();
        applyFilters();
      } catch (err) {
        STATE.index = null;
        STATE.entries = [];
        STATE.filtered = [];
        gp$("#gameplay-count").textContent = "0";
        renderListNote(text("loadError", { message: err && err.message ? err.message : String(err) }));
      } finally {
        window.WebUI.hideLoader?.("gameplay");
        STATE.loading = null;
      }
    })();
    return STATE.loading;
  }

  function maybeLoadGameplay(force = false) {
    if (isGameplayActive()) loadGameplay(force);
  }

  function bindEvents() {
    gp$("#gameplay-q")?.addEventListener("input", () => applyFilters());
    gp$("#gameplay-reset")?.addEventListener("click", () => resetFilters());
    gp$("#gameplay-reveal-current")?.addEventListener("click", () => revealSelectedInList());
    window.addEventListener("webui:view-changed", (event) => {
      if (event.detail && event.detail.view === "gameplay") loadGameplay();
    });
    window.addEventListener("hashchange", () => maybeLoadGameplay());
    window.addEventListener("webui:language-changed", (event) => {
      STATE.language = String((event.detail && event.detail.language) || currentLanguage()).toUpperCase();
      if (isGameplayActive()) loadGameplay(true);
    });
    window.addEventListener("webui:ui-locale-changed", (event) => {
      STATE.uiLocale = normalizeUiLocale(event.detail && event.detail.locale) || STATE.uiLocale;
      applyUiStrings();
    });
  }

  function init() {
    if (!gp$("#gameplay-app")) return;
    STATE.uiLocale = resolveInitialUiLocale();
    STATE.language = currentLanguage();
    STATE.collapsedKinds = loadCollapsedKinds();
    STATE.levelFraction = loadLevelFraction();
    ensurePanelToggle();
    bindEvents();
    applyUiStrings();
    maybeLoadGameplay();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
