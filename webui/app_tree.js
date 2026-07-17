// Endfield conversation browser - tree/filter helpers.

function normalizeSearchText(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

// Concatenate every searchable field of an entry into one lowercased blob, so a
// multi-token query can be OR-matched and scored against it in one pass.
function entrySearchHaystack(e) {
  const parts = [e.k, e.m, e.title, e.p, e.x];
  const missionName = missionDisplay(entryTreeMissionId(e), entryDataType(e));
  if (missionName) parts.push(missionName);
  for (const dataType of entryTreeDataTypes(e)) {
    parts.push(dataType, dataTypeLabel(dataType));
    const group = treeGroupInfo(e, dataType);
    if (group.label) parts.push(group.label);
    if (group.raw) parts.push(group.raw);
  }
  for (const typeKey of entryMediaTypeFilterKeys(e)) {
    parts.push(typeKey, typeFilterLabel(typeKey));
  }
  for (const tag of entryMetadataTags(e)) {
    parts.push(tag, metadataTagLabel(tag));
  }
  for (const method of entryRecoveryMethods(e)) {
    parts.push(method, recoveryMethodLabel(method));
  }
  for (const aid of e.c || []) {
    parts.push(aid);
    for (const nm of (STATE.actorNames[aid] || [])) parts.push(nm);
  }
  return normalizeSearchText(parts.filter(Boolean).join("\n"));
}

function entrySearchAliasBaseKey(key) {
  const raw = String(key || "");
  if (raw.startsWith("misc_")) return raw.slice(5);
  return raw;
}

function entryMatchesOptionIdSearch(entry, q) {
  if (!entry || !q || !q.includes("option_")) return false;
  const keys = [
    String(entry.k || ""),
    entrySearchAliasBaseKey(entry.k),
  ].filter(Boolean);
  for (const key of new Set(keys)) {
    if (q.includes(`option_${normalizeSearchText(key)}_`)) return true;
  }
  return false;
}

function entryTreeDataType(entry) {
  const types = entryTreeDataTypes(entry);
  return types[0] || DEFAULT_DATA_TYPE_KEY;
}

function entryTreeDataTypes(entry) {
  if (!entry) return [DEFAULT_DATA_TYPE_KEY];
  if (aiBarkSimActorId(entry)) return ["sim"];
  return entryDataTypes(entry).filter((dataType) => !entryShouldHideArchiveDuplicateStoryType(entry, dataType));
}

function entryTreeDataTypesForSort(entry, sortMode) {
  const types = entryTreeDataTypes(entry);
  if ((sortMode || "story") !== "story") return types;
  if (typeof storyOrderDetailForEntry !== "function" || !storyOrderDetailForEntry(entry)) return types;
  const missionId = typeof storyOrderMissionIdForEntry === "function"
    ? storyOrderMissionIdForEntry(entry)
    : entryTreeMissionId(entry);
  const storyType = typeof storyMissionTypeFromId === "function"
    ? storyMissionTypeFromId(missionId)
    : "";
  if (!storyType) return types;
  const out = [storyType];
  for (const dataType of types) {
    if (
      dataType !== storyType
      && typeof entryUsesMissionLinkedNativeDataType === "function"
      && entryUsesMissionLinkedNativeDataType(entry, dataType)
    ) {
      out.push(dataType);
    }
  }
  return out;
}

function entryShouldHideArchiveDuplicateStoryType(entry, dataType) {
  if (!entry || !dataType || typeof entryHasReadingArchiveMissionDuplicate !== "function") return false;
  if (!entryHasReadingArchiveMissionDuplicate(entry)) return false;
  if (String(dataType || "").startsWith("prtscat:")) return false;
  const missionType = typeof storyMissionTypeFromId === "function"
    ? storyMissionTypeFromId(entryTreeMissionId(entry))
    : "";
  return !!missionType && dataType === missionType;
}

function entryMatchesTreeDataTypeFilters(entry, filters) {
  if (!filters || !filters.size) return true;
  return entryTreeDataTypes(entry).some((dataType) => filters.has(dataType));
}

function simTreeGroupInfo(entry) {
  if (!entry) return null;
  const actorId =
    pairedSimActorId(entry) ||
    simCharacterId(entry) ||
    linkedSimActorId(entry) ||
    aiBarkSimActorId(entry) ||
    continueActorIdFromMissionId(entry.m);
  if (!actorId) return null;

  const label = characterDisplayFromActorId(actorId, true) || actorDisplay(actorId);
  return {
    key: `simchar:${actorId}`,
    label: label || actorId,
    raw: label && label !== actorId ? actorId : "",
    mono: !label || label === actorId,
  };
}

function topicTreeGroupInfo(entry) {
  if (!entry || String(entry.d || "") !== "sns") return null;
  const chatTitle = snsChannelDisplayTitle(entry);
  const chatId = String(entry.chatId || "").trim();
  if (chatTitle) {
    return {
      key: `snschat:${(chatId || chatTitle).toLowerCase()}`,
      label: chatTitle,
      raw: chatId && chatId !== chatTitle ? chatId : "",
      mono: false,
    };
  }

  const actorId = String(entry.chatGroupSpeaker || (entry.c && entry.c[0]) || "").trim();
  if (!actorId) return null;
  if (SPECIAL_SIM_ACTOR_IDS.has(actorId.toLowerCase())) return null;

  const label = characterDisplayFromActorId(actorId, true) || actorDisplay(actorId);
  return {
    key: `topicactor:${actorId.toLowerCase()}`,
    label: label || actorId,
    raw: label && label !== actorId ? actorId : "",
    mono: !label || label === actorId,
  };
}

function sourceTreeGroupInfo(entry, missionId, missionName) {
  const normalizedLabel = normalizeGroupedTagLabel(missionName || missionId);
  const normalizedKey = normalizeGroupedTagKey(missionName || missionId);
  const rawSubtitle = sourceGroupSubtitle(entry);
  return {
    key: normalizedKey ? `sourcegroup:${normalizedKey}` : missionId,
    label: normalizedLabel || missionName || missionId,
    raw: rawSubtitle,
    mono: !(normalizedLabel || missionName) && !rawSubtitle,
  };
}

function missionTreeGroupInfo(missionId, missionName) {
  return {
    key: missionId,
    label: missionName || missionId,
    raw: missionName ? missionId : "",
    mono: !missionName,
  };
}

function archiveResearchTreeGroupInfo(entry) {
  const research = entryArchiveResearchInfo(entry);
  if (!research) return null;
  const label = research.title || research.id;
  if (!label) return null;
  const normalizedKey = normalizeGroupedTagKey(research.id || label);
  return {
    key: normalizedKey ? `archive-research:${normalizedKey}` : `archive-research:${label}`,
    label,
    raw: research.title && research.id ? research.id : "",
    mono: !research.title,
  };
}

function entryTreeMissionId(entry) {
  return entryStoryMissionId(entry) || String(entry && entry.m || "");
}

function treeGroupInfo(entry, dataTypeOverride = "") {
  const dataType = dataTypeOverride || entryTreeDataType(entry);
  const useNativeMissionGroup = typeof entryUsesMissionLinkedNativeDataType === "function"
    && entryUsesMissionLinkedNativeDataType(entry, dataType);
  if (dataType === "topic") {
    const topicGroup = topicTreeGroupInfo(entry);
    if (topicGroup) return topicGroup;
  }

  if (dataType === "sim") {
    const simGroup = simTreeGroupInfo(entry);
    if (simGroup) return simGroup;
  }

  if (isArchiveReportDataType(dataType)) {
    const archiveResearchGroup = archiveResearchTreeGroupInfo(entry);
    if (archiveResearchGroup) return archiveResearchGroup;
  }

  const storyMissionId = useNativeMissionGroup ? "" : entryStoryMissionId(entry);
  const missionId = storyMissionId || String(entry && entry.m || "");
  const missionName = missionDisplay(missionId, dataType);
  if (entryHasSourceTag(entry) && !storyMissionId) {
    return sourceTreeGroupInfo(entry, missionId, missionName);
  }
  return missionTreeGroupInfo(missionId, missionName);
}

function singletonSourceGroupParentLabel(label) {
  const parts = String(label || "")
    .split("/")
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length < 3) return "";
  parts.pop();
  return parts.join(" / ");
}

function collapseSingletonSourceGroups(groupMap) {
  if (!groupMap || typeof groupMap !== "object") return groupMap;

  const plans = new Map();
  for (const [bucketKey, bucket] of Object.entries(groupMap)) {
    if (!bucket || !Array.isArray(bucket.items) || !bucket.items.length) continue;
    if (!String(bucketKey || "").startsWith("sourcegroup:")) continue;
    if (!bucket.items.every((entry) => entryHasSourceTag(entry))) continue;

    const parentLabel = singletonSourceGroupParentLabel(bucket.label);
    if (!parentLabel) continue;

    const parentKey = normalizeGroupedTagKey(parentLabel);
    if (!parentKey) continue;

    const planKey = `sourcegroup:${parentKey}`;
    const plan = plans.get(planKey) || {
      key: planKey,
      label: parentLabel,
      children: [],
    };
    plan.children.push({ bucketKey, bucket });
    plans.set(planKey, plan);
  }

  if (!plans.size) return groupMap;

  const collapsed = { ...groupMap };
  for (const plan of plans.values()) {
    if (plan.children.length < 2) continue;
    if (plan.children.some(({ bucket }) => bucket.items.length !== 1)) continue;
    if (Object.prototype.hasOwnProperty.call(groupMap, plan.key)) continue;

    const mergedItems = [];
    for (const { bucketKey, bucket } of plan.children) {
      delete collapsed[bucketKey];
      mergedItems.push(...bucket.items);
    }
    collapsed[plan.key] = {
      key: plan.key,
      label: plan.label,
      raw: "",
      mono: false,
      items: mergedItems,
    };
  }

  return collapsed;
}

// Some cutscenes are exported as a small family of sibling assets sharing the
// same scene root. Keep the detail entries separate, but nest them together in
// the tree so the sidebar reads as one cutscene cluster instead of five peers.
function cutsceneFamilyBaseKey(value) {
  let key = String(value || "").trim();
  const prefixed = key.match(/^(?:f|m|fm)_(cutscene_.+)$/i);
  if (prefixed) key = prefixed[1];
  if (!key.startsWith("cutscene_")) return "";
  key = key.replace(/_p[0-9A-Fa-f]{8,16}$/i, "");
  key = key.replace(/_(?:Actor|Audio|Effect|Light|Others)(?:_(?:cam_\d+|AU|CHI|CN|EN|ENG|JP|KO|KR|ENV))*$/i, "");
  key = key.replace(/_(?:CHI|CN|EN|ENG|JP|KO|KR|ENV)$/i, "");
  return key === "cutscene" ? "" : key;
}

function cutsceneFamilyInfo(entry) {
  if (!entry || entry.d !== "cutscene") return null;
  const key = cutsceneFamilyBaseKey(entry.k);
  if (!key) return null;
  return {
    key,
    pathKey: `cutscene:${key}`,
    label: key,
    raw: "",
    mono: true,
  };
}

function formatLevelRef(ref) {
  if (!ref) return "";
  const levelId = ref.levelId || ref.file || "";
  const flags = [];
  if (ref.hostType) flags.push(ref.hostType);
  if (ref.kind === "mission") flags.push("mission");
  return flags.length ? `${levelId} [${flags.join(", ")}]` : levelId;
}

// ---------- filter UI ----------
function filterSectionActiveCount(key) {
  const filters = STATE.filters || createDefaultFilters();
  switch (key) {
    case "basic":
      return filters.q ? 1 : 0;
    case "kind":
      return filters.kinds.size;
    case "type":
      return filters.dataTypes.size;
    case "media":
      return filters.media.size;
    case "story-issue":
      return filters.issues.size;
    case "recovery-method":
      return filters.recoveryMethods.size;
    default:
      return 0;
  }
}

function hasActiveStoryFilters() {
  return !!(
    filterSectionActiveCount("basic") ||
    filterSectionActiveCount("kind") ||
    filterSectionActiveCount("type") ||
    filterSectionActiveCount("media") ||
    filterSectionActiveCount("story-issue") ||
    filterSectionActiveCount("recovery-method")
  );
}

function syncFilterSectionActiveCounts() {
  for (const section of $$("#filter-panel .filter-section[data-filter-section]")) {
    const count = filterSectionActiveCount(section.dataset.filterSection || "");
    const title = section.querySelector(".filter-section-toggle, .filter-section-title");
    if (!title) continue;

    let badge = title.querySelector(".filter-section-active-count");
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "filter-section-active-count";
      badge.hidden = true;
      const label = title.querySelector("span[id$='-label']");
      if (label && label.nextSibling) title.insertBefore(badge, label.nextSibling);
      else if (label) title.appendChild(badge);
      else title.insertBefore(badge, title.firstChild);
    }

    badge.textContent = count ? `(${count})` : "";
    badge.hidden = !count;
    badge.setAttribute("aria-label", count ? `${count} active filters` : "");
    section.classList.toggle("has-active-filters", !!count);
  }
}

function preserveCurrentTreeExpansion() {
  if (!Array.isArray(STATE.rows)) return;
  for (const row of STATE.rows) {
    if (row && row.type === "group" && row.expanded && row.path) {
      STATE.expanded.add(row.path);
    }
  }
}

function buildKindChips() {
  const kindCounts = countBy(STATE.entries, (e) => entryGroupedKindKey(e));
  const kindKeys = Object.keys(kindCounts)
    .filter((k) => !shouldSuppressKindChip(k))
    .sort((a, b) => {
      const aName = kindMeta(a).name || formatStructuredLabel(a);
      const bName = kindMeta(b).name || formatStructuredLabel(b);
      return aName.localeCompare(bName, undefined, { numeric: true });
    });
  pruneFilterSet(STATE.filters.kinds, new Set(kindKeys.map(kindFilterToken)));
  const items = kindKeys
    .filter((k) => kindCounts[k])
    .map((k) => {
      const meta = kindMeta(k);
      return {
        value: kindFilterToken(k),
        label: meta.name,
        count: kindCounts[k],
        className: `kind-chip ${meta.cls || ""}`.trim(),
      };
    });
  window.WebUI.filters.buildChips("#kind-filter", items, {
    active: STATE.filters.kinds,
    prune: false,
    onToggle: () => applyFilters(),
  });
}

function buildDataTypeChips() {
  const counts = {};
  for (const entry of STATE.entries) {
    for (const dataType of entryTreeDataTypes(entry)) {
      counts[dataType] = (counts[dataType] || 0) + 1;
    }
  }
  const dataTypeKeys = Object.keys(counts)
    .filter(Boolean)
    .sort((a, b) => compareDataTypeKeys(a, b, counts));
  pruneFilterSet(STATE.filters.dataTypes, new Set(dataTypeKeys));
  const items = dataTypeKeys
    .filter((dataType) => counts[dataType])
    .map((dataType) => ({ value: dataType, label: dataTypeLabel(dataType), count: counts[dataType] }));
  window.WebUI.filters.buildChips("#type-filter", items, {
    active: STATE.filters.dataTypes,
    prune: false,
    onToggle: () => applyFilters(),
  });
}

function buildMediaChips() {
  const counts = {};
  for (const entry of STATE.entries) {
    for (const mediaKey of entryMediaTypeFilterKeys(entry)) {
      counts[mediaKey] = (counts[mediaKey] || 0) + 1;
    }
  }
  const mediaKeys = MEDIA_TYPE_FILTER_KEYS.filter((key) => counts[key]);
  pruneFilterSet(STATE.filters.media, new Set(mediaKeys));
  const items = mediaKeys.map((mediaKey) => ({
    value: mediaKey,
    label: mediaTypeFilterLabel(mediaKey),
    count: counts[mediaKey],
  }));
  window.WebUI.filters.buildChips("#media-filter", items, {
    active: STATE.filters.media,
    className: "media-chip",
    prune: false,
    onToggle: () => applyFilters(),
  });
}

function buildStoryIssueChips() {
  const counts = {};
  for (const entry of STATE.entries) {
    for (const code of new Set(entryStoryIssues(entry))) {
      counts[code] = (counts[code] || 0) + 1;
    }
  }
  const issueKeys = STORY_ISSUE_ORDER.filter((code) => counts[code]);
  pruneFilterSet(STATE.filters.issues, new Set(issueKeys));
  const items = issueKeys.map((code) => ({ value: code, label: storyIssueLabel(code), count: counts[code] }));
  window.WebUI.filters.buildChips("#story-issue-filter", items, {
    active: STATE.filters.issues,
    prune: false,
    onToggle: () => applyFilters(),
  });
}

function buildRecoveryMethodChips() {
  const counts = {};
  for (const entry of STATE.entries) {
    for (const method of new Set(entryRecoveryMethods(entry))) {
      counts[method] = (counts[method] || 0) + 1;
    }
  }
  const methodKeys = Object.keys(counts)
    .filter(Boolean)
    .sort((a, b) => compareRecoveryMethodKeys(a, b, counts));
  pruneFilterSet(STATE.filters.recoveryMethods, new Set(methodKeys));
  const items = methodKeys.map((method) => ({
    value: method,
    label: recoveryMethodLabel(method),
    count: counts[method],
  }));
  window.WebUI.filters.buildChips("#recovery-method-filter", items, {
    active: STATE.filters.recoveryMethods,
    prune: false,
    onToggle: () => applyFilters(),
  });
}

const STORY_SORT_MODES = new Set(["natural", "story", "lines-desc", "lines-asc", "key"]);

function normalizeStorySortMode(mode) {
  const normalized = String(mode || "");
  return STORY_SORT_MODES.has(normalized) ? normalized : "story";
}

function syncStorySortControl() {
  const sortSelect = $("#sort");
  if (sortSelect) sortSelect.value = normalizeStorySortMode(STATE.sortMode);
  syncStoryOrderEditor();
}

function setStorySortMode(mode, { resetScroll = true } = {}) {
  STATE.sortMode = normalizeStorySortMode(mode);
  syncStorySortControl();
  rebuildTree({ resetScroll });
}

function storyOrderEditingEnabled() {
  return STATE.showDebug && (STATE.sortMode || "story") === "story";
}

function syncStoryOrderEditor() {
  const row = $("#story-order-editor-row");
  if (!row) return;
  const inStorySort = (STATE.sortMode || "story") === "story";
  row.hidden = !inStorySort;
}

function storyOrderMoveInfo(entry) {
  if (!entry || typeof storyOrderMissionIdForEntry !== "function") return null;
  const missionId = storyOrderMissionIdForEntry(entry);
  if (!missionId) return null;
  const mission = STATE.storyOrderPayload
    && STATE.storyOrderPayload.missions
    && STATE.storyOrderPayload.missions[missionId];
  let order = typeof overrideKeyList === "function"
    ? overrideKeyList(mission && mission.order)
    : [];
  if (!order.length) order = storyOrderMissionBaselineOrder(missionId);
  const key = String(entry.k || "");
  const index = order.indexOf(key);
  if (!order.length || index < 0) return null;
  return { missionId, order, index };
}

function storyOrderEntryEditable(entry) {
  if (!storyOrderEditingEnabled()) return null;
  const info = storyOrderMoveInfo(entry);
  if (!info) return null;
  const isLocked = typeof storyOrderMissionLocked === "function"
    && storyOrderMissionLocked(info.missionId);
  if (isLocked) return null;
  return info;
}

function reorderStoryOrderEntry(missionId, fromKey, toKey, placeAfter) {
  if (!storyOrderEditingEnabled()) return false;
  const mission = STATE.storyOrderPayload
    && STATE.storyOrderPayload.missions
    && STATE.storyOrderPayload.missions[missionId];
  let order = typeof overrideKeyList === "function"
    ? overrideKeyList(mission && mission.order)
    : [];
  if (!order.length) order = storyOrderMissionBaselineOrder(missionId);
  if (!order.length) return false;
  if (typeof storyOrderMissionLocked === "function" && storyOrderMissionLocked(missionId)) return false;
  const fromIndex = order.indexOf(String(fromKey));
  const toIndex = order.indexOf(String(toKey));
  if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) return false;

  const nextOrder = order.slice();
  const [moved] = nextOrder.splice(fromIndex, 1);
  let insertAt = nextOrder.indexOf(String(toKey));
  if (insertAt < 0) return false;
  if (placeAfter) insertAt += 1;
  nextOrder.splice(insertAt, 0, moved);

  if (typeof setStoryOrderMissionOrder !== "function" || !setStoryOrderMissionOrder(missionId, nextOrder)) {
    return false;
  }
  if (typeof scheduleStoryOrderSave === "function") scheduleStoryOrderSave();

  const wrap = $("#list-wrap");
  const prevScroll = wrap ? wrap.scrollTop : 0;
  rebuildTree({ resetScroll: false });
  if (wrap) wrap.scrollTop = prevScroll;
  renderList();
  return true;
}

function storyOrderMissionIdForGroup(groupKey) {
  const missionId = String(groupKey || "");
  if (!missionId || missionId.includes(":")) return "";
  if (typeof storyMissionTypeFromId === "function" && storyMissionTypeFromId(missionId)) {
    return missionId;
  }
  const mission = STATE.storyOrderPayload
    && STATE.storyOrderPayload.missions
    && STATE.storyOrderPayload.missions[missionId];
  return mission && Array.isArray(mission.order) && mission.order.length ? missionId : "";
}

// Reorder operations target the full mission order. When the override has no
// entry for this mission yet, seed from all loaded rows so filtered Story views
// can be rearranged without dropping hidden files from the saved override.
function storyOrderMissionBaselineOrder(missionId) {
  const target = String(missionId || "");
  if (!target) return [];
  const source = STATE.entries || [];
  const seen = new Set();
  const items = [];
  for (const entry of source) {
    if (!entry) continue;
    const mid = typeof storyOrderMissionIdForEntry === "function"
      ? storyOrderMissionIdForEntry(entry)
      : String(entry.m || "");
    if (String(mid) !== target) continue;
    const key = String(entry.k || "");
    if (!key || seen.has(key)) continue;
    seen.add(key);
    items.push(entry);
  }
  items.sort((a, b) => {
    const ap = typeof storyOrderPositionForEntry === "function" ? storyOrderPositionForEntry(a) : null;
    const bp = typeof storyOrderPositionForEntry === "function" ? storyOrderPositionForEntry(b) : null;
    const hasA = Number.isFinite(ap);
    const hasB = Number.isFinite(bp);
    if (hasA && hasB && ap !== bp) return ap - bp;
    if (hasA !== hasB) return hasA ? -1 : 1;
    return String(a.k).localeCompare(String(b.k), undefined, { numeric: true });
  });
  return items.map((e) => String(e.k));
}

function storyOrderMissionLockControl(row) {
  if ((STATE.sortMode || "story") !== "story") return "";
  const missionId = String(row && row.storyOrderMissionId || "");
  if (!missionId) return "";
  const locked = typeof storyOrderMissionLocked === "function" && storyOrderMissionLocked(missionId);
  const stateKey = locked ? "storyOrderMissionLocked" : "storyOrderMissionEditable";
  const titleKey = locked ? "storyOrderUnlockMissionTitle" : "storyOrderLockMissionTitle";
  const label = escapeHtml(uiText(stateKey));
  const title = escapeHtml(uiText(titleKey));
  const icon = locked
    ? `<svg class="story-order-pin-icon" viewBox="0 0 14 14" aria-hidden="true"><path d="M4 6 V4.5 a3 3 0 0 1 6 0 V6" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/><rect x="3" y="6" width="8" height="6" rx="1.2" fill="currentColor"/></svg>`
    : `<svg class="story-order-pin-icon" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 10 L9 3 L11 5 L4 12 Z" fill="currentColor"/><path d="M8.5 3.5 L10.5 5.5" stroke="rgba(0,0,0,0.35)" stroke-width="0.8"/></svg>`;
  return (
    `<button class="story-order-mission-lock-button${locked ? " is-locked" : " is-editable"}" ` +
      `type="button" data-mission-id="${escapeHtml(missionId)}" ` +
      `aria-pressed="${locked ? "true" : "false"}" title="${title}">${icon}<span class="story-order-mission-lock-label">${label}</span></button>`
  );
}

function storyOrderMissionMoveUnusedControl(row) {
  if ((STATE.sortMode || "story") !== "story") return "";
  const missionId = String(row && row.storyOrderMissionId || "");
  if (!missionId) return "";
  const unusedSet = typeof storyOrderMissionPossiblyUnused === "function"
    ? storyOrderMissionPossiblyUnused(missionId)
    : new Set();
  const count = unusedSet ? unusedSet.size : 0;
  const titleKey = count ? "storyOrderMoveUnusedToEndTitle" : "storyOrderMoveUnusedToEndNone";
  const label = escapeHtml(uiText("storyOrderMoveUnusedToEnd"));
  const title = escapeHtml(uiText(titleKey));
  const disabled = count ? "" : " disabled";
  return (
    `<button class="story-order-mission-move-unused-button" type="button" ` +
      `data-mission-id="${escapeHtml(missionId)}" title="${title}"${disabled}>` +
      `<svg class="story-order-pin-icon" viewBox="0 0 14 14" aria-hidden="true">` +
        `<path d="M7 2 V10" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>` +
        `<path d="M4 7 L7 10 L10 7" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>` +
        `<path d="M3 12 H11" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>` +
      `</svg>` +
      `<span class="story-order-mission-lock-label">${label}${count ? ` (${count})` : ""}</span>` +
    `</button>`
  );
}

// #2 �?flag missions whose order is NOT human-verified (not locked). Non-locked
// overrides may be OCR/auto-seeded; per project policy OCR is untrusted, so these
// need a human pass. Locked missions are treated as verified and show no badge.
function storyOrderMissionVerifiedControl(row) {
  if ((STATE.sortMode || "story") !== "story") return "";
  const missionId = String(row && row.storyOrderMissionId || "");
  if (!missionId) return "";
  const mission = STATE.storyOrderPayload && STATE.storyOrderPayload.missions
    && STATE.storyOrderPayload.missions[missionId];
  if (!mission || !Array.isArray(mission.order) || !mission.order.length) return "";
  const locked = typeof storyOrderMissionLocked === "function" && storyOrderMissionLocked(missionId);
  if (locked) return "";
  const label = escapeHtml(uiText("storyOrderUnverifiedBadge"));
  const title = escapeHtml(uiText("storyOrderUnverifiedTitle"));
  return `<span class="story-order-unverified-badge" title="${title}">${label}</span>`;
}

// #1 �?jump to the next low-confidence row needing review. Count reflects the
// mission's fallback/weak rows; only shown once the mission JSON is cached (debug).
function storyOrderMissionReviewControl(row) {
  if ((STATE.sortMode || "story") !== "story" || !STATE.showDebug) return "";
  const missionId = String(row && row.storyOrderMissionId || "");
  if (!missionId) return "";
  const keys = typeof storyOrderMissionUncertainKeys === "function"
    ? storyOrderMissionUncertainKeys(missionId) : [];
  if (!keys.length) return "";
  const label = escapeHtml(uiText("storyOrderReviewJump"));
  const title = escapeHtml(uiText("storyOrderReviewJumpTitle"));
  return (
    `<button class="story-order-mission-review-button" type="button" ` +
      `data-mission-id="${escapeHtml(missionId)}" title="${title}">` +
      `<span class="story-order-review-mark" aria-hidden="true">!</span>` +
      `<span class="story-order-mission-lock-label">${label} (${keys.length})</span>` +
    `</button>`
  );
}

function moveStoryOrderMissionUnusedToEnd(missionId) {
  const missionKey = String(missionId || "");
  if (!missionKey) return false;
  if (typeof storyOrderMissionLocked === "function" && storyOrderMissionLocked(missionKey)) return false;
  const mission = STATE.storyOrderPayload
    && STATE.storyOrderPayload.missions
    && STATE.storyOrderPayload.missions[missionKey];
  let order = typeof overrideKeyList === "function"
    ? overrideKeyList(mission && mission.order)
    : [];
  if (!order.length) order = storyOrderMissionBaselineOrder(missionKey);
  if (!order.length) return false;
  const unusedSet = typeof storyOrderMissionPossiblyUnused === "function"
    ? storyOrderMissionPossiblyUnused(missionKey)
    : new Set();
  if (!unusedSet || !unusedSet.size) return false;

  const kept = [];
  const moved = [];
  for (const key of order) {
    if (unusedSet.has(String(key))) moved.push(key);
    else kept.push(key);
  }
  if (!moved.length || !kept.length) return false;
  const nextOrder = kept.concat(moved);
  if (nextOrder.every((k, i) => k === order[i])) return false;

  if (typeof setStoryOrderMissionOrder !== "function" || !setStoryOrderMissionOrder(missionKey, nextOrder)) {
    return false;
  }
  if (typeof scheduleStoryOrderSave === "function") scheduleStoryOrderSave();

  const wrap = $("#list-wrap");
  const prevScroll = wrap ? wrap.scrollTop : 0;
  rebuildTree({ resetScroll: false });
  if (wrap) wrap.scrollTop = prevScroll;
  renderList();
  return true;
}

function toggleStoryOrderMissionLock(missionId) {
  const missionKey = String(missionId || "");
  if (!missionKey || typeof setStoryOrderMissionLocked !== "function") return false;
  const nextLocked = !(typeof storyOrderMissionLocked === "function" && storyOrderMissionLocked(missionKey));
  if (!setStoryOrderMissionLocked(missionKey, nextLocked)) return false;
  if (typeof scheduleStoryOrderSave === "function") scheduleStoryOrderSave();

  const wrap = $("#list-wrap");
  const prevScroll = wrap ? wrap.scrollTop : 0;
  rebuildTree({ resetScroll: false });
  if (wrap) wrap.scrollTop = prevScroll;
  renderList();
  return true;
}

function cycleStoryOrderEntryTagState(missionId, entryKey) {
  const missionKey = String(missionId || "");
  const key = String(entryKey || "");
  if (!missionKey || !key) return false;

  if (typeof setStoryOrderEntryTagState !== "function") {
    if (typeof setStoryOrderEntryPossiblyUnused !== "function") return false;
    const next = !(typeof storyOrderEntryPossiblyUnused === "function" && storyOrderEntryPossiblyUnused(missionKey, key));
    if (!setStoryOrderEntryPossiblyUnused(missionKey, key, next)) return false;
  } else {
    const current = typeof storyOrderEntryTagState === "function"
      ? storyOrderEntryTagState(missionKey, key)
      : "";
    const next = typeof nextStoryOrderEntryTagState === "function"
      ? nextStoryOrderEntryTagState(current)
      : (current === "unused" ? "" : "unused");
    if (!setStoryOrderEntryTagState(missionKey, key, next)) return false;
  }

  if (typeof scheduleStoryOrderSave === "function") scheduleStoryOrderSave();

  const wrap = $("#list-wrap");
  const prevScroll = wrap ? wrap.scrollTop : 0;
  rebuildTree({ resetScroll: false });
  if (wrap) wrap.scrollTop = prevScroll;
  renderList();
  return true;
}

function toggleStoryOrderEntryPossiblyUnused(missionId, entryKey) {
  return cycleStoryOrderEntryTagState(missionId, entryKey);
}

function removeStoryOrderEntryFromMissionAndSave(missionId, entryKey) {
  const missionKey = String(missionId || "");
  const key = String(entryKey || "");
  if (!missionKey || !key || typeof removeStoryOrderEntryFromMission !== "function") return false;
  if (!removeStoryOrderEntryFromMission(missionKey, key)) return false;
  if (typeof scheduleStoryOrderSave === "function") scheduleStoryOrderSave();

  const wrap = $("#list-wrap");
  const prevScroll = wrap ? wrap.scrollTop : 0;
  rebuildTree({ resetScroll: false });
  if (wrap) wrap.scrollTop = prevScroll;
  renderList();
  return true;
}

function clearStoryOrderDropIndicators(listEl) {
  if (!listEl) return;
  listEl.querySelectorAll(".story-order-drop-before, .story-order-drop-after").forEach((el) => {
    el.classList.remove("story-order-drop-before", "story-order-drop-after");
  });
}

function bindStoryOrderDragEvents(listEl) {
  if (!listEl) return;

  listEl.addEventListener("dragstart", (ev) => {
    const row = ev.target.closest(".row.item.story-order-draggable");
    if (!row) return;
    STATE.storyOrderDragKey = row.dataset.key || "";
    STATE.storyOrderDragMissionId = row.dataset.storyOrderMissionId || "";
    if (ev.dataTransfer) {
      ev.dataTransfer.effectAllowed = "move";
      try { ev.dataTransfer.setData("text/plain", STATE.storyOrderDragKey); } catch (_) {}
    }
    row.classList.add("story-order-dragging");
  });

  listEl.addEventListener("dragover", (ev) => {
    if (!STATE.storyOrderDragKey) return;
    const target = ev.target.closest(".row.item.story-order-draggable");
    if (!target) return;
    if (target.dataset.storyOrderMissionId !== STATE.storyOrderDragMissionId) return;
    if (target.dataset.key === STATE.storyOrderDragKey) return;
    ev.preventDefault();
    if (ev.dataTransfer) ev.dataTransfer.dropEffect = "move";
    const rect = target.getBoundingClientRect();
    const after = ev.clientY > rect.top + rect.height / 2;
    clearStoryOrderDropIndicators(listEl);
    target.classList.add(after ? "story-order-drop-after" : "story-order-drop-before");
  });

  listEl.addEventListener("dragleave", (ev) => {
    const target = ev.target.closest(".row.item.story-order-draggable");
    if (!target) return;
    if (ev.relatedTarget && target.contains(ev.relatedTarget)) return;
    target.classList.remove("story-order-drop-before", "story-order-drop-after");
  });

  listEl.addEventListener("drop", (ev) => {
    if (!STATE.storyOrderDragKey) return;
    const target = ev.target.closest(".row.item.story-order-draggable");
    if (!target) return;
    if (target.dataset.storyOrderMissionId !== STATE.storyOrderDragMissionId) return;
    if (target.dataset.key === STATE.storyOrderDragKey) return;
    ev.preventDefault();
    const rect = target.getBoundingClientRect();
    const after = ev.clientY > rect.top + rect.height / 2;
    const fromKey = STATE.storyOrderDragKey;
    const missionId = STATE.storyOrderDragMissionId;
    clearStoryOrderDropIndicators(listEl);
    STATE.storyOrderDragKey = "";
    STATE.storyOrderDragMissionId = "";
    reorderStoryOrderEntry(missionId, fromKey, target.dataset.key, after);
  });

  listEl.addEventListener("dragend", () => {
    STATE.storyOrderDragKey = "";
    STATE.storyOrderDragMissionId = "";
    clearStoryOrderDropIndicators(listEl);
    listEl.querySelectorAll(".story-order-dragging").forEach((el) => el.classList.remove("story-order-dragging"));
  });
}

function bindEvents() {
  let qTimer = null;
  $("#language").addEventListener("change", (ev) => {
    switchLanguage(ev.target.value);
  });
  $("#ui-language").addEventListener("click", (ev) => {
    setUiLocale(ev.currentTarget.dataset.nextLocale || "en");
  });
  $("#q").addEventListener("input", (ev) => {
    clearTimeout(qTimer);
    const v = ev.target.value;
    qTimer = setTimeout(() => {
      STATE.filters.q = normalizeSearchText(v);
      applyFilters();
    }, 120);
  });
  const sortSelect = $("#sort");
  if (sortSelect) {
    STATE.sortMode = normalizeStorySortMode(sortSelect.value || STATE.sortMode);
    syncStorySortControl();
    sortSelect.addEventListener("change", (ev) => {
      setStorySortMode(ev.target.value);
    });
  }
  $("#reset").addEventListener("click", () => {
    clearTimeout(qTimer);
    preserveCurrentTreeExpansion();
    STATE.filters = createDefaultFilters();
    STATE.sortMode = "story";
    $("#q").value = "";
    syncStorySortControl();
    $$(".chip.on").forEach((c) => c.classList.remove("on"));
    applyFilters();
  });
  $("#list-wrap").addEventListener("scroll", renderList);
  window.addEventListener("resize", renderList);

  bindStoryOrderDragEvents($("#list"));

  // Delegated click on the tree (groups + items).
  $("#list").addEventListener("click", (ev) => {
    const missionLockButton = ev.target.closest(".story-order-mission-lock-button");
    if (missionLockButton) {
      ev.preventDefault();
      ev.stopPropagation();
      toggleStoryOrderMissionLock(missionLockButton.dataset.missionId);
      return;
    }
    const missionMoveUnusedButton = ev.target.closest(".story-order-mission-move-unused-button");
    if (missionMoveUnusedButton) {
      ev.preventDefault();
      ev.stopPropagation();
      if (missionMoveUnusedButton.disabled) return;
      moveStoryOrderMissionUnusedToEnd(missionMoveUnusedButton.dataset.missionId);
      return;
    }
    const missionReviewButton = ev.target.closest(".story-order-mission-review-button");
    if (missionReviewButton) {
      ev.preventDefault();
      ev.stopPropagation();
      if (typeof jumpToNextUncertainRow === "function") {
        jumpToNextUncertainRow(missionReviewButton.dataset.missionId);
      }
      return;
    }
    const unusedToggle = ev.target.closest(".story-order-unused-toggle");
    if (unusedToggle) {
      ev.preventDefault();
      ev.stopPropagation();
      toggleStoryOrderEntryPossiblyUnused(unusedToggle.dataset.missionId, unusedToggle.dataset.entryKey);
      return;
    }
    const removeButton = ev.target.closest(".story-order-remove-from-mission");
    if (removeButton) {
      ev.preventDefault();
      ev.stopPropagation();
      removeStoryOrderEntryFromMissionAndSave(removeButton.dataset.missionId, removeButton.dataset.entryKey);
      return;
    }
    const row = ev.target.closest(".row");
    if (!row) return;
    if (row.classList.contains("group")) {
      togglePath(row.dataset.path);
    } else if (row.classList.contains("item")) {
      loadConv(row.dataset.key);
    }
  });

  $("#show-empty").addEventListener("change", (ev) => {
    STATE.showEmpty = ev.target.checked;
    if (STATE.selectedKey && STATE.convCache.has(STATE.selectedKey)) {
      renderConv(STATE.convCache.get(STATE.selectedKey));
    }
  });
  $("#show-raw").addEventListener("change", (ev) => {
    STATE.showRaw = ev.target.checked;
    if (STATE.selectedKey && STATE.convCache.has(STATE.selectedKey)) {
      renderConv(STATE.convCache.get(STATE.selectedKey));
    }
  });
  const showDebug = $("#show-debug");
  if (showDebug) {
    showDebug.addEventListener("click", () => {
      const next = showDebug.getAttribute("aria-pressed") !== "true";
      showDebug.setAttribute("aria-pressed", next ? "true" : "false");
      STATE.showDebug = next;
      document.body.classList.toggle("show-debug", next);
      window.dispatchEvent(new CustomEvent("webui:debug-changed", {
        detail: { enabled: next },
      }));
      if (STATE.selectedKey && STATE.convCache.has(STATE.selectedKey)) {
        renderConv(STATE.convCache.get(STATE.selectedKey));
      }
      if (typeof renderList === "function") renderList();
    });
  }
  $("#inline-tag-mode").addEventListener("change", (ev) => {
    setInlineTagDisplayMode(ev.target.checked ? "raw" : "rendered");
  });
  $("#gender-variant").addEventListener("click", () => {
    const btn = $("#gender-variant");
    const isF = btn.getAttribute("aria-pressed") === "true";
    setGenderVariant(isF ? "m" : "f");
  });
  $("#reveal-current").addEventListener("click", () => {
    const entry = getSelectedEntry();
    if (!entry) return;
    revealEntryInTree(entry);
  });

  $("#conv-lines").addEventListener("click", (ev) => {
    const clickTarget = ev.target && ev.target.closest ? ev.target : null;
    const storyOrderAdoptButton = clickTarget ? clickTarget.closest(".story-order-compare-adopt-button") : null;
    if (storyOrderAdoptButton) {
      ev.preventDefault();
      ev.stopPropagation();
      if (!storyOrderAdoptButton.disabled && typeof storyOrderAdoptMissionOrder === "function") {
        storyOrderAdoptMissionOrder(storyOrderAdoptButton.dataset.missionId, storyOrderAdoptButton.dataset.source);
      }
      return;
    }
    if (handleInlineImageModalActivate(ev.target)) {
      ev.preventDefault();
      ev.stopPropagation();
      return;
    }
    if (handleGenderToggleActivate(ev.target)) {
      ev.preventDefault();
      ev.stopPropagation();
    }
  });

  $("#conv-lines").addEventListener("keydown", (ev) => {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    if (handleInlineImageModalActivate(ev.target)) {
      ev.preventDefault();
      ev.stopPropagation();
      return;
    }
    if (handleGenderToggleActivate(ev.target)) {
      ev.preventDefault();
      ev.stopPropagation();
    }
  });

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") closeInlineImageModal();
  });
}

// ---------- filtering + tree build ----------
function applyFilters() {
  syncFilterSectionActiveCounts();
  syncStoryOrderEditor();
  const f = STATE.filters;
  let out = STATE.entries;

  if (f.kinds.size) out = out.filter((e) => entryMatchesKindFilters(e, f.kinds));
  if (f.dataTypes.size) out = out.filter((e) => entryMatchesTreeDataTypeFilters(e, f.dataTypes));
  if (f.media.size) out = out.filter((e) => entryMatchesMediaFilters(e, f.media));
  if (f.issues.size) out = out.filter((e) => entryMatchesStoryIssueFilters(e, f.issues));
  if (f.recoveryMethods.size) out = out.filter((e) => entryMatchesRecoveryMethodFilters(e, f.recoveryMethods));
  const tokens = window.WebUI.parseQuery(f.q);
  if (tokens.length) {
    if (typeof ensureStorySearchIndexLoaded === "function" && !STATE.storySearchLoaded) {
      void ensureStorySearchIndexLoaded().then(() => {
        if (STATE.filters.q && STATE.storySearchLoaded) applyFilters();
      });
    }
    // OR semantics: keep an entry if any token matches any searchable field, and
    // record how many distinct tokens matched so multi-word queries can rank by it.
    const scores = new Map();
    out = out.filter((e) => {
      const hay = entrySearchHaystack(e);
      let score = 0;
      for (const token of tokens) {
        if (hay.includes(token) || entryMatchesOptionIdSearch(e, token)) score += 1;
      }
      if (score <= 0) return false;
      scores.set(e.k, score);
      return true;
    });
    STATE.searchScores = scores;
  } else {
    STATE.searchScores = null;
  }
  STATE.searchTokens = tokens;

  STATE.filtered = out;
  $("#shown").textContent = out.length.toLocaleString();
  $("#total").textContent = STATE.entries.length.toLocaleString();

  rebuildTree();
}

function rebuildTree({ resetScroll = true } = {}) {
  // A multi-word query switches to a flat list ranked by how many keywords each
  // entry matched, so the best hits float to the top regardless of story order.
  if ((STATE.searchTokens || []).length > 1) {
    rebuildFlatSearchList({ resetScroll });
    return;
  }

  // Group by data type and then mission. Kind (dlg/sns/misc) is not a tree
  // level, so story and chat from the same mission stay together.
  const tree = {};
  const sortMode = STATE.sortMode || "story";
  for (const e of STATE.filtered) {
    for (const dataType of entryTreeDataTypesForSort(e, sortMode)) {
      (tree[dataType] ??= {});
      const group = treeGroupInfo(e, dataType);
      const bucket = (tree[dataType][group.key] ??= { ...group, items: [] });
      bucket.items.push(e);
    }
  }
  for (const dataType of Object.keys(tree)) {
    tree[dataType] = collapseSingletonSourceGroups(tree[dataType]);
  }

  const makeBucketSorter = () => makeItemSorter(sortMode);
  const autoExpand = !!STATE.filters.q;

  const rows = [];
  let offset = 0;
  const pushGroup = (level, path, label, count, mono, raw = "", extra = {}) => {
    const expanded = autoExpand || STATE.expanded.has(path);
    rows.push({
      type: "group", level, path, label, count, mono, raw,
      ...extra,
      top: offset, h: ROW_GROUP_H, expanded,
    });
    offset += ROW_GROUP_H;
    return expanded;
  };
  const pushItem = (entry) => {
    rows.push({
      type: "item", entry,
      top: offset, h: ROW_ITEM_H,
    });
    offset += ROW_ITEM_H;
  };

  const dataTypeKeys = Object.keys(tree).sort(compareDataTypeKeys);

  for (const dataType of dataTypeKeys) {
    const dataTypeTitle = dataTypeLabel(dataType);
    const dataTypeCount = sumLeaves(tree[dataType]);
    if (!pushGroup(0, dataType, dataTypeTitle, dataTypeCount, false)) continue;

    const missions = Object.keys(tree[dataType]).sort(missionSort);
    for (const m of missions) {
      const mPath = `${dataType}/${m}`;
      const bucket = tree[dataType][m];
      const items = bucket.items;
      const sortItems = makeBucketSorter(items);
      items.sort(sortItems);
      const storyOrderMissionId = storyOrderMissionIdForGroup(m);
      if (!pushGroup(1, mPath, bucket.label, items.length, bucket.mono, bucket.raw, { storyOrderMissionId })) continue;

      const cutsceneFamilies = new Map();
      for (const it of items) {
        const family = cutsceneFamilyInfo(it);
        if (!family) continue;
        const familyBucket = cutsceneFamilies.get(family.key) || { ...family, items: [] };
        familyBucket.items.push(it);
        cutsceneFamilies.set(family.key, familyBucket);
      }
      for (const familyBucket of cutsceneFamilies.values()) {
        familyBucket.items.sort(makeBucketSorter(familyBucket.items));
      }

      const emittedFamilies = new Set();
      for (const it of items) {
        const family = cutsceneFamilyInfo(it);
        const familyBucket = family ? cutsceneFamilies.get(family.key) : null;
        if (!familyBucket || familyBucket.items.length < 2) {
          pushItem(it);
          continue;
        }
        if (emittedFamilies.has(family.key)) continue;
        emittedFamilies.add(family.key);

        const familyPath = `${mPath}/${familyBucket.pathKey}`;
        if (!pushGroup(2, familyPath, familyBucket.label, familyBucket.items.length, familyBucket.mono, familyBucket.raw)) {
          continue;
        }
        for (const member of familyBucket.items) pushItem(member);
      }
    }
  }

  STATE.rows = rows;
  STATE.totalH = offset;
  $("#list-spacer").style.height = offset + "px";
  if (resetScroll) $("#list-wrap").scrollTop = 0;
  renderList();
}

// Flat, ranked result list used when a multi-word query is active: order by
// keyword-match count (desc), breaking ties with the active sort mode.
function rebuildFlatSearchList({ resetScroll = true } = {}) {
  const scores = STATE.searchScores || new Map();
  const tieBreak = makeItemSorter(STATE.sortMode || "story");
  const items = [...STATE.filtered].sort((a, b) => {
    const delta = (scores.get(b.k) || 0) - (scores.get(a.k) || 0);
    return delta || tieBreak(a, b);
  });

  const rows = [];
  let offset = 0;
  for (const entry of items) {
    rows.push({ type: "item", entry, top: offset, h: ROW_ITEM_H });
    offset += ROW_ITEM_H;
  }

  STATE.rows = rows;
  STATE.totalH = offset;
  $("#list-spacer").style.height = offset + "px";
  if (resetScroll) $("#list-wrap").scrollTop = 0;
  renderList();
}

// SNS chats happen on the player's terminal *before* the actual cutscene plays,
// authored dialog follows, then standalone radio for that scene, and finally
// ambient / misc content.
const KIND_ORDER = {
  sns: 0,
  cutscene: 1,
  video: 1.5,
  dlg: 2,
  black: 3,
  remotecomm: 4,
  radio: 5,
  reading: 5.5,
  mail: 6,
  prts: 7,
  wiki: 8,
  responsive: 9,
  env: 10,
  misc: 11,
};

function compareEntryName(a, b) {
  const titleA = displayEntryTitle(a) || String(a && a.k || "");
  const titleB = displayEntryTitle(b) || String(b && b.k || "");
  return titleA.localeCompare(titleB, undefined, { numeric: true, sensitivity: "base" })
    || String(a && a.k || "").localeCompare(String(b && b.k || ""), undefined, { numeric: true, sensitivity: "base" });
}

function makeItemSorter(mode) {
  const kindRank = (k) => KIND_ORDER[k] ?? 99;
  const lineCount = (entry) => {
    const count = Number(entry && entry.n);
    return Number.isFinite(count) ? count : 0;
  };
  const naturalCompare = (a, b) => (
    kindRank(a && a.d) - kindRank(b && b.d)
  ) || compareEntryName(a, b);
  switch (mode) {
    case "lines-desc": return (a, b) => (lineCount(b) - lineCount(a)) || naturalCompare(a, b);
    case "lines-asc":  return (a, b) => (lineCount(a) - lineCount(b)) || naturalCompare(a, b);
    case "key":        return (a, b) => String(a && a.k || "").localeCompare(String(b && b.k || ""), undefined, { numeric: true });
    case "story":      return makeStorySorter();
    // natural: kind first, then the displayed scene name/key.
    default:           return naturalCompare;
  }
}

// Story sort mode: trust story_order.json only. No env-talk segregation,
// no kind-rank, no display-name fallback. Items with a recovered position
// come first in that order; items without one fall back to key compare for
// stability only.
function makeStorySorter() {
  return (a, b) => {
    const ap = typeof storyOrderPositionForEntry === "function" ? storyOrderPositionForEntry(a) : null;
    const bp = typeof storyOrderPositionForEntry === "function" ? storyOrderPositionForEntry(b) : null;
    const hasA = Number.isFinite(ap);
    const hasB = Number.isFinite(bp);
    if (hasA && hasB && ap !== bp) return ap - bp;
    if (hasA !== hasB) return hasA ? -1 : 1;
    return String(a && a.k || "").localeCompare(
      String(b && b.k || ""),
      undefined,
      { numeric: true },
    );
  };
}

function entryIsReadingPopup(entry) {
  return String(entry && entry.d || "") === "text"
    && typeof entryHasTag === "function"
    && entryHasTag(entry, "readingPopup");
}

function missionSort(a, b) {
  // "a1m6d10" < "a1m6d2" lexically; do a natural-ish sort by digit chunks.
  const ax = a.match(/(\D+|\d+)/g) || [];
  const bx = b.match(/(\D+|\d+)/g) || [];
  for (let i = 0; i < Math.max(ax.length, bx.length); i++) {
    const ai = ax[i], bi = bx[i];
    if (ai === undefined) return -1;
    if (bi === undefined) return 1;
    const an = +ai, bn = +bi;
    if (!isNaN(an) && !isNaN(bn)) { if (an !== bn) return an - bn; }
    else if (ai !== bi) return ai < bi ? -1 : 1;
  }
  return 0;
}
