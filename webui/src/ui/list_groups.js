// Collapsible list groups shared by the Gameplay and Production catalogs.
// Each page keeps its own collapsed-group set (owned by the returned
// controller), renders groups as <details data-list-group>, and reopens a
// collapsed group before scrolling a selected row into view.
//
//   const groups = WebUI.listGroups.create();
//   host.innerHTML = groups.section({ id, title, count, icon, className, body });
//   groups.bind(host);           // remember user collapse/expand per group id
//   groups.reveal(row);          // open the row's group, then scroll to it
//   WebUI.listGroups.counts(rows, (row) => key)  // Map key -> row count, one pass
(() => {
  const WebUI = window.WebUI;
  const esc = (value) => WebUI.escapeHtml(value);

  function counts(rows, keyOf) {
    const result = new Map();
    for (const row of rows) {
      const key = keyOf(row);
      result.set(key, (result.get(key) || 0) + 1);
    }
    return result;
  }

  function create() {
    const collapsed = new Set();
    // Opening markup only when `body` is omitted, so a caller that streams rows
    // can close the group itself with "</details>".
    function section({ id, title, count, icon = "", className = "", body }) {
      const open = `<details class="list-group-section${className ? ` ${className}` : ""}" data-list-group="${esc(id)}"${collapsed.has(id) ? "" : " open"}>`
        + `<summary class="list-group-summary">${icon}<strong>${esc(title)}</strong><span>${WebUI.formatNumber(count)}</span></summary>`;
      return body === undefined ? open : `${open}${body}</details>`;
    }
    function bind(host) {
      host.querySelectorAll("[data-list-group]").forEach((group) => {
        group.addEventListener("toggle", () => {
          if (group.open) collapsed.delete(group.dataset.listGroup);
          else collapsed.add(group.dataset.listGroup);
        });
      });
    }
    function reveal(row) {
      const group = row?.closest("[data-list-group]");
      if (group) { collapsed.delete(group.dataset.listGroup); group.open = true; }
      row?.scrollIntoView({ block: "center", behavior: "smooth" });
    }
    return { section, bind, reveal };
  }

  WebUI.listGroups = { create, counts };
})();
