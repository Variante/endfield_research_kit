"""Validate the reviewed EntityPtr producer output-alias facts, per build.

A producer writes an entity into a ParamOutput. It *aliases* its filter when
that written entity is provably the filter entity whenever the producer runs,
so Story may name the output by the filter's constant. The reviewed readings,
authored by name and re-proved by ``--regenerate`` on the selected build:

- ``LevelEvent.OnSpecificEntityDie`` aliases, but only as logic-id identity:
  ``Process`` reads the ``@event_receiver`` argument, returns while
  ``EntityPtr.op_Inequality(receiver, _filterEntity)`` holds, and otherwise
  writes the receiver to ``_entity``. ``op_Inequality`` is ``Equals`` xor 1,
  and ``EntityPtr.Equals`` first requires both ``useSlotId`` flags to match;
  with ``useSlotId`` false it compares ``logicId`` alone. The row therefore
  carries ``constantCondition = {"useSlotId": false}`` and proves that the
  output names the filter's logic id, never that the two 40-byte values are
  equal. A filter that addresses a script slot (``useSlotId`` true) compares
  ``slotId`` against a runtime slot binding no static input supplies; that
  path is recorded as ``slotPath.status = "unresolved"`` and a consumer must
  not alias it.
- ``EntityEvent.OnEntityEnterTrigger`` does **not** alias. Its SPECIFY_ENTITY
  listener is keyed by the target (``LevelEventManager`` registration), the
  event is raised by the trigger's own component with that entity as sender,
  and ``Process`` writes the ``trigger_cast_entity`` argument -- the entity
  that entered -- to ``entityPtr``.
- ``ScriptEvent.OnKickableInteractiveLeaveTriggerVolume`` does not alias: it
  compares the kickable's derived spawner with ``_spawnerEntity`` and writes
  the kickable itself to ``_entityOutput``.
- ``RepeatEntityPtrListAction`` does not alias: ``Execute`` writes a runtime
  list element chosen by ``_TryGetValidEntity``.

Evidence tiers (``evidenceBoundary`` in the contract): union tags, member
ordinals, field offsets and method-body hashes are ``exact`` for the pinned
build; which entity each producer writes is ``direct`` (read from the bodies);
every reading is ``conditional`` on no installed IFix patch replacing one of
the bodies, all of which carry IFix hook checks; the slot-id path is
``unresolved``. The loader refuses an alias row without the constant
condition or with a slot path marked anything but unresolved.

Per-build facts are regenerated through ``levelscript_union_tags``,
``memorypack.wrapper_members``, ``il2cpp.method_resolver`` and
``il2cpp.call_graph`` against the build the selectors name; nothing is carried
over from an earlier build. A claim that no longer holds refuses the write.
An overloaded method (``EntityPtr.Equals``) is pinned through ``calledFrom``:
the one overload the named reviewed caller directly calls.
The loader forwards ``gameassembly``/``metadata`` (or ``game_root``) to
``check_installed_native_inputs`` so the caller's selected pair, not a
module-global root, decides the gate.

Run as: python -m scripts.game_data.entityptr_output_alias_native --regenerate [--write]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA = "endfield.entityptr-output-alias-native.v3"
DEFAULT_CONTRACT = CONTRACTS_DIR / "entityptr_output_alias.json"
#: Stable identifier cited in Story evidence; the build lives in the contract.
NATIVE_MAPPING_ID = "entityptr-producer-output-alias.v3"
ALIAS_STATUS = "aliases_filter_when_guard_matches"
ALIAS_STATUSES = frozenset({ALIAS_STATUS, "validated_non_alias"})
#: The only selection under which the alias reading holds.
ALIAS_CONSTANT_CONDITION = {"useSlotId": False}
BOUNDARY_TIERS = ("conditional", "direct", "exact", "unresolved")


def _selected(gameassembly: Path | None, metadata: Path | None,
              game_root: Path | None) -> tuple[Path | None, Path | None]:
    if game_root is not None and gameassembly is None and metadata is None:
        root = Path(game_root)
        return root.parent / "GameAssembly.dll", root / "il2cpp_data/Metadata/global-metadata.dat"
    return gameassembly, metadata


def load_entityptr_output_alias_contract(
    contract_path: Path = DEFAULT_CONTRACT, *, gameassembly: Path | None = None,
    metadata: Path | None = None, game_root: Path | None = None,
) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    gameassembly, metadata = _selected(gameassembly, metadata, game_root)
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "entityPtrOutputAliasNativeContract",
                         "gate": gate, "expected": expected, "actual": actual})

    def audit(native: Any = None) -> dict[str, Any]:
        result = {"status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
                  "nativeMappingId": NATIVE_MAPPING_ID, "validationFailures": failures}
        if native is not None:
            result["nativeInputs"] = {"status": native.status, "detail": native.detail}
        return result

    try:
        contract = json.loads(Path(contract_path).read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", True, str(error)[:400])
        return {}, audit()
    for gate, expected, actual in (("schema", SCHEMA, contract.get("schema")),
                                   ("status", "validated", contract.get("status")),
                                   ("native_mapping_id", NATIVE_MAPPING_ID, contract.get("nativeMappingId"))):
        if actual != expected:
            reject(gate, expected, actual)
    boundary = contract.get("evidenceBoundary")
    if not isinstance(boundary, dict) or tuple(sorted(boundary)) != BOUNDARY_TIERS:
        reject("evidence_boundary_tiers", list(BOUNDARY_TIERS),
               sorted(boundary) if isinstance(boundary, dict) else boundary)
    inputs = contract.get("nativeInputs") or {}
    native = check_installed_native_inputs(
        str(inputs.get("gameAssemblySha256") or ""), str(inputs.get("metadataSha256") or ""),
        gameassembly=gameassembly, metadata=metadata)
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject("installed_native_inputs", NATIVE_EVIDENCE_VALIDATED,
               {"status": native.status, "detail": native.detail})
    image = b""
    if not failures:
        try:
            image = Path(native.gameassembly).read_bytes()
        except OSError as error:
            reject("read_gameassembly", True, str(error)[:400])
    out: dict[tuple[int, int], dict[str, Any]] = {}
    for producer in contract.get("producers") or []:
        key = (producer.get("unionTag"), producer.get("serializedMemberCount"))
        name = producer.get("producerType")
        if not all(isinstance(value, int) for value in key) or key in out:
            reject("unique_producer_key", "unique integer pair", key)
            continue
        status = producer.get("aliasStatus")
        if status not in ALIAS_STATUSES:
            reject("alias_status", sorted(ALIAS_STATUSES), status)
            continue
        if status == ALIAS_STATUS:
            if producer.get("constantCondition") != ALIAS_CONSTANT_CONDITION:
                reject("alias_constant_condition",
                       {"producer": name, "constantCondition": ALIAS_CONSTANT_CONDITION},
                       producer.get("constantCondition"))
            slot_status = (producer.get("slotPath") or {}).get("status")
            if slot_status != "unresolved":
                reject("alias_slot_path_unresolved", {"producer": name, "status": "unresolved"}, slot_status)
        methods = producer.get("methods") or []
        if not methods:
            reject("reviewed_methods", {"producer": name, "methods": ">=1"}, 0)
        for method in methods:
            offset, size = method.get("fileOffset"), method.get("bodySize")
            if not isinstance(offset, int) or not isinstance(size, int):
                reject("method_body_extent", {"producer": name, "method": method.get("name")},
                       {"fileOffset": offset, "bodySize": size})
                continue
            if not image:
                continue
            digest = hashlib.sha256(image[offset:offset + size]).hexdigest().upper()
            if digest != str(method.get("bodySha256") or "").upper():
                reject("method_body_sha256", {"producer": name, "method": method.get("name")},
                       {"sha256": digest})
        out[key] = producer
    if failures:
        out = {}
    return out, audit(native)


def regenerate(contract: dict[str, Any], *, gameassembly: Path | None = None,
               metadata: Path | None = None) -> tuple[dict[str, Any], list[str]]:
    """Re-prove every authored reading and re-record the per-build facts."""
    from scripts.game_data import levelscript_union_tags as union_tags
    from scripts.game_data.il2cpp import protocol
    from scripts.game_data.il2cpp.call_graph import CallGraph, calls_named, first_missing_in_order, loaded_literals
    from scripts.game_data.il2cpp.method_resolver import MethodSpec, open_resolver
    from scripts.game_data.il2cpp.native_image import NativeImage
    from scripts.game_data.memorypack.wrapper_members import derive_from_image

    native = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        raise SystemExit(f"installed native inputs: {native.status}: {native.detail}")
    image = NativeImage(native.gameassembly, native.metadata, label="entityptrOutputAlias")
    graph = CallGraph(image)
    resolver, _receipt = open_resolver(gameassembly=Path(native.gameassembly), metadata=Path(native.metadata))
    metadata_file = image.metadata
    wrappers = {w.wrapped_type: w for w in derive_from_image(image).values() if w.wrapped_type}
    type_index = {metadata_file.type_full_name(t): i for i, t in enumerate(metadata_file.types)}
    refused: list[str] = []
    producers = []
    for authored in contract.get("producers") or []:
        managed = authored["producerType"]
        pair = union_tags.pair(authored["family"], authored["unionName"])
        wrapper = wrappers.get(managed)
        if not isinstance(pair[0], int) or wrapper is None:
            refused.append(f"{managed}: not a {authored['family']} type in the selected build")
            continue
        ordinals = {member.name: ordinal for ordinal, member in enumerate(wrapper.members)}
        offsets: dict[str, int] = {}
        for owner in authored.get("fieldOwners") or [managed]:
            try:
                offsets.update(protocol.runtime_type_field_offsets(
                    metadata_file, image.pe, image.registration, type_index[owner]))
            except (KeyError, RuntimeError):
                pass
        row = {key: value for key, value in authored.items() if key not in ("review", "methods")}
        row.update({"unionTag": pair[0], "serializedMemberCount": pair[1]})
        for role in ("outputField", "filterField", "runtimeInputField"):
            field = authored.get(role)
            if not field:
                continue
            name = field["fieldName"]
            if name not in ordinals:
                refused.append(f"{managed}.{name}: not a serialized member now")
                continue
            row[role] = {**field, "memberOrdinalZeroBased": ordinals[name],
                         "fieldOffset": hex(offsets[name]) if name in offsets else None}
        methods = []
        for claim in (authored.get("review") or {}).get("methods") or []:
            resolved = resolver.resolve(MethodSpec(type_name=claim["type"], method_name=claim["name"]))
            matches = resolved.get("matches") or []
            caller = claim.get("calledFrom")
            if caller and resolved.get("status") == "exact" and len(matches) > 1:
                # An overloaded name is pinned by the one overload the reviewed
                # caller reaches, never by metadata order.
                parent = resolver.resolve(MethodSpec(type_name=caller["type"], method_name=caller["name"]))
                parents = parent.get("matches") or []
                targets = set()
                if parent.get("status") == "exact" and len(parents) == 1:
                    targets = {call.target_va for call in graph.direct_calls(
                        int(parents[0]["methodPointerVa"], 16), parents[0]["bodyExtent"])
                        if calls_named(call, caller["call"])}
                matches = [match for match in matches if int(match["methodPointerVa"], 16) in targets]
            if resolved.get("status") != "exact" or len(matches) != 1:
                refused.append(f"{claim['type']}.{claim['name']}: {resolved.get('status')} ({len(matches)} matches)")
                continue
            match = matches[0]
            va, size = int(match["methodPointerVa"], 16), match["bodyExtent"]
            missing = first_missing_in_order(graph.direct_calls(va, size), claim.get("calls") or [])
            if missing:
                refused.append(f"{claim['type']}.{claim['name']}: no ordered call to {missing}")
            absent = set(claim.get("literals") or []) - loaded_literals(graph, va, size)
            if absent:
                refused.append(f"{claim['type']}.{claim['name']}: does not load {sorted(absent)}")
            methods.append({"type": claim["type"], "name": claim["name"], "va": match["methodPointerVa"],
                            "fileOffset": int(match["fileOffset"], 16), "bodySize": size,
                            "bodySha256": match["bodySha256"].upper()})
        row["methods"] = methods
        row["review"] = authored.get("review")
        producers.append(row)
    return {
        **{key: value for key, value in contract.items() if key not in ("producers", "nativeInputs", "metadata")},
        "schema": SCHEMA, "status": "validated", "nativeMappingId": NATIVE_MAPPING_ID,
        "nativeInputs": {"gameAssemblySha256": native.gameassembly_sha256.upper(),
                         "metadataSha256": native.metadata_sha256.upper()},
        "producers": producers,
    }, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if not args.regenerate:
        _rows, audit = load_entityptr_output_alias_contract(
            args.contract, gameassembly=args.gameassembly, metadata=args.metadata)
        print(json.dumps(audit, indent=1))
        return 0 if audit["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    regenerated, refused = regenerate(json.loads(args.contract.read_bytes().decode("utf-8-sig")),
                                      gameassembly=args.gameassembly, metadata=args.metadata)
    print(json.dumps({"refused": refused, "producers": len(regenerated["producers"])}, indent=1))
    if refused:
        return 1
    if args.write:
        args.contract.write_bytes((json.dumps(regenerated, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["load_entityptr_output_alias_contract", "regenerate", "NATIVE_MAPPING_ID",
           "ALIAS_CONSTANT_CONDITION", "SCHEMA"]
