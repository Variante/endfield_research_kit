(() => {
  "use strict";

  const DEFAULT_CONTAINER_ID = "gameplay-combat-relationships";
  const EDGE_PAGE_SIZE = 120;
  const instances = new Map();
  const pendingLoads = new WeakMap();
  let nextInstanceId = 0;
  let nextLoadToken = 0;
  let localeListenerBound = false;
  const KIND_LABELS = {
    ability_entity: "Authored ability behavior",
    ability_component: "Ability building block",
    target_settings: "Targeting rules",
    selector: "Target selector",
    selector_component: "Selector rule",
    gameplay_effect: "Gameplay effect",
    projectile_effect: "Projectile effect",
    skill_group: "Skill group",
    audio: "Sound reference",
    asset: "Exported asset",
  };
  const RELATION_LABELS = {
    skill_data_references_effect: "Skill points to effect",
    skill_data_references_audio: "Skill points to sound",
    skill_data_references_buff: "Skill points to buff",
    buff_data_references_buff: "Buff points to another buff",
    buff_data_references_effect: "Buff points to effect",
    buff_data_references_audio: "Buff points to sound",
    has_managed_component: "Ability contains building block",
    references_action_skill: "References action skill",
    has_representative_asset: "May be represented by asset",
    starts_with_buff: "Starts with buff",
    identifier_matches_ability_entity: "Matches authored ability behavior",
    has_enemy_ability: "Enemy has ability",
    has_skill_group: "Has skill group",
    effect_name_matches_export_base_asset: "Effect name matches exported asset",
    has_target_settings: "Uses targeting rules",
    has_selector_fields: "Has target selector fields",
    identifier_matches_projectile_effect: "Matches projectile effect",
    uses_target_finder: "Uses target finder",
    uses_target_validator: "Uses target validator",
  };
  const TEXT = {
    en: { title: "Character & Enemy Combat Links", purpose: "Follow the authored pieces connected to a character or enemy: skills, buffs, effects, targeting rules, sounds, and assets.", records: "records", connections: "connections", why: "Why care?", whyBody: "Use this to trace the ingredients behind a skill or enemy behavior, then jump from one connected record to the next.", q1: "What belongs to this fighter?", q1b: "Find the abilities, buffs, and effects referenced by a character or enemy.", q2: "How might it choose a target?", q2b: "Follow a matched ability into its targeting rules and selector fields.", q3: "Which sound or asset goes with it?", q3b: "Trace effect and audio references to likely exported presentation files.", start: "Start here:", startBody: "choose a familiar character or enemy, scan its connections, then click a linked name to follow the chain. Use “Back” to return.", limits: "Limits, evidence strength, and combat terms", actor: "Character or enemy", find: "Find a connection from this selection", placeholder: "Ability, buff, effect, sound, asset…", strength: "Evidence strength", all: "All connections", exported: "Exported links", matched: "Matched links", clear: "Clear filters", heading: "Connections from this selection", technical: "Technical evidence", exportedLink: "Exported link", matchedLink: "Matched link" },
    zh: { title: "角色与敌人战斗联系", purpose: "追踪与角色或敌人相连的配置内容：技能、增益、效果、目标规则、声音和资源。", records: "条记录", connections: "条联系", why: "为什么值得看？", whyBody: "用它追踪技能或敌人行为背后的组成部分，并从一条关联记录继续跳到下一条。", q1: "这个战斗单位有哪些内容？", q1b: "查找角色或敌人引用的能力、增益与效果。", q2: "它可能怎样选择目标？", q2b: "从匹配的能力继续查看目标规则与选择器字段。", q3: "它对应哪些声音或资源？", q3b: "沿特效和声音引用追踪可能对应的导出展示文件。", start: "建议从这里开始：", startBody: "选择熟悉的角色或敌人，浏览它的联系，再点击关联名称继续追踪；使用“返回”回到战斗单位。", limits: "局限、证据强度与战斗术语", actor: "角色或敌人", find: "在当前选择的联系中查找", placeholder: "能力、增益、效果、声音、资源…", strength: "证据强度", all: "全部联系", exported: "导出直链", matched: "匹配联系", clear: "清除筛选", heading: "从当前选择出发的联系", technical: "技术证据", exportedLink: "导出直链", matchedLink: "匹配联系" },
  };
  const KIND_LABELS_ZH = { ability_entity: "能力行为配置", ability_component: "能力组成块", target_settings: "目标规则", selector: "目标选择器", selector_component: "选择器规则", gameplay_effect: "玩法效果", projectile_effect: "投射物效果", skill_group: "技能组", audio: "声音引用", asset: "导出资源", ability: "能力", buff: "增益", character: "角色", enemy: "敌人" };

  function dataPath(language) {
    const code = String(language || "CN").toUpperCase();
    return `data/lang/${encodeURIComponent(code)}/gameplay/combat_relationships.json`;
  }

  async function load(language = "CN", dataUrl = "", signal = null) {
    const url = dataUrl || dataPath(language);
    const response = await fetch(url, { cache: "no-store", signal });
    if (!response.ok) throw new Error(`Combat relationships HTTP ${response.status}: ${url}`);
    const payload = await response.json();
    if (!payload || ![2, 3].includes(payload.schemaVersion) || !Array.isArray(payload.nodes) || !Array.isArray(payload.edges)) {
      throw new Error("Unsupported combat relationship payload");
    }
    return payload;
  }

  function element(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== "") node.textContent = text;
    return node;
  }

  function readable(value) {
    return String(value || "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function normalizeLocale(value) {
    return String(value || "en").toLowerCase().startsWith("zh") ? "zh" : "en";
  }

  function detectLocale() {
    return normalizeLocale(window.WEBUI_UI_LOCALE || document.documentElement.lang || "en");
  }

  function t(key, locale) {
    return (TEXT[locale] || TEXT.en)[key] || TEXT.en[key] || key;
  }

  function kindLabel(value, locale = "en") {
    return (locale === "zh" ? KIND_LABELS_ZH[value] : KIND_LABELS[value]) || readable(value);
  }

  function relationLabel(value, locale = "en") {
    if (locale === "zh") return readable(value).replaceAll(" ", " · ");
    return RELATION_LABELS[value] || readable(value);
  }

  function confidenceLabel(value, locale = "en") {
    return value === "direct" ? t("exportedLink", locale) : value === "inferred" ? t("matchedLink", locale) : readable(value);
  }

  function bindLocaleListener() {
    if (localeListenerBound) return;
    localeListenerBound = true;
    window.addEventListener("webui:ui-locale-changed", (event) => {
      const uiLocale = normalizeLocale(event.detail?.locale || detectLocale());
      for (const [container, state] of instances) {
        if (state.uiLocale === uiLocale) continue;
        render(container, state.payload, {
          ...state.options,
          selectedId: state.selectedId,
          rootId: state.rootId,
          query: state.query,
          confidence: state.confidence,
          visibleLimit: state.visibleLimit,
          uiLocale,
        });
      }
    });
  }

  function stringify(value) {
    try { return JSON.stringify(value, null, 2); }
    catch (_) { return String(value); }
  }

  function resolveContainer(options = {}) {
    if (options.container instanceof Element) return options.container;
    const id = options.containerId || DEFAULT_CONTAINER_ID;
    return document.getElementById(id);
  }

  function renderBadge(text, kind = "") {
    return element("span", `combat-badge${kind ? ` combat-badge-${kind}` : ""}`, text);
  }

  function buildState(container, payload, options) {
    const nodes = new Map(payload.nodes.map((node) => [node.id, node]));
    const outgoing = new Map();
    payload.edges.forEach((edge, index) => {
      if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
      outgoing.get(edge.source).push(index);
    });
    const familiarRoot = (payload.roots || []).find((rootId) => {
      const node = nodes.get(rootId) || {};
      return `${rootId} ${node.key || ""} ${node.label || ""}`.toLowerCase().includes("pelica");
    });
    const initial = options.selectedId && nodes.has(options.selectedId)
      ? options.selectedId
      : familiarRoot || payload.roots[0] || (payload.nodes[0] && payload.nodes[0].id) || "";
    const initialRoot = options.rootId && nodes.has(options.rootId) ? options.rootId : (payload.roots.includes(initial) ? initial : (payload.roots[0] || initial));
    return {
      container,
      payload,
      nodes,
      outgoing,
      selectedId: initial,
      rootId: initialRoot,
      query: options.query || "",
      confidence: options.confidence || "all",
      visibleLimit: options.visibleLimit || EDGE_PAGE_SIZE,
      uiLocale: normalizeLocale(options.uiLocale || detectLocale()),
      options,
      elements: {},
    };
  }

  function edgeIndexesFor(state, nodeId) {
    if (state.payload.rootEdges && Array.isArray(state.payload.rootEdges[nodeId])) {
      return state.payload.rootEdges[nodeId];
    }
    return state.outgoing.get(nodeId) || [];
  }

  function edgeSearchText(edge, state) {
    const source = state.nodes.get(edge.source) || {};
    const target = state.nodes.get(edge.target) || {};
    const evidence = edge.evidence || {};
    return [
      source.label, source.key, source.kind,
      target.label, target.key, target.kind,
      edge.type, edge.confidence,
      evidence.source, evidence.path,
    ].filter(Boolean).join(" ").toLowerCase();
  }

  function renderSummary(state) {
    const host = state.elements.summary;
    host.replaceChildren();
    const node = state.nodes.get(state.selectedId);
    if (!node) return;

    const heading = element("div", "combat-focus-heading");
    heading.append(element("h3", "combat-focus-title", node.label || node.id));
    heading.append(renderBadge(kindLabel(node.kind, state.uiLocale), "kind"));
    host.append(heading);

    const identity = element("div", "combat-focus-id", node.key || node.id);
    host.append(identity);
    if (node.subtitle) host.append(element("div", "combat-focus-subtitle", node.subtitle));
    if (state.selectedId !== state.rootId && state.nodes.has(state.rootId)) {
      const back = element("button", "combat-back", `Back to ${state.nodes.get(state.rootId).label || "selected actor"}`);
      back.type = "button";
      back.addEventListener("click", () => focusNode(state, state.rootId, true));
      host.append(back);
    }

    const facts = [];
    if (node.classification) facts.push(["Classification", node.classification]);
    if (node.semanticStatus) facts.push(["Semantic status", node.semanticStatus]);
    if (node.source) facts.push(["Source", node.source]);
    if (node.path) facts.push(["Path", node.path]);
    if (node.raw) facts.push(["Authored / decoded fields", node.raw]);
    for (const [label, value] of facts) {
      const details = element("details", "combat-fact");
      const summary = element("summary", "", label);
      const pre = element("pre", "combat-raw", stringify(value));
      details.append(summary, pre);
      host.append(details);
    }
  }

  function focusNode(state, nodeId, focusSummary = false) {
    if (!state.nodes.has(nodeId)) return;
    state.selectedId = nodeId;
    state.visibleLimit = EDGE_PAGE_SIZE;
    const isRoot = state.payload.roots.includes(nodeId);
    if (isRoot) {
      state.rootId = nodeId;
      state.elements.rootSelect.value = nodeId;
    }
    renderSummary(state);
    renderEdges(state);
    if (focusSummary) state.elements.summary.focus();
    state.container.dispatchEvent(new CustomEvent("combatrelationshipselect", {
      detail: { id: nodeId, node: state.nodes.get(nodeId) },
    }));
  }

  function nodeButton(state, node, fallbackId) {
    const button = element("button", "combat-node-link", node ? (node.label || node.id) : fallbackId);
    button.type = "button";
    button.title = node ? node.id : fallbackId;
    if (node) button.addEventListener("click", () => focusNode(state, node.id, true));
    else button.disabled = true;
    return button;
  }

  function renderEdgeRow(state, edge) {
    const source = state.nodes.get(edge.source);
    const target = state.nodes.get(edge.target);
    const row = element("article", "combat-edge");
    row.setAttribute("role", "listitem");
    const relation = element("div", "combat-edge-relation");
    relation.append(nodeButton(state, source, edge.source));
    relation.append(element("span", "combat-edge-arrow", "→"));
    relation.append(element("span", "combat-edge-type", relationLabel(edge.type, state.uiLocale)));
    relation.append(element("span", "combat-edge-arrow", "→"));
    relation.append(nodeButton(state, target, edge.target));
    relation.append(renderBadge(confidenceLabel(edge.confidence, state.uiLocale), edge.confidence));
    row.append(relation);

    const evidence = edge.evidence || {};
    if (evidence.source || evidence.path || evidence.raw || edge.note) {
      const details = element("details", "combat-evidence");
      details.append(element("summary", "", t("technical", state.uiLocale)));
      const body = element("div", "combat-evidence-body");
      body.append(element("div", "", `Data relationship: ${edge.type}`));
      if (evidence.source) body.append(element("div", "", `Source: ${evidence.source}`));
      if (evidence.path) body.append(element("div", "", `Field/path: ${evidence.path}`));
      if (edge.note) body.append(element("div", "combat-evidence-note", edge.note));
      if (evidence.raw !== undefined) body.append(element("pre", "combat-raw", stringify(evidence.raw)));
      details.append(body);
      row.append(details);
    }
    return row;
  }

  function renderEdges(state) {
    const host = state.elements.edges;
    const meta = state.elements.edgeMeta;
    host.replaceChildren();
    const tokens = state.query.toLowerCase().split(/\s+/).filter(Boolean);
    let edges = edgeIndexesFor(state, state.selectedId)
      .map((index) => state.payload.edges[index])
      .filter(Boolean);
    if (state.confidence !== "all") {
      edges = edges.filter((edge) => edge.confidence === state.confidence);
    }
    if (tokens.length) {
      edges = edges.filter((edge) => {
        const haystack = edgeSearchText(edge, state);
        return tokens.every((token) => haystack.includes(token));
      });
    }

    const visible = edges.slice(0, state.visibleLimit);
    const directCount = edges.filter((edge) => edge.confidence === "direct").length;
    const inferredCount = edges.length - directCount;
    meta.textContent = `Showing ${visible.length} of ${edges.length} · ${directCount} exported · ${inferredCount} matched`;
    for (const edge of visible) host.append(renderEdgeRow(state, edge));
    if (!visible.length) host.append(element("div", "combat-empty", "No relationships match these filters."));

    state.elements.more.hidden = visible.length >= edges.length;
    state.elements.more.textContent = `Show next ${Math.min(EDGE_PAGE_SIZE, edges.length - visible.length)} (${visible.length} of ${edges.length})`;
    state.elements.clear.hidden = !state.query && state.confidence === "all";
  }

  function render(container, payload, options = {}) {
    if (!(container instanceof Element)) throw new Error("Combat explorer container is required");
    const state = buildState(container, payload, options);
    bindLocaleListener();
    const edgeResultsId = `combat-edge-results-${++nextInstanceId}`;
    container.replaceChildren();
    container.classList.add("combat-explorer");

    const header = element("header", "combat-header");
    const titleBlock = element("div", "combat-title-block");
    titleBlock.append(element("h2", "combat-title", options.title || t("title", state.uiLocale)));
    titleBlock.append(element("p", "combat-disclaimer", t("purpose", state.uiLocale)));
    header.append(titleBlock);
    const counts = payload.counts || {};
    header.append(renderBadge(`${counts.nodes || 0} ${t("records", state.uiLocale)} · ${counts.edges || 0} ${t("connections", state.uiLocale)}`, "count"));
    container.append(header);

    const confidenceCounts = counts.confidence || {};
    const intro = element("section", "combat-intro");
    intro.setAttribute("aria-labelledby", "combat-why-title");
    const lead = element("div", "combat-intro-lead");
    const why = element("strong", "", t("why", state.uiLocale));
    why.id = "combat-why-title";
    lead.append(why, element("span", "", t("whyBody", state.uiLocale)));
    const questions = element("div", "combat-question-grid");
    questions.setAttribute("aria-label", "Example questions this page can answer");
    [
      [t("q1", state.uiLocale), t("q1b", state.uiLocale)],
      [t("q2", state.uiLocale), t("q2b", state.uiLocale)],
      [t("q3", state.uiLocale), t("q3b", state.uiLocale)],
    ].forEach(([title, copy]) => {
      const card = element("article", "");
      card.append(element("strong", "", title), element("span", "", copy));
      questions.append(card);
    });
    const first = element("p", "combat-first-step");
    first.append(element("strong", "", `${t("start", state.uiLocale)} `), element("span", "", t("startBody", state.uiLocale)));
    intro.append(lead, questions, first);
    container.append(intro);

    const scope = element("details", "combat-scope");
    scope.append(element("summary", "", t("limits", state.uiLocale)));
    const scopeBody = element("div", "combat-scope-body");
    scopeBody.append(
      element("p", "", state.uiLocale === "zh" ? "这些是配置引用，不是重建后的运行时战斗公式。" : (payload.scope?.note || "These are authored references, not a reconstructed runtime combat formula.")),
      element("p", "", state.uiLocale === "zh" ? `导出直链（${confidenceCounts.direct || 0}）来自明确字段或精确解码引用；匹配联系（${confidenceCounts.inferred || 0}）来自标识符或关系图匹配，仍需确认。` : `Exported link (${confidenceCounts.direct || 0}): an explicit field or exact decoded reference. Matched link (${confidenceCounts.inferred || 0}): an identifier or graph match that still needs confirmation.`),
      element("p", "", state.uiLocale === "zh" ? "能力行为配置（AbilityEntity）是能力使用的解码配置对象；目标规则描述配置限制，但不会模拟实战中最终选中谁。" : "An authored ability behavior (AbilityEntity) is a decoded configuration object used by an ability. Targeting rules describe configured selection constraints; they do not simulate who will be chosen during play."),
      element("p", "", state.uiLocale === "zh" ? "本页无法证明伤害公式、执行顺序、时序或最终运行时目标判断。" : "This page cannot prove damage formulas, execution order, timing, or final runtime target evaluation."),
    );
    scope.append(scopeBody);
    container.append(scope);

    if (payload.graph && payload.graph.degradedMode) {
      const reason = payload.graph.stale
        ? `Source graph is stale (${payload.graph.staleReason || "rebuild required"}).`
        : "Source graph unavailable.";
      container.append(element("div", "combat-warning", `${reason} Showing authored Gameplay plus available exact AnimeStudio AbilityEntity and reachable TargetSettings evidence only.`));
    }

    const toolbar = element("div", "combat-toolbar");
    const rootLabel = element("label", "combat-control");
    rootLabel.append(element("span", "", t("actor", state.uiLocale)));
    const rootSelect = element("select", "combat-root-select");
    for (const rootId of payload.roots || []) {
      const node = state.nodes.get(rootId);
      const option = element("option", "", node ? `${node.label} · ${node.key || node.id}` : rootId);
      option.value = rootId;
      rootSelect.append(option);
    }
    rootSelect.value = state.selectedId;
    rootSelect.addEventListener("change", () => focusNode(state, rootSelect.value));
    rootLabel.append(rootSelect);
    toolbar.append(rootLabel);

    const searchLabel = element("label", "combat-control combat-control-search");
    searchLabel.append(element("span", "", t("find", state.uiLocale)));
    const search = element("input", "combat-search");
    search.type = "search";
    search.placeholder = t("placeholder", state.uiLocale);
    search.value = state.query;
    search.autocomplete = "off";
    search.setAttribute("aria-controls", edgeResultsId);
    search.addEventListener("input", () => {
      state.query = search.value.trim();
      state.visibleLimit = EDGE_PAGE_SIZE;
      renderEdges(state);
    });
    searchLabel.append(search);
    toolbar.append(searchLabel);

    const confidenceLabel = element("label", "combat-control");
    confidenceLabel.append(element("span", "", t("strength", state.uiLocale)));
    const confidence = element("select", "combat-confidence");
    for (const [value, label] of [["all", t("all", state.uiLocale)], ["direct", t("exported", state.uiLocale)], ["inferred", t("matched", state.uiLocale)]]) {
      const option = element("option", "", label);
      option.value = value;
      confidence.append(option);
    }
    confidence.value = state.confidence;
    confidence.addEventListener("change", () => {
      state.confidence = confidence.value;
      state.visibleLimit = EDGE_PAGE_SIZE;
      renderEdges(state);
    });
    confidenceLabel.append(confidence);
    toolbar.append(confidenceLabel);
    const clear = element("button", "combat-clear", t("clear", state.uiLocale));
    clear.type = "button";
    clear.hidden = true;
    clear.addEventListener("click", () => {
      state.query = "";
      state.confidence = "all";
      state.visibleLimit = EDGE_PAGE_SIZE;
      search.value = "";
      confidence.value = "all";
      renderEdges(state);
      search.focus();
    });
    toolbar.append(clear);
    container.append(toolbar);

    const layout = element("div", "combat-layout");
    const summary = element("aside", "combat-summary");
    summary.tabIndex = -1;
    summary.setAttribute("aria-label", "Selected combat node");
    const relationshipPanel = element("section", "combat-relationships");
    const relationshipHeader = element("div", "combat-relationships-header");
    relationshipHeader.append(element("h3", "", t("heading", state.uiLocale)));
    const edgeMeta = element("span", "combat-edge-meta");
    edgeMeta.setAttribute("role", "status");
    relationshipHeader.append(edgeMeta);
    const edges = element("div", "combat-edge-list");
    edges.id = edgeResultsId;
    edges.setAttribute("role", "list");
    edges.setAttribute("aria-label", "Filtered combat relationships");
    const more = element("button", "combat-show-more", "Show more relationships");
    more.type = "button";
    more.addEventListener("click", () => {
      state.visibleLimit += EDGE_PAGE_SIZE;
      renderEdges(state);
    });
    relationshipPanel.append(relationshipHeader, edges, more);
    layout.append(summary, relationshipPanel);
    container.append(layout);

    state.elements = { rootSelect, search, confidence, clear, summary, edgeMeta, edges, more };
    renderSummary(state);
    renderEdges(state);
    instances.set(container, state);
    return state;
  }

  async function init(options = {}) {
    const container = resolveContainer(options);
    if (!container) throw new Error(`Combat explorer container #${options.containerId || DEFAULT_CONTAINER_ID} not found`);
    const previous = pendingLoads.get(container);
    if (previous) previous.controller.abort();
    const controller = new AbortController();
    const token = ++nextLoadToken;
    const uiLocale = normalizeLocale(options.uiLocale || detectLocale());
    pendingLoads.set(container, { controller, token });
    const loading = element("div", "combat-loading", uiLocale === "zh" ? "正在加载战斗联系…" : "Loading combat relationships…");
    loading.setAttribute("role", "status");
    container.replaceChildren(loading);
    try {
      const payload = options.payload || await load(options.language || "CN", options.dataUrl || "", controller.signal);
      if (pendingLoads.get(container)?.token !== token) return null;
      return render(container, payload, options);
    } catch (error) {
      if (error?.name === "AbortError" || pendingLoads.get(container)?.token !== token) return null;
      const failure = element("div", "combat-error");
      failure.setAttribute("role", "alert");
      failure.append(element("strong", "", uiLocale === "zh" ? "无法加载战斗联系" : "Unable to load combat relationships"));
      failure.append(element("span", "", String(error.message || error)));
      const retry = element("button", "combat-retry", uiLocale === "zh" ? "重试" : "Try again");
      retry.type = "button";
      retry.addEventListener("click", () => {
        if (typeof window.WebUI?.retryView === "function") window.WebUI.retryView("combat", options.language || "CN");
        else void init(options).catch(() => {});
      });
      failure.append(retry);
      container.replaceChildren(failure);
      throw error;
    } finally {
      if (pendingLoads.get(container)?.token === token) pendingLoads.delete(container);
    }
  }

  function select(id, container = null) {
    const target = container || document.getElementById(DEFAULT_CONTAINER_ID);
    const state = target && instances.get(target);
    if (!state) return false;
    focusNode(state, id);
    return state.selectedId === id;
  }

  window.WebUICombat = Object.freeze({
    DEFAULT_CONTAINER_ID,
    dataPath,
    init,
    load,
    render,
    select,
  });
})();
