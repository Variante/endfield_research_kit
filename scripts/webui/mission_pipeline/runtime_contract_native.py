"""Re-derive and re-check the Mission Pipeline runtime contract's native rows.

``RUNTIME_CONTRACT`` rows name their native path as a chain of short managed
names (``MissionSystem.AcceptMission -> BasePlayerManager.SendMsg``). Those
names are what survive a client update; the addresses beside them do not. This
module resolves every hop by name in the selected build, publishes the
addresses found there, and checks that each hop is reached by the chain before
it: an arrow reads "then", so a hop may be called by any earlier hop or one call
below it (directly, through a split-off fragment, or through one unnamed
helper).

A hop into an event listener (``*.Process``) or out of a dispatcher
(``RaiseLevelEvent``, ``SendGlobal``) is runtime dispatch, which a static call
scan cannot see; such links are labelled ``dispatch`` and not claimed. Prose
hops are kept as prose. A row is ``verified`` only when every hop resolved and
every checked link holds; the reviewed finding text beside it is otherwise
unchanged, so an unverified row says so instead of borrowing a stale address.
"""
from __future__ import annotations

import copy
import re
from collections import defaultdict
from functools import cached_property
from typing import Any

from scripts.game_data.il2cpp.body_claims import BodyIndex, ClaimError

CHAIN_SECTIONS = ("localOnly", "inbound", "outbound", "nativeEvidence")
DISPATCHERS = frozenset({"RaiseLevelEvent", "SendGlobal", "RaiseScriptEvent"})


class ChainResolver:
    """Resolve short managed ``Type.Method`` spellings to unique full names."""

    def __init__(self, index: BodyIndex) -> None:
        self.index = index

    @cached_property
    def _callee_cache(self) -> dict[str, set[str]]:
        return {}

    def callees(self, full: str) -> set[str]:
        """Callees of every overload of ``full``, fragments included."""
        if full not in self._callee_cache:
            names: set[str] = set()
            for body in self.index.overload_bodies(*_split(full)):
                try:
                    rows = self.index.body_with_fragments(body)
                except ClaimError:
                    rows = body.rows
                names |= {name for _offset, name in self.index.callees(rows)}
            self._callee_cache[full] = names
        return self._callee_cache[full]

    def reach(self, sources: list[str]) -> set[str]:
        """Methods called by ``sources`` or by their direct callees."""
        first = set().union(*(self.callees(name) for name in sources))
        return first.union(*(self.callees(name) for name in first))

    def resolve(self, hop: str, previous_type: str | None) -> str | None:
        return self.index.resolve(hop, previous_type)


def _short_type(full: str) -> str:
    return re.split(r"[.+]", full.rpartition(".")[0])[-1]


def _method(full: str) -> str:
    return ".ctor" if full.endswith("..ctor") else full.rpartition(".")[2]


def verify_row(row: dict[str, Any], resolver: ChainResolver) -> dict[str, Any]:
    text = str(row.get("handler") or row.get("symbol") or "")
    hops: list[list[dict[str, Any]]] = []
    previous: str | None = None
    for hop in re.split(r"\s*->\s*", text):
        stage = []
        for alternative in hop.split(" / "):
            full = resolver.resolve(alternative, previous)
            entry: dict[str, Any] = {"name": alternative.strip(), "resolved": full}
            if full:
                pointer = min(resolver.index.pointers_by_name[full])
                entry["address"] = f"0x{pointer:x}"
            stage.append(entry)
        resolved = [entry["resolved"] for entry in stage if entry["resolved"]]
        previous = _short_type(resolved[0]) if resolved else previous
        hops.append(stage)
    links: list[dict[str, Any]] = []
    earlier: list[str] = []
    for position, stage in enumerate(hops):
        for target in stage:
            if position == 0 or not target["resolved"]:
                continue
            link: dict[str, Any] = {"to": target["resolved"], "from": list(earlier)}
            if not earlier:
                link["route"] = "unchecked_after_prose_hop"
            elif _method(target["resolved"]) == "Process" or any(
                _method(name) in DISPATCHERS for name in earlier
            ):
                link["route"] = "dispatch"
            else:
                link["holds"] = target["resolved"] in resolver.reach(earlier)
            links.append(link)
        earlier.extend(entry["resolved"] for entry in stage if entry["resolved"])
    # A middle hop the build inlined is unreachable while the hop after it is
    # still reached: the path's effect holds, only its spelling changed.
    for position, link in enumerate(links):
        if link.get("holds") is False and any(
            later.get("holds") is True for later in links[position + 1:]
        ):
            link.pop("holds")
            link["route"] = "bypassed"
    unresolved = [entry["name"] for stage in hops for entry in stage if not entry["resolved"]]
    checked = [link for link in links if "holds" in link]
    if any(link["holds"] is False for link in checked):
        status = "link_failed"
    elif unresolved:
        status = "partially_resolved"
    elif any(link.get("route") == "bypassed" for link in links):
        status = "verified_with_bypassed_hops"
    else:
        status = "verified"
    addresses = " -> ".join(
        "/".join(entry.get("address", "?") for entry in stage) for stage in hops
    )
    return {
        "status": status,
        "address": addresses if any(e.get("address") for s in hops for e in s) else "",
        "unresolvedHops": unresolved,
        "links": links,
    }


def _split(full: str) -> tuple[str, str]:
    if full.endswith("..ctor"):
        return full[:-6], ".ctor"
    type_name, _, method = full.rpartition(".")
    return type_name, method




def fallback_patch_id(index: BodyIndex, full: str) -> str | None:
    """The iFix patch id a body tests before running its AOT path."""
    pointers = sorted(index.pointers_by_name.get(full) or [])
    return index.ifix_patch_id(pointers[0]) if pointers else None


def _token(index: BodyIndex, full: str) -> str | None:
    for pointer in sorted(index.pointers_by_name.get(full) or []):
        for row in index.names_by_pointer[pointer]:
            if f"{row.get('type')}.{row.get('method')}" == full and row.get("token"):
                return str(row["token"])
    return None


def _resolve_symbol(resolver: ChainResolver, symbol: str) -> tuple[list[str | None], str]:
    text = re.sub(r"\s*\+\s*0x[0-9a-f]+", "", symbol)
    separator = " -> " if "->" in text else " / "
    names: list[str | None] = []
    previous: str | None = None
    for hop in re.split(r"\s*->\s*|\s+/\s+", text):
        hop = re.sub(r"\s+callback$", "", hop.strip())
        full = resolver.resolve(hop, previous)
        names.append(full)
        if full:
            previous = _short_type(full)
    return names, separator


def refresh_record(record: dict[str, Any], resolver: ChainResolver) -> None:
    """Re-derive a symbol record's address, token and iFix patch id by name."""
    index = resolver.index
    names, separator = _resolve_symbol(resolver, str(record["symbol"]))
    resolved = [name for name in names if name]
    addresses = [f"0x{min(index.pointers_by_name[name]):x}" for name in resolved]
    if "addresses" in record or "tokens" in record:
        record["addresses"] = addresses
        record["tokens"] = [_token(index, name) for name in resolved]
        if "fallbackPatchIds" in record:
            record["fallbackPatchIds"] = [fallback_patch_id(index, name) for name in resolved]
        if "address" in record:
            record["address"] = separator.join(addresses)
        if "token" in record:
            record["token"] = None
    else:
        record["address"] = separator.join(addresses)
        if "token" in record:
            record["token"] = _token(index, resolved[0]) if len(resolved) == 1 else None
        if "fallbackPatchId" in record:
            record["fallbackPatchId"] = fallback_patch_id(index, resolved[0]) if len(resolved) == 1 else None
    record["nativeResolution"] = "resolved" if len(resolved) == len(names) else "partially_resolved"


def _refresh_records(value: Any, resolver: ChainResolver) -> None:
    if isinstance(value, dict):
        if isinstance(value.get("symbol"), str) and any(
            key in value for key in ("address", "token", "fallbackPatchId", "addresses", "tokens")
        ):
            refresh_record(value, resolver)
        for item in value.values():
            _refresh_records(item, resolver)
    elif isinstance(value, list):
        for item in value:
            _refresh_records(item, resolver)


def _blackboard_key_slot(index: BodyIndex, full: str, callee: str) -> set[int]:
    """Static key slots loaded into rdx for each call to a ParamBlackboard method."""
    slots: set[int] = set()
    for body in index.overload_bodies(*_split(full)):
        key = None
        for row in index.body_with_fragments(body):
            text = str(row.get("text") or "")
            match = re.fullmatch(r"mov rdx, \[rip[+-]0x[0-9a-f]+ => 0x([0-9a-f]+)\]", text)
            if match:
                key = int(match.group(1), 16)
            call = re.fullmatch(r"call 0x([0-9a-f]+)", text)
            if call and callee in index.names_of(int(call.group(1), 16)):
                if key is not None:
                    slots.add(key)
                key = None
    return slots


def _shared_key_slot(index: BodyIndex, writer: str, reader: str) -> tuple[str | None, int]:
    """The key slot the writer stores under and the reader loads, and its references."""
    shared = _blackboard_key_slot(index, writer, "Beyond.Gameplay.ParamBlackboard.SetValue") & (
        _blackboard_key_slot(index, reader, "Beyond.Gameplay.ParamBlackboard.TryGetValue")
    )
    if len(shared) != 1:
        return None, 0
    slot = shared.pop()
    pattern = re.compile(rf"\[rip[+-]0x[0-9a-f]+ => 0x{slot:x}\]")
    count = sum(
        1
        for full in (writer, reader)
        for body in index.overload_bodies(*_split(full))
        for row in index.body_with_fragments(body)
        if pattern.search(str(row.get("text") or ""))
    )
    return f"0x{slot:x}", count


def refresh_runtime_facts(contract: dict[str, Any], resolver: ChainResolver) -> None:
    """Re-derive the per-build facts the reviewed sections publish."""
    index = resolver.index
    for section in ("serverPlaceholder", "levelScriptCtxTokenAudit", "protobufIdentityCarrierAudit",
                    "airWallMissionRadioContext"):
        _refresh_records(contract.get(section), resolver)

    placeholder = contract.get("serverPlaceholder") or {}
    condition = resolver.resolve("GameConditionServerPlaceHolder.get_conditionType", None)
    binders = sorted(
        name for name in index.pointers_by_name
        if name.startswith("Beyond.Gameplay.MissionSystem") and ".<StartQuest>g__BindCallback|" in name
    )
    checks: dict[str, bool] = {}
    if condition:
        placeholder["conditionTypeAddress"] = f"0x{min(index.pointers_by_name[condition]):x}"
        body = index.overload_bodies(*_split(condition))[0]
        checks["conditionTypeReturnsIntMax"] = "mov eax, 0x7fffffff" in {
            str(row.get("text") or "") for row in body.rows
        }
    else:
        placeholder["conditionTypeAddress"] = None
    if len(binders) == 1:
        placeholder["startQuestBinderAddress"] = f"0x{min(index.pointers_by_name[binders[0]]):x}"
        rows = index.body_with_fragments(index.overload_bodies(*_split(binders[0]))[0])
        checks["binderRequiresClientOnly"] = any(
            re.fullmatch(r"cmp \w+, 0x270f", str(row.get("text") or "")) for row in rows
        )
    else:
        placeholder["startQuestBinderAddress"] = None
    placeholder["relevantMethods"] = [
        name for name in (condition, binders[0] if len(binders) == 1 else None) if name
    ]
    placeholder["relevantPatchIds"] = [
        patch_id for patch_id in (fallback_patch_id(index, name) for name in placeholder["relevantMethods"])
        if patch_id
    ]
    placeholder["nativeChecks"] = checks
    if not all(checks.values()) or len(checks) != 2:
        placeholder["confidence"] = "reviewed_claim_not_reproved"

    ctx = contract.get("levelScriptCtxTokenAudit") or {}
    writer = resolver.resolve("GameplayNetwork._Handle_SceneTriggerClientLevelScriptEvent", None)
    reader = resolver.resolve("CallServer.Execute", None)
    slot, count = _shared_key_slot(index, writer, reader) if writer and reader else (None, 0)
    ctx["paramBlackboardKeySlot"] = slot
    ctx["directKeySlotReferences"] = count if slot else None


def verify_runtime_contract(
    contract: dict[str, Any], index: BodyIndex | None, *, unavailable_reason: str = ""
) -> dict[str, Any]:
    """Return the contract with live addresses and a per-row verification."""
    verified = copy.deepcopy(contract)
    resolver = ChainResolver(index) if index is not None else None
    if resolver is not None:
        refresh_runtime_facts(verified, resolver)
    else:
        _strip_build_facts(verified)
    counts: dict[str, int] = defaultdict(int)
    for section in CHAIN_SECTIONS:
        for row in verified.get(section) or []:
            if resolver is None:
                row["address"] = ""
                row["nativeVerification"] = {"status": "native_unavailable", "reason": unavailable_reason}
            else:
                result = verify_row(row, resolver)
                row["address"] = result.pop("address")
                row["nativeVerification"] = result
                if "fallbackPatchId" in row:
                    full = resolver.resolve(str(row["symbol"]), None)
                    row["fallbackPatchId"] = fallback_patch_id(index, full) if full else None
            counts[row["nativeVerification"]["status"]] += 1
    verified["nativeVerificationSummary"] = dict(sorted(counts.items()))
    return verified


def _strip_build_facts(value: Any) -> None:
    """Without the selected build, publish names and findings, no addresses."""
    if isinstance(value, dict):
        for key in list(value):
            if key in {"address", "token", "fallbackPatchId", "addresses", "tokens", "fallbackPatchIds",
                       "conditionTypeAddress", "startQuestBinderAddress", "paramBlackboardKeySlot",
                       "relevantPatchIds"}:
                value[key] = None
            else:
                _strip_build_facts(value[key])
    elif isinstance(value, list):
        for item in value:
            _strip_build_facts(item)


__all__ = ["ChainResolver", "fallback_patch_id", "refresh_runtime_facts", "verify_row", "verify_runtime_contract"]
