"""Audit a bounded Windows minidump offline, without attaching to a process.

This proves stored framing, exception/context values and module-range membership.
Raw stack values are not unwound frames. Missing memory never establishes a
former allocation owner, an unloaded code target, a crash cause or a repair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any

if __name__ == "__main__" and not __package__:
    raise SystemExit("run as: python -m scripts.webui.story_recovery.audit_capture_crash_dump")

from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.capture-crash-dump-audit.v1"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_INPUT_BUDGET = 512 * 1024 * 1024
MAX_ENTRIES = 4096
MAX_STRING_BYTES = 65536
MAX_CONTEXT_BYTES = 65536
MAX_STACK_WORDS = 16
STREAM_NAMES = {3: "ThreadList", 4: "ModuleList", 5: "MemoryList", 6: "Exception",
                7: "SystemInfo", 9: "Memory64List", 14: "UnloadedModuleList",
                15: "MiscInfo", 16: "MemoryInfoList"}
PRIMARY_SOURCES = {
    "header": "https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_header",
    "exception": "https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_exception_stream",
    "exceptionParameter8": "https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-exception_record",
    "amd64Context": "https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-context",
    "modules": "https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_module",
    "unloadedModules": "https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_unloaded_module_list",
    "threads": "https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_thread",
    "streamTypes": "https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ne-minidumpapiset-minidump_stream_type",
}


class DumpAuditError(ValueError):
    def __init__(self, check: str, expected: Any, actual: Any, *, offset: int | None = None):
        self.diagnostic = {"check": check, "expected": expected, "actual": actual}
        if offset is not None:
            self.diagnostic["offset"] = hex(offset)
        super().__init__(f"{check}: expected={expected!r}, actual={actual!r}")


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _utc(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")


class _Dump:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.streams: dict[int, tuple[int, int]] = {}
        self.regions: list[tuple[int, int, str]] = []
        self.memory: list[tuple[int, int, int, str]] = []
        self.modules: list[dict[str, Any]] = []

    def span(self, offset: int, size: int, label: str) -> bytes:
        if not 0 <= offset <= len(self.raw) or not 0 <= size <= len(self.raw) - offset:
            raise DumpAuditError(label + ".span", f"within {len(self.raw)} input bytes",
                                 {"start": offset, "size": size}, offset=offset)
        return self.raw[offset:offset + size]

    def unpack(self, fmt: str, offset: int, label: str) -> tuple:
        return struct.unpack(fmt, self.span(offset, struct.calcsize(fmt), label))

    def region(self, offset: int, size: int, label: str, *, alias: bool = False) -> None:
        self.span(offset, size, label)
        if not size:
            return
        for start, end, other in self.regions:
            if offset < end and start < offset + size:
                if alias and start == offset and end == offset + size and other == label:
                    return
                raise DumpAuditError("fileRegion.overlap", "disjoint stored structures",
                                     {"first": other, "second": label}, offset=offset)
        self.regions.append((offset, offset + size, label))

    def stream(self, kind: int, minimum: int) -> tuple[int, int]:
        size, offset = self.streams[kind]
        if size < minimum:
            raise DumpAuditError(f"stream.{kind}.size", f">={minimum}", size, offset=offset)
        return size, offset

    def count(self, count: int, size: int, header: int, stride: int, label: str) -> None:
        if count > MAX_ENTRIES or header + count * stride > size:
            raise DumpAuditError(label + ".count", {"maximum": MAX_ENTRIES, "tableBytes": size}, count)

    def string(self, offset: int) -> str:
        size, = self.unpack("<I", offset, "string")
        if size > MAX_STRING_BYTES or size % 2:
            raise DumpAuditError("string.size", f"even and <= {MAX_STRING_BYTES}", size, offset=offset)
        self.region(offset, size + 4, "string", alias=True)
        try:
            return self.span(offset + 4, size, "string").decode("utf-16-le")
        except UnicodeDecodeError as exc:
            raise DumpAuditError("string.utf16", "valid UTF-16LE", "invalid code units", offset=offset) from exc

    def resolve(self, address: int, modules: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
        return [{"name": row["name"], "moduleRva": hex(address - int(row["base"], 16))}
                for row in (self.modules if modules is None else modules)
                if int(row["base"], 16) <= address < int(row["endExclusive"], 16)]

    def context(self, size: int, offset: int, architecture: int | None,
                *, decode_registers: bool = True) -> dict[str, Any]:
        if not size:
            if offset:
                raise DumpAuditError("context.absent", "zero size and RVA", offset)
            return {"status": "absent", "size": 0, "rva": "0x0"}
        if not 0 < size <= MAX_CONTEXT_BYTES:
            raise DumpAuditError("context.size", f"0..{MAX_CONTEXT_BYTES}", size, offset=offset)
        self.region(offset, size, "context", alias=True)
        result: dict[str, Any] = {"size": size, "rva": hex(offset),
                                  "sha256": _digest(self.span(offset, size, "context"))}
        if architecture != 9:
            return {**result, "status": "architecture unsupported", "processorArchitecture": architecture}
        if size < 256:
            raise DumpAuditError("amd64Context.size", ">=256", size, offset=offset)
        flags, = self.unpack("<I", offset + 48, "context.flags")
        if flags & 0x100000 != 0x100000:
            raise DumpAuditError("amd64Context.flags", "AMD64 architecture bit", hex(flags), offset=offset + 48)
        if not decode_registers:
            return {**result, "status": "stored", "contextFlags": hex(flags)}
        # CONTROL and INTEGER bits authorize the corresponding stored registers.
        registers = dict(zip(("rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
                              "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "rip"),
                             self.unpack("<17Q", offset + 120, "context.registers")))
        authorized = {key: value for key, value in registers.items()
                      if (flags & 1 if key in {"rsp", "rip"} else flags & 2)}
        return {**result, "status": "decoded", "contextFlags": hex(flags),
                "registers": {key: hex(value) for key, value in authorized.items()},
                "registerLoadedModuleMatches": {key: self.resolve(value) for key, value in authorized.items()
                                                if self.resolve(value)}}

    def add_memory(self, address: int, size: int, offset: int, source: str) -> None:
        self.span(offset, size, source)
        if address + size > 1 << 64:
            raise DumpAuditError("memory.virtualRange", "within uint64 address space", hex(address + size))
        if size:
            # Shared/contained snapshots are legal; disagreeing aliases fail when read.
            if any(offset < end and start < offset + size for start, end, _ in self.regions):
                raise DumpAuditError("memory.structureOverlap", "memory outside stored structures", source, offset=offset)
            self.memory.append((address, size, offset, source))

    def read_memory(self, address: int, size: int) -> bytes | None:
        snapshots = [self.span(offset + address - base, size, source)
                     for base, length, offset, source in self.memory
                     if base <= address and address + size <= base + length]
        if not snapshots:
            return None
        selected = snapshots[0]
        for base, length, offset, source in self.memory:
            start, end = max(address, base), min(address + size, base + length)
            if start < end and self.span(offset + start - base, end - start, source) != selected[start - address:end - address]:
                raise DumpAuditError("memory.aliasMismatch", "equal overlapping samples", hex(start))
        return selected


def audit_dump_bytes(raw: bytes) -> dict[str, Any]:
    """Parse one immutable snapshot; no disk files, process or symbol lookup."""
    dump = _Dump(raw)
    signature, version, count, directory_rva, checksum, timestamp, flags = dump.unpack("<6IQ", 0, "header")
    if signature != 0x504D444D or version & 0xffff != 0xa793:
        raise DumpAuditError("header.signatureVersion", "MDMP and MINIDUMP_VERSION",
                             {"signature": hex(signature), "version": hex(version)})
    if count > MAX_ENTRIES:
        raise DumpAuditError("header.streamCount", f"<={MAX_ENTRIES}", count)
    dump.region(0, 32, "header")
    dump.region(directory_rva, count * 12, "directory")
    directory = []
    for index in range(count):
        kind, size, offset = dump.unpack("<III", directory_rva + 12 * index, "directory")
        dump.span(offset, size, "stream")
        directory.append({"type": kind, "name": STREAM_NAMES.get(kind, "opaque"), "size": size, "rva": hex(offset)})
        if not kind:
            if size or offset:
                raise DumpAuditError("unusedStream", "zero size and RVA", {"size": size, "rva": offset})
            continue
        if kind in dump.streams:
            raise DumpAuditError("directory.duplicateType", "unique nonzero stream type", kind)
        dump.region(offset, size, f"stream.{kind}")
        dump.streams[kind] = (size, offset)

    architecture = None
    if 7 in dump.streams:
        _, offset = dump.stream(7, 56)
        architecture, = dump.unpack("<H", offset, "system.architecture")

    if 4 in dump.streams:
        size, offset = dump.stream(4, 4)
        count, = dump.unpack("<I", offset, "modules")
        dump.count(count, size, 4, 108, "modules")
        for index in range(count):
            base, length, module_checksum, module_timestamp, name_rva = dump.unpack("<QIIII", offset + 4 + index * 108, "module")
            if not length or base + length > 1 << 64:
                raise DumpAuditError("module.virtualRange", "positive size within uint64", {"base": hex(base), "size": length})
            dump.modules.append({"name": dump.string(name_rva), "base": hex(base), "size": length,
                                 "endExclusive": hex(base + length), "checksum": hex(module_checksum),
                                 "timeDateStamp": hex(module_timestamp)})
        ordered = sorted(dump.modules, key=lambda row: int(row["base"], 16))
        for first, second in zip(ordered, ordered[1:]):
            if int(first["endExclusive"], 16) > int(second["base"], 16):
                raise DumpAuditError("loadedModules.overlap", "disjoint image ranges", [first["name"], second["name"]])

    unloaded: dict[str, Any] = {"status": "stream absent"}
    if 14 in dump.streams:
        size, offset = dump.stream(14, 12)
        header_size, entry_size, count = dump.unpack("<III", offset, "unloadedModules")
        if header_size < 12 or entry_size < 24:
            raise DumpAuditError("unloadedModules.layout", "header>=12 and entry>=24", [header_size, entry_size])
        dump.count(count, size, header_size, entry_size, "unloadedModules")
        rows = []
        for index in range(count):
            base, length, module_checksum, module_timestamp, name_rva = dump.unpack("<QIIII", offset + header_size + index * entry_size, "unloadedModule")
            if not length or base + length > 1 << 64:
                raise DumpAuditError("unloadedModule.virtualRange", "positive size within uint64", {"base": hex(base), "size": length})
            rows.append({"name": dump.string(name_rva), "base": hex(base), "size": length,
                         "endExclusive": hex(base + length), "checksum": hex(module_checksum), "timeDateStamp": hex(module_timestamp)})
        unloaded = {"status": "parsed", "count": count, "rows": rows,
                    "evidenceBoundary": "Recorded unloaded ranges may overlap reused addresses; membership alone is not fault attribution."}

    exception: dict[str, Any] = {"status": "stream absent"}
    exception_thread_id = None
    if 6 in dump.streams:
        _, offset = dump.stream(6, 168)
        exception_thread_id, = dump.unpack("<I", offset, "exception.thread")
        code, exception_flags, chain, address, count, _ = dump.unpack("<IIQQII", offset + 8, "exception")
        if count > 15:
            raise DumpAuditError("exception.parameterCount", "<=15", count)
        parameters = dump.unpack("<15Q", offset + 40, "exception.parameters")[:count]
        context_size, context_rva = dump.unpack("<II", offset + 160, "exception.context")
        operation = {0: "read", 1: "write", 8: "execute / user-mode DEP"}.get(parameters[0], "unclassified") if code == 0xc0000005 and parameters else "unclassified"
        exception = {"status": "parsed", "threadId": exception_thread_id, "code": hex(code),
                     "flags": hex(exception_flags), "chainedRecordPointer": hex(chain),
                     "address": hex(address), "parameters": [hex(value) for value in parameters],
                     "accessOperation": operation, "loadedModuleMatches": dump.resolve(address),
                     "unloadedModuleMatches": dump.resolve(address, unloaded.get("rows", [])),
                     "context": dump.context(context_size, context_rva, architecture)}

    thread_count, stack_count, exception_thread = None, 0, None
    thread_stacks = []
    if 3 in dump.streams:
        size, offset = dump.stream(3, 4)
        thread_count, = dump.unpack("<I", offset, "threads")
        dump.count(thread_count, size, 4, 48, "threads")
        ids = set()
        for index in range(thread_count):
            row_offset = offset + 4 + index * 48
            tid, suspend, priority_class, priority = dump.unpack("<4I", row_offset, "thread")
            if tid in ids:
                raise DumpAuditError("threads.duplicateId", "unique thread ID", tid)
            ids.add(tid)
            teb, base, length, rva, context_size, context_rva = dump.unpack("<QQIIII", row_offset + 16, "thread")
            stored_context = dump.context(context_size, context_rva, architecture,
                                          decode_registers=tid == exception_thread_id)
            thread_stacks.append((base, length, rva, f"thread.{tid}.stack"))
            stack_count += int(bool(length))
            if tid == exception_thread_id:
                exception_thread = {"threadId": tid, "teb": hex(teb), "suspendCount": suspend,
                                    "priorityClass": priority_class, "priority": priority,
                                    "stack": {"base": hex(base), "size": length, "rva": hex(rva)},
                                    "threadListContext": stored_context}
        if exception_thread_id is not None and exception_thread is None:
            raise DumpAuditError("exception.threadMembership", "exception thread in ThreadList", exception_thread_id)

    memory_count, memory64_count = None, None
    if 5 in dump.streams:
        size, offset = dump.stream(5, 4)
        memory_count, = dump.unpack("<I", offset, "memory")
        dump.count(memory_count, size, 4, 16, "memory")
        for index in range(memory_count):
            base, length, rva = dump.unpack("<QII", offset + 4 + index * 16, "memory")
            dump.add_memory(base, length, rva, f"MemoryList.{index}")
    if 9 in dump.streams:
        size, offset = dump.stream(9, 16)
        memory64_count, data_rva = dump.unpack("<QQ", offset, "memory64")
        dump.count(memory64_count, size, 16, 16, "memory64")
        for index in range(memory64_count):
            base, length = dump.unpack("<QQ", offset + 16 + index * 16, "memory64")
            dump.add_memory(base, length, data_rva, f"Memory64List.{index}")
            data_rva += length
    for values in thread_stacks:
        dump.add_memory(*values)

    misc: dict[str, Any] = {"status": "stream absent"}
    if 15 in dump.streams:
        size, offset = dump.stream(15, 24)
        info_size, misc_flags, pid, creation, user, kernel = dump.unpack("<6I", offset, "misc")
        if not 24 <= info_size <= size:
            raise DumpAuditError("misc.size", f"24..{size}", info_size)
        misc = {"status": "parsed", "flags": hex(misc_flags), "processId": pid if misc_flags & 1 else None,
                "processCreateUtc": _utc(creation) if misc_flags & 2 else None,
                "processUserSeconds": user if misc_flags & 2 else None,
                "processKernelSeconds": kernel if misc_flags & 2 else None}

    evidence: dict[str, Any] = {"threadCount": thread_count, "nonemptyThreadStacks": stack_count,
                               "memoryListRangeCount": memory_count, "memory64ListRangeCount": memory64_count,
                               "memoryInfoListStreamPresent": 16 in dump.streams,
                               "memoryProtectionAnalysis": "not decoded",
                               "exceptionStackBytesPresent": bool(exception_thread and exception_thread["stack"]["size"]),
                               "stackUnwind": "not attempted; raw values are not verified frames",
                               "faultInstructionBytes": None, "rawStackAtRsp": []}
    if exception.get("status") == "parsed":
        registers = exception["context"].get("registers", {})
        exception["contextRipEqualsExceptionAddress"] = (int(registers["rip"], 16) == int(exception["address"], 16)
                                                        if "rip" in registers else None)
        if "rip" in registers:
            code_bytes = dump.read_memory(int(registers["rip"], 16), 16)
            evidence["faultInstructionBytes"] = code_bytes.hex() if code_bytes is not None else None
        if "rsp" in registers:
            rsp = int(registers["rsp"], 16)
            for index in range(MAX_STACK_WORDS):
                word = dump.read_memory(rsp + index * 8, 8)
                if word is None:
                    break
                value, = struct.unpack("<Q", word)
                evidence["rawStackAtRsp"].append({"offsetFromRsp": index * 8, "value": hex(value),
                                                  "loadedModuleMatches": dump.resolve(value)})
    return {"schema": SCHEMA, "status": "parsed", "diagnostics": [],
            "header": {"version": hex(version), "checksum": hex(checksum), "flags": hex(flags),
                       "dumpUtc": _utc(timestamp), "streamCount": len(directory)},
            "streamDirectory": directory, "system": {"processorArchitecture": architecture},
            "miscInfo": misc, "exception": exception, "exceptionThread": exception_thread,
            "loadedModules": {"status": "parsed" if 4 in dump.streams else "stream absent",
                              "count": len(dump.modules), "rows": dump.modules},
            "unloadedModules": unloaded, "memoryEvidence": evidence, "primarySources": PRIMARY_SOURCES,
            "evidenceBoundary": {
                "direct": "Stored exception/context values and listed module-range membership only.",
                "unresolved": "Raw stack values are not unwound frames. Absent memory cannot identify code, protection, former allocation ownership, crash cause or a verified repair."}}


def compare_dbghelp(raw: bytes, directory: list[dict[str, Any]]) -> dict[str, Any]:
    """Optional Windows directory cross-check; no process access or symbols."""
    if sys.platform != "win32":
        return {"status": "unavailable", "reason": "DbgHelp comparison requires Windows"}
    import ctypes
    try:
        library = ctypes.WinDLL("dbghelp", use_last_error=True)
        read = library.MiniDumpReadDumpStream
        read.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
                         ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint32)]
        read.restype = ctypes.c_int
        buffer = ctypes.create_string_buffer(raw)
        checks = []
        for row in directory:
            if not row["type"]:
                continue
            directory_ptr, stream_ptr, size = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_uint32()
            success = bool(read(buffer, row["type"], ctypes.byref(directory_ptr), ctypes.byref(stream_ptr), ctypes.byref(size)))
            match = success and size.value == row["size"] and stream_ptr.value - ctypes.addressof(buffer) == int(row["rva"], 16)
            checks.append({"streamType": row["type"], "matches": match})
        return {"status": "matched" if all(row["matches"] for row in checks) else "mismatched", "rows": checks}
    except (OSError, AttributeError) as exc:
        return {"status": "unavailable", "reason": str(exc)[:512]}


def read_snapshot(path: Path, max_input_bytes: int) -> bytes:
    if type(max_input_bytes) is not int or not 1 <= max_input_bytes <= MAX_INPUT_BUDGET:
        raise DumpAuditError("input.budget", f"1..{MAX_INPUT_BUDGET}", max_input_bytes)
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        raw = handle.read(max_input_bytes + 1)
        after = os.fstat(handle.fileno())
    if len(raw) > max_input_bytes:
        raise DumpAuditError("input.size", f"<={max_input_bytes}", len(raw))
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if identity(before) != identity(after) or len(raw) != after.st_size:
        raise DumpAuditError("input.changed", "one stable immutable snapshot", "changed while reading")
    return raw


def validate_output(output: Path, source: Path) -> Path:
    resolved = output.resolve()
    reports = (REPO_ROOT / "reports").resolve()
    if not resolved.is_relative_to(reports) or resolved == reports or resolved.suffix.lower() != ".json":
        raise ValueError("--output must name a JSON report under the repository reports/ root")
    if resolved == source.resolve() or (resolved.exists() and source.exists() and resolved.samefile(source)):
        raise ValueError("--output aliases --input")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="closed Windows minidump; never a live process")
    parser.add_argument("--output", type=Path, required=True, help="JSON report under reports/")
    parser.add_argument("--max-input-bytes", type=int, default=MAX_INPUT_BYTES)
    parser.add_argument("--compare-dbghelp", action="store_true", help="optional Windows offline directory cross-check")
    args = parser.parse_args(argv)
    try:
        output = validate_output(args.output, args.input)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    raw = None
    try:
        raw = read_snapshot(args.input, args.max_input_bytes)
        report = audit_dump_bytes(raw)
    except DumpAuditError as exc:
        report = {"schema": SCHEMA, "status": "invalid", "diagnostics": [exc.diagnostic]}
    except OSError as exc:
        report = {"schema": SCHEMA, "status": "unavailable", "diagnostics": [{"check": "input.read", "actual": str(exc)[:512]}]}
    report["input"] = {"path": str(args.input.resolve()), "size": len(raw) if raw is not None else None,
                       "sha256": _digest(raw) if raw is not None else None,
                       "maxInputBytes": args.max_input_bytes}
    report["parser"] = {"path": str(Path(__file__).resolve()),
                        "sourceSha256": _digest(Path(__file__).read_bytes())}
    if args.compare_dbghelp and report["status"] == "parsed":
        report["dbgHelpComparison"] = compare_dbghelp(raw, report["streamDirectory"])
        if report["dbgHelpComparison"]["status"] == "mismatched":
            report["status"] = "invalid"
            report["diagnostics"].append({"check": "dbgHelp.directory", "expected": "matched", "actual": "mismatched"})
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    print(f"Crash dump audit {report['status']}: {output}")
    if "dbgHelpComparison" in report:
        print(f"DbgHelp directory comparison: {report['dbgHelpComparison']['status']}")
    if report["diagnostics"]:
        print(json.dumps(report["diagnostics"][0], ensure_ascii=False), file=sys.stderr)
    return 0 if report["status"] == "parsed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
