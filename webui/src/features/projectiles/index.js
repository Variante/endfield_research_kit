(() => {
  const DEFAULT_CONTAINER = "#projectile-inspector";
  const DEFAULT_DATA_PATH = "data/gameplay/projectiles.json";
  const PAGE_SIZE = 100;
  const COMBAT_LINK_LIMIT = 40;
  let localeListenerBound = false;
  let languageListenerBound = false;
  const COMBAT_TEXT = {
    en: {
      sender: "Sender",
      character: "Character",
      enemy: "Enemy",
      unresolved: "Unknown / unresolved sender",
      unresolvedHelp: "No single character or enemy is supported by the exported combat actors and authored skill identifiers.",
      directOwner: "Skill ownership exported",
      linkedOwner: "Authored skill/projectile chain",
      inferredOwner: "Identifier match only",
      combatTitle: "Sender, skill, and combat links",
      combatIntro: "This merges the useful part of Combat into the projectile record: who sends it, which exported skill supports that assignment, and what combat records are connected.",
      skillGroup: "Named skill",
      authoredSkill: "Authored skill ID",
      ownerEvidence: "Sender evidence",
      links: "Combat links for this sender",
      specificLinks: "Links for the matched skill",
      technical: "Evidence",
      relation: "Relationship",
      source: "Source",
      path: "Field / path",
      direct: "Exported link",
      inferred: "Matched link",
      linkLimit: "Showing the first {shown} of {total} links. Use the debug-only Combat page for the exhaustive graph.",
      graphUnavailable: "Combat relationship data is unavailable, so these records stay in the unresolved group.",
      noSpecificLinks: "No skill-specific combat links were exported for this projectile.",
      recordsInGroup: "records",
      selected: "Selected",
    },
    zh: {
      sender: "\u53d1\u8d77\u8005",
      character: "\u89d2\u8272",
      enemy: "\u654c\u4eba",
      unresolved: "\u672a\u77e5 / \u672a\u89e3\u6790\u53d1\u8d77\u8005",
      unresolvedHelp: "\u5bfc\u51fa\u7684\u6218\u6597\u89d2\u8272\u4e0e\u6280\u80fd\u6807\u8bc6\u65e0\u6cd5\u652f\u6301\u552f\u4e00\u7684\u89d2\u8272\u6216\u654c\u4eba\u5f52\u5c5e\u3002",
      directOwner: "\u5df2\u5bfc\u51fa\u6280\u80fd\u5f52\u5c5e",
      linkedOwner: "\u5df2\u5bfc\u51fa\u6280\u80fd / \u6295\u5c04\u7269\u5173\u7cfb\u94fe",
      inferredOwner: "\u4ec5\u6807\u8bc6\u5339\u914d",
      combatTitle: "\u53d1\u8d77\u8005\u3001\u6280\u80fd\u4e0e\u6218\u6597\u5173\u7cfb",
      combatIntro: "\u8fd9\u91cc\u5c06 Combat \u9875\u4e2d\u6709\u7528\u7684\u90e8\u5206\u5408\u5e76\u5230\u6295\u5c04\u7269\uff1a\u8c01\u53d1\u8d77\u5b83\u3001\u54ea\u4e2a\u5bfc\u51fa\u6280\u80fd\u652f\u6301\u8be5\u5f52\u5c5e\uff0c\u4ee5\u53ca\u8fde\u63a5\u4e86\u54ea\u4e9b\u6218\u6597\u8bb0\u5f55\u3002",
      skillGroup: "\u547d\u540d\u6280\u80fd",
      authoredSkill: "\u914d\u7f6e\u6280\u80fd ID",
      ownerEvidence: "\u53d1\u8d77\u8005\u8bc1\u636e",
      links: "\u8be5\u53d1\u8d77\u8005\u7684\u6218\u6597\u5173\u7cfb",
      specificLinks: "\u5339\u914d\u6280\u80fd\u7684\u5173\u7cfb",
      technical: "\u8bc1\u636e",
      relation: "\u6570\u636e\u5173\u7cfb",
      source: "\u6765\u6e90",
      path: "\u5b57\u6bb5 / \u8def\u5f84",
      direct: "\u5bfc\u51fa\u76f4\u94fe",
      inferred: "\u5339\u914d\u5173\u7cfb",
      linkLimit: "\u663e\u793a\u524d {shown} / {total} \u6761\u5173\u7cfb\u3002\u8be6\u7ec6\u56fe\u8bf7\u4f7f\u7528\u4ec5\u8c03\u8bd5\u6a21\u5f0f\u53ef\u89c1\u7684 Combat \u9875\u3002",
      graphUnavailable: "\u6218\u6597\u5173\u7cfb\u6570\u636e\u4e0d\u53ef\u7528\uff0c\u56e0\u6b64\u8fd9\u4e9b\u8bb0\u5f55\u4fdd\u7559\u5728\u672a\u89e3\u6790\u5206\u7ec4\u4e2d\u3002",
      noSpecificLinks: "\u6ca1\u6709\u4e3a\u8be5\u6295\u5c04\u7269\u5bfc\u51fa\u6280\u80fd\u4e13\u5c5e\u6218\u6597\u5173\u7cfb\u3002",
      recordsInGroup: "\u6761\u8bb0\u5f55",
      selected: "\u5df2\u9009",
    },
  };
  const TEXT = {
    en: {
      title: "Projectile Behavior Inspector", purpose: "See how an authored projectile travels, collides, chooses targets, ends, and triggers visual or sound cues.", why: "Why care?", whyBody: "Skills often hide important behavior in a separate projectile record. This view exposes that behavior without pretending to run the combat simulation.", q1: "How does it move and end?", q1b: "Check its lifetime, speed, travel mode, curves, reach rules, and finish conditions.", q2: "What can it hit?", q2b: "Inspect collision shape, faction and tag filters, repeat-hit rules, and maximum hit count.", q3: "What happens on launch or impact?", q3b: "Find the effects and sound fields authored for launch, reach, hit, block, and finish.", start: "Start here:", startBody: "search for a character name such as pelica, choose a projectile, then read “At a glance” before opening the detailed sections.", limits: "Limits and technical terms", find: "Find a projectile", placeholder: "Character, skill, effect, or data ID", fileGroup: "Data file group", allGroups: "All file groups", clear: "Clear filters", records: "projectile records", full: "Record fully decoded", partial: "Record partly decoded", glance: "Projectile at a glance", lifetime: "Lifetime limits", movement: "Movement", hit: "Hit behavior", visual: "Visual effects", modes: "authored modes", maxHits: "max hits", effects: "authored effect references", confidence: "Limits and decoder confidence", noMatch: "Nothing matched", noMatchBody: "Try a character name, a shorter skill ID, or clear the filters.",
    },
    zh: {
      title: "投射物行为查看器", purpose: "查看配置中的投射物如何移动、碰撞、选择目标、结束，并触发画面或声音提示。", why: "为什么值得看？", whyBody: "技能的重要行为经常藏在独立的投射物记录中。本页把这些配置展开，但不会假装已经模拟了战斗运行过程。", q1: "它怎样移动和结束？", q1b: "查看存在时间、速度、移动模式、曲线、到达规则与结束条件。", q2: "它能命中什么？", q2b: "查看碰撞形状、阵营与标签过滤、重复命中规则和最大命中数。", q3: "发射或命中时发生什么？", q3b: "查找发射、到达、命中、格挡与结束时配置的特效和声音字段。", start: "建议从这里开始：", startBody: "搜索 pelica 等角色名，选择一个投射物，先阅读“一览”，再展开详细栏目。", limits: "局限与技术术语", find: "查找投射物", placeholder: "角色、技能、特效或数据 ID", fileGroup: "数据文件组", allGroups: "全部文件组", clear: "清除筛选", records: "条投射物记录", full: "记录已完整解码", partial: "记录仅部分解码", glance: "投射物一览", lifetime: "存续限制", movement: "移动", hit: "命中行为", visual: "视觉特效", modes: "个配置移动模式", maxHits: "最大命中数", effects: "个配置特效引用", confidence: "局限与解码可信度", noMatch: "没有匹配结果", noMatchBody: "请尝试角色名、较短的技能 ID，或清除筛选。",
    },
  };

  const state = {
    container: null,
    uiLocale: "en",
    dataPath: DEFAULT_DATA_PATH,
    payload: null,
    language: "CN",
    combatPayload: null,
    combatIndex: null,
    combatError: "",
    combatAssignments: new Map(),
    entries: [],
    filtered: [],
    selectedKey: "",
    query: "",
    source: "all",
    visibleLimit: PAGE_SIZE,
    loadToken: 0,
    abortController: null,
    combatAbortController: null,
    combatLoadToken: 0,
    listeners: [],
  };

  const normalizeLocale = (value) => String(value || "en").toLowerCase().startsWith("zh") ? "zh" : "en";
  const detectLocale = () => normalizeLocale(window.WEBUI_UI_LOCALE || document.documentElement.lang || "en");
  const t = (key) => (TEXT[state.uiLocale] || TEXT.en)[key] || TEXT.en[key] || key;
  const ct = (key) => (COMBAT_TEXT[state.uiLocale] || COMBAT_TEXT.en)[key] || COMBAT_TEXT.en[key] || key;
  const ui = (en, zh) => state.uiLocale === "zh" ? zh : en;
  const detectLanguage = () => String(document.querySelector("#language")?.value || "CN").toUpperCase();
  const combatDataPath = (language) => `data/lang/${encodeURIComponent(String(language || "CN").toUpperCase())}/gameplay/combat_relationships.json`;

  function bindLocaleListener() {
    if (localeListenerBound) return;
    localeListenerBound = true;
    window.addEventListener("webui:ui-locale-changed", (event) => {
      const next = normalizeLocale(event.detail?.locale || detectLocale());
      if (next === state.uiLocale) return;
      state.uiLocale = next;
      if (state.container && state.payload) render(state.payload);
    });
  }

  function bindLanguageListener() {
    if (languageListenerBound) return;
    languageListenerBound = true;
    window.addEventListener("webui:language-changed", (event) => {
      const language = String(event.detail?.language || detectLanguage()).toUpperCase();
      if (!state.container || !state.payload || language === state.language) return;
      loadCombat(language);
    });
  }

  function escapeHtml(value) {
    const helper = window.WebUI && window.WebUI.escapeHtml;
    if (typeof helper === "function") return helper(value == null ? "" : String(value));
    return String(value == null ? "" : value).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[char]);
  }

  function asContainer(value) {
    if (value instanceof Element) return value;
    return document.querySelector(value || DEFAULT_CONTAINER);
  }

  function listen(target, type, handler) {
    if (!target) return;
    target.addEventListener(type, handler);
    state.listeners.push(() => target.removeEventListener(type, handler));
  }

  function clearListeners() {
    state.listeners.splice(0).forEach((remove) => remove());
  }

  function readableIdentifier(value) {
    return String(value || "")
      .replace(/^projectile_/, "")
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .replace(/([A-Za-z])(\d+)/g, "$1 $2")
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function hasIdentifier(text, identifier) {
    const value = String(text || "").toLowerCase();
    const key = String(identifier || "").toLowerCase();
    if (!value || !key) return false;
    return value === key || value.startsWith(`${key}_`) || value.endsWith(`_${key}`) || value.includes(`_${key}_`);
  }

  function buildCombatIndex(payload) {
    if (!payload || !Array.isArray(payload.nodes) || !Array.isArray(payload.edges)) return null;
    const nodes = new Map(payload.nodes.map((node) => [node.id, node]));
    const outgoing = new Map();
    payload.edges.forEach((edge, index) => {
      if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
      outgoing.get(edge.source).push({ edge, index });
    });
    const owners = new Map();
    const skillMappings = [];
    const rootSet = new Set(payload.roots || []);
    for (const ownerId of rootSet) {
      const owner = nodes.get(ownerId);
      if (!owner) continue;
      owners.set(ownerId, owner);
      for (const { edge } of outgoing.get(ownerId) || []) {
        if (edge.confidence !== "direct") continue;
        const target = nodes.get(edge.target);
        if (!target) continue;
        if (edge.type === "has_skill_group") {
          for (const { edge: skillEdge } of outgoing.get(target.id) || []) {
            if (skillEdge.type !== "references_action_skill" || skillEdge.confidence !== "direct") continue;
            const skill = nodes.get(skillEdge.target);
            const skillKey = String(skill?.key || skill?.label || "").toLowerCase();
            if (skillKey) skillMappings.push({ ownerId, owner, group: target, skill, skillKey, ownerEdge: edge, skillEdge });
          }
        } else if (edge.type === "has_enemy_ability") {
          const skillKey = String(target.key || target.label || "").toLowerCase();
          if (skillKey) skillMappings.push({ ownerId, owner, group: null, skill: target, skillKey, ownerEdge: edge, skillEdge: null });
        }
      }
    }
    const projectileMappings = new Map();
    for (const mapping of skillMappings) {
      for (const { edge } of outgoing.get(mapping.skill?.id) || []) {
        if (edge.type !== "skill_data_has_param_string" || edge.confidence !== "direct") continue;
        const target = nodes.get(edge.target);
        const projectileId = String(target?.label || target?.key || "").toLowerCase();
        if (!projectileId.startsWith("projectile_")) continue;
        if (!projectileMappings.has(projectileId)) projectileMappings.set(projectileId, []);
        projectileMappings.get(projectileId).push({ ...mapping, projectileEdge: edge, projectileNode: target });
      }
    }
    return { payload, nodes, outgoing, owners, rootSet, skillMappings, projectileMappings };
  }

  function uniqueMappings(mappings) {
    const byOwner = new Map();
    for (const mapping of mappings) {
      if (!mapping?.ownerId) continue;
      if (!byOwner.has(mapping.ownerId)) byOwner.set(mapping.ownerId, mapping);
    }
    return [...byOwner.values()];
  }

  function assignCombat(entry) {
    const index = state.combatIndex;
    if (!index) return { ownerId: "", confidence: "unresolved", method: "graph-unavailable" };
    const projectileId = String(entry.id || "").toLowerCase();
    const authoredRefs = [
      ...((entry.template || {}).activeSkillIds || []),
      ...((entry.template || {}).passiveSkillIds || []),
      ...((entry.template || {}).normalAttackIds || []),
    ].map((value) => String(value).toLowerCase());

    const directProjectile = uniqueMappings(index.projectileMappings.get(projectileId) || []);
    if (directProjectile.length === 1) {
      // The exported graph proves owner -> skill and skill -> projectile
      // parameter references, but not a single projectile -> sender ownership
      // field. Keep the useful assignment while labelling the composed join.
      return { ...directProjectile[0], confidence: "inferred", method: "authored-skill-parameter-chain" };
    }
    if (directProjectile.length > 1) {
      return { ownerId: "", confidence: "unresolved", method: "ambiguous-skill-parameter-edge" };
    }

    const directSkill = uniqueMappings(index.skillMappings.filter((mapping) => authoredRefs.some((ref) => ref === mapping.skillKey)));
    if (directSkill.length === 1) {
      return { ...directSkill[0], confidence: "direct", method: "authored-skill-reference" };
    }
    if (directSkill.length > 1) {
      return { ownerId: "", confidence: "unresolved", method: "ambiguous-authored-skill-reference" };
    }

    // A projectile commonly names a derived hit/projhit skill whose identifier
    // begins with the owner skill id. That is useful evidence, but it is still
    // an identifier-family join rather than an exported ownership edge.
    const skillFamily = uniqueMappings(index.skillMappings.filter((mapping) => authoredRefs.some((ref) => ref.startsWith(`${mapping.skillKey}_`))));
    if (skillFamily.length === 1) {
      return { ...skillFamily[0], confidence: "inferred", method: "authored-skill-family-identifier" };
    }
    if (skillFamily.length > 1) {
      return { ownerId: "", confidence: "unresolved", method: "ambiguous-authored-skill-family" };
    }

    const ownerFromSkillRef = [...index.owners.entries()].filter(([, owner]) => {
      const key = owner.key || String(owner.id || "").split(":", 2)[1];
      return authoredRefs.some((ref) => hasIdentifier(ref, key));
    });
    if (ownerFromSkillRef.length === 1) {
      return { ownerId: ownerFromSkillRef[0][0], owner: ownerFromSkillRef[0][1], confidence: "inferred", method: "authored-skill-identifier" };
    }
    if (ownerFromSkillRef.length > 1) {
      return { ownerId: "", confidence: "unresolved", method: "ambiguous-authored-skill-identifier" };
    }

    const ownerFromProjectile = [...index.owners.entries()].filter(([, owner]) => {
      const key = owner.key || String(owner.id || "").split(":", 2)[1];
      return hasIdentifier(projectileId, key);
    });
    if (ownerFromProjectile.length === 1) {
      return { ownerId: ownerFromProjectile[0][0], owner: ownerFromProjectile[0][1], confidence: "inferred", method: "projectile-identifier" };
    }
    return { ownerId: "", confidence: "unresolved", method: ownerFromProjectile.length ? "ambiguous-projectile-identifier" : "no-supported-owner" };
  }

  function enrichCombatAssignments() {
    state.combatAssignments = new Map();
    for (const entry of state.entries) state.combatAssignments.set(entry.key, assignCombat(entry));
  }

  function combatAssignment(entry) {
    return state.combatAssignments.get(entry?.key) || { ownerId: "", confidence: "unresolved", method: "not-indexed" };
  }

  function ownerLabel(assignment) {
    return assignment?.owner?.label || ct("unresolved");
  }

  function ownerKindLabel(assignment) {
    if (!assignment?.owner) return ct("unresolvedHelp");
    return assignment.owner.kind === "enemy" ? ct("enemy") : ct("character");
  }

  function entryDisplayName(entry) {
    const assignment = combatAssignment(entry);
    const ownerKey = String(assignment.owner?.key || "").toLowerCase();
    if (assignment.group?.label && assignment.skillKey) {
      const suffix = assignment.skillKey.startsWith(`${ownerKey}_`) ? assignment.skillKey.slice(ownerKey.length + 1) : assignment.skillKey;
      return `${assignment.group.label} \u00b7 ${readableIdentifier(suffix)}`;
    }
    if (assignment.skill?.label && String(assignment.skill.label).toLowerCase() !== assignment.skillKey) return assignment.skill.label;
    let value = String(entry.id || "").replace(/^projectile_/, "");
    if (ownerKey && value.toLowerCase().startsWith(`${ownerKey}_`)) value = value.slice(ownerKey.length + 1);
    return readableIdentifier(value) || entry.id;
  }

  function groupKey(entry) {
    return combatAssignment(entry).ownerId || "__unresolved__";
  }

  function groupSortValue(group) {
    const assignment = group.assignment;
    const rank = !assignment?.owner ? 2 : assignment.owner.kind === "character" ? 0 : 1;
    return `${rank}:${ownerLabel(assignment).toLocaleLowerCase()}:${group.key}`;
  }

  function relationLabel(value) {
    return readableIdentifier(value);
  }

  function formatTemplate(value, values) {
    return Object.entries(values).reduce((result, [key, replacement]) => result.replace(`{${key}}`, String(replacement)), String(value));
  }

  function number(value) {
    return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 6 }) : String(value ?? "—");
  }

  function enumText(value) {
    if (value == null) return "—";
    if (typeof value !== "object") return String(value);
    const numeric = value.value == null ? "" : String(value.value);
    const named = value.name || value.enumType || "";
    const hex = value.hex && value.hex !== numeric ? value.hex : "";
    return [named, numeric && named ? `(${numeric})` : numeric, hex].filter(Boolean).join(" ") || "—";
  }

  function scalarText(value) {
    if (value == null) return "—";
    if (typeof value !== "object") return number(value);
    const candidate = value.valueFloatCandidate ?? value.valueIntCandidate ?? value.value;
    if (value.useBlackboardKey && value.blackboardKey) return `${number(candidate)} · BB: ${value.blackboardKey}`;
    if (value.blackboardKey) return `${number(candidate)} · key: ${value.blackboardKey}`;
    return number(candidate);
  }

  function vectorText(value) {
    if (!value || typeof value !== "object") return "—";
    const candidate = value.valueCandidate;
    if (candidate) return `(${number(candidate.x)}, ${number(candidate.y)}, ${number(candidate.z)})`;
    if (!("x" in value) && !("y" in value) && !("z" in value)) return "—";
    return `(${scalarText(value.x)}, ${scalarText(value.y)}, ${scalarText(value.z)})`;
  }

  function rangeText(value) {
    if (!value || typeof value !== "object") return "—";
    const candidate = value.valueCandidate;
    if (candidate) return `${number(candidate.min)} – ${number(candidate.max)}`;
    return `${scalarText(value.min)} – ${scalarText(value.max)}`;
  }

  function boolText(value) {
    if (value == null) return "—";
    return value ? "Yes" : "No";
  }

  function row(label, value, hint = "") {
    return `<div class="projectile-field"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}${hint ? `<small>${escapeHtml(hint)}</small>` : ""}</dd></div>`;
  }

  function section(title, content, open = true) {
    if (!content) return "";
    return `<details class="projectile-section"${open ? " open" : ""}><summary>${escapeHtml(title)}</summary><div class="projectile-section-body">${content}</div></details>`;
  }

  function curveCard(label, value) {
    const frames = (value && value.keyframes) || [];
    if (!frames.length) return "";
    const body = frames.map((frame, index) => `<tr><td>${index + 1}</td><td>${escapeHtml(number(frame.time))}</td><td>${escapeHtml(number(frame.value))}</td><td>${escapeHtml(number(frame.inSlope))}</td><td>${escapeHtml(number(frame.outSlope))}</td></tr>`).join("");
    return `<div class="projectile-curve"><h5>${escapeHtml(label)}</h5><div class="projectile-curve-meta">${escapeHtml(enumText(value.preInfinity))} → ${escapeHtml(enumText(value.postInfinity))}</div><div class="projectile-table-wrap"><table><thead><tr><th>#</th><th>Time</th><th>Value</th><th>In slope</th><th>Out slope</th></tr></thead><tbody>${body}</tbody></table></div></div>`;
  }

  function renderLifetime(entry) {
    const value = entry.lifetime || {};
    return `<dl class="projectile-fields">
      ${row("Finish duration", scalarText(value.finishDuration))}
      ${row("Finish distance", scalarText(value.finishDistance))}
      ${row("Finish on reach", boolText(value.finishOnReach))}
      ${row("Hit on reach", boolText(value.hitOnReach))}
      ${row("Keep moving on reach", boolText(value.keepMoveOnReach))}
      ${row("Main-effect finish type", enumText(value.mainEffectFinishType), "Numeric semantics are qualified when unnamed.")}
      ${row("Main-effect finish distance", number(value.mainEffectFinishDistance))}
    </dl>`;
  }

  function renderCollision(entry) {
    const value = entry.collision || {};
    return `<dl class="projectile-fields">
      ${row("Shape", enumText(value.shapeType))}
      ${row("Radius", scalarText(value.radius))}
      ${row("Center", vectorText(value.center))}
      ${row("Extent", vectorText(value.extent))}
      ${row("Initial outer radius", scalarText(value.initOuterRadius))}
      ${row("Initial inner radius", scalarText(value.initInnerRadius))}
      ${row("Outer growth speed", scalarText(value.outerRadiusIncreaseSpeed))}
      ${row("Inner growth speed", scalarText(value.innerRadiusIncreaseSpeed))}
      ${row("Height", scalarText(value.height))}
      ${row("Sector", boolText(value.isSector))}
      ${row("Sector direction", enumText(value.sectorDirection))}
      ${row("Sector angle", scalarText(value.sectorAngle))}
    </dl>`;
  }

  function renderTargeting(entry) {
    const value = entry.targeting || {};
    const filter = value.targetFilter || {};
    const query = filter.tagQuery || {};
    return `<dl class="projectile-fields">
      ${row("Block layer definition", enumText(value.blockLayerDef))}
      ${row("Block layer", enumText(value.blockLayer))}
      ${row("Check alive", boolText(filter.checkAlive))}
      ${row("Auto-set target faction", boolText(filter.autoSetTargetFaction))}
      ${row("Faction target", enumText(filter.factionTarget))}
      ${row("Target faction type", enumText(filter.targetFactionType))}
      ${row("Filter slot", boolText(filter.filterSlot))}
      ${row("Slot index", number(filter.slotIndex))}
      ${row("Filter gameplay tag", boolText(filter.filterGameplayTag))}
      ${row("Tag query", `${enumText(query.queryType)}${(query.tags || []).length ? ` · ${query.tags.join(", ")}` : ""}`)}
      ${row("Ignore immune level", enumText(value.ignoreImmuneLevel))}
      ${row("Max hit count", scalarText(value.maxHitCount))}
      ${row("Allow same target", boolText(value.allowHitSameTarget))}
      ${row("Hit interval per target", number(value.hitIntervalPerTarget))}
    </dl>`;
  }

  function renderBezier(label, point) {
    if (!point) return "";
    return `<div class="projectile-mini-card"><h5>${escapeHtml(label)}</h5><dl class="projectile-fields projectile-fields-compact">
      ${row("Status", point.status || "—")}
      ${row("Preset point", point.usePresetPoint ? point.presetPointKey || "Yes" : "No")}
      ${row("X ratio", rangeText(point.xRatioRange))}
      ${row("YZ angle", rangeText(point.yzAngleRange))}
      ${row("YZ radius", rangeText(point.yzRadiusRange))}
      ${row("Scale YZ radius", boolText(point.scaledYzRadius))}
    </dl></div>`;
  }

  function renderMovement(entry) {
    const movement = entry.movement || {};
    const segments = (movement.segments || []).map((segment, index) => `<article class="projectile-mini-card"><h4>Segment ${index + 1}: ${escapeHtml(segment.startPointKey || "?")} → ${escapeHtml(segment.endPointKey || "?")}</h4><dl class="projectile-fields projectile-fields-compact">
      ${row("Move mode", segment.moveModeId || "—")}
      ${row("Early next by duration", boolText(segment.earlyNextByDuration))}
      ${row("Duration", scalarText(segment.segmentDuration))}
      ${row("Speed lerp time", scalarText(segment.speedLerpTime))}
    </dl></article>`).join("");
    const modes = (movement.modes || []).map((mode, index) => `<article class="projectile-mode-card"><header><h4>${escapeHtml(mode.key || `Mode ${index + 1}`)}</h4><span class="projectile-confidence-pill">Exact structure · qualified semantics</span></header><dl class="projectile-fields">
      ${row("Trace type", enumText(mode.traceType), "Member name is withheld when not independently validated.")}
      ${row("Trace time", scalarText(mode.traceTime))}
      ${row("Trace-until distance", scalarText(mode.traceUntilDistance))}
      ${row("Move type", enumText(mode.moveType))}
      ${row("Parabola definition", enumText(mode.parabolaDef))}
      ${row("Speed", scalarText(mode.speed))}
      ${row("Scale speed with distance", boolText(mode.useSpeedScaleWithDistance))}
      ${row("Lock velocity to XZ", boolText(mode.lockVelocityToXZ))}
      ${row("Grounded move", boolText(mode.groundedMove))}
      ${row("Limit angular speed", boolText(mode.limitAngularSpeed))}
      ${row("Angular speed", scalarText(mode.angularSpeed))}
      ${row("Travel duration", scalarText(mode.travelDuration))}
      ${row("Vertex Y offset", scalarText(mode.vertexYOffset))}
      ${row("Gravity", scalarText(mode.gravity))}
    </dl><div class="projectile-curve-grid">${curveCard("Speed curve", mode.speedCurve)}${curveCard("Distance scale", mode.speedScaleWithDistance)}${curveCard("Angular-speed curve", mode.angularSpeedCurve)}</div><div class="projectile-mini-grid">${renderBezier("Bezier midpoint 1", mode.bezierMidPoint1)}${renderBezier("Bezier midpoint 2", mode.bezierMidPoint2)}</div></article>`).join("");
    return `<div class="projectile-inline-meta"><span>Segment movement: <strong>${boolText(movement.useSegmentMove)}</strong></span><span>Preset points: <strong>${escapeHtml((movement.presetPointKeys || []).join(", ") || "None")}</strong></span></div>${segments ? `<div class="projectile-mini-grid">${segments}</div>` : ""}${modes || '<p class="projectile-muted">No authored movement modes.</p>'}`;
  }

  function renderEffectBehavior(value) {
    if (!value || !Object.keys(value).length) return "";
    return `<dl class="projectile-fields projectile-fields-compact">
      ${row("Move / position", `${enumText(value.moveType)} / ${enumText(value.positionRef)}`)}
      ${row("Visible with entity", boolText(value.visibleWithEntity))}
      ${row("Follow grounded", `${boolText(value.followGrounded)} · max ${number(value.followGroundedMaxDistance)}`)}
      ${row("Position offset", value.usePositionOffsetBB ? vectorText(value.positionOffsetBB) : vectorText(value.positionOffset))}
      ${row("Rotation", `${enumText(value.rotType)} · ref ${enumText(value.rotRef)}`)}
      ${row("Alert type", enumText(value.alertType))}
      ${row("Animate alert", `${boolText(value.animateAlert)} · ${number(value.alertAnimateDuration)}`)}
      ${row("Angle / hollow", `${number(value.angle)} / ${number(value.hollow)}`)}
      ${row("Modify type / value", `${enumText(value.modifyType)} / ${number(value.value)}`)}
    </dl>`;
  }

  function renderEffectCard(effect, index) {
    return `<article class="projectile-mini-card"><header><h4>${escapeHtml(effect.effectName || `Unnamed effect ${index + 1}`)}</h4><span>${escapeHtml(enumText(effect.fxType))}</span></header><dl class="projectile-fields projectile-fields-compact">
      ${row("Guard / force guard", `${boolText(effect.guardEffect)} / ${boolText(effect.forceGuardEffect)}`)}
      ${row("Scale", vectorText({ valueCandidate: effect.scale }))}
      ${row("Length", scalarText(effect.lengthBB))}
      ${row("Release by action", boolText(effect.releaseByAction))}
      ${row("Ignore owner time scale", boolText(effect.ignoreOwnerTimeScale))}
      ${row("Interrupt time", number(effect.interruptTime))}
    </dl>${renderEffectBehavior(effect.behavior)}</article>`;
  }

  function renderEffects(entry) {
    const effects = entry.effects || {};
    const lists = effects.lists || {};
    const groups = Object.entries(lists).map(([name, rows]) => {
      if (!rows.length) return `<div class="projectile-effect-group"><h4>${escapeHtml(name)} <span>0</span></h4></div>`;
      return `<div class="projectile-effect-group"><h4>${escapeHtml(name)} <span>${rows.length}</span></h4><div class="projectile-mini-grid">${rows.map(renderEffectCard).join("")}</div></div>`;
    }).join("");
    const alert = effects.alert || {};
    return `<div class="projectile-inline-meta"><span>Reach requires target: <strong>${boolText(effects.showReachEffectOnlyWithTarget)}</strong></span><span>Finish only when unblocked and no hit: <strong>${boolText(effects.showFinishEffectOnlyWhenUnblockAndNotHit)}</strong></span></div>${groups}<div class="projectile-effect-group projectile-alert"><h4>Alert effect <span>${effects.showAlertEffect ? "shown" : "not shown"}</span></h4>${renderEffectCard(alert, 0)}</div>`;
  }

  function renderSounds(entry) {
    const sounds = entry.sounds || {};
    const keys = ["launchSound", "loopSound", "reachSound", "hitSound", "blockSound", "finishedSound", "sizzleSound"];
    return `<p class="projectile-callout">These are metadata-named hash-like authored values. They are not presented as resolved Wwise event IDs.</p><dl class="projectile-fields">${keys.map((key) => row(key.replace(/([A-Z])/g, " $1"), enumText(sounds[key]))).join("")}${row("Sizzle trigger distance", number(sounds.sizzleSoundTriggerDistance))}${row("Ring sound smooth factor", number(sounds.ringProjectileSoundSmoothFactor))}</dl>`;
  }

  function renderSource(entry) {
    const source = entry.source || {};
    const template = entry.template || {};
    return `<dl class="projectile-fields">
      ${row("Source root", source.root)}
      ${row("Asset name", source.assetName)}
      ${row("Path ID", source.pathId)}
      ${row("CAB source", source.sourceFile)}
      ${row("VFS path", source.vfsPath)}
      ${row("Decoded JSON", source.jsonPath)}
      ${row("Raw byte size", number(source.byteSize))}
      ${row("Raw SHA-256", source.rawDataSha256)}
      ${row("TypeTree source", source.typeTreeSource)}
      ${row("Faction index", enumText(template.factionIndex))}
      ${row("Born tag", enumText(template.bornTag))}
      ${row("Active skills", (template.activeSkillIds || []).join(", ") || "None")}
      ${row("Passive skills", (template.passiveSkillIds || []).join(", ") || "None")}
      ${row("Normal attacks", (template.normalAttackIds || []).join(", ") || "None")}
    </dl>`;
  }

  function renderCombatEdge(edge) {
    const index = state.combatIndex;
    const source = index?.nodes.get(edge.source) || {};
    const target = index?.nodes.get(edge.target) || {};
    const evidence = edge.evidence || {};
    const evidenceBody = [
      `<div><strong>${escapeHtml(ct("relation"))}:</strong> ${escapeHtml(edge.type)}</div>`,
      evidence.source ? `<div><strong>${escapeHtml(ct("source"))}:</strong> ${escapeHtml(evidence.source)}</div>` : "",
      evidence.path ? `<div><strong>${escapeHtml(ct("path"))}:</strong> ${escapeHtml(evidence.path)}</div>` : "",
      edge.note ? `<p>${escapeHtml(edge.note)}</p>` : "",
      evidence.raw !== undefined ? `<pre>${escapeHtml(JSON.stringify(evidence.raw, null, 2))}</pre>` : "",
    ].join("");
    return `<article class="projectile-combat-edge"><div><span class="projectile-combat-node">${escapeHtml(source.label || source.key || edge.source)}</span><span class="projectile-combat-arrow" aria-hidden="true">\u2192</span><span class="projectile-combat-relation">${escapeHtml(relationLabel(edge.type))}</span><span class="projectile-combat-arrow" aria-hidden="true">\u2192</span><span class="projectile-combat-node">${escapeHtml(target.label || target.key || edge.target)}</span><span class="projectile-combat-confidence is-${escapeHtml(edge.confidence || "direct")}">${escapeHtml(edge.confidence === "inferred" ? ct("inferred") : ct("direct"))}</span></div>${evidenceBody ? `<details><summary>${escapeHtml(ct("technical"))}</summary><div class="projectile-combat-evidence">${evidenceBody}</div></details>` : ""}</article>`;
  }

  function renderCombatConnections(entry) {
    const assignment = combatAssignment(entry);
    if (!assignment.owner || !state.combatIndex) {
      return `<section class="projectile-combat-card is-unresolved"><header><div><span class="projectile-eyebrow">${escapeHtml(ct("sender"))}</span><h3>${escapeHtml(ct("unresolved"))}</h3></div><span class="projectile-combat-confidence is-unresolved">${escapeHtml(ct("unresolved"))}</span></header><p>${escapeHtml(state.combatError ? ct("graphUnavailable") : ct("unresolvedHelp"))}</p><dl class="projectile-fields projectile-fields-compact">${row(ct("ownerEvidence"), assignment.method || "no-supported-owner")}</dl></section>`;
    }

    const index = state.combatIndex;
    const specific = [];
    const seenSpecific = new Set();
    const addSpecific = (edge) => {
      if (!edge) return;
      const key = `${edge.source}\u0000${edge.type}\u0000${edge.target}`;
      if (seenSpecific.has(key)) return;
      seenSpecific.add(key);
      specific.push(edge);
    };
    addSpecific(assignment.ownerEdge);
    addSpecific(assignment.skillEdge);
    addSpecific(assignment.projectileEdge);
    for (const { edge } of index.outgoing.get(assignment.skill?.id) || []) addSpecific(edge);

    const rootIndexes = index.payload.rootEdges?.[assignment.ownerId] || [];
    const allLinks = rootIndexes.map((edgeIndex) => index.payload.edges[edgeIndex]).filter(Boolean);
    const shown = allLinks.slice(0, COMBAT_LINK_LIMIT);
    const ownerKey = assignment.owner.key || String(assignment.owner.id || "").split(":", 2)[1] || assignment.owner.id;
    const confidenceText = assignment.confidence === "direct"
      ? ct("directOwner")
      : assignment.method === "authored-skill-parameter-chain"
        ? ct("linkedOwner")
        : ct("inferredOwner");
    const facts = [
      row(ct("sender"), `${ownerLabel(assignment)} \u00b7 ${ownerKey}`, ownerKindLabel(assignment)),
      assignment.group ? row(ct("skillGroup"), assignment.group.label || assignment.group.key, assignment.group.subtitle || "") : "",
      assignment.skillKey ? row(ct("authoredSkill"), assignment.skillKey) : "",
      row(ct("ownerEvidence"), confidenceText, assignment.method),
    ].join("");
    const specificBody = specific.length
      ? `<div class="projectile-combat-list">${specific.map(renderCombatEdge).join("")}</div>`
      : `<p class="projectile-muted">${escapeHtml(ct("noSpecificLinks"))}</p>`;
    const limitNote = formatTemplate(ct("linkLimit"), { shown: shown.length, total: allLinks.length });
    return `<section class="projectile-combat-card"><header><div><span class="projectile-eyebrow">${escapeHtml(ct("sender"))} \u00b7 ${escapeHtml(ownerKindLabel(assignment))}</span><h3>${escapeHtml(ownerLabel(assignment))}</h3><p>${escapeHtml(ct("combatIntro"))}</p></div><span class="projectile-combat-confidence is-${escapeHtml(assignment.confidence)}">${escapeHtml(confidenceText)}</span></header><dl class="projectile-fields">${facts}</dl><details class="projectile-combat-specific" open><summary>${escapeHtml(ct("specificLinks"))} <span>${specific.length}</span></summary>${specificBody}</details><details class="projectile-combat-all"><summary>${escapeHtml(ct("links"))} <span>${allLinks.length}</span></summary><p class="projectile-combat-limit">${escapeHtml(limitNote)}</p><div class="projectile-combat-list">${shown.map(renderCombatEdge).join("")}</div></details></section>`;
  }

  function renderDetail(entry) {
    const root = state.container && state.container.querySelector("[data-projectile-detail]");
    if (!root) return;
    if (!entry) {
      root.innerHTML = '<div class="projectile-empty">Select a projectile from the list.</div>';
      return;
    }
    const confidence = entry.confidence || {};
    const qualifiers = (confidence.qualifiers || []).map((text) => `<li>${escapeHtml(text)}</li>`).join("");
    const modes = (entry.movement || {}).modes || [];
    const effects = Object.values((entry.effects || {}).lists || {}).flat();
    root.innerHTML = `<article class="projectile-detail"><header class="projectile-detail-header" tabindex="-1"><div><div class="projectile-eyebrow">${escapeHtml((entry.source || {}).root || "")}</div><h2>${escapeHtml(entryDisplayName(entry))}</h2><div class="projectile-path-id">${escapeHtml(entry.id)} \u00b7 Path ID ${escapeHtml((entry.source || {}).pathId || "")}</div></div><span class="projectile-status ${confidence.byteComplete ? "is-exact" : "is-incomplete"}">${escapeHtml(confidence.byteComplete ? t("full") : t("partial"))}</span></header>
      <section class="projectile-at-a-glance" aria-label="${escapeHtml(t("glance"))}"><article><strong>${escapeHtml(t("lifetime"))}</strong><span>${escapeHtml(scalarText((entry.lifetime || {}).finishDuration))} ${state.uiLocale === "zh" ? "时长" : "duration"} · ${escapeHtml(scalarText((entry.lifetime || {}).finishDistance))} ${state.uiLocale === "zh" ? "距离" : "distance"}</span></article><article><strong>${escapeHtml(t("movement"))}</strong><span>${modes.length} ${escapeHtml(t("modes"))}</span></article><article><strong>${escapeHtml(t("hit"))}</strong><span>${escapeHtml(enumText((entry.collision || {}).shapeType))} · ${escapeHtml(scalarText((entry.targeting || {}).maxHitCount))} ${escapeHtml(t("maxHits"))}</span></article><article><strong>${escapeHtml(t("visual"))}</strong><span>${effects.length} ${escapeHtml(t("effects"))}</span></article></section>
      ${renderCombatConnections(entry)}
      <details class="projectile-confidence"><summary>${escapeHtml(t("confidence"))}</summary><div><p>${state.uiLocale === "zh" ? "“记录已完整解码”表示解码器消费了观察到的整条记录，并不证明每个字段的玩法含义。" : "Record fully decoded means the decoder consumed the observed record. It does not prove every field’s gameplay meaning."}</p><p>${state.uiLocale === "zh" ? "黑板键是在运行时提供或改变的命名值，因此旁边的导出数值可能只是回退值。单位、未命名枚举、声音哈希与交互仍可能未解析。" : "A blackboard key names a value supplied or changed at runtime, so the nearby exported number may only be a fallback. Units, unnamed enum meanings, sound hashes, and interactions can remain unresolved."}</p><ul>${qualifiers}</ul></div></details>
      ${section(ui("Lifetime and reach", "存续时间与到达规则"), renderLifetime(entry))}
      ${section(ui("Collision geometry", "碰撞形状"), renderCollision(entry))}
      ${section(ui("Targeting and hit rules", "目标与命中规则"), renderTargeting(entry))}
      ${section(ui("Movement segments, modes, and curves", "移动分段、模式与曲线"), renderMovement(entry), false)}
      ${section(ui("Effect lists and alert behavior", "特效列表与预警行为"), renderEffects(entry), false)}
      ${section(ui("Sound hash fields", "声音哈希字段"), renderSounds(entry), false)}
      ${section(ui("Source and template identity", "来源与模板标识"), renderSource(entry), false)}
    </article>`;
  }

  function searchText(entry) {
    const source = entry.source || {};
    const template = entry.template || {};
    const modes = ((entry.movement || {}).modes || []).map((mode) => mode.key).join(" ");
    const effects = Object.values(((entry.effects || {}).lists || {})).flat().map((effect) => effect.effectName).join(" ");
    const assignment = combatAssignment(entry);
    return [entry.id, entryDisplayName(entry), source.assetName, source.pathId, source.root, source.sourceFile, source.vfsPath, ...(template.activeSkillIds || []), ...(template.passiveSkillIds || []), ...(template.normalAttackIds || []), assignment.owner?.label, assignment.owner?.key, assignment.group?.label, assignment.skillKey, modes, effects].filter(Boolean).join(" ").toLowerCase();
  }

  function applyFilters() {
    const tokens = state.query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    state.filtered = state.entries.filter((entry) => {
      if (state.source !== "all" && (entry.source || {}).root !== state.source) return false;
      if (!tokens.length) return true;
      const haystack = searchText(entry);
      return tokens.every((token) => haystack.includes(token));
    });
    if (!state.filtered.some((entry) => entry.key === state.selectedKey)) {
      state.selectedKey = state.filtered[0]?.key || "";
      renderDetail(state.filtered[0] || null);
    }
    renderList();
  }

  function renderFlatList() {
    if (!state.container) return;
    const count = state.container.querySelector("[data-projectile-shown]");
    const visible = state.filtered.slice(0, state.visibleLimit);
    const selected = state.filtered.find((entry) => entry.key === state.selectedKey);
    const selectedIsPinned = Boolean(selected && !visible.includes(selected));
    if (selectedIsPinned) {
      if (visible.length >= PAGE_SIZE) visible[visible.length - 1] = selected;
      else visible.push(selected);
    }
    if (count) count.textContent = state.uiLocale === "zh"
      ? `显示 ${visible.length} / ${state.filtered.length} 个匹配项 · 共 ${state.entries.length} 条`
      : `Showing ${visible.length} of ${state.filtered.length} matches · ${state.entries.length} total`;
    const root = state.container.querySelector("[data-projectile-list]");
    if (!root) return;
    root.innerHTML = state.filtered.length ? visible.map((entry) => {
      const shape = enumText((entry.collision || {}).shapeType);
      const modes = ((entry.movement || {}).modes || []).length;
      return `<button type="button" class="projectile-row${entry.key === state.selectedKey ? " is-selected" : ""}" data-projectile-key="${escapeHtml(entry.key)}"${entry.key === state.selectedKey ? ' aria-current="true"' : ""}><span>${escapeHtml(entry.id)}${selectedIsPinned && entry.key === state.selectedKey ? `<small class="projectile-selected-note">${ui("Selected", "已选择")}</small>` : ""}</span><small>${escapeHtml((entry.source || {}).root || "")} · ${escapeHtml(shape)} · ${modes} ${ui(`mode${modes === 1 ? "" : "s"}`, "个模式")}</small></button>`;
    }).join("") + (visible.length < state.filtered.length ? `<button type="button" class="projectile-more" data-projectile-more>${state.uiLocale === "zh" ? "再显示" : "Show next"} ${Math.min(PAGE_SIZE, state.filtered.length - visible.length)} <span>(${visible.length} / ${state.filtered.length})</span></button>` : "") : `<div class="projectile-empty projectile-empty-list"><strong>${escapeHtml(t("noMatch"))}</strong><span>${escapeHtml(t("noMatchBody"))}</span></div>`;
  }

  function renderList() {
    if (!state.container) return;
    const count = state.container.querySelector("[data-projectile-shown]");
    const visible = state.filtered.slice(0, state.visibleLimit);
    const selected = state.filtered.find((entry) => entry.key === state.selectedKey);
    const selectedIsPinned = Boolean(selected && !visible.includes(selected));
    if (selectedIsPinned) {
      if (visible.length >= PAGE_SIZE) visible[visible.length - 1] = selected;
      else visible.push(selected);
    }
    if (count) count.textContent = state.uiLocale === "zh"
      ? `显示 ${visible.length} / ${state.filtered.length} 个匹配项 · 共 ${state.entries.length} 条`
      : `Showing ${visible.length} of ${state.filtered.length} matches · ${state.entries.length} total`;
    const root = state.container.querySelector("[data-projectile-list]");
    if (!root) return;
    if (!state.filtered.length) {
      root.innerHTML = `<div class="projectile-empty projectile-empty-list"><strong>${escapeHtml(t("noMatch"))}</strong><span>${escapeHtml(t("noMatchBody"))}</span></div>`;
      return;
    }

    const totals = new Map();
    for (const entry of state.filtered) totals.set(groupKey(entry), (totals.get(groupKey(entry)) || 0) + 1);
    const groups = new Map();
    for (const entry of visible) {
      const key = groupKey(entry);
      if (!groups.has(key)) groups.set(key, { key, assignment: combatAssignment(entry), entries: [] });
      groups.get(key).entries.push(entry);
    }
    const groupHtml = [...groups.values()].sort((left, right) => groupSortValue(left).localeCompare(groupSortValue(right))).map((group) => {
      group.entries.sort((left, right) => entryDisplayName(left).localeCompare(entryDisplayName(right)) || String(left.id).localeCompare(String(right.id)));
      const label = ownerLabel(group.assignment);
      const ownerKey = group.assignment.owner?.key || "";
      const open = group.entries.some((entry) => entry.key === state.selectedKey) || Boolean(state.query);
      const rows = group.entries.map((entry) => {
        const shape = enumText((entry.collision || {}).shapeType);
        const modes = ((entry.movement || {}).modes || []).length;
        const assignment = combatAssignment(entry);
        const evidence = assignment.confidence === "direct" ? ct("directOwner") : assignment.confidence === "inferred" ? ct("inferredOwner") : ct("unresolved");
        return `<button type="button" class="projectile-row${entry.key === state.selectedKey ? " is-selected" : ""}" data-projectile-key="${escapeHtml(entry.key)}"${entry.key === state.selectedKey ? ' aria-current="true"' : ""}><span>${escapeHtml(entryDisplayName(entry))}${selectedIsPinned && entry.key === state.selectedKey ? `<small class="projectile-selected-note">${escapeHtml(ct("selected"))}</small>` : ""}</span><small class="projectile-row-id">${escapeHtml(entry.id)}</small><small>${escapeHtml(shape)} · ${modes} ${ui(`mode${modes === 1 ? "" : "s"}`, "个模式")} · ${escapeHtml(evidence)}</small></button>`;
      }).join("");
      const total = totals.get(group.key) || group.entries.length;
      return `<details class="projectile-owner-group${group.key === "__unresolved__" ? " is-unresolved" : ""}"${open ? " open" : ""}><summary><span><strong>${escapeHtml(label)}</strong><small>${escapeHtml(group.assignment.owner ? `${ownerKindLabel(group.assignment)} · ${ownerKey}` : ct("unresolvedHelp"))}</small></span><b>${group.entries.length === total ? total : `${group.entries.length}/${total}`} ${escapeHtml(ct("recordsInGroup"))}</b></summary><div>${rows}</div></details>`;
    }).join("");
    const more = visible.length < state.filtered.length
      ? `<button type="button" class="projectile-more" data-projectile-more>${ui("Show next", "继续显示")} ${Math.min(PAGE_SIZE, state.filtered.length - visible.length)} <span>(${visible.length} / ${state.filtered.length})</span></button>`
      : "";
    root.innerHTML = groupHtml + more;
  }

  function select(identifier, { focusDetail = false } = {}) {
    const entry = state.entries.find((row) => row.key === identifier) || state.entries.find((row) => row.id === identifier);
    if (!entry) return false;
    state.selectedKey = entry.key;
    renderList();
    renderDetail(entry);
    if (focusDetail) state.container?.querySelector(".projectile-detail-header")?.focus();
    return true;
  }

  function shell(payload) {
    const counts = (payload && payload.counts) || {};
    const sources = Object.keys(counts.bySource || {});
    return `<div class="projectile-toolbar"><div><h1>${escapeHtml(ui("Combat & Projectile Explorer", "战斗与投射物查看器"))}</h1><p>${escapeHtml(ui("Browse projectiles by their resolved character or enemy sender, then inspect skill links, movement, collision, targeting, effects, and source evidence.", "按已解析的角色或敌人发起者浏览投射物，并查看技能关系、移动、碰撞、目标、特效与来源证据。"))}</p></div><div class="projectile-summary"><strong>${escapeHtml(number(counts.projectiles || 0))}</strong> ${escapeHtml(t("records"))}</div></div>
      <section class="projectile-intro" aria-labelledby="projectile-why-title"><div class="projectile-intro-lead"><strong id="projectile-why-title">${escapeHtml(t("why"))}</strong><span>${escapeHtml(t("whyBody"))}</span></div><div class="projectile-question-grid"><article><strong>${escapeHtml(t("q1"))}</strong><span>${escapeHtml(t("q1b"))}</span></article><article><strong>${escapeHtml(t("q2"))}</strong><span>${escapeHtml(t("q2b"))}</span></article><article><strong>${escapeHtml(t("q3"))}</strong><span>${escapeHtml(t("q3b"))}</span></article></div><p class="projectile-first-step"><strong>${escapeHtml(t("start"))}</strong> ${escapeHtml(t("startBody"))}</p></section>
      <details class="projectile-scope"><summary>${escapeHtml(t("limits"))}</summary><div><p>${state.uiLocale === "zh" ? "投射物记录是配置的行为模板，不是在游戏中观察到的一发攻击。" : "A projectile record is an authored behavior template, not a shot observed in play."}</p><p>${state.uiLocale === "zh" ? "黑板键是在运行时提供的命名值。记录完整解码只表示字节已消费，并不表示每个枚举、单位、哈希或运行时交互都已理解。" : "A blackboard key is a named value supplied at runtime. A fully decoded record means its bytes were consumed, not that every enum, unit, hash, or runtime interaction is understood."}</p><p>${state.uiLocale === "zh" ? "文件组、CAB、VFS、TypeTree 与 Path ID 是提取诊断信息，不是玩法描述。" : "Source group, CAB, VFS, TypeTree, and Path ID are extraction diagnostics, not gameplay descriptions."}</p></div></details>
      <div class="projectile-layout"><aside class="projectile-sidebar" aria-label="${ui("Projectile results", "投射物结果")}"><div class="projectile-filters"><label>${escapeHtml(t("find"))}<input type="search" data-projectile-search placeholder="${escapeHtml(t("placeholder"))}" aria-controls="projectile-result-list" autocomplete="off"></label><label>${escapeHtml(t("fileGroup"))}<select data-projectile-source><option value="all">${escapeHtml(t("allGroups"))}</option>${sources.map((source) => `<option value="${escapeHtml(source)}">${escapeHtml(source)} (${escapeHtml(number(counts.bySource[source]))})</option>`).join("")}</select></label><button type="button" class="projectile-reset" data-projectile-reset hidden>${escapeHtml(t("clear"))}</button></div><div class="projectile-list-count" data-projectile-shown role="status"></div><div class="projectile-list" id="projectile-result-list" data-projectile-list></div></aside><main class="projectile-main" data-projectile-detail aria-label="${ui("Selected projectile", "已选择的投射物")}"></main></div>`;
  }

  function render(payload) {
    if (payload) state.payload = payload;
    if (!state.container || !state.payload) return false;
    clearListeners();
    state.entries = Array.isArray(state.payload.entries) ? state.payload.entries : [];
    if (!state.combatIndex || state.combatIndex.payload !== state.combatPayload) state.combatIndex = buildCombatIndex(state.combatPayload);
    enrichCombatAssignments();
    state.filtered = [...state.entries];
    const requested = state.entries.find((entry) => entry.key === state.selectedKey || entry.id === state.selectedKey);
    if (requested) state.selectedKey = requested.key;
    else if (!state.selectedKey) {
      state.selectedKey = (state.entries.find((entry) => entry.id === "projectile_chr_0004_pelica_normal_attack1") || {}).key || "";
    }
    state.container.classList.add("projectile-inspector");
    state.container.innerHTML = shell(state.payload);
    const search = state.container.querySelector("[data-projectile-search]");
    const source = state.container.querySelector("[data-projectile-source]");
    const reset = state.container.querySelector("[data-projectile-reset]");
    const list = state.container.querySelector("[data-projectile-list]");
    search.value = state.query;
    source.value = state.source;
    reset.hidden = !state.query && state.source === "all";
    const filter = () => {
      state.visibleLimit = PAGE_SIZE;
      reset.hidden = !state.query && state.source === "all";
      applyFilters();
    };
    listen(search, "input", () => { state.query = search.value; filter(); });
    listen(source, "change", () => { state.source = source.value; filter(); });
    listen(reset, "click", () => {
      state.query = "";
      state.source = "all";
      state.visibleLimit = PAGE_SIZE;
      search.value = "";
      source.value = "all";
      reset.hidden = true;
      applyFilters();
      search.focus();
    });
    listen(list, "click", (event) => {
      const button = event.target.closest("[data-projectile-key]");
      if (button && list.contains(button)) select(button.dataset.projectileKey, { focusDetail: true });
      if (event.target.closest("[data-projectile-more]")) {
        state.visibleLimit += PAGE_SIZE;
        renderList();
        const replacement = state.container?.querySelector("[data-projectile-more]");
        const rows = state.container?.querySelectorAll?.(".projectile-row");
        (replacement || rows?.[rows.length - 1])?.focus();
      }
    });
    applyFilters();
    const preferred = state.entries.find((entry) => entry.key === state.selectedKey)
      || state.entries.find((entry) => entry.id === "projectile_chr_0004_pelica_normal_attack1")
      || state.entries[0];
    if (preferred) select(preferred.key);
    else renderDetail(null);
    return true;
  }

  async function fetchCombatPayload(language, signal) {
    const response = await fetch(combatDataPath(language), { cache: "no-store", signal });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const payload = await response.json();
    if (!payload || !Array.isArray(payload.roots) || !Array.isArray(payload.nodes) || !Array.isArray(payload.edges)) {
      throw new Error("Unsupported combat relationship payload");
    }
    return payload;
  }

  async function loadCombat(language = detectLanguage()) {
    const token = ++state.combatLoadToken;
    state.language = String(language || "CN").toUpperCase();
    state.combatAbortController?.abort();
    state.combatAbortController = new AbortController();
    try {
      const payload = await fetchCombatPayload(state.language, state.combatAbortController.signal);
      if (token !== state.combatLoadToken || !state.container) return null;
      state.combatPayload = payload;
      state.combatIndex = null;
      state.combatError = payload.graph?.staleReason || "";
      render(state.payload);
      return payload;
    } catch (error) {
      if (error?.name === "AbortError" || token !== state.combatLoadToken || !state.container) return null;
      state.combatPayload = null;
      state.combatIndex = null;
      state.combatError = String(error?.message || error);
      render(state.payload);
      return null;
    }
  }

  async function load(path) {
    state.dataPath = path || state.dataPath || DEFAULT_DATA_PATH;
    if (!state.container) return null;
    const token = ++state.loadToken;
    state.abortController?.abort();
    state.abortController = new AbortController();
    state.container.classList.add("projectile-inspector");
    state.container.innerHTML = `<div class="projectile-empty projectile-loading" role="status"><span aria-hidden="true"></span>${ui("Loading projectile data…", "正在加载投射物数据…")}</div>`;
    try {
      const combatRequest = fetchCombatPayload(state.language, state.abortController.signal)
        .then((payload) => ({ payload, error: "" }))
        .catch((error) => ({ payload: null, error: error?.name === "AbortError" ? "" : String(error?.message || error) }));
      const response = await fetch(state.dataPath, { cache: "no-store", signal: state.abortController.signal });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const payload = await response.json();
      const combat = await combatRequest;
      if (token !== state.loadToken) return null;
      if (!payload || !Array.isArray(payload.entries)) throw new Error("Unsupported projectile payload");
      state.combatPayload = combat.payload;
      state.combatIndex = null;
      state.combatError = combat.error || combat.payload?.graph?.staleReason || "";
      render(payload);
      return payload;
    } catch (error) {
      if (error?.name === "AbortError" || token !== state.loadToken) return null;
      state.container.innerHTML = `<div class="projectile-empty projectile-error" role="alert"><strong>${ui("Unable to load projectile data", "无法加载投射物数据")}</strong><span>${escapeHtml(error.message || error)}</span><button type="button" data-projectile-retry>${ui("Try again", "重试")}</button></div>`;
      state.container.querySelector("[data-projectile-retry]")?.addEventListener("click", () => {
        if (typeof window.WebUI?.retryView === "function") window.WebUI.retryView("projectiles");
        else load(state.dataPath);
      });
      return null;
    }
  }

  function init(options = {}) {
    const container = asContainer(options.container);
    if (!container) return false;
    destroy();
    state.container = container;
    state.uiLocale = normalizeLocale(options.uiLocale || detectLocale());
    state.language = String(options.language || detectLanguage()).toUpperCase();
    bindLocaleListener();
    bindLanguageListener();
    state.dataPath = options.dataPath || DEFAULT_DATA_PATH;
    state.selectedKey = options.selected || "";
    if (options.payload) {
      state.combatPayload = options.combatPayload || null;
      state.combatIndex = null;
      render(options.payload);
      return true;
    }
    load(state.dataPath);
    return true;
  }

  function destroy() {
    state.loadToken += 1;
    state.abortController?.abort();
    state.abortController = null;
    state.combatLoadToken += 1;
    state.combatAbortController?.abort();
    state.combatAbortController = null;
    clearListeners();
    if (state.container) {
      state.container.classList.remove("projectile-inspector");
      state.container.replaceChildren();
    }
    state.container = null;
    state.payload = null;
    state.combatPayload = null;
    state.combatIndex = null;
    state.combatError = "";
    state.combatAssignments = new Map();
    state.entries = [];
    state.filtered = [];
    state.query = "";
    state.source = "all";
    state.visibleLimit = PAGE_SIZE;
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.projectiles = {
    containerId: DEFAULT_CONTAINER,
    dataPath: DEFAULT_DATA_PATH,
    init,
    load,
    render,
    loadCombat,
    select,
    destroy,
  };
})();
