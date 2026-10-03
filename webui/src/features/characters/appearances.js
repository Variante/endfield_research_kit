(() => {
  const WebUI = window.WebUI = window.WebUI || {};
  const ui = (en, zh) => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").startsWith("zh") ? zh : en;
  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const scalar = (value) => String(value ?? "");
  const normalizeText = (value) => scalar(value).trim();
  const labels = {
    DialogTextTable: ["Dialogue", "对白"], RadioTable: ["Radio", "无线电"],
    EnvTalkTable: ["Ambient dialogue", "环境对白"], SNSDialogTable: ["SNS", "SNS"],
    RemoteCommonTable: ["Remote communication", "远程通讯"], MailTemplateTable: ["Mail", "邮件"],
  };
  const sourceLabel = (source) => labels[source] ? ui(...labels[source]) : source;

  function matchesTextReference(reference, raw, fieldTrace) {
    const rawText = typeof raw === "object" && raw ? raw.text : raw;
    if (scalar(rawText || "") !== scalar(reference.text || "")) return false;
    const expectedId = scalar(reference.id || "");
    if (!expectedId) return !raw?.id || raw.id === 0;
    // JSON's numeric raw.id may already be rounded. Only an exact source-field
    // lookup string or a safe integer can prove the I18n reference.
    const sourcePath = fieldTrace && `${fieldTrace.table}[${fieldTrace.rowId}].${fieldTrace.field}`;
    const exactId = (fieldTrace?.lookup || []).find((item) => item.from === sourcePath
      && typeof item.value === "string" && /^-?\d+$/.test(item.value))?.value;
    const safeId = Number.isSafeInteger(raw?.id) ? scalar(raw.id) : "";
    return (exactId || safeId) === expectedId;
  }

  function matchesPublishedLine(entry, line) {
    const location = entry.story;
    const trace = line?._debug;
    const source = trace?.source;
    if (!location || !source || trace.table !== location.table || scalar(trace.rowId) !== scalar(location.rowId)) return false;
    if (location.lineId && scalar(line.id) !== scalar(location.lineId)) return false;
    if (location.cid != null && scalar(line.cid) !== scalar(location.cid)) return false;
    if (scalar(source[entry.speakerField] || "") !== entry.speakerId) return false;
    const textTrace = trace.fields?.text?.field === entry.textField ? trace.fields.text : null;
    if (!matchesTextReference(entry.textReference || {}, source[entry.textField], textTrace)) return false;
    // SNS media text may be synthesized from contentParam. Check the localized
    // source content field instead of comparing it with the rendered media tag.
    if (normalizeText(textTrace?.text ?? line.text) !== normalizeText(entry.text)) return false;
    if (entry.evidenceBoundary !== "direct" && entry.speakerReference) {
      const actorTrace = trace.fields?.actor?.field === entry.speakerNameField ? trace.fields.actor : null;
      if (!matchesTextReference(entry.speakerReference, source[entry.speakerNameField], actorTrace)) return false;
      if (entry.speakerLabel && normalizeText(actorTrace?.text ?? line.actor) !== normalizeText(entry.speakerLabel)) return false;
    }
    if (entry.source === "SNSDialogTable" && (scalar(source.contentType) !== scalar(entry.contentType)
        || JSON.stringify(source.contentParam || []) !== JSON.stringify(entry.contentParameters || []))) return false;
    return true;
  }

  function validateAppearance(entry, conversation) {
    if (conversation?.key !== entry.story?.key) return false;
    return (conversation.lines || []).some((line) => matchesPublishedLine(entry, line));
  }

  function storyUrl(entry, language) {
    const url = new URL(window.location.href);
    url.search = "";
    url.searchParams.set("lang", language);
    url.searchParams.set("story", entry.story.key);
    if (entry.story.lineId) url.searchParams.set("line", entry.story.lineId);
    if (entry.story.cid != null) url.searchParams.set("cid", entry.story.cid);
    url.hash = "story";
    return url.href;
  }

  let panel, pager, facets, rows = [], currentLanguage = "CN", generation = 0;
  const sidecars = new Map();

  function ensurePanel() {
    if (panel) return;
    panel = document.createElement("details");
    panel.className = "character-appearances";
    panel.open = true;
    panel.innerHTML = `<summary></summary><p class="character-appearance-note"></p>
      <input class="character-appearance-search" type="search">
      <div class="character-appearance-source-filters filter-chips"></div>
      <div class="character-appearance-attribution-filters filter-chips"></div>
      <div class="character-appearance-count" aria-live="polite"></div>
      <div class="character-appearance-pager"></div><div class="character-appearance-list"></div>`;
    pager = WebUI.pagination.createPager({ container: panel.querySelector(".character-appearance-pager"),
      storageKey: "characters.appearances.pageSize", defaultPageSize: 50, onChange: () => renderRows() });
    facets = WebUI.facets.create({ countMode: "total", groups: [
      { id: "source", container: panel.querySelector(".character-appearance-source-filters"), values: (row) => row.source, label: sourceLabel },
      { id: "evidence", container: panel.querySelector(".character-appearance-attribution-filters"), values: (row) => row.evidenceBoundary,
        label: (value) => value === "direct" ? ui("Authored speaker", "直接说话者") : ui("Label attribution unresolved", "名称归属待确认") },
    ], onChange: () => renderRows(true) });
    panel.querySelector("input").addEventListener("input", () => renderRows(true));
    panel.querySelector(".character-appearance-list").addEventListener("click", openStory);
  }

  function renderRows(reset = false) {
    if (!panel) return;
    const query = panel.querySelector("input").value.trim().toLocaleLowerCase();
    const filtered = facets.filter(rows).filter((entry) => !query || [entry.text, entry.key, entry.speakerId, entry.identity, entry.speakerLabel]
      .some((value) => scalar(value).toLocaleLowerCase().includes(query)));
    pager.setTotal(filtered.length, { reset });
    panel.querySelector(".character-appearance-count").textContent = ui(`${filtered.length.toLocaleString()} of ${rows.length.toLocaleString()} authored appearances`, `${filtered.length.toLocaleString()} / ${rows.length.toLocaleString()} 条来源记录`);
    panel.querySelector(".character-appearance-list").innerHTML = pager.slice(filtered).map((entry) => `
      <article class="character-appearance" data-appearance-index="${entry._index}">
        <div class="character-appearance-heading"><strong>${escape(sourceLabel(entry.source))}</strong>
          ${entry.evidenceBoundary !== "direct" ? `<span class="character-appearance-unresolved">${ui("Attribution unresolved", "归属待确认")}</span>` : ""}
          ${entry.story ? `<button type="button" data-appearance-story>${ui("Find in Story", "在剧情中查找")}</button>` : ""}</div>
        <p>${escape(entry.text || ui("Media or empty text record", "媒体或空文本记录"))}</p>
        <code>${escape(entry.key)}</code>
        <small>${escape(entry.identity)}${entry.speakerLabel ? ` · ${escape(entry.speakerLabel)}` : ""}</small>
        <span class="character-appearance-story-status" role="status"></span>
      </article>`).join("") || `<p>${ui("No matching authored appearances.", "没有符合筛选条件的来源记录。")}</p>`;
  }

  async function openStory(event) {
    const button = event.target.closest("[data-appearance-story]");
    if (!button) return;
    const card = button.closest("[data-appearance-index]");
    const entry = rows[Number(card.dataset.appearanceIndex)];
    const token = generation;
    const language = currentLanguage;
    button.disabled = true;
    const status = card.querySelector(".character-appearance-story-status");
    status.textContent = ui("Checking published source…", "正在核对已发布来源…");
    try {
      const response = await fetch(`data/lang/${encodeURIComponent(language)}/conv/${encodeURIComponent(entry.story.key)}.json`, { cache: "no-store" });
      const conversation = response.ok ? await response.json() : null;
      if (token !== generation || !card.isConnected) return;
      if (!validateAppearance(entry, conversation)) {
        status.textContent = ui("No matching line in the current Story publication. The source record remains available here.", "当前剧情发布数据未匹配该行。此处保留原始来源记录。");
        return;
      }
      const link = document.createElement("a");
      link.href = storyUrl(entry, language);
      link.textContent = ui("Open in Story ↗", "打开剧情 ↗");
      link.className = "character-appearance-story-link";
      button.replaceWith(link);
      status.textContent = ui("Source row, speaker and text verified.", "已核对来源行、说话者与文本。");
      link.click();
    } catch (_error) {
      if (token === generation) status.textContent = ui("Story publication is unavailable.", "剧情发布数据不可用。");
    } finally {
      button.disabled = false;
    }
  }

  async function mount(host, identities, language) {
    if (!host) return;
    ensurePanel();
    const token = ++generation;
    currentLanguage = language;
    host.append(panel);
    panel.querySelector("summary").textContent = ui("Appearances", "出场记录");
    panel.querySelector(".character-appearance-note").textContent = ui("All indexed speaker records. Story navigation checks the last published source; label-only attributions remain unresolved.", "显示全部已索引的说话者记录。跳转前核对最近发布的剧情来源；仅有名称的归属仍待确认。");
    const input = panel.querySelector("input");
    input.value = "";
    input.placeholder = ui("Search text or source IDs…", "搜索文本或来源 ID…");
    input.setAttribute("aria-label", input.placeholder);
    facets.reset({ silent: true });
    rows = [];
    facets.render(rows);
    renderRows(true);
    panel.querySelector(".character-appearance-count").textContent = ui("Loading appearances…", "正在加载出场记录…");
    const results = await Promise.allSettled((identities || []).filter((identity) => identity.appearancesPath).map(async (identity) => {
      const path = identity.appearancesPath;
      if (!/^appearances\/[a-z0-9_]+\.json$/.test(path)) throw new Error("Invalid appearance path");
      const cacheKey = `${language}/${path}/${identity.appearancesSignature}`;
      let entries = sidecars.get(cacheKey);
      if (!entries) {
        const response = await fetch(`data/lang/${encodeURIComponent(language)}/characters/${path}`, { cache: "no-store" });
        if (!response.ok) throw new Error("Appearance file unavailable");
        const data = await response.json();
        if (data.schema !== "characterAppearances.v1" || data.identity !== identity.id || data.language !== language
            || !identity.appearancesSignature || data.sourceSignature !== identity.appearancesSignature
            || !Array.isArray(data.entries) || data.entries.length !== identity.appearanceCount) throw new Error("Appearance publication mismatch");
        entries = data.entries;
        if (sidecars.size >= 128) sidecars.delete(sidecars.keys().next().value);
        sidecars.set(cacheKey, entries);
      }
      return entries.map((entry) => ({ ...entry, identity: identity.id }));
    }));
    if (token !== generation) return;
    rows = results.flatMap((result) => result.status === "fulfilled" ? result.value : [])
      .sort((a, b) => a.source.localeCompare(b.source) || a.key.localeCompare(b.key, undefined, { numeric: true }) || a.identity.localeCompare(b.identity))
      .map((entry, index) => ({ ...entry, _index: index }));
    facets.render(rows);
    renderRows(true);
    if (results.some((result) => result.status === "rejected")) {
      panel.querySelector(".character-appearance-note").textContent += ui(" Some appearance files are missing or belong to a different publication; refresh Characters to rebuild them.", " 部分出场文件缺失或不属于同一次发布；请重新生成 Characters 数据。");
    }
  }
  WebUI.characterAppearances = { mount, validateAppearance };
})();
