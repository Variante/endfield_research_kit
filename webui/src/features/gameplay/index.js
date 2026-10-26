(() => {
  // Gameplay page behavior contract (webui/README.md links here; evidence
  // limits are in memory/webui/gameplay.md).
  //   * Filter sections basic, kind, rarity, job, character-property,
  //     weapon-type, equipment-type, enemy-type and item-type, plus search, reset and
  //     #gameplay-reveal-current. The page loads the base index, projectiles,
  //     projectile_audio.json, combat relationships and asset refs; the large
  //     sound_effects.json loads in the background and fills the projectile,
  //     skill and character/enemy sound sections when it arrives. Both are
  //     Audio publications; Audio still owns the binding evidence.
  //   * Character/enemy details lead with readable effects and attributes.
  //     Parsed mechanisms and description checks stay visible. Raw actions
  //     and references require debug; variant comparisons are disclosures.
  //   * Each character active skill is one card: header with the level
  //     slider, parsed mechanisms, authored description with field-level audit,
  //     and upgrade cost. In debug, one row per sub-skill carries DamageUnits
  //     (type, attribute, stored
  //     blackboard keys resolved to the selected level), remaining blackboard
  //     values and assigned projectiles (speed, distance, time, hits). A
  //     projectile matched only by the group's family identifier gets its own
  //     row named after its action token and marked inferred. Enum numbers,
  //     calculations, effect setup and source paths appear only in debug rows;
  //     evidence notes shared by all skills are stated once above the cards.
  //   * Playable characters have a Data / Loadout switch (loadout.js). Loadout
  //     picks character level (with break stage) and potential, a weapon of
  //     the character's type with level, potential and skill levels, and one
  //     body, one hand and two accessory pieces, each attribute line with its
  //     own enhancement slider (lines sharing an attrIndex move together; a
  //     line with one value at every step is fixed). Cost and final
  //     attributes come from attributeCalculation with per-source breakdowns;
  //     without a validated formula it shows the gate status and computes
  //     nothing. Unmodelled hooks display explicitly partial configuration values.
  //   * A descriptionTemplate (skill groups, weapon/equipment skill levels,
  //     talents, potentials, item use) renders in the browser from the
  //     selected level, highlighting substituted values; value chips the text
  //     already shows are hidden outside debug. An unresolvable placeholder
  //     falls back to the builder's rendered description.
  //   * Exact chr_NNNN_token namespaces without a CharacterTable row are
  //     labeled namespace-only (availability and playable status unproven).
  //     Enemy level selectors show authored level points only, never
  //     interpolated; positive authored skill cooldowns follow the level.
  //   * Skill damage: skillDamageUnits[skillId] are authored DamageUnit rows
  //     from whole-record SkillData, with native enum names beside raw numbers
  //     only after the plan and field types validate; a missing join shows a
  //     note. Conditional formula badges, each behind its own audit status:
  //       - skillDamageRouteEvidence (normal-entity DamageAction selector):
  //         Hp units with simpleCalculation true and takeAtkSnapshot false
  //         show resolved atkScale x attacker attribute element 2, even when an
  //         evaluator subtype is also stored; Poise units get no Hp badge;
  //       - skillDamageAtkScaleEvidence: the AtkScaleCalculation expression,
  //         only when simpleCalculation and takeAtkSnapshot are both false;
  //       - skillDamageBreakingAttackEvidence: the BreakingAttackCalculation
  //         expression on the same non-simple route; its hover keeps the
  //         Double attribute product, Single scale product, Double-to-Single
  //         conversion, final Single multiply and widening to Double;
  //       - skillDamagePoiseRouteEvidence + skillDamageDefiniteValueEvidence:
  //         a conditional Poise calculation-input expression, never an applied
  //         or displayed Poise amount.
  //     Stored level values are never substituted for runtime GetValue; an
  //     unavailable audit leaves raw setup visible with one skill-level note.
  //   * Enemy born-Buff cards expose exact BuffData lifecycle, stacking,
  //     trigger, keyed values, attribute modifiers and applied tag ids. An
  //     unmapped ID keeps its raw value with a hover reason. A nonempty stored
  //     stacking key is quoted only when native evidence validates and the
  //     exact-tail projection supplies it; it is a stored field, not a runtime
  //     stacking group.
  //   * Decoded action chains show the gated event name and decoded fields,
  //     including If/Else-nested actions and common TargetSettings fields of a
  //     partial action; unresolved unions, selectors and payloads stay
  //     visibly unresolved. TargetSettings show native enum names beside each
  //     stored source/target/selector-owner/direction/center number only when
  //     the native field/plan join validates, else raw numbers plus a note.
  //   * Projectile templates, spawned behavior and playable-skill ownership
  //     stay separate relations. Projectile cards list authored effect setup
  //     by serialized list slot; effect type, movement and position-reference
  //     names appear only when projectiles.json schema 5 carries validated
  //     effectConfigEnums/effectConfigEnumEvidence. The authored alert row
  //     appears only when its stored showAlertEffect flag is set.
  //   * Native enum names, tag names and gated event names disappear when the
  //     selected build gate does not validate; the authored rows remain.
  const FILTER_PANEL_STORAGE_KEY = "gameplay_filters_collapsed";
  const COLLAPSED_KINDS_STORAGE_KEY = "gameplay_collapsed_kinds";
  const LEVEL_FRACTION_STORAGE_KEY = "gameplay_level_fraction";
  const GAMEPLAY_DATA_VERSION = "20261010-enemy-distributions";
  const GAMEPLAY_INTEGRATION_VERSION = "20260924-projectile-effect-enums1";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const GENDER_VARIANT_STORAGE_KEY = "webui_gender_variant";
  const ENDADMINISTRATOR_ID = "chr_9000_endmin";
  const ENDADMINISTRATOR_VARIANTS = [
    { gender: "f", characterId: "chr_0003_endminf" },
    { gender: "m", characterId: "chr_0002_endminm" },
  ];
  // Fixed display order for the data-type groups in the list.
  const KIND_ORDER = ["character", "weapon", "gem", "equipment", "item", "enemy"];
  // Enemy display types, ordered 领袖 > 头目 > 精英 > 进阶 > 普通 (by displayType id).
  const ENEMY_TYPE_RANK = { "2": 0, "4": 1, "1": 2, "3": 3, "0": 4 };
  // Reuse the story page's badge color sets for the kind filter chips, so each
  // data type reads with the same palette as the story badges (badge-env, ...).
  const KIND_CHIP_CLASS = {
    gem: "kind-chip badge-radio",
    weapon: "kind-chip badge-cutscene",
    equipment: "kind-chip badge-radio",
    character: "kind-chip badge-env",
    enemy: "kind-chip badge-reading",
    item: "kind-chip badge-mail",
  };
  // Same palette as a plain badge chip for the list rows (story item style).
  const KIND_BADGE_CLASS = {
    gem: "badge-radio",
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
    characterView: storageGet("endfield.characterView") === "loadout" ? "loadout" : "info",
    index: null,
    entries: [],
    filtered: [],
    selected: null,
    enemyVariantIds: new Map(),
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
    loadToken: 0,
    showDebug: false,
    searchTokens: [],
    collapsedKinds: new Set(),
    levelFraction: 1,
    facets: null,
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
    const gameKey = {
      equipmentStats: "ui_wiki_equip_attribute",
      equipmentAttributeFilter: "ui_wiki_equip_attribute",
      loadoutSetEffect: "ui_wiki_equip_suit_effect",
      enemyAbilities: "ui_wiki_enemy_power",
      dropItems: "ui_wiki_enemy_drop",
      weaponSkills: "ui_wiki_weapon_skill_effect",
    }[key];
    if (gameKey && STATE.index?.uiLabels?.[gameKey]) return applyTemplate(STATE.index.uiLabels[gameKey], replacements);
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
    return decoded;
  }

  function requestedGameplaySelection() {
    const params = new URLSearchParams(window.location.search || "");
    return normalizeGameplaySelection(params.get("gameplay") || "");
  }

  function findGameplayEntry(value, entries = STATE.entries) {
    const id = normalizeGameplaySelection(value);
    if (!id) return null;
    const raw = String(value || "").trim();
    const exactKey = raw.includes(":") ? raw : "";
    if (exactKey) {
      const exact = entries.find((entry) => entry && `${entry.kind}:${entry.id}` === exactKey);
      if (exact) return exact;
    }
    const candidates = new Set([id]);
    if (!id.startsWith("wiki_")) candidates.add(`wiki_${id}`);
    const variantOwners = entries.filter((entry) => entry?.kind === "enemy" && entry.variants?.some((variant) => variant.id === id));
    if (variantOwners.length === 1) return variantOwners[0];
    return entries.find((entry) => entry && (
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
    if (kind === "gem") return text("gem");
    if (kind === "weapon") return text("weapon");
    if (kind === "equipment") return text("equipment");
    if (kind === "character") return text("character");
    if (kind === "enemy") return text("enemy");
    if (kind === "item") return text("item");
    return String(kind || "");
  }

  function entrySubtitle(entry) {
    const parts = [];
    if (entry.kind === "gem") parts.push(entry.location || "");
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

  function section(title, body, key = "") {
    return window.WebUI.gameplayDetail.section(title, body, { id: key ? `gameplay-section-${key}` : "", focusable: Boolean(key) });
  }

  function disclosure(title, body, hint = "") {
    if (!body) return "";
    return `<details class="gameplay-disclosure"><summary><span>${escapeHtml(title)}</span>${hint ? `<small>${escapeHtml(hint)}</small>` : ""}</summary><div class="gameplay-disclosure-body">${body}</div></details>`;
  }

  function bindDetailContents(root) {
    const sections = [...root.querySelectorAll("[data-gameplay-section]")];
    if (sections.length < 2) return;
    const nav = document.createElement("nav");
    nav.className = "gameplay-contents";
    nav.setAttribute("aria-label", text("detailContents"));
    sections.forEach((target) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = target.dataset.gameplaySection;
      button.addEventListener("click", () => {
        if (target.tagName === "DETAILS") target.open = true;
        const header = gp$("#gameplay-detail-header");
        const headerHeight = header && getComputedStyle(header).position === "sticky"
          ? header.getBoundingClientRect().height : 0;
        target.style.scrollMarginTop = `${headerHeight + 18}px`;
        target.scrollIntoView({ block: "start" });
        target.focus({ preventScroll: true });
      });
      nav.append(button);
    });
    root.querySelector(".gameplay-reading-view")?.prepend(nav);
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

  function storyWikiHrefForKey(key, language = STATE.language) {
    if (!key) return "";
    const params = new URLSearchParams();
    params.set("lang", language || currentLanguage());
    params.set("ui", STATE.uiLocale || "zh");
    params.set("story", key);
    return `?${params.toString()}#story`;
  }

  function storyWikiHref(entry) {
    return storyWikiHrefForKey(storyWikiKey(entry));
  }

  function renderStoryWikiLink(entry, language = STATE.language) {
    const activeGender = currentCharacterGender();
    const keys = isEndministrator(entry)
      ? storyWikiKeys(entry).filter((key) => {
        const gender = endministratorGenderForValue(key);
        return !gender || gender === activeGender;
      })
      : storyWikiKeys(entry);
    return keys.map((key) => {
      const href = storyWikiHrefForKey(key, language);
      if (!href) return "";
      return window.WebUI.gameplayDetail.storyWikiLink(href, text("storyWiki"));
    }).filter(Boolean).join("");
  }
  function renderDescription(value) {
    const textValue = String(value || "").trim();
    if (!textValue) return "";
    return `<p class="gameplay-description">${escapeHtml(textValue).replace(/\n/g, "<br>")}</p>`;
  }

  // Authored descriptions carry `{key}`, `{key:0.0%}` or a small arithmetic
  // expression over keys (`{1-dmg_taken_down:0%}`). The builder renders them
  // once; rendering here lets the text follow the selected level. Mirrors
  // render_description in scripts/webui/gameplay/base_data.py, except that
  // fixed-decimal specs (`0.0`, `0.##`) are honoured instead of `%.6g`.
  const DESC_PLACEHOLDER_RE = /\{([^}:]+)(?::([^}]+))?\}/g;

  function descriptionValueMap(...sources) {
    const values = new Map();
    const set = (key, value) => {
      if (key === undefined || key === null || key === "" || value === undefined || value === null || value === "") return;
      const name = String(key);
      if (!values.has(name)) values.set(name, value);
      if (!values.has(name.toLowerCase())) values.set(name.toLowerCase(), value);
    };
    for (const source of sources) {
      if (Array.isArray(source)) source.forEach((item) => set(item?.key, item?.value));
      else if (source && typeof source === "object") Object.entries(source).forEach(([key, value]) => set(key, value));
    }
    return values;
  }

  function lookupDescriptionValue(name, values) {
    const key = String(name || "").trim();
    if (values.has(key)) return { key, value: values.get(key) };
    if (values.has(key.toLowerCase())) return { key, value: values.get(key.toLowerCase()) };
    return null;
  }

  // Recursive-descent evaluator for + - * / and parentheses over numbers and
  // value keys. Returns null when any key is missing or non-numeric.
  function evaluateDescriptionExpression(expr, values) {
    const direct = lookupDescriptionValue(expr, values);
    if (direct) return { value: direct.value, keys: [direct.key] };
    const tokens = String(expr).match(/\d+(?:\.\d+)?|[A-Za-z_][\w.\\]*|[-+*/()]/g) || [];
    if (tokens.join("") !== String(expr).replace(/\s+/g, "")) return { value: null, keys: [] };
    const keys = [];
    let index = 0;
    const primary = () => {
      const token = tokens[index++];
      if (token === undefined) return null;
      if (token === "(") {
        const value = additive();
        return tokens[index++] === ")" ? value : null;
      }
      if (token === "-" || token === "+") {
        const value = primary();
        return value === null ? null : token === "-" ? -value : value;
      }
      if (/^\d/.test(token)) return Number(token);
      const found = lookupDescriptionValue(token, values);
      const number = found ? Number(found.value) : NaN;
      if (!found || typeof found.value === "boolean" || !Number.isFinite(number)) return null;
      keys.push(found.key);
      return number;
    };
    const multiplicative = () => {
      let value = primary();
      while (value !== null && (tokens[index] === "*" || tokens[index] === "/")) {
        const op = tokens[index++];
        const right = primary();
        if (right === null || (op === "/" && right === 0)) return null;
        value = op === "*" ? value * right : value / right;
      }
      return value;
    };
    const additive = () => {
      let value = multiplicative();
      while (value !== null && (tokens[index] === "+" || tokens[index] === "-")) {
        const op = tokens[index++];
        const right = multiplicative();
        if (right === null) return null;
        value = op === "+" ? value + right : value - right;
      }
      return value;
    };
    const value = additive();
    return index === tokens.length && value !== null ? { value, keys } : { value: null, keys: [] };
  }

  function formatDescriptionValue(value, spec) {
    if (typeof value !== "number" || !Number.isFinite(value)) return String(value);
    const format = String(spec || "").trim();
    const decimals = (format.match(/\.([0#]+)/) || [])[1] || "";
    const fixed = (number) => {
      const out = number.toFixed(decimals.length);
      // `#` digits are optional: trim trailing zeros they allow.
      return decimals.includes("#") ? String(Number(out)) : out;
    };
    if (format.includes("%")) return `${fixed(value * 100)}%`;
    if (/^0(?:\.[0#]+)?$/.test(format)) return fixed(value);
    return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(6)));
  }

  // Returns the description HTML with each substituted value highlighted, and
  // the value keys the text consumed. When the frontend cannot resolve a
  // placeholder the builder's rendered text is used as-is.
  function renderTemplateDescription(template, values, fallback = "") {
    const source = String(template || "").trim();
    if (!source || !source.includes("{")) return { html: renderDescription(fallback || source), used: new Set() };
    const used = new Set();
    let unresolved = 0;
    let html = "";
    let last = 0;
    for (const match of source.matchAll(DESC_PLACEHOLDER_RE)) {
      html += escapeHtml(source.slice(last, match.index));
      last = match.index + match[0].length;
      const result = evaluateDescriptionExpression(match[1], values);
      if (result.value === null) {
        unresolved += 1;
        html += escapeHtml(match[0]);
        continue;
      }
      result.keys.forEach((key) => used.add(key));
      html += `<span class="gameplay-desc-value" title="${escapeHtml(match[1].trim())}">${escapeHtml(formatDescriptionValue(result.value, match[2]))}</span>`;
    }
    html += escapeHtml(source.slice(last));
    const fallbackText = String(fallback || "").trim();
    if (unresolved && fallbackText && !fallbackText.includes("{")) return { html: renderDescription(fallbackText), used: new Set() };
    return { html: `<p class="gameplay-description">${html.replace(/\n/g, "<br>")}</p>`, used };
  }

  // Blackboard chips minus the keys the description already shows; debug
  // mode keeps every chip.
  function renderUnusedBlackboard(items, used) {
    if (STATE.showDebug || !used?.size) return renderBlackboard(items);
    return renderBlackboard((items || []).filter((item) => !used.has(String(item?.key || ""))));
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

  function gameplayTargetForItem(item, entries = STATE.entries) {
    const id = String(item?.id || "").trim();
    if (!id) return null;
    let kind = ["weapon", "character"].includes(String(item?.kind || "")) ? String(item.kind) : "";
    if (!kind && id.startsWith("wpn_")) kind = "weapon";
    if (!kind && id.startsWith("chr_")) kind = "character";
    return kind ? findGameplayEntry(`${kind}:${id}`, entries) : null;
  }

  function materialChipRows(items, entries = STATE.entries) {
    return (items || [])
      .filter((item) => item && (item.name || item.id))
      .map((item) => {
        const label = item.name || item.id;
        const count = window.WebUI.gameplayDetail.knownQuantity(item.count, item.quantityDataUnavailable)
          ? formatValue(item.count) : "";
        const target = gameplayTargetForItem(item, entries);
        const icon = renderGameplayItemIcon(item, label, { static: Boolean(target) });
        if (target) {
          const targetKey = `${target.kind}:${target.id}`;
          return `<button type="button" class="gameplay-value-chip gameplay-item-chip gameplay-related-link gameplay-item-chip-link" data-gameplay-related-key="${escapeHtml(targetKey)}" title="${escapeHtml(target.id)}" aria-label="${escapeHtml(label)}">${icon}<b>${escapeHtml(label)}</b>${escapeHtml(count)}</button>`;
        }
        if (item.id && (!item.kind || item.kind === 'item')) {
          const href = window.WebUI.gameplayTabs.pageUrl('item', String(item.id));
          return `<a class="gameplay-value-chip gameplay-item-chip gameplay-item-chip-link" href="${escapeHtml(href)}">${icon}<b>${escapeHtml(label)}</b>${escapeHtml(count)}</a>`;
        }
        return `<span class="gameplay-value-chip gameplay-item-chip">${icon}<b>${escapeHtml(label)}</b>${escapeHtml(count)}</span>`;
      })
      .join("");
  }

  function renderMaterialChips(items, entries = STATE.entries) {
    const rows = materialChipRows(items, entries);
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
        Number(brk.gold) > 0 ? renderValueChip(goldCostPair(brk.gold)) : "",
        materialChipRows(brk.items || []),
      ].filter(Boolean).join("");
      if (chips) parts.push(`<div class="gameplay-subheading">${escapeHtml(costIndex.breakLabel)}</div><div class="gameplay-blackboard">${chips}</div>`);
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
      cumulativeExpItems ? materialChipRows(cumulativeExpItems) : "",
      upPairs ? upPairs.map((pair) => renderValueChip(pair)).join("") : "",
      expItems.length ? materialChipRows(expItems) : "",
    ].filter(Boolean).join("");
    if (upChips) parts.push(`<div class="gameplay-subheading">${escapeHtml(text("levelUpCosts"))}</div><div class="gameplay-blackboard">${upChips}</div>`);
    return parts.length ? `<div class="gameplay-level-cost">${parts.join("")}</div>` : "";
  }

  function renderStatPane(row, active, costIndex, textOnly) {
    return `<div class="gameplay-level-pane gameplay-stat-pane" data-level-label="${escapeHtml(statLevelLabel(row))}"${active ? "" : " hidden"}>
      <div class="gameplay-level-effect">${renderStatAttrs(row, textOnly) || `<span class="muted">-</span>`}</div>
      ${renderStatCost(row, costIndex)}
    </div>`;
  }

  function renderStats(stats, costIndex, { showSource = true, textOnly = false } = {}) {
    const rows = ((stats && (stats.rows || stats.checkpoints)) || []).filter((row) => row && (row.attrs || []).length);
    if (!rows.length) return "";
    const body = rows.length > 1
      ? `<div class="gameplay-level-slider-wrap gameplay-stat-slider" data-level-card>
        <div class="gameplay-level-slider-control">
          <span>${escapeHtml(text("selectedLevel"))}</span>
          <input class="gameplay-level-slider" type="range" min="0" max="${rows.length - 1}" step="1" value="0" aria-label="${escapeHtml(text("selectedLevel"))}">
          <output class="gameplay-level-slider-output">${escapeHtml(statLevelLabel(rows[0]))}</output>
        </div>
        <div class="gameplay-level-panes">${rows.map((row, index) => renderStatPane(row, index === 0, costIndex, textOnly)).join("")}</div>
      </div>`
      : `<div class="gameplay-level-table">${rows.map((row) => `<div class="gameplay-level-row gameplay-stat-row">
        <div class="gameplay-level-num">${escapeHtml(statLevelLabel(row))}</div>
        <div class="gameplay-level-effect">${renderStatAttrs(row, textOnly) || `<span class="muted">-</span>`}${renderStatCost(row, costIndex)}</div>
        <div class="gameplay-level-values"></div>
      </div>`).join("")}</div>`;
    return window.WebUI.gameplayDetail.propertyCard({ title: text("statCheckpoints"), bodyHtml: body,
      className: "gameplay-stat-card", metaHtml: `<div class="gameplay-skill-meta">${escapeHtml(statCurveMeta(stats, showSource))}</div>` });
  }

  function skillLevelDescription(level) {
    return renderTemplateDescription(
      level.descriptionTemplate,
      descriptionValueMap(level.blackboard, { costValue: level.costValue, coolDown: level.coolDown }),
      level.description,
    );
  }

  function renderLevelPane(level, active, costRow) {
    const description = skillLevelDescription(level);
    const values = [renderUnusedBlackboard(level.blackboard, description.used), renderSubDesc(level.subDesc)].filter(Boolean).join("");
    const cost = renderUpgradeCost(costRow);
    return `<div class="gameplay-level-pane${values ? "" : " is-text-only"}" data-level-label="${escapeHtml(levelLabel(level))}"${active ? "" : " hidden"}>
      <div class="gameplay-level-effect">${description.html || `<span class="muted">-</span>`}</div>
      ${values ? `<div class="gameplay-level-values">${values}</div>` : ""}
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
      const description = skillLevelDescription(level);
      const values = [renderUnusedBlackboard(level.blackboard, description.used), renderSubDesc(level.subDesc)].filter(Boolean).join("");
      const cost = renderUpgradeCost(levelUpForLevel(level, levelUpRows));
      return `<div class="gameplay-level-row${values ? "" : " is-text-only"}">
        <div class="gameplay-level-num">${escapeHtml(formatValue(level.level || ""))}</div>
        <div class="gameplay-level-effect">${description.html || `<span class="muted">-</span>`}</div>
        ${values ? `<div class="gameplay-level-values">${values}</div>` : ""}
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
    const description = renderTemplateDescription(talent.descriptionTemplate, descriptionValueMap(talent.blackboard), talent.description);
    return `<article class="gameplay-skill-card">
      <header>
        <div class="gameplay-skill-title">${escapeHtml(talent.title || talent.id || "")}</div>
        <div class="gameplay-skill-meta">${escapeHtml([talent.id, meta].filter(Boolean).join(" / "))}</div>
      </header>
      ${description.html}
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

  // Skill ids a potential/passive effect targets carry no table name; name
  // them from the character's own skill groups and passive talents.
  function characterSkillNames(entry) {
    const names = new Map();
    for (const group of entry?.skillGroups || []) {
      for (const skill of group.skills || []) if (skill?.id) names.set(skill.id, group.name || group.id);
      if (group.id) names.set(group.id, group.name || group.id);
    }
    for (const group of entry?.talentGroups || []) {
      for (const level of group.levels || []) {
        for (const ref of level.effectRefs || []) {
          if (ref?.type === "skill" && ref.id && !names.has(ref.id)) names.set(ref.id, group.title || level.title || ref.id);
        }
      }
    }
    return names;
  }

  const EFFECT_OPERATION_SYMBOLS = { Add: "+", Multiply: "×", Overwrite: "=" };
  const EFFECT_PARAM_LABEL_KEYS = { CostValue: "effectParamCost", CoolDown: "cooldown", CoolDownDisplay: "cooldown", MaxChargeTime: "effectParamMaxCharge" };

  // `has_potential1`, `potential_3`, `talent_1`... set to 1: a switch the
  // target skill reads to enable a branch, not a quantity.
  function isEffectSwitch(row) {
    return /^(?:has_)?(?:potential|talent)_?\d*$/i.test(String(row.key || "")) && Number(row.value) === 1;
  }

  function effectOperationText(row, value) {
    const symbol = EFFECT_OPERATION_SYMBOLS[row.operationName];
    if (symbol === "+") return Number(row.value) < 0 ? value : `+${value}`;
    return symbol ? `${symbol} ${value}` : `(${formatValue(row.operation)}) ${value}`;
  }

  function renderEffectRow(row, skillNames, used = new Set()) {
    const target = row.skillId ? `<b title="${escapeHtml(row.skillId)}">${escapeHtml(skillNames.get(row.skillId) || row.skillId)}</b>` : "";
    let body = "";
    if (row.kind === "attribute") {
      const spec = (String(row.valueFormat || "").match(/\{value(?::([^}]+))?\}/) || [])[1] || "";
      const value = formatDescriptionValue(Number(row.value), spec);
      body = `<b>${escapeHtml(row.attrName || row.attrTypeName || `attr ${row.attrType}`)}</b> ${escapeHtml(Number(row.value) < 0 ? value : `+${value}`)}`;
    } else if (row.kind === "skillBlackboard") {
      body = isEffectSwitch(row)
        ? `${target} ${escapeHtml(text("effectEnableSwitch"))} <code>${escapeHtml(row.key)}</code>`
        : `${target} <code>${escapeHtml(row.key)}</code> ${escapeHtml(effectOperationText(row, formatValue(row.value)))}`;
    } else if (row.kind === "skillParam") {
      const labelKey = EFFECT_PARAM_LABEL_KEYS[row.paramName];
      const label = (labelKey ? text(labelKey) : "") || row.paramName || `param ${row.paramType}`;
      body = `${target} ${escapeHtml(label)} ${escapeHtml(effectOperationText(row, formatValue(row.value)))}`;
    } else if (row.kind === "passiveSkill") {
      body = `${escapeHtml(text("effectAddPassive"))} ${target}`;
    } else if (row.kind === "buff") {
      body = `${escapeHtml(text("effectAddBuff"))} <code>${escapeHtml(row.buffId)}</code>`;
    }
    const paramRows = (row.kind === "passiveSkill" || row.kind === "buff")
      ? (row.blackboard || []).filter((item) => STATE.showDebug || !used.has(String(item?.key || "")))
      : [];
    const params = paramRows.length
      ? ` <small>${escapeHtml(paramRows.map((item) => `${item.key} ${formatValue(item.value)}`).join(" · "))}</small>`
      : "";
    const condition = (row.conditions || []).length ? ` <small>${escapeHtml(text("effectCondition"))}: ${escapeHtml(row.conditions.join(", "))}</small>` : "";
    const debug = STATE.showDebug
      ? ` <small class="muted">${escapeHtml([row.modifyTypeName || `modifyType ${row.modifyType}`, row.operationName, row.modifierTypeName, row.attrTypeName].filter(Boolean).join(" · "))}</small>`
      : "";
    return `<li>${body}${params}${condition}${debug}</li>`;
  }

  // Effects the description does not already state. Attribute rows are
  // stated when the text reads their native name (`{Wisd}`); blackboard and
  // param rows when it reads their key. Debug mode lists every row.
  function renderTalentEffects(record, used, skillNames) {
    const rows = (record?.effects || []).filter((row) => {
      if (STATE.showDebug) return true;
      if (row.kind === "attribute") return !used.has(String(row.attrTypeName || ""));
      if (row.kind === "skillBlackboard") return !used.has(String(row.key || ""));
      // A passive skill the talent itself grants is the talent: list it only
      // when it carries a value the text does not show.
      if (row.kind === "passiveSkill") return (row.blackboard || []).some((item) => !used.has(String(item?.key || "")));
      if (row.kind === "skillParam") {
        const aliases = { CostValue: ["costvalue", "costValue"], CoolDown: ["coolDown", "cooldown", "cd"] }[row.paramName] || [];
        return !aliases.some((key) => used.has(key));
      }
      return true;
    });
    if (!rows.length) return "";
    const title = STATE.showDebug ? text("effectsAll") : text("effectsOther");
    return `<div class="gameplay-effect-list"><div class="gameplay-subheading">${escapeHtml(title)}</div><ul>${rows.map((row) => renderEffectRow(row, skillNames, used)).join("")}</ul></div>`;
  }

  function renderTalentLevelCell(level, groupTitle, groupKind, skillNames = new Map()) {
    const title = level.name || (level.title !== groupTitle ? level.title : "") || `${text("level")} ${formatValue(level.level || "")}`;
    const coordinate = sourceCoordinate(level.source);
      const meta = [
        level.level ? `${text("level")} ${formatValue(level.level)}` : "",
        level.breakStage ? `${text("breakStage")} ${formatValue(level.breakStage)}` : "",
        level.equipTierLimit ? `T${formatValue(level.equipTierLimit)}` : "",
        level.unlockHint ? `${text("unlockHint")}: ${level.unlockHint}` : "",
        STATE.showDebug && level.iconId ? `${text("iconId")}: ${level.iconId}` : "",
        STATE.showDebug && coordinate ? `${text("dataCoordinate")}: ${coordinate}` : "",
        STATE.showDebug ? level.id : "",
    ].filter(Boolean).join(" / ");
    const icon = renderGameplayTokenIcon(level.iconId, title, {
      className: groupKind === "passive" ? "gameplay-passive-talent-icon" : "",
    });
    const attr = level.attributeModifier && Object.keys(level.attributeModifier).length
      ? renderBlackboard(Object.entries(level.attributeModifier).map(([key, value]) => ({ key, value })))
      : "";
    const required = renderRequiredItems(level.requiredItem || []);
    const description = renderTemplateDescription(level.descriptionTemplate, descriptionValueMap(level.blackboard), level.description);
    const effects = Array.isArray(level.effects)
      ? renderTalentEffects(level, description.used, skillNames)
      : renderUnusedBlackboard(level.blackboard, description.used);
    const values = disclosure(text("configurationDetails"), [effects, attr].filter(Boolean).join(""));
    return `<div class="gameplay-talent-level">
      <div class="gameplay-talent-level-title">${icon}<span>${escapeHtml(title)}</span></div>
      <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
      ${description.html}
      ${values}
      ${required ? `<div class="gameplay-subheading">${escapeHtml(text("requiredItems"))}</div>${required}` : ""}
    </div>`;
  }

  function renderTalentGroupRow(group, skillNames) {
    if (!group) return "";
    const levels = group.levels || [];
    const meta = [group.rank ? `${text("rank")} ${formatValue(group.rank)}` : "", STATE.showDebug ? group.id : ""]
      .filter(Boolean)
      .join(" / ");
    const title = (group.kind === "attribute" || group.kind === "upgrade") ? talentKindLabel(group.kind) : (group.title || group.id || "");
    return `<article class="gameplay-talent-row gameplay-talent-${escapeHtml(group.kind || "other")}">
      <header class="gameplay-talent-row-header">
        <div>
          <div class="gameplay-group-title">${escapeHtml(title)}</div>
          ${meta ? `<div class="gameplay-skill-meta">${escapeHtml(meta)}</div>` : ""}
        </div>
      </header>
      <div class="gameplay-talent-levels">${levels.map((level) => renderTalentLevelCell(level, group.title, group.kind, skillNames)).join("")}</div>
    </article>`;
  }

  function renderTalentGroups(groups, skillNames = new Map()) {
    // Breakthrough and attribute nodes belong to the removed character-growth
    // surface. Keep actual passive/factory talents in the native talent table.
    const rows = (groups || [])
      .filter((group) => !["upgrade", "attribute"].includes(String(group?.kind || "")))
      .map((group) => renderTalentGroupRow(group, skillNames))
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
    const itemId = item?.iconItem?.id;
    const icon = item?.iconItem ? renderGameplayItemIcon(item.iconItem, item.iconLabel || item.label, { static: Boolean(itemId) }) : "";
    const content = `${icon}<b>${escapeHtml(item.label)}</b>${escapeHtml(formatValue(item.value))}`;
    const className = `gameplay-value-chip${cls ? ` ${escapeHtml(cls)}` : ""}`;
    return itemId
      ? `<a class="${className} gameplay-item-chip gameplay-item-chip-link" href="${escapeHtml(window.WebUI.gameplayTabs.pageUrl("item", String(itemId)))}">${content}</a>`
      : `<span class="${className}">${content}</span>`;
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

  function renderStatAttrs(rowOrAttrs, textOnly = false) {
    const attrs = Array.isArray(rowOrAttrs) ? rowOrAttrs : (rowOrAttrs && rowOrAttrs.attrs || []);
    const abilityClass = (item) => item.key === "main_attr" || item.type === "Main" ? " gameplay-ability-main" : item.key === "sub_attr" || item.type === "Sub" ? " gameplay-ability-sub" : "";
    if (textOnly) return attrs
      .filter((item) => item && item.value !== undefined && item.value !== null && item.value !== "")
      .map((item) => `<p class="gameplay-description"><span class="${abilityClass(item).trim()}">${escapeHtml(statAttrLabel(item))}+<span class="gameplay-desc-value">${escapeHtml(formatStatValue(item.value))}</span></span></p>`).join("");
    const rows = attrs
      .filter((item) => item && item.value !== undefined && item.value !== null && item.value !== "")
      .map((item) => `<span class="gameplay-value-chip${abilityClass(item)}"><b>${escapeHtml(statAttrLabel(item))}</b>${escapeHtml(formatStatValue(item.value))}</span>`);
    return rows.length ? `<div class="gameplay-blackboard">${rows.join("")}</div>` : "";
  }

  function statCurveMeta(stats, showSource = true) {
    if (!stats) return "";
    return [
      showSource ? stats.source : "",
      showSource ? stats.templateId : "",
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

  // Cooldown and subDesc labels describe the whole skill group, so they stay
  // as chips above the action table. Blackboard keys belong to one sub-skill
  // and are shown on that sub-skill's action row instead.
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

  // The group description reads the sub-skills' values at one level, first
  // occurrence of each key in sub-skill order (as the builder aggregates).
  function activeSkillGroupDescription(group, levelValue) {
    const items = [];
    const seen = new Set();
    for (const skill of group.skills || []) {
      for (const item of levelForSkill(skill, levelValue)?.blackboard || []) {
        if (!item?.key || seen.has(item.key)) continue;
        seen.add(item.key);
        items.push(item);
      }
    }
    return renderTemplateDescription(group.descriptionTemplate, descriptionValueMap(items), group.description).html;
  }

  // Skill audio is level-independent: rendered once into the active pane's
  // slot (after the description, before the upgrade cost) and moved with
  // the level slider.
  function renderActiveSkillLevelPane(group, levelValue, active, actions, sound = "") {
    const description = activeSkillGroupDescription(group, levelValue);
    const chips = collectGroupLevelChips(group, levelValue);
    const table = STATE.showDebug ? disclosure(text("skillParameters"), renderActiveSkillActionTable(actions, levelValue)) : "";
    const mechanics = `<div class="gameplay-mechanics" data-mechanics-group="${escapeHtml(group.id)}" data-mechanics-level="${escapeHtml(levelValue)}"><h4>${escapeHtml(text("mechanicsSummary"))}</h4><div class="gameplay-mechanics-content"><p class="muted">${escapeHtml(text("mechanicsLoading"))}</p></div></div>`;
    const authored = description ? `<div class="gameplay-authored-description"><span class="gameplay-caption">${escapeHtml(text("authoredDescription"))}</span>${description}<div data-description-audit></div></div>` : "";
    const cost = renderUpgradeCost(levelUpForLevel({ level: levelValue }, group.levelUp || []));
    const footer = chips || cost ? `<div class="gameplay-skill-level-footer">${chips}${cost}</div>` : "";
    const soundSlot = sound ? `<div data-skill-sound-slot>${active ? sound : ""}</div>` : "";
    return `<div class="gameplay-level-pane gameplay-active-skill-pane" data-level-label="${escapeHtml(levelLabel({ level: levelValue }))}"${active ? "" : " hidden"}>${mechanics}${authored}${table}${soundSlot}${footer}</div>`;
  }

  async function mountSkillMechanics(root, entry) {
    const slots = [...root.querySelectorAll("[data-mechanics-group]")];
    if (!slots.length) return;
    const groups = new Map((entry.skillGroups || []).map((group) => [String(group.id), group]));
    const ids = [...groups.values()].flatMap((group) => [...(group.actionSkillIds || []), ...(group.skills || []).map((skill) => skill.id)]);
    const index = STATE.index;
    const mechanics = window.WebUI.gameplayMechanics;
    let records = new Map();
    try {
      records = await window.WebUI.gameplaySkillRefs.loadRecords(ids);
      if (!slots.some((slot) => slot.isConnected)) return;
      const callbacks = mechanics.callbackIds(records);
      if (callbacks.length) {
        const children = await window.WebUI.gameplaySkillRefs.loadRecords(callbacks);
        for (const [id, record] of children) records.set(id, record);
      }
    } catch (_) { /* Missing actions stay unverified; descriptions remain usable. */ }
    for (const slot of slots) {
      if (!slot.isConnected) continue;
      const group = groups.get(slot.dataset.mechanicsGroup);
      if (!group) continue;
      const level = Number(slot.dataset.mechanicsLevel);
      const helpers = { index, records, text };
      slot.querySelector(".gameplay-mechanics-content").innerHTML = mechanics.markup(mechanics.skillRows(group, level, helpers));
      const audit = slot.parentElement.querySelector("[data-description-audit]");
      if (audit) audit.innerHTML = mechanics.auditMarkup(mechanics.descriptionAudit(group, level, helpers));
    }
  }

  // Returns the level slider (placed in the skill header) and the per-level
  // panes separately; the skill card carries `data-level-card`, so the slider
  // drives panes anywhere inside it.
  function renderActiveSkillLevels(group, sound = "") {
    const levels = sortedSkillLevelsForGroup(group);
    if (!levels.length) return { control: "", panes: "" };
    const actions = activeSkillActions(group);
    const control = levels.length === 1
      ? `<span class="gameplay-skill-level-single">${escapeHtml(levelLabel({ level: levels[0] }))}</span>`
      : `<div class="gameplay-level-slider-control">
          <span>${escapeHtml(text("selectedLevel"))}</span>
          <input class="gameplay-level-slider" type="range" min="0" max="${levels.length - 1}" step="1" value="0" aria-label="${escapeHtml(text("selectedLevel"))}">
          <output class="gameplay-level-slider-output">${escapeHtml(levelLabel({ level: levels[0] }))}</output>
        </div>`;
    const panes = levels.map((level, index) => renderActiveSkillLevelPane(group, level, index === 0, actions, sound)).join("");
    return { control, panes };
  }

  function skillDamageEnum(value) {
    if (!value || !Number.isInteger(value.value)) return "";
    return value.name
      ? `${value.name} (${formatValue(value.value)})`
      : formatValue(value.value);
  }

  function skillDamageOperand(value) {
    if (!value || typeof value !== "object") return "";
    const mode = value.useBlackboardKey
      ? `${text("skillDamageBlackboardKey")}: ${value.blackboardKey || "?"}`
      : text("skillDamageLiteral");
    return `${mode}; ${text("skillDamageStoredValue")}: ${formatValue(value.value)}`;
  }

  function skillDamageCalculation(value) {
    if (!value) return "";
    const type = String(value.type || "").split(".").pop();
    const members = Object.entries(value.enums || {})
      .map(([key, member]) => `${key}=${skillDamageEnum(member)}`);
    const operands = Object.entries(value.operands || {})
      .map(([key, operand]) => `${key}=[${skillDamageOperand(operand)}]`);
    const scalars = Object.entries(value.scalars || {})
      .map(([key, scalar]) => `${key}=${formatValue(scalar)}`);
    return [type, `tag=${formatValue(value.tag)}`, ...members, ...operands, ...scalars]
      .filter(Boolean).join(", ");
  }

  // Authored Blackboard keys on a DamageUnit, in stored order: the attack
  // scale plus any keyed operand of its attack/poise calculation. A route may
  // bypass some of these keys; this list is only for displaying setup values.
  function skillDamageUnitKeys(unit) {
    const keys = [];
    const add = (operand) => {
      if (operand?.useBlackboardKey && operand.blackboardKey && !keys.includes(operand.blackboardKey)) keys.push(operand.blackboardKey);
    };
    add(unit.atkScale);
    for (const calculation of [unit.atkCalculation, unit.poiseCalculation]) {
      for (const operand of Object.values(calculation?.operands || {})) add(operand);
    }
    return keys;
  }

  function skillDamageUnitDebugText(unit) {
    return [
      [text("skillDamageAttribute"), skillDamageEnum(unit.damageAttributeType)],
      [text("skillDamageType"), skillDamageEnum(unit.damageType)],
      [text("skillDamageSimpleCalculation"), typeof unit.simpleCalculation === "boolean" ? String(unit.simpleCalculation) : ""],
      [text("skillDamageTakeAtkSnapshot"), typeof unit.takeAtkSnapshot === "boolean" ? String(unit.takeAtkSnapshot) : ""],
      [text("skillDamageAttackScale"), skillDamageOperand(unit.atkScale || {})],
      [text("skillDamageAttackCalculation"), skillDamageCalculation(unit.atkCalculation)],
      [text("skillDamagePoiseCalculation"), skillDamageCalculation(unit.poiseCalculation)],
      [text("skillDamageVisualImportance"), skillDamageEnum(unit.damageVisualImportance)],
      [text("skillDamageImmunitySetting"), skillDamageEnum(unit.ignoreDamageImmuneLevel)],
      [text("skillDamageDecorationMask"), Number.isInteger(unit.damageDecorateMask)
        ? `${formatValue(unit.damageDecorateMask)} (0x${unit.damageDecorateMask.toString(16)})` : ""],
      [text("source"), unit.sourcePath || ""],
    ].filter(([, value]) => value).map(([label, value]) => `${label}: ${value}`).join(" · ");
  }

  // One action per sub-skill: its authored DamageUnits and the projectiles
  // assigned to it. Group-level projectile matches without a sub-skill owner
  // form a trailing action with no sub-skill.
  function activeSkillActions(group) {
    const damageValidated = STATE.index?.skillDamageEvidence?.status === "validated";
    const catalog = damageValidated ? STATE.index?.skillDamageUnits || {} : {};
    const skills = group.skills?.length
      ? group.skills
      : (group.actionSkillIds || []).map((id) => ({ id: String(id || "") })).filter((skill) => skill.id);
    const siblingSkillIds = skills.map((skill) => skill?.id).filter(Boolean);
    const assigned = new Set();
    const actions = skills.map((skill) => {
      const projectiles = [];
      for (const row of projectilesForSkill(skill, siblingSkillIds)) {
        const id = String(row.projectile?.id || "");
        if (!id || assigned.has(id)) continue;
        assigned.add(id);
        projectiles.push(row);
      }
      const record = catalog[skill?.id];
      const units = record?.status === "exact" ? record.units || [] : [];
      const damageMissing = damageValidated && !!skill?.id && record?.status !== "exact";
      return { skill, units, projectiles, damageMissing };
    });
    // A projectile matched only by the group's family identifier has no
    // sub-skill in this group's skill list; name its row after the
    // projectile's own action token and mark the ownership as inferred.
    const inferred = new Map();
    for (const row of projectilesForSkillGroupUnassigned(group, assigned)) {
      const token = String(row.projectile?.id || "").replace(/^(?:data_)?projectile_/, "").replace(/^chr_\d+_[^_]+_/, "");
      if (!inferred.has(token)) inferred.set(token, { skill: null, label: token, inferred: true, units: [], projectiles: [], damageMissing: false });
      inferred.get(token).projectiles.push(row);
    }
    actions.push(...inferred.values());
    return actions;
  }

  function renderActionDamage(action, level) {
    const values = new Map((level?.blackboard || []).filter((item) => item?.key).map((item) => [item.key, item.value]));
    const lines = new Map();
    for (const unit of action.units) {
      const keys = skillDamageUnitKeys(unit);
      // Translate only published enum names; unknown names remain inspectable.
      const damageName = (name) => name && text(`damage${name}`) !== `damage${name}` ? text(`damage${name}`) : name;
      const kind = [damageName(unit.damageType?.name), damageName(unit.damageAttributeType?.name)].filter(Boolean).join(" ") || text("skillDamageUnit");
      const amounts = keys.length
        ? keys.map((key) => `${key} ${values.has(key) ? formatValue(values.get(key)) : `(${text("skillDamageKeyMissing")})`}`)
        : [Number(unit.atkScale?.value) ? formatValue(unit.atkScale.value) : ""].filter(Boolean);
      const atkScaleCalculation = unit.atkCalculation?.type === "Beyond.Gameplay.Core.AtkScaleCalculation";
      const breakingAttackCalculation = unit.atkCalculation?.type === "Beyond.Gameplay.Core.BreakingAttackCalculation";
      const normalRoute = STATE.index?.skillDamageRouteEvidence?.status === "validated"
        && unit.takeAtkSnapshot === false
        && unit.damageAttributeType?.name === "Hp";
      const formula = normalRoute && unit.simpleCalculation === true
        ? ["skillSimpleDamageFormula", "skillSimpleDamageFormulaBoundary"]
        : normalRoute && unit.simpleCalculation === false
          && atkScaleCalculation && STATE.index?.skillDamageAtkScaleEvidence?.status === "validated"
          ? ["skillAtkScaleFormula", "skillAtkScaleFormulaBoundary"]
          : normalRoute && unit.simpleCalculation === false
            && breakingAttackCalculation && STATE.index?.skillDamageBreakingAttackEvidence?.status === "validated"
            ? ["skillBreakingAttackFormula", "skillBreakingAttackFormulaBoundary"] : null;
      const poiseCalculation = unit.poiseCalculation;
      const poiseFormula = poiseCalculation?.type === "Beyond.Gameplay.Core.DefiniteValueCalculation"
        && STATE.index?.skillDamagePoiseRouteEvidence?.status === "validated"
        && STATE.index?.skillDamageDefiniteValueEvidence?.status === "validated"
        ? poiseCalculation.scalars?.applyScale === false
          ? ["skillPoiseDefiniteValueFormula", "skillPoiseDefiniteValueFormulaBoundary"]
          : poiseCalculation.scalars?.applyScale === true
            ? ["skillPoiseDefiniteValueScaledFormula", "skillPoiseDefiniteValueFormulaBoundary"]
            : null
        : null;
      const evaluator = [
        formula ? ["skillAtkScaleFormulaLabel", ...formula] : null,
        poiseFormula ? ["skillPoiseFormulaLabel", ...poiseFormula] : null,
      ].filter(Boolean)
        .map(([labelKey, expressionKey, boundaryKey]) =>
          `<small class="muted" title="${escapeHtml(text(boundaryKey))}">${escapeHtml(`${text(labelKey)}: ${text(expressionKey)}`)}</small>`)
        .join("<br>");
      const label = `<b>${escapeHtml(kind)}</b>${amounts.length ? ` ${escapeHtml(amounts.join(" · "))}` : ""}${STATE.showDebug && evaluator ? `<br>${evaluator}` : ""}`;
      lines.set(label, (lines.get(label) || 0) + 1);
    }
    const body = [...lines].map(([label, count]) => `<div>${label}${count > 1 ? ` <small class="gameplay-inline-count">${count} ${escapeHtml(text("configRecords"))}</small>` : ""}</div>`).join("");
    if (body) return body;
    return action.damageMissing ? `<span class="muted">${escapeHtml(text("skillDamageFileUnavailable"))}</span>` : "";
  }

  function renderActionOtherValues(action, level) {
    const used = new Set(action.units.flatMap(skillDamageUnitKeys));
    return (level?.blackboard || [])
      .filter((item) => item?.key && !used.has(item.key))
      .map((item) => `<span class="gameplay-action-value"><b>${escapeHtml(item.key)}</b> ${escapeHtml(formatValue(item.value))}</span>`)
      .join("");
  }

  function renderActionProjectiles(action) {
    return action.projectiles.map((match) => {
      const projectile = match?.projectile || match;
      const lifetime = projectile?.lifetime || {};
      const speed = projectileScalarText((projectile?.movement?.modes || [])[0]?.speed);
      const facts = [
        speed ? `${text("projectileSpeed")} ${speed}` : "",
        projectileScalarText(lifetime.finishDistance) ? `${text("projectileDistanceShort")} ${projectileScalarText(lifetime.finishDistance)}` : "",
        projectileScalarText(lifetime.finishDuration) ? `${text("projectileLifetimeShort")} ${projectileScalarText(lifetime.finishDuration)}` : "",
        projectileHitLimitText(projectile?.targeting?.maxHitCount) ? `${text("projectileHitsShort")} ${projectileHitLimitText(projectile.targeting.maxHitCount)}` : "",
      ].filter(Boolean).join(" · ");
      const partial = projectile?.confidence?.byteComplete ? "" : ` <span class="gameplay-projectile-status">${escapeHtml(text("projectilePartial"))}</span>`;
      return `<div><b>${escapeHtml(projectileFriendlyName(projectile))}</b>${partial}${facts ? ` <small>${escapeHtml(facts)}</small>` : ""}</div>`;
    }).join("");
  }

  function renderActiveSkillActionTable(actions, levelValue) {
    const rows = [];
    for (const action of actions) {
      const level = action.skill ? levelForSkill(action.skill, levelValue) : null;
      const damage = renderActionDamage(action, level);
      const other = renderActionOtherValues(action, level);
      const projectiles = renderActionProjectiles(action);
      if (!damage && !other && !projectiles) continue;
      const name = action.skill
        ? `<code title="${escapeHtml(action.skill.id)}">${escapeHtml(String(action.skill.id).replace(/^chr_\d+_[^_]+_/, ""))}</code>`
        : `<code>${escapeHtml(action.label || "-")}</code> <span class="gameplay-status-badge is-partial" title="${escapeHtml(text("skillActionInferredNote"))}">${escapeHtml(text("skillActionInferred"))}</span>`;
      rows.push(`<tr><td class="gameplay-skill-unit">${name}</td><td>${damage || "-"}</td><td>${other || "-"}</td><td>${projectiles || "-"}</td></tr>`);
      if (STATE.showDebug && (action.units.length || action.projectiles.length)) {
        const facts = [
          ...action.units.map((unit, index) => `<span><b>${escapeHtml(text("skillDamageUnit"))} ${index + 1}</b> <code>${escapeHtml(skillDamageUnitDebugText(unit))}</code></span>`),
          ...action.projectiles.map((match) => renderProjectileDebugFacts(match)),
        ].join("");
        rows.push(`<tr class="gameplay-projectile-technical"><td colspan="4">${facts}</td></tr>`);
      }
    }
    if (!rows.length) return "";
    const head = `<tr><th>${escapeHtml(text("skillAction"))}</th><th>${escapeHtml(text("skillDamage"))}${STATE.index?.skillDamageEvidence?.status === "validated" ? renderEvidenceBadge("recoveryExact", "skillDamageBoundary") : ""}</th><th>${escapeHtml(text("skillOtherValues"))}</th><th>${escapeHtml(text("projectiles"))}</th></tr>`;
    return `<p class="gameplay-evidence-note muted">${escapeHtml(text("skillParametersNote"))}</p><div class="gameplay-table-scroll"><table class="gameplay-skill-table gameplay-action-table">${head}${rows.join("")}</table></div>`;
  }

  function renderSkillDamageAvailability() {
    const evidence = STATE.index?.skillDamageEvidence || {};
    if (evidence.status === "validated") return "";
    return `<p class="muted">${escapeHtml(text("skillDamageUnavailable"))}</p>`;
  }

  // Evidence notes shared by every skill card, stated once above them.
  function renderCharacterSkillNotes(character) {
    const damage = STATE.index?.skillDamageEvidence?.status === "validated" ? text("skillDamageBoundary") : "";
    const damageCatalog = STATE.index?.skillDamageUnits || {};
    const routeValidated = STATE.index?.skillDamageRouteEvidence?.status === "validated";
    const hasDamageUnits = (character?.skillGroups || []).some((group) =>
      (group.skills || []).some((skill) => (damageCatalog[skill?.id]?.units || []).length));
    const routeUnavailable = hasDamageUnits && !routeValidated
      ? text("skillDamageRouteUnavailable") : "";
    const hasAtkScaleCalculation = (character?.skillGroups || []).some((group) =>
      (group.skills || []).some((skill) =>
        (damageCatalog[skill?.id]?.units || []).some((unit) =>
          unit.simpleCalculation === false && unit.takeAtkSnapshot === false
          && unit.atkCalculation?.type === "Beyond.Gameplay.Core.AtkScaleCalculation")));
    const atkScaleUnavailable = routeValidated && hasAtkScaleCalculation
      && STATE.index?.skillDamageAtkScaleEvidence?.status !== "validated"
      ? text("skillAtkScaleFormulaUnavailable") : "";
    const hasBreakingAttackCalculation = (character?.skillGroups || []).some((group) =>
      (group.skills || []).some((skill) =>
        (damageCatalog[skill?.id]?.units || []).some((unit) =>
          unit.simpleCalculation === false && unit.takeAtkSnapshot === false
          && unit.atkCalculation?.type === "Beyond.Gameplay.Core.BreakingAttackCalculation")));
    const breakingAttackUnavailable = routeValidated && hasBreakingAttackCalculation
      && STATE.index?.skillDamageBreakingAttackEvidence?.status !== "validated"
      ? text("skillBreakingAttackFormulaUnavailable") : "";
    const hasPoiseDefiniteValue = (character?.skillGroups || []).some((group) =>
      (group.skills || []).some((skill) =>
        (damageCatalog[skill?.id]?.units || []).some((unit) =>
          unit.poiseCalculation?.type === "Beyond.Gameplay.Core.DefiniteValueCalculation")));
    const poiseFormulaUnavailable = hasPoiseDefiniteValue
      && (STATE.index?.skillDamagePoiseRouteEvidence?.status !== "validated"
        || STATE.index?.skillDamageDefiniteValueEvidence?.status !== "validated")
      ? text("skillPoiseFormulaUnavailable") : "";
    const effectsNamed = STATE.integration.projectiles?.effectConfigEnumEvidence?.status === "validated";
    const notes = [
      text("skillConfigNote"),
      STATE.showDebug ? text("projectileCoverageNote") : "",
      STATE.showDebug ? damage : "",
      routeUnavailable,
      atkScaleUnavailable,
      breakingAttackUnavailable,
      poiseFormulaUnavailable,
      // Effect setup only appears in the debug rows.
      STATE.showDebug ? [text("projectileEffectStoredNote"), effectsNamed ? "" : text("projectileEffectEnumUnavailable")].filter(Boolean).join(" ") : "",
    ].filter(Boolean);
    return `${renderSkillDamageAvailability()}<ul class="gameplay-skill-notes">${notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}</ul>`;
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
    const skillNames = characterSkillNames(entry);
    const potentialRows = (entry.potentials && entry.potentials.levels || []).map((row) => {
      const coordinate = sourceCoordinate(row.source);
      const meta = [
        STATE.showDebug ? row.potentialEffectId : "",
        row.level ? `${text("level")} ${formatValue(row.level)}` : "",
        STATE.showDebug && coordinate ? `${text("dataCoordinate")}: ${coordinate}` : "",
      ].filter(Boolean).join(" / ");
      const required = renderRequiredItems(row.requiredItem || []);
      const description = renderTemplateDescription(row.descriptionTemplate, descriptionValueMap(row.blackboard), row.description);
      const values = Array.isArray(row.effects)
        ? renderTalentEffects(row, description.used, skillNames)
        : renderUnusedBlackboard(row.blackboard || [], description.used);
      const alt = row.name || entry.title || entry.id;
      const visiblePictures = filterEndministratorVariant(row.pictures, entry, (picture) => picture?.id);
      const pictures = renderPotentialPictures(visiblePictures, alt);
      const topicImages = renderGameplayTokenImages([row.unlockCardTopicItem].filter(Boolean), alt, "gameplay-potential-assets");
      return `<div class="gameplay-talent-level">
        <div class="gameplay-talent-level-title">${escapeHtml(row.name || `${text("potential")} ${formatValue(row.level === undefined || row.level === null ? "" : row.level)}`)}</div>
        ${meta ? `<div class="gameplay-skill-meta">${escapeHtml(meta)}</div>` : ""}
        ${description.html}
        ${values ? `<div class="gameplay-subheading">${escapeHtml(text("configurationDetails"))}</div>${values}` : ""}
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

  function renderGameplayAssetStrip(entry, assetRefs) {
    const key = `${entry?.kind || ""}:${entry?.id || ""}`;
    const refs = assetRefs || STATE.integration.assets?.entries?.[key];
    if (!refs) return "";
    // The sidecar ranks character portraits by semantic category and image
    // size: complete illustrations/poses first, then tighter crops. Keep the
    // sidecar order so the crop/pose progression stays stable for every
    // character instead of being re-sorted by the browser. The Administrator
    // sidecar carries both concrete portrait identities; only the persisted
    // active gender variant belongs in the visible strip.
    const images = filterEndministratorVariant(refs.images, entry, (item) => item?.rel);
    const models = filterEndministratorVariant(refs.models, entry, (item) => item?.rel);
    const imageCards = images.map((asset) => {
      const fileName = asset.rel.split(/[\\/]/).pop();
      const preview = renderGameplayImageButton(asset, {
        className: "gameplay-asset-image-preview",
        alt: fileName,
        imageId: asset.rel,
        imageName: fileName,
      });
      return `<div class="gameplay-character-asset-thumb"><figure>${preview}<figcaption>${escapeHtml(fileName)}</figcaption></figure></div>`;
    }).join("");
    const modelLink = (entry.kind === "character" ? models.slice(0, 1) : models).map((model) =>
      `<a class="gameplay-character-asset-model" href="${escapeHtml(gameplayAssetPageHref(model.rel))}" title="${escapeHtml(text("openAsset"))}"><span>${escapeHtml(text(model.temporaryAssociation ? "assetModelsTemporary" : model.association === "factory-render-config-mesh-pathid" && model.evidenceBoundary === "conditional" ? "assetModelCandidates" : "assetModels"))}</span><code>${escapeHtml(model.rel)}</code></a>`
    ).join("");
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

  function projectileEffectEnumText(field, value) {
    const numeric = projectileEnumText(value);
    if (!numeric) return "";
    const dataset = STATE.integration.projectiles || {};
    const name = dataset.effectConfigEnumEvidence?.status === "validated"
      ? dataset.effectConfigEnums?.[field]?.[String(value)]
      : "";
    return name ? `${name} (${numeric})` : numeric;
  }

  function projectileEffectRows(projectile) {
    const effects = projectile?.effects || {};
    const rows = Object.entries(effects.lists || {}).flatMap(([slot, values]) =>
      (Array.isArray(values) ? values : [])
        .filter((effect) => effect && effect.effectName)
        .map((effect) => ({ slot, effect })),
    );
    if (effects.showAlertEffect && effects.alert?.effectName) {
      rows.push({ slot: "alert", effect: effects.alert });
    }
    return rows;
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
      const candidates = row.audio.map((audio, index) => `<div class="gameplay-projectile-audio-candidate">${lazyAudioButton(audio.src)}<small>${escapeHtml(`${text("projectileAudioCandidate")} ${index + 1} · ${audio.mediaId || "-"}`)}</small></div>`).join("");
      return `<div class="gameplay-projectile-audio-phase"><header><strong>${escapeHtml(phaseLabel)}</strong><span>${escapeHtml(row.audio.length ? `${row.audio.length} ${text("projectilePlayableCandidates")}` : text("projectileSoundUnlinked"))}</span></header>${candidates || `<p>${escapeHtml(text("projectileSoundUnlinkedNote"))}</p>`}</div>`;
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

  function renderGameplaySoundCandidateItem(candidate, index) {
    const evidence = gameplaySoundMediaEvidence(candidate);
    const visibleMeta = [
      `${text("soundPossibleFile")} ${index + 1}`,
      evidence.roots.length ? `${evidence.roots.length} ${text("soundPlayBranches")}` : "",
      ...evidence.relations,
      Number(candidate.contentEquivalentCount || 0) > 1 ? `${text("soundEquivalentContent")} ×${candidate.contentEquivalentCount}` : "",
    ].filter(Boolean).join(" · ");
    // The player already names the file; the evidence line is debug-only.
    const debugMeta = STATE.showDebug
      ? `<small>${escapeHtml(visibleMeta)}</small><code>${escapeHtml([candidate.mediaId ? `media ${candidate.mediaId}` : "", evidence.soundObjects ? `${evidence.soundObjects} Sound objects` : ""].filter(Boolean).join(" · "))}</code>`
      : "";
    return `<div class="gameplay-projectile-audio-candidate gameplay-sfx-possible-file">${lazyAudioButton(candidate.src)}${debugMeta}</div>`;
  }

  const GAMEPLAY_SOUND_POOL_LABELS = { random: "soundPoolRandom", sequence: "soundPoolSequence", switch: "soundPoolSwitch" };

  // Drop leaves without a playable candidate and collapse containers that no
  // longer choose or layer anything. Play roots and actor-mixer groups merge
  // into their parent; a Wwise layer stays its own block unless nested in one.
  function gameplaySoundNodeContentKey(node) {
    if (node.kind === "sound") return `sound:${[...node.mediaIds].map(String).sort().join(",")}`;
    return `${node.kind}(${(node.children || []).map(gameplaySoundNodeContentKey).sort().join("|")})`;
  }

  function simplifyGameplaySoundNode(node, byMedia) {
    if (!node) return null;
    if (node.kind === "sound") {
      const mediaIds = (node.mediaIds || []).filter((id) => byMedia.has(String(id)));
      return mediaIds.length ? { ...node, mediaIds } : null;
    }
    const pool = Boolean(GAMEPLAY_SOUND_POOL_LABELS[node.kind]);
    const children = [];
    (node.children || []).forEach((child) => {
      const simple = simplifyGameplaySoundNode(child, byMedia);
      if (!simple) return;
      const merge = simple.kind === "play" || simple.kind === "group" || (simple.kind === "layer" && node.kind === "layer");
      if (!pool && merge) children.push(...simple.children);
      else children.push(simple);
    });
    // Two Play actions can reach the same container, two containers can hold
    // the same files, and two switch states can select identical branches;
    // show that content once (a pool left with one alternative is dropped).
    {
      const seen = new Set();
      const unique = children.filter((child) => {
        const key = gameplaySoundNodeContentKey(child);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      children.splice(0, children.length, ...unique);
    }
    if (!children.length) return null;
    if (children.length === 1 && (pool || children[0].kind !== "sound" || (children[0].mediaIds || []).length === 1)) return children[0];
    return { ...node, children };
  }

  function renderGameplaySoundNode(node, byMedia, used, inColumn = false, headless = false) {
    if (node.kind === "sound") {
      return node.mediaIds.map((id) => {
        const entry = byMedia.get(String(id));
        used.add(entry.candidate);
        return renderGameplaySoundCandidateItem(entry.candidate, entry.index);
      }).join("");
    }
    const debug = STATE.showDebug ? ` <code>${escapeHtml(`${node.kind} ${node.id}`)}</code>` : "";
    const poolLabel = GAMEPLAY_SOUND_POOL_LABELS[node.kind];
    if (poolLabel) {
      const columns = node.children.map((child) => `<div class="gameplay-sfx-pool-column">${renderGameplaySoundNode(child, byMedia, used, true)}</div>`).join("");
      if (headless) return `<div class="gameplay-sfx-pool-columns" data-kind="${escapeHtml(node.kind)}">${columns}</div>`;
      return `<div class="gameplay-sfx-pool" data-kind="${escapeHtml(node.kind)}"><div class="gameplay-sfx-pool-head">${escapeHtml(text(poolLabel))}${debug}</div><div class="gameplay-sfx-pool-columns">${columns}</div></div>`;
    }
    // Children of a non-pool node sound together: one row each. Groups come
    // first, larger (more files) first, then single files.
    const children = node.children.length > 1
      ? node.children
        .map((child, order) => ({ child, order, size: child.kind === "sound" ? 0 : gameplaySoundNodeFileCount(child) }))
        .sort((a, b) => b.size - a.size || a.order - b.order)
        .map((entry) => entry.child)
      : node.children;
    const body = children.length > 1
      ? children.map((child) => `<div class="gameplay-sfx-row">${renderGameplaySoundNode(child, byMedia, used, false)}</div>`).join("")
      : children.map((child) => renderGameplaySoundNode(child, byMedia, used, false)).join("");
    // A real Wwise layer inside a pool column keeps its label: its stacked
    // children all sound when that branch is chosen.
    if (headless || (inColumn && node.kind !== "layer")) return body;
    const label = gameplaySoundNodeLabel(node);
    return `<div class="gameplay-sfx-layer" data-kind="${escapeHtml(node.kind)}"><div class="gameplay-sfx-layer-head">${escapeHtml(text(label))}${debug}</div>${body}</div>`;
  }

  function gameplaySoundNodeFileCount(node) {
    if (node.kind === "sound") return node.mediaIds.length;
    return (node.children || []).reduce((sum, child) => sum + gameplaySoundNodeFileCount(child), 0);
  }

  // The synthetic event root holds several Play actions of one Event; real
  // Wwise layer containers keep their own label.
  function gameplaySoundNodeLabel(node) {
    return GAMEPLAY_SOUND_POOL_LABELS[node.kind] || (node.kind === "play" ? "soundEventActions" : "soundLayerTogether");
  }

  function gameplaySoundTree(event, audio) {
    const roots = Array.isArray(event?.selectionTree) ? event.selectionTree : [];
    if (!roots.length) return null;
    const byMedia = new Map();
    audio.forEach((candidate, index) => {
      if (candidate.mediaId != null && !byMedia.has(String(candidate.mediaId))) byMedia.set(String(candidate.mediaId), { candidate, index });
    });
    const tree = simplifyGameplaySoundNode({ kind: "play", id: "event", children: roots }, byMedia);
    return tree ? { tree, byMedia } : null;
  }

  // Compact playback plan for the simulate button: a leaf is a file src;
  // {k, c} is "a" (all children sound together), "r" (random one),
  // "q" (sequence: next one per trigger) or "s" (switch: the runtime state is
  // unknown, so a random state). A sound object with several media picks one.
  function gameplaySoundSimNode(node, byMedia) {
    if (node.kind === "sound") {
      const srcs = node.mediaIds.map((id) => byMedia.get(String(id))?.candidate?.src).filter(Boolean);
      return srcs.length === 1 ? srcs[0] : { k: "r", c: srcs };
    }
    const k = { random: "r", sequence: "q", switch: "s" }[node.kind] || "a";
    return { k, c: (node.children || []).map((child) => gameplaySoundSimNode(child, byMedia)) };
  }

  function gameplaySoundSimPlan(event, audio) {
    const built = gameplaySoundTree(event, audio);
    if (built) return gameplaySoundSimNode(built.tree, built.byMedia);
    const srcs = audio.map((candidate) => candidate.src).filter(Boolean);
    return srcs.length ? { k: "r", c: srcs } : null;
  }

  function renderGameplaySoundSimButton(event, audio) {
    const plan = gameplaySoundSimPlan(event, audio);
    if (!plan) return "";
    // Without a published selectionTree the structure is unknown; say so.
    const hint = gameplaySoundTree(event, audio) ? "soundSimulateHint" : "soundSimulateFlatHint";
    return `<button type="button" class="gameplay-sfx-simulate" data-gameplay-sfx-sim="${escapeHtml(JSON.stringify(plan))}" title="${escapeHtml(text(hint))}"><span aria-hidden="true">▶</span>${escapeHtml(text("soundSimulate"))}</button>`;
  }

  // Resolve one trigger of a plan into the files that sound. Sequence steps
  // are kept per button and node path, so repeated clicks advance like the game.
  function resolveGameplaySoundSim(plan, steps, path = "0") {
    if (typeof plan === "string") return [plan];
    const children = plan.c || [];
    if (!children.length) return [];
    if (plan.k === "a") return children.flatMap((child, index) => resolveGameplaySoundSim(child, steps, `${path}.${index}`));
    let index = Math.floor(Math.random() * children.length);
    if (plan.k === "q") {
      index = (steps.get(path) || 0) % children.length;
      steps.set(path, index + 1);
    }
    return resolveGameplaySoundSim(children[index], steps, `${path}.${index}`);
  }

  const GAMEPLAY_SFX_SIM_STATE = new WeakMap();

  function stopGameplaySoundSim(button) {
    const state = GAMEPLAY_SFX_SIM_STATE.get(button);
    (state?.players || []).forEach((player) => player.pause());
    if (state) state.players = [];
    button.classList.remove("is-playing");
    button.closest(".gameplay-sfx-event")?.querySelectorAll(".is-simulated").forEach((node) => node.classList.remove("is-simulated"));
  }

  function playGameplaySoundSim(button) {
    const state = GAMEPLAY_SFX_SIM_STATE.get(button) || { steps: new Map(), players: [] };
    GAMEPLAY_SFX_SIM_STATE.set(button, state);
    const wasPlaying = button.classList.contains("is-playing");
    stopGameplaySoundSim(button);
    if (wasPlaying) return;
    let plan;
    try { plan = JSON.parse(button.dataset.gameplaySfxSim); } catch { return; }
    const srcs = resolveGameplaySoundSim(plan, state.steps);
    if (!srcs.length) return;
    const chosen = new Set(srcs);
    button.closest(".gameplay-sfx-event")?.querySelectorAll("[data-gameplay-audio-src], [data-gameplay-sfx-file]").forEach((node) => {
      const src = node.dataset.gameplayAudioSrc || node.dataset.gameplaySfxFile;
      if (chosen.has(src)) node.closest(".gameplay-sfx-possible-file")?.classList.add("is-simulated");
    });
    button.classList.add("is-playing");
    let pending = srcs.length;
    const done = () => { if (--pending <= 0 && state.players.length) stopGameplaySoundSim(button); };
    state.players = srcs.map((src) => {
      const player = new Audio(src);
      player.addEventListener("ended", done);
      player.addEventListener("error", done);
      player.play().catch(done);
      return player;
    });
  }

  // Label of the event's top selection node, shown on the event header so the
  // top node needs no box of its own; "" when the top is a single file.
  function gameplaySoundTreeHead(event, audio) {
    const tree = gameplaySoundTree(event, audio)?.tree;
    return tree && tree.kind !== "sound" ? text(gameplaySoundNodeLabel(tree)) : "";
  }

  // Authored Wwise structure from the Audio page's selectionTree: layers sound
  // together, random/sequence/switch pools show one column per alternative.
  // The top node renders headless (its label is on the event header).
  // Returns "" when the event has no usable tree (older Audio publication).
  function renderGameplaySoundSelectionTree(event, audio) {
    const built = gameplaySoundTree(event, audio);
    if (!built) return "";
    const { tree, byMedia } = built;
    const used = new Set();
    const html = renderGameplaySoundNode(tree, byMedia, used, false, true);
    const rest = audio.filter((candidate) => !used.has(candidate));
    const restHtml = rest.length
      ? `<div class="gameplay-sfx-layer gameplay-sfx-ungrouped"><div class="gameplay-sfx-layer-head">${escapeHtml(text("soundTreeUngrouped"))}</div>${rest.map((candidate) => renderGameplaySoundCandidateItem(candidate, audio.indexOf(candidate))).join("")}</div>`
      : "";
    return `<div class="gameplay-sfx-possible-files gameplay-sfx-tree">${html}${restHtml}</div>`;
  }

  function renderGameplaySoundCandidates(event, audio) {
    if (!audio.length) return "";
    return renderGameplaySoundSelectionTree(event, audio)
      || `<div class="gameplay-sfx-possible-files">${audio.map(renderGameplaySoundCandidateItem).join("")}</div>`;
  }

  // Variant events (e.g. male/female Endministrator) often play the same
  // files; keep the first one and name the rest on its header.
  function dedupeGameplaySoundEvents(events) {
    const aliases = new Map();
    const firstByFiles = new Map();
    const rows = (events || []).filter((event) => {
      const files = [...new Set((event.audio || []).filter((candidate) => candidate?.src).map((candidate) => candidate.mediaId ?? candidate.src))].sort().join(",");
      if (!files) return true;
      const first = firstByFiles.get(files);
      if (!first) {
        firstByFiles.set(files, event);
        return true;
      }
      if (!aliases.has(first)) aliases.set(first, []);
      aliases.get(first).push(event.id);
      return false;
    });
    return { rows, aliases };
  }

  function renderGameplaySoundEvents(events, options = {}) {
    const { rows: eventRows, aliases } = options.aliases
      ? { rows: events || [], aliases: options.aliases }
      : dedupeGameplaySoundEvents(events);
    return eventRows.map((event) => {
      const audio = (event.audio || []).filter((candidate) => candidate?.src);
      const sameFiles = (aliases.get(event) || []).map((id) => gameplaySoundEventName(id) || id);
      const aliasHtml = sameFiles.length ? `<small class="gameplay-sfx-event-aliases">${escapeHtml(`${text("soundSameFilesAs")} ${sameFiles.join(" / ")}`)}</small>` : "";
      const evidenceIds = gameplaySoundSkillIds(event);
      const clips = event.sourceAnimationClips || [];
      const trigger = (event.evidence || []).map((row) => row?.triggerKey).find(Boolean) || "";
      const technical = STATE.showDebug ? `<div class="gameplay-sfx-technical"><b>${escapeHtml(text("projectileTechnical"))}</b><code class="gameplay-sfx-event-id">${escapeHtml(event.id || "")}</code>${evidenceIds.length ? `<code>${escapeHtml(evidenceIds.join(" / "))}</code>` : ""}${clips.length ? `<code>${escapeHtml(clips.join(" / "))}</code>` : ""}${trigger ? `<code>${escapeHtml(trigger)}</code>` : ""}<a data-gameplay-audio-event href="${escapeHtml(gameplayAudioEventHref(event.id))}">${escapeHtml(text("openInAudio"))}</a></div>` : "";
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
      const eventName = gameplaySoundEventName(event.id) || text("soundEvent");
      // Counts and evidence chips are debug detail; the normal view keeps the
      // event name, its action when that differs, and the playable files.
      const scope = STATE.showDebug
        ? [actionLabel, eventScope].filter(Boolean).join(" · ")
        : [actionLabel && actionLabel !== eventName ? actionLabel : "", gameplaySoundTreeHead(event, audio)].filter(Boolean).join(" · ");
      // Reached only through a skill's BuffData chain: name the buff that
      // holds the PlaySound action so reused audio is visibly indirect.
      const evidenceRows = (event.evidence || []).filter(Boolean);
      const viaBuffIds = evidenceRows.length && evidenceRows.every((row) => row.kind === "skillBuffData")
        ? [...new Set(evidenceRows.flatMap((row) => row.buffIds || []))]
        : [];
      const viaBuffHtml = viaBuffIds.length ? `<small class="gameplay-sfx-event-aliases">${escapeHtml(`${text("soundViaBuff")} ${viaBuffIds.join(" / ")}`)}</small>` : "";
      const boundary = sharedAnimation ? `<p class="gameplay-enemy-sfx-note">${escapeHtml(text("soundSharedRuntimeGraphNote"))}</p>` : "";
      const evidence = STATE.showDebug ? renderGameplaySoundEvidence(event, audio) : "";
      // Every event starts folded; its body is built on first unfold.
      const body = () => `${boundary}${evidence}${technical}${renderGameplaySoundCandidates(event, audio)}`;
      return `<details class="gameplay-sfx-event" data-gameplay-deferred="${deferGameplayBody(body)}"><summary class="gameplay-sfx-event-summary"><strong>${escapeHtml(eventName)}</strong>${scope ? `<span>${escapeHtml(scope)}</span>` : ""}${viaBuffHtml}${aliasHtml}${renderGameplaySoundSimButton(event, audio)}</summary></details>`;
    }).join("");
  }

  function renderGameplaySoundActionGroups(events, options = {}) {
    const groups = new Map();
    const { rows, aliases } = dedupeGameplaySoundEvents(events);
    for (const event of rows) {
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
      .map((group) => renderGameplaySoundEvents(group.events, { showActionLabel: true, aliases }))
      .join("");
  }

  function renderGameplaySoundEventList(events, options = {}) {
    return `<div class="gameplay-sfx-event-list">${renderGameplaySoundActionGroups(events, options)}</div>`;
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

  // options.shown (a Set of audio srcs) hides files an earlier section already
  // listed and records the ones this group adds, so each file appears once.
  function withoutShownGameplayAudio(events, shown) {
    if (!shown) return events;
    return events.flatMap((event) => {
      const audio = event.audio || [];
      if (!audio.some((candidate) => candidate?.src)) return [event];
      const fresh = audio.filter((candidate) => candidate?.src && !shown.has(candidate.src));
      return fresh.length ? [{ ...event, audio: fresh }] : [];
    });
  }

  function renderGameplaySoundGroup(events, options = {}) {
    const playableEvents = withoutShownGameplayAudio(gameplayResolvedSoundEvents(events), options.shown).filter((event) => (event.audio || []).some((candidate) => candidate?.src) || Number(event.possibleMediaCount || event.playableCandidates || 0) > 0);
    const playable = playableEvents.reduce((total, event) => total + ((event.audio || []).filter((candidate) => candidate?.src).length || Number(event.possibleMediaCount || event.playableCandidates || 0)), 0);
    if (!playable) return "";
    for (const event of playableEvents) for (const candidate of event.audio || []) if (candidate?.src) options.shown?.add(candidate.src);
    const confidence = options.confidence ? integrationConfidence(options.confidence) : "";
    const wrapper = options.inline ? "div" : "section";
    return `<${wrapper} class="gameplay-related-sfx${options.inline ? " gameplay-sfx-inline" : ""}"><header class="gameplay-related-sfx-summary"><strong>${escapeHtml(options.label || text("relatedSoundEffects"))}</strong><span>${escapeHtml(gameplaySoundCountText(playableEvents, options))}</span>${confidence}</header><p>${escapeHtml(options.note || text("soundRuntimeNote"))}</p>${renderGameplaySoundEventList(playableEvents, options)}</${wrapper}>`;
  }

  function gameplayIntegrationError(kind) {
    return STATE.integration.errors.find((error) => error?.kind === kind) || null;
  }

  function renderSoundEffectsUnavailable() {
    if (STATE.integration.status !== "ready" || !gameplayIntegrationError("soundEffects")) return "";
    return `<div class="gameplay-integration-note is-warning" role="status">${escapeHtml(text("soundEffectsUnavailable"))}</div>`;
  }

  function renderSoundEffectsLoading() {
    if (STATE.integration.soundEffectsStatus !== "loading") return "";
    return `<div class="gameplay-integration-note" role="status">${escapeHtml(text("soundEffectsLoading"))}</div>`;
  }

  function skillGroupSoundEvents(group, character) {
    const groups = STATE.integration.soundEffects?.characters?.[character?.id]?.groups || {};
    return filterEndministratorVariant(groups[group?.id]?.events, character, (event) => event?.id);
  }

  function exactSkillSoundEvents(group, character) {
    return skillGroupSoundEvents(group, character).filter(gameplaySoundHasExactSkillTrigger);
  }

  // Events owned by this skill group only through its playable-skill ID
  // prefix; shown on the skill card under an inferred badge.
  function inferredSkillSoundEvents(group, character) {
    return skillGroupSoundEvents(group, character).filter((event) => !gameplaySoundHasExactSkillTrigger(event));
  }

  // Audio srcs the skill cards already show (exact and inferred skill events
  // and projectile phases), which the trailing related-sound section skips.
  function skillShownGameplayAudio(entry) {
    const shown = new Set();
    for (const group of entry?.skillGroups || []) {
      const events = [...exactSkillSoundEvents(group, entry), ...inferredSkillSoundEvents(group, entry)];
      for (const event of gameplayResolvedSoundEvents(events)) {
        for (const candidate of event.audio || []) if (candidate?.src) shown.add(candidate.src);
      }
      for (const row of projectilesForGroup(group)) {
        for (const sound of projectileSoundRows(row.projectile)) for (const candidate of sound.audio) shown.add(candidate.src);
      }
    }
    return shown;
  }

  function renderActiveSkillSoundEffects(group, character) {
    // One set per card so an inferred file the exact group already lists is
    // not repeated; one wrapper so the level slider moves both groups.
    const shown = new Set();
    const groups = `${renderGameplaySoundGroup(exactSkillSoundEvents(group, character), {
      label: text("exactSkillSoundEffects"),
      confidence: "direct",
      note: text("soundExactSkillTriggerNote"),
      inline: true,
      shown,
    })}${renderGameplaySoundGroup(mergeGameplaySoundEvents(inferredSkillSoundEvents(group, character)), {
      label: text("inferredSkillSoundEffects"),
      confidence: "inferred",
      note: text("inferredSkillSoundEffectsNote"),
      inline: true,
      shown,
    })}`;
    return groups ? `<div class="gameplay-skill-sounds">${groups}</div>` : "";
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
    const nativeVoiceResponses = (sounds.nativeVoiceResponseEvents || []).map((event) => ({
      ...event,
      audio: event?.mediaRefs || [],
    }));
    const nativeVoiceGroup = renderGameplaySoundGroup(nativeVoiceResponses, {
      label: text("enemyNativeVoiceResponses"),
      confidence: "direct",
      note: text("enemyNativeVoiceResponsesNote"),
    });
    const responseCandidates = (sounds.enemyResponseCandidateEvents || []).map((event) => ({
      ...event,
      audio: event?.mediaRefs || [],
    }));
    const responseCandidateGroup = renderGameplaySoundGroup(responseCandidates, {
      label: text("enemyResponseCandidates"),
      confidence: "direct",
      note: text("enemyResponseCandidatesNote"),
    });
    if (!playableEvents.length) return `${nativeVoiceGroup}${responseCandidateGroup}${namespaceGroup}`;
    const confidence = integrationConfidence(
      sounds.ownershipConfidence === "inferred" || sounds.animationOwnershipConfidence === "inferred" ? "inferred" : "direct",
    );
    const notes = [text("soundRuntimeNote")];
    if ((sounds.animationEvents || []).length) notes.push(text("animationSoundNote"));
    return `${nativeVoiceGroup}${responseCandidateGroup}${namespaceGroup}<div class="gameplay-enemy-sfx-meta"><strong>${escapeHtml(gameplaySoundCountText(playableEvents))}</strong>${confidence}</div><p class="gameplay-enemy-sfx-note">${escapeHtml(notes.join(" "))}</p>${renderGameplaySoundEventList(playableEvents, { flattenGroups: true })}`;
  }

  function renderCharacterAnimationSounds(entry, shown) {
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
      shown,
      note: text("animationSoundNote"),
    })}${renderGameplaySoundGroup(sharedAnimationEvents, {
      label: text("soundSharedAnimationSystems"),
      confidence: sounds.animationOwnershipConfidence,
      note: text("soundSharedRuntimeGraphNote"),
      sharedGraph: true,
      shown,
    })}${renderGameplaySoundGroup(profileVoices, {
      label: text("combatVoice"),
      confidence: "direct",
      note: text("profileVoiceNote"),
      shown,
    })}`;
  }

  function renderCharacterSoundEffects(entry) {
    if (!STATE.integration.soundEffects) return renderSoundEffectsUnavailable();
    // Sections render in display order and share one set, so a file already
    // shown on a skill card or in an earlier section is not repeated.
    const shown = skillShownGameplayAudio(entry);
    const animationSounds = renderCharacterAnimationSounds(entry, shown);
    const namespaceOwnerId = isEndministrator(entry)
      ? ENDADMINISTRATOR_VARIANTS.find((variant) => variant.gender === currentCharacterGender())?.characterId
      : entry?.id;
    const namespaceEvents = filterEndministratorVariant(
      STATE.integration.soundEffects?.characters?.[namespaceOwnerId]?.authoredNamespaceEvents,
      entry,
      (event) => event?.id,
    );
    const nativeVoiceResponses = (
      STATE.integration.soundEffects?.characters?.[namespaceOwnerId]?.nativeVoiceResponseEvents || []
    ).map((event) => ({
      ...event,
      audio: event?.mediaRefs || [],
    }));
    const nativeVoiceGroup = renderGameplaySoundGroup(nativeVoiceResponses, {
      label: text("characterNativeVoiceResponses"),
      confidence: "direct",
      shown,
      note: text("characterNativeVoiceResponsesNote"),
    });
    const authoredNamespaces = renderGameplaySoundGroup(namespaceEvents, {
      label: text("authoredNamespaceAudio"),
      shown,
      note: text("authoredNamespaceAudioNote"),
    });
    return `${animationSounds}${nativeVoiceGroup}${authoredNamespaces}`;
  }


  // One table row per projectile; every attribute gets its own cell so a
  // skill's projectiles share one container instead of nested cards.
  function renderProjectileDebugFacts(match) {
    const projectile = match?.projectile || match;
    const lifetime = projectile?.lifetime || {};
    const collision = projectile?.collision || {};
    const targeting = projectile?.targeting || {};
    const filter = targeting.targetFilter || {};
    const movement = projectile?.movement || {};
    const modes = movement.modes || [];
    const effectNames = [...new Set(projectileEffectRows(projectile).map(({ effect }) => effect.effectName))];
    const behaviorSkills = projectileBehaviorSkillIds(projectile);
    const matchedActions = match?.matchMethod === "skill-family-identifier"
      ? []
      : (match?.matched || []).filter((value) => String(value || "").includes("_"));
    const detailFacts = [
      matchedActions.length ? [text("projectileAction"), matchedActions.join(", ")] : null,
      [text("projectileAssignment"), projectileMatchMethodText(match?.matchMethod)],
      [text("projectileMovement"), modes.map((item) => [item.key, projectileEnumText(item.moveType), projectileScalarText(item.speed), item.surroundCenterKey].filter(Boolean).join(" / ")).filter(Boolean).join("; ")],
      (movement.segments || []).length ? [text("projectileSegments"), (movement.segments || []).map((segment) => [segment.startPointKey, segment.moveModeId, segment.endPointKey, segment.skipHitAndBlockDetection ? text("projectileSkipCollision") : ""].filter(Boolean).join(" -> ")).join("; ")] : null,
      [text("projectileCollision"), [projectileEnumText(collision.shapeType), projectileScalarText(collision.radius), projectileVectorText(collision.extent)].filter(Boolean).join(" / ")],
      [text("projectileTargeting"), [projectileScalarText(targeting.maxHitCount), targeting.allowHitSameTarget ? `${text("projectileRepeatHit")} / ${formatValue(targeting.hitIntervalPerTarget)}` : text("projectileSingleHit"), projectileEnumText(targeting.collisionDetectTiming), projectileEnumText(filter.objectType), projectileTagText(filter)].filter(Boolean).join(" / ")],
      [text("projectileDetectionDelay"), [projectileScalarText(targeting.hitAndBlockDetectDelayTime), projectileScalarText(targeting.hitAndBlockDetectDelayDistance), targeting.canTraceTargetAfterReach ? text("projectileTraceAfterReach") : ""].filter(Boolean).join(" / ")],
      effectNames.length ? [text("projectileEffects"), effectNames.join(", ")] : null,
      behaviorSkills.length ? [text("projectileBehaviorSkills"), behaviorSkills.join(", ")] : null,
      [text("source"), [projectile?.source?.root, projectile?.source?.assetName, projectile?.source?.pathId].filter(Boolean).join(" / ")],
    ].filter((row) => row && row[1]);
    return `<span><b>${escapeHtml(projectileFriendlyName(projectile))}</b></span>${detailFacts.map(([label, value]) => `<span><b>${escapeHtml(label)}</b> <code>${escapeHtml(value)}</code></span>`).join("")}`;
  }

  function renderCharacterProjectileRow(match) {
    const projectile = match?.projectile || match;
    const lifetime = projectile?.lifetime || {};
    const collision = projectile?.collision || {};
    const targeting = projectile?.targeting || {};
    const filter = targeting.targetFilter || {};
    const movement = projectile?.movement || {};
    const modes = movement.modes || [];
    const effectRows = projectileEffectRows(projectile);
    const travel = [
      modes.map((item) => [item.key, projectileScalarText(item.speed) ? `${text("projectileSpeed")} ${projectileScalarText(item.speed)}` : ""].filter(Boolean).join(" · ")).filter(Boolean).join("; "),
      lifetime.finishOnReach ? text("projectileFinishOnReach") : "",
      lifetime.hitOnReach ? text("projectileHitOnReach") : "",
    ].filter(Boolean).join(" · ");
    const hit = [
      projectileFriendlyEnum(collision.shapeType),
      targeting.allowHitSameTarget ? text("projectileRepeatHit") : text("projectileSingleHit"),
      projectileFriendlyTagText(filter),
    ].filter(Boolean).join(" · ");
    const effects = effectRows.map(({ slot, effect }) => {
      const behavior = effect.behavior || {};
      const facts = [
        projectileEffectEnumText("fxType", effect.fxType),
        projectileEffectEnumText("moveType", behavior.moveType),
        projectileEffectEnumText("positionRef", behavior.positionRef),
      ].filter(Boolean).join(" · ");
      return `<div class="gameplay-projectile-effect"><b>${escapeHtml(slot)}</b> <code>${escapeHtml(effect.effectName)}</code>${facts ? ` <small>${escapeHtml(facts)}</small>` : ""}</div>`;
    }).join("");
    const complete = projectile?.confidence?.byteComplete;
    const cells = [
      `<td class="gameplay-projectile-name"><strong>${escapeHtml(projectileFriendlyName(projectile))}</strong>${complete ? "" : `<span class="gameplay-projectile-status">${escapeHtml(text("projectilePartial"))}</span>`}</td>`,
      `<td>${escapeHtml(projectileScalarText(lifetime.finishDuration) || "-")}</td>`,
      `<td>${escapeHtml(projectileScalarText(lifetime.finishDistance) || "-")}</td>`,
      `<td>${escapeHtml(projectileHitLimitText(targeting.maxHitCount) || "-")}</td>`,
      `<td>${escapeHtml(travel || "-")}</td>`,
      `<td>${escapeHtml(hit || "-")}</td>`,
      `<td>${effects || "-"}</td>`,
    ];
    const technical = STATE.showDebug
      ? `<tr class="gameplay-projectile-technical"><td colspan="${cells.length}">${renderProjectileDebugFacts(match)}</td></tr>`
      : "";
    const audio = renderProjectileAudio(projectileSoundRows(projectile));
    const audioRow = audio ? `<tr class="gameplay-projectile-audio-row"><td colspan="${cells.length}">${audio}</td></tr>` : "";
    return `<tr>${cells.join("")}</tr>${audioRow}${technical}`;
  }

  function renderProjectileTable(matches) {
    const columns = ["projectiles", "projectileLifetimeShort", "projectileDistanceShort", "projectileHitsShort", "projectileTravel", "projectileHitRule", "projectileEffectSetup"];
    const head = `<tr>${columns.map((key) => `<th>${escapeHtml(text(key))}</th>`).join("")}</tr>`;
    return `<div class="gameplay-table-scroll"><table class="gameplay-skill-table gameplay-projectile-table">${head}${matches.map(renderCharacterProjectileRow).join("")}</table></div>`;
  }

  // One active skill (a skill group - Normal Attack / Skill / Ultimate /
  // Combo) can be made of several authored sub-skills (combo hits, charged
  // variants, ...). Merge their matched projectiles into a single deduped
  // list plus whatever the group-level fallback match picks up, so the
  // right-hand column shows every projectile that belongs to this skill
  // exactly once.
  function projectilesForGroup(group) {
    return activeSkillActions(group).flatMap((action) => action.projectiles);
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
    return `<div class="gameplay-skill-part gameplay-projectile-unassigned"><div class="gameplay-skill-part-title">${escapeHtml(`${text("projectileOwnershipUnresolved")} (${unresolved.length})`)}</div><p class="muted">${escapeHtml(text("projectileOwnershipUnresolvedNote"))}</p>${renderProjectileTable(unresolved)}</div>`;
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

  // One card per skill group (Normal Attack / Skill / Ultimate / Combo):
  // header with the level slider, the description, then the selected level's
  // action table (damage, values, projectiles per sub-skill) and cost.
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
    const meta = [group.id, group.iconId ? `${text("iconId")}: ${group.iconId}` : ""].filter(Boolean).join(" / ");
    const typeKey = { "normal-attack": "skillTypeNormal", "normal-skill": "skillTypeSkill", ultimate: "skillTypeUltimate", combo: "skillTypeCombo" }[skillType];
    const typeLabel = typeKey ? text(typeKey) : group.typeLabel;
    const sound = renderActiveSkillSoundEffects(group, character);
    const levels = renderActiveSkillLevels(group, sound);
    return `<article class="gameplay-skill-block" data-level-card>
      <header class="gameplay-skill-block-head">
        ${groupIcon}
        <div class="gameplay-skill-block-title">
          <strong>${escapeHtml(group.name || group.id || "")}</strong>${typeLabel ? `<span class="gameplay-skill-type">${escapeHtml(typeLabel)}</span>` : ""}
          ${STATE.showDebug ? `<div class="gameplay-skill-meta">${escapeHtml(meta)}</div>` : ""}
        </div>
        ${levels.control}
      </header>
      ${renderActiveSkillCombatMeta(group, character)}
      ${levels.panes ? `<div class="gameplay-skill-block-levels">${levels.panes}</div>` : `${renderDescription(group.description)}${sound}`}
    </article>`;
  }

  function renderWeaponDetail(entry) {
    const facts = [
      fact(text("fileName"), entry.fileName || entry.title),
      fact(text("rarity"), entry.rarity),
      fact(text("weaponType"), entry.weaponTypeLabel || entry.weaponType),
    ].filter(Boolean);
    const skills = (entry.skills || []).map((skill) => renderSkillCard(skill, { slider: true })).join("");
    return {
      facts,
      body: [
        section(text("weaponStats"), renderStats(entry.stats, statCostIndex(entry, "weapon"), { textOnly: true })),
        section(text("weaponSkills"), skills ? `<div class="gameplay-card-grid">${skills}</div>` : ""),
        section(text("gemSources"), renderGemLinks(entry.gemSources, "gem") + `<p>${escapeHtml(text("gemPoolBoundary"))}</p>`),
      ].join(""),
    };
  }
  function renderGemLinks(rows, kind) {
    return rows?.length ? rows.map((row) => {
      const key = `${kind}:${row.id}`;
      const target = findGameplayEntry(key) || { id: row.id, kind };
      const icon = renderGameplayItemIcon(target, row.title, { static: true });
      return window.WebUI.gameplayDetail.relatedLink(row.title, { iconHtml: icon, relatedKey: key });
    }).join(" ") : `<p>${escapeHtml(text("gemNoMatch"))}</p>`;
  }

  function renderGameplayMapLink(levelId, label, title = levelId) {
    const url = new URL(location.href);
    url.searchParams.set("map", levelId);
    url.searchParams.delete("mission");
    url.hash = "map";
    return `<a class="gameplay-value-chip" href="${escapeHtml(url.href)}" title="${escapeHtml(title)}">${escapeHtml(label)}</a>`;
  }

  function renderGemDetail(entry) {
    const maps = [...new Map((entry.stages || []).filter((stage) => stage.levelId)
      .map((stage) => [stage.levelId, stage])).values()]
      .map((stage) => renderGameplayMapLink(stage.levelId, stage.location || stage.levelId)).join(" ");
    const poolLabels = ["weaponAttributeFilter", "weaponBonusFilter", "weaponPassiveFilter"];
    const pools = poolLabels.map((label, index) => {
      const terms = [...new Map((entry.termPools?.[index] || []).map((term) => [term.id, term])).values()];
      return `<div class="gameplay-talent-level gameplay-gem-term-column"><div class="gameplay-talent-level-title">${escapeHtml(text(label))}</div><div class="chips">${terms.map((term) => `<span class="gameplay-value-chip" title="${escapeHtml(term.id)}">${escapeHtml(gemTermLabel(term, index))}</span>`).join(" ") || `<span class="muted">—</span>`}</div></div>`;
    }).join("");
    return {
      facts: [fact(text("gemRegion"), entry.domain?.name), fact(text("gemLocation"), entry.location)],
      body: section(text("gemTerms"), `<div class="gameplay-talent-levels gameplay-gem-term-columns">${pools}</div><p class="gameplay-integration-note">${escapeHtml(text("gemPoolBoundary"))}</p>`)
        + section(text("gemMaps"), maps)
        + section(text("gemCompatibleWeapons"), renderGemLinks(entry.compatibleWeapons, "weapon")),
    };
  }

  function renderCharacterDetail(entry) {
    const variantEntry = endministratorVariantEntry(entry);
    const facts = [
      fact(text("rarity"), entry.rarity),
      fact(text("profession"), entry.professionLabel || entry.profession),
      fact(text("element"), entry.elementLabel || entry.element),
      fact(text("weaponType"), entry.weaponTypeLabel || entry.weaponType),
      fact(text("defaultWeapon"), entry.defaultWeaponName || entry.defaultWeaponId),
      fact(text("stat_main_attr"), entry.mainAttrType != null ? statAttrLabel({ type: entry.mainAttrType }) : ""),
      fact(text("stat_sub_attr"), entry.subAttrType != null ? statAttrLabel({ type: entry.subAttrType }) : ""),
    ].filter(Boolean);
    const skillRows = (variantEntry.skillGroups || []).map((group) => renderActiveSkillRow(group, variantEntry)).join("");
    const unresolvedProjectiles = renderUnassignedCharacterProjectiles(variantEntry);
    const talents = entry.talentGroups || [];
    const skillNames = characterSkillNames(entry);
    const talentGroups = renderTalentGroups(talents.filter((group) => group.kind !== "factory"), skillNames);
    const factoryGroups = renderTalentGroups(talents.filter((group) => group.kind === "factory"), skillNames);
    const talentCards = (entry.talents || []).map(renderTalentCard).join("");
    const characterAssets = renderGameplayAssetStrip(entry);
    const variantControl = renderEndministratorVariantControl(entry);
    return {
      facts,
      body: [
        variantControl,
        section(text("characterSkills"), skillRows || unresolvedProjectiles ? `${renderCharacterSkillNotes(variantEntry)}${skillRows ? `<div class="gameplay-skill-blocks">${skillRows}</div>` : ""}${unresolvedProjectiles}` : "", "skills"),
        section(text("combatTalents"), talentGroups || (talentCards ? `<div class="gameplay-card-grid">${talentCards}</div>` : ""), "talents"),
        section(text("factoryTalents"), factoryGroups, "factory"),
        section(text("characterPotentials"), renderCharacterPotentials(entry), "potentials"),
        section(text("growthMaterials"), renderCharacterBreakthroughs(entry), "growth"),
        section(text("characterAssets"), characterAssets, "assets"),
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
          <div class="gameplay-skill-title">${escapeHtml((skill.name && skill.name !== skill.id ? skill.name : suit.name) || text("equipmentSuit"))}</div>
          <div class="gameplay-skill-meta">${escapeHtml(meta)}</div>
        </header>
        ${renderLevelRows(skill, { slider: true })}
      </article>`;
    }).join("");
    return effects ? `<div class="gameplay-card-grid">${effects}</div>` : "";
  }

  function renderEquipmentPropertyStats(stats) {
    const curves = (stats && stats.propertyCurves || []).filter((curve) => curve && (curve.rows || []).length);
    if (!curves.length) return renderStats(stats, undefined, { textOnly: true });
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
          <div class="gameplay-level-panes">${rows.map((row, index) => renderStatPane(row, index === 0, undefined, true)).join("")}</div>
        </div>`
        : renderStatPane(rows[0], true, undefined, true);
      return window.WebUI.gameplayDetail.propertyCard({ title: statAttrLabel(curve), bodyHtml: body,
        className: `gameplay-stat-card${curve.key === "main_attr" ? " gameplay-equipment-main" : curve.key === "sub_attr" ? " gameplay-equipment-sub" : ""}`, metaHtml: STATE.showDebug ? `<div class="gameplay-skill-meta">${escapeHtml(stats.source || "")}</div>` : "" });
    }).filter(Boolean);
    return window.WebUI.gameplayDetail.propertyGrid(cards);
  }
  function renderEquipmentDetail(entry) {
    const facts = [
      fact(text("rarity"), entry.rarity),
      fact(text("partType"), entry.showingTypeLabel || entry.partTypeLabel || entry.partType),
      fact(text("minWearLevel"), entry.minWearLv),
      fact(text("domain"), entry.domainName || (entry.domain && entry.domain.name) || entry.domainId),
      fact(text("suit"), entry.suit && (entry.suit.name || entry.suit.id)),
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
    const rows = (entry.abilities || []).map((ability, index) => {
      if (!ability) return "";
      const name = ability.name && ability.name !== ability.id ? ability.name : `${text("enemyTrait")} ${index + 1}`;
      return window.WebUI.gameplayDetail.propertyCard({
        title: name,
        metaHtml: STATE.showDebug ? `<div class="gameplay-skill-meta">${escapeHtml(ability.id || "")}</div>` : "",
        bodyHtml: renderDescription(ability.description),
      });
    }).filter(Boolean);
    if (!rows.length) return "";
    const mechanics = window.WebUI.gameplayMechanics;
    const checks = mechanics.descriptionAudit({ description: (entry.abilities || []).map((ability) => ability.description || "").join("\n") }, null, { index: STATE.index, text });
    return window.WebUI.gameplayDetail.propertyGrid(rows) + mechanics.auditMarkup(checks);
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

  const buffStackingLabel = (name) => text(BUFF_STACKING_LABEL_KEYS[name] || "buffStackUnknown");

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
    let missingEnumName = false;
    for (const [field, label] of [
      ["targetSource", "source"], ["target", "target"],
      ["selectorOwner", "selector owner"], ["selectorDirection", "direction"],
      ["centerType", "center"],
    ]) {
      if (!Number.isInteger(settings[field])) continue;
      const name = settings[`${field}Name`];
      if (!name) missingEnumName = true;
      parts.push(`${label}=${name ? `${name} (${formatValue(settings[field])})` : formatValue(settings[field])}`);
    }
    if (missingEnumName) parts.push(text("buffTargetEnumUnavailable"));
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
    return `<div class="gameplay-buff-action-technical"><b>${escapeHtml(text("buffActionTechnical"))}</b>${renderChipPairs(pairs)}</div>`;
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

  function renderBuffCard(id, highlight, index = 0) {
    const record = buffRecord(id);
    const diffClass = highlight && highlight.has(id) ? " gameplay-diff" : "";
    if (!record || record.evidenceStatus === "unresolved") {
      return `<article class="gameplay-buff-card${diffClass}"><header class="gameplay-buff-card-head"><code>${escapeHtml(id)}</code>${renderEvidenceBadge("recoveryUnavailable", "buffDecodeUnavailable", "unresolved")}</header><p class="muted">${escapeHtml(text("buffDecodeUnavailable"))}</p></article>`;
    }
    const stacking = record.stacking || {};
    const stackingLabel = buffStackingLabel(stacking.stackingTypeName);
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
    if (!STATE.showDebug) {
      const mechanics = window.WebUI.gameplayMechanics;
      const rows = mechanics.buffRows(record, {
        text, statAttrLabel, stackingLabel: buffStackingLabel,
        decodedActions: mechanics.decodedBuffActions,
      });
      return `<article class="gameplay-buff-card gameplay-effect-summary${diffClass}"><header class="gameplay-buff-card-head"><strong>${escapeHtml(text("attachedEffects"))} ${index + 1}</strong>${renderEvidenceBadge(summaryStatusKey, summaryStatusDetail, summaryStatusTone)}</header>${mechanics.markup(rows)}</article>`;
    }
    const facts = [
      { label: text("buffLifeType"), value: buffLifeLabel(record.lifeType) },
      duration ? { label: text("buffDuration"), value: Number(duration.value) < 0 ? text("buffLifeInfinity") : `${formatValue(duration.value)} ${text("secondsShort")}` } : null,
      { label: text("buffStackingType"), value: stackingLabel },
      { label: text("buffIdentifierType"), value: stacking.identifierTypeName === "StackingKey" ? text("buffIdentifierStackingKey") : text("buffIdentifierId") },
      typeof stacking.stackingKey === "string" && stacking.stackingKey
        ? { label: text("buffStoredStackingKey"), value: JSON.stringify(stacking.stackingKey) }
        : null,
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
    return `<details class="gameplay-disclosure gameplay-buff-card${diffClass}">
      <summary><span>${escapeHtml(text("attachedEffects"))} ${index + 1}</span>${renderEvidenceBadge(summaryStatusKey, summaryStatusDetail, summaryStatusTone)}<code>${escapeHtml(id)}</code></summary>
      <div class="gameplay-disclosure-body">
      ${STATE.showDebug && hint ? `<p class="muted">${escapeHtml(text("buffIdentifierHint"))}: ${escapeHtml(hint)}</p>` : ""}
      ${renderChipPairs(facts)}
      ${abilityEventActions}
      ${abilityEventActionCount > 0 || hasActionGroup ? `<div class="gameplay-evidence-status-row">${renderEvidenceBadge(actionStatusKey, actionBoundaryKey, actionStatusTone)}</div>` : ""}
      ${attributeModifiers ? `${renderBuffSubheading("buffAttributeModifiers", renderEvidenceBadge("recoveryExact", "buffAttributeModifierBoundary"))}${attributeModifiers}` : ""}
      ${appliedTags ? `${renderBuffSubheading("buffAppliedTags", renderEvidenceBadge("recoveryExact", "buffAppliedTagBoundary"))}${appliedTags}` : ""}
      ${params ? renderBuffSubheading("buffParameterCandidates") + params : ""}
      ${flags.length ? renderBuffSubheading("buffFlags") + renderChipPairs(flags) : ""}
      ${refs ? renderBuffSubheading("buffReferences") + refs : ""}
      ${STATE.showDebug && record.source?.path ? `<p class="gameplay-buff-source muted">${escapeHtml(text("source"))}: ${escapeHtml(record.source.path)}</p>` : ""}
      </div>
    </details>`;
  }

  function renderBuffCards(ids, opts = {}) {
    const rows = [...new Set((ids || []).filter(Boolean))].map((id, index) => renderBuffCard(id, opts.highlight, index));
    if (!rows.length) return "";
    return `<p class="gameplay-section-intro">${escapeHtml(text(STATE.showDebug ? "buffEvidenceBoundary" : "attachedEffectsNote"))}</p><div class="gameplay-buff-grid">${rows.join("")}</div>`;
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
    const distributions = (entry.distributions || []).map((row) => {
      const label = escapeHtml(row.name || row.id);
      if (!row.levelId || row.evidenceBoundary !== "direct") return `<span class="gameplay-value-chip" title="${escapeHtml(row.id)}">${label}</span>`;
      return renderGameplayMapLink(row.levelId, row.name || row.id, `${row.id} → ${row.levelId}`);
    }).join(" ");
    if (distributions) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("distribution"))}</div>${distributions}`);
    return blocks.join("");
  }

  function variantPaneBody(variant, diffLabels) {
    const details = renderChipPairs(variantDetailPairs(variant), { diffLabels });
    return disclosure(text("configurationSource"), `<code>${escapeHtml(variant.id || "")}</code>${details}`);
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
      section(text("attachedEffects"), renderBuffCards(combatValues.bornBuffs, { highlight: variantBuffDiff(entry.variants || []) })),
      section(text("enemyStats"), renderStats(attributes.stats || entry.stats, undefined, { showSource: STATE.showDebug })),
      section(text("combatValues"), renderEnemyCombatValues(combatValues, {
        diffLabels: variantDiffLabels(entry.variants || []),
      })),
    ].join("");
  }

  function renderEnemyVariants(entry) {
    const variants = (entry.variants || []).filter(Boolean);
    if (!variants.length) return renderEnemyVariantDependent(entry, null);
    const selectedIndex = Math.max(0, variants.findIndex((variant) => variant.id === STATE.enemyVariantIds.get(entry.id)));
    const selectedVariant = variants[selectedIndex];
    const diffLabels = variantDiffLabels(variants);
    const columns = variantTableColumns(variants);
    const head = columns.map((column) => `<th scope="col">${escapeHtml(column.label)}</th>`).join("");
    const options = variants.map((variant, index) => {
      const name = variant.name && variant.name !== entry.title && variant.name !== variant.id ? variant.name : `${text("enemyConfiguration")} ${index + 1}`;
      return `<button type="button" class="gameplay-variant-row${index === selectedIndex ? " is-selected" : ""}" data-variant-index="${index}" aria-pressed="${index === selectedIndex}" title="${escapeHtml(variant.id || "")}">${escapeHtml(name)} ${window.WebUI.updateBadges.html("gameplay", `enemy:${variant.id}`)}<br><code>${escapeHtml(variant.id || "")}</code></button>`;
    }).join("");
    const rows = variants.map((variant, index) => {
      const cells = columns.map((column) => `<td>${renderVariantTableCell(column.value(variant))}</td>`).join("");
      return `<tr>
        <th scope="row">${escapeHtml(text("enemyConfiguration"))} ${index + 1} ${window.WebUI.updateBadges.html("gameplay", `enemy:${variant.id}`)}<br><code>${escapeHtml(variant.id || "")}</code></th>${cells}
      </tr>`;
    }).join("");
    const comparison = columns.length ? `<div class="gameplay-variant-table-wrap"><table class="gameplay-variant-table">
      <thead><tr><th scope="col">${escapeHtml(text("enemyConfiguration"))}</th>${head}</tr></thead><tbody>${rows}</tbody>
    </table></div>` : `<p class="muted">${escapeHtml(text("noVariantDifferences"))}</p>`;
    return `<div class="gameplay-variant-switch" data-variant-card>
      <p class="gameplay-section-intro">${escapeHtml(text("enemyConfigurationNote"))}</p>
      <div class="gameplay-variant-options" role="group" aria-label="${escapeHtml(text("enemyConfigurations"))}">${options}</div>
      <div data-enemy-variant-dependent>${renderEnemyVariantDependent(entry, selectedVariant)}</div>
      ${variants.length > 1 ? disclosure(text("configurationComparison"), comparison) : ""}
      <div class="gameplay-variant-pane" data-selected-variant-pane>${variantPaneBody(selectedVariant, diffLabels)}</div>
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
      const select = (row) => {
        const index = Number(row.dataset.variantIndex || 0);
        const variant = variants[index];
        if (!variant) return;
        STATE.enemyVariantIds.set(entry.id, variant.id);
        rows.forEach((candidate) => {
          const selected = candidate === row;
          candidate.classList.toggle("is-selected", selected);
          candidate.setAttribute("aria-pressed", String(selected));
        });
        if (pane) pane.innerHTML = variantPaneBody(variant, diffLabels);
        if (dependent) {
          dependent.innerHTML = renderEnemyVariantDependent(entry, variant);
          bindLevelSliders(dependent);
        }
      };
      rows.forEach((row) => {
        row.addEventListener("click", () => select(row));
        row.addEventListener("keydown", (event) => {
          const index = rows.indexOf(row);
          const next = { ArrowRight: (index + 1) % rows.length, ArrowLeft: (index + rows.length - 1) % rows.length, Home: 0, End: rows.length - 1 }[event.key];
          if (next === undefined) return;
          event.preventDefault();
          rows[next].focus();
          select(rows[next]);
        });
      });
    });
  }

  function renderEnemyCombatValues(entry, { diffLabels } = {}) {
    const blocks = [];
    const localizeField = (row) => {
      const label = text(`enemyField_${row.key}`);
      return { ...row, label: label === `enemyField_${row.key}` ? row.label || row.key : label };
    };
    const damage = renderChipPairs((entry.damageScalars || []).map(localizeField));
    const resilience = renderChipPairs((entry.resilience || []).map(localizeField));
    const attributes = entry.independentAttributes || [];
    const isNamed = (attr) => !/^Attr \d+$/.test(statAttrLabel(attr));
    const independent = renderStatAttrs(attributes.filter(isNamed));
    if (independent) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("independentAttributes"))}</div>${independent}`);
    const unnamed = attributes.filter((attr) => !isNamed(attr));
    if (unnamed.length) blocks.push(disclosure(text("unnamedAttributes"), renderStatAttrs(unnamed), `${unnamed.length} ${text("configRecords")}`));
    const template = [
      damage ? `<div class="gameplay-subheading">${escapeHtml(text("damageScalars"))}</div>${damage}` : "",
      resilience ? `<div class="gameplay-subheading">${escapeHtml(text("resilience"))}</div>${resilience}` : "",
    ].join("");
    if (template) blocks.push(disclosure(text("enemyTemplateParameters"), `<p class="gameplay-section-intro">${escapeHtml(text("enemyTemplateParametersNote"))}</p>${template}`));
    const modifiers = renderEnemyModifierRows(entry, diffLabels);
    if (modifiers) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("attrModifiers"))}</div>${modifiers}`);
    return blocks.join("");
  }

  function renderEnemyDetail(entry) {
    const facts = [
      fact(text("templateId"), entry.templateId, { mono: true }),
      fact(text("attrTemplateId"), entry.attrTemplateId, { mono: true }),
      fact(text("displayType"), entry.displayTypeLabel || entry.displayType),
      fact(text("variantCount"), entry.variantCount || ((entry.variants || []).length || "")),
      fact(text("nickname"), entry.nickname),
      fact(text("modelId"), entry.modelId, { mono: true }),
      fact(text("aiTemplateId"), entry.aiTemplateId, { mono: true }),
      fact(text("dangerous"), entry.isDangerous ? text("dangerous") : ""),
    ].filter(Boolean);
    return {
      facts,
      body: [
        section(text("enemyTraits"), renderEnemyAbilities(entry), "traits"),
        section(text("enemyConfigurations"), renderEnemyVariants(entry), "configurations"),
        section(text("enemyDetails"), renderEnemyDetails(entry), "details"),
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
    const rendered = renderTemplateDescription(
      use.descriptionTemplate,
      descriptionValueMap(...actions.flatMap((action) => [action?.buffBlackboard, action?.skillBlackboard]), { duration: use.duration }),
      use.description,
    );
    return [rendered.html, details].filter(Boolean).join("");
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

  function renderItemRewardCards(entry, entries = STATE.entries) {
    const chest = entry.chestData || {};
    const quantities = (items, unavailable = false) => unavailable
      ? (items || []).map((item) => ({ ...item, quantityDataUnavailable: true })) : items || [];
    const blocks = [];
    if (chest.sharedTrialEquipment) blocks.push(`<div class="gameplay-integration-note is-warning" role="status">${escapeHtml(STATE.uiLocale === "zh" ? "以下为关联角色试用的装备奖励。现有数据未明确各防具箱分别包含哪些装备；列表不代表单箱可获得全部装备。" : "Equipment rewards from the linked operator trial. The available data does not identify each supply box's contents; this list is not the contents of a single box.")}</div>`);
    const chestDetails = renderChipPairs([
      { label: text("chestType"), value: chest.type },
      { label: text("selectedCount"), value: chest.selectedCount },
    ]);
    if (chestDetails) blocks.push(chestDetails);
    const randomItems = renderMaterialChips(quantities(chest.randomItems, chest.sharedTrialEquipment), entries);
    if (randomItems) blocks.push(`<div class="gameplay-subheading">${escapeHtml(text("randomItems"))}</div>${randomItems}`);
    const rewardCards = (chest.rewards || []).map((reward) => {
      if (!reward) return "";
      const unavailable = chest.sharedTrialEquipment || reward.quantityDataUnavailable;
      const fixed = renderMaterialChips(quantities(reward.items, unavailable), entries);
      const probable = renderMaterialChips(quantities(reward.probableItems, unavailable), entries);
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
      fact(text("rarity"), entry.rarity),
      fact(text("itemType"), entry.itemTypeLabel || entry.itemType),
      fact(text("showingType"), entry.showingTypeLabel || entry.showingType),
      fact(text("useCategory"), entry.useCategory),
      entry.apSupplyData && fact(text("apRecoverValue"), entry.apSupplyData.apRecoverValue),
      fact(text("iconId"), entry.iconId || entry.iconCompositeId, { mono: true }),
      fact(text("maxStack"), entry.maxStackCount),
      fact(text("backpackStack"), entry.maxBackpackStackCount),
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

  // Item catalog details read the matching Gameplay publication without
  // replacing the entity pane's language, selection or pending requests.
  const itemIndexes = new Map();
  let itemAssets = null;
  async function catalogItem(id, language) {
    if (!itemIndexes.has(language)) {
      const pending = (async () => {
        if (STATE.index && STATE.language === language) return STATE.index;
        const response = await fetchWithProgress(gameplayDataPath(language));
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        return response.json();
      })().catch((error) => { itemIndexes.delete(language); throw error; });
      itemIndexes.set(language, pending);
    }
    const data = await itemIndexes.get(language);
    const entries = Array.isArray(data.entries) ? data.entries : [];
    return { entry: entries.find((row) => row.kind === "item" && row.id === id), entries };
  }

  async function itemContent(id, language) {
    const { entry, entries } = await catalogItem(id, language);
    if (!entry) return "";
    return [
      entry.apSupplyData ? section(text("apRecoverValue"), renderChipPairs([
        { label: text("apRecoverValue"), value: entry.apSupplyData.apRecoverValue },
      ])) : "",
      section(text("itemUse"), renderItemUse(entry)),
      section(text("itemActions"), renderItemActions(entry)),
      section(text("itemRewards"), renderItemRewardCards(entry, entries)),
    ].join("");
  }

  async function catalogAssets(language) {
    return await (itemAssets ||= fetchIntegrationJson(integrationPath("assets", language),
      (payload) => payload?.schemaVersion === "gameplayAssetRefs.v11" && typeof payload.entries === "object").catch(() => null));
  }

  async function itemImages(language) {
    const assets = await catalogAssets(language);
    return Object.fromEntries(Object.entries(assets?.entries || {}).filter(([key]) => key.startsWith("item:"))
      .map(([key, refs]) => [key.slice(5), refs.images || []]));
  }

  async function itemGallery(id, language, opts = {}) {
    const entry = opts.entry ? { ...opts.entry, kind: opts.entry.kind === "items" ? "item" : opts.entry.kind }
      : (await catalogItem(id, language)).entry;
    if (!entry) return "";
    const assets = await catalogAssets(language);
    const refs = assets?.entries?.[`${entry.kind}:${entry.id}`] || {};
      const models = [...(refs.models || [])];
    const images = [...(refs.images || []), ...(String(entry.type) === "13" ? [] : opts.images || [])];
    const seen = new Set();
    const displayEntry = opts.assetKind ? { ...entry, kind: opts.assetKind } : entry;
    return renderGameplayAssetGallery(displayEntry, { entries: { [`${displayEntry.kind}:${entry.id}`]: {
      ...refs, models: [...new Map(models.map((model) => [model.rel, model])).values()],
      images: images.filter((asset) => asset?.rel && !seen.has(asset.rel) && seen.add(asset.rel)),
    } } });
  }

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
    // Unity object documents are export-store rows browsed on the Data page.
    const dataUrl = window.WebUI?.dataPageUrlForRel?.(rel);
    if (dataUrl) return dataUrl;
    const url = new URL(window.location.href);
    url.searchParams.set("asset", String(rel || ""));
    url.hash = "#assets";
    return url.toString();
  }

  const gameplayAssetHref = window.WebUI.exportFullHref;

  function gameplayAssetRefsForItem(item) {
    const itemId = String(item?.id || "").trim();
    if (!itemId) return null;
    if (item.kind === "gem" && item.iconId) {
      const refs = STATE.integration.assets?.entries?.[`enemy:${item.iconId}`];
      if (refs?.images?.some((asset) => asset?.rel)) return refs;
      const iconRefs = integrationAssetRefsForToken(item.iconId);
      if (iconRefs?.images?.some((asset) => asset?.rel)) return iconRefs;
    }
    const tokenRefs = integrationAssetRefsForToken(item?.iconId || itemId);
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
    return `<button type="button" class="${escapeHtml(className)}" title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}" data-inline-image-id="${escapeHtml(imageId)}" data-inline-image-name="${escapeHtml(imageName)}" data-inline-image-src="${escapeHtml(src)}" data-inline-image-href="${escapeHtml(gameplayAssetPageHref(rel))}"${token ? ` data-gameplay-token="${escapeHtml(token)}"` : ""}>${content}</button>`;
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

  function refreshGameplayFileSearch() {
    for (const entry of STATE.entries) {
      const refs = [STATE.integration.assets?.entries?.[`${entry.kind}:${entry.id}`]];
      const seen = new Set();
      function visit(value) {
        if (typeof value === "string") {
          const assets = integrationAssetRefsForToken(value);
          if (assets) refs.push(assets);
        } else if (value && typeof value === "object" && !seen.has(value)) {
          seen.add(value);
          for (const [key, child] of Object.entries(value)) {
            if (key !== "linkedFileSearch" && key !== "search") visit(child);
          }
        }
      }
      visit(entry);
      const { linkedFileSearch: _previousFiles, ...record } = entry;
      entry.linkedFileSearch = window.WebUI.linkedFileSearchText(record, refs);
    }
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

  function renderGameplayAssetGallery(entry, assets = STATE.integration.assets) {
    const key = `${entry?.kind || ""}:${entry?.id || ""}`;
    const refs = assets?.entries?.[key] || (entry?.kind === "gem" ? assets?.entries?.[`enemy:${entry.iconId}`] : null)
      || assets?.tokens?.[entry?.iconId] || assets?.tokens?.[entry?.id];
    if (!refs) return "";
    const kind = String(entry?.kind || "");
    if (["weapon", "equipment", "enemy", "item", "items", "machines", "activity", "stage"].includes(kind)) return section(text("assetMaterials"), renderGameplayAssetStrip(entry, refs));
    if (kind === "gem") {
      // One preview per named icon family; Texture/Sprite crops and resolutions
      // remain distinct source assets. Keep the largest representation for display.
      const images = new Map();
      for (const asset of refs.images || []) {
        if (!asset?.rel) continue;
        const family = asset.rel.split("/").pop().replace(/_p[0-9a-f]+(?=\.[^.]+$)/i, "").toLowerCase();
        const previous = images.get(family);
        if (!previous || Number(asset.width) * Number(asset.height) > Number(previous.width) * Number(previous.height)) images.set(family, asset);
      }
      const models = [...new Map((refs.models || []).filter((asset) => asset?.rel).map((asset) => [asset.rel, asset])).values()];
      return section(text("assetMaterials"), renderGameplayAssetStrip(entry, { images: [...images.values()], models }));
    }
    const iconLike = ["weapon", "equipment", "item"].includes(kind);
    const allImages = Array.isArray(refs.images) ? refs.images.filter((item) => item?.rel) : [];
    const images = allImages;
    const models = Array.isArray(refs.models) ? refs.models.filter((item) => item?.rel) : [];
    const imageCards = images.map((asset) => {
      const caption = asset.rel.split(/[\\/]/).pop();
      const preview = renderGameplayImageButton(asset, {
        className: "gameplay-asset-image-preview",
        alt: entry.title || entry.id || "",
        imageId: `${entry.id || "entry"}:${asset.rel}`,
        imageName: caption,
      });
      return `<div class="gameplay-asset-thumb${iconLike ? " gameplay-item-weapon-thumb" : ""}"><figure>${preview}<figcaption>${escapeHtml(caption)}</figcaption></figure></div>`;
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
    if (!edges.length) return section(text("combatLinks"), `<p class="gameplay-integration-empty">${escapeHtml(text("noCombatLinks"))}</p>`);
    const direct = edges.filter((edge) => edge.confidence === "direct").length;
    const body = `<div class="gameplay-integration-summary"><span>${formatNumber(edges.length)} ${escapeHtml(text("combatLinks"))}</span><span>${formatNumber(direct)} ${escapeHtml(text("directEvidence"))}</span><span>${formatNumber(edges.length - direct)} ${escapeHtml(text("inferredEvidence"))}</span></div>${edges.map(renderCombatEdge).join("")}`;
    return section(text("combatLinks"), body);
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
    return section(`${text("projectiles")} (${matches.length})`, `<div class="gameplay-projectile-grid">${cards}</div>`);
  }

  function renderIntegratedSections(entry) {
    if (entry?.kind === "character") return "";
    const blocks = [];
    if (STATE.showDebug) {
      blocks.push(renderCombatIntegration(entry), renderProjectileIntegration(entry));
    }
    blocks.push(renderGameplayAssetGallery(entry));
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
        if (window.WebUI.gameplayTabs) {
          window.WebUI.gameplayTabs.open(target.kind, target.id);
          return;
        }
        STATE.selected = target;
        // A related reward often points outside the current search/filter
        // result (for example, an item search pointing at a weapon).  Clear
        // conflicting filters before rendering so renderList does not reset
        // the selection back to the source item.
        if (!STATE.filtered.includes(target)) {
          const query = gp$("#gameplay-q");
          if (query) query.value = "";
          STATE.facets.reset({ silent: true });
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
    const formulaLink = formula.formulaId ? `<a class="gameplay-value-chip gameplay-item-chip gameplay-item-chip-link" href="${escapeHtml(window.WebUI.gameplayTabs.pageUrl('item', formula.formulaId))}"><b>${escapeHtml(text('formula'))}</b>${escapeHtml(formula.formulaName || formula.name || formula.formulaId)}</a>` : '';
    const methods = [formula, ...(formula.variants || [])].filter((method) => (method.costs || []).length);
    const variants = methods.map((method, index) => window.WebUI.gameplayItems.renderCraftingRecipe({
      id: `${formula.formulaId || entry.id}:${method.chainId ?? index}`,
      ingredients: [method.costs],
      outcomes: [[{ id: formula.outcomeEquipId || entry.id, name: formula.outcomeEquipName || entry.title, count: 1 }]],
    }, renderEquipmentCostItem)).join("");
    return `<article class="gameplay-skill-card gameplay-equipment-formula">
      <header>
        ${formulaLink || `<div class="gameplay-skill-title">${escapeHtml(formula.formulaName || formula.name || text("equipmentFormula"))}</div>`}
      </header>
      <div class="gameplay-items-references">${variants}</div>
    </article>`;
  }

  function renderEquipmentCostItem(cost) {
    return `<a class="gameplay-value-chip gameplay-item-chip gameplay-item-chip-link" href="${escapeHtml(window.WebUI.gameplayTabs.pageUrl('item', cost.id))}"><span class="gameplay-item-chip-icon gameplay-item-chip-icon-static" data-equipment-cost-icon="${escapeHtml(cost.id)}"></span><b>${escapeHtml(cost.name || cost.id)}</b> × ${escapeHtml(formatValue(cost.count))}</a>`;
  }

  const equipmentItemIndexes = new Map();
  async function mountEquipmentCostIcons(root, language) {
    const slots = [...root.querySelectorAll("[data-equipment-cost-icon]")];
    if (!slots.length) return;
    try {
      if (!equipmentItemIndexes.has(language)) {
        equipmentItemIndexes.set(language, (async () => {
          const response = await fetchWithProgress(`data/lang/${encodeURIComponent(language)}/gameplay/items/index.json`);
          if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
          return response.json();
        })().catch((error) => { equipmentItemIndexes.delete(language); throw error; }));
      }
      const data = await equipmentItemIndexes.get(language);
      const items = new Map((data.items || []).map((item) => [item.id, item]));
      for (const slot of slots) {
        if (!slot.isConnected) continue;
        const id = slot.dataset.equipmentCostIcon;
        const icon = data.icons?.[String(items.get(id)?.iconId || id).toLowerCase()];
        if (icon?.r) slot.innerHTML = `<img src="${escapeHtml(gameplayAssetHref(icon.r))}" alt="" loading="lazy" onerror="this.parentElement.classList.add('is-missing')">`;
        else slot.classList.add("is-missing");
      }
    } catch {
      for (const slot of slots) if (slot.isConnected) slot.classList.add("is-missing");
    }
  }
  function syncLevelCard(input) {
    const card = input.closest("[data-level-card]");
    if (!card) return;
    const index = Number(input.value || 0);
    const panes = [...card.querySelectorAll(".gameplay-level-pane")];
    panes.forEach((pane, paneIndex) => {
      pane.hidden = paneIndex !== index;
    });
    const soundSlot = panes[index]?.querySelector(":scope > [data-skill-sound-slot]");
    const sound = card.querySelector("[data-skill-sound-slot] > *");
    if (soundSlot && sound && sound.parentElement !== soundSlot) soundSlot.append(sound);
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
    const row = listGroups.locate(list, STATE.selected);
    if (!row) return false;
    listGroups.reveal(row);
    if (isMobileLayout()) {
      const left = gp$("#gameplay-left");
      if (left) left.scrollIntoView({ block: "start", behavior: "smooth" });
    }
    return true;
  }

  // Sound sections can list thousands of candidates; a real <audio> is only
  // created when its play button is clicked.
  // Collapsed sound lists can hold thousands of cards; their bodies are built
  // only when the disclosure is first opened.
  const DEFERRED_GAMEPLAY_BODIES = new Map();
  let deferredGameplayBodySeq = 0;
  function deferGameplayBody(render) {
    const id = String(++deferredGameplayBodySeq);
    DEFERRED_GAMEPLAY_BODIES.set(id, render);
    return id;
  }

  function gameplayAudioFileName(src) {
    return String(src || "").split("/").pop();
  }

  function lazyAudioButton(src) {
    return `<button type="button" class="gameplay-audio-lazy" data-gameplay-audio-src="${escapeHtml(src)}" title="${escapeHtml(src)}" aria-label="${escapeHtml(`${text("playAudio")} ${gameplayAudioFileName(src)}`)}"><span aria-hidden="true">▶</span><span class="gameplay-audio-lazy-name">${escapeHtml(gameplayAudioFileName(src))}</span></button>`;
  }

  function bindGameplayMediaPlayers(root) {
    if (!root) return;
    if (!root.dataset.lazyAudioBound) {
      root.dataset.lazyAudioBound = "1";
      // toggle does not bubble; capture reaches disclosures added later too.
      root.addEventListener("toggle", (event) => {
        const details = event.target;
        if (details?.tagName !== "DETAILS" || !details.open || !details.dataset.gameplayDeferred) return;
        const render = DEFERRED_GAMEPLAY_BODIES.get(details.dataset.gameplayDeferred);
        DEFERRED_GAMEPLAY_BODIES.delete(details.dataset.gameplayDeferred);
        delete details.dataset.gameplayDeferred;
        if (render) details.insertAdjacentHTML("beforeend", render());
        enhanceVisible();
      }, true);
      root.addEventListener("click", (event) => {
        const sim = event.target.closest?.("[data-gameplay-sfx-sim]");
        if (sim && root.contains(sim)) {
          // The button sits in the event's <summary>; don't fold/unfold.
          event.preventDefault();
          playGameplaySoundSim(sim);
          return;
        }
        const button = event.target.closest?.("[data-gameplay-audio-src]");
        if (!button || !root.contains(button)) return;
        const audio = document.createElement("audio");
        audio.controls = true;
        audio.preload = "auto";
        audio.src = button.dataset.gameplayAudioSrc;
        audio.dataset.mediaLabel = gameplayAudioFileName(audio.src);
        audio.dataset.gameplaySfxFile = button.dataset.gameplayAudioSrc;
        button.replaceWith(audio);
        if (window.WebUI.enhanceMediaPlayers && audio.parentElement) window.WebUI.enhanceMediaPlayers(audio.parentElement);
        audio.play().catch(() => {});
      });
    }
    root.querySelectorAll("[data-gameplay-audio-event]").forEach((link) => {
      link.addEventListener("click", (event) => {
        if (!window.WebUI.isPlainClick(event)) return;
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
    const isCharacter = entry.kind === "character" && (entry.attributeRows || []).length > 0;
    const view = isCharacter && STATE.characterView === "loadout" ? "loadout" : "info";
    const titleNode = gp$("#gameplay-detail-title");
    titleNode.classList.toggle("has-view-switch", isCharacter);
    titleNode.innerHTML = `<span>${highlightText(title)}${window.WebUI.updateBadges.html("gameplay", gameplayUpdateIds(entry))}</span>`
      + (isCharacter ? renderCharacterViewSwitch(view) : "");
    const rendered = entry.kind === "gem" ? renderGemDetail(entry) : entry.kind === "weapon" ? renderWeaponDetail(entry) : entry.kind === "equipment" ? renderEquipmentDetail(entry) : entry.kind === "enemy" ? renderEnemyDetail(entry) : entry.kind === "item" ? renderItemDetail(entry) : renderCharacterDetail(entry);
    // The header already shows the title; drop any fact that merely repeats it
    // (e.g. file/internal name equal to the title) to avoid duplicated info.
    const detailTags = dedupeDetailTags([
      fact(text("kind"), kindLabel(entry.kind), { kind: entry.kind }),
      fact(text("id"), entry.id),
      ...(rendered.facts || []),
    ].filter((tag) => tag && String(tag.value) !== title));
    // Facts render as a conv-meta-style "label=value | ..." text line.
    const readingView = true;
    const meta = gp$("#gameplay-detail-meta");
    const visibleTags = detailTags.filter((tag) => !["character", "enemy"].includes(entry.kind) || !tag.mono || STATE.showDebug);
    meta.textContent = window.WebUI.gameplayDetail.metadata(visibleTags.map((tag) => ({ label: tag.label, value: formatValue(tag.value) })));
    const refs = STATE.integration.assets?.entries?.[`${entry.kind}:${entry.id}`] || gameplayAssetRefsForItem(entry);
    const images = filterEndministratorVariant(refs?.images, entry, (image) => image?.rel) || [];
    window.WebUI.gameplayDetail.mount(gp$("#gameplay-detail-header"), gp$("#gameplay-detail-header-main"), titleNode, meta,
      window.WebUI.gameplayDetail.image(images.find((image) => image?.rel), gameplayAssetHref));
    // The story-wiki link sits in its own slot, mirroring the story page's
    // gameplay link under the header meta.
    const wikiSlot = gp$("#gameplay-detail-wiki");
    if (wikiSlot) {
      const itemLink = ["weapon", "equipment"].includes(entry.kind) && window.WebUI.gameplayItems.hasItem(entry.id, STATE.language)
        ? window.WebUI.gameplayDetail.datasetLink("item", `items:${entry.id}`, text("itemDetails")) : "";
      const wiki = renderStoryWikiLink(entry) + itemLink;
      wikiSlot.innerHTML = wiki;
      wikiSlot.hidden = !wiki;
    }
    window.WebUI.gameplayDetail.bindDatasetLinks(gp$("#gameplay-detail-header"));
    // Playable characters switch between their data and the loadout
    // calculator; other kinds have only the data view.
    const trailingAudio = entry.kind === "enemy"
      ? section(text("relatedSoundEffects"), renderEnemySoundEffects(entry) || renderSoundEffectsLoading())
      : entry.kind === "character"
        ? section(text("relatedSoundEffects"), renderCharacterSoundEffects(endministratorVariantEntry(entry)) || renderSoundEffectsLoading())
        : "";
    const body = view === "loadout"
      ? window.WebUI.gameplayLoadout.render(entry, loadoutHelpers())
      : `${rendered.body || ""}${STATE.showDebug && ["character", "enemy"].includes(entry.kind) ? window.WebUI.gameplaySkillRefs?.markup() || "" : ""}${renderIntegratedSections(entry)}${trailingAudio}`;
    gp$("#gameplay-detail-body").innerHTML = readingView && view === "info" ? `<div class="gameplay-reading-view${["weapon", "gem", "equipment", "enemy"].includes(entry.kind) ? " gameplay-catalog-reading-view" : ""}">${body}</div>` : body;
    if (entry.kind === "equipment") void mountEquipmentCostIcons(gp$("#gameplay-detail-body"), STATE.language);
    if (readingView && view === "info") bindDetailContents(detail);
    const updateIds = gameplayUpdateIds(entry);
    window.WebUI.updateBadges.mount(gp$("#gameplay-detail-body"), "gameplay", updateIds, {
      owners: entry.kind === "enemy" ? updateIds.map((id) => {
        const index = (entry.variants || []).findIndex((variant) => `enemy:${variant.id}` === id);
        const variant = entry.variants?.[index];
        return { id, code: id.slice("enemy:".length), label: index < 0 ? title : `${text("enemyConfiguration")} ${index + 1}${variant.name && variant.name !== title && variant.name !== variant.id ? ` · ${variant.name}` : ""}` };
      }) : null,
    });
    bindGameplayMediaPlayers(detail);
    bindIntegratedLinks(detail);
    bindLevelSliders(detail);
    bindVariantSwitches(detail);
    if (view !== "loadout") {
      const selectedEntry = endministratorVariantEntry(entry);
      if (entry.kind === "character") void mountSkillMechanics(detail, selectedEntry);
      if (STATE.showDebug) void window.WebUI.gameplaySkillRefs?.mount(detail, selectedEntry);
    }
    detail.querySelectorAll("[data-character-view]").forEach((button) => {
      button.addEventListener("click", () => {
        if (STATE.characterView === button.dataset.characterView) return;
        STATE.characterView = button.dataset.characterView;
        storageSet("endfield.characterView", STATE.characterView);
        renderDetail(entry);
      });
    });
    if (view === "loadout") window.WebUI.gameplayLoadout.bind(detail, entry, loadoutHelpers());
    syncLocateCurrentButton();
  }

  function renderCharacterViewSwitch(view) {
    const button = (key, label) => `<button type="button" role="tab" class="gameplay-view-switch-button${view === key ? " is-active" : ""}" aria-selected="${view === key}" data-character-view="${key}">${escapeHtml(text(label))}</button>`;
    return `<div class="gameplay-view-switch" role="tablist">${button("info", "characterInfoView")}${button("loadout", "characterLoadoutView")}</div>`;
  }

  function loadoutHelpers() {
    return {
      STATE,
      index: STATE.index || {},
      entries: STATE.entries || [],
      text,
      escapeHtml,
      formatValue,
      formatNumber,
      formatDescriptionValue,
      renderMaterialChips,
      renderEvidenceBadge,
      renderItemIcon: renderGameplayItemIcon,
      goldItem: goldCurrencyItem,
    };
  }

  function renderListNote(message) {
    const list = gp$("#gameplay-list");
    if (list) list.innerHTML = `<div class="gameplay-list-note">${escapeHtml(message)}</div>`;
    gp$("#gameplay-shown").textContent = "0";
    gp$("#gameplay-total").textContent = formatNumber(STATE.entries.filter((entry) => STATE.facets.active("kinds").has(entry.kind)).length);
    renderDetail(null);
  }

  function rowPathText(entry) {
    if (entry.kind === "weapon") return entry.fileName || entry.id || "";
    if (entry.kind === "enemy" || entry.kind === "item") return entry.fileName || entry.title || entry.id || "";
    return entry.id || "";
  }

  // A single list row, copying the story file-list item style: a colored kind
  // badge chip, then the readable name, with the subtitle below.
  function weaponEffectLabel(entry, index) {
    return entry?.kind === "weapon" ? gemTermLabel({ name: entry.skills?.[index]?.name }, index) : "";
  }

  function gemTermLabel(term, index) {
    const name = String(term.name || term.id || "").split("·")[0].trim();
    return index === 0 ? name.replace(/提升$/, "") : name;
  }

  function gemPoolFilterValues(entry, index) {
    return entry.kind === "gem" ? (entry.termPools?.[index] || []).map((term) => gemTermLabel(term, index)) : weaponEffectLabel(entry, index);
  }

  function equipmentAttributeLabels(entry) {
    if (entry?.kind !== "equipment") return [];
    const attrs = entry.stats?.propertyCurves?.length ? entry.stats.propertyCurves
      : entry.stats?.displayAttrs || entry.stats?.rows?.[0]?.attrs || [];
    return [...new Set(attrs.filter((attr) => attr.key !== "def" && Number(attr.type) !== 3)
      .map(statAttrLabel).filter(Boolean))];
  }

  function equipmentBaseAttributeValue(entry, label) {
    if (entry?.kind !== "equipment") return null;
    // displayAttrs stores the base attrValue used by the level 1 curve row.
    const attr = entry.stats?.displayAttrs?.find((item) => statAttrLabel(item) === label);
    return attr && attr.value !== null && attr.value !== "" && Number.isFinite(Number(attr.value))
      ? Number(attr.value) : null;
  }

  function syncEquipmentAttributeSort() {
    const select = gp$("#gameplay-sort");
    if (!select) return;
    const previous = select.value;
    const labels = STATE.facets.active("kinds").has("equipment")
      ? [...STATE.facets.active("equipmentAttributes")] : [];
    const options = labels.map((label) => ({
      value: `equipment-attribute:${label}`,
      label: `${label} · ${text("equipmentBaseAttributeSort")}`,
    }));
    const existing = [...select.querySelectorAll('[data-equipment-attribute-sort]')];
    if (JSON.stringify(existing.map((option) => ({ value: option.value, label: option.textContent }))) !== JSON.stringify(options)) {
      existing.forEach((option) => option.remove());
      for (const item of options) {
        const option = new Option(item.label, item.value);
        option.dataset.equipmentAttributeSort = "1";
        select.add(option);
      }
      select.value = [...select.options].some((option) => option.value === previous) ? previous : "default";
      window.WebUI.sorting.refresh();
    }
  }

  function renderRow(entry, selectedId) {
    const key = `${entry.kind}:${entry.id}`;
    const selected = key === selectedId ? " is-selected" : "";
    const badgeClass = KIND_BADGE_CLASS[entry.kind] || "";
    const kindBadge = ["character", "weapon", "gem", "equipment"].includes(entry.kind)
      ? "" : `<span class="badge ${badgeClass}">${escapeHtml(kindLabel(entry.kind))}</span>`;
    const refs = STATE.integration.assets?.entries?.[key] || gameplayAssetRefsForItem(entry);
    const images = filterEndministratorVariant(refs?.images, entry, (image) => image?.rel);
    // Use the gallery's horizontal face banner for characters. Missing banners
    // leave a text row; a full illustration is not a substitute at this size.
    const asset = entry.kind === "character"
      ? images.find((image) => image.rel && image.height > 0 && image.width / image.height > 1.45)
      : images.find((image) => image.rel);
    const thumbnail = asset ? `<span class="gameplay-row-thumbnail${entry.kind === "character" ? " gameplay-row-banner" : ""}"><img src="${escapeHtml(gameplayAssetHref(asset.rel))}" alt="" loading="lazy" onerror="this.parentElement.classList.add('is-missing')"></span>` : "";
    const weaponEffects = entry.kind === "weapon" ? (entry.skills || []).map((skill, index) => {
      const name = String(skill.name || "").trim();
      return name ? `<span title="${escapeHtml(name)}">${highlightText(weaponEffectLabel(entry, index))}</span>` : "";
    }).filter(Boolean).join(" · ") : equipmentAttributeLabels(entry).map((label) => `<span>${highlightText(label)}</span>`).join(" · ");
    return `<button class="gameplay-row${selected}" type="button" data-key="${escapeHtml(key)}">
      ${thumbnail}<span class="gameplay-row-text"><span class="gameplay-row-line1">
        ${kindBadge}
        ${window.WebUI.updateBadges.html("gameplay", gameplayUpdateIds(entry))}
        <span class="gameplay-row-name">${highlightText(entry.title || entry.id || "")}</span>
      </span>
      <span class="gameplay-row-meta">${highlightText(entrySubtitle(entry) || rowPathText(entry) || "")}${weaponEffects ? ` / ${weaponEffects}` : ""}</span></span>
    </button>`;
  }

  const listGroups = window.WebUI.listGroups.create();
  function gameplayUpdateIds(entry) {
    return [...new Set([entry.id, ...(entry.variants || []).map((variant) => variant.id)])]
      .map((id) => `${entry.kind}:${id}`);
  }

  function gameplayUpdateStatuses(entry) {
    return [...new Set(gameplayUpdateIds(entry).map((id) => window.WebUI.updateBadges.status("gameplay", id)).filter(Boolean))];
  }

  function renderList() {
    const list = gp$("#gameplay-list");
    if (!list) return;
    gp$("#gameplay-shown").textContent = formatNumber(STATE.filtered.length);
    gp$("#gameplay-total").textContent = formatNumber(STATE.entries.filter((entry) => STATE.facets.active("kinds").has(entry.kind)).length);
    if (!STATE.filtered.length) {
      renderListNote(text(STATE.entries.length ? "noResults" : "noData"));
      return;
    }

    const selectedId = STATE.selected && `${STATE.selected.kind}:${STATE.selected.id}`;
    listGroups.render(list, STATE.filtered, {
      keyOf: gameplayListGroupKey, title: gameplayListGroup,
      renderRow: (entry) => renderRow(entry, selectedId), estimateHeight: 90,
    });
    list.onclick = (event) => {
      const row = event.target.closest('.gameplay-row');
      if (!row) return;
      STATE.selected = STATE.filtered.find((entry) => `${entry.kind}:${entry.id}` === row.dataset.key) || null;
      renderList(); renderDetail(STATE.selected);
    };

    if (!STATE.selected || !STATE.filtered.includes(STATE.selected)) {
      STATE.selected = STATE.filtered[0] || null;
    }
    renderDetail(STATE.selected);
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

  function abilityFilterKey(entry, field) {
    return entry?.kind === "character" && Number(entry[field]) > 0 ? String(entry[field]) : "";
  }

  function abilityFilterLabel(entry, field) {
    return abilityFilterKey(entry, field) ? statAttrLabel({ type: Number(entry[field]) }) : "";
  }

  function rarityFilterKey(entry) {
    if (entry?.kind === "enemy") return "";
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

  function itemTypeFilterKey(entry) {
    if (!entry || entry.kind !== "item") return "";
    if (entry.apSupplyData) return entry.id.startsWith("item_char_ap_supply_") ? "character_ap_supply" : "ap_supply";
    if (String(entry.showingType) === "5" && entry.itemTypeLabel) return `type:${entry.itemType}`;
    if (entry.showingType && entry.showingTypeLabel) return `showing:${entry.showingType}`;
    return `type:${entry.itemType ?? entry.useCategory ?? "other"}`;
  }

  function itemTypeFilterLabel(entry) {
    if (!entry || entry.kind !== "item") return "";
    if (entry.apSupplyData) return text(entry.id.startsWith("item_char_ap_supply_") ? "characterApSupply" : "apSupply");
    if (String(entry.showingType) === "5" && entry.itemTypeLabel) return entry.itemTypeLabel;
    return entry.showingTypeLabel || entry.itemTypeLabel || entry.useCategory || text("itemType");
  }

  function renderKindTabs() {
    const active = [...STATE.facets.active("kinds")][0] || "character";
    gp$("#gameplay-count").textContent = formatNumber(STATE.entries.filter((entry) => entry.kind === active).length);
    window.WebUI.gameplayTabs?.render();
    for (const [, suffix, , , kind] of ENTRY_FACET_GROUPS) {
      const section = gp$(`[data-filter-section="gameplay-${suffix}"]`);
      if (section) section.hidden = (kind || "character") !== active;
    }
    for (const [, suffix] of WEAPON_EFFECT_FACET_GROUPS) {
      const section = gp$(`[data-filter-section="gameplay-${suffix}"]`);
      if (section) section.hidden = !["weapon", "gem"].includes(active);
    }
    const domain = gp$('[data-filter-section="gameplay-gem-domain"]');
    if (domain) domain.hidden = active !== "gem";
    const rarity = gp$('[data-filter-section="gameplay-rarity"]');
    if (rarity) rarity.hidden = ["gem", "enemy"].includes(active);
    const sort = gp$("#gameplay-sort");
    if (sort) {
      for (const option of sort.options) {
        if (option.value.startsWith("rarity-")) option.hidden = option.disabled = active === "enemy";
      }
      if (active === "enemy" && sort.value.startsWith("rarity-")) sort.value = "default";
      window.WebUI.sorting.refresh();
    }
    const equipmentAttributes = gp$('[data-filter-section="gameplay-equipment-attribute"]');
    if (equipmentAttributes) equipmentAttributes.hidden = active !== "equipment";
  }

  function selectKind(kind) {
    const requested = findGameplayEntry(requestedGameplaySelection());
    restoreRequestedEnemyVariant(requested);
    if (!STATE.facets.active("kinds").has(kind) || (requested && !STATE.filtered.includes(requested))) {
      STATE.facets.reset({ silent: true });
      STATE.facets.set("kinds", [kind], { silent: true });
      gp$("#gameplay-q").value = "";
    }
    if (requested?.kind === kind) STATE.selected = requested;
    applyFilters();
    if (requested?.kind === kind) revealSelectedInList();
  }

  function restoreRequestedEnemyVariant(entry) {
    const id = requestedGameplaySelection();
    if (entry?.kind === "enemy" && entry.variants?.some((variant) => variant.id === id)) {
      STATE.enemyVariantIds.set(entry.id, id);
    }
  }

  function listTypeLabel(entry) {
    if (!entry) return "";
    if (entry.kind === "enemy") return enemyTypeFilterLabel(entry);
    if (entry.kind === "item") return itemTypeFilterLabel(entry);
    if (entry.kind === "weapon") return weaponTypeFilterLabel(entry);
    if (entry.kind === "equipment") return equipmentTypeFilterLabel(entry);
    if (entry.kind === "character") return characterPropertyFilterLabel(entry) || jobFilterLabel(entry);
    return "";
  }

  function listGroupLabel(entry) {
    return [kindLabel(entry && entry.kind), listTypeLabel(entry)].filter(Boolean).join(" / ");
  }

  function gameplayListGroupKey(entry) {
    if (entry.kind === "gem") return `gem:domain:${entry.domain?.id || "unknown"}`;
    return entry.kind === "equipment" && entry.suit?.id
      ? `equipment:suit:${entry.suit.id}` : `${entry.kind}:${gameplayListGroup(entry)}`;
  }

  function gameplayListGroup(entry) {
    if (entry.kind === "gem") return entry.domain?.name || text("gemUnknownRegion");
    if (entry.kind === "equipment" && entry.suit?.id) return entry.suit.name || entry.suit.id;
    return entry.kind === "character" ? jobFilterLabel(entry) || kindLabel(entry.kind)
      : listTypeLabel(entry) || kindLabel(entry.kind);
  }

  // Per-kind type groups are one cross-kind union: once any of them is
  // active, an entry passes only through its own kind's group, so a weapon
  // passes a character-property group exactly when its weapon-type group is
  // active (and decides it). Kinds without a type group never pass.
  const TYPE_GROUP_BY_KIND = {
    character: "characterProperties",
    weapon: "weaponTypes",
    equipment: "equipmentTypes",
    enemy: "enemyTypes",
    item: "itemTypes",
  };
  // [group id, section/container suffix, value key, value label, owning kind]
  const ENTRY_FACET_GROUPS = [
    ["jobs", "job", jobFilterKey, jobFilterLabel],
    ["characterProperties", "character-property", characterPropertyFilterKey, characterPropertyFilterLabel, "character"],
    ["mainAbilities", "main-ability", (entry) => abilityFilterKey(entry, "mainAttrType"), (entry) => abilityFilterLabel(entry, "mainAttrType"), "character"],
    ["subAbilities", "sub-ability", (entry) => abilityFilterKey(entry, "subAttrType"), (entry) => abilityFilterLabel(entry, "subAttrType"), "character"],
    ["weaponTypes", "weapon-type", weaponTypeFilterKey, weaponTypeFilterLabel, "weapon"],
    ["equipmentTypes", "equipment-type", equipmentTypeFilterKey, equipmentTypeFilterLabel, "equipment"],
    ["enemyTypes", "enemy-type", enemyTypeFilterKey, enemyTypeFilterLabel, "enemy"],
    ["itemTypes", "item-type", itemTypeFilterKey, itemTypeFilterLabel, "item"],
  ];
  const facetLabels = new Map(); // group id -> Map(value -> label from the loaded entries)
  const WEAPON_EFFECT_FACET_GROUPS = [
    ["weaponAttributes", "weapon-attribute", "weaponAttributeFilter"],
    ["weaponBonuses", "weapon-bonus", "weaponBonusFilter"],
    ["weaponPassives", "weapon-passive", "weaponPassiveFilter"],
  ];

  function createFacets() {
    const labelOf = (id) => (value) => facetLabels.get(id)?.get(value) || value;
    const entryGroups = ENTRY_FACET_GROUPS.map(([id, suffix, key, , kind]) => ({
      id,
      container: `#gameplay-${suffix}-filter`,
      section: `gameplay-${suffix}`,
      values: key,
      label: labelOf(id),
      order: id === "enemyTypes"
        ? (a, b) => ((ENEMY_TYPE_RANK[a] ?? 99) - (ENEMY_TYPE_RANK[b] ?? 99)) || String(labelOf(id)(a)).localeCompare(String(labelOf(id)(b)))
        : "natural",
      match: kind && ((entry, active) => (entry.kind === kind
        ? active.has(key(entry))
        : !!TYPE_GROUP_BY_KIND[entry.kind] && STATE.facets.isFiltered(TYPE_GROUP_BY_KIND[entry.kind]))),
    }));
    return window.WebUI.facets.create({
      countMode: "total",
      groups: [
        { id: "kinds", container: "#gameplay-kind-filter", section: "gameplay-kind", values: (entry) => entry.kind,
          label: kindLabel, className: (kind) => KIND_CHIP_CLASS[kind] || "kind-chip",
          order: (a, b) => kindRank(a) - kindRank(b) || a.localeCompare(b) },
        ...entryGroups,
        { id: "equipmentAttributes", container: "#gameplay-equipment-attribute-filter",
          section: "gameplay-equipment-attribute", values: equipmentAttributeLabels, order: "natural" },
        ...WEAPON_EFFECT_FACET_GROUPS.map(([id, suffix], index) => ({
          id, container: `#gameplay-${suffix}-filter`, section: `gameplay-${suffix}`,
          values: (entry) => gemPoolFilterValues(entry, index), countMode: "faceted", hideEmpty: true,
        })),
        { id: "gemDomains", container: "#gameplay-gem-domain-filter", section: "gameplay-gem-domain",
          values: (entry) => entry.kind === "gem" ? entry.domain?.id || "unknown" : [],
          label: (id) => gemDomains.get(id)?.name || text("gemUnknownRegion"),
          order: (a, b) => (gemDomains.get(a)?.sortId ?? 999) - (gemDomains.get(b)?.sortId ?? 999) || a.localeCompare(b),
          countMode: "faceted", hideEmpty: true },
        window.WebUI.updateBadges.filterGroup("gameplay", gameplayUpdateStatuses, { countMode: "faceted" }),
        { id: "rarities", container: "#gameplay-rarity-filter", section: "gameplay-rarity", values: rarityFilterKey,
          label: rarityFilterLabel, order: (a, b) => Number(b) - Number(a),
          countMode: "faceted", hideEmpty: true },
      ],
      onChange: () => applyFilters(),
    });
  }

  // Gem domain id -> domain, rebuilt per load so chip labels and ordering
  // do not rescan every entry per comparison.
  const gemDomains = new Map();

  function buildFilterChips({ render = true } = {}) {
    gemDomains.clear();
    for (const entry of STATE.entries) {
      if (entry.kind === "gem" && entry.domain?.id && !gemDomains.has(entry.domain.id)) gemDomains.set(entry.domain.id, entry.domain);
    }
    window.WebUI.updateBadges.syncFilter("gameplay", "gameplay", STATE.facets);
    for (const [id, , key, label] of ENTRY_FACET_GROUPS) {
      facetLabels.set(id, new Map(STATE.entries.map((entry) => [key(entry), label(entry)]).filter(([value]) => value)));
    }
    if (render) STATE.facets.render(STATE.entries);
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
    if (!STATE.facets.isFiltered("kinds")) STATE.facets.set("kinds", [STATE.selected?.kind || "character"], { silent: true });
    renderKindTabs();
    syncEquipmentAttributeSort();
    STATE.facets.render(STATE.entries);
    const rarityCounts = STATE.facets.counts("rarities");
    const validRarities = [...STATE.facets.active("rarities")].filter((value) => rarityCounts.get(value) > 0);
    if (validRarities.length !== STATE.facets.activeCount("rarities")) {
      STATE.facets.set("rarities", validRarities, { silent: true });
      STATE.facets.render(STATE.entries);
    }
    window.WebUI.continuousList.reset(gp$("#gameplay-list"));
    const tokens = parseQuery(gp$("#gameplay-q") && gp$("#gameplay-q").value);
    const scores = new Map();
    STATE.searchTokens = tokens;
    window.WebUI?.setFilterSectionActiveCounts?.({ "gameplay-basic": tokens.length ? 1 : 0 });
    STATE.filtered = STATE.facets.filter(STATE.entries).filter((entry) => {
      if (tokens.length) {
        const score = queryScore([entry.search, entry.linkedFileSearch, entry.title, entry.id, entry.group, entry.subtitle], tokens);
        if (score <= 0) return false;
        scores.set(entry, score);
      }
      return true;
    });
    // A multi-word query ranks entries by keyword-match count first; ties (and
    // single-word / no query) fall back to the stable kind/type ordering.
    const sort = gp$("#gameplay-sort")?.value || "default";
    const collator = new Intl.Collator(STATE.uiLocale === "en" ? "en" : "zh-CN", { numeric: true, sensitivity: "base" });
    const titleCompare = (a, b) => collator.compare(a.title || a.id || "", b.title || b.id || "")
      || collator.compare(a.id || "", b.id || "");
    const rankByScore = sort === "default" && tokens.length > 1;
    // Group order and "missing value last" placement stay outside the shared
    // comparator, whose direction toggle flips the sign of everything inside.
    const attributeLabel = sort.startsWith("equipment-attribute:") ? sort.slice("equipment-attribute:".length) : null;
    const directed = window.WebUI.sorting.comparator("gameplay-sort", (a, b) => {
      if (attributeLabel !== null) {
        const av = equipmentBaseAttributeValue(a, attributeLabel), bv = equipmentBaseAttributeValue(b, attributeLabel);
        return (av !== null && bv !== null ? bv - av : 0) || titleCompare(a, b);
      }
      if (rankByScore) {
        const delta = (scores.get(b) || 0) - (scores.get(a) || 0);
        if (delta) return delta;
      }
      if (sort === "title") return titleCompare(a, b);
      if (sort === "title-desc") return -titleCompare(a, b);
      if (sort.startsWith("rarity-")) {
        const ar = a.rarity === null || a.rarity === undefined || a.rarity === "" ? null : Number(a.rarity);
        const br = b.rarity === null || b.rarity === undefined || b.rarity === "" ? null : Number(b.rarity);
        if (ar === null && br !== null) return 1;
        if (br === null && ar !== null) return -1;
        return (ar !== null && br !== null ? (sort === "rarity-desc" ? br - ar : ar - br) : 0) || titleCompare(a, b);
      }
      if (sort === "type") return (a.kind === "enemy" && b.kind === "enemy"
        ? enemyTypeRank(a) - enemyTypeRank(b)
        : collator.compare(listTypeLabel(a), listTypeLabel(b))) || titleCompare(a, b);
      if (sort === "id") return collator.compare(a.id || "", b.id || "");
      return compareGameplayEntries(a, b);
    });
    STATE.filtered.sort((a, b) => {
      if (attributeLabel !== null) {
        const aMissing = equipmentBaseAttributeValue(a, attributeLabel) === null;
        const bMissing = equipmentBaseAttributeValue(b, attributeLabel) === null;
        if (aMissing !== bMissing) return aMissing ? 1 : -1;
        return directed(a, b);
      }
      return kindRank(a.kind) - kindRank(b.kind)
        || (a.kind === "gem" ? (a.domain?.sortId ?? 999) - (b.domain?.sortId ?? 999) : 0)
        || (a.kind === "enemy" ? enemyTypeRank(a) - enemyTypeRank(b) : 0)
        || collator.compare(gameplayListGroup(a), gameplayListGroup(b))
        || directed(a, b);
    });
    if (STATE.selected && !STATE.filtered.includes(STATE.selected)) STATE.selected = null;
    renderList();
  }

  function resetFilters() {
    const q = gp$("#gameplay-q");
    if (q) q.value = "";
    gp$("#gameplay-sort").value = "default";
    const kinds = STATE.facets.active("kinds");
    STATE.facets.reset({ silent: true });
    STATE.facets.set("kinds", kinds, { silent: true });
    applyFilters();
  }

  function applyUiStrings() {
    // #gameplay-tab is owned by the shared data-i18n loop in app.js
    // (gameplayTab in app_labels.js) — not repeated here.
    const pairs = [
      ["#gameplay-title", "title"],
      ["#gameplay-count-label", "countLabel"],
      ["#gameplay-basic-filter-label", "basicFilters"],
      ["#gameplay-sort-label", "sort"],
      ["#gameplay-sort-default", "sortDefault"],
      ["#gameplay-sort-title", "sortTitle"],
      ["#gameplay-sort-title-desc", "sortTitleDesc"],
      ["#gameplay-sort-rarity-desc", "sortRarityDesc"],
      ["#gameplay-sort-rarity-asc", "sortRarityAsc"],
      ["#gameplay-sort-type", "sortType"],
      ["#gameplay-sort-id", "sortId"],
      ["#gameplay-kind-label", "kind"],
      ["#gameplay-job-label", "job"],
      ["#gameplay-character-property-label", "element"],
      ["#gameplay-main-ability-label", "stat_main_attr"],
      ["#gameplay-sub-ability-label", "stat_sub_attr"],
      ["#gameplay-weapon-type-label", "weaponTypeFilter"],
      ...WEAPON_EFFECT_FACET_GROUPS.map(([, suffix, label]) => [`#gameplay-${suffix}-label`, label]),
      ["#gameplay-gem-domain-label", "gemRegion"],
      ["#gameplay-equipment-type-label", "equipmentTypeFilter"],
      ["#gameplay-equipment-attribute-label", "equipmentAttributeFilter"],
      ["#gameplay-enemy-type-label", "enemyTypeFilter"],
      ["#gameplay-item-type-label", "itemTypeFilter"],
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
    renderKindTabs();
    syncEquipmentAttributeSort();
    if (STATE.entries.length) renderList();
  }

  function validSoundEffectsPayload(payload) {
    return Boolean(payload && Number.isInteger(payload.schemaVersion) && payload.schemaVersion >= 1 && payload.characters && payload.enemies);
  }

  function loadGameplaySoundEffects(language, token) {
    const integration = STATE.integration;
    integration.soundEffectsStatus = "loading";
    fetchIntegrationJson(integrationPath("soundEffects", language), validSoundEffectsPayload)
      .then((payload) => ({ payload, error: "" }), (error) => ({ payload: null, error: String(error?.message || error) }))
      .then(async ({ payload, error }) => {
        if (integration.token !== token) return;
        // Sound sections depend on the base integration's ready state.
        if (integration.loading) await integration.loading;
        if (integration.token !== token) return;
        integration.soundEffects = payload;
        integration.soundEffectsStatus = "ready";
        // A missing sidecar stays visible: an empty sound section otherwise
        // looks like a valid zero-owner result.
        if (error) integration.errors.push({ kind: "soundEffects", message: error });
        const selected = STATE.selected;
        if (selected && (selected.kind === "character" || selected.kind === "enemy")
          && document.body.dataset.activeView === "gameplay" && !gp$("#gameplay-app")?.hidden) {
          renderDetail(selected);
        }
      });
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
      ["assets", integrationPath("assets", nextLanguage), (payload) => payload?.schemaVersion === "gameplayAssetRefs.v11" && typeof payload.entries === "object"],
    ];
    // The character/enemy sound sidecar is large (~100 MB), so it loads beside
    // the base integration instead of delaying it; sound sections fill in when
    // it arrives.
    loadGameplaySoundEffects(nextLanguage, token);
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
        // Asset refs are a purely visual enhancement and the projectile audio
        // links are an optional addition, so neither failure is an error.
        if (result.error && !["assets", "projectileAudio"].includes(result.kind)) integration.errors.push({ kind: result.kind, message: result.error });
      }
      integration.indexes = buildIntegrationIndexes();
      integration.status = "ready";
      integration.loading = null;
      refreshGameplayFileSearch();
      if (document.body.dataset.activeView === "gameplay" && !gp$("#gameplay-app")?.hidden) {
        if (gp$("#gameplay-q")?.value.trim()) applyFilters();
        else renderList(); // The list also renders the selected detail.
      }
      return integration;
    }).catch((error) => {
      if (integration.token !== token) return null;
      integration.status = "ready";
      integration.loading = null;
      integration.errors = [{ kind: "integration", message: String(error?.message || error) }];
      integration.indexes = buildIntegrationIndexes();
      if (document.body.dataset.activeView === "gameplay" && !gp$("#gameplay-app")?.hidden && STATE.selected) renderDetail(STATE.selected);
      return integration;
    });
    integration.loading = promise;
    return promise;
  }

  async function loadGameplay(force = false, { render = true } = {}) {
    const language = currentLanguage();
    if (!force && STATE.index && STATE.language === language) {
      if (STATE.integration.language !== language || STATE.integration.status === "idle") void loadGameplayIntegration(language);
      return STATE.index;
    }
    if (!force && STATE.loading && STATE.language === language) return STATE.loading;
    const token = ++STATE.loadToken;
    ++STATE.integration.token;
    STATE.language = language;
    STATE.index = null;
    STATE.entries = [];
    STATE.filtered = [];
    STATE.selected = null;
    if (force) { itemIndexes.clear(); itemAssets = null; }
    window.WebUI.showLoader?.("gameplay", text("loading"));
    const pending = (async () => {
      try {
        const res = await fetchWithProgress(gameplayDataPath(language), {
          onProgress: window.WebUI.loaderProgress("gameplay", () => token === STATE.loadToken),
        });
        if (!res.ok) {
          if (res.status === 404) throw new Error(text("noData"));
          throw new Error(`${res.status} ${res.statusText}`.trim());
        }
        const data = await res.json();
        if (token !== STATE.loadToken) return null;
        window.WebUI.updateLoaderPhase("gameplay", "preparing");
        await Promise.all([window.WebUI.updateBadges.load("gameplay"), window.WebUI.updateBadges.loadFiles()]);
        if (token !== STATE.loadToken) return null;
        window.WebUI.updateLoaderPhase("gameplay", "rendering");
        await window.WebUI.nextPaint();
        if (token !== STATE.loadToken) return null;
        STATE.index = data || {};
        STATE.entries = Array.isArray(data.entries) ? data.entries : [];
        refreshGameplayFileSearch();
        STATE.selected = findGameplayEntry(requestedGameplaySelection());
        restoreRequestedEnemyVariant(STATE.selected);
        if (STATE.selected) STATE.facets.set("kinds", [STATE.selected.kind], { silent: true });
        gp$("#gameplay-count").textContent = formatNumber(STATE.entries.length);
        buildFilterChips({ render });
        if (render) applyFilters();
        await window.WebUI.nextPaint();
        if (token !== STATE.loadToken) return null;
        void loadGameplayIntegration(language, force);
        return STATE.index;
      } catch (err) {
        if (token !== STATE.loadToken) return null;
        STATE.index = null;
        STATE.entries = [];
        STATE.filtered = [];
        gp$("#gameplay-count").textContent = "0";
        renderListNote(text("loadError", { message: err && err.message ? err.message : String(err) }));
        renderDetail(null);
        return null;
      } finally {
        if (token === STATE.loadToken) {
          window.WebUI.hideLoader?.("gameplay");
          STATE.loading = null;
        }
      }
    })();
    STATE.loading = pending;
    return STATE.loading;
  }

  function bindEvents() {
    gp$("#gameplay-q")?.addEventListener("input", () => applyFilters());
    gp$("#gameplay-sort")?.addEventListener("change", () => applyFilters());
    gp$("#gameplay-reset")?.addEventListener("click", () => resetFilters());
    gp$("#gameplay-reveal-current")?.addEventListener("click", () => revealSelectedInList());
    window.addEventListener("webui:ui-locale-changed", (event) => {
      STATE.uiLocale = normalizeUiLocale(event.detail && event.detail.locale) || STATE.uiLocale;
      applyUiStrings();
    });
    window.addEventListener("webui:debug-changed", (event) => {
      STATE.showDebug = Boolean(event.detail && event.detail.enabled);
      if (STATE.selected) renderDetail(STATE.selected);
    });
    window.addEventListener("webui:gender-changed", () => {
      if (STATE.index) renderList();
      if (STATE.selected && isEndministrator(STATE.selected)) renderDetail(STATE.selected);
    });
  }

  function init() {
    if (!gp$("#gameplay-app")) return;
    const sidebarHeader = gp$("#gameplay-left > header");
    sidebarHeader.classList.add("gameplay-sidebar-header");
    sidebarHeader.innerHTML = window.WebUI.gameplayDetail.sidebarHeader({
      statsHtml: '<div id="gameplay-stats"><span id="gameplay-count">?</span> <span id="gameplay-count-label">entries</span></div>',
      toggleId: "gameplay-filter-toggle", panelId: "gameplay-filter-panel", resetId: "gameplay-reset",
    });
    STATE.uiLocale = resolveInitialUiLocale();
    STATE.language = currentLanguage();
    STATE.showDebug = document.body.classList.contains("show-debug")
      || gp$("#show-debug")?.getAttribute("aria-pressed") === "true";
    STATE.collapsedKinds = loadCollapsedKinds();
    STATE.levelFraction = loadLevelFraction();
    ensurePanelToggle();
    STATE.facets = createFacets();
    bindEvents();
    applyUiStrings();
  }

  window.WebUI.gameplay = {
    hasEntry: (kind, id, language) => !!STATE.index && STATE.language === language && STATE.entries.some((entry) => entry.kind === kind && entry.id === id),
    load: loadGameplay, selectKind, itemContent, itemGallery, itemImages, assetGallery: renderGameplayAssetGallery,
    count: (kind) => STATE.index && STATE.language === currentLanguage() ? STATE.entries.filter((entry) => entry.kind === kind).length : null,
    statLabel: statAttrLabel,
    // Pure presentation reuse for independently published battle-stage Buffs.
    // ``values`` carries the applier's blackboard overrides (a Map).
    buffRows: (record, values) => window.WebUI.gameplayMechanics.buffRows(record, {
      text, statAttrLabel, stackingLabel: buffStackingLabel, decodedActions: window.WebUI.gameplayMechanics.decodedBuffActions, values,
    }),
    invalidateItems: () => { itemIndexes.clear(); itemAssets = null; },
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
