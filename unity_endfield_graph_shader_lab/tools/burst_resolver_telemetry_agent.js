"use strict";

// This agent is deliberately an observation-only boundary.  It never calls a
// game export, invokes a returned resolver pointer, or mutates target memory.
const CONFIG = __BURST_RESOLVER_TRACE_CONFIG__;
const capture = CONFIG.capture;
const hookStates = {};
const targetModuleName = String(CONFIG.resolverModuleName).toLowerCase();
const gameAssemblyName = String(CONFIG.moduleName).toLowerCase();
let captureEnabled = false;
let captureStarted = false;
let eventCount = 0;
let capped = false;
let terminalState = null;
let batch = [];
let burstHandle = null;
let burstIdentity = null;

function transmit(channel, payload) {
  send({ channel, ...payload });
}

function pointerText(value) {
  if (value === null || value === undefined) return null;
  try { return String(value); } catch (_) { return null; }
}

function moduleInfo(item, status) {
  return {
    status: status || "observed",
    name: item ? item.name : null,
    path: item ? item.path : null,
    base: item ? pointerText(item.base) : null,
    size: item ? item.size : null,
  };
}

function findResolverModules() {
  return Process.enumerateModules().filter(
    (item) => String(item.name).toLowerCase() === targetModuleName,
  );
}

function setResolverIdentity(handle, path, source) {
  const text = pointerText(handle);
  if (!text || text === "0x0") return false;
  if (burstHandle && !ptr(burstHandle).equals(ptr(handle))) {
    fatal("resolver_hmodule_changed", {
      expectedHModule: pointerText(burstHandle),
      actualHModule: text,
      source,
    });
    return false;
  }
  burstHandle = ptr(handle);
  let observedPath = path || null;
  let observedModule = null;
  try {
    observedModule = Process.findModuleByAddress(burstHandle);
  } catch (_) {
    observedModule = null;
  }
  if (!observedModule) {
    fatal("resolver_hmodule_not_enumerated", {
      hModule: text,
      source,
    });
    return false;
  }
  if (String(observedModule.name).toLowerCase() !== targetModuleName) {
    fatal("resolver_hmodule_module_name_mismatch", {
      hModule: text,
      observedModuleName: observedModule.name,
      expectedModuleName: CONFIG.resolverModuleName,
      source,
    });
    return false;
  }
  if (!observedPath && observedModule) observedPath = observedModule.path;
  burstIdentity = {
    status: source,
    name: observedModule ? observedModule.name : CONFIG.resolverModuleName,
    path: observedPath,
    base: text,
    size: observedModule ? observedModule.size : null,
  };
  return true;
}

function discoverResolverIdentity() {
  let matches;
  try {
    matches = findResolverModules();
  } catch (error) {
    fatal("resolver_module_enumeration_failed", { error: String(error) });
    return;
  }
  if (matches.length > 1) {
    fatal("multiple_resolver_modules", {
      resolverModuleName: CONFIG.resolverModuleName,
      modules: matches.map((item) => moduleInfo(item, "ambiguous")),
    });
    return;
  }
  if (matches.length === 1) {
    setResolverIdentity(matches[0].base, matches[0].path, "already_loaded");
  } else {
    burstIdentity = {
      status: "not_loaded_at_attach",
      name: CONFIG.resolverModuleName,
      path: null,
      base: null,
      size: null,
    };
  }
}

function flush() {
  if (!batch.length) return;
  transmit("events", { events: batch });
  batch = [];
}

function state(kind, values) {
  transmit("state", { state: { kind, ...values } });
}

function fatal(kind, values) {
  if (terminalState === "fatal") return;
  terminalState = "fatal";
  captureEnabled = false;
  flush();
  state("capture_fatal", { reason: kind, ...values });
  transmit("fatal", { fatal: { kind, ...values } });
}

function record(kind, values) {
  if (!captureEnabled || capped || terminalState) return;
  batch.push({ kind, ...values });
  eventCount += 1;
  if (batch.length >= capture.batchSize) flush();
  if (eventCount >= capture.maxEvents) {
    captureEnabled = false;
    capped = true;
    flush();
    terminalState = "capped";
    state("capture_capped", { maxEvents: capture.maxEvents });
  }
}

function resolverPath(value) {
  if (value === null || value === undefined) return { value: null, matched: false };
  try {
    const pointer = ptr(value);
    if (pointer.isNull()) return { value: null, matched: false };
    let length = 0;
    for (; length < capture.maxLibraryPathChars; length++) {
      if (pointer.add(length * 2).readU16() === 0) break;
    }
    if (length >= capture.maxLibraryPathChars) {
      fatal("loadlibrary_path_unterminated", { maxChars: capture.maxLibraryPathChars });
      return { value: null, matched: false, failed: true };
    }
    const path = length === 0 ? "" : pointer.readUtf16String(length);
    if (path === null) return { value: null, matched: false, failed: true };
    const normalized = String(path).replace(/\//g, "\\").toLowerCase();
    const leaf = normalized.split("\\").pop();
    return {
      value: String(path),
      matched: leaf === targetModuleName,
    };
  } catch (error) {
    fatal("loadlibrary_path_unreadable", { error: String(error) });
    return { value: null, matched: false, failed: true };
  }
}

function procName(value) {
  // Frida supplies a NativePointer for every native argument, including a
  // NULL pointer.  NativePointer(0) is truthy in JavaScript, so check the
  // pointer value before applying the ordinal convention.  Treating NULL as
  // ordinal #0 would misrepresent an invalid GetProcAddress call and would
  // also make the bounded ANSI read look successful.
  try {
    if (value === null || value === undefined) return { value: null, type: "null" };
    const pointer = ptr(value);
    if (pointer.isNull()) return { value: null, type: "null" };
    if (pointer.compare(ptr("0x10000")) < 0) {
      return { value: "#" + pointer.toUInt32(), type: "ordinal" };
    }
    let length = 0;
    for (; length < capture.maxProcNameChars; length++) {
      if (pointer.add(length).readU8() === 0) break;
    }
    if (length >= capture.maxProcNameChars) {
      fatal("getproc_name_unterminated", { maxBytes: capture.maxProcNameChars });
      return { value: null, type: "unreadable" };
    }
    const name = length === 0 ? "" : pointer.readAnsiString(length);
    if (name === null) {
      fatal("getproc_name_unreadable", {});
      return { value: null, type: "unreadable" };
    }
    return { value: String(name), type: "name" };
  } catch (error) {
    fatal("getproc_name_unreadable", { error: String(error) });
    return { value: null, type: "unreadable" };
  }
}

function gameAssemblyBacktrace(context) {
  const frames = [];
  try {
    const trace = Thread.backtrace(context, Backtracer.ACCURATE);
    for (const address of trace) {
      if (frames.length >= capture.maxBacktraceFrames) break;
      let owner = null;
      try { owner = Process.findModuleByAddress(address); } catch (_) { owner = null; }
      // Match the verified module instance, not just a basename.  A basename
      // alone is insufficient if a same-named DLL was loaded from another
      // directory or a module was replaced while the trace was running.
      if (
        !owner ||
        !gameAssembly ||
        String(owner.name).toLowerCase() !== gameAssemblyName ||
        !ptr(owner.base).equals(ptr(gameAssembly.base)) ||
        String(owner.path).toLowerCase() !== String(gameAssembly.path).toLowerCase()
      ) continue;
      frames.push({
        address: pointerText(address),
        module: owner.name,
        modulePath: owner.path,
        moduleBase: pointerText(owner.base),
        moduleSize: owner.size,
        offset: pointerText(ptr(address).sub(owner.base)),
      });
    }
    return {
      status: frames.length ? "gameassembly_frames" : "no_gameassembly_frame",
      frames,
    };
  } catch (error) {
    return { status: "unavailable", frames, error: String(error) };
  }
}

function attachHook(name, spec) {
  let address;
  try {
    address = Module.findExportByName(spec.moduleName, spec.export);
  } catch (error) {
    hookStates[name] = "export_lookup_failed";
    fatal("hook_export_lookup_failed", { hook: name, error: String(error) });
    return;
  }
  if (!address) {
    hookStates[name] = "export_missing";
    fatal("hook_export_missing", { hook: name, moduleName: spec.moduleName, export: spec.export });
    return;
  }
  try {
    Interceptor.attach(address, {
      onEnter(args) {
        if (name === "loadLibraryW") {
          const request = resolverPath(args[0]);
          this.requestedPath = request.value;
          this.resolverMatch = request.matched;
          this.pathReadFailed = request.failed === true;
          return;
        }
        const handle = args[0];
        this.matchingHandle = Boolean(burstHandle && ptr(handle).equals(burstHandle));
        if (!this.matchingHandle || terminalState || !captureEnabled || capped) return;
        const nameValue = procName(args[1]);
        this.hModule = pointerText(handle);
        this.lpProcName = nameValue;
        this.callerBacktrace = gameAssemblyBacktrace(this.context);
      },
      onLeave(retval) {
        if (name === "loadLibraryW") {
          if (this.pathReadFailed || !this.resolverMatch || terminalState || capped) return;
          const loaded = !retval.isNull();
          const module = loaded ? (() => {
            try { return Process.findModuleByAddress(retval); } catch (_) { return null; }
          })() : null;
          if (loaded && !setResolverIdentity(retval, module ? module.path : this.requestedPath, "loadlibraryw")) return;
          // Identity discovery must not depend on the capture trigger.  The
          // resolver may load during the attach-to-trigger window; retain its
          // HMODULE so GetProcAddress calls after start are still attributed.
          if (!captureEnabled) return;
          record("resolver_module_loaded", {
            requestedPath: this.requestedPath,
            hModule: pointerText(retval),
            loadSucceeded: loaded,
            module: moduleInfo(module, "loadlibraryw"),
          });
          return;
        }
        if (!this.matchingHandle || terminalState || !captureEnabled || capped) return;
        record("get_proc_address", {
          hModule: this.hModule,
          lpProcName: this.lpProcName.value,
          lpProcNameType: this.lpProcName.type,
          returnPointer: pointerText(retval),
          gameAssemblyCallerBacktrace: this.callerBacktrace.frames,
          backtraceStatus: this.callerBacktrace.status,
          threadId: Process.getCurrentThreadId(),
        });
      },
    });
    hookStates[name] = "attached";
  } catch (error) {
    hookStates[name] = "attach_failed";
    fatal("hook_attach_failed", { hook: name, error: String(error) });
  }
}

let gameAssembly = null;
let kernel32 = null;
try {
  gameAssembly = Process.getModuleByName(CONFIG.moduleName);
  kernel32 = Process.getModuleByName(CONFIG.kernel32ModuleName);
} catch (error) {
  fatal("required_module_missing", { error: String(error) });
}

discoverResolverIdentity();
for (const [name, spec] of Object.entries(CONFIG.hooks)) attachHook(name, spec);
const failed = Object.entries(hookStates)
  .filter(([, value]) => value !== "attached")
  .map(([name, value]) => ({ name, state: value }));

setInterval(flush, capture.flushIntervalMs);

function waitForStart() {
  recv("start_capture", () => {
    if (captureStarted || terminalState || capped) {
      state("capture_start_rejected", {
        reason: terminalState || (capped ? "capped" : "already_started"),
      });
      waitForStart();
      return;
    }
    captureStarted = true;
    captureEnabled = true;
    eventCount = 0;
    capped = false;
    batch = [];
    transmit("diagnostic", { diagnostic: { kind: "capture_started" } });
    waitForStart();
  });
}
waitForStart();
recv("stop_capture", () => {
  captureEnabled = false;
  flush();
  state("capture_stop_ack", {
    eventCount,
    captureStarted,
    terminalState,
    resolverModuleIdentity: burstIdentity,
  });
});

transmit("ready", {
  ready: {
    pid: Process.id,
    moduleName: gameAssembly ? gameAssembly.name : CONFIG.moduleName,
    modulePath: gameAssembly ? gameAssembly.path : null,
    moduleBase: gameAssembly ? String(gameAssembly.base) : null,
    moduleSize: gameAssembly ? gameAssembly.size : 0,
    kernel32ModuleName: kernel32 ? kernel32.name : CONFIG.kernel32ModuleName,
    resolverModuleName: CONFIG.resolverModuleName,
    resolverModuleIdentity: burstIdentity,
    hooks: hookStates,
    failed,
    maxEvents: capture.maxEvents,
    maxBacktraceFrames: capture.maxBacktraceFrames,
    captureEnabled,
    captureStarted,
    terminalState,
  },
});
