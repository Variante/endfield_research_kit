// Recovery progress page.
//
// Renders webui/data/recovery/index.json (schema endfield.recovery-progress.v4):
// a log-scaled volume bar per VFS block, then a tree of VFS blocks whose leaves
// are the declared logical-file types, each with its four L1-L4 stage states.
//
// Volumes are measured; stages are declared readings of the cited memory
// topic. There is no progress score, and bar width never means "understood".
(() => {
  const DATA_URL = "data/recovery/index.json";
  const SCHEMA = "endfield.recovery-progress.v4";

  const TEXTS = {
    zh: {
      pageTitle: "恢复进度",
      intro: "上方为各 VFS 数据块的体量；下方文件树按数据块列出每类逻辑文件及其 L1–L4 恢复状态。体量为实测，状态为对所引记忆主题的声明性解读，不是百分比。",
      overviewTitle: "数据块体量",
      overviewNote: "段宽为对数刻度，只表示体量，不表示恢复程度；斜纹为已声明但本地未安装。点击某段可在下方文件树中定位。",
      metricBytes: "按载荷字节",
      metricFiles: "按逻辑文件",
      metricLabel: "体量度量",
      legendProfiled: "本地已读取",
      legendAbsent: "已声明、未安装",
      ofTotal: "占全部",
      treeTitle: "文件类型与恢复状态",
      levels: "层级",
      states: "状态",
      selectFamily: "选择一类文件查看各层级的证据与来源。",
      files: "文件",
      chunks: "chunk",
      noFiles: "本地概况中无文件",
      avail_absent: "未安装",
      avail_mixed: "部分可用",
      unclassified: "未分类",
      unclassifiedNote: "没有任何已声明模式匹配这些路径，因此不声明任何阶段。",
      pattern: "路径模式",
      samples: "示例路径",
      sharedStages: "阶段沿用自",
      source: "来源",
      limit: "证据边界",
      generated: "生成于",
      rebuild: "重建",
      loadError: "无法加载恢复进度数据。请先运行构建命令。",
      missing: "尚未生成恢复进度数据。",
      schemaMismatch: "恢复进度数据的格式版本不符，请重新运行构建命令。",
    },
    en: {
      pageTitle: "Recovery Progress",
      intro: "The bar shows each VFS block's volume. The tree lists every logical-file type under its block with its L1–L4 recovery state. Volumes are measured; states are declared readings of the cited memory topic, not percentages.",
      overviewTitle: "Block volume",
      overviewNote: "Log-scaled widths show volume only, never recovery; hatched sections are declared but not installed locally. Select a section to find it in the tree.",
      metricBytes: "by payload bytes",
      metricFiles: "by logical files",
      metricLabel: "Volume measure",
      legendProfiled: "read locally",
      legendAbsent: "declared, not installed",
      ofTotal: "of total",
      treeTitle: "File types and recovery state",
      levels: "Levels",
      states: "States",
      selectFamily: "Select a file type to see its evidence and sources per level.",
      files: "files",
      chunks: "chunks",
      noFiles: "no files in the local profile",
      avail_absent: "not installed",
      avail_mixed: "partly available",
      unclassified: "unclassified",
      unclassifiedNote: "No declared pattern matches these paths, so no stage is claimed.",
      pattern: "Path pattern",
      samples: "Sample paths",
      sharedStages: "Stages shared with",
      source: "source",
      limit: "evidence limit",
      generated: "Generated",
      rebuild: "rebuild",
      loadError: "Recovery progress data could not be loaded. Run the build command first.",
      missing: "Recovery progress data has not been generated yet.",
      schemaMismatch: "Recovery progress data has an unexpected schema. Rebuild it.",
    },
  };

  const LEVEL_NAMES = {
    zh: { 1: "字节在哪里", 2: "字节如何划分", 3: "字段是什么", 4: "数据意味着什么" },
  };

  const LANE_COLORS = {
    unity_assets: "#5a7d9a",
    world: "#3d7478",
    audio: "#8a5f9e",
    gameplay: "#c8410f",
    text: "#2f7a55",
    catalog: "#8a6d1f",
    code: "#4a6fa5",
    story: "#b03a6a",
    extraction: "#5f6c74",
    shared: "#6f7f88",
    cross_lane: "#7a6a5a",
    provenance: "#98a1a8",
  };

  // A glyph per stage state, so a state never depends on colour alone.
  const STATE_GLYPHS = { closed: "●", partial: "◐", open: "○", notAssessed: "?" };

  const STATE = {
    payload: null,
    loading: null,
    loaded: false,
    locale: "zh",
    metric: "bytes",
    collapsed: new Set(), // blocks start open so every type's state is visible
    selected: null, // { block, family }
    status: null,
  };

  // --- helpers ------------------------------------------------------------

  function normalizeLocale(value) {
    return String(value || "").toLowerCase().startsWith("en") ? "en" : "zh";
  }

  function t(key) {
    return TEXTS[STATE.locale]?.[key] || TEXTS.en[key] || key;
  }

  function localized(node, key) {
    if (!node) return "";
    return (STATE.locale === "zh" && node[`${key}Zh`]) || node[key] || "";
  }

  function levelName(level) {
    return LEVEL_NAMES[STATE.locale]?.[level.level] || level.name;
  }

  const NUM = new Intl.NumberFormat("en-US");
  const num = (value) => (Number.isFinite(value) ? NUM.format(value) : "—");

  function bytes(value) {
    if (!Number.isFinite(value)) return "—";
    if (value >= 1e9) return `${(value / 1e9).toFixed(2)} GB`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(1)} MB`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(1)} kB`;
    return `${value} B`;
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function domId(...parts) {
    return `recovery-${parts.join("-").replace(/[^A-Za-z0-9_-]/g, "_")}`;
  }

  function section(title, note) {
    const wrap = el("section", "recovery-section");
    wrap.appendChild(el("h2", null, title));
    if (note) wrap.appendChild(el("p", "recovery-note", note));
    return wrap;
  }

  function stateInfo(id) {
    return (STATE.payload?.stageStates || []).find((state) => state.id === id);
  }

  function laneLabel(id) {
    const lane = (STATE.payload?.lanes || []).find((row) => row.id === id);
    return lane ? localized(lane, "label") : id;
  }

  function sizeLine(measured) {
    if (!measured?.files) return t("noFiles");
    return `${num(measured.files)} ${t("files")} · ${bytes(measured.declaredBytes)}`;
  }

  // --- tooltip ------------------------------------------------------------

  let tooltip = null;

  function hideTip() {
    if (tooltip) tooltip.hidden = true;
  }

  function showTip(anchor, lines) {
    if (!tooltip || !tooltip.isConnected) {
      tooltip = el("div", "recovery-tip");
      tooltip.setAttribute("role", "tooltip");
      document.body.appendChild(tooltip);
    }
    tooltip.textContent = "";
    lines.forEach((line, index) => {
      tooltip.appendChild(el("div", index === 0 ? "recovery-tip-line is-strong" : "recovery-tip-line", line));
    });
    tooltip.hidden = false;
    const rect = anchor.getBoundingClientRect();
    const tipRect = tooltip.getBoundingClientRect();
    const left = Math.max(8, Math.min(rect.left + rect.width / 2 - tipRect.width / 2, window.innerWidth - tipRect.width - 8));
    let top = rect.top - tipRect.height - 8;
    if (top < 8) top = rect.bottom + 8;
    tooltip.style.left = `${Math.round(left + window.scrollX)}px`;
    tooltip.style.top = `${Math.round(top + window.scrollY)}px`;
  }

  // --- volume bar ---------------------------------------------------------

  function metricOf(block, availability) {
    const bucket = block.measured?.byAvailability?.[availability];
    return (STATE.metric === "files" ? bucket?.files : bucket?.declaredBytes) || 0;
  }

  function renderOverview(payload) {
    const wrap = section(t("overviewTitle"), t("overviewNote"));

    const toolbar = el("div", "recovery-toolbar");
    const toggle = el("div", "recovery-toggle");
    toggle.setAttribute("role", "group");
    toggle.setAttribute("aria-label", t("metricLabel"));
    for (const metric of ["bytes", "files"]) {
      const button = el("button", "recovery-toggle-btn", t(metric === "bytes" ? "metricBytes" : "metricFiles"));
      button.type = "button";
      button.setAttribute("aria-pressed", String(STATE.metric === metric));
      button.addEventListener("click", () => {
        if (STATE.metric === metric) return;
        STATE.metric = metric;
        render({ focus: `.recovery-toggle-btn[aria-pressed="true"]` });
      });
      toggle.appendChild(button);
    }
    toolbar.appendChild(toggle);
    const legend = el("div", "recovery-legend");
    for (const [cls, key] of [["", "legendProfiled"], [" is-absent", "legendAbsent"]]) {
      const item = el("span", "recovery-legend-item");
      item.appendChild(el("span", `recovery-swatch${cls}`));
      item.appendChild(el("span", null, t(key)));
      legend.appendChild(item);
    }
    toolbar.appendChild(legend);
    wrap.appendChild(toolbar);

    // Profiled sections first, then the hatched declared-but-absent ones.
    // Log-scaled widths keep every nonzero section visible; the tooltip keeps
    // the true measured share.
    const pieces = [];
    for (const availability of ["profiled", "absent"]) {
      for (const block of payload.vfs.blocks) {
        const value = metricOf(block, availability);
        if (value > 0) pieces.push({ block, availability, value });
      }
    }
    const total = pieces.reduce((sum, piece) => sum + piece.value, 0) || 1;
    const smallest = Math.min(...pieces.map((piece) => piece.value));
    const weight = (value) => Math.log10(1 + (100 * value) / smallest);
    const weightTotal = pieces.reduce((sum, piece) => sum + weight(piece.value), 0) || 1;

    const bar = el("div", "recovery-segbar");
    bar.setAttribute("role", "group");
    bar.setAttribute("aria-label", t("overviewTitle"));
    for (const { block, availability, value } of pieces) {
      const absent = availability === "absent";
      const piece = el("button", `recovery-segbar-piece${absent ? " is-absent" : ""}`);
      piece.type = "button";
      piece.style.width = `${(weight(value) / weightTotal) * 100}%`;
      if (!absent) piece.style.background = LANE_COLORS[block.lane] || "var(--accent-2)";
      const share = value / total;
      const shareText = share < 0.00005 ? "<0.01%" : `${(share * 100).toFixed(2)}%`;
      const volume = STATE.metric === "files" ? `${num(value)} ${t("files")}` : bytes(value);
      const summary = `${volume} · ${shareText} ${t("ofTotal")}${absent ? ` · ${t("legendAbsent")}` : ""}`;
      piece.setAttribute("aria-label", `${block.enumName}: ${summary}`);
      const tip = () => showTip(piece, [block.enumName, laneLabel(block.lane), summary]);
      piece.addEventListener("mouseenter", tip);
      piece.addEventListener("focus", tip);
      piece.addEventListener("mouseleave", hideTip);
      piece.addEventListener("blur", hideTip);
      piece.addEventListener("click", () => {
        STATE.collapsed.delete(block.enumName);
        render({ focus: `#${domId("block", block.enumName)}`, scroll: true });
      });
      bar.appendChild(piece);
    }
    wrap.appendChild(bar);
    return wrap;
  }

  // --- tree ---------------------------------------------------------------

  function stageStrip(stages, levels) {
    const strip = el("span", "recovery-stages");
    for (const stage of stages || []) {
      const info = stateInfo(stage.state);
      const level = levels.find((row) => row.level === stage.level);
      const cell = el("span", `recovery-stage-cell is-${stage.state}`);
      cell.appendChild(el("span", "recovery-stage-level", `L${stage.level}`));
      cell.appendChild(el("span", "recovery-stage-glyph", STATE_GLYPHS[stage.state] || "?"));
      cell.title = `L${stage.level} ${level ? levelName(level) : ""}: ${info ? localized(info, "label") : stage.state}`;
      strip.appendChild(cell);
    }
    return strip;
  }

  function renderKey(payload) {
    const key = el("div", "recovery-key");
    const levels = el("p", "recovery-key-row");
    levels.appendChild(el("strong", null, `${t("levels")}: `));
    levels.appendChild(
      document.createTextNode(payload.levels.map((level) => `L${level.level} ${levelName(level)}`).join(" · ")),
    );
    key.appendChild(levels);
    const states = el("p", "recovery-key-row");
    states.appendChild(el("strong", null, `${t("states")}: `));
    for (const state of payload.stageStates || []) {
      const item = el("span", `recovery-key-state is-${state.id}`);
      item.appendChild(el("span", "recovery-stage-glyph", STATE_GLYPHS[state.id] || "?"));
      item.appendChild(el("span", null, localized(state, "label")));
      item.title = localized(state, "meaning");
      states.appendChild(item);
    }
    key.appendChild(states);
    return key;
  }

  function renderTree(payload) {
    const wrap = section(t("treeTitle"));
    wrap.appendChild(renderKey(payload));

    const browser = el("div", "recovery-browser");
    const tree = el("ul", "recovery-tree");
    for (const block of payload.vfs.blocks) {
      if (block.families?.length) tree.appendChild(renderBlock(payload, block));
    }
    browser.appendChild(tree);
    const detail = el("aside", "recovery-detail");
    detail.setAttribute("aria-live", "polite");
    fillDetail(payload, detail);
    browser.appendChild(detail);
    wrap.appendChild(browser);
    return wrap;
  }

  function renderBlock(payload, block) {
    const open = !STATE.collapsed.has(block.enumName);
    const item = el("li", "recovery-block");
    item.style.setProperty("--lane-color", LANE_COLORS[block.lane] || "var(--accent-2)");

    const toggle = el("button", "recovery-block-toggle");
    toggle.type = "button";
    toggle.id = domId("block", block.enumName);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.appendChild(el("span", "recovery-chevron", open ? "▾" : "▸"));
    toggle.appendChild(el("span", "recovery-block-name", block.enumName));
    const availability = block.measured?.availability;
    if (availability === "absent" || availability === "mixed") {
      toggle.appendChild(el("span", "recovery-avail", t(`avail_${availability}`)));
    }
    toggle.appendChild(el("span", "recovery-size", sizeLine(block.measured)));
    toggle.title = localized(block, "holds");
    item.appendChild(toggle);

    const list = el("ul", "recovery-families");
    list.hidden = !open;
    for (const family of block.families) list.appendChild(renderFamily(payload, block, family));
    item.appendChild(list);

    toggle.addEventListener("click", () => {
      const nowOpen = STATE.collapsed.has(block.enumName);
      if (nowOpen) STATE.collapsed.delete(block.enumName);
      else STATE.collapsed.add(block.enumName);
      toggle.setAttribute("aria-expanded", String(nowOpen));
      toggle.querySelector(".recovery-chevron").textContent = nowOpen ? "▾" : "▸";
      list.hidden = !nowOpen;
    });
    return item;
  }

  function renderFamily(payload, block, family) {
    const item = el("li");
    const button = el("button", `recovery-family${family.declared ? "" : " is-other"}`);
    button.type = "button";
    button.setAttribute(
      "aria-pressed",
      String(STATE.selected?.block === block.enumName && STATE.selected?.family === family.id),
    );
    const label = el("span", "recovery-family-name", localized(family, "label"));
    if (!family.declared) label.appendChild(el("span", "recovery-avail", t("unclassified")));
    button.appendChild(label);
    button.appendChild(el("span", "recovery-size", sizeLine(family.measured)));
    button.appendChild(stageStrip(family.stages, payload.levels));
    button.addEventListener("click", () => {
      STATE.selected = { block: block.enumName, family: family.id };
      document.querySelectorAll(".recovery-family[aria-pressed='true']").forEach((node) => {
        node.setAttribute("aria-pressed", "false");
      });
      button.setAttribute("aria-pressed", "true");
      const detail = document.querySelector(".recovery-detail");
      if (detail) fillDetail(payload, detail);
    });
    item.appendChild(button);
    return item;
  }

  function fillDetail(payload, detail) {
    detail.textContent = "";
    const block = payload.vfs.blocks.find((row) => row.enumName === STATE.selected?.block);
    const family = block?.families.find((row) => row.id === STATE.selected?.family);
    if (!family) {
      detail.appendChild(el("p", "recovery-note", t("selectFamily")));
      return;
    }
    const measured = family.measured || {};
    detail.appendChild(el("h3", null, localized(family, "label")));
    detail.appendChild(
      el(
        "p",
        "recovery-note",
        `${block.enumName} · ${sizeLine(measured)}${measured.containerChunks ? ` · ${num(measured.containerChunks)} ${t("chunks")}` : ""}`,
      ),
    );
    detail.appendChild(el("p", null, family.declared ? localized(family, "description") : t("unclassifiedNote")));

    const stages = el("ol", "recovery-stage-list");
    for (const stage of family.stages || []) {
      const level = payload.levels.find((row) => row.level === stage.level);
      const info = stateInfo(stage.state);
      const row = el("li", `is-${stage.state}`);
      const head = el("p", "recovery-stage-head");
      head.appendChild(el("span", "recovery-stage-glyph", STATE_GLYPHS[stage.state] || "?"));
      head.appendChild(
        el("strong", null, `L${stage.level} ${level ? levelName(level) : ""} — ${info ? localized(info, "label") : stage.state}`),
      );
      row.appendChild(head);
      if (level) row.title = level.question;
      row.appendChild(el("p", null, localized(stage, "text")));
      if (stage.source) {
        const source = el("p", "recovery-note");
        source.appendChild(document.createTextNode(`${t("source")}: `));
        source.appendChild(el("code", null, stage.source));
        row.appendChild(source);
      }
      for (const id of stage.eliminations || []) {
        const limit = (payload.evidenceLimits || []).find((entry) => entry.id === id);
        const line = el("p", "recovery-note", `↳ ${t("limit")}: ${limit ? localized(limit, "title") : id}`);
        if (limit) line.title = localized(limit, "detail");
        row.appendChild(line);
      }
      stages.appendChild(row);
    }
    detail.appendChild(stages);

    if (family.pathRegex) {
      const pattern = el("p", "recovery-note");
      pattern.appendChild(document.createTextNode(`${t("pattern")}: `));
      pattern.appendChild(el("code", null, family.pathRegex));
      detail.appendChild(pattern);
    }
    if (family.stagesFrom) {
      const donor = block.families.find((row) => row.id === family.stagesFrom);
      detail.appendChild(el("p", "recovery-note", `${t("sharedStages")}: ${donor ? localized(donor, "label") : family.stagesFrom}`));
    }
    if (measured.samplePaths?.length) {
      detail.appendChild(el("p", "recovery-note", `${t("samples")}:`));
      const list = el("ul", "recovery-samples");
      for (const path of measured.samplePaths) {
        const row = el("li");
        row.appendChild(el("code", null, path));
        list.appendChild(row);
      }
      detail.appendChild(list);
    }
  }

  // --- page ---------------------------------------------------------------

  function render({ focus = null, scroll = false } = {}) {
    const body = document.querySelector("#recovery-body");
    if (!body) return;
    hideTip();
    body.textContent = "";
    const payload = STATE.payload;
    if (!payload) return;

    const header = el("header", "recovery-header");
    header.appendChild(el("h1", null, t("pageTitle")));
    header.appendChild(el("p", "recovery-note", t("intro")));
    body.appendChild(header);
    body.appendChild(renderOverview(payload));
    body.appendChild(renderTree(payload));
    const footer = el("p", "recovery-note recovery-footer");
    footer.appendChild(document.createTextNode(`${t("generated")} ${payload.generatedAt || "—"} · ${t("rebuild")}: `));
    footer.appendChild(el("code", null, "python -m scripts.webui.recovery.build_recovery"));
    body.appendChild(footer);

    const target = focus && body.querySelector(focus);
    if (target) {
      target.focus({ preventScroll: !scroll });
      if (scroll) {
        const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
        target.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
      }
    }
  }

  // The status is kept as a key plus detail so a locale change re-renders it.
  function setStatus(key, detail = "") {
    STATE.status = key ? { key, detail } : null;
    const status = document.querySelector("#recovery-status");
    if (!status) return;
    const message = key ? `${t(key)}${detail ? ` (${detail})` : ""}` : "";
    status.textContent = message;
    status.hidden = !message;
  }

  function ensureLoaded() {
    if (STATE.loaded) return Promise.resolve(STATE.payload);
    if (STATE.loading) return STATE.loading;
    window.WebUI?.showLoader?.("recovery");
    STATE.loading = fetch(DATA_URL)
      .then((res) => {
        if (res.status === 404) return null;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        const usable = payload && payload.schema === SCHEMA ? payload : null;
        STATE.payload = usable;
        STATE.loaded = true;
        STATE.loading = null;
        if (usable) setStatus(null);
        else if (payload) setStatus("schemaMismatch", payload.schema || "?");
        else setStatus("missing");
        render();
        return usable;
      })
      .catch((error) => {
        STATE.loading = null;
        setStatus("loadError", error.message);
        return null;
      })
      .finally(() => {
        window.WebUI?.hideLoader?.("recovery");
      });
    return STATE.loading;
  }

  function maybeLoad() {
    if (document.body.dataset.activeView === "recovery" || window.location.hash === "#recovery") {
      ensureLoaded();
    }
  }

  function init() {
    STATE.locale = normalizeLocale(window.WEBUI_UI_LOCALE || document.documentElement.lang);
    document.querySelectorAll(".view-tab").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.view === "recovery") setTimeout(maybeLoad, 0);
      });
    });
    window.addEventListener("hashchange", () => setTimeout(maybeLoad, 0));
    window.addEventListener("webui:view-changed", (event) => {
      if (event.detail?.view === "recovery") maybeLoad();
      else hideTip();
    });
    window.addEventListener("webui:ui-locale-changed", (event) => {
      STATE.locale = normalizeLocale(event.detail?.locale) || STATE.locale;
      if (STATE.status) setStatus(STATE.status.key, STATE.status.detail);
      render();
    });
    // Capture, because the page scrolls inside #recovery-app rather than on the
    // window: a bubbling listener would never see it and the tip would detach.
    window.addEventListener("scroll", hideTip, { passive: true, capture: true });
    maybeLoad();
  }

  init();
})();
