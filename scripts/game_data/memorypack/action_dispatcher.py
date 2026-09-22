"""Enumerate the whole AbilityActionData union dispatcher of the selected build.

Reviewed contracts prove one union tag at a time: the switch entry, the route
target, the rip-relative usage cell that route loads, the registered type index
that cell encodes, and the generated wrapper that index names.  That chain is
mechanical, so it does not have to be walked by hand once per tag.  This module
walks every entry of the dispatcher's switch table and reports the wrapper each
tag routes to, joined with the member order
``scripts.game_data.memorypack.wrapper_members`` derives for it.

The table's own identity is not rediscovered or hard-coded here.  It is read
from the reviewed contracts that already pin it -- RVA, entry count and the
table's SHA256 -- every such contract must agree, and the live image's bytes are
re-hashed against that pin.  A build whose table differs therefore produces
nothing rather than a plausible-looking wrong route set.

What this establishes is a tag's *identity*: which generated wrapper the route
selects, and what that wrapper's members are called.  It is evidence tier
``direct``.  It does not read a payload, establish a cursor, a member width, a
nested extent or an EOF, and it does not promote a tag to ``exact``: a route
enumerated here still needs a reader, and a reviewed contract if its bytes are
to be pinned.  Its value is that an unreviewed tag stops being anonymous.

Every contracted tag is re-derived and compared.  A contradiction fails the run
closed rather than publishing a route set that disagrees with reviewed evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.memorypack.wrapper_members import WrapperType, derive_from_image
from scripts.repo_paths import REPO_ROOT as REPO


DEFAULT_OUTPUT = REPO / "reports/game_data/memorypack_action_dispatcher.json"
WRAPPER_SUFFIX = "ForMemoryPack"
# The route prologue this walk understands: ``mov r64, [rip+disp32]`` loading
# the union's type-usage cell.  Three bytes of opcode plus a four-byte
# displacement, relative to the end of the seven-byte instruction.
RIP_QWORD_LOADS = (b"\x48\x8b\x0d", b"\x48\x8b\x05", b"\x48\x8b\x15", b"\x4c\x8b\x05")
RIP_LOAD_LENGTH = 7
# The usage-cell tag an unresolved type reference carries.
TYPE_USAGE_TAG = 1


@dataclass(frozen=True)
class SwitchTable:
    """The dispatcher's switch table, as the reviewed contracts pin it."""

    rva: int
    entry_count: int
    sha256: str
    contracts: tuple[str, ...]

    def row(self) -> dict[str, Any]:
        return {
            "switchTableRva": self.rva,
            "switchEntryCount": self.entry_count,
            "switchTableSha256": self.sha256,
            "pinnedByContracts": list(self.contracts),
        }


@dataclass(frozen=True)
class ActionRoute:
    """One union tag's resolved route, or the gate that stopped it."""

    tag: int
    target_rva: int
    status: str
    detail: str | None = None
    usage_cell_rva: int | None = None
    usage_raw_hex: str | None = None
    registered_type_index: int | None = None
    wrapper_type_definition: int | None = None
    wrapper_name: str | None = None
    member_order: tuple[str, ...] = ()
    member_kinds: tuple[str, ...] = ()
    inherited_member_count: int | None = None

    def row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "unionTag": self.tag,
            "tagEncodingHex": f"{self.tag:02X}",
            "switchTargetRva": self.target_rva,
            "status": self.status,
        }
        if self.detail is not None:
            row["detail"] = self.detail
        if self.usage_cell_rva is not None:
            row["usageCellRva"] = self.usage_cell_rva
            row["usageRawHex"] = self.usage_raw_hex
            row["registeredTypeIndex"] = self.registered_type_index
        if self.wrapper_name is not None:
            row["wrapperTypeDefinition"] = self.wrapper_type_definition
            row["wrapperName"] = self.wrapper_name
            row["serializedMemberCount"] = len(self.member_order)
            row["inheritedMemberCount"] = self.inherited_member_count
            row["generatedMemberOrder"] = list(self.member_order)
            row["generatedMemberKinds"] = list(self.member_kinds)
        return row


def _blocks(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if "switchTableRva" in value and "unionTag" in value:
            yield value
        for nested in value.values():
            yield from _blocks(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _blocks(nested)


def reviewed_switch_table(
    contracts_dir: Path = CONTRACTS_DIR,
) -> tuple[SwitchTable, dict[int, dict[str, Any]]]:
    """The switch table the reviewed contracts pin, plus their per-tag rows.

    Every contract that pins the table must pin the same one.  Disagreement is
    a reviewed-evidence conflict, not something to resolve by majority.
    """
    identities: dict[tuple[int, int, str], list[str]] = {}
    reviewed: dict[int, dict[str, Any]] = {}
    for path in sorted(contracts_dir.glob("*.json")):
        try:
            value = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        for block in _blocks(value):
            key = (
                int(block["switchTableRva"]),
                int(block["switchEntryCount"]),
                str(block["switchTableSha256"]).upper(),
            )
            identities.setdefault(key, []).append(path.name)
            tag = int(block["unionTag"])
            existing = reviewed.get(tag)
            if existing is not None and existing.get("wrapperTypeDefinition") is not None:
                continue
            reviewed[tag] = block
    if not identities:
        raise ValueError("no reviewed contract pins an action dispatcher switch table")
    if len(identities) != 1:
        raise ValueError(f"conflicting-switch-table-pins={sorted(identities)}")
    (rva, entry_count, sha256), sources = next(iter(identities.items()))
    if not 0 < entry_count <= 4096:
        raise ValueError(f"implausible-switch-entry-count={entry_count}")
    return SwitchTable(rva, entry_count, sha256, tuple(sorted(set(sources)))), reviewed


def _resolve_route(
    image: NativeImage, wrappers: dict[int, WrapperType], tag: int, target_rva: int
) -> ActionRoute:
    pe = image.pe
    try:
        prologue = pe.bytes_at_va(pe.image_base + target_rva, RIP_LOAD_LENGTH + 1)
    except (OSError, ValueError, struct.error) as error:
        return ActionRoute(tag, target_rva, "route-unreadable", str(error))
    if prologue[:3] not in RIP_QWORD_LOADS:
        # A route shaped some other way is not guessed at; it is reported so a
        # future build's new prologue is visible instead of silently dropped.
        return ActionRoute(
            tag, target_rva, "unsupported-route-prologue", prologue[:3].hex().upper()
        )
    cell_va = pe.image_base + target_rva + RIP_LOAD_LENGTH + struct.unpack_from("<i", prologue, 3)[0]
    try:
        usage = pe.bytes_at_va(cell_va, 8)
    except (OSError, ValueError, struct.error) as error:
        return ActionRoute(tag, target_rva, "usage-cell-unreadable", str(error))
    try:
        type_index = unresolved_usage_index(
            usage,
            image.registration["typesCount"],
            tag=TYPE_USAGE_TAG,
            source=str(image.gameassembly),
            offset=cell_va,
        )
    except Exception as error:  # ContextError and its bounds failures
        return ActionRoute(
            tag, target_rva, "usage-cell-not-an-unresolved-type", str(error),
            usage_cell_rva=cell_va - pe.image_base, usage_raw_hex=usage.hex().upper(),
        )
    common = {
        "usage_cell_rva": cell_va - pe.image_base,
        "usage_raw_hex": usage.hex().upper(),
        "registered_type_index": type_index,
    }
    try:
        type_pointer = pe.u64_at_va(int(image.registration["types"], 16) + type_index * 8)
        definition = struct.unpack_from("<Q", pe.bytes_at_va(type_pointer, 16))[0]
        name = image.type_name(definition)
    except (OSError, ValueError, IndexError, struct.error) as error:
        return ActionRoute(tag, target_rva, "registered-type-unresolved", str(error), **common)
    if not name.endswith(WRAPPER_SUFFIX):
        return ActionRoute(tag, target_rva, "not-a-generated-wrapper", name, **common)
    wrapper = wrappers.get(definition)
    if wrapper is None:
        return ActionRoute(
            tag, target_rva, "wrapper-members-unavailable", name,
            wrapper_type_definition=definition, wrapper_name=name, **common,
        )
    return ActionRoute(
        tag, target_rva, "resolved", None,
        wrapper_type_definition=definition, wrapper_name=name,
        member_order=tuple(member.name for member in wrapper.members),
        member_kinds=tuple(member.kind for member in wrapper.members),
        inherited_member_count=len(wrapper.inherited_members),
        **common,
    )


def _compare_reviewed(
    routes: dict[int, ActionRoute], reviewed: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    """Re-derive every contracted tag; a contradiction is a hard failure."""
    checked = agreed = unrecorded = 0
    conflicts: list[dict[str, Any]] = []
    for tag, block in sorted(reviewed.items()):
        recorded = block.get("wrapperTypeDefinition")
        route = routes.get(tag)
        if recorded is None:
            unrecorded += 1
            continue
        checked += 1
        if route is not None and route.wrapper_type_definition == recorded:
            agreed += 1
            continue
        conflicts.append({
            "unionTag": tag,
            "recordedWrapperTypeDefinition": recorded,
            "recordedWrapperName": block.get("wrapperName"),
            "derivedWrapperTypeDefinition": route.wrapper_type_definition if route else None,
            "derivedWrapperName": route.wrapper_name if route else None,
            "derivedStatus": route.status if route else "missing",
        })
    return {
        "tags": sorted(reviewed),
        "reviewedTags": len(reviewed),
        "checked": checked,
        "agreed": agreed,
        "withoutRecordedWrapper": unrecorded,
        "conflicts": conflicts,
    }


def load_action_routes(
    *, gameassembly: Path | None = None, metadata: Path | None = None,
    contracts_dir: Path = CONTRACTS_DIR,
) -> tuple[dict[int, ActionRoute], dict[str, Any]]:
    """Return ``{unionTag: ActionRoute}`` for the selected build, or nothing."""
    audit: dict[str, Any] = {"status": "enumeration_failed", "failures": []}
    try:
        gate = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
        audit["nativeGate"] = {"status": gate.status, "detail": gate.detail}
        if gate.status != "validated":
            audit["failures"].append({
                "gate": "installed_native_inputs",
                "expected": "validated", "actual": gate.status, "detail": gate.detail,
            })
            audit["status"] = gate.status
            return {}, audit
        audit["nativeInputs"] = {
            "GameAssembly.dll": gate.gameassembly_sha256,
            "global-metadata.dat": gate.metadata_sha256,
        }
        table, reviewed = reviewed_switch_table(contracts_dir)
        audit["switchTable"] = table.row()
        image = NativeImage(gate.gameassembly, gate.metadata, label="actionDispatcher")
        raw = image.pe.bytes_at_va(image.pe.image_base + table.rva, table.entry_count * 4)
        actual = hashlib.sha256(raw).hexdigest().upper()
        if actual != table.sha256:
            audit["failures"].append({
                "gate": "switch_table_sha256", "expected": table.sha256, "actual": actual,
            })
            audit["status"] = "mismatched"
            return {}, audit
        wrappers = derive_from_image(image)
        routes = {
            tag: _resolve_route(image, wrappers, tag, struct.unpack_from("<I", raw, tag * 4)[0])
            for tag in range(table.entry_count)
        }
        comparison = _compare_reviewed(routes, reviewed)
        audit["reviewedComparison"] = comparison
        if comparison["conflicts"]:
            audit["failures"].append({
                "gate": "reviewed_tag_agreement",
                "detail": f"{len(comparison['conflicts'])} contracted tag(s) disagree",
            })
            audit["status"] = "conflicted"
            return {}, audit
        resolved = sum(1 for route in routes.values() if route.status == "resolved")
        audit.update(
            status="validated",
            routeCount=len(routes),
            resolvedRoutes=resolved,
            unresolvedRoutes=len(routes) - resolved,
            tagsWithoutReviewedContract=sum(1 for tag in routes if tag not in reviewed),
            evidenceBoundary={
                "direct": (
                    "Each tag's switch entry, route prologue usage cell, registered type "
                    "index and generated wrapper identity are read from the selected build, "
                    "and every reviewed tag re-derives to its contracted wrapper."
                ),
                "structuralOnly": (
                    "Member names and kinds come from the generated wrapper; no payload is "
                    "read and no cursor, member width, nested extent or EOF is established."
                ),
                "conditional": (
                    "The switch table identity is the one the reviewed contracts pin and the "
                    "image's bytes re-hash to; a build whose table differs yields no routes."
                ),
            },
        )
        return routes, audit
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as error:
        audit["failures"].append({"gate": "route_enumeration", "detail": str(error)})
        return {}, audit


def build(output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    routes, audit = load_action_routes()
    reviewed_tags = set(audit.get("reviewedComparison", {}).get("tags", ()))
    statuses: dict[str, int] = {}
    for route in routes.values():
        statuses[route.status] = statuses.get(route.status, 0) + 1
    report = {
        "schema": "endfield.memorypack-action-dispatcher.v1",
        "audit": audit,
        "summary": {
            "status": audit["status"],
            "routes": len(routes),
            "routeStatuses": dict(sorted(statuses.items())),
            "reviewedAgreed": audit.get("reviewedComparison", {}).get("agreed"),
            "reviewedChecked": audit.get("reviewedComparison", {}).get("checked"),
            "newTags": sum(1 for tag in routes if tag not in reviewed_tags),
            "elapsedSeconds": round(time.perf_counter() - started, 3),
        },
        "routes": [
            {**routes[tag].row(), "hasReviewedContract": tag in reviewed_tags}
            for tag in sorted(routes)
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tag", action="append", default=[],
                        help="print one union tag's route instead of writing a report")
    args = parser.parse_args()
    if args.tag:
        routes, audit = load_action_routes()
        if audit["status"] != "validated":
            print(json.dumps(audit, ensure_ascii=False), file=sys.stderr)
            return 1
        for raw_tag in args.tag:
            route = routes.get(int(raw_tag, 0))
            if route is None:
                print(json.dumps({"tag": raw_tag, "status": "not-found"}), file=sys.stderr)
                return 1
            print(json.dumps(route.row(), ensure_ascii=False))
        return 0
    try:
        report = build(args.output)
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
