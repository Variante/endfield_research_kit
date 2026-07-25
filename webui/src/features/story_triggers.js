(function initStoryTriggers(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.WebUIStoryTriggers = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function storyTriggerFactory() {
  "use strict";

  const CATEGORY_PRIORITY = {
    native_playback: 0,
    native_playback_owner_unresolved: 1,
    playback: 2,
    playback_owner_unresolved: 3,
    condition: 4,
    context: 5,
    dependency: 6,
    definition_only: 7,
    non_mission_content: 8,
    // Ambient world content: a consumer table names the file, but nothing in
    // the shipped data proves what triggers it. Ranked below every attached
    // class and above only "unknown".
    ambient_world_content: 9,
    unknown: 10,
  };

  function array(value) {
    return Array.isArray(value) ? value : [];
  }

  function nativePaths(route) {
    return array(route && route.nativePaths).filter((path) => path && typeof path === "object");
  }

  function routeCategory(route) {
    const causality = String(route && route.causality || "");
    if (nativePaths(route).length) {
      return causality === "playback_owner_unresolved"
        ? "native_playback_owner_unresolved"
        : "native_playback";
    }
    if (Object.prototype.hasOwnProperty.call(CATEGORY_PRIORITY, causality)) return causality;
    return "unknown";
  }

  function routesForKey(manifest, key) {
    const normalizedKey = String(key || "");
    const record = manifest && typeof manifest === "object" ? manifest[normalizedKey] : null;
    return array(record && record.routes)
      .filter((route) => route && (!route.storyKey || route.storyKey === normalizedKey))
      .map((route, index) => ({ route, index, category: routeCategory(route) }))
      .sort((left, right) => (
        (CATEGORY_PRIORITY[left.category] ?? CATEGORY_PRIORITY.unknown)
        - (CATEGORY_PRIORITY[right.category] ?? CATEGORY_PRIORITY.unknown)
        || left.index - right.index
      ))
      .map((item) => item.route);
  }

  function fallbackCategory(record) {
    const status = String(record && record.attachmentStatus || "");
    if (status === "definition_only_no_consumer") return "definition_only";
    if (status === "non_mission_content") return "non_mission_content";
    if (status === "ambient_world_content") return "ambient_world_content";
    return "unknown";
  }

  function triggerView(manifest, key) {
    const normalizedKey = String(key || "");
    const record = manifest && typeof manifest === "object" ? manifest[normalizedKey] : null;
    const routes = routesForKey(manifest, normalizedKey);
    const primary = routes[0] || null;
    const category = primary ? routeCategory(primary) : fallbackCategory(record);
    return {
      key: normalizedKey,
      record: record || null,
      routes,
      primary,
      category,
      hasProvenPlayback: category === "native_playback"
        || category === "native_playback_owner_unresolved"
        || category === "playback"
        || category === "playback_owner_unresolved",
    };
  }

  function uniqueStrings(values) {
    const out = [];
    const seen = new Set();
    for (const value of array(values)) {
      const text = String(value || "").trim();
      if (!text || seen.has(text)) continue;
      seen.add(text);
      out.push(text);
    }
    return out;
  }

  function primaryNativePath(route) {
    return nativePaths(route)[0] || null;
  }

  function nativePathActions(path) {
    return uniqueStrings(array(path && path.steps).map((step) => (
      step && (step.actionName || step.recordClass || step.edge)
    )));
  }

  function compactTrigger(view) {
    const route = view && view.primary;
    const path = primaryNativePath(route);
    if (path) {
      return {
        category: view.category,
        event: String(path.eventSummary || path.eventName || "").trim(),
        eventName: String(path.eventName || "").trim(),
        actions: nativePathActions(path),
        owner: String(route.questId || route.missionId || "").trim(),
        pathCount: nativePaths(route).length,
      };
    }
    return {
      category: String(view && view.category || "unknown"),
      event: "",
      eventName: "",
      actions: uniqueStrings(route && route.actionNames),
      owner: String(route && (route.questId || route.missionId) || "").trim(),
      pathCount: 0,
    };
  }

  return {
    compactTrigger,
    nativePathActions,
    nativePaths,
    routeCategory,
    routesForKey,
    triggerView,
    uniqueStrings,
  };
});
