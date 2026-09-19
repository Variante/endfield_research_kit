"use strict";

// Replaced by capture_runtime_tags.py before this agent is loaded.
const CONFIG = __GAMEPLAY_TAG_TRACE_CONFIG__;

const gameAssembly = Process.getModuleByName(CONFIG.moduleName);
const hookStats = {};
const seenMappings = new Set();
const seenIds = new Set();

function rva(value) {
  return gameAssembly.base.add(parseInt(String(value), 16));
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
      threadId: Process.getCurrentThreadId(),
      runtimeExecutionObserved: true,
      ...values,
    },
  });
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

function pointerString(value) {
  try {
    return value && !value.isNull() ? String(value) : "0x0";
  } catch (_) {
    return "";
  }
}

function u32(value) {
  try {
    return value.toUInt32() >>> 0;
  } catch (_) {
    return null;
  }
}

function tagIdHex(value) {
  const number = typeof value === "number" ? value >>> 0 : u32(value);
  return number === null ? "" : `0x${number.toString(16).padStart(8, "0")}`;
}

function emitMapping(sourceKind, tagId, tagName, values = {}) {
  if (typeof tagId !== "number" || !tagName) return;
  const id = tagId >>> 0;
  const idHex = tagIdHex(id);
  const key = `${idHex}\u0000${tagName}`;
  if (seenMappings.has(key)) return;
  seenMappings.add(key);
  event("tag_mapping", {
    sourceKind,
    tagId: id,
    tagIdHex: idHex,
    tagName,
    ...values,
  });
}

function emitId(sourceKind, tagId, values = {}) {
  if (typeof tagId !== "number") return;
  const id = tagId >>> 0;
  const idHex = tagIdHex(id);
  const key = `${sourceKind}\u0000${idHex}`;
  if (seenIds.has(key)) return;
  seenIds.add(key);
  event("tag_id_seen", {
    sourceKind,
    tagId: id,
    tagIdHex: idHex,
    ...values,
  });
}

function readValueTypeTagId(value) {
  const direct = u32(value);
  // GameplayTag is a one-field value type in this build.  If IL2CPP passes a
  // boxed value to an instance getter, retain only bounded fallback reads;
  // the capture remains evidence-only until the returned name confirms it.
  const candidates = [];
  if (direct !== null && direct < 0x10000000) candidates.push(direct);
  try {
    const pointer = ptr(value);
    if (!pointer.isNull() && direct !== null && direct >= 0x10000000) {
      for (const offset of [0x10, 0x8, 0x0]) {
        try {
          const candidate = pointer.add(offset).readU32();
          if (!candidates.includes(candidate)) candidates.push(candidate);
        } catch (_) {}
      }
    }
  } catch (_) {}
  return candidates;
}

function attachHook(hook) {
  try {
    const address = rva(hook.rva);
    Interceptor.attach(address, {
      onEnter(args) {
        this.args0 = args[0];
        this.tagName = hook.stringArgIndex === undefined
          ? ""
          : readIl2CppString(args[hook.stringArgIndex]);
        this.tagIdArg = hook.tagIdArgIndex === undefined
          ? null
          : u32(args[hook.tagIdArgIndex]);
        if (hook.kind === "build") {
          event("tag_config_build_enter", {
            hookName: hook.name,
            instancePointer: pointerString(args[0]),
          });
        }
      },
      onLeave(retval) {
        if (hook.kind === "request") {
          const tagId = u32(retval);
          emitMapping(hook.sourceKind, tagId, this.tagName, {
            hookName: hook.name,
            returnValue: pointerString(retval),
          });
        } else if (hook.kind === "name") {
          const tagName = readIl2CppString(retval);
          for (const tagId of readValueTypeTagId(this.args0)) {
            emitMapping(hook.sourceKind, tagId, tagName, {
              hookName: hook.name,
              returnValue: pointerString(retval),
            });
          }
        } else if (hook.kind === "lookup") {
          emitId(hook.sourceKind, this.tagIdArg, {
            hookName: hook.name,
            returnValue: pointerString(retval),
          });
        } else if (hook.kind === "build") {
          event("tag_config_build_leave", {
            hookName: hook.name,
            instancePointer: pointerString(this.args0),
          });
        }
      },
    });
    hookStats[hook.name] = "attached";
  } catch (error) {
    hookStats[hook.name] = `failed: ${error}`;
    diagnostic("tag_hook_attach_failed", {
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
