"use strict";

// Replaced by runtime_trace.py capture --profile audio before this agent is loaded.
const CONFIG = __AUDIO_TRACE_CONFIG__;

const gameAssembly = Process.getModuleByName(CONFIG.moduleName);
const nativeModule = CONFIG.nativeModuleName
  ? Process.getModuleByName(CONFIG.nativeModuleName)
  : null;
const hookStats = {};
const nativeHookStats = {};
const contextStacks = new Map();
const callStacks = new Map();
const nativeCallStacks = new Map();
let captureCounter = 0;

function rva(value) {
  return gameAssembly.base.add(parseInt(String(value), 16));
}

function nativeRva(value) {
  return nativeModule.base.add(parseInt(String(value), 16));
}

function currentThreadId() {
  return Process.getCurrentThreadId();
}

function stackFor(threadId) {
  let stack = contextStacks.get(threadId);
  if (!stack) {
    stack = [];
    contextStacks.set(threadId, stack);
  }
  return stack;
}

function callStackFor(threadId) {
  let stack = callStacks.get(threadId);
  if (!stack) {
    stack = [];
    callStacks.set(threadId, stack);
  }
  return stack;
}

function nativeCallStackFor(threadId) {
  let stack = nativeCallStacks.get(threadId);
  if (!stack) {
    stack = [];
    nativeCallStacks.set(threadId, stack);
  }
  return stack;
}

function transmit(channel, payload) {
  send({ channel, ...payload });
}

function diagnostic(kind, values = {}) {
  transmit("diagnostic", { diagnostic: { kind, ...values } });
}

function event(kind, values = {}) {
  transmit("event", {
    event: {
      kind,
      threadId: currentThreadId(),
      runtimeExecutionObserved: true,
      ...values,
    },
  });
}

function pointerString(value) {
  try {
    return value && !value.isNull() ? String(value) : "0x0";
  } catch (_) {
    return "";
  }
}

function readU64(value) {
  try {
    return value.toUInt64().toString();
  } catch (_) {
    return "";
  }
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

function readValue(value, kind) {
  try {
    switch (kind || "pointer") {
      case "string":
        return readIl2CppString(value);
      case "utf16":
        return !value || value.isNull() ? "" : (value.readUtf16String(4096) || "");
      case "u32":
        return value.toUInt32();
      case "i32":
        return value.toInt32();
      case "bool":
        return (value.toUInt32() & 0xff) !== 0;
      case "u64":
        return readU64(value);
      case "pointer":
      default:
        return pointerString(value);
    }
  } catch (_) {
    return null;
  }
}

function readArguments(hook, args) {
  const values = {};
  for (const [name, spec] of Object.entries(hook.args || {})) {
    if (!spec || typeof spec.index !== "number") continue;
    values[name] = readValue(args[spec.index], spec.kind);
  }
  for (const [indexText, name] of Object.entries(hook.stringArgs || {})) {
    const index = Number(indexText);
    if (Number.isInteger(index) && !Object.prototype.hasOwnProperty.call(values, name)) {
      values[name] = readValue(args[index], "string");
    }
  }
  return values;
}

function readStackArguments(hook, stackPointer) {
  const values = {};
  if (!stackPointer) return values;
  for (const spec of hook.stackArguments || []) {
    if (!spec || typeof spec.name !== "string" || typeof spec.offset !== "number") continue;
    try {
      values[spec.name] = readNativeMemoryValue(
        stackPointer.add(spec.offset),
        spec.kind || "pointer",
      );
    } catch (_) {
      values[spec.name] = null;
    }
  }
  return values;
}

function readReturn(value, kind) {
  if (!kind || kind === "void") return null;
  return readValue(value, kind);
}

function readNativeMemoryValue(pointer, kind) {
  try {
    if (!pointer || pointer.isNull()) return null;
    switch (kind || "pointer") {
      case "u32":
        return pointer.readU32();
      case "i32":
        return pointer.readS32();
      case "u64":
        return pointer.readU64().toString();
      case "utf16":
        {
          const stringPointer = pointer.readPointer();
          return stringPointer.isNull() ? "" : (stringPointer.readUtf16String(4096) || "");
        }
      case "pointer":
      default:
        return pointerString(pointer.readPointer());
    }
  } catch (_) {
    return null;
  }
}

function readNativeMemory(hook, args, stackPointer = null, savedBases = {}) {
  const values = {};
  for (const spec of hook.memory || []) {
    if (!spec || typeof spec.name !== "string") continue;
    try {
      let base = null;
      let usingSavedBase = false;
      if (typeof spec.argIndex === "number") {
        base = args[spec.argIndex];
      } else if (
        typeof spec.baseField === "string"
        && savedBases[spec.baseField]
      ) {
        base = savedBases[spec.baseField];
        usingSavedBase = true;
      } else if (typeof spec.stackOffset === "number" && stackPointer) {
        base = stackPointer.add(spec.stackOffset);
      } else {
        continue;
      }
      if (!base || base.isNull()) {
        values[spec.name] = null;
        continue;
      }
      let target = base;
      const pointerOffsets = Array.isArray(spec.pointerOffsets)
        ? spec.pointerOffsets
        : (typeof spec.pointerOffset === "number" ? [spec.pointerOffset] : []);
      let pointerMissing = false;
      for (const pointerOffset of pointerOffsets) {
        if (typeof pointerOffset !== "number") {
          pointerMissing = true;
          break;
        }
        target = target.add(pointerOffset).readPointer();
        if (!target || target.isNull()) {
          pointerMissing = true;
          break;
        }
      }
      if (pointerMissing) {
        values[spec.name] = null;
        continue;
      }
      if (
        spec.savePointer
        && !usingSavedBase
        && (spec.kind || "pointer") === "pointer"
      ) {
        try {
          const saved = target.readPointer();
          if (saved && !saved.isNull()) savedBases[spec.name] = saved;
        } catch (_) {
          // Keep the scalar observation even when the optional saved base is
          // unreadable on this invocation.
        }
      }
      // A stack-backed pointer is both an output slot and the base used by
      // later fields. On post-call sampling, preserve the pointer captured at
      // entry as the scalar value; do not treat that pointer as a new memory
      // location and read its first word (usually a vtable) as the pointer.
      if (
        typeof spec.stackOffset === "number"
        && !usingSavedBase
        && (spec.kind || "pointer") === "pointer"
        && savedBases[spec.name]
        && typeof spec.pointerOffset !== "number"
        && !Array.isArray(spec.pointerOffsets)
      ) {
        values[spec.name] = pointerString(savedBases[spec.name]);
        continue;
      }
      values[spec.name] = readNativeMemoryValue(
        target.add(spec.offset || 0),
        spec.kind || "pointer",
      );
    } catch (_) {
      values[spec.name] = null;
    }
  }
  return values;
}

function readNativeArguments(hook, args) {
  const values = {};
  for (let index = 0; index < nativeArgumentCount(hook); index += 1) {
    try {
      values[`arg${index}`] = pointerString(args[index]);
    } catch (_) {
      values[`arg${index}`] = null;
    }
  }
  return values;
}

function nativeArgumentCount(hook) {
  let maximum = 5;
  for (const spec of Object.values((hook && hook.args) || {})) {
    if (spec && typeof spec.index === "number") maximum = Math.max(maximum, spec.index);
  }
  for (const indexText of Object.keys((hook && hook.stringArgs) || {})) {
    const index = Number(indexText);
    if (Number.isInteger(index)) maximum = Math.max(maximum, index);
  }
  for (const spec of (hook && hook.memory) || []) {
    if (spec && typeof spec.argIndex === "number") maximum = Math.max(maximum, spec.argIndex);
  }
  return maximum + 1;
}

function readNativeDecodedArguments(hook, args) {
  try {
    return readArguments(hook, args);
  } catch (_) {
    return {};
  }
}

// The external-source manager is a small hash table whose bucket head lives at
// manager +0 and whose bucket count lives at manager +8.  The constructor does
// not return the allocated entry, so a bounded post-call scan by its generated
// serial is the only way to expose the entry pointer without patching the
// target process.  The same scan at join/lookup gives a pointer identity that
// is stronger than a same-session integer intersection.
function managerEntryForKey(manager, keyValue) {
  try {
    if (!manager || manager.isNull()) return null;
    const bucketCount = manager.add(8).readU32();
    if (!bucketCount || bucketCount > 0x100000) return null;
    const buckets = manager.readPointer();
    if (!buckets || buckets.isNull()) return null;
    const key = Number(keyValue >>> 0);
    let entry = buckets.add((key % bucketCount) * Process.pointerSize).readPointer();
    for (let index = 0; index < 4096 && entry && !entry.isNull(); index += 1) {
      if (entry.add(0x4c).readU32() === key) return entry;
      entry = entry.add(0x68).readPointer();
    }
  } catch (_) {
    return null;
  }
  return null;
}

function derivedManagerEntryArguments(hook, args) {
  const sourceKind = hook && hook.sourceKind;
  if (![
    "externalSourceRegistration",
    "externalSourceManagerJoin",
    "externalSourceLookup",
    "externalSourceSiblingLookup",
  ].includes(sourceKind)) return {};
  try {
    const manager = args[0];
    const key = args[1].toUInt32();
    const entry = managerEntryForKey(manager, key);
    if (!entry) return { managerEntryPointer: null, managerEntryFound: false };
    return {
      managerEntryPointer: pointerString(entry),
      managerEntryFound: true,
      managerEntrySerial: entry.add(0x4c).readU32(),
      managerEntryAux: entry.add(0x24).readU32(),
      managerEntryContext: pointerString(entry.add(0x28).readPointer()),
      managerEntryDescriptorInfo: pointerString(entry.add(0x38).readPointer()),
      managerEntryCallback: pointerString(entry.add(0x50).readPointer()),
      managerEntryCallbackCookie: pointerString(entry.add(0x58).readPointer()),
      managerEntryFlags: entry.add(0x60).readU32(),
    };
  } catch (_) {
    return { managerEntryPointer: null, managerEntryFound: false };
  }
}

function activeContexts(threadId) {
  return (contextStacks.get(threadId) || []).map((context) => ({
    captureId: context.captureId,
    hookName: context.hookName,
    sourceKind: context.sourceKind,
    instancePointer: context.instancePointer,
  }));
}

function managedCallStack(threadId) {
  return (callStacks.get(threadId) || []).map((frame) => ({
    captureId: frame.captureId,
    parentCaptureId: frame.parentCaptureId || null,
    hookName: frame.hookName,
    sourceKind: frame.sourceKind || null,
    mode: frame.mode || null,
  }));
}

function attachHook(hook) {
  const address = rva(hook.rva);
  try {
    Interceptor.attach(address, {
      onEnter(args) {
        const threadId = currentThreadId();
        const captureId = `audio-${Process.id}-${++captureCounter}`;
        const callStack = callStackFor(threadId);
        const parentFrame = callStack.length ? callStack[callStack.length - 1] : null;
        const values = {
          captureId,
          parentCaptureId: parentFrame ? parentFrame.captureId : null,
          hookName: hook.name,
          sourceKind: hook.sourceKind,
          token: hook.token,
          methodIndex: hook.methodIndex,
          rva: hook.rva,
          arguments: readArguments(hook, args),
          stackArguments: readStackArguments(hook, this.context.sp),
          activeContexts: activeContexts(threadId),
        };
        if (hook.instance) values.instancePointer = pointerString(args[0]);
        const frame = {
          captureId,
          parentCaptureId: parentFrame ? parentFrame.captureId : null,
          hookName: hook.name,
          sourceKind: hook.sourceKind,
          mode: hook.mode,
        };
        callStack.push(frame);
        this.audioFrame = frame;

        if (hook.mode === "carrier") {
          const context = {
            captureId,
            hookName: hook.name,
            sourceKind: hook.sourceKind,
            instancePointer: values.instancePointer || null,
          };
          stackFor(threadId).push(context);
          this.audioContext = context;
          event("audio_carrier_enter", values);
        } else if (hook.mode === "control") {
          event("audio_control_request", values);
        } else {
          event("audio_request", values);
        }
      },
      onLeave(retval) {
        const threadId = currentThreadId();
        const common = {
          hookName: hook.name,
          sourceKind: hook.sourceKind,
          token: hook.token,
          methodIndex: hook.methodIndex,
          rva: hook.rva,
          returnValue: readReturn(retval, hook.returnKind),
          captureId: this.audioFrame ? this.audioFrame.captureId : null,
          parentCaptureId: this.audioFrame ? this.audioFrame.parentCaptureId || null : null,
        };
        if (hook.mode === "carrier") {
          const stack = contextStacks.get(threadId) || [];
          const context = this.audioContext;
          if (context && stack.length && stack[stack.length - 1] === context) {
            stack.pop();
          } else if (context) {
            diagnostic("audio_carrier_stack_mismatch", {
              hookName: hook.name,
              captureId: context.captureId,
              stackDepth: stack.length,
            });
            const index = stack.lastIndexOf(context);
            if (index >= 0) stack.splice(index, 1);
          }
          if (!stack.length) contextStacks.delete(threadId);
          event("audio_carrier_leave", {
            ...common,
            captureId: context ? context.captureId : common.captureId,
          });
        } else if (hook.mode === "control") {
          event("audio_control_result", {
            ...common,
          });
        } else {
          event("audio_request_result", {
            ...common,
          });
        }
        const callStack = callStacks.get(threadId) || [];
        const frame = this.audioFrame;
        if (frame && callStack.length && callStack[callStack.length - 1] === frame) {
          callStack.pop();
        } else if (frame) {
          diagnostic("audio_call_stack_mismatch", {
            hookName: hook.name,
            captureId: frame.captureId,
            stackDepth: callStack.length,
          });
          const index = callStack.lastIndexOf(frame);
          if (index >= 0) callStack.splice(index, 1);
        }
        if (!callStack.length) callStacks.delete(threadId);
      },
    });
    hookStats[hook.name] = "attached";
  } catch (error) {
    hookStats[hook.name] = `failed: ${error}`;
    diagnostic("audio_hook_attach_failed", {
      hookName: hook.name,
      rva: hook.rva,
      error: String(error),
    });
  }
}

function attachNativeHook(hook) {
  const address = nativeRva(hook.rva);
  try {
    Interceptor.attach(address, {
      onEnter(args) {
        const threadId = currentThreadId();
        this.nativeCaptureId = `audio-native-${Process.id}-${++captureCounter}`;
        const nativeCallStack = nativeCallStackFor(threadId);
        const parentNativeFrame = nativeCallStack.length
          ? nativeCallStack[nativeCallStack.length - 1]
          : null;
        this.nativeFrame = {
          nativeCaptureId: this.nativeCaptureId,
          hookName: hook.name,
          sourceKind: hook.sourceKind,
          returnAddress: pointerString(this.returnAddress),
          parentNativeCaptureId: parentNativeFrame
            ? parentNativeFrame.nativeCaptureId
            : null,
        };
        nativeCallStack.push(this.nativeFrame);
        // Keep the entry stack pointer so stack-argument memory can be read
        // again after the native function stores its output fields.  The
        // default Wwise I/O open routine receives its provider context in
        // stack argument 5 and writes the resulting handle there indirectly.
        this.nativeStackPointer = this.context.sp;
        this.nativeMemoryBases = {};
        this.nativeArgs = [];
        for (let index = 0; index < nativeArgumentCount(hook); index += 1) {
          try {
            this.nativeArgs[index] = args[index];
          } catch (_) {
            this.nativeArgs[index] = null;
          }
        }
        event("audio_native_call", {
          native: true,
          moduleName: nativeModule.name,
          nativeCaptureId: this.nativeCaptureId,
          nativeParentCaptureId: this.nativeFrame.parentNativeCaptureId,
          hookName: hook.name,
          sourceKind: hook.sourceKind,
          rva: hook.rva,
          nativeReturnAddress: this.nativeFrame.returnAddress,
          activeContexts: activeContexts(threadId),
          managedCallStack: managedCallStack(threadId),
          arguments: readNativeArguments(hook, args),
          decodedArguments: readNativeDecodedArguments(hook, args),
          derivedArguments: derivedManagerEntryArguments(hook, args),
          memory: readNativeMemory(
            hook,
            args,
            this.nativeStackPointer,
            this.nativeMemoryBases,
          ),
        });
      },
      onLeave(retval) {
        const threadId = currentThreadId();
        const nativeFrame = this.nativeFrame;
        event("audio_native_result", {
          native: true,
          moduleName: nativeModule.name,
          nativeCaptureId: this.nativeCaptureId || null,
          nativeParentCaptureId: nativeFrame
            ? nativeFrame.parentNativeCaptureId
            : null,
          hookName: hook.name,
          sourceKind: hook.sourceKind,
          rva: hook.rva,
          nativeReturnAddress: nativeFrame ? nativeFrame.returnAddress : null,
          activeContexts: activeContexts(threadId),
          managedCallStack: managedCallStack(threadId),
          returnValue: readReturn(retval, hook.returnKind),
          decodedArgumentsAfter: readNativeDecodedArguments(hook, this.nativeArgs || []),
          derivedArgumentsAfter: derivedManagerEntryArguments(hook, this.nativeArgs || []),
          memoryAfter: readNativeMemory(
            hook,
            this.nativeArgs || [],
            this.nativeStackPointer,
            this.nativeMemoryBases || {},
          ),
        });
        const nativeCallStack = nativeCallStacks.get(threadId) || [];
        if (nativeFrame && nativeCallStack.length && nativeCallStack[nativeCallStack.length - 1] === nativeFrame) {
          nativeCallStack.pop();
        } else if (nativeFrame) {
          diagnostic("audio_native_call_stack_mismatch", {
            hookName: hook.name,
            nativeCaptureId: nativeFrame.nativeCaptureId,
            stackDepth: nativeCallStack.length,
          });
          const index = nativeCallStack.lastIndexOf(nativeFrame);
          if (index >= 0) nativeCallStack.splice(index, 1);
        }
        if (!nativeCallStack.length) nativeCallStacks.delete(threadId);
      },
    });
    nativeHookStats[hook.name] = "attached";
  } catch (error) {
    nativeHookStats[hook.name] = `failed: ${error}`;
    diagnostic("audio_native_hook_attach_failed", {
      hookName: hook.name,
      rva: hook.rva,
      error: String(error),
    });
  }
}

for (const hook of CONFIG.hooks || []) attachHook(hook);
if (nativeModule) {
  for (const hook of CONFIG.nativeHooks || []) attachNativeHook(hook);
}

transmit("ready", {
  ready: {
    pid: Process.id,
    moduleName: gameAssembly.name,
    modulePath: gameAssembly.path,
    moduleBase: String(gameAssembly.base),
    moduleSize: gameAssembly.size,
    hooks: hookStats,
    nativeModuleName: nativeModule ? nativeModule.name : null,
    nativeModulePath: nativeModule ? nativeModule.path : null,
    nativeModuleBase: nativeModule ? String(nativeModule.base) : null,
    nativeModuleSize: nativeModule ? nativeModule.size : null,
    nativeHooks: nativeHookStats,
    evidenceBoundary: CONFIG.evidenceBoundary,
  },
});
