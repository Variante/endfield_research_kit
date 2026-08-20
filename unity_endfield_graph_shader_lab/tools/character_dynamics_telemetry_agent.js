"use strict";

// Read-only Frida agent.  The launcher verifies the executable, GameAssembly,
// and metadata hashes before this source is rendered and loaded.  This agent
// only observes the five pinned native boundaries; it never calls a game
// function, changes memory, or decodes a pointer as an object.
const CONFIG = __CHARACTER_DYNAMICS_TRACE_CONFIG__;
const module = Process.getModuleByName(CONFIG.moduleName);
const capture = CONFIG.capture;
const hookStates = {};
let captureEnabled = false;
let eventCount = 0;
let capped = false;
let batch = [];

function transmit(channel, payload) {
  send({ channel, ...payload });
}

function bytesToHex(buffer) {
  return Array.from(new Uint8Array(buffer || new ArrayBuffer(0)))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

function pointerText(value) {
  if (value === null || value === undefined) return null;
  try { return String(value); } catch (_) { return null; }
}

function boundedSnapshot(value) {
  if (!value) return { status: "null" };
  try {
    const bytes = value.readByteArray(capture.readBytesPerPointer);
    return {
      status: "read",
      bytes: bytesToHex(bytes),
      length: capture.readBytesPerPointer,
    };
  } catch (error) {
    return { status: "unreadable", error: String(error) };
  }
}

function flush() {
  if (!batch.length) return;
  transmit("events", { events: batch });
  batch = [];
}

function record(kind, values) {
  if (!captureEnabled || capped) return;
  batch.push({ kind, ...values });
  eventCount += 1;
  if (batch.length >= capture.batchSize) flush();
  if (eventCount >= capture.maxEvents) {
    capped = true;
    flush();
    transmit("diagnostic", {
      diagnostic: { kind: "event_limit_reached", maxEvents: capture.maxEvents },
    });
  }
}

function registerSnapshot(context, name, spec) {
  const value = context[name];
  const result = { pointer: pointerText(value) };
  if ((spec.snapshotRegisters || []).includes(name)) {
    result.snapshot = boundedSnapshot(value);
  }
  return result;
}

function attachHook(name, spec) {
  const address = module.base.add(parseInt(String(spec.rva), 16));
  const expected = String(spec.expectedBytes).toLowerCase();
  const actual = bytesToHex(address.readByteArray(expected.length / 2));
  if (actual !== expected) {
    hookStates[name] = "bytes_changed";
    transmit("fatal", {
      fatal: {
        kind: "hook_bytes_changed",
        hook: name,
        type: spec.type,
        method: spec.method,
        rva: spec.rva,
        expectedBytes: expected,
        actualBytes: actual,
      },
    });
    return;
  }
  try {
    Interceptor.attach(address, {
      onEnter() {
        this.trace = {
          threadId: Process.getCurrentThreadId(),
          registers: {
            rcx: registerSnapshot(this.context, "rcx", spec),
            rdx: registerSnapshot(this.context, "rdx", spec),
            r8: registerSnapshot(this.context, "r8", spec),
            r9: registerSnapshot(this.context, "r9", spec),
          },
        };
        record("hook_enter", {
          hook: name,
          type: spec.type,
          method: spec.method,
          address: String(address),
          ...this.trace,
        });
        const unreadable = Object.entries(this.trace.registers).some(
          ([, value]) => value.snapshot && value.snapshot.status === "unreadable"
        );
        if (unreadable) {
          captureEnabled = false;
          capped = true;
          transmit("fatal", {
            fatal: {
              kind: "pointer_snapshot_unreadable",
              hook: name,
              message: "stopping capture after a configured pointer snapshot could not be read",
            },
          });
          flush();
        }
      },
      onLeave(retval) {
        record("hook_leave", {
          hook: name,
          type: spec.type,
          method: spec.method,
          address: String(address),
          threadId: this.trace ? this.trace.threadId : Process.getCurrentThreadId(),
          returnValue: pointerText(retval),
        });
      },
    });
    hookStates[name] = "attached";
  } catch (error) {
    hookStates[name] = "attach_failed";
    transmit("fatal", {
      fatal: { kind: "hook_attach_failed", hook: name, error: String(error) },
    });
  }
}

for (const [name, spec] of Object.entries(CONFIG.hooks)) attachHook(name, spec);
const failed = Object.entries(hookStates)
  .filter(([, state]) => state !== "attached")
  .map(([name, state]) => ({ name, state }));

setInterval(flush, capture.flushIntervalMs);

function waitForStart() {
  recv("start_capture", () => {
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
  transmit("diagnostic", { diagnostic: { kind: "capture_stopped", eventCount } });
});

transmit("ready", {
  ready: {
    pid: Process.id,
    moduleName: module.name,
    modulePath: module.path,
    moduleBase: String(module.base),
    moduleSize: module.size,
    hooks: hookStates,
    failed,
    maxEvents: capture.maxEvents,
    readBytesPerPointer: capture.readBytesPerPointer,
    captureEnabled,
  },
});
