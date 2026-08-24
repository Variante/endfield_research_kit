(() => {
  const FILTER_PANEL_STORAGE_KEY = "gameplay_filters_collapsed";
  const COLLAPSED_KINDS_STORAGE_KEY = "gameplay_collapsed_kinds";
  const LEVEL_FRACTION_STORAGE_KEY = "gameplay_level_fraction";
  const GAMEPLAY_DATA_VERSION = "20260814-gp13";
  const GAMEPLAY_INTEGRATION_VERSION = "20260813-projectile-audio1";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const GAMEPLAY_INLINE_AUDIO_LIMIT = 20;
  const GENDER_VARIANT_STORAGE_KEY = "webui_gender_variant";
  const ENDADMINISTRATOR_ID = "chr_9000_endmin";
  const ENDADMINISTRATOR_VARIANTS = [
    { gender: "f", characterId: "chr_0003_endminf" },
    { gender: "m", characterId: "chr_0002_endminm" },
  ];
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
    integration: {
      language: "",
      status: "idle",
      loading: null,
      token: 0,
      combat: null,
      projectiles: null,
      projectileAudio: null,
      soundEffects: null,
      assets: null,
      errors: [],
      indexes: null,
    },
    loading: null,
    showDebug: false,
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

  function normalizeCharacterGender(value) {
    const normalized = String(value || "").trim().toLowerCase();
    return normalized === "m" || normalized === "f" ? normalized : "";
  }

  function currentCharacterGender() {
    if (typeof window.resolveGenderVariant === "function") {
      const resolved = normalizeCharacterGender(window.resolveGenderVariant());
      if (resolved) return resolved;
    }
    return normalizeCharacterGender(storageGet(GENDER_VARIANT_STORAGE_KEY)) || "f";
  }

  function setCharacterGender(value) {
    const gender = normalizeCharacterGender(value) || "f";
    if (typeof window.setGenderVariant === "function") {
      window.setGenderVariant(gender);
      return;
    }
    storageSet(GENDER_VARIANT_STORAGE_KEY, gender);
    document.body.classList.toggle("gender-active-f", gender === "f");
    document.body.classList.toggle("gender-active-m", gender === "m");
    window.dispatchEvent(new CustomEvent("webui:gender-changed", { detail: { gender } }));
  }

  function isEndministrator(entry) {
    return entry?.kind === "character" && String(entry.id || "") === ENDADMINISTRATOR_ID;
  }

  function endministratorGenderForValue(value) {
    const normalized = String(value || "").toLowerCase();
    if (!normalized) return "";
    if (normalized.includes("chr_0002_endminm") || normalized.includes("actor_endminm")) return "m";
    if (
      normalized.includes("chr_0003_endminf")
      || normalized.includes("actor_endminf")
      || /chr_0003_endmin(?:_|$)/.test(normalized)
    ) return "f";
    return "";
  }

  function filterEndministratorVariant(items, entry, valueForItem) {
    const rows = Array.isArray(items) ? items.filter(Boolean) : [];
    if (!isEndministrator(entry)) return rows;
    const active = currentCharacterGender();
    return rows.filter((item) => {
      const gender = endministratorGenderForValue(valueForItem(item));
      return !gender || gender === active;
    });
  }

  function endministratorVariantEntry(entry) {
    if (!isEndministrator(entry)) return entry;
    return {
      ...entry,
      skillGroups: (entry.skillGroups || []).map((group) => ({
        ...group,
        actionSkillIds: filterEndministratorVariant(group.actionSkillIds, entry, (value) => value),
        skills: filterEndministratorVariant(group.skills, entry, (skill) => skill?.id),
      })),
    };
  }

  function renderEndministratorVariantControl(entry) {
    if (!isEndministrator(entry)) return "";
    const active = currentCharacterGender();
    const buttons = ENDADMINISTRATOR_VARIANTS.map((variant) => {
      const selected = variant.gender === active;
      const label = text(variant.gender === "f" ? "female" : "male");
      const debugId = STATE.showDebug ? `<code>${escapeHtml(variant.characterId)}</code>` : "";
      return `<button type="button" class="gameplay-character-gender-button${selected ? " is-selected" : ""}" data-gameplay-character-gender="${variant.gender}" aria-pressed="${selected ? "true" : "false"}"><span>${escapeHtml(label)}</span>${debugId}</button>`;
    }).join("");
    return `<div class="gameplay-character-gender-control">
      <div class="gameplay-character-gender-heading">${escapeHtml(text("characterVariant"))}</div>
      <div class="gameplay-character-gender-buttons" role="group" aria-label="${escapeHtml(text("characterVariant"))}">${buttons}</div>
      <p>${escapeHtml(text("characterVariantNote"))}</p>
    </div>`;
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
    const raw = String(value || "").trim();
    const exactKey = raw.includes(":") ? raw : "";
    if (exactKey) {
      const exact = STATE.entries.find((entry) => entry && `${entry.kind}:${entry.id}` === exactKey);
      if (exact) return exact;
    }
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
    const activeGender = currentCharacterGender();
    const keys = isEndministrator(entry)
      ? storyWikiKeys(entry).filter((key) => {
        const gender = endministratorGenderForValue(key);
        return !gender || gender === activeGender;
      })
      : storyWikiKeys(entry);
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

  function renderGameplayTagDetails(details) {
    const rows = (details || [])
      .filter((item) => item && item.id)
      .map((item) => {
        const names = (item.names || []).filter(Boolean);
        const contexts = (item.contexts || [])
          .map((context) => context?.name || "")
          .filter(Boolean);
        const label = names.length ? names.join(" / ") : text("id");
        const contextSuffix = contexts.length
          ? ` · ${text("gameplayTagContext")}: ${contexts.join(" / ")}`
          : "";
        const cls = item.evidenceStatus === "unresolved" ? " gameplay-tag-unresolved" : "";
        const evidenceReason = item.evidenceStatus === "unresolved"
          ? (item.unresolvedReason || "")
          : "";
        const evidenceTitle = item.evidenceStatus === "unresolved"
          ? text("gameplayTagUnresolvedReason")
          : "";
        const title = evidenceTitle ? ` title="${escapeHtml(evidenceTitle)}"` : "";
        const reason = evidenceReason
          ? ` data-unresolved-reason="${escapeHtml(evidenceReason)}"`
          : "";
        return `<span class="gameplay-value-chip${cls}"${title}${reason}><b>${escapeHtml(label)}</b>${escapeHtml(`${item.id}${contextSuffix}`)}</span>`;
      });
    return rows.length ? `<div class="gameplay-blackboard">${rows.join("")}</div>` : "";
  }

  function renderGameplayTagQuery(query) {
    const details = query?.tagDetails || [];
    return details.length
      ? renderGameplayTagDetails(details)
      : renderIdChips(query?.tagIds || []);
  }

  function gameplayTagQueryValues(query) {
    const details = query?.tagDetails || [];
    if (details.length) {
      return details.map((item) => {
        const names = (item.names || []).filter(Boolean);
        const contexts = (item.contexts || [])
          .map((context) => context?.name || "")
          .filter(Boolean);
        if (names.length) return `${names.join(" / ")} (${item.id})`;
        return contexts.length ? `${item.id} [${contexts.join(" / ")}]` : item.id;
      });
    }
    return query?.tagIds || [];
  }

  function gameplayTargetForItem(item) {
    const id = String(item?.id || "").trim();
    if (!id) return null;
    let kind = ["weapon", "character"].includes(String(item?.kind || "")) ? String(item.kind) : "";
    if (!kind && id.startsWith("wpn_")) kind = "weapon";
    if (!kind && id.startsWith("chr_")) kind = "character";
    return kind ? findGameplayEntry(`${kind}:${id}`) : null;
  }

  function materialChipRows(items) {
    return (items || [])
      .filter((item) => item && (item.name || item.id))
      .map((item) => {
        const label = item.name || item.id;
        const count = item.count !== undefined && item.count !== null && item.count !== "" ? formatValue(item.count) : "";
        const target = gameplayTargetForItem(item);
        const icon = renderGameplayItemIcon(item, label, { static: Boolean(target) });
        if (target) {
          const targetKey = `${target.kind}:${target.id}`;
          return `<button type="button" class="gameplay-value-chip gameplay-item-chip gameplay-related-link gameplay-item-chip-link" data-gameplay-related-key="${escapeHtml(targetKey)}" title="${escapeHtml(target.id)}" aria-label="${escapeHtml(label)}">${icon}<b>${escapeHtml(label)}</b>${escapeHtml(count)}</button>`;
        }
        return `<span class="gameplay-value-chip gameplay-item-chip">${icon}<b>${escapeHtml(label)}</b>${escapeHtml(count)}</span>`;
      })
      .join("");
  }

  function renderMaterialChips(items) {
    const rows = materialChipRows(items);
    return rows ? `<div class="gameplay-blackboard">${rows}</div>` : "";
  }

  const HIDDEN_CHARACTER_LEVEL_UP_COST_ITEM_IDS = new Set([
    "item_expcard_stage1_low",
    "item_expcard_stage1_mid",
    "item_expcard_stage1_high",
    "item_expcard_stage2_low",
    "item_expcard_stage2_high",
  ]);

  function visibleCharacterLevelUpCostItems(items) {
    return (items || []).filter((item) => item && !HIDDEN_CHARACTER_LEVEL_UP_COST_ITEM_IDS.has(String(item.id || "")));
  }

  function renderUpgradeCost(row) {
    if (!row) return "";
    const chips = [];
    if (row.goldCost !== undefined && row.goldCost !== null && row.goldCost !== "") {
      chips.push(renderValueChip(goldCostPair(row.goldCost)));
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
    9: "critical_rate", 13: "move_speed", 17: "normal_attack_efficiency",
    20: "max_poise", 21: "poise_recovery_time", 28: "ultimate_skill_efficiency",
    29: "heal_output", 30: "heal_taken", 31: "healing_taken_scalar",
    32: "skill_damage", 33: "combo_skill_damage", 34: "normal_attack_damage",
    35: "fire_burst_damage", 36: "pulse_burst_damage", 37: "cryst_burst_damage", 38: "natural_burst_damage",
    39: "str", 40: "agi", 41: "wis", 42: "will",
    44: "ultimate_sp_gain", 47: "combo_skill_cooldown", 48: "natural_damage_taken",
    50: "physical_damage", 51: "fire_damage", 52: "pulse_damage", 53: "cryst_damage", 54: "natural_damage", 55: "ether_damage",
    60: "ether_damage_taken", 61: "broken_unit_damage",
    80: "physical_damage_taken_scalar", 81: "natural_damage_taken_scalar", 82: "cryst_damage_taken_scalar",
    83: "pulse_damage_taken_scalar", 84: "fire_damage_taken_scalar", 85: "ether_damage_taken_scalar",
    87: "infliction", 91: "in_air_move_speed",
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
        Number(brk.gold) > 0 ? renderChipPairs([goldCostPair(brk.gold)]) : "",
        renderMaterialChips(brk.items || []),
      ].filter(Boolean).join("");
      if (chips) parts.push(`<div class="gameplay-subheading">${escapeHtml(costIndex.breakLabel)}</div>${chips}`);
    }
    // Cumulative level-up cost up to this exact level (falls back to the nearest
    // checkpoint when a per-level curve isn't available), plus the stage's EXP items.
    const cp = costIndex.levelUpByLevel.get(Number(row.level)) || cumulativeLevelUpAt(costIndex.checkpoints, Number(row.level));
    const cumulativeExpItems = cp && (cp.expItems || []).length ? cp.expItems : null;
    let upPairs = cp && Number(cp.gold) > 0
      ? [{ ...goldCostPair(cp.gold), label: text("cumulativeGold") }]
      : null;
    if (cp && !cumulativeExpItems && Number(cp.exp) > 0) {
      (upPairs || (upPairs = [])).unshift({ label: text("cumulativeExp"), value: cp.exp });
    }
    const expItems = visibleCharacterLevelUpCostItems(costIndex.levelUpItemsByStage.get(stage));
    const upChips = [
      cumulativeExpItems ? renderMaterialChips(cumulativeExpItems) : "",
      upPairs ? renderChipPairs(upPairs) : "",
      expItems.length ? renderMaterialChips(expItems) : "",
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

  function renderTalentLevelCell(level, groupTitle, groupKind) {
    const title = level.name || (level.title !== groupTitle ? level.title : "") || `${text("level")} ${formatValue(level.level || "")}`;
    const coordinate = sourceCoordinate(level.source);
      const meta = [
        level.level ? `${text("level")} ${formatValue(level.level)}` : "",
        level.breakStage ? `Break ${formatValue(level.breakStage)}` : "",
        level.equipTierLimit ? `T${formatValue(level.equipTierLimit)}` : "",
        level.unlockHint ? `${text("unlockHint")}: ${level.unlockHint}` : "",
        level.iconId ? `${text("iconId")}: ${level.iconId}` : "",
        coordinate ? `${text("dataCoordinate")}: ${coordinate}` : "",
        level.id,
    ].filter(Boolean).join(" / ");
    const icon = renderGameplayTokenIcon(level.iconId, title, {
      className: groupKind === "passive" ? "gameplay-passive-talent-icon" : "",
    });
    const attr = level.attributeModifier && Object.keys(level.attributeModifier).length
      ? renderBlackboard(Object.entries(level.attributeModifier).map(([key, value]) => ({ key, value })))
      : "";
    const required = renderRequiredItems(level.requiredItem || []);
    const values = [renderBlackboard(level.blackboard), attr].filter(Boolean).join("");
    return `<div class="gameplay-talent-level">
      <div class="gameplay-talent-level-title">${icon}<span>${escapeHtml(title)}</span></div>
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
      <div class="gameplay-talent-levels">${levels.map((level) => renderTalentLevelCell(level, group.title, group.kind)).join("")}</div>
    </article>`;
  }

  function renderTalentGroups(groups) {
    // Breakthrough and attribute nodes belong to the removed character-growth
    // surface. Keep actual passive/factory talents in the native talent table.
    const rows = (groups || [])
      .filter((group) => !["upgrade", "attribute"].includes(String(group?.kind || "")))
      .map(renderTalentGroupRow)
      .filter(Boolean);
    return rows.length ? `<div class="gameplay-talent-table">${rows.join("")}</div>` : "";
  }

  function goldCurrencyItem() {
    const item = STATE.index?.currencyItems?.gold;
    return item && item.id ? item : null;
  }

  function goldCostPair(value) {
    const item = goldCurrencyItem();
    const label = item?.name || text("gold");
    return { label, value, iconItem: item, iconLabel: label };
  }

  function renderValueChip(item, opts = {}) {
    const cls = opts.className || "";
    const icon = item?.iconItem ? renderGameplayItemIcon(item.iconItem, item.iconLabel || item.label) : "";
    return `<span class="gameplay-value-chip${cls ? ` ${escapeHtml(cls)}` : ""}">${icon}<b>${escapeHtml(item.label)}</b>${escapeHtml(formatValue(item.value))}</span>`;
  }

  function renderChipPairs(pairs, opts = {}) {
    const diff = opts.diffLabels;
    const rows = (pairs || [])
      .filter((item) => item && item.value !== undefined && item.value !== null && item.value !== "")
      .map((item) => {
        const className = diff && diff.has(String(item.label || "")) ? "gameplay-diff" : "";
        return renderValueChip(item, { className });
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
      stats.templateId,
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
      { ...goldCostPair(row.lvUpGold) },
      { label: text("cumulativeExp"), value: row.lvUpExpSum },
      { ...goldCostPair(row.lvUpGoldSum), label: text("cumulativeGold") },
    ]));
    cards.push(progressionCard(text("upgradeCurve"), [upgrade.templateId, `${formatValue(upgrade.rowCount)} ${text("level")}`].filter(Boolean).join(" / "), upgradeRows));

    const breakthroughRows = (entry.breakthrough && entry.breakthrough.rows || []).map((row) => {
      const meta = row.showLevel ? `${text("showLevel")} ${formatValue(row.showLevel)}` : "";
      const goldCost = row.goldCost ? renderChipPairs([goldCostPair(row.goldCost)]) : "";
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

  // Buff numbers live on each sub-skill's per-level entry (blackboard keys
  // and subDesc labels). A group's visible action is a merge of every
  // sub-skill sharing that level number, deduped so repeated keys (the same
  // scale re-declared on a follow-up hit) only show once.
  function collectGroupLevelChips(group, levelValue) {
    const seen = new Set();
    const chips = [];
    for (const skill of group.skills || []) {
      const level = levelForSkill(skill, levelValue);
      if (!level) continue;
      const cooldown = Number(level.coolDown);
      if (Number.isFinite(cooldown) && cooldown > 0) {
        const key = `cooldown ${cooldown}`;
        if (!seen.has(key)) {
          seen.add(key);
          chips.push(`<span class="gameplay-value-chip"><b>${escapeHtml(text("cooldown"))}</b>${escapeHtml(`${formatValue(cooldown)} ${text("secondsShort")}`)}</span>`);
        }
      }
      for (const item of level.blackboard || []) {
        if (!item || !item.key) continue;
        const key = `bb ${item.key} ${item.value}`;
        if (seen.has(key)) continue;
        seen.add(key);
        chips.push(`<span class="gameplay-value-chip"><b>${escapeHtml(item.key)}</b>${escapeHtml(formatValue(item.value))}</span>`);
      }
      for (const item of level.subDesc || []) {
        if (!item || !(item.label || item.value)) continue;
        const key = `sub ${item.label} ${item.value}`;
        if (seen.has(key)) continue;
        seen.add(key);
        chips.push(`<span class="gameplay-value-chip"><b>${escapeHtml(item.label || "-")}</b>${escapeHtml(item.value || "")}</span>`);
      }
    }
    return chips.length ? `<div class="gameplay-blackboard">${chips.join("")}</div>` : "";
  }

  function renderActiveSkillLevelPane(group, levelValue, active) {
    const values = collectGroupLevelChips(group, levelValue);
    const cost = renderUpgradeCost(levelUpForLevel({ level: levelValue }, group.levelUp || []));
    return `<div class="gameplay-level-pane gameplay-active-skill-pane" data-level-label="${escapeHtml(levelLabel({ level: levelValue }))}"${active ? "" : " hidden"}>
      ${values || `<span class="muted">-</span>`}
      ${cost}
    </div>`;
  }

  function renderActiveSkillLevels(group) {
    const levels = sortedSkillLevelsForGroup(group);
    const label = `<div class="gameplay-active-skill-col-label">${escapeHtml(text("level"))}</div>`;
    if (!levels.length) return `<div class="gameplay-active-skill-levels">${label}<span class="muted">-</span></div>`;
    const body = levels.length === 1
      ? `<div class="gameplay-level-table">${renderActiveSkillLevelPane(group, levels[0], true)}</div>`
      : `<div class="gameplay-level-slider-wrap" data-level-card>
        <div class="gameplay-level-slider-control">
          <span>${escapeHtml(text("selectedLevel"))}</span>
          <input class="gameplay-level-slider" type="range" min="0" max="${levels.length - 1}" step="1" value="0" aria-label="${escapeHtml(text("selectedLevel"))}">
          <output class="gameplay-level-slider-output">${escapeHtml(levelLabel({ level: levels[0] }))}</output>
        </div>
        <div class="gameplay-level-panes">${levels.map((level, index) => renderActiveSkillLevelPane(group, level, index === 0)).join("")}</div>
      </div>`;
    return `<div class="gameplay-active-skill-levels">${label}${body}</div>`;
  }
  // Potential-unlock keepsake photos (levels 1/3/5) are wide, cinematic
  // illustrations rather than square icons, and each one carries an authored
  // flavor line (`decoDesc` in ItemTable) shown alongside it in-game. Render
  // them as captioned figures instead of bare icon tiles so the source aspect
  // ratio survives and the line is visible.
  function renderPotentialPictures(pictures, alt = "") {
    const cards = (pictures || []).map((picture) => {
      const token = String(picture?.id || "").trim();
      if (!token) return "";
      const refs = integrationAssetRefsForToken(token);
      const asset = refs?.images?.find((item) => item?.rel);
      if (!asset) return "";
      const name = picture.name || alt;
      const image = renderGameplayImageButton(asset, {
        className: "gameplay-potential-picture-asset",
        alt: name,
        token,
        imageName: name || token,
      });
      const caption = [
        name ? `<div class="gameplay-potential-picture-name">${escapeHtml(name)}</div>` : "",
        picture.sentence ? `<div class="gameplay-potential-picture-quote">${escapeHtml(picture.sentence)}</div>` : "",
      ].filter(Boolean).join("");
      return `<figure class="gameplay-potential-picture">${image}${caption ? `<figcaption>${caption}</figcaption>` : ""}</figure>`;
    }).filter(Boolean).join("");
    return cards ? `<div class="gameplay-potential-picture-row">${cards}</div>` : "";
  }

  function renderCharacterPotentials(entry) {
    const potentialRows = (entry.potentials && entry.potentials.levels || []).map((row) => {
      const coordinate = sourceCoordinate(row.source);
      const meta = [
        row.potentialEffectId,
        row.level ? `${text("level")} ${formatValue(row.level)}` : "",
        coordinate ? `${text("dataCoordinate")}: ${coordinate}` : "",
      ].filter(Boolean).join(" / ");
      const required = renderRequiredItems(row.requiredItem || []);
      const values = renderBlackboard(row.blackboard || []);
      const alt = row.name || entry.title || entry.id;
      const visiblePictures = filterEndministratorVariant(row.pictures, entry, (picture) => picture?.id);
      const pictures = renderPotentialPictures(visiblePictures, alt);
      const topicImages = renderGameplayTokenImages([row.unlockCardTopicItem].filter(Boolean), alt, "gameplay-potential-assets");
      return `<div class="gameplay-talent-level">
        <div class="gameplay-talent-level-title">${escapeHtml(row.name || `${text("potential")} ${formatValue(row.level === undefined || row.level === null ? "" : row.level)}`)}</div>
        ${meta ? `<div class="gameplay-skill-meta">${escapeHtml(meta)}</div>` : ""}
        ${renderDescription(row.description)}
        ${values}
        ${pictures ? `<div class="gameplay-subheading">${escapeHtml(text("potentialPictures"))}</div>${pictures}` : ""}
        ${topicImages ? `<div class="gameplay-subheading">${escapeHtml(text("potentialCardTopic"))}</div>${topicImages}` : ""}
        ${required ? `<div class="gameplay-subheading">${escapeHtml(text("requiredItems"))}</div>${required}` : ""}
      </div>`;
    }).join("");
    return potentialRows ? `<div class="gameplay-talent-levels">${potentialRows}</div>` : "";
  }

  function renderCharacterBreakthroughs(entry) {
    const rows = (entry.breakthroughs || []).map((row) => {
      const meta = [
        row.stage !== undefined && row.stage !== null ? `${text("stage")} ${formatValue(row.stage)}` : "",
        row.level !== undefined && row.level !== null ? `${text("level")} ${formatValue(row.level)}` : "",
        row.equipTierLimit ? `T${formatValue(row.equipTierLimit)}` : "",
        row.id,
      ].filter(Boolean).join(" / ");
      const required = renderRequiredItems(row.requiredItem || []);
      return `<article class="gameplay-skill-card">
        <header>
          <div class="gameplay-skill-title">${escapeHtml(row.name || row.id || text("characterBreakthroughs"))}</div>
          <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
        </header>
        ${renderDescription(row.description)}
        ${required ? `<div class="gameplay-subheading">${escapeHtml(text("requiredItems"))}</div>${required}` : ""}
      </article>`;
    }).filter(Boolean).join("");
    return rows ? `<div class="gameplay-card-grid">${rows}</div>` : "";
  }

  function renderCharacterAssetStrip(entry) {
    const key = `${entry?.kind || ""}:${entry?.id || ""}`;
    const refs = STATE.integration.assets?.entries?.[key];
    if (!refs) return "";
    // The sidecar ranks character portraits by semantic category and image
    // size: complete illustrations/poses first, then tighter crops. Keep the
    // sidecar order so the crop/pose progression stays stable for every
    // character instead of being re-sorted by the browser. The Administrator
    // sidecar carries both concrete portrait identities; only the persisted
    // active gender variant belongs in the visible strip.
    const images = filterEndministratorVariant(refs.images, entry, (item) => item?.rel).slice(0, 4);
    const models = filterEndministratorVariant(refs.models, entry, (item) => item?.rel);
    const imageCards = images.map((asset, index) => {
      const portraitName = `${entry.title || entry.id || asset.rel} #${index + 1}`;
      return renderGameplayImageButton(asset, {
        className: "gameplay-character-asset-thumb",
        alt: entry.title || entry.id || "",
        imageId: entry.id || asset.rel,
        imageName: portraitName,
      });
    }).join("");
    const model = models[0];
    const modelLink = model
      ? `<a class="gameplay-character-asset-model" href="${escapeHtml(gameplayAssetPageHref(model.rel))}" title="${escapeHtml(text("openAsset"))}"><span>${escapeHtml(text("assetModels"))}</span><code>${escapeHtml(model.rel)}</code></a>`
      : "";
    if (!imageCards && !modelLink) return "";
    return `<div class="gameplay-character-asset-strip"><div class="gameplay-character-asset-images">${imageCards}</div>${modelLink}</div>`;
  }

  function projectileScalarText(value) {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value !== "object") return formatValue(value);
    const candidate = value.valueFloatCandidate ?? value.valueIntCandidate ?? value.value;
    const display = formatValue(candidate);
    if (value.useBlackboardKey && value.blackboardKey) return `${display} / BB: ${value.blackboardKey}`;
    return value.blackboardKey ? `${display} / key: ${value.blackboardKey}` : display;
  }

  function projectileEnumText(value) {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value !== "object") return formatValue(value);
    const name = value.name || value.enumType || "";
    const numeric = value.value === null || value.value === undefined ? "" : formatValue(value.value);
    return [name, numeric && name ? `(${numeric})` : numeric].filter(Boolean).join(" ");
  }

  function projectileVectorText(value) {
    if (!value || typeof value !== "object") return "";
    const vector = value.valueCandidate || value;
    const axes = ["x", "y", "z"].filter((axis) => vector[axis] !== undefined);
    return axes.length ? `(${axes.map((axis) => projectileScalarText(vector[axis])).join(", ")})` : "";
  }

  function projectileFriendlyEnum(value) {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value !== "object") return formatValue(value);
    return value.name || "";
  }

  function projectileHitLimitText(value) {
    const raw = typeof value === "object"
      ? (value?.valueIntCandidate ?? value?.valueFloatCandidate ?? value?.value)
      : value;
    return Number(raw) === -1 ? text("projectileUnlimitedHits") : projectileScalarText(value);
  }

  function projectileBehaviorSkillIds(projectile) {
    const template = projectile?.template || {};
    return [...new Set([
      ...(template.normalAttackIds || []),
      ...(template.activeSkillIds || []),
      ...(template.passiveSkillIds || []),
      ...(template.normalAttackList || []),
      ...(template.enabledBreakingNormalAttacks || []),
      ...(template.enabledPassiveSkills || []),
      template.normalSkillId,
      template.ultimateSkillId,
      template.plungingAttackStartId,
      template.plungingAttackEndId,
      template.comboSkillId,
      template.dodgeSkillId,
    ].map((value) => String(value || "").trim()).filter(Boolean))];
  }

  function projectileMatchMethodText(method) {
    const key = `projectileMatch_${String(method || "unresolved").replace(/-([a-z])/g, (_, char) => char.toUpperCase())}`;
    const translated = text(key);
    return translated === key ? readableIntegrationId(method || "unresolved") : translated;
  }

  function projectileTagText(filter) {
    const query = filter?.tagQuery || {};
    const tags = (query.tags || []).map((tag) => {
      if (typeof tag === "string") return tag;
      if (!tag || typeof tag !== "object") return "";
      return [tag.path, projectileEnumText(tag.tagId)].filter(Boolean).join(" / ");
    }).filter(Boolean);
    return [projectileEnumText(query.queryType), ...tags].filter(Boolean).join(" / ");
  }

  function projectileFriendlyTagText(filter) {
    const query = filter?.tagQuery || {};
    const tags = (query.tags || []).map((tag) => typeof tag === "string" ? tag : tag?.path).filter(Boolean);
    return [projectileFriendlyEnum(query.queryType), ...tags].filter(Boolean).join(" / ");
  }

  const PROJECTILE_SOUND_PHASES = [
    "launchSound", "loopSound", "reachSound", "hitSound", "blockSound", "finishedSound", "sizzleSound",
  ];

  function projectileEventHash(value) {
    const raw = value && typeof value === "object" ? value.value : value;
    const numeric = Number(raw);
    return Number.isFinite(numeric) && numeric !== 0 ? numeric >>> 0 : null;
  }

  function renderEvidenceBadge(labelKey, detailKey, tone = "exact") {
    const detail = text(detailKey);
    return `<span class="gameplay-status-badge is-${escapeHtml(tone)}" title="${escapeHtml(detail)}">${escapeHtml(text(labelKey))}</span>`;
  }

  function renderBuffSubheading(labelKey, badge = "") {
    return `<div class="gameplay-subheading gameplay-subheading-row"><span>${escapeHtml(text(labelKey))}</span>${badge}</div>`;
  }

  function projectileAudioIndexKey(projectileId, field, eventHash) {
    return `${String(projectileId || "")}\u0000${String(field || "")}\u0000${Number(eventHash) >>> 0}`;
  }

  function projectileFriendlyName(projectile) {
    const id = String(projectile?.id || "")
      .replace(/^data_/, "")
      .replace(/^projectile_/, "")
      .replace(/^(?:chr|eny)_\d+_[^_]+_/, "")
      .replace(/^projectile/, "");
    return readableIntegrationId(id) || projectileDisplayName(projectile);
  }

  function projectileSoundRows(projectile) {
    const sounds = projectile?.sounds || {};
    return PROJECTILE_SOUND_PHASES.map((field) => {
      const value = sounds[field];
      const eventHash = projectileEventHash(value);
      if (eventHash === null) return null;
      const link = STATE.integration.indexes?.projectileAudio?.get(
        projectileAudioIndexKey(projectile?.id, field, eventHash),
      );
      return {
        field,
        value,
        event: link?.event || { hash: eventHash, hex: `0x${eventHash.toString(16).padStart(8, "0")}` },
        audio: Array.isArray(link?.audio) ? link.audio.filter((row) => row?.src) : [],
      };
    }).filter(Boolean);
  }

  function renderProjectileAudio(soundRows) {
    const playable = soundRows.filter((row) => row.audio.length);
    if (!soundRows.length) return "";
    const sidecarUnavailable = STATE.integration.status === "ready" && !STATE.integration.projectileAudio;
    const phases = soundRows.map((row) => {
      const phaseLabel = text(`projectileSound_${row.field}`);
      const candidates = row.audio.map((audio, index) => `<div class="gameplay-projectile-audio-candidate"><audio controls preload="none" src="${escapeHtml(audio.src)}"></audio><small>${escapeHtml(`${text("projectileAudioCandidate")} ${index + 1} · ${audio.mediaId || "-"}`)}</small></div>`).join("");
      const open = row.audio.length > 0 && row.audio.length <= GAMEPLAY_INLINE_AUDIO_LIMIT ? " open" : "";
      return `<details class="gameplay-projectile-audio-phase"${open}><summary><strong>${escapeHtml(phaseLabel)}</strong><span>${escapeHtml(row.audio.length ? `${row.audio.length} ${text("projectilePlayableCandidates")}` : text("projectileSoundUnlinked"))}</span></summary>${candidates || `<p>${escapeHtml(text("projectileSoundUnlinkedNote"))}</p>`}</details>`;
    }).join("");
    return `<section class="gameplay-projectile-audio"><header><strong>${escapeHtml(text("projectileAudio"))}</strong><span>${escapeHtml(`${playable.reduce((total, row) => total + row.audio.length, 0)} ${text("projectilePlayableCandidates")}`)}</span></header><p${sidecarUnavailable ? ' class="gameplay-integration-note is-warning" role="status"' : ""}>${escapeHtml(text(sidecarUnavailable ? "projectileAudioUnavailable" : "projectileAudioNote"))}</p>${phases}</section>`;
  }

  function gameplaySoundEventName(eventId) {
    return readableIntegrationId(String(eventId || "")
      .replace(/^(?:au|bark|radio)_/i, "")
      .replace(/^(?:play_|sfx_)/i, "")
      .replace(/^(?:chr|eny)_\d+_[^_]+_/i, ""));
  }

  function gameplaySoundCountText(events, options = {}) {
    const rows = events || [];
    if (options.sharedGraph) return `${rows.length} ${text("soundSharedEvents")}`;
    const mediaKeys = new Set();
    const possibleFiles = rows.reduce((total, event) => {
      for (const audio of event.audio || []) {
        const key = audio?.mediaId != null
          ? `media:${audio.mediaId}`
          : audio?.src ? `src:${audio.src}` : "";
        if (key) mediaKeys.add(key);
      }
      const resolved = (event.audio || []).filter((audio) => audio?.src).length;
      return total + (resolved || Number(event.possibleMediaCount || event.playableCandidates || 0));
    }, 0);
    const uniqueFiles = mediaKeys.size;
    const uniqueLabel = uniqueFiles ? ` · ${uniqueFiles} ${text("soundUniqueFiles")}` : "";
    return `${rows.length} ${text("soundEvents")} · ${possibleFiles} ${text("soundPossibleFiles")}${uniqueLabel}`;
  }

  function gameplaySoundIsSharedAnimation(event) {
    return event?.possibleMediaScope === "sharedEventGraph"
      || event?.animationOwnershipScope === "sharedPlayableCharacters"
      || Number(event?.animationOwnerCount || 0) > 1;
  }

  function gameplaySoundHasExactSkillTrigger(event) {
    return event?.triggerBindingStatus === "exactSkillConfig"
      || (event?.triggerBindings || []).some((binding) => binding?.status === "exactSkillConfig");
  }

  function gameplaySoundTriggerLabels(event) {
    const values = [];
    if (event?.triggerBindingStatus === "exactSkillConfig") values.push(text("soundExactSkillTrigger"));
    else if (event?.triggerBindingStatus === "exactEnemyBornBuffConfig") values.push(text("soundExactEnemyBornTrigger"));
    else if (event?.triggerBindingStatus === "inferredSkillConfigOwner") values.push(text("soundInferredSkillTrigger"));
    const relationLabels = {
      skillDataEventReference: "soundTriggerSkillData",
      skillBuffChain: "soundTriggerBuffChain",
      enemyBornBuffChain: "soundTriggerEnemyBornBuff",
      buffPlaySoundAction: "soundTriggerPlaySoundAction",
    };
    for (const relation of event?.triggerRelationTypes || []) {
      values.push(text(relationLabels[relation] || relation));
    }
    for (const binding of event?.triggerBindings || []) {
      if (binding?.runtimeActivationStatus === "conditionAndTimingUnresolved") values.push(text("soundTriggerConditionUnresolved"));
      else if (binding?.runtimeActivationStatus === "authoredFrameWindowRecoveredConditionUnresolved") values.push(text("soundTriggerFrameConditionUnresolved"));
    }
    return [...new Set(values.filter(Boolean))];
  }

  function gameplayAudioEventHref(eventId) {
    const url = new URL(window.location.href);
    url.searchParams.delete("gameplay");
    url.searchParams.delete("gameplayId");
    url.searchParams.delete("entry");
    url.searchParams.set("audio", String(eventId || ""));
    url.searchParams.set("audioKind", "events");
    url.hash = "#audio";
    return url.toString();
  }

  function gameplaySoundSkillIds(event) {
    const ids = new Set((event?.sourceSkillIds || []).filter(Boolean).map(String));
    for (const evidence of event?.evidence || []) {
      if (evidence?.skillId) ids.add(String(evidence.skillId));
    }
    return [...ids].sort();
  }

  function gameplaySoundActionGroup(event) {
    const actionKinds = [...new Set((event?.actionKinds || []).filter(Boolean).map(String))].sort();
    if (actionKinds.length) return { key: `kind:${actionKinds.join("|")}`, kind: "kind", values: actionKinds };
    const skillIds = gameplaySoundSkillIds(event);
    if (skillIds.length) return { key: `skill:${skillIds.join("|")}`, kind: "skill", values: skillIds };
    const spawn = (event?.evidence || []).some((row) => row?.kind === "enemyBornBuffData");
    if (spawn) return { key: "spawn", kind: "spawn", values: [] };
    return { key: "other", kind: "other", values: [] };
  }

  function gameplaySoundActionLabel(group) {
    const kindLabels = {
      attack: "soundActionAttack",
      skill: "soundActionSkill",
      reaction: "soundActionReaction",
      movement: "soundActionMovement",
      action: "soundActionOther",
      attackVoice: "soundActionAttackVoice",
      skillVoice: "soundActionSkillVoice",
      reactionVoice: "soundActionReactionVoice",
      combatVoice: "soundActionCombatVoice",
    };
    if (group.kind === "kind") {
      return group.values.map((value) => text(kindLabels[value] || "soundActionOther")).join(" / ");
    }
    if (group.kind === "spawn") return text("enemySpawnSounds");
    if (group.kind === "other") return text("soundActionOther");
    const labels = group.values.map((value) => readableIntegrationId(String(value || "")
      .replace(/^(?:chr|eny)_\d+_[^_]+_/i, "")));
    if (labels.length === 1) return labels[0];
    return `${text("soundActionShared")}: ${labels.slice(0, 2).join(" / ")}${labels.length > 2 ? ` +${labels.length - 2}` : ""}`;
  }

  function gameplaySoundRelationLabels(relations) {
    const labels = {
      randomAlternative: "soundRelationRandom",
      sequenceItem: "soundRelationSequence",
      switchCandidate: "soundRelationSwitch",
      layerChild: "soundRelationLayer",
      groupChild: "soundRelationGroup",
      directSound: "soundRelationDirect",
    };
    return [...new Set((relations || []).map((value) => labels[value] ? text(labels[value]) : readableIntegrationId(value)))];
  }

  function gameplaySoundMediaEvidence(audio) {
    const rows = audio?.wwiseMediaEvidence || [];
    const roots = [...new Set(rows.flatMap((row) => row?.rootActionIds || []).filter((value) => Number.isInteger(value)))];
    const relations = gameplaySoundRelationLabels(rows.flatMap((row) => row?.relationTypes || []));
    const soundObjects = rows.reduce((total, row) => total + Number(row?.soundObjectCount || 0), 0);
    return { roots, relations, soundObjects };
  }

  function mergeGameplaySoundEvents(events) {
    const merged = new Map();
    const uniqueScalars = (...values) => [...new Set(values.flat().filter(Boolean))];
    const uniqueObjects = (...values) => {
      const rows = new Map();
      for (const value of values.flat().filter((row) => row && typeof row === "object")) {
        rows.set(JSON.stringify(value), value);
      }
      return [...rows.values()];
    };
    const mergeSelectorEvidence = (...values) => {
      const evidence = values.filter((value) => value && typeof value === "object");
      if (!evidence.length) return undefined;
      const containers = {};
      for (const value of evidence) {
        for (const [relation, counts] of Object.entries(value.containers || {})) {
          const previous = containers[relation] || {};
          containers[relation] = {
            ...previous,
            ...counts,
            nodeCount: Math.max(Number(previous.nodeCount || 0), Number(counts?.nodeCount || 0)),
            childEdgeCount: Math.max(Number(previous.childEdgeCount || 0), Number(counts?.childEdgeCount || 0)),
          };
        }
      }
      return {
        ...evidence[0],
        ...evidence[evidence.length - 1],
        bankDefinitionCount: Math.max(...evidence.map((value) => Number(value.bankDefinitionCount || 0))),
        rootStopActionCount: Math.max(...evidence.map((value) => Number(value.rootStopActionCount || 0))),
        containers,
      };
    };
    for (const event of events || []) {
      const key = String(event?.id || "").toLowerCase();
      if (!key) continue;
      const previous = merged.get(key);
      if (!previous) {
        merged.set(key, { ...event });
        continue;
      }
      const audio = new Map();
      for (const candidate of [...(previous.audio || []), ...(event.audio || [])]) {
        const candidateKey = String(candidate?.src || candidate?.mediaId || "");
        if (!candidateKey) continue;
        const previousCandidate = audio.get(candidateKey);
        audio.set(candidateKey, previousCandidate ? {
          ...previousCandidate,
          ...candidate,
          wwiseMediaEvidence: uniqueObjects(previousCandidate.wwiseMediaEvidence || [], candidate.wwiseMediaEvidence || []),
        } : candidate);
      }
      merged.set(key, {
        ...previous,
        ...event,
        foundInWwise: Boolean(previous.foundInWwise || event.foundInWwise),
        audio: [...audio.values()],
        actionKinds: uniqueScalars(previous.actionKinds || [], event.actionKinds || []),
        sourceSkillIds: uniqueScalars(previous.sourceSkillIds || [], event.sourceSkillIds || []),
        sourceAnimationClips: uniqueScalars(previous.sourceAnimationClips || [], event.sourceAnimationClips || []),
        animationFunctions: uniqueScalars(previous.animationFunctions || [], event.animationFunctions || []),
        animationClipContexts: uniqueScalars(previous.animationClipContexts || [], event.animationClipContexts || []),
        playRootActionIds: uniqueScalars(previous.playRootActionIds || [], event.playRootActionIds || []),
        mediaRelationTypes: uniqueScalars(previous.mediaRelationTypes || [], event.mediaRelationTypes || []),
        selectionContainerTypes: uniqueScalars(previous.selectionContainerTypes || [], event.selectionContainerTypes || []),
        triggerRelationTypes: uniqueScalars(previous.triggerRelationTypes || [], event.triggerRelationTypes || []),
        selectorEvidence: mergeSelectorEvidence(previous.selectorEvidence, event.selectorEvidence),
        actionDispatchEvidence: uniqueObjects(previous.actionDispatchEvidence || [], event.actionDispatchEvidence || []),
        evidence: uniqueObjects(previous.evidence || [], event.evidence || []),
        triggerBindings: uniqueObjects(previous.triggerBindings || [], event.triggerBindings || []),
        playRootCount: Math.max(Number(previous.playRootCount || 0), Number(event.playRootCount || 0)),
        possibleMediaCount: Math.max(Number(previous.possibleMediaCount || 0), Number(event.possibleMediaCount || 0)),
        playableCandidates: Math.max(Number(previous.playableCandidates || 0), Number(event.playableCandidates || 0)),
        animationOccurrenceCount: Math.max(Number(previous.animationOccurrenceCount || 0), Number(event.animationOccurrenceCount || 0)),
        animationClipCount: Math.max(Number(previous.animationClipCount || 0), Number(event.animationClipCount || 0)),
        animationOwnerCount: Math.max(Number(previous.animationOwnerCount || 0), Number(event.animationOwnerCount || 0)),
        unresolvedNodeCount: Math.max(Number(previous.unresolvedNodeCount || 0), Number(event.unresolvedNodeCount || 0)),
        traversalStatus: previous.traversalStatus === "partial" || event.traversalStatus === "partial"
          ? "partial"
          : (event.traversalStatus || previous.traversalStatus),
      });
    }
    return [...merged.values()];
  }

  function renderGameplaySoundEvidence(event, audio) {
    const roots = Number(event?.playRootCount || 0) || new Set(audio.flatMap((row) => gameplaySoundMediaEvidence(row).roots)).size;
    const relations = gameplaySoundRelationLabels(event?.mediaRelationTypes || audio.flatMap((row) => (row?.wwiseMediaEvidence || []).flatMap((evidence) => evidence?.relationTypes || [])));
    const selectorEvidence = event?.selectorEvidence || {};
    const selectorRelations = Object.entries(selectorEvidence.containers || {}).map(([relation, counts]) => {
      const label = gameplaySoundRelationLabels([relation])[0] || readableIntegrationId(relation);
      return `${label}: ${Number(counts?.nodeCount || 0)} ${text("soundSelectorNodes")} / ${Number(counts?.childEdgeCount || 0)} ${text("soundSelectorEdges")}`;
    });
    const definitions = Number(selectorEvidence.bankDefinitionCount || 0);
    const stopActions = Number(selectorEvidence.rootStopActionCount || 0);
    const animationCallbacks = Number(event?.animationOccurrenceCount || 0)
      || (event?.evidence || []).filter((row) => row?.kind === "animationClipEvent").length;
    const animationClips = Number(event?.animationClipCount || 0)
      || new Set((event?.sourceAnimationClips || []).filter(Boolean)).size;
    const isPartial = event?.traversalStatus === "partial";
    const status = isPartial ? text("soundTraversalPartial") : event?.traversalStatus === "complete" ? text("soundTraversalTyped") : text("soundTraversalDirect");
    const branch = roots ? `${roots} ${text("soundPlayBranches")}` : text("soundDirectMedia");
    const relationLabels = selectorRelations.length ? selectorRelations : relations;
    const triggerLabels = gameplaySoundTriggerLabels(event);
    const playSoundActions = [...new Map(
      (event?.triggerBindings || [])
        .flatMap((binding) => binding?.playSoundActions || [])
        .map((action) => [JSON.stringify(action), action]),
    ).values()];
    const playSoundLabels = playSoundActions.map((action) => {
      const frameWindow = `${text("soundPlaySoundFrame")} ${action?.startFrame ?? "?"}-${action?.endFrame ?? "?"}`;
      const lifetime = action?.stopOnEnd
        ? `${text("soundPlaySoundStopOnEnd")} / ${Number(action?.stopFadeDurationMs || 0)} ms`
        : text("soundPlaySoundNotStoppedOnEnd");
      return `${frameWindow} / ${lifetime}`;
    });
    const dispatchLabels = [];
    for (const definition of event?.actionDispatchEvidence || []) {
      const actionCount = Number(definition?.playbackActionCount || 0);
      const timingLabel = {
        singlePlayback: "soundDispatchSingle",
        coDispatchNoExplicitDelay: "soundDispatchNoExplicitDelay",
        coDispatchWithAuthoredDelayDifference: "soundDispatchDelayDifference",
        coDispatchUniformExplicitDelay: "soundDispatchUniformDelay",
        coDispatchDynamicDelayRangeUnresolved: "soundDispatchDynamicDelay",
        actionParserUnresolved: "soundDispatchParserUnresolved",
      }[definition?.timingClass] || "";
      if (actionCount) {
        dispatchLabels.push(`${actionCount} ${text("soundPlaybackActions")}${timingLabel ? ` / ${text(timingLabel)}` : ""}`);
      }
      for (const action of definition?.actions || []) {
        const ordinal = Number(action?.eventActionOrdinal);
        const actionName = `${text("soundPlaybackAction")} ${Number.isFinite(ordinal) ? ordinal + 1 : "?"}`;
        const delay = action?.delay || {};
        const transition = action?.transition || {};
        const probability = action?.probability || {};
        const explicitParts = [];
        if ((delay.baseValuesMs || []).length) explicitParts.push(`${text("soundActionDelay")} ${(delay.baseValuesMs || []).join(" / ")} ms`);
        if ((delay.modifierRangesMs || []).length) explicitParts.push(`${text("soundActionDelayRange")} ${(delay.modifierRangesMs || []).map((range) => `${range.min ?? "?"}-${range.max ?? "?"}`).join(" / ")} ms`);
        if ((transition.baseValuesMs || []).length) explicitParts.push(`${text("soundActionTransition")} ${(transition.baseValuesMs || []).join(" / ")} ms`);
        if ((probability.baseValuesPercent || []).length) explicitParts.push(`${text("soundActionProbability")} ${(probability.baseValuesPercent || []).join(" / ")}%`);
        if (explicitParts.length) dispatchLabels.push(`${actionName}: ${explicitParts.join(" / ")}`);
      }
    }
    const namespaceIdentity = event?.authoredNamespaceOwnershipStatus === "exactCharacterTableNamespaceIdentity"
      ? `<span>${escapeHtml(text("soundAuthoredNamespaceEvidence"))}</span>`
      : "";
    return `<div class="gameplay-sfx-evidence">${namespaceIdentity}${triggerLabels.map((label) => `<span>${escapeHtml(label)}</span>`).join("")}${playSoundLabels.map((label) => `<span>${escapeHtml(label)}</span>`).join("")}${dispatchLabels.map((label) => `<span>${escapeHtml(label)}</span>`).join("")}<span>${escapeHtml(branch)}</span>${animationCallbacks ? `<span>${escapeHtml(`${animationCallbacks} ${text("soundAuthoredCallbacks")} / ${animationClips} ${text("soundAnimationClips")}`)}</span>` : ""}${definitions ? `<span>${escapeHtml(`${definitions} ${text("soundBankDefinitions")}`)}</span>` : ""}${stopActions ? `<span>${escapeHtml(`${stopActions} ${text("soundStopActions")}`)}</span>` : ""}${relationLabels.map((label) => `<span>${escapeHtml(label)}</span>`).join("")}<span class="${isPartial ? "is-partial" : ""}">${escapeHtml(status)}</span></div>`;
  }

  function renderGameplaySoundCandidateList(event, audio) {
    const cards = audio.map((candidate, index) => {
      const evidence = gameplaySoundMediaEvidence(candidate);
      const visibleMeta = [
        `${text("soundPossibleFile")} ${index + 1}`,
        evidence.roots.length ? `${evidence.roots.length} ${text("soundPlayBranches")}` : "",
        ...evidence.relations,
        Number(candidate.contentEquivalentCount || 0) > 1 ? `${text("soundEquivalentContent")} ×${candidate.contentEquivalentCount}` : "",
      ].filter(Boolean).join(" · ");
      const debugMeta = STATE.showDebug
        ? `<code>${escapeHtml([candidate.mediaId ? `media ${candidate.mediaId}` : "", evidence.soundObjects ? `${evidence.soundObjects} Sound objects` : ""].filter(Boolean).join(" · "))}</code>`
        : "";
      return `<div class="gameplay-projectile-audio-candidate gameplay-sfx-possible-file"><audio controls preload="none" src="${escapeHtml(candidate.src)}"></audio><small>${escapeHtml(visibleMeta)}</small>${debugMeta}</div>`;
    }).join("");
    const list = `<div class="gameplay-sfx-possible-files">${cards}</div>`;
    if (audio.length <= GAMEPLAY_INLINE_AUDIO_LIMIT) return list;
    const count = `${audio.length} ${text("soundPossibleFiles")}`;
    return `<details class="gameplay-sfx-overflow gameplay-sfx-possible-files-overflow"><summary class="gameplay-sfx-list-toggle"><strong>${escapeHtml(count)}</strong><span>${escapeHtml(text("soundOpenToList"))}</span></summary>${list}</details>`;
  }

  function renderGameplaySoundCandidates(event, audio) {
    return audio.length ? renderGameplaySoundCandidateList(event, audio) : "";
  }

  function renderGameplaySoundEvents(events, options = {}) {
    const eventRows = events || [];
    return eventRows.map((event) => {
      const audio = (event.audio || []).filter((candidate) => candidate?.src);
      const evidenceIds = gameplaySoundSkillIds(event);
      const clips = event.sourceAnimationClips || [];
      const trigger = (event.evidence || []).map((row) => row?.triggerKey).find(Boolean) || "";
      const technical = STATE.showDebug ? `<details class="gameplay-sfx-technical"><summary>${escapeHtml(text("projectileTechnical"))}</summary><code class="gameplay-sfx-event-id">${escapeHtml(event.id || "")}</code>${evidenceIds.length ? `<code>${escapeHtml(evidenceIds.join(" / "))}</code>` : ""}${clips.length ? `<code>${escapeHtml(clips.join(" / "))}</code>` : ""}${trigger ? `<code>${escapeHtml(trigger)}</code>` : ""}<a data-gameplay-audio-event href="${escapeHtml(gameplayAudioEventHref(event.id))}">${escapeHtml(text("openInAudio"))}</a></details>` : "";
      const possibleCount = audio.length || Number(event.possibleMediaCount || event.playableCandidates || 0);
      const roots = Number(event.playRootCount || 0);
      const branch = roots ? `${roots} ${text("soundPlayBranches")}` : text("soundDirectMedia");
      const sharedAnimation = gameplaySoundIsSharedAnimation(event);
      const uniqueEventFiles = new Set((audio || []).map((candidate) => candidate?.mediaId != null
        ? `media:${candidate.mediaId}`
        : candidate?.src ? `src:${candidate.src}` : "").filter(Boolean)).size;
      const eventScope = sharedAnimation
        ? `${Number(event.animationOwnerCount || 0)} ${text("soundSharedByCharacters")} · ${possibleCount} ${text("soundGlobalPossibleFiles")}${uniqueEventFiles ? ` · ${uniqueEventFiles} ${text("soundUniqueFiles")}` : ""}`
        : `${branch} · ${possibleCount} ${text("soundPossibleFiles")}${uniqueEventFiles ? ` · ${uniqueEventFiles} ${text("soundUniqueFiles")}` : ""}`;
      const actionLabel = options.showActionLabel ? gameplaySoundActionLabel(gameplaySoundActionGroup(event)) : "";
      const scope = [actionLabel, eventScope].filter(Boolean).join(" · ");
      const boundary = sharedAnimation ? `<p class="gameplay-enemy-sfx-note">${escapeHtml(text("soundSharedRuntimeGraphNote"))}</p>` : "";
      return `<article class="gameplay-sfx-event"><header class="gameplay-sfx-event-summary"><strong>${escapeHtml(gameplaySoundEventName(event.id) || text("soundEvent"))}</strong><span>${escapeHtml(scope)}</span></header>${boundary}${renderGameplaySoundEvidence(event, audio)}${technical}${renderGameplaySoundCandidates(event, audio)}</article>`;
    }).join("");
  }

  function renderGameplaySoundActionGroups(events, options = {}) {
    const groups = new Map();
    for (const event of events || []) {
      const action = gameplaySoundActionGroup(event);
      if (!groups.has(action.key)) groups.set(action.key, { ...action, events: [] });
      groups.get(action.key).events.push(event);
    }
    const priority = ["attack", "skill", "attackVoice", "skillVoice", "reaction", "reactionVoice", "combatVoice", "movement", "action"];
    const orderedGroups = [...groups.values()]
      .sort((left, right) => {
        const leftIndex = priority.indexOf(left.values[0]);
        const rightIndex = priority.indexOf(right.values[0]);
        return (leftIndex < 0 ? 99 : leftIndex) - (rightIndex < 0 ? 99 : rightIndex)
          || gameplaySoundActionLabel(left).localeCompare(gameplaySoundActionLabel(right));
      });
    // Keep one flat event stream. Action ownership remains visible on each
    // event card, but nested action sections made a single skill/enemy page
    // grow into several layers of collapsible-looking containers.
    return orderedGroups
      .map((group) => renderGameplaySoundEvents(group.events, { showActionLabel: true }))
      .join("");
  }

  function renderGameplaySoundEventList(events, playableAudioCount, options = {}) {
    const eventList = renderGameplaySoundActionGroups(events, options);
    if (playableAudioCount <= GAMEPLAY_INLINE_AUDIO_LIMIT) return eventList;
    return `<details class="gameplay-sfx-overflow gameplay-sfx-event-list-overflow"><summary class="gameplay-sfx-list-toggle"><strong>${escapeHtml(gameplaySoundCountText(events, options))}</strong><span>${escapeHtml(text("soundOpenToList"))}</span></summary><div class="gameplay-sfx-event-list">${eventList}</div></details>`;
  }

  function gameplayResolvedSoundEvents(events) {
    const catalog = STATE.integration.soundEffects?.animationEventCatalog || {};
    return (events || []).map((event) => {
      if ((event?.audio || []).length) return event;
      const shared = catalog[String(event?.id || "").toLowerCase()];
      return shared ? { ...shared, ...event, audio: shared.audio || [] } : event;
    });
  }

  function ensureGameplayAnimationCatalog(entry) {
    const payload = STATE.integration.soundEffects;
    const owner = entry?.kind === "character"
      ? payload?.characters?.[entry.id]
      : entry?.kind === "enemy" ? payload?.enemies?.[entry.id] : null;
    if (!payload || payload.animationEventCatalog || payload._animationCatalogLoading || !(owner?.animationEvents || []).length) return;
    const shard = String(payload.animationEventCatalogPath || "");
    if (!shard) return;
    payload._animationCatalogLoading = true;
    fetch(`data/lang/${encodeURIComponent(STATE.language)}/gameplay/${encodeURIComponent(shard)}?v=${GAMEPLAY_INTEGRATION_VERSION}`)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        return response.json();
      })
      .then((catalog) => {
        payload.animationEventCatalog = catalog?.events || {};
      })
      .catch(() => {
        payload.animationEventCatalog = {};
      })
      .finally(() => {
        payload._animationCatalogLoading = false;
        if (STATE.selected?.id === entry.id) renderDetail(STATE.selected);
      });
  }

  function renderGameplaySoundGroup(events, options = {}) {
    const playableEvents = gameplayResolvedSoundEvents(events).filter((event) => (event.audio || []).some((candidate) => candidate?.src) || Number(event.possibleMediaCount || event.playableCandidates || 0) > 0);
    const playable = playableEvents.reduce((total, event) => total + ((event.audio || []).filter((candidate) => candidate?.src).length || Number(event.possibleMediaCount || event.playableCandidates || 0)), 0);
    const playableAudio = playableEvents.reduce((total, event) => total + (event.audio || []).filter((candidate) => candidate?.src).length, 0);
    if (!playable) return "";
    const confidence = options.confidence ? integrationConfidence(options.confidence) : "";
    const wrapper = options.inline ? "div" : "section";
    return `<${wrapper} class="gameplay-related-sfx${options.inline ? " gameplay-sfx-inline" : ""}"><header class="gameplay-related-sfx-summary"><strong>${escapeHtml(options.label || text("relatedSoundEffects"))}</strong><span>${escapeHtml(gameplaySoundCountText(playableEvents, options))}</span>${confidence}</header><p>${escapeHtml(options.note || text("soundRuntimeNote"))}</p>${renderGameplaySoundEventList(playableEvents, playableAudio, options)}</${wrapper}>`;
  }

  function gameplayIntegrationError(kind) {
    return STATE.integration.errors.find((error) => error?.kind === kind) || null;
  }

  function renderSoundEffectsUnavailable() {
    if (STATE.integration.status !== "ready" || !gameplayIntegrationError("soundEffects")) return "";
    return `<div class="gameplay-integration-note is-warning" role="status">${escapeHtml(text("soundEffectsUnavailable"))}</div>`;
  }

  function renderCharacterSkillSounds(entry) {
    const groups = STATE.integration.soundEffects?.characters?.[entry?.id]?.groups || {};
    const events = (entry?.skillGroups || []).flatMap((group) => {
      const soundGroup = groups[group?.id] || {};
      return filterEndministratorVariant(soundGroup.events, entry, (event) => event?.id)
        .filter((event) => !gameplaySoundHasExactSkillTrigger(event));
    });
    return renderGameplaySoundGroup(mergeGameplaySoundEvents(events), {
      label: text("inferredSkillSoundEffects"),
      confidence: "inferred",
      note: text("inferredSkillSoundEffectsNote"),
    });
  }

  function renderActiveSkillSoundEffects(group, character) {
    const groups = STATE.integration.soundEffects?.characters?.[character?.id]?.groups || {};
    const soundGroup = groups[group?.id] || {};
    const events = filterEndministratorVariant(soundGroup.events, character, (event) => event?.id)
      .filter(gameplaySoundHasExactSkillTrigger);
    return renderGameplaySoundGroup(events, {
      label: text("exactSkillSoundEffects"),
      confidence: "direct",
      note: text("soundExactSkillTriggerNote"),
      inline: true,
    });
  }

  function renderEnemySoundEffects(entry) {
    if (!STATE.integration.soundEffects) return renderSoundEffectsUnavailable();
    const sounds = STATE.integration.soundEffects?.enemies?.[entry?.id] || {};
    const playableEvents = gameplayResolvedSoundEvents(mergeGameplaySoundEvents([...(sounds.events || []), ...(sounds.animationEvents || [])]))
      .filter((event) => (event.audio || []).some((candidate) => candidate?.src) || Number(event.possibleMediaCount || event.playableCandidates || 0) > 0);
    const namespaceEvents = filterEndministratorVariant(
      sounds.authoredNamespaceEvents,
      entry,
      (event) => event?.id,
    );
    const namespaceGroup = renderGameplaySoundGroup(namespaceEvents, {
      label: text("authoredEnemyNamespaceAudio"),
      note: text("authoredEnemyNamespaceAudioNote"),
    });
    if (!playableEvents.length) return namespaceGroup;
    const confidence = integrationConfidence(
      sounds.ownershipConfidence === "inferred" || sounds.animationOwnershipConfidence === "inferred" ? "inferred" : "direct",
    );
    const notes = [text("soundRuntimeNote")];
    if ((sounds.animationEvents || []).length) notes.push(text("animationSoundNote"));
    const playableAudio = playableEvents.reduce((total, event) => total + (event.audio || []).filter((candidate) => candidate?.src).length, 0);
    return `${namespaceGroup}<div class="gameplay-enemy-sfx-meta"><strong>${escapeHtml(gameplaySoundCountText(playableEvents))}</strong>${confidence}</div><p class="gameplay-enemy-sfx-note">${escapeHtml(notes.join(" "))}</p>${renderGameplaySoundEventList(playableEvents, playableAudio, { flattenGroups: true })}`;
  }

  function renderCharacterAnimationSounds(entry) {
    const sounds = STATE.integration.soundEffects?.characters?.[entry?.id] || {};
    const animationEvents = filterEndministratorVariant(
      sounds.animationEvents,
      entry,
      (event) => [event?.id, ...(event?.sourceAnimationClips || [])].join(" "),
    );
    const profileVoices = filterEndministratorVariant(sounds.profileVoices, entry, (event) => event?.id);
    const sharedAnimationEvents = animationEvents.filter(gameplaySoundIsSharedAnimation);
    const ownerAnimationEvents = animationEvents.filter((event) => !gameplaySoundIsSharedAnimation(event));
    return `${renderGameplaySoundGroup(ownerAnimationEvents, {
      label: text("animationTriggeredSounds"),
      confidence: sounds.animationOwnershipConfidence,
      note: text("animationSoundNote"),
    })}${renderGameplaySoundGroup(sharedAnimationEvents, {
      label: text("soundSharedAnimationSystems"),
      confidence: sounds.animationOwnershipConfidence,
      note: text("soundSharedRuntimeGraphNote"),
      sharedGraph: true,
    })}${renderGameplaySoundGroup(profileVoices, {
      label: text("combatVoice"),
      confidence: "direct",
      note: text("profileVoiceNote"),
    })}`;
  }

  function renderCharacterSoundEffects(entry) {
    if (!STATE.integration.soundEffects) return renderSoundEffectsUnavailable();
    const namespaceEvents = filterEndministratorVariant(
      STATE.integration.soundEffects?.characters?.[entry?.id]?.authoredNamespaceEvents,
      entry,
      (event) => event?.id,
    );
    const authoredNamespaces = renderGameplaySoundGroup(namespaceEvents, {
      label: text("authoredNamespaceAudio"),
      note: text("authoredNamespaceAudioNote"),
    });
    return `${renderCharacterSkillSounds(entry)}${renderCharacterAnimationSounds(entry)}${authoredNamespaces}`;
  }

  function renderCharacterProjectileCompact(match) {
    const projectile = match?.projectile || match;
    const lifetime = projectile?.lifetime || {};
    const collision = projectile?.collision || {};
    const targeting = projectile?.targeting || {};
    const filter = targeting.targetFilter || {};
    const movement = projectile?.movement || {};
    const modes = movement.modes || [];
    const mode = modes[0] || {};
    const effectNames = [...new Set(Object.values(projectile?.effects?.lists || {}).flat().map((effect) => effect?.effectName).filter(Boolean))];
    const soundRows = projectileSoundRows(projectile);
    const audioCandidateCount = soundRows.reduce((total, row) => total + row.audio.length, 0);
    const behaviorSkills = projectileBehaviorSkillIds(projectile);
    const matchedActions = match?.matchMethod === "skill-family-identifier"
      ? []
      : (match?.matched || []).filter((value) => String(value || "").includes("_"));
    const summaryFacts = [
      [text("projectileLifetimeShort"), projectileScalarText(lifetime.finishDuration)].filter(Boolean).join(" "),
      [text("projectileDistanceShort"), projectileScalarText(lifetime.finishDistance)].filter(Boolean).join(" "),
      [text("projectileHitsShort"), projectileHitLimitText(targeting.maxHitCount)].filter(Boolean).join(" "),
      audioCandidateCount ? `${audioCandidateCount} ${text("projectileAudioShort")}` : "",
    ].filter(Boolean);
    const travelSummary = [
      modes.map((item) => [item.key, projectileScalarText(item.speed) ? `${text("projectileSpeed")} ${projectileScalarText(item.speed)}` : ""].filter(Boolean).join(" · ")).filter(Boolean).join("; "),
      lifetime.finishOnReach ? text("projectileFinishOnReach") : "",
      lifetime.hitOnReach ? text("projectileHitOnReach") : "",
    ].filter(Boolean).join(" · ");
    const hitSummary = [
      projectileFriendlyEnum(collision.shapeType),
      targeting.allowHitSameTarget ? text("projectileRepeatHit") : text("projectileSingleHit"),
      projectileFriendlyTagText(filter),
    ].filter(Boolean).join(" · ");
    const feedbackSummary = [
      effectNames.length ? `${effectNames.length} ${text("projectileEffectRefs")}` : "",
      soundRows.length ? `${soundRows.length} ${text("projectileSoundPhases")}` : "",
    ].filter(Boolean).join(" · ");
    const detailFacts = [
      matchedActions.length ? [text("projectileAction"), matchedActions.join(", ")] : null,
      [text("projectileAssignment"), projectileMatchMethodText(match?.matchMethod)],
      [text("projectileLifetime"), [projectileScalarText(lifetime.finishDuration), projectileScalarText(lifetime.finishDistance), lifetime.finishOnReach ? text("projectileFinishOnReach") : "", lifetime.hitOnReach ? text("projectileHitOnReach") : ""].filter(Boolean).join(" / ")],
      [text("projectileMovement"), modes.map((item) => [item.key, projectileEnumText(item.moveType), projectileScalarText(item.speed), item.surroundCenterKey].filter(Boolean).join(" / ")).filter(Boolean).join("; ")],
      (movement.segments || []).length ? [text("projectileSegments"), (movement.segments || []).map((segment) => [segment.startPointKey, segment.moveModeId, segment.endPointKey, segment.skipHitAndBlockDetection ? text("projectileSkipCollision") : ""].filter(Boolean).join(" -> ")).join("; ")] : null,
      [text("projectileCollision"), [projectileEnumText(collision.shapeType), projectileScalarText(collision.radius), projectileVectorText(collision.extent)].filter(Boolean).join(" / ")],
      [text("projectileTargeting"), [projectileScalarText(targeting.maxHitCount), targeting.allowHitSameTarget ? `${text("projectileRepeatHit")} / ${formatValue(targeting.hitIntervalPerTarget)}` : text("projectileSingleHit"), projectileEnumText(targeting.collisionDetectTiming), projectileEnumText(filter.objectType), projectileTagText(filter)].filter(Boolean).join(" / ")],
      [text("projectileDetectionDelay"), [projectileScalarText(targeting.hitAndBlockDetectDelayTime), projectileScalarText(targeting.hitAndBlockDetectDelayDistance), targeting.canTraceTargetAfterReach ? text("projectileTraceAfterReach") : ""].filter(Boolean).join(" / ")],
      effectNames.length ? [text("projectileEffects"), effectNames.join(", ")] : null,
      behaviorSkills.length ? [text("projectileBehaviorSkills"), behaviorSkills.join(", ")] : null,
      [text("source"), [projectile?.source?.root, projectile?.source?.assetName, projectile?.source?.pathId].filter(Boolean).join(" / ")],
    ].filter((row) => row && row[1]);
    const complete = projectile?.confidence?.byteComplete;
    const overview = [travelSummary, hitSummary, feedbackSummary].filter(Boolean).join(" · ");
    const technical = STATE.showDebug ? `<details class="gameplay-projectile-technical"><summary>${escapeHtml(text("projectileTechnical"))}</summary><div class="gameplay-projectile-inline-details">${detailFacts.map(([label, value]) => `<span><b>${escapeHtml(label)}</b><code>${escapeHtml(value)}</code></span>`).join("")}</div></details>` : "";
    return `<details class="gameplay-projectile-inline"><summary><span class="gameplay-projectile-friendly-name">${escapeHtml(projectileFriendlyName(projectile))}</span><span class="gameplay-projectile-status${complete ? " is-complete" : ""}">${escapeHtml(complete ? text("projectileComplete") : text("projectilePartial"))}</span><span class="gameplay-projectile-summary-chips">${summaryFacts.map((fact) => `<small>${escapeHtml(fact)}</small>`).join("")}</span></summary><div class="gameplay-projectile-body">${overview ? `<div class="gameplay-projectile-overview"><strong>${escapeHtml(text("projectileBehaviorSummary"))}</strong><span>${escapeHtml(overview)}</span></div>` : ""}${renderProjectileAudio(soundRows)}${technical}</div></details>`;
  }

  // One active skill (a skill group - Normal Attack / Skill / Ultimate /
  // Combo) can be made of several authored sub-skills (combo hits, charged
  // variants, ...). Merge their matched projectiles into a single deduped
  // list plus whatever the group-level fallback match picks up, so the
  // right-hand column shows every projectile that belongs to this skill
  // exactly once.
  function projectilesForGroup(group) {
    const assigned = new Set();
    // The generated payload normally carries full skill rows. Keep the action
    // ID as a safe fallback so a partial export cannot silently lose a
    // projectile (or make its ownership appear to belong to another group).
    const skills = group.skills?.length
      ? group.skills
      : (group.actionSkillIds || []).map((id) => ({ id: String(id || "") })).filter((skill) => skill.id);
    const siblingSkillIds = skills.map((skill) => skill?.id).filter(Boolean);
    const matched = [];
    for (const skill of skills) {
      for (const row of projectilesForSkill(skill, siblingSkillIds)) {
        const id = String(row.projectile?.id || "");
        if (!id || assigned.has(id)) continue;
        assigned.add(id);
        matched.push(row);
      }
    }
    matched.push(...projectilesForSkillGroupUnassigned(group, assigned));
    return matched;
  }

  function renderActiveSkillProjectiles(group) {
    const label = `<div class="gameplay-active-skill-col-label">${escapeHtml(text("projectiles"))}</div>`;
    const projectiles = projectilesForGroup(group);
    if (!projectiles.length) {
      return `<div class="gameplay-active-skill-projectiles">${label}<span class="gameplay-projectile-no-template">${escapeHtml(text("projectileNoTemplate"))}</span></div>`;
    }
    const chips = projectiles.map(renderCharacterProjectileCompact).join("");
    return `<div class="gameplay-active-skill-projectiles">${label}<div class="gameplay-skill-projectiles">${chips}</div></div>`;
  }

  function renderUnassignedCharacterProjectiles(entry) {
    if (!STATE.showDebug) return "";
    const assigned = new Set();
    for (const group of entry?.skillGroups || []) {
      for (const row of projectilesForGroup(group)) assigned.add(String(row.projectile?.id || ""));
    }
    const unresolved = projectilesForEntry(entry)
      .filter(({ projectile }) => !assigned.has(String(projectile?.id || "")))
      .map((row) => ({ ...row, matched: [], matchMethod: "ownership-unresolved" }));
    if (!unresolved.length) return "";
    return `<details class="gameplay-projectile-unassigned"><summary>${escapeHtml(`${text("projectileOwnershipUnresolved")} (${unresolved.length})`)}</summary><p>${escapeHtml(text("projectileOwnershipUnresolvedNote"))}</p><div class="gameplay-skill-projectiles">${unresolved.map(renderCharacterProjectileCompact).join("")}</div></details>`;
  }

  // Small debug-only combat-log evidence badge folded into the description
  // column so it does not need its own row.
  function renderActiveSkillCombatMeta(group, character) {
    if (!STATE.showDebug) return "";
    const edges = filterEndministratorVariant(
      combatEdgesForNode(`skill_group:${group.id}`),
      character,
      (edge) => [edge?.source, edge?.target, edge?.evidence?.raw].join(" "),
    );
    if (!edges.length) return "";
    const direct = edges.filter((edge) => edge.confidence === "direct").length;
    return `<div class="gameplay-skill-evidence-summary"><span class="gameplay-skill-evidence-chip"><b>${escapeHtml(text("skillCombat"))}</b>${formatNumber(edges.length)} / ${formatNumber(direct)} ${escapeHtml(text("directEvidence"))}</span></div>`;
  }

  // Active-skill table: one row per skill group (Normal Attack / Skill /
  // Ultimate / Combo, i.e. the character's playable active skills, as
  // opposed to passive talents). Column 1 is the authored description,
  // column 2 is the selected level's buff numbers and upgrade cost. Debug mode
  // Column 3 keeps the useful projectile summary visible in normal mode;
  // debug-only identifiers and ownership evidence stay inside each card.
  function renderActiveSkillTableHeader() {
    const columns = [text("description"), text("level"), text("projectiles")];
    return `<div class="gameplay-active-skill-header" aria-hidden="true">${columns.map((label) => `<span>${escapeHtml(label)}</span>`).join("")}</div>`;
  }

  function renderActiveSkillRow(group, character) {
    const skillType = characterSkillIconType(group);
    const elementToken = String(character?.element || "").trim().toLowerCase();
    const elementClass = ["normal-skill", "ultimate", "combo"].includes(skillType)
      && ["cryst", "fire", "natural", "physical", "pulse"].includes(elementToken)
      ? `gameplay-attack-skill-element-${elementToken}`
      : "";
    const groupIcon = renderGameplayTokenIcon(group.iconId, group.name || group.id, {
      skillType,
      className: elementClass,
    });
    const meta = [group.typeLabel, group.id, group.iconId ? `${text("iconId")}: ${group.iconId}` : ""].filter(Boolean).join(" / ");
    return `<article class="gameplay-active-skill-row">
      <div class="gameplay-active-skill-desc">
        <div class="gameplay-group-title-wrap">${groupIcon}<div class="gameplay-group-title">${escapeHtml(group.name || group.id || "")}</div></div>
        <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
        ${renderActiveSkillCombatMeta(group, character)}
        ${renderDescription(group.description)}
        ${renderActiveSkillSoundEffects(group, character)}
      </div>
      ${renderActiveSkillLevels(group)}
      ${renderActiveSkillProjectiles(group)}
    </article>`;
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
    const variantEntry = endministratorVariantEntry(entry);
    const facts = [
      fact(text("id"), entry.id, { mono: true }),
      fact(text("rarity"), entry.rarity),
      fact(text("profession"), entry.professionLabel || entry.profession),
      fact(text("element"), entry.elementLabel || entry.element),
      fact(text("weaponType"), entry.weaponTypeLabel || entry.weaponType),
      fact(text("defaultWeapon"), entry.defaultWeaponName || entry.defaultWeaponId),
      fact(text("source"), `${entry.source && entry.source.table || ""} / ${entry.source && entry.source.id || ""}`, { mono: true }),
    ].filter(Boolean);
    const skillRows = (variantEntry.skillGroups || []).map((group) => renderActiveSkillRow(group, variantEntry)).join("");
    const unresolvedProjectiles = renderUnassignedCharacterProjectiles(variantEntry);
    const talentGroups = renderTalentGroups(entry.talentGroups || []);
    const talentCards = (entry.talents || []).map(renderTalentCard).join("");
    const characterAssets = renderCharacterAssetStrip(entry);
    const variantControl = renderEndministratorVariantControl(entry);
    return {
      facts,
      body: [
        section(text("characterAssets"), `${variantControl}${characterAssets}`),
        section(text("characterSkills"), skillRows || unresolvedProjectiles ? `${skillRows ? `<div class="gameplay-active-skill-table${STATE.showDebug ? " is-debug" : ""}">${renderActiveSkillTableHeader()}<details class="gameplay-guidance"><summary>${escapeHtml(text("projectileCoverageHelp"))}</summary><p>${escapeHtml(text("projectileCoverageNote"))}</p></details>${skillRows}</div>` : ""}${unresolvedProjectiles}` : ""),
        section(text("talents"), talentGroups || (talentCards ? `<div class="gameplay-card-grid">${talentCards}</div>` : "")),
        section(text("characterBreakthroughs"), renderCharacterBreakthroughs(entry)),
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

  const BUFF_STACKING_LABEL_KEYS = {
    HighPriorityWithMaxStack: "buffStackHighPriorityWithMaxStack",
    OverwriteDuration: "buffStackOverwriteDuration",
    Unique: "buffStackUnique",
    Extend: "buffStackExtend",
    Enhance: "buffStackEnhance",
    HighPriority: "buffStackHighPriority",
    Unlimited: "buffStackUnlimited",
    Stack: "buffStackStack",
    Refresh: "buffStackRefresh",
    Modify: "buffStackModify",
    EnhanceAndRefresh: "buffStackEnhanceAndRefresh",
    EnhanceAndOverwriteDuration: "buffStackEnhanceAndOverwriteDuration",
  };

  const MODIFIER_LABEL_KEYS = {
    Addition: "modifierAddition",
    Multiplier: "modifierMultiplier",
    FinalAddition: "modifierFinalAddition",
    FinalMultiplier: "modifierFinalMultiplier",
    BaseAddition: "modifierBaseAddition",
    BaseMultiplier: "modifierBaseMultiplier",
    BaseFinalAddition: "modifierBaseFinalAddition",
    BaseFinalMultiplier: "modifierBaseFinalMultiplier",
    None: "modifierNone",
    Enum: "modifierEnum",
  };

  const MODIFIER_TARGET_LABEL_KEYS = {
    Specific: "modifierTargetSpecific",
    Main: "modifierTargetMain",
    Sub: "modifierTargetSub",
    All: "modifierTargetAll",
  };

  const BUFF_FLAG_LABEL_KEYS = {
    ignoreCooldownWhenAdding: "buffFlagIgnoreAddingCooldown",
    ignoreTagImmune: "buffFlagIgnoreTagImmune",
    onlyUseSelfTimeDilation: "buffFlagSelfTimeDilationOnly",
    useTimeDilationDt: "buffFlagUseTimeDilationDt",
    waitFirstTriggerInterval: "buffFlagWaitFirstInterval",
  };

  const BUFF_ABILITY_EVENT_LABEL_KEYS = {
    OnOwnerHpZero: "buffEventOwnerHpZero",
    OnTakeDamage: "buffEventTakeDamage",
    OnBeforeCastSkill: "buffEventBeforeCastSkill",
    OnSkillEnd: "buffEventSkillEnd",
    OnAfterOutputWeaknessTriggered: "buffEventAfterWeaknessTriggered",
  };

  const BUFF_BRANCH_LABEL_KEYS = {
    condition: "buffActionBranchCondition",
    fail: "buffActionBranchFail",
    succeed: "buffActionBranchSucceed",
  };

  // Keep branch provenance beside each decoded object while retaining the
  // existing semantic rendering checks below.  A WeakMap avoids mutating the
  // generated data payload with frontend-only state.
  const buffActionBranchByDecoded = new WeakMap();
  // Action summaries are frontend-only as well.  Keep the bounded technical
  // coordinates beside decoded objects without publishing them into the
  // generated payload or rendering raw byte dumps in normal mode.
  const buffActionSummaryByDecoded = new WeakMap();

  function buffRecord(id) {
    return STATE.index?.buffs?.[String(id || "")] || null;
  }

  function buffIdentifierHint(id) {
    const value = String(id || "").toLowerCase();
    const rules = [
      [/damage_immune|dmg_immune|invincible|_wudi|full_immune/, "buffHintDamageImmune"],
      [/shield/, "buffHintShield"],
      [/reducecd|cooldown|nocd|_cd_|cdreset/, "buffHintCooldown"],
      [/slow|speed_down/, "buffHintSlow"],
      [/superarmor|super_armor/, "buffHintSuperArmor"],
      [/resilience|poise|fragile/, "buffHintPoise"],
      [/explode_on_death|deathskill|realdead|undeadable|_dead/, "buffHintDeathAction"],
      [/addtag|add_tag/, "buffHintAddTag"],
      [/born_fx|bornfx|endinggame_vfx|effect_asset|vfx|_fx|lighting_fx/, "buffHintVisual"],
      [/settlement/, "buffHintSettlement"],
      [/take_power_attack_only/, "buffHintPowerAttackOnly"],
      [/norootmotion/, "buffHintNoRootMotion"],
      [/teleport/, "buffHintTeleport"],
      [/deduct_hp|checkhp|hp_listener/, "buffHintHpCondition"],
      [/counter|behit_counter/, "buffHintCounter"],
      [/absorb/, "buffHintAbsorb"],
      [/summon|minion/, "buffHintSummon"],
      [/dung_coin|minibreak_coin/, "buffHintDungeonCoin"],
      [/camera/, "buffHintCamera"],
      [/interrupt/, "buffHintInterrupt"],
      [/angry/, "buffHintAngry"],
      [/support/, "buffHintSupport"],
      [/phantom/, "buffHintPhantom"],
      [/born|_race|hdg\d|_hard|_quest|prolog|_train|_dg\d|e\d+m\d/, "buffHintModeState"],
    ];
    const match = rules.find(([pattern]) => pattern.test(value));
    return text(match ? match[1] : "buffHintInternal");
  }

  function buffLifeLabel(lifeType) {
    if (!lifeType) return "";
    if (lifeType.name === "Infinity") return text("buffLifeInfinity");
    if (lifeType.name === "Limited") return text("buffLifeLimited");
    return lifeType.name || formatValue(lifeType.value);
  }

  function blackboardValue(row) {
    if (!row) return "";
    const value = row.value;
    return row.useBlackboardKey && row.blackboardKey
      ? `${row.blackboardKey} (${formatValue(value)})`
      : formatValue(value);
  }

  function buffCompareLabel(value) {
    return ({ 0: "<", 1: "≤", 2: ">", 3: "≥", 4: "=" })[Number(value)]
      || `${text("buffCompareType")} ${formatValue(value)}`;
  }

  function buffTargetSettingsSummary(settings) {
    if (!settings || settings.status !== "exact") return "";
    const parts = [];
    if (settings.targetGroupKey) parts.push(`group=${settings.targetGroupKey}`);
    if (settings.targetContextKey) parts.push(`context=${settings.targetContextKey}`);
    if (settings.ownerContextKey) parts.push(`owner=${settings.ownerContextKey}`);
    if (Number.isFinite(Number(settings.targetSource))) parts.push(`source=${formatValue(settings.targetSource)}`);
    if (Number.isFinite(Number(settings.target))) parts.push(`target=${formatValue(settings.target)}`);
    if (Number.isFinite(Number(settings.selectorOwner))) parts.push(`selector=${formatValue(settings.selectorOwner)}`);
    if (Number.isFinite(Number(settings.selectorDirection))) parts.push(`direction=${formatValue(settings.selectorDirection)}`);
    return parts.join(", ");
  }

  function buffActionCoverageStatus(decoded, item) {
    const decodedStatus = decoded && typeof decoded === "object" ? decoded.decodeStatus : "";
    const status = decodedStatus || (item && item.decodeStatus);
    if (status === "exact") return "exact";
    if (status === "partial") return "partial";
    return "unresolved";
  }

  function buffActionSummary(decoded, item) {
    const source = decoded && typeof decoded === "object" ? decoded : {};
    const summary = {
      status: buffActionCoverageStatus(decoded, item),
      type: source.type || item?.name || "",
      tag: item?.tag || "",
      memberCount: item?.memberCount ?? source.memberCount,
      semanticStatus: source.semanticStatus || "",
      offset: item?.offset || source.offset || "",
      bytes: item?.bytes ?? source.byteLength,
      boundaryProof: item?.boundaryProof || source.boundaryProof || "",
      decoded: source,
    };
    return summary;
  }

  function buffActionDebugStats(value, path = "", out = [], depth = 0) {
    if (!value || typeof value !== "object" || depth > 3 || out.length >= 8) return out;
    if (Array.isArray(value)) return out;
    for (const [key, child] of Object.entries(value)) {
      const childPath = path ? `${path}.${key}` : key;
      if (typeof child === "string" && /sha256$/i.test(key) && /^[0-9a-f]{64}$/i.test(child)) {
        out.push({ label: `${childPath} SHA-256`, value: child });
        continue;
      }
      if (Array.isArray(child)) {
        out.push({ label: `${childPath} count`, value: child.length });
        continue;
      }
      if (child && typeof child === "object") buffActionDebugStats(child, childPath, out, depth + 1);
      if (out.length >= 8) break;
    }
    return out;
  }

  function renderBuffActionTechnical(summary) {
    if (!STATE.showDebug || !summary || summary.status === "exact") return "";
    const pairs = [
      { label: text("buffActionTechnicalType"), value: summary.type },
      { label: text("buffActionTechnicalTag"), value: summary.tag },
      { label: text("buffActionTechnicalMemberCount"), value: summary.memberCount },
      { label: text("buffActionTechnicalStatus"), value: summary.status },
      { label: text("buffActionTechnicalSemanticStatus"), value: summary.semanticStatus },
      { label: text("buffActionTechnicalOffset"), value: summary.offset },
      { label: text("buffActionTechnicalBytes"), value: summary.bytes },
      ...buffActionDebugStats(summary.decoded),
    ].filter((item) => item.value !== undefined && item.value !== null && item.value !== "");
    if (!pairs.length) return "";
    return `<details class="gameplay-buff-action-technical"><summary>${escapeHtml(text("buffActionTechnical"))}</summary>${renderChipPairs(pairs)}</details>`;
  }

  function buffDecodedActions(sequence) {
    const rows = [];
    const visitSequence = (candidate, branch = "") => {
      (candidate?.actionDataItems || []).forEach((item) => {
        const decoded = item?.decoded && typeof item.decoded === "object" ? item.decoded : {};
        const summary = buffActionSummary(decoded, item);
        buffActionBranchByDecoded.set(decoded, branch);
        buffActionSummaryByDecoded.set(decoded, summary);
        rows.push(decoded);
        visitSequence(decoded.conditionAction, branch ? `${branch}.condition` : "condition");
        visitSequence(decoded.failActions, branch ? `${branch}.fail` : "fail");
        visitSequence(decoded.succeedActions, branch ? `${branch}.succeed` : "succeed");
      });
    };
    visitSequence(sequence);
    return rows;
  }

  function buffAttributeModifierPairs(record) {
    return ((record.attributeModifier || {}).attributeModifiers || []).map((modifier) => {
      if (!modifier) return null;
      const attributeLabel = statAttrLabel({
        type: modifier.attributeType,
        key: `attr_${modifier.attributeType}`,
        label: modifier.attributeTypeName,
      });
      const targetLabel = modifier.modifyAttributeTypeName
        ? text(MODIFIER_TARGET_LABEL_KEYS[modifier.modifyAttributeTypeName] || "modifierTargetUnknown")
        : `${text("modifierTargetUnknown")} ${formatValue(modifier.modifyAttributeType)}`;
      const formulaLabel = modifier.formulaItemName
        ? text(MODIFIER_LABEL_KEYS[modifier.formulaItemName] || "modifierUnknown")
        : `${text("modifierType")} ${formatValue(modifier.formulaItem)}`;
      return {
        label: [attributeLabel, targetLabel, formulaLabel].filter(Boolean).join(" / "),
        value: blackboardValue(modifier.param),
      };
    }).filter(Boolean);
  }

  function renderBuffAbilityEventActions(record) {
    const actionGroupCount = (record.abilityEventActions || []).length;
    const coverage = { exact: 0, partial: 0, unresolved: 0, total: 0 };
    const groups = (record.abilityEventActions || []).map((eventMap, groupIndex) => {
      if (!eventMap) return "";
      const rows = [];
      let activeBranch = "";
      let activeSummary = null;
      let activeCoverage = "unresolved";
      const rawPush = rows.push.bind(rows);
      rows.push = (row) => rawPush({
        ...row,
        branch: activeBranch,
        coverage: row.coverage || activeCoverage,
        actionSummary: row.actionSummary || activeSummary,
      });
      (eventMap.actions || []).forEach((sequence) => {
        buffDecodedActions(sequence).forEach((decoded) => {
          const summary = buffActionSummaryByDecoded.get(decoded) || buffActionSummary(decoded, null);
          activeSummary = summary;
          activeCoverage = summary.status;
          coverage[summary.status] += 1;
          coverage.total += 1;
          const rowStart = rows.length;
          activeBranch = buffActionBranchByDecoded.get(decoded) || "";
          if (decoded.semanticStatus === "exact-skill-id-condition") {
            const ids = (decoded.skillIdList || []).map((entry) => blackboardValue(entry)).filter(Boolean);
            if (ids.length) rows.push({ label: text("buffActionCheckSkillId"), value: ids.join(", ") });
          }
          if (decoded.semanticStatus === "exact-skill-cooldown-operation") {
            const operation = decoded.functionTypeName === "Set"
              ? text("buffActionSetCooldown")
              : decoded.functionTypeName === "Reduce"
                ? text("buffActionReduceCooldown")
                : `${text("buffActionUnknownCooldown")}: ${formatValue(decoded.functionTypeName ?? decoded.functionType)}`;
            const target = decoded.useSkillType
              ? (decoded.skillTypeMaskName || formatValue(decoded.skillTypeMask))
              : decoded.skillId;
            const rawAmount = blackboardValue(decoded.value);
            const amount = decoded.isPercentage
              ? `${rawAmount}%`
              : `${rawAmount} ${text("secondsShort")}`;
            rows.push({ label: operation, value: target ? `${target}: ${amount}` : amount });
          }
          if (decoded.semanticStatus === "exact-super-armor-condition") {
            rows.push({
              label: text("buffActionCheckSuperArmor"),
              value: `${buffCompareLabel(decoded.compareType)} ${blackboardValue(decoded.value)}`,
            });
          }
          if (decoded.semanticStatus === "exact-buff-id-context-condition") {
            const ids = (decoded.buffIdList || []).map((entry) => entry?.value || blackboardValue(entry)).filter(Boolean);
            const tags = gameplayTagQueryValues(decoded.query);
            rows.push({ label: text("buffActionCheckBuffId"), value: [...ids, ...tags].join(", ") || text("buffActionContextBuff") });
          }
          if (decoded.semanticStatus === "exact-buff-stack-condition") {
            const ids = decoded.advanced ? (decoded.buffSettings?.buffIds || []) : [decoded.buffId].filter(Boolean);
            rows.push({
              label: text("buffActionCheckBuffStack"),
              value: `${ids.join(", ") || text("buffActionTargetBuff")} ${buffCompareLabel(decoded.compareType)} ${blackboardValue(decoded.value)}`,
            });
          }
          if (decoded.semanticStatus === "exact-hp-condition") {
            const threshold = blackboardValue(decoded.value);
            rows.push({ label: decoded.isRatio ? text("buffActionCheckHpRatio") : text("buffActionCheckHp"), value: `${buffCompareLabel(decoded.compareType)} ${threshold}${decoded.isRatio ? "%" : ""}` });
          }
          if (decoded.semanticStatus === "exact-poise-value-condition") {
            rows.push({ label: text("buffActionCheckPoise"), value: `${buffCompareLabel(decoded.compareType)} ${blackboardValue(decoded.value)}` });
          }
          if (decoded.semanticStatus === "exact-damage-type-condition") {
            const damageName = ({ 0: text("damagePhysical"), 1: text("damageReal"), 2: text("damageFire"), 3: text("damagePulse"), 4: text("damageCryst"), 5: text("damageLifeDrain"), 6: text("damageNatural"), 7: text("damageEther") })[Number(decoded.damageType)];
            rows.push({ label: text("buffActionCheckDamageType"), value: damageName || formatValue(decoded.damageType) });
          }
          if (decoded.semanticStatus === "exact-gameplay-tag-condition") {
            rows.push({ label: text("buffActionCheckTag"), value: gameplayTagQueryValues(decoded.query).join(", ") || text("buffActionConfiguredTagQuery") });
          }
          if (decoded.semanticStatus === "exact-timed-marker-condition") {
            rows.push({ label: text("buffActionCheckTimedMarker"), value: decoded.useBlackboardKey ? decoded.blackboardKey : decoded.markerId });
          }
          if (decoded.semanticStatus === "exact-object-type-condition") {
            rows.push({ label: text("buffActionCheckObjectType"), value: formatValue(decoded.objectTypeMask) });
          }
          if (decoded.semanticStatus === "exact-probability-condition") {
            const probability = Number(decoded.probability?.value);
            rows.push({ label: text("buffActionProbability"), value: Number.isFinite(probability) ? `${formatValue(probability * 100)}%` : blackboardValue(decoded.probability) });
          }
          if (decoded.semanticStatus === "exact-distance-condition") {
            rows.push({ label: text("buffActionCheckDistance"), value: `${decoded.lessThan ? "<" : "≥"} ${formatValue(decoded.distance)}` });
          }
          if (decoded.semanticStatus === "exact-consume-buff-layer-condition") {
            rows.push({ label: text("buffActionConsumeBuffLayer"), value: `${buffCompareLabel(decoded.compareType)} ${blackboardValue(decoded.num)}` });
          }
          if (decoded.semanticStatus === "exact-global-cooldown-condition") {
            rows.push({ label: text("buffActionCheckGlobalCooldown"), value: decoded.buffId });
          }
          if (decoded.semanticStatus === "exact-targets-equal-condition") {
            rows.push({ label: text("buffActionCheckTargetsEqual"), value: text("enabled") });
          }
          if (decoded.semanticStatus === "exact-main-character-target-condition") {
            rows.push({ label: text("buffActionCheckMainCharacter"), value: text("enabled") });
          }
          if (decoded.semanticStatus === "exact-damage-decorate-mask-condition") {
            rows.push({
              label: text("buffActionCheckDamageMask"),
              value: `${decoded.maskHex || formatValue(decoded.mask)} (${text("buffCompareType")} ${formatValue(decoded.checkType)})`,
            });
          }
          if (decoded.semanticStatus === "exact-create-timed-marker-action") {
            const markerId = blackboardValue(decoded.markerId);
            const duration = blackboardValue(decoded.duration);
            rows.push({
              label: text("buffActionCreateTimedMarker"),
              value: [markerId, duration ? `${duration} ${text("secondsShort")}` : ""].filter(Boolean).join(": "),
            });
          }
          if (decoded.semanticStatus === "partial-effect-action-cfg-and-target-settings-opaque") {
            const effectIds = (decoded.effectActionCfgPartial?.stringHits || [])
              .map((entry) => String(entry?.value || ""))
              .filter(Boolean);
            const effectName = effectIds[0] || decoded.bigEffectName || text("buffActionOpaquePayload");
            const target = buffTargetSettingsSummary(decoded.targetSettingsEnvelopePartial);
            rows.push({ label: text("buffActionConfiguredCandidate"), value: [effectName, target].filter(Boolean).join(" · ") });
          }
          if (decoded.semanticStatus === "partial-create-buff-input-tail-and-target-settings-opaque") {
            const buffIds = (decoded.buffsPartial?.items || []).map((entry) => entry?.buffId).filter(Boolean);
            const target = buffTargetSettingsSummary(decoded.targetSettingsEnvelopePartial);
            if (buffIds.length) rows.push({ label: text("buffActionRecoveredBuffIds"), value: [buffIds.join(", "), target].filter(Boolean).join(" · ") });
          }
          if (decoded.semanticStatus === "exact-finish-buff-action") {
            const buffIds = (decoded.buffIds || []).filter(Boolean);
            rows.push({
              label: text("buffActionFinishBuff"),
              value: decoded.finishAll ? `${buffIds.join(", ") || text("buffActionTargetBuff")} (${text("buffFinishAll")})` : (buffIds.join(", ") || text("buffActionTargetBuff")),
            });
          }
          if (decoded.semanticStatus === "exact-finish-buff-advanced-action") {
            rows.push({ label: text("buffActionFinishBuff"), value: (decoded.buffSettings?.buffIds || []).join(", ") || text("buffActionConfiguredBuffQuery") });
          }
          if (decoded.semanticStatus === "exact-finish-owner-action") {
            rows.push({ label: text("buffActionFinishOwner"), value: decoded.skipDieDisplay ? text("buffActionSkipDeathDisplay") : text("enabled") });
          }
          if (decoded.semanticStatus === "exact-add-global-cooldown-action") {
            rows.push({ label: text("buffActionAddGlobalCooldown"), value: `${decoded.buffId}: ${blackboardValue(decoded.cdTime)} ${text("secondsShort")}` });
          }
          if (decoded.semanticStatus === "exact-cast-skill-action") {
            rows.push({ label: text("buffActionCastSkill"), value: blackboardValue(decoded.skillId) });
          }
          if (decoded.semanticStatus === "exact-obtain-cost-action") {
            const costType = Number(decoded.costType) === 1 ? text("buffResourceAtb") : text("buffResourceUltimateSp");
            rows.push({ label: text("buffActionObtainCost"), value: `${costType}: ${blackboardValue(decoded.costValue)} × ${blackboardValue(decoded.coefficient)}` });
          }
          if (decoded.semanticStatus === "exact-spawn-interactive-gold-coin-action") {
            rows.push({ label: text("buffActionSpawnGoldCoin"), value: blackboardValue(decoded.count) });
          }
          if (decoded.semanticStatus === "exact-save-ai-blackboard-value-action") {
            rows.push({ label: text("buffActionSaveAiBlackboard"), value: `${decoded.aiBBKey} → ${decoded.skillBBKey || decoded.skillXKey || decoded.skillYKey || decoded.skillZKey}` });
          }
          if (decoded.semanticStatus === "exact-simple-blackboard-calculation-action") {
            const operation = decoded.operationName || formatValue(decoded.operation);
            rows.push({ label: text("buffActionCalculateBlackboard"), value: `${decoded.key}: ${blackboardValue(decoded.value1)} ${operation} ${blackboardValue(decoded.value2)}` });
          }
          if (decoded.semanticStatus === "exact-compare-float-action") {
            const compare = decoded.compareName || buffCompareLabel(decoded.compare);
            rows.push({
              label: text("buffActionCompareBlackboard"),
              value: `${blackboardValue(decoded.valueA)} ${compare} ${blackboardValue(decoded.valueB)}`,
            });
          }
          if (decoded.semanticStatus === "exact-special-game-event-action") {
            rows.push({ label: text("buffActionSpecialGameEvent"), value: formatValue(decoded.specialGameEventType) });
          }
          if (decoded.semanticStatus === "exact-obtain-atb-type-condition") {
            rows.push({
              label: text("buffActionCheckObtainAtbType"),
              value: [
                decoded.checkObtainMethod ? `${text("buffActionObtainMethod")}: ${(decoded.obtainMethodList || []).join(", ")}` : "",
                decoded.checkObtainType ? `${text("buffActionObtainType")}: ${(decoded.obtainTypeList || []).join(", ")}` : "",
              ].filter(Boolean).join(" · "),
            });
          }
          if (decoded.semanticStatus === "partial-damage-units-opaque-hit-env-bounded") {
            const target = buffTargetSettingsSummary(decoded.targetSettingsEnvelopePartial);
            rows.push({ label: text("buffActionDealDamage"), value: [text("buffDamageValueOpaque"), target].filter(Boolean).join(" · ") });
          }
          if (["exact-modify-dynamic-blackboard-action", "partial-calculation-target-settings-envelope-opaque"].includes(decoded.semanticStatus)) {
            const target = buffTargetSettingsSummary(decoded.calculationTarget);
            const operation = decoded.operationName || formatValue(decoded.operation);
            const calculationType = decoded.calculateTypeName || formatValue(decoded.calculateType);
            rows.push({
              label: text("buffActionCalculateBlackboard"),
              value: [decoded.key, calculationType, operation, target].filter(Boolean).join(" · "),
            });
          }
          if (decoded.semanticStatus === "partial-convert-from-target-settings-envelope-opaque") {
            const operation = decoded.operationTypeName || formatValue(decoded.operationType);
            const translate = decoded.translateOperationName || formatValue(decoded.translateOperation);
            const target = decoded.targetGroupKey || text("buffActionTargetBuff");
            rows.push({
              label: text("buffActionConvertTargetContext"),
              value: [operation, translate, target].filter(Boolean).join(" · "),
            });
          }
          if (decoded.semanticStatus === "partial-source-target-settings-envelopes-opaque") {
            rows.push({
              label: text("buffActionSpellInfliction"),
              value: [decoded.inflictionTypeName || formatValue(decoded.inflictionType), decoded.isExtra ? text("enabled") : ""].filter(Boolean).join(" · "),
            });
          }
          if (decoded.semanticStatus === "exact-not-next-check-control-action") {
            rows.push({ label: text("buffActionStopNextCheck"), value: text("enabled") });
          }
          const isExactIfElse = summary.status === "exact"
            && summary.semanticStatus === "exact-if-else-action";
          const hasNestedIfElseItems = ["conditionAction", "failActions", "succeedActions"]
            .some((key) => (decoded[key]?.actionDataItems || []).length > 0);
          if (isExactIfElse && !hasNestedIfElseItems && rows.length === rowStart) {
            rows.push({
              label: text("buffActionIfElseExact"),
              value: text("buffActionIfElseExactSummary"),
            });
          } else if (rows.length === rowStart && !isExactIfElse) {
            const isIfElse = /IfElseAction/i.test(String(summary.type || decoded.type || ""));
            rows.push({
              label: isIfElse && summary.status === "partial"
                ? text("buffActionIfElsePartial")
                : summary.status === "partial"
                  ? text("buffActionPartialPayload")
                  : text("buffActionUnresolvedPayload"),
              value: summary.type || summary.semanticStatus || text("buffActionOpaquePayload"),
            });
          }
        });
      });
      if (!rows.length) return "";
      const eventName = eventMap.abilityEventName
        ? text(BUFF_ABILITY_EVENT_LABEL_KEYS[eventMap.abilityEventName] || eventMap.abilityEventName)
        : formatValue(eventMap.abilityEvent);
      const chain = actionGroupCount > 1
        ? ` · ${text("buffAbilityEventChain")} ${groupIndex + 1}/${actionGroupCount}`
        : "";
      const rowsWithBranchContext = rows.map((row) => {
        const branch = row && row.branch;
        const branchLabel = branch
          .split(".")
          .map((key) => text(BUFF_BRANCH_LABEL_KEYS[key] || key))
          .join(" / ");
        const coverageLabel = row.coverage === "partial"
          ? text("buffActionPartialMarker")
          : row.coverage === "unresolved"
            ? text("buffActionUnresolvedMarker")
            : "";
        return {
          ...row,
          label: [branchLabel, coverageLabel, row.label].filter(Boolean).join(": "),
        };
      });
      const technical = [...new Set(rowsWithBranchContext.map((row) => row.actionSummary).filter(Boolean))]
        .map(renderBuffActionTechnical)
        .join("");
      return `<div class="gameplay-buff-action-group"><div class="gameplay-subheading">${escapeHtml(text("buffAbilityEvent"))}: ${escapeHtml(eventName)}${escapeHtml(chain)}</div>${renderChipPairs(rowsWithBranchContext)}${technical}</div>`;
    }).filter(Boolean);
    return { html: groups.join(""), coverage };
  }

  function renderBuffCard(id, highlight) {
    const record = buffRecord(id);
    const diffClass = highlight && highlight.has(id) ? " gameplay-diff" : "";
    if (!record || record.evidenceStatus === "unresolved") {
      return `<details class="gameplay-buff-card${diffClass}"><summary><code>${escapeHtml(id)}</code>${renderEvidenceBadge("recoveryUnavailable", "buffDecodeUnavailable", "unresolved")}</summary><p class="muted">${escapeHtml(text("buffDecodeUnavailable"))}</p></details>`;
    }
    const stacking = record.stacking || {};
    const stackingLabel = text(BUFF_STACKING_LABEL_KEYS[stacking.stackingTypeName] || "buffStackUnknown");
    const trigger = record.triggerInterval || {};
    const maxTriggers = record.maxTriggerCnt || {};
    const duration = record.duration || null;
    const addingCooldown = record.addingCooldown || null;
    const abilityEventActionCount = Number(record.abilityEventActionCount || 0);
    const abilityEventRender = renderBuffAbilityEventActions(record);
    const abilityEventActions = abilityEventRender.html;
    const actionCoverage = abilityEventRender.coverage;
    const hasActionGroup = Array.isArray(record.abilityEventActions) && record.abilityEventActions.length > 0;
    const actionBoundaryKey = actionCoverage.total > 0
      && actionCoverage.partial === 0
      && actionCoverage.unresolved === 0
      ? "buffAbilityEventActionExactBoundary"
      : actionCoverage.total > 0
        ? "buffAbilityEventActionPartialBoundary"
        : "buffAbilityEventActionBoundary";
    const actionStatusKey = actionCoverage.total > 0
      && actionCoverage.partial === 0
      && actionCoverage.unresolved === 0
      ? "recoveryExact"
      : actionCoverage.total > 0
        ? "recoveryPartial"
        : "recoveryUnavailable";
    const actionStatusTone = actionCoverage.total > 0
      && actionCoverage.partial === 0
      && actionCoverage.unresolved === 0
      ? "exact"
      : actionCoverage.total > 0
        ? "partial"
        : "unresolved";
    const summaryStatusKey = actionCoverage.total > 0 ? actionStatusKey : "recoveryStructured";
    const summaryStatusTone = actionCoverage.total > 0 ? actionStatusTone : "exact";
    const summaryStatusDetail = actionCoverage.total > 0 ? actionBoundaryKey : "buffEvidenceBoundary";
    const facts = [
      { label: text("buffLifeType"), value: buffLifeLabel(record.lifeType) },
      duration ? { label: text("buffDuration"), value: Number(duration.value) < 0 ? text("buffLifeInfinity") : `${formatValue(duration.value)} ${text("secondsShort")}` } : null,
      { label: text("buffStackingType"), value: stackingLabel },
      { label: text("buffIdentifierType"), value: stacking.identifierTypeName === "StackingKey" ? text("buffIdentifierStackingKey") : text("buffIdentifierId") },
      Number(stacking.maxStackCnt) > 0 ? { label: text("buffMaxStack"), value: stacking.maxStackCnt } : null,
      Number(stacking.priority) !== 0 || stacking.usePriorityKey ? { label: text("buffPriority"), value: stacking.usePriorityKey ? `${stacking.priorityKey} (${formatValue(stacking.priority)})` : stacking.priority } : null,
      Number(trigger.value) >= 0 || trigger.useBlackboardKey ? { label: text("buffTriggerInterval"), value: blackboardValue(trigger) } : null,
      Number(maxTriggers.value) !== 0 || maxTriggers.useBlackboardKey ? { label: text("buffMaxTriggers"), value: Number(maxTriggers.value) < 0 ? text("buffLifeInfinity") : blackboardValue(maxTriggers) } : null,
      addingCooldown && (addingCooldown.useBlackboardKey || Number(addingCooldown.value) !== 0)
        ? { label: text("buffAddingCooldown"), value: blackboardValue(addingCooldown) }
        : null,
      abilityEventActionCount > 0
        ? { label: text("buffAbilityEventActions"), value: abilityEventActionCount }
        : null,
    ].filter(Boolean);
    const attributeModifiers = renderChipPairs(buffAttributeModifierPairs(record));
    const appliedTagIds = (record.applyTags || {}).tagIds || [];
    const appliedTagDetails = (record.applyTags || {}).tagDetails || [];
    const appliedTags = appliedTagDetails.length
      ? renderGameplayTagQuery(record.applyTags)
      : appliedTagIds.length
        ? renderIdChips(appliedTagIds)
      : "";
    const params = renderChipPairs((record.blackboardCandidates || []).map((row) => ({ label: row.key, value: row.value })));
    const refs = renderIdChips(record.refs || []);
    const hint = buffIdentifierHint(id);
    const flags = Object.entries(record.flags || {})
      .filter(([, value]) => value)
      .map(([key]) => ({ label: text(BUFF_FLAG_LABEL_KEYS[key] || key), value: text("enabled") }));
    return `<details class="gameplay-buff-card${diffClass}">
      <summary><code>${escapeHtml(id)}</code>${renderEvidenceBadge(summaryStatusKey, summaryStatusDetail, summaryStatusTone)}${hint ? `<span>${escapeHtml(text("buffIdentifierHint"))}: ${escapeHtml(hint)}</span>` : ""}</summary>
      ${renderChipPairs(facts)}
      ${abilityEventActions}
      ${abilityEventActionCount > 0 || hasActionGroup ? `<div class="gameplay-evidence-status-row">${renderEvidenceBadge(actionStatusKey, actionBoundaryKey, actionStatusTone)}</div>` : ""}
      ${attributeModifiers ? `${renderBuffSubheading("buffAttributeModifiers", renderEvidenceBadge("recoveryExact", "buffAttributeModifierBoundary"))}${attributeModifiers}` : ""}
      ${appliedTags ? `${renderBuffSubheading("buffAppliedTags", renderEvidenceBadge("recoveryExact", "buffAppliedTagBoundary"))}${appliedTags}` : ""}
      ${params ? renderBuffSubheading("buffParameterCandidates") + params : ""}
      ${flags.length ? renderBuffSubheading("buffFlags") + renderChipPairs(flags) : ""}
      ${refs ? renderBuffSubheading("buffReferences") + refs : ""}
      ${STATE.showDebug && record.source?.path ? `<p class="gameplay-buff-source muted">${escapeHtml(text("source"))}: ${escapeHtml(record.source.path)}</p>` : ""}
    </details>`;
  }

  function renderBuffCards(ids, opts = {}) {
    const rows = [...new Set((ids || []).filter(Boolean))].map((id) => renderBuffCard(id, opts.highlight));
    if (!rows.length) return "";
    return `<details class="gameplay-guidance gameplay-buff-guidance"><summary>${escapeHtml(text("buffEvidenceHelp"))}</summary><p>${escapeHtml(text("buffEvidenceBoundary"))}</p></details><div class="gameplay-buff-grid">${rows.join("")}</div>`;
  }

  function enemyModifierPairs(source) {
    return (source.attrModifiers || []).map((modifier) => {
      if (!modifier) return null;
      const modifierLabel = modifier.modifierTypeName
        ? text(MODIFIER_LABEL_KEYS[modifier.modifierTypeName] || "modifierUnknown")
        : `${text("modifierType")} ${formatValue(modifier.modifierType)}`;
      const targetLabel = modifier.modifyAttributeTypeName
        ? text(MODIFIER_TARGET_LABEL_KEYS[modifier.modifyAttributeTypeName] || "modifierTargetUnknown")
        : "";
      const label = [statAttrLabel(modifier), targetLabel, modifierLabel].filter(Boolean).join(" / ");
      return { label, value: modifier.value };
    }).filter(Boolean);
  }

  function renderEnemyModifierRows(entry, diffLabels) {
    const rows = renderChipPairs(enemyModifierPairs(entry), { diffLabels });
    return rows ? `${rows}<p class="gameplay-evidence-note muted">${escapeHtml(text("enemyModifierBoundary"))}</p>` : "";
  }

  function variantDetailPairs(variant) {
    return [
      { label: text("attrTemplateId"), value: variant.attrTemplateId },
      { label: text("modelId"), value: variant.modelId },
      { label: text("aiTemplateId"), value: variant.aiTemplateId },
      { label: text("displayType"), value: variant.displayTypeLabel || variant.displayType },
      { label: text("dangerous"), value: variant.isDangerous },
      { label: text("showBigEffect"), value: variant.showBigEffect },
      { label: text("showBigHeadbar"), value: variant.showBigHeadbar },
      { label: text("autoLockCancelType"), value: variant.autoLockCancelType },
      { label: text("autoLockCancelTime"), value: variant.autoLockCancelTime },
      { label: text("serverDeathCheck"), value: variant.serverDeathCheck },
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
    const buffs = renderBuffCards(variant.bornBuffs || [], { highlight: buffDiff });
    const modifiers = renderEnemyModifierRows(variant, diffLabels);
    return `<div class="gameplay-skill-meta">${escapeHtml([variant.id, variant.displayTypeLabel].filter(Boolean).join(" / "))}</div>
      ${details}
      ${buffs ? `<div class="gameplay-subheading">${escapeHtml(text("bornBuffs"))}</div>${buffs}` : ""}
      ${modifiers ? `<div class="gameplay-subheading">${escapeHtml(text("attrModifiers"))}</div>${modifiers}` : ""}`;
  }

  function stableVariantValue(value) {
    if (Array.isArray(value)) return JSON.stringify(value);
    if (value && typeof value === "object") return JSON.stringify(value, Object.keys(value).sort());
    return value === undefined || value === null ? "" : String(value);
  }

  function variantModifierSummary(variant) {
    return enemyModifierPairs(variant)
      .map((pair) => `${pair.label}: ${formatValue(pair.value)}`)
      .join("; ");
  }

  function variantTableColumns(variants) {
    const candidates = variantDetailPairs({}).map((pair, index) => ({
      key: `detail:${index}`,
      label: pair.label,
      value: (variant) => variantDetailPairs(variant)[index]?.value,
    }));
    candidates.push(
      { key: "buffs", label: text("bornBuffs"), value: (variant) => (variant.bornBuffs || []).join(", ") },
      { key: "modifiers", label: text("attrModifiers"), value: variantModifierSummary },
    );
    return candidates.filter((column) => {
      const values = new Set(variants.map((variant) => stableVariantValue(column.value(variant))));
      return values.size > 1;
    });
  }

  function renderVariantTableCell(value) {
    const display = formatValue(value);
    return display ? `<code>${escapeHtml(display)}</code>` : `<span class="muted">-</span>`;
  }

  function enemyAttributeTemplate(entry, variant) {
    const id = String(variant?.attrTemplateId || entry?.attrTemplateId || "");
    const exact = entry?.attributeTemplates?.[id];
    if (exact) return exact;
    return {
      stats: entry?.stats || {},
      independentAttributes: entry?.independentAttributes || [],
      damageScalars: entry?.damageScalars || [],
      resilience: entry?.resilience || [],
    };
  }

  function renderEnemyVariantDependent(entry, variant) {
    const attributes = enemyAttributeTemplate(entry, variant);
    const combatValues = {
      damageScalars: attributes.damageScalars || [],
      resilience: attributes.resilience || [],
      independentAttributes: attributes.independentAttributes || [],
      attrModifiers: variant?.attrModifiers || entry.attrModifiers || [],
      bornBuffs: variant?.bornBuffs || entry.bornBuffs || [],
    };
    return [
      section(text("enemyStats"), renderStats(attributes.stats || entry.stats)),
      section(text("combatValues"), renderEnemyCombatValues(combatValues)),
    ].join("");
  }

  function renderEnemyVariants(entry) {
    const variants = (entry.variants || []).filter(Boolean);
    if (!variants.length) return "";
    const diffLabels = variantDiffLabels(variants);
    const buffDiff = variantBuffDiff(variants);
    const columns = variantTableColumns(variants);
    const head = columns.map((column) => `<th scope="col">${escapeHtml(column.label)}</th>`).join("");
    const rows = variants.map((variant, index) => {
      const cells = columns.map((column) => `<td>${renderVariantTableCell(column.value(variant))}</td>`).join("");
      return `<tr class="gameplay-variant-row${index === 0 ? " is-selected" : ""}" data-variant-index="${index}" role="option" tabindex="0" aria-selected="${index === 0 ? "true" : "false"}">
        <th scope="row"><code>${escapeHtml(variant.id || "")}</code></th>${cells}
      </tr>`;
    }).join("");
    return `<div class="gameplay-variant-switch" data-variant-card>
      <div class="gameplay-variant-table-wrap"><table class="gameplay-variant-table" role="listbox" aria-label="${escapeHtml(text("enemyVariants"))}">
        <thead><tr><th scope="col">${escapeHtml(text("selectedVariant"))}</th>${head}</tr></thead>
        <tbody>${rows}</tbody>
      </table></div>
      ${columns.length ? "" : `<p class="gameplay-variant-no-diff muted">${escapeHtml(text("noVariantDifferences"))}</p>`}
      <div class="gameplay-variant-pane" data-selected-variant-pane>${variantPaneBody(variants[0], diffLabels, buffDiff)}</div>
    </div>`;
  }

  function bindVariantSwitches(root) {
    root.querySelectorAll("[data-gameplay-character-gender]").forEach((button) => {
      button.addEventListener("click", () => setCharacterGender(button.dataset.gameplayCharacterGender));
    });
    root.querySelectorAll(".gameplay-variant-switch").forEach((card) => {
      const rows = [...card.querySelectorAll(".gameplay-variant-row")];
      const pane = card.querySelector("[data-selected-variant-pane]");
      const dependent = root.querySelector("[data-enemy-variant-dependent]");
      const entry = STATE.selected;
      const variants = (entry?.variants || []).filter(Boolean);
      const diffLabels = variantDiffLabels(variants);
      const buffDiff = variantBuffDiff(variants);
      const select = (row) => {
        const index = Number(row.dataset.variantIndex || 0);
        const variant = variants[index];
        if (!variant) return;
        rows.forEach((candidate) => {
          const selected = candidate === row;
          candidate.classList.toggle("is-selected", selected);
          candidate.setAttribute("aria-selected", selected ? "true" : "false");
        });
        if (pane) pane.innerHTML = variantPaneBody(variant, diffLabels, buffDiff);
        if (dependent) {
          dependent.innerHTML = renderEnemyVariantDependent(entry, variant);
          bindLevelSliders(dependent);
        }
      };
      rows.forEach((row) => {
        row.addEventListener("click", () => select(row));
        row.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          select(row);
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
    const bornBuffs = renderBuffCards(entry.bornBuffs || []);
    if (bornBuffs) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("bornBuffs"))}</div>${bornBuffs}`);
    return blocks.join("");
  }

  function renderEnemyDetail(entry) {
    const selectedVariant = (entry.variants || []).find(Boolean) || null;
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
        `<div data-enemy-variant-dependent>${renderEnemyVariantDependent(entry, selectedVariant)}</div>`,
        section(text("enemyAbilities"), renderEnemyAbilities(entry)),
        section(text("enemyDetails"), renderEnemyDetails(entry)),
      ].join(""),
    };
  }

  function itemUseActionHasEffect(action) {
    if (!action || typeof action !== "object") return false;
    const identifiers = [action.buffId, action.skillId, action.skillPath]
      .some((value) => String(value || "").trim());
    if (identifiers) return true;
    return [action.buffBlackboard, action.skillBlackboard].some((rows) =>
      Array.isArray(rows) && rows.some((row) => row && (
        String(row.key || "").trim()
        || row.value !== undefined && row.value !== null && row.value !== ""
      ))
    );
  }

  function itemUseActions(entry) {
    return (((entry?.useData || {}).actions) || []).filter(itemUseActionHasEffect);
  }

  function renderItemUse(entry) {
    const use = entry.useData || {};
    const actions = itemUseActions(entry);
    const description = String(use.description || "").trim();
    if (!description && !actions.length) return "";
    // Numeric use metadata is only useful when a real buff/skill action is
    // present. Detector/revival items can have a textual use description but
    // no structured action; showing their default enum values as an effect is
    // misleading, so keep those entries description-only.
    const details = actions.length ? renderChipPairs([
      { label: text("duration"), value: Number(use.duration) > 0 ? use.duration : "" },
      { label: text("effectType"), value: Number(use.effectType) > 0 ? use.effectType : "" },
      { label: text("uiType"), value: Number(use.uiType) > 0 ? use.uiType : "" },
      { label: text("targetNumType"), value: Number(use.targetNumType) > 0 ? use.targetNumType : "" },
      { label: text("persistentBuff"), value: use.isPersistentBuff ? "true" : "" },
      { label: text("stackKey"), value: use.stackingKey },
    ]) : "";
    return [renderDescription(use.description), details].filter(Boolean).join("");
  }

  function renderItemActions(entry) {
    const rows = itemUseActions(entry).map((action, index) => {
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
      const quantityNote = reward.quantityDataUnavailable
        ? `<div class="gameplay-integration-note is-warning" role="status">${escapeHtml(text("rewardQuantityUnavailable"))}</div>`
        : "";
      return `<article class="gameplay-skill-card">
        <header>
          <div class="gameplay-skill-title">${escapeHtml(reward.id || text("rewardId"))}</div>
          <div class="gameplay-skill-meta">${escapeHtml(text("rewardId"))}</div>
        </header>
        ${quantityNote}
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

  const INTEGRATION_ASSET_SOURCE_ROOTS = Object.freeze({
    StreamingAssets: "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type",
    "StreamingAssets-maps": "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps",
    "StreamingAssets-structured": "export_full/structured/StreamingAssets",
    Persistent: "export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type",
    "Persistent-maps": "export_full/recovered/AnimeStudio-cli/Persistent/maps",
    "Persistent-structured": "export_full/structured/Persistent",
    "StreamingAssets-materials": "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type",
    "Persistent-materials": "export_full/recovered/AnimeStudio-cli/Persistent/json_by_type",
  });

  function integrationPath(kind, language) {
    const code = encodeURIComponent(String(language || "CN").toUpperCase());
    if (kind === "combat") return `data/lang/${code}/gameplay/combat_relationships.json?v=${GAMEPLAY_INTEGRATION_VERSION}`;
    if (kind === "projectiles") return `data/gameplay/projectiles.json?v=${GAMEPLAY_INTEGRATION_VERSION}`;
    if (kind === "projectileAudio") return `data/lang/${code}/gameplay/projectile_audio.json?v=${GAMEPLAY_INTEGRATION_VERSION}`;
    if (kind === "soundEffects") return `data/lang/${code}/gameplay/sound_effects.json?v=${GAMEPLAY_INTEGRATION_VERSION}`;
    return `data/assets/gameplay_refs.json?v=${GAMEPLAY_INTEGRATION_VERSION}`;
  }

  async function fetchIntegrationJson(path, validator) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`.trim());
    const payload = await response.json();
    if (validator && !validator(payload)) throw new Error("Unsupported integration payload");
    return payload;
  }

  function buildIntegrationIndexes() {
    const combat = STATE.integration.combat;
    const projectile = STATE.integration.projectiles;
    const projectileAudio = STATE.integration.projectileAudio;
    const indexes = { combat: null, projectileAudio: new Map() };
    if (combat && Array.isArray(combat.nodes) && Array.isArray(combat.edges)) {
      const nodes = new Map(combat.nodes.map((node) => [String(node.id || ""), node]));
      const outgoing = new Map();
      combat.edges.forEach((edge, index) => {
        if (!edge) return;
        const source = String(edge.source || "");
        if (!outgoing.has(source)) outgoing.set(source, []);
        outgoing.get(source).push(index);
      });
      indexes.combat = { nodes, outgoing };
    }
    if (projectile && Array.isArray(projectile.entries)) {
      indexes.projectiles = projectile.entries;
    }
    for (const link of projectileAudio?.links || []) {
      const eventHash = projectileEventHash(link?.eventHash);
      if (!link?.projectileId || !link?.field || eventHash === null) continue;
      indexes.projectileAudio.set(
        projectileAudioIndexKey(link.projectileId, link.field, eventHash),
        link,
      );
    }
    return indexes;
  }

  function integrationNodeCandidates(entry) {
    if (!entry || !entry.id) return [];
    const id = String(entry.id);
    const candidates = [`${entry.kind}:${id}`];
    if (entry.kind === "item") candidates.push(`equipment:${id}`);
    if (entry.kind === "equipment") candidates.push(`item:${id}`);
    if (entry.kind === "enemy") candidates.push(`enemy:${id}`);
    return [...new Set(candidates)];
  }

  function readableIntegrationId(value) {
    return String(value || "")
      .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
      .replace(/[_:]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function integrationConfidence(value) {
    if (value === "direct") return `<span class="gameplay-integration-confidence is-direct">${escapeHtml(text("directEvidence"))}</span>`;
    if (value === "inferred") return `<span class="gameplay-integration-confidence is-inferred">${escapeHtml(text("inferredEvidence"))}</span>`;
    return value ? `<span class="gameplay-integration-confidence">${escapeHtml(readableIntegrationId(value))}</span>` : "";
  }

  function gameplayAssetPageHref(rel) {
    const url = new URL(window.location.href);
    url.searchParams.set("asset", String(rel || ""));
    url.hash = "#assets";
    return url.toString();
  }

  function gameplayAssetHref(rel) {
    const helper = window.WebUI?.exportFullHref;
    if (typeof helper === "function") return helper(rel, INTEGRATION_ASSET_SOURCE_ROOTS, "export_full");
    return `/export_full/${String(rel || "").split("/").map((part) => encodeURIComponent(part)).join("/")}`;
  }

  function gameplayAssetRefsForItem(item) {
    const itemId = String(item?.id || "").trim();
    if (!itemId) return null;
    const tokenRefs = integrationAssetRefsForToken(itemId);
    if (tokenRefs?.images?.some((asset) => asset?.rel)) return tokenRefs;
    const refsByKey = STATE.integration.assets?.entries || {};
    const entry = findGameplayEntry(itemId);
    const keys = [
      entry ? `${entry.kind}:${entry.id}` : "",
      `item:${itemId}`,
      `equipment:${itemId}`,
      `weapon:${itemId}`,
    ].filter(Boolean);
    for (const key of [...new Set(keys)]) {
      const refs = refsByKey[key];
      if (refs?.images?.some((asset) => asset?.rel)) return refs;
    }
    return null;
  }

  function renderGameplayItemIcon(item, label = "", opts = {}) {
    const refs = gameplayAssetRefsForItem(item);
    const asset = refs?.images?.find((candidate) => candidate?.rel);
    if (!asset) return "";
    if (opts.static) {
      const src = gameplayAssetHref(asset.rel);
      const title = label || item?.id || asset.rel;
      return `<span class="gameplay-item-chip-icon gameplay-item-chip-icon-static" title="${escapeHtml(title)}"><img src="${escapeHtml(src)}" alt="${escapeHtml(title)}" loading="lazy" onerror="this.closest('.gameplay-item-chip-icon')?.classList.add('is-missing')"></span>`;
    }
    return renderGameplayImageButton(asset, {
      className: "gameplay-item-chip-icon",
      alt: label || item?.id || "",
      imageId: `item:${item?.id || asset.rel}`,
      imageName: label || item?.id || asset.rel,
    });
  }

  function renderGameplayImageButton(asset, opts = {}) {
    const rel = String(asset?.rel || "");
    if (!rel) return "";
    const src = gameplayAssetHref(rel);
    const token = String(opts.token || "");
    const imageId = String(opts.imageId || token || rel);
    const imageName = String(opts.imageName || opts.alt || token || rel);
    const className = [
      opts.className || "",
      "gameplay-image-preview",
      "inline-image-tag",
      "has-preview",
    ].filter(Boolean).join(" ");
    const title = opts.title || `${text("previewImage")}: ${imageName}`;
    const image = `<img src="${escapeHtml(src)}" alt="${escapeHtml(opts.alt || imageName)}" loading="lazy" onerror="this.closest('.gameplay-image-preview')?.classList.add('is-missing')">`;
    const content = opts.content || image;
    return `<button type="button" class="${escapeHtml(className)}" title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}" data-inline-image-id="${escapeHtml(imageId)}" data-inline-image-name="${escapeHtml(imageName)}" data-inline-image-src="${escapeHtml(src)}"${token ? ` data-gameplay-token="${escapeHtml(token)}"` : ""}>${content}</button>`;
  }

  function sourceCoordinate(source) {
    return [source?.table, source?.id].filter(Boolean).join(" / ");
  }

  function integrationAssetRefsForToken(token) {
    const raw = String(token || "").trim();
    if (!raw) return null;
    const tokens = STATE.integration.assets?.tokens || {};
    const variants = [raw, raw.replace(/^item_pic_/i, "pic_")];
    if (/^item_topic_/i.test(raw)) {
      variants.push(raw.replace(/^item_topic_/i, "business_card_topic_"));
    }
    for (const variant of [...new Set(variants)]) {
      if (tokens[variant]) return tokens[variant];
    }
    return null;
  }

  function characterSkillIconType(group) {
    const numericType = Number(group?.type);
    if (numericType === 0) return "normal-attack";
    if (numericType === 1) return "normal-skill";
    if (numericType === 2) return "ultimate";
    if (numericType === 3) return "combo";
    const id = String(group?.id || "");
    const suffix = id.match(/_(NormalAttack|NormalSkill|UltimateSkill|ComboSkill)$/i)?.[1]?.toLowerCase();
    if (suffix === "normalattack") return "normal-attack";
    if (suffix === "normalskill") return "normal-skill";
    if (suffix === "ultimateskill") return "ultimate";
    if (suffix === "comboskill") return "combo";
    const label = `${group?.typeLabel || ""} ${group?.name || ""}`.toLowerCase();
    if (label.includes("normal attack") || label.includes("普通攻击")) return "normal-attack";
    if (label.includes("ultimate") || label.includes("终结")) return "ultimate";
    if (label.includes("combo") || label.includes("连携")) return "combo";
    if (label.includes("skill") || label.includes("技能")) return "normal-skill";
    return "";
  }

  function renderGameplayTokenIcon(token, alt = "", opts = {}) {
    const refs = integrationAssetRefsForToken(token);
    const asset = refs?.images?.find((item) => item?.rel);
    if (!asset) return "";
    const skillType = String(opts.skillType || "").trim();
    return renderGameplayImageButton(asset, {
      className: [
        "gameplay-token-icon",
        skillType ? "gameplay-attack-skill-icon" : "",
        skillType ? `gameplay-attack-skill-${skillType}` : "",
        opts.className || "",
      ].filter(Boolean).join(" "),
      alt,
      token,
      imageName: readableIntegrationId(token) || alt || token,
    });
  }

  function renderGameplayTokenImages(tokens, alt = "", className = "") {
    const images = [];
    const seen = new Set();
    for (const token of tokens || []) {
      const refs = integrationAssetRefsForToken(token);
      for (const asset of refs?.images || []) {
        const rel = String(asset?.rel || "");
        if (!rel || seen.has(rel)) continue;
        seen.add(rel);
        images.push({ asset, token });
      }
    }
    if (!images.length) return "";
    const cards = images.slice(0, 4).map(({ asset, token }) => {
      return renderGameplayImageButton(asset, {
        className: "gameplay-token-asset",
        alt,
        token,
        imageName: readableIntegrationId(token) || alt || token,
      });
    }).join("");
    return `<div class="gameplay-token-image-row${className ? ` ${className}` : ""}">${cards}${images.length > 4 ? `<span class="gameplay-character-asset-more">+${formatNumber(images.length - 4)}</span>` : ""}</div>`;
  }

  function renderGameplayAssetLink(asset, label = "") {
    const rel = String(asset?.rel || "");
    if (!rel) return "";
    const title = label || rel;
    return `<a class="gameplay-asset-path" href="${escapeHtml(gameplayAssetPageHref(rel))}" title="${escapeHtml(text("openAsset"))}"><span>${escapeHtml(title)}</span><code>${escapeHtml(rel)}</code></a>`;
  }

  function renderGameplayAssetGallery(entry) {
    const key = `${entry?.kind || ""}:${entry?.id || ""}`;
    const refs = STATE.integration.assets?.entries?.[key];
    if (!refs) return "";
    const kind = String(entry?.kind || "");
    const iconLike = ["weapon", "equipment", "item"].includes(kind);
    const allImages = Array.isArray(refs.images) ? refs.images.filter((item) => item?.rel) : [];
    const images = kind === "weapon" ? allImages : (iconLike || kind === "enemy") ? allImages.slice(0, 1) : allImages;
    const models = Array.isArray(refs.models) ? refs.models.filter((item) => item?.rel) : [];
    const imageCards = images.map((asset, index) => {
      const caption = asset.category || (index === 0 ? text("assetImages") : "");
      return renderGameplayImageButton(asset, {
        className: `gameplay-asset-thumb${kind === "weapon" ? " gameplay-weapon-asset-thumb" : iconLike ? " gameplay-item-weapon-thumb" : ""}`,
        alt: entry.title || entry.id || "",
        imageId: `${entry.id || "entry"}:${asset.rel}`,
        imageName: [entry.title || entry.id || "", caption].filter(Boolean).join(" / "),
        content: `<figure><img src="${escapeHtml(gameplayAssetHref(asset.rel))}" alt="${escapeHtml(entry.title || entry.id || "")}" loading="lazy" onerror="this.closest('.gameplay-image-preview')?.classList.add('is-missing')"><figcaption>${escapeHtml(caption)}</figcaption></figure>`,
      });
    }).join("");
    const modelLinks = models.map((asset) => renderGameplayAssetLink(asset, asset.category || text("assetModels"))).join("");
    if (!imageCards && !modelLinks) return "";
    return `<div class="gameplay-asset-gallery"><div class="gameplay-subheading">${escapeHtml(text("assetImages"))}</div><div class="gameplay-asset-images">${imageCards || `<span class="gameplay-asset-no-preview">${escapeHtml(text("noAssetPreview"))}</span>`}</div>${modelLinks ? `<div class="gameplay-asset-models"><div class="gameplay-subheading">${escapeHtml(text("assetModels"))}</div>${modelLinks}</div>` : ""}</div>`;
  }

  function renderIntegrationNode(nodeId, node) {
    const target = findGameplayEntry(nodeId);
    const label = node?.name || node?.label || node?.key || nodeId;
    if (target) {
      const key = `${target.kind}:${target.id}`;
      return `<button type="button" class="gameplay-related-link" data-gameplay-related-key="${escapeHtml(key)}" title="${escapeHtml(target.id)}">${escapeHtml(label)}</button>`;
    }
    if (node?.kind === "asset" && node?.path) {
      return renderGameplayAssetLink({ rel: node.path }, label);
    }
    return `<code class="gameplay-integration-node">${escapeHtml(label)}</code>`;
  }

  function combatRootForEntry(entry) {
    if (!entry || !["character", "enemy"].includes(entry.kind)) return "";
    const id = `${entry.kind}:${entry.id}`;
    return STATE.integration.indexes?.combat?.nodes.has(id) ? id : "";
  }

  function combatEdgesFromRoot(rootId) {
    const index = STATE.integration.indexes?.combat;
    const payload = STATE.integration.combat;
    if (!index || !payload) return [];
    const indexedEdges = payload.rootEdges?.[rootId];
    if (Array.isArray(indexedEdges)) {
      return indexedEdges
        .slice(0, 160)
        .map((edgeIndex) => payload.edges[edgeIndex])
        .filter(Boolean)
        .sort((left, right) => {
          const confidence = (left.confidence === "direct" ? 0 : 1) - (right.confidence === "direct" ? 0 : 1);
          if (confidence) return confidence;
          return String(left.type || "").localeCompare(String(right.type || ""));
        });
    }
    const queue = [[rootId, 0]];
    const visitedNodes = new Set([rootId]);
    const edgeIds = new Set();
    const out = [];
    while (queue.length && out.length < 120) {
      const [nodeId, depth] = queue.shift();
      for (const edgeIndex of index.outgoing.get(nodeId) || []) {
        if (edgeIds.has(edgeIndex)) continue;
        const edge = payload.edges[edgeIndex];
        if (!edge) continue;
        edgeIds.add(edgeIndex);
        out.push(edge);
        const target = String(edge.target || "");
        if (depth < 2 && target && !visitedNodes.has(target)) {
          visitedNodes.add(target);
          queue.push([target, depth + 1]);
        }
      }
    }
    return out;
  }

  function combatEdgesForNode(nodeId) {
    const index = STATE.integration.indexes?.combat;
    const payload = STATE.integration.combat;
    if (!index || !payload) return [];
    return (index.outgoing.get(String(nodeId || "")) || [])
      .map((edgeIndex) => payload.edges[edgeIndex])
      .filter(Boolean);
  }

  function combatRelationLabel(value) {
    const key = `combatRelation_${String(value || "")}`;
    const translated = text(key);
    return translated === key ? readableIntegrationId(value) : translated;
  }

  function compactEvidenceValue(value, maxLength = 360) {
    if (value === undefined || value === null || value === "") return "";
    let rendered;
    if (typeof value === "string") rendered = value;
    else {
      try { rendered = JSON.stringify(value); }
      catch (_) { rendered = String(value); }
    }
    return rendered.length > maxLength ? `${rendered.slice(0, maxLength - 1)}…` : rendered;
  }

  function integrationNodeSemantics(node) {
    if (!node) return "";
    const raw = node.raw || {};
    const source = node.source || {};
    const sourceValue = typeof source === "string"
      ? source
      : [source.table, source.id, source.file, source.path, source.layout].filter(Boolean).join(" / ");
    const authoredFields = ["attrTemplateId", "modelId", "aiTemplateId", "displayType", "isDangerous"]
      .filter((key) => raw[key] !== undefined && raw[key] !== null && raw[key] !== "")
      .map((key) => `${readableIntegrationId(key)}=${formatValue(raw[key])}`);
    if (Array.isArray(raw.bornBuffs) && raw.bornBuffs.length) authoredFields.push(`${text("bornBuffs")}: ${raw.bornBuffs.join(", ")}`);
    if (Array.isArray(raw.attrModifiers) && raw.attrModifiers.length) authoredFields.push(`${text("attrModifiers")}: ${formatNumber(raw.attrModifiers.length)}`);
    const scalarFields = [...(raw.damageScalars || []), ...(raw.resilience || [])]
      .filter((item) => item && item.value !== undefined && item.value !== null)
      .slice(0, 8)
      .map((item) => `${item.label || readableIntegrationId(item.key)}=${formatValue(item.value)}`);
    const authored = [
      raw.description,
      raw.dataPath,
      raw.domain,
      Array.isArray(raw.fields) ? raw.fields.join(", ") : "",
      raw.statPointCount !== undefined ? `${text("statPointCount")}: ${formatValue(raw.statPointCount)}` : "",
      raw.interpolated === false ? text("noInterpolation") : "",
      ...authoredFields,
      ...scalarFields,
      node.classification?.basis,
    ].filter(Boolean).join(" · ");
    const rows = [
      node.semanticStatus ? `<span><b>${escapeHtml(text("semanticStatus"))}</b>${escapeHtml(node.semanticStatus)}</span>` : "",
      sourceValue ? `<span><b>${escapeHtml(text("source"))}</b><code>${escapeHtml(sourceValue)}</code></span>` : "",
      authored ? `<span><b>${escapeHtml(text("authoredSemantics"))}</b>${escapeHtml(authored)}</span>` : "",
    ].filter(Boolean).join("");
    return rows ? `<div class="gameplay-integration-semantics">${rows}</div>` : "";
  }

  function renderCombatEdge(edge) {
    const index = STATE.integration.indexes?.combat;
    const source = index?.nodes.get(String(edge.source || ""));
    const targetId = String(edge.target || "");
    const target = index?.nodes.get(targetId);
    const evidence = edge.evidence || {};
    const evidenceText = [evidence.source, evidence.path].filter(Boolean).join(" / ");
    const rawEvidence = compactEvidenceValue(evidence.raw);
    return `<article class="gameplay-integration-relation gameplay-combat-relation">
      <div class="gameplay-integration-relation-main">${renderIntegrationNode(String(edge.source || ""), source)}<span class="gameplay-integration-arrow">→</span><span class="gameplay-integration-relation-kind">${escapeHtml(combatRelationLabel(edge.type))}</span><span class="gameplay-integration-arrow">→</span>${renderIntegrationNode(targetId, target)}${integrationConfidence(edge.confidence)}</div>
      ${evidenceText || rawEvidence || edge.note ? `<div class="gameplay-integration-evidence">${evidenceText ? `<span><b>${escapeHtml(text("evidenceCoordinate"))}</b><code>${escapeHtml(evidenceText)}</code></span>` : ""}${rawEvidence ? `<span><b>${escapeHtml(text("evidenceValue"))}</b><code>${escapeHtml(rawEvidence)}</code></span>` : ""}${edge.note ? `<span><b>${escapeHtml(text("evidenceMeaning"))}</b>${escapeHtml(edge.note)}</span>` : ""}</div>` : ""}
      ${integrationNodeSemantics(target)}
    </article>`;
  }

  function renderCombatIntegration(entry) {
    const rootId = combatRootForEntry(entry);
    if (!rootId) return "";
    const edges = combatEdgesFromRoot(rootId);
    if (!edges.length) return section(text("combatLinks"), `<p class="gameplay-integration-empty">${escapeHtml(text("noCombatLinks"))}</p>`, { open: false });
    const direct = edges.filter((edge) => edge.confidence === "direct").length;
    const body = `<div class="gameplay-integration-summary"><span>${formatNumber(edges.length)} ${escapeHtml(text("combatLinks"))}</span><span>${formatNumber(direct)} ${escapeHtml(text("directEvidence"))}</span><span>${formatNumber(edges.length - direct)} ${escapeHtml(text("inferredEvidence"))}</span></div>${edges.map(renderCombatEdge).join("")}`;
    return section(text("combatLinks"), body, { open: true });
  }

  function projectileTokenMatches(value, token) {
    const haystack = `_${String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "_")}_`;
    const needle = String(token || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
    return !!needle && haystack.includes(`_${needle}_`);
  }

  function projectileTokenKey(value) {
    return String(value || "").toLowerCase().replace(/^(?:data_)?projectile_/, "");
  }

  function projectileCanonicalKey(value) {
    return projectileTokenKey(value).replace(/[^a-z0-9]+/g, "");
  }

  function projectileTokenEquals(value, token) {
    const left = projectileTokenKey(value);
    const right = projectileTokenKey(token);
    return !!right && left === right;
  }

  function projectileTokensForEntry(entry) {
    const tokens = [entry?.id];
    for (const skill of entry?.skills || []) tokens.push(skill?.id);
    for (const group of entry?.skillGroups || []) {
      tokens.push(...(group?.actionSkillIds || []));
      for (const skill of group?.skills || []) tokens.push(skill?.id);
    }
    for (const action of entry?.useData?.actions || []) tokens.push(action?.skillId);
    return [...new Set(tokens.map((value) => String(value || "").trim()).filter(Boolean))];
  }

  function projectilesForTokens(tokens, preferredToken = "", valueSelector = projectileValues) {
    const rows = STATE.integration.indexes?.projectiles || [];
    if (!tokens.length) return [];
    return rows.map((projectile) => {
      const values = valueSelector(projectile);
      const matched = tokens.filter((token) => values.some((value) => projectileTokenMatches(value, token)));
      if (!matched.length) return null;
      return { projectile, score: matched.some((token) => token === preferredToken) ? 0 : 1, matched };
    }).filter(Boolean).sort((left, right) => left.score - right.score || String(left.projectile.id).localeCompare(String(right.projectile.id)));
  }

  function projectilesForEntry(entry) {
    return projectilesForTokens(projectileTokensForEntry(entry), entry?.id || "");
  }

  function projectileTokenVariants(token) {
    const variants = [String(token || "").trim()];
    let current = variants[0];
    while (/_\d+$/.test(current)) {
      current = current.replace(/_\d+$/, "");
      variants.push(current);
    }
    return variants.filter(Boolean);
  }

  function projectileValues(projectile) {
    return [
      projectile?.id,
      projectile?.source?.assetName,
      ...projectileBehaviorSkillIds(projectile),
    ].map((value) => String(value || "").toLowerCase());
  }

  function projectileIdentityValues(projectile) {
    return [projectile?.id, projectile?.source?.assetName]
      .map((value) => String(value || "").toLowerCase())
      .filter(Boolean);
  }

  function projectileMatchesSkillFamily(projectile, baseId, family) {
    const values = projectileIdentityValues(projectile);
    if (!baseId || !values.some((value) => projectileTokenMatches(value, baseId))) return false;
    const haystack = values.join(" ");
    const isUltimate = /(?:^|_)ult(?:_|$)/.test(haystack) || haystack.includes("ultimate_skill") || haystack.includes("ultimate");
    const isNormalSkill = haystack.includes("normal_skill");
    const isCombo = haystack.includes("combo_skill");
    if (family === "NormalAttack") return !isUltimate && !isNormalSkill && !isCombo && haystack.includes("attack");
    if (family === "NormalSkill") return isNormalSkill;
    if (family === "UltimateSkill") return isUltimate;
    if (family === "ComboSkill") return isCombo;
    return false;
  }

  function projectilesForSkill(skill, siblingSkillIds = []) {
    const skillId = String(skill?.id || "");
    const rows = STATE.integration.indexes?.projectiles || [];
    const siblingIds = new Set(siblingSkillIds.map((id) => projectileTokenKey(id)).filter(Boolean));
    const skillCanonical = projectileCanonicalKey(skillId);
    const siblingCanonical = siblingSkillIds.map((id) => ({
      id: String(id || ""),
      key: projectileCanonicalKey(id),
    })).filter((item) => item.key && item.id !== skillId);
    const exact = rows
      .filter((projectile) => projectileIdentityValues(projectile).some((value) => projectileTokenEquals(value, skillId)))
      .map((projectile) => ({ projectile, score: 0, matched: [skillId], matchMethod: "exact-action-id" }));
    const fallbackTokens = projectileTokenVariants(skillId).slice(1);
    // Some authored projectile assets add a descriptive suffix (for example
    // `attack2_robot`) while the skill action remains `attack2`. The same
    // fallback also collects numeric variants such as `attack3_2` when there
    // is no sibling skill with that exact identifier.
    const tokens = fallbackTokens.length ? fallbackTokens : [skillId];
    const exactIds = new Set(exact.map(({ projectile }) => String(projectile?.id || "")));
    const fallback = projectilesForTokens([...new Set(tokens)], skillId, projectileIdentityValues)
      // If a sibling action has the exact projectile identifier, do not let a
      // shorter parent action claim it through the boundary-aware fallback.
      .filter(({ projectile }) => !exactIds.has(String(projectile?.id || "")))
      .filter(({ projectile }) => !projectileIdentityValues(projectile).some((value) => siblingIds.has(projectileTokenKey(value))))
      .map((row) => ({ ...row, matchMethod: "action-id-family" }));
    const claimedIds = new Set([...exact, ...fallback].map(({ projectile }) => String(projectile?.id || "")));
    const separatorVariants = rows
      .filter((projectile) => !claimedIds.has(String(projectile?.id || "")))
      .filter((projectile) => projectileIdentityValues(projectile).some((value) => {
        const key = projectileCanonicalKey(value);
        if (!skillCanonical || !key.startsWith(skillCanonical)) return false;
        return !siblingCanonical.some((sibling) => sibling.key.length > skillCanonical.length && key.startsWith(sibling.key));
      }))
      .map((projectile) => ({ projectile, score: 1, matched: [skillId], matchMethod: "normalized-action-prefix" }));
    return [...exact, ...fallback, ...separatorVariants];
  }

  function projectilesForSkillGroupUnassigned(group, assignedIds) {
    const groupId = String(group?.id || "");
    const familyMatch = groupId.match(/^(.*)_(NormalAttack|NormalSkill|UltimateSkill|ComboSkill)$/);
    if (!familyMatch) return [];
    const rows = STATE.integration.indexes?.projectiles || [];
    return rows
      .filter((projectile) => projectileMatchesSkillFamily(projectile, familyMatch[1], familyMatch[2]))
      .filter((projectile) => !assignedIds.has(String(projectile?.id || "")))
      .map((projectile) => ({ projectile, score: 2, matched: [familyMatch[1]], matchMethod: "skill-family-identifier" }));
  }

  function projectileDisplayName(projectile) {
    const id = String(projectile?.id || "").replace(/^data_projectile_/, "");
    return readableIntegrationId(id) || String(projectile?.id || "");
  }

  function projectileEffectCount(projectile) {
    return Object.values(projectile?.effects?.lists || {}).reduce((total, items) => total + (Array.isArray(items) ? items.length : 0), 0);
  }

  function projectileSoundCount(projectile) {
    return projectileSoundRows(projectile).length;
  }

  function renderProjectileIntegration(entry) {
    const matches = projectilesForEntry(entry);
    if (!matches.length) return "";
    const cards = matches.map(({ projectile }) => {
      const lifetime = projectile.lifetime || {};
      const movement = projectile.movement || {};
      const collision = projectile.collision || {};
      const targeting = projectile.targeting || {};
      const effects = projectileEffectCount(projectile);
      const sounds = projectileSoundCount(projectile);
      const complete = projectile.confidence?.byteComplete;
      const facts = [
        [text("projectileLifetime"), [lifetime.finishDuration, lifetime.finishDistance].filter((value) => value !== null && value !== undefined && value !== "").map(formatValue).join(" / ")],
        [text("projectileMovement"), `${(movement.modes || []).length}`],
        [text("projectileCollision"), formatValue(collision.shapeType)],
        [text("projectileTargeting"), formatValue(targeting.maxHitCount)],
        [text("projectileEffects"), `${effects} / ${sounds}`],
      ].filter(([, value]) => value !== "" && value !== "undefined");
      const source = projectile.source || {};
      return `<article class="gameplay-projectile-card"><header><div><strong>${escapeHtml(projectileDisplayName(projectile))}</strong><code>${escapeHtml(projectile.id || "")}</code></div><span class="gameplay-projectile-status${complete ? " is-complete" : ""}">${escapeHtml(complete ? text("projectileComplete") : text("projectilePartial"))}</span></header><div class="gameplay-projectile-facts">${facts.map(([label, value]) => `<span><b>${escapeHtml(label)}</b><code>${escapeHtml(value)}</code></span>`).join("")}</div><div class="gameplay-integration-evidence"><code>${escapeHtml([source.root, source.assetName, source.pathId].filter(Boolean).join(" / "))}</code></div></article>`;
    }).join("");
    return section(`${text("projectiles")} (${matches.length})`, `<div class="gameplay-projectile-grid">${cards}</div>`, { open: true });
  }

  function renderIntegratedSections(entry) {
    if (entry?.kind === "character") return "";
    const blocks = [renderGameplayAssetGallery(entry)];
    if (STATE.showDebug) {
      blocks.push(renderCombatIntegration(entry), renderProjectileIntegration(entry));
    }
    const visibleBlocks = blocks.filter(Boolean);
    if (visibleBlocks.length) return visibleBlocks.join("");
    if (!STATE.showDebug) return "";
    if (STATE.integration.status === "loading") {
      return `<div class="gameplay-integration-note" role="status">${escapeHtml(text("integrationLoading"))}</div>`;
    }
    if (STATE.integration.errors.length) {
      return `<div class="gameplay-integration-note is-warning" role="status">${escapeHtml(text("integrationUnavailable"))}</div>`;
    }
    return "";
  }

  function bindIntegratedLinks(root) {
    root.querySelectorAll("[data-gameplay-related-key]").forEach((button) => {
      button.addEventListener("click", () => {
        const target = findGameplayEntry(button.dataset.gameplayRelatedKey || "");
        if (!target) return;
        STATE.selected = target;
        // A related reward often points outside the current search/filter
        // result (for example, an item search pointing at a weapon).  Clear
        // conflicting filters before rendering so renderList does not reset
        // the selection back to the source item.
        if (!STATE.filtered.includes(target)) {
          const query = gp$("#gameplay-q");
          if (query) query.value = "";
          Object.values(STATE.filters).forEach((filter) => filter.clear());
          buildFilterChips();
          applyFilters();
        } else {
          renderList();
        }
        revealSelectedInList();
      });
    });
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

  function bindGameplayMediaPlayers(root) {
    if (!root) return;
    root.querySelectorAll("[data-gameplay-audio-event]").forEach((link) => {
      link.addEventListener("click", (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const audioTab = gp$('.view-tab[data-view="audio"]');
        if (!audioTab || audioTab.hidden) return;
        event.preventDefault();
        history.pushState(null, "", link.href);
        audioTab.click();
      });
    });
    const isRevealed = (media) => {
      for (let node = media.parentElement; node && node !== root; node = node.parentElement) {
        if (node.tagName === "DETAILS" && !node.open) return false;
      }
      return true;
    };
    const enhanceVisible = () => {
      if (!window.WebUI.enhanceMediaPlayers) return;
      root.querySelectorAll("audio:not([data-media-player]), video:not([data-media-player])").forEach((media) => {
        if (!isRevealed(media) || !media.parentElement) return;
        window.WebUI.enhanceMediaPlayers(media.parentElement);
      });
    };
    enhanceVisible();
    root.querySelectorAll("details").forEach((details) => {
      details.addEventListener("toggle", () => {
        if (details.open) enhanceVisible();
      });
    });
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
    ensureGameplayAnimationCatalog(entry);
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
    const integrated = renderIntegratedSections(entry);
    const trailingAudio = entry.kind === "enemy"
      ? section(text("relatedSoundEffects"), renderEnemySoundEffects(entry))
      : entry.kind === "character"
        ? section(text("relatedSoundEffects"), renderCharacterSoundEffects(endministratorVariantEntry(entry)))
        : "";
    gp$("#gameplay-detail-body").innerHTML = `${rendered.body || ""}${integrated}${trailingAudio}`;
    bindGameplayMediaPlayers(detail);
    bindIntegratedLinks(detail);
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
    window.WebUI?.setFilterSectionActiveCounts?.({
      "gameplay-basic": tokens.length ? 1 : 0,
      "gameplay-kind": STATE.filters.kinds.size,
      "gameplay-job": STATE.filters.jobs.size,
      "gameplay-character-property": STATE.filters.characterProperties.size,
      "gameplay-weapon-type": STATE.filters.weaponTypes.size,
      "gameplay-equipment-type": STATE.filters.equipmentTypes.size,
      "gameplay-enemy-type": STATE.filters.enemyTypes.size,
      "gameplay-rarity": STATE.filters.rarities.size,
    });
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
    // #gameplay-tab is owned by the shared data-i18n loop in app.js
    // (gameplayTab in app_labels.js) — not repeated here.
    const pairs = [
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

  function validSoundEffectsPayload(payload) {
    return Boolean(
      payload
      && [1, 2, 3, 4, 5, 6, 7].includes(payload.schemaVersion)
      && payload.characters
      && payload.enemies
    );
  }

  function loadGameplayIntegration(language = currentLanguage(), force = false) {
    const nextLanguage = String(language || "CN").toUpperCase();
    const integration = STATE.integration;
    if (!force && integration.language === nextLanguage && integration.status === "ready") {
      return Promise.resolve(integration);
    }
    if (!force && integration.loading && integration.language === nextLanguage) return integration.loading;
    const token = ++integration.token;
    integration.language = nextLanguage;
    integration.status = "loading";
    integration.combat = null;
    integration.projectiles = null;
    integration.projectileAudio = null;
    integration.soundEffects = null;
    integration.assets = null;
    integration.errors = [];
    integration.indexes = null;
    const requests = [
      ["combat", integrationPath("combat", nextLanguage), (payload) => payload && Array.isArray(payload.nodes) && Array.isArray(payload.edges)],
      ["projectiles", integrationPath("projectiles", nextLanguage), (payload) => payload && Array.isArray(payload.entries)],
      ["projectileAudio", integrationPath("projectileAudio", nextLanguage), (payload) => payload?.schemaVersion === 1 && Array.isArray(payload.links)],
      ["soundEffects", integrationPath("soundEffects", nextLanguage), validSoundEffectsPayload],
      ["assets", integrationPath("assets", nextLanguage), (payload) => payload && payload.entries && typeof payload.entries === "object"],
    ];
    const promise = Promise.all(requests.map(async ([kind, path, validator]) => {
      try {
        return { kind, payload: await fetchIntegrationJson(path, validator), error: "" };
      } catch (error) {
        return { kind, payload: null, error: String(error?.message || error) };
      }
    })).then((results) => {
      if (integration.token !== token) return null;
      for (const result of results) {
        integration[result.kind] = result.payload;
        // Asset refs are an optional visual enhancement. Missing visual refs
        // must not turn a valid Gameplay/Combat/Projectile build into an error.
        // Asset refs are purely visual. Audio sidecars are optional for the
        // authored Gameplay page, but their failure must stay visible: an
        // empty sound section otherwise looks like a valid zero-owner result.
        if (result.error && !["assets", "projectileAudio"].includes(result.kind)) integration.errors.push({ kind: result.kind, message: result.error });
      }
      integration.indexes = buildIntegrationIndexes();
      integration.status = "ready";
      integration.loading = null;
      if (STATE.selected) renderDetail(STATE.selected);
      return integration;
    }).catch((error) => {
      if (integration.token !== token) return null;
      integration.status = "ready";
      integration.loading = null;
      integration.errors = [{ kind: "integration", message: String(error?.message || error) }];
      integration.indexes = buildIntegrationIndexes();
      if (STATE.selected) renderDetail(STATE.selected);
      return integration;
    });
    integration.loading = promise;
    return promise;
  }

  async function loadGameplay(force = false) {
    const language = currentLanguage();
    if (!force && STATE.index && STATE.language === language) {
      if (STATE.integration.language !== language || STATE.integration.status === "idle") void loadGameplayIntegration(language);
      return;
    }
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
        void loadGameplayIntegration(language, force);
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
    window.addEventListener("webui:debug-changed", (event) => {
      STATE.showDebug = Boolean(event.detail && event.detail.enabled);
      if (STATE.selected) renderDetail(STATE.selected);
    });
    window.addEventListener("webui:gender-changed", () => {
      if (STATE.selected && isEndministrator(STATE.selected)) renderDetail(STATE.selected);
    });
  }

  function init() {
    if (!gp$("#gameplay-app")) return;
    STATE.uiLocale = resolveInitialUiLocale();
    STATE.language = currentLanguage();
    STATE.showDebug = document.body.classList.contains("show-debug")
      || gp$("#show-debug")?.getAttribute("aria-pressed") === "true";
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
