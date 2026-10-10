// Production catalog renderer inside Gameplay. Publication paths and exact ID
// joins remain owned by the Production builder; gameplay/tabs.js owns navigation.
(() => {
  const W = window.WebUI;
  const esc = W.escapeHtml;
  const $ = (selector) => document.querySelector(selector);
  const ui = (en, cn) => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").startsWith("zh") ? cn : en;
  const kinds = ["recipes", "items", "machines"];
  const state = {
    root: null, data: null, requestedLanguage: "", language: "", kind: "recipes", selectedId: "",
    query: "", sort: "title", facets: null, pager: null, rows: [], filtered: [], shards: new Map(),
    loadToken: 0, detailToken: 0, detail: null, loading: null, splitter: null, records: {},
  };
  const currentLanguage = () => String($("#language")?.value || "CN").toUpperCase();
  const active = () => document.body.dataset.activeView === "gameplay" && ["item", "recipe", "machine"].includes(W.gameplayTabs?.kind);
  const kindLabel = (kind) => ({ items: ui("Items & materials", "物品与材料"), recipes: ui("Recipes", "配方"), machines: ui("Machines & buildings", "设备与建筑") })[kind] || kind;
  const tagLabel = (tag) => ({
    factory_item: ui("Production material", "生产物料"), craftable: ui("Recipe output", "配方产物"),
    ingredient: ui("Recipe ingredient", "配方原料"), shop_reward: ui("Shop listing", "商店配置"),
    other_uses: ui("Other linked uses", "其他用途引用"), building_item: ui("Building item", "建筑物品"),
    no_source_link: ui("No linked recipe or shop", "未关联配方或商店"),
    machine: ui("Machine crafting", "由设备制造"), hub: ui("Infrastructure equipment", "制作设备的配方"),
    manual: ui("Manual crafting", "简易制造"), has_recipes: ui("Has recipes", "含配方"),
    needs_power: ui("Requires power", "需要供电"),
    activity_only: ui("Activity-only formula", "活动限定配方"),
  })[tag] || tag;
  const useLabel = (type) => ({
    weapon_breakthrough: ui("Weapon breakthrough", "武器突破"), weapon_experience: ui("Weapon experience", "武器经验"),
    equipment_enhance: ui("Equipment enhancement", "装备强化"),
    manual_upgrade_mapping: ui("Manual upgrade mapping", "手动制作升级映射"),
    recipe_formula: ui("Recipe formula reference", "配方物品引用"),
    shop_currency: ui("Shop currency", "商店货币"),
  })[type] || type;
  const number = (value) => W.formatNumber(value);
  const badge = (value) => `<span class="production-badge">${esc(value)}</span>`;
  const empty = (message) => `<p class="production-empty">${esc(message)}</p>`;
  const path = (file) => `data/lang/${encodeURIComponent(state.language)}/production/${file}`;
  const richText = (text) => window.renderDisplayedTextHtml ? window.renderDisplayedTextHtml(text, "") : esc(text);
  const iconUrl = (id) => {
    const icon = state.data?.icons?.[String(id || "").toLowerCase()];
    return icon ? W.exportFullHref(icon.r) : "";
  };
  const iconHtml = (id, className = "") => {
    const url = iconUrl(id);
    return url ? `<img class="production-icon ${className}" src="${esc(url)}" alt="" loading="lazy" decoding="async">` : "";
  };
  const rowIcon = (row, className = "") => {
    const tiers = row.medalIcons || row.medalLevels?.map((tier) => ({
      iconId: tier.item?.iconId, level: tier.level, plated: tier.plated,
    }));
    if (tiers?.length) {
      return `<span class="production-medal-icons">${tiers.map((tier) => {
        const label = `${ui("Level", "等级")} ${tier.level}${tier.plated ? ` · ${ui("Plated", "镀层")}` : ""}`;
        const image = iconHtml(tier.iconId, className);
        return image ? `<span title="${esc(label)}" aria-label="${esc(label)}">${image}</span>` : "";
      }).join("")}</span>`;
    }
    const refs = row.kind === "recipes" ? (row.outcomes || []).flat() : [row];
    const ref = refs.find((value) => iconUrl(value.iconId));
    if (!ref) return "";
    const base = iconHtml(ref.iconId, className);
    return iconUrl(ref.contentIconId)
      ? `<span class="production-composite-icon ${className}">${base}${iconHtml(ref.contentIconId, "production-content-icon")}</span>` : base;
  };
  const categoryLabel = (id) => id === "(none)" ? ui("Uncategorized", "未分类")
    : state.rows.flatMap((row) => row.categories || []).find((category) => category.id === id)?.title || id;
  const categoryIcon = (id) => iconUrl(state.rows.flatMap((row) => row.categories || []).find((category) => category.id === id)?.iconId);
  const typeValue = (row) => row.kind === "machines" ? (row.categories?.length ? row.categories.map((category) => category.id) : ["(none)"])
    : row.kind === "items" ? row.typeGroup || row.type || "(none)" : row.types || row.type || "(none)";
  const canonicalId = (kind, id) => (kind === "items" ? state.data?.itemAliases?.[id]
    : kind === "recipes" ? state.data?.recipeAliases?.[id] : "") || id;

  function pageUrl(kind, id) {
    id = canonicalId(kind, id);
    return W.gameplayTabs.pageUrl({ items: "item", recipes: "recipe", machines: "machine" }[kind], id);
  }

  function recordLink(kind, id, title, resolved = true) {
    if (!id) return "";
    if (!resolved) return `<span class="production-unresolved" title="${esc(ui("Unresolved identifier", "未解析标识符"))}">${esc(title || id)}</span>`;
    id = canonicalId(kind, id);
    const row = state.records[kind]?.get(id);
    return `<a class="production-record-link" href="${esc(pageUrl(kind, id))}" data-production-kind="${esc(kind)}" data-production-id="${esc(id)}" title="${esc(id)}">${row ? rowIcon(row) : ""}<span>${esc(title || id)}</span></a>`;
  }

  const itemLink = (ref) => recordLink("items", ref.id, ref.title, ref.resolved);
  const itemBundle = (ref) => `<span class="production-bundle">${itemLink(ref)}${ref.count != null ? ` <b>× ${esc(number(ref.count))}</b>` : ""}</span>`;

  function sourceLinks(rows = []) {
    const unique = [...new Map(rows.map((row) => [`${row.table}:${row.row}:${row.field || ""}`, row])).values()];
    if (!unique.length) return "";
    return `<details class="production-sources production-technical"><summary>${esc(ui("Source tables", "源数据表"))} (${unique.length})</summary><ul>${unique.map((row) => {
      const href = W.dataPageUrl({ store: "loose", group: "Table", name: `${row.table}.json` });
      return `<li><a href="${esc(href)}">${esc(row.table)}.json</a> · <code>${esc(row.row)}${row.field ? `.${esc(row.field)}` : ""}</code></li>`;
    }).join("")}</ul></details>`;
  }

  function properties(values, label = ui("Stored configuration", "存储配置"), expanded = false) {
    const rows = Object.entries(values).filter(([, value]) => value != null && value !== "");
    if (!rows.length && !expanded) return "";
    const content = rows.length ? `<dl>${rows.map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(typeof value === "object" ? JSON.stringify(value) : String(value))}</dd>`).join("")}</dl>` : empty(ui("No values stored.", "未存储配置值。"));
    return expanded ? `<section class="production-properties"><h4>${esc(label)}</h4>${content}</section>`
      : `<details class="production-properties"><summary>${esc(label)}</summary>${content}</details>`;
  }

  function section(title, contents, count) {
    if (count === 0 || !contents) return "";
    return `<section class="production-section"><h3>${esc(title)}${count != null ? ` <span>(${number(count)})</span>` : ""}</h3>${contents}</section>`;
  }

  function dimensions(range) {
    const axes = ["depth", "width", "height"];
    if (!axes.some((key) => Number.isFinite(range?.[key]))) return "";
    const size = axes.map((key) => Number.isFinite(range?.[key]) ? number(range[key]) : "—").join(" × ");
    return `<dl class="production-dimensions"><div><dt>${esc(ui("Dimensions (depth × width × height)", "尺寸（深度 × 宽度 × 高度）"))}</dt><dd>${esc(size)}</dd></div></dl>`;
  }

  const durationText = (row) => row.durationSeconds != null
    ? `${esc(number(row.durationSeconds))} ${esc(ui("s", "秒"))}` : esc(ui("Not specified", "未指定"));

  function gasRequirement(row) {
    const env = row.gasEnvironment;
    const id = env?.id ?? row.conditions?.gasEnv;
    if (!id) return "";
    const gas = {
      T_fx_icon_gas_stable_UI: { name: ui("Stable", "稳定"), icon: "icon_gas_env_stable" },
      T_fx_icon_gas_wet_UI: { name: ui("Wet", "潮湿"), icon: "icon_gas_env_humidity" },
      T_fx_icon_gas_acidic_UI: { name: ui("Acidic", "酸性"), icon: "icon_gas_env_acid" },
      T_fx_icon_gas_xiranite_UI: { name: ui("Xiranite", "息壤"), icon: "icon_gas_env_xiranite" },
    }[env?.iconId];
    return `<div class="production-gas-requirement"><strong>${esc(ui("Required gas environment", "所需气体环境"))}</strong>: ${iconHtml(gas?.icon)} ${esc(gas?.name || String(id))}</div>`;
  }

  function activityTag(row) {
    return row.activityId ? `<div class="production-activity-tag">${badge(tagLabel("activity_only"))} <code>${esc(row.activityId)}</code></div>` : "";
  }

  function rateText(ref, seconds) {
    return Number.isFinite(seconds) && seconds > 0 && Number.isFinite(ref.count) && ref.count >= 0
      ? `<span class="production-rate">${esc(number(ref.count * 60 / seconds))} ${esc(ui("/ min", "/ 分钟"))}</span>` : "";
  }

  function inlineRecipeGroups(groups, seconds) {
    if (!(groups || []).some((group) => group.length)) return esc(ui("No items recorded", "未记录物品"));
    return groups.map((group) => `<span class="production-machine-group">${groups.length > 1 ? "(" : ""}${group.map((ref) => `${itemBundle(ref)} ${rateText(ref, seconds)}`).join(" <span class=production-plus>+</span> ")}${groups.length > 1 ? ")" : ""}</span>`).join(" · ");
  }

  function renderMachineRecipe(recipe) {
    const formula = recipe.ingredients && recipe.outcomes
      ? `${inlineRecipeGroups(recipe.ingredients, recipe.durationSeconds)}<span class="production-machine-arrow" aria-hidden="true">→</span>${inlineRecipeGroups(recipe.outcomes, recipe.durationSeconds)}`
      : recordLink("recipes", recipe.id, recipe.title);
    return `<article class="production-reference production-machine-recipe" data-production-recipe="${esc(recipe.id)}"><div class="production-machine-formula">${gasRequirement(recipe)}${activityTag(recipe)}${formula}</div><span class="production-machine-time">${esc(ui("Processing time", "处理时间"))}: ${durationText(recipe)}</span><a class="production-machine-recipe-link" href="${esc(pageUrl("recipes", recipe.id))}" data-production-kind="recipes" data-production-id="${esc(recipe.id)}" title="${esc(recipe.title)}">${esc(ui("Details", "详情"))}</a></article>`;
  }

  function renderGroups(groups, seconds) {
    if (!(groups || []).some((group) => group.length)) return empty(ui("No items recorded.", "未记录物品。"));
    return `<div class="production-groups">${groups.map((group, index) => `<div class="production-group">${groups.length > 1 ? `<small>${esc(ui("Group", "组"))} ${index + 1}</small>` : ""}${group.map((ref) => `${itemBundle(ref)} ${rateText(ref, seconds)}`).join(" <span class=production-plus>+</span> ")}</div>`).join("")}</div>`;
  }

  function recipeRefs(rows, produced) {
    if (!rows.length) return empty(ui("No recipe links recovered in these tables.", "这些表中未恢复到配方关联。"));
    return `<div class="production-references">${rows.map((row) => `<article class="production-reference">${gasRequirement(row)}${activityTag(row)}${recordLink("recipes", row.id, row.title)} ${badge(tagLabel(row.type))}<div>${esc(produced ? ui("Output", "产出") : ui("Ingredient", "投入"))}: ${number(row.count)}${row.machineId ? ` · ${recordLink("machines", row.machineId, row.machineName, state.data.machines.some((machine) => machine.id === row.machineId))}` : ""}</div></article>`).join("")}</div>`;
  }

  function renderShop(row) {
    const conditions = Object.values(row.conditions || {}).some((value) => Array.isArray(value) ? value.length : !!value);
    return `<article class="production-reference"><strong>${esc(row.shopGroupName)}${row.shopName !== row.shopGroupName ? ` · ${esc(row.shopName)}` : ""}</strong>
      <div>${esc(ui("Configured quantity", "配置数量"))}: ${number(row.count)} · ${esc(ui("Price", "价格"))}: ${number(row.price)} ${itemLink(row.currency)}</div>
      ${conditions ? badge(ui("Has unlock conditions", "有解锁条件")) : ""}${row.hasRandomRewards ? badge(ui("Also contains random rewards", "还含随机奖励")) : ""}
      ${row.lockDescription ? `<p>${richText(row.lockDescription)}</p>` : ""}
      ${properties({ goodsId: row.id, limitCount: row.limitCount, limitCountRefreshType: row.limitCountRefreshType,
        cnDiscount: row.cnDiscount, shopRefreshType: row.shopRefreshType, shopRefreshCycleType: row.shopRefreshCycleType,
        unlockConditions: row.conditions }, ui("Limits and conditions", "限购与条件"))}${sourceLinks(row.sources)}</article>`;
  }

  function renderUses(rows) {
    const groups = new Map();
    for (const row of rows) {
      if (!groups.has(row.type)) groups.set(row.type, []);
      groups.get(row.type).push(row);
    }
    return [...groups].map(([type, group]) => `<details class="production-use-group"${group.length <= 5 ? " open" : ""}><summary>${esc(useLabel(type))} (${number(group.length)})</summary><div class="production-references">${group.map((row) => {
      const resolved = row.targetKind && state.records[row.targetKind]?.has(canonicalId(row.targetKind, row.targetId));
      const title = row.targetId ? recordLink(row.targetKind, row.targetId, row.title, resolved) : esc(row.title);
      return `<article class="production-reference">${gasRequirement(row)}${title}${row.count != null ? ` ${badge(`× ${number(row.count)}`)}` : ""}
        ${row.level != null ? `<div>${esc(ui("Breakthrough level", "突破等级"))}: ${esc(row.level)}${row.displayLevel != null ? ` · ${esc(ui("Displayed level", "显示等级"))}: ${esc(row.displayLevel)}` : ""}</div>` : ""}
        ${row.items?.length ? `<div>${row.items.map(itemBundle).join(" + ")}</div>` : ""}
        ${row.hasRandomRewards ? badge(ui("Also contains random rewards", "还含随机奖励")) : ""}
        ${type === "weapon_experience" ? properties({ itemExp: row.itemExp, weaponExp: row.weaponExp, weaponExpConvertRatio: row.weaponExpConvertRatio }) : ""}
        ${sourceLinks(row.sources)}</article>`;
    }).join("")}</div></details>`).join("") || empty(ui("No other uses linked in the supported tables.", "支持的数据表中未关联其他用途。"));
  }

  function renderItem(row) {
    let html = `<div class="production-meta">${badge(row.typeName)}${row.showingTypeName && row.showingTypeName !== row.typeName ? badge(row.showingTypeName) : ""}${badge(`${ui("Rarity", "稀有度")} ${row.rarity}`)}</div>`;
    if (row.medalLevels?.length) {
      html += `<div class="production-meta">${(row.categories || []).map((category) => badge(category.title)).join("")}</div>`;
      return html + section(ui("Medal tiers", "蚀刻章等级"), `<div class="production-references">${row.medalLevels.map((tier) => `<article class="production-reference production-medal-tier">
        <h4>${rowIcon(tier.item)}${esc(`${ui("Level", "等级")} ${tier.level}${tier.plated ? ` · ${ui("Plated", "镀层")}` : ""}`)}</h4><code>${esc(tier.item.id)}</code>
        ${tier.item.description && tier.item.description !== row.description ? `<div class="production-description">${richText(tier.item.description)}</div>` : ""}
        ${tier.conditions.length ? `<ul>${tier.conditions.map((condition) => `<li>${richText(condition.description || condition.conditionId)}${condition.progressToCompare != null ? ` · ${esc(ui("Target", "目标"))} ${number(condition.progressToCompare)}` : ""}</li>`).join("")}</ul>` : ""}
        ${renderItem(tier.item)}${sourceLinks(tier.item.sources)}</article>`).join("")}</div>`, row.medalLevels.length);
    }
    if (row.lore && row.lore !== row.description) html += section(ui("Item description", "物品说明"), `<div class="production-description production-lore">${richText(row.lore)}</div>`);
    for (const building of row.buildingDimensions || []) {
      html += `${row.buildingDimensions.length > 1 ? `<p>${esc(building.title)}</p>` : ""}${dimensions(building)}`;
    }
    html += section(ui("Produced by", "制作来源"), recipeRefs(row.producedBy, true), row.producedBy.length);
    html += section(ui("Used in recipes", "配方用途"), recipeRefs(row.usedBy, false), row.usedBy.length);
    html += section(ui("Configured shop listings", "商店配置"), row.shops.length ? row.shops.map(renderShop).join("") : empty(ui("No shop reward links recovered.", "未恢复到商店奖励关联。")), row.shops.length);
    html += section(ui("Upgrades and other uses", "升级与其他用途"), renderUses(row.upgrades), row.upgrades.length);
    if (row.buildingIds.length) html += section(ui("Places buildings", "对应建筑"), row.buildingIds.map((id) => recordLink("machines", id, state.data.machines.find((machine) => machine.id === id)?.title || id, state.data.machines.some((machine) => machine.id === id))).join(" · "));
    if (row.outputReferences.length) html += section(ui("Configured output references", "配置产物引用"), row.outputReferences.map(itemLink).join(" · "));
    html += properties({ maxStackCount: row.stackLimit, maxBackpackStackCount: row.backpackStackLimit, obtainWayIds: row.obtainWayIds, ...row.factory });
    return html;
  }

  function renderRecipe(row) {
    if (row.recipeVariants?.length) {
      return section(ui("Production methods", "制作方式"), `<div class="production-recipe-variants">${row.recipeVariants.map((variant) => `<article class="production-recipe-variant"><h4>${esc(variant.title)}</h4>${renderRecipe(variant)}${sourceLinks(variant.sources)}</article>`).join("")}</div>`, row.recipeVariants.length);
    }
    let html = `${gasRequirement(row)}${activityTag(row)}<div class="production-meta">${badge(tagLabel(row.type))}${(row.categories || []).map((category) => badge(category.title)).join("")}${row.machineId ? recordLink("machines", row.machineId, row.machineName, row.machineResolved) : ""}</div>`;
    html += `<p class="production-duration"><strong>${esc(ui("Production time", "生产时间"))}</strong>: ${durationText(row)}</p>`;
    html += `<div class="production-flow">${section(ui("Ingredients", "原料"), renderGroups(row.ingredients, row.durationSeconds))}<div class="production-arrow" aria-hidden="true">→</div>${section(ui("Outputs", "产物"), renderGroups(row.outcomes, row.durationSeconds))}</div>`;
    if (Number.isFinite(row.durationSeconds) && row.durationSeconds > 0) html += `<p class="production-note">${esc(ui("Nominal rates at continuous operation, calculated from the configured cycle time.", "每分钟用量与产量按配置周期、连续运行计算。"))}</p>`;
    if (row.formulaItem) html += section(ui("Formula item", "配方物品"), itemLink(row.formulaItem));
    html += `<div class="production-recipe-config">${properties(row.conditions, ui("Unlock and operating conditions", "解锁与运行条件"), true)}${properties({ ...(row.configuration || {}), ...(row.timing || {}) }, ui("Stored configuration", "存储配置"), true)}</div>`;
    return html;
  }

  function renderMachine(row) {
    let html = `<div class="production-meta">${(row.categories || []).map((category) => `<span class="production-badge production-category">${iconHtml(category.iconId)}${esc(category.title)}</span>`).join("")}${row.needPower ? badge(ui("Requires power", "需要供电")) : ""}${badge(`${ui("Electricity consumption", "电力消耗")}: ${row.powerConsume ?? "—"}`)}</div>`;
    html += dimensions(row.range);
    if (row.items.length) html += section(ui("Building items", "建筑物品"), row.items.map(itemLink).join(" · "));
    html += section(ui("Recipes", "配方"), row.recipes.length ? `<div class="production-references">${row.recipes.map(renderMachineRecipe).join("")}</div>` : empty(ui("No recipe names this building ID.", "没有配方直接引用此建筑标识符。")), row.recipes.length);
    html += properties({ type: row.type, inputPorts: row.inputPorts, outputPorts: row.outputPorts, range: row.range,
      placeDomains: row.placeDomains, recommendDomains: row.recommendDomains, rendererTemplateMap: row.rendererTemplateMap });
    return html;
  }

  function renderDetail(row) {
    const panel = $("#production-detail");
    if (!panel) return;
    if (!row) { panel.innerHTML = empty(ui("Select an item, recipe or machine to explore its connections.", "选择物品、配方或设备以查看关联。")); return; }
    const updateId = `${row.kind}:${row.id}`;
    panel.innerHTML = `<header class="production-detail-header"><div class="production-identity">${rowIcon(row, "production-icon-large")}<div><small>${esc(kindLabel(row.kind))}</small><h2>${esc(row.title)} ${W.updateBadges.html("production", updateId)}</h2><code>${esc(row.id)}</code></div></div><div class="production-detail-actions"><button id="production-reveal-current" class="panel-toggle" type="button">${esc(ui("Locate current file", "定位当前文件"))}</button></div></header>
      ${W.updateBadges.panel("production", updateId)}
      ${row.kind === "items" && /^item_pic_/i.test(row.id) ? '<div data-gameplay-item-picture></div>' : ""}
      ${row.description ? `<div class="production-description">${richText(row.description)}</div>` : ""}
      ${row.kind === "items" ? renderItem(row) : row.kind === "recipes" ? renderRecipe(row) : renderMachine(row)}
      ${row.kind === "items" ? '<div class="production-gameplay-item" data-gameplay-item-content></div><div data-gameplay-item-assets></div>' : ""}${sourceLinks(row.sources)}`;
    if (row.kind === "items") {
      const contents = panel.querySelector("[data-gameplay-item-content]");
      const token = state.detailToken;
      const picture = panel.querySelector("[data-gameplay-item-picture]");
      if (picture) W.gameplay.itemGallery(row.id, state.language, { picture: true }).then((html) => {
        if (token === state.detailToken && picture.isConnected) picture.innerHTML = html;
      }).catch(() => {});
      W.gameplay.itemContent(row.id, state.language).then((html) => {
        if (token === state.detailToken && contents.isConnected) contents.innerHTML = html;
      }).catch(() => {
        if (token === state.detailToken && contents.isConnected) contents.innerHTML = `${empty(ui("Gameplay item effects are unavailable in this publication.", "当前数据暂不可读取物品使用效果。"))}<button type="button" data-gameplay-item-retry>${esc(ui("Retry item effects", "重试使用效果"))}</button>`;
      });
      const gallery = panel.querySelector("[data-gameplay-item-assets]");
      W.gameplay.itemGallery(row.id, state.language).then((html) => {
        if (token === state.detailToken && gallery.isConnected) gallery.innerHTML = html;
      }).catch(() => {});
    }
    $("#production-reveal-current").addEventListener("click", revealSelectedInList);

  }

  async function select(id, { write = true } = {}) {
    id = canonicalId(state.kind, id);
    state.selectedId = id;
    state.detail = null;
    if (write) syncUrl();
    renderList();
    const token = ++state.detailToken;
    const row = state.rows.find((entry) => entry.id === id);
    if (!row) { $("#production-detail").innerHTML = empty(id ? ui("This record is not in the published catalog.", "此记录不在已发布目录中。") : ui("Select a record to explore its connections.", "选择记录以查看关联。")); return; }
    $("#production-detail").innerHTML = empty(ui("Loading details…", "正在加载详情…"));
    try {
      const file = path(row.detail);
      if (!state.shards.has(file)) state.shards.set(file, getJson(file).catch((error) => { state.shards.delete(file); throw error; }));
      const shard = await state.shards.get(file);
      if (token !== state.detailToken) return;
      const detail = shard.records?.[id];
      if (!detail) throw new Error(ui("The detail shard does not contain this record.", "详情分片不含此记录。"));
      state.detail = detail;
      renderDetail(detail);
    } catch (error) {
      if (token === state.detailToken) $("#production-detail").innerHTML = `${empty(ui("Details could not be loaded.", "无法加载详情。"))}<p>${esc(error.message)}</p><button type="button" data-production-retry-detail>${esc(ui("Retry", "重试"))}</button>`;
    }
  }

  function searchText(row) {
    return [row.id, row.title, row.description, row.typeName, row.showingTypeName, row.machineName, row.machineId,
      ...(row.aliases || []), ...(row.machineNames || []), ...(row.machineIds || []),
      ...(row.categories || []).map((category) => `${category.id} ${category.title}`),
      ...[...(row.ingredients || []), ...(row.outcomes || [])].flatMap((group) => group.map((ref) => `${ref.id} ${ref.title}`)),
      ...row.tags.map(tagLabel), ...row.sources.map((source) => `${source.table}.json ${source.row}`),
    ].filter(Boolean).join("\n");
  }

  function productionListGroup(row) {
    if (row.kind === "machines") return row.categories?.[0] || { id: "(none)", title: ui("Uncategorized", "未分类") };
    const values = typeValue(row);
    const id = Array.isArray(values) ? [...values].sort().join("|") : values;
    return { id, title: row.kind === "recipes" ? (Array.isArray(values) ? values : [values]).map(tagLabel).join(" / ")
      : row.typeName || ui("Uncategorized", "未分类") };
  }

  const listGroups = W.listGroups.create();

  function renderList() {
    const host = $("#production-list");
    if (!host) return;
    let previousCategory = null;
    let groupOpen = false;
    const counts = W.listGroups.counts(state.filtered, (entry) => productionListGroup(entry).id);
    host.innerHTML = state.pager.slice(state.filtered).map((row) => {
      let heading = "";
      const category = productionListGroup(row);
      if (category.id !== previousCategory) {
        previousCategory = category.id;
        heading = `${groupOpen ? "</details>" : ""}${listGroups.section({ id: category.id, title: category.title, count: counts.get(category.id) || 0, icon: iconHtml(category.iconId), className: "production-list-section" })}`;
        groupOpen = true;
      }
      const subtitle = row.kind === "items" ? (row.medalLevelCount ? `${row.typeName} · ${(row.categories || []).map((category) => category.title).join(" · ")} · ${row.medalLevelCount} ${ui("tiers", "个等级")}` : `${row.typeName} · ${ui("Recipe sources", "制作来源")} ${row.counts.producedBy} · ${ui("Uses", "用途")} ${row.counts.usedBy + row.counts.upgrades}`)
        : row.kind === "recipes" ? `${(row.types || [row.type]).map(tagLabel).join(" · ")} · ${(row.categories || []).map((category) => category.title).join(" · ")}${row.tags.includes("activity_only") ? ` · ${tagLabel("activity_only")}` : ""}${row.variantCount > 1 ? ` · ${row.variantCount} ${ui("methods", "种方式")}` : row.machineName ? ` · ${row.machineName}` : ""}`
          : `${(row.categories || []).map((category) => category.title).join(" · ") || ui("Uncategorized", "未分类")}${row.recipeCount ? ` · ${ui("Recipes", "配方")} ${row.recipeCount}` : ""}`;
      return `${heading}<button type="button" class="production-row${row.id === state.selectedId ? " selected" : ""}" data-production-select="${esc(row.id)}" aria-pressed="${row.id === state.selectedId}">${rowIcon(row, "production-icon-list")}<span class="production-row-text"><strong>${esc(row.title)} ${W.updateBadges.html("production", `${row.kind}:${row.id}`)}</strong><span>${esc(subtitle)}</span><code>${esc(row.id)}</code></span></button>`;
    }).join("") + (groupOpen ? "</details>" : "") || empty(ui("No matching records. Reset filters to see the catalog.", "没有符合条件的记录；可重置筛选查看目录。"));
    listGroups.bind(host);
    $("#production-count").textContent = `${number(state.filtered.length)} / ${number(state.rows.length)}`;
    const locate = $("#production-reveal-current");
    if (locate) locate.disabled = !state.selectedId;
  }

  function revealSelectedInList() {
    if (!state.selectedId) return;
    const index = state.filtered.findIndex((row) => row.id === state.selectedId);
    if (index < 0) return;
    if (state.pager.showIndex(index)) renderList();
    const row = [...$("#production-list").querySelectorAll("[data-production-select]")]
      .find((candidate) => candidate.dataset.productionSelect === state.selectedId);
    listGroups.reveal(row);
  }

  function applyFilters(reset = true, write = true) {
    const tokens = W.parseQuery(state.query);
    const scored = state.facets.filter(state.rows).map((row) => ({ row, score: W.queryScore(searchText(row), tokens) }))
      .filter((entry) => !tokens.length || entry.score > 0)
      .map((entry) => ({ ...entry, group: productionListGroup(entry.row) }));
    const compare = W.sorting.comparator("production-sort", (a, b) => {
      const title = a.title.localeCompare(b.title, undefined, { numeric: true, sensitivity: "base" }) || a.id.localeCompare(b.id);
      if (state.sort === "title-desc") return -title;
      if (state.sort === "rarity-asc") return (a.rarity - b.rarity) || title;
      if (state.sort === "rarity-desc") return (b.rarity - a.rarity) || title;
      return title;
    });
    const categoryOrder = new Map((state.data.machineCategories || []).map((category, index) => [category.id, index]));
    scored.sort((a, b) => {
      const categoryA = a.group.id;
      const categoryB = b.group.id;
      if (state.kind === "machines") {
        const order = (categoryOrder.get(categoryA) ?? Infinity) - (categoryOrder.get(categoryB) ?? Infinity);
        if (order) return order;
      }
      if (categoryA !== categoryB) return categoryA === "(none)" ? 1 : categoryB === "(none)" ? -1
        : a.group.title.localeCompare(b.group.title, undefined, { numeric: true });
      return compare(a.row, b.row);
    });
    state.filtered = scored.map((entry) => entry.row);
    state.pager.setTotal(state.filtered.length, { reset });
    renderList();
    if (write) syncUrl();
  }

  function syncUrl() {
    if (!active()) return;
    const url = new URL(location.href);
    for (const key of [...url.searchParams.keys()]) if (key.startsWith("production")) url.searchParams.delete(key);
    url.searchParams.set("productionKind", state.kind);
    url.searchParams.set("gameplayKind", { items: "item", recipes: "recipe", machines: "machine" }[state.kind]);
    if (state.selectedId) url.searchParams.set("productionId", state.selectedId);
    if (state.query) url.searchParams.set("productionQ", state.query);
    if (state.sort !== "title") url.searchParams.set("productionSort", state.sort);
    state.facets.toParams(url.searchParams);
    url.hash = "gameplay";
    history.replaceState(history.state, "", url);
  }

  function readUrl() {
    const params = new URLSearchParams(location.search);
    state.kind = { item: "items", recipe: "recipes", machine: "machines" }[params.get("gameplayKind") || W.gameplayTabs?.kind]
      || (kinds.includes(params.get("productionKind")) ? params.get("productionKind") : "recipes");
    const legacyItem = state.kind === "items" ? W.gameplay.normalizeSelection(params.get("gameplay") || params.get("gameplayId") || params.get("entry") || "") : "";
    state.selectedId = canonicalId(state.kind, params.get("productionId") || legacyItem);
    state.query = params.get("productionQ") || "";
    state.sort = ["title", "title-desc", "rarity-asc", "rarity-desc"].includes(params.get("productionSort")) ? params.get("productionSort") : "title";
    if (state.kind === "items" && state.data) {
      const types = params.getAll("productionType").map((value) => {
        const row = state.data.items.find((item) => item.type === value);
        return row ? typeValue(row) : value;
      });
      params.delete("productionType");
      for (const value of new Set(types)) params.append("productionType", value);
    }
    return params;
  }

  function setupPaneSplitter() {
    // The shell is replaced on catalog/locale changes; retire its global listener.
    if (state.splitter) window.removeEventListener("resize", state.splitter.requestSync);
    const sidebar = $("#production-sidebar");
    const shell = $("#production-app .production-layout");
    const handle = $("#production-splitter");
    const utils = W.splitterUtils;
    const storageKey = "webui_production_splitter_width";
    state.splitter = W.setupSplitter({
      handle, storageKey, bodyDragClass: "is-resizing-pane", client: (event) => event.clientX,
      keys: { decrease: ["ArrowLeft"], increase: ["ArrowRight"] },
      enabled: () => !utils.isMobileLayout(),
      bounds: () => ({ min: 320, max: Math.max(320, shell.getBoundingClientRect().width - handle.getBoundingClientRect().width - 320) }),
      read: () => sidebar.getBoundingClientRect().width,
      write: (width) => { sidebar.style.width = `${Math.round(width)}px`; },
      clear: () => sidebar.style.removeProperty("width"),
      sync: (controller) => {
        if (utils.isMobileLayout()) { controller.clear({ commit: false }); return; }
        if (shell.getBoundingClientRect().width < 48) return;
        const width = utils.readStoredNumber(storageKey) ?? sidebar.getBoundingClientRect().width;
        controller.set(width, { persist: false, commit: false });
      },
    });
  }

  function renderShell({ params = null } = {}) {
    if (!state.root || !state.data) return;
    ++state.detailToken;
    state.detail = null;
    const facetState = state.facets?.snapshot();
    state.rows = state.data[state.kind];
    state.root.innerHTML = `<div class="production-layout">
      <aside id="production-sidebar" class="production-sidebar"><header><div class="production-toolbar"><h2>${esc(kindLabel(state.kind))}</h2><button id="production-filter-toggle" class="panel-toggle" type="button" aria-controls="production-filters" aria-expanded="true"></button></div></header>
      <div id="production-filters" class="filters"><div class="filter-control-row production-search-row"><label for="production-search">${esc(ui("Search names, IDs, ingredients or files", "搜索名称、标识符、原料或文件"))}</label><input id="production-search" type="search" value="${esc(state.query)}" placeholder="${esc(ui("Regex tokens; match any word", "正则词条；任一词匹配"))}"></div>
      <div class="filter-section-body filter-control-row"><label for="production-sort">${esc(ui("Sort", "排序"))}</label><select id="production-sort"><option value="title">${esc(ui("Name (A-Z)", "名称 (A-Z)"))}</option><option value="title-desc">${esc(ui("Name descending", "名称降序"))}</option><option value="rarity-asc">${esc(ui("Rarity ascending", "稀有度升序"))}</option><option value="rarity-desc">${esc(ui("Rarity descending", "稀有度降序"))}</option></select></div>
      ${state.kind === "recipes" ? "" : `<details class="filter-section" data-filter-section="production-type"><summary>${esc(state.kind === "machines" ? ui("Encyclopedia categories", "百科分类") : ui("Types", "类型"))}</summary><div id="production-type-filter" class="production-chips"></div></details>`}
      <details class="filter-section" data-filter-section="production-category"${state.kind === "machines" ? " hidden" : ""}><summary>${esc(state.kind === "recipes" ? ui("Output categories", "产物分类") : ui("Medal categories", "蚀刻章分类"))}</summary><div id="production-category-filter" class="production-chips"></div></details>
      <details class="filter-section" data-filter-section="production-tag"><summary>${esc(state.kind === "recipes" ? ui("Formula tags", "配方标签") : ui("Relationships", "关联"))}</summary><div id="production-tag-filter" class="production-chips"></div></details>
      ${W.updateBadges.filterSection("production")}
      <button id="production-reset" class="panel-toggle" type="button">${esc(ui("Reset filters", "重置筛选"))}</button></div>
      <div class="production-list-heading"><strong>${esc(kindLabel(state.kind))}</strong><span id="production-count" aria-live="polite"></span></div><div id="production-list"></div><footer id="production-pager"></footer></aside>
      <div id="production-splitter" class="pane-splitter" role="separator" aria-label="${esc(ui("Resize production sidebar", "调整生产侧栏宽度"))}" aria-orientation="vertical" tabindex="0"></div>
      <main class="production-main"><p class="production-boundary">${esc(ui("Stored recipes, shop listings and item-use references. Unlock conditions and actual availability may differ in play.", "展示存储的配方、商店配置与物品用途引用。实际解锁条件及可用性以游戏运行情况为准。"))}</p>
      ${state.language !== state.requestedLanguage ? `<p class="production-note">${esc(ui(`This catalog has no ${state.requestedLanguage} publication; showing ${state.language}.`, `此目录没有 ${state.requestedLanguage} 数据，当前显示 ${state.language}。`))}</p>` : ""}
      <div id="production-detail" aria-live="polite"></div><details class="production-technical production-audit"><summary>${esc(ui("Coverage and unresolved references", "覆盖范围与待解析引用"))}</summary><p>${esc(ui("Upgrade coverage: weapon breakthrough and experience, equipment enhancement, manual-upgrade mappings, formula items and shop currencies. Other item sources and uses may exist.", "升级用途覆盖武器突破与经验、装备强化、手动升级映射、配方物品及商店货币；物品还可能有其他来源和用途。"))}</p>
      <p>${esc(ui("Unresolved source references", "待解析来源引用"))}: ${number(state.data.unresolvedReferences.length)}</p><ul>${state.data.unresolvedReferences.map((row) => `<li>${esc(row.table)} · <code>${esc(row.row)}.${esc(row.field)} → ${esc(row.target || ui("empty", "空值"))}</code></li>`).join("")}</ul></details></main></div>`;
    $("#production-sort").value = state.sort;
    W.sorting.refresh();
    state.facets = W.facets.create({
      countMode: "total", groups: [
        W.updateBadges.filterGroup("production", (row) => W.updateBadges.status("production", `${row.kind}:${row.id}`), { param: "productionUpdate" }),
        ...(state.kind === "recipes" ? [] : [{ id: "type", container: "#production-type-filter", section: "production-type", param: "productionType",
          values: typeValue, label: (value) => state.kind === "machines" ? categoryLabel(value) : state.rows.find((row) => typeValue(row) === value)?.typeName || value,
          icon: (value) => state.kind === "machines" ? categoryIcon(value) : "" }]),
        { id: "category", container: "#production-category-filter", section: "production-category", param: "productionCategory",
          values: (row) => state.kind === "machines" ? [] : (row.categories || []).map((category) => category.id), label: categoryLabel, icon: categoryIcon },
        { id: "tag", container: "#production-tag-filter", section: "production-tag", param: "productionTag", values: (row) => row.tags, label: tagLabel },
      ], onChange: () => applyFilters(),
    });
    if (state.kind === "recipes") {
      if (params) {
        params = new URLSearchParams(params);
        for (const value of params.getAll("productionType")) {
          if (!params.getAll("productionTag").includes(value)) params.append("productionTag", value);
        }
        params.delete("productionType");
      } else if (facetState?.type?.length) {
        facetState.tag = [...new Set([...(facetState.tag || []), ...facetState.type])];
        delete facetState.type;
      }
    }
    if (params) state.facets.fromParams(params, { silent: true });
    else if (facetState) state.facets.restore(facetState, { silent: true });
    W.updateBadges.syncFilter("production", "production", state.facets);
    W.updateBadges.bindFilter("production");
    state.facets.render(state.rows);
    state.pager = W.pagination.createPager({ container: "#production-pager", storageKey: "webui_production_page_size", onChange: renderList });
    setupPaneSplitter();
    W.filters.createPanelToggle({ panel: "#production-filters", toggle: "#production-filter-toggle", left: ".production-sidebar",
      storageKey: "webui_production_filters_collapsed", labels: (collapsed) => collapsed ? ui("Show filters", "显示筛选") : ui("Hide filters", "隐藏筛选") });
    $("#production-search").addEventListener("input", (event) => { state.query = event.target.value; applyFilters(); });
    $("#production-sort").addEventListener("change", (event) => { state.sort = event.target.value; applyFilters(); });
    $("#production-reset").addEventListener("click", () => {
      state.query = ""; state.sort = "title"; $("#production-search").value = ""; $("#production-sort").value = "title";
      state.facets.reset({ silent: true }); state.facets.render(state.rows); W.sorting.refresh(); applyFilters();
    });
    applyFilters(true, false);
    if (state.selectedId) {
      state.pager.showIndex(state.filtered.findIndex((row) => row.id === state.selectedId));
      select(state.selectedId, { write: false });
    } else renderDetail(null);
    W.gameplayTabs?.render();
  }

  async function getJson(url) {
    const response = await W.fetchWithProgress(url, { cache: "no-cache" });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
    return response.json();
  }

  async function load(language = currentLanguage(), force = false) {
    if (!state.root) init();
    if (!state.root) return null;
    const requested = String(language || "CN").toUpperCase();
    if (!force && state.loading && requested === state.requestedLanguage) return state.loading;
    if (!force && state.data && requested === state.requestedLanguage) { renderShell({ params: readUrl() }); return state.data; }
    const token = ++state.loadToken;
    ++state.detailToken;
    state.requestedLanguage = requested;
    state.root.innerHTML = empty(ui("Loading catalog…", "正在加载目录…"));
    const pending = (async () => {
      try {
        const manifest = await getJson("data/production/manifest.json");
        const chosen = manifest.languages.includes(requested) ? requested : manifest.defaultLanguage;
        const [data] = await Promise.all([getJson(`data/lang/${encodeURIComponent(chosen)}/production/index.json`), W.updateBadges.load("production")]);
        if (token !== state.loadToken) return null;
        if (data.schema !== "endfield.production.v1") throw new Error(ui("Unsupported Production data schema.", "不支持的生产数据结构。"));
        state.data = data; state.language = chosen; state.shards.clear(); state.detail = null;
        state.records = Object.fromEntries(kinds.map((kind) => [kind, new Map(data[kind].map((row) => [row.id, row]))]));
        renderShell({ params: readUrl() });
        return data;
      } catch (error) {
        if (token !== state.loadToken) return null;
        state.data = null;
        state.root.innerHTML = `${empty(ui("This catalog could not be loaded.", "无法加载此目录。"))}<p class="production-error">${esc(error.message)}</p><button type="button" data-production-retry>${esc(ui("Retry", "重试"))}</button>`;
        W.gameplayTabs?.render();
        return null;
      } finally { if (token === state.loadToken) state.loading = null; }
    })();
    state.loading = pending;
    return pending;
  }

  function open(kind, id = "") {
    if (!kinds.includes(kind)) return;
    W.gameplayTabs.open({ items: "item", recipes: "recipe", machines: "machine" }[kind], canonicalId(kind, id));
  }

  function init() {
    state.root = $("#production-app");
    if (!state.root || state.root.dataset.productionBound) return;
    state.root.dataset.productionBound = "1";
    state.root.addEventListener("click", (event) => {
      const link = event.target.closest("[data-production-kind]");
      if (link && W.isPlainClick(event)) { event.preventDefault(); open(link.dataset.productionKind, link.dataset.productionId); return; }
      const reward = event.target.closest("[data-gameplay-related-key]");
      if (reward) { const [kind, ...id] = reward.dataset.gameplayRelatedKey.split(":"); W.gameplayTabs.open(kind, id.join(":")); return; }
      const selection = event.target.closest("[data-production-select]");
      if (selection) { select(selection.dataset.productionSelect); return; }
      if (event.target.closest("[data-production-retry]")) load(currentLanguage(), true);
      if (event.target.closest("[data-production-retry-detail]")) select(state.selectedId);
      if (event.target.closest("[data-gameplay-item-retry]") && state.detail) renderDetail(state.detail);
    });
  }

  W.production = { init, load, open, pageUrl, count: (kind) => state.data ? state.data[kind]?.length : null };
  window.addEventListener("webui:ui-locale-changed", () => { if (active() && state.data) renderShell(); });
  window.addEventListener("webui:inline-tag-mode-changed", () => { if (state.detail) renderDetail(state.detail); });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true }); else init();
})();
