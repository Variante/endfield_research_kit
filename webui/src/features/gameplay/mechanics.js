// Human-readable projections of proven fields. No ID/name heuristics or runtime simulation.
(() => {
  const W = window.WebUI;
  const tr = (en, cn) => String(window.WEBUI_UI_LOCALE || "zh").startsWith("zh") ? cn : en;
  const number = (value) => Number(value.toFixed(3)).toString();
  const valid = (index, key) => index?.[key]?.status === "validated";
  const typeName = (value) => String(value || "").replace(/^Beyond\.Gameplay\.Core\./, "").split("+")[0];
  const levelOf = (skill, level) => (skill?.levels || []).find((row) => Number(row.level) === Number(level));

  function operand(input, values = new Map()) {
    if (!input || input.useCustomValue === false) return null;
    const value = input.useBlackboardKey === true ? values.get(input.blackboardKey)
      : input.useBlackboardKey === false ? input.value : null;
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  }

  function context(path) {
    // An enclosing branch is a condition, not proof that the action executes.
    const parts = [];
    if (/succeedActions|failActions|(?:^|\.)(?:succeed|fail)\b/.test(path)) parts.push(tr("conditional branch", "条件分支"));
    if (/actionOnTick/.test(path)) parts.push(tr("periodic action", "周期动作"));
    return parts.join(tr(" / ", " / "));
  }

  function disabledPaths(record) {
    return (record?.nodes || []).filter((node) => node.parameters?.isEnable === false).map((node) => node.path);
  }

  function isDisabled(path, disabled) {
    path = String(path || "").replace(/^\$\./, "");
    return disabled.some((parent) => path === parent || path.startsWith(`${parent}.`));
  }

  const projectileCallbacks = [["castSkillOnHit", "projectileSkillId"], ["castSkillOnBlock", "skillIdOnBlock"], ["castSkillOnFinish", "skillIdOnFinish"], ["castSkillOnReach", "skillIdOnReach"]];
  function callbackIds(records) {
    const ids = new Set();
    for (const record of records.values()) for (const node of record.nodes || []) {
      if (isDisabled(node.path, disabledPaths(record)) || typeName(node.type) !== "LaunchProjectile") continue;
      for (const [flag, field] of projectileCallbacks) {
        if (node.parameters?.[flag] === true) for (const ref of node.references || []) {
          if (ref.field === field && ref.resolution === "exact_id") ids.add(ref.target);
        }
      }
    }
    return [...ids].filter((id) => !records.has(id));
  }

  function damageRows(id, level, index, text, actionRecord) {
    const record = index?.skillDamageUnits?.[id];
    if (!valid(index, "skillDamageEvidence") || record?.status !== "exact") return [];
    const values = new Map((level?.blackboard || []).map((item) => [item.key, item.value]));
    const rows = [];
    for (const unit of record.units || []) {
      if (isDisabled(unit.sourcePath, disabledPaths(actionRecord))) continue;
      const type = unit.damageType?.name;
      const translated = type && text(`damage${type}`);
      const damage = translated && translated !== `damage${type}` ? translated : tr("Damage", "伤害");
      const scope = context(unit.sourcePath || "");
      if (unit.damageAttributeType?.name === "Hp") {
        const calc = unit.atkCalculation;
        const normal = valid(index, "skillDamageRouteEvidence") && unit.takeAtkSnapshot === false;
        const simple = normal && unit.simpleCalculation === true;
        const scaled = normal && unit.simpleCalculation === false && typeName(calc?.type) === "AtkScaleCalculation" && valid(index, "skillDamageAtkScaleEvidence");
        const breaking = normal && unit.simpleCalculation === false && typeName(calc?.type) === "BreakingAttackCalculation" && valid(index, "skillDamageBreakingAttackEvidence");
        const scale = operand(simple ? unit.atkScale : scaled || breaking ? calc?.operands?.atkScale : null, values);
        let body = scale == null ? tr("Multiplier depends on runtime values", "倍率取决于运行时参数")
          : tr(`${number(scale * 100)}% ATK multiplier`, `攻击倍率 ${number(scale * 100)}%`);
        if (breaking) {
          const multiplier = operand(calc.operands?.multiplier, values);
          body += tr(" × break-damage scalar", " × 破防受伤系数");
          body += multiplier != null ? ` × ${number(multiplier)}` : tr(" × runtime factor", " × 运行时系数");
        }
        if (!simple && !scaled && !breaking) body = tr("Damage type known; calculation unresolved", "已识别伤害类型，计算方式待解析");
        rows.push({ label: translated && translated !== `damage${type}` ? tr(`${damage} damage`, `${damage}伤害`) : damage, body, scope });
      } else if (unit.damageAttributeType?.name === "Poise") {
        const calc = unit.poiseCalculation;
        let value = null;
        if (typeName(calc?.type) === "DefiniteValueCalculation" && valid(index, "skillDamagePoiseRouteEvidence") && valid(index, "skillDamageDefiniteValueEvidence")) {
          value = operand(calc.operands?.value, values);
          if (calc.scalars?.applyScale === true) {
            const scale = operand(calc.operands?.valueScale, values);
            value = value != null && scale != null ? value * scale : null;
          } else if (calc.scalars?.applyScale !== false) value = null;
        }
        rows.push({ label: tr("Stagger", "削韧"), body: value == null ? tr("Amount depends on runtime values", "数值取决于运行时参数") : tr(`Configured amount ${number(value)}`, `配置值 ${number(value)}`), scope });
      }
    }
    return rows;
  }

  const cosmetic = /^(PlayAnimationAction|EffectAction|PlaySoundAction|VoiceTriggerAction|CharWeaponVisibleAction|HideWeaponAction|Camera|SetFace|Facial|MotionBlur|PlayVfx|ChangeAnimation)/;
  function skillRows(group, level, { index, records = new Map(), text }) {
    const rows = [];
    const ids = [...new Set([...(group.actionSkillIds || []), ...(group.skills || []).map((skill) => skill.id)])];
    let missing = false;
    let unexplained = false;
    let unknownBuff = false;
    for (const id of ids) {
      // A child skill never borrows another skill's blackboard by proximity.
      const ownLevel = levelOf((group.skills || []).find((skill) => skill.id === id), level);
      const record = records.get(id);
      if (!record) { missing = true; continue; }
      rows.push(...damageRows(id, ownLevel, index, text, record));
      const disabled = disabledPaths(record);
      for (const node of record.nodes || []) {
        if (isDisabled(node.path, disabled)) continue;
        const type = typeName(node.type);
        const p = node.parameters || {};
        const refs = node.references || [];
        const scope = context(node.path || "");
        const add = (label, body) => rows.push({ label, body, scope });
        if (type === "LaunchProjectile") {
          const callbacks = [["castSkillOnHit", "projectileSkillId", tr("on hit", "命中")], ["castSkillOnBlock", "skillIdOnBlock", tr("on block", "被阻挡")], ["castSkillOnFinish", "skillIdOnFinish", tr("on expiry", "结束")], ["castSkillOnReach", "skillIdOnReach", tr("on arrival", "到达目标")]];
          const effects = [];
          for (const [flag, field, when] of callbacks) {
            if (p[flag] !== true) continue;
            const ref = refs.find((ref) => ref.field === field && ref.resolution === "exact_id");
            const childRecord = ref && records.get(ref.target);
            const child = childRecord && damageRows(ref.target, null, index, text, childRecord);
            const types = [...new Set((child || []).map((row) => row.label))];
            effects.push(types.length ? tr(`${when}: ${types.join(" / ")}`, `${when}后触发${types.join("、")}`) : tr(`${when}: follow-up skill`, `${when}后调用后续技能`));
          }
          add(tr("Projectile", "投射攻击"), effects.length ? tr(`Launch a projectile; ${effects.join("; ")}`, `发射投射物；${effects.join("；")}`) : tr("Launch a projectile", "发射投射物"));
        } else if (type === "CreateBuffAction") {
          const effects = refs.filter((ref) => ref.kind === "buff" && ["exact_id", "source_only"].includes(ref.resolution)).map((ref) => index?.buffs?.[ref.target]).filter(Boolean);
          const summaries = effects.flatMap((effect) => modifierRows(effect, text)).map((row) => `${row.label} ${row.body}`);
          if (summaries.length) add(tr("Apply effect", "附加效果"), [...new Set(summaries)].join(tr("; ", "；")));
          else unknownBuff = true;
        } else if (type === "SetSuperArmorAction") {
          const armor = operand(node.operands?.superArmorValue);
          const impact = operand(node.operands?.impactResistance);
          const items = [];
          if (armor != null) items.push(tr(`super armor ${number(armor)}`, `霸体值 ${number(armor)}`));
          if (impact != null) items.push(tr(`impact resistance ${number(impact)}`, `抗冲击 ${number(impact)}`));
          if (items.length) add(tr("Interruption resistance", "抗打断"), items.join(tr("; ", "，")));
        } else if (type === "AllowNextSkillAction") {
          // Permission/input housekeeping is available in debug; it is not an effect.
        } else if (type === "MoveToAction" || type === "SnapToTargetWithRangeAction") {
          add(tr("Movement", "位移"), tr("Moves toward the configured target", "向配置目标移动"));
        } else if (type === "SelfRotateAction") {
          // Routine facing changes add no useful combat explanation.
        } else if (type === "ComboCacheAction") {
          // Input buffering is not evidence of a combo being cast.
        } else if (!cosmetic.test(type) && !/Damage|IfElse|Condition|Sequence/.test(type)) {
          unexplained = true;
        }
      }
    }
    const result = compactSkillRows(rows);
    if (unknownBuff) result.push({ label: tr("Apply effect", "附加效果"), body: tr("Status application is present; its behavior still needs decoding", "已找到附加状态的动作，具体作用待解析"), muted: true });
    if (!result.length) result.push({ label: tr("Mechanics", "机制"), body: tr("No supported behavior summary yet", "暂未解析出可说明的战斗机制"), muted: true });
    if (missing || unexplained) result.push({ label: tr("Pending", "待解析"), body: missing ? tr("Some action data is unavailable", "部分动作数据暂不可用") : tr("Some action behavior is not yet explained", "仍有部分动作尚待解读"), muted: true });
    return result;
  }

  function modifierRows(record, text, statAttrLabel) {
    const rows = [];
    if (record.evidenceStatus === "unresolved") return rows;
    for (const modifier of record.attributeModifier?.attributeModifiers || []) {
      if (modifier.modifyAttributeTypeName !== "Specific") continue;
      const value = operand(modifier.param);
      const label = statAttrLabel ? statAttrLabel({ type: modifier.attributeType, label: modifier.attributeTypeName }) : ({ MaxPoise: tr("Maximum stagger", "韧性上限") })[modifier.attributeTypeName];
      if (!label || /^Attr \d+$/.test(label) || value == null) continue;
      const formula = modifier.formulaItemName;
      const body = formula === "Addition" ? `${value >= 0 ? "+" : ""}${number(value)}`
        : formula === "Multiply" ? `×${number(value)}` : "";
      if (body) rows.push({ label, body });
    }
    return rows;
  }

  function buffRows(record, { text, statAttrLabel, decodedActions }) {
    const rows = modifierRows(record, text, statAttrLabel);
    const events = { OnOwnerHpZero: tr("When HP reaches zero", "生命归零时"), OnTakeDamage: tr("When taking damage", "受到伤害时"), OnBeforeCastSkill: tr("Before casting", "施放技能前"), OnSkillEnd: tr("When a skill ends", "技能结束时"), OnAfterOutputWeaknessTriggered: tr("After triggering weakness", "触发弱点后") };
    let unresolved = false;
    for (const event of record.abilityEventActions || []) {
      const label = events[event.abilityEventName] || tr("Event response", "事件响应");
      for (const sequence of event.actions || []) {
        for (const { decoded: d, branch } of decodedActions(sequence)) {
          if (d.prefix?.isEnable === false) continue;
          let body = "";
          const value = operand(d.value);
          const compare = { 0: "<", 1: "≤", 2: ">", 3: "≥", 4: "=" }[d.compareType];
          switch (d.semanticStatus) {
            case "exact-super-armor-condition": body = value != null && compare ? tr(`Checks super armor ${compare} ${number(value)}`, `检查霸体值 ${compare} ${number(value)}`) : tr("Checks a super-armor threshold supplied at runtime", "按运行时阈值检查霸体状态"); break;
            case "exact-main-character-target-condition": body = tr("Checks whether the target is the controlled character", "检查目标是否为主控角色"); break;
            case "exact-hp-condition": body = value != null && compare && !d.isRatio ? tr(`Checks HP ${compare} ${number(value)}`, `检查生命值 ${compare} ${number(value)}`) : tr("Checks an HP threshold", "检查生命阈值"); break;
            case "exact-poise-value-condition": body = value != null && compare ? tr(`Checks stagger ${compare} ${number(value)}`, `检查韧性值 ${compare} ${number(value)}`) : tr("Checks a stagger threshold", "检查韧性阈值"); break;
            case "exact-create-timed-marker-action": {
              const duration = operand(d.duration);
              body = duration != null ? tr(`Creates a ${number(duration)} s timed marker`, `设置持续 ${number(duration)} 秒的临时标记`) : tr("Creates a timed marker; duration depends on runtime values", "设置临时标记，时长取决于运行时参数"); break;
            }
            case "exact-cast-skill-action": body = tr("Calls another skill", "调用后续技能"); break;
            case "exact-finish-buff-action": case "exact-finish-buff-advanced-action": body = tr("Ends the selected effects", "结束指定附加效果"); break;
            case "exact-skill-cooldown-operation": {
              const operation = d.functionTypeName === "Reduce" ? tr("Reduces skill cooldown", "缩短技能冷却") : d.functionTypeName === "Set" ? tr("Sets skill cooldown", "设置技能冷却") : "";
              body = operation && value != null && !d.isPercentage ? `${operation} ${number(value)} ${tr("s", "秒")}` : operation; break;
            }
            case "exact-if-else-action": continue;
            default: unresolved = true;
          }
          if (body) rows.push({ label, body, scope: context(branch || "") });
        }
      }
    }
    if (record.lifeType?.name === "Infinity") rows.push({ label: tr("Duration", "持续"), body: tr("No fixed expiry", "无固定结束时间") });
    if (record.lifeType?.name === "Limited") {
      const duration = operand(record.duration);
      rows.push({ label: tr("Duration", "持续"), body: duration == null ? tr("Determined at runtime", "由运行时参数决定") : `${number(duration)} ${tr("s", "秒")}` });
    }
    if (!rows.length || unresolved) rows.push({ label: tr("Pending", "待解析"), body: tr("Some effect behavior remains unresolved", "部分效果或触发关系尚未解析"), muted: true });
    return compact(rows);
  }

  function decodedBuffActions(sequence, branch = "") {
    const rows = [];
    for (const item of sequence?.actionDataItems || []) {
      const decoded = item.decoded || {};
      if (decoded.prefix?.isEnable === false || decoded.members?.isEnable === false) continue;
      rows.push({ decoded, branch });
      // Unknown containers cannot establish which payload belongs to a branch.
      if (decoded.semanticStatus !== "exact-if-else-action") continue;
      for (const [field, label] of [["conditionAction", "condition"], ["failActions", "fail"], ["succeedActions", "succeed"]]) {
        rows.push(...decodedBuffActions(decoded[field], branch ? `${branch}.${label}` : label));
      }
    }
    return rows;
  }

  function compact(rows) {
    const result = new Map();
    for (const row of rows) {
      const key = `${row.label}\n${row.scope || ""}\n${!!row.muted}`;
      if (!result.has(key)) result.set(key, { ...row, values: new Set() });
      for (const phrase of row.body.split(tr("; ", "；"))) result.get(key).values.add(phrase);
    }
    return [...result.values()].map(({ values, ...row }) => ({ ...row, body: [...values].join(tr("; ", "；")) }));
  }

  function compactSkillRows(rows) {
    // Merge the same fact across branches without implying a hit count or order.
    const facts = new Map();
    for (const row of rows) {
      const key = `${row.label}\n${row.body}`;
      if (!facts.has(key)) facts.set(key, { ...row, scopes: new Set() });
      if (row.scope) facts.get(key).scopes.add(row.scope);
    }
    return compact([...facts.values()].map(({ scopes, ...row }) => ({ ...row, scope: "", body: `${row.body}${scopes.size ? tr(` (includes ${[...scopes].join(" / ")})`, `（含${[...scopes].join("、")}）`) : ""}` })));
  }

  // This audit checks individual fields mentioned in the description. A matching
  // damage type does not validate its target, trigger, duration or the whole text.
  function descriptionAudit(group, level, { index, records = new Map(), text }) {
    const description = group.descriptionTemplate || group.description || "";
    const ids = new Set([...(group.actionSkillIds || []), ...(group.skills || []).map((skill) => skill.id)]);
    const directIds = new Set(ids);
    for (const id of directIds) {
      const record = records.get(id);
      for (const node of record?.nodes || []) {
        if (isDisabled(node.path, disabledPaths(record)) || typeName(node.type) !== "LaunchProjectile") continue;
        for (const [flag, field] of [["castSkillOnHit", "projectileSkillId"], ["castSkillOnBlock", "skillIdOnBlock"], ["castSkillOnFinish", "skillIdOnFinish"], ["castSkillOnReach", "skillIdOnReach"]]) {
          if (node.parameters?.[flag] === true) {
            for (const ref of node.references || []) if (ref.field === field && ref.resolution === "exact_id") ids.add(ref.target);
          }
        }
      }
    }
    const units = [];
    if (valid(index, "skillDamageEvidence")) for (const id of ids) {
      const record = index.skillDamageUnits?.[id];
      if (record?.status !== "exact" || !records.has(id)) continue;
      for (const unit of record.units || []) {
        if (!isDisabled(unit.sourcePath, disabledPaths(records.get(id)))) units.push({ id, unit });
      }
    }
    const checks = [];
    const damageTypes = [[/物理伤害|physical damage/i, "Physical"], [/灼热伤害|heat damage|fire damage/i, "Fire"], [/寒冷伤害|cryo damage/i, "Cryst"], [/电磁伤害|electric damage/i, "Pulse"], [/自然伤害|nature damage/i, "Natural"]];
    for (const [pattern, name] of damageTypes) {
      if (!pattern.test(description)) continue;
      const evidence = units.filter(({ unit }) => unit.damageAttributeType?.name === "Hp" && unit.damageType?.name === name).map(({ id, unit }) => ({ skillId: id, path: unit.sourcePath }));
      checks.push({ status: evidence.length ? "supported" : "unverified", label: tr(`${text(`damage${name}`)} damage type`, `${text(`damage${name}`)}伤害类型`), evidence });
    }
    // Tie a numeric comparison to the exact placeholder and the same skill's
    // selected-level blackboard. Never compare a group total to an arbitrary hit.
    const tokens = description.matchAll(/\{([^{}:]+):([^{}]*)\}([^{}\n。；]{0,14})/g);
    for (const [, key, format, after] of tokens) {
      if (!/^(?:点)?(?:失衡|韧性)|^\s*(?:stagger|poise)/i.test(after)) continue;
      const skill = (group.skills || []).find((skill) => levelOf(skill, level)?.blackboard?.some((item) => item.key === key));
      const ownLevel = levelOf(skill, level);
      const values = new Map((ownLevel?.blackboard || []).map((item) => [item.key, item.value]));
      const described = values.get(key);
      const matches = units.filter(({ id, unit }) => id === skill?.id && unit.damageAttributeType?.name === "Poise" && unit.poiseCalculation?.operands?.value?.useBlackboardKey === true && unit.poiseCalculation.operands.value.blackboardKey === key);
      const observed = [];
      if (valid(index, "skillDamagePoiseRouteEvidence") && valid(index, "skillDamageDefiniteValueEvidence")) for (const { unit } of matches) {
        const calc = unit.poiseCalculation;
        if (typeName(calc.type) !== "DefiniteValueCalculation") continue;
        const base = operand(calc.operands.value, values);
        const scale = calc.scalars?.applyScale === false ? 1 : calc.scalars?.applyScale === true ? operand(calc.operands.valueScale, values) : null;
        if (base != null && scale != null) observed.push(base * scale);
      }
      const actual = [...new Set(observed)];
      const decimals = (format.match(/0\.(0+)/)?.[1] || "").length;
      const comparable = typeof described === "number" && actual.length === 1;
      const same = comparable && actual[0].toFixed(decimals) === described.toFixed(decimals);
      checks.push({ status: comparable ? same ? "supported" : "review" : "unverified", label: tr("Stagger amount", "失衡数值"), described,
        actual, evidence: matches.map(({ id, unit }) => ({ skillId: id, path: unit.sourcePath, key })) });
    }
    const otherClaims = [[/冻结|frozen|freez/i, "Freeze", "冻结"], [/燃烧|burn/i, "Burn", "燃烧"], [/腐蚀|corrosion/i, "Corrosion", "腐蚀"], [/暴击率|crit(?:ical)? rate/i, "Critical rate", "暴击率"], [/暴击伤害|crit(?:ical)? damage/i, "Critical damage", "暴击伤害"], [/牵引|拉拽|pull/i, "Pull", "牵引"], [/反弹|reflect/i, "Reflection", "反弹"], [/终结技.{0,5}能量|ultimate energy/i, "Ultimate energy", "终结技能量"], [/恢复.{0,5}技力|recover.{0,12}SP/i, "SP recovery", "技力恢复"], [/附着|infliction/i, "Infliction", "附着"], [/形态|stance/i, "Stance changes", "形态切换"]];
    for (const [pattern, en, cn] of otherClaims) if (pattern.test(description)) checks.push({ status: "unverified", label: tr(en, cn), evidence: [] });
    return checks;
  }

  function auditMarkup(checks) {
    const esc = W.escapeHtml;
    const supported = checks.filter((check) => check.status === "supported").map((check) => check.label);
    const unverified = checks.filter((check) => check.status === "unverified").map((check) => check.label);
    const review = checks.filter((check) => check.status === "review");
    const rows = [];
    if (supported.length) rows.push({ label: tr("Field support", "字段支持"), body: [...new Set(supported)].join(tr(", ", "、")) });
    if (unverified.length) rows.push({ label: tr("Unverified", "尚未验证"), body: [...new Set(unverified)].join(tr(", ", "、")), muted: true });
    for (const check of review) rows.push({ label: tr("Check value", "数值待核对"), body: tr(`${check.label}: description ${number(check.described)}, parsed calculation ${check.actual.map(number).join(" / ")}`, `${check.label}：文案 ${number(check.described)}，解析计算 ${check.actual.map(number).join(" / ")}`) });
    const note = supported.length ? tr("Support covers these fields only; targets and activation conditions still need verification.", "仅支持列出的字段，目标与触发条件仍需核对。") : tr("The description has not been verified against the implementation.", "说明中的效果尚未与实现完整对应。 ");
    return `<div class="gameplay-description-audit${review.length ? " has-review" : ""}"><span class="gameplay-caption">${esc(tr("Description check", "说明核对"))}</span>${markup(rows)}<p class="gameplay-audit-note">${esc(note)}</p></div>`;
  }

  function markup(rows) {
    const esc = W.escapeHtml;
    return `<dl class="gameplay-mechanic-list">${rows.map((row) => `<div class="gameplay-mechanic-row${row.muted ? " is-pending" : ""}"><dt>${esc(row.label)}</dt><dd>${row.scope ? `<span class="gameplay-mechanic-context">${esc(row.scope)}</span>` : ""}${esc(row.body)}</dd></div>`).join("")}</dl>`;
  }

  W.gameplayMechanics = { operand, damageRows, callbackIds, skillRows, buffRows, decodedBuffActions, descriptionAudit, auditMarkup, markup };
})();
