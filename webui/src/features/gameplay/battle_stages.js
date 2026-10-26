// Authored combat stages: exact series, raid pairs, enemy levels and fixed
// rewards, conditional Spawner schedules and literal Buff references.
// Schema 3 keeps Spawner configurations once in ``spawners`` (shared scenes
// reuse them) and entries reference them through ``battle.spawnerIds``.
(() => {
  const W = window.WebUI;
  const $ = (id) => document.getElementById(`battle-${id}`);
  const esc = W.escapeHtml;
  const text = (en, zh) => window.WEBUI_UI_LOCALE === 'en' ? en : zh;
  const rich = (value) => window.renderDisplayedTextHtml ? window.renderDisplayedTextHtml(value, '') : esc(value);
  const debug = () => document.body.classList.contains('show-debug');
  const state = { language: '', entries: [], spawners: {}, enemies: {}, buffs: {}, audits: [], selected: '', generation: 0, loading: null, preview: false, modeUnavailable: false };
  const language = () => String(document.querySelector('#language')?.value || 'CN').toUpperCase();
  const active = () => document.body.dataset.activeView === 'gameplay' && W.gameplayTabs?.kind === 'stage';
  const categoryLabel = (row) => ({
    dungeon_bossrush: text('Boss challenges', '危境挑战'), dungeon_resource: text('Resource stages', '资源关卡'),
    dungeon_chartrial: text('Character trials', '角色试用'), dungeon_chartutorial: text('Combat tutorials', '战术教学'),
    dungeon_train: text('Combat training', '战术训练'), dungeon_worldlevel: text('World level challenges', '世界等级挑战'),
    dungeon_weeklyraid: text('Weekly challenges', '每周挑战'),
  })[row.category] || row.categoryName;
  const mode = (value) => ({ normal: text('Normal', '普通模式'), raid: text('Hard', '苦难模式'), unspecified: text('Mode unspecified', '模式未关联') })[value];
  const SORTS = ['default', 'name', 'level-desc', 'level-asc'];
  const FACETS = ['category', 'mode', 'level'];
  const groups = W.listGroups.create();
  let facets;

  const number = (value) => typeof value === 'number' ? Number(value.toFixed(4)).toLocaleString() : '?';
  const seconds = (value) => `${number(value)}${text('s', '秒')}`;
  const chip = (value, cls = '') => `<span class="gameplay-value-chip${cls ? ` ${cls}` : ''}">${esc(value)}</span>`;

  function strings() {
    $('q').placeholder = text('Search stage / series / enemy / reward', '搜索关卡／系列／敌人／奖励');
    $('q').setAttribute('aria-label', $('q').placeholder);
    $('reset').textContent = text('Reset filters', '重置筛选');
    $('retry').textContent = text('Retry', '重试');
    $('basic-label').textContent = text('Basic filters', '基础筛选');
    $('category-label').textContent = text('Gameplay', '玩法');
    $('mode-label').textContent = text('Mode', '模式');
    $('level-label').textContent = text('Recommended level', '推荐等级');
    $('sort-label').textContent = text('Sort', '排序');
    const options = [text('Default', '默认顺序'), text('Name', '名称'), text('Level (high to low)', '推荐等级从高到低'), text('Level (low to high)', '推荐等级从低到高')];
    [...$('sort').options].forEach((option, index) => { option.textContent = options[index]; });
    $('boundary').textContent = (state.preview ? text('Preview from the last published data. ', '使用上次已发布数据的预览。') : '')
      + (state.modeUnavailable ? text(' Normal/hard mode mappings are unavailable.', ' 普通／苦难模式配对表尚未发布。') : '');
    $('boundary').hidden = !$('boundary').textContent;
  }

  function restore() {
    const params = new URL(location.href).searchParams;
    $('q').value = params.get('battleQ') || '';
    $('sort').value = SORTS.includes(params.get('battleSort')) ? params.get('battleSort') : 'default';
    facets.fromParams(params, { silent: true });
    const wanted = params.get('battleStage');
    state.selected = state.entries.some((row) => row.id === wanted) ? wanted : '';
    // Start with the first authored stage, without selecting a filtered-out row.
    if (!state.selected && !wanted) state.selected = filtered()[0]?.id || '';
  }

  function writeUrl() {
    if (!active()) return;
    const url = new URL(location.href);
    for (const [key, value] of [['battleStage', state.selected], ['battleQ', $('q').value], ['battleSort', $('sort').value === 'default' ? '' : $('sort').value]]) {
      if (value) url.searchParams.set(key, value); else url.searchParams.delete(key);
    }
    facets.toParams(url.searchParams);
    history.replaceState(history.state, '', url);
  }

  function filtered() {
    const tokens = W.parseQuery($('q').value);
    const rows = facets.filter(state.entries).filter((row) => W.queryMatches(row.search, tokens));
    const sort = $('sort').value;
    const positions = new Map(state.entries.map((row, index) => [row, index]));
    return rows.sort(W.sorting.comparator('battle-sort', (a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name, state.language === 'CN' ? 'zh-CN' : undefined);
      if (sort.startsWith('level-')) return (sort === 'level-desc' ? -1 : 1) * ((a.recommendLevel || 0) - (b.recommendLevel || 0));
      return positions.get(a) - positions.get(b);
    }));
  }

  function rowMeta(row) {
    const level = row.recommendLevel > 0 ? text(`Recommended Lv.${row.recommendLevel}`, `推荐等级 ${row.recommendLevel}`) : '';
    const description = row.mode !== 'unspecified' ? mode(row.mode) : row.texts.dungeonLevelDesc !== row.name ? row.texts.dungeonLevelDesc : '';
    return [description, level].filter(Boolean).join(' · ');
  }

  function renderList() {
    if (!$('list')) return;
    const rows = filtered();
    $('stats').textContent = text(`${state.entries.length} stages`, `${state.entries.length} 个关卡`);
    $('list-meta').textContent = text(`${rows.length} shown`, `显示 ${rows.length} 个`);
    groups.render($('list'), rows, {
      keyOf: (row) => `${row.category}/${row.seriesId}`,
      title: (row) => [...new Set([categoryLabel(row), row.seriesName || text('Ungrouped', '未分组')])].join(' · '),
      renderRow: (row) => {
      const art = row.art?.[0];
      return `<button type="button" class="gameplay-row${row.id === state.selected ? ' is-selected' : ''}" data-stage="${esc(row.id)}" aria-pressed="${row.id === state.selected}">${art ? `<span class="gameplay-row-thumbnail battle-row-art"><img src="${esc(W.exportFullHref(art.rel))}" alt="" loading="lazy"></span>` : ''}<span class="gameplay-row-text"><span class="gameplay-row-name">${esc(row.name)}</span><span class="gameplay-row-meta">${esc(rowMeta(row))}</span></span></button>`;
      }, estimateHeight: 90,
    });
    W.locateCurrent?.sync($('locate-current'), filtered().some((row) => row.id === state.selected));
  }

  function locateSelected() {
    const index = filtered().findIndex((row) => row.id === state.selected);
    if (index < 0) return null;
    return groups.locate($('list'), filtered()[index]);
  }

  function select(id) {
    if (!state.entries.some((row) => row.id === id)) return;
    state.selected = id;
    renderList(); renderDetail(); writeUrl();
  }

  function section(title, body, id = '') {
    return W.gameplayDetail.section(title, body, { className: "battle-section", id: id ? `battle-section-${id}` : "", anchorLabel: id });
  }
  function entityLink(kind, id, name, resolved = true) {
    return resolved ? `<a class="gameplay-value-chip" href="${esc(W.gameplayTabs.pageUrl(kind, id))}">${esc(name)}</a>` : chip(`${name} · ${text('Unresolved', '未关联')}`);
  }
  function artwork(art, label, className = '') {
    if (!art?.rel) return '';
    const src = W.exportFullHref(art.rel);
    return `<button type="button" class="battle-art gameplay-image-preview inline-image-tag has-preview ${className}" aria-label="${esc(text('Preview ', '预览') + label)}" data-inline-image-id="${esc(art.rel)}" data-inline-image-name="${esc(label)}" data-inline-image-src="${esc(src)}"><img src="${esc(src)}" alt="${esc(label)}" loading="lazy"></button>`;
  }

  // Buff references: the applier's blackboard values feed the recovered Buff
  // fields, so a ``ratio`` of -0.5 renders as "-50%" on the modifier it keys.
  const blackboardValue = (bb) => bb.useString ? bb.valueString : bb.valueFloat;
  const buffKey = (buff) => `${buff.id}|${(buff.blackboards || []).map((bb) => `${bb.key}=${blackboardValue(bb)}`).join(',')}`;
  function buffFacts(buff) {
    const record = state.buffs[buff.id];
    const values = new Map((buff.blackboards || []).map((bb) => [bb.key, blackboardValue(bb)]));
    const rows = record && record.evidenceStatus !== 'unresolved' && record.idStringVerified ? W.gameplay.buffRows(record, values) : [];
    return { rows, parameters: (buff.blackboards || []).map((bb) => `${bb.key || '?'} = ${bb.useString ? bb.valueString : number(bb.valueFloat)}`).join(' · ') };
  }
  function buffReference(buff, origin = '') {
    const { rows, parameters } = buffFacts(buff);
    const summary = rows.length ? W.gameplayMechanics.markup(rows) : '';
    return `<div class="battle-buff-reference"><div class="battle-buff-head"><code>${esc(buff.id)}</code>${origin ? `<span class="gameplay-caption">${esc(origin)}</span>` : ''}</div>${summary || `<p class="gameplay-caption">${text('Effect semantics unresolved', '具体效果尚未解析')}</p>`}${parameters ? `<p class="gameplay-caption">${esc(parameters)}</p>` : ''}</div>`;
  }
  // A tag names the first recovered effect; the full reference opens in the
  // shared popup on hover, focus or click.
  function buffTag(buff, origin = '') {
    const effect = buffFacts(buff).rows.find((row) => row.kind !== 'meta' && !row.muted);
    const label = effect ? `${effect.label} ${effect.body}` : buff.id;
    popupBuffs.set(buffKey(buff), { buff, origin });
    return `<button type="button" class="battle-buff-tag${effect ? '' : ' is-unresolved'}" data-battle-buff="${esc(buffKey(buff))}">${esc(label)}</button>`;
  }
  function buffTags(buffs, origin = '') {
    const unique = new Map();
    for (const buff of buffs) if (!unique.has(buffKey(buff))) unique.set(buffKey(buff), buff);
    return [...unique.values()].map((buff) => buffTag(buff, origin)).join('');
  }
  const popupBuffs = new Map();
  function showBuffPopup(tag) {
    const entry = popupBuffs.get(tag.dataset.battleBuff);
    const pop = $('buff-pop');
    if (!entry || !pop) return;
    pop.innerHTML = buffReference(entry.buff, entry.origin);
    pop.hidden = false;
    const box = tag.getBoundingClientRect(), width = pop.offsetWidth, height = pop.offsetHeight;
    pop.style.left = `${Math.max(8, Math.min(box.left, innerWidth - width - 8))}px`;
    pop.style.top = `${box.bottom + 6 + height > innerHeight ? Math.max(8, box.top - height - 6) : box.bottom + 6}px`;
  }
  function hideBuffPopup() { const pop = $('buff-pop'); if (pop) pop.hidden = true; }

  function enemyName(id, fallback) {
    const detail = state.enemies[id];
    return { detail, name: detail?.name || fallback || id };
  }

  function enemyChip(id, name, detail, resolved, withIcon = true) {
    const art = withIcon ? detail?.art?.[0] : null;
    const icon = art?.rel ? `<span class="gameplay-item-chip-icon battle-enemy-icon"><img src="${esc(W.exportFullHref(art.rel))}" alt="" loading="lazy"></span>` : '';
    const body = `${icon}<b>${esc(name)}</b>`;
    if (!id || !(detail || resolved)) return `<span class="gameplay-value-chip gameplay-item-chip" title="${esc(text('Unresolved', '未关联'))}">${body}</span>`;
    return `<a class="gameplay-value-chip gameplay-item-chip gameplay-item-chip-link" href="${esc(W.gameplayTabs.pageUrl('enemy', id))}">${body}</a>`;
  }

  // Variant cards title the enemy with plain text (linked when resolved),
  // not a chip; the artwork beside it already identifies the enemy.
  function enemyTitle(id, name, detail, resolved) {
    if (!id || !(detail || resolved)) return `<h4 class="battle-enemy-name" title="${esc(text('Unresolved', '未关联'))}">${esc(name)}</h4>`;
    return `<h4 class="battle-enemy-name"><a href="${esc(W.gameplayTabs.pageUrl('enemy', id))}">${esc(name)}</a></h4>`;
  }
  function enemyCard(enemy) {
    const { detail, name } = enemyName(enemy.id, enemy.name);
    const modifiers = (detail?.modifiers || []).map((m) => chip(`${W.gameplay.statLabel({ ...m, type: m.attrType })} ${m.modifierTypeName === 'Multiplier' ? `${m.value >= 0 ? '+' : ''}${number(m.value * 100)}%` : `${m.modifierTypeName || m.modifierType} ${number(m.value)}`}`)).join('');
    const facts = [detail?.type, enemy.level == null ? '' : `Lv.${enemy.level}`].filter(Boolean);
    const born = detail?.bornBuffs || [];
    return `<article class="battle-enemy-card gameplay-skill-block"><div class="battle-enemy-head">${artwork(detail?.art?.[0], name, 'battle-enemy-art')}<div>${enemyTitle(enemy.id, name, detail, enemy.resolved)}<p class="gameplay-caption">${esc(facts.join(' · '))}</p>${debug() ? `<code class="battle-variant-id">${esc(enemy.id)}</code>` : ''}</div></div>${modifiers ? `<div class="battle-tags">${modifiers}</div>` : ''}${born.length ? `<div class="battle-buff-tags"><span class="gameplay-caption">${text('Variant Buffs', '自带 Buff')}</span>${buffTags(born.map((id) => ({ id })), text('Variant Buff', '变种自带'))}</div>` : ''}</article>`;
  }

  // Timing: every level stores its own offset (wave, group, spawn action).
  // Offsets are shown as stored; equal offsets do not establish an order.
  function spawnTiming(spawn) {
    const parts = [];
    if (spawn.timestamp != null) parts.push(`+${seconds(spawn.timestamp)}`);
    if (spawn.interval > 0) parts.push(text(`every ${seconds(spawn.interval)}`, `间隔 ${seconds(spawn.interval)}`));
    if (spawn.preWarnTime > 0) parts.push(text(`warning ${seconds(spawn.preWarnTime)}`, `预警 ${seconds(spawn.preWarnTime)}`));
    return parts.join(' · ');
  }

  // Hints say what the stored field holds; the runtime transition each one
  // drives depends on an unrecovered mode enum, so none is presented as proven.
  const conditionHints = () => ({
    repeatable: text('Stored repeat flag on the wave. Seen only on single-group waves; how often it repeats is not stored here.', '波次上的重复标记，仅见于单生成组波次；重复次数与条件未在此处存储。'),
    hidden: text('Stored hidden flag; its in-game effect is unconfirmed.', '存储的隐藏标记；游戏内效果未确认。'),
    killCount: text('Stored kill count paired with the transition mode. Usually below the configured enemy count, so it reads like "advance after N kills"; unconfirmed.', '与切换模式配对的击杀数。通常小于配置敌人数，看起来像“击杀 N 名后推进”，尚未确认。'),
    deadline: text('Stored time limit offset for this step.', '此步骤存储的时限偏移。'),
    backup: text('Stored backup count for the group: extra spawns held in reserve beyond the listed enemies; the refill rule is unconfirmed.', '生成组存储的候补数：列出敌人之外的预备生成；补充规则尚未确认。'),
    alive: text('Stored cap on how many of this group may be alive at once.', '此生成组同时存活数量的存储上限。'),
  });

  function conditions(item, group = false) {
    const hints = conditionHints();
    const parts = [];
    if (item.repeatable) parts.push([text('Repeatable', '可重复'), hints.repeatable]);
    if (item.hidden) parts.push([text('Hidden', '隐藏'), hints.hidden]);
    if (item.killCount > 0) parts.push([text(`Kill threshold ${item.killCount}`, `击杀阈值 ${item.killCount}`), hints.killCount]);
    if (item.hasDeadline) parts.push([text(`Deadline +${seconds(item.deadlineDelta)}`, `截止 +${seconds(item.deadlineDelta)}`), hints.deadline]);
    if (group && item.backupCount > 0) parts.push([text(`${item.backupCount} backups`, `候补 ${item.backupCount}`), hints.backup]);
    if (group && item.limitMaxCount) parts.push([text(`At most ${item.maxCount} alive`, `同时存活 ≤ ${item.maxCount}`), hints.alive]);
    // Enum meanings are not recovered; keep the code in debug instead of
    // translating it into an assumed kill/time/automatic transition.
    if (debug()) parts.push([`mode ${item.mode ?? '?'}${item.targetKey ? ` · ${item.targetKey}` : ''}`, '']);
    return parts.map(([label, hint]) => `<span class="gameplay-value-chip battle-condition"${hint ? ` title="${esc(hint)}" tabindex="0"` : ''}>${esc(label)}</span>`).join('');
  }

  function conditionLegend() {
    const hints = conditionHints();
    const rows = [
      [text('Kill threshold', '击杀阈值'), hints.killCount],
      [text('Backups', '候补'), hints.backup],
      [text('At most N alive', '同时存活 ≤ N'), hints.alive],
      [text('Repeatable', '可重复'), hints.repeatable],
    ];
    return `<details class="gameplay-disclosure battle-condition-legend"><summary>${text('What the group and wave tags mean', '生成组与波次标签说明')}</summary><dl>${rows.map(([term, hint]) => `<dt>${esc(term)}</dt><dd>${esc(hint)}</dd>`).join('')}</dl></details>`;
  }

  // Spawns of one enemy type in a group (same level and Buffs) collapse into
  // one row: counts are summed and timing summarises the stored offsets.
  function spawnRows(group) {
    const merged = new Map();
    for (const spawn of group.spawns) {
      const key = [spawn.enemyId || spawn.libraryKey, spawn.level, spawn.levelUsesGrade, (spawn.buffs || []).map(buffKey).join(';')].join('|');
      const row = merged.get(key);
      if (row) { row.count += spawn.count || 0; row.members.push(spawn); } else merged.set(key, { ...spawn, count: spawn.count || 0, members: [spawn] });
    }
    return [...merged.values()];
  }
  function span(values, format) {
    const list = [...new Set(values.filter((value) => value != null))].sort((a, b) => a - b);
    if (!list.length) return '';
    return list.length === 1 ? format(list[0]) : `${format(list[0])}–${format(list[list.length - 1])}`;
  }
  function mergedTiming(row) {
    const members = row.members || [row];
    if (members.length === 1) return spawnTiming(members[0]);
    const parts = [span(members.map((spawn) => spawn.timestamp), (value) => `+${seconds(value)}`)];
    const interval = span(members.map((spawn) => spawn.interval > 0 ? spawn.interval : null), seconds);
    if (interval) parts.push(text(`every ${interval}`, `间隔 ${interval}`));
    const warning = span(members.map((spawn) => spawn.preWarnTime > 0 ? spawn.preWarnTime : null), seconds);
    if (warning) parts.push(text(`warning ${warning}`, `预警 ${warning}`));
    return parts.filter(Boolean).join(' · ');
  }
  function spawnCells(spawn) {
    const { detail, name } = enemyName(spawn.enemyId, spawn.enemyId || spawn.libraryKey);
    const level = spawn.levelUsesGrade ? text('Lv. by grade', '等级随评级') : spawn.level != null ? `Lv.${spawn.level}` : '';
    const members = spawn.members || [spawn];
    const offsets = members.length > 1 ? members.map(spawnTiming).join('\n') : '';
    return `<td>${enemyChip(spawn.enemyId, name, detail, spawn.resolved)}</td><td class="battle-num">${spawn.count > 1 ? `×${spawn.count}` : ''}</td><td class="battle-num">${esc(level)}</td><td class="battle-num"${offsets ? ` title="${esc(offsets)}"` : ''}>${esc(mergedTiming(spawn))}</td><td>${buffTags(spawn.buffs || [], text('Spawn Buff', '出生 Buff'))}</td>`;
  }

  function groupRows(group) {
    const rows = spawnRows(group);
    const head = (span) => `<th scope="rowgroup" rowspan="${span}"><span class="battle-num">+${seconds(group.timestamp)}</span>${debug() ? ` <code>${esc(group.id)}</code>` : ''}${conditions(group, true)}</th>`;
    if (!rows.length) return `<tr>${head(1)}<td colspan="5" class="muted">${text('No spawn action linked', '未关联生成动作')}</td></tr>`;
    return rows.map((spawn, index) => `<tr>${index ? '' : head(rows.length)}${spawnCells(spawn)}</tr>`).join('');
  }
  // Stored wave/group ids are config keys, not order; waves are numbered by
  // their position and the raw ids stay in debug mode.
  function renderWave(wave, index) {
    const count = wave.configuredCount == null ? text('count partial', '数量部分关联') : text(`${wave.configuredCount} enemies`, `${wave.configuredCount} 名`);
    const other = wave.groups.flatMap((group) => group.otherActions || []);
    return `<tbody><tr class="battle-wave-row"><th colspan="6"><strong>${text('Wave', '第')} ${index + 1}${text('', ' 波')}</strong> <span class="gameplay-caption">+${seconds(wave.timestamp)} · ${count}${debug() ? ` · id ${esc(wave.id)}` : ''}</span>${conditions(wave)}${other.length && debug() ? `<span class="gameplay-caption"> ${esc(other.join(' · '))}</span>` : ''}</th></tr>${wave.groups.map(groupRows).join('')}</tbody>`;
  }
  function renderWaves(row) {
    const battle = row.battle || {};
    const configs = (battle.spawnerIds || []).map((id) => state.spawners[id]).filter(Boolean);
    const unavailable = state.audits.filter((a) => a.status === 'unavailable');
    if (!configs.length) return `<p class="gameplay-section-intro">${text('Spawn configuration is not linked for this stage.', '此关卡尚未关联生成配置。')}</p>${unavailable.map((a) => `<p class="muted">${esc(a.datasetId)}：${esc(a.diagnostic)}</p>`).join('')}`;
    const shared = battle.selection !== 'dungeonBranch' && battle.selection !== 'boundScript';
    const note = shared
      ? text(`${configs.length} shared scene configurations; which one this stage uses is unresolved, so do not add them up.`, `${configs.length} 组共享场景配置，尚未确认本关启用哪一组，请勿相加。`)
      : '';
    const legend = text('Offsets (+N s) are stored per wave, group and spawn; backups, alive limits and repeats change the actual population.', '“+N秒”为波次、生成组与单次生成各自的偏移；候补、存活上限与重复设置会影响实际出场数。');
    const head = `<thead><tr><th>${text('Group', '生成组')}</th><th>${text('Enemy', '敌人')}</th><th>${text('Count', '数量')}</th><th>${text('Level', '等级')}</th><th>${text('Timing', '时间')}</th><th>${text('Spawn Buffs', '出生 Buff')}</th></tr></thead>`;
    return `<p class="gameplay-section-intro">${note ? `${note} ` : ''}${legend}</p>${conditionLegend()}${configs.map((cfg) => {
      const enemies = cfg.waves.reduce((sum, wave) => sum + (wave.configuredCount || 0), 0);
      const title = configs.length > 1 ? `<h4 class="battle-spawner-head">${text(`${cfg.waves.length} waves · ${enemies} enemies`, `${cfg.waves.length} 波 · ${enemies} 名`)}${debug() ? ` <code>${esc(cfg.id)}</code>` : ''}</h4>` : '';
      return `<div class="battle-spawner">${title}<div class="battle-wave-scroll"><table class="battle-wave-table battle-spawn-table"><colgroup><col class="battle-col-group"><col class="battle-col-enemy"><col class="battle-col-count"><col class="battle-col-level"><col class="battle-col-time"><col class="battle-col-buff"></colgroup>${head}${cfg.waves.map(renderWave).join('')}</table></div>${debug() ? `<p class="muted"><code>${esc(cfg.id)}</code> · ${esc(cfg.source)}</p>` : ''}</div>`;
    }).join('')}`;
  }

  function renderFieldBuffs(row) {
    const buffs = row.battle?.fieldBuffs || [];
    const target = { mainCharacter: text('Main character', '主控干员'), spawnedEnemies: text('Spawner enemies', '此生成器的敌人'), unresolved: text('Target unresolved', '目标未关联') };
    const trigger = (type) => ({
      ScriptEvent_OnLeaderEnterTriggerVolume: text('Main character enters a trigger volume', '主控干员进入触发区'),
      ScriptEvent_OnLeaderExitTriggerVolume: text('Main character leaves a trigger volume', '主控干员离开触发区'),
      LevelEvent_OnBattleSignal: text('Battle signal', '战斗信号'),
      LevelEvent_OnSpawnerWaveBegin: text('Spawner wave begins', '生成器波次开始'),
      ScriptEvent_OnScriptActive: text('Script activation', '脚本激活'),
    })[type] || type;
    let html = row.fieldDescription ? `<div class="gameplay-trait-card battle-prose">${rich(row.fieldDescription)}</div>` : '';
    if (!buffs.length) return html + `<p class="gameplay-section-intro">${text('No named Buff action is linked. This does not mean the stage has no special effects.', '尚未关联可展示的具名 Buff 动作；不代表场地没有特殊效果。')}</p>`;
    html += `<p class="gameplay-section-intro">${row.battle.selection === 'sharedScene' ? text('Shared scene scripts. ', '共享场景脚本。') : ''}${text('Stored Buff-application actions; triggers and branch conditions do not prove live activation.', '脚本中的 Buff 施加配置；触发入口与分支条件不代表实际已生效。')}</p>`;
    const rows = buffs.map((buff) => {
      const who = target[buff.target] || target.unresolved;
      const triggers = [...new Set(buff.triggers.map((t) => t.eventKey || trigger(t.type)))].join(' · ') || text('Unresolved', '未关联');
      return `<tr><td>${buffTag(buff, who)}</td><td>${esc(who)}</td><td class="gameplay-caption">${esc(triggers)}</td></tr>`;
    });
    return html + `<div class="battle-wave-scroll"><table class="battle-wave-table battle-field-table"><thead><tr><th>${text('Effect', '效果')}</th><th>${text('Target', '目标')}</th><th>${text('Trigger', '触发入口')}</th></tr></thead><tbody>${[...new Set(rows)].join('')}</tbody></table></div>`;
  }

  // Same reward chip as the Activities page: icon, name and quantity, linking
  // to the item's Gameplay entry.
  function rewardTag(item) {
    const art = item.art?.[0], label = esc(item.name), icon = art?.rel ? `<span class="gameplay-item-chip-icon"><img src="${esc(W.exportFullHref(art.rel))}" alt="" loading="lazy"></span>` : '';
    const body = `${icon}<b>${label}</b><span>×${esc(item.count ?? '?')}</span>`;
    return item.resolved ? `<a class="gameplay-value-chip gameplay-item-chip gameplay-item-chip-link" href="${esc(W.gameplayTabs.pageUrl('item', item.id))}" data-battle-item="${esc(item.id)}">${body}</a>` : `<span class="gameplay-value-chip gameplay-item-chip" title="${esc(text('Unresolved', '未关联'))}">${body}</span>`;
  }
  function renderRewards(row) {
    const names = { firstPassRewardId: text('First clear', '首次通关'), rewardId: text('Clear reward', '通关奖励'), extraRewardId: text('Additional reward', '额外奖励'), customRewardId: text('Custom reward', '特殊奖励'), hunterModeRewardId: text('Hunter mode reward', '猎取模式奖励') };
    return row.rewards.map((reward) => `<div class="battle-reward"><h4>${esc(names[reward.field])}</h4>${reward.items.length ? `<div class="item-reward-tags">${reward.items.map(rewardTag).join('')}</div>` : ''}${!reward.resolved ? `<p class="muted">${text('Reward record unavailable', '奖励记录未关联')}：${esc(reward.id)}</p>` : ''}${reward.hasRandomRewards ? `<p class="muted">${text('Random rewards are also configured; fixed items above are not the complete pool.', '另有随机奖励配置；以上固定物品不代表完整奖励池。')}</p>` : ''}</div>`).join('');
  }
  // Map and mission targets are identity joins published by the builder; a
  // mission link only says the stage is gated on or shelled by that mission.
  function pageLink(hash, key, value) {
    const url = new URL(location.href); url.search = ''; url.hash = hash; url.searchParams.set(key, value);
    return url.href;
  }
  function renderLinks(row) {
    const links = row.links || {}, maps = links.maps || [], missions = links.missions || [];
    if (!maps.length && !missions.length) return '';
    const role = { scene: text('Stage map', '关卡地图'), level: text('Linked area', '关联区域'), entrance: text('Entrance', '入口') };
    const relation = { unlock: text('Unlocked by mission', '任务解锁'), unlockQuest: text('Unlocked by quest', '任务步骤解锁'), missionShell: text('Mission stage', '任务关卡') };
    const mapChips = maps.map((map) => `<a class="gameplay-value-chip" href="${esc(pageLink('map', 'map', map.variant || map.id))}"><b>${esc(map.name || map.id)}</b> <span class="gameplay-caption">${role[map.role] || ''}</span></a>`);
    const missionChips = missions.map((mission) => {
      const label = `<b>${esc(mission.name || mission.id)}</b> <span class="gameplay-caption">${relation[mission.relation] || ''}</span>`;
      return mission.story ? `<a class="gameplay-value-chip" href="${esc(pageLink('story', 'story', mission.story))}">${label}</a>` : `<span class="gameplay-value-chip">${label}</span>`;
    });
    return `<div class="gameplay-trait-card battle-links"><h4>${text('Map and missions', '地图与任务')}</h4><div class="battle-tags">${[...mapChips, ...missionChips].join('')}</div></div>`;
  }
  function renderDetail() {
    const row = state.entries.find((entry) => entry.id === state.selected);
    $('empty').hidden = !!row;
    $('detail-header').hidden = !row;
    if (!row) { $('detail-body').innerHTML = ''; $('empty').textContent = text('Select a combat stage', '选择一个战斗关卡'); return; }
    const facts = [];
    if (row.recommendLevel > 0) facts.push({ label: text('Recommended level', '推荐等级'), value: row.recommendLevel });
    if (row.stamina != null) facts.push({ label: text('Stamina', '体力'), value: row.stamina });
    if (row.hunterStamina > 0) facts.push({ label: text('Hunter stamina', '猎取体力'), value: row.hunterStamina });
    $('detail-title').textContent = row.name;
    $('detail-meta').innerHTML = esc(W.gameplayDetail.metadata([
      { label: text('Type', '类型'), value: text('Combat stage', '战斗关卡') },
      { label: 'ID', value: row.id },
      { label: text('Category', '分类'), value: categoryLabel(row) },
      row.seriesName ? { label: text('Series', '系列'), value: row.seriesName } : null,
      row.mode !== 'unspecified' ? { label: text('Mode', '模式'), value: mode(row.mode) } : null,
      ...facts,
    ]));
    const counterpart = state.entries.find((entry) => entry.id === row.counterpart);
    if (counterpart) {
      const label = text(`Switch to ${mode(counterpart.mode)} mode`, `切换至${mode(counterpart.mode)}`);
      $('detail-meta').innerHTML += `<div class="gameplay-heading-links">${W.gameplayDetail.datasetLink('stage', counterpart.id, label)}</div>`;
    }
    W.gameplayDetail.mount($('detail-header'), $('detail-header-main'), $('detail-title'), $('detail-meta'));
    W.gameplayDetail.bindDatasetLinks($('detail-header'));
    const sections = [['rules', text('Rules', '规则')], ['enemies', text('Enemies', '敌人')], ['waves', text('Waves', '波次')], ['buffs', text('Field Buffs', '场地 Buff')], ['rewards', text('Rewards', '奖励')]];
    const rules = [['mainGoalDesc', text('Objective', '主要目标')], ['extraGoalDesc', text('Extra objective', '额外目标')], ['featureDesc', text('Special rules', '特殊规则')]].filter(([key]) => row.texts[key]);
    const images = (row.art || []).filter((art) => art?.rel);
    if (images.length) sections.push(['assets', text('Assets', '素材')]);
    let html = section(text('Description and rules', '描述与规则'),
      `${row.texts.dungeonDesc ? `<div class="battle-prose">${rich(row.texts.dungeonDesc)}</div>` : ''}`
      + `<div class="battle-rules">${rules.map(([key, label]) => `<div><h4>${label}</h4><div class="battle-prose">${rich(row.texts[key])}</div></div>`).join('') || `<p class="muted">${text('No authored rules are published.', '未发布关卡规则文案。')}</p>`}${renderLinks(row)}</div>`, 'rules');
    html += `<nav class="gameplay-contents" aria-label="${text('Stage contents', '关卡目录')}">${sections.map(([id, label]) => `<button type="button" data-battle-section="${id}">${label}</button>`).join('')}</nav>`;
    html += section(text('Enemy variants', '敌人变种'), row.enemies.length ? `<div class="battle-enemy-grid">${row.enemies.map(enemyCard).join('')}</div><p class="gameplay-audit-note">${text('Artwork comes from the linked bestiary template, not a variant-specific appearance.', '图片沿用关联图鉴模板，不代表变种独立外观。')}</p>` : `<p class="muted">${text('No enemy list is published for this configuration.', '此配置没有列出敌人。')}</p>`, 'enemies');
    html += section(text('Waves and timing', '波次与时间'), renderWaves(row), 'waves');
    html += section(text('Field Buffs', '场地与脚本 Buff'), renderFieldBuffs(row), 'buffs');
    html += section(text('Rewards', '奖励'), renderRewards(row), 'rewards');
    html += section(text('Unlock information', '解锁信息'), row.specialUnlockCondition ? `<p class="muted">${text('A special unlock condition is flagged; its condition has not been resolved.', '配置标记了特殊解锁条件，具体条件尚未关联。')}</p>` : '');
    html += section(text('Related activities', '关联活动'), row.activities.map((activity) => {
      const url = new URL(location.href); url.hash = 'gameplay'; url.searchParams.set('gameplayKind', 'activity'); url.searchParams.set('activity', activity.id); url.searchParams.delete('activityTable');
      const relation = activity.relation === 'completionReference' ? text('Completion condition reference', '完成条件引用')
        : activity.relation === 'modeDestination' ? text('Season configuration', '赛季配置') : '';
      return `<p><a href="${esc(url.href)}">${esc(activity.name)}</a>${relation ? ` · ${relation}` : ''}${activity.unlockStage ? ` · ${text('A stage unlock is configured; its condition is unresolved.', '配置了阶段解锁，具体条件尚未关联。')}` : ''}</p>`;
    }).join(''));
    const siblings = state.entries.filter((entry) => row.seriesId && entry.seriesId === row.seriesId && entry.category === row.category);
    if (siblings.length > 1) html += section(text('Stages in this series', '同系列关卡'), `<div class="gameplay-variant-options">${siblings.map((entry) => `<button type="button" data-stage="${esc(entry.id)}" aria-pressed="${entry.id === row.id}" class="${entry.id === row.id ? 'is-selected' : ''}">${esc(entry.name)}${entry.mode !== 'unspecified' ? ` · ${esc(mode(entry.mode))}` : entry.recommendLevel > 0 ? ` · Lv.${esc(entry.recommendLevel)}` : ''}</button>`).join('')}</div>`);
    if (debug()) {
      const source = state.preview ? `data/lang/${encodeURIComponent(state.language)}/reference/game/DungeonTable.json` : W.dataPageUrl({ store: 'loose', group: 'Table', name: 'DungeonTable.json' });
      const { search, ...stored } = row;
      html += section(text('Source configuration', '来源配置'), `<p><a href="${esc(source)}">DungeonTable / ${esc(row.id)}</a></p><pre>${esc(JSON.stringify(stored, null, 2))}</pre>`);
    }
    if (images.length) html += `<div id="battle-section-assets">${W.gameplay.assetGallery({ kind: 'stage', id: row.id, title: row.name }, { entries: { [`stage:${row.id}`]: { images } } })}</div>`;
    hideBuffPopup();
    $('detail-body').innerHTML = html;
  }

  async function load(force = false, { render = true } = {}) {
    if (!force && state.language === language()) {
      if (render) { strings(); restore(); facets.render(state.entries); renderList(); renderDetail(); }
      return true;
    }
    if (!force && state.loading && state.loadingLanguage === language()) return state.loading;
    const requested = language(), generation = ++state.generation;
    state.controller?.abort(); state.controller = new AbortController();
    state.entries = []; state.selected = ''; state.language = '';
    renderList(); renderDetail(); $('empty').textContent = text('Loading combat stages…', '正在加载战斗关卡…'); $('retry').hidden = true;
    state.loadingLanguage = requested;
    const pending = (async () => {
      try {
        const response = await fetch(`data/lang/${encodeURIComponent(requested)}/gameplay/battle_stages.json`, { signal: state.controller.signal, cache: force ? 'reload' : 'default' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (generation !== state.generation) return false;
        if (data.schemaVersion !== 3 || data.language !== requested || !Array.isArray(data.entries)) throw new Error(text('Unsupported stage publication', '关卡数据格式不匹配'));
        state.spawners = data.spawners || {}; state.enemies = data.enemyDetails || {}; state.buffs = data.buffDetails || {}; state.audits = data.battleEvidence || [];
        state.language = requested; state.entries = data.entries.map((row) => ({ ...row, search: JSON.stringify(row) }));
        state.preview = data.publicationMode === 'referencePreview'; state.modeUnavailable = data.missingTables?.includes('DungeonRaidTable') || false;
        if (render && active()) { strings(); restore(); facets.render(state.entries); renderList(); renderDetail(); }
        W.gameplayTabs.render(); return true;
      } catch (error) {
        if (generation !== state.generation || error.name === 'AbortError') return false;
        $('empty').hidden = false;
        $('empty').textContent = text('Combat stages unavailable. Run the Gameplay battle-stages build: ', '战斗关卡数据不可用，请运行玩法 battle-stages 构建：') + error.message;
        $('retry').hidden = false; W.gameplayTabs.render(); return false;
      } finally { if (generation === state.generation) state.loading = null; }
    })();
    state.loading = pending; return pending;
  }

  // Shared Gameplay sidebar markup (see the Audio/Characters filter panels).
  function shellMarkup() {
    const facet = (id) => `<section class="filter-section is-collapsed" data-filter-section="battle-${id}" data-default-collapsed="1"><button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="battle-${id}-body"><span id="battle-${id}-label"></span></button><div id="battle-${id}-body" class="filter-section-body" hidden><div id="battle-${id}-filter" class="chips" data-multi="1"></div></div></section>`;
    return `<aside id="battle-left"><header><div id="battle-stats" aria-live="polite"></div><div class="sidebar-header-actions"><button id="battle-filter-toggle" type="button" class="panel-toggle" aria-controls="battle-filter-panel"></button><button id="battle-reset" type="button"></button></div></header>`
      + `<div id="battle-filter-panel" class="filters"><section class="filter-section filter-section-basic" data-filter-section="battle-basic" data-fixed-open="1"><span id="battle-basic-label" class="filter-section-title"></span><div class="filter-section-body filter-section-body-stack"><input id="battle-q" type="search"><div class="filter-control-row"><label id="battle-sort-label" for="battle-sort"></label><select id="battle-sort">${SORTS.map((value) => `<option value="${value}"></option>`).join('')}</select></div></div></section>${FACETS.map(facet).join('')}</div>`
      + `<div id="battle-filter-splitter" class="filter-splitter" role="separator" aria-orientation="horizontal" tabindex="0"></div><div id="battle-list-meta"></div><div id="battle-list"></div></aside>`
      + `<div id="battle-splitter" class="pane-splitter" role="separator" aria-orientation="vertical" tabindex="0"></div>`
      + `<main id="battle-right"><p id="battle-boundary" class="muted"></p><button id="battle-retry" type="button" hidden></button><p id="battle-empty" class="muted"></p><header id="battle-detail-header" hidden><div id="battle-detail-header-main"><h2 id="battle-detail-title"></h2><div id="battle-detail-meta"></div></div><button id="battle-locate-current" class="locate-current-button" type="button" disabled></button></header><div id="battle-detail-body" class="gameplay-reading-view"></div><div id="battle-buff-pop" role="tooltip" hidden></div></main>`;
  }

  function bindFilterSections(host) {
    host.querySelectorAll('.filter-section-toggle').forEach((button) => button.addEventListener('click', () => {
      const sectionNode = button.closest('.filter-section'), body = sectionNode?.querySelector('.filter-section-body');
      if (!sectionNode || !body) return;
      const collapsed = !sectionNode.classList.contains('is-collapsed');
      sectionNode.classList.toggle('is-collapsed', collapsed);
      body.hidden = collapsed;
      button.setAttribute('aria-expanded', String(!collapsed));
      window.dispatchEvent(new Event('resize'));
    }));
  }

  function init() {
    const host = document.getElementById('battle-stages-app');
    host.innerHTML = shellMarkup();
    bindFilterSections(host);
    W.locateCurrent?.bind($('locate-current'), locateSelected, () => $('left'));
    facets = W.facets.create({ countMode: 'total', groups: [
      { id: 'category', section: 'battle-category', container: '#battle-category-filter', param: 'battleCategory', values: (row) => row.category, label: (id) => { const row = state.entries.find((entry) => entry.category === id); return row ? categoryLabel(row) : id; } },
      { id: 'mode', section: 'battle-mode', container: '#battle-mode-filter', param: 'battleMode', values: (row) => row.mode, label: mode },
      { id: 'level', section: 'battle-level', container: '#battle-level-filter', param: 'battleLevel', values: (row) => row.recommendLevel > 0 ? String(row.recommendLevel) : 'unspecified', label: (id) => id === 'unspecified' ? text('Unspecified', '未指定') : id },
    ], onChange: () => { W.continuousList.reset($('list')); renderList(); writeUrl(); } });
    W.filters.createPanelToggle({ panel: '#battle-filter-panel', toggle: '#battle-filter-toggle', left: '#battle-left', storageKey: 'battle_filters_collapsed', labels: (collapsed) => collapsed ? text('Show filters', '显示筛选') : text('Hide filters', '隐藏筛选') });
    W.setupListShellSplitters({ shell: host, sidebar: $('left'), pane: $('splitter'), panel: $('filter-panel'), filter: $('filter-splitter'), list: $('list'),
      paneStorageKey: 'webui_battle_splitter_width', filterStorageKey: 'webui_filter_splitter_height_battle', minSidebarWidth: 300 });
    $('q').addEventListener('input', () => { W.continuousList.reset($('list')); renderList(); writeUrl(); });
    $('sort').addEventListener('change', () => { W.continuousList.reset($('list')); renderList(); writeUrl(); });
    $('reset').addEventListener('click', () => { $('q').value = ''; $('sort').value = 'default'; facets.reset({ silent: true }); facets.render(state.entries); W.continuousList.reset($('list')); renderList(); writeUrl(); });
    $('retry').addEventListener('click', () => load(true));
    host.addEventListener('click', (event) => {
      const tag = event.target.closest('[data-battle-buff]');
      if (tag) { showBuffPopup(tag); return; }
      const button = event.target.closest('[data-stage]'); if (button) select(button.dataset.stage);
      const item = event.target.closest('[data-battle-item]');
      if (item && event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) { event.preventDefault(); W.gameplayTabs.open('item', item.dataset.battleItem); }
      const contents = event.target.closest('[data-battle-section]');
      if (contents) document.getElementById(`battle-section-${contents.dataset.battleSection}`)?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    });
    window.addEventListener('webui:debug-changed', () => renderDetail());
    const buffTarget = (event) => event.target.closest?.('[data-battle-buff]');
    host.addEventListener('mouseover', (event) => { const tag = buffTarget(event); if (tag) showBuffPopup(tag); });
    host.addEventListener('focusin', (event) => { const tag = buffTarget(event); if (tag) showBuffPopup(tag); });
    host.addEventListener('mouseout', (event) => { if (buffTarget(event) && !buffTarget({ target: event.relatedTarget || document.body })) hideBuffPopup(); });
    host.addEventListener('focusout', hideBuffPopup);
    host.addEventListener('scroll', hideBuffPopup, true);
    window.addEventListener('webui:ui-locale-changed', () => { strings(); facets.render(state.entries); renderList(); renderDetail(); });
    window.addEventListener('webui:language-changed', () => { if (!active()) { state.generation++; state.controller?.abort(); state.loading = null; state.entries = []; state.language = ''; } });
    strings(); restore(); renderList(); renderDetail();
  }
  W.battleStages = {
    load,
    count: () => state.language === language() ? state.entries.length : null,
    activityStages: (id) => state.language === language()
      ? state.entries.filter((row) => row.activities.some((activity) => activity.id === id)) : [],
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
