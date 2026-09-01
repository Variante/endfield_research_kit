"use strict";

// This agent is deliberately an observation-only boundary.  It never calls a
// game export, invokes a returned resolver pointer, or mutates target memory.
const CONFIG = __BURST_RESOLVER_TRACE_CONFIG__;
const capture = CONFIG.capture;
const hookStates = {};
const callTargetStates = {};
const routeProbeStates = {};
const observedCallTargets = new Set();
const observedRouteGates = new Set();
const targetModuleName = String(CONFIG.resolverModuleName).toLowerCase();
const gameAssemblyName = String(CONFIG.moduleName).toLowerCase();
const targetWindows = Array.isArray(CONFIG.targets) ? CONFIG.targets : [];
const routeProbes = CONFIG.routeProbes || {};
const expectedResolverPath = CONFIG.resolverExpectedPath
  ? String(CONFIG.resolverExpectedPath).replace(/\//g, "\\").toLowerCase()
  : null;
const expectedResolverSize = Number(CONFIG.resolverExpectedSize || 0);
const requireResolverExportEnumeration = CONFIG.capture.requireResolverExportEnumeration === true;
let captureEnabled = false;
let captureStarted = false;
let eventCount = 0;
let capped = false;
let terminalState = null;
let batch = [];
let burstHandle = null;
let burstIdentity = null;
let resolverExports = new Map();
let resolverExportStatus = "not_loaded";
let resolverHashedExportCount = 0;
let resolverExportMap = [];
let resolverRequestOrdinal = 0;

function transmit(channel, payload) {
  send({ channel, ...payload });
}

function pointerText(value) {
  if (value === null || value === undefined) return null;
  try { return String(value); } catch (_) { return null; }
}

function normalizedPath(value) {
  return value ? String(value).replace(/\//g, "\\").toLowerCase() : null;
}

function moduleInfo(item, status) {
  return {
    status: status || "observed",
    name: item ? item.name : null,
    path: item ? item.path : null,
    base: item ? pointerText(item.base) : null,
    moduleBase: item ? pointerText(item.base) : null,
    size: item ? item.size : null,
    exportEnumerationStatus: item ? resolverExportStatus : "not_loaded",
    hashedExportCount: item ? resolverHashedExportCount : 0,
  };
}

function refreshResolverExports(item) {
  resolverExports = new Map();
  resolverExportMap = [];
  resolverHashedExportCount = 0;
  if (!item) {
    resolverExportStatus = "not_loaded";
    return;
  }
  try {
    const entries = item.enumerateExports();
    for (const entry of entries) {
      if (!entry || !entry.address) continue;
      const name = String(entry.name);
      const address = pointerText(entry.address);
      if (!address) continue;
      resolverExports.set(address.toLowerCase(), name);
      if (/^[0-9a-f]{32}$/i.test(name)) {
        resolverHashedExportCount += 1;
        resolverExportMap.push({ name, offset: pointerText(ptr(entry.address).sub(item.base)) });
      }
    }
    resolverExportStatus = "available";
  } catch (error) {
    resolverExportStatus = "unavailable";
    transmit("diagnostic", {
      diagnostic: { kind: "resolver_export_enumeration_failed", error: String(error) },
    });
  }
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
  if (
    expectedResolverPath &&
    normalizedPath(observedPath) !== expectedResolverPath
  ) {
    fatal("resolver_module_path_mismatch", {
      expectedPath: CONFIG.resolverExpectedPath,
      actualPath: observedPath,
      source,
    });
    return false;
  }
  if (expectedResolverSize && observedModule.size !== expectedResolverSize) {
    fatal("resolver_module_size_mismatch", {
      expectedSize: expectedResolverSize,
      actualSize: observedModule.size,
      source,
    });
    return false;
  }
  refreshResolverExports(observedModule);
  if (requireResolverExportEnumeration && resolverExportStatus !== "available") {
    fatal("resolver_export_enumeration_required", {
      status: resolverExportStatus,
      source,
    });
    return false;
  }
  burstIdentity = {
    status: source,
    name: observedModule ? observedModule.name : CONFIG.resolverModuleName,
    path: observedPath,
    base: text,
    moduleBase: text,
    size: observedModule ? observedModule.size : null,
    exportEnumerationStatus: resolverExportStatus,
    hashedExportCount: resolverHashedExportCount,
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
      moduleBase: null,
      size: null,
      exportEnumerationStatus: "not_loaded",
      hashedExportCount: 0,
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

function sameGameAssembly(owner) {
  return Boolean(
    owner &&
    gameAssembly &&
    String(owner.name).toLowerCase() === gameAssemblyName &&
    ptr(owner.base).equals(ptr(gameAssembly.base)) &&
    normalizedPath(owner.path) === normalizedPath(gameAssembly.path)
  );
}

function frameRecord(address, owner) {
  return {
    address: pointerText(address),
    module: owner ? owner.name : null,
    modulePath: owner ? owner.path : null,
    moduleBase: owner ? pointerText(owner.base) : null,
    moduleSize: owner ? owner.size : null,
    offset: owner ? pointerText(ptr(address).sub(owner.base)) : null,
  };
}

function callerBacktraces(context) {
  const allFrames = [];
  const gameFrames = [];
  try {
    const trace = Thread.backtrace(context, Backtracer.ACCURATE);
    for (const address of trace) {
      if (allFrames.length >= capture.maxBacktraceFrames) break;
      let owner = null;
      try { owner = Process.findModuleByAddress(address); } catch (_) { owner = null; }
      // Unresolved addresses are omitted rather than inventing a module or
      // offset.  The all-module list remains bounded and every retained frame
      // carries the module load base and module-relative offset.
      if (!owner) continue;
      const frame = frameRecord(address, owner);
      allFrames.push(frame);
      if (sameGameAssembly(owner)) gameFrames.push(frame);
    }
    return {
      all: allFrames,
      gameAssembly: gameFrames,
      allStatus: allFrames.length ? "frames" : "no_resolved_frame",
      gameStatus: gameFrames.length ? "gameassembly_frames" : "no_gameassembly_frame",
    };
  } catch (error) {
    return {
      all: allFrames,
      gameAssembly: gameFrames,
      allStatus: "unavailable",
      gameStatus: "unavailable",
      error: String(error),
    };
  }
}

function targetMatches(frames) {
  const matches = [];
  for (const frame of frames) {
    if (!frame || !frame.offset || !frame.moduleBase) continue;
    for (const target of targetWindows) {
      for (const window of target.windows || []) {
        try {
          const offset = ptr(frame.offset);
          const start = ptr(window.startOffset);
          const end = ptr(window.endOffsetExclusive);
          if (offset.compare(start) >= 0 && offset.compare(end) < 0) {
            matches.push({
              targetId: target.id,
              targetMethodIndex: target.methodIndex,
              targetMethodName: target.methodName,
              targetFullName: target.fullName,
              role: window.role,
              methodIndex: window.methodIndex,
              windowStartOffset: window.startOffset,
              windowEndOffsetExclusive: window.endOffsetExclusive,
              frameAddress: frame.address,
              frameOffset: frame.offset,
            });
          }
        } catch (_) {
          // Manifest validation is performed before rendering.  A malformed
          // runtime comparison is not evidence and simply yields no match.
        }
      }
    }
  }
  return matches;
}

function resolvedPointer(retval) {
  if (!retval || retval.isNull()) {
    return {
      resolvedAddress: null,
      resolvedModuleName: null,
      resolvedModulePath: null,
      resolvedModuleBase: null,
      resolvedModuleSize: null,
      resolvedModuleOffset: null,
      resolvedExportName: null,
      resolvedExportStatus: "null_return",
    };
  }
  let owner = null;
  try { owner = Process.findModuleByAddress(retval); } catch (_) { owner = null; }
  const address = pointerText(retval);
  const key = address ? address.toLowerCase() : null;
  return {
    resolvedAddress: address,
    resolvedModuleName: owner ? owner.name : null,
    resolvedModulePath: owner ? owner.path : null,
    resolvedModuleBase: owner ? pointerText(owner.base) : null,
    resolvedModuleSize: owner ? owner.size : null,
    resolvedModuleOffset: owner ? pointerText(ptr(retval).sub(owner.base)) : null,
    resolvedExportName: key && resolverExports.has(key) ? resolverExports.get(key) : null,
    resolvedExportStatus: key && resolverExports.has(key)
      ? "enumerated"
      : (resolverExportStatus === "available" ? "not_enumerated" : resolverExportStatus),
  };
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
        this.callerBacktraces = callerBacktraces(this.context);
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
            resolverModuleIdentity: burstIdentity,
            resolverExportMap: resolverExportMap,
            resolverExportMapCount: resolverHashedExportCount,
          });
          return;
        }
        if (!this.matchingHandle || terminalState || !captureEnabled || capped) return;
        const backtraces = this.callerBacktraces || {
          all: [], gameAssembly: [], allStatus: "unavailable", gameStatus: "unavailable",
        };
        const matches = targetMatches(backtraces.gameAssembly);
        const targets = Array.from(new Set(matches.map((entry) => entry.targetId)));
        const resolved = resolvedPointer(retval);
        record("get_proc_address", {
          requestOrdinal: resolverRequestOrdinal++,
          hModule: this.hModule,
          lpProcName: this.lpProcName.value,
          lpProcNameType: this.lpProcName.type,
          requestedExportIsHashed: Boolean(
            this.lpProcName.type === "name" &&
            /^[0-9a-f]{32}$/i.test(String(this.lpProcName.value || ""))
          ),
          returnPointer: pointerText(retval),
          resolverModule: burstIdentity,
          ...resolved,
          caller: backtraces.all.length ? backtraces.all[0] : null,
          callerBacktrace: backtraces.all,
          callerBacktraceStatus: backtraces.allStatus,
          gameAssemblyCallerBacktrace: backtraces.gameAssembly,
          backtraceStatus: backtraces.gameStatus,
          targetWindowMatches: matches,
          targetAttributionStatus: targets.length ? "target_window_match" : "no_target_window_match",
          targetAttributionTargets: targets,
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

function attachCallTargetHook(target) {
  const probe = target.callTargetProbe;
  if (!gameAssembly || !probe) {
    callTargetStates[target.id] = "probe_missing";
    fatal("call_target_probe_missing", { targetId: target.id });
    return;
  }
  let address;
  try {
    address = gameAssembly.base.add(ptr(probe.getFunctionPointerOffset));
  } catch (error) {
    callTargetStates[target.id] = "address_failed";
    fatal("call_target_probe_address_failed", { targetId: target.id, error: String(error) });
    return;
  }
  try {
    Interceptor.attach(address, {
      onLeave(retval) {
        if (!captureEnabled || capped || terminalState) return;
        const returnPointer = pointerText(retval);
        const observationKey = `${target.id}:${String(returnPointer).toLowerCase()}`;
        if (observedCallTargets.has(observationKey)) return;
        observedCallTargets.add(observationKey);
        record("burst_function_pointer", {
          targetId: target.id,
          targetMethodIndex: target.methodIndex,
          targetMethodName: target.methodName,
          targetFullName: target.fullName,
          callTargetProbe: probe,
          returnPointer,
          ...resolvedPointer(retval),
          threadId: Process.getCurrentThreadId(),
        });
      },
    });
    callTargetStates[target.id] = "attached";
  } catch (error) {
    callTargetStates[target.id] = "attach_failed";
    fatal("call_target_probe_attach_failed", { targetId: target.id, error: String(error) });
  }
}

function sameOffset(left, right) {
  try { return ptr(left).equals(ptr(right)); } catch (_) { return false; }
}

function attachCalcLineBurstGate(probe) {
  const name = "calcLineBurstEnabled";
  if (!gameAssembly || !probe) {
    routeProbeStates[name] = "probe_missing";
    fatal("route_probe_missing", { probe: name });
    return;
  }
  try {
    Interceptor.attach(gameAssembly.base.add(ptr(probe.startOffset)), {
      onEnter() {
        const returnOffset = this.returnAddress.sub(gameAssembly.base);
        const methodInfo = pointerText(this.context.rcx);
        this.admitted = sameOffset(returnOffset, probe.invokeReturnOffset) &&
          methodInfo === String(probe.expectedMethodInfo);
        this.returnOffset = pointerText(returnOffset);
        this.methodInfo = methodInfo;
      },
      onLeave(retval) {
        if (!this.admitted || !captureEnabled || capped || terminalState) return;
        const result = retval.toUInt32() & 0xff;
        const key = `${name}:${result}`;
        if (observedRouteGates.has(key)) return;
        observedRouteGates.add(key);
        record("calc_line_burst_gate", {
          probe: name,
          methodIndex: probe.methodIndex,
          methodName: probe.methodName,
          result: result !== 0,
          returnRegister: probe.returnRegister,
          callerReturnOffset: this.returnOffset,
          methodInfo: this.methodInfo,
          threadId: Process.getCurrentThreadId(),
        });
      },
    });
    routeProbeStates[name] = "attached";
  } catch (error) {
    routeProbeStates[name] = "attach_failed";
    fatal("route_probe_attach_failed", { probe: name, error: String(error) });
  }
}

function attachCalcLineIfixGate(probe) {
  const name = "fromToRotationIfix";
  if (!gameAssembly || !probe) {
    routeProbeStates[name] = "probe_missing";
    fatal("route_probe_missing", { probe: name });
    return;
  }
  try {
    Interceptor.attach(gameAssembly.base.add(ptr(probe.startOffset)), {
      onEnter() {
        const returnOffset = this.returnAddress.sub(gameAssembly.base);
        const patchId = this.context.rcx.toUInt32();
        const methodInfo = pointerText(this.context.rdx);
        const traces = callerBacktraces(this.context);
        let matchedRoute = null;
        let matchedReturnOffset = null;
        for (const caller of probe.calcLineCallerReturns || []) {
          const matched = traces.gameAssembly.find((frame) =>
            frame && frame.offset && sameOffset(frame.offset, caller.returnOffset));
          if (matched) {
            matchedRoute = caller.route;
            matchedReturnOffset = caller.returnOffset;
            break;
          }
        }
        this.admitted = sameOffset(returnOffset, probe.callReturnOffset) &&
          patchId === Number(probe.patchId) &&
          methodInfo === String(probe.expectedMethodInfo) &&
          matchedRoute !== null;
        this.returnOffset = pointerText(returnOffset);
        this.patchId = patchId;
        this.methodInfo = methodInfo;
        this.matchedRoute = matchedRoute;
        this.matchedReturnOffset = matchedReturnOffset;
      },
      onLeave(retval) {
        if (!this.admitted || !captureEnabled || capped || terminalState) return;
        const result = retval.toUInt32() & 0xff;
        const key = `${name}:${this.matchedRoute}:${result}`;
        if (observedRouteGates.has(key)) return;
        observedRouteGates.add(key);
        record("calc_line_ifix_gate", {
          probe: name,
          methodIndex: probe.methodIndex,
          methodName: probe.methodName,
          result: result !== 0,
          patchId: this.patchId,
          returnRegister: probe.returnRegister,
          fromToReturnOffset: this.returnOffset,
          calcLineRoute: this.matchedRoute,
          calcLineCallerReturnOffset: this.matchedReturnOffset,
          methodInfo: this.methodInfo,
          threadId: Process.getCurrentThreadId(),
        });
      },
    });
    routeProbeStates[name] = "attached";
  } catch (error) {
    routeProbeStates[name] = "attach_failed";
    fatal("route_probe_attach_failed", { probe: name, error: String(error) });
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
for (const target of targetWindows) attachCallTargetHook(target);
attachCalcLineBurstGate(routeProbes.calcLineBurstEnabled);
attachCalcLineIfixGate(routeProbes.fromToRotationIfix);
const failed = [
  ...Object.entries(hookStates).map(([name, state]) => ({ kind: "resolver_hook", name, state })),
  ...Object.entries(callTargetStates).map(([name, state]) => ({ kind: "call_target_hook", name, state })),
  ...Object.entries(routeProbeStates).map(([name, state]) => ({ kind: "route_probe_hook", name, state })),
].filter((entry) => entry.state !== "attached");

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
    resolverExportEnumerationStatus: resolverExportStatus,
    resolverHashedExportCount: resolverHashedExportCount,
    resolverExportMap: resolverExportMap,
    targets: targetWindows.map((target) => ({
      id: target.id,
      methodIndex: target.methodIndex,
      methodName: target.methodName,
      windowCount: Array.isArray(target.windows) ? target.windows.length : 0,
    })),
    hooks: hookStates,
    callTargetHooks: callTargetStates,
    routeProbeHooks: routeProbeStates,
    failed,
    maxEvents: capture.maxEvents,
    maxBacktraceFrames: capture.maxBacktraceFrames,
    captureEnabled,
    captureStarted,
    terminalState,
  },
});
