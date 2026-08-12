"use strict";

// Replaced by capture_audio_runtime_trace.py before this agent is loaded.
const CONFIG = __AUDIO_TRACE_CONFIG__;

const gameAssembly = Process.getModuleByName(CONFIG.moduleName);
const hookStats = {};
const contextStacks = new Map();
const callStacks = new Map();
let captureCounter = 0;

function rva(value) {
  return gameAssembly.base.add(parseInt(String(value), 16));
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

function readReturn(value, kind) {
  if (!kind || kind === "void") return null;
  return readValue(value, kind);
}

function activeContexts(threadId) {
  return (contextStacks.get(threadId) || []).map((context) => ({
    captureId: context.captureId,
    hookName: context.hookName,
    sourceKind: context.sourceKind,
    instancePointer: context.instancePointer,
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
          activeContexts: activeContexts(threadId),
        };
        if (hook.instance) values.instancePointer = pointerString(args[0]);
        const frame = {
          captureId,
          parentCaptureId: parentFrame ? parentFrame.captureId : null,
          hookName: hook.name,
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

for (const hook of CONFIG.hooks || []) attachHook(hook);

transmit("ready", {
  ready: {
    pid: Process.id,
    moduleName: gameAssembly.name,
    modulePath: gameAssembly.path,
    moduleBase: String(gameAssembly.base),
    moduleSize: gameAssembly.size,
    hooks: hookStats,
    evidenceBoundary: CONFIG.evidenceBoundary,
  },
});
