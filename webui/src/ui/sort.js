// Shared category/direction controls. The hidden source select retains page
// values and change handlers, including older direction-bearing URL values.
// Pages wrap their comparator with sorting.comparator(id, compare).
(() => {
  const bindings = new Map();
  const specs = {
    sort: { lines: ["lines-asc", "lines-desc"] },
    "gameplay-sort": { title: ["title", "title-desc"], rarity: ["rarity-asc", "rarity-desc"] },
    "production-sort": { title: ["title", "title-desc"], rarity: ["rarity-asc", "rarity-desc"] },
    "asset-sort": { size: ["size-asc", "size-desc"] },
    "audio-sort": { duration: ["duration-asc", "duration-desc"] },
    "updates-sort": {}, "data-files-sort": {}, "reference-sort": {},
    "map-sort": {}, "recovery-sort": {},
  };
  const descending = new Set(["size-delta", "line-delta", "stories", "bytes", "files"]);
  const text = (en, zh) => window.WEBUI_UI_LOCALE === "en" ? en : zh;
  function sync(binding) {
    const { source, category, order: direction, pairs } = binding;
    const groups = [];
    for (const option of source.options) {
      const pair = Object.entries(pairs).find(([, values]) => values.includes(option.value));
      const key = pair ? pair[0] : option.value;
      if (groups.some((group) => group.key === key)) continue;
      const label = pair ? ({ lines: text("Line count", "行数"), title: text("Name", "名称"), rarity: text("Rarity", "稀有度"), size: text("File size", "文件大小"), duration: text("Duration", "时长") })[key]
        : option.textContent.replace(/\s*\(A-Z\)/g, "");
      const disabled = pair ? pair[1].every((value) => [...source.options].find((item) => item.value === value)?.disabled) : option.disabled;
      groups.push({ key, label, disabled });
    }
    const signature = JSON.stringify(groups);
    if (binding.signature !== signature) {
      category.replaceChildren(...groups.map(({ key, label, disabled }) => Object.assign(new Option(label, key), { disabled })));
      binding.signature = signature;
    }
    const pair = Object.entries(pairs).find(([, values]) => values.includes(source.value));
    category.value = pair ? pair[0] : source.value;
    if (pair) binding.direction = pair[1].indexOf(source.value) ? "desc" : "asc";
    else if (binding.value !== source.value) binding.direction = descending.has(source.value) ? "desc" : "asc";
    binding.value = source.value;
    direction.options[0].textContent = text("Ascending ↑", "正序 ↑");
    direction.options[1].textContent = text("Descending ↓", "倒序 ↓");
    direction.value = binding.direction;
    direction.disabled = false;
    category.disabled = source.disabled;
    category.labels[0].textContent = text("Category", "类别");
    direction.labels[0].hidden = true;
    direction.setAttribute("aria-label", text("Sort direction", "排序方向"));
  }
  function mount(source, pairs) {
    if (bindings.get(source.id)?.source === source) return;
    const previous = bindings.get(source.id);
    const wrapper = document.createElement("div");
    wrapper.className = "sort-controls";
    source.before(wrapper);
    for (const label of source.labels) label.hidden = true;
    source.hidden = true;
    wrapper.append(source);
    const make = (suffix) => {
      const label = document.createElement("label");
      const select = document.createElement("select");
      select.id = `${source.id}-${suffix}`;
      label.htmlFor = select.id;
      const row = document.createElement("div");
      row.className = "sort-control";
      row.append(label, select);
      wrapper.append(row);
      return select;
    };
    const category = make("category"), direction = make("direction");
    direction.append(new Option("", "asc"), new Option("", "desc"));
    const binding = { source, category, order: direction, pairs, direction: "asc" };
    if (previous) {
      binding.direction = previous.direction;
      binding.value = source.value;
    }
    bindings.set(source.id, binding);
    const notify = () => source.dispatchEvent(new Event("change", { bubbles: true }));
    category.addEventListener("change", () => {
      const values = pairs[category.value];
      binding.direction = (values && category.value !== "title") || descending.has(category.value) ? "desc" : "asc";
      source.value = values ? values[binding.direction === "desc" ? 1 : 0] : category.value;
      sync(binding);
      notify();
    });
    direction.addEventListener("change", () => {
      binding.direction = direction.value;
      const values = pairs[category.value];
      if (values) source.value = values[direction.value === "desc" ? 1 : 0];
      sync(binding);
      notify();
    });
    source.addEventListener("change", () => sync(binding));
    sync(binding);
  }
  function refresh() {
    for (const [id, pairs] of Object.entries(specs)) {
      const source = document.getElementById(id);
      if (source) { mount(source, pairs); sync(bindings.get(id)); }
    }
  }
  window.WebUI.sorting = {
    refresh,
    comparator(id, compare) {
      const binding = bindings.get(id);
      const paired = binding && Object.values(binding.pairs).some((values) => values.includes(binding.source.value));
      const baseline = binding && descending.has(binding.source.value) ? "desc" : "asc";
      const sign = binding && !paired && binding.direction !== baseline ? -1 : 1;
      return (a, b) => sign * compare(a, b);
    },
  };
  document.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button?.id.endsWith("reset")) return;
    for (const binding of bindings.values()) {
      if (!button.closest("[role=tabpanel]")?.contains(binding.source)) continue;
      binding.direction = "asc";
      binding.value = null;
    }
    queueMicrotask(refresh);
  }, true);
  // Dynamic pages replace their sidebar; observe structure and option labels,
  // but ignore changes produced by our own controls to avoid render loops.
  const sourceSelector = Object.keys(specs).map((id) => `select[id="${id}"]`).join(",");
  new MutationObserver((records) => {
    if (records.some((record) => record.target.closest?.(sourceSelector)
      || [...record.addedNodes].some((node) => node.matches?.(sourceSelector) || node.querySelector?.(sourceSelector)))) refresh();
  }).observe(document.body, { childList: true, subtree: true, characterData: true });
  window.addEventListener("webui:ui-locale-changed", () => queueMicrotask(refresh));
  refresh();
})();
