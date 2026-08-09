(() => {
  const PAGE_SIZE = Infinity;
  const RELATION_PAGE_SIZE = Infinity;
  const state = {
    initialized: false,
    language: "",
    data: null,
    nodes: new Map(),
    rootMeta: new Map(),
    filtered: [],
    selected: "",
    page: 0,
    groupPages: new Map(),
    request: 0,
    controller: null,
    promise: null,
  };

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const app = () => document.querySelector("#presentation-app");
  const byId = (id) => document.querySelector(`#${id}`);
  const normalize = (value) => String(value || "").trim().toLowerCase();
  const label = (value) => String(value || "").replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());

  function init() {
    if (state.initialized || !app()) return Boolean(app());
    state.initialized = true;
    app().innerHTML = `
      <div class="presentation-shell">
        <header class="presentation-hero">
          <div>
            <p class="presentation-eyebrow">Static source-graph evidence</p>
            <h1>Entity Presentation</h1>
            <p id="presentation-scope">Models, materials, animation, effects, and representative exported assets.</p>
          </div>
          <div id="presentation-summary" class="presentation-summary" role="status" aria-live="polite">Open this view to load its graph.</div>
        </header>
        <div id="presentation-banner" class="presentation-banner" role="status" aria-live="polite" hidden></div>
        <div class="presentation-layout">
          <aside class="presentation-browser" aria-label="Presentation roots">
            <form id="presentation-filters" class="presentation-filters">
              <label class="presentation-search">Search
                <input id="presentation-search" type="search" placeholder="Name, id, path, or related asset" autocomplete="off">
              </label>
              <div class="presentation-filter-grid">
                <label>Kind<select id="presentation-kind"><option value="">All kinds</option></select></label>
                <label>Evidence<select id="presentation-confidence"><option value="">Any evidence</option><option value="direct">Has direct</option><option value="inferred">Has inferred</option></select></label>
                <label>Preview<select id="presentation-preview"><option value="">Any</option><option value="yes">Has previewable asset</option></select></label>
                <label>Links<select id="presentation-links"><option value="">Any</option><option value="connected">Connected</option><option value="standalone">Standalone</option></select></label>
              </div>
              <button id="presentation-reset" type="reset">Reset filters</button>
            </form>
            <p id="presentation-results" class="presentation-results" role="status" aria-live="polite"></p>
            <div id="presentation-list" class="presentation-list" role="listbox" aria-label="Presentation roots"></div>
            <div class="presentation-pager" aria-label="Root pages">
              <button id="presentation-previous" class="presentation-more" type="button">Previous roots</button>
              <button id="presentation-next" class="presentation-more" type="button">Next roots</button>
            </div>
          </aside>
          <main id="presentation-detail" class="presentation-detail" tabindex="-1">
            <div class="presentation-empty">Choose a root to inspect its presentation evidence.</div>
          </main>
        </div>
      </div>`;
    bind();
    return true;
  }

  function bind() {
    ["presentation-search", "presentation-kind", "presentation-confidence", "presentation-preview", "presentation-links"]
      .forEach((id) => byId(id)?.addEventListener(id === "presentation-search" ? "input" : "change", applyFilters));
    byId("presentation-filters")?.addEventListener("reset", () => requestAnimationFrame(applyFilters));
    byId("presentation-previous")?.addEventListener("click", () => {
      state.page = Math.max(0, state.page - 1);
      renderList();
      byId("presentation-list")?.querySelector("button[data-root]")?.focus();
    });
    byId("presentation-next")?.addEventListener("click", () => {
      state.page += 1;
      renderList();
      byId("presentation-list")?.querySelector("button[data-root]")?.focus();
    });
    byId("presentation-list")?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-root]");
      if (button) selectRoot(button.dataset.root, { focusDetail: false });
    });
    byId("presentation-list")?.addEventListener("keydown", (event) => {
      if (!event.target.matches("button[data-root]")) return;
      const buttons = Array.from(byId("presentation-list").querySelectorAll("button[data-root]"));
      const index = buttons.indexOf(event.target);
      let target = null;
      if (event.key === "ArrowDown") target = buttons[index + 1] || buttons[0];
      else if (event.key === "ArrowUp") target = buttons[index - 1] || buttons.at(-1);
      else if (event.key === "Home") target = buttons[0];
      else if (event.key === "End") target = buttons.at(-1);
      if (target) { event.preventDefault(); target.focus(); }
    });
    byId("presentation-detail")?.addEventListener("click", (event) => {
      const rootButton = event.target.closest("button[data-select-root]");
      if (rootButton && state.nodes.has(rootButton.dataset.selectRoot)) {
        selectRoot(rootButton.dataset.selectRoot, { focusDetail: true });
        return;
      }
      const pager = event.target.closest("button[data-page-group]");
      if (pager) {
        const group = pager.dataset.pageGroup;
        const nextPage = Math.max(0, (state.groupPages.get(group) || 0) + Number(pager.dataset.pageDirection || 0));
        state.groupPages.set(group, nextPage);
        renderDetail(group);
      }
    });
  }

  function showLoading() {
    init();
    byId("presentation-summary").textContent = "Loading presentation graph…";
    byId("presentation-list").innerHTML = '<div class="presentation-loading">Loading 9 MB of curated evidence…</div>';
    byId("presentation-detail").innerHTML = '<div class="presentation-loading">Preparing relationships…</div>';
  }

  async function load(language = "CN", force = false) {
    init();
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && state.data && state.language === nextLanguage) return state.data;
    if (!force && state.promise && state.language === nextLanguage) return state.promise;
    const request = ++state.request;
    state.controller?.abort();
    state.controller = new AbortController();
    state.language = nextLanguage;
    showLoading();
    const promise = fetch(`data/lang/${encodeURIComponent(nextLanguage)}/presentation/index.json`, {
      signal: state.controller.signal,
      cache: force ? "reload" : "default",
    }).then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }).then((data) => {
      if (request !== state.request) return null;
      prepare(data);
      return data;
    }).catch((error) => {
      if (request !== state.request || error?.name === "AbortError") return null;
      state.data = null;
      renderError(error);
      throw error;
    }).finally(() => {
      if (request === state.request) state.promise = null;
    });
    state.promise = promise;
    return promise;
  }

  function prepare(data) {
    state.data = data;
    state.nodes = new Map((data.nodes || []).map((node) => [node.id, node]));
    state.rootMeta.clear();
    for (const root of data.roots || []) {
      const node = state.nodes.get(root) || { id: root, label: root, kind: "unknown" };
      const indexes = data.rootEdges?.[root] || [];
      const edges = indexes.map((index) => data.edges?.[index]).filter(Boolean);
      const related = [];
      let hasPreview = Boolean(node.previewable);
      for (const edge of edges) {
        const other = state.nodes.get(edge.source === root ? edge.target : edge.source);
        if (other && related.length < 80) related.push(other.label, other.id, other.path);
        if (other?.previewable) hasPreview = true;
      }
      state.rootMeta.set(root, {
        node, edges, edgeCount: edges.length, hasPreview,
        confidence: new Set(edges.map((edge) => edge.confidence)),
        search: normalize([node.label, node.id, node.path, ...related].filter(Boolean).join(" ")),
      });
    }
    populateKinds();
    state.selected = state.rootMeta.has(state.selected) ? state.selected : (data.roots?.[0] || "");
    state.page = 0;
    state.groupPages.clear();
    const counts = data.counts || {};
    byId("presentation-summary").textContent = `${Number(counts.roots || 0).toLocaleString()} roots · ${Number(counts.nodes || 0).toLocaleString()} nodes · ${Number(counts.edges || 0).toLocaleString()} relationships`;
    byId("presentation-scope").textContent = data.scope?.note || "Static authored and exported-asset evidence; runtime presentation is outside scope.";
    renderBanner();
    applyFilters();
  }

  function populateKinds() {
    const select = byId("presentation-kind");
    const selected = select.value;
    const counts = new Map();
    for (const { node } of state.rootMeta.values()) counts.set(node.kind, (counts.get(node.kind) || 0) + 1);
    select.innerHTML = '<option value="">All kinds</option>' + Array.from(counts).sort((a, b) => a[0].localeCompare(b[0]))
      .map(([kind, count]) => `<option value="${esc(kind)}">${esc(label(kind))} (${count.toLocaleString()})</option>`).join("");
    select.value = counts.has(selected) ? selected : "";
  }

  function renderBanner() {
    const banner = byId("presentation-banner");
    const graph = state.data?.graph || {};
    if (graph.degradedMode || graph.stale || !graph.available) {
      banner.hidden = false;
      banner.className = "presentation-banner is-warning";
      banner.innerHTML = `<strong>Evidence unavailable.</strong> ${esc(graph.staleReason || "Rebuild the local source graph and Presentation payload.")} <button type="button" data-retry>Retry</button>`;
      banner.querySelector("[data-retry]")?.addEventListener("click", () => window.WebUI?.retryView?.("presentation", state.language));
    } else {
      banner.hidden = true;
      banner.textContent = "";
    }
  }

  function applyFilters() {
    if (!state.data) return;
    const query = normalize(byId("presentation-search")?.value);
    const kind = byId("presentation-kind")?.value || "";
    const confidence = byId("presentation-confidence")?.value || "";
    const preview = byId("presentation-preview")?.value || "";
    const links = byId("presentation-links")?.value || "";
    state.filtered = (state.data.roots || []).filter((root) => {
      const meta = state.rootMeta.get(root);
      return meta && (!query || meta.search.includes(query)) && (!kind || meta.node.kind === kind)
        && (!confidence || meta.confidence.has(confidence)) && (!preview || meta.hasPreview)
        && (!links || (links === "connected" ? meta.edgeCount > 0 : meta.edgeCount === 0));
    });
    state.page = 0;
    renderList();
    renderDetail();
  }

  function visibleRoots() {
    // Reserve one of the 150 DOM rows for the selected root. This keeps the
    // selection visible without dropping a filtered match from the page range.
    const matchPageSize = PAGE_SIZE - 1;
    const start = state.page * matchPageSize;
    const page = state.filtered.slice(start, start + matchPageSize);
    if (state.selected && state.rootMeta.has(state.selected) && !page.includes(state.selected)) {
      page.push(state.selected);
    }
    return page;
  }

  function renderList() {
    const list = byId("presentation-list");
    const roots = visibleRoots();
    const matchPageSize = PAGE_SIZE - 1;
    const start = state.page * matchPageSize;
    const end = Math.min(state.filtered.length, start + matchPageSize);
    const selectedPinned = Boolean(state.selected) && !state.filtered.slice(start, end).includes(state.selected);
    const range = state.filtered.length ? `${(start + 1).toLocaleString()}–${end.toLocaleString()}` : "0";
    byId("presentation-results").textContent = `${state.filtered.length.toLocaleString()} matching roots · page rows ${range}${selectedPinned ? " + selected root" : ""}`;
    if (!roots.length) {
      list.innerHTML = '<div class="presentation-empty">No roots match these filters. Reset filters or broaden the search.</div>';
    } else {
      list.innerHTML = roots.map((root) => {
        const meta = state.rootMeta.get(root);
        const active = root === state.selected;
        return `<button type="button" role="option" aria-selected="${active}" class="presentation-root${active ? " is-selected" : ""}" data-root="${esc(root)}">
          <span class="presentation-root-title">${esc(meta.node.label || root)}</span>
          <span class="presentation-root-meta"><span>${esc(label(meta.node.kind))}</span><span>${meta.edgeCount.toLocaleString()} links</span>${meta.hasPreview ? "<span>preview</span>" : ""}</span>
          <code>${esc(root)}</code>
        </button>`;
      }).join("");
    }
    const previous = byId("presentation-previous");
    const next = byId("presentation-next");
    previous.disabled = state.page === 0;
    next.disabled = end >= state.filtered.length;
    previous.hidden = state.filtered.length <= matchPageSize;
    next.hidden = state.filtered.length <= matchPageSize;
  }

  function selectRoot(root, { focusDetail = false } = {}) {
    if (!state.rootMeta.has(root)) return;
    state.selected = root;
    state.groupPages.clear();
    renderList();
    renderDetail();
    if (focusDetail) byId("presentation-detail")?.focus();
  }

  function relationGroup(edge, root) {
    if (edge.target === root) return "Usage";
    const source = state.nodes.get(edge.source);
    const target = state.nodes.get(edge.target);
    const signal = `${edge.type} ${source?.kind || ""} ${target?.kind || ""}`.toLowerCase();
    if (/material|texture|shader/.test(signal)) return "Materials & shaders";
    if (/animation|clip|state|montage|facial|effect/.test(signal)) return "Animation & effects";
    if (/model|prefab|controller|asset_entity/.test(signal)) return "Model & prefab";
    return "Other relationships";
  }

  function edgeCard(edge, root) {
    const incident = edge.source === root || edge.target === root;
    const outgoing = edge.source === root;
    const source = state.nodes.get(edge.source) || { id: edge.source, label: edge.source, kind: "unknown" };
    const target = state.nodes.get(edge.target) || { id: edge.target, label: edge.target, kind: "unknown" };
    const otherId = outgoing ? edge.target : edge.source;
    const other = outgoing ? target : source;
    const evidence = edge.evidence || {};
    const endpoint = (node, id) => state.rootMeta.has(id)
      ? `<button type="button" data-select-root="${esc(id)}">${esc(node.label || id)}</button>`
      : `<span>${esc(node.label || id)}</span>`;
    const endpoints = incident
      ? `${endpoint(other, otherId)}<span>${esc(label(other.kind))}</span>`
      : `<span class="presentation-chain-end">${endpoint(source, edge.source)}<small>${esc(label(source.kind))}</small></span><span class="presentation-chain-arrow" aria-label="to">→</span><span class="presentation-chain-end">${endpoint(target, edge.target)}<small>${esc(label(target.kind))}</small></span>`;
    return `<article class="presentation-edge">
      <div class="presentation-edge-head">
        <span class="presentation-badge ${edge.confidence === "inferred" ? "is-inferred" : "is-direct"}">${esc(edge.confidence || "unknown")}</span>
        <span class="presentation-direction">${incident ? (outgoing ? "Outgoing" : "Incoming") : "Path step"}</span>
        <strong>${esc(label(edge.type))}</strong>
      </div>
      <div class="presentation-edge-target${incident ? "" : " is-chain"}">${endpoints}</div>
      <code>${esc(edge.source)} → ${esc(edge.target)}</code>
      ${incident && other.path ? `<p class="presentation-path">${esc(other.path)}</p>` : ""}
      <details><summary>Evidence</summary><dl><dt>Source</dt><dd>${esc(evidence.source || "source graph")}</dd>${evidence.path ? `<dt>Path</dt><dd>${esc(evidence.path)}</dd>` : ""}</dl>${evidence.raw ? `<pre>${esc(compactJson(evidence.raw))}</pre>` : ""}</details>
    </article>`;
  }

  function compactJson(value) {
    const text = JSON.stringify(value, null, 2);
    return text.length > 5000 ? `${text.slice(0, 5000)}\n… truncated for display` : text;
  }

  function renderDetail(focusGroup = "") {
    const detail = byId("presentation-detail");
    if (!state.data) return;
    if (!state.selected || !state.rootMeta.has(state.selected)) {
      detail.innerHTML = '<div class="presentation-empty">Choose a root to inspect its presentation evidence.</div>';
      return;
    }
    const root = state.selected;
    const meta = state.rootMeta.get(root);
    const groups = new Map();
    [...meta.edges].sort((a, b) => (a.confidence === "inferred") - (b.confidence === "inferred") || a.type.localeCompare(b.type))
      .forEach((edge) => {
        const group = relationGroup(edge, root);
        if (!groups.has(group)) groups.set(group, []);
        groups.get(group).push(edge);
      });
    const order = ["Usage", "Model & prefab", "Materials & shaders", "Animation & effects", "Other relationships"];
    const sections = order.filter((name) => groups.has(name)).map((name) => {
      const edges = groups.get(name);
      const page = state.groupPages.get(name) || 0;
      const start = page * RELATION_PAGE_SIZE;
      const visible = edges.slice(start, start + RELATION_PAGE_SIZE);
      const end = Math.min(edges.length, start + RELATION_PAGE_SIZE);
      return `<section class="presentation-section" data-group="${esc(name)}"><h2>${esc(name)} <span>${edges.length.toLocaleString()}</span></h2>
        <div class="presentation-edge-list">${visible.map((edge) => edgeCard(edge, root)).join("")}</div>
        ${edges.length > RELATION_PAGE_SIZE ? `<div class="presentation-relation-pager"><button class="presentation-more" type="button" data-page-group="${esc(name)}" data-page-direction="-1" ${page === 0 ? "disabled" : ""}>Previous</button><span>${(start + 1).toLocaleString()}–${end.toLocaleString()} of ${edges.length.toLocaleString()}</span><button class="presentation-more" type="button" data-page-group="${esc(name)}" data-page-direction="1" ${end >= edges.length ? "disabled" : ""}>Next</button></div>` : ""}
      </section>`;
    }).join("");
    const omissions = state.data.omissions || {};
    const confidenceSummary = [meta.confidence.has("direct") ? "direct" : "", meta.confidence.has("inferred") ? "inferred" : ""].filter(Boolean).join(" + ") || "none";
    const assetTab = document.querySelector("#assets-tab");
    const assetsAvailable = assetTab && !assetTab.hidden && assetTab.getAttribute("aria-hidden") !== "true";
    detail.innerHTML = `<article class="presentation-detail-card">
      <header><p class="presentation-eyebrow">${esc(label(meta.node.kind))}</p><h1>${esc(meta.node.label || root)}</h1><code>${esc(root)}</code>
        <div class="presentation-chips"><span>${meta.edgeCount.toLocaleString()} relationships</span>${meta.hasPreview ? `<span>Previewable asset linked</span>${assetsAvailable ? '<a href="#assets">Open Assets</a>' : ""}` : ""}</div>
      </header>
      ${meta.node.path ? `<p class="presentation-path">${esc(meta.node.path)}</p>` : ""}
      <section class="presentation-section"><h2>Overview</h2><dl class="presentation-facts"><dt>Graph kind</dt><dd>${esc(meta.node.graphKind || meta.node.kind)}</dd><dt>Source</dt><dd>${esc(meta.node.source || "source graph")}</dd><dt>Evidence</dt><dd>${esc(confidenceSummary)}</dd></dl></section>
      ${sections || '<section class="presentation-section"><h2>Relationships</h2><p>No curated presentation relationships were recovered for this standalone record.</p></section>'}
      <section class="presentation-section presentation-evidence"><h2>Evidence & boundaries</h2><p>${esc(state.data.scope?.note || "Static evidence only.")}</p>
        <details><summary>Payload caps and omissions</summary><pre>${esc(compactJson({ caps: state.data.caps || {}, omissions }))}</pre></details>
        ${meta.node.raw ? `<details><summary>Raw node evidence</summary><pre>${esc(compactJson(meta.node.raw))}</pre></details>` : ""}
      </section>
    </article>`;
    if (focusGroup) {
      const group = detail.querySelector(`[data-group="${CSS.escape(focusGroup)}"]`);
      const focusTarget = Array.from(group?.querySelectorAll("button[data-page-group]") || []).find((button) => !button.disabled) || group?.querySelector("h2");
      if (focusTarget?.tagName === "H2") focusTarget.tabIndex = -1;
      focusTarget?.focus();
    }
  }

  function renderError(error) {
    init();
    byId("presentation-summary").textContent = "Presentation data could not be loaded.";
    byId("presentation-list").innerHTML = '<div class="presentation-empty">No presentation roots are available.</div>';
    byId("presentation-detail").innerHTML = `<div class="presentation-error" role="alert"><h2>Unable to load Presentation</h2><p>${esc(error?.message || error)}</p><button type="button">Retry</button></div>`;
    byId("presentation-detail").querySelector("button")?.addEventListener("click", () => window.WebUI?.retryView?.("presentation", state.language || "CN"));
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.presentation = { init, load };
})();
