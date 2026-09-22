// Recovery progress page.
//
// Renders webui/data/recovery/index.json: how far the installed game data is
// understood, level by level and lane by lane, plus how much data sits behind
// each answer.
//
// The one rule this view enforces everywhere: a measured figure and a declared
// figure never look the same. Anything whose `evidence` is "declared" carries a
// visible marker and its own reason, and "framed and named" is never rendered
// as "understood".
(() => {
  const DATA_URL = "data/recovery/index.json";

  const TEXTS = {
    zh: {
      tab: "进度",
      pageTitle: "恢复进度",
      intro: "安装数据的理解程度，按层级与通道拆分。每个数字要么来自生成报告，要么被明确标记为声明。",
      measured: "实测",
      declared: "声明",
      measuredHint: "来自 reports/ 下的生成报告或已跟踪的通道索引。",
      declaredHint: "没有报告能提供该数字；悬停查看原因。",
      corpusTitle: "安装语料库",
      corpusFiles: "逻辑文件",
      corpusBytes: "总体量",
      corpusBlocks: "VFS 数据块类型",
      blocksTitle: "全部文件：一条进度条",
      blocksNote: "整个安装语料库作为一条条形，每一段是一个 VFS 数据块类型，宽度为字节占比（线性）。数据量与理解程度无关。",
      deepestLevel: "通道已记录的最深层级",
      depthTitle: "逐层拆解",
      depthNote: "同一条语料库，按层级拆开。",
      depthBlockTypes: "个数据块类型",
      depthUndocumented: "该层尚未记录",
      depthOfBytes: "的字节",
      depthOfFiles: "的文件",
      depthNone: "无",
      matrixTitle: "通道 × 层级",
      matrixNote: "左侧为实测数据量，右侧四格为该通道在每一层已记录的主题数。悬停查看明细。",
      levelsTitle: "四个层级",
      levelTopics: "已记录主题",
      levelLanes: "涉及通道",
      jsonTitle: "JsonData：已命名字节",
      jsonFamilies: "家族",
      jsonFullyNamed: "全部命名的家族",
      monoTitle: "MonoBehaviour 证据",
      monoClasses: "已命名类",
      monoObjects: "对象",
      monoFields: "字段路径",
      monoRefs: "已填充的引用字段解析到容器",
      monoClassification: "字段分类",
      monoTopClasses: "对象最多的类",
      monoNoSignal: "无类特异信号的游戏类",
      monoNoSignalMeans: "去掉引擎通用字段后，没有任何类特异证据被恢复的游戏类——即真实的“未理解”集合。",
      monoSignalKinds: "算作类特异信号的条件",
      monoUniversalExcluded: "已排除的通用字段",
      monoPublicExcluded: "已排除的公开引擎命名空间",
      monoUnnamedIncluded: "包含的未命名类",
      monoUnnamedClass: "（未命名类）",
      monoOfConsidered: "／共计",
      monoRange: "区间下限与上限",
      monoStrict: "严格计法",
      monoFloor: "宽松计法",
      monoHeadline: "主要读数",
      monoLooser: "更宽松的读数",
      monoBetween: "介于两者之间",
      monoBetweenByObjects: "对象数最多",
      monoBetweenByRefs: "未落到名字的引用最多",
      monoStrictTop: "严格集合中对象最多的类",
      monoFilledRefs: "个已填充引用",
      monoNamedRefs: "个落到名字",
      tableKeysTitle: "表键连接",
      tableKeysTables: "表",
      tableKeysDistinct: "不同键",
      tableKeysConsidered: "考察的字符串字段",
      openTitle: "静态数据无法触及",
      openNote: "这些不是待办项，而是已记录的排除结论。",
      sourcesTitle: "数据来源",
      rebuild: "重建命令",
      generatedAt: "生成时间",
      files: "文件",
      bytes: "字节",
      topics: "主题",
      level: "层",
      lane: "通道",
      notReached: "该层尚无结论",
      noBlock: "没有独立数据块",
      ownedElsewhere: "由其他文档拥有",
      noTopics: "此目录下未记录",
      why: "为何是声明",
      loadError: "无法加载恢复进度数据。请先运行构建命令。",
      missing: "尚未生成恢复进度数据。",
      namedShare: "已命名字节占比",
      openItemsHere: "此处的排除结论",
    },
    en: {
      tab: "Progress",
      pageTitle: "Recovery Progress",
      intro: "How far the installed game data is understood, broken down by level and by lane. Every figure is either read from a generated report or explicitly marked as a declaration.",
      measured: "measured",
      declared: "declared",
      measuredHint: "Read from a generated report under reports/ or from the tracked lane index.",
      declaredHint: "No report carries this figure; hover for the reason.",
      corpusTitle: "Installed corpus",
      corpusFiles: "logical files",
      corpusBytes: "total payload",
      corpusBlocks: "VFS block types",
      blocksTitle: "Every file, as one progress bar",
      blocksNote: "The whole installed corpus as a single bar, one section per VFS block type, each sized by its linear share of total bytes. Volume says nothing about how well the data is understood.",
      deepestLevel: "Deepest level documented for its lane",
      depthTitle: "Broken down level by level",
      depthNote: "The same corpus, split by level.",
      depthBlockTypes: "block types",
      depthUndocumented: "No conclusion recorded at this level",
      depthOfBytes: "of bytes",
      depthOfFiles: "of files",
      depthNone: "none",
      matrixTitle: "Lane × level",
      matrixNote: "Left is measured data volume; the four cells are how many topics that lane has recorded at each level. Hover for detail.",
      levelsTitle: "The four levels",
      levelTopics: "documented topics",
      levelLanes: "lanes with a conclusion",
      jsonTitle: "JsonData: named bytes",
      jsonFamilies: "families",
      jsonFullyNamed: "families fully named",
      monoTitle: "MonoBehaviour evidence",
      monoClasses: "named classes",
      monoObjects: "objects",
      monoFields: "field paths",
      monoRefs: "filled reference fields resolve to a container",
      monoClassification: "Fields by classification",
      monoTopClasses: "Largest classes by object count",
      monoNoSignal: "Game classes with no recovered class-specific signal",
      monoNoSignalMeans: "Game-specific classes for which, once the universal engine fields are set aside, nothing class-specific has been recovered — the honest not-understood set.",
      monoSignalKinds: "What counts as class-specific signal",
      monoUniversalExcluded: "Universal engine fields excluded first",
      monoPublicExcluded: "Public engine namespaces excluded",
      monoUnnamedIncluded: "Unnamed classes included",
      monoUnnamedClass: "(unnamed class)",
      monoOfConsidered: "of",
      monoRange: "Range, lower and upper bound",
      monoStrict: "Strict",
      monoFloor: "Floor",
      monoHeadline: "headline",
      monoLooser: "looser reading",
      monoBetween: "Between the two bounds",
      monoBetweenByObjects: "Most objects",
      monoBetweenByRefs: "Most references landing on nothing named",
      monoStrictTop: "Largest classes in the strict set",
      monoFilledRefs: "filled references",
      monoNamedRefs: "land on a name",
      tableKeysTitle: "Table-key joins",
      tableKeysTables: "tables",
      tableKeysDistinct: "distinct keys",
      tableKeysConsidered: "string fields considered",
      openTitle: "Known unreachable from static data",
      openNote: "These are recorded eliminations, not a to-do list.",
      sourcesTitle: "Sources",
      rebuild: "Rebuild with",
      generatedAt: "Generated",
      files: "files",
      bytes: "bytes",
      topics: "topics",
      level: "Level",
      lane: "Lane",
      notReached: "No conclusion recorded at this level",
      noBlock: "no block of its own",
      ownedElsewhere: "documented elsewhere",
      noTopics: "not documented in this directory",
      why: "Why this is a declaration",
      loadError: "Recovery progress data could not be loaded. Run the build command first.",
      missing: "Recovery progress data has not been generated yet.",
      namedShare: "named-byte share",
      openItemsHere: "Recorded eliminations here",
    },
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

  const STATE = {
    payload: null,
    loading: null,
    loaded: false,
    locale: "zh",
  };

  function normalizeLocale(value) {
    const raw = String(value || "").toLowerCase();
    return raw.startsWith("en") ? "en" : "zh";
  }

  function t(key) {
    const bundle = TEXTS[STATE.locale] || TEXTS.en;
    return bundle[key] || TEXTS.en[key] || key;
  }

  function localized(node, key) {
    if (!node) return "";
    if (STATE.locale === "zh") {
      const zhKey = `${key}Zh`;
      if (node[zhKey]) return node[zhKey];
    }
    return node[key] || "";
  }

  const NUM = new Intl.NumberFormat("en-US");

  function num(value) {
    return Number.isFinite(value) ? NUM.format(value) : "—";
  }

  function bytes(value) {
    if (!Number.isFinite(value)) return "—";
    if (value >= 1e9) return `${(value / 1e9).toFixed(2)} GB`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(1)} MB`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(1)} kB`;
    return `${value} B`;
  }

  function pct(value, digits = 1) {
    if (!Number.isFinite(value)) return "—";
    return `${(value * 100).toFixed(digits)}%`;
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  // --- tooltip ------------------------------------------------------------

  let tooltip = null;

  function ensureTooltip() {
    if (tooltip && tooltip.isConnected) return tooltip;
    tooltip = el("div", "recovery-tip");
    tooltip.hidden = true;
    tooltip.setAttribute("role", "tooltip");
    document.body.appendChild(tooltip);
    return tooltip;
  }

  function hideTip() {
    if (tooltip) tooltip.hidden = true;
  }

  function showTip(anchor, lines) {
    const tip = ensureTooltip();
    tip.textContent = "";
    for (const line of lines) {
      if (!line) continue;
      if (typeof line === "string") {
        tip.appendChild(el("div", "recovery-tip-line", line));
      } else {
        const row = el("div", `recovery-tip-line${line.strong ? " is-strong" : ""}${line.muted ? " is-muted" : ""}`);
        row.textContent = line.text;
        tip.appendChild(row);
      }
    }
    tip.hidden = false;
    const rect = anchor.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();
    let left = rect.left + rect.width / 2 - tipRect.width / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tipRect.width - 8));
    let top = rect.top - tipRect.height - 8;
    if (top < 8) top = rect.bottom + 8;
    tip.style.left = `${Math.round(left + window.scrollX)}px`;
    tip.style.top = `${Math.round(top + window.scrollY)}px`;
  }

  // Hover and keyboard focus both reveal the detail, so the graph stays usable
  // without a pointer.
  function bindTip(node, linesFn) {
    node.tabIndex = 0;
    const show = () => showTip(node, linesFn().filter(Boolean));
    node.addEventListener("mouseenter", show);
    node.addEventListener("focus", show);
    node.addEventListener("mouseleave", hideTip);
    node.addEventListener("blur", hideTip);
    return node;
  }

  function evidenceChip(kind) {
    const chip = el("span", `recovery-evidence is-${kind}`, kind === "declared" ? t("declared") : t("measured"));
    bindTip(chip, () => [kind === "declared" ? t("declaredHint") : t("measuredHint")]);
    return chip;
  }

  function section(titleText, noteText) {
    const wrap = el("section", "recovery-section");
    const head = el("header", "recovery-section-head");
    head.appendChild(el("h2", null, titleText));
    if (noteText) head.appendChild(el("p", "recovery-note", noteText));
    wrap.appendChild(head);
    return wrap;
  }

  function statTile(value, label, extra) {
    const tile = el("div", "recovery-stat");
    tile.appendChild(el("span", "recovery-stat-value", value));
    tile.appendChild(el("span", "recovery-stat-label", label));
    if (extra) tile.appendChild(extra);
    return tile;
  }

  // --- sections -----------------------------------------------------------

  function renderHeader(payload) {
    const head = el("header", "recovery-header");
    head.appendChild(el("h1", null, t("pageTitle")));
    head.appendChild(el("p", "recovery-intro", t("intro")));

    const totals = payload.corpus?.totals || {};
    const stats = el("div", "recovery-stat-row");
    stats.appendChild(statTile(bytes(totals.bytes), t("corpusBytes"), evidenceChip("measured")));
    stats.appendChild(statTile(num(totals.files), t("corpusFiles")));
    stats.appendChild(statTile(num(totals.blockTypes), t("corpusBlocks")));
    head.appendChild(stats);

    const caveats = el("div", "recovery-caveats");
    for (const key of ["namedIsNotUnderstood", "documentedTopicsAreNotBytes"]) {
      const caveat = payload.caveats?.[key];
      if (!caveat) continue;
      caveats.appendChild(el("p", "recovery-caveat", localized(caveat, "text")));
    }
    head.appendChild(caveats);
    return head;
  }

  // The whole corpus as one segmented progress bar. `segments` are the rows to
  // draw, `total` the denominator the bar is scaled against, so several bars in
  // different sections stay directly comparable. A `remainder` segment makes the
  // uncounted part of a level's bar visible instead of implying a short bar is
  // a small corpus.
  function segmentedBar(segments, total, { remainder = null, height = "" } = {}) {
    const bar = el("div", "recovery-segbar");
    if (height) bar.style.height = height;
    const denominator = total || 1;
    for (const segment of segments || []) {
      const piece = el("div", "recovery-segbar-piece");
      piece.style.width = `${Math.max((segment.bytes / denominator) * 100, 0.18)}%`;
      piece.style.background = LANE_COLORS[segment.lane] || "var(--accent-2)";
      bindTip(piece, () => segment.tip());
      bar.appendChild(piece);
    }
    if (remainder && remainder.bytes > 0) {
      const piece = el("div", "recovery-segbar-piece is-remainder");
      piece.style.width = `${Math.max((remainder.bytes / denominator) * 100, 0.18)}%`;
      bindTip(piece, () => remainder.tip());
      bar.appendChild(piece);
    }
    return bar;
  }

  function blockSegments(blocks, laneById, total) {
    return (blocks || []).map((block) => ({
      lane: block.lane,
      bytes: block.bytes,
      tip: () => {
        const lane = laneById.get(block.lane);
        const lines = [
          { text: block.blockType, strong: true },
          `${t("lane")}: ${lane ? localized(lane, "label") : block.lane}`,
          `${num(block.files)} ${t("files")} · ${bytes(block.bytes)} · ${pct(block.bytes / (total || 1), 2)}`,
        ];
        if (Number.isFinite(block.laneDeepestDocumentedLevel)) {
          lines.push(`${t("deepestLevel")}: L${block.laneDeepestDocumentedLevel}`);
        }
        for (const family of block.topPathFamilies || []) {
          lines.push({ text: `${family.pathFamily} · ${num(family.files)}`, muted: true });
        }
        return lines;
      },
    }));
  }

  function renderBlocks(payload) {
    const wrap = section(t("blocksTitle"), t("blocksNote"));
    const blocks = payload.corpus?.blocks || [];
    const total = payload.corpus?.totals?.bytes || 1;
    const laneById = new Map((payload.lanes || []).map((lane) => [lane.id, lane]));

    wrap.appendChild(segmentedBar(blockSegments(blocks, laneById, total), total, { height: "26px" }));

    // The numbers stay readable as text; 22 separate bars only repeated the one
    // bar above at worse precision.
    const legend = el("div", "recovery-legend");
    for (const block of blocks) {
      const row = el("div", "recovery-legend-row");
      const swatch = el("span", "recovery-swatch");
      swatch.style.background = LANE_COLORS[block.lane] || "var(--accent-2)";
      row.appendChild(swatch);
      row.appendChild(el("span", "recovery-legend-name", block.blockType));
      row.appendChild(el("span", "recovery-legend-value", bytes(block.bytes)));
      row.appendChild(el("span", "recovery-legend-share", pct(block.bytes / total, 1)));
      row.appendChild(el("span", "recovery-legend-files", `${num(block.files)} ${t("files")}`));
      bindTip(row, () => blockSegments([block], laneById, total)[0].tip());
      legend.appendChild(row);
    }
    wrap.appendChild(legend);
    return wrap;
  }

  // The same corpus, broken down level by level. Each level draws only the
  // block types whose lane is documented at that level, against the same total,
  // with the rest shown as an explicit undocumented remainder.
  function renderLevelDepth(payload) {
    const rows = payload.corpus?.levelDepth;
    if (!rows?.length) return null;
    const basis = payload.caveats?.corpusLevelDepth;
    const wrap = section(t("depthTitle"), localized(basis, "text") || t("depthNote"));
    const total = payload.corpus?.totals?.bytes || 1;
    const blocks = payload.corpus?.blocks || [];
    const laneById = new Map((payload.lanes || []).map((lane) => [lane.id, lane]));
    const levels = payload.levels || [];
    const byBlockType = new Map(blocks.map((block) => [block.blockType, block]));

    const grid = el("div", "recovery-depth");
    for (const row of rows) {
      const level = levels.find((entry) => entry.level === row.level);
      const line = el("div", "recovery-depth-row");

      const label = el("div", "recovery-depth-label");
      label.appendChild(el("span", "recovery-level-num", `L${row.level}`));
      label.appendChild(el("span", "recovery-depth-name", level ? level.name : ""));
      bindTip(label, () => [
        { text: `${t("level")} ${row.level}${level ? ` — ${level.name}` : ""}`, strong: true },
        level ? level.question : "",
      ]);
      line.appendChild(label);

      const counted = row.segments
        .map((segment) => byBlockType.get(segment.blockType))
        .filter(Boolean);
      const remainderBytes = Math.max(total - row.bytes, 0);
      const missing = blocks.filter((block) => !row.blockTypes.includes(block.blockType));
      const bar = segmentedBar(blockSegments(counted, laneById, total), total, {
        remainder: {
          bytes: remainderBytes,
          tip: () => [
            { text: t("depthUndocumented"), strong: true },
            `${bytes(remainderBytes)} · ${pct(remainderBytes / total, 1)}`,
            missing.length ? missing.map((block) => block.blockType).join(", ") : "",
            { text: localized(basis, "text") || "", muted: true },
          ],
        },
      });
      line.appendChild(bar);

      const status = el("div", "recovery-depth-status");
      status.appendChild(
        el(
          "span",
          "recovery-depth-chip",
          `${num(row.blockTypesCounted)} / ${num(row.blockTypesTotal)} ${t("depthBlockTypes")}`,
        ),
      );
      status.appendChild(el("span", "recovery-depth-pct", pct(row.byteShare, 0)));
      bindTip(status, () => [
        { text: `${t("level")} ${row.level}`, strong: true },
        `${bytes(row.bytes)} · ${pct(row.byteShare, 1)} ${t("depthOfBytes")}`,
        `${num(row.files)} ${t("files")} · ${pct(row.fileShare, 1)} ${t("depthOfFiles")}`,
        row.blockTypes.length ? row.blockTypes.join(", ") : t("depthNone"),
        { text: localized(basis, "text") || "", muted: true },
      ]);
      line.appendChild(status);

      grid.appendChild(line);
    }
    wrap.appendChild(grid);
    return wrap;
  }

  function renderMatrix(payload) {
    const wrap = section(t("matrixTitle"), t("matrixNote"));
    const lanes = payload.lanes || [];
    const levels = payload.levels || [];
    const maxBytes = Math.max(1, ...lanes.map((lane) => lane.volume?.bytes || 0));

    const grid = el("div", "recovery-matrix");

    const head = el("div", "recovery-matrix-row is-head");
    head.appendChild(el("div", "recovery-matrix-lane", t("lane")));
    head.appendChild(el("div", "recovery-matrix-volume", t("bytes")));
    const heads = el("div", "recovery-matrix-levels");
    for (const level of levels) {
      const cell = el("div", "recovery-matrix-levelhead", `L${level.level}`);
      bindTip(cell, () => [
        { text: `${t("level")} ${level.level} — ${level.name}`, strong: true },
        level.question,
      ]);
      heads.appendChild(cell);
    }
    head.appendChild(heads);
    grid.appendChild(head);

    for (const lane of lanes) {
      const row = el("div", "recovery-matrix-row");

      const name = el("div", "recovery-matrix-lane");
      const swatch = el("span", "recovery-swatch");
      swatch.style.background = LANE_COLORS[lane.id] || "var(--accent-2)";
      name.appendChild(swatch);
      name.appendChild(el("span", "recovery-matrix-lane-label", localized(lane, "label")));
      if (!lane.documentedHere) name.appendChild(el("span", "recovery-flag", "↗"));
      bindTip(name, () => {
        const lines = [
          { text: localized(lane, "label"), strong: true },
          localized(lane, "blurb"),
        ];
        if (lane.noBlockOfItsOwn) lines.push({ text: t("noBlock"), muted: true });
        if (lane.ownedElsewhere) {
          lines.push({ text: `${t("ownedElsewhere")}: ${lane.ownedElsewhere}`, muted: true });
        }
        return lines;
      });
      row.appendChild(name);

      const volume = el("div", "recovery-matrix-volume");
      const track = el("div", "recovery-bar-track");
      const fill = el("div", "recovery-bar-fill");
      const laneBytes = lane.volume?.bytes || 0;
      fill.style.width = laneBytes ? `${Math.max((laneBytes / maxBytes) * 100, 1.2)}%` : "0%";
      fill.style.background = LANE_COLORS[lane.id] || "var(--accent-2)";
      track.appendChild(fill);
      volume.appendChild(track);
      volume.appendChild(el("span", "recovery-matrix-bytes", laneBytes ? bytes(laneBytes) : "—"));
      bindTip(volume, () => [
        { text: localized(lane, "label"), strong: true },
        laneBytes
          ? `${bytes(laneBytes)} · ${num(lane.volume.files)} ${t("files")}`
          : t("noBlock"),
        lane.volume?.blockTypes?.length ? lane.volume.blockTypes.join(", ") : "",
      ]);
      row.appendChild(volume);

      const cells = el("div", "recovery-matrix-levels");
      for (const entry of lane.documentedTopics?.perLevel || []) {
        const openHere = (lane.openItems || []).filter((item) => item.level === entry.level);
        const cell = el(
          "div",
          `recovery-cell${entry.reached ? " is-reached" : ""}${openHere.length ? " has-open" : ""}`,
        );
        cell.appendChild(el("span", "recovery-cell-count", entry.reached ? String(entry.topics) : "·"));
        bindTip(cell, () => {
          const level = levels.find((row2) => row2.level === entry.level);
          const lines = [
            { text: `${localized(lane, "label")} · ${t("level")} ${entry.level}`, strong: true },
          ];
          if (level) lines.push({ text: level.question, muted: true });
          if (entry.reached) {
            lines.push(`${entry.topics} ${t("topics")}`);
            const topics = (lane.documentedTopics?.topics || []).filter(
              (topic) => topic.level === entry.level,
            );
            for (const topic of topics) lines.push({ text: `• ${topic.file}`, muted: true });
          } else {
            lines.push(lane.documentedHere ? t("notReached") : t("noTopics"));
          }
          if (openHere.length) {
            lines.push({ text: t("openItemsHere"), strong: true });
            for (const item of openHere) lines.push({ text: `✗ ${localized(item, "title")}`, muted: true });
          }
          return lines;
        });
        cells.appendChild(cell);
      }
      row.appendChild(cells);
      grid.appendChild(row);
    }

    wrap.appendChild(grid);
    return wrap;
  }

  function renderLevels(payload) {
    const wrap = section(t("levelsTitle"));
    const cards = el("div", "recovery-levels");
    const laneById = new Map((payload.lanes || []).map((lane) => [lane.id, lane]));
    for (const level of payload.levels || []) {
      const card = el("article", "recovery-level-card");
      card.appendChild(el("span", "recovery-level-num", `L${level.level}`));
      card.appendChild(el("h3", null, level.name));
      card.appendChild(el("p", "recovery-level-q", level.question));
      const meta = el("div", "recovery-level-meta");
      meta.appendChild(el("span", null, `${level.topics} ${t("levelTopics")}`));
      meta.appendChild(
        el("span", null, `${(level.lanesWithAtLeastOneTopic || []).length} ${t("levelLanes")}`),
      );
      card.appendChild(meta);
      const laneList = el("div", "recovery-level-lanes");
      for (const id of level.lanesWithAtLeastOneTopic || []) {
        const chip = el("span", "recovery-lane-chip", localized(laneById.get(id), "label") || id);
        chip.style.borderColor = LANE_COLORS[id] || "var(--border)";
        laneList.appendChild(chip);
      }
      card.appendChild(laneList);
      for (const item of level.openItems || []) {
        const open = el("p", "recovery-level-open", `✗ ${localized(item, "title")}`);
        bindTip(open, () => [
          { text: localized(item, "title"), strong: true },
          localized(item, "detail"),
          { text: item.owner, muted: true },
        ]);
        card.appendChild(open);
      }
      cards.appendChild(card);
    }
    wrap.appendChild(cards);
    return wrap;
  }

  function renderJsonData(payload) {
    const data = payload.jsonData;
    if (!data) return null;
    const wrap = section(t("jsonTitle"), localized(payload.caveats?.namedIsNotUnderstood, "text"));
    const totals = data.totals || {};

    const stats = el("div", "recovery-stat-row");
    stats.appendChild(statTile(pct(totals.namedShare, 2), t("namedShare"), evidenceChip("measured")));
    stats.appendChild(
      statTile(`${num(totals.familiesFullyNamed)} / ${num(totals.families)}`, t("jsonFullyNamed")),
    );
    stats.appendChild(statTile(num(totals.files), t("corpusFiles")));
    stats.appendChild(statTile(bytes(totals.bytes), t("corpusBytes")));
    wrap.appendChild(stats);

    const list = el("div", "recovery-families");
    for (const family of data.families || []) {
      const row = el("div", "recovery-family-row");
      row.appendChild(el("span", "recovery-family-name", family.family));
      const track = el("div", "recovery-bar-track");
      const fill = el("div", "recovery-bar-fill is-named");
      fill.style.width = `${Math.min(family.namedShare * 100, 100)}%`;
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el("span", "recovery-family-value", pct(family.namedShare, 1)));
      bindTip(row, () => {
        const lines = [
          { text: family.family, strong: true },
          `${num(family.files)} ${t("files")} · ${bytes(family.bytes)}`,
          `${bytes(family.namedBytes)} ${t("namedShare")}`,
        ];
        if (family.unnamedBytes) lines.push(`${bytes(family.unnamedBytes)} unnamed`);
        for (const bucket of family.buckets || []) {
          lines.push({ text: `${bucket.status} · ${num(bucket.files)}`, muted: true });
        }
        lines.push({ text: data.method, muted: true });
        return lines;
      });
      list.appendChild(row);
    }
    wrap.appendChild(list);
    return wrap;
  }

  // A bounded bar chart of `{scriptClass, objects, filledReferenceFields}` rows.
  function classBars(rows, valueKey, limit = 12) {
    const shown = (rows || []).slice(0, limit);
    const max = Math.max(1, ...shown.map((row) => row[valueKey] || 0));
    const list = el("div", "recovery-signal-list");
    for (const entry of shown) {
      const row = el("div", "recovery-family-row");
      row.appendChild(el("span", "recovery-family-name", entry.scriptClass || t("monoUnnamedClass")));
      const track = el("div", "recovery-bar-track");
      const fill = el("div", "recovery-bar-fill is-open");
      fill.style.width = `${Math.max(((entry[valueKey] || 0) / max) * 100, 0.8)}%`;
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el("span", "recovery-family-value", num(entry[valueKey])));
      bindTip(row, () => [
        { text: entry.scriptClass || t("monoUnnamedClass"), strong: true },
        `${num(entry.objects)} ${t("monoObjects")}`,
        Number.isFinite(entry.filledReferenceFields)
          ? `${num(entry.filledReferenceFields)} ${t("monoFilledRefs")} · ${num(entry.referenceFieldsLandingOnAName)} ${t("monoNamedRefs")}`
          : "",
      ]);
      list.appendChild(row);
    }
    return list;
  }

  // The not-understood set, published as a measured range. The strict bound is
  // the headline because it is what the evidence supports; the floor is shown
  // beside it so the range is honest in both directions, never one bound alone.
  function renderNoSignal(signal) {
    const panel = el("div", "recovery-open-panel");
    const head = el("div", "recovery-declared-head");
    head.appendChild(el("strong", null, t("monoNoSignal")));
    head.appendChild(evidenceChip(signal.evidence === "declared" ? "declared" : "measured"));
    panel.appendChild(head);

    const strict = signal.strict || {};
    const floor = signal.floor || {};
    const considered = signal.classesConsidered || 0;

    panel.appendChild(
      el(
        "p",
        "recovery-declared-value",
        `${num(floor.classes)} – ${num(strict.classes)} ${t("monoOfConsidered")} ${num(considered)}`,
      ),
    );
    panel.appendChild(el("p", "recovery-declared-detail", t("monoNoSignalMeans")));

    // Range bar: the floor is the certain part, the span up to the strict bound
    // is the reading the reference evidence does not support.
    const rangeTrack = el("div", "recovery-range-track");
    const floorFill = el("div", "recovery-range-floor");
    floorFill.style.width = `${Math.min(((floor.classes || 0) / (considered || 1)) * 100, 100)}%`;
    const spanFill = el("div", "recovery-range-span");
    spanFill.style.width = `${Math.max(
      Math.min((((strict.classes || 0) - (floor.classes || 0)) / (considered || 1)) * 100, 100),
      0,
    )}%`;
    rangeTrack.appendChild(floorFill);
    rangeTrack.appendChild(spanFill);
    bindTip(rangeTrack, () => [
      { text: t("monoRange"), strong: true },
      `${t("monoStrict")}: ${num(strict.classes)} ${t("monoClasses")} · ${num(strict.objects)} ${t("monoObjects")} · ${pct(strict.shareOfClassesConsidered, 0)}`,
      `${t("monoFloor")}: ${num(floor.classes)} ${t("monoClasses")} · ${num(floor.objects)} ${t("monoObjects")} · ${pct(floor.shareOfClassesConsidered, 0)}`,
      { text: signal.whyBoundsDiffer, muted: true },
    ]);
    panel.appendChild(rangeTrack);

    const bounds = el("div", "recovery-stat-row");
    const strictTile = statTile(
      `${num(strict.classes)} · ${pct(strict.shareOfClassesConsidered, 0)}`,
      `${t("monoStrict")} — ${t("monoHeadline")}`,
    );
    bindTip(strictTile, () => [
      { text: t("monoStrict"), strong: true },
      strict.referenceRule || "",
      `${num(strict.objects)} ${t("monoObjects")}`,
    ]);
    bounds.appendChild(strictTile);
    const floorTile = statTile(
      `${num(floor.classes)} · ${pct(floor.shareOfClassesConsidered, 0)}`,
      `${t("monoFloor")} — ${t("monoLooser")}`,
    );
    bindTip(floorTile, () => [
      { text: t("monoFloor"), strong: true },
      floor.referenceRule || "",
      `${num(floor.objects)} ${t("monoObjects")}`,
    ]);
    bounds.appendChild(floorTile);
    panel.appendChild(bounds);

    panel.appendChild(el("p", "recovery-declared-detail is-why", signal.whyBoundsDiffer || ""));

    panel.appendChild(el("p", "recovery-criteria-head", t("monoSignalKinds")));
    const criteria = el("ul", "recovery-criteria");
    for (const kind of signal.sharedSignalKinds || []) criteria.appendChild(el("li", null, kind));
    if (strict.referenceRule) {
      criteria.appendChild(el("li", null, `${t("monoStrict")}: ${strict.referenceRule}`));
    }
    if (floor.referenceRule) {
      criteria.appendChild(el("li", null, `${t("monoFloor")}: ${floor.referenceRule}`));
    }
    panel.appendChild(criteria);

    const notes = el("p", "recovery-declared-why");
    notes.textContent = [
      `${t("monoUniversalExcluded")}: ${(signal.universalFieldsExcluded || []).join(", ")}`,
      `${t("monoPublicExcluded")} (${num(signal.publicEngineClassesExcluded)}): ${(signal.publicNamespacePrefixes || []).join(", ")}`,
      `${t("monoUnnamedIncluded")}: ${num(strict.unnamedClasses)}`,
    ].join(" — ");
    panel.appendChild(notes);

    const between = signal.betweenBounds;
    if (between) {
      const block = el("div", "recovery-between");
      block.appendChild(
        el(
          "p",
          "recovery-criteria-head",
          `${t("monoBetween")}: ${num(between.classes)} ${t("monoClasses")} · ${num(between.objects)} ${t("monoObjects")}`,
        ),
      );
      block.appendChild(el("p", "recovery-declared-detail", between.means || ""));
      if (between.topClassesByObjects?.length) {
        block.appendChild(el("p", "recovery-subhead", t("monoBetweenByObjects")));
        block.appendChild(classBars(between.topClassesByObjects, "objects"));
      }
      if (between.topClassesByUnnamedReferences?.length) {
        block.appendChild(el("p", "recovery-subhead", t("monoBetweenByRefs")));
        block.appendChild(classBars(between.topClassesByUnnamedReferences, "filledReferenceFields"));
      }
      panel.appendChild(block);
    }

    if (strict.topClassesByObjects?.length) {
      panel.appendChild(el("p", "recovery-subhead", t("monoStrictTop")));
      panel.appendChild(classBars(strict.topClassesByObjects, "objects"));
    }

    return panel;
  }

  function renderMonoBehaviour(payload) {
    const mono = payload.monoBehaviour;
    if (!mono) return null;
    const wrap = section(t("monoTitle"));

    const stats = el("div", "recovery-stat-row");
    stats.appendChild(statTile(num(mono.classes), t("monoClasses"), evidenceChip("measured")));
    stats.appendChild(statTile(num(mono.objectsSwept), t("monoObjects")));
    stats.appendChild(statTile(num(mono.fieldPaths), t("monoFields")));
    const refTile = statTile(
      `${num(mono.referenceFieldsResolvingToContainer)} / ${num(mono.referenceFieldsFilled)}`,
      t("monoRefs"),
    );
    bindTip(refTile, () => [
      { text: t("monoRefs"), strong: true },
      `${num(mono.referenceFields)} reference fields recorded, ${num(mono.referenceFieldsFilled)} ever filled`,
      `${num(mono.referenceFieldsWithUnresolvedContainer)} filled fields with an unresolved container`,
    ]);
    stats.appendChild(refTile);
    wrap.appendChild(stats);

    // The honest not-understood set. It is measured, and it is given the most
    // prominent block in this section on purpose: what is open must read as
    // loudly as what is closed.
    const signal = mono.noClassSpecificSignal;
    if (signal) {
      wrap.appendChild(renderNoSignal(signal));
    }

    const classification = mono.fieldsByClassification || {};
    const maxFields = Math.max(1, ...Object.values(classification));
    const chart = el("div", "recovery-classification");
    chart.appendChild(el("h3", "recovery-subhead", t("monoClassification")));
    for (const [name, count] of Object.entries(classification)) {
      const row = el("div", "recovery-family-row");
      row.appendChild(el("span", "recovery-family-name", name));
      const track = el("div", "recovery-bar-track");
      const fill = el("div", "recovery-bar-fill is-classification");
      fill.style.width = `${Math.max((count / maxFields) * 100, 0.8)}%`;
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el("span", "recovery-family-value", num(count)));
      bindTip(row, () => [
        { text: name, strong: true },
        `${num(count)} ${t("monoFields")} · ${pct(count / (mono.fieldPaths || 1), 1)}`,
      ]);
      chart.appendChild(row);
    }
    wrap.appendChild(chart);

    const top = el("div", "recovery-classification");
    top.appendChild(el("h3", "recovery-subhead", t("monoTopClasses")));
    const maxObjects = Math.max(1, ...(mono.topClassesByObjects || []).map((row) => row.objects));
    for (const entry of mono.topClassesByObjects || []) {
      const row = el("div", "recovery-family-row");
      row.appendChild(el("span", "recovery-family-name", entry.scriptClass || "—"));
      const track = el("div", "recovery-bar-track");
      const fill = el("div", "recovery-bar-fill is-classification");
      fill.style.width = `${Math.max((entry.objects / maxObjects) * 100, 0.8)}%`;
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el("span", "recovery-family-value", num(entry.objects)));
      bindTip(row, () => [
        { text: entry.scriptClass || "—", strong: true },
        `${num(entry.objects)} ${t("monoObjects")}`,
        `${num(entry.fieldPaths)} ${t("monoFields")} · ${num(entry.fieldsBeyondBase)} beyond the engine base fields`,
      ]);
      top.appendChild(row);
    }
    wrap.appendChild(top);

    const keys = payload.tableKeys;
    if (keys) {
      const keyWrap = el("div", "recovery-classification");
      keyWrap.appendChild(el("h3", "recovery-subhead", t("tableKeysTitle")));
      const keyStats = el("div", "recovery-stat-row");
      keyStats.appendChild(statTile(num(keys.keyOwnership?.tables), t("tableKeysTables")));
      keyStats.appendChild(statTile(num(keys.keyOwnership?.distinctKeys), t("tableKeysDistinct")));
      keyStats.appendChild(statTile(num(keys.stringFieldsConsidered), t("tableKeysConsidered")));
      keyWrap.appendChild(keyStats);
      const statuses = el("div", "recovery-chips");
      for (const [status, count] of Object.entries(keys.byStatus || {})) {
        statuses.appendChild(el("span", "recovery-lane-chip", `${status} · ${num(count)}`));
      }
      keyWrap.appendChild(statuses);
      keyWrap.appendChild(el("p", "recovery-note", keys.evidenceBoundary || ""));
      wrap.appendChild(keyWrap);
    }

    return wrap;
  }

  function renderOpen(payload) {
    const open = payload.openItems;
    if (!open) return null;
    const wrap = section(t("openTitle"), t("openNote"));
    const head = el("div", "recovery-declared-head");
    head.appendChild(evidenceChip("declared"));
    wrap.appendChild(head);
    const list = el("div", "recovery-open-list");
    for (const item of open.items || []) {
      const card = el("article", "recovery-open-card");
      const title = el("h3", null, localized(item, "title"));
      card.appendChild(title);
      card.appendChild(el("p", "recovery-open-detail", localized(item, "detail")));
      const meta = el("p", "recovery-open-meta", `${t("level")} ${item.level} · ${item.owner}`);
      card.appendChild(meta);
      list.appendChild(card);
    }
    wrap.appendChild(list);
    wrap.appendChild(el("p", "recovery-declared-why", `${t("why")}: ${open.why}`));
    return wrap;
  }

  function renderSources(payload) {
    const wrap = section(t("sourcesTitle"));
    const list = el("ul", "recovery-sources");
    for (const source of payload.sources || []) {
      const row = el("li", null);
      row.appendChild(el("code", null, source.path));
      row.appendChild(el("span", "recovery-source-meta", `${bytes(source.bytes)} · ${source.modified}`));
      list.appendChild(row);
    }
    wrap.appendChild(list);
    const cmd = el("p", "recovery-note");
    cmd.appendChild(el("span", null, `${t("rebuild")}: `));
    cmd.appendChild(el("code", null, "python -m scripts.webui.recovery.build_recovery"));
    wrap.appendChild(cmd);
    wrap.appendChild(el("p", "recovery-note", `${t("generatedAt")}: ${payload.generatedAt || "—"}`));
    return wrap;
  }

  function render() {
    const body = document.querySelector("#recovery-body");
    if (!body) return;
    hideTip();
    body.textContent = "";
    const payload = STATE.payload;
    if (!payload) return;
    body.appendChild(renderHeader(payload));
    // One bar for the whole corpus, then the same corpus level by level, then
    // the per-lane detail behind those two summaries.
    body.appendChild(renderBlocks(payload));
    const depth = renderLevelDepth(payload);
    if (depth) body.appendChild(depth);
    body.appendChild(renderMatrix(payload));
    body.appendChild(renderLevels(payload));
    const json = renderJsonData(payload);
    if (json) body.appendChild(json);
    const mono = renderMonoBehaviour(payload);
    if (mono) body.appendChild(mono);
    const open = renderOpen(payload);
    if (open) body.appendChild(open);
    body.appendChild(renderSources(payload));
  }

  function setStatus(message) {
    const status = document.querySelector("#recovery-status");
    if (!status) return;
    status.textContent = message || "";
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
        STATE.payload = payload;
        STATE.loaded = true;
        STATE.loading = null;
        setStatus(payload ? "" : t("missing"));
        render();
        return payload;
      })
      .catch((error) => {
        STATE.loading = null;
        setStatus(`${t("loadError")} (${error.message})`);
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
      render();
    });
    // Capture, because the page scrolls inside #recovery-app rather than on the
    // window: a bubbling listener would never see it and the tip would detach.
    window.addEventListener("scroll", hideTip, { passive: true, capture: true });
    maybeLoad();
  }

  init();
})();
