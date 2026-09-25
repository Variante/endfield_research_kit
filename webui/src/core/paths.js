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

  // Asset references are "<label>/<path>" (layout v2): Unity is the decoded
  // Unity tree, whose files carry a _p<PathID> suffix; Game is the export's
  // game/ tree of final VFS files.
  const DEFAULT_SOURCE_ROOTS = Object.freeze({
    Unity: "game/Unity",
    Game: "game",
    Audio: "game/Audio",
  });

  function relRequiresPathIdExportName(relPath) {
    const source = normalizeRelPath(relPath).split("/")[0] || "";
    return source.toLowerCase() === "unity";
  }

  function defaultSourceRoot(source) {
    return DEFAULT_SOURCE_ROOTS[String(source || "")] || "";
  }

  function exportFullHref(relPath, sourceRoots = {}, exportRoot = "export_full") {
    const normalizedRel = normalizeRelPath(relPath);
    if (!normalizedRel) return "/export_full/";

    const [source, ...rest] = normalizedRel.split("/").filter(Boolean);
    const sourceRoot = (sourceRoots && sourceRoots[source]) || defaultSourceRoot(source);
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

  function exportDataHref(relPath) {
    const normalizedRel = normalizeRelPath(relPath);
    if (!normalizedRel) return "/export_data/";
    return `/export_data/${normalizedRel.split("/").map(encodeURIComponent).join("/")}`;
  }

  // The Data page (#data-inspector) opens one export-store row from these
  // query parameters: dataRoot (current|previous), dataStore (unity|game-files),
  // dataGroup (a Unity type, or a packed game folder), dataName (the row name
  // inside that group). dataMode picks the page mode (files|sql|decoded).
  const DATA_PAGE_PARAMS = Object.freeze(["dataMode", "dataRoot", "dataStore", "dataGroup", "dataName", "dataField", "dataQ"]);

  function dataPageUrl({ root = "", store = "", group = "", name = "" } = {}, base = window.location.href) {
    const url = new URL(base);
    for (const key of DATA_PAGE_PARAMS) url.searchParams.delete(key);
    url.searchParams.delete("inspectDataset");
    url.searchParams.delete("inspect");
    url.searchParams.set("dataMode", "files");
    if (root && root !== "current") url.searchParams.set("dataRoot", root);
    if (store) url.searchParams.set("dataStore", store);
    if (group) url.searchParams.set("dataGroup", group);
    if (name) url.searchParams.set("dataName", name);
    url.hash = "#data-inspector";
    return url.toString();
  }

  // A Unity object document ref ("Unity/<Type>/<name>" or
  // "game/Unity/<Type>/<name>") is a row of the export's Unity store. Only the
  // document suffixes the store holds qualify; loose media stays a file.
  function unityStoreDocumentRef(relPath) {
    const match = normalizeRelPath(relPath).match(/^(?:game\/)?Unity\/([^/]+)\/([^/]+\.(?:json|anim))$/i);
    return match ? { store: "unity", group: match[1], name: match[2] } : null;
  }

  function dataPageUrlForRel(relPath) {
    const ref = unityStoreDocumentRef(relPath);
    return ref ? dataPageUrl(ref) : "";
  }

  Object.assign(WebUI, {
    DATA_PAGE_PARAMS,
    dataPageUrl,
    unityStoreDocumentRef,
    dataPageUrlForRel,
    normalizeRelPath,
    splitPathIdExportStem,
    pathIdExportBaseStem,
    relRequiresPathIdExportName,
    exportFullHref,
    exportDataHref,
  });
})();
