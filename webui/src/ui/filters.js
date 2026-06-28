// Shared filter-control helpers used by every view's left-hand filter panel.
// Each view previously hand-rolled its own chip builder and an identical panel
// collapse/expand quartet; these two helpers replace all of those copies.
(() => {
  const { $, storageGet, storageSet, formatNumber } = window.WebUI;
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const PANEL_STORAGE_KEY = "webui_filters_collapsed";

  function isMobileLayout() {
    return !!(window.matchMedia && window.matchMedia(MOBILE_LAYOUT_QUERY).matches);
  }

  function resolveEl(ref) {
    return typeof ref === "string" ? $(ref) : ref;
  }

  function resolveCount(countOpt, value, item) {
    if (item && item.count != null) return item.count;
    if (countOpt == null) return undefined;
    if (typeof countOpt === "function") return countOpt(value, item);
    if (countOpt instanceof Map) return countOpt.get(value);
    if (typeof countOpt === "object") return countOpt[value];
    return undefined;
  }

  // Render a set of filter chips into `container`.
  //
  //   container  element or selector for the chip wrapper
  //   items      array of values (string/number) or { value, label, count, title, className }
  //              (a per-item className overrides opts.className for that chip)
  //   opts:
  //     active      Set (multi-select) | string (single-select group)
  //     single      true for radio-style single-select (caller re-renders on toggle)
  //     className   extra class(es) appended to "chip" (e.g. "asset-filter-chip")
  //     label       (value, item) => string  (defaults to String(value))
  //     count       counts as a function | Map | object keyed by value (optional)
  //     formatCount (count) => string        (defaults to formatNumber)
  //     title       (value, item) => string  (optional tooltip)
  //     prune       drop active entries absent from items (multi-select; default true)
  //     onToggle    (value, info) => void     called after a chip is clicked
  function buildChips(container, items, opts = {}) {
    const wrap = resolveEl(container);
    if (!wrap) return;

    const single = opts.single === true;
    const active = opts.active;
    const labelOpt = opts.label;
    const formatCount = opts.formatCount || formatNumber;
    const normalized = (items || []).map((item) =>
      item && typeof item === "object" && "value" in item ? item : { value: item });

    if (!single && opts.prune !== false && active && typeof active.delete === "function") {
      const present = new Set(normalized.map((item) => item.value));
      for (const value of [...active]) {
        if (!present.has(value)) active.delete(value);
      }
    }

    const fragment = document.createDocumentFragment();
    for (const item of normalized) {
      const value = item.value;
      const labelText = item.label != null
        ? item.label
        : (typeof labelOpt === "function" ? labelOpt(value, item) : String(value));
      const count = resolveCount(opts.count, value, item);

      const extraClass = item.className != null ? item.className : opts.className;
      const chip = document.createElement("span");
      chip.className = extraClass ? `chip ${extraClass}` : "chip";
      chip.dataset.value = value;
      chip.textContent = `${labelText}${count ? ` (${formatCount(count)})` : ""}`;
      if (opts.title) {
        const title = typeof opts.title === "function" ? opts.title(value, item) : opts.title;
        if (title) chip.title = title;
      }

      const isOn = single
        ? value === active
        : !!(active && typeof active.has === "function" && active.has(value));
      chip.classList.toggle("on", isOn);

      chip.addEventListener("click", () => {
        if (single) {
          const next = value === active ? "" : value;
          opts.onToggle?.(next, { value, single: true });
          return;
        }
        let on = isOn;
        if (active && typeof active.has === "function") {
          on = !active.has(value);
          if (on) active.add(value);
          else active.delete(value);
          chip.classList.toggle("on", on);
        }
        opts.onToggle?.(value, { on, active });
      });

      fragment.appendChild(chip);
    }
    wrap.replaceChildren(fragment);
  }

  // Manage the collapse/expand of a whole filter panel, with persistence shared
  // across views via PANEL_STORAGE_KEY.
  //
  //   opts:
  //     panel/toggle/left  elements or selectors
  //     storageKey         persistence key (defaults to the shared key)
  //     isMobile           () => bool fallback when no stored preference
  //     labels             (collapsed) => string for the toggle's text (optional)
  //     onChange           (collapsed) => void after each change (optional)
  //     bindToggle         auto-bind the toggle's click (default true)
  //
  // Returns { collapsed, sync(), set(collapsed, {persist}), toggle() }.
  function createPanelToggle(opts = {}) {
    const panel = resolveEl(opts.panel);
    const toggleBtn = resolveEl(opts.toggle);
    const left = resolveEl(opts.left);
    const storageKey = opts.storageKey || PANEL_STORAGE_KEY;
    const isMobile = opts.isMobile || isMobileLayout;
    const labelFor = opts.labels;

    const api = { collapsed: false };

    api.sync = () => {
      if (panel) panel.hidden = api.collapsed;
      if (left) left.classList.toggle("filters-collapsed", api.collapsed);
      if (toggleBtn) {
        toggleBtn.setAttribute("aria-expanded", String(!api.collapsed));
        if (labelFor) {
          const text = labelFor(api.collapsed);
          if (text != null) toggleBtn.textContent = text;
        }
      }
    };

    api.set = (collapsed, { persist = true } = {}) => {
      api.collapsed = !!collapsed;
      if (persist && storageKey) storageSet(storageKey, api.collapsed ? "1" : "0");
      api.sync();
      opts.onChange?.(api.collapsed);
    };

    api.toggle = () => api.set(!api.collapsed);

    const stored = storageGet(storageKey);
    api.collapsed = stored === "1" ? true : stored === "0" ? false : isMobile();

    if (opts.bindToggle !== false && toggleBtn) {
      toggleBtn.addEventListener("click", () => api.toggle());
    }
    api.sync();
    return api;
  }

  window.WebUI.filters = { buildChips, createPanelToggle };
})();
