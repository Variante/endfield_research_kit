// Endfield conversation browser - tree/filter helpers.

function normalizeSearchText(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function searchTextIncludes(value, q) {
  return normalizeSearchText(value).includes(q);
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
  return entryDataTypes(entry);
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

  const storyMissionId = entryStoryMissionId(entry);
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
function buildKindChips() {
  const wrap = $("#kind-filter");
  wrap.innerHTML = "";

  const kindCounts = countBy(STATE.entries, (e) => entryGroupedKindKey(e));
  const kindKeys = Object.keys(kindCounts)
    .filter((k) => !shouldSuppressKindChip(k))
    .sort((a, b) => {
      const aName = kindMeta(a).name || formatStructuredLabel(a);
      const bName = kindMeta(b).name || formatStructuredLabel(b);
      return aName.localeCompare(bName, undefined, { numeric: true });
    });
  const availableTokens = new Set(kindKeys.map(kindFilterToken));
  pruneFilterSet(STATE.filters.kinds, availableTokens);
  for (const k of kindKeys) {
    const n = kindCounts[k] || 0;
    if (!n) continue;
    const meta = kindMeta(k);
    const chip = document.createElement("span");
    chip.className = `chip kind-chip ${meta.cls || ""}`;
    chip.dataset.value = kindFilterToken(k);
    if (STATE.filters.kinds.has(kindFilterToken(k))) chip.classList.add("on");
    chip.textContent = `${meta.name} (${n})`;
    chip.addEventListener("click", () => toggleSet(STATE.filters.kinds, kindFilterToken(k), chip));
    wrap.appendChild(chip);
  }
}

function buildDataTypeChips() {
  const counts = {};
  for (const entry of STATE.entries) {
    for (const dataType of entryTreeDataTypes(entry)) {
      counts[dataType] = (counts[dataType] || 0) + 1;
    }
  }
  const wrap = $("#type-filter");
  wrap.innerHTML = "";
  const dataTypeKeys = Object.keys(counts)
    .filter(Boolean)
    .sort((a, b) => compareDataTypeKeys(a, b, counts));
  pruneFilterSet(STATE.filters.dataTypes, new Set(dataTypeKeys));
  for (const dataType of dataTypeKeys) {
    const n = counts[dataType] || 0;
    if (!n) continue;
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.dataset.value = dataType;
    if (STATE.filters.dataTypes.has(dataType)) chip.classList.add("on");
    chip.textContent = `${dataTypeLabel(dataType)} (${n})`;
    chip.addEventListener("click", () => toggleSet(STATE.filters.dataTypes, dataType, chip));
    wrap.appendChild(chip);
  }
}

function buildMediaChips() {
  const wrap = $("#media-filter");
  if (!wrap) return;

  const counts = {};
  for (const entry of STATE.entries) {
    for (const mediaKey of entryMediaTypeFilterKeys(entry)) {
      counts[mediaKey] = (counts[mediaKey] || 0) + 1;
    }
  }
  wrap.innerHTML = "";
  const mediaKeys = MEDIA_TYPE_FILTER_KEYS.filter((key) => counts[key]);
  pruneFilterSet(STATE.filters.media, new Set(mediaKeys));
  for (const mediaKey of mediaKeys) {
    const n = counts[mediaKey] || 0;
    if (!n) continue;
    const chip = document.createElement("span");
    chip.className = "chip media-chip";
    chip.dataset.value = mediaKey;
    if (STATE.filters.media.has(mediaKey)) chip.classList.add("on");
    chip.textContent = `${mediaTypeFilterLabel(mediaKey)} (${n})`;
    chip.addEventListener("click", () => toggleSet(STATE.filters.media, mediaKey, chip));
    wrap.appendChild(chip);
  }
}

function buildStoryIssueChips() {
  const wrap = $("#story-issue-filter");
  if (!wrap) return;

  wrap.innerHTML = "";
  const counts = {};
  for (const entry of STATE.entries) {
    for (const code of new Set(entryStoryIssues(entry))) {
      counts[code] = (counts[code] || 0) + 1;
    }
  }

  const issueKeys = STORY_ISSUE_ORDER.filter((code) => counts[code]);
  pruneFilterSet(STATE.filters.issues, new Set(issueKeys));
  for (const code of issueKeys) {
    const n = counts[code] || 0;
    if (!n) continue;
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.dataset.value = code;
    if (STATE.filters.issues.has(code)) chip.classList.add("on");
    chip.textContent = `${storyIssueLabel(code)} (${n})`;
    chip.addEventListener("click", () => toggleSet(STATE.filters.issues, code, chip));
    wrap.appendChild(chip);
  }
}

function buildRecoveryMethodChips() {
  const wrap = $("#recovery-method-filter");
  if (!wrap) return;

  wrap.innerHTML = "";
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
  for (const method of methodKeys) {
    const n = counts[method] || 0;
    if (!n) continue;
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.dataset.value = method;
    if (STATE.filters.recoveryMethods.has(method)) chip.classList.add("on");
    chip.textContent = `${recoveryMethodLabel(method)} (${n})`;
    chip.addEventListener("click", () => toggleSet(STATE.filters.recoveryMethods, method, chip));
    wrap.appendChild(chip);
  }
}

function toggleSet(set, value, el) {
  if (set.has(value)) set.delete(value);
  else set.add(value);
  el.classList.toggle("on");
  applyFilters();
}

const STORY_SORT_MODES = new Set(["natural", "lines-desc", "lines-asc", "key"]);

function normalizeStorySortMode(mode) {
  const normalized = String(mode || "");
  return STORY_SORT_MODES.has(normalized) ? normalized : "natural";
}

function syncStorySortControl() {
  const sortSelect = $("#sort");
  if (sortSelect) sortSelect.value = normalizeStorySortMode(STATE.sortMode);
}

function setStorySortMode(mode, { resetScroll = true } = {}) {
  STATE.sortMode = normalizeStorySortMode(mode);
  syncStorySortControl();
  rebuildTree({ resetScroll });
}

function bindEvents() {
  let qTimer = null;
  $("#language").addEventListener("change", (ev) => {
    switchLanguage(ev.target.value);
  });
  $("#ui-language").addEventListener("change", (ev) => {
    setUiLocale(ev.target.value);
  });
  $("#filter-toggle").addEventListener("click", () => {
    setFiltersCollapsed(!STATE.filtersCollapsed);
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
    STATE.filters = createDefaultFilters();
    STATE.sortMode = "natural";
    STATE.expanded.clear();
    $("#q").value = "";
    syncStorySortControl();
    $$(".chip.on").forEach((c) => c.classList.remove("on"));
    applyFilters();
  });

  $("#list-wrap").addEventListener("scroll", renderList);
  window.addEventListener("resize", renderList);

  // Delegated click on the tree (groups + items).
  $("#list").addEventListener("click", (ev) => {
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
  $("#inline-tag-mode").addEventListener("change", (ev) => {
    setInlineTagDisplayMode(ev.target.checked ? "raw" : "rendered");
  });
  $("#gender-variant").addEventListener("change", (ev) => {
    setGenderVariant(ev.target.checked ? "f" : "m");
  });
  $("#reveal-current").addEventListener("click", () => {
    const entry = getSelectedEntry();
    if (!entry) return;
    revealEntryInTree(entry);
  });

  $("#conv-lines").addEventListener("click", (ev) => {
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
  const f = STATE.filters;
  let out = STATE.entries;

  if (f.kinds.size) out = out.filter((e) => entryMatchesKindFilters(e, f.kinds));
  if (f.dataTypes.size) out = out.filter((e) => entryMatchesTreeDataTypeFilters(e, f.dataTypes));
  if (f.media.size) out = out.filter((e) => entryMatchesMediaFilters(e, f.media));
  if (f.issues.size) out = out.filter((e) => entryMatchesStoryIssueFilters(e, f.issues));
  if (f.recoveryMethods.size) out = out.filter((e) => entryMatchesRecoveryMethodFilters(e, f.recoveryMethods));
  if (f.q) {
    const q = f.q;
    if (typeof ensureStorySearchIndexLoaded === "function" && !STATE.storySearchLoaded) {
      void ensureStorySearchIndexLoaded().then(() => {
        if (STATE.filters.q && STATE.storySearchLoaded) applyFilters();
      });
    }
    out = out.filter((e) => {
      if (searchTextIncludes(e.k, q)) return true;
      if (searchTextIncludes(e.m, q)) return true;
      if (e.title && searchTextIncludes(e.title, q)) return true;
      const missionName = missionDisplay(entryTreeMissionId(e), entryDataType(e));
      if (missionName && searchTextIncludes(missionName, q)) return true;
      for (const dataType of entryTreeDataTypes(e)) {
        if (searchTextIncludes(dataType, q)) return true;
        if (searchTextIncludes(dataTypeLabel(dataType), q)) return true;
        const group = treeGroupInfo(e, dataType);
        if (group.label && searchTextIncludes(group.label, q)) return true;
        if (group.raw && searchTextIncludes(group.raw, q)) return true;
      }
      for (const typeKey of entryMediaTypeFilterKeys(e)) {
        if (searchTextIncludes(typeKey, q)) return true;
        if (searchTextIncludes(typeFilterLabel(typeKey), q)) return true;
      }
      for (const tag of entryMetadataTags(e)) {
        if (searchTextIncludes(tag, q)) return true;
        if (searchTextIncludes(metadataTagLabel(tag), q)) return true;
      }
      for (const method of entryRecoveryMethods(e)) {
        if (searchTextIncludes(method, q)) return true;
        if (searchTextIncludes(recoveryMethodLabel(method), q)) return true;
      }
      if (entryMatchesOptionIdSearch(e, q)) return true;
      if (e.p && searchTextIncludes(e.p, q)) return true;
      if (e.x && searchTextIncludes(e.x, q)) return true;
      for (const aid of e.c) {
        if (searchTextIncludes(aid, q)) return true;
        for (const nm of (STATE.actorNames[aid] || [])) {
          if (searchTextIncludes(nm, q)) return true;
        }
      }
      return false;
    });
  }

  STATE.filtered = out;
  $("#shown").textContent = out.length.toLocaleString();
  $("#total").textContent = STATE.entries.length.toLocaleString();

  rebuildTree();
}

function rebuildTree({ resetScroll = true } = {}) {
  // Group by data type and then mission. Kind (dlg/sns/misc) is not a tree
  // level, so story and chat from the same scene end up next to each other.
  // user can browse them together. Kind is still visible per item (badge) and
  // filterable via the chip row above.
  const tree = {};
  for (const e of STATE.filtered) {
    for (const dataType of entryTreeDataTypes(e)) {
      (tree[dataType] ??= {});
      const group = treeGroupInfo(e, dataType);
      const bucket = (tree[dataType][group.key] ??= { ...group, items: [] });
      bucket.items.push(e);
    }
  }
  for (const dataType of Object.keys(tree)) {
    tree[dataType] = collapseSingletonSourceGroups(tree[dataType]);
  }

  const sortMode = STATE.sortMode || "natural";
  const makeBucketSorter = (items) =>
    makeItemSorter(sortMode, { graphOrderActive: items.some(hasEntryGraphOrder) });
  const autoExpand = !!STATE.filters.q;

  const rows = [];
  let offset = 0;
  const pushGroup = (level, path, label, count, mono, raw = "") => {
    const expanded = autoExpand || STATE.expanded.has(path);
    rows.push({
      type: "group", level, path, label, count, mono, raw,
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
      if (!pushGroup(1, mPath, bucket.label, items.length, bucket.mono, bucket.raw)) continue;

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

// SNS chats happen on the player's terminal *before* the actual cutscene plays,
// authored dialog follows, then standalone radio for that scene, and finally
// ambient / misc content.
const KIND_ORDER = {
  sns: 0,
  cutscene: 1,
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

function entryGraphOrder(entry) {
  const graphOrder = Number(entry && entry.go);
  return Number.isFinite(graphOrder) ? graphOrder : null;
}

function hasEntryGraphOrder(entry) {
  return entryGraphOrder(entry) !== null;
}

function makeItemSorter(mode, { graphOrderActive = false } = {}) {
  const kindRank = (k) => KIND_ORDER[k] ?? 99;
  const lineCount = (entry) => {
    const count = Number(entry && entry.n);
    return Number.isFinite(count) ? count : 0;
  };
  const fallbackSceneRank = (entry) => {
    const scene = Number(entry && entry.s);
    return Number.isFinite(scene) ? scene : 0;
  };
  const sceneRank = (entry) => {
    const graphOrder = entryGraphOrder(entry);
    if (graphOrder !== null) return graphOrder;
    if (entry && entry.d === "env" && entryDataType(entry) !== "env") {
      return (graphOrderActive ? 2000000 : 1000000) + fallbackSceneRank(entry);
    }
    const fallback = fallbackSceneRank(entry);
    return graphOrderActive ? 1000000 + fallback : fallback;
  };
  const naturalCompare = (a, b) =>
    (sceneRank(a) - sceneRank(b)) || (kindRank(a.d) - kindRank(b.d)) || a.k.localeCompare(b.k);
  switch (mode) {
    case "lines-desc": return (a, b) => (lineCount(b) - lineCount(a)) || naturalCompare(a, b);
    case "lines-asc":  return (a, b) => (lineCount(a) - lineCount(b)) || naturalCompare(a, b);
    case "key":        return (a, b) => a.k.localeCompare(b.k);
    // natural: scene first, then kind so sns_X_1 sits above dlg_X_1.
    default:           return naturalCompare;
  }
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
