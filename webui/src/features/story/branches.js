// A compact view of already published branch evidence. It never sorts scenes
// into a playthrough or turns a filename/numbering hint into a control-flow edge.
(() => {
  const WebUI = window.WebUI = window.WebUI || {};
  const list = (value) => Array.isArray(value) ? value : [];
  const text = (value) => String(value ?? "");
  const unique = (values) => [...new Set(values.filter(Boolean).map(text))];
  const ui = (en, zh) => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").startsWith("zh") ? zh : en;
  const esc = window.WebUI.escapeHtml;

  function buildModel(conv, { missionTimelineRecovery = null } = {}) {
    if (!conv || !conv.key) return null;
    const names = new Map(), manualOptions = new Set();
    for (const group of list(conv.optionGroups)) for (const option of list(group.options)) {
      names.set(text(option.id), option.text || "");
      if (group.manualOverride || option.manualOverride || option.manualResponse) manualOptions.add(text(option.id));
    }
    for (const link of list(conv.sceneGraphLinks)) for (const option of list(link.options))
      for (const target of list(option.submenuTargets)) if (target.optionId) names.set(text(target.optionId), target.text || names.get(text(target.optionId)) || "");
    const groups = [], covered = new Set();
    for (const link of list(conv.sceneGraphLinks)) {
      const options = list(link.options).map((option) => {
        covered.add(text(option.optionId));
        const targets = unique([option.firstSceneKey, ...list(option.sceneKeys), ...list(option.submenuSceneKeys)]);
        const lineIds = unique([option.firstLineId, ...list(option.pathLineIds)]);
        const terminal = option.terminal || (option.outcomeKind === "terminalOnly" ? "terminal" : "");
        const loop = option.loop?.kind || (option._debug?.returnsToSourceOptionNode ? "sameOptionMenuReturn" : "");
        return { id: text(option.optionId), label: names.get(text(option.optionId)) || text(option.optionId),
          targets, lineIds, terminal, loop, outcome: option.outcomeKind || "", boundary: "direct",
          manualLabel: manualOptions.has(text(option.optionId)),
          unresolved: !targets.length && !lineIds.length && !terminal && !loop };
      });
      if (options.length) groups.push({ source: link.sourceKey || conv.key, after: link.after || "", options,
        boundary: "direct", file: link.file || "", node: link._debug?.link?.sourceOptionNodeId || "" });
    }
    for (const group of list(conv.optionGroups)) {
      const options = list(group.options).filter((option) => !covered.has(text(option.id))).map((option) => {
        const manual = !!(group.manualOverride || option.manualOverride || option.manualResponse);
        const lineIds = unique(list(option.branchLines));
        const targets = unique([option.targetSceneKey, ...list(option.submenuTargets).map((target) => target.sceneKey)]);
        return { id: text(option.id), label: option.text || text(option.id), targets, lineIds,
          terminal: "", loop: "", outcome: "", boundary: manual ? "manual" : "structuralOnly",
          unresolved: !targets.length && !lineIds.length };
      });
      if (options.length) groups.push({ source: conv.key, after: group.after || "", options,
        boundary: group.manualOverride ? "manual" : "structuralOnly", hint: !!group.branchHint,
        risk: group.optionBranchRisk?.code || "", file: "", node: text(group.g) });
    }
    // SNS options refer to exact content IDs in the same published conversation.
    const snsLines = new Map(list(conv.lines).filter((line) => line.cid != null).map((line) => [text(line.cid), line]));
    if (conv.kind === "sns") for (const line of list(conv.lines)) {
      const options = list(line.options).map((option) => {
        const next = option.next ?? option.nextContentId;
        const matched = next != null && snsLines.has(text(next));
        return { id: text(option.id || option.oid), label: option.text || text(option.id || option.oid),
          targets: [], lineIds: [], cid: matched ? next : null, terminal: "", loop: "",
          outcome: "", boundary: "direct", unresolved: !matched };
      });
      if (options.length) groups.push({ source: conv.key, after: "", cid: line.cid, options, boundary: "direct", sourceKind: "sns", file: "", node: "" });
    }
    const recovery = missionTimelineRecovery || {};
    const sceneLinks = list(recovery.sourceBackedSceneEdges).filter((edge) => edge.from === conv.key || edge.to === conv.key)
      .map((edge) => ({ from: edge.from, to: edge.to, kind: edge.kind || "sourceBacked", sourceKeys: list(edge.sourceKeys) }));
    const confidence = recovery.sceneOrderInfo?.[conv.key]?.confidence || "";
    const unresolved = list(recovery.unresolved).filter((item) => item.sceneKey === conv.key);
    const hasOrderGap = confidence === "weak" || confidence === "fallback";
    if (!groups.length && !sceneLinks.length && !hasOrderGap && !unresolved.length) return null;
    return { key: conv.key, groups, sceneLinks, confidence, hasOrderGap, unresolved,
      optionCount: groups.reduce((total, group) => total + group.options.length, 0) };
  }

  function boundaryLabel(boundary, sourceKind) {
    return boundary === "direct" ? (sourceKind === "sns" ? ui("Authored content reference", "原始内容引用") : ui("Source graph", "来源图"))
      : boundary === "manual" ? ui("Manual override", "手动覆盖") : ui("Recovered placement", "恢复的位置");
  }

  function defaultUrl(key, language, lineId, cid) {
    const url = new URL(window.location.href);
    url.search = "";
    if (language) url.searchParams.set("lang", language);
    url.searchParams.set("story", key);
    if (lineId) url.searchParams.set("line", lineId);
    if (cid != null) url.searchParams.set("cid", cid);
    url.hash = "story";
    return url.href;
  }

  // Returns a new detached <details> or null. Appending it to the conversation's
  // fresh fragment means scene switches need no teardown and cannot leave stale
  // branches behind. Optional navigate receives {key, lineId, cid}.
  function render(conv, options = {}) {
    const model = buildModel(conv, options);
    if (!model) return null;
    const container = document.createElement("details");
    container.className = "story-branch-overview";
    const navigation = [];
    const jump = (key, label = key, lineId = "", cid = null) => {
      const index = navigation.push({ key, lineId, cid }) - 1;
      return `<a href="${esc(defaultUrl(key, options.language, lineId, cid))}" data-branch-jump="${index}">${esc(label)}</a>`;
    };
    const outcomes = {
      nextOptionPrompt: ui("Next choice prompt", "后续选项提示"), sameSceneMenuLoop: ui("Returns to a menu", "返回菜单"),
      terminalOnly: ui("Source graph ends", "来源图结束"),
    };
    container.innerHTML = `<summary>${ui("Branch overview", "分支概览")} <span>${model.optionCount} ${ui("choices", "个选项")}</span></summary>
      <p class="story-branch-boundary">${ui("These are local recovered routes. Connections across source files and a complete playthrough order may remain unresolved.", "此处展示已恢复的局部路线。不同来源文件之间的连接及完整游玩顺序仍可能未解析。")}</p>
      <div class="story-branch-groups">${model.groups.map((group) => `<section class="story-branch-group">
        <header><span class="story-branch-evidence" data-boundary="${esc(group.boundary)}">${esc(boundaryLabel(group.boundary, group.sourceKind))}</span>
          <code>${esc(group.source)}</code>${group.after ? ` <span>→ ${jump(conv.key, group.after, group.after)}</span>` : ""}
          ${group.cid != null ? `<span>${ui("Content", "内容")} ${esc(group.cid)}</span>` : ""}</header>
        <ul>${group.options.map((option) => `<li><div class="story-branch-choice">
          <strong>${esc(option.label)}</strong>${option.boundary === "manual" || option.manualLabel ? `<span class="story-branch-evidence" data-boundary="manual">${esc(boundaryLabel("manual"))}</span>` : ""}
          <div class="story-branch-route"><span aria-hidden="true">↳</span>
          ${option.targets.map((key) => jump(key)).join(" <span>·</span> ")}
          ${option.lineIds.length ? `<span>${option.lineIds.length} ${ui("line(s)", "行")}</span>${jump(option.targets[0] || conv.key, ui("First line", "首行"), option.lineIds[0])}` : ""}
          ${option.cid != null ? jump(conv.key, `${ui("Content", "内容")} ${option.cid}`, "", option.cid) : ""}
          ${option.terminal ? `<span>${ui("Source graph ends", "来源图结束")}</span>` : ""}
          ${option.loop ? `<span>↻ ${ui("Menu return", "返回菜单")}</span>` : ""}
          ${!option.terminal && !option.loop && outcomes[option.outcome] ? `<span>${esc(outcomes[option.outcome])}</span>` : ""}
          ${option.unresolved ? `<span class="story-branch-unresolved">${ui("Continuation unresolved", "后续路径未解析")}</span>` : ""}
          </div><small>${esc(option.id)}</small></div></li>`).join("")}</ul>
        ${group.boundary === "structuralOnly" ? `<p class="story-branch-note">${ui("Published placement; no direct source-graph route is attached to these options.", "这是已发布的位置；这些选项未附带直接来源图路线。")}</p>` : ""}
        ${group.hint || group.risk ? `<p class="story-branch-unresolved">${ui("Sibling-scene hints or response risks remain; no extra edge is inferred here.", "仍有相邻场景提示或应答风险；此处不会据此添加连接。")}</p>` : ""}
        ${options.showDebug && (group.file || group.node) ? `<p class="story-branch-source"><code>${esc(group.file)}${group.node ? ` · node ${esc(group.node)}` : ""}</code></p>` : ""}
      </section>`).join("")}</div>
      ${model.sceneLinks.length ? `<details class="story-branch-scene-links"><summary>${ui("Related scene connections", "相关场景连接")} (${model.sceneLinks.length})</summary>
        <p>${ui("Edge types preserve their source meaning; menu availability does not establish execution order.", "连接保留其来源类型；菜单可选项不代表执行顺序。")}</p>
        <ul>${model.sceneLinks.map((edge) => `<li>${jump(edge.from)} → ${jump(edge.to)} <span>${esc(edge.kind)}</span></li>`).join("")}</ul></details>` : ""}
      ${model.hasOrderGap ? `<p class="story-branch-unresolved">${ui("Scene ordering is weak or fallback-only; its connection to the surrounding story remains unresolved.", "场景排序仅有较弱或回退证据；与前后剧情的连接仍待解析。")}</p>` : ""}
      ${!model.sceneLinks.length ? `<p class="story-branch-note">${ui("No source-backed connection to another scene is published here.", "此处未发布指向其他场景的来源支持连接。")}</p>` : ""}
      ${model.unresolved.length ? `<p class="story-branch-unresolved">${ui(`${model.unresolved.length} source-evidence gap(s) remain for this scene.`, `此场景仍有 ${model.unresolved.length} 项来源证据缺口。`)}</p>` : ""}`;
    if (typeof options.navigate === "function") container.addEventListener("click", (event) => {
      const anchor = event.target.closest("[data-branch-jump]");
      if (!anchor || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      options.navigate(navigation[Number(anchor.dataset.branchJump)]);
    });
    return container;
  }
  WebUI.storyBranches = { render, buildModel };
})();
