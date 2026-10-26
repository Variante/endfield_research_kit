// Activities browses published ActivityTable rows with their linked
// supporting tables. Guides are shared with Text; availability is not inferred.
(() => {
  const W = window.WebUI;
  const $ = (id) => document.getElementById(`activities-${id}`);
  const state = { language: '', table: null, rows: [], selected: '', generation: 0, times: {}, tags: {}, activities: {}, media: { rows: {} }, mediaError: '', related: {}, story: null };
  const language = () => String(document.querySelector('#language')?.value || 'CN').toUpperCase();
  let countLanguage = '';
  let total = null;
  async function loadCount() {
    const requestedLanguage = language();
    try {
      await W.referenceRows.prepare(requestedLanguage);
      if (requestedLanguage !== language()) return;
      const table = W.referenceRows.tables().find((entry) => entry.table === 'ActivityTable.json');
      countLanguage = requestedLanguage;
      total = Number.isInteger(table?.rows) ? table.rows : null;
    } catch {
      if (requestedLanguage === language()) { countLanguage = requestedLanguage; total = null; }
    }
  }
  const en = () => window.WEBUI_UI_LOCALE === 'en';
  const text = (english, chinese) => en() ? english : chinese;
  const path = (file) => `data/lang/${encodeURIComponent(state.language)}/reference/${file}`;

  const panel = W.filters.createPanelToggle({
    panel: '#activities-filter-panel', toggle: '#activities-filter-toggle', left: '#activities-left',
    storageKey: 'activities_filters_collapsed', labels: (collapsed) => collapsed ? text('Show filters', '显示筛选') : text('Hide filters', '隐藏筛选'),
  });
  const facets = W.facets.create({ countMode: 'total', groups: [
    { id: 'type', container: '#activities-type-filter', section: 'activities-type', param: 'activityType', values: (row) => row.bucket },
    { id: 'tag', container: '#activities-tag-filter', section: 'activities-tag', param: 'activityTag', values: (row) => row.activityTags,
      label: (id) => state.tags[id]?.name?.text || id, title: (id) => id },
    { id: 'schedule', container: '#activities-schedule-filter', section: 'activities-schedule', param: 'activitySchedule', values: (row) => row.scheduleTag,
      label: (id) => ({ permanent: text('Permanent activity', '常驻活动'), limited: text('Limited-time activity', '限时活动'), unknown: text('Unspecified time', '未指定时间') })[id] },
  ], onChange: () => { W.continuousList.reset($('list')); renderList(); writeUrl(); } });
  facets.fromParams(new URL(location.href).searchParams, { silent: true });
  W.setupListShellSplitters({ shell: $('app'), sidebar: $('left'), pane: $('splitter'), panel: $('filter-panel'), filter: $('filter-splitter'), list: $('list'),
    paneStorageKey: 'webui_activities_splitter_width', filterStorageKey: 'webui_filter_splitter_height_activities', minSidebarWidth: 320 });

  W.setupSplitter({
    handle: $('mobile-splitter'), storageKey: 'activities_mobile_list_height', bodyDragClass: 'is-resizing-filter',
    client: (event) => event.clientY, keys: { decrease: ['ArrowUp'], increase: ['ArrowDown'] },
    enabled: W.splitterUtils.isMobileLayout,
    bounds: () => ({ min: 140, max: Math.max(140, window.innerHeight * .7) }),
    read: () => $('list').getBoundingClientRect().height,
    write: (height) => { $('list').style.height = `${Math.round(height)}px`; $('list').style.maxHeight = 'none'; },
    clear: () => { $('list').style.removeProperty('height'); $('list').style.removeProperty('max-height'); },
    sync: (controller) => {
      if (!W.splitterUtils.isMobileLayout()) { controller.clear({ commit: false }); return; }
      if ($('app').getBoundingClientRect().width < 48) return;
      controller.set(W.splitterUtils.readStoredNumber('activities_mobile_list_height') ?? window.innerHeight * .42, { persist: false, commit: false });
    },
  });

  function writeUrl() {
    // Shared storage restores hidden controls too; those changes must not navigate.
    if (document.body.dataset.activeView !== 'gameplay' || W.gameplayTabs?.kind !== 'activity' || $('app').hidden) return;
    if (!location.search && !location.hash) return;
    const url = new URL(location.href);
    url.hash = 'gameplay';
    url.searchParams.set('gameplayKind', 'activity');
    url.searchParams.delete('activityTable');
    if (state.selected) url.searchParams.set('activity', state.selected); else url.searchParams.delete('activity');
    if ($('q').value) url.searchParams.set('activityQ', $('q').value); else url.searchParams.delete('activityQ');
    url.searchParams.set('activitySort', $('sort').value);
    facets.toParams(url.searchParams);
    history.replaceState(null, '', url);
  }

  // Compare authored calendar components; do not assume the game's time zone.
  function timeKey(value) {
    const match = /^(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:[ T](\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?$/.exec(String(value || ''));
    return match ? match.slice(1).map((part) => String(part || 0).padStart(2, '0')).join('') : '';
  }
  // Official IDs can share a localized label. Present one union facet while
  // retaining all source IDs in raw records and accepting existing URLs.
  function categoryKey(id) {
    const label = state.tags[id]?.name?.text;
    return label ? Object.keys(state.tags).sort().find((key) => state.tags[key]?.name?.text === label) || id : id;
  }
  function enrich(row, raw) {
    const parent = raw.activityId && state.activities[raw.activityId];
    const activity = parent || raw;
    // Use the first authored slot consistently without assigning a region or zone.
    const ranges = (state.times[activity.timeId]?.timeRangeList || []).slice(0, 1);
    const opens = ranges.map((range) => timeKey(range.openTime)).filter(Boolean).sort();
    const enriched = { ...row, raw, timeId: activity.timeId, ranges, start: opens[0] || '',
      activityTags: [...new Set((activity.tagIds || []).map(categoryKey))], scheduleTag: ranges.length ? (ranges.every((range) => !range.closeTime) ? ['permanent'] : ranges.every((range) => !!range.closeTime) ? ['limited'] : ['permanent', 'limited']) : ['unknown'] };
    // Search the same serialized row as before, built once instead of per keystroke.
    enriched.search = JSON.stringify(enriched).toLocaleLowerCase();
    return enriched;
  }
  function rangeText(range, { start = text('Unspecified start', '未指定开始时间'), end = text('No configured end', '未配置结束时间') } = {}) {
    return `${range.openTime || start} → ${range.closeTime || end}`;
  }
  function timeSummary(row) {
    const distinct = [...new Set(row.ranges.map((range) => rangeText(range)))];
    return distinct.join(' / ') || text('Time unspecified', '未指定时间');
  }
  function scheduleTags(row) {
    const tags = document.createElement('span'); tags.className = 'activities-schedule-tags';
    for (const kind of row.scheduleTag) {
      if (kind === 'unknown') continue;
      const tag = document.createElement('span');
      tag.className = `activities-schedule-tag is-${kind}`;
      tag.textContent = kind === 'limited' ? text('Limited-time', '限时活动') : text('Permanent', '常驻活动');
      tags.appendChild(tag);
    }
    return tags;
  }
  const tableStem = () => 'ActivityTable';
  function mediaFor(row, stem = tableStem()) {
    const refs = [...(state.media.rows[row.mediaKey || `${stem}/${row.id}`] || [])];
    if (row.raw.activityId) refs.push(...(state.media.rows[`ActivityTable/${row.raw.activityId}`] || []));
    const seen = new Set();
    return refs.filter((ref) => { if (seen.has(ref.rel)) return false; seen.add(ref.rel); return true; });
  }
  function image(ref, preview = false) {
    const img = document.createElement('img');
    img.src = W.exportFullHref(ref.rel); img.alt = preview ? ref.token : ''; img.loading = 'lazy'; img.decoding = 'async';
    img.addEventListener('error', () => { img.hidden = true; }, { once: true });
    return img;
  }
  function renderTimes(host, row) {
    const block = document.createElement('section'); block.className = 'gameplay-section activities-times';
    const title = document.createElement('h3'); title.className = 'gameplay-section-title'; title.textContent = text('Configured schedule', '配置时间'); block.appendChild(title);
    if (!row.ranges.length) { const note = document.createElement('span'); note.textContent = timeSummary(row); block.appendChild(note); }
    row.ranges.forEach((range) => {
      const line = document.createElement('div');
      const kind = range.closeTime ? text('Limited-time', '限时') : text('Permanent', '常驻');
      line.textContent = `${kind}: ${rangeText(range, { end: text('Permanent (no configured end)', '常驻（未配置结束时间）') })}`;
      block.appendChild(line);
    });
    host.appendChild(block);
  }
  function authoredImage(row, field, refs = mediaFor(row)) {
    const activity = (row.raw.activityId && state.activities[row.raw.activityId]) || row.raw;
    const token = activity[field];
    if (!token) return null;
    return refs.find((ref) => ref.token === token && ref.field === field && ref.table !== 'ItemTable') || null;
  }
  function imagePreview(ref) {
    const preview = document.createElement('span');
    preview.className = 'inline-image-tag has-preview activities-image-preview';
    preview.tabIndex = 0; preview.setAttribute('role', 'button');
    preview.setAttribute('aria-label', text('Preview image: ', '预览图片：') + ref.token);
    preview.title = `${ref.table} / ${ref.row} · ${ref.field}`;
    preview.dataset.inlineImageId = ref.token;
    preview.dataset.inlineImageSrc = W.exportFullHref(ref.rel);
    preview.dataset.inlineImageName = ref.token;
    preview.appendChild(image(ref, true));
    return preview;
  }
  function decorateField(refs, line, field) {
    // Place one authored icon beside the exact referenced record, rather than
    // rendering every asset variant as an independent gallery entry.
    const matching = field.ref && field.resolved === true
      ? refs.filter((ref) => ref.table === field.ref.table && ref.row === String(field.ref.row))
      : refs.filter((ref) => ref.token === String(field.value || '') && ref.field === field.field);
    const ref = matching.find((ref) => /(?:^|\.)iconId$/.test(ref.field)) || matching[0];
    if (!ref) return;
    const value = line.querySelector('.reference-field-value');
    value?.prepend(imagePreview(ref));
    line.classList.add('activities-illustrated-field');
  }

  const relatedHeadings = () => ({
    CheckInRewardTable: text('Daily check-in rewards', '每日签到奖励'),
    ActivityConditionalMultiStageTable: text('Stage rewards', '阶段奖励'),
    ActivityConditionalMultiStageTaskConfigTable: text('Task rewards', '任务奖励'),
    ActivityConditionalMultiStageMilestoneTable: text('Milestone rewards', '里程碑奖励'),
    ActivityWeeklyTaskMileStoneTable: text('Weekly milestone rewards', '每周里程碑奖励'),
  });
  const RELATED_TABLES = Object.keys(relatedHeadings());

  function activityText(value) {
    return String(value || '').replace(/<size\s*=[^>]*>|<\/size>/gi, '')
      .replace(/<color\s*=[^>]*>/gi, '<b>').replace(/<\/color>/gi, '</b>');
  }

  function compactActivityRow(row, omitDescription = false) {
    if (!row.guide) return row;
    const hidden = new Set(['activityId', 'timeId', 'unlockTimeId', 'displayTimeId', 'jumpId',
      'rewardId', 'stageId', 'milestoneId', 'sortId', 'displayFactor', 'timeOffset']);
    return { ...row, guide: { ...row.guide, sections: row.guide.sections
      .map((group) => ({
      ...group, title: activityText(group.title), fields: (group.fields || []).filter((field) => {
        const key = field.field.split('.').pop();
        if (omitDescription && group.label === 'Activity configuration'
          && !['introMissionQuestId', 'endMissionQuestId'].includes(key)) return false;
        if (field.technical || hidden.has(key) || (omitDescription && field.field === 'desc')) return false;
        if (field.ref && !field.name && field.quantity === undefined && String(field.value) === String(field.ref.row)
          && field.ref.table !== 'MissionRuntimeAsset') return false;
        if (/%.?s|\{\d+\}/.test(String(field.value))) return false;
        return true;
      }).map((field) => ({ ...field, value: activityText(field.value) })),
    })).filter((group) => group.title || group.fields.length) } };
  }

  function referenceOptions(media, debug) {
    return { compact: !debug, renderRewardTag: (field) => rewardTag(field, media),
      decorateField: (line, field) => decorateField(media, line, field),
      resolveReference: (field) => field.ref?.table === 'MissionRuntimeAsset'
        ? W.storyLinks.resolve(state.story, field.ref.row) : null };
  }

  function renderSupplyStages(host, row, media) {
    const groups = new Map();
    for (const group of row.guide.sections) {
      if (!group.path?.startsWith('stageList.')) continue;
      const key = group.path.split('.').slice(0, 2).join('.');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(group);
    }
    const esc = W.escapeHtml;
    for (const sections of groups.values()) {
      const title = sections.find((group) => group.label === 'Activity stage')?.title
        || sections.find((group) => group.label === 'Supply stage text')?.title
        || text('Additional stage', '额外阶段');
      const card = document.createElement('article'); card.className = 'gameplay-trait-card';
      card.innerHTML = `<h4>${esc(title)}</h4>`;
      const order = { 'Supply stage text': 0, 'Stage submission': 1, 'Activity stage': 2 };
      const stage = { ...row, guide: { ...row.guide, sections: [...sections].sort((a, b) => (order[a.label] ?? 3) - (order[b.label] ?? 3)).map((group) => ({
        ...group, title: group.title === title ? '' : group.title,
        ...(group.label === 'Activity stage' ? { label: 'Stage rewards and mission', labelZh: '阶段奖励与任务' } : {}),
      })) } };
      W.referenceRows.render(card, stage, referenceOptions(media, false));
      host.append(card);
    }
  }

  function renderRelatedRewards(host, row, tableName) {
    if (tableName !== 'ActivityTable') return;
    for (const [stem, title] of Object.entries(relatedHeadings())) {
      const payload = state.related[stem];
      const raw = payload?.rawRows?.[row.id];
      const projected = payload?.rows?.find((entry) => String(entry.id) === String(row.id));
      if (!projected?.guide || !raw) continue;
      if (stem === 'CheckInRewardTable' && !(raw.stageList?.length && raw.stageList.every((day) => day.activityId === row.id))) continue;
      if (stem === 'ActivityConditionalMultiStageTable' && raw.activityId !== row.id) continue;
      const section = document.createElement('section'); section.className = 'gameplay-section activities-related-rewards';
      const isSupply = projected.guide.sections.some((group) => group.label === 'Supply stage text' || group.label === 'Stage submission');
      const heading = document.createElement('h3'); heading.className = 'gameplay-section-title'; heading.textContent = isSupply ? text('Supply stages', '供给阶段') : title;
      section.appendChild(heading);
      const linked = { ...projected, mediaKey: `${stem}/${row.id}`, raw: { ...raw, activityId: row.id } };
      const linkedRefs = mediaFor(linked);
      const debug = !!document.querySelector('#show-debug')?.checked;
      const displayed = debug ? linked : compactActivityRow(linked);
      if (!debug && isSupply) {
        renderSupplyStages(section, displayed, linkedRefs);
        host.append(section);
        continue;
      }
      if (!debug && stem === 'ActivityConditionalMultiStageTable') {
        const supplyStages = new Set(displayed.guide.sections.filter((group) => group.label === 'Supply stage text' || group.label === 'Stage submission').map((group) => group.path.split('.').slice(0, 2).join('.')));
        displayed.guide.sections = displayed.guide.sections.filter((group) => group.fields.some((field) => field.quantity !== undefined || field.ref?.table === 'MissionRuntimeAsset') || supplyStages.has(group.path.split('.').slice(0, 2).join('.')));
      }
      if (!debug && !displayed.guide?.sections.length) continue;
      W.referenceRows.render(section, displayed, referenceOptions(linkedRefs, debug));
      section.querySelectorAll('.reference-fields-title').forEach((heading) => heading.remove());
      host.appendChild(section);
    }
  }

  function renderAssets(host, row, stem) {
    const families = new Map();
    const pixels = (ref) => Math.max(0, Number(ref.width) || 0) * Math.max(0, Number(ref.height) || 0);
    for (const ref of sourcesForSummary(row, stem)) {
      if (!ref.rel) continue;
      const family = ref.token || ref.rel.split(/[\\/]/).pop().replace(/_p[0-9a-f]+(?=\.[^.]+$)/i, '');
      const previous = families.get(family);
      if (!previous || pixels(ref) > pixels(previous)
        || (pixels(ref) === pixels(previous) && ref.rel.localeCompare(previous.rel) < 0)) families.set(family, ref);
    }
    const images = [...families.values()];
    if (!images.length) return;
    const gallery = document.createElement('div');
    gallery.className = 'activities-assets';
    gallery.innerHTML = W.gameplay.assetGallery({ kind: 'activity', id: row.id, title: row.title }, {
      entries: { [`activity:${row.id}`]: { images, models: [] } },
    });
    host.appendChild(gallery);
  }

  function rewardSummary(row, stem) {
    const details = [];
    if (stem === 'ActivityTable') {
      for (const table of RELATED_TABLES) {
        const payload = state.related[table];
        const raw = payload?.rawRows?.[row.id];
        const linked = payload?.rows?.find((entry) => String(entry.id) === String(row.id));
        if (!raw || !linked?.guide) continue;
        if (table === 'CheckInRewardTable' && !(raw.stageList?.length && raw.stageList.every((day) => day.activityId === row.id))) continue;
        if (table === 'ActivityConditionalMultiStageTable' && raw.activityId !== row.id) continue;
        details.push({ row: linked, table });
      }
    }
    const quantified = (entry) => (entry.guide?.sections || []).some((group) => (group.fields || []).some((field) => field.ref?.table === 'ItemTable' && field.role !== 'submission' && W.gameplayDetail.knownQuantity(field.quantity)));
    const sources = details.filter((entry) => quantified(entry.row));
    const preview = !sources.length && stem === 'ActivityTable';
    if (!sources.length) sources.push({ row, table: stem });
    const totals = new Map();
    const seen = new Set();
    for (const source of sources) {
      for (const [index, group] of (source.row.guide?.sections || []).entries()) {
        for (const field of group.fields || []) {
          if (field.ref?.table !== 'ItemTable' || field.role === 'submission') continue;
          const grant = `${source.table}/${source.row.id}/${group.path || index}/${field.field}`;
          if (seen.has(grant)) continue;
          seen.add(grant);
          const key = String(field.ref.row);
          const total = totals.get(key);
          const quantity = W.gameplayDetail.knownQuantity(field.quantity) ? Number(field.quantity) : undefined;
          totals.set(key, total ? { ...total, quantity: total.quantity !== undefined && quantity !== undefined
            ? total.quantity + quantity : undefined } : { ...field, quantity });
        }
      }
    }
    return { fields: [...totals.values()], preview };
  }

  function renderRewardSummary(host, row, stem) {
    const summary = rewardSummary(row, stem);
    const section = document.createElement('section'); section.className = 'gameplay-section activities-reward-summary';
    const title = document.createElement('h3'); title.className = 'gameplay-section-title'; title.textContent = text('Reward summary', '奖励汇总'); section.appendChild(title);
    const note = document.createElement('p');
    note.textContent = !summary.fields.length ? text('No quantified rewards published.', '暂无已发布的明确奖励数量。')
      : summary.preview ? text('Activity reward preview; not a total of reward grants.', '活动配置的奖励预览，非逐项领取总量。')
        : text('Total of published fixed reward entries; requirements still apply.', '按已发布的固定奖励明细汇总，领取仍需满足各项条件。');
    section.appendChild(note);
    if (summary.fields.length) {
      const media = sourcesForSummary(row, stem);
      const tags = document.createElement('div'); tags.className = 'item-reward-tags';
      for (const field of summary.fields) {
        tags.appendChild(rewardTag(summary.preview ? { ...field, quantity: undefined } : field, media));
      }
      section.appendChild(tags);
    }
    host.appendChild(section);
  }
  function rewardTag(field, media) {
        const tag = document.createElement('a'); tag.className = 'gameplay-value-chip gameplay-item-chip gameplay-item-chip-link';
        tag.href = W.gameplayTabs.pageUrl('item', String(field.ref.row));
        tag.addEventListener('click', (event) => {
          if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
          event.preventDefault(); W.gameplayTabs.open('item', String(field.ref.row));
        });
        const refs = media.filter((ref) => ref.table === field.ref.table && ref.row === String(field.ref.row));
        const ref = refs.find((entry) => /(?:^|\.)iconId$/.test(entry.field)) || refs[0];
        if (ref) { const icon = document.createElement('span'); icon.className = 'gameplay-item-chip-icon'; icon.appendChild(image(ref)); tag.appendChild(icon); }
        const name = document.createElement('b'); name.textContent = field.name || field.value;
        tag.append(name);
        if (W.gameplayDetail.knownQuantity(field.quantity)) {
          const count = document.createElement('span'); count.textContent = `×${field.quantity}`;
          tag.append(count);
        }
        return tag;
  }
  function sourcesForSummary(row, stem) {
    return [...mediaFor(row, stem), ...RELATED_TABLES.flatMap((table) => state.media.rows[`${table}/${row.id}`] || [])];
  }

  function strings() {
    $('type-label').textContent = text('Type', '类型');
    $('q').placeholder = text('Search activity / ID / target / reward', '搜索活动 / ID / 目标 / 奖励');
    $('q').setAttribute('aria-label', $('q').placeholder);
    $('reset').textContent = text('Reset filters', '重置筛选');
    $('tag-label').textContent = text('Official categories', '官方分类');
    $('schedule-label').textContent = text('Schedule', '时间配置');
    $('sort-label').textContent = text('Sort', '排序');
    const labels = [['Opening time (newest first)', '开始时间（最新优先）'], ['Opening time (oldest first)', '开始时间（最早优先）'], ['Name', '名称'], ['Display order', '显示顺序']];
    [...$('sort').options].forEach((option, i) => { option.textContent = text(...labels[i]); });
    panel.sync();
    W.sorting.refresh();
  }

  function resetView() {
    state.rows = []; $('list').replaceChildren(); $('detail').replaceChildren();
    $('detail-header').hidden = true;
    $('count').textContent = text('Loading…', '加载中…');
  }

  function renderBattleLinks(host, row) {
    const slot = document.createElement('div');
    host.append(slot);
    const requestedLanguage = state.language;
    // Reuse the Gameplay-owned publication and its in-flight loader. Only exact
    // Authored activity references and published scene-map targets become links.
    void W.battleStages.load(false, { render: false }).then(() => {
      if (!slot.isConnected || state.language !== requestedLanguage) return;
      const stages = W.battleStages.activityStages(row.id);
      if (!stages.length) { slot.remove(); return; }
      const groups = new Map();
      for (const stage of stages) {
        const relation = stage.activities.find((activity) => activity.id === row.id)?.relation || 'activityDungeon';
        const group = ['completionReference', 'modeDestination'].includes(relation) ? relation : 'activityDungeon';
        if (!groups.has(group)) groups.set(group, []);
        groups.get(group).push(stage);
      }
      const labels = {
        activityDungeon: text('Activity stages', '活动关卡'),
        completionReference: text('Stages referenced by completion conditions', '完成条件关联关卡'),
        modeDestination: text('Season configuration stages', '赛季配置关卡'),
      };
      const stageLinks = [...groups].map(([group, entries]) => {
        const roles = ['scene', 'level'].filter((role) => entries.some((stage) => (stage.links?.maps || []).some((map) => map.role === role)));
        const mapLabel = (role) => role === 'scene' ? text('Combat map', '战斗地图') : text('Linked area map', '关联区域地图');
        const mapLink = (map) => {
          const url = new URL(location.href);
          const id = map.variant || map.id;
          url.search = ''; url.hash = 'map'; url.searchParams.set('map', id);
          return W.gameplayDetail.relatedLink(map.name || id, { href: url.href });
        };
        const rows = entries.map((stage) => `<tr><th scope="row">${W.gameplayDetail.relatedLink(stage.name, { kind: 'stage', id: stage.id })}</th>${roles.map((role) => {
          const maps = (stage.links?.maps || []).filter((map) => map.role === role);
          return `<td><div class="gameplay-heading-links">${maps.map(mapLink).join('') || '—'}</div></td>`;
        }).join('')}</tr>`).join('');
        return `<h4>${labels[group]}</h4><div class="activities-battle-scroll"><table class="activities-battle-links"><thead><tr><th scope="col">${text('Stage', '关卡')}</th>${roles.map((role) => `<th scope="col">${mapLabel(role)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
      }).join('');
      slot.innerHTML = W.gameplayDetail.section(text('Combat stages and maps', '战斗关卡与地图'),
        stageLinks);
      W.gameplayDetail.bindDatasetLinks(slot);
    });
  }

  function renderDetail() {
    const host = $('detail');
    host.replaceChildren();
    const row = state.rows.find((row) => String(row.id) === state.selected);
    $('detail-header').hidden = !row;
    host.classList.toggle('is-empty', !row);
    if (!row) { host.textContent = text('Select an activity', '选择一个活动'); return; }
    const stem = tableStem();
    const media = mediaFor(row, stem);
    const heading = $('detail-title');
    heading.textContent = row.title || row.id;
    const meta = $('detail-meta');
    meta.textContent = W.gameplayDetail.metadata([
      { label: text('Type', '类型'), value: text('Activity', '活动') },
      { label: 'ID', value: row.id },
      row.scheduleTag.length ? { label: text('Schedule', '时间配置'), value: row.scheduleTag.map((kind) => kind === 'permanent' ? text('Permanent activity', '常驻活动') : kind === 'limited' ? text('Limited-time activity', '限时活动') : kind).join(' / ') } : null,
      row.activityTags.length ? { label: text('Category', '分类'), value: row.activityTags.map((tag) => state.tags[tag]?.name?.text || tag).join(' / ') } : null,
    ]);
    const artwork = authoredImage(row, 'tabImg');
    W.gameplayDetail.mount($('detail-header'), $('detail-header-main'), heading, meta, artwork ? image(artwork).outerHTML : '');
    const id = document.createElement('p');
    id.textContent = row.id;
    const source = document.createElement('a');
    source.href = path(state.table.file);
    source.textContent = text('Published source JSON', '已发布的源 JSON');
    const desc = row.texts?.find((entry) => entry.path === '$.desc')?.text
      || row.guide?.sections?.flatMap((group) => group.fields || []).find((field) => field.field === 'desc')?.value;
    if (desc) {
      const description = document.createElement('div'); description.className = 'activities-description';
      description.innerHTML = window.renderDisplayedTextHtml(activityText(desc), '');
      host.appendChild(description);
    }
    const debug = !!document.querySelector('#show-debug')?.checked;
    if (debug) host.append(id, source);
    W.updateBadges.mount(host, 'activities', `${stem}/${row.id}`);
    renderTimes(host, row);
    renderBattleLinks(host, row);
    if (state.mediaError) { const note = document.createElement('p'); note.textContent = state.mediaError; host.appendChild(note); }
    const displayed = debug ? row : compactActivityRow(row, true);
    W.referenceRows.render(host, displayed, { ...referenceOptions(media, debug), hideConfigurationHeading: true });
    renderRewardSummary(host, row, stem);
    renderRelatedRewards(host, row, stem);
    renderAssets(host, row, stem);
    host.querySelectorAll('.reference-fields-title').forEach((title) => title.classList.add('gameplay-section-title'));
  }

  function sortedRows() {
    const query = $('q').value.trim().toLocaleLowerCase();
    const rows = facets.filter(state.rows).filter((row) => !query || row.search.includes(query));
    rows.sort((a, b) => {
      if ($('sort').value.startsWith('time')) {
        if (!a.start || !b.start) return a.start ? -1 : b.start ? 1 : String(a.id).localeCompare(String(b.id));
        const order = a.start.localeCompare(b.start);
        return ($('sort').value === 'time-desc' ? -order : order) || String(a.id).localeCompare(String(b.id));
      }
      if ($('sort').value === 'title') return W.sorting.comparator('activities-sort', (a, b) => String(a.title || a.id).localeCompare(String(b.title || b.id)))(a, b);
      return W.sorting.comparator('activities-sort', (a, b) => (Number(a.order) || 0) - (Number(b.order) || 0) || String(a.id).localeCompare(String(b.id)))(a, b);
    });
    return rows;
  }

  function locateSelected() {
    if (!state.selected) return null;
    renderList();
    W.continuousList.reveal($('list'), sortedRows().find((row) => String(row.id) === state.selected));
    return $('list').querySelector('.activities-entry.is-active');
  }

  function renderList() {
    const rows = sortedRows();
    W.locateCurrent?.sync($('locate-current'), Boolean(state.selected));
    $('count').textContent = `${rows.length} / ${state.rows.length}`;
    const host = $('list');
    W.continuousList.render(host, rows, (row) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'activities-entry';
      button.classList.toggle('is-active', String(row.id) === state.selected);
      button.setAttribute('aria-pressed', String(String(row.id) === state.selected));
      const title = document.createElement('strong');
      title.textContent = row.title || row.id;
      const heading = document.createElement('div'); heading.className = 'activities-entry-heading';
      heading.append(scheduleTags(row), title);
      const meta = document.createElement('span'); meta.className = 'activities-entry-meta'; meta.hidden = !document.querySelector('#show-debug')?.checked;
      meta.textContent = [row.bucket, row.id].filter(Boolean).join(' · ');
      const schedule = document.createElement('span'); schedule.className = 'activities-entry-schedule'; schedule.textContent = timeSummary(row);
      button.title = `${row.id} · ${timeSummary(row)}`;
      const category = document.createElement('span'); category.className = 'activities-entry-category';
      category.textContent = row.activityTags.map((id) => state.tags[id]?.name?.text || id).join(' · ');
      const body = document.createElement('div'); body.className = 'activities-entry-body'; body.append(heading, category, meta, schedule);
      const thumbnail = authoredImage(row, 'tabImg');
      if (thumbnail) { const img = image(thumbnail); img.className = 'activities-thumbnail'; img.addEventListener('load', () => button.classList.add('has-tab-image'), { once: true }); button.appendChild(img); }
      button.appendChild(body);
      button.addEventListener('click', () => {
        state.selected = String(row.id);
        writeUrl();
        renderList(); renderDetail();
      });
      return button;
    }, { estimateHeight: 140 });
  }

  function prepareTable(payload) {
    resetView();
    try {
      state.rows = (payload.rows || []).map((row) => enrich(row, payload.rawRows?.[row.id] || {}));
      state.rows.sort((a, b) => (Number(a.order) || 0) - (Number(b.order) || 0) || String(a.id).localeCompare(String(b.id)));
      facets.render(state.rows);
      const wanted = new URL(location.href).searchParams.get('activity');
      state.selected = state.rows.some((row) => String(row.id) === wanted) ? wanted : '';
      W.continuousList.reset($('list')); renderList(); renderDetail();
    } catch (error) {
      $('count').textContent = text('Unable to load activities: ', '无法加载活动：') + error.message;
    }
  }

  let activation = null;
  let activationLanguage = "";
  function activate(force = false) {
    const requested = language();
    if (!force && activation && activationLanguage === requested) return activation;
    activationLanguage = requested;
    const pending = activateData(force).finally(() => {
      if (activation === pending) activation = null;
    });
    activation = pending;
    return pending;
  }

  async function activateData(force = false) {
    if (document.body.dataset.activeView !== 'gameplay' || W.gameplayTabs?.kind !== 'activity') return;
    const params = new URL(location.href).searchParams;
    $('q').value = params.get('activityQ') || '';
    $('sort').value = ['time-desc', 'time-asc', 'title', 'default'].includes(params.get('activitySort')) ? params.get('activitySort') : 'time-desc';
    facets.reset({ silent: true });
    facets.fromParams(params, { silent: true });
    if (!force && state.language === language() && state.table) {
      const wanted = params.get('activity');
      state.selected = state.rows.some((row) => String(row.id) === wanted) ? wanted : '';
      facets.render(state.rows); renderList(); renderDetail();
      return;
    }
    state.language = language();
    state.table = null;
    const generation = ++state.generation;
    state.controller?.abort();
    state.controller = new AbortController();
    const signal = state.controller.signal;
    resetView();
    try {
      // Text owns the reference index; reuse its single fetch.
      await W.referenceRows.prepare(state.language);
      if (generation !== state.generation) return;
      const indexTables = W.referenceRows.tables();
      const find = (stem) => indexTables.find((table) => table.table === `${stem}.json`);
      const load = (stem) => find(stem) ? W.referenceRows.load(find(stem).file, signal) : Promise.resolve({});
      const [times, tags, activities, media, related, story] = await Promise.all([load('TimeRangeTable'), load('ActivityTagTable'), load('ActivityTable'),
        fetch('data/assets/activity_media.json', { signal }).then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
          .catch((error) => { if (error.name === 'AbortError') throw error; return { rows: {}, error: error.message }; }), Promise.all(RELATED_TABLES.map(load)),
        W.storyLinks.load(state.language).catch(() => null), W.updateBadges.load('activities')]);
      if (generation !== state.generation) return;
      state.times = times.rawRows || {}; state.tags = tags.rawRows || {}; state.activities = activities.rawRows || {}; state.media = media;
      facets.set('tag', [...new Set([...facets.active('tag')].map(categoryKey))], { silent: true });
      state.related = Object.fromEntries(RELATED_TABLES.map((stem, index) => [stem, related[index]]));
      state.story = story;
      state.mediaError = media.error ? text('Activity images unavailable. Rebuild Assets: ', '活动图片不可用，请重建资源：') + media.error : '';
      state.table = find('ActivityTable');
      if (!state.table) { $('count').textContent = text('No published activity table. Rebuild Story/Text data.', '没有已发布的活动表，请重建剧情/文本数据。'); return; }
      prepareTable(activities);
    } catch (error) {
      if (generation !== state.generation || error.name === 'AbortError') return;
      state.table = null;
      $('count').textContent = text('Unable to load activities: ', '无法加载活动：') + error.message;
    }
  }
  $('q').value = new URL(location.href).searchParams.get('activityQ') || '';
  const savedSort = new URL(location.href).searchParams.get('activitySort');
  if ([...$('sort').options].some((option) => option.value === savedSort)) $('sort').value = savedSort;
  $('q').addEventListener('input', () => { W.continuousList.reset($('list')); renderList(); writeUrl(); });
  $('sort').addEventListener('change', () => { W.continuousList.reset($('list')); renderList(); writeUrl(); });
  $('reset').addEventListener('click', () => { $('q').value = ''; $('sort').value = 'time-desc'; facets.reset({ silent: true }); facets.render(state.rows); W.continuousList.reset($('list')); renderList(); writeUrl(); });
  document.querySelector('#show-debug')?.addEventListener('change', () => { renderList(); renderDetail(); });
  window.addEventListener('webui:ui-locale-changed', () => { strings(); facets.render(state.rows); renderList(); renderDetail(); });
  W.locateCurrent?.bind($('locate-current'), locateSelected, () => $('left'));
  W.gameplayActivities = { load: activate, loadCount, count: () => countLanguage === language() ? total : null };
  strings();
})();
