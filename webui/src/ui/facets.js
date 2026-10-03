// Declarative multi-select facet groups for a page's left-hand filter panel.
//
// A page declares its chip groups once; the model owns the active values, the
// chip rendering (through WebUI.filters.buildChips), faceted per-chip counts,
// the filter-section "(n)" badges, matching, reset, and URL/storage
// persistence. Semantics everywhere: OR within a group ("any" of its active
// values), AND across groups; a group with nothing active does not constrain.
//
//   const facets = WebUI.facets.create({
//     groups: [
//       { id: "kind", container: "#x-kind-filter", section: "x-kind",
//         values: (item) => item.kind,             // value, array of values, or null
//         label: (value) => kindLabel(value), order: "count", param: "kind" },
//       { id: "tag", container: "#x-tag-filter", values: (item) => item.tags },
//     ],
//     predicate: (item) => matchesSearch(item),    // optional non-facet filters
//     onChange: () => applyFilters(),
//   });
//   facets.render(items);                         // after data loads (and on locale change)
//   const shown = facets.filter();                // or facets.filter(items) / facets.matches(item)
//
// Groups whose items come from elsewhere (a server-side query) omit `values`
// and give `items` (chip list) plus `counts`; `matches()` ignores such a group
// and the caller applies its active values itself.
//
// Page conventions (every list page uses this model: Story in app_tree.js,
// Assets, Gameplay, Characters, Audio, Text, Updates and the Data page; Map's
// layer checkboxes and Recovery are not filter groups):
//   * chip counts are dataset totals (countMode: "total") on every page; the
//     Data page's store groups carry server counts;
//   * search stays outside `predicate`, so typing never recounts chips (Audio
//     media alone is tens of thousands of records); each page applies its
//     search after facets.filter(), and ranking stays page-owned;
//   * values() must not return "": an empty value is dropped, so a page that
//     needs one maps it to a sentinel (Assets uses "(root)");
//   * a union across groups (Gameplay's per-kind type groups) is written as a
//     `match` that reads the other groups' state;
//   * state API: active(id) (a copy), has, set(id, values), toggle(id, value,
//     on), reset({ only }), isFiltered(id?), activeCount(id?), counts(id);
//     every mutator takes { silent: true } to skip onChange;
//   * persistence: toParams/fromParams write one repeated URL parameter per
//     active value (?kind=a&kind=b, so values may contain commas) for groups
//     that declare `param`; snapshot()/restore() round-trip a plain
//     { groupId: [values] } object for storage.
// The Data page Files mode is the reference consumer.
(() => {
  const WebUI = window.WebUI;
  const { $ } = WebUI;

  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

  function resolveEl(ref) {
    return typeof ref === "string" ? $(ref) : ref || null;
  }

  function asList(value) {
    if (value == null || value === "") return [];
    if (Array.isArray(value)) return value.filter((entry) => entry != null && entry !== "");
    if (value instanceof Set) return [...value].filter((entry) => entry != null && entry !== "");
    return [value];
  }

  function lookup(source, value) {
    if (source == null) return undefined;
    if (typeof source === "function") return source(value);
    if (source instanceof Map) return source.get(value);
    if (typeof source === "object") return source[value];
    return undefined;
  }

  // Group options (all but `id` optional):
  //   id         unique key (state, onChange info, snapshot keys)
  //   container  chip wrapper element or selector; a group without one is
  //              state-only (still matched and persisted, never rendered)
  //   section    data-filter-section key whose "(n)" badge shows the active count
  //   values     (item) => value | value[] | Set | null   the item's values
  //   items      chips to show: array (or () => array) of values or
  //              { value, label, count, title, className }; default: every
  //              value `values` yields over the rendered items
  //   counts     Map | object | (value) => number   explicit counts (server-side
  //              groups); otherwise counted from the items
  //   icon       (value) => image URL    optional decorative chip icon
  //   label      (value) => string        title  (value) => string (tooltip; an
  //              `items` entry's own `title` wins)
  //   className  string | (value) => string   extra chip classes
  //   order      "natural" (by label; the default for derived values) |
  //              "count" (desc, then label) | "none" (keep the `items` order;
  //              the default when `items` is given) | array of values |
  //              (a, b) => n
  //   single     radio-style: at most one active value (clicking it again clears)
  //   mode       "any" (default, OR within the group) | "all" (item needs every
  //              active value)
  //   match      (item, activeSet) => bool   custom test replacing `mode`
  //   param      URL parameter name for toParams/fromParams
  //   hideEmpty  hide chips whose count is 0 (active chips always stay)
  //   countMode  overrides the model's countMode for this group
  //
  // Model options:
  //   groups     array of group options
  //   predicate  (item) => bool   non-facet filters (search text, toggles); it
  //              narrows both `filter()` and the chip counts
  //   countMode  "faceted" (default): a chip counts the items that pass every
  //              *other* group and the predicate, i.e. what selecting it would
  //              add; "total": the items that pass the predicate only
  //   onChange   (info) => void after a user toggle, set(), reset() or
  //              fromParams(); info = { reason, group, value, on }
  //   chipClassName  extra class(es) for every chip (e.g. "kind-chip")
  function create(options = {}) {
    const groups = (options.groups || []).map((spec) => ({
      spec,
      id: String(spec.id),
      active: new Set(),
      counts: new Map(),
    }));
    const byId = new Map(groups.map((group) => [group.id, group]));
    let lastItems = [];
    let cache = null; // { items, values: Array<Array<values>|null per group> }

    function groupFor(id) {
      const group = byId.get(String(id));
      if (!group) throw new Error(`WebUI.facets: unknown group ${id}`);
      return group;
    }

    function itemValues(group, item) {
      return group.spec.values ? asList(group.spec.values(item)) : null;
    }

    function groupMatches(group, item, values = itemValues(group, item)) {
      if (!group.active.size || values === null) return true;
      if (group.spec.match) return !!group.spec.match(item, group.active);
      if (group.spec.mode === "all") {
        for (const value of group.active) if (!values.includes(value)) return false;
        return true;
      }
      return values.some((value) => group.active.has(value));
    }

    function passesPredicate(item) {
      return typeof options.predicate === "function" ? !!options.predicate(item) : true;
    }

    function matches(item) {
      if (!passesPredicate(item)) return false;
      return groups.every((group) => groupMatches(group, item));
    }

    function filter(items = lastItems) {
      return (items || []).filter(matches);
    }

    function valueCache(items) {
      if (cache && cache.items === items) return cache;
      cache = {
        items,
        values: items.map((item) => groups.map((group) => itemValues(group, item))),
      };
      return cache;
    }

    // One pass over the items: an item that fails no group counts for every
    // group; one that fails exactly one group counts only for that group
    // (selecting a value there would add it); others count nowhere.
    function computeCounts(items) {
      const { values } = valueCache(items);
      const universe = groups.map(() => new Set());
      for (const group of groups) group.counts = new Map();
      const bump = (group, list) => {
        for (const value of new Set(list)) group.counts.set(value, (group.counts.get(value) || 0) + 1);
      };
      items.forEach((item, index) => {
        const row = values[index];
        groups.forEach((group, g) => {
          if (row[g]) for (const value of row[g]) universe[g].add(value);
        });
        if (!passesPredicate(item)) return;
        const failing = [];
        groups.forEach((group, g) => {
          if (row[g] !== null && !groupMatches(group, item, row[g])) failing.push(g);
        });
        groups.forEach((group, g) => {
          if (!row[g]) return;
          const mode = group.spec.countMode || options.countMode || "faceted";
          const own = group.spec.mode === "all" || group.spec.match;
          let counts;
          if (mode === "total") counts = true;
          else if (own) counts = failing.length === 0;
          else counts = failing.length === 0 || (failing.length === 1 && failing[0] === g);
          if (counts) bump(group, row[g]);
        });
      });
      return universe;
    }

    function orderValues(group, values) {
      const spec = group.spec;
      const labelOf = (value) => String(spec.label ? spec.label(value) : value);
      const order = spec.order || "natural";
      if (order === "none") return values;
      if (Array.isArray(order)) {
        const rank = new Map(order.map((value, index) => [value, index]));
        return [...values].sort((a, b) => (rank.has(a) ? rank.get(a) : Infinity) - (rank.has(b) ? rank.get(b) : Infinity)
          || collator.compare(labelOf(a), labelOf(b)));
      }
      if (typeof order === "function") return [...values].sort(order);
      if (order === "count") {
        return [...values].sort((a, b) => (group.counts.get(b) || 0) - (group.counts.get(a) || 0)
          || collator.compare(labelOf(a), labelOf(b)));
      }
      return [...values].sort((a, b) => collator.compare(labelOf(a), labelOf(b)));
    }

    function chipItems(group, universe) {
      const spec = group.spec;
      let listed = typeof spec.items === "function" ? spec.items() : spec.items;
      let entries;
      if (Array.isArray(listed)) {
        entries = listed.map((entry) => (entry && typeof entry === "object" && "value" in entry ? { ...entry } : { value: entry }));
      } else {
        entries = [...(universe || [])].map((value) => ({ value }));
      }
      for (const entry of entries) {
        if (entry.count == null) {
          const explicit = lookup(spec.counts, entry.value);
          entry.count = explicit != null ? explicit : (spec.values ? group.counts.get(entry.value) || 0 : undefined);
        }
      }
      // An active value absent from the data stays visible so it can be cleared.
      const present = new Set(entries.map((entry) => entry.value));
      for (const value of group.active) if (!present.has(value)) entries.push({ value, count: 0 });
      if (!Array.isArray(listed) || (spec.order && spec.order !== "none")) {
        const ordered = orderValues(group, entries.map((entry) => entry.value));
        const byValue = new Map(entries.map((entry) => [entry.value, entry]));
        entries = ordered.map((value) => byValue.get(value));
      }
      if (spec.hideEmpty) entries = entries.filter((entry) => entry.count || group.active.has(entry.value));
      return entries.map((entry) => {
        const own = typeof spec.className === "function" ? spec.className(entry.value) : spec.className;
        const classes = [options.chipClassName, entry.className ?? own, entry.count === 0 ? "is-facet-empty" : ""]
          .filter(Boolean).join(" ");
        return {
          ...entry,
          label: entry.label ?? (spec.label ? spec.label(entry.value) : String(entry.value)),
          icon: entry.icon ?? (spec.icon ? spec.icon(entry.value) : ""),
          className: classes,
        };
      });
    }

    function syncBadges() {
      const counts = {};
      for (const group of groups) {
        if (!group.spec.section) continue;
        counts[group.spec.section] = (counts[group.spec.section] || 0) + group.active.size;
      }
      WebUI.setFilterSectionActiveCounts?.(counts);
    }

    function renderGroup(group, universe) {
      const container = resolveEl(group.spec.container);
      if (!container) return;
      const single = !!group.spec.single;
      WebUI.filters.buildChips(container, chipItems(group, universe), {
        active: single ? ([...group.active][0] ?? "") : group.active,
        single,
        prune: false,
        title: (value, item) => item.title || (group.spec.title ? group.spec.title(value) : ""),
        onToggle: (value, info) => {
          if (single) {
            group.active.clear();
            if (value !== "") group.active.add(value);
            changed({ reason: "toggle", group: group.id, value: info.value, on: value !== "" });
          } else {
            changed({ reason: "toggle", group: group.id, value, on: !!info.on });
          }
        },
      });
    }

    function render(items) {
      if (items) lastItems = items;
      const universes = computeCounts(lastItems);
      groups.forEach((group, g) => renderGroup(group, universes[g]));
      syncBadges();
      return api;
    }

    function changed(info) {
      render();
      options.onChange?.(info);
    }

    function set(id, values, { silent = false } = {}) {
      const group = groupFor(id);
      group.active.clear();
      for (const value of asList(values)) {
        group.active.add(value);
        if (group.spec.single) break;
      }
      if (silent) render();
      else changed({ reason: "set", group: group.id });
      return api;
    }

    function toggle(id, value, on, { silent = false } = {}) {
      const group = groupFor(id);
      const next = on == null ? !group.active.has(value) : !!on;
      if (group.spec.single) group.active.clear();
      if (next) group.active.add(value);
      else group.active.delete(value);
      if (silent) render();
      else changed({ reason: "toggle", group: group.id, value, on: next });
      return api;
    }

    function reset({ silent = false, only = null } = {}) {
      for (const group of groups) {
        if (!only || only.includes(group.id)) group.active.clear();
      }
      if (silent) render();
      else changed({ reason: "reset" });
      return api;
    }

    // URL persistence: one repeated parameter per active value
    // (`?kind=a&kind=b`), so values may contain commas. Groups without `param`
    // are not written.
    function toParams(params) {
      for (const group of groups) {
        const name = group.spec.param;
        if (!name) continue;
        params.delete(name);
        for (const value of group.active) params.append(name, String(value));
      }
      return params;
    }

    function fromParams(params, { silent = false } = {}) {
      let touched = false;
      for (const group of groups) {
        const name = group.spec.param;
        if (!name || !params.has(name)) continue;
        touched = true;
        group.active.clear();
        for (const value of params.getAll(name)) {
          if (value === "") continue;
          group.active.add(value);
          if (group.spec.single) break;
        }
      }
      if (touched) {
        if (silent) render();
        else changed({ reason: "params" });
      }
      return touched;
    }

    // Storage persistence: a plain { groupId: [values] } object.
    function snapshot() {
      const out = {};
      for (const group of groups) if (group.active.size) out[group.id] = [...group.active];
      return out;
    }

    function restore(state, { silent = true } = {}) {
      for (const group of groups) {
        group.active.clear();
        for (const value of asList(state?.[group.id])) group.active.add(value);
      }
      if (silent) render();
      else changed({ reason: "set" });
      return api;
    }

    const api = {
      render,
      matches,
      filter,
      active: (id) => new Set(groupFor(id).active),
      has: (id, value) => groupFor(id).active.has(value),
      set,
      toggle,
      reset,
      isFiltered: (id) => (id != null ? groupFor(id).active.size > 0 : groups.some((group) => group.active.size > 0)),
      activeCount: (id) => (id != null ? groupFor(id).active.size : groups.reduce((sum, group) => sum + group.active.size, 0)),
      counts: (id) => new Map(groupFor(id).counts),
      groupIds: () => groups.map((group) => group.id),
      toParams,
      fromParams,
      snapshot,
      restore,
      syncBadges,
      // Items changed shape without a new array (mutated in place): drop the value cache.
      invalidate: () => {
        cache = null;
        return api;
      },
    };
    return api;
  }

  WebUI.facets = { create };
})();
