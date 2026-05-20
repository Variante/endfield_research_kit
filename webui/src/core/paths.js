(() => {
  const WebUI = window.WebUI;

  function normalizeRelPath(value) {
    return String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  }

  function splitPathIdExportStem(value) {
    const match = String(value || "").match(/^(.*)_p([0-9a-f]{16})$/i);
    return match ? { base: match[1], pathId: match[2].toUpperCase() } : null;
  }

  function pathIdExportBaseStem(value) {
    const split = splitPathIdExportStem(value);
    return split ? split.base : "";
  }

  function relRequiresPathIdExportName(relPath) {
    const source = normalizeRelPath(relPath).split("/")[0] || "";
    if (!source || /-structured$/i.test(source) || source.toLowerCase() === "raw_vfs") return false;
    return ["streamingassets", "persistent"].includes(source.split("-")[0].toLowerCase());
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

  Object.assign(WebUI, {
    normalizeRelPath,
    splitPathIdExportStem,
    pathIdExportBaseStem,
    relRequiresPathIdExportName,
    exportFullHref,
  });
})();
