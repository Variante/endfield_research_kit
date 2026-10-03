/* CONFIG is prepended by the authenticated staging command. */
'use strict';
const gameModule = Process.getModuleByName('GameAssembly.dll');
if (gameModule.path.toLowerCase() !== CONFIG.nativeModulePath.replaceAll('/', '\\').toLowerCase())
  throw new Error('native-module-path-mismatch');
const active = new Map();
const hooks = [];
let observations = 0;
let events = 0;
let stopping = false;
let sourceCopied = false;
let capExceeded = false;
function emit(event, data) {
  events++;
  if (events <= CONFIG.maxEvents) send(event, data);
  else if (!capExceeded) {
    capExceeded = true;
    stopping = true;
    send({kind: 'event-cap-exceeded', events, maxEvents: CONFIG.maxEvents});
  }
}
function hex(address, length) {
  return Array.from(new Uint8Array(address.readByteArray(length))).map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase();
}
function raw(address) {
  try { return {pointer: address.toString(), rawHex: hex(address, CONFIG.contextSnapshotBytes)}; }
  catch (error) { return {pointer: address.toString(), error: String(error)}; }
}
function context(address) {
  const result = raw(address);
  result.interpretation = 'raw bounded pointer snapshots; no typed slot/inflation identity inferred';
  try {
    const carrier = address.add(0x38).readPointer();
    result.pointerAt0x38 = raw(carrier);
    result.carrierPointerAt0 = raw(carrier.readPointer());
    result.carrierPointerAt8 = carrier.add(8).readPointer().toString();
    result.nestedPointerAt0x38 = raw(carrier.readPointer().add(0x38).readPointer());
  } catch (error) { result.snapshotError = String(error); }
  return result;
}
function object(address) {
  const result = raw(address);
  try {
    const klass = address.readPointer();
    result.klass = raw(klass);
    result.classPointerAt0x190 = klass.add(0x190).readPointer().toString();
    result.classPointerAt0x198 = context(klass.add(0x198).readPointer());
    result.classSnapshotInterpretation = 'raw class offsets; actual dispatch/companion requires native and child-register join';
  } catch (error) { result.classError = String(error); }
  return result;
}
function state(reader) {
  const layout = CONFIG.readerLayout;
  const source = reader.add(layout.sourceBase).readPointer();
  const total = Number(reader.add(layout.totalLength).readU64().toString());
  const segment = reader.add(layout.segmentLength).readS32();
  const consumed = reader.add(layout.consumed).readU32();
  const current = reader.add(layout.current).readPointer();
  return {reader: reader.toString(), sourceBase: source.toString(), totalLength: total,
    segmentLength: segment, consumed, current: current.toString(),
    coherentSingleSpan: total > 0 && total === segment && consumed <= total && current.equals(source.add(consumed))};
}
for (const hook of CONFIG.hooks) {
  const address = gameModule.base.add(hook.rva);
  if (hex(address, 16) !== hook.entryHex) throw new Error('native-hook-window-mismatch:' + hook.role);
}
for (const hook of CONFIG.hooks) {
  hooks.push(Interceptor.attach(gameModule.base.add(hook.rva), {
    onEnter(args) {
      this.record = null;
      this.thread = Process.getCurrentThreadId();
      if (stopping) return;
      if (hook.role === 'readvalue') {
        if (observations >= CONFIG.maxObservations || active.has(this.thread)) return;
        const parent = hook.callsites.find(row => gameModule.base.add(row.returnRva).equals(this.returnAddress));
        if (!parent) return;
        let before;
        let data;
        try {
          before = state(args[0]);
          if (!before.coherentSingleSpan || before.totalLength !== CONFIG.source.length || before.totalLength > CONFIG.maxSourceBytes) return;
          data = ptr(before.sourceBase).readByteArray(before.totalLength);
        } catch (error) { emit({kind: 'source-copy-error', error: String(error)}); return; }
        const record = {id: ++observations, thread: this.thread, fieldName: parent.fieldName,
          memberIndex: parent.memberIndex, reader: args[0], before};
        active.set(this.thread, record);
        this.record = record;
        sourceCopied = true;
        emit({kind: 'source-copy', id: record.id, before}, data);
        emit({kind: 'readvalue-enter', id: record.id, fieldName: record.fieldName,
          memberIndex: record.memberIndex, before, methodInfo: context(args[1])});
        return;
      }
      const record = active.get(this.thread);
      if (!record) return;
      if (hook.callerRanges && !hook.callerRanges.some(([start, end]) =>
          this.returnAddress.compare(gameModule.base.add(start)) >= 0 &&
          this.returnAddress.compare(gameModule.base.add(end)) < 0)) return;
      this.record = record;
      const registers = [0, 1, 2, 3].map(index => args[index].toString());
      const callerRva = this.returnAddress.sub(gameModule.base).toString();
      if (hook.role === 'provider') {
        emit({kind: 'provider-enter', id: record.id, registers, callerRva, providerInput: raw(args[0])});
      } else if (hook.role === 'dispatch') {
        emit({kind: 'dispatch-enter', id: record.id, registers, callerRva, formatterObject: object(args[1]),
          readerMatches: args[2].equals(record.reader)});
      } else {
        const matchingReaderArguments = [0, 1, 2, 3].filter(index => args[index].equals(record.reader));
        emit({kind: 'candidate-child-enter', id: record.id, childKind: hook.childKind,
          methodIndex: hook.methodIndex, methodName: hook.methodName, registers, callerRva, matchingReaderArguments,
          cursor: state(record.reader)});
      }
    },
    onLeave(retval) {
      const record = this.record;
      if (!record) return;
      try {
        if (hook.role === 'readvalue') {
          emit({kind: 'readvalue-leave', id: record.id, fieldName: record.fieldName,
            returnedValue: retval.toString(), after: state(record.reader)});
          active.delete(this.thread);
        } else if (hook.role === 'provider') {
          emit({kind: 'provider-leave', id: record.id, returnedObject: object(retval)});
        } else if (hook.role === 'child') {
          emit({kind: 'candidate-child-leave', id: record.id, childKind: hook.childKind,
            methodIndex: hook.methodIndex, returnedValue: retval.toString(), cursor: state(record.reader)});
        }
      } catch (error) {
        emit({kind: 'observation-error', id: record.id, error: String(error)});
        if (hook.role === 'readvalue') active.delete(this.thread);
      }
    }
  }));
}
emit({kind: 'observer-ready', hooks: hooks.length, sourceLength: CONFIG.source.length});
rpc.exports = {stop() {
  stopping = true;
  const inFlight = active.size;
  for (const hook of hooks) hook.detach();
  Interceptor.flush();
  return {status: inFlight === 0 ? 'hooks-detached-quiescent' : 'hooks-detached-incomplete', inFlight,
    observations, events, sourceCopied, capExceeded};
}};
