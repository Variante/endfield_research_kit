// Shared helpers for the static WebUI. Keep this file small and dependency-free.
(() => {
  const WebUI = {};

  function $(sel, root = document) {
    return root.querySelector(sel);
  }

  function $$(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function storageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (_error) {
      // Ignore unavailable storage.
    }
  }

  function normalizeUiLocale(locale) {
    const value = String(locale || "").toLowerCase();
    return value === "zh" || value === "en" ? value : "";
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[ch]));
  }

  function textIncludes(value, q) {
    return String(value || "").toLowerCase().includes(q);
  }

  function formatNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number.toLocaleString() : "";
  }

  function formatSignedNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "";
    return `${number > 0 ? "+" : ""}${number.toLocaleString()}`;
  }

  function applyTemplate(template, replacements = {}) {
    return String(template || "").replace(/\{(\w+)\}/g, (_, name) => String(replacements[name] ?? ""));
  }

  function normalizeRelPath(value) {
    return String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  }

  function exportFullHref(relPath, sourceRoots = {}, exportRoot = "export_full") {
    const normalizedRel = normalizeRelPath(relPath);
    if (!normalizedRel) return "/export_full/";

    const [source, ...rest] = normalizedRel.split("/").filter(Boolean);
    const sourceRoot = sourceRoots && sourceRoots[source];
    let exportFullRel = normalizedRel;

    if (sourceRoot) {
      let normalizedRoot = normalizeRelPath(sourceRoot);
      const rootPrefix = normalizeRelPath(exportRoot);
      if (rootPrefix && normalizedRoot.startsWith(`${rootPrefix}/`)) {
        normalizedRoot = normalizedRoot.slice(rootPrefix.length + 1);
      } else if (normalizedRoot === rootPrefix) {
        normalizedRoot = "";
      }
      exportFullRel = [normalizedRoot, rest.join("/")].filter(Boolean).join("/");
    }

    return `/export_full/${exportFullRel.split("/").map(encodeURIComponent).join("/")}`;
  }

  function rebuildSelect(select, values, labeler) {
    if (!select) return;
    const current = select.value;
    const all = select.querySelector("option[value='']");
    select.replaceChildren();
    if (all) select.appendChild(all);
    for (const value of values) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = labeler ? labeler(value) : value;
      select.appendChild(option);
    }
    select.value = Array.from(select.options).some((option) => option.value === current) ? current : "";
  }

  Object.assign(WebUI, {
    $,
    $$,
    storageGet,
    storageSet,
    normalizeUiLocale,
    escapeHtml,
    textIncludes,
    formatNumber,
    formatSignedNumber,
    applyTemplate,
    exportFullHref,
    rebuildSelect,
  });

  window.WebUI = WebUI;
})();
