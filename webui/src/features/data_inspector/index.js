// Decoded datasets: one source of the Data page's Files mode. The page
// controller in stores.js owns the list shell (sources, facet filters,
// virtualized list, pager, deep links) and uses WebUI.decodedInspector for this
// source's catalog, matching, ordering, row markup and record viewer.
//
// The record viewer is one general decoded-record viewer. It is deliberately
// schema-agnostic -- no decoder-specific field list is taught to the frontend.
// The record's own structure is preserved exactly as published, and semantics
// are layered on top of it as annotations:
//   * a declared read order (`fieldOrder` / `<key>FieldOrder`) orders the
//     members it names and numbers them, and members it names but that were not
//     published are shown as declared-not-decoded rather than omitted;
//   * keys the decoder published beside a declared order are marked as framing
//     metadata instead of being mixed in with serialized members;
//   * byte ranges, member counts, decode status, null framing, and Unity
//     PPtr references are recognized by shape and surfaced as chips on the
//     node that carries them, while still remaining visible as ordinary
//     children;
//   * exact integers published as decimal strings keep every digit and also
//     show their hexadecimal form.
// Nothing here promotes evidence: every status, range, and boundary passes
// through from the publisher unchanged.
//
// Record viewer contract (memory/webui/data_inspector.md owns the dataset
// list; scripts/webui/data_inspector/contract.py owns the envelope):
//   * Scalar `facts` are quick-scan cards; `facts` and `payload` are then two
//     labelled roots of one annotated tree. The root label follows the
//     required `payloadKind`: `reader` is a maintained scripts/game_data
//     reader's own result, `projection` was assembled by the publisher from an
//     already-decoded source whose mounted raw file stays authoritative.
//     `facts` is always the publisher's projection and may hold more than
//     `payload`. Only the reader payload root receives framing chips; a
//     `bytesConsumed` quoted in facts is not a consumption claim. Payload
//     sniffing for a framing status survives only for datasets published
//     before `payloadKind` existed. No dataset id is hardcoded.
//   * For a value-only reader the header shows a cursor at EOF only when
//     facts.wholeFileCursorExact is true and bytesConsumed equals the source
//     size. A facts `evidenceBoundary` is labelled as a publisher boundary,
//     never a decoder claim; a decoder's own payload boundary wins when both
//     exist. Header chips drop a tag or schemaStatus that repeats the family
//     or decode status already shown, and a whole-file read is stated on the
//     size chip rather than as a second chip.
//   * Field names are shown verbatim in every locale so a row stays
//     searchable against the export, the contract JSON and the reader; only
//     page furniture and evidence vocabulary are localized.
//   * The tree offers a field search under TREE_ROW_BUDGET, expand/collapse
//     all (alt-click folds one branch recursively), a raw-JSON view, and an
//     on-demand bounded raw source preview. Branches below the roots
//     materialize lazily.
//   * `references` (publisher projection): each stored identifier with its
//     exact source path; an item links only when targetState is `present` and
//     the target is in the loaded catalog. Absent or ambiguous targets stay
//     labelled non-links, and the publisher boundary is shown above the list.
//     SkillData uses this for AllowNextSkillAction.allowedSkillIdList,
//     including nested action values; links do not assert a runtime skill
//     transition.
//   * Catalog `searchTerms` feed the sidebar search without loading shards.
//     The detail shows them as a collapsed list of exact same-dataset
//     filters; selecting one clears other list facets, and editing the search
//     box returns to regex search. With a complete directStoredActionTypes
//     inventory (SkillData), each term also shows its union tag and this
//     record's timeline/passive occurrence counts; the `records` number counts
//     catalog records carrying the term, never occurrences.
//   * The same validated inventory offers a collapsed list of direct action
//     occurrences with decoded array indices and field paths; selecting one
//     opens that node. The payload's type/tag counts are checked against the
//     publisher inventory first, and a changed or incomplete shape withholds
//     the list. Nested branch actions stay outside it; positions are stored
//     array order, not execution order or timing.
//   * buff-action-receipts records show a collapsed span list that locates
//     each verified wrapper in the tree by byte range; it claims no nested
//     field semantics, whole-file ownership or runtime execution.
(() => {
  const ROOT_PATH = "data/data_inspector/index.json";
  const AUTO_OPEN_DEPTH = 1;
  const TREE_ROW_BUDGET = 4000;
  const RAW_PREVIEW_LIMIT = 1000000;
  const JSON_VIEW_LIMIT = 2000000;
  const MISSING = Symbol("declared-but-not-published");

  const lazyValues = new Map();
  let lazySequence = 0;

  const state = {
    container: null,
    hooks: {},
    root: null,
    loadPromise: null,
    datasets: [],
    datasetTone: new Map(),
    records: [],
    selectedKey: "",
    selectedRecord: null,
    selectedEntry: null,
    shardCache: new Map(),
    treeQuery: "",
    treeView: "semantic",
  };

  const { $ } = window.WebUI;
  const esc = window.WebUI.escapeHtml;
  const formatNumber = window.WebUI.formatNumber;
  const zh = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh")
    .toLowerCase().startsWith("zh");
  const ui = (en, cn) => (zh() ? cn : en);

  // ---------------------------------------------------------------- labels --

  // Field names are the decoder's own identifiers, so they are shown verbatim in
  // every locale. Renaming or translating them would make a row unsearchable
  // against the source, the contract JSON, and the reader that produced it.
  function fieldLabel(key, isArrayIndex = false) {
    const raw = String(key ?? "");
    return isArrayIndex ? `#${Number(raw) + 1}` : raw;
  }

  function statusLabel(value) {
    const labels = {
      named_exact: ["Complete named decode", "完整命名解码"],
      named_exact_frame: ["Complete framed decode", "完整分帧解码"],
      exact: ["Exact decode", "精确解码"],
      structural_only: ["Whole-file structural decode", "整文件结构解码"],
      "exact-current-complete": ["Exact and complete for this build", "对该版本精确且完整"],
      decoded_unity_json: ["Unity JSON decoded", "Unity JSON 已解析"],
      bounded_partial: ["Partial decode", "部分解码"],
      bounded_partial_ambiguous: ["Partial, ambiguous", "部分且存在歧义"],
      unsupported: ["No maintained reader", "无维护中读取器"],
      decode_error: ["Decode failed", "解码失败"],
      unknown: ["Unknown status", "状态未知"],
    };
    const pair = labels[String(value || "unknown")];
    return pair ? ui(pair[0], pair[1]) : String(value || ui("Unknown", "未知"));
  }

  function statusClass(value) {
    return String(value || "unknown").replace(/[^a-z0-9_-]+/gi, "-").toLowerCase();
  }

  function formatBytes(value) {
    const bytes = Number(value);
    if (!Number.isFinite(bytes) || bytes < 0) return String(value ?? "");
    if (bytes < 1024) return `${bytes.toLocaleString()} B`;
    const units = ["KB", "MB", "GB"];
    let size = bytes;
    let unit = "B";
    for (const candidate of units) {
      size /= 1024;
      unit = candidate;
      if (size < 1024) break;
    }
    return `${size.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${unit}`;
  }

  // ------------------------------------------------------------ record list --

  function datasetPath(descriptor) {
    return `data/data_inspector/${String(descriptor?.path || "")}`;
  }

  function shardPath(entry) {
    return `data/data_inspector/datasets/${encodeURIComponent(entry._datasetId)}/${entry.shard}`;
  }

  function toneClass(datasetId) {
    return `is-tone-${state.datasetTone.get(datasetId) ?? 0}`;
  }

  // Group by the first three export segments. A per-file folder would produce
  // thousands of single-record chips; three segments keeps the family readable
  // (`game/Json/NPC`, `game/Unity/AnimatorController`) without inventing a
  // classification the publisher did not record.
  function folderKey(sourcePath) {
    const parts = String(sourcePath || "").split("/").filter(Boolean);
    if (parts.length <= 1) return parts[0] || "";
    return parts.slice(0, Math.min(3, parts.length - 1)).join("/");
  }

  function buildSearchText(entry) {
    return [window.WebUI.linkedFileSearchText(entry), entry.linkedFileSearch,
      entry.id, entry.title, entry.status, entry.summary, entry.sourcePath, entry._folder,
      ...(entry.tags || []), ...(entry.searchTerms || [])]
      .join("\n").toLocaleLowerCase();
  }

  function countValues(records, pick) {
    const counts = new Map();
    for (const record of records) {
      for (const value of pick(record)) {
        if (value === "" || value == null) continue;
        counts.set(value, (counts.get(value) || 0) + 1);
      }
    }
    return counts;
  }

  // ------------------------------------------------------------------ shell --

  function bindFilterSections(root = document) {
    root.querySelectorAll(".filter-section-toggle").forEach((button) => {
      button.addEventListener("click", () => {
        const section = button.closest(".filter-section");
        const body = section?.querySelector(".filter-section-body");
        if (!section || !body) return;
        const collapsed = !section.classList.contains("is-collapsed");
        section.classList.toggle("is-collapsed", collapsed);
        body.hidden = collapsed;
        button.setAttribute("aria-expanded", String(!collapsed));
        window.dispatchEvent(new Event("resize"));
      });
    });
  }

  // The pane splitter (sidebar width) and, when a filter panel and its splitter
  // are given, the filter splitter (panel height) of one list-page shell. The
  // Data page's Files and SQL modes reuse it with their own elements.
  // ------------------------------------------------------------- list rows --

  // The page controller (stores.js) owns the list, its filters and paging;
  // these helpers give it this source's matching, ordering and row markup.
  function queryMatcher(query, catalogTerm = "") {
    if (catalogTerm) return (entry) => (entry.searchTerms || []).includes(catalogTerm);
    const text = String(query || "").trim();
    if (!text) return () => true;
    const lower = text.toLocaleLowerCase();
    const tokens = window.WebUI.parseQuery(text);
    // Union type names contain `+`, which queryMatches treats as a regex
    // operator. Keep regex search, while accepting an exact literal term.
    return (entry) => entry._search.includes(lower) || window.WebUI.queryMatches(entry._search, tokens);
  }

  function sortOptions() {
    return [
      ["path", ui("Source path (A-Z)", "源文件路径 (A-Z)")],
      ["title", ui("Name (A-Z)", "名称 (A-Z)")],
      ["dataset", ui("Data family, then name", "数据族，再按名称")],
      ["status", ui("Decode status", "解码状态")],
    ];
  }

  function comparator(sort) {
    const byTitle = (a, b) => a.title.localeCompare(b.title, undefined, { numeric: true })
      || a.id.localeCompare(b.id, undefined, { numeric: true });
    const comparators = {
      path: (a, b) => (a.sourcePath || a.id).localeCompare(b.sourcePath || b.id, undefined, { numeric: true }),
      title: byTitle,
      dataset: (a, b) => a._datasetTitle.localeCompare(b._datasetTitle, undefined, { numeric: true }) || byTitle(a, b),
      status: (a, b) => String(a.status).localeCompare(String(b.status)) || byTitle(a, b),
    };
    return comparators[sort] || comparators.path;
  }

  function rowHtml(entry) {
    return `
        <span class="data-inspector-row-title-line">
          <span class="data-inspector-row-family ${esc(toneClass(entry._datasetId))}">${esc(entry._datasetTitle)}</span>
          <span class="data-inspector-row-title">${esc(entry.title)}</span>
        </span>
        <span class="data-inspector-row-path" title="${esc(entry.sourcePath || entry.id)}">${esc(entry.sourcePath || entry.id)}</span>
        <span class="data-inspector-row-meta">
          <span class="data-inspector-status is-${esc(statusClass(entry.status))}" title="${esc(entry.status)}">${esc(statusLabel(entry.status))}</span>
          <span class="data-inspector-row-summary">${esc(entry.summary || "")}</span>
        </span>`;
  }
  // --------------------------------------------------------- value semantics --

  const EXACT_INTEGER_KEY = /(?:id|path|hash|guid)$/i;
  const HEX_WORTHY_KEY = /(?:id|hash|guid|mask|flag|flags|tag)$/i;

  function isExactIntegerString(value, key) {
    return typeof value === "string" && /^-?\d{10,}$/.test(value) && EXACT_INTEGER_KEY.test(String(key));
  }

  function hexOf(decimalText) {
    try {
      const big = BigInt(decimalText);
      const negative = big < 0n;
      return `${negative ? "-" : ""}0x${(negative ? -big : big).toString(16).toUpperCase()}`;
    } catch (_error) {
      return "";
    }
  }

  function scalarHtml(value, key = "") {
    if (value === MISSING) {
      return `<span class="json-missing" title="${esc(ui(
        "The decoder declared this member in its read order but published no value for it",
        "解码器在读取顺序中声明了该成员，但未发布其值",
      ))}">${esc(ui("declared in read order, not published", "已在读取顺序中声明，未发布"))}</span>`;
    }
    if (value === null) return '<span class="json-null">null</span>';
    if (value === undefined) return '<span class="json-null">undefined</span>';
    if (typeof value === "string") {
      if (isExactIntegerString(value, key)) {
        const hex = hexOf(value);
        return `<span class="json-number data-inspector-exact-integer" title="${esc(ui(
          "Exact integer published as text so no digit is lost in the browser",
          "为避免浏览器丢失数位而以文本发布的精确整数",
        ))}">${esc(value)}</span>${hex ? `<span class="data-inspector-alt-form">${esc(hex)}</span>` : ""}`;
      }
      if (value === "") return `<span class="json-string is-empty">${esc(ui('"" (empty)', '"" (空)'))}</span>`;
      return `<span class="json-string">${esc(JSON.stringify(value))}</span>`;
    }
    if (typeof value === "number") {
      // A hexadecimal form helps for identity-like numbers; on a count it is noise.
      const hex = Number.isInteger(value) && Math.abs(value) >= 4096 && HEX_WORTHY_KEY.test(String(key))
        ? hexOf(String(value))
        : "";
      return `<span class="json-number">${esc(String(value))}</span>${hex ? `<span class="data-inspector-alt-form">${esc(hex)}</span>` : ""}`;
    }
    if (typeof value === "boolean") {
      return `<span class="json-boolean is-${value}">${value}</span>`;
    }
    return `<span>${esc(String(value))}</span>`;
  }

  function shortScalar(value) {
    if (typeof value === "string") return value.length > 48 ? `${JSON.stringify(value.slice(0, 48))}…` : JSON.stringify(value);
    if (value === null) return "null";
    if (value && typeof value === "object") return Array.isArray(value) ? `[${value.length}]` : `{${Object.keys(value).length}}`;
    return String(value);
  }

  // A Unity PPtr, as AnimeStudio publishes it. Recognized by shape only.
  function pptrText(value) {
    if (!value || typeof value !== "object" || value.m_PathID === undefined || value.m_FileID === undefined) return "";
    const name = value.Name ? ` ${value.Name}` : "";
    const nullMark = value.IsNull === true ? ` · ${ui("null", "空")}` : "";
    return `PPtr ${value.m_FileID}:${value.m_PathID}${name}${nullMark}`;
  }

  // Shape-recognized decoder semantics. Every chip restates something the
  // publisher already wrote into the node; nothing is inferred beyond that.
  function annotations(value, key) {
    const chips = [];
    if (!value || typeof value !== "object") return chips;
    if (Array.isArray(value)) return chips;
    const number = (name) => (typeof value[name] === "number" && Number.isFinite(value[name]) ? value[name] : null);

    const start = number("startOffset");
    const end = number("endOffset");
    const headerEnd = number("headerEndOffset");
    if (start !== null && end !== null) {
      chips.push({
        cls: "is-bytes",
        text: `${ui("bytes", "字节")} ${start}–${end} · ${formatBytes(Math.max(0, end - start))}`,
        title: ui("Byte range the decoder proved for this node", "解码器为该节点确定的字节范围"),
      });
    } else if (start !== null) {
      chips.push({ cls: "is-bytes", text: `${ui("from byte", "起始字节")} ${start}` });
    }
    if (headerEnd !== null && start !== null) {
      chips.push({ cls: "is-bytes is-soft", text: `${ui("header ends", "头部结束")} ${headerEnd}` });
    }
    const length = number("length");
    if (length !== null && start === null) chips.push({ cls: "is-bytes", text: formatBytes(length) });

    if (typeof value.status === "string" && value.status) {
      chips.push({ cls: `is-state is-status-${statusClass(value.status)}`, text: value.status });
    }
    if (typeof value.schemaStatus === "string" && value.schemaStatus) {
      chips.push({ cls: `is-state is-status-${statusClass(value.schemaStatus)}`, text: value.schemaStatus });
    }
    if (value.isNull === true || value.status === "null") {
      chips.push({ cls: "is-state is-null", text: ui("null frame", "空帧") });
    }
    if (value.closed === true) chips.push({ cls: "is-state is-ok", text: ui("frame closed", "帧已闭合") });
    if (value.closed === false) chips.push({ cls: "is-state is-warn", text: ui("frame not closed", "帧未闭合") });

    const members = number("memberCount") ?? number("serializedMemberCount");
    if (members !== null) chips.push({ cls: "is-count", text: `${formatNumber(members)} ${ui("members", "成员")}` });
    const count = number("count");
    if (count !== null) chips.push({ cls: "is-count", text: `${formatNumber(count)} ${ui("rows", "行")}` });
    const consumed = number("bytesConsumed");
    if (consumed !== null) chips.push({ cls: "is-bytes", text: `${formatBytes(consumed)} ${ui("consumed", "已读取")}` });

    const pptr = pptrText(value);
    if (pptr) chips.push({ cls: "is-ref", text: pptr, title: ui("Unity object reference", "Unity 对象引用") });

    if (typeof value.evidenceBoundary === "string" && value.evidenceBoundary) {
      chips.push({
        cls: "is-boundary",
        text: `${ui("evidence", "证据")}: ${truncate(value.evidenceBoundary, 90)}`,
        title: value.evidenceBoundary,
      });
    }
    if (declaredOrderOf(value, key, null)) {
      chips.push({
        cls: "is-order",
        text: ui("declared read order", "声明读取顺序"),
        title: ui("Members below are shown in the order the decoder read them", "下列成员按解码器读取顺序显示"),
      });
    }
    return chips;
  }

  function truncate(text, limit) {
    const value = String(text ?? "");
    return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
  }

  function chipsHtml(chips) {
    return chips.map((chip) => `<span class="data-inspector-chip ${esc(chip.cls || "")}"${chip.title ? ` title="${esc(chip.title)}"` : ""}>${esc(chip.text)}</span>`).join("");
  }

  // A declared read order applies to the object that actually holds the named
  // members: a `fields` child when the node delegates to one, otherwise the node
  // itself. Parent-declared orders (`rootFieldOrder`, `dataFieldOrder`, ...)
  // take precedence because they name the child explicitly.
  function declaredOrderOf(value, key, parent) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    if (parent && typeof parent === "object" && !Array.isArray(parent)) {
      const named = parent[`${key}FieldOrder`];
      if (Array.isArray(named) && named.length) return named;
      if (key === "fields" && Array.isArray(parent.fieldOrder) && parent.fieldOrder.length) return parent.fieldOrder;
    }
    const own = value.fieldOrder;
    const delegates = value.fields && typeof value.fields === "object" && !Array.isArray(value.fields);
    if (Array.isArray(own) && own.length && !delegates) return own;
    return null;
  }

  // Children in publication order, with declared serialized members first (in
  // their declared order and numbered), then whatever framing metadata the
  // decoder published beside them.
  function childEntries(value, key, parent) {
    if (Array.isArray(value)) return value.map((item, index) => ({ key: String(index), value: item, isArrayIndex: true }));
    const order = declaredOrderOf(value, key, parent);
    const keys = Object.keys(value);
    if (!order) return keys.map((name) => ({ key: name, value: value[name] }));
    const named = new Set(order);
    const out = order.map((name, index) => ({
      key: name,
      value: Object.prototype.hasOwnProperty.call(value, name) ? value[name] : MISSING,
      ordinal: index + 1,
      missing: !Object.prototype.hasOwnProperty.call(value, name),
    }));
    for (const name of keys) {
      if (!named.has(name)) out.push({ key: name, value: value[name], meta: true });
    }
    return out;
  }

  // Keys already restated as chips on the same row are not repeated in the
  // inline preview, so a row reads once rather than twice.
  const CHIPPED_KEYS = new Set([
    "startOffset", "endOffset", "headerEndOffset", "length", "status", "schemaStatus",
    "isNull", "closed", "memberCount", "serializedMemberCount", "count", "bytesConsumed",
    "evidenceBoundary", "fieldOrder",
  ]);

  function previewHtml(value, key) {
    if (value === MISSING || value === null || typeof value !== "object") return "";
    if (Array.isArray(value)) {
      if (!value.length) return "";
      const shown = value.slice(0, 8).map(shortScalar);
      const suffix = value.length > shown.length ? `, … +${value.length - shown.length}` : "";
      return `<span class="data-inspector-preview">${esc(shown.join(", "))}${esc(suffix)}</span>`;
    }
    const pptr = pptrText(value);
    if (pptr) return "";
    const entries = Object.entries(value).filter(([name]) => !CHIPPED_KEYS.has(name) && !/FieldOrder$/.test(name));
    if (!entries.length) return "";
    const shown = entries.slice(0, 5)
      .filter(([, child]) => child === null || typeof child !== "object")
      .map(([name, child]) => `${fieldLabel(name)}=${shortScalar(child)}`);
    if (!shown.length) return "";
    return `<span class="data-inspector-preview">${esc(shown.join(", "))}</span>`;
  }

  function shapeText(value) {
    if (Array.isArray(value)) return `${ui("list", "列表")} · ${formatNumber(value.length)}`;
    return `${ui("object", "对象")} · ${formatNumber(Object.keys(value).length)}`;
  }

  // ------------------------------------------------------------- tree render --

  function rowClasses(entry) {
    const classes = [];
    if (entry.meta) classes.push("is-meta");
    if (entry.missing) classes.push("is-missing");
    return classes.join(" ");
  }

  function ordinalHtml(entry) {
    if (!entry.ordinal) return `<span class="data-inspector-ordinal is-blank"></span>`;
    return `<span class="data-inspector-ordinal" title="${esc(ui("Serialized member order", "序列化成员顺序"))}">${entry.ordinal}</span>`;
  }

  function keyHtml(entry) {
    return `<span class="data-inspector-key">${esc(fieldLabel(entry.key, entry.isArrayIndex))}</span>`;
  }

  function metaMarker(entry) {
    if (entry.missing) return "";
    if (entry.meta) {
      return `<span class="data-inspector-chip is-framing" title="${esc(ui(
        "Decoder framing metadata published beside the serialized members",
        "与序列化成员一同发布的解码框架信息",
      ))}">${esc(ui("framing", "框架"))}</span>`;
    }
    return "";
  }

  // `depth` drives auto-expansion only; everything below AUTO_OPEN_DEPTH becomes
  // a lazy branch so a controller projection with thousands of hashes does not
  // build its whole DOM on select.
  function nodeHtml(entry, path, parent, depth) {
    const value = entry.value;
    if (value === MISSING || value === null || typeof value !== "object") {
      return `<div class="data-inspector-leaf ${rowClasses(entry)}" data-path="${esc(path)}">
        ${ordinalHtml(entry)}
        ${keyHtml(entry)}
        <span class="data-inspector-value">${scalarHtml(value, entry.key)}</span>
        ${metaMarker(entry)}
      </div>`;
    }
    const children = childEntries(value, entry.key, parent);
    const chips = chipsHtml(annotations(value, entry.key));
    const head = `${ordinalHtml(entry)}${keyHtml(entry)}<span class="data-inspector-shape">${esc(shapeText(value))}</span>${chips}${metaMarker(entry)}${previewHtml(value, entry.key)}`;
    if (!children.length) {
      return `<div class="data-inspector-leaf ${rowClasses(entry)}" data-path="${esc(path)}">${head}
        <span class="data-inspector-value"><span class="json-null">${esc(ui("empty", "空"))}</span></span></div>`;
    }
    const open = depth < AUTO_OPEN_DEPTH;
    if (!open) {
      const token = `di-${++lazySequence}`;
      lazyValues.set(token, { entry, path, parent, depth });
      return `<details class="data-inspector-branch ${rowClasses(entry)}" data-path="${esc(path)}" data-lazy-token="${token}">
        <summary><button class="data-inspector-fold" type="button" aria-expanded="false">+</button>${head}</summary>
        <div class="data-inspector-children"></div>
      </details>`;
    }
    return `<details class="data-inspector-branch ${rowClasses(entry)}" data-path="${esc(path)}" open>
      <summary><button class="data-inspector-fold" type="button" aria-expanded="true">−</button>${head}</summary>
      <div class="data-inspector-children">${children
        .map((child) => nodeHtml(child, `${path}.${child.key}`, value, depth + 1))
        .join("")}</div>
    </details>`;
  }

  function materializeLazy(node) {
    if (node.dataset.lazyLoaded || !node.dataset.lazyToken) return;
    const stored = lazyValues.get(node.dataset.lazyToken);
    node.dataset.lazyLoaded = "true";
    lazyValues.delete(node.dataset.lazyToken);
    if (!stored) return;
    const { entry, path, parent, depth } = stored;
    const children = childEntries(entry.value, entry.key, parent);
    $(".data-inspector-children", node).innerHTML = children
      .map((child) => nodeHtml(child, `${path}.${child.key}`, entry.value, depth + 1))
      .join("");
    bindTree(node);
  }

  function syncFold(node) {
    const button = node.firstElementChild?.querySelector(".data-inspector-fold");
    if (!button) return;
    button.textContent = node.open ? "−" : "+";
    button.setAttribute("aria-expanded", String(node.open));
  }

  function setBranchOpen(node, open, { recursive = false } = {}) {
    node.open = open;
    syncFold(node);
    if (open) materializeLazy(node);
    if (!recursive) return;
    const children = $(".data-inspector-children", node);
    if (!children) return;
    children.querySelectorAll(":scope > details.data-inspector-branch")
      .forEach((child) => setBranchOpen(child, open, { recursive: true }));
  }

  function bindTree(root) {
    root.querySelectorAll("details.data-inspector-branch:not([data-tree-bound])").forEach((node) => {
      node.dataset.treeBound = "true";
      const summary = node.firstElementChild;
      const button = summary?.querySelector(".data-inspector-fold");
      if (!button) return;
      // Alt-click folds or unfolds the whole branch; a plain click is one level.
      const toggle = (event) => {
        event.preventDefault();
        event.stopPropagation();
        setBranchOpen(node, !node.open, { recursive: event.altKey });
      };
      button.addEventListener("click", toggle);
      summary.addEventListener("click", (event) => {
        if (event.target.closest(".data-inspector-fold")) return;
        toggle(event);
      });
      node.addEventListener("toggle", () => {
        syncFold(node);
        if (node.open) materializeLazy(node);
      });
      syncFold(node);
    });
  }

  // ---- search over the structure ------------------------------------------

  function matchesNode(entry, path, regex) {
    if (regex.test(path) || regex.test(String(entry.key)) || regex.test(fieldLabel(entry.key, entry.isArrayIndex))) return true;
    const value = entry.value;
    if (value === MISSING || value === null || typeof value === "object") return false;
    return regex.test(String(value));
  }

  // Renders only the branches that contain a hit, fully expanded, under a shared
  // row budget so a large projection cannot lock the page.
  function filteredNodeHtml(entry, path, parent, regex, budget) {
    if (budget.count >= budget.max) return { html: "", matched: false };
    const value = entry.value;
    const selfMatch = matchesNode(entry, path, regex);
    if (value === MISSING || value === null || typeof value !== "object") {
      if (!selfMatch) return { html: "", matched: false };
      budget.count += 1;
      return {
        html: `<div class="data-inspector-leaf is-hit ${rowClasses(entry)}">${ordinalHtml(entry)}${keyHtml(entry)}<span class="data-inspector-value">${scalarHtml(value, entry.key)}</span>${metaMarker(entry)}</div>`,
        matched: true,
      };
    }
    const children = childEntries(value, entry.key, parent);
    const parts = [];
    let childMatched = false;
    for (const child of children) {
      if (budget.count >= budget.max) break;
      const result = filteredNodeHtml(child, `${path}.${child.key}`, value, regex, budget);
      if (result.matched) {
        childMatched = true;
        parts.push(result.html);
      }
    }
    if (!selfMatch && !childMatched) return { html: "", matched: false };
    budget.count += 1;
    const chips = chipsHtml(annotations(value, entry.key));
    const head = `${ordinalHtml(entry)}${keyHtml(entry)}<span class="data-inspector-shape">${esc(shapeText(value))}</span>${chips}${metaMarker(entry)}`;
    const body = parts.length
      ? parts.join("")
      : `<div class="data-inspector-leaf is-elided">${esc(ui("no matching member", "无匹配成员"))}</div>`;
    return {
      html: `<details class="data-inspector-branch ${selfMatch ? "is-hit" : ""} ${rowClasses(entry)}" open>
        <summary><button class="data-inspector-fold" type="button" aria-expanded="true">−</button>${head}</summary>
        <div class="data-inspector-children">${body}</div>
      </details>`,
      matched: true,
    };
  }

  // The structure view covers every container the record actually published.
  // The two are different things and must not be labelled as if one contained
  // the other:
  //
  //   `facts`   is the WebUI publisher adapter's own projection. It is a
  //             convenience for scanning and searching, and for an
  //             already-decoded JSON source it may hold far more than
  //             `payload` does, because the adapter computed it from the whole
  //             raw file.
  //   `payload` is what the publisher republished of the decoder's output. It
  //             is the maintained reader's complete result only when that
  //             reader produced it; some readers report a framing status in
  //             that result, while others return values and a cursor for the
  //             publisher to verify. Otherwise it is a selected part of an
  //             already-decoded source and the mounted raw file stays
  //             authoritative.
  //
  // A payload that reports its own `status`/`schemaStatus` came from a
  // maintained `scripts/game_data/` reader. That is the general signal, and it
  // keeps this page from being taught which datasets those are.
  // `payloadKind` is the publisher's own declaration and is authoritative. The
  // shape sniff behind it only covers a dataset published before that field
  // existed; a publisher must not be trusted to be silent here.
  function payloadFromMaintainedReader(record) {
    if (record.payloadKind === "reader") return true;
    if (record.payloadKind === "projection") return false;
    const payload = record.payload;
    return typeof payload.schemaStatus === "string" || typeof payload.status === "string";
  }

  function structureRoots(record) {
    const roots = [];
    if (record.facts && typeof record.facts === "object" && Object.keys(record.facts).length) {
      roots.push({
        key: "facts",
        value: record.facts,
        label: ui("Publisher projection", "发布器投影"),
        note: ui("values the publisher selected for review", "发布器为便于查看而选出的值"),
      });
    }
    if (record.payload !== undefined && record.payload !== null && typeof record.payload === "object") {
      const framed = payloadFromMaintainedReader(record);
      const payloadReportsFraming = typeof record.payload.schemaStatus === "string"
        || typeof record.payload.status === "string";
      roots.push({
        key: "payload",
        value: record.payload,
        label: framed
          ? ui("Decoder result", "解码器结果")
          : ui("Republished source fields", "转载的源字段"),
        note: framed
          ? payloadReportsFraming ? ui(
            "the maintained reader's own result, with the framing status it reported",
            "维护中读取器自身的结果，附其报告的分帧状态",
          ) : ui(
            "maintained reader values; the record status and facts show the publisher's validation",
            "维护中读取器的值；记录状态和事实列出发布器的验证结果",
          )
          : ui(
            "a selected part of an already-decoded source; the raw source stays authoritative",
            "已解码源文件的部分内容；原始文件仍为准",
          ),
      });
    }
    return roots;
  }

  function structureJson(record) {
    const roots = structureRoots(record);
    if (!roots.length) return "";
    if (roots.length === 1) return JSON.stringify(roots[0].value, null, 2);
    return JSON.stringify(Object.fromEntries(roots.map((root) => [root.key, root.value])), null, 2);
  }

  // A root is a normal branch row carrying its own explanatory note.
  function rootNodeHtml(root) {
    const children = childEntries(root.value, root.key, null);
    // `facts` is a publisher projection. A scalar such as bytesConsumed may
    // quote the reader, but the projection itself did not consume those bytes
    // or deserialize that many members. Framing chips belong to payload only.
    // The header already carries that payload's evidence boundary in full.
    const chips = root.key === "payload"
      ? chipsHtml(annotations(root.value, root.key).filter((chip) => chip.cls !== "is-boundary"))
      : "";
    const head = `<span class="data-inspector-root-label">${esc(root.label)}</span>`
      + `<span class="data-inspector-rawkey">${esc(root.key)}</span>`
      + `<span class="data-inspector-shape">${esc(shapeText(root.value))}</span>${chips}`
      + `<span class="data-inspector-root-note">${esc(root.note)}</span>`;
    return `<details class="data-inspector-branch is-root" open>
      <summary><button class="data-inspector-fold" type="button" aria-expanded="true">−</button>${head}</summary>
      <div class="data-inspector-children">${children
        .map((child) => nodeHtml(child, `${root.key}.${child.key}`, root.value, 1))
        .join("")}</div>
    </details>`;
  }

  function renderTree() {
    const host = $("#data-inspector-tree", state.container);
    const record = state.selectedRecord;
    if (!host || !record) return;
    const roots = structureRoots(record);
    if (!roots.length) {
      host.innerHTML = `<div class="data-inspector-empty">${esc(ui("This publisher did not include a decoded structure.", "该发布器未包含解码结构。"))}</div>`;
      return;
    }
    lazyValues.clear();
    if (state.treeView === "json") {
      const text = structureJson(record);
      const shown = text.length > JSON_VIEW_LIMIT ? text.slice(0, JSON_VIEW_LIMIT) : text;
      host.innerHTML = `<pre class="data-inspector-json">${esc(shown)}</pre>${
        text.length > shown.length
          ? `<p class="data-inspector-description">${esc(ui(
            "Shown up to the first 2,000,000 characters; open the raw source for the complete file.",
            "最多显示前 2,000,000 个字符；请打开原始文件查看完整内容。",
          ))}</p>`
          : ""}`;
      return;
    }
    const query = state.treeQuery.trim();
    if (query) {
      const regex = window.WebUI.queryRegex(query);
      const budget = { count: 0, max: TREE_ROW_BUDGET };
      const parts = [];
      for (const root of roots) {
        for (const child of childEntries(root.value, root.key, null)) {
          const result = filteredNodeHtml(child, `${root.key}.${child.key}`, root.value, regex, budget);
          if (result.matched) parts.push(result.html);
        }
      }
      host.innerHTML = parts.length
        ? `${parts.join("")}${budget.count >= budget.max
          ? `<p class="data-inspector-description">${esc(ui(
            `Stopped after ${TREE_ROW_BUDGET.toLocaleString()} matching rows. Narrow the field search.`,
            `已在 ${TREE_ROW_BUDGET.toLocaleString()} 行匹配结果后停止，请细化字段搜索。`,
          ))}</p>`
          : ""}`
        : `<div class="data-inspector-empty">${esc(ui("No field or value matches.", "没有匹配的字段或值。"))}</div>`;
      bindTree(host);
      return;
    }
    host.innerHTML = roots.map(rootNodeHtml).join("");
    bindTree(host);
  }

  function setAllBranches(open) {
    const host = $("#data-inspector-tree", state.container);
    if (!host) return;
    host.querySelectorAll(":scope > details.data-inspector-branch")
      .forEach((node) => setBranchOpen(node, open, { recursive: true }));
  }

  function locateDecodedField(path) {
    if (!path?.startsWith("payload.")) return;
    state.treeQuery = "";
    state.treeView = "semantic";
    const query = $("#data-inspector-tree-q", state.container);
    if (query) query.value = "";
    state.container.querySelectorAll("[data-tree-view]").forEach((button) => {
      const active = button.dataset.treeView === "semantic";
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    renderTree();
    const host = $("#data-inspector-tree", state.container);
    const parts = path.split(".");
    let node = null;
    for (let length = 2; length <= parts.length; length += 1) {
      const prefix = parts.slice(0, length).join(".");
      node = [...host.querySelectorAll("[data-path]")]
        .find((candidate) => candidate.dataset.path === prefix);
      if (!node) return;
      if (node.matches("details.data-inspector-branch")) setBranchOpen(node, true);
    }
    node?.classList.add("is-located");
    node?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // ----------------------------------------------------------- detail render --

  // Scalars only: a collection's contents belong in the structure tree, where
  // they keep their own shape instead of being previewed twice.
  function highlightsHtml(facts) {
    if (!facts || typeof facts !== "object") return "";
    const scalars = Object.entries(facts).filter(([, value]) => value === null || typeof value !== "object");
    if (!scalars.length) return "";
    const cards = scalars.map(([key, value]) => `
      <div class="data-inspector-fact">
        <div class="data-inspector-fact-label" title="${esc(key)}">${esc(fieldLabel(key))}</div>
        <div class="data-inspector-fact-value">${scalarHtml(value, key)}</div>
      </div>`).join("");
    return `
      <section class="data-inspector-section">
        <h3>${esc(ui("Key values", "关键值"))}</h3>
        <p class="data-inspector-description">${esc(ui(
          "The publisher's selected scalar values. Lists and objects keep their own shape in the structure below.",
          "发布器选出的标量值。列表与对象在下方结构中保留各自的形状。",
        ))}</p>
        <div class="data-inspector-facts">${cards}</div>
      </section>`;
  }

  // Catalog terms are publisher-supplied search labels. Keep the relation exact
  // and within its dataset; a shared term does not establish a runtime edge.
  function catalogTermsHtml(entry, record) {
    const terms = [...new Set((entry.searchTerms || [])
      .filter((term) => typeof term === "string" && term.trim()))];
    if (!terms.length) return "";
    const publishedActions = record?.facts?.directStoredActionTypes;
    const actionRows = Array.isArray(publishedActions)
      && publishedActions.every((row) => row && typeof row === "object"
        && Number.isInteger(row.tag) && row.tag >= 0
        && typeof row.type === "string" && terms.includes(row.type)
        && Number.isInteger(row.timelineOccurrences) && row.timelineOccurrences >= 0
        && Number.isInteger(row.passiveEventOccurrences) && row.passiveEventOccurrences >= 0)
      && terms.every((term) => publishedActions.some((row) => row.type === term))
      ? publishedActions : null;
    const counts = countValues(
      state.records.filter((record) => record._datasetId === entry._datasetId),
      (record) => new Set(record.searchTerms || []),
    );
    const buttons = terms.map((term) => {
      const label = term.includes(".") ? term.slice(term.lastIndexOf(".") + 1) : term;
      const occurrences = actionRows?.filter((row) => row.type === term) || [];
      const details = occurrences.map((row) =>
        `0x${row.tag.toString(16).padStart(4, "0")} · ${ui("timeline", "时间轴")} ${formatNumber(row.timelineOccurrences)}`
        + ` · ${ui("passive", "被动")} ${formatNumber(row.passiveEventOccurrences)}`,
      ).join("; ");
      return `<button type="button" class="${details ? "is-action-term" : ""}" data-inspector-catalog-term="${esc(term)}" title="${esc(term)}">
        <code>${esc(label)}</code>${details ? `<span>${esc(details)}</span>` : ""}
        <span>${esc(ui("records", "记录"))} ${esc(formatNumber(counts.get(term) || 0))}</span>
      </button>`;
    }).join("");
    return `<details class="data-inspector-section data-inspector-catalog-terms">
      <summary>${esc(actionRows
        ? ui("Direct stored action types", "直接存储的动作类型")
        : ui("Catalog terms", "目录检索词"))} <span>(${esc(formatNumber(terms.length))})</span></summary>
      <p class="data-inspector-description">${esc(ui(
        actionRows
          ? "Tags and occurrence counts are from this record's direct timeline and passive-event arrays. Nested branch actions are excluded. Select a type to find catalog records with that exact type; these are stored assignments, not observed execution."
          : "Publisher-supplied terms. Select one to find records in this data family with the same exact term; counts are catalog records, not observed uses.",
        actionRows
          ? "标记和出现次数来自此记录中直接的时间轴及被动事件数组，不包括嵌套分支动作。选择类型可查找目录中具有相同精确类型的记录；这些是存储的赋值，不代表实际执行。"
          : "发布器提供的检索词。选择一项可查找同一数据族中具有相同词的记录；数量指目录记录，不代表实际使用次数。",
      ))}</p>
      <div class="data-inspector-catalog-term-list">${buttons}</div>
    </details>`;
  }

  // The publisher's direct-action inventory establishes the allowed shape and
  // counts. Recheck it against the payload before offering a path into the
  // tree, so a stale or differently shaped projection cannot point elsewhere.
  function directActionOccurrences(record) {
    const facts = record.facts;
    const group = record.payload?.actionGroupData;
    if (facts?.directStoredActionInventoryAvailable !== true
        || !Array.isArray(facts.directStoredActionTypes)
        || !group || !Array.isArray(group.timelineActions)
        || !Array.isArray(group.passiveEventActions)) return null;
    const rows = [];
    const counts = new Map();
    const append = (actions, lane, indices, sourcePrefix, treePrefix) => {
      if (!Array.isArray(actions)) return false;
      for (let index = 0; index < actions.length; index += 1) {
        const action = actions[index];
        if (!action || typeof action !== "object" || Array.isArray(action)
            || !Number.isInteger(action.$tag) || action.$tag < 0
            || typeof action.$type !== "string" || !action.$type) return false;
        const key = `${action.$tag}\n${action.$type}`;
        const pair = counts.get(key) || [0, 0];
        pair[lane] += 1;
        counts.set(key, pair);
        rows.push({
          lane,
          indices: [...indices, index],
          tag: action.$tag,
          type: action.$type,
          sourcePath: `${sourcePrefix}[${index}]`,
          treePath: `${treePrefix}.${index}`,
        });
      }
      return true;
    };
    for (let slot = 0; slot < group.timelineActions.length; slot += 1) {
      const sequence = group.timelineActions[slot]?._sequenceActionData;
      if (!sequence || !append(sequence.actionData, 0, [slot],
        `actionGroupData.timelineActions[${slot}]._sequenceActionData.actionData`,
        `payload.actionGroupData.timelineActions.${slot}._sequenceActionData.actionData`)) return null;
    }
    for (let event = 0; event < group.passiveEventActions.length; event += 1) {
      const actionGroups = group.passiveEventActions[event]?.actions;
      if (!Array.isArray(actionGroups)) return null;
      for (let actionGroup = 0; actionGroup < actionGroups.length; actionGroup += 1) {
        if (!append(actionGroups[actionGroup]?.actionData, 1, [event, actionGroup],
          `actionGroupData.passiveEventActions[${event}].actions[${actionGroup}].actionData`,
          `payload.actionGroupData.passiveEventActions.${event}.actions.${actionGroup}.actionData`)) return null;
      }
    }
    if (counts.size !== facts.directStoredActionTypes.length) return null;
    const seen = new Set();
    for (const fact of facts.directStoredActionTypes) {
      const key = `${fact.tag}\n${fact.type}`;
      const pair = counts.get(key);
      if (seen.has(key) || !pair || pair[0] !== fact.timelineOccurrences
          || pair[1] !== fact.passiveEventOccurrences) return null;
      seen.add(key);
    }
    if (Number.isInteger(facts.directStoredActionOccurrenceCount)
        && rows.length !== facts.directStoredActionOccurrenceCount) return null;
    return rows;
  }

  function directActionOccurrencesHtml(record) {
    const rows = directActionOccurrences(record);
    if (!rows?.length) return "";
    const items = rows.map((row) => {
      const location = row.lane === 0
        ? `${ui("timeline slot", "时间轴槽位")} ${row.indices[0] + 1} · ${ui("action", "动作")} ${row.indices[1] + 1}`
        : `${ui("passive event", "被动事件")} ${row.indices[0] + 1} · ${ui("group", "组")} ${row.indices[1] + 1} · ${ui("action", "动作")} ${row.indices[2] + 1}`;
      const name = row.type.includes(".") ? row.type.slice(row.type.lastIndexOf(".") + 1) : row.type;
      return `<li><button type="button" data-inspector-action-path="${esc(row.treePath)}"
        title="${esc(row.type)}"><span>${esc(location)}</span><code>${esc(name)}</code>
        <span>0x${esc(row.tag.toString(16).padStart(4, "0"))}</span></button>
        <code class="data-inspector-action-source">${esc(row.sourcePath)}</code></li>`;
    }).join("");
    return `<details class="data-inspector-section data-inspector-action-occurrences">
      <summary>${esc(ui("Direct stored action locations", "直接存储的动作位置"))} <span>(${esc(formatNumber(rows.length))})</span></summary>
      <p class="data-inspector-description">${esc(ui(
        "Positions and tags come from this record's decoded arrays. Select an occurrence to locate that exact field in the structure. Array position does not establish execution order or timing; nested branch actions are excluded.",
        "位置和标记来自此记录的解码数组。选择一项可定位到结构中的确切字段。数组位置不代表执行顺序或时间；不包括嵌套分支动作。",
      ))}</p>
      <ol>${items}</ol>
    </details>`;
  }

  // A Buff receipt describes a byte span inside a partial source file. Recheck
  // the projected boundaries before offering a shortcut into the tree.
  function buffActionReceiptsHtml(record) {
    const facts = record.facts;
    const spans = record.payload?.actionReceipts;
    if (record.payloadKind !== "projection" || record.status !== "bounded_partial"
        || facts?.wholeBuffDataExact !== false
        || facts?.recursiveNamedSchemaExact !== false
        || !Number.isInteger(facts?.verifiedActionSpanCount)
        || !Array.isArray(spans) || spans.length !== facts.verifiedActionSpanCount
        || !spans.length) return "";
    const valid = spans.every((span) => span && typeof span === "object"
      && [0x0092, 0x00B4].includes(span.tag)
      && typeof span.typeName === "string" && span.typeName
      && Number.isInteger(span.startOffset) && span.startOffset >= 0
      && Number.isInteger(span.endOffset) && span.endOffset > span.startOffset
      && span.wholeActionByteSpanExact === true
      && span.recursiveNamedSchemaExact === false
      && span.wholeBuffDataExact === false
      && Number.isInteger(span.memberCount)
      && Array.isArray(span.namedFields)
      && span.namedFields.length === span.memberCount);
    if (!valid) return "";
    const rows = spans.map((span, index) => {
      const name = span.typeName.includes(".")
        ? span.typeName.slice(span.typeName.lastIndexOf(".") + 1) : span.typeName;
      return `<li><button type="button" data-inspector-action-path="payload.actionReceipts.${index}"
        title="${esc(span.typeName)}"><code>${esc(name)}</code>
        <span>0x${esc(span.tag.toString(16).padStart(4, "0"))}</span>
        <span>${esc(ui("bytes", "字节"))} ${esc(span.startOffset)}–${esc(span.endOffset)}</span></button></li>`;
    }).join("");
    return `<details class="data-inspector-section data-inspector-action-occurrences">
      <summary>${esc(ui("Verified Buff action spans", "已验证的 Buff 动作片段"))} <span>(${esc(formatNumber(spans.length))})</span></summary>
      <p class="data-inspector-description">${esc(ui(
        "Each listed wrapper has an exact byte span and named fields in this stored BuffData file. Select one to inspect its fields. Nested values and the enclosing BuffData schema remain partial; no runtime use is implied.",
        "每个列出的包装层在此 BuffData 文件中都有精确字节范围和命名字段。选择一项可查看字段。嵌套值及整个 BuffData 结构仍不完整，不能据此推断运行时使用。",
      ))}</p><ol>${rows}</ol>
    </details>`;
  }

  // Publishers may attach exact source-field references separately from the
  // decoder payload. Resolve their targets against the loaded catalog before
  // offering navigation; a stored identifier alone is never a runtime edge.
  function referencesHtml(record) {
    const references = record.references;
    const items = references && Array.isArray(references.items) ? references.items : [];
    if (!items.length) return "";
    const rows = items.map((reference) => {
      const target = reference.targetState === "present"
        ? state.records.find((entry) => (
          entry._datasetId === reference.targetDatasetId
          && entry.id === reference.targetRecordId
        ))
        : null;
      const result = target
        ? `<button type="button" data-inspector-reference-key="${esc(target._key)}">${esc(ui(
          "Open matching record", "打开匹配记录",
        ))}</button>`
        : `<span class="data-inspector-reference-state">${esc(reference.targetState === "ambiguous"
          ? ui("Multiple filename matches; link withheld", "文件名存在多个匹配项，未提供链接")
          : reference.targetState === "absent"
            ? ui("No matching file in this export", "当前导出中无匹配文件")
            : ui("Target absent from the Inspector catalog", "检查器目录中缺少目标记录"))}</span>`;
      return `<li class="data-inspector-reference">
        <div><code>${esc(reference.storedId || "")}</code>${result}</div>
        <small><code>${esc(reference.sourcePath || "")}</code></small>
      </li>`;
    }).join("");
    const boundary = typeof references.evidenceBoundary === "string" ? references.evidenceBoundary : "";
    return `<section class="data-inspector-section data-inspector-references">
      <h3>${esc(ui("Stored references", "存储的引用"))}</h3>
      ${boundary ? `<p class="data-inspector-boundary"><span>${esc(ui(
        "Publisher evidence boundary", "发布器证据边界",
      ))}</span>${esc(boundary)}</p>` : ""}
      <ul>${rows}</ul>
    </section>`;
  }

  // The eyebrow above already carries the data family and the decode status, and
  // a publisher's `tags` normally repeat both plus the schema status. A token is
  // shown once: anything already stated is dropped here rather than restated.
  function headerMetaHtml(record, entry) {
    const source = record.source || {};
    const payload = record.payload && typeof record.payload === "object" ? record.payload : null;
    const facts = record.facts && typeof record.facts === "object" ? record.facts : null;
    const chips = [];
    const seen = new Set([record.status, entry._datasetId, entry._datasetTitle]
      .filter(Boolean).map((value) => String(value).toLocaleLowerCase()));
    const add = (chip) => {
      const token = String(chip.text).toLocaleLowerCase();
      if (seen.has(token)) return;
      seen.add(token);
      chips.push(chip);
    };

    const readerConsumed = payload?.bytesConsumed != null && Number.isFinite(Number(payload.bytesConsumed))
      ? Number(payload.bytesConsumed)
      : null;
    // Value-only readers leave EOF validation in the publisher facts. Only use
    // that cursor when the publisher explicitly says it reached EOF; a generic
    // bytesConsumed fact could describe a bounded prefix instead.
    const publisherConsumed = facts?.wholeFileCursorExact === true
      && facts.bytesConsumed != null
      && Number.isFinite(Number(facts.bytesConsumed))
      ? Number(facts.bytesConsumed)
      : null;
    const consumed = readerConsumed ?? publisherConsumed;
    if (source.bytes !== undefined) {
      // One size chip: a reader cursor at EOF is worth stating,
      // but not as a second chip holding the same number.
      const whole = consumed !== null && consumed === Number(source.bytes);
      chips.push({
        cls: "is-bytes",
        text: whole
          ? `${formatBytes(source.bytes)} · ${ui("cursor at EOF", "游标到达文件末尾")}`
          : formatBytes(source.bytes),
      });
      if (consumed !== null && !whole) {
        chips.push({ cls: "is-bytes is-soft", text: `${formatBytes(consumed)} ${ui("consumed", "已读取")}` });
      }
    } else if (consumed !== null) {
      chips.push({ cls: "is-bytes", text: `${formatBytes(consumed)} ${ui("consumed", "已读取")}` });
    }
    if (source.mediaType) add({ cls: "is-soft", text: source.mediaType });
    if (payload?.schemaStatus) add({ cls: `is-state is-status-${statusClass(payload.schemaStatus)}`, text: payload.schemaStatus });
    if (payload?.status) add({ cls: "is-state", text: payload.status });
    for (const tag of record.tags || []) add({ cls: "is-tag", text: tag });
    return chipsHtml(chips);
  }

  // A decoder boundary takes precedence. Value-only decoders may put the
  // publisher's narrower validation boundary in facts; label its origin.
  function evidenceBoundaryHtml(record) {
    const payload = record.payload;
    const decoderBoundary = payload && typeof payload === "object" ? payload.evidenceBoundary : "";
    const publisherBoundary = record.facts && typeof record.facts === "object"
      ? record.facts.evidenceBoundary : "";
    const fromPublisher = !(typeof decoderBoundary === "string" && decoderBoundary);
    const boundary = fromPublisher ? publisherBoundary : decoderBoundary;
    if (!boundary || typeof boundary !== "string") return "";
    const label = fromPublisher
      ? ui("Publisher evidence boundary", "发布器证据边界")
      : ui("Evidence boundary", "证据边界");
    return `<p class="data-inspector-boundary"><span>${esc(label)}</span>${esc(boundary)}</p>`;
  }

  function canonicalSkillEvidenceHtml(record) {
    const proof = record.facts?.canonicalRootEvidence;
    if (!proof || typeof proof.storedFrameExact !== "boolean"
        || proof.namedSchemaStatus !== "unproved") return "";
    const framing = proof.storedFrameExact
      ? ui("Complete stored frame through EOF", "完整存储结构已读至文件末尾")
      : ui("Stored frame remains partial", "存储结构仍有未解析部分");
    return `<section class="data-inspector-section data-inspector-skill-evidence">
      <h3>${esc(ui("Stored Skill evidence", "技能存储结构证据"))}</h3>
      <p>${esc(framing)} · ${esc(ui("Nested field naming remains unproved", "嵌套字段的完整命名仍未证实"))}</p>
      <p class="data-inspector-description">${esc(ui(
        "These source-matched framing facts are separate from the derived values below. Known fields remain available in the structure tree; runtime execution is not established.",
        "这些与源文件匹配的结构证据独立于下方的派生值。已知字段保留在结构树中；尚未证明运行时执行。",
      ))}</p>
    </section>`;
  }

  function renderDetail() {
    const host = state.container;
    const record = state.selectedRecord;
    const entry = state.selectedEntry;
    if (!host || !record || !entry) return;
    const source = record.source || {};
    host.innerHTML = `
      <article class="data-inspector-record">
        <header class="data-inspector-detail-header">
          <div class="data-inspector-eyebrow">
            <span class="data-inspector-row-family ${esc(toneClass(entry._datasetId))}">${esc(entry._datasetTitle)}</span>
            <span class="data-inspector-status is-${esc(statusClass(record.status))}" title="${esc(record.status)}">${esc(statusLabel(record.status))}</span>
          </div>
          <h1>${esc(record.title || record.id)}</h1>
          <div class="data-inspector-detail-path"><code>${esc(source.path || record.id)}</code></div>
          ${record.summary ? `<p class="data-inspector-description">${esc(record.summary)}</p>` : ""}
          <div class="data-inspector-chip-row">${headerMetaHtml(record, entry)}</div>
          ${evidenceBoundaryHtml(record)}
          <div class="data-inspector-actions">
            ${source.href ? `<a href="${esc(source.href)}" target="_blank" rel="noopener">${esc(ui("Open raw source", "打开原始文件"))}</a>` : ""}
            <button id="data-inspector-copy-path" type="button">${esc(ui("Copy source path", "复制源文件路径"))}</button>
            <button id="data-inspector-copy-json" type="button">${esc(ui("Copy decoded JSON", "复制解码 JSON"))}</button>
            ${source.href ? `<button id="data-inspector-load-raw" type="button">${esc(ui("Preview raw source", "预览原始文件"))}</button>` : ""}
          </div>
        </header>
        <div class="data-inspector-detail-body">
          ${record.diagnostic ? `<section class="data-inspector-diagnostic">
            <h3>${esc(ui("Decode diagnostic", "解码诊断"))}</h3><pre>${esc(record.diagnostic)}</pre></section>` : ""}
          ${canonicalSkillEvidenceHtml(record)}
          ${highlightsHtml(record.facts)}
          ${catalogTermsHtml(entry, record)}
          ${directActionOccurrencesHtml(record)}
          ${buffActionReceiptsHtml(record)}
          ${referencesHtml(record)}
          <section class="data-inspector-section data-inspector-structure">
            <div class="data-inspector-structure-head">
              <div>
                <h3>${esc(ui("Decoded structure", "解码结构"))}</h3>
                <p class="data-inspector-description">${esc(ui(
                  "Every container this record published, each in its own shape and labelled with where it came from. Numbered members follow the decoder's declared read order; byte ranges, counts, status, and references are read back from the record itself.",
                  "该记录发布的各个容器，均保留原始结构并标明来源。编号成员按解码器声明的读取顺序排列；字节范围、数量、状态与引用均取自记录本身。",
                ))}</p>
              </div>
              <div class="data-inspector-structure-tools">
                <input id="data-inspector-tree-q" type="search" autocomplete="off" value="${esc(state.treeQuery)}"
                  placeholder="${esc(ui("Find a field or value", "查找字段或值"))}">
                <button id="data-inspector-expand" type="button">${esc(ui("Expand all", "全部展开"))}</button>
                <button id="data-inspector-collapse" type="button">${esc(ui("Collapse all", "全部折叠"))}</button>
                <div class="data-inspector-view-switch" role="group" aria-label="${esc(ui("Structure view", "结构视图"))}">
                  <button type="button" data-tree-view="semantic" class="${state.treeView === "semantic" ? "is-active" : ""}" aria-pressed="${state.treeView === "semantic"}">${esc(ui("Annotated", "带注解"))}</button>
                  <button type="button" data-tree-view="json" class="${state.treeView === "json" ? "is-active" : ""}" aria-pressed="${state.treeView === "json"}">${esc(ui("Raw JSON", "原始 JSON"))}</button>
                </div>
              </div>
            </div>
            <div id="data-inspector-tree" class="data-inspector-tree"></div>
          </section>
          <details class="data-inspector-panel">
            <summary>
              <span>${esc(ui("Source and decode information", "文件来源与解码信息"))}</span>
              <small>${esc(source.path || record.id)}</small>
            </summary>
            <dl class="data-inspector-meta">
              <div><dt>${esc(ui("Record id", "记录 ID"))}</dt><dd><code>${esc(record.id)}</code></dd></div>
              <div><dt>${esc(ui("Data family", "数据族"))}</dt><dd>${esc(entry._datasetTitle)}<code>${esc(entry._datasetId)}</code></dd></div>
              <div><dt>${esc(ui("Status", "解码状态"))}</dt><dd>${esc(statusLabel(record.status))}<code>${esc(record.status || "unknown")}</code></dd></div>
              ${source.path ? `<div><dt>${esc(ui("Source path", "源文件路径"))}</dt><dd><code>${esc(source.path)}</code></dd></div>` : ""}
              ${source.bytes !== undefined ? `<div><dt>${esc(ui("File size", "文件大小"))}</dt><dd>${esc(formatBytes(source.bytes))}</dd></div>` : ""}
              ${source.mediaType ? `<div><dt>${esc(ui("Media type", "文件类型"))}</dt><dd><code>${esc(source.mediaType)}</code></dd></div>` : ""}
              ${(record.tags || []).length ? `<div><dt>${esc(ui("Tags", "标签"))}</dt><dd>${esc((record.tags || []).join(", "))}</dd></div>` : ""}
            </dl>
          </details>
          <section id="data-inspector-raw-section" class="data-inspector-section" hidden>
            <h3>${esc(ui("Raw source preview", "原始文件预览"))}</h3>
            <div id="data-inspector-raw"></div>
          </section>
        </div>
      </article>`;
    bindDetailEvents(record, source);
    renderTree();
  }

  function bindDetailEvents(record, source) {
    const container = state.container;
    container.querySelectorAll("[data-inspector-catalog-term]").forEach((button) => {
      button.addEventListener("click", () => {
        const term = button.dataset.inspectorCatalogTerm;
        if (!term || !state.selectedEntry) return;
        state.hooks?.onCatalogTerm?.(term, state.selectedEntry);
      });
    });
    container.querySelectorAll("[data-inspector-action-path]").forEach((button) => {
      button.addEventListener("click", () => locateDecodedField(button.dataset.inspectorActionPath));
    });
    container.querySelectorAll("[data-inspector-reference-key]").forEach((button) => {
      button.addEventListener("click", () => state.hooks?.onOpenRecord?.(button.dataset.inspectorReferenceKey));
    });
    $("#data-inspector-tree-q", container)?.addEventListener("input", (event) => {
      state.treeQuery = event.target.value;
      renderTree();
    });
    $("#data-inspector-expand", container)?.addEventListener("click", () => setAllBranches(true));
    $("#data-inspector-collapse", container)?.addEventListener("click", () => setAllBranches(false));
    container.querySelectorAll("[data-tree-view]").forEach((button) => {
      button.addEventListener("click", () => {
        state.treeView = button.dataset.treeView;
        container.querySelectorAll("[data-tree-view]").forEach((other) => {
          const active = other.dataset.treeView === state.treeView;
          other.classList.toggle("is-active", active);
          other.setAttribute("aria-pressed", String(active));
        });
        renderTree();
      });
    });
    $("#data-inspector-copy-path", container)?.addEventListener("click", (event) => {
      copyToClipboard(event.currentTarget, source.path || record.id);
    });
    $("#data-inspector-copy-json", container)?.addEventListener("click", (event) => {
      copyToClipboard(event.currentTarget, structureJson(record));
    });
    $("#data-inspector-load-raw", container)?.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      button.textContent = ui("Loading…", "正在加载…");
      try {
        const response = await fetch(source.href, { cache: "no-store" });
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        const text = await response.text();
        const shown = text.slice(0, RAW_PREVIEW_LIMIT);
        const section = $("#data-inspector-raw-section", container);
        section.hidden = false;
        $("#data-inspector-raw", container).innerHTML = `<pre>${esc(shown)}</pre>${
          text.length > shown.length
            ? `<p class="data-inspector-description">${esc(ui(
              "Preview limited to the first 1,000,000 characters; open the raw source for the complete file.",
              "预览限于前 1,000,000 个字符；请打开原始文件查看完整内容。",
            ))}</p>`
            : ""}`;
        section.scrollIntoView({ behavior: "smooth", block: "start" });
        button.textContent = ui("Raw source loaded", "原始文件已加载");
      } catch (error) {
        button.disabled = false;
        button.textContent = `${ui("Load failed", "加载失败")}: ${error.message}`;
      }
    });
  }

  function copyToClipboard(button, text) {
    if (!text) return;
    const label = button.textContent;
    navigator.clipboard?.writeText(text).then(() => {
      button.textContent = ui("Copied", "已复制");
      setTimeout(() => { button.textContent = label; }, 1400);
    }).catch(() => {
      button.textContent = ui("Copy failed", "复制失败");
      setTimeout(() => { button.textContent = label; }, 1400);
    });
  }

  // ------------------------------------------------------------- selection ---

  async function loadShard(entry) {
    const key = `${entry._datasetId}/${entry.shard}`;
    if (state.shardCache.has(key)) return state.shardCache.get(key);
    const promise = fetch(shardPath(entry), { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return response.json();
    });
    promise.catch(() => state.shardCache.delete(key));
    state.shardCache.set(key, promise);
    return promise;
  }

  // Render one record into `host`, the Data page's viewer pane. The hooks hand
  // navigation back to the page controller: `onCatalogTerm(term, entry)` for a
  // catalog-term button, `onOpenRecord(key)` for a resolved stored reference.
  async function showRecord(host, entry, hooks = {}) {
    if (!host || !entry) return;
    state.container = host;
    state.hooks = hooks;
    const key = entry._key;
    if (state.selectedKey !== key) {
      state.selectedRecord = null;
      state.treeQuery = "";
    }
    state.selectedKey = key;
    state.selectedEntry = entry;
    host.innerHTML = `<div class="data-inspector-empty">${esc(ui("Loading record…", "正在加载记录…"))}</div>`;
    try {
      const shard = await loadShard(entry);
      if (state.selectedKey !== key || state.container !== host) return;
      const record = (shard.records || []).find((candidate) => candidate.id === entry.id);
      if (!record) throw new Error("record is absent from its declared shard");
      state.selectedRecord = record;
      renderDetail();
    } catch (error) {
      if (state.selectedKey !== key || state.container !== host) return;
      host.innerHTML = `<div class="data-inspector-empty is-error">${esc(error.message)}</div>`;
    }
  }

  function clearSelection() {
    state.selectedKey = "";
    state.selectedEntry = null;
    state.selectedRecord = null;
  }

  // ------------------------------------------------------------------ load ---

  function catalog() {
    return {
      ok: true,
      datasets: state.datasets.map(({ descriptor, manifest }) => ({
        id: descriptor.id,
        title: descriptor.title || manifest.title || descriptor.id,
        description: descriptor.description || manifest.description || "",
        count: (manifest.catalog || []).length,
      })),
      records: state.records,
    };
  }

  async function loadCatalog() {
    const response = await fetch(ROOT_PATH, { cache: "no-store" });
    if (!response.ok) throw new Error(`${ROOT_PATH}: ${response.status} ${response.statusText}`);
    state.root = await response.json();
    const descriptors = state.root?.datasets || [];
    const results = await Promise.all(descriptors.map(async (descriptor) => {
      const reply = await fetch(datasetPath(descriptor), { cache: "no-store" });
      if (!reply.ok) throw new Error(`${descriptor.id}: ${reply.status} ${reply.statusText}`);
      return { descriptor, manifest: await reply.json() };
    }));
    state.datasets = results;
    state.datasetTone = new Map(results.map(({ descriptor }, index) => [descriptor.id, index % 6]));
    state.records = results.flatMap(({ descriptor, manifest }) => (
      (manifest.catalog || []).map((entry) => {
        const record = {
          ...entry,
          _datasetId: descriptor.id,
          _datasetTitle: descriptor.title || manifest.title || descriptor.id,
          _key: `${descriptor.id}:${entry.id}`,
          _folder: folderKey(entry.sourcePath || entry.id),
        };
        record._search = buildSearchText({
          ...record,
          tags: [descriptor.id, descriptor.title, ...(entry.tags || [])],
        });
        return record;
      })
    ));
    return catalog();
  }

  // The catalog and every dataset manifest load once (detail shards load per
  // record). Resolves to { ok, datasets, records } or { ok: false, error }.
  function load() {
    if (!state.loadPromise) {
      state.loadPromise = loadCatalog().catch((error) => ({ ok: false, error: error.message }));
    }
    return state.loadPromise;
  }

  window.WebUI.decodedInspector = {
    load,
    showRecord,
    clearSelection,
    find: (datasetId, recordId) => state.records.find((entry) => (
      entry.id === recordId && (!datasetId || entry._datasetId === datasetId)
    )) || null,
    byKey: (key) => state.records.find((entry) => entry._key === key) || null,
    queryMatcher,
    comparator,
    sortOptions,
    rowHtml,
    statusLabel,
    statusClass,
    toneClass,
  };
  window.WebUI.dataInspectorShell = {
    bindFilterSections,
    formatBytes,
    copyToClipboard,
  };
})();
