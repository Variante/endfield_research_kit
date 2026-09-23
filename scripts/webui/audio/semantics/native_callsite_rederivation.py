"""Re-derive the managed audio callsite catalog on the installed build by name.

``managed_literals`` records, for each Wwise Event literal, the managed method
that plays it, how the literal reaches the call, and the playback path. Those
rows were reviewed on one client build and carry its method indexes and
instruction addresses. The names are what survive an update, so this module
re-checks every row on whichever build is installed and publishes only the rows
whose claims still hold, with that build's addresses:

* the consumer method resolves by type and method name;
* the literal is loaded by the consumer itself (its body, split-off ``.pdata``
  fragments or unnamed helpers), by a named method the consumer reaches, or --
  for a selector row -- by an initializer of the selector's type while the
  consumer reads the selector field;
* the playback sink (or the switch method, for custom-state rows) is called by
  the consumer or a method it reaches.

A row that fails a claim is withheld with the reason; it needs a fresh reading,
not a looser check. Instruction addresses that cannot be re-derived by name are
left empty rather than carried over. The reviewed prose beside a row (trigger
role, branch condition) is a reading of the previous build; a verified row
proves the literal and the playback path, not that prose.

The evaluation opens the whole binary, so it is cached under ``reports/`` and
reused only for the same build and the same catalog.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import re
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from scripts.common import check_installed_native_inputs, write_canonical_json
from scripts.repo_paths import REPO_ROOT

SCHEMA = "audioNativeCallsiteRederivation.v1"
DEFAULT_REPORT = REPO_ROOT / "reports" / "audio" / "native_callsite_rederivation.json"
MAX_HELPER_BYTES = 0x800
INITIALIZER_METHODS = (".ctor", ".cctor", "_Init", "Init", "Setup", "Awake", "OnValidate")
_BRANCH = re.compile(r"(?:call|jmp|j[a-z]{1,3}|jcc) 0x([0-9a-f]+)$")
_CALL = re.compile(r"call 0x([0-9a-f]+)$")
# Addresses the verifier re-derives; every other ``*Va`` field of a verified row
# is cleared, because it belongs to the build the row was reviewed on.
_REDERIVED_ADDRESSES = ("methodVa", "literalLoadVa", "playbackCallVa", "playbackSinkVa",
                        "switchMethodVa", "playbackHashCallVa")


def _full(type_name: str, method: str) -> str:
    return f"{type_name}.{method}"


def _split(full: str) -> tuple[str, str]:
    """``Type.Method`` apart, keeping ``.ctor``/``.cctor`` whole."""
    for constructor in (".cctor", ".ctor"):
        if full.endswith("." + constructor):
            return full[: -len(constructor) - 1], constructor
    type_name, _, method = full.rpartition(".")
    return type_name, method


class _Build:
    """Name-addressed bodies plus every audio literal load, for one build."""

    def __init__(self, index: Any) -> None:
        self.index = index
        self.starts = index.sorted_pointers
        self.loads = self._literal_loads()
        self._calls: dict[str, list[tuple[int, list[str]]]] = {}

    def _literal_loads(self) -> dict[str, list[int]]:
        """``literal -> [instruction VA]`` for every ``mov r64, [rip+cell]`` of a string literal."""
        pe, metadata = self.index.pe, self.index.metadata
        literal_section = metadata.sections["stringLiteral"]
        data_section = metadata.sections["stringLiteralData"]
        literal_count = literal_section.size // 8
        pattern = re.compile(rb"[\x48\x4c]\x8b[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]")
        loads: dict[str, list[int]] = defaultdict(list)
        for section in pe.sections:
            if section["name"] not in (".text", "il2cpp"):
                continue
            base = pe.image_base + section["virtualAddress"]
            raw = bytes(pe.buf[section["rawPointer"]:section["rawPointer"] + section["rawSize"]])
            for match in pattern.finditer(raw):
                offset = match.start()
                if offset + 7 > len(raw):
                    continue
                cell = base + offset + 7 + struct.unpack_from("<i", raw, offset + 3)[0]
                try:
                    word = pe.u64_at_va(cell)
                except (ValueError, IndexError, struct.error):
                    continue
                if word > 0xFFFFFFFF or not word & 1 or word >> 29 != 5:
                    continue
                literal_index = (word >> 1) & 0x0FFFFFFF
                if literal_index >= literal_count:
                    continue
                length, start = struct.unpack_from("<ii", metadata.buf, literal_section.offset + literal_index * 8)
                text = metadata.buf[data_section.offset + start:data_section.offset + start + length]
                loads[text.decode("utf-8", "replace").lower()].append(base + offset)
        return loads

    def spans(self, full: str) -> list[tuple[int, int]]:
        """Every overload body of ``full`` with its fragments and unnamed helpers."""
        spans: list[tuple[int, int]] = []
        type_name, method = _split(full)
        for body in self.index.overload_bodies(type_name, method):
            spans.append((body.pointer, body.size))
            for row in body.rows:
                match = _BRANCH.search(str(row.get("text") or ""))
                if not match:
                    continue
                target = int(match.group(1), 16)
                if body.pointer <= target < body.pointer + body.size or target in self.index.names_by_pointer:
                    continue
                if target in self.index.extents and self.index.extents[target] - target <= MAX_HELPER_BYTES:
                    spans.append((target, self.index.extents[target] - target))
        return spans

    def calls(self, full: str) -> list[tuple[int, list[str]]]:
        """``(call VA, callee names)`` across ``full``'s spans; unnamed helpers expose their callees."""
        if full in self._calls:
            return self._calls[full]
        found: list[tuple[int, list[str]]] = []
        for start, size in self.spans(full):
            for row in self.index._decode(start, size):
                match = _CALL.search(str(row.get("text") or ""))
                if not match:
                    continue
                target = int(match.group(1), 16)
                names = self.index.names_of(target)
                if not names and target in self.index.extents and self.index.extents[target] - target <= MAX_HELPER_BYTES:
                    names = sorted({name for _o, name in self.index.callees(self.index._decode(target, self.index.extents[target] - target))})
                found.append((int(str(row.get("va") or "0"), 16), names))
        self._calls[full] = found
        return found

    def reach(self, full: str) -> set[str]:
        """Methods ``full`` calls, and the methods those call."""
        first = {name for _va, names in self.calls(full) for name in names}
        second: set[str] = set()
        for name in first:
            if name in self.index.pointers_by_name:
                second |= {callee for _va, names in self.calls(name) for callee in names}
        return first | second

    def load_in(self, literal: str, full: str) -> int | None:
        spans = self.spans(full)
        for va in self.loads.get(literal.lower(), []):
            if any(start <= va < start + size for start, size in spans):
                return va
        return None

    def loader_methods(self, literal: str) -> set[str]:
        """Named methods whose own body span holds a load of ``literal``."""
        owners = set()
        for va in self.loads.get(literal.lower(), []):
            position = bisect.bisect_right(self.starts, va) - 1
            if position < 0:
                continue
            pointer = self.starts[position]
            if va < pointer + self.index._extent(pointer):
                owners.update(self.index.names_of(pointer))
        return owners


def _method_index(index: Any, full: str) -> int | None:
    pointers = sorted(index.pointers_by_name.get(full) or [])
    if len(pointers) != 1:
        return None
    return (index.names_by_pointer[pointers[0]][0]).get("methodIndex")


def _address(index: Any, full: str | None) -> str | None:
    pointers = sorted(index.pointers_by_name.get(full or "") or [])
    return f"0x{pointers[0]:x}" if len(pointers) == 1 else None


def _resolve_consumer(index: Any, type_name: str, method: str) -> str | None:
    """The consumer's full name on this build.

    A type that moved namespace keeps its own name and nesting, so a missing
    full name falls back to the unique ``Outer+Inner.Method`` suffix; the
    literal and playback claims still have to hold on the body it finds.
    """
    full = _full(type_name, method)
    if full in index.pointers_by_name:
        return full
    resolve = getattr(index, "resolve", None)
    short_type = type_name.rsplit(".", 1)[-1]
    if resolve is None or not short_type:
        return None
    return resolve(f"{short_type.replace('+', '.')}.{method}")


def verify_row(build: _Build, event: str, row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Return the row with this build's addresses, or ``None`` and the reason it is withheld."""
    index = build.index
    consumer = _resolve_consumer(index, str(row.get("consumerType") or ""), str(row.get("consumerMethod") or ""))
    if consumer is None:
        return None, "consumer-missing"
    literal = str(row.get("customStateName") or event)
    source, loader, load_va = "direct", consumer, build.load_in(literal, consumer)
    if load_va is None:
        owners = build.loader_methods(literal)
        reached = sorted(owners & build.reach(consumer))
        selector_type, selector_field = row.get("selectorType"), row.get("selectorField")
        initializers = sorted(
            owner for owner in owners
            if selector_type and _split(owner)[0] in {selector_type, str(selector_type).split("+")[0]}
            and _split(owner)[1] in INITIALIZER_METHODS
        )
        if reached:
            source, loader = "helper", reached[0]
        elif initializers and selector_field:
            try:
                offset = index.field_offset(f"{selector_type}::{selector_field}")
            except Exception:  # the selector field is gone on this build
                return None, "selector-field-missing"
            pattern = re.compile(rf"\[\w+\+0x{offset:x}\]")
            texts = [str(row.get("text") or "") for start, size in build.spans(consumer) for row in index._decode(start, size)]
            if not any(pattern.search(text) and not text.startswith("lea ") for text in texts):
                return None, "selector-field-not-read"
            source, loader = "selectorInitializer", initializers[0]
        else:
            return None, "literal-not-loaded" if not owners else "literal-loaded-elsewhere"
    sink = row.get("switchMethod") or row.get("playbackSink")
    if not sink and "." in str(row.get("playbackCall") or ""):
        sink = row.get("playbackCall")
    call_va = None
    if sink:
        direct = [va for va, names in build.calls(consumer) if sink in names]
        if direct:
            call_va = direct[0]
        elif sink not in build.reach(consumer):
            return None, "sink-not-reached"
    current = dict(row)
    for key in list(current):
        if key.endswith("Va") and key not in _REDERIVED_ADDRESSES:
            current[key] = None
    current.update({
        "methodIndex": _method_index(index, consumer),
        "methodVa": _address(index, consumer),
        "literalLoadVa": f"0x{load_va:x}" if load_va is not None and source == "direct" else None,
        "playbackCallVa": f"0x{call_va:x}" if call_va is not None else None,
        "playbackSinkVa": _address(index, row.get("playbackSink")),
        "switchMethodVa": _address(index, row.get("switchMethod")),
        "playbackHashCallVa": _address(index, row.get("playbackHashCall")),
        "consumerType": _split(consumer)[0],
        "nativeRederivation": {
            "status": "verified",
            **({"consumerMovedFrom": row.get("consumerType")}
               if _split(consumer)[0] != row.get("consumerType") else {}),
            "literalSource": source,
            "literalLoader": loader,
            "branchConditionStatus": "reviewedOnPreviousBuild",
        },
    })
    for key in ("callsiteOffset", "metadataUsageWord", "metadataStringLiteralIndex", "additionalMethodIndex"):
        current.pop(key, None)
    return current, "verified"


# Every spelling a reviewed row uses for a fact of the build it was read on.
_BUILD_KEY_SUFFIXES = ("Va", "VirtualAddress", "MethodIndex", "Token", "Sha256")
_BUILD_KEYS = frozenset({"methodIndex", "token", "virtualAddress", "bodyLength"})


def _clear_addresses(spec: Mapping[str, Any]) -> dict[str, Any]:
    """A copy with every build address and fingerprint of the reviewed build removed."""
    current: dict[str, Any] = {}
    for key, value in spec.items():
        if isinstance(value, list):
            current[key] = [_clear_addresses(item) if isinstance(item, Mapping) else item for item in value]
        elif key.endswith(_BUILD_KEY_SUFFIXES) or key in _BUILD_KEYS:
            current[key] = None
        else:
            current[key] = value
    return current


def verify_enemy_voice_action(build: _Build, spec: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """The static constructor loads each trigger key in voiceType order; OnExecute responds."""
    index = build.index
    consumer = _resolve_consumer(index, str(spec.get("consumerType") or ""), str(spec.get("consumerMethod") or ""))
    if consumer is None:
        return None, "consumer-missing"
    type_name = _split(consumer)[0]
    constructor = f"{type_name}..cctor"
    rows = list(spec.get("voiceTypes") or [])
    loads = [build.load_in(str(row["triggerKey"]), constructor) for row in rows]
    if not loads or any(va is None for va in loads):
        return None, "trigger-key-not-loaded"
    ordered = [row["voiceType"] for _va, row in sorted(zip(loads, rows), key=lambda pair: pair[0])]
    if ordered != sorted(row["voiceType"] for row in rows):
        return None, "trigger-key-order-changed"
    if spec.get("playbackCall") not in build.reach(consumer):
        return None, "sink-not-reached"
    current = _clear_addresses(spec)
    current.update({
        "consumerType": type_name,
        "methodIndex": _method_index(index, consumer),
        "methodVa": _address(index, consumer),
        "playbackCallVa": _address(index, spec.get("playbackCall")),
        "mappingConstructorMethodVa": _address(index, constructor),
    })
    for row, va in zip(current["voiceTypes"], loads):
        row["literalLoadVa"] = f"0x{va:x}"
    current["nativeRederivation"] = {"status": "verified", "claims": [
        "the static constructor loads each trigger key in voiceType order",
        "the consumer reaches playbackCall",
    ]}
    return current, "verified"


def _inlined(build: _Build, target: str, sources: list[str]) -> bool:
    from scripts.webui.mission_pipeline.runtime_contract_native import ChainResolver

    return ChainResolver(build.index).inlined_into(target, sources)


def verify_method_chain(
    build: _Build, spec: Mapping[str, Any], keys: tuple[str, ...]
) -> tuple[dict[str, Any] | None, str]:
    """Each named method is reached by the ones before it (directly, one call down, or inlined)."""
    index = build.index
    chain = [str(spec.get(key) or "") for key in keys]
    missing = [name for name in chain if name not in index.pointers_by_name]
    if missing:
        return None, f"method-missing:{missing[0]}"
    for position in range(1, len(chain)):
        earlier = chain[:position]
        reached = set().union(*(build.reach(name) for name in earlier))
        if chain[position] not in reached and not _inlined(build, chain[position], earlier):
            return None, f"link-missing:{chain[position]}"
    current = _clear_addresses(spec)
    for key, name in zip(keys, chain):
        current[f"{key}Index"] = _method_index(index, name)
        current[f"{key}Va"] = _address(index, name)
    current["nativeRederivation"] = {"status": "verified", "claims": ["each chain method reaches the next"]}
    return current, "verified"


def verify_overloads_call(build: _Build, spec: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Every overload of a composite consumer (``M(a) / M(b)``) calls the playback method."""
    index = build.index
    first = str(spec.get("consumerMethod") or "").split(" / ")[0]
    method = first.split("(")[0].strip()
    consumer = _resolve_consumer(index, str(spec.get("consumerType") or ""), method)
    if consumer is None:
        return None, "consumer-missing"
    bodies = index.overload_bodies(*_split(consumer))
    if len(bodies) < 2:
        return None, "overload-missing"
    for body in bodies:
        rows = index.body_with_fragments(body)
        if spec.get("playbackCall") not in {name for _offset, name in index.callees(rows)}:
            return None, "sink-not-reached"
    current = _clear_addresses(spec)
    current.update({
        "consumerType": _split(consumer)[0],
        "methodVa": f"0x{bodies[0].pointer:x}",
        "additionalMethodVa": f"0x{bodies[1].pointer:x}",
        "playbackCallVa": _address(index, spec.get("playbackCall")),
        "nativeRederivation": {"status": "verified", "claims": ["every overload calls playbackCall"]},
    })
    return current, "verified"


def _verify_ai_bark(build: _Build, spec: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    return verify_method_chain(build, spec, (
        "barkSystemMethod", "postActionMethod", "managerPostMethod",
        "managerDispatchMethod", "voicePostMethod", "voiceBarkEntryMethod",
    ))


def _token(index: Any, full: str | None) -> str | None:
    pointers = sorted(index.pointers_by_name.get(full or "") or [])
    return str(index.names_by_pointer[pointers[0]][0].get("token") or "") or None if len(pointers) == 1 else None


def _immediate_loaded(build: _Build, full: str, value: int) -> bool:
    """Whether ``full`` (with fragments and helpers) moves ``value`` into a register."""
    wanted = {f"0x{value & 0xFFFFFFFF:x}", str(value)}
    for start, size in build.spans(full):
        for row in build.index._decode(start, size):
            parts = str(row.get("text") or "").split(", ")
            if len(parts) == 2 and parts[0].startswith("mov ") and parts[1] in wanted:
                return True
    return False


def _call_to(build: _Build, caller: str, target: str) -> int | None:
    for va, names in build.calls(caller):
        if target in names:
            return va
    return None


def _enum_members(build: _Build, enum_type: str) -> list[str] | None:
    index = build.index
    type_def = index.types.get(enum_type)
    if type_def is None:
        return None
    fields = index.metadata.fields_for(type_def) if hasattr(index.metadata, "fields_for") else None
    if fields is None:
        return None
    names = [index.metadata.string(field.name_index) for field in fields]
    return [name for name in names if name != "value__"]


def _fnv1_lower(name: str) -> int:
    value = 0x811C9DC5
    for code_unit in name.lower().encode("utf-16-le")[::2]:
        value = ((value * 0x01000193) & 0xFFFFFFFF) ^ code_unit
    return value


def verify_music_state_groups(build: _Build, groups: Any) -> tuple[list[dict[str, Any]], str]:
    """Each group's setter by name, its enum members from metadata, its callsites by body.

    A static callsite holds when its caller moves the value id into a register
    and calls the setter; a runtime callsite when the caller calls the setter.
    A callsite that no longer holds is dropped, and a group whose setter is gone
    keeps its enum values but carries no native fields.
    """
    index = build.index
    current_groups: list[dict[str, Any]] = []
    for group in groups:
        row = _clear_addresses(group)
        row.pop("binaryEvidence", None)
        owner = str(group.get("enumType") or "").split("+")[0]
        setter = f"{owner}.{group.get('setterMethod')}"
        members = _enum_members(build, str(group.get("enumType") or ""))
        if members is not None:
            reviewed = {value["member"]: value for value in group.get("values") or ()}
            row["values"] = [
                dict(reviewed[name]) if name in reviewed and reviewed[name].get("valueId") == _fnv1_lower(name)
                else {"member": name, "hashInput": name.lower(), "valueId": _fnv1_lower(name),
                      "valueIdHex": f"0x{_fnv1_lower(name):08x}",
                      "resolution": "exactCurrentMetadataEnumMemberFNV1Utf16Hash"}
                for name in members
            ]
        if setter not in index.pointers_by_name:
            row.update({"staticValueCallsites": [], "runtimeValueCallsites": [],
                        "nativeRederivation": {"status": "setter-missing"}})
            current_groups.append(row)
            continue
        row.update({"methodIndex": _method_index(index, setter), "token": _token(index, setter),
                    "virtualAddress": _address(index, setter)})
        static_rows, dropped = [], 0
        for callsite in group.get("staticValueCallsites") or ():
            caller = f"{owner}.{callsite.get('callerMethod')}"
            call_va = _call_to(build, caller, setter) if caller in index.pointers_by_name else None
            if call_va is None or not _immediate_loaded(build, caller, int(callsite.get("valueId") or 0)):
                dropped += 1
                continue
            static_rows.append({**_clear_addresses(callsite), "callerMethodIndex": _method_index(index, caller),
                                "callVirtualAddress": f"0x{call_va:x}"})
        runtime_rows = []
        for callsite in group.get("runtimeValueCallsites") or ():
            caller = f"{owner}.{callsite.get('callerMethod')}"
            call_va = _call_to(build, caller, setter) if caller in index.pointers_by_name else None
            if call_va is None:
                dropped += 1
                continue
            runtime_rows.append({**_clear_addresses(callsite), "callerMethodIndex": _method_index(index, caller),
                                 "callVirtualAddress": f"0x{call_va:x}"})
        row.update({"staticValueCallsites": static_rows, "runtimeValueCallsites": runtime_rows,
                    "nativeRederivation": {"status": "verified", "droppedCallsites": dropped,
                                           "enumMembers": "installedMetadata" if members is not None else "reviewed"}})
        current_groups.append(row)
    return current_groups, "verified"


def verify_selector_groups(build: _Build, groups: Any) -> tuple[list[dict[str, Any]], str]:
    """Re-prove each selector group's native setter; drop the setter when it no longer holds."""
    index = build.index
    current_groups: list[dict[str, Any]] = []
    for group in groups:
        setter_spec = group.get("runtimeSetter")
        if not setter_spec:
            current_groups.append(dict(group))
            continue
        row = dict(group)
        caller_type = str(setter_spec.get("callerType") or "")
        setter = str(setter_spec.get("setter") or "").split("(")[0]
        current = _clear_addresses(setter_spec)
        holds = setter in index.pointers_by_name
        if holds and setter_spec.get("callerMethod"):
            caller = f"{caller_type}.{setter_spec['callerMethod']}"
            call_va = _call_to(build, caller, setter) if caller in index.pointers_by_name else None
            holds = call_va is not None
            if holds:
                current.update({"callerMethodIndex": _method_index(index, caller), "callerToken": _token(index, caller),
                                "setSwitchCallVirtualAddress": f"0x{call_va:x}"})
                source = setter_spec.get("audioObjectIdSource") or {}
                if source.get("method") in index.pointers_by_name:
                    current["audioObjectIdSource"] = {**_clear_addresses(source),
                                                      "methodIndex": _method_index(index, source["method"]),
                                                      "token": _token(index, source["method"]),
                                                      "virtualAddress": _address(index, source["method"])}
        if holds and setter_spec.get("calls"):
            calls = []
            for call in setter_spec["calls"]:
                caller = f"{caller_type}.{call.get('method')}"
                reached = caller in index.pointers_by_name and setter in build.reach(caller)
                if not reached or not _immediate_loaded(build, caller, int(call.get("valueId") or 0)):
                    holds = False
                    break
                call_va = _call_to(build, caller, setter)
                calls.append({**_clear_addresses(call),
                              "setStateCallVirtualAddress": f"0x{call_va:x}" if call_va is not None else None})
            if holds:
                current["calls"] = calls
                current.update({"setterMethodIndex": _method_index(index, setter), "setterToken": _token(index, setter),
                                "setterVirtualAddress": _address(index, setter)})
        resolver = group.get("valueResolver")
        if holds and resolver:
            full = f"{caller_type}.{resolver.get('method')}"
            row["valueResolver"] = ({**_clear_addresses(resolver), "methodIndex": _method_index(index, full),
                                     "token": _token(index, full), "virtualAddress": _address(index, full)}
                                    if full in index.pointers_by_name else None)
        if holds:
            row["runtimeSetter"] = {**current, "nativeRederivation": {"status": "verified"}}
        else:
            row.pop("runtimeSetter", None)
            row.pop("valueResolver", None)
            row["runtimeObservationStatus"] = "nativeSetterNotReprovedOnInstalledBuild"
        current_groups.append(row)
    return current_groups, "verified"


ROUTE_VERIFIERS = {
    "musicStateGroups": verify_music_state_groups,
    "selectorGroups": verify_selector_groups,
    "enemyVoiceAction": verify_enemy_voice_action,
    "aiBark": _verify_ai_bark,
    "animationVoiceTrigger": verify_overloads_call,
}


def _catalog_digest(catalogs: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(catalogs, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def rederive_catalogs(
    catalogs: Mapping[str, Mapping[str, Mapping[str, Any]]],
    *,
    routes: Mapping[str, Mapping[str, Any]] | None = None,
    report_path: Path = DEFAULT_REPORT,
    index_factory: Any = None,
) -> dict[str, Any]:
    """Verified rows per catalog plus the audit, for the installed build.

    ``catalogs`` maps a catalog name to its ``{event: row}`` table. Without an
    installed build nothing is verified and every catalog is empty.
    """
    native = check_installed_native_inputs()
    if not native.validated:
        return {"status": native.status, "detail": native.detail, "catalogs": {name: {} for name in catalogs},
                "routes": {name: None for name in routes or {}}, "withheld": {}}
    key = {
        "_schema": SCHEMA,
        "catalogSha256": _catalog_digest({"catalogs": catalogs, "routes": routes or {}}),
        # The verifier is an input of the report too: a changed rule re-evaluates.
        "verifierSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "gameAssemblySha256": native.gameassembly_sha256.upper(),
        "globalMetadataSha256": native.metadata_sha256.upper(),
    }
    try:
        cached = json.loads(Path(report_path).read_bytes())
    except (OSError, ValueError):
        cached = {}
    if isinstance(cached, dict) and all(cached.get(k) == v for k, v in key.items()):
        return {"status": "validated", **cached}
    if index_factory is None:
        from scripts.game_data.il2cpp.body_claims import BodyIndex
        from scripts.game_data.il2cpp.native_image import open_native_image

        def index_factory():
            return BodyIndex(open_native_image(native.gameassembly, native.metadata))
    build = _Build(index_factory())
    verified: dict[str, dict[str, Any]] = {}
    withheld: dict[str, dict[str, str]] = {}
    for name, rows in catalogs.items():
        verified[name], withheld[name] = {}, {}
        for event, row in rows.items():
            current, reason = verify_row(build, event, row)
            if current is None:
                withheld[name][event] = reason
            else:
                verified[name][event] = current
    current_routes: dict[str, Any] = {}
    for name, spec in (routes or {}).items():
        current, reason = ROUTE_VERIFIERS[name](build, spec)
        current_routes[name] = current
        if current is None:
            withheld.setdefault("routes", {})[name] = reason
    result = {**key, "catalogs": verified, "routes": current_routes, "withheld": withheld}
    write_canonical_json(Path(report_path), result)
    return {"status": "validated", **result}


def reviewed_routes() -> dict[str, Mapping[str, Any]]:
    """The native routes and group catalogs this module re-derives, as reviewed."""
    from scripts.webui.audio.semantics import build_contracts, native_evidence

    return {
        "enemyVoiceAction": native_evidence.ENEMY_TRIGGER_VOICE_ACTION_NATIVE,
        "aiBark": native_evidence.AI_BARK_NATIVE_RUNTIME,
        "animationVoiceTrigger": native_evidence.ANIMATION_VOICE_TRIGGER_NATIVE,
        "musicStateGroups": build_contracts.AUDIO_MUSIC_NATIVE_STATE_GROUPS,
        "selectorGroups": build_contracts.AUDIO_RUNTIME_SELECTOR_GROUPS,
    }


def reviewed_catalogs() -> dict[str, Mapping[str, Mapping[str, Any]]]:
    """Every callsite catalog this module re-derives, as reviewed.

    Imported here rather than at module load because the catalog owners import
    this module.
    """
    from scripts.webui.audio.semantics import managed_literals, native_evidence

    return {
        "managed": managed_literals.MANAGED_AUDIO_CALLSITE_CONTEXTS,
        "customState": managed_literals.NATIVE_CUSTOM_STATE_CALLSITE_CONTEXTS,
        "voiceTrigger": native_evidence.NATIVE_VOICE_TRIGGER_ROWS,
    }


def current_catalogs(native_context: Any) -> dict[str, dict[str, Any]]:
    """The callsite rows to publish for the build ``native_context`` measured.

    The reviewed rows on the build they were reviewed on; on another installed
    build that the gate measured, the rows re-derived there; otherwise none.
    All catalogs are evaluated together so one cached evaluation serves every
    consumer.
    """
    catalogs = reviewed_catalogs()
    if native_context.validated:
        return {name: dict(rows) for name, rows in catalogs.items()}
    if not (native_context.gate_verified and native_context.status == "mismatched"):
        return {name: {} for name in catalogs}
    result = rederive_catalogs(catalogs, routes=reviewed_routes())
    return {name: dict((result.get("catalogs") or {}).get(name) or {}) for name in catalogs}


def current_routes(native_context: Any) -> dict[str, dict[str, Any] | None]:
    """The native voice routes to publish; ``None`` for a route that does not hold.

    Evaluated in the same cached pass as ``current_catalogs``.
    """
    routes = reviewed_routes()
    if native_context.validated:
        return {name: dict(spec) for name, spec in routes.items()}
    if not (native_context.gate_verified and native_context.status == "mismatched"):
        return {name: None for name in routes}
    result = rederive_catalogs(reviewed_catalogs(), routes=routes)
    return {name: (result.get("routes") or {}).get(name) for name in routes}


def withheld_summary(result: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for name, rows in (result.get("withheld") or {}).items():
        counts: dict[str, int] = defaultdict(int)
        for reason in rows.values():
            counts[reason] += 1
        summary[name] = dict(sorted(counts.items()))
    return summary


__all__ = ["rederive_catalogs", "verify_row", "withheld_summary"]
