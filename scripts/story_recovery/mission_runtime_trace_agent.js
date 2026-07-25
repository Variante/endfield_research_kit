"use strict";

// Replaced by capture_mission_runtime_trace.py before this agent is loaded.
const CONFIG = __MISSION_TRACE_CONFIG__;

const gameAssembly = Process.getModuleByName(CONFIG.moduleName);
const chainStacks = new Map();
const actionStacks = new Map();
const playbackStacks = new Map();
const taskStacks = new Map();
const questToMission = new Map();
const snsRequestStacks = new Map();
const snsContextsByQueueItem = new Map();
const snsContextsByBrain = new Map();
const dialogRequestStacks = new Map();
const dialogContextsByQueueItem = new Map();
const dialogConsumerStacks = new Map();
const hookStats = {};
let chainCounter = 0;
let snsContextCounter = 0;
let dialogContextCounter = 0;

function rva(value) {
  return gameAssembly.base.add(parseInt(String(value), 16));
}

function currentThreadId() {
  return Process.getCurrentThreadId();
}

function stackFor(table, threadId) {
  let stack = table.get(threadId);
  if (!stack) {
    stack = [];
    table.set(threadId, stack);
  }
  return stack;
}

function top(table, threadId) {
  const stack = table.get(threadId);
  return stack && stack.length ? stack[stack.length - 1] : null;
}

function transmit(channel, payload) {
  send({ channel, ...payload });
}

function diagnostic(kind, values = {}) {
  transmit("diagnostic", { diagnostic: { kind, ...values } });
}

function event(kind, values = {}) {
  transmit("event", { event: { kind, threadId: currentThreadId(), ...values } });
}

function exported(name) {
  try {
    return gameAssembly.getExportByName(name);
  } catch (_) {
    return Module.getGlobalExportByName(name);
  }
}

const il2cppStringLength = new NativeFunction(
  exported("il2cpp_string_length"),
  "int",
  ["pointer"],
);
const il2cppStringChars = new NativeFunction(
  exported("il2cpp_string_chars"),
  "pointer",
  ["pointer"],
);

function readIl2CppString(value) {
  try {
    if (!value || value.isNull()) return "";
    const length = il2cppStringLength(value);
    if (length < 0 || length > 16384) return "";
    const chars = il2cppStringChars(value);
    if (!chars || chars.isNull()) return "";
    return chars.readUtf16String(length) || "";
  } catch (_) {
    return "";
  }
}

function readU64Argument(value) {
  try {
    return value.toUInt64().toString();
  } catch (_) {
    return "";
  }
}

function readU64Field(value, offset) {
  try {
    if (!value || value.isNull()) return "";
    return value.add(parseInt(String(offset), 16)).readU64().toString();
  } catch (_) {
    return "";
  }
}

function readInt32Field(value, offset) {
  try {
    if (!value || value.isNull()) return null;
    return value.add(parseInt(String(offset), 16)).readS32();
  } catch (_) {
    return null;
  }
}

function readBoolField(value, offset) {
  try {
    if (!value || value.isNull()) return null;
    return value.add(parseInt(String(offset), 16)).readU8() !== 0;
  } catch (_) {
    return null;
  }
}

function readStringField(value, offset) {
  try {
    if (!value || value.isNull()) return "";
    return readIl2CppString(value.add(parseInt(String(offset), 16)).readPointer());
  } catch (_) {
    return "";
  }
}

function readPointerField(value, offset) {
  try {
    if (!value || value.isNull()) return null;
    const pointer = value.add(parseInt(String(offset), 16)).readPointer();
    return pointer && !pointer.isNull() ? pointer : null;
  } catch (_) {
    return null;
  }
}

function pointerKey(value) {
  return value && !value.isNull() ? String(value) : "";
}

function snapshotChain(chain) {
  if (!chain) return null;
  return {
    chainId: chain.chainId,
    levelId: chain.levelId,
    scriptId: chain.scriptId,
    eventValue: chain.eventValue,
    valid: chain.valid,
  };
}

function deleteMappedContext(table, key, context) {
  if (key && table.get(key) === context) table.delete(key);
}

function insertBoundedContext(table, key, context, maxContexts, label) {
  const prior = table.get(key);
  if (prior && prior !== context) {
    diagnostic(`${label}_pointer_reused`, {
      pointer: key,
      priorContextId: prior.contextId,
      contextId: context.contextId,
    });
  }
  table.set(key, context);
  while (table.size > maxContexts) {
    const oldestKey = table.keys().next().value;
    const oldest = table.get(oldestKey);
    table.delete(oldestKey);
    diagnostic(`${label}_context_evicted`, {
      pointer: oldestKey,
      contextId: oldest ? oldest.contextId : null,
      maxContexts,
    });
  }
}

function attachHook(name, address, handlers) {
  try {
    Interceptor.attach(address, handlers);
    hookStats[name] = "attached";
  } catch (error) {
    hookStats[name] = `failed: ${error}`;
    diagnostic("hook_attach_failed", { name, address: String(address), error: String(error) });
  }
}

const levelHooks = CONFIG.hooks.levelScript;
const getLevelId = new NativeFunction(rva(levelHooks.getLevelId.rva), "pointer", ["pointer"]);
const getScriptId = new NativeFunction(rva(levelHooks.getScriptId.rva), "pointer", ["pointer"]);

attachHook(
  "LevelScriptRuntime._RaiseOnScriptEvent",
  rva(levelHooks.raiseOnScriptEvent.rva),
  {
    onEnter(args) {
      const threadId = currentThreadId();
      const runtime = args[0];
      const eventValue = args[1].toInt32();
      const levelId = readIl2CppString(getLevelId(runtime));
      const scriptId = readIl2CppString(getScriptId(runtime));
      const chainId = `dispatch-${Process.id}-${threadId}-${++chainCounter}`;
      const taskContext = top(taskStacks, threadId);
      const selector = { gameScriptEventValue: eventValue };
      if (taskContext) {
        selector.taskContext = {
          taskEvent: taskContext.taskEvent,
          direction: taskContext.direction,
          messageId: taskContext.messageId,
          sceneNumId: taskContext.sceneNumId,
          scriptId: taskContext.scriptId,
          taskId: taskContext.taskId,
          conditionId: taskContext.conditionId,
          conditionCompleted: taskContext.conditionCompleted,
          taskState: taskContext.taskState,
        };
      }
      const chain = {
        chainId,
        levelId,
        scriptId,
        eventValue,
        valid: Boolean(levelId && scriptId),
      };
      stackFor(chainStacks, threadId).push(chain);
      this.threadId = threadId;
      if (!chain.valid) {
        diagnostic("levelscript_identity_missing", {
          chainId,
          eventValue,
          levelId,
          scriptId,
        });
        return;
      }
      event("levelscript_event", {
        chainId,
        levelId,
        scriptId,
        headerLocalId: null,
        eventName: `GameScriptEvent#${eventValue}`,
        selector,
      });
    },
    onLeave() {
      const stack = chainStacks.get(this.threadId);
      if (stack && stack.length) stack.pop();
      if (stack && !stack.length) chainStacks.delete(this.threadId);
    },
  },
);

function validTaskIdentity(values, taskRequired = true) {
  return (
    values.sceneNumId !== null &&
    values.sceneNumId >= 0 &&
    Boolean(values.scriptId) &&
    (!taskRequired || Boolean(values.taskId))
  );
}

function emitTaskEvent(values) {
  event("levelscript_task", values);
}

function pushTaskContext(values) {
  const threadId = currentThreadId();
  stackFor(taskStacks, threadId).push(values);
  return threadId;
}

function popTaskContext(threadId) {
  const stack = taskStacks.get(threadId);
  if (stack && stack.length) stack.pop();
  if (stack && !stack.length) taskStacks.delete(threadId);
}

const taskHooks = CONFIG.hooks.levelScriptTask;
attachHook(
  taskHooks.conditionResultChanged.symbol,
  rva(taskHooks.conditionResultChanged.rva),
  {
    onEnter(args) {
      const target = args[0];
      const offsets = taskHooks.conditionResultChanged.fieldOffsets;
      const values = {
        taskEvent: "condition_result_changed",
        direction: "client_local",
        messageId: null,
        sceneNumId: readInt32Field(target, offsets.sceneNumId),
        scriptId: readU64Field(target, offsets.scriptId),
        taskId: readStringField(target, offsets.taskId),
        conditionId: readStringField(target, offsets.conditionId),
        conditionResult: args[1].toInt32() !== 0,
        sourceHook: taskHooks.conditionResultChanged.symbol,
      };
      this.threadId = pushTaskContext(values);
      if (!validTaskIdentity(values) || !values.conditionId) {
        diagnostic("levelscript_task_identity_missing", values);
        return;
      }
      emitTaskEvent(values);
    },
    onLeave() {
      popTaskContext(this.threadId);
    },
  },
);

attachHook(
  taskHooks.sendProgress.symbol,
  rva(taskHooks.sendProgress.rva),
  {
    onEnter(args) {
      const values = {
        taskEvent: "objective_progress_send",
        direction: "client_to_server",
        messageId: taskHooks.sendProgress.messageId,
        message: taskHooks.sendProgress.message,
        sceneNumId: args[2].toInt32(),
        scriptId: readU64Argument(args[1]),
        taskId: readIl2CppString(args[3]),
        conditionId: readIl2CppString(args[4]),
        progress: args[5].toInt32(),
        sourceHook: taskHooks.sendProgress.symbol,
      };
      if (!validTaskIdentity(values) || !values.conditionId) {
        diagnostic("levelscript_task_send_identity_missing", values);
        return;
      }
      emitTaskEvent(values);
    },
  },
);

function attachInboundTaskHook(config, taskEvent, extraReader = null, taskRequired = true) {
  attachHook(config.symbol, rva(config.rva), {
    onEnter(args) {
      const message = args[1];
      const offsets = config.fieldOffsets;
      const values = {
        taskEvent,
        direction: "server_to_client",
        messageId: config.messageId,
        message: config.message,
        sceneNumId: readInt32Field(message, offsets.sceneNumId),
        scriptId: readU64Field(message, offsets.scriptId),
        taskId: offsets.taskId ? readStringField(message, offsets.taskId) : null,
        sourceHook: config.symbol,
      };
      if (extraReader) extraReader(values, message, offsets);
      this.threadId = pushTaskContext(values);
      if (!validTaskIdentity(values, taskRequired)) {
        diagnostic("levelscript_task_message_identity_missing", values);
        return;
      }
      emitTaskEvent(values);
    },
    onLeave() {
      popTaskContext(this.threadId);
    },
  });
}

attachInboundTaskHook(
  taskHooks.stateUpdate,
  "state_update",
  (values, message, offsets) => {
    values.taskState = readInt32Field(message, offsets.taskState);
  },
);
attachInboundTaskHook(
  taskHooks.progressUpdate,
  "progress_update",
  (values) => {
    values.conditionMapCaptured = false;
  },
);
attachHook(
  taskHooks.conditionCompletionChanged.symbol,
  rva(taskHooks.conditionCompletionChanged.rva),
  {
    onEnter(args) {
      this.threadId = null;
      const parent = top(taskStacks, currentThreadId());
      if (!parent || parent.taskEvent !== "progress_update" || parent.messageId !== 815) return;
      const target = args[0];
      const offsets = taskHooks.conditionCompletionChanged.fieldOffsets;
      const values = {
        taskEvent: "condition_completion_applied",
        direction: "server_to_client",
        messageId: parent.messageId,
        message: parent.message,
        sceneNumId: readInt32Field(target, offsets.sceneNumId),
        scriptId: readU64Field(target, offsets.scriptId),
        taskId: readStringField(target, offsets.taskId),
        conditionId: readStringField(target, offsets.conditionId),
        conditionCompleted: readBoolField(target, offsets.isCompleted),
        sourceHook: taskHooks.conditionCompletionChanged.symbol,
      };
      if (
        !validTaskIdentity(values) ||
        !values.conditionId ||
        values.conditionCompleted === null
      ) {
        diagnostic("levelscript_task_completion_identity_missing", values);
        return;
      }
      if (
        values.sceneNumId !== parent.sceneNumId ||
        values.scriptId !== parent.scriptId ||
        values.taskId !== parent.taskId
      ) {
        diagnostic("levelscript_task_completion_parent_mismatch", {
          ...values,
          parentSceneNumId: parent.sceneNumId,
          parentScriptId: parent.scriptId,
          parentTaskId: parent.taskId,
        });
        return;
      }
      this.threadId = pushTaskContext(values);
      emitTaskEvent(values);
    },
    onLeave() {
      if (this.threadId !== null) popTaskContext(this.threadId);
    },
  },
);
attachInboundTaskHook(taskHooks.startFinish, "start_finish");
attachInboundTaskHook(taskHooks.scriptSetDone, "script_set_done", null, false);

const dispatchHooks = CONFIG.hooks.actionDispatch;
attachHook(
  "ActionHeader.Process",
  rva(dispatchHooks.actionHeaderProcess.rva),
  {
    onEnter() {
      const chain = top(chainStacks, currentThreadId());
      if (chain) chain.actionHeaderProcessCount = (chain.actionHeaderProcessCount || 0) + 1;
    },
  },
);
attachHook(
  "ActionHeader.DoProcess",
  rva(dispatchHooks.actionHeaderDoProcess.rva),
  {
    onEnter() {
      const chain = top(chainStacks, currentThreadId());
      if (chain) chain.actionHeaderDoProcessCount = (chain.actionHeaderDoProcessCount || 0) + 1;
    },
  },
);
attachHook(
  "ActionMapAsset.RunAction",
  rva(dispatchHooks.runAction.rva),
  {
    onEnter(args) {
      const threadId = currentThreadId();
      const actionLocalId = args[1].toInt32();
      stackFor(actionStacks, threadId).push(actionLocalId >= 0 ? actionLocalId : null);
      this.threadId = threadId;
    },
    onLeave() {
      const stack = actionStacks.get(this.threadId);
      if (stack && stack.length) stack.pop();
      if (stack && !stack.length) actionStacks.delete(this.threadId);
    },
  },
);

function matchesStoryKey(value, prefixes) {
  return Boolean(value) && prefixes.some((prefix) => value.startsWith(prefix));
}

function resolvePlaybackStoryKey(value, config) {
  if (config.keyMap) {
    const keyMap = (CONFIG.hooks.playbackKeyMaps || {})[config.keyMap] || {};
    const mapped = Object.prototype.hasOwnProperty.call(keyMap, value)
      ? keyMap[value]
      : "";
    return matchesStoryKey(mapped, config.prefixes) ? mapped : "";
  }
  return matchesStoryKey(value, config.prefixes) ? value : "";
}

function emitPlayback(pending, storyKey) {
  if (pending.emitted) return;
  pending.emitted = true;
  const chain = pending.chain && pending.chain.valid ? pending.chain : null;
  if (chain && pending.actionLocalId !== null) {
    event("action_enter", {
      chainId: chain.chainId,
      levelId: chain.levelId,
      scriptId: chain.scriptId,
      headerLocalId: null,
      actionLocalId: pending.actionLocalId,
      actionType: pending.config.actionType,
    });
  }
  const values = {
    chainId: chain ? chain.chainId : null,
    storyKey,
    playbackType: pending.config.playbackType,
    actionType: pending.config.actionType,
  };
  if (chain) {
    values.levelId = chain.levelId;
    values.scriptId = chain.scriptId;
    values.headerLocalId = null;
  }
  if (pending.actionLocalId !== null) values.actionLocalId = pending.actionLocalId;
  event("story_playback", values);
}

for (const playback of CONFIG.hooks.playback) {
  attachHook(playback.symbol || playback.actionType, rva(playback.rva), {
    onEnter() {
      const threadId = currentThreadId();
      const pending = {
        config: playback,
        chain: top(chainStacks, threadId),
        actionLocalId: top(actionStacks, threadId),
        strings: [],
        resolvedStoryKey: "",
        deferredStoryKeyAmbiguous: false,
        deferredRequestSeen: false,
        emitted: false,
      };
      stackFor(playbackStacks, threadId).push(pending);
      this.threadId = threadId;
      this.pending = pending;
    },
    onLeave() {
      if (this.pending.config.deferToAcceptedPlayback) {
        if (
          !this.pending.resolvedStoryKey
          || this.pending.deferredStoryKeyAmbiguous
        ) {
          diagnostic("deferred_playback_story_key_invalid", {
            actionType: this.pending.config.actionType,
            deferToAcceptedPlayback:
              this.pending.config.deferToAcceptedPlayback,
            observedStrings: this.pending.strings,
            resolvedStoryKey: this.pending.resolvedStoryKey || null,
            ambiguous: this.pending.deferredStoryKeyAmbiguous,
            chainId: this.pending.chain
              ? this.pending.chain.chainId
              : null,
            actionLocalId: this.pending.actionLocalId,
          });
        } else if (!this.pending.deferredRequestSeen) {
          diagnostic("deferred_playback_request_missing", {
            actionType: this.pending.config.actionType,
            deferToAcceptedPlayback:
              this.pending.config.deferToAcceptedPlayback,
            storyKey: this.pending.resolvedStoryKey,
            chainId: this.pending.chain
              ? this.pending.chain.chainId
              : null,
            actionLocalId: this.pending.actionLocalId,
          });
        }
      } else if (!this.pending.emitted) {
        diagnostic("playback_story_key_missing", {
          actionType: this.pending.config.actionType,
          keySource: this.pending.config.keySource || "paramString",
          keyMap: this.pending.config.keyMap || null,
          prefixes: this.pending.config.prefixes,
          observedStrings: this.pending.strings,
          chainId: this.pending.chain ? this.pending.chain.chainId : null,
          actionLocalId: this.pending.actionLocalId,
        });
      }
      const stack = playbackStacks.get(this.threadId);
      if (stack && stack.length) stack.pop();
      if (stack && !stack.length) playbackStacks.delete(this.threadId);
    },
  });
}

const maskPlayback = CONFIG.hooks.maskPlaybackBoundary;
if (maskPlayback) {
  attachHook(maskPlayback.symbol, rva(maskPlayback.rva), {
    onEnter(args) {
      const threadId = currentThreadId();
      const pending = top(playbackStacks, threadId);
      if (!pending || pending.config.keySource !== maskPlayback.keySource) {
        diagnostic("black_playback_without_action_context", {
          sourceHook: maskPlayback.symbol,
          pendingActionType: pending ? pending.config.actionType : null,
          pendingKeySource: pending ? pending.config.keySource || "paramString" : null,
          chainId: top(chainStacks, threadId)?.chainId || null,
          actionLocalId: top(actionStacks, threadId),
        });
        return;
      }

      const data = args[0];
      const textList = readPointerField(data, maskPlayback.dataTextListFieldOffset);
      const size = textList
        ? readInt32Field(textList, maskPlayback.listSizeFieldOffset)
        : null;
      const items = textList
        ? readPointerField(textList, maskPlayback.listItemsFieldOffset)
        : null;
      if (
        size === null ||
        size < 1 ||
        size > maskPlayback.maxTextItems ||
        !items
      ) {
        diagnostic("black_playback_text_list_invalid", {
          actionType: pending.config.actionType,
          textItemCount: size,
          hasTextList: Boolean(textList),
          hasItems: Boolean(items),
          chainId: pending.chain ? pending.chain.chainId : null,
          actionLocalId: pending.actionLocalId,
        });
        return;
      }

      const linePattern = new RegExp(maskPlayback.lineIdPattern);
      const suffixPattern = new RegExp(maskPlayback.lineSuffixPattern);
      const lineIds = [];
      const storyKeys = new Set();
      for (let index = 0; index < size; index += 1) {
        let item = null;
        try {
          item = items
            .add(parseInt(String(maskPlayback.arrayDataOffset), 16) + index * Process.pointerSize)
            .readPointer();
        } catch (_) {
          item = null;
        }
        const lineId = item && !item.isNull()
          ? readStringField(item, maskPlayback.lineKeyFieldOffset)
          : "";
        lineIds.push(lineId);
        if (!linePattern.test(lineId)) {
          diagnostic("black_playback_line_id_invalid", {
            actionType: pending.config.actionType,
            textItemCount: size,
            lineIndex: index,
            observedLineIds: lineIds,
            chainId: pending.chain ? pending.chain.chainId : null,
            actionLocalId: pending.actionLocalId,
          });
          return;
        }
        storyKeys.add(lineId.replace(suffixPattern, ""));
      }

      if (storyKeys.size !== 1) {
        diagnostic("black_playback_story_key_ambiguous", {
          actionType: pending.config.actionType,
          observedLineIds: lineIds,
          normalizedStoryKeys: Array.from(storyKeys),
          chainId: pending.chain ? pending.chain.chainId : null,
          actionLocalId: pending.actionLocalId,
        });
        return;
      }
      const storyKey = Array.from(storyKeys)[0];
      if (!matchesStoryKey(storyKey, pending.config.prefixes)) {
        diagnostic("black_playback_story_key_invalid", {
          actionType: pending.config.actionType,
          observedLineIds: lineIds,
          normalizedStoryKey: storyKey,
          prefixes: pending.config.prefixes,
          chainId: pending.chain ? pending.chain.chainId : null,
          actionLocalId: pending.actionLocalId,
        });
        return;
      }
      pending.strings.push(...lineIds);
      emitPlayback(pending, storyKey);
    },
  });
}

const asyncSns = CONFIG.hooks.asyncSnsPlayback;
if (asyncSns) {
  attachHook(asyncSns.request.symbol, rva(asyncSns.request.rva), {
    onEnter(args) {
      const threadId = currentThreadId();
      const chatId = readIl2CppString(args[0]);
      const storyKey = readIl2CppString(args[1]);
      const request = {
        contextId: `sns-${Process.id}-${++snsContextCounter}`,
        config: asyncSns,
        chain: snapshotChain(top(chainStacks, threadId)),
        actionLocalId: top(actionStacks, threadId),
        chatId,
        storyKey,
        showToast: args[2].toInt32() !== 0,
        queueItemKey: "",
        queueItemKeys: [],
        context: null,
        invalid: false,
      };
      stackFor(snsRequestStacks, threadId).push(request);
      this.threadId = threadId;
      this.request = request;
      if (!chatId || !matchesStoryKey(storyKey, asyncSns.prefixes)) {
        diagnostic("sns_async_request_identity_invalid", {
          contextId: request.contextId,
          chatId,
          storyKey,
          prefixes: asyncSns.prefixes,
          chainId: request.chain ? request.chain.chainId : null,
          actionLocalId: request.actionLocalId,
        });
      }
    },
    onLeave(retval) {
      const accepted = retval.toInt32() !== 0;
      const request = this.request;
      if (
        accepted
        && request.chatId
        && matchesStoryKey(request.storyKey, asyncSns.prefixes)
        && !request.context
      ) {
        diagnostic("sns_async_queue_item_missing", {
          contextId: request.contextId,
          storyKey: request.storyKey,
          chatId: request.chatId,
        });
      }
      if (request.context && (!accepted || request.invalid)) {
        for (const itemKey of request.queueItemKeys) {
          deleteMappedContext(snsContextsByQueueItem, itemKey, request.context);
        }
      }
      if (
        request.context
        && accepted
        && (request.invalid || request.context.queueItemBindCount !== 1)
      ) {
        for (const itemKey of request.queueItemKeys) {
          deleteMappedContext(snsContextsByQueueItem, itemKey, request.context);
        }
        diagnostic("sns_async_queue_item_count_invalid", {
          contextId: request.contextId,
          queueItemBindCount: request.context.queueItemBindCount,
          accepted,
        });
      } else if (!accepted && request.context) {
        diagnostic("sns_async_request_rejected", {
          contextId: request.contextId,
          storyKey: request.storyKey,
          chatId: request.chatId,
        });
      }
      const stack = snsRequestStacks.get(this.threadId);
      if (stack && stack.length) stack.pop();
      if (stack && !stack.length) snsRequestStacks.delete(this.threadId);
    },
  });

  attachHook(asyncSns.queueBoundary.symbol, rva(asyncSns.queueBoundary.rva), {
    onEnter(args) {
      const request = top(snsRequestStacks, currentThreadId());
      if (!request) return;
      const item = args[0];
      const itemKey = pointerKey(item);
      if (request.queueItemKeys.length) {
        request.invalid = true;
        for (const priorKey of request.queueItemKeys) {
          deleteMappedContext(
            snsContextsByQueueItem,
            priorKey,
            request.context,
          );
        }
        diagnostic("sns_async_multiple_queue_items", {
          contextId: request.contextId,
          priorQueueItems: request.queueItemKeys,
          additionalQueueItem: itemKey || null,
        });
        return;
      }
      const itemChatId = readStringField(
        item,
        asyncSns.queueBoundary.itemChatIdFieldOffset,
      );
      const itemStoryKey = readStringField(
        item,
        asyncSns.queueBoundary.itemStoryKeyFieldOffset,
      );
      const itemShowToast = readBoolField(
        item,
        asyncSns.queueBoundary.itemShowToastFieldOffset,
      );
      if (
        !itemKey
        || !request.chatId
        || !matchesStoryKey(request.storyKey, asyncSns.prefixes)
        || itemChatId !== request.chatId
        || itemStoryKey !== request.storyKey
        || itemShowToast === null
        || itemShowToast !== request.showToast
      ) {
        diagnostic("sns_async_queue_item_identity_mismatch", {
          contextId: request.contextId,
          hasQueueItem: Boolean(itemKey),
          requestChatId: request.chatId,
          itemChatId,
          requestStoryKey: request.storyKey,
          itemStoryKey,
          requestShowToast: request.showToast,
          itemShowToast,
        });
        return;
      }
      if (!request.context) {
        request.context = {
          contextId: request.contextId,
          config: asyncSns.fieldPlayback,
          chain: request.chain,
          actionLocalId: request.actionLocalId,
          chatId: request.chatId,
          storyKey: request.storyKey,
          showToast: request.showToast,
          queueItemKey: itemKey,
          queueItemBindCount: 0,
        };
      }
      request.context.queueItemBindCount += 1;
      request.queueItemKey = itemKey;
      request.queueItemKeys.push(itemKey);
      insertBoundedContext(
        snsContextsByQueueItem,
        itemKey,
        request.context,
        asyncSns.maxPendingContexts,
        "sns_async_queue_item",
      );
    },
  });

  attachHook(asyncSns.consumer.symbol, rva(asyncSns.consumer.rva), {
    onEnter(args) {
      const brain = args[0];
      const handle = args[1];
      const item = readPointerField(
        handle,
        asyncSns.consumer.handleItemFieldOffset,
      );
      const itemKey = pointerKey(item);
      const context = itemKey ? snsContextsByQueueItem.get(itemKey) : null;
      this.brain = brain;
      this.brainKey = pointerKey(brain);
      this.itemKey = itemKey;
      this.context = context || null;
      if (!context) return;

      const itemChatId = readStringField(
        item,
        asyncSns.queueBoundary.itemChatIdFieldOffset,
      );
      const itemStoryKey = readStringField(
        item,
        asyncSns.queueBoundary.itemStoryKeyFieldOffset,
      );
      const itemShowToast = readBoolField(
        item,
        asyncSns.queueBoundary.itemShowToastFieldOffset,
      );
      if (
        !this.brainKey
        || itemChatId !== context.chatId
        || itemStoryKey !== context.storyKey
        || itemShowToast === null
        || itemShowToast !== context.showToast
      ) {
        diagnostic("sns_async_consumer_identity_mismatch", {
          contextId: context.contextId,
          hasBrain: Boolean(this.brainKey),
          itemChatId,
          expectedChatId: context.chatId,
          itemStoryKey,
          expectedStoryKey: context.storyKey,
          itemShowToast,
          expectedShowToast: context.showToast,
        });
        deleteMappedContext(snsContextsByQueueItem, itemKey, context);
        this.context = null;
      }
    },
    onLeave(retval) {
      const context = this.context;
      if (!context) return;
      deleteMappedContext(snsContextsByQueueItem, this.itemKey, context);
      const accepted = retval.toInt32() !== 0;
      const brainChatId = readStringField(
        this.brain,
        asyncSns.fieldPlayback.contextFieldOffsets.chatId,
      );
      const brainStoryKey = readStringField(
        this.brain,
        asyncSns.fieldPlayback.storyKeyFieldOffset,
      );
      if (
        !accepted
        || !this.brainKey
        || brainChatId !== context.chatId
        || brainStoryKey !== context.storyKey
      ) {
        diagnostic("sns_async_consumer_rejected", {
          contextId: context.contextId,
          accepted,
          hasBrain: Boolean(this.brainKey),
          brainChatId,
          expectedChatId: context.chatId,
          brainStoryKey,
          expectedStoryKey: context.storyKey,
        });
        return;
      }
      insertBoundedContext(
        snsContextsByBrain,
        this.brainKey,
        context,
        asyncSns.maxPendingContexts,
        "sns_async_brain",
      );
    },
  });
}

const asyncDialog = CONFIG.hooks.asyncDialogPlayback;
if (asyncDialog) {
  attachHook(asyncDialog.request.symbol, rva(asyncDialog.request.rva), {
    onEnter(args) {
      this.request = null;
      this.threadId = null;
      const threadId = currentThreadId();
      const pending = top(playbackStacks, threadId);
      if (
        !pending
        || pending.config.deferToAcceptedPlayback
          !== asyncDialog.deferToAcceptedPlayback
      ) {
        return;
      }

      const storyKey = readIl2CppString(args[0]);
      pending.deferredRequestSeen = true;
      const eligible = (
        matchesStoryKey(storyKey, asyncDialog.prefixes)
        && pending.resolvedStoryKey === storyKey
        && !pending.deferredStoryKeyAmbiguous
      );
      const request = {
        contextId: `dialog-${Process.id}-${++dialogContextCounter}`,
        pending,
        storyKey,
        eligible,
        queueItemKeys: [],
        context: null,
        invalid: false,
      };
      stackFor(dialogRequestStacks, threadId).push(request);
      this.request = request;
      this.threadId = threadId;
      if (!eligible) {
        diagnostic("dialog_async_request_identity_mismatch", {
          contextId: request.contextId,
          actionType: pending.config.actionType,
          storyKey,
          resolvedStoryKey: pending.resolvedStoryKey || null,
          ambiguous: pending.deferredStoryKeyAmbiguous,
          prefixes: asyncDialog.prefixes,
          chainId: pending.chain ? pending.chain.chainId : null,
          actionLocalId: pending.actionLocalId,
        });
      }
    },
    onLeave(retval) {
      const request = this.request;
      if (!request) return;
      const accepted = retval.toInt32() !== 0;
      if (accepted && request.eligible && !request.context) {
        diagnostic("dialog_async_queue_item_missing", {
          contextId: request.contextId,
          actionType: request.pending.config.actionType,
          storyKey: request.storyKey,
        });
      }
      if (request.context && (!accepted || request.invalid)) {
        for (const itemKey of request.queueItemKeys) {
          deleteMappedContext(
            dialogContextsByQueueItem,
            itemKey,
            request.context,
          );
        }
      }
      if (
        request.context
        && accepted
        && (request.invalid || request.context.queueItemBindCount !== 1)
      ) {
        for (const itemKey of request.queueItemKeys) {
          deleteMappedContext(
            dialogContextsByQueueItem,
            itemKey,
            request.context,
          );
        }
        diagnostic("dialog_async_queue_item_count_invalid", {
          contextId: request.contextId,
          queueItemBindCount: request.context.queueItemBindCount,
          accepted,
        });
      } else if (!accepted && request.eligible) {
        diagnostic("dialog_async_request_rejected", {
          contextId: request.contextId,
          actionType: request.pending.config.actionType,
          storyKey: request.storyKey,
        });
      }
      const stack = dialogRequestStacks.get(this.threadId);
      if (stack && stack.length) stack.pop();
      if (stack && !stack.length) dialogRequestStacks.delete(this.threadId);
    },
  });

  attachHook(asyncDialog.queueBoundary.symbol, rva(asyncDialog.queueBoundary.rva), {
    onEnter(args) {
      const request = top(dialogRequestStacks, currentThreadId());
      if (!request || !request.eligible) return;
      const item = args[0];
      const itemKey = pointerKey(item);
      if (request.queueItemKeys.length) {
        request.invalid = true;
        for (const priorKey of request.queueItemKeys) {
          deleteMappedContext(
            dialogContextsByQueueItem,
            priorKey,
            request.context,
          );
        }
        diagnostic("dialog_async_multiple_queue_items", {
          contextId: request.contextId,
          priorQueueItems: request.queueItemKeys,
          additionalQueueItem: itemKey || null,
        });
        return;
      }
      const itemStoryKey = readStringField(
        item,
        asyncDialog.queueBoundary.itemStoryKeyFieldOffset,
      );
      if (!itemKey || itemStoryKey !== request.storyKey) {
        diagnostic("dialog_async_queue_item_identity_mismatch", {
          contextId: request.contextId,
          hasQueueItem: Boolean(itemKey),
          requestStoryKey: request.storyKey,
          itemStoryKey,
        });
        return;
      }
      request.context = {
        contextId: request.contextId,
        config: request.pending.config,
        chain: snapshotChain(request.pending.chain),
        actionLocalId: request.pending.actionLocalId,
        storyKey: request.storyKey,
        queueItemKey: itemKey,
        queueItemBindCount: 1,
        sourcePending: request.pending,
        emitted: false,
      };
      request.queueItemKeys.push(itemKey);
      insertBoundedContext(
        dialogContextsByQueueItem,
        itemKey,
        request.context,
        asyncDialog.maxPendingContexts,
        "dialog_async_queue_item",
      );
    },
  });

  attachHook(asyncDialog.consumer.symbol, rva(asyncDialog.consumer.rva), {
    onEnter(args) {
      this.context = null;
      this.threadId = null;
      this.itemKey = "";
      const handle = args[1];
      const item = readPointerField(
        handle,
        asyncDialog.consumer.handleItemFieldOffset,
      );
      const itemKey = pointerKey(item);
      const context = itemKey
        ? dialogContextsByQueueItem.get(itemKey)
        : null;
      if (!context) return;
      const itemStoryKey = readStringField(
        item,
        asyncDialog.queueBoundary.itemStoryKeyFieldOffset,
      );
      if (itemStoryKey !== context.storyKey) {
        diagnostic("dialog_async_consumer_identity_mismatch", {
          contextId: context.contextId,
          itemStoryKey,
          expectedStoryKey: context.storyKey,
        });
        deleteMappedContext(dialogContextsByQueueItem, itemKey, context);
        return;
      }
      const threadId = currentThreadId();
      stackFor(dialogConsumerStacks, threadId).push(context);
      this.context = context;
      this.threadId = threadId;
      this.itemKey = itemKey;
    },
    onLeave(retval) {
      const context = this.context;
      if (!context) return;
      const stack = dialogConsumerStacks.get(this.threadId);
      if (stack && stack.length) stack.pop();
      if (stack && !stack.length) dialogConsumerStacks.delete(this.threadId);
      deleteMappedContext(
        dialogContextsByQueueItem,
        this.itemKey,
        context,
      );
      const accepted = retval.toInt32() !== 0;
      if (!accepted || !context.emitted) {
        diagnostic("dialog_async_consumer_rejected", {
          contextId: context.contextId,
          actionType: context.config.actionType,
          storyKey: context.storyKey,
          accepted,
          reachedAcceptedPlayback: context.emitted,
        });
      }
    },
  });

  attachHook(asyncDialog.acceptedPlayback.symbol, rva(asyncDialog.acceptedPlayback.rva), {
    onEnter(args) {
      const context = top(dialogConsumerStacks, currentThreadId());
      if (!context || context.emitted) return;
      const storyKey = readIl2CppString(args[1]);
      if (
        storyKey !== context.storyKey
        || !matchesStoryKey(storyKey, asyncDialog.prefixes)
      ) {
        diagnostic("dialog_async_final_identity_mismatch", {
          contextId: context.contextId,
          actionType: context.config.actionType,
          storyKey,
          expectedStoryKey: context.storyKey,
        });
        return;
      }
      context.sourcePending.emitted = true;
      emitPlayback(context, storyKey);
    },
  });
}

for (const playback of CONFIG.hooks.fieldPlayback || []) {
  attachHook(playback.actionType, rva(playback.rva), {
    onEnter(args) {
      const threadId = currentThreadId();
      const target = args[0];
      const storyKey = readStringField(target, playback.storyKeyFieldOffset);
      if (!matchesStoryKey(storyKey, playback.prefixes)) {
        const context = {};
        for (const [name, offset] of Object.entries(playback.contextFieldOffsets || {})) {
          context[name] = readStringField(target, offset);
        }
        diagnostic("playback_story_key_missing", {
          actionType: playback.actionType,
          prefixes: playback.prefixes,
          observedStrings: storyKey ? [storyKey] : [],
          context,
          chainId: top(chainStacks, threadId)?.chainId || null,
          actionLocalId: null,
        });
        return;
      }
      let propagated = null;
      if (
        asyncSns
        && playback.actionType === asyncSns.fieldPlayback.actionType
      ) {
        const brainKey = pointerKey(target);
        const candidate = brainKey ? snsContextsByBrain.get(brainKey) : null;
        if (candidate) {
          const chatId = readStringField(
            target,
            playback.contextFieldOffsets.chatId,
          );
          snsContextsByBrain.delete(brainKey);
          if (
            candidate.storyKey === storyKey
            && candidate.chatId === chatId
          ) {
            propagated = candidate;
          } else {
            diagnostic("sns_async_final_identity_mismatch", {
              contextId: candidate.contextId,
              brain: brainKey,
              storyKey,
              expectedStoryKey: candidate.storyKey,
              chatId,
              expectedChatId: candidate.chatId,
            });
          }
        }
      }
      emitPlayback({
        config: playback,
        chain: propagated ? propagated.chain : top(chainStacks, threadId),
        // This is a final subsystem/UI boundary, not an ActionMap node. An
        // asynchronous call can carry an action-local id only through the
        // exact queue-item -> handle -> brain object-identity handoff above.
        actionLocalId: propagated ? propagated.actionLocalId : null,
        emitted: false,
      }, storyKey);
    },
  });
}

attachHook(
  "Param<string>.GetValue",
  rva(dispatchHooks.paramStringGetValue.rva),
  {
    onEnter() {
      this.pending = top(playbackStacks, currentThreadId());
    },
    onLeave(retval) {
      if (!this.pending || this.pending.emitted) return;
      if ((this.pending.config.keySource || "paramString") !== "paramString") return;
      const value = readIl2CppString(retval);
      if (!value) return;
      if (this.pending.strings.length < 12) this.pending.strings.push(value);
      const storyKey = resolvePlaybackStoryKey(value, this.pending.config);
      if (!storyKey) return;
      if (this.pending.config.deferToAcceptedPlayback) {
        if (
          this.pending.resolvedStoryKey
          && this.pending.resolvedStoryKey !== storyKey
        ) {
          this.pending.deferredStoryKeyAmbiguous = true;
        } else {
          this.pending.resolvedStoryKey = storyKey;
        }
        return;
      }
      emitPlayback(this.pending, storyKey);
    },
  },
);

const missionHooks = CONFIG.hooks.mission;
attachHook(
  "MissionSystem.GetMissionIdByQuestId",
  rva(missionHooks.getMissionIdByQuestId.rva),
  {
    onEnter(args) {
      this.questId = readIl2CppString(args[1]);
    },
    onLeave(retval) {
      const missionId = readIl2CppString(retval);
      if (this.questId && missionId) questToMission.set(this.questId, missionId);
    },
  },
);

function dictionarySnapshot(dictionary, label, maxUsedCount, layout) {
  try {
    if (!dictionary || dictionary.isNull()) {
      return { ok: false, reason: `${label}_dictionary_missing` };
    }

    const entriesOffset = parseInt(String(layout.entries), 16);
    const usedCountOffset = parseInt(String(layout.usedCount), 16);
    const versionOffset = parseInt(String(layout.version), 16);
    const arrayLengthOffset = parseInt(String(layout.arrayLength), 16);
    const arrayDataOffset = parseInt(String(layout.arrayData), 16);
    const entryStride = parseInt(String(layout.entryStride), 16);
    const entryHashCodeOffset = parseInt(String(layout.entryHashCode), 16);
    const entryKeyOffset = parseInt(String(layout.entryKey), 16);
    const entryValueOffset = parseInt(String(layout.entryValue), 16);

    const usedCount = dictionary.add(usedCountOffset).readS32();
    const versionBefore = dictionary.add(versionOffset).readS32();
    if (usedCount < 0 || usedCount > maxUsedCount) {
      return {
        ok: false,
        reason: `${label}_used_count_invalid`,
        usedCount,
        maxUsedCount,
      };
    }

    const entries = dictionary.add(entriesOffset).readPointer();
    if (usedCount === 0) {
      const versionAfter = dictionary.add(versionOffset).readS32();
      if (versionAfter !== versionBefore) {
        return { ok: false, reason: `${label}_version_changed` };
      }
      return { ok: true, rows: [], usedCount, version: versionBefore };
    }
    if (!entries || entries.isNull()) {
      return { ok: false, reason: `${label}_entries_missing`, usedCount };
    }

    const arrayLength = entries.add(arrayLengthOffset).readU64().toNumber();
    if (
      !Number.isSafeInteger(arrayLength)
      || arrayLength < usedCount
      || arrayLength > maxUsedCount * 4
    ) {
      return {
        ok: false,
        reason: `${label}_array_length_invalid`,
        usedCount,
        arrayLength,
      };
    }

    const rows = [];
    const seenKeys = new Set();
    for (let index = 0; index < usedCount; index += 1) {
      const entry = entries.add(arrayDataOffset + index * entryStride);
      const hashCode = entry.add(entryHashCodeOffset).readS32();
      if (hashCode < 0) continue;

      const keyPointer = entry.add(entryKeyOffset).readPointer();
      const valuePointer = entry.add(entryValueOffset).readPointer();
      const key = readIl2CppString(keyPointer);
      if (!key || !valuePointer || valuePointer.isNull()) {
        return {
          ok: false,
          reason: `${label}_entry_identity_invalid`,
          index,
        };
      }
      if (seenKeys.has(key)) {
        return {
          ok: false,
          reason: `${label}_duplicate_key`,
          index,
          key,
        };
      }
      seenKeys.add(key);
      rows.push({ key, valuePointer });
    }

    const usedCountAfter = dictionary.add(usedCountOffset).readS32();
    const versionAfter = dictionary.add(versionOffset).readS32();
    if (usedCountAfter !== usedCount || versionAfter !== versionBefore) {
      return {
        ok: false,
        reason: `${label}_changed_during_snapshot`,
        usedCount,
        usedCountAfter,
        versionBefore,
        versionAfter,
      };
    }
    return {
      ok: true,
      rows,
      usedCount,
      version: versionBefore,
      activeEntryCount: rows.length,
    };
  } catch (error) {
    return {
      ok: false,
      reason: `${label}_read_failed`,
      error: String(error),
    };
  }
}

function dictionarySnapshotStillCurrent(dictionary, snapshot, layout) {
  try {
    if (!dictionary || dictionary.isNull() || !snapshot.ok) return false;
    const usedCount = dictionary
      .add(parseInt(String(layout.usedCount), 16))
      .readS32();
    const version = dictionary
      .add(parseInt(String(layout.version), 16))
      .readS32();
    return usedCount === snapshot.usedCount && version === snapshot.version;
  } catch (_) {
    return false;
  }
}

function buildMissionStateSnapshot(system, config) {
  try {
    if (!system || system.isNull()) {
      return { ok: false, reason: "mission_system_missing" };
    }

    const dictionaryLayout = config.dictionaryLayout;
    const systemOffsets = config.systemFieldOffsets;
    const limits = config.maxUsedCounts;
    const idMapDictionary = readPointerField(system, systemOffsets.idMap);
    const missionsDictionary = readPointerField(system, systemOffsets.missions);
    const questsDictionary = readPointerField(system, systemOffsets.currentQuests);
    const idMap = dictionarySnapshot(
      idMapDictionary,
      "id_map",
      limits.idMap,
      dictionaryLayout,
    );
    if (!idMap.ok) return idMap;
    const missions = dictionarySnapshot(
      missionsDictionary,
      "missions",
      limits.missions,
      dictionaryLayout,
    );
    if (!missions.ok) return missions;
    const quests = dictionarySnapshot(
      questsDictionary,
      "current_quests",
      limits.currentQuests,
      dictionaryLayout,
    );
    if (!quests.ok) return quests;
    if (!idMap.rows.length || !missions.rows.length) {
      return {
        ok: false,
        reason: "mission_state_dictionaries_not_ready",
        idMapEntries: idMap.rows.length,
        missionEntries: missions.rows.length,
        questEntries: quests.rows.length,
      };
    }

    const snapshotQuestToMission = new Map();
    for (const row of idMap.rows) {
      const missionId = readIl2CppString(row.valuePointer);
      if (!missionId) {
        return { ok: false, reason: "id_map_mission_id_invalid", questId: row.key };
      }
      snapshotQuestToMission.set(row.key, missionId);
    }

    const missionById = new Map();
    for (const row of missions.rows) {
      const missionId = readStringField(
        row.valuePointer,
        config.missionData.idFieldOffset,
      );
      const stateValue = readInt32Field(
        row.valuePointer,
        config.missionData.stateFieldOffset,
      );
      if (missionId !== row.key) {
        return {
          ok: false,
          reason: "mission_data_id_mismatch",
          dictionaryKey: row.key,
          dataId: missionId,
        };
      }
      if (
        stateValue === null
        || !Object.prototype.hasOwnProperty.call(config.missionData.states, String(stateValue))
      ) {
        return {
          ok: false,
          reason: "mission_state_value_invalid",
          missionId,
          stateValue,
        };
      }
      missionById.set(missionId, {
        state: config.missionData.states[String(stateValue)],
        stateValue,
      });
    }

    const questRows = [];
    for (const row of quests.rows) {
      const questId = readStringField(row.valuePointer, config.questData.idFieldOffset);
      const stateValue = readInt32Field(
        row.valuePointer,
        config.questData.stateFieldOffset,
      );
      const missionId = snapshotQuestToMission.get(row.key);
      if (questId !== row.key) {
        return {
          ok: false,
          reason: "quest_data_id_mismatch",
          dictionaryKey: row.key,
          dataId: questId,
        };
      }
      if (
        stateValue === null
        || !Object.prototype.hasOwnProperty.call(config.questData.states, String(stateValue))
      ) {
        return {
          ok: false,
          reason: "quest_state_value_invalid",
          questId,
          stateValue,
        };
      }
      if (!missionId || !missionById.has(missionId)) {
        return {
          ok: false,
          reason: "quest_mission_identity_missing",
          questId,
          missionId: missionId || "",
        };
      }
      questRows.push({
        missionId,
        questId,
        state: config.questData.states[String(stateValue)],
        stateValue,
      });
    }

    const currentIdMapDictionary = readPointerField(system, systemOffsets.idMap);
    const currentMissionsDictionary = readPointerField(system, systemOffsets.missions);
    const currentQuestsDictionary = readPointerField(
      system,
      systemOffsets.currentQuests,
    );
    if (
      !currentIdMapDictionary
      || !currentIdMapDictionary.equals(idMapDictionary)
      || !currentMissionsDictionary
      || !currentMissionsDictionary.equals(missionsDictionary)
      || !currentQuestsDictionary
      || !currentQuestsDictionary.equals(questsDictionary)
      || !dictionarySnapshotStillCurrent(idMapDictionary, idMap, dictionaryLayout)
      || !dictionarySnapshotStillCurrent(
        missionsDictionary,
        missions,
        dictionaryLayout,
      )
      || !dictionarySnapshotStillCurrent(questsDictionary, quests, dictionaryLayout)
    ) {
      return { ok: false, reason: "mission_state_snapshot_changed_before_publish" };
    }

    const activeMissions = [];
    for (const [missionId, row] of missionById.entries()) {
      if (row.stateValue === config.missionData.processingState) {
        activeMissions.push({ missionId, state: row.state });
      }
    }
    const activeQuests = questRows.filter(
      (row) => row.stateValue === config.questData.processingState,
    );

    return {
      ok: true,
      questToMission: snapshotQuestToMission,
      activeMissions,
      activeQuests,
      counts: {
        idMapEntries: idMap.rows.length,
        missionEntries: missions.rows.length,
        questEntries: quests.rows.length,
        activeMissions: activeMissions.length,
        activeQuests: activeQuests.length,
      },
      versions: {
        idMap: idMap.version,
        missions: missions.version,
        currentQuests: quests.version,
      },
    };
  } catch (error) {
    return {
      ok: false,
      reason: "mission_state_snapshot_failed",
      error: String(error),
    };
  }
}

const missionSnapshotConfig = missionHooks.snapshot;
const missionSnapshotState = {
  ticks: 0,
  attempts: 0,
  complete: false,
  abandoned: false,
  lastFailure: "",
};
attachHook(
  "MissionSystem.Tick.initialStateSnapshot",
  rva(missionSnapshotConfig.tick.rva),
  {
    onEnter(args) {
      if (missionSnapshotState.complete || missionSnapshotState.abandoned) return;
      missionSnapshotState.ticks += 1;
      const retryEveryTicks = Math.max(1, missionSnapshotConfig.retryEveryTicks || 1);
      if (
        missionSnapshotState.ticks !== 1
        && missionSnapshotState.ticks % retryEveryTicks !== 0
      ) {
        return;
      }

      missionSnapshotState.attempts += 1;
      const snapshot = buildMissionStateSnapshot(args[0], missionSnapshotConfig);
      if (!snapshot.ok) {
        const failure = String(snapshot.reason || "unknown");
        if (
          missionSnapshotState.attempts === 1
          || failure !== missionSnapshotState.lastFailure
        ) {
          diagnostic("mission_state_snapshot_retry", {
            attempt: missionSnapshotState.attempts,
            ...snapshot,
          });
        }
        missionSnapshotState.lastFailure = failure;
        if (missionSnapshotState.attempts >= missionSnapshotConfig.maxAttempts) {
          missionSnapshotState.abandoned = true;
          diagnostic("mission_state_snapshot_abandoned", {
            attempts: missionSnapshotState.attempts,
            lastFailure: failure,
          });
        }
        return;
      }

      for (const [questId, missionId] of snapshot.questToMission.entries()) {
        questToMission.set(questId, missionId);
      }
      for (const row of snapshot.activeMissions) {
        event("mission_state", {
          missionId: row.missionId,
          state: row.state,
          active: true,
          snapshot: true,
        });
      }
      for (const row of snapshot.activeQuests) {
        event("quest_state", {
          missionId: row.missionId,
          questId: row.questId,
          state: row.state,
          active: true,
          snapshot: true,
        });
      }
      missionSnapshotState.complete = true;
      diagnostic("mission_state_snapshot_complete", {
        attempts: missionSnapshotState.attempts,
        ticks: missionSnapshotState.ticks,
        counts: snapshot.counts,
        versions: snapshot.versions,
      });
    },
  },
);

function attachMissionState(name, hook, state, active) {
  attachHook(name, rva(hook.rva), {
    onEnter(args) {
      const missionId = readIl2CppString(args[1]);
      if (!missionId) {
        diagnostic("mission_id_missing", { hook: name });
        return;
      }
      event("mission_state", { missionId, state, active });
    },
  });
}

function attachQuestState(name, hook, state, active) {
  attachHook(name, rva(hook.rva), {
    onEnter(args) {
      this.questId = readIl2CppString(args[1]);
    },
    onLeave() {
      const missionId = questToMission.get(this.questId);
      if (!this.questId || !missionId) {
        diagnostic("quest_mission_id_missing", { hook: name, questId: this.questId || "" });
        return;
      }
      event("quest_state", {
        missionId,
        questId: this.questId,
        state,
        active,
      });
    },
  });
}

attachMissionState("MissionSystem.StartMission", missionHooks.startMission, "Processing", true);
attachMissionState("MissionSystem.CompleteMission", missionHooks.completeMission, "Completed", false);
attachMissionState("MissionSystem.FailMission", missionHooks.failMission, "Failed", false);
attachQuestState("MissionSystem.StartQuest", missionHooks.startQuest, "Processing", true);
attachQuestState("MissionSystem.SucceedQuest", missionHooks.succeedQuest, "Completed", false);
attachQuestState("MissionSystem.FailQuest", missionHooks.failQuest, "Failed", false);

transmit("ready", {
  ready: {
    pid: Process.id,
    moduleName: gameAssembly.name,
    modulePath: gameAssembly.path,
    moduleBase: String(gameAssembly.base),
    moduleSize: gameAssembly.size,
    hooks: hookStats,
  },
});
