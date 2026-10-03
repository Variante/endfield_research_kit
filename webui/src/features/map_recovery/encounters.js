// Map-owned compact views of the last validated Data publication.
(() => {
  const W = window.WebUI;
  const esc = W.escapeHtml;
  const BASE = "data/map_recovery/encounters/";
  const SCHEMA = "endfield.webui.map-encounters.v1";
  const state = { index: null, rows: [], unplaced: null, levelIds: new Set(), query: "", scope: "map", selected: "", page: 0, open: false, error: "" };
  const cache = new Map();
  let host = null;
  let locate = null;
  let facets = null;
  let loadSerial = 0;
  const zh = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").toLowerCase().startsWith("zh");
  const tr = (en, cn) => zh() ? cn : en;
  const kindLabel = (kind) => ({ spawner: tr("Spawner waves", "刷怪波次"), group: tr("Enemy groups", "敌人编组"), patrol: tr("Patrol routes", "巡逻路线"), npc: tr("Atmospheric NPCs", "氛围 NPC"), "scene-state": tr("Scene conditions", "场景条件") }[kind] || kind);
  const placementLabel = (value) => ({ placed: tr("Authored position", "配置坐标"), level: tr("Level-wide configuration", "关卡级配置"), unplaced: tr("No published map anchor", "尚无地图定位") }[value] || value);
  const title = () => tr("Encounters & scene conditions", "遭遇与场景条件");
  const text = (value) => value == null ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value);
  const formatPosition = (p) => p ? [p.x, p.y, p.z].map((n) => Number(n).toFixed(2)).join(", ") : "—";

  async function fetchDocument(path) {
    const response = await fetch(BASE + path, { cache: "no-store" });
    if (!response.ok) throw new Error(`${response.status}: ${path}`);
    const payload = await response.json();
    if (payload.schema !== SCHEMA) throw new Error(tr("Unsupported encounter publication", "遭遇数据版本不兼容"));
    return payload;
  }

  async function fetchLevel(row) {
    if (!cache.has(row.path)) {
      const pending = fetchDocument(row.path).catch((error) => { cache.delete(row.path); throw error; });
      cache.set(row.path, pending);
    }
    const payload = await cache.get(row.path);
    if (payload.levelId !== row.levelId || !Array.isArray(payload.rows) || payload.rows.length !== row.count) {
      throw new Error(tr("Encounter shard does not match its catalog", "遭遇分片与目录不一致"));
    }
    return payload.rows;
  }

  async function load(levelIds) {
    const request = ++loadSerial;
    const requestedLevels = new Set(levelIds);
    state.levelIds = requestedLevels;
    state.rows = [];
    state.selected = "";
    state.page = 0;
    state.error = "";
    try {
      const index = state.index || await fetchDocument("index.json");
      if (request !== loadSerial) return false;
      state.index = index;
      const descriptors = index.levels.filter((row) => requestedLevels.has(row.levelId));
      const rows = (await Promise.all(descriptors.map(fetchLevel))).flat();
      if (request !== loadSerial) return false;
      state.rows = rows;
      if (state.scope === "unplaced") await loadUnplaced();
    } catch (error) {
      if (request !== loadSerial) return false;
      state.error = String(error.message || error);
    }
    return request === loadSerial;
  }

  async function loadUnplaced() {
    if (state.unplaced) return;
    const descriptor = state.index?.levels.find((row) => row.levelId === "unplaced");
    state.unplaced = descriptor ? await fetchLevel(descriptor) : [];
  }

  function markup() {
    const count = state.rows.length;
    return `<details class="mr-encounters"${state.open ? " open" : ""}><summary>${esc(title())} <b>${count.toLocaleString()}</b></summary><div class="mr-encounters-content"></div></details>`;
  }

  function sourceHtml(row) {
    return `<div class="mr-encounter-sources">${(row.sources || []).map((source) => {
      const href = W.dataPageUrl({ store: "decoded", group: source.datasetId, name: source.recordId });
      return `<a href="${esc(href)}" title="${esc(source.path || source.recordId)}">${esc(source.datasetId)} · ${esc(source.status)}</a>`;
    }).join("")}</div>`;
  }

  function table(headers, rows) {
    if (!rows.length) return `<p class="mr-note">${esc(tr("No stored rows.", "没有配置记录。"))}</p>`;
    return `<div class="mr-encounter-table"><table><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((cells) => `<tr>${cells.map((cell) => `<td>${esc(text(cell))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }

  function fieldList(fields) {
    return `<dl class="mr-fields mr-encounter-fields">${Object.entries(fields || {}).map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(text(value))}</dd>`).join("")}</dl>`;
  }

  function storedDetails(label, fields) {
    return `<details><summary>${esc(label)}</summary>${fieldList(fields)}</details>`;
  }

  function spawnerHtml(row) {
    const enemies = row.enemyLibrary || [];
    const enemyKeys = new Map();
    for (const enemy of enemies) {
      const key = String(enemy.key);
      enemyKeys.set(key, [...(enemyKeys.get(key) || []), enemy]);
    }
    const routeIds = new Map();
    for (const route of row.routes || []) {
      const key = String(route.routeId);
      routeIds.set(key, [...(routeIds.get(key) || []), route]);
    }
    const library = table([tr("Library key", "库键"), tr("Enemy", "敌人"), tr("Level", "等级"), tr("Buffs", "增益")],
      enemies.map((e) => [e.key, e.enemyId, e.enemyLevel, (e.bornBuffList || []).map((b) => b.buffId).join(", ")]));
    const waves = (row.waves || []).map((wave) => {
      const groups = (wave.groupMap || []).map((group) => {
        const actions = (group.actionMap || []).map((action) => {
          const matches = enemyKeys.get(String(action.libraryKey)) || [];
          const enemy = matches.length === 1 ? matches[0].enemyId : action.libraryKey;
          const route = action.routeId == null ? "" : `${action.routeId} (${(routeIds.get(String(action.routeId)) || []).length === 1 ? tr("exact route id", "精确路线 ID") : tr("unresolved", "未解析")})`;
          return [action.actionId ?? action.mapKey, String(action.concreteType || "").replace(/^SpawnerActions\./, ""), action.timestamp, enemy, action.spawnCount, action.spawnInterval, route];
        });
        return `<details open><summary>${esc(tr("Group", "组"))} ${esc(group.groupKey || group.groupId || group.mapKey)} · ${esc(tr("stored time", "配置时间"))} ${esc(text(group.timestamp))}</summary>${table(["ID", tr("Action", "动作"), tr("Time", "时间"), tr("Enemy / key", "敌人 / 键"), tr("Count", "数量"), tr("Interval", "间隔"), tr("Route", "路线")], actions)}${storedDetails(tr("Stored group and action fields", "组与动作配置字段"), group)}</details>`;
      }).join("");
      return `<details class="mr-encounter-wave"><summary>${esc(tr("Wave", "波次"))} ${esc(wave.waveKey || wave.waveId || wave.mapKey)} · ${esc(tr("stored time", "配置时间"))} ${esc(text(wave.timestamp))} · ${esc(tr("repeatable", "可重复"))}: ${esc(text(wave.repeatable))}</summary>${groups}${storedDetails(tr("Stored wave fields", "波次配置字段"), Object.fromEntries(Object.entries(wave).filter(([key]) => key !== "groupMap")))}</details>`;
    }).join("");
    return `${fieldList(row.host)}<p class="mr-note">${esc(tr("Wave, group and action times are independent stored fields. They are not a simulated spawn schedule.", "波次、组和动作时间是各自的配置字段，并非模拟刷怪时间表。"))}</p><h4>${esc(tr("Enemy library", "敌人库"))} (${enemies.length})</h4>${library}<h4>${esc(tr("Waves", "波次"))} (${(row.waves || []).length})</h4>${waves || `<p class="mr-note">${esc(tr("No decoded waves.", "尚无已解码波次。"))}</p>`}${(row.routes || []).map((route) => storedDetails(`${tr("Route", "路线")} ${route.routeId}`, route.patrolData || route)).join("")}${storedDetails(tr("Spawner settings", "生成器配置"), row.settings || {})}`;
  }

  function conditionTree(value) {
    if (value == null || typeof value !== "object") return `<code>${esc(text(value))}</code>`;
    if (Array.isArray(value)) return `<ol>${value.map((v) => `<li>${conditionTree(v)}</li>`).join("")}</ol>`;
    const type = value.$type ? `<b>${esc(String(value.$type).split(",")[0])}</b>` : "";
    return `${type}<dl class="mr-fields mr-encounter-fields">${Object.entries(value).filter(([key]) => key !== "$type").map(([key, val]) => `<dt>${esc(key)}</dt><dd>${conditionTree(val)}</dd>`).join("")}</dl>`;
  }

  function detailsHtml(row) {
    const canLocate = row.placement === "placed" && state.levelIds.has(row.levelId);
    const content = row.kind === "spawner" ? spawnerHtml(row)
      : row.kind === "group" ? `${fieldList(row.fields)}${table([tr("Member pointer", "成员指针"), tr("Leader", "队长"), tr("Position X, Y, Z", "坐标 X, Y, Z"), tr("Join", "关联")], (row.members || []).map((m) => [m.identity, m.leader, formatPosition(m.position), m.join]))}`
      : row.kind === "patrol" ? `${fieldList(row.fields)}<p class="mr-note">${esc(tr("Stored waypoint order; the line does not prove a walkable path.", "仅连接配置路点，不代表可通行路径。"))}</p>${table(["#", tr("Position X, Y, Z", "坐标 X, Y, Z"), tr("Gait code", "步态代码"), tr("Actions", "动作")], (row.points || []).map((p, i) => [i + 1, formatPosition(p.position), p.enterGaitRaw ?? p.patrolGaitRaw, p.actions]))}`
      : row.kind === "scene-state" ? `${table([tr("Scene state", "场景状态"), tr("Stored index", "配置索引")], Object.entries(row.sceneStates || {}))}<p class="mr-note">${esc(tr("Stored conditions, with raw comparison codes. No current condition result or entity visibility is inferred.", "条件与比较代码均为配置值，不推断当前条件结果或实体可见性。"))}</p>${(row.conditions || []).map((c) => `<details open><summary>${esc(c.stateName || tr("Condition", "条件"))}</summary>${conditionTree(c.condition)}</details>`).join("")}${storedDetails(tr("Map variable defaults", "地图变量默认值"), row.variables || {})}`
      : `${fieldList(row.fields)}${row.envTalkIds?.length ? `<h4>${esc(tr("Configured ambient dialogue ids", "环境对话配置 ID"))}</h4><p>${esc(row.envTalkIds.join(", "))}</p>` : ""}`;
    return `<h3>${esc(row.title || row.id)}</h3><p class="mr-note">${esc(placementLabel(row.placement))} · ${esc(row.levelId || tr("Unassigned level", "尚无关卡"))}${row.position ? ` · ${esc(formatPosition(row.position))}` : ""}</p>${canLocate ? `<button type="button" data-encounter-locate>${esc(tr("Locate authored position", "定位配置坐标"))}</button>` : ""}${row.diagnostic ? `<p class="mr-encounter-diagnostic">${esc(row.diagnostic)}</p>` : ""}${sourceHtml(row)}${content}<p class="mr-note">${esc(row.boundary || state.index?.boundary || "")}</p>`;
  }

  function rows() { return state.scope === "unplaced" ? state.unplaced || [] : state.rows; }

  function renderList() {
    if (!host) return;
    const list = host.querySelector(".mr-encounter-list");
    const detail = host.querySelector(".mr-encounter-detail");
    if (!list || !detail) return;
    const tokens = W.parseQuery(state.query);
    const visible = facets.filter(rows()).filter((row) => !tokens.length || W.queryMatches(JSON.stringify(row), tokens));
    const pageCount = Math.max(1, Math.ceil(visible.length / 40));
    state.page = Math.min(state.page, pageCount - 1);
    const start = state.page * 40;
    list.innerHTML = `<p class="mr-note" role="status">${visible.length.toLocaleString()} ${esc(tr("records", "条记录"))}</p>${visible.slice(start, start + 40).map((row) => `<button type="button" class="mr-encounter-pick${row.id === state.selected ? " is-active" : ""}" data-encounter-id="${esc(row.id)}" aria-pressed="${row.id === state.selected}"><b>${esc(row.title || row.id)}</b><small>${esc(kindLabel(row.kind))} · ${esc(placementLabel(row.placement))}</small></button>`).join("") || `<p class="mr-note">${esc(tr("No records match these filters.", "没有符合筛选的记录。"))}</p>`}${pageCount > 1 ? `<div class="mr-encounter-pages"><button type="button" data-encounter-page="-1" ${state.page === 0 ? "disabled" : ""}>‹</button><span>${state.page + 1} / ${pageCount}</span><button type="button" data-encounter-page="1" ${state.page + 1 === pageCount ? "disabled" : ""}>›</button></div>` : ""}`;
    const selected = visible.find((row) => row.id === state.selected);
    if (!selected && state.selected) { state.selected = ""; locate?.(null, false); }
    detail.innerHTML = selected ? detailsHtml(selected) : `<p class="mr-placeholder">${esc(tr("Choose a record to inspect its stored relationships and authored placement.", "选择记录以查看配置关联与坐标。"))}</p>`;
    list.querySelectorAll("[data-encounter-id]").forEach((button) => button.addEventListener("click", () => {
      state.selected = button.dataset.encounterId;
      renderList();
      locate?.(visible.find((row) => row.id === state.selected) || null, false);
    }));
    list.querySelectorAll("[data-encounter-page]").forEach((button) => button.addEventListener("click", () => {
      state.page += Number(button.dataset.encounterPage);
      renderList();
      list.scrollTop = 0;
    }));
    detail.querySelector("[data-encounter-locate]")?.addEventListener("click", () => locate?.(selected, true));
  }

  function renderContent() {
    if (!host) return;
    const content = host.querySelector(".mr-encounters-content");
    if (!content) return;
    const failures = (state.index?.datasets || []).filter((row) => row.status !== "current");
    const unplacedCount = state.index?.levels.find((row) => row.levelId === "unplaced")?.count || 0;
    content.innerHTML = `<p class="mr-note">${esc(tr("Browse authored waves, groups, patrol points and NPC placements. Scene conditions apply to their named levels.", "浏览配置波次、编组、巡逻路点与 NPC 坐标。场景条件按其明确关卡归属显示。"))}</p>${state.error ? `<p class="mr-encounter-diagnostic">${esc(tr("Encounter publication unavailable", "遭遇数据暂不可用"))}: ${esc(state.error)}</p>` : ""}${failures.map((row) => `<p class="mr-encounter-diagnostic">${esc(row.datasetId)}: ${esc(row.diagnostic)}</p>`).join("")}<div class="mr-encounter-toolbar"><input type="search" data-encounter-search value="${esc(state.query)}" placeholder="${esc(tr("Search names, ids and stored fields", "搜索名称、ID 与配置字段"))}" aria-label="${esc(tr("Search encounters", "搜索遭遇"))}"><select data-encounter-scope aria-label="${esc(tr("Encounter scope", "遭遇范围"))}"><option value="map">${esc(tr("Current map", "当前地图"))} (${state.rows.length})</option><option value="unplaced">${esc(tr("All unplaced records", "全部未定位记录"))} (${unplacedCount})</option></select><button type="button" data-encounter-reset>${esc(tr("Reset", "重置"))}</button></div><div class="mr-encounter-kinds"></div><div class="mr-encounter-placement"></div><div class="mr-encounter-browser"><div class="mr-encounter-list"></div><div class="mr-encounter-detail"></div></div>`;
    const snapshot = facets?.snapshot();
    facets = W.facets.create({ countMode: "total", groups: [
      { id: "kind", container: content.querySelector(".mr-encounter-kinds"), values: (row) => row.kind, label: kindLabel },
      { id: "placement", container: content.querySelector(".mr-encounter-placement"), values: (row) => row.placement, label: placementLabel },
    ], onChange: () => { state.page = 0; renderList(); } });
    if (snapshot) facets.restore(snapshot, { silent: true });
    facets.render(rows());
    const scope = content.querySelector("[data-encounter-scope]");
    scope.value = state.scope;
    scope.addEventListener("change", async () => {
      state.scope = scope.value;
      state.selected = "";
      state.page = 0;
      locate?.(null, false);
      if (state.scope === "unplaced") {
        try { await loadUnplaced(); } catch (error) { state.error = String(error.message || error); }
      }
      renderContent();
    });
    content.querySelector("[data-encounter-search]").addEventListener("input", (event) => { state.query = event.target.value; state.page = 0; renderList(); });
    content.querySelector("[data-encounter-reset]").addEventListener("click", () => {
      state.query = ""; state.page = 0; state.selected = "";
      facets.reset({ silent: true }); locate?.(null, false); renderContent();
    });
    renderList();
  }

  function mount(root, onLocate) {
    host = root.querySelector(".mr-encounters");
    locate = onLocate;
    if (!host) return;
    host.addEventListener("toggle", () => { state.open = host.open; });
    renderContent();
  }

  function geometry(row) {
    if (!row || row.placement !== "placed" || !state.levelIds.has(row.levelId)) return { points: [], route: false };
    const points = row.kind === "group" ? (row.members || []).map((member) => member.position).filter(Boolean)
      : row.kind === "patrol" ? (row.plotPoints || []).map((point) => point.position)
      : row.position ? [row.position] : [];
    return { points, route: row.kind === "patrol" };
  }

  W.mapEncounters = { load, markup, mount, geometry };
})();
