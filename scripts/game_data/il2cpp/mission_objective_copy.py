"""Prove complete normal ObjectiveData.Copy loop control and argument flow.

The grammar owns every byte between the unpatched entry and normal cleanup,
including nested backedges and off-line interface fast paths. Selected fields
and passed MethodSpecs bind source/destination references. Callee semantics,
heap aliases, pair field layout, exceptional/fallback paths and live values
remain separate. No selected-build address, hash or registration index lives
here; changed instruction programs fail closed.
"""
from __future__ import annotations

from typing import Any

from .context import unresolved_usage_index, usage_method_spec, rip_qword_load_target
from .packed_pair_current import prove_current_helper, selected_current_type
from .reference_layouts import NativeReferenceContext


class Program:
    """Consume exact instruction forms and bind relocations to local labels."""

    def __init__(self, index: Any, body: Any, start: int) -> None:
        self.index, self.body, self.offset = index, body, start
        self.raw = index.pe.bytes_at_va(body.pointer, body.size)
        self.labels: dict[str, int] = {}
        self.branches: list[tuple[int, int, str | None]] = []
        self.calls: list[dict[str, Any]] = []
        self.variable: set[int] = set()

    def take(self, count: int) -> bytes:
        start = self.offset
        if not 0 <= start <= len(self.raw)-count:
            raise ValueError(f"copy_loop.owner: offset={start} bytes={count} extent={len(self.raw)}")
        self.offset += count
        return self.raw[start:self.offset]

    def fixed(self, hexadecimal: str) -> None:
        expected = bytes.fromhex(hexadecimal)
        start = self.offset
        actual = self.take(len(expected))
        if actual != expected:
            raise ValueError(f"copy_loop.program: offset={start} expected={expected.hex()} actual={actual.hex()}")

    def field(self, prefix: str, qualified: str) -> None:
        self.fixed(prefix)
        offset = self.index.field_offset(qualified)
        if not 0 <= offset < 0x80:
            raise ValueError(f"copy_loop.field: {qualified}: expected small positive displacement actual={offset}")
        self.fixed(bytes([offset]).hex())

    def mark(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"copy_loop.label: duplicate {name}")
        self.labels[name] = self.offset

    def branch(self, opcode: str, label: str | None, width: int = 4) -> None:
        start = self.offset
        self.fixed(opcode)
        at = self.offset
        delta = int.from_bytes(self.take(width), "little", signed=True)
        self.variable.update(range(at, at+width))
        self.branches.append((start, self.offset+delta, label))

    def call(self, symbol: str | None = None) -> int:
        start = self.offset
        self.fixed("e8")
        at = self.offset
        target = self.body.pointer+self.offset+4+int.from_bytes(self.take(4), "little", signed=True)
        self.variable.update(range(at, at+4))
        if symbol and symbol not in self.index.names_of(target):
            raise ValueError(f"copy_loop.call: offset={start} expected={symbol} actual={self.index.names_of(target)[:4]}")
        self.calls.append({"offset": start, "targetVa": hex(target), "symbol": symbol,
                           "calleeSemanticsProved": False})
        return target

    def rip(self, prefix: str) -> int:
        start = self.offset
        self.fixed(prefix)
        at = self.offset
        self.take(4)
        self.variable.update(range(at, at+4))
        return rip_qword_load_target(self.raw[start:self.offset], self.body.pointer+start, source="objective copy")

    def displacement(self, following_bytes: int = 0) -> int:
        at = self.offset
        delta = int.from_bytes(self.take(4), "little", signed=True)
        self.variable.update(range(at, at+4))
        return self.body.pointer+self.offset+following_bytes+delta

    def finish(self, error_start: int) -> None:
        for position, target, label in self.branches:
            if label is None:
                if not error_start <= target < len(self.raw) or self.raw[target] != 0xe8:
                    raise ValueError(f"copy_loop.excluded_error: offset={position} target={target}; expected owned post-epilogue call")
            elif target != self.labels.get(label):
                raise ValueError(f"copy_loop.branch: offset={position} label={label} expected={self.labels.get(label)} actual={target}")


def method_context(index: Any, cell: int, target: int, symbol: str, arguments: list[str], arity: int) -> None:
    """Authenticate the actual usage cell against its physical call target."""
    from .protocol import runtime_type_name
    image, metadata, pe = index.image, index.metadata, index.pe
    base = int(image.registration["methodSpecs"], 16)
    context = usage_method_spec(pe.bytes_at_va(cell, 8), pe.bytes_at_va(base, image.registration["methodSpecsCount"]*12),
        len(metadata.methods), image.instantiations.count, source=str(image.gameassembly), usage_offset=cell, records_offset=base)
    method = metadata.methods[context["definition"]]
    actual = metadata.type_full_name(metadata.types[method.declaring_type])+"."+metadata.string(method.name_index)
    parts = [runtime_type_name(pe, metadata, arg.type_pointer_va)
             for arg in image.instantiations.resolve(context["classInstantiationIndex"]).arguments]
    if (actual != symbol or parts != arguments or method.parameter_count != arity or method.flags & 0x10 or
            context["methodInstantiationIndex"] != -1 or not any(row.get("methodIndex") == context["definition"]
                for row in index.names_by_pointer.get(target, []))):
        raise ValueError(f"copy_loop.method_context: expected={symbol} {arguments}/{arity} actual={actual} {parts}/{method.parameter_count}")


def interface_slot(index: Any, cell: int, owner: str, method_name: str) -> None:
    """Select the nongeneric IEnumerator/IDisposable slot used by this program."""
    from .protocol import runtime_type_name
    image, pe, metadata = index.image, index.pe, index.metadata
    selected = unresolved_usage_index(pe.bytes_at_va(cell, 8), image.registration["typesCount"],
        tag=1, source=str(image.gameassembly), offset=cell)
    pointer = pe.u64_at_va(int(image.registration["types"], 16)+selected*8)
    raw = pe.bytes_at_va(pointer, 16)
    definition = int.from_bytes(raw[:8], "little")
    if raw[10] != 0x12 or not 0 <= definition < len(metadata.types):
        raise ValueError("copy_loop.interface: selected nongeneric class declaration is missing")
    td = metadata.types[definition]
    methods = [row for row in metadata.methods[td.method_start:td.method_start+td.method_count]
               if metadata.string(row.name_index) == method_name]
    if (metadata.type_full_name(td) != owner or not td.flags & 0x20 or len(methods) != 1 or
            methods[0].declaring_type != td.index or methods[0].slot != 0 or methods[0].parameter_count != 0 or
            methods[0].flags & 0x10 or not methods[0].flags & 0x40):
        raise ValueError(f"copy_loop.interface: expected {owner}.{method_name} instance virtual slot zero")
    returned = runtime_type_name(pe,metadata,pe.u64_at_va(int(image.registration["types"],16)+methods[0].return_type*8))
    expected = "bool" if (owner,method_name) == ("System.Collections.IEnumerator","MoveNext") else "void"
    if returned != expected:
        raise ValueError(f"copy_loop.interface_return: {owner}.{method_name}: expected={expected} actual={returned}")


def current(program: Program, pair: list[str], external_cell: int | None = None) -> None:
    helper = program.call()
    end = program.index.extents.get(helper)
    if end is None or end-helper not in (175, 178, 182):
        raise ValueError("copy_loop.current_owner: unsupported current helper extent")
    dispatch = prove_current_helper(program.index.pe.bytes_at_va(helper, end-helper), helper)
    cell = dispatch.get("typeUsageCellVa", external_cell)
    if cell is None or (external_cell is not None and dispatch.get("typeArgumentRegister") != "r8"):
        raise ValueError("copy_loop.current_context: complete helper TypeInfo argument join is missing")
    selected = selected_current_type(program.index, cell)
    if selected["classArguments"] != pair:
        raise ValueError(f"copy_loop.current_context: expected={pair} actual={selected['classArguments']}")


def move_next(program: Program, name: str, receiver: str, padding: str, *, inner: bool = False,
              wide: bool = False, far_fast: bool = False, far_exit: bool = False) -> None:
    """Complete interface search, slot-zero invocation and its Boolean branch."""
    p = program
    p.mark(name+".head"); p.fixed(receiver+"4885ff"); p.branch("0f84", None)
    cell = p.rip("488b35")
    interface_slot(p.index, cell, "System.Collections.IEnumerator", "MoveNext")
    p.fixed("4c8b37498bce"); p.call()  # class initialization; assumed normal
    p.fixed("410fb7c7" if inner else "410fb7cf")
    p.fixed("410fb7963001000066443bfa"); p.branch("73", name+".fallback", 1)
    p.fixed("4d8b86b0000000"+padding)
    p.mark(name+".search")
    p.fixed("0fb7c84803c9493934c8" if inner else "0fb7c14803c0493934c0")
    p.branch("0f84" if far_fast else "74", name+".fast", 4 if far_fast else 1)
    p.fixed("66ffc0663bc2" if inner else "66ffc1663bca"); p.branch("72", name+".search", 1)
    p.mark(name+".fallback"); p.fixed("4533c0488bd6488bcf"); p.call()  # fallback lookup is unproved
    p.fixed("488bd0"); p.mark(name+".invoke")
    p.fixed("488b02488b5208488bcfffd084c0")
    p.branch("0f84" if far_exit else "74", name+".exit", 4 if far_exit else 1)


def fast_slot(program: Program, name: str, *, inner: bool = False, wide: bool = True) -> None:
    p = program
    p.mark(name+".fast")
    p.fixed(("0fb7c8" if inner else "0fb7c9")+"4803c9496354c8084883c21448c1e2044903d6")
    p.branch("e9" if wide else "eb", name+".invoke", 4 if wide else 1)


def cleanup(program: Program, name: str, continuation: str, *, scope: str = "28") -> None:
    p = program
    p.mark(name+".exit"); p.fixed("48833b00"); p.branch("74", name+".skip", 1)
    p.fixed("33c94c8b03")
    cell = p.rip("488b15")
    interface_slot(p.index, cell, "System.IDisposable", "Dispose")
    p.call()  # dispatch helper's disposal effects are a separate obligation
    p.mark(name+".skip"); p.branch("eb", continuation, 1)
    p.mark(name+".finally"); p.fixed("488d4c24"+scope); p.call()
    p.fixed("488b4c24204885c9"); p.branch("0f85", None)


def prove_copy_loops(index: Any, body: Any) -> dict[str, Any]:
    """Own complete normal control flow of values, details and nested hash loops."""
    if body.symbol != "Beyond.Gameplay.MissionSystem+ObjectiveData.Copy":
        raise ValueError("copy_loop.owner: requires the named ObjectiveData.Copy method")
    if index.parameter_location(body.pointer, body.symbol, "src") != ("register", "rdx"):
        raise ValueError("copy_loop.parameter: source must be the selected incoming RDX parameter")
    declarations = [row for row in index.names_by_pointer.get(body.pointer, [])
                    if f"{row.get('type')}.{row.get('method')}" == body.symbol]
    if len(declarations) != 1:
        raise ValueError("copy_loop.declaration: unique caller declaration required")
    method = index.metadata.methods[declarations[0]["methodIndex"]]
    if (method.flags & 0x10 or method.parameter_count != 1 or
            index.metadata.metadata_type_name(index.metadata.parameters_for(method)[0].type_index) != "Proto.QUEST_OBJECTIVE"):
        raise ValueError("copy_loop.signature: instance Copy(Proto.QUEST_OBJECTIVE) required")
    root, dest, detail = "Proto.QUEST_OBJECTIVE::", "Beyond.Gameplay.MissionSystem+ObjectiveData::", "Beyond.Gameplay.MissionSystem+ObjectiveData+ConditionDetail"
    expected_fields = {root+"conditionId_": "string", root+"values_": "Google.Protobuf.Collections.MapField`2<string,int>",
        root+"extraDetails_": "Google.Protobuf.Collections.MapField`2<string,Proto.QUEST_OBJECTIVE_DETAIL>", root+"isComplete_": "bool",
        dest+"conditionId": "string", dest+"values": "System.Collections.Generic.Dictionary`2<string,int>", dest+"isCompleted": "bool",
        dest+"extraDetails": "System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.MissionSystem+ObjectiveData+ConditionDetail>",
        "Proto.QUEST_OBJECTIVE_DETAIL::hashValue_": "Google.Protobuf.Collections.MapField`2<ulong,bool>", detail+"::hashValue": "System.Collections.Generic.Dictionary`2<long,bool>"}
    context = NativeReferenceContext(index.image, index=index)
    for field, expected in expected_fields.items():
        actual = context.field(field)[1]
        if actual != expected:
            raise ValueError(f"copy_loop.field_type: {field}: expected={expected} actual={actual}")

    p = Program(index, body, 0)
    # Saved incoming arguments, nonvolatile aliases and exactly matching frame.
    p.fixed("488954241048894c240853565741544155415641574881ecb00000004c8bea4c8be1")
    # Initialization contains only RCX usage addresses and one repeated call;
    # checked Win64 nonvolatile aliases survive it, conditional on that helper.
    p.fixed("803d"); flag=p.displacement(1); p.fixed("00"); p.branch("0f85","initialized")
    helper=None; count=0
    while p.raw[p.offset:p.offset+3] == bytes.fromhex("488d0d"):
        p.fixed("488d0d"); p.displacement(); target=p.call()
        if helper is not None and target != helper:
            raise ValueError("copy_loop.initialization: expected one repeated usage-resolution helper")
        helper=target; count+=1
        if count>64:
            raise ValueError("copy_loop.initialization: more than 64 usage calls")
    if not count:
        raise ValueError("copy_loop.initialization: no selected usage-resolution calls")
    p.fixed("c605"); written=p.displacement(1); p.fixed("01")
    if written != flag:
        raise ValueError("copy_loop.initialization: flag test/store addresses differ")
    p.mark("initialized")
    p.fixed("4533ff4c89bc24080100004c897c243033d2b9"); p.displacement()  # EAX guard predicate is independent of selected patch ID
    p.call("IFix.WrappersManagerImpl.IsPatched"); p.fixed("84c0"); p.branch("0f85", "patch")
    normal_start = p.offset
    p.fixed("4d85ed"); p.branch("0f84", None)
    p.field("498b45", root+"conditionId_"); p.field("49894424", dest+"conditionId")
    p.field("498d4c24", dest+"conditionId"); p.call()  # reference barrier remains unproved
    p.field("498b5c24", dest+"values"); p.fixed("4885db"); p.branch("0f84", None)
    cell=p.rip("488b15"); p.fixed("488bcb"); target=p.call("System.Collections.Generic.Dictionary`2.Clear")
    method_context(index,cell,target,"System.Collections.Generic.Dictionary`2.Clear",["string","int"],0)
    p.field("498b5d",root+"values_"); p.fixed("4885db"); p.branch("0f84",None)
    cell=p.rip("488b15"); p.fixed("488bcb"); target=p.call("Google.Protobuf.Collections.MapField`2.GetEnumerator")
    method_context(index,cell,target,"Google.Protobuf.Collections.MapField`2.GetEnumerator",["string","int"],0)
    p.fixed("48894424384c897c2420488d5c243848895c24280f1f4000660f1f840000000000")
    move_next(p,"values","488b7c2438","0f1f8000000000")
    p.fixed("4c8b4c24384d85c9"); p.branch("0f84",None); p.fixed("488d4c2458")
    current(p,["string","int"]); p.fixed("0f1008")
    p.field("498b4c24",dest+"values"); p.fixed("4885c9"); p.branch("0f84",None)
    cell=p.rip("4c8b0d"); p.fixed("660f6fc1660f73d80866410f7ec066480f7eca")
    target=p.call("System.Collections.Generic.Dictionary`2.Add")
    method_context(index,cell,target,"System.Collections.Generic.Dictionary`2.Add",["string","int"],2)
    p.branch("e9","values.head"); fast_slot(p,"values",wide=False)
    cleanup(p,"values","root.resume")
    p.fixed("4533ff4c8bac24f80000004c8ba424f0000000"); p.mark("root.resume")
    p.fixed("4d85ed"); p.branch("0f84",None)
    p.field("410fb645",root+"isComplete_"); p.field("41884424",dest+"isCompleted")
    p.field("498b4c24",dest+"extraDetails"); p.fixed("4885c9"); p.branch("0f84",None)
    cell=p.rip("488b15"); target=p.call("System.Collections.Generic.Dictionary`2.Clear")
    method_context(index,cell,target,"System.Collections.Generic.Dictionary`2.Clear",["string",detail],0)
    p.field("498b4d",root+"extraDetails_"); p.fixed("4885c9"); p.branch("0f84",None)
    cell=p.rip("488b15"); target=p.call("Google.Protobuf.Collections.MapField`2.GetEnumerator")
    method_context(index,cell,target,"Google.Protobuf.Collections.MapField`2.GetEnumerator",["string","Proto.QUEST_OBJECTIVE_DETAIL"],0)
    p.fixed("48898424080100004c897c2420488d9c240801000048895c24286690")
    move_next(p,"details","488bbc2408010000","0f1f4000",far_fast=True,far_exit=True)
    p.fixed("4c8b8c24080100004d85c9"); p.branch("0f84",None); p.fixed("488d8c2490000000")
    current(p,["string","Proto.QUEST_OBJECTIVE_DETAIL"])
    p.fixed("0f10000f118424800000000f11442458")
    cell=p.rip("488b0d"); p.call()  # allocation; selected TypeInfo checked below
    selected=unresolved_usage_index(index.pe.bytes_at_va(cell,8),index.image.registration["typesCount"],tag=1,source="copy allocation",offset=cell)
    from .protocol import runtime_type_name
    if runtime_type_name(index.pe,index.metadata,index.pe.u64_at_va(int(index.image.registration["types"],16)+selected*8)) != detail:
        raise ValueError("copy_loop.allocation_type: named ConditionDetail TypeInfo required")
    p.fixed("4c8be84885c0"); p.branch("0f84",None); p.fixed("33d2488bc8"); p.call(detail+"..ctor")
    p.fixed("4c896c24500f10842480000000660f73d80866480f7ec04885c0"); p.branch("0f84",None)
    p.field("488b48","Proto.QUEST_OBJECTIVE_DETAIL::hashValue_"); p.fixed("4885c9"); p.branch("0f84",None)
    cell=p.rip("488b15"); target=p.call("Google.Protobuf.Collections.MapField`2.GetEnumerator")
    method_context(index,cell,target,"Google.Protobuf.Collections.MapField`2.GetEnumerator",["ulong","bool"],0)
    p.fixed("48894424304c897c2440488d4424304889442448660f1f440000")
    move_next(p,"hash","488b7c2430","0f1f8000000000",inner=True,far_fast=True,far_exit=True)
    p.fixed("4c8b4c24304d85c9"); p.branch("0f84",None)
    cell=p.rip("4c8b05"); p.fixed("488d8c24a0000000"); current(p,["ulong","bool"],cell); p.fixed("0f1008")
    p.field("498b4d",detail+"::hashValue"); p.fixed("4885c9"); p.branch("0f84",None)
    cell=p.rip("4c8b0d"); p.fixed("660f6fc1660f73d80866410f7ec066480f7eca")
    target=p.call("System.Collections.Generic.Dictionary`2.Add")
    method_context(index,cell,target,"System.Collections.Generic.Dictionary`2.Add",["long","bool"],2)
    p.branch("e9","hash.head"); fast_slot(p,"details"); fast_slot(p,"hash",inner=True)
    # Nested finally scope uses its own exception slot and preserves outer key.
    p.mark("hash.exit"); p.fixed("488d4c2448"); p.call(); p.branch("eb","hash.resume",1)
    p.fixed("488d4c2448"); p.call(); p.fixed("488b4c24404885c9"); p.branch("0f85",None)
    p.fixed("4533ff4c8ba424f00000004c8b6c2450488b5c2428"); p.mark("hash.resume")
    p.field("498b4c24",dest+"extraDetails"); p.fixed("4885c9"); p.branch("0f84",None)
    cell=p.rip("4c8b0d"); p.fixed("4d8bc5488b542458"); target=p.call("System.Collections.Generic.Dictionary`2.Add")
    method_context(index,cell,target,"System.Collections.Generic.Dictionary`2.Add",["string",detail],2)
    p.branch("e9","details.head"); cleanup(p,"details","epilogue")
    p.branch("eb","epilogue",1)
    normal_end=p.offset; p.mark("patch")
    p.offset=1570; p.mark("epilogue"); p.fixed("4881c4b0000000415f415e415d415c5f5e5bc3")
    p.finish(p.offset)
    return {"normalRegion": [normal_start,normal_end],"normalEpilogue": [p.labels['epilogue'],p.offset],
        "loops": ["values","details","hash"],"loopLabels":p.labels,"calls":p.calls,
        "typedFields":expected_fields,"hashKeyTransfer":"low 64 bits preserved from unsigned source context to signed destination context; no numeric arithmetic or range check in this caller",
        "pairFieldLayoutProved":False,"calleeSemanticsProved":False,"liveValuesProved":False,
        "conditions":["unpatched guard false","normal usage/class resolution and Win64 ABI","valid non-null objects and interface tables","valid current returns","successful allocation, collection and cleanup calls","no external alias mutation"]}


def check_copy_loops(index: Any, body: Any, spec: Any) -> str | None:
    if spec != {}:
        return "copy_loop.claim_shape: empty spec selects the named ObjectiveData.Copy grammar"
    try:
        prove_copy_loops(index,body)
    except (ValueError,OSError,KeyError,IndexError,AttributeError,RuntimeError) as exc:
        return f"copy_loop.default_path: {str(exc)[:900]}"
    return None
