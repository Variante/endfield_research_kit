// Read-only authored action navigation. No runtime order, damage or audio inference.
(() => {
  const W = window.WebUI;
  const esc = W.escapeHtml;
  const BASE = "data/gameplay/skill_refs/";
  const SCHEMA = "endfield.webui.skill-references.v1";
  const state = { index: null, entry: "", ids: new Set(), names: new Map(), query: "", scope: "entry", selected: "", record: null, node: 0, page: 0, trail: [], target: "", error: "", pending: false };
  const cache = new Map();
  let indexPromise = null;
  let host = null;
  let facets = null;
  let serial = 0;
  const tr = (en, cn) => String(window.WEBUI_UI_LOCALE || "zh").toLowerCase().startsWith("zh") ? cn : en;
  const kindLabel = (kind) => ({ skill: tr("Skills", "技能"), buff: "Buff", projectile: tr("Projectiles", "投射物") }[kind] || kind);
  const shortType = (type) => String(type || "").replace(/^Beyond\.Gameplay\.Core\./, "").replace(/\+Data$/, "");
  // Labels describe the named stored action only, not whether it executes.
  const actionNames = {
    PlayAnimationAction: ["Play animation", "播放动画"],
    EffectAction: ["Visual effect", "视觉特效"],
    LaunchProjectile: ["Launch projectile", "发射投射物"],
    PlaySoundAction: ["Sound cue", "音效触发"],
    VoiceTriggerAction: ["Voice cue", "语音触发"],
    CharWeaponVisibleAction: ["Weapon visibility", "武器显隐"],
    SelfRotateAction: ["Rotate", "转向"],
    MoveToAction: ["Move", "移动"],
    SnapToTargetWithRangeAction: ["Approach target", "接近目标"],
    SetSuperArmorAction: ["Super armor setting", "霸体设置"],
    AllowNextSkillAction: ["Next-skill allowance", "后续技能许可"],
    ComboCacheAction: ["Combo input buffer", "连招输入缓存"],
    "Conditions.CheckEntityNum": ["Entity-count condition", "实体数量条件"],
  };
  const actionLabel = (type) => {
    const name = actionNames[shortType(type).split("+")[0]];
    return name ? tr(...name) : shortType(type);
  };
  const skillLabel = (id) => state.names.get(id) || id;
  const scalar = (value) => value == null ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value);
  const dataLink = (options, label) => `<a href="${esc(W.dataPageUrl(options))}">${esc(label)}</a>`;

  async function fetchDoc(path) {
    const response = await fetch(BASE + path, { cache: "no-store" });
    if (!response.ok) throw new Error(`${response.status}: ${path}`);
    const value = await response.json();
    if (value.schema !== SCHEMA) throw new Error(tr("Unsupported skill reference publication", "技能引用数据版本不兼容"));
    return value;
  }

  function loadIndex() {
    indexPromise ||= fetchDoc("index.json").catch((error) => { indexPromise = null; throw error; });
    return indexPromise;
  }

  async function loadRecord(descriptor) {
    if (!cache.has(descriptor.path)) cache.set(descriptor.path, fetchDoc(descriptor.path).catch((error) => { cache.delete(descriptor.path); throw error; }));
    const row = await cache.get(descriptor.path);
    if (row.recordId !== descriptor.recordId || row.id !== descriptor.id || !Array.isArray(row.nodes)) throw new Error(tr("Skill shard/catalog mismatch", "技能分片与目录不一致"));
    return row;
  }

  async function loadRecords(ids) {
    const index = await loadIndex();
    if (index.status !== "current") throw new Error(tr("Skill action data is not current", "技能动作数据尚未通过当前来源校验"));
    const wanted = new Set(ids);
    const records = new Map();
    const rows = index.records.filter((row) => wanted.has(row.id) && index.records.filter((other) => other.id === row.id).length === 1);
    // Bound parallel requests; the navigator shares the same validated cache.
    for (let offset = 0; offset < rows.length; offset += 6) {
      const batch = await Promise.allSettled(rows.slice(offset, offset + 6).map(loadRecord));
      for (const result of batch) if (result.status === "fulfilled") records.set(result.value.id, result.value);
    }
    return records;
  }

  function markup() {
    const title = tr("Skill actions & references", "技能动作与引用");
    return `<details class="gameplay-disclosure gp-skill-refs" id="gameplay-section-references" data-gameplay-section="${esc(title)}" tabindex="-1"><summary><span>${esc(title)}</span><small>${esc(tr("Explore action structure, linked effects and source fields", "查看动作结构、关联效果与原始字段"))}</small></summary><div class="gp-skill-refs-content">${esc(tr("Loading…", "加载中…"))}</div></details>`;
  }

  function entryIds(entry) {
    const ids = new Set();
    for (const group of entry.skillGroups || []) {
      for (const id of group.actionSkillIds || []) if (id) ids.add(id);
      for (const skill of group.skills || []) if (skill.id) ids.add(skill.id);
    }
    for (const skill of entry.skills || []) if (skill.id) ids.add(skill.id);
    return ids;
  }

  function fieldList(fields) {
    return `<dl class="gp-ref-fields">${Object.entries(fields || {}).map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(scalar(value))}</dd>`).join("")}</dl>`;
  }

  function referenceHtml(ref) {
    let target = `<code>${esc(ref.target)}</code>`;
    let status = tr("Target not published", "目标尚未发布");
    if (ref.resolution === "ambiguous") status = tr("Ambiguous target", "目标不唯一");
    if (ref.resolution === "exact_id") {
      status = tr("Exact stored ID", "精确配置 ID");
      target = `<button type="button" data-ref-${ref.kind}="${esc(ref.target)}">${esc(ref.target)}</button>`;
    } else if (ref.resolution === "source_only") {
      status = tr("Source exists; Buff interior unresolved", "源文件存在；Buff 内部逻辑未定");
      const relative = String(ref.sourcePath || "").replace(/^game\/Json\//, "");
      target = dataLink({ store: "loose", group: "Json", name: relative }, ref.target);
    }
    return `<li><span class="gp-ref-kind">${esc(kindLabel(ref.kind))}</span> ${target}<small>${esc(ref.field)} · ${esc(status)}</small></li>`;
  }

  function projectileHtml() {
    if (!state.target) return "";
    const targets = state.index?.projectiles?.[state.target] || [];
    if (targets.length !== 1) return "";
    const target = targets[0];
    const skillIds = Object.values(target.skills || {}).flatMap((value) => typeof value === "string" ? [value] : Array.isArray(value) ? value.filter((v) => typeof v === "string") : []).filter(Boolean);
    const links = [...new Set(skillIds)].map((id) => {
      const found = state.index.records.filter((row) => row.id === id);
      return found.length === 1 ? `<button type="button" data-ref-skill="${esc(id)}">${esc(id)}</button>` : `<code>${esc(id)}</code>`;
    }).join(" ");
    return `<div class="gp-ref-target"><h4>${esc(target.id)}</h4><p>${dataLink(target.source, tr("Projectile source", "投射物源记录"))} · ${esc(tr("Stored projectile definition", "投射物配置定义"))}</p>${links ? `<div class="gp-ref-target-skills">${links}</div>` : ""}<h5>${esc(tr("Lifetime fields", "寿命字段"))}</h5>${fieldList(target.lifetime)}<h5>${esc(tr("Collision fields", "碰撞字段"))}</h5>${fieldList(target.collision)}</div>`;
  }

  function recordHtml() {
    if (state.pending) return `<p>${esc(tr("Loading skill…", "正在加载技能…"))}</p>`;
    const row = state.record;
    if (!row) return `<p>${esc(tr("Choose a skill to inspect its stored actions and references.", "选择技能以查看配置的动作与引用。"))}</p>`;
    const nodes = row.nodes || [];
    const node = nodes[state.node];
    const start = Math.floor(state.node / 40) * 40;
    const pages = Math.ceil(nodes.length / 40);
    const lines = nodes.slice(start, start + 40).map((item, offset) => `<tr class="${start + offset === state.node ? "is-selected" : ""}"><td><button type="button" data-ref-node="${start + offset}" title="${esc(shortType(item.type))}">${esc(actionLabel(item.type))}</button>${item.parent ? `<small>${esc(tr("Nested", "嵌套"))}</small>` : ""}</td><td>${item.window ? `${esc(item.window.startFrame)}–${esc(item.window.endFrame)}` : "—"}</td><td>${item.references.length}</td></tr>`).join("");
    const refs = node?.references || [];
    const incoming = [...new Set((row.incoming || []).map((item) => item.id))];
    return `<header class="gp-ref-record-head"><strong>${esc(skillLabel(row.id))}</strong>${skillLabel(row.id) !== row.id ? `<code>${esc(row.id)}</code>` : ""}${dataLink({ store: "decoded", group: "skill-data", name: row.recordId }, tr("SkillData source", "SkillData 源记录"))}<span>${row.actionCount} ${esc(tr("actions", "动作"))} · ${row.references.length} ${esc(tr("references", "引用"))}</span></header>
      <p class="gp-ref-note">${esc(tr("Frames are stored intervals. Nested rows retain their source path; list order is not runtime order.", "帧数为配置区间。嵌套记录保留源路径；列表顺序不代表运行顺序。"))}</p>
      ${nodes.length ? `<div class="gp-ref-table"><table><thead><tr><th>${esc(tr("Action / reference context", "动作 / 引用上下文"))}</th><th>${esc(tr("Frames", "帧"))}</th><th>${esc(tr("Refs", "引用"))}</th></tr></thead><tbody>${lines}</tbody></table></div>${pages > 1 ? `<div class="gp-ref-pager"><button type="button" data-ref-node-page="${Math.max(0, start - 40)}"${start === 0 ? " disabled" : ""}>‹</button><span>${Math.floor(start / 40) + 1} / ${pages}</span><button type="button" data-ref-node-page="${start + 40}"${start + 40 >= nodes.length ? " disabled" : ""}>›</button></div>` : ""}` : `<p>${esc(tr("No named action rows in this record.", "此记录没有具名动作。"))}</p>`}
      ${node ? `<div class="gp-ref-node"><h4>${esc(shortType(node.type))}</h4><p class="gp-ref-path">${esc(node.path)}</p>${node.window ? `<p>${esc(tr("Stored frame window", "配置帧区间"))}: ${esc(node.window.startFrame)}–${esc(node.window.endFrame)}</p>` : ""}${refs.length ? `<ul class="gp-ref-links">${refs.map(referenceHtml).join("")}</ul>` : `<p class="gp-ref-note">${esc(tr("No recognized static target IDs on this action.", "此动作未识别到静态目标 ID。"))}</p>`}${fieldList(node.parameters)}</div>` : ""}
      ${projectileHtml()}
      ${incoming.length ? `<div class="gp-ref-incoming"><h4>${esc(tr("Referenced by skills", "被下列技能引用"))}</h4>${incoming.map((id) => `<button type="button" data-ref-skill="${esc(id)}">${esc(id)}</button>`).join(" ")}</div>` : ""}`;
  }

  function renderResults() {
    if (!host?.isConnected) return;
    const rows = (state.index?.records || []).filter((row) => state.scope === "all" || state.ids.has(row.id));
    const tokens = W.parseQuery(state.query);
    facets?.render(rows);
    const filtered = (facets ? facets.filter(rows) : rows).filter((row) => !state.query.trim() || W.queryMatches([skillLabel(row.id), row.id, ...(row.targets || [])].join(" ").toLowerCase(), tokens));
    const lastPage = Math.max(0, Math.ceil(filtered.length / 30) - 1);
    state.page = Math.min(state.page, lastPage);
    const list = host.querySelector(".gp-ref-list");
    list.innerHTML = filtered.slice(state.page * 30, state.page * 30 + 30).map((row) => `<button type="button" data-ref-record="${esc(row.recordId)}" class="${row.recordId === state.selected ? "is-selected" : ""}"><strong>${esc(skillLabel(row.id))}</strong>${skillLabel(row.id) !== row.id ? `<small><code>${esc(row.id)}</code></small>` : ""}<small>${row.actions} ${esc(tr("actions", "动作"))} · ${row.references} ${esc(tr("references", "引用"))}</small></button>`).join("") || `<p>${esc(tr("No matching published skills. Use All skills to browse the full catalog.", "没有匹配的技能记录。可选择全部技能浏览完整目录。"))}</p>`;
    host.querySelector(".gp-ref-list-pager").innerHTML = `<button type="button" data-ref-page="${state.page - 1}"${state.page === 0 ? " disabled" : ""}>‹</button><span>${filtered.length} · ${state.page + 1} / ${lastPage + 1}</span><button type="button" data-ref-page="${state.page + 1}"${state.page >= lastPage ? " disabled" : ""}>›</button>`;
    host.querySelector(".gp-ref-detail").innerHTML = state.error ? `<p class="gp-ref-diagnostic">${esc(state.error)}</p>` : recordHtml();
    const back = host.querySelector("[data-ref-back]");
    back.disabled = !state.trail.length;
  }

  async function select(recordId, remember = true) {
    const descriptor = state.index?.records.find((row) => row.recordId === recordId);
    if (!descriptor) return;
    if (remember && state.selected && state.selected !== recordId) state.trail.push(state.selected);
    state.selected = recordId;
    state.node = 0;
    state.target = "";
    state.error = "";
    state.pending = true;
    const token = ++serial;
    renderResults();
    try {
      const row = await loadRecord(descriptor);
      if (token !== serial) return;
      state.record = row;
    } catch (error) {
      if (token !== serial) return;
      state.record = null;
      state.error = String(error.message || error);
    } finally {
      if (token === serial) { state.pending = false; renderResults(); }
    }
  }

  function render() {
    if (!host?.isConnected) return;
    const previous = facets?.snapshot();
    const diagnostics = (state.index?.sources || []).filter((row) => row.status !== "current").map((row) => `${row.datasetId}: ${row.diagnostic || row.status}`);
    if (state.index?.rejected?.length) diagnostics.push(`${state.index.rejected.length} ${tr("records lack complete projection proof", "记录缺少完整投影依据")}`);
    host.innerHTML = `<p class="gp-ref-note">${esc(tr("Explore authored actions, static Buff/projectile/skill IDs and stored frame windows. These records do not establish execution or final damage.", "查看配置动作、静态 Buff / 投射物 / 技能 ID 与帧区间。这些记录不能证明实际执行或最终伤害。"))}</p>${diagnostics.map((text) => `<p class="gp-ref-diagnostic">${esc(text)}</p>`).join("")}
      <div class="gp-ref-controls"><label>${esc(tr("Scope", "范围"))}<select data-ref-scope><option value="entry"${state.scope === "entry" ? " selected" : ""}>${esc(tr("This entry’s skills", "当前条目的技能"))}</option><option value="all"${state.scope === "all" ? " selected" : ""}>${esc(tr("All skills", "全部技能"))}</option></select></label><input type="search" data-ref-search value="${esc(state.query)}" placeholder="${esc(tr("Search skill or target ID…", "搜索技能或目标 ID…"))}" aria-label="${esc(tr("Search skill references", "搜索技能引用"))}"><button type="button" data-ref-back>${esc(tr("Back", "返回"))}</button><button type="button" data-ref-reset>${esc(tr("Reset", "重置"))}</button></div><div class="gp-ref-facets"></div>
      <div class="gp-ref-layout"><div><div class="gp-ref-list"></div><div class="gp-ref-list-pager gp-ref-pager"></div></div><div class="gp-ref-detail"></div></div>`;
    facets = W.facets.create({ countMode: "total", groups: [{ id: "kinds", container: host.querySelector(".gp-ref-facets"), values: (row) => row.kinds, label: kindLabel }], onChange: () => { state.page = 0; renderResults(); } });
    if (previous) facets.restore(previous, { silent: true });
    host.querySelector("[data-ref-search]").addEventListener("input", (event) => { state.query = event.target.value; state.page = 0; renderResults(); });
    host.querySelector("[data-ref-scope]").addEventListener("change", (event) => { state.scope = event.target.value; state.page = 0; renderResults(); });
    host.onclick = (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      if (button.hasAttribute("data-ref-record")) void select(button.dataset.refRecord);
      if (button.hasAttribute("data-ref-skill")) {
        const rows = state.index.records.filter((row) => row.id === button.dataset.refSkill);
        if (rows.length === 1) void select(rows[0].recordId);
      }
      if (button.hasAttribute("data-ref-projectile")) { state.target = button.dataset.refProjectile; renderResults(); host.querySelector(".gp-ref-target")?.scrollIntoView({ block: "nearest" }); }
      if (button.hasAttribute("data-ref-node") || button.hasAttribute("data-ref-node-page")) { state.node = Number(button.dataset.refNode ?? button.dataset.refNodePage); state.target = ""; renderResults(); }
      if (button.hasAttribute("data-ref-page")) { state.page = Number(button.dataset.refPage); renderResults(); }
      if (button.hasAttribute("data-ref-back")) { const id = state.trail.pop(); if (id) void select(id, false); }
      if (button.hasAttribute("data-ref-reset")) { state.query = ""; state.scope = "entry"; state.page = 0; state.trail = []; facets.reset({ silent: true }); render(); }
    };
    renderResults();
  }

  async function mount(root, entry) {
    const next = root.querySelector(".gp-skill-refs-content");
    if (!next) return;
    host = next;
    const entryKey = `${entry.kind}:${entry.id}`;
    if (state.entry !== entryKey) {
      serial += 1;
      Object.assign(state, { entry: entryKey, ids: entryIds(entry), selected: "", record: null, node: 0, page: 0, trail: [], target: "", error: "", pending: false });
    }
    state.names = new Map();
    for (const group of entry.skillGroups || []) {
      for (const id of [...(group.actionSkillIds || []), ...(group.skills || []).map((skill) => skill.id)]) {
        if (id && group.name) state.names.set(id, group.name);
      }
    }
    try {
      state.index ||= await loadIndex();
      if (host !== next || !next.isConnected) return;
      render();
      if (!state.selected) {
        const first = state.index.records.find((row) => state.ids.has(row.id));
        if (first) await select(first.recordId, false);
      }
    } catch (error) {
      if (host === next) next.innerHTML = `<p class="gp-ref-diagnostic">${esc(tr("Skill reference publication unavailable", "技能引用数据尚不可用"))}: ${esc(error.message || error)}</p>`;
    }
  }

  W.gameplaySkillRefs = { markup, mount, loadRecords };
})();
