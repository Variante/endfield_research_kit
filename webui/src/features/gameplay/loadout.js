// Character loadout calculator for the Gameplay page.
//
// Computes a playable character's final attributes from the selected level,
// potential, weapon and equipment with the native formula published in
// `attributeCalculation` (scripts/game_data/contracts/attribute_formula_native.json):
//
//   base  = clamp(raw + ΣBaseAddition + otherBaseAdd)
//   armed = clamp((base · max(1 + ΣBaseMultiplier, 0) + ΣBaseFinalAddition) · ΠBaseFinalMultiplier)
//   final = clamp(((armed + ΣAddition) · max(1 + ΣMultiplier, 0) + ΣFinalAddition) · ΠFinalMultiplier · otherFinalScalar)
//
// otherBaseAdd gives MaxHp floor(Str)·efficiencyOfSTR and the four
// AtkIncreaseFactorFrom* attributes their main/sub rates; otherFinalScalar
// gives Atk 1 + Σ floor(X)·AtkIncreaseFactorFromX. Reviewed v2 publications also
// include Will healing, Agi/Wisd resistance and movement/cooldown scalars.
// Attributes whose hooks the
// contract does not model are labelled as partial configuration values. The page never computes without
// a validated formula.
(() => {
  const WebUI = window.WebUI;

  const MODIFIER = { Addition: 0, Multiplier: 1, FinalAddition: 3, FinalMultiplier: 4, BaseAddition: 5, BaseMultiplier: 6, BaseFinalAddition: 7, BaseFinalMultiplier: 8 };
  const PRODUCT_TYPES = new Set([MODIFIER.FinalMultiplier, MODIFIER.BaseFinalMultiplier]);
  const MODIFIER_NAMES = Object.fromEntries(Object.entries(MODIFIER).map(([name, id]) => [id, name]));
  const STR = 39, MAX_HP = 1, ATK = 2;
  const FOUR_ATTRS = [39, 40, 41, 42];
  const FACTOR_OF = { 39: 76, 40: 77, 41: 78, 42: 79 };
  const DAMAGE_REDUCTION_OF = { 4: 101, 48: 102, 7: 103, 6: 104, 5: 105, 60: 106 };
  // Keep unmodelled derived hooks visible, but label their configuration-only
  // result rather than claiming the general modifier formula is complete.
  const CONVERSION_ATTRS = new Set([13, 29, 30, 47, 94, 95, 96, 97, 98, 99]);
  const DISPLAY_ORDER = [39, 40, 41, 42, 1, 2, 3, 9, 10, 87,
    94, 98, 97, 96, 95, 99, 29, 30, 47, 44, 26, 50, 51, 52, 53, 54];
  // Resistance scalars are another representation of the resistance family;
  // avoid presenting two identically named rows as independent player stats.
  const INTERNAL_ATTRS = new Set([...Object.values(FACTOR_OF), 80, 81, 82, 83, 84, 85]);
  const SLOTS = [
    { key: "body", partType: 0 },
    { key: "hand", partType: 1 },
    { key: "acc1", partType: 2 },
    { key: "acc2", partType: 2 },
  ];

  function levelsBlackboard(skill, level) {
    const row = (skill?.levels || []).find((item) => Number(item?.level) === Number(level)) || null;
    return new Map((row?.blackboard || []).filter((item) => item?.key).map((item) => [item.key, Number(item.value)]));
  }

  // ---- calculation -------------------------------------------------------

  function resolveTargets(modifier, character) {
    const type = Number(modifier.modifyAttributeType || 0);
    if (type === 1) return character.mainAttrType ? [Number(character.mainAttrType)] : [];
    if (type === 2) return character.subAttrType ? [Number(character.subAttrType)] : [];
    if (type === 3) return FOUR_ATTRS;
    const attr = Number(modifier.attrType ?? modifier.attributeType);
    return attr ? [attr] : [];
  }

  function createCalculator(calc, character, row, modifiers) {
    const meta = calc.attributes || {};
    const k = calc.coefficients || {};
    const conversionsReviewed = !!calc.formula?.otherBaseFinalScalar;
    const buckets = new Map();
    for (const modifier of modifiers) {
      const value = Number(modifier.value);
      if (!Number.isFinite(value)) continue;
      for (const attr of resolveTargets(modifier, character)) {
        if (!buckets.has(attr)) buckets.set(attr, { sums: {}, products: {}, sources: [] });
        const bucket = buckets.get(attr);
        const type = Number(modifier.modifierType);
        if (PRODUCT_TYPES.has(type)) bucket.products[type] = (bucket.products[type] ?? 1) * value;
        else bucket.sums[type] = (bucket.sums[type] ?? 0) + value;
        bucket.sources.push({ ...modifier, attr, value, modifierType: type });
      }
    }
    const sum = (attr, type) => buckets.get(attr)?.sums[type] ?? 0;
    const product = (attr, type) => buckets.get(attr)?.products[type] ?? 1;
    const clamp = (attr, value) => {
      const m = meta[String(attr)] || {};
      let out = value;
      if (m.min !== null && m.min !== undefined) out = Math.max(out, Number(m.min));
      if (m.max !== null && m.max !== undefined) out = Math.min(out, Number(m.max));
      return out;
    };
    const raw = (attr) => {
      const stored = row?.attrs?.[String(attr)];
      if (stored !== undefined) return Number(stored);
      return Number(meta[String(attr)]?.default ?? 0);
    };
    const memo = new Map();
    const otherBaseAdd = (attr) => {
      if (attr === MAX_HP) return Math.floor(final(STR)) * Number(k.efficiencyOfSTR || 0);
      if (conversionsReviewed && (attr === 29 || attr === 30)) return Math.floor(final(42)) * Number(k[attr === 29 ? 'healerEfficiencyOfWILL' : 'recoverEfficiencyOfWILL'] || 0);
      if (conversionsReviewed && attr >= 94 && attr <= 98) {
        const ability = attr === 94 ? 40 : 41;
        const efficiency = Number(k[attr === 94 ? 'efficiencyOfAGI' : 'efficiencyOfWISD'] || 0);
        return 100 * (1 - 1 / (1 + Math.floor(final(ability)) * efficiency));
      }
      const source = Object.keys(FACTOR_OF).find((key) => FACTOR_OF[key] === attr);
      if (source) {
        const id = Number(source);
        return (Number(character.mainAttrType) === id ? Number(k.atkRateOfMain || 0) : 0)
          + (Number(character.subAttrType) === id ? Number(k.atkRateOfSub || 0) : 0);
      }
      return 0;
    };
    const otherFinalScalar = (attr) => {
      if (conversionsReviewed && attr === 47) return final(100);
      const reduction = DAMAGE_REDUCTION_OF[attr];
      const nativeName = meta[String(attr)]?.nativeName;
      if (reduction && nativeName && calc.formula?.otherFinalScalar?.[nativeName]) return final(reduction);
      if (attr !== ATK) return 1;
      return 1 + FOUR_ATTRS.reduce((total, id) => total + Math.floor(final(id)) * final(FACTOR_OF[id]), 0);
    };
    function base(attr) {
      return clamp(attr, raw(attr) + sum(attr, MODIFIER.BaseAddition) + otherBaseAdd(attr));
    }
    function armed(attr) {
      const factor = Math.max(1 + sum(attr, MODIFIER.BaseMultiplier), 0);
      const otherScalar = conversionsReviewed && attr === 13 ? 1 - final(86) : 1;
      return clamp(attr, (base(attr) * factor + sum(attr, MODIFIER.BaseFinalAddition)) * product(attr, MODIFIER.BaseFinalMultiplier) * otherScalar);
    }
    function final(attr) {
      if (memo.has(attr)) return memo.get(attr);
      const factor = Math.max(1 + sum(attr, MODIFIER.Multiplier), 0);
      const value = clamp(attr, ((armed(attr) + sum(attr, MODIFIER.Addition)) * factor + sum(attr, MODIFIER.FinalAddition))
        * product(attr, MODIFIER.FinalMultiplier) * otherFinalScalar(attr));
      memo.set(attr, value);
      return value;
    }
    return { raw, base, final, otherBaseAdd, otherFinalScalar, buckets };
  }

  // ---- inputs -------------------------------------------------------------

  function defaultState(entry, h) {
    const rows = entry.attributeRows || [];
    const weapon = h.entries.find((item) => item.kind === "weapon" && item.id === entry.defaultWeaponId) || null;
    return {
      pos: Math.max(0, rows.length - 1),
      potential: 0,
      favorTalent: null,
      weaponId: weapon?.id || "",
      weaponPos: null,
      weaponPotential: 0,
      skillLevels: {},
      slots: { body: "", hand: "", acc1: "", acc2: "" },
      // Enhancement step per equipment attribute line: slot -> attrIndex -> step.
      enhance: { body: {}, hand: {}, acc1: {}, acc2: {} },
    };
  }

  const LOADOUT_STORAGE_PREFIX = "endfield.loadout.v1:";
  function restoreState(entry, h) {
    const state = defaultState(entry, h);
    let saved;
    try { saved = JSON.parse(WebUI.storageGet(LOADOUT_STORAGE_PREFIX + entry.id) || "null"); } catch (_) { return state; }
    if (!saved || typeof saved !== "object") return state;
    const integer = (value, fallback, max = Number.MAX_SAFE_INTEGER) => Number.isInteger(value) && value >= 0 ? Math.min(value, max) : fallback;
    state.pos = integer(saved.pos, state.pos, Math.max(0, entry.attributeRows.length - 1));
    state.potential = integer(saved.potential, state.potential, (entry.potentials?.levels || []).length);
    state.favorTalent = saved.favorTalent === null ? null : integer(saved.favorTalent, null);
    const weapon = h.entries.find((item) => item.kind === "weapon" && item.id === saved.weaponId && Number(item.weaponType) === Number(entry.weaponType));
    state.weaponId = saved.weaponId === "" ? "" : weapon?.id || state.weaponId;
    state.weaponPos = integer(saved.weaponPos, null, weapon ? Math.max(0, weaponPositions(weapon).length - 1) : 0);
    state.weaponPotential = integer(saved.weaponPotential, 0, weapon?.talentTemplate?.rows?.length || 0);
    for (const [key, value] of Object.entries(saved.skillLevels || {})) {
      if (key !== "__proto__" && Number.isInteger(value) && value >= 1) state.skillLevels[key] = value;
    }
    for (const slot of SLOTS) {
      const item = h.entries.find((candidate) => candidate.kind === "equipment" && candidate.id === saved.slots?.[slot.key] && Number(candidate.partType) === slot.partType);
      state.slots[slot.key] = item?.id || "";
      for (const line of item?.attributeModifiers || []) {
        const value = saved.enhance?.[slot.key]?.[String(line.attrIndex)];
        if (Number.isInteger(value) && value >= 1) state.enhance[slot.key][String(line.attrIndex)] = Math.min(value, (line.values || []).length || 1);
      }
    }
    return state;
  }

  function saveState(entry, state) {
    WebUI.storageSet(LOADOUT_STORAGE_PREFIX + entry.id, JSON.stringify(state));
  }

  function weaponPositions(weapon) {
    const rows = weapon?.breakthrough?.rows || [];
    const maxLv = Number(weapon?.maxLv || weapon?.upgrade?.maxLevel || 1);
    const out = [];
    rows.forEach((row, stage) => {
      const start = Number(row.level || 1);
      const end = stage + 1 < rows.length ? Number(rows[stage + 1].level) : maxLv;
      for (let level = start; level <= end; level += 1) out.push({ level, stage });
    });
    if (!out.length) for (let level = 1; level <= maxLv; level += 1) out.push({ level, stage: 0 });
    return out;
  }

  function weaponSkillBounds(weapon, stage, potential, index) {
    const bound = weapon?.breakthrough?.rows?.[stage]?.skillLevelBounds?.[index] || { lowerBound: 1, upperBound: 1 };
    const extra = potential > 0 ? weapon?.talentTemplate?.rows?.[potential - 1]?.skillLevelExtraBounds?.[index] : null;
    const count = Number(weapon?.skills?.[index]?.levelCount || 1);
    const low = Math.min(count, Number(bound.lowerBound || 1) + Number(extra?.lowerBound || 0));
    const high = Math.min(count, Number(bound.upperBound || 1) + Number(extra?.upperBound || 0));
    return { low: Math.max(1, low), high: Math.max(1, low, high) };
  }

  function weaponBaseAtk(weapon, level) {
    const row = (weapon?.stats?.rows || []).find((item) => Number(item.level) === Number(level));
    const attr = (row?.attrs || []).find((item) => item.key === "baseAtk");
    return attr ? Number(attr.value) : null;
  }

  function skillModifiers(skill, level, source, h) {
    const record = h.index.skillAttributeModifiers?.[skill?.id];
    if (!record || record.status !== "exact") return { modifiers: [], unknown: !!skill?.id };
    const blackboard = levelsBlackboard(skill, level);
    const modifiers = (record.modifiers || []).map((item) => ({
      attrType: item.attributeType,
      modifierType: item.modifierType,
      modifyAttributeType: item.modifyAttributeType,
      value: item.blackboardKey ? blackboard.get(item.blackboardKey) : item.value,
      source,
    })).filter((item) => Number.isFinite(Number(item.value)));
    return { modifiers, unknown: false };
  }

  function favorTalentInfo(entry, state, row) {
    const levels = (entry.talentGroups || []).filter((group) => group.kind === "attribute")
      .flatMap((group) => group.levels || []).sort((a, b) => Number(a.sortIndex || a.level) - Number(b.sortIndex || b.level));
    const available = levels.filter((level) => Number(level.breakStage || 0) <= Number(row.breakStage || 0));
    const count = Math.max(0, Math.min(available.length, state.favorTalent ?? available.length));
    return { levels: available, count };
  }

  function gatherInputs(entry, state, h) {
    const rows = entry.attributeRows || [];
    const row = rows[state.pos] || rows[rows.length - 1] || { attrs: {} };
    const modifiers = [];
    const notes = [];
    const favor = favorTalentInfo(entry, state, row);
    for (const talent of favor.levels.slice(0, favor.count)) {
      const effects = talent.attributeModifier?.attributeModifiers || [];
      if (!effects.length) notes.push(`${talent.title}: ${h.text("loadoutSkillUnknown")}`);
      for (const effect of effects) {
        if (!Number.isFinite(Number(effect.attrValue))) continue;
        modifiers.push({ ...effect, value: Number(effect.attrValue), source: `${h.text("loadoutFavorTalent")} · ${talent.title} ${talent.level}` });
      }
    }
    // Potential attribute effects up to the selected potential.
    for (const potential of entry.potentials?.levels || []) {
      if (Number(potential.level) > state.potential) continue;
      for (const effect of potential.effects || []) {
        if (effect.kind !== "attribute") continue;
        modifiers.push({ attrType: effect.attrType, modifierType: effect.modifierType, modifyAttributeType: effect.modifyAttributeType, value: effect.value, source: `${h.text("loadoutPotential")} ${potential.level} · ${potential.name || ""}` });
      }
    }
    const weapon = h.entries.find((item) => item.kind === "weapon" && item.id === state.weaponId) || null;
    let weaponInfo = null;
    if (weapon) {
      const positions = weaponPositions(weapon);
      const pos = state.weaponPos === null ? positions.length - 1 : Math.min(state.weaponPos, positions.length - 1);
      const { level, stage } = positions[pos] || { level: 1, stage: 0 };
      const baseAtk = weaponBaseAtk(weapon, level);
      if (baseAtk !== null) modifiers.push({ attrType: ATK, modifierType: MODIFIER.BaseAddition, modifyAttributeType: 0, value: baseAtk, source: `${weapon.title} · ${h.text("loadoutWeaponBaseAtk")}` });
      const skills = (weapon.skills || []).map((skill, index) => {
        const bounds = weaponSkillBounds(weapon, stage, state.weaponPotential, index);
        const chosen = state.skillLevels[`${weapon.id}:${index}`];
        const level = Math.min(bounds.high, Math.max(bounds.low, chosen ?? bounds.high));
        const result = skillModifiers(skill, level, `${weapon.title} · ${skill.name}`, h);
        modifiers.push(...result.modifiers);
        if (result.unknown) notes.push(`${skill.name}: ${h.text("loadoutSkillUnknown")}`);
        return { skill, index, level, bounds };
      });
      weaponInfo = { weapon, positions, pos, level, stage, skills };
    }
    // Equipment lines and set effects.
    const equipped = {};
    const suitCounts = new Map();
    for (const slot of SLOTS) {
      const item = h.entries.find((candidate) => candidate.kind === "equipment" && candidate.id === state.slots[slot.key]) || null;
      if (!item) continue;
      equipped[slot.key] = item;
      for (const line of item.attributeModifiers || []) {
        const values = line.values || [];
        if (!values.length) continue;
        const step = lineStep(state, slot.key, line);
        modifiers.push({ ...line, value: values[Math.min(step, values.length) - 1], source: `${item.title}` });
      }
      if (item.suit?.id) suitCounts.set(item.suit.id, { suit: item.suit, count: (suitCounts.get(item.suit.id)?.count || 0) + 1 });
    }
    const suits = [];
    for (const { suit, count } of suitCounts.values()) {
      for (const effect of suit.effects || []) {
        const active = count >= Number(effect.equipCount || 0);
        suits.push({ suit, effect, count, active });
        if (!active) continue;
        const result = skillModifiers(effect.skill, effect.skillLevel || 1, `${suit.name} · ${h.text("loadoutSetEffect")}`, h);
        modifiers.push(...result.modifiers);
        if (result.unknown) notes.push(`${suit.name}: ${h.text("loadoutSkillUnknown")}`);
      }
    }
    return { row, modifiers, notes, weaponInfo, equipped, suits };
  }

  // ---- rendering ------------------------------------------------------------

  function formatAttr(calc, attr, value, h) {
    const meta = calc.attributes?.[String(attr)] || {};
    const format = String(meta.valueFormat || "");
    const match = /^\{(value|1-value|value-1|100-100\*value)(?::([^}]+))?\}$/.exec(format);
    if (match) {
      const displayed = { value, "1-value": 1 - value, "value-1": value - 1, "100-100*value": 100 - 100 * value }[match[1]];
      return h.formatDescriptionValue(displayed, match[2] || "");
    }
    return h.formatValue(Number(value.toFixed(2)));
  }

  function attrName(calc, attr) {
    const meta = calc.attributes?.[String(attr)] || {};
    return meta.name || meta.nativeName || `attr ${attr}`;
  }

  function renderSlider(name, max, value, label) {
    return `<label class="gameplay-loadout-slider"><span>${label}</span><input type="range" min="0" max="${max}" step="1" value="${value}" data-loadout="${name}"></label>`;
  }

  // Merge cost lines of the same item. Level-up gold comes from the curve
  // and breakthrough gold from the break table under a different id, so the
  // item name is the merge key.
  function sumCost(items) {
    const totals = new Map();
    for (const item of items) {
      if (!item || !(item.name || item.id) || !Number(item.count)) continue;
      const key = item.name || item.id;
      const current = totals.get(key) || { ...item, count: 0 };
      current.count += Number(item.count);
      totals.set(key, current);
    }
    return [...totals.values()];
  }

  function renderCharacterControls(entry, state, inputs, h) {
    const rows = entry.attributeRows || [];
    const row = inputs.row;
    const perLevel = (entry.levelCurve?.perLevel || []).find((item) => Number(item.level) === Number(row.level)) || {};
    const breakItems = (entry.breakthroughs || []).filter((item) => Number(item.stage) <= Number(row.breakStage)).flatMap((item) => item.requiredItem || []);
    const potentials = (entry.potentials?.levels || []).length;
    const favor = favorTalentInfo(entry, state, row);
    const cost = [
      Number(perLevel.expSum) ? { id: "loadout-exp", name: h.text("loadoutExp"), count: perLevel.expSum } : null,
      Number(perLevel.goldSum) ? { ...(h.goldItem() || { id: "item_gold", name: h.text("gold") }), count: perLevel.goldSum } : null,
    ].filter(Boolean);
    return `<div class="gameplay-loadout-block">
      <div class="gameplay-loadout-block-title">${h.escapeHtml(entry.title)}</div>
      ${renderSlider("pos", Math.max(0, rows.length - 1), state.pos, `${h.escapeHtml(h.text("loadoutLevel"))} <b>${h.escapeHtml(String(row.level))}</b> · ${h.escapeHtml(h.text("loadoutBreakStage"))} ${h.escapeHtml(String(row.breakStage ?? 0))}`)}
      ${potentials ? renderSlider("potential", potentials, state.potential, `${h.escapeHtml(h.text("loadoutPotential"))} <b>${state.potential}</b>`) : ""}
      ${favor.levels.length ? renderSlider("favorTalent", favor.levels.length, favor.count, `${h.escapeHtml(h.text("loadoutFavorTalent"))} <b>${favor.count}/${favor.levels.length}</b> · ${h.escapeHtml(favor.count ? h.text("loadoutFavorRequirement", { value: `${Math.floor(Number(favor.levels[favor.count - 1].favorability || 0) / 3)}%` }) : h.text("loadoutFavorNone"))}`) : ""}
      <div class="gameplay-subheading">${h.escapeHtml(h.text("loadoutLevelCost"))}</div>
      ${h.renderMaterialChips(sumCost([...cost, ...breakItems])) || `<span class="muted">-</span>`}
    </div>`;
  }

  // Pinyin collation boundaries provide initials without a network dependency.
  // Polyphonic names may supply explicit aliases in the published record.
  const pinyinCollator = new Intl.Collator("zh-Hans-u-co-pinyin");
  const initialBoundaries = [..."阿八嚓搭蛾发噶哈击喀垃妈拿哦啪期然撒塌挖昔压匝"];
  const initialLetters = "abcdefghjklmnopqrstwxyz";
  const initialCache = new Map();
  function initials(value) {
    return [...String(value || "")].map((char) => {
      if (!/[\u3400-\u9fff]/.test(char)) return /[a-z0-9]/i.test(char) ? char.toLowerCase() : "";
      if (!initialCache.has(char)) {
        let result = "";
        for (let i = 0; i < initialBoundaries.length; i += 1) {
          if (pinyinCollator.compare(char, initialBoundaries[i]) < 0) break;
          result = initialLetters[i];
        }
        initialCache.set(char, result);
      }
      return initialCache.get(char);
    }).join("");
  }

  function pickerSearchText(item) {
    const names = [item.title, item.name, item.suit?.name, ...(item.aliases || [])].filter(Boolean);
    return [...names, ...names.map(initials), item.id].join("\n");
  }

  function renderPicker(options, value, kind, slot, h) {
    const chosen = options.find((item) => item.id === value);
    const label = (item) => kind === "weaponId"
      ? `${"★".repeat(Number(item.rarity || 0))} ${item.title}`
      : `Lv${item.minWearLv || "?"} · ${item.title}${item.suit?.name ? ` · ${item.suit.name}` : ""}`;
    const image = (item) => item ? h.renderItemIcon(item, item.title, { static: true }) : "";
    const row = (item) => `<button type="button" class="gameplay-loadout-choice" data-picker-value="${h.escapeHtml(item?.id || "")}" aria-pressed="${(item?.id || "") === value}" data-picker-search="${h.escapeHtml(item ? pickerSearchText(item) : "")}">${image(item)}<span>${h.escapeHtml(item ? label(item) : h.text("loadoutNone"))}</span></button>`;
    return `<details class="gameplay-loadout-picker" data-picker-kind="${kind}" data-picker-slot="${slot || ""}"><summary>${image(chosen)}<span>${h.escapeHtml(chosen ? label(chosen) : h.text("loadoutNone"))}</span></summary><label class="gameplay-loadout-search"><span>${h.escapeHtml(h.text("loadoutSearch"))}</span><input type="search" autocomplete="off" placeholder="${h.escapeHtml(h.text("loadoutSearch"))}"></label><div class="gameplay-loadout-choices" data-update-files-exclude>${row(null)}${options.map(row).join("")}</div><p class="muted" data-picker-empty hidden>${h.escapeHtml(h.text("loadoutSearchEmpty"))}</p></details>`;
  }

  function renderWeaponControls(entry, state, inputs, h) {
    const options = h.entries
      .filter((item) => item.kind === "weapon" && Number(item.weaponType) === Number(entry.weaponType))
      .sort((a, b) => Number(b.rarity || 0) - Number(a.rarity || 0) || String(a.title).localeCompare(String(b.title)));
    const select = renderPicker(options, state.weaponId, "weaponId", "", h);
    const info = inputs.weaponInfo;
    let body = "";
    if (info) {
      const cost = sumCost([
        ...info.weapon.breakthrough?.rows?.slice(1, info.stage + 1).flatMap((row) => [...(row.items || []), row.goldCost ? { ...(h.goldItem() || { id: "item_gold", name: h.text("gold") }), count: row.goldCost } : null]) || [],
      ].filter(Boolean));
      const upgrade = (info.weapon.upgrade?.perLevel || []).find((item) => Number(item.level) === Number(info.level)) || {};
      const talentRows = info.weapon.talentTemplate?.rows?.length || 0;
      body = `${renderSlider("weaponPos", info.positions.length - 1, info.pos, `${h.escapeHtml(h.text("loadoutLevel"))} <b>${info.level}</b> · ${h.escapeHtml(h.text("loadoutBreakStage"))} ${info.stage}`)}
        ${talentRows ? renderSlider("weaponPotential", talentRows, state.weaponPotential, `${h.escapeHtml(h.text("loadoutPotential"))} <b>${state.weaponPotential}</b>`) : ""}
        ${info.skills.map(({ skill, index, level, bounds }) => bounds.high > bounds.low
          ? `<label class="gameplay-loadout-slider"><span>${h.escapeHtml(skill.name)} <b>Lv ${level}</b></span><input type="range" min="${bounds.low}" max="${bounds.high}" step="1" value="${level}" data-loadout="skill" data-skill-index="${index}"></label>`
          : `<div class="gameplay-loadout-fixed">${h.escapeHtml(skill.name)} <b>Lv ${level}</b></div>`).join("")}
        <div class="gameplay-subheading">${h.escapeHtml(h.text("loadoutLevelCost"))}</div>
        ${h.renderMaterialChips(sumCost([
          Number(upgrade.expSum) ? { id: "loadout-weapon-exp", name: h.text("loadoutExp"), count: upgrade.expSum } : null,
          Number(upgrade.goldSum) ? { ...(h.goldItem() || { id: "item_gold", name: h.text("gold") }), count: upgrade.goldSum } : null,
          ...cost,
        ].filter(Boolean))) || `<span class="muted">-</span>`}`;
    }
    return `<div class="gameplay-loadout-block">
      <div class="gameplay-loadout-block-title">${h.escapeHtml(h.text("loadoutWeapon"))}</div>
      ${select}
      ${body}
    </div>`;
  }

  // Lines sharing an attrIndex are one enhanceable line in game; they move
  // together. A line not yet touched sits at its first step.
  function lineStep(state, slotKey, line) {
    return Number(state.enhance[slotKey]?.[String(line.attrIndex)] || 1);
  }

  function renderLineSliders(entry, state, slotKey, item, h) {
    const calc = h.index.attributeCalculation || {};
    const groups = new Map();
    for (const line of item.attributeModifiers || []) {
      const key = String(line.attrIndex);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(line);
    }
    return [...groups.entries()].map(([attrIndex, lines]) => {
      const steps = Math.max(...lines.map((line) => (line.values || []).length));
      const step = Math.min(lineStep(state, slotKey, lines[0]), steps);
      const label = lines.map((line) => {
        const targets = resolveTargets(line, entry);
        const resolvedName = targets.length === 4 ? h.text("loadoutAllAttributes") : targets.map((attr) => attrName(calc, attr)).join(" / ");
        const targetType = Number(line.modifyAttributeType || 0);
        const originalName = targetType === 1 ? h.text("stat_main_attr") : targetType === 2 ? h.text("stat_sub_attr") : "";
        const name = originalName ? `${originalName}${resolvedName ? `（${resolvedName}）` : ""}` : resolvedName;
        const value = Number((line.values || [])[Math.min(step, (line.values || []).length) - 1]);
        const shown = Number.isFinite(value) ? formatAttr(calc, targets[0] ?? line.attrType, value, h) : "-";
        // Multiplier lines are fractions of the attribute; show them as percent.
        const percent = [MODIFIER.BaseMultiplier, MODIFIER.Multiplier].includes(Number(line.modifierType)) && Number.isFinite(value);
        const matchesMain = targets.includes(Number(entry.mainAttrType));
        const matchesSub = targets.includes(Number(entry.subAttrType));
        const roles = [matchesMain ? "main" : "", matchesSub ? "sub" : ""].filter(Boolean);
        const roleLabel = roles.map((role) => h.text(role === "main" ? "stat_main_attr" : "stat_sub_attr")).join(" / ");
        const content = h.escapeHtml(`${name} +${percent ? h.formatDescriptionValue(value, "0.0%") : shown}`);
        return roles.length ? `<span class="${roles.map((role) => `gameplay-ability-${role}`).join(" ")}" title="${h.escapeHtml(roleLabel)}">${content}<small class="gameplay-ability-label">${h.escapeHtml(roleLabel)}</small></span>` : content;
      }).join(" · ");
      // A line whose value is the same at every step has nothing to enhance.
      const varies = lines.some((line) => new Set((line.values || []).map(Number)).size > 1);
      if (steps <= 1 || !varies) return `<div class="gameplay-loadout-fixed">${label}</div>`;
      return `<label class="gameplay-loadout-slider"><span>${label} <b>${step}/${steps}</b></span><input type="range" min="1" max="${steps}" step="1" value="${step}" data-loadout="enhance" data-slot="${slotKey}" data-line="${h.escapeHtml(attrIndex)}"></label>`;
    }).join("");
  }

  function renderEquipmentControls(entry, state, inputs, h) {
    const level = Number(inputs.row.level || 0);
    const slots = SLOTS.map((slot) => {
      const options = h.entries
        .filter((item) => item.kind === "equipment" && Number(item.partType) === slot.partType)
        .sort((a, b) => Number(b.minWearLv || 0) - Number(a.minWearLv || 0) || Number(b.rarity || 0) - Number(a.rarity || 0) || String(a.title).localeCompare(String(b.title)));
      const label = options[0]?.partTypeLabel || slot.key;
      const chosen = inputs.equipped[slot.key];
      const warn = chosen && Number(chosen.minWearLv || 0) > level
        ? `<small class="gameplay-loadout-warn">${h.escapeHtml(h.text("loadoutMinWear", { level: chosen.minWearLv }))}</small>` : "";
      return `<div class="gameplay-loadout-slot">
        <div class="gameplay-loadout-slot-heading"><span class="gameplay-loadout-slot-label">${h.escapeHtml(slot.partType === 2 ? `${label} ${slot.key === "acc1" ? 1 : 2}` : label)}</span>
        ${slot.partType === 2 ? `<button type="button" data-copy-accessory="${slot.key}"${state.slots[slot.key === "acc1" ? "acc2" : "acc1"] ? "" : " disabled"}>${h.escapeHtml(h.text("loadoutCopyAccessory", { slot: slot.key === "acc1" ? 2 : 1 }))}</button>` : ""}</div>
        ${renderPicker(options, state.slots[slot.key], "slot", slot.key, h)}
        ${chosen ? `<div class="gameplay-loadout-lines">${renderLineSliders(entry, state, slot.key, chosen, h)}</div>` : ""}
        ${warn}
      </div>`;
    }).join("");
    const suits = inputs.suits.length
      ? `<ul class="gameplay-loadout-suits">${inputs.suits.map(({ suit, effect, count, active }) => `<li class="${active ? "is-active" : ""}"><b>${h.escapeHtml(suit.name)}</b> ${count}/${effect.equipCount} · ${h.escapeHtml(active ? h.text("loadoutActive") : h.text("loadoutInactive"))}</li>`).join("")}</ul>` : "";
    return `<div class="gameplay-loadout-block">
      <div class="gameplay-loadout-block-title">${h.escapeHtml(h.text("loadoutEquipment"))}</div>
      ${slots}
      ${suits ? `<div class="gameplay-subheading">${h.escapeHtml(h.text("loadoutSetEffect"))}</div>${suits}` : ""}
    </div>`;
  }

  function renderStats(entry, calc, inputs, h) {
    const calculator = createCalculator(calc, entry, inputs.row, inputs.modifiers);
    const shown = new Set(DISPLAY_ORDER);
    for (const [key, meta] of Object.entries(calc.attributes || {})) if (meta.name) shown.add(Number(key));
    for (const attr of calculator.buckets.keys()) if (calc.attributes?.[String(attr)]?.name) shown.add(attr);
    const attrs = [...shown].filter((attr) => !INTERNAL_ATTRS.has(attr))
      .sort((a, b) => (DISPLAY_ORDER.indexOf(a) + 1 || 999) - (DISPLAY_ORDER.indexOf(b) + 1 || 999)
        || Number(calc.attributes?.[String(a)]?.sortIndex ?? 999) - Number(calc.attributes?.[String(b)]?.sortIndex ?? 999)
        || a - b);
    const rows = attrs.map((attr) => {
      const raw = calculator.raw(attr);
      const value = calculator.final(attr);
      const sources = (calculator.buckets.get(attr)?.sources || []).map((item) => `${item.source}: ${MODIFIER_NAMES[item.modifierType] || item.modifierType} ${h.formatValue(Number(item.value.toFixed(4)))}`);
      if (attr === MAX_HP) sources.push(`${attrName(calc, STR)} → +${h.formatValue(Number(calculator.otherBaseAdd(MAX_HP).toFixed(2)))}`);
      if (attr === ATK) sources.push(`${h.text("loadoutAtkScalar")} ×${calculator.otherFinalScalar(ATK).toFixed(4)}`);
      if (attr === 29 || attr === 30 || (attr >= 94 && attr <= 98)) {
        const ability = attr === 29 || attr === 30 ? 42 : attr === 94 ? 40 : 41;
        sources.push(`${attrName(calc, ability)} → +${h.formatValue(Number(calculator.otherBaseAdd(attr).toFixed(4)))}`);
      }
      if (attr === 47) sources.push(`${h.text("loadoutCooldownScalar")} ×${calculator.otherFinalScalar(attr).toFixed(4)}`);
      const partial = !calc.formula?.otherBaseFinalScalar && CONVERSION_ATTRS.has(attr);
      const boundary = partial ? `<small class="gameplay-loadout-partial" title="${h.escapeHtml(h.text("loadoutPartialNote"))}">${h.escapeHtml(h.text("loadoutPartial"))}</small>` : "";
      const changed = Math.abs(value - raw) > 1e-9;
      return `<tr${changed ? ' class="is-changed"' : ""}><th>${h.escapeHtml(attrName(calc, attr))}</th><td>${h.escapeHtml(formatAttr(calc, attr, raw, h))}</td><td><b>${h.escapeHtml(formatAttr(calc, attr, value, h))}</b>${boundary}</td><td>${sources.map((line) => `<div>${h.escapeHtml(line)}</div>`).join("") || `<span class="muted">-</span>`}</td></tr>`;
    }).join("");
    return `<div class="gameplay-loadout-block gameplay-loadout-stats">
      <div class="gameplay-loadout-block-title">${h.escapeHtml(h.text("loadoutStats"))} ${h.renderEvidenceBadge("recoveryExact", "loadoutFormulaNote", "exact")}</div>
      <div class="gameplay-table-scroll"><table class="gameplay-skill-table"><tr><th></th><th>${h.escapeHtml(h.text("loadoutBase"))}</th><th>${h.escapeHtml(h.text("loadoutFinal"))}</th><th>${h.escapeHtml(h.text("loadoutSources"))}</th></tr>${rows}</table></div>
      <p class="muted">${h.escapeHtml(h.text("loadoutFormulaNote"))}</p>
      ${inputs.notes.length ? `<ul class="gameplay-skill-notes">${inputs.notes.map((note) => `<li>${h.escapeHtml(note)}</li>`).join("")}</ul>` : ""}
    </div>`;
  }

  function render(entry, h) {
    const calc = h.index.attributeCalculation || {};
    if (calc.evidence?.status !== "validated" || !calc.formula) {
      return `<p class="gameplay-integration-note is-warning" role="status">${h.escapeHtml(h.text("loadoutUnavailable"))} (${h.escapeHtml(calc.evidence?.status || "missing")})</p>`;
    }
    if (!(entry.attributeRows || []).length) return `<p class="muted">${h.escapeHtml(h.text("loadoutNoRows"))}</p>`;
    h.STATE.loadouts ||= {};
    const state = h.STATE.loadouts[entry.id] ||= restoreState(entry, h);
    const inputs = gatherInputs(entry, state, h);
    return `<div class="gameplay-loadout" data-loadout-root="${h.escapeHtml(entry.id)}">
      <div class="gameplay-loadout-controls">
        ${renderCharacterControls(entry, state, inputs, h)}
        ${renderWeaponControls(entry, state, inputs, h)}
      </div>
      ${renderEquipmentControls(entry, state, inputs, h)}
      ${renderStats(entry, calc, inputs, h)}
    </div>`;
  }

  function bind(root, entry, h) {
    const container = root.querySelector("[data-loadout-root]");
    const state = h.STATE.loadouts?.[entry.id];
    if (!container || !state) return;
    const apply = (control) => {
      const kind = control.dataset.loadout;
      const value = control.value;
      if (kind === "pos") state.pos = Number(value);
      else if (kind === "favorTalent") state.favorTalent = Number(value);
      else if (kind === "potential") state.potential = Number(value);
      else if (kind === "weaponId") { state.weaponId = value; state.weaponPos = null; }
      else if (kind === "weaponPos") state.weaponPos = Number(value);
      else if (kind === "weaponPotential") state.weaponPotential = Number(value);
      else if (kind === "skill") state.skillLevels[`${state.weaponId}:${control.dataset.skillIndex}`] = Number(value);
      else if (kind === "slot") { state.slots[control.dataset.slot] = value; state.enhance[control.dataset.slot] = {}; }
      else if (kind === "enhance") state.enhance[control.dataset.slot][control.dataset.line] = Number(value);
      saveState(entry, state);
    };
    const rerender = () => {
      container.outerHTML = render(entry, h);
      bind(root, entry, h);
    };
    container.querySelectorAll("[data-copy-accessory]").forEach((button) => {
      button.addEventListener("click", () => {
        const target = button.dataset.copyAccessory;
        if (target !== "acc1" && target !== "acc2") return;
        const source = target === "acc1" ? "acc2" : "acc1";
        if (!state.slots[source]) return;
        state.slots[target] = state.slots[source];
        state.enhance[target] = { ...state.enhance[source] };
        saveState(entry, state);
        rerender();
        root.querySelector(`[data-copy-accessory="${target}"]`)?.focus();
      });
    });
    container.querySelectorAll("[data-picker-kind]").forEach((picker) => {
      const search = picker.querySelector("input");
      picker.addEventListener("toggle", () => { if (picker.open) search.focus(); });
      search.addEventListener("input", () => {
        const tokens = WebUI.parseQuery(search.value);
        let matches = 0;
        picker.querySelectorAll("[data-picker-value]").forEach((button) => {
          button.hidden = Boolean(button.dataset.pickerValue) && !WebUI.queryMatches(button.dataset.pickerSearch, tokens);
          if (!button.hidden && button.dataset.pickerValue) matches += 1;
        });
        picker.querySelector("[data-picker-empty]").hidden = matches > 0;
      });
      search.addEventListener("keydown", (event) => {
        if (event.key === "Escape") { picker.open = false; picker.querySelector("summary").focus(); }
      });
      picker.querySelectorAll("[data-picker-value]").forEach((button) => {
        button.addEventListener("click", () => {
          apply({ dataset: { loadout: picker.dataset.pickerKind, slot: picker.dataset.pickerSlot }, value: button.dataset.pickerValue });
          const kind = picker.dataset.pickerKind;
          const slot = picker.dataset.pickerSlot;
          rerender();
          root.querySelector(`[data-picker-kind="${kind}"][data-picker-slot="${slot}"] summary`)?.focus();
        });
      });
    });
    // While a slider moves only the stats table is replaced, so the dragged
    // control survives; releasing it re-renders labels, bounds and costs.
    const refreshStats = () => {
      const stats = container.querySelector(".gameplay-loadout-stats");
      const calc = h.index.attributeCalculation || {};
      if (stats) stats.outerHTML = renderStats(entry, calc, gatherInputs(entry, state, h), h);
    };
    container.querySelectorAll("[data-loadout]").forEach((control) => {
      if (control.tagName === "SELECT") {
        control.addEventListener("change", () => { apply(control); rerender(); });
        return;
      }
      control.addEventListener("input", () => {
        apply(control);
        cancelAnimationFrame(container._loadoutFrame);
        container._loadoutFrame = requestAnimationFrame(refreshStats);
      });
      control.addEventListener("change", () => { apply(control); rerender(); });
    });
  }

  WebUI.gameplayLoadout = { render, bind, createCalculator, pickerSearchText, restoreState };
})();
