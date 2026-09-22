"""Validate the reviewed EntityPtr producer output-alias facts, per build.

A producer writes an entity into a ParamOutput. It *aliases* its filter when
that written entity is provably the filter entity whenever the producer runs,
so Story may name the output by the filter's constant. The reviewed readings,
authored by name and re-proved by ``--regenerate`` on the installed build:

- ``LevelEvent.OnSpecificEntityDie`` aliases: ``Process`` reads the
  ``@event_receiver`` argument, returns unless it equals ``_filterEntity``
  (``EntityPtr.op_Inequality``), then writes it to ``_entity``.
- ``EntityEvent.OnEntityEnterTrigger`` does **not** alias. Its SPECIFY_ENTITY
  listener is keyed by the target (``LevelEventManager`` registration), the
  event is raised by the trigger's own component with that entity as sender,
  and ``Process`` writes the ``trigger_cast_entity`` argument -- the entity
  that entered -- to ``entityPtr``. The build this contract was first
  recorded on read it as an alias; the current code does not support that.
- ``ScriptEvent.OnKickableInteractiveLeaveTriggerVolume`` does not alias: it
  compares the kickable's derived spawner with ``_spawnerEntity`` and writes
  the kickable itself to ``_entityOutput``.
- ``RepeatEntityPtrListAction`` does not alias: ``Execute`` writes a runtime
  list element chosen by ``_TryGetValidEntity``.

Per-build facts -- union tags, member ordinals, field offsets, method bodies --
are data, regenerated through ``levelscript_union_tags``,
``memorypack.wrapper_members``, ``il2cpp.method_resolver`` and
``il2cpp.call_graph``. A claim that no longer holds refuses the write.

Run as: python -m scripts.game_data.entityptr_output_alias_native --regenerate [--write]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA = "entityPtrOutputAliasNativeContract.v2"
DEFAULT_CONTRACT = CONTRACTS_DIR / "entityptr_output_alias.json"
#: Stable identifier cited in Story evidence; the build lives in the contract.
NATIVE_MAPPING_ID = "entityptr-producer-output-alias.v2"
ALIAS_STATUSES = frozenset({"aliases_filter_when_guard_matches", "validated_non_alias"})


@lru_cache(maxsize=1)
def load_entityptr_output_alias_contract(
    contract_path: Path = DEFAULT_CONTRACT,
) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"validator": "entityPtrOutputAliasNativeContract",
                         "gate": gate, "expected": expected, "actual": actual})

    try:
        contract = json.loads(Path(contract_path).read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", True, str(error)[:400])
        return {}, {"status": "validation_failed", "nativeMappingId": NATIVE_MAPPING_ID,
                    "validationFailures": failures}
    for gate, expected, actual in (("schema", SCHEMA, contract.get("schema")),
                                   ("status", "validated", contract.get("status"))):
        if actual != expected:
            reject(gate, expected, actual)
    inputs = contract.get("nativeInputs") or {}
    native = check_installed_native_inputs(
        str(inputs.get("gameAssemblySha256") or ""), str(inputs.get("metadataSha256") or ""))
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
        if not all(isinstance(value, int) for value in key) or key in out:
            reject("unique_producer_key", "unique integer pair", key)
            continue
        if producer.get("aliasStatus") not in ALIAS_STATUSES:
            reject("alias_status", sorted(ALIAS_STATUSES), producer.get("aliasStatus"))
            continue
        for method in producer.get("methods") or []:
            offset, size = method.get("fileOffset"), method.get("bodySize")
            if not image or not isinstance(offset, int) or not isinstance(size, int):
                continue
            digest = hashlib.sha256(image[offset:offset + size]).hexdigest().upper()
            if digest != str(method.get("bodySha256") or "").upper():
                reject("method_body_sha256", {"producer": producer.get("producerType"),
                                              "method": method.get("name")}, {"sha256": digest})
        out[key] = producer
    if failures:
        out = {}
    return out, {"status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
                 "nativeMappingId": NATIVE_MAPPING_ID, "validationFailures": failures}


def regenerate(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Re-prove every authored reading and re-record the per-build facts."""
    from scripts.game_data import levelscript_union_tags as union_tags
    from scripts.game_data.il2cpp import protocol
    from scripts.game_data.il2cpp.call_graph import CallGraph, first_missing_in_order, loaded_literals
    from scripts.game_data.il2cpp.method_resolver import MethodSpec, open_resolver
    from scripts.game_data.il2cpp.native_image import NativeImage
    from scripts.game_data.memorypack.wrapper_members import derive_from_image

    native = check_installed_native_inputs()
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        raise SystemExit(f"installed native inputs: {native.status}: {native.detail}")
    image = NativeImage(native.gameassembly, native.metadata, label="entityptrOutputAlias")
    graph = CallGraph(image)
    resolver, _receipt = open_resolver()
    metadata = image.metadata
    wrappers = {w.wrapped_type: w for w in derive_from_image(image).values() if w.wrapped_type}
    type_index = {metadata.type_full_name(t): i for i, t in enumerate(metadata.types)}
    refused: list[str] = []
    producers = []
    for authored in contract.get("producers") or []:
        managed = authored["producerType"]
        pair = union_tags.pair(authored["family"], authored["unionName"])
        wrapper = wrappers.get(managed)
        if not isinstance(pair[0], int) or wrapper is None:
            refused.append(f"{managed}: not a {authored['family']} type in the current build")
            continue
        ordinals = {member.name: ordinal for ordinal, member in enumerate(wrapper.members)}
        offsets: dict[str, int] = {}
        for owner in authored.get("fieldOwners") or [managed]:
            try:
                offsets.update(protocol.runtime_type_field_offsets(
                    metadata, image.pe, image.registration, type_index[owner]))
            except (KeyError, RuntimeError):
                pass
        row = {key: value for key, value in authored.items() if key != "review"}
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
            if resolved.get("status") != "exact" or len(matches) != 1:
                refused.append(f"{claim['type']}.{claim['name']}: {resolved.get('status')}")
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
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if not args.regenerate:
        _rows, audit = load_entityptr_output_alias_contract(args.contract)
        print(json.dumps(audit, indent=1))
        return 0 if audit["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    regenerated, refused = regenerate(json.loads(args.contract.read_bytes().decode("utf-8-sig")))
    print(json.dumps({"refused": refused, "producers": len(regenerated["producers"])}, indent=1))
    if refused:
        return 1
    if args.write:
        args.contract.write_bytes((json.dumps(regenerated, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["load_entityptr_output_alias_contract", "regenerate", "NATIVE_MAPPING_ID"]
