(() => {
  const FILTER_PANEL_STORAGE_KEY = "gameplay_filters_collapsed";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const TEXTS = {
    zh: {
      tab: "\u5b9e\u6218",
      title: "\u5b9e\u6218\u6570\u636e",
      countLabel: "\u6761\u76ee",
      search: "\u641c\u7d22\u6b66\u5668 / \u88c5\u5907 / \u89d2\u8272 / \u6280\u80fd / \u6570\u503c",
      showFilters: "\u663e\u793a\u7b5b\u9009",
      hideFilters: "\u9690\u85cf\u7b5b\u9009",
      reset: "\u91cd\u7f6e\u7b5b\u9009",
      basicFilters: "\u57fa\u7840\u7b5b\u9009",
      kind: "\u7c7b\u578b",
      group: "\u5206\u7ec4",
      job: "\u804c\u4e1a",
      characterPropertyFilter: "\u4e3b\u5c5e\u6027",
      weaponTypeFilter: "\u6b66\u5668\u7c7b\u578b",
      equipmentTypeFilter: "\u88c5\u5907\u7c7b\u578b",
      rareLevel: "\u7a00\u6709\u5ea6",
      listUnit: "\u6761",
      empty: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u6761\u5b9e\u6218\u6570\u636e",
      noData: "\u5c1a\u672a\u6784\u5efa\u5b9e\u6218\u6570\u636e\u3002\u8fd0\u884c python scripts\\build_gameplay_data.py\u3002",
      noResults: "\u6ca1\u6709\u5339\u914d\u7684\u6761\u76ee",
      loading: "\u52a0\u8f7d\u5b9e\u6218\u6570\u636e...",
      loadError: "\u52a0\u8f7d\u5931\u8d25: {message}",
      weapon: "\u6b66\u5668",
      character: "\u89d2\u8272",
      equipment: "\u88c5\u5907",
      storyWiki: "\u5267\u60c5 Wiki",
      openStoryWiki: "\u5728\u5267\u60c5\u9875\u6253\u5f00",
      id: "ID",
      rarity: "\u7a00\u6709\u5ea6",
      groupFact: "\u5206\u7ec4",
      weaponType: "\u6b66\u5668\u7c7b\u578b",
      maxLevel: "\u6700\u5927\u7b49\u7ea7",
      modelPath: "\u6a21\u578b\u8def\u5f84",
      baseAtkMax: "\u6ee1\u7ea7\u57fa\u7840\u653b\u51fb",
      profession: "\u804c\u4e1a",
      element: "\u5c5e\u6027",
      defaultWeapon: "\u9ed8\u8ba4\u6b66\u5668",
      description: "\u63cf\u8ff0",
      weaponSkills: "\u6b66\u5668\u63d0\u4f9b\u7684\u6280\u80fd / \u6548\u679c",
      characterSkills: "\u89d2\u8272\u6280\u80fd",
      talents: "\u5929\u8d4b / \u88ab\u52a8",
      level: "\u7b49\u7ea7",
      effect: "\u6548\u679c",
      values: "\u6570\u503c",
      maxEffect: "\u6ee1\u7ea7\u6548\u679c",
      source: "\u6765\u6e90",
      fileName: "\u6587\u4ef6\u540d",
      internalName: "\u5185\u90e8\u540d",
      actionData: "\u52a8\u4f5c\u6570\u636e",
      actionSkillIds: "\u52a8\u4f5c ID",
      levelUpCosts: "\u5347\u7ea7\u6d88\u8017",
      gold: "\u91d1\u5e01",
      materials: "\u6750\u6599",
      rank: "\u9636",
      unlockHint: "\u89e3\u9501\u6761\u4ef6",
      requiredItems: "\u9700\u6c42\u6750\u6599",
      passiveSkill: "\u88ab\u52a8\u6280\u80fd",
      factorySkill: "\u57fa\u5efa\u6280\u80fd",
      equipmentBreak: "\u88c5\u5907\u7a81\u7834",
      attributeNode: "\u5c5e\u6027\u8282\u70b9",
      upgradeNodes: "\u7a81\u7834\u8282\u70b9",
      selectedLevel: "\u663e\u793a\u7b49\u7ea7",
      weaponStats: "\u6b66\u5668\u5c5e\u6027",
      equipmentStats: "\u88c5\u5907\u5c5e\u6027",
      equipmentSuit: "\u5957\u88c5\u6548\u679c",
      equipmentFormula: "\u5236\u9020\u914d\u65b9",
      partType: "\u90e8\u4f4d",
      minWearLevel: "\u7a7f\u6234\u7b49\u7ea7",
      domain: "\u5730\u533a",
      suit: "\u5957\u88c5",
      formula: "\u914d\u65b9",
      pack: "\u5236\u9020\u5305",
      unlock: "\u89e3\u9501",
      equipCount: "\u4ef6\u6570",
      displayAttrs: "\u5c55\u793a\u5c5e\u6027",
      characterStats: "\u89d2\u8272\u5c5e\u6027",
      statCheckpoints: "\u5c5e\u6027\u6570\u503c",
      breakStage: "\u7a81\u7834\u9636\u6bb5",
      stat_baseAtk: "\u57fa\u7840\u653b\u51fb",
      stat_hp: "\u751f\u547d\u503c",
      stat_atk: "\u653b\u51fb\u529b",
      stat_def: "\u9632\u5fa1\u529b",
      stat_str: "\u529b\u91cf",
      stat_agi: "\u654f\u6377",
      stat_wis: "\u667a\u8bc6",
      stat_will: "\u610f\u5fd7",
      stat_physical_damage_taken: "受到的物理伤害",
      stat_fire_damage_taken: "受到的灼热伤害",
      stat_pulse_damage_taken: "受到的电磁伤害",
      stat_cryst_damage_taken: "受到的寒冷伤害",
      stat_natural_damage_taken: "受到的自然伤害",
      stat_ether_damage_taken: "受到的超域伤害",
      stat_critical_rate: "暴击率",
      stat_normal_attack_efficiency: "普通攻击效率",
      stat_ultimate_skill_efficiency: "终结技充能效率",
      stat_heal_taken: "受治疗效果",
      stat_healing_taken_scalar: "受治疗倍率",
      stat_fire_burst_damage: "灼热爆发伤害",
      stat_pulse_burst_damage: "电磁爆发伤害",
      stat_cryst_burst_damage: "寒冷爆发伤害",
      stat_natural_burst_damage: "自然爆发伤害",
      stat_ultimate_sp_gain: "终结技充能效率",
      stat_broken_unit_damage: "失衡目标伤害",
      stat_all_damage_taken_scalar: "受到的所有伤害",
      stat_all_skill_damage: "所有技能伤害",
      stat_cryst_pulse_damage: "寒冷和电磁伤害加成",
      stat_spell_damage: "法术伤害",
      stat_main_attr: "主能力",
      stat_sub_attr: "副能力",
      stat_fire_natural_damage: "灼热和自然伤害",
      stat_heal_output: "\u6cbb\u7597\u6548\u679c",
      stat_skill_damage: "\u6218\u6280\u4f24\u5bb3",
      stat_combo_skill_damage: "\u8fde\u643a\u6280\u4f24\u5bb3",
      stat_normal_attack_damage: "\u666e\u653b\u4f24\u5bb3",
      stat_physical_damage: "\u7269\u7406\u4f24\u5bb3",
      stat_fire_damage: "\u707c\u70ed\u4f24\u5bb3",
      stat_pulse_damage: "\u7535\u78c1\u4f24\u5bb3",
      stat_cryst_damage: "\u5bd2\u51b7\u4f24\u5bb3",
      stat_natural_damage: "\u81ea\u7136\u4f24\u5bb3",
      stat_infliction: "\u6e90\u77f3\u6280\u827a\u5f3a\u5ea6",
      progression: "\u517b\u6210",
      upgradeCurve: "\u5347\u7ea7\u66f2\u7ebf",
      weaponBreakthroughs: "\u6b66\u5668\u7a81\u7834",
      weaponTalentBounds: "\u6b66\u5668\u5929\u8d4b\u4e0a\u9650",
      weaponStatCurve: "\u6b66\u5668\u5c5e\u6027\u66f2\u7ebf",
      characterStatCurve: "\u89d2\u8272\u5c5e\u6027\u66f2\u7ebf",
      rawMaxLevel: "\u539f\u59cb\u6700\u5927\u7b49\u7ea7",
      extraRawRows: "\u8d85\u51fa\u53ef\u7528\u4e0a\u9650\u884c",
      characterLevelCurve: "\u89d2\u8272\u7b49\u7ea7\u66f2\u7ebf",
      characterBreakStages: "\u7a81\u7834\u9636\u6bb5",
      characterBreakthroughs: "\u7a81\u7834\u6d88\u8017",
      characterPotentials: "\u6f5c\u80fd",
      stage: "\u9636\u6bb5",
      levelRange: "\u7b49\u7ea7\u8303\u56f4",
      baseAtk: "\u57fa\u7840\u653b\u51fb",
      exp: "\u7ecf\u9a8c",
      cumulativeExp: "\u7d2f\u8ba1\u7ecf\u9a8c",
      cumulativeGold: "\u7d2f\u8ba1\u91d1\u5e01",
      skillBounds: "\u6280\u80fd\u8303\u56f4",
      skillCaps: "\u6280\u80fd\u4e0a\u9650",
      breakStatus: "\u7a81\u7834\u72b6\u6001",
      expItems: "\u7ecf\u9a8c\u6750\u6599",
      potential: "\u6f5c\u80fd",
      showLevel: "\u663e\u793a\u7b49\u7ea7",
      generated: "\u751f\u6210\u65f6\u95f4",
    },
    en: {
      tab: "Gameplay",
      title: "Gameplay Data",
      countLabel: "entries",
      search: "Search weapon / equipment / character / skill / stat",
      showFilters: "Show filters",
      hideFilters: "Hide filters",
      reset: "Reset filters",
      basicFilters: "Basic filters",
      kind: "Kind",
      group: "Group",
      job: "Job",
      characterPropertyFilter: "Main property",
      weaponTypeFilter: "Weapon type",
      equipmentTypeFilter: "Equipment type",
      rareLevel: "Rare level",
      listUnit: "items",
      empty: "Select a gameplay entry",
      noData: "Gameplay data has not been built. Run python scripts\\build_gameplay_data.py.",
      noResults: "No matching entries",
      loading: "Loading gameplay data...",
      loadError: "Load failed: {message}",
      weapon: "Weapon",
      character: "Character",
      equipment: "Equipment",
      storyWiki: "Story wiki",
      openStoryWiki: "Open in Story",
      id: "ID",
      rarity: "Rarity",
      groupFact: "Group",
      weaponType: "Weapon type",
      maxLevel: "Max level",
      modelPath: "Model path",
      baseAtkMax: "Base ATK at max",
      profession: "Profession",
      element: "Element",
      defaultWeapon: "Default weapon",
      description: "Description",
      weaponSkills: "Weapon-provided skills / effects",
      characterSkills: "Character skills",
      talents: "Talents / passives",
      level: "Level",
      effect: "Effect",
      values: "Values",
      maxEffect: "Max effect",
      source: "Source",
      fileName: "File name",
      internalName: "Internal name",
      actionData: "Action data",
      actionSkillIds: "Action IDs",
      levelUpCosts: "Level-up costs",
      gold: "Gold",
      materials: "Materials",
      rank: "Rank",
      unlockHint: "Unlock",
      requiredItems: "Required materials",
      passiveSkill: "Passive skill",
      factorySkill: "Factory skill",
      equipmentBreak: "Equipment break",
      attributeNode: "Attribute node",
      upgradeNodes: "Upgrade nodes",
      selectedLevel: "Selected level",
      weaponStats: "Weapon stats",
      equipmentStats: "Equipment stats",
      equipmentSuit: "Suit effects",
      equipmentFormula: "Crafting formula",
      partType: "Part",
      minWearLevel: "Wear level",
      domain: "Domain",
      suit: "Suit",
      formula: "Formula",
      pack: "Pack",
      unlock: "Unlock",
      equipCount: "Pieces",
      displayAttrs: "Display attrs",
      characterStats: "Character stats",
      statCheckpoints: "Stat values",
      breakStage: "Break stage",
      stat_baseAtk: "Base ATK",
      stat_hp: "HP",
      stat_atk: "ATK",
      stat_def: "DEF",
      stat_str: "STR",
      stat_agi: "AGI",
      stat_wis: "WIS",
      stat_will: "WILL",
      stat_physical_damage_taken: "Physical Taken",
      stat_fire_damage_taken: "Fire Taken",
      stat_pulse_damage_taken: "Pulse Taken",
      stat_cryst_damage_taken: "Cold Taken",
      stat_natural_damage_taken: "Natural Taken",
      stat_ether_damage_taken: "Ether Taken",
      stat_critical_rate: "Critical Rate",
      stat_normal_attack_efficiency: "Normal ATK Efficiency",
      stat_ultimate_skill_efficiency: "Ultimate Efficiency",
      stat_heal_taken: "Heal Taken",
      stat_healing_taken_scalar: "Healing Taken Scalar",
      stat_fire_burst_damage: "Fire Burst DMG",
      stat_pulse_burst_damage: "Pulse Burst DMG",
      stat_cryst_burst_damage: "Cold Burst DMG",
      stat_natural_burst_damage: "Natural Burst DMG",
      stat_ultimate_sp_gain: "Ultimate SP Gain",
      stat_broken_unit_damage: "Broken Target DMG",
      stat_fire_natural_damage: "Fire / Natural DMG",
      stat_heal_output: "Heal Output",
      stat_skill_damage: "Skill DMG",
      stat_combo_skill_damage: "Combo DMG",
      stat_normal_attack_damage: "Normal ATK DMG",
      stat_physical_damage: "Physical DMG",
      stat_fire_damage: "Fire DMG",
      stat_pulse_damage: "Pulse DMG",
      stat_cryst_damage: "Cold DMG",
      stat_natural_damage: "Natural DMG",
      stat_infliction: "Infliction",
      progression: "Progression",
      upgradeCurve: "Upgrade curve",
      weaponBreakthroughs: "Weapon breakthroughs",
      weaponTalentBounds: "Weapon talent bounds",
      weaponStatCurve: "Weapon stat curve",
      characterStatCurve: "Character stat curve",
      rawMaxLevel: "Raw max level",
      extraRawRows: "Rows beyond playable cap",
      characterLevelCurve: "Character level curve",
      characterBreakStages: "Break stages",
      characterBreakthroughs: "Breakthrough costs",
      characterPotentials: "Potentials",
      stage: "Stage",
      levelRange: "Level range",
      baseAtk: "Base ATK",
      exp: "EXP",
      cumulativeExp: "Cumulative EXP",
      cumulativeGold: "Cumulative gold",
      skillBounds: "Skill bounds",
      skillCaps: "Skill caps",
      breakStatus: "Break status",
      expItems: "EXP items",
      potential: "Potential",
      showLevel: "Shown level",
      generated: "Generated",
    },
  };

  const {
    $,
    applyTemplate,
    escapeHtml,
    fetchWithProgress,
    formatNumber,
    normalizeUiLocale,
    textIncludes,
  } = window.WebUI;

  const STATE = {
    uiLocale: "zh",
    language: "CN",
    index: null,
    entries: [],
    filtered: [],
    selected: null,
    loading: null,
    filters: {
      kinds: new Set(),
      jobs: new Set(),
      characterProperties: new Set(),
      weaponTypes: new Set(),
      equipmentTypes: new Set(),
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
    return `data/lang/${encodeURIComponent(language)}/gameplay/index.json`;
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
    return kind === "weapon" ? text("weapon") : kind === "equipment" ? text("equipment") : kind === "character" ? text("character") : String(kind || "");
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

  function renderDetailTags(tags, entry) {
    const chips = dedupeDetailTags(tags).map((tag) => {
      const kindAttr = tag.kind ? ` data-kind="${escapeHtml(tag.kind)}"` : "";
      return `<span class="gameplay-detail-tag"${kindAttr}><span>${escapeHtml(tag.label || "")}</span><b${tag.mono ? ' class="mono"' : ""}>${escapeHtml(formatValue(tag.value))}</b></span>`;
    });
    const wiki = renderStoryWikiLink(entry);
    if (wiki) chips.unshift(wiki);
    return chips.join("");
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

  function storyWikiLinkLabel(key, index, total) {
    if (total <= 1) return text("openStoryWiki");
    const suffix = String(key || "").replace(/^wiki_chr_\d+_/, "").replace(/^wiki_/, "");
    return suffix || `${index + 1}`;
  }

  function renderStoryWikiLink(entry) {
    const keys = storyWikiKeys(entry);
    return keys.map((key, index) => {
      const href = storyWikiHrefForKey(key);
      if (!href) return "";
      return `<a class="gameplay-detail-tag gameplay-detail-wiki-link gameplay-wiki-link" href="${escapeHtml(href)}"><span>${escapeHtml(text("storyWiki"))}</span><b>${escapeHtml(storyWikiLinkLabel(key, index, keys.length))}</b></a>`;
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

  function renderIdChips(items) {
    const rows = (items || [])
      .filter(Boolean)
      .map((item) => `<span class="gameplay-value-chip"><b>${escapeHtml(text("id"))}</b>${escapeHtml(item)}</span>`);
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

  function statAttrLabel(attr) {
    const key = `stat_${attr && attr.key || ""}`;
    const translated = text(key);
    return translated === key ? (attr && (attr.label || attr.key) || "") : translated;
  }

  function statLevelLabel(row) {
    const parts = [];
    if (row && row.level !== undefined && row.level !== null) parts.push(`${text("level")} ${formatValue(row.level)}`);
    if (row && row.breakStage !== undefined && row.breakStage !== null) parts.push(`${text("breakStage")} ${formatValue(row.breakStage)}`);
    return parts.join(" / ");
  }


  function renderStatPane(row, active) {
    return `<div class="gameplay-level-pane gameplay-stat-pane" data-level-label="${escapeHtml(statLevelLabel(row))}"${active ? "" : " hidden"}>
      <div class="gameplay-level-effect">${renderStatAttrs(row) || `<span class="muted">-</span>`}</div>
    </div>`;
  }

  function renderStats(stats) {
    const rows = ((stats && (stats.rows || stats.checkpoints)) || []).filter((row) => row && (row.attrs || []).length);
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
      : `<div class="gameplay-level-table">${rows.map((row) => `<div class="gameplay-level-row gameplay-stat-row">
        <div class="gameplay-level-num">${escapeHtml(statLevelLabel(row))}</div>
        <div class="gameplay-level-effect">${renderStatAttrs(row) || `<span class="muted">-</span>`}</div>
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

  function renderChipPairs(pairs) {
    const rows = (pairs || [])
      .filter((item) => item && item.value !== undefined && item.value !== null && item.value !== "")
      .map((item) => `<span class="gameplay-value-chip"><b>${escapeHtml(item.label)}</b>${escapeHtml(formatValue(item.value))}</span>`);
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
        section(text("weaponStats"), renderStats(entry.stats)),
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
        section(text("characterStats"), renderStats(entry.stats)),
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
    sliders.forEach((slider) => {
      const max = Number(slider.max || requested);
      slider.value = String(Math.max(0, Math.min(requested, max)));
      syncLevelCard(slider);
    });
  }

  function bindLevelSliders(root) {
    root.querySelectorAll(".gameplay-level-slider").forEach((input) => {
      input.addEventListener("input", () => syncLevelSlider(input));
      syncLevelCard(input);
    });
  }

  function renderDetail(entry) {
    const empty = gp$("#gameplay-empty");
    const detail = gp$("#gameplay-detail");
    if (!entry || !detail) {
      if (empty) empty.hidden = false;
      if (detail) detail.hidden = true;
      return;
    }
    if (empty) empty.hidden = true;
    detail.hidden = false;
    gp$("#gameplay-detail-title").textContent = entry.title || entry.id || "";
    const rendered = entry.kind === "weapon" ? renderWeaponDetail(entry) : entry.kind === "equipment" ? renderEquipmentDetail(entry) : renderCharacterDetail(entry);
    const detailTags = [
      fact(text("kind"), kindLabel(entry.kind), { kind: entry.kind }),
      ...(rendered.facts || []),
    ];
    gp$("#gameplay-detail-meta").innerHTML = renderDetailTags(detailTags, entry);
    gp$("#gameplay-detail-body").innerHTML = rendered.body || "";
    bindLevelSliders(detail);
  }

  function renderListNote(message) {
    const list = gp$("#gameplay-list");
    if (list) list.innerHTML = `<div class="gameplay-list-note">${escapeHtml(message)}</div>`;
    gp$("#gameplay-shown").textContent = "0";
    gp$("#gameplay-total").textContent = formatNumber(STATE.entries.length || 0);
    renderDetail(null);
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
    list.innerHTML = STATE.filtered.map((entry) => {
      const key = `${entry.kind}:${entry.id}`;
      const selected = key === selectedId ? " is-selected" : "";
      return `<button class="gameplay-row${selected}" type="button" data-key="${escapeHtml(key)}">
        <div class="gameplay-row-head">
          <span class="gameplay-kind-badge" data-kind="${escapeHtml(entry.kind || "")}">${escapeHtml(kindLabel(entry.kind))}</span>
          <span class="gameplay-row-name">${escapeHtml(entry.title || entry.id || "")}</span>
        </div>
        <div class="gameplay-row-meta">${escapeHtml(entrySubtitle(entry) || entry.group || "")}</div>
        <div class="gameplay-row-path">${escapeHtml(entry.kind === "weapon" ? (entry.fileName || entry.id || "") : (entry.id || ""))}</div>
      </button>`;
    }).join("");
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

  function typeFiltersMatch(entry) {
    const hasCharacterProperties = STATE.filters.characterProperties.size > 0;
    const hasWeaponTypes = STATE.filters.weaponTypes.size > 0;
    const hasEquipmentTypes = STATE.filters.equipmentTypes.size > 0;
    if (!hasCharacterProperties && !hasWeaponTypes && !hasEquipmentTypes) return true;
    if (entry && entry.kind === "character") return hasCharacterProperties && STATE.filters.characterProperties.has(characterPropertyFilterKey(entry));
    if (entry && entry.kind === "weapon") return hasWeaponTypes && STATE.filters.weaponTypes.has(weaponTypeFilterKey(entry));
    if (entry && entry.kind === "equipment") return hasEquipmentTypes && STATE.filters.equipmentTypes.has(equipmentTypeFilterKey(entry));
    return false;
  }
  function buildFilterChips() {
    const kindCounts = countBy(STATE.entries, (entry) => entry.kind);
    const jobCounts = countBy(STATE.entries, (entry) => jobFilterKey(entry));
    const propertyCounts = countBy(STATE.entries, (entry) => characterPropertyFilterKey(entry));
    const weaponTypeCounts = countBy(STATE.entries, (entry) => weaponTypeFilterKey(entry));
    const equipmentTypeCounts = countBy(STATE.entries, (entry) => equipmentTypeFilterKey(entry));
    const rarityCounts = countBy(STATE.entries, (entry) => rarityFilterKey(entry));
    const jobLabels = new Map(STATE.entries.map((entry) => [jobFilterKey(entry), jobFilterLabel(entry)]).filter(([value]) => value));
    const propertyLabels = new Map(STATE.entries.map((entry) => [characterPropertyFilterKey(entry), characterPropertyFilterLabel(entry)]).filter(([value]) => value));
    const weaponTypeLabels = new Map(STATE.entries.map((entry) => [weaponTypeFilterKey(entry), weaponTypeFilterLabel(entry)]).filter(([value]) => value));
    const equipmentTypeLabels = new Map(STATE.entries.map((entry) => [equipmentTypeFilterKey(entry), equipmentTypeFilterLabel(entry)]).filter(([value]) => value));
    const kindItems = [...kindCounts.keys()].sort().map((value) => ({ value, label: kindLabel(value), count: kindCounts.get(value) }));
    const jobItems = [...jobCounts.keys()].sort((a, b) => String(jobLabels.get(a) || a).localeCompare(String(jobLabels.get(b) || b))).map((value) => ({ value, label: jobLabels.get(value) || value, count: jobCounts.get(value) }));
    const propertyItems = [...propertyCounts.keys()].sort((a, b) => String(propertyLabels.get(a) || a).localeCompare(String(propertyLabels.get(b) || b))).map((value) => ({ value, label: propertyLabels.get(value) || value, count: propertyCounts.get(value) }));
    const weaponTypeItems = [...weaponTypeCounts.keys()].sort((a, b) => String(weaponTypeLabels.get(a) || a).localeCompare(String(weaponTypeLabels.get(b) || b))).map((value) => ({ value, label: weaponTypeLabels.get(value) || value, count: weaponTypeCounts.get(value) }));
    const equipmentTypeItems = [...equipmentTypeCounts.keys()].sort((a, b) => String(equipmentTypeLabels.get(a) || a).localeCompare(String(equipmentTypeLabels.get(b) || b))).map((value) => ({ value, label: equipmentTypeLabels.get(value) || value, count: equipmentTypeCounts.get(value) }));
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
    window.WebUI.filters.buildChips("#gameplay-rarity-filter", rarityItems, {
      active: STATE.filters.rarities,
      onToggle: () => applyFilters(),
    });
  }
  function applyFilters() {
    const q = String((gp$("#gameplay-q") && gp$("#gameplay-q").value) || "").trim().toLowerCase();
    STATE.filtered = STATE.entries.filter((entry) => {
      if (STATE.filters.kinds.size && !STATE.filters.kinds.has(entry.kind)) return false;
      if (STATE.filters.jobs.size && !STATE.filters.jobs.has(jobFilterKey(entry))) return false;
      if (STATE.filters.rarities.size && !STATE.filters.rarities.has(rarityFilterKey(entry))) return false;
      if (!typeFiltersMatch(entry)) return false;
      if (q) {
        const haystack = [entry.search, entry.title, entry.id, entry.group, entry.subtitle].join(" ");
        if (!textIncludes(haystack, q)) return false;
      }
      return true;
    }).sort((a, b) => {
      const order = { weapon: 0, equipment: 1, character: 2 };
      const ak = order[a.kind] ?? 9;
      const bk = order[b.kind] ?? 9;
      if (ak !== bk) return ak - bk;
      const ar = Number(a.rarity || 0);
      const br = Number(b.rarity || 0);
      if (ar !== br) return br - ar;
      return String(a.title || a.id || "").localeCompare(String(b.title || b.id || ""));
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
      ["#gameplay-rarity-label", "rareLevel"],
      ["#gameplay-reset", "reset"],
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
    ensurePanelToggle();
    bindEvents();
    applyUiStrings();
    maybeLoadGameplay();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
