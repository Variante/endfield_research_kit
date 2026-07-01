(() => {
  const FILTER_PANEL_STORAGE_KEY = "gameplay_filters_collapsed";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const TEXTS = {
    zh: {
      tab: "\u5b9e\u6218",
      title: "\u5b9e\u6218\u6570\u636e",
      countLabel: "\u6761\u76ee",
      search: "\u641c\u7d22\u6b66\u5668 / \u89d2\u8272 / \u6280\u80fd / \u6570\u503c",
      showFilters: "\u663e\u793a\u7b5b\u9009",
      hideFilters: "\u9690\u85cf\u7b5b\u9009",
      reset: "\u91cd\u7f6e\u7b5b\u9009",
      basicFilters: "\u57fa\u7840\u7b5b\u9009",
      kind: "\u7c7b\u578b",
      group: "\u5206\u7ec4",
      listUnit: "\u6761",
      empty: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u6761\u5b9e\u6218\u6570\u636e",
      noData: "\u5c1a\u672a\u6784\u5efa\u5b9e\u6218\u6570\u636e\u3002\u8fd0\u884c python scripts\\build_gameplay_data.py\u3002",
      noResults: "\u6ca1\u6709\u5339\u914d\u7684\u6761\u76ee",
      loading: "\u52a0\u8f7d\u5b9e\u6218\u6570\u636e...",
      loadError: "\u52a0\u8f7d\u5931\u8d25: {message}",
      weapon: "\u6b66\u5668",
      character: "\u89d2\u8272",
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
      itemDescription: "\u7269\u54c1\u63cf\u8ff0",
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
      progression: "\u517b\u6210",
      upgradeCurve: "\u5347\u7ea7\u66f2\u7ebf",
      weaponBreakthroughs: "\u6b66\u5668\u7a81\u7834",
      weaponTalentBounds: "\u6b66\u5668\u5929\u8d4b\u4e0a\u9650",
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
      search: "Search weapon / character / skill / stat",
      showFilters: "Show filters",
      hideFilters: "Hide filters",
      reset: "Reset filters",
      basicFilters: "Basic filters",
      kind: "Kind",
      group: "Group",
      listUnit: "items",
      empty: "Select a gameplay entry",
      noData: "Gameplay data has not been built. Run python scripts\\build_gameplay_data.py.",
      noResults: "No matching entries",
      loading: "Loading gameplay data...",
      loadError: "Load failed: {message}",
      weapon: "Weapon",
      character: "Character",
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
      itemDescription: "Item description",
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
      progression: "Progression",
      upgradeCurve: "Upgrade curve",
      weaponBreakthroughs: "Weapon breakthroughs",
      weaponTalentBounds: "Weapon talent bounds",
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
      groups: new Set(),
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
    return kind === "weapon" ? text("weapon") : kind === "character" ? text("character") : String(kind || "");
  }

  function entrySubtitle(entry) {
    const parts = [];
    if (entry.rarity) parts.push(`${text("rarity")} ${entry.rarity}`);
    if (entry.kind === "weapon" && entry.weaponTypeLabel) parts.push(entry.weaponTypeLabel);
    if (entry.kind === "character") {
      if (entry.professionLabel) parts.push(entry.professionLabel);
      if (entry.elementLabel) parts.push(entry.elementLabel);
    }
    return parts.join(" / ");
  }

  function fact(label, value, opts = {}) {
    const display = formatValue(value);
    if (!display) return "";
    return `<div class="gameplay-fact"><span>${escapeHtml(label)}</span><b${opts.mono ? ' class="mono"' : ""}>${escapeHtml(display)}</b></div>`;
  }

  function section(title, body) {
    if (!body) return "";
    return `<section class="gameplay-section"><h2>${escapeHtml(title)}</h2>${body}</section>`;
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
    const maxDifferent = skill.maxDescription && skill.maxDescription !== skill.description;
    return `<article class="gameplay-skill-card">
      <header>
        <div class="gameplay-skill-title">${escapeHtml(skill.name || skill.id || "")}</div>
        <div class="gameplay-skill-meta">${escapeHtml(skill.id || "")}${skill.levelCount ? ` / ${formatNumber(skill.levelCount)} Lv` : ""}</div>
      </header>
      ${renderDescription(skill.description)}
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
    ].filter(Boolean).join("");
    const skills = (entry.skills || []).map(renderSkillCard).join("");
    return {
      facts,
      body: [
        section(text("itemDescription"), renderDescription(entry.itemDescription)),
        section(text("description"), renderDescription(entry.description)),
        section(text("progression"), renderWeaponProgression(entry)),
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
    ].filter(Boolean).join("");
    const groups = (entry.skillGroups || []).map((group) => {
      const actionIds = renderIdChips(group.actionSkillIds || []);
      const levelUpRows = group.levelUp || [];
      const skills = (group.skills || []).map((skill) => renderSkillCard(skill, { slider: true, levelUp: levelUpRows })).join("");
      return `<section class="gameplay-group-card" data-linked-level-group>
        <header>
          <div class="gameplay-group-title">${escapeHtml(group.name || group.id || "")}</div>
          <div class="gameplay-skill-meta">${escapeHtml([group.typeLabel, group.id].filter(Boolean).join(" / "))}</div>
        </header>
        ${renderDescription(group.description)}
        ${actionIds ? `<div class="gameplay-subheading">${escapeHtml(text("actionSkillIds"))}</div>${actionIds}` : ""}

        ${skills ? `<div class="gameplay-subheading">${escapeHtml(text("actionData"))}</div><div class="gameplay-action-stack">${skills}</div>` : ""}
      </section>`;
    }).join("");
    const talentGroups = renderTalentGroups(entry.talentGroups || []);
    const talentCards = (entry.talents || []).map(renderTalentCard).join("");
    return {
      facts,
      body: [
        section(text("progression"), renderCharacterProgression(entry)),
        section(text("characterSkills"), groups),
        section(text("talents"), talentGroups || (talentCards ? `<div class="gameplay-card-grid">${talentCards}</div>` : "")),
      ].join(""),
    };
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
    gp$("#gameplay-detail-meta").textContent = [kindLabel(entry.kind), entrySubtitle(entry), entry.group].filter(Boolean).join(" / ");
    const rendered = entry.kind === "weapon" ? renderWeaponDetail(entry) : renderCharacterDetail(entry);
    gp$("#gameplay-detail-facts").innerHTML = rendered.facts;
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
          <span class="gameplay-kind-badge">${escapeHtml(kindLabel(entry.kind))}</span>
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

  function buildFilterChips() {
    const kindCounts = countBy(STATE.entries, (entry) => entry.kind);
    const groupCounts = countBy(STATE.entries, (entry) => entry.group);
    const kindItems = [...kindCounts.keys()].sort().map((value) => ({ value, label: kindLabel(value), count: kindCounts.get(value) }));
    const groupItems = [...groupCounts.keys()].sort().map((value) => ({ value, label: value, count: groupCounts.get(value) }));
    window.WebUI.filters.buildChips("#gameplay-kind-filter", kindItems, {
      active: STATE.filters.kinds,
      onToggle: () => applyFilters(),
    });
    window.WebUI.filters.buildChips("#gameplay-group-filter", groupItems, {
      active: STATE.filters.groups,
      onToggle: () => applyFilters(),
    });
  }

  function applyFilters() {
    const q = String((gp$("#gameplay-q") && gp$("#gameplay-q").value) || "").trim().toLowerCase();
    STATE.filtered = STATE.entries.filter((entry) => {
      if (STATE.filters.kinds.size && !STATE.filters.kinds.has(entry.kind)) return false;
      if (STATE.filters.groups.size && !STATE.filters.groups.has(entry.group)) return false;
      if (q) {
        const haystack = [entry.search, entry.title, entry.id, entry.group, entry.subtitle].join(" ");
        if (!textIncludes(haystack, q)) return false;
      }
      return true;
    }).sort((a, b) => {
      const ak = a.kind === "weapon" ? 0 : 1;
      const bk = b.kind === "weapon" ? 0 : 1;
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
    STATE.filters.groups.clear();
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
      ["#gameplay-group-label", "group"],
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
        STATE.selected = null;
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
