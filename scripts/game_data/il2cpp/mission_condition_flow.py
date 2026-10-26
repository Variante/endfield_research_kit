"""Bounded default Mission state comparisons and Boolean AST control flow.

Every admitted instruction byte is checked; relocations join selected symbols,
fields, local labels or unwind-owned excluded paths. This proves caller flow,
not live activation, IFix selection, collection/getter implementations, event
packet field layout, or the parser's mapping from source text to a live AST.
"""
from __future__ import annotations

from collections import deque
from typing import Any

from .reference_layouts import NativeReferenceContext


class Program:
    def __init__(self, index: Any, body: Any):
        self.index, self.body = index, body
        self.regions = [(body.pointer, body.size), *index.chained_fragments.get(body.pointer, ())]
        self.at = body.pointer
        self.labels: dict[str, int] = {}
        self.branches: list[tuple[int, int, str]] = []
        self.variable: set[int] = set()
        self.visited: set[int] = set()

    def seek(self, address: int) -> None:
        if not any(p <= address < p+z for p, z in self.regions):
            raise ValueError(f"mission_condition.owner: {self.body.symbol}: target={address:#x} outside owned regions")
        self.at = address

    def take(self, count: int, *, variable: bool = False) -> bytes:
        at = self.at
        if not any(p <= at <= p+z-count for p, z in self.regions):
            raise ValueError(f"mission_condition.owner: {self.body.symbol}: offset={at-self.body.pointer} count={count}")
        raw = self.index.pe.bytes_at_va(at, count)
        if len(raw) != count:
            raise ValueError("mission_condition.bytes: truncated selected region")
        self.at += count
        self.visited.update(range(at, self.at))
        if variable:
            self.variable.update(range(at, self.at))
        return raw

    def fixed(self, hex_bytes: str) -> None:
        expected = bytes.fromhex(hex_bytes)
        at = self.at
        actual = self.take(len(expected))
        if actual != expected:
            raise ValueError(f"mission_condition.program: {self.body.symbol}: offset={at-self.body.pointer} expected={expected.hex()} actual={actual.hex()}")

    def mark(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"mission_condition.label: duplicate={name}")
        self.labels[name] = self.at

    def branch(self, opcode: str, label: str, width: int = 4) -> int:
        at = self.at
        self.fixed(opcode)
        target = self.at+width+int.from_bytes(self.take(width, variable=True), "little", signed=True)
        self.branches.append((at, target, label))
        return target

    def call(self, symbol: str, *, result: str | None = None, parameters: list[str] | None = None,
             opcode: str = "e8") -> int:
        at = self.at
        self.fixed(opcode)
        target = self.at+4+int.from_bytes(self.take(4, variable=True), "little", signed=True)
        selected_method(self.index, target, symbol, result=result, parameters=parameters)
        return target

    def field(self, opcode: str, qualified: str, expected_type: str, width: int = 4) -> None:
        context = NativeReferenceContext(self.index.image, index=self.index)
        _owner, kind, displacement = context.field(qualified)
        if kind != expected_type or not 0 <= displacement < 1 << (8*width):
            raise ValueError(f"mission_condition.field: {qualified}: expected={expected_type} actual={kind}/{displacement}")
        self.fixed(opcode)
        self.fixed(displacement.to_bytes(width, "little").hex())

    def immediate(self, opcode: str, value: int, width: int = 1) -> None:
        self.fixed(opcode)
        self.fixed(value.to_bytes(width, "little").hex())

    def relocation(self, opcode: str, *, tail: int = 0) -> int:
        self.fixed(opcode)
        return self.at+4+tail+int.from_bytes(self.take(4, variable=True), "little", signed=True)

    def anonymous_call(self) -> int:
        return self.relocation("e8")

    def excluded(self, name: str, target: int) -> None:
        self.seek(target)
        self.mark(name)

    def finish(self) -> dict[str, Any]:
        for at, actual, label in self.branches:
            if actual != self.labels.get(label):
                raise ValueError(f"mission_condition.branch: {self.body.symbol}: offset={at-self.body.pointer} label={label} expected={self.labels.get(label)} actual={actual}")
        return {"symbol": self.body.symbol, "checkedBytes": len(self.visited),
                "checkedBranchCount": len(self.branches),
                "fixedByteAddresses": sorted(self.visited-self.variable)}


def selected_method(index: Any, pointer: int, symbol: str, *, result: str | None = None,
                    parameters: list[str] | None = None) -> Any:
    context = NativeReferenceContext(index.image, index=index)
    declarations = {}
    for row in index.names_by_pointer.get(pointer, ()):
        if f"{row.get('type')}.{row.get('method')}" != symbol:
            continue
        method = index.metadata.methods[row["methodIndex"]]
        owner = index.metadata.types[method.declaring_type]
        if index.metadata.type_full_name(owner)+"."+index.metadata.string(method.name_index) != symbol:
            raise ValueError(f"mission_condition.declaration: {symbol}: inconsistent method identity")
        expects_static = symbol.startswith(("IFix.WrappersManagerImpl.", "Beyond.TableUtils.", "Beyond.DLogger.", "System.String.Equals"))
        if bool(method.flags & 0x10) != expects_static:
            continue
        if parameters is not None and [context.type_name(p.type_index) for p in index.metadata.parameters_for(method)] != parameters:
            continue
        if result is not None and context.type_name(method.return_type) != result:
            continue
        declarations[row["methodIndex"]] = method
    if len(declarations) != 1:
        raise ValueError(f"mission_condition.declaration: {symbol}: expected one selected signature; actual={len(declarations)}")
    return next(iter(declarations.values()))


def enum_members(index: Any, name: str, members: list[str]) -> dict[str, int]:
    context = NativeReferenceContext(index.image, index=index)
    if not context.is_enum(name) or context.field(name+"::value__")[1] != "int":
        raise ValueError(f"mission_condition.enum: {name}: expected Int32 enum")
    values = {member: index.enum_member_id(name, member) for member in members}
    if any(type(v) is not int or not 0 <= v < 128 for v in values.values()) or len(set(values.values())) != len(values):
        raise ValueError(f"mission_condition.enum: {name}: small distinct selected members required")
    return values


def prove_objective_initializer(index: Any, body: Any) -> dict[str, Any]:
    """The complete false-patch path returns without initializing an AST."""
    if body.symbol != "Beyond.Gameplay.GameCondition.InitAsObjectiveCondition":
        raise ValueError("mission_condition.objective_init: wrong selected method")
    p = Program(index, body)
    p.fixed("4053 4883ec20 488bd9 33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    patch = p.branch("0f85", "patch")
    p.fixed("4883c420 5b c3")
    p.excluded("patch", patch)
    result = p.finish()
    result.update(defaultBodyIsNoOp=True,
                  boundary="Complete ordinary path after false IFix guard; patch body excluded. Does not establish a live virtual override or caller.")
    return result


def prove_progress_ast_entry(index: Any, body: Any) -> dict[str, Any]:
    """Lazy parse and useProgress=true evaluation, independent of activation."""
    if body.symbol != "Beyond.Gameplay.CombineCondition.GetResultByProgress":
        raise ValueError("mission_condition.progress_ast: wrong selected method")
    p = Program(index, body)
    p.fixed("48895c2410 48894c2408 57 4883ec30 488bf9 33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    patch = p.branch("0f85", "patch")
    p.field("488b8f", "Beyond.Gameplay.CombineCondition::ast", "Beyond.Gameplay.AST")
    p.fixed("4885c9")
    p.branch("75", "validCheck", 1)
    null_helper = p.anonymous_call()  # Valid nonnull receivers exclude this throwing path.
    p.mark("validCheck")
    p.fixed("33d2")
    p.call("Beyond.Gameplay.AST.get_valid", result="bool", parameters=[])
    p.fixed("84c0")
    p.branch("75", "evaluate", 1)
    p.field("488b8f", "Beyond.Gameplay.CombineCondition::ast", "Beyond.Gameplay.AST")
    p.fixed("4885c9")
    p.branch("75", "parse", 1)
    if p.anonymous_call() != null_helper:
        raise ValueError("mission_condition.progress_ast: null helper differs")
    p.mark("parse")
    p.fixed("4533c0")
    p.field("488b97", "Beyond.Gameplay.CombineCondition::conditionEvalString", "string")
    p.call("Beyond.Gameplay.AST.Parse", result="void", parameters=["string"])
    p.mark("evaluate")
    p.field("488b97", "Beyond.Gameplay.CombineCondition::ast", "Beyond.Gameplay.AST")
    p.fixed("4885d2")
    p.branch("75", "node", 1)
    if p.anonymous_call() != null_helper:
        raise ValueError("mission_condition.progress_ast: null helper differs")
    p.mark("node")
    p.fixed("4533c9 41b001")
    p.field("488b52", "Beyond.Gameplay.AST::rootNode", "Beyond.Gameplay.ASTNode", 1)
    p.fixed("488bcf")
    p.call("Beyond.Gameplay.CombineCondition._EvaluateNode", result="bool", parameters=["Beyond.Gameplay.ASTNode", "bool"])
    p.fixed("8ad8")
    returned = p.branch("eb", "result", 1)
    # The intervening exception filter/log handler is outside this valid,
    # successfully returning callee path; it is not ordinary evaluation.
    p.seek(returned)
    p.mark("result")
    p.fixed("8ac3")
    epilogue_target = p.branch("eb", "epilogue", 1)
    p.seek(epilogue_target)
    p.mark("epilogue")
    p.fixed("488b5c2448 4883c430 5f c3")
    p.excluded("patch", patch)
    result = p.finish()
    result.update(useProgress=True, parsesOnlyWhenAstInvalid=True, waitsForEveryChildDecided=False,
                  setsCachedResult=False,
                  boundary="Complete nonnull unpatched caller path with successfully returning parser/evaluator. Exception handling and callee effects excluded. Does not activate state predicates, prove live ownership or establish a quest handoff.")
    return result


def prove_progress_comparison(index: Any, body: Any) -> dict[str, Any]:
    """Base progress truth compares virtual progress operands, not state IDs."""
    from .body_claims import _virtual_method_slot, _virtual_getter_helper
    if body.symbol != "Beyond.Gameplay.GameCondition.GetResultByProgress":
        raise ValueError("mission_condition.progress_compare: wrong selected method")
    p = Program(index, body)
    p.fixed("48895c2408 4889742410 57 4883ec20 488bf1 bb")
    p.take(4, variable=True)
    p.fixed("8bcb 33d2")
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    patch = p.branch("75", "patch", 1)
    helper = None
    for name, extra in (("get_compareOperator", ""), ("get_progress", "8bf8"), ("get_progressToCompare", "8bd8")):
        p.immediate("b9", _virtual_method_slot(index, "Beyond.Gameplay.GameCondition."+name), 4)
        p.fixed("488bd6"+extra)
        target = p.anonymous_call()
        if helper is not None and helper != target or not _virtual_getter_helper(index, target):
            raise ValueError("mission_condition.progress_compare: typed virtual getter helper differs")
        helper = target
    p.fixed("4533c9 448bc0 8bd3 8bcf")
    p.call("Beyond.TableUtils.DoCompare", result="bool", parameters=["Beyond.GEnums.CompareOperator", "int", "int"])
    returned = p.branch("eb", "return", 1)
    p.seek(returned)
    p.mark("return")
    p.fixed("488b5c2430 488b742438 4883c420 5f c3")
    p.excluded("patch", patch)
    result = p.finish()
    result.update(operands=["virtual get_compareOperator", "virtual get_progress", "virtual get_progressToCompare"],
                  cachedResultRead=False, stateIdQuery=False,
                  boundary="Complete false-patch base caller path; valid typed virtual getter ABI and successful returning helpers/comparator required. Overrides/getter effects, progress provenance and live ownership remain separate.")
    return result


def prove_combined_client_activation(index: Any, body: Any) -> dict[str, Any]:
    """Check the whole initialized, nonnull default child loop.

    This loop dispatches on children only. It does not call Activate on its
    own receiver, Parse its AST, or write parent pointers. Virtual/helper and
    collection effects, patches, null/error paths and recursive overrides are
    conditional boundaries, rather than global no-side-effect claims.
    """
    from .body_claims import _virtual_method_slot, _virtual_slot_helper, _virtual_getter_helper
    from .context import unresolved_usage_index
    p = Program(index, body)
    p.fixed("48896c2418 57 4883ec20")
    p.relocation("803d", tail=1)
    p.fixed("00 488bea 488bf9")
    init = p.branch("0f84", "init")
    p.mark("ready")
    p.fixed("48895c2430 33d2 b9")
    p.take(4, variable=True)
    p.fixed("4889742438")
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    patch = p.branch("0f85", "patch")
    p.fixed("33db")
    p.mark("loop")
    p.field("488b87", "Beyond.Gameplay.CombineCondition::subConditions", "System.Collections.Generic.List`1<Beyond.Gameplay.GameCondition>")
    p.fixed("4885c0")
    null_list = p.branch("0f84", "nullList")
    p.fixed("3b5818")
    p.branch("7d", "return", 1)
    p.relocation("4c8b05")
    p.fixed("8bd3 488bc8")
    item = p.anonymous_call()
    if "System.Collections.Generic.List`1.get_Item" not in index.names_of(item):
        raise ValueError("mission_condition.client_loop: expected named list item reader")
    p.fixed("488bf0 4885c0")
    null_child = p.branch("0f84", "nullChild")
    cell = p.relocation("488b05")
    type_index = unresolved_usage_index(index.pe.bytes_at_va(cell, 8), index.image.registration["typesCount"],
                                        tag=1, source=str(index.image.gameassembly), offset=cell)
    if NativeReferenceContext(index.image, index=index).type_name(type_index) != "Beyond.Gameplay.CombineCondition":
        raise ValueError("mission_condition.client_loop: exact runtime-type test usage differs")
    p.fixed("488bd6 483906")
    p.branch("75", "leaf", 1)
    slot = _virtual_method_slot(index, "Beyond.Gameplay.GameCondition.ActivateClientCondition")
    p.immediate("b9", slot, 4)
    p.fixed("4c8bc5")
    dispatch = p.anonymous_call()
    if not _virtual_slot_helper(index, dispatch):
        raise ValueError("mission_condition.client_loop: child virtual dispatch helper differs")
    p.mark("advance")
    p.fixed("ffc3")
    p.branch("eb", "loop", 1)
    p.mark("return")
    p.fixed("488b742438 488b5c2430 488b6c2440 4883c420 5f c3")
    p.mark("leaf")
    p.immediate("b9", _virtual_method_slot(index, "Beyond.Gameplay.GameCondition.get_conditionType"), 4)
    getter = p.anonymous_call()
    if not _virtual_getter_helper(index, getter):
        raise ValueError("mission_condition.client_loop: child type getter helper differs")
    p.immediate("3d", index.enum_member_id("Beyond.GEnums.ConditionType", "ClientOnly"), 4)
    p.branch("75", "advance", 1)
    p.immediate("b9", slot, 4)
    p.fixed("4c8bc5 488bd6")
    if p.anonymous_call() != dispatch:
        raise ValueError("mission_condition.client_loop: leaf and composite dispatch differ")
    p.fixed("ffc3")
    p.branch("e9", "loop")
    for name, target in (("init", init), ("patch", patch), ("nullList", null_list), ("nullChild", null_child)):
        p.excluded(name, target)
    result = p.finish()
    result.update(activatesOwnReceiver=False, parsesOwnAst=False, writesParentPointers=False,
                  childSelection="Exact CombineCondition children recurse; other children require virtual ClientOnly.",
                  boundary="Complete initialized nonnull default caller loop; returning collection/virtual helpers, valid metadata usages, false patches and recursive default selection required. Callee effects and live objects remain unproved.")
    return result


def prove_state_activation_order(index: Any, body: Any) -> dict[str, Any]:
    """Check every completing default path's subscribe/initial-result order.

    Start after the owned IsPatched false guard. Direct callees are returning
    opaque boundaries; their effects, exceptions and reentrancy are separate.
    Null/exception endpoints ending in INT3 are excluded from normal completion.
    This walks branches, never uses address order as execution order.
    """
    bind, result = "Beyond.EventManager.BindGlobal", "Beyond.Gameplay.GameCondition.set_result"
    orders = {"Beyond.Gameplay.CheckQuestState.OnActivate": (bind, result),
              "Beyond.Gameplay.CheckMissionState.OnActivate": (result, bind)}
    if body.symbol not in orders:
        raise ValueError("mission_condition.activation: requires a named quest/mission predicate")
    expected = orders[body.symbol]
    rows = {int(row["va"], 16): row for row in body.all_rows}
    regions = [(body.pointer, body.size), *index.chained_fragments.get(body.pointer, ())]

    def owned(at: int, size: int) -> bool:
        return any(start <= at and at+size <= start+length for start, length in regions)

    def raw_at(at: int) -> bytes:
        row = rows.get(at)
        if row is None or str(row.get("text", "")).startswith("db"):
            raise ValueError(f"mission_condition.activation_decode: {body.symbol}: at={at:#x}")
        raw = bytes.fromhex(row["bytes"])
        if not raw or not owned(at, len(raw)) or index.pe.bytes_at_va(at, len(raw)) != raw:
            raise ValueError(f"mission_condition.activation_bytes: {body.symbol}: at={at:#x}")
        return raw

    entries = []
    for at, row in rows.items():
        raw = bytes.fromhex(row["bytes"])
        if len(raw) == 5 and raw[0] == 0xe8:
            target = at+5+int.from_bytes(raw[1:], "little", signed=True)
            if "IFix.WrappersManagerImpl.IsPatched" in index.names_of(target):
                # Mission predicates clear EDX between call and test; the
                # following JNE selects the patch, whose fallthrough we admit.
                suffix = index.pe.bytes_at_va(at+5, 10)
                if suffix[:6] != b"\x33\xd2\x84\xc0\x0f\x85":
                    raise ValueError("mission_condition.activation_guard: default false branch differs")
                require = at+15
                if require not in rows:
                    raise ValueError("mission_condition.activation_guard: fallthrough is not an instruction")
                entries.append(require)
    if len(entries) != 1:
        raise ValueError(f"mission_condition.activation_guard: expected one owned selector; actual={len(entries)}")

    pending = deque([(entries[0], ())])
    visited, checked, completions, refused = set(), set(), set(), set()
    while pending:
        at, observed = pending.popleft()
        state = (at, observed)
        if state in visited:
            continue
        visited.add(state)
        if len(visited) > 4096:
            raise ValueError("mission_condition.activation_budget: control graph exceeds 4096 states")
        raw = raw_at(at)
        checked.update(range(at, at+len(raw)))
        next_at = at+len(raw)
        if raw == b"\xcc":
            refused.add(at)
            continue
        if raw == b"\xc3":
            if observed != expected:
                raise ValueError(f"mission_condition.activation_order: {body.symbol}: endpoint={at:#x}; expected={expected}; actual={observed}")
            completions.add(at)
            continue
        if len(raw) == 5 and raw[0] in (0xe8, 0xe9):
            target = at+5+int.from_bytes(raw[1:], "little", signed=True)
            names = index.names_of(target)
            selected = [name for name in (bind, result) if name in names]
            if len(selected) > 1:
                raise ValueError("mission_condition.activation_alias: critical call identities overlap")
            if selected:
                observed = (*observed, selected[0])
                if observed != expected[:len(observed)]:
                    raise ValueError(f"mission_condition.activation_order: {body.symbol}: call={at:#x}; expected={expected}; actual={observed}")
            if raw[0] == 0xe8:
                pending.append((next_at, observed))
            elif owned(target, 1):
                pending.append((target, observed))
            elif selected == [result] and observed == expected:
                completions.add(at)
            else:
                raise ValueError(f"mission_condition.activation_tail: unreviewed external target={target:#x}")
        elif len(raw) == 2 and (0x70 <= raw[0] <= 0x7f or raw[0] == 0xeb):
            target = next_at+int.from_bytes(raw[1:], "little", signed=True)
            pending.append((target, observed))
            if raw[0] != 0xeb:
                pending.append((next_at, observed))
        elif len(raw) == 6 and raw[0] == 0x0f and 0x80 <= raw[1] <= 0x8f:
            target = next_at+int.from_bytes(raw[2:], "little", signed=True)
            pending.extend([(target, observed), (next_at, observed)])
        elif str(rows[at]["text"]).startswith(("call ", "jmp ", "ret", "jcc ", "je ", "jne ")):
            raise ValueError(f"mission_condition.activation_control: unsupported control at={at:#x}")
        else:
            pending.append((next_at, observed))
    if not completions:
        raise ValueError("mission_condition.activation_completion: no normal endpoint")
    return {"symbol": body.symbol, "status": "validated", "callOrder": list(expected),
            "checkedBytes": len(checked), "normalEndpoints": len(completions),
            "excludedExceptionEndpoints": len(refused), "controlStates": len(visited),
            "boundary": "conditional native default path after IsPatched=false, opaque callees return; no callee effects, live selection, subscription success, callback purity, reentrancy or observed chronology"}


def selected_patch_selector(index: Any, body: Any) -> int:
    """A unique owned ECX immediate directly feeding named GetPatch."""
    candidates = set()
    for row in body.all_rows:
        raw = bytes.fromhex(str(row.get("bytes", "")))
        if len(raw) != 5 or raw[0] != 0xe8:
            continue
        address = int(row["va"], 16)
        target = address+5+int.from_bytes(raw[1:], "little", signed=True)
        if "IFix.WrappersManagerImpl.GetPatch" not in index.names_of(target):
            continue
        p = Program(index, body)
        p.seek(address-7)
        p.fixed("33d2 b9")
        value = int.from_bytes(p.take(4), "little")
        p.call("IFix.WrappersManagerImpl.GetPatch")
        p.fixed("4885c0")
        candidates.add(value)
    if len(candidates) != 1:
        raise ValueError(f"mission_condition.patch_selector: {body.symbol}: expected one owned GetPatch selector; actual={len(candidates)}")
    return next(iter(candidates))


def prove_result_propagation(index: Any, body: Any) -> dict[str, Any]:
    """Active decided changes write the cache, call its hook, then parent Evaluate.

    The unnamed hook helper is deliberately only a returning caller assumption.
    It may mutate other state; no atomic or globally coherent snapshot follows.
    """
    if body.symbol != "Beyond.Gameplay.GameCondition.set_result":
        raise ValueError("mission_condition.result: wrong selected setter")
    selected_method(index, body.pointer, body.symbol, result="void",
                    parameters=["Beyond.Gameplay.ConditionResult"])
    state = enum_members(index, "Beyond.Gameplay.ConditionState", ["Activate", "Deactivate"])
    result = enum_members(index, "Beyond.Gameplay.ConditionResult", ["False", "True", "Undecided"])
    if state["Activate"] != 0:
        raise ValueError("mission_condition.result: selected active zero test differs")
    base = "Beyond.Gameplay.GameCondition::"
    p = Program(index, body)
    p.fixed("48895c2408 57 4883ec20")
    flag = p.relocation("803d", tail=1)
    p.fixed("00 8bfa 488bd9")
    init = p.branch("74", "init", 1)
    p.mark("ready")
    p.fixed("33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    patched = p.branch("0f85", "patched")
    p.field("837b", base+"<state>k__BackingField", "Beyond.Gameplay.ConditionState", 1)
    p.fixed("00")
    p.branch("75", "return", 1)
    p.immediate("83ff", result["Undecided"])
    refused = p.branch("0f84", "refused")
    p.field("397b", base+"m_result", "Beyond.Gameplay.ConditionResult", 1)
    p.branch("74", "return", 1)
    p.field("488b4b", base+"onResultChange", "Beyond.Gameplay.GameCondition+ResultChange", 1)
    p.field("897b", base+"m_result", "Beyond.Gameplay.ConditionResult", 1)
    p.fixed("4885c9")
    p.branch("75", "callback", 1)
    p.mark("parent")
    p.field("488b4b", base+"parent", "Beyond.Gameplay.CombineCondition", 1)
    p.fixed("4885c9")
    p.branch("75", "evaluate", 1)
    p.mark("return")
    p.fixed("488b5c2430 4883c420 5f c3")
    p.mark("callback")
    p.immediate("83ff", result["True"])
    p.fixed("0f94c2")
    hook = p.anonymous_call()
    p.branch("eb", "parent", 1)
    p.mark("evaluate")
    p.fixed("33d2 488b5c2430 4883c420 5f")
    p.call("Beyond.Gameplay.CombineCondition.Evaluate", result="void", parameters=[], opcode="e9")
    p.excluded("init", init)
    for _ in range(2):
        p.relocation("488d0d")
        p.anonymous_call()
    actual_flag = p.relocation("c605", tail=1)
    p.fixed("01")
    if actual_flag != flag:
        raise ValueError("mission_condition.result: initializer flag differs")
    p.branch("e9", "ready")
    p.excluded("refused", refused)
    p.relocation("488b0d")
    p.fixed("83b9 e0000000 00")
    p.branch("75", "log", 1)
    p.anonymous_call()
    p.mark("log")
    p.relocation("488b15")
    p.fixed("4533c0 b104")
    p.call("Beyond.DLogger.LogError")
    p.fixed("90")
    p.branch("e9", "return")
    p.excluded("patched", patched)
    p.fixed("33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.GetPatch")
    p.fixed("4885c0")
    finished = p.finish()
    finished.update(callbackHelper=hex(hook), activeState=state["Activate"],
        boundary="conditional complete default setter caller: active state, changed decided result, successful returning callback helper before parent Evaluate; no callback purity, reentrancy exclusion, live selection, coherent snapshot or observed order")
    return finished


def epilogue(p: Program, *, frame: str = "30") -> None:
    p.fixed("48 8b 5c 24 40 48 8b 74 24 48 48 83 c4 "+frame+" 5f c3")


def prove_int_comparison(index: Any, body: Any) -> dict[str, Any]:
    """Signed Int32 comparisons, including the selected jump-table cases."""
    symbol = "Beyond.TableUtils.DoCompare"
    if body.symbol != symbol:
        raise ValueError("mission_condition.compare: wrong caller")
    selected_method(index, body.pointer, symbol, result="bool",
                    parameters=["Beyond.GEnums.CompareOperator", "int", "int"])
    names = ["Equal", "NotEqual", "GreaterThan", "GreaterEqual", "LessThan", "LessEqual"]
    values = enum_members(index, "Beyond.GEnums.CompareOperator", names)
    if list(values.values()) != list(range(6)):
        raise ValueError("mission_condition.compare: switch requires selected contiguous Equal..LessEqual")
    p = Program(index, body)
    p.fixed("48 89 5c 24 08 48 89 74 24 10 57 48 83 ec 30 8b da 48 63 f1 33 d2 b9")
    p.take(4, variable=True)  # IFix patch selector is provenance, not the comparison.
    p.fixed("41 8b f8")
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84 c0")
    patched = p.branch("0f85", "patched")
    p.fixed("85 f6")
    p.branch("75", "switch", 1)
    p.mark("Equal")
    p.fixed("3b df 0f94c0")
    p.mark("return")
    epilogue(p)
    p.mark("switch")
    p.immediate("83fe", values["LessEqual"])
    p.branch("77", "unknown", 1)
    p.fixed("488d15")
    base = p.at+4+int.from_bytes(p.take(4, variable=True), "little", signed=True)
    if base != index.pe.image_base:
        raise ValueError("mission_condition.compare: table RVA base differs from selected image")
    p.fixed("8b8cb2")
    table = base+int.from_bytes(p.take(4, variable=True), "little")
    p.fixed("4803ca ffe1")
    p.mark("NotEqual")
    p.fixed("3bdf 0f95c0")
    epilogue(p)
    p.mark("GreaterEqual")
    p.fixed("488b742448 3bdf 488b5c2440 0f9dc0 4883c430 5fc3")
    p.mark("unknown")
    p.fixed("32c0")
    p.branch("eb", "return", 1)
    p.fixed("6690")
    if p.at != table or body.pointer+body.size != table+24:
        raise ValueError("mission_condition.compare: owned six-entry table boundary differs")
    targets = [base+int.from_bytes(p.take(4, variable=True), "little") for _ in range(6)]
    for name, opcode in (("GreaterThan", "0f9fc0"), ("LessThan", "0f9cc0"), ("LessEqual", "0f9ec0")):
        p.seek(targets[values[name]])
        p.mark(name)
        p.fixed("3bdf "+opcode)
        p.branch("e9", "return")
    for name, value in values.items():
        if targets[value] != p.labels[name]:
            raise ValueError(f"mission_condition.compare: selected table case={name} targets another block")
    p.excluded("patched", patched)
    p.fixed("33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.GetPatch")
    result = p.finish()
    result.update(comparatorEnum="Beyond.GEnums.CompareOperator", members=values, signedInt32=True,
                  unknownComparatorResult=False, condition="IsPatched is false; normal Win64 ABI",
                  evidenceBoundary="conditional: complete selected Int32 comparison cases; no chronological interpretation of state integers")
    return result


def prove_state_callback(index: Any, body: Any) -> dict[str, Any]:
    """Owned matching-ID callback flow from raw EventData lanes to result."""
    quest = body.symbol == "Beyond.Gameplay.CheckQuestState._OnQuestStateChange"
    mission = body.symbol == "Beyond.Gameplay.CheckMissionState._OnMissionStateChange"
    if not (quest or mission):
        raise ValueError("mission_condition.callback: wrong caller")
    owner = "Beyond.Gameplay.CheckQuestState" if quest else "Beyond.Gameplay.CheckMissionState"
    state_type = "Beyond.Gameplay.MissionSystem+"+("QuestState" if quest else "MissionState")
    selected_method(index, body.pointer, body.symbol, result="void", parameters=[f"Beyond.EventData`2<string,{state_type}>"])
    enum_members(index, state_type, ["None", "Processing", "Completed", "Failed", "Disabled"])
    enum_members(index, "Beyond.GEnums.CompareOperator", ["Equal", "NotEqual", "GreaterThan", "GreaterEqual", "LessThan", "LessEqual"])
    values = enum_members(index, "Beyond.Gameplay.ConditionResult", ["False", "True", "Undecided"])
    if values["False"] != 0 or values["True"] != 1:
        raise ValueError("mission_condition.callback: selected False/True must match normalized Boolean values")
    p = Program(index, body)
    p.fixed("48895c2408 57 4883ec20 488bfa 488bd9 33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    patched = p.branch("0f85" if quest else "75", "patched", 4 if quest else 1)
    p.field("488b93", owner+"::m_"+("questId" if quest else "missionId"), "string")
    p.fixed("4533c0 488b0f")  # Incoming packet lane 0 vs configured ID.
    p.call("System.String.Equals", result="bool", parameters=["string", "string"])
    p.fixed("84c0")
    match = p.branch("0f85" if quest else "74", "compare" if quest else "return", 4 if quest else 1)
    if quest:
        p.mark("return")
        p.fixed("488b5c2430 4883c420 5fc3")
        p.seek(match)
    p.mark("compare")
    p.field("448b83", owner+"::m_target"+("QuestState" if quest else "MissionState"), state_type)
    p.fixed("4533c9 8b5708")  # Raw incoming packet lane 8; closed field layout separate.
    p.field("8b8b", owner+"::m_comparer", "Beyond.GEnums.CompareOperator")
    p.call("Beyond.TableUtils.DoCompare", result="bool", parameters=["Beyond.GEnums.CompareOperator", "int", "int"])
    p.fixed("4533c0 488bcb 84c0")
    p.branch("75", "true", 1)
    p.mark("write")
    p.fixed("33d2")
    p.mark("setter")
    p.call("Beyond.Gameplay.GameCondition.set_result", result="void", parameters=["Beyond.Gameplay.ConditionResult"])
    if quest:
        p.fixed("90")
        p.branch("e9", "return")
    else:
        p.branch("eb", "return", 1)
    p.mark("true")
    p.immediate("ba", values["True"], 4)
    if quest:
        p.call("Beyond.Gameplay.GameCondition.set_result", result="void", parameters=["Beyond.Gameplay.ConditionResult"])
        p.fixed("90")
        p.branch("e9", "return")
    else:
        p.branch("eb", "setter", 1)
    p.excluded("patched", patched)
    p.fixed("33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.GetPatch")
    if not quest:
        # The patch path is excluded; the normal return is selected by ID mismatch
        # and both Boolean result arms. Authenticate its complete epilogue.
        p.seek(match)
        p.mark("return")
        p.fixed("488b5c2430 4883c420 5fc3")
    result = p.finish()
    result.update(targetKind="quest" if quest else "mission", stateEnum=state_type,
                  idLaneBytes=8, stateLaneOffset=8, ignoresNonmatchingIds=True,
                  resultMembers=values, currentStateQuery=False,
                  condition="IsPatched is false; valid incoming EventData ABI storage and successful callees",
                  evidenceBoundary="conditional: matching raw packet ID/state lanes feed comparator then result setter; EventData closed field layout, event delivery and setter effects remain separate")
    return result


def prove_boolean_ast(index: Any, body: Any, *, use_progress: bool = False) -> dict[str, Any]:
    """Complete valid-node paths of _EvaluateNode with useProgress=false."""
    if body.symbol != "Beyond.Gameplay.CombineCondition._EvaluateNode":
        raise ValueError("mission_condition.ast: wrong caller")
    selected_method(index, body.pointer, body.symbol, result="bool", parameters=["Beyond.Gameplay.ASTNode", "bool"])
    logic = enum_members(index, "Beyond.Gameplay.LogicOperator", ["ConditionIdx", "Not", "And", "Or"])
    if list(logic.values()) != list(range(4)):
        raise ValueError("mission_condition.ast: selected ConditionIdx/Not/And/Or dispatch differs")
    results = enum_members(index, "Beyond.Gameplay.ConditionResult", ["False", "True", "Undecided"])
    p = Program(index, body)
    p.fixed("48895c2408 4889742410 57 4883ec30 488bda 488bf9 33d2 b9")
    p.take(4, variable=True)
    p.fixed("410fb6f0")
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    excluded = {"patched": p.branch("0f85", "patched")}
    p.fixed("4885db")
    excluded["nullNode"] = p.branch("0f84", "nullNode")
    p.field("8b4b", "Beyond.Gameplay.ASTNode::logicOperator", "Beyond.Gameplay.LogicOperator", 1)
    p.fixed("85c9")
    p.branch("74", "leaf", 1)
    p.fixed("83e901")
    p.branch("0f84", "not")
    p.fixed("83e901")
    p.branch("0f85", "orDispatch")

    def child(position: int, *, short: bool = False) -> None:
        p.field("488b53", "Beyond.Gameplay.ASTNode::children", "Beyond.Gameplay.ASTNode[]", 1)
        p.fixed("4885d2")
        excluded.setdefault("nullChildArray", p.branch("74" if short else "0f84", "nullChildArray", 1 if short else 4))
        p.fixed("394a18" if position == 0 and p.labels.get("and") is None else "837a18"+bytes([position]).hex())
        excluded.setdefault("shortChildArray", p.branch("76" if short else "0f86", "shortChildArray", 1 if short else 4))
        p.fixed("488b52"+bytes([0x20+position*8]).hex()+" 4533c9 440fb6c6 488bcf")
        p.call(body.symbol, result="bool", parameters=["Beyond.Gameplay.ASTNode", "bool"])

    # At And entry ECX is zero from the two dispatch decrements.
    child(0)
    p.fixed("84c0")
    p.branch("0f85", "andRight")
    p.mark("false")
    p.fixed("32c0")
    epilogue(p)
    p.mark("leaf")
    p.field("837b", "Beyond.Gameplay.ASTNode::conditionIdx", "int", 1)
    p.fixed("00")
    excluded["invalidIndex"] = p.branch("0f8c", "invalidIndex")
    p.field("488b87", "Beyond.Gameplay.CombineCondition::subConditions", "System.Collections.Generic.List`1<Beyond.Gameplay.GameCondition>")
    p.field("8b4b", "Beyond.Gameplay.ASTNode::conditionIdx", "int", 1)
    p.fixed("4885c0")
    excluded.setdefault("nullChildArray", p.branch("0f84", "nullChildArray"))
    p.fixed("3b4818")
    p.branch("0f8d", "invalidIndex")
    p.fixed("488bc8 4885c0")
    p.branch("0f84", "nullChildArray")
    p.fixed("4c8b05")
    p.take(4, variable=True)  # Passed generic context; getter body/layout separate.
    p.field("8b53", "Beyond.Gameplay.ASTNode::conditionIdx", "int", 1)
    p.call("System.Collections.Generic.List`1.get_Item")
    p.fixed("4885c0")
    p.branch("0f84", "nullChildArray")
    p.fixed("4084f6")
    excluded["useProgress"] = p.branch("0f85", "useProgress")
    p.fixed("33d2 488bc8")
    p.call("Beyond.Gameplay.GameCondition.get_result", result="Beyond.Gameplay.ConditionResult", parameters=[])
    p.immediate("83f8", results["True"])
    p.fixed("0f94c0")
    p.mark("leafReturn")
    epilogue(p)
    p.mark("andRight")
    p.mark("and")  # Subsequent child checks must use explicit immediate bounds.
    child(1)
    p.fixed("84c0 0f95c0")
    epilogue(p)
    p.mark("orDispatch")
    p.fixed("83f901")
    p.branch("0f85", "false")
    child(0)
    p.fixed("84c0")
    p.branch("75", "true", 1)
    child(1, short=True)
    p.fixed("84c0")
    p.branch("0f84", "false")
    p.mark("true")
    p.fixed("b001")
    epilogue(p)
    p.mark("not")
    child(0, short=True)
    p.fixed("488b5c2440 3401 488b742448 4883c430 5fc3")
    # These are deliberately excluded paths. Validate ownership and known entry
    # forms so a valid-input branch cannot silently join an unrelated helper.
    for name, target in excluded.items():
        p.excluded(name, target)
        if name in ("shortChildArray", "nullChildArray"):
            p.fixed("e8")
            p.take(4, variable=True)
            p.fixed("cc")
        elif name == "patched":
            p.fixed("33d2 b9")
            p.take(4, variable=True)
            p.call("IFix.WrappersManagerImpl.GetPatch")
        elif name == "useProgress":
            from .body_claims import _virtual_method_slot
            p.immediate("b9", _virtual_method_slot(index, "Beyond.Gameplay.GameCondition.GetResultByProgress") if use_progress else 21, 4)
            p.fixed("488bd0")
            if use_progress:
                target = p.anonymous_call()
                size = index._extent(target)
                if not 0 < size <= 16384:
                    raise ValueError("mission_condition.progress_leaf: oversized Boolean virtual helper")
                raw = index.pe.bytes_at_va(target, size)
                prefix = bytes.fromhex("0fb7d9 488bfa 488b0a")
                lookup = bytes.fromhex("488d4b14 48c1e104 48030f 488b01 488b5108")
                invoke = bytes.fromhex("488bcf 488b5c2430 4883c420 5f 48ffe0")
                a, b, c = raw.find(prefix), raw.find(lookup), raw.find(invoke)
                if not 0 <= a < b < c:
                    raise ValueError("mission_condition.progress_leaf: receiver/slot/MethodInfo Boolean virtual fallback differs")
                p.fixed("90")
                p.branch("e9", "leafReturn")
        else:
            p.fixed("488b0d")
            p.take(4, variable=True)
    result = p.finish()
    result.update(logicEnum="Beyond.Gameplay.LogicOperator", operators=logic, conditionResults=results,
                  leafTest="virtual GetResultByProgress" if use_progress else "get_result == True", shortCircuit={"And": "left false skips right", "Or": "left true skips right"},
                  notOperation="Boolean XOR 1", useProgress=use_progress,
                  condition="all recursive IsPatched guards false; valid node/child/index storage; successful List/getter callees",
                  evidenceBoundary="conditional: exact Boolean valid-node evaluator paths; source parser equivalence and getter/callee effects remain separate")
    return result


def prove_progress_ast(index: Any, body: Any) -> dict[str, Any]:
    result = prove_boolean_ast(index, body, use_progress=True)
    result.update(evidenceBoundary="conditional: complete valid-node progress AST caller paths, with opaque returning child virtual getters and selected initialized helper ABI. No cached-result gate, getter purity, source parser equivalence, activation or live owner inferred.")
    return result


def prove_combined_evaluation(index: Any, body: Any) -> dict[str, Any]:
    """Normal outer loop gates AST evaluation on all child results decided.

    Expanded IFix getter implementations are excluded by their false guards.
    The checked inline side reads the selected GameCondition result field.
    Enumerator ABI storage and successful collection helpers are conditional.
    """
    if body.symbol != "Beyond.Gameplay.CombineCondition.Evaluate":
        raise ValueError("mission_condition.combined: wrong caller")
    selected_method(index, body.pointer, body.symbol, result="void", parameters=[])
    results = enum_members(index, "Beyond.Gameplay.ConditionResult", ["False", "True", "Undecided"])
    if results["False"] != 0 or results["True"] != 1:
        raise ValueError("mission_condition.combined: Boolean setter lanes differ")
    p = Program(index, body)
    p.fixed("48895c2410 4889742420 48894c2408 57 4154 4155 4156 4157 4881ec80000000 4c8bf1 4c8be1 48898c24c0000000")
    cell = p.relocation("803d", tail=1)
    p.fixed("00")
    p.branch("75", "initialized", 1)
    helper = None
    for _ in range(4):
        p.relocation("488d0d")
        target = p.anonymous_call()
        if helper is not None and helper != target:
            raise ValueError("mission_condition.combined: usage initialization helper differs")
        helper = target
    if p.relocation("c605", tail=1) != cell:
        raise ValueError("mission_condition.combined: initialization flag cells differ")
    p.fixed("01")
    p.mark("initialized")
    p.fixed("33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    excluded = {"patched": p.branch("0f85", "patched")}
    p.field("498b9e", "Beyond.Gameplay.CombineCondition::subConditions", "System.Collections.Generic.List`1<Beyond.Gameplay.GameCondition>")
    p.fixed("4885db")
    excluded["nullList"] = p.branch("0f84", "nullList")
    p.relocation("4c8b05")
    p.fixed("488bd3 488d4c2448")
    p.call("System.Collections.Generic.List`1.GetEnumerator")
    p.fixed("0f10442448 0f11442460 f20f104c2458 f20f114c2470 33f6 4889742448 488d442460 4889442450")
    base = p.relocation("4c8d3d")
    if base != index.pe.image_base:
        raise ValueError("mission_condition.combined: image base relocation differs")
    p.fixed("49bdabaaaaaaaaaaaaaa 0f1f00")
    p.mark("next")
    p.relocation("488b15")
    p.fixed("488d4c2460")
    p.call("System.Collections.Generic.List`1+Enumerator.MoveNext", result="bool")
    p.fixed("84c0")
    exhausted = p.branch("0f84", "exhausted")
    p.fixed("488b7c2470 4885ff")
    wait = p.branch("0f84", "wait")
    p.fixed("33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    excluded["childGetterPatched"] = p.branch("75", "childGetterPatched", 1)
    p.field("8b47", "Beyond.Gameplay.GameCondition::m_result", "Beyond.Gameplay.ConditionResult", 1)
    child_gate = p.branch("e9", "childGate")
    p.seek(child_gate)
    p.mark("childGate")
    p.immediate("83f8", results["Undecided"])
    p.branch("0f85", "next")
    p.mark("wait")
    if p.at != wait:
        raise ValueError("mission_condition.combined: null child must join waiting return")
    p.branch("e9", "return")
    p.mark("exhausted")
    if p.at != exhausted:
        raise ValueError("mission_condition.combined: exhaustion must follow waiting jump")
    ast = p.branch("eb", "ast", 1)
    p.seek(ast)
    p.mark("ast")
    p.field("498b96", "Beyond.Gameplay.CombineCondition::ast", "Beyond.Gameplay.AST")
    p.fixed("4885d2")
    excluded["nullReceiver"] = p.branch("0f84", "nullReceiver")
    p.fixed("4533c9 4533c0")  # useProgress=false.
    p.field("488b52", "Beyond.Gameplay.AST::rootNode", "Beyond.Gameplay.ASTNode", 1)
    p.fixed("498bce")
    p.call("Beyond.Gameplay.CombineCondition._EvaluateNode", result="bool", parameters=["Beyond.Gameplay.ASTNode", "bool"])
    p.fixed("0fb6d8")  # Boolean AL -> complete EBX setter lane.

    def current_result(label: str) -> int:
        p.fixed("33d2 b9")
        p.take(4, variable=True)
        p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
        p.fixed("84c0")
        excluded[label] = p.branch("75", label, 1)
        p.field("418b46", "Beyond.Gameplay.GameCondition::m_result", "Beyond.Gameplay.ConditionResult", 1)
        return p.branch("e9", label+"Join")

    own = current_result("ownGetterPatched")
    p.seek(own)
    p.mark("ownGetterPatchedJoin")
    p.immediate("83f8", results["Undecided"])
    write = p.branch("0f84", "write")
    compare = current_result("secondGetterPatched")
    p.seek(compare)
    p.mark("secondGetterPatchedJoin")
    p.immediate("83f8", results["True"])
    p.fixed("400f94c6 3bde")
    ret = p.branch("74", "return", 1)
    p.mark("write")
    if p.at != write:
        raise ValueError("mission_condition.combined: own Undecided must join result write")
    p.fixed("4d85e4")
    p.branch("74", "nullReceiver", 1)
    p.fixed("8bd3 4533c0 498bcc")
    p.call("Beyond.Gameplay.GameCondition.set_result", result="void", parameters=["Beyond.Gameplay.ConditionResult"])
    p.branch("eb", "return", 1)
    p.seek(ret)
    p.mark("return")
    p.fixed("4c8d9c2480000000 498b5b38 498b7348 498be3 415f 415e 415d 415c 5fc3")
    for name, target in excluded.items():
        p.excluded(name, target)
        if name.endswith("GetterPatched"):
            p.relocation("803d", tail=1)
            p.fixed("00")
        elif name in ("nullList", "nullReceiver"):
            p.fixed("e8")
            p.take(4, variable=True)
        else:
            p.fixed("33d2 b9")
            p.take(4, variable=True)
            p.call("IFix.WrappersManagerImpl.GetPatch")
    result = p.finish()
    result.update(conditionResults=results, waitsForEveryChildDecided=True, nullChildAlsoWaits=True,
                  useProgress=False, unchangedDecidedResultSkipsSetter=True,
                  ownUndecidedForcesSetter=True,
                  condition="all entry/inline getter IsPatched guards false; successful usage and collection calls; valid Win64 enumerator storage and receiver",
                  evidenceBoundary="conditional: complete selected normal loop gate, AST call and result write flow; callee bodies, parser equivalence, IFix and live activation remain separate")
    return result


def prove_quest_state_lookup(index: Any, body: Any) -> dict[str, Any]:
    """Normal current-quest lookup plus completed owning-mission fallback.

    Caller control and typed fields are proved. Dictionary/String helpers and
    GetMissionIdByQuestId remain successful-callee assumptions. Expanded IFix
    lookup/class-initialization paths are excluded under stated selections.
    """
    if body.symbol != "Beyond.Gameplay.MissionSystem.GetQuestState":
        raise ValueError("mission_condition.quest_lookup: wrong caller")
    quest_type, mission_type = "Beyond.Gameplay.MissionSystem+QuestState", "Beyond.Gameplay.MissionSystem+MissionState"
    selected_method(index, body.pointer, body.symbol, result=quest_type, parameters=["string"])
    quest = enum_members(index, quest_type, ["None", "Completed"])
    mission = enum_members(index, mission_type, ["None", "Completed"])
    if quest["None"] != 0 or quest["Completed"] != mission["Completed"]:
        raise ValueError("mission_condition.quest_lookup: selected fallback enum mapping differs")
    p = Program(index, body)
    p.fixed("48895c2410 57 4883ec30 488bfa 488bd9 33d2 b9")
    p.take(4, variable=True)
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("33d2 84c0")
    excluded = {"patched": p.branch("0f85", "patched")}
    # The primary extent ends here; fallthrough must enter a chained region.
    if p.at != body.pointer+body.size:
        raise ValueError("mission_condition.quest_lookup: primary fallthrough boundary differs")
    p.fixed("4889742440 33f6 b9")
    p.take(4, variable=True)
    p.fixed("4889742458")
    p.call("IFix.WrappersManagerImpl.IsPatched", result="bool")
    p.fixed("84c0")
    excluded["questLookupPatched"] = p.branch("0f85", "questLookupPatched")
    p.field("488b8b", "Beyond.Gameplay.MissionSystem::currentQuests", "System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.MissionSystem+QuestData>")
    p.fixed("4885c9")
    excluded["nullQuests"] = p.branch("0f84", "nullQuests")
    p.relocation("4c8b0d")
    p.fixed("4c8d442458 488bd7")
    p.call("System.Collections.Generic.Dictionary`2.TryGetValue", result="bool")
    p.fixed("84c0")
    p.branch("74", "fallback", 1)
    p.fixed("488b442458 4885c0")
    record = p.branch("0f85", "questRecord")
    p.mark("fallback")
    p.fixed("4533c0 488bd7 488bcb")
    p.call("Beyond.Gameplay.MissionSystem.GetMissionIdByQuestId", result="string", parameters=["string"])
    p.fixed("488bf8 4885c0")
    none = p.branch("0f84", "none")
    p.fixed("397010")  # String length header vs zero ESI, valid String ABI.
    p.branch("0f86", "none")
    context_cell = p.relocation("488b0d")
    p.fixed("4889742458 39b1e0000000")
    excluded["classInitialization"] = p.branch("0f84", "classInitialization")
    p.fixed("488b81b8000000 488b10 4885d2")
    excluded["nullMissionContext"] = p.branch("0f84", "nullMissionContext")
    p.fixed("817a18")
    patch_selector = p.take(4, variable=True)
    mission_getter = index.body("Beyond.Gameplay.MissionSystem", "GetMissionData")
    selector = selected_patch_selector(index, mission_getter)
    if selector != int.from_bytes(patch_selector, "little"):
        raise ValueError("mission_condition.quest_lookup: inline patch selector differs from GetMissionData")
    patch_check = p.branch("0f8f", "missionPatchCheck")
    p.mark("missions")
    p.field("488b8b", "Beyond.Gameplay.MissionSystem::missions", "System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.MissionSystem+MissionData>")
    p.fixed("4885c9")
    p.branch("0f84", "nullMissionContext")
    p.relocation("4c8b0d")
    p.fixed("4c8d442458 488bd7")
    p.call("System.Collections.Generic.Dictionary`2.TryGetValue", result="bool")
    p.fixed("84c0")
    p.branch("74", "none", 1)
    p.fixed("488b4c2458 4885c9")
    p.branch("74", "none", 1)
    p.immediate("b8", quest["Completed"], 4)
    p.field("3941", "Beyond.Gameplay.MissionSystem+MissionData::missionState", mission_type, 1)
    p.fixed("0f45c6 488b742440")  # Noncompleted mission -> zero None.
    p.mark("return")
    p.fixed("488b5c2448 4883c430 5fc3")
    if p.at != none:
        raise ValueError("mission_condition.quest_lookup: missing/empty/default result must join None epilogue")
    p.mark("none")
    p.fixed("488b742440 33c0 488b5c2448 4883c430 5fc3")
    if p.at != record:
        raise ValueError("mission_condition.quest_lookup: cached-record branch target differs")
    p.mark("questRecord")
    p.field("8b40", "Beyond.Gameplay.MissionSystem+QuestData::questState", quest_type, 1)
    p.fixed("488b742440 488b5c2448 4883c430 5fc3")
    # The greater-count patch-table branch enters a second owned check. Its
    # selected false side checks the method cell then rejoins dictionary lookup.
    p.seek(patch_check)
    p.mark("missionPatchCheck")
    p.fixed("39b1e0000000")
    p.branch("75", "patchClassReady", 1)
    p.anonymous_call()  # Successful selected runtime class initialization.
    if p.relocation("488b0d") != context_cell:
        raise ValueError("mission_condition.quest_lookup: patch context cells differ")
    p.mark("patchClassReady")
    p.fixed("488b81b8000000 488b08 4885c9")
    p.branch("0f84", "nullMissionContext")
    p.fixed("817918")
    p.fixed(patch_selector.hex())
    absent_slot = p.branch("0f87", "absentSlot")
    p.fixed("e8")
    p.take(4, variable=True)
    p.fixed("cc")  # Inconsistent table length is excluded by valid table ABI.
    p.seek(absent_slot)
    p.mark("absentSlot")
    p.fixed("4839b1")
    p.fixed((0x20+int.from_bytes(patch_selector, "little")*8).to_bytes(4, "little").hex())
    p.branch("0f84", "missions")
    excluded["missionLookupPatched"] = p.branch("e9", "missionLookupPatched")
    for name, target in excluded.items():
        p.excluded(name, target)
        if name == "patched":
            p.fixed("b9")
            p.take(4, variable=True)
            p.call("IFix.WrappersManagerImpl.GetPatch")
        elif name in ("questLookupPatched", "missionLookupPatched"):
            p.fixed("33d2 b9")
            p.take(4, variable=True)
            p.call("IFix.WrappersManagerImpl.GetPatch")
        else:
            p.fixed("e8")
            p.take(4, variable=True)
    result = p.finish()
    result.update(stateEnum=quest_type, missionStateEnum=mission_type,
                  cachedQuestStateWins=True, noQuestRecordAndCompletedMissionReturns="Completed",
                  missingOrOtherMissionReturns="None", questStateEventRequired=False,
                  condition="unpatched lookup choices; initialized class context (or successful inline initialization); valid String/dictionary/out-slot and patch-table ABI; successful callees",
                  evidenceBoundary="conditional: selected cached quest record wins; otherwise the returned owning-mission ID and mission-state field can synthesize Completed without a new quest-state event; owner getter, dictionary semantics and event timing remain separate")
    return result


def check_condition_flow(index: Any, body: Any, spec: dict[str, Any], kind: str) -> str | None:
    from .body_claims import ClaimError
    try:
        if spec != {}:
            raise ValueError("empty symbolic claim specification required")
        {"intComparison": prove_int_comparison, "stateCallback": prove_state_callback,
         "booleanAst": prove_boolean_ast, "combinedEvaluation": prove_combined_evaluation,
         "progressAstEntry": prove_progress_ast_entry, "progressAst": prove_progress_ast,
         "progressComparison": prove_progress_comparison,
         "questLookup": prove_quest_state_lookup, "resultPropagation": prove_result_propagation}[kind](index, body)
        return None
    except (ValueError, KeyError, IndexError, RuntimeError, ClaimError) as exc:
        return f"mission_condition.{kind}: {str(exc)[:700]}"
