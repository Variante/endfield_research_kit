// Optional export-source changes. Pages keep their current datasets and IDs;
// missing/invalid sidecars remove badges and their filters. Deleted IDs remain in the
// comparison and never create recovered page content.
(() => {
  const statuses = new Set(["added", "modified", "deleted"]);
  const pages = new Map();
  const available = new Set();
  const sourceTables = new Map();
  const pending = new Map();
  const files = new Map();
  const localeZh = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").toLowerCase().startsWith("zh");
  const ui = (en, zh) => localeZh() ? zh : en;
  const esc = (value) => window.WebUI.escapeHtml(value);
  const language = () => String(document.querySelector("#language")?.value || "CN").toUpperCase();
  const label = (status) => (localeZh()
    ? { added: "新增", modified: "修改", deleted: "删除" }
    : { added: "Added", modified: "Modified", deleted: "Deleted" })[status] || "";
  async function load(page) {
    if (pending.has(page)) return pending.get(page);
    const promise = fetchPage(page);
    pending.set(page, promise);
    await promise;
    pending.delete(page);
  }
  async function fetchPage(page) {
    try {
      const response = await fetch(`data/updates/${encodeURIComponent(page)}.json`, { cache: "no-store" });
      const payload = response.ok ? await response.json() : null;
      register(page, payload);
    } catch (_) { register(page, null); }
  }
  function register(page, payload) {
    const versions = page === "characters" ? [3, 4] : [1, 2, 3];
    const valid = payload?.available === true && versions.includes(payload.schemaVersion)
      && (page === "characters" || payload.page === page) && Array.isArray(payload.entries);
    if (valid) available.add(page);
    else available.delete(page);
    pages.set(page, new Map(valid ? payload.entries.filter((entry) => statuses.has(entry?.status))
      .map((entry) => [String(entry.id || entry.characterKey || entry.characterId || ""), entry]).filter(([id]) => id) : []));
    if (page === "reference") {
      sourceTables.clear();
      for (const [id, entry] of pages.get(page)) {
        const table = id.split("/")[0].replace(/\.json$/, "");
        if (!sourceTables.has(table)) sourceTables.set(table, new Set());
        sourceTables.get(table).add(entry.status);
      }
    }
  }
  // Table facets use the sidecar index without fetching every Text payload.
  function sourceTableStatuses(table) {
    return [...(sourceTables.get(String(table || "").replace(/\.json$/, "")) || [])];
  }
  function filterGroup(prefix, values, options = {}) {
    return { id: "update", container: `#${prefix}-update-filter`, section: `${prefix}-updates`,
      values, items: [...statuses], label, ...options };
  }
  function filterSection(prefix) {
    return `<section class="filter-section is-collapsed" data-filter-section="${prefix}-updates" data-default-collapsed="1" hidden>
      <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="${prefix}-update-filter-body"><span id="${prefix}-update-filter-label">${ui("Version changes", "版本变化")}</span></button>
      <div id="${prefix}-update-filter-body" class="filter-section-body" hidden><div id="${prefix}-update-filter" class="chips" data-multi="1"></div></div></section>`;
  }
  function syncFilter(prefix, page = prefix, facets = null) {
    const cleared = !available.has(page) && !!facets?.active("update").size;
    if (cleared) facets.reset({ silent: true, only: ["update"] });
    const title = document.querySelector(`#${prefix}-update-filter-label`);
    if (title) {
      title.textContent = ui("Version changes", "版本变化");
      title.closest(".filter-section").hidden = !available.has(page);
    }
    return cleared;
  }
  // Dynamically rendered pages without their own section binding use this.
  function bindFilter(prefix) {
    const body = document.querySelector(`#${prefix}-update-filter-body`);
    const button = body?.previousElementSibling;
    if (!button) return;
    button.addEventListener("click", () => {
      body.hidden = !body.hidden;
      button.setAttribute("aria-expanded", String(!body.hidden));
      body.parentElement.classList.toggle("is-collapsed", body.hidden);
    });
  }
  function entries(page, id) {
    return [...new Set(Array.isArray(id) ? id : [id])].map((key) => pages.get(page)?.get(String(key || ""))).filter(Boolean);
  }
  function status(page, id) {
    if (Array.isArray(id)) {
      const changes = entries(page, id).map((entry) => entry.status);
      if (!changes.length) return "";
      return changes.every((change) => change === changes[0]) ? changes[0] : "modified";
    }
    return pages.get(page)?.get(String(id || ""))?.status || "";
  }
  function html(page, id) {
    const change = status(page, id);
    if (!change) return "";
    const title = localeZh() ? "相较上次导出，关联的游戏源数据发生变化" : "Linked game source data changed since the previous export";
    return `<span class="version-update-badge" data-update-status="${change}" title="${title}">${label(change)}</span>`;
  }
  function badge(change, title = "") {
    return statuses.has(change) ? `<span class="version-update-badge" data-update-status="${change}" title="${esc(title || ui("Changed since the previous export", "相较上次导出发生变化"))}">${label(change)}</span>` : "";
  }
  function visibleFields(change) {
    return (change.fields || []).filter((field) => {
      const path = field.path || [];
      if (path[0] === "text" && path.length > 1) return String(path[1]).toUpperCase() === language();
      if (path[0] === "languages" && path.length > 1) return String(path[1]).toUpperCase() === language();
      return true;
    });
  }
  function changes(page, id) {
    const result = new Map();
    for (const entry of entries(page, id)) for (const change of entry.changes || []) {
      const fields = visibleFields(change);
      if (fields.length) {
        const key = JSON.stringify([change.source, fields]);
        const previous = result.get(key);
        const owner = String(entry.id || entry.characterKey || entry.characterId || "");
        result.set(key, { ...change, fields,
          owners: [...new Set([...(previous?.owners || []), owner])] });
      }
    }
    return [...result.values()];
  }
  const sourceKey = (source) => String(source || "").replace(/\.json\//, "/");
  const sourceChanges = (source) => changes("reference", sourceKey(source));
  const sourceHtml = (source) => html("reference", sourceKey(source));
  function valueHtml(field, key) {
    if (!Object.hasOwn(field, key)) return `<span class="version-update-absent">${ui("Absent", "无此项")}</span>`;
    const value = field[key];
    return `<span class="version-update-value">${esc(typeof value === "string" ? value : JSON.stringify(value, null, 2))}</span>`;
  }
  function pathLabel(path) {
    const parts = [...path];
    if (parts[0] === "record") parts.shift();
    if (parts[0] === "text") return `${ui("Text", "文本")} · ${parts.slice(1).join(" / ")}`;
    return parts.join(" / ") || ui("Content", "内容");
  }
  function changeTable(change) {
    // File hashes prove a byte change. The linked feed supplies the decoded
    // comparison where its reader has coverage; hashes alone are not content.
    if (fileKey(change.source)) {
      const rows = change.file ? [change.file] : fileEntries(change.source);
      return fileDetails(change.source, { rows: rows.length ? rows : [{ path: change.source, status: change.status }], open: true });
    }
    return `<div class="version-update-source"><div class="version-update-source-title">${badge(change.status)}<code>${esc(change.source)}</code></div>${change.owners?.length ? `<p class="version-update-note">${esc(change.owners.join(" · "))}</p>` : ""}
      <div class="version-update-table-wrap"><table class="version-update-table"><thead><tr><th>${ui("Field", "字段")}</th><th>${ui("Previous", "旧版")}</th><th>${ui("Current", "新版")}</th></tr></thead>
      <tbody>${change.fields.map((field) => `<tr data-update-status="${field.status}"><th scope="row">${esc(pathLabel(field.path || []))}${badge(field.status)}</th><td class="version-update-before">${valueHtml(field, "before")}</td><td class="version-update-after">${valueHtml(field, "after")}</td></tr>`).join("")}</tbody></table></div></div>`;
  }
  function detailsHtml(changeRows, { inline = false } = {}) {
    if (!changeRows.length) return "";
    const count = changeRows.reduce((sum, change) => sum + change.fields.length, 0);
    return `<details class="version-update-details${inline ? " is-inline" : ""}"${inline ? "" : " open"}><summary>${ui("What changed", "具体更新")} <span class="version-update-count">${count}</span></summary><div class="version-update-detail-content">${changeRows.map(changeTable).join("")}</div></details>`;
  }
  function panel(page, id) {
    const content = detailsHtml(changes(page, id));
    if (content || !entries(page, id).length) return content;
    const detailed = entries(page, id).every((entry) => Array.isArray(entry.changes));
    return `<details class="version-update-details" open><summary>${ui("What changed", "具体更新")}</summary><p class="version-update-note">${detailed
      ? ui("Changes are recorded in other languages. Select a compared language to view them.", "更新记录位于其他语言，切换到参与对比的语言即可查看。")
      : ui("This comparison contains a change label but no detailed content.", "此次对比记录了更新标签，尚未包含详细内容。")}</p></details>`;
  }
  function mark(node, change) {
    node.classList.add("version-update-content");
    node.dataset.versionUpdate = change;
  }
  function decorate(root, page, id) {
    if (!root) return;
    const rows = changes(page, id);
    const byId = new Map();
    for (const change of rows) {
      const key = change.source.slice(change.source.indexOf("/") + 1);
      if (!byId.has(key)) byId.set(key, []);
      byId.get(key).push(change);
    }
    root.querySelectorAll("[data-line-id], [data-update-source]").forEach((node) => {
      const matched = node.dataset.updateSource ? rows.filter((row) => row.source === node.dataset.updateSource)
        : byId.get(node.dataset.lineId) || [];
      if (!matched.length || node.querySelector(":scope > .version-update-details")) return;
      mark(node, matched.every((row) => row.status === "added") ? "added" : "modified");
      node.insertAdjacentHTML("beforeend", detailsHtml(matched, { inline: true }));
    });
    // Match complete displayed strings within this owner. Bare numbers are
    // excluded because identical stats need not share a source field.
    const textChanges = new Map();
    for (const row of rows) for (const field of row.fields) {
      if (typeof field.after === "string" && field.after.trim().length >= 3) textChanges.set(field.after.trim(), field.status);
    }
    root.querySelectorAll(".text, .reference-text-body, .reference-field-value, .characters-name strong, .gameplay-description, td, dd").forEach((node) => {
      if (node.closest(".version-update-details")) return;
      const change = textChanges.get(node.textContent.trim());
      if (change) mark(node, change);
    });
    decorateFiles(root);
  }
  function mount(root, page, id) {
    if (!root) return;
    root.querySelectorAll(":scope > .version-update-details").forEach((node) => node.remove());
    const content = panel(page, id);
    const header = root.firstElementChild?.tagName === "HEADER" ? root.firstElementChild : null;
    if (content) (header || root).insertAdjacentHTML(header ? "afterend" : "afterbegin", content);
    const reportedFiles = new Set(changes(page, id).map((row) => files.get(fileKey(row.source))).filter(Boolean));
    const extraFiles = fileEntries(linkedFiles(root)).filter((entry) => !reportedFiles.has(entry));
    const resources = fileDetails(extraFiles.map((entry) => entry.path));
    if (resources) {
      const preceding = root.querySelector(":scope > .version-update-details") || header;
      (preceding || root).insertAdjacentHTML(preceding ? "afterend" : "afterbegin", resources);
    }
    decorate(root, page, id);
  }
  function linkedFiles(root) {
    return [...root.querySelectorAll("img[src], video[src], audio[src], source[src], a[href], [data-map-file-path]")]
      .filter((node) => !node.closest(".version-update-details"))
      .map((node) => node.getAttribute("src") || node.getAttribute("href") || node.dataset.mapFilePath);
  }
  function mountFiles(root) {
    if (!root) return;
    root.querySelectorAll(":scope > .version-update-files").forEach((node) => node.remove());
    const content = fileDetails(linkedFiles(root));
    if (content) root.insertAdjacentHTML("beforeend", content);
    decorateFiles(root);
  }
  function fileKey(value) {
    let path = String(value || "").replace(/\\/g, "/");
    try { path = decodeURIComponent(path); } catch (_) { /* Preserve malformed spelling. */ }
    if (/^https?:/i.test(path)) {
      try { const url = new URL(path); if (url.origin !== window.location.origin) return ""; path = url.pathname; } catch (_) { return ""; }
    }
    if (/\/export_previous\//i.test(path)) return "";
    path = path.replace(/^.*?\/export_full\//i, "").replace(/^export_full\//i, "");
    path = path.split(/[?#]/)[0].replace(/^\/+/, "");
    if (path.startsWith("Data/")) path = "game/" + path.slice(5);
    else if (path.startsWith("Unity/")) path = "game/" + path;
    else if (path.startsWith("Game/")) path = "game/" + path.slice(5);
    else if (path.startsWith("Audio/")) path = "game/" + path;
    else if (/^(Texture2D|Mesh|Sprite|VideoClip|AnimationClip|Material)\//.test(path)) path = "game/Unity/" + path;
    return /^(game|raw)\//.test(path) && !path.split("/").some((part) => part === "." || part === "..") ? path : "";
  }
  async function loadFiles() {
    if (pending.has("files")) return pending.get("files");
    const promise = fetchFiles();
    pending.set("files", promise);
    await promise;
    pending.delete("files");
  }
  async function fetchFiles() {
    files.clear();
    available.delete("files");
    try {
      const response = await fetch("data/updates/latest.json", { cache: "no-store" });
      const payload = response.ok ? await response.json() : null;
      if (!payload || !Array.isArray(payload.entries) || ![1, 2, 3, 4].includes(payload.schemaVersion)) return;
      available.add("files");
      for (const entry of payload.entries) {
        if (!statuses.has(entry.status)) continue;
        for (const path of [entry.path, entry.asset_rel, entry.new_asset_rel, entry.new_asset_export_rel]) {
          const key = fileKey(path);
          if (key) files.set(key, entry);
        }
      }
    } catch (_) { /* The comparison is optional. */ }
  }
  function fileEntries(values) {
    const found = new Set();
    const visit = (value) => {
      if (typeof value === "string") {
        const entry = files.get(fileKey(value));
        if (entry) found.add(entry);
      } else if (Array.isArray(value)) value.forEach(visit);
      else if (value && typeof value === "object") Object.values(value).forEach(visit);
    };
    visit(values);
    return [...found];
  }
  function fileStatus(values) {
    const rows = fileEntries(values);
    return rows.length ? rows.every((row) => row.status === rows[0].status) ? rows[0].status : "modified" : "";
  }
  function fileHtml(values) {
    return badge(fileStatus(values));
  }
  function fileDetails(values, { rows = fileEntries(values), open = false } = {}) {
    if (!rows.length) return "";
    return `<details class="version-update-details version-update-files"${open ? " open" : ""}><summary>${ui("Changed files", "具体资源更新")} <span class="version-update-count">${rows.length}</span></summary>${rows.map((entry) => {
      const oldPath = entry.old_asset_export_rel || fileKey(entry.old_asset_rel) || fileKey(entry.path);
      const newPath = entry.new_asset_export_rel || fileKey(entry.new_asset_rel) || fileKey(entry.path);
      const link = (root, path, title) => `<a href="/${root}/${path.split("/").map(encodeURIComponent).join("/")}" target="_blank" rel="noopener">${title}</a>`;
      const links = [entry.status !== "added" && oldPath ? link("export_previous", oldPath, ui("Previous file", "旧版文件")) : "", entry.status !== "deleted" && newPath ? link("export_full", newPath, ui("Current file", "新版文件")) : ""].filter(Boolean).join(" · ");
      const diff = Array.isArray(entry.text_diff) && entry.text_diff.length ? `<pre class="version-update-file-diff">${entry.text_diff.map((line) => `<span class="${line.startsWith("+") ? "is-added" : line.startsWith("-") ? "is-deleted" : ""}">${esc(line)}</span>`).join("\n")}</pre>` : `<p class="version-update-note">${fileNote(entry)}</p>`;
      const note = entry.text_diff_truncated ? `<p>${ui("Preview truncated; open the files for the full content.", "差异预览已截断，可打开文件查看完整内容。")}</p>` : "";
      const size = [ui("Previous", "旧版"), entry.old_size == null ? "—" : `${entry.old_size.toLocaleString()} B`, ui("Current", "新版"), entry.new_size == null ? "—" : `${entry.new_size.toLocaleString()} B`].join(" · ");
      const relocated = oldPath && newPath && oldPath !== newPath ? `<p class="version-update-note"><code>${esc(oldPath)}</code> → <code>${esc(newPath)}</code></p>` : "";
      const coverage = entry.text_kind === "decoded_partial" ? `<p class="version-update-note">${ui("This comparison covers only the fields exposed by the current reader.", "此对比仅覆盖当前读取器已解析的字段。")}</p>` : "";
      return `<div class="version-update-source"><div class="version-update-source-title">${badge(entry.status)}<code>${esc(newPath || oldPath)}</code></div>${relocated}<div class="version-update-file-links">${links}</div><p class="version-update-note">${esc(size)}</p>${coverage}${diff}${note}</div>`;
    }).join("")}</details>`;
  }
  function fileNote(entry) {
    if (entry.text_diff_note === "decoded_identical") return ui("The file changed, but the decoded view is identical. Its reader does not expose the changed content.", "文件发生变化，但已解码的内容相同；当前读取器尚未展示变化部分。");
    if (entry.text_diff_note === "binary_too_large") return ui("This file exceeds the comparison preview limit. Open the previous and current files to inspect the full content.", "此文件超出差异预览大小限制，可打开旧版和新版文件查看完整内容。");
    if (entry.domain === "asset") return ui("This media file changed. Open the previous and current files to compare their content.", "此媒体资源发生变化，可打开旧版和新版文件对比具体内容。");
    return ui("The file changed; a text comparison is unavailable. Open the files to inspect their content.", "文件发生变化，暂无文本对比，可打开文件查看具体内容。");
  }
  function decorateFiles(root) {
    root?.querySelectorAll("img[src], video[src], audio[src], source[src], a[href], [data-map-file-path]").forEach((node) => {
      if (node.closest(".version-update-details")) return;
      const value = node.getAttribute("src") || node.getAttribute("href") || node.dataset.mapFilePath;
      const entry = files.get(fileKey(value));
      if (!entry || node.dataset.versionUpdate) return;
      mark(node, entry.status);
      const marker = document.createElement("span");
      marker.className = "version-update-file-marker";
      marker.innerHTML = badge(entry.status);
      node.insertAdjacentElement("afterend", marker);
    });
  }
  window.WebUI.updateBadges = { load, register, status, html, changes, sourceChanges, sourceHtml,
    sourceTableStatuses, filterGroup, filterSection, syncFilter, bindFilter, fileStatus,
    panel, detailsHtml, decorate, mount, mountFiles, loadFiles, fileKey, fileEntries, fileHtml, fileDetails, decorateFiles };
})();
