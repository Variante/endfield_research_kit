// Activities browses all published ActivityTable rows and every Activity-prefixed
// supporting table. Guides are shared with Text; availability is not inferred.
(() => {
  const W = window.WebUI;
  const $ = (id) => document.getElementById(`activities-${id}`);
  const state = { language: '', tables: [], rows: [], selected: '', generation: 0, times: {}, tags: {}, activities: {}, media: { rows: {} }, mediaError: '', related: {} };
  const language = () => String(document.querySelector('#language')?.value || 'CN').toUpperCase();
  const en = () => window.WEBUI_UI_LOCALE === 'en';
  const text = (english, chinese) => en() ? english : chinese;
  const path = (file) => `data/lang/${encodeURIComponent(state.language)}/reference/${file}`;
  const pager = W.pagination.createPager({ container: '#activities-pager', storageKey: 'activities_page_size', defaultPageSize: 100, onChange: renderList });

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
  ], onChange: () => { pager.reset(); renderList(); writeUrl(); } });
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
    const url = new URL(location.href);
    url.searchParams.set('activityTable', $('table').value);
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
  function enrich(row, raw) {
    const parent = raw.activityId && state.activities[raw.activityId];
    const activity = parent || raw;
    const ranges = state.times[activity.timeId]?.timeRangeList || [];
    const opens = ranges.map((range) => timeKey(range.openTime)).filter(Boolean).sort();
    const enriched = { ...row, raw, timeId: activity.timeId, ranges, start: opens[0] || '',
      activityTags: activity.tagIds || [], scheduleTag: ranges.length ? (ranges.every((range) => !range.closeTime) ? ['permanent'] : ranges.every((range) => !!range.closeTime) ? ['limited'] : ['permanent', 'limited']) : ['unknown'] };
    // Search the same serialized row as before, built once instead of per keystroke.
    enriched.search = JSON.stringify(enriched).toLocaleLowerCase();
    return enriched;
  }
  // The list card passes its own fallbacks: no start text and "Permanent" for an open end.
  function rangeText(range, { start = text('Unspecified start', '未指定开始时间'), end = text('No configured end', '未配置结束时间') } = {}) {
    return `${range.openTime || start} → ${range.closeTime || end}`;
  }
  function timeSummary(row) {
    const distinct = [...new Set(row.ranges.map((range) => rangeText(range)))];
    return distinct.join(' / ') || text('Time unspecified', '未指定时间');
  }
  const tableStem = () => $('table').selectedOptions[0]?.textContent || '';
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
    const block = document.createElement('section'); block.className = 'activities-times';
    const title = document.createElement('strong'); title.textContent = text('Configured schedule', '配置时间'); block.appendChild(title);
    if (!row.ranges.length) { const note = document.createElement('span'); note.textContent = timeSummary(row); block.appendChild(note); }
    row.ranges.forEach((range, index) => {
      const line = document.createElement('div');
      line.textContent = `${text('Range', '时间段')} ${index + 1}: ${rangeText(range)}`;
      block.appendChild(line);
    });
    const note = document.createElement('small');
    note.textContent = text('Times are shown as stored; no time zone or regional variant is inferred.', '时间按原始配置显示，不推断时区或各时间段的地区归属。'); block.appendChild(note); host.appendChild(block);
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

  function renderRelatedRewards(host, row, tableName) {
    if (tableName !== 'ActivityTable') return;
    for (const [stem, title] of Object.entries(relatedHeadings())) {
      const payload = state.related[stem];
      const raw = payload?.rawRows?.[row.id];
      const projected = payload?.rows?.find((entry) => String(entry.id) === String(row.id));
      if (!projected?.guide || !raw) continue;
      if (stem === 'CheckInRewardTable' && !(raw.stageList?.length && raw.stageList.every((day) => day.activityId === row.id))) continue;
      if (stem === 'ActivityConditionalMultiStageTable' && raw.activityId !== row.id) continue;
      const section = document.createElement('section'); section.className = 'activities-related-rewards';
      const heading = document.createElement('h3'); heading.textContent = title;
      section.appendChild(heading);
      const linked = { ...projected, mediaKey: `${stem}/${row.id}`, raw: { ...raw, activityId: row.id } };
      const linkedRefs = mediaFor(linked);
      W.referenceRows.render(section, linked, { decorateField: (line, field) => decorateField(linkedRefs, line, field) });
      host.appendChild(section);
    }
  }

  function renderArtwork(host, row, media) {
    const refs = ['tabImg', 'bgImg'].map((field) => ({ field, ref: authoredImage(row, field, media) })).filter((entry) => entry.ref);
    if (!refs.length) return;
    const section = document.createElement('section'); section.className = 'activities-artwork';
    const heading = document.createElement('h3'); heading.textContent = text('Activity artwork', '活动图片素材');
    section.appendChild(heading);
    for (const { field, ref } of refs) {
      const figure = document.createElement('figure');
      const caption = document.createElement('figcaption'); caption.textContent = `${field} · ${ref.token}`;
      figure.append(imagePreview(ref), caption); section.appendChild(figure);
    }
    host.appendChild(section);
  }

  function strings() {
    $('title').textContent = text('Activities', '活动');
    $('table-label').textContent = text('Dataset', '数据集');
    $('type-label').textContent = text('Type', '类型');
    $('q').placeholder = text('Search activity / ID / target / reward', '搜索活动 / ID / 目标 / 奖励');
    $('q').setAttribute('aria-label', $('q').placeholder);
    $('reset').textContent = text('Reset filters', '重置筛选');
    $('boundary').textContent = text('All exported activity configurations, including prerequisites, targets and rewards. Current availability and player progress are not evaluated.', '展示所有已导出的活动配置，包括前置条件、目标和奖励；不判断当前开放状态或玩家进度。');
    $('tag-label').textContent = text('Official categories', '官方分类');
    $('schedule-label').textContent = text('Schedule', '时间配置');
    $('sort-label').textContent = text('Sort', '排序');
    const labels = [['Opening time (newest first)', '开始时间（最新优先）'], ['Opening time (oldest first)', '开始时间（最早优先）'], ['Name', '名称'], ['Display order', '显示顺序']];
    [...$('sort').options].forEach((option, i) => { option.textContent = text(...labels[i]); });
    panel.sync();
    W.sorting.refresh();
  }

  function clearBackground() {
    $('right').style.removeProperty('--activities-background');
    $('right').classList.remove('has-activity-background');
  }
  function resetView() {
    state.rows = []; $('list').replaceChildren(); $('detail').replaceChildren();
    clearBackground();
    $('count').textContent = text('Loading…', '加载中…');
  }

  function renderDetail() {
    const host = $('detail');
    host.replaceChildren();
    clearBackground();
    const row = state.rows.find((row) => String(row.id) === state.selected);
    if (!row) { host.textContent = text('Select an activity', '选择一个活动'); return; }
    const stem = tableStem();
    const media = mediaFor(row, stem);
    const background = authoredImage(row, 'bgImg', media);
    if (background) {
      $('right').style.setProperty('--activities-background', `url(${JSON.stringify(W.exportFullHref(background.rel))})`);
      $('right').classList.add('has-activity-background');
    }
    const heading = document.createElement('h2');
    heading.textContent = row.title || row.id;
    const id = document.createElement('p');
    id.textContent = row.id;
    const source = document.createElement('a');
    source.href = path($('table').value);
    source.textContent = text('Published source JSON', '已发布的源 JSON');
    const header = document.createElement('header');
    header.appendChild(heading);
    host.append(header, id, source);
    W.updateBadges.mount(host, 'activities', `${stem}/${row.id}`);
    renderTimes(host, row);
    const tags = document.createElement('div'); tags.className = 'activities-tags';
    for (const tag of row.activityTags) { const chip = document.createElement('span'); chip.className = 'chip'; chip.textContent = state.tags[tag]?.name?.text || tag; tags.appendChild(chip); }
    host.appendChild(tags);
    if (state.mediaError) { const note = document.createElement('p'); note.textContent = state.mediaError; host.appendChild(note); }
    W.referenceRows.render(host, row, { decorateField: (line, field) => decorateField(media, line, field) });
    renderRelatedRewards(host, row, stem);
    renderArtwork(host, row, media);
  }

  function renderList() {
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
    pager.setTotal(rows.length);
    $('count').textContent = `${rows.length} / ${state.rows.length}`;
    const host = $('list');
    host.replaceChildren();
    for (const row of pager.slice(rows)) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'activities-entry';
      button.classList.toggle('is-active', String(row.id) === state.selected);
      button.setAttribute('aria-pressed', String(String(row.id) === state.selected));
      const title = document.createElement('strong');
      title.textContent = row.title || row.id;
      const meta = document.createElement('span'); meta.className = 'activities-entry-meta'; meta.hidden = !document.querySelector('#show-debug')?.checked;
      meta.textContent = [row.bucket, row.id].filter(Boolean).join(' · ');
      const schedule = document.createElement('span'); schedule.className = 'activities-entry-schedule'; schedule.textContent = row.ranges.length ? rangeText(row.ranges[0], { start: '', end: text('Permanent', '常驻') }) : text('Time unspecified', '未指定时间');
      button.title = `${row.id} · ${timeSummary(row)}`;
      const category = document.createElement('span'); category.className = 'activities-entry-category';
      category.textContent = row.activityTags.map((id) => state.tags[id]?.name?.text || id).join(' · ');
      const body = document.createElement('div'); body.className = 'activities-entry-body'; body.append(title, category, meta, schedule);
      const thumbnail = authoredImage(row, 'tabImg');
      if (thumbnail) { const img = image(thumbnail); img.className = 'activities-thumbnail'; img.addEventListener('load', () => button.classList.add('has-tab-image'), { once: true }); button.appendChild(img); }
      button.appendChild(body);
      button.addEventListener('click', () => {
        state.selected = String(row.id);
        writeUrl();
        renderList(); renderDetail();
      });
      host.appendChild(button);
    }
    if (!rows.length) host.textContent = text('No matching activities', '没有匹配的活动');
  }

  async function loadTable() {
    const generation = ++state.generation;
    state.controller?.abort();
    state.controller = new AbortController();
    const signal = state.controller.signal;
    resetView();
    try {
      const payload = await W.referenceRows.load($('table').value, signal);
      if (generation !== state.generation) return;
      state.rows = (payload.rows || []).map((row) => enrich(row, payload.rawRows?.[row.id] || {}));
      state.rows.sort((a, b) => (Number(a.order) || 0) - (Number(b.order) || 0) || String(a.id).localeCompare(String(b.id)));
      facets.render(state.rows);
      const wanted = new URL(location.href).searchParams.get('activity');
      state.selected = state.rows.some((row) => String(row.id) === wanted) ? wanted : '';
      pager.reset(); renderList(); renderDetail();
    } catch (error) {
      if (generation !== state.generation || error.name === 'AbortError') return;
      $('count').textContent = text('Unable to load activities: ', '无法加载活动：') + error.message;
    }
  }

  async function activate(force = false) {
    if (document.body.dataset.activeView !== 'activities') return;
    if (!force && state.language === language() && state.tables.length) return;
    state.language = language();
    state.tables = [];
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
      const [times, tags, activities, media, related] = await Promise.all([load('TimeRangeTable'), load('ActivityTagTable'), load('ActivityTable'),
        fetch('data/assets/activity_media.json', { signal }).then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
          .catch((error) => { if (error.name === 'AbortError') throw error; return { rows: {}, error: error.message }; }), Promise.all(RELATED_TABLES.map(load)),
        W.updateBadges.load('activities')]);
      if (generation !== state.generation) return;
      state.times = times.rawRows || {}; state.tags = tags.rawRows || {}; state.activities = activities.rawRows || {}; state.media = media;
      state.related = Object.fromEntries(RELATED_TABLES.map((stem, index) => [stem, related[index]]));
      state.mediaError = media.error ? text('Activity images unavailable. Rebuild Assets: ', '活动图片不可用，请重建资源：') + media.error : '';
      state.tables = indexTables.filter((table) => (/^(?:Activity.*Table|CheckInRewardTable)\.json$/.test(table.table)));
      state.tables.sort((a, b) => (a.table === 'ActivityTable.json' ? -1 : b.table === 'ActivityTable.json' ? 1 : a.table.localeCompare(b.table)));
      $('table').replaceChildren(...state.tables.map((table) => new Option(table.table.replace(/\.json$/, ''), table.file)));
      const wanted = new URL(location.href).searchParams.get('activityTable');
      if (state.tables.some((table) => table.file === wanted)) $('table').value = wanted;
      if (!state.tables.length) { $('count').textContent = text('No published activity tables. Rebuild Story/Text data.', '没有已发布的活动表，请重建剧情/文本数据。'); return; }
      await loadTable();
    } catch (error) {
      if (generation !== state.generation || error.name === 'AbortError') return;
      state.tables = [];
      $('count').textContent = text('Unable to load activities: ', '无法加载活动：') + error.message;
    }
  }
  $('q').value = new URL(location.href).searchParams.get('activityQ') || '';
  const savedSort = new URL(location.href).searchParams.get('activitySort');
  if ([...$('sort').options].some((option) => option.value === savedSort)) $('sort').value = savedSort;
  $('q').addEventListener('input', () => { pager.reset(); renderList(); writeUrl(); });
  $('sort').addEventListener('change', () => { pager.reset(); renderList(); writeUrl(); });
  $('table').addEventListener('change', () => { $('q').value = ''; state.selected = ''; facets.reset({ silent: true }); writeUrl(); loadTable(); });
  $('reset').addEventListener('click', () => { $('q').value = ''; $('sort').value = 'time-desc'; facets.reset({ silent: true }); facets.render(state.rows); pager.reset(); renderList(); writeUrl(); });
  document.querySelector('#show-debug')?.addEventListener('change', renderList);
  window.addEventListener('webui:view-changed', () => activate());
  window.addEventListener('webui:language-changed', () => { state.language = ''; activate(true); });
  window.addEventListener('webui:ui-locale-changed', () => { strings(); facets.render(state.rows); renderList(); renderDetail(); });
  strings(); activate();
})();
