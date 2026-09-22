"""Re-derive the per-build fields of reviewed PureGetter contract rows.

A getter contract authors what a getter means and records, as data, where the
installed build puts it. This module owns the second half for every such
contract: the union tag from the PureGetter formatter switch, the member count
and ordinals from the generated wrapper, and the ``GetResult`` body from the
method resolver. It pins nothing and decides nothing about semantics; a
caller compares the fresh body hash with its own reviewed one.
"""
from __future__ import annotations

from typing import Any, Iterable

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs

UNION_BASE = "Beyond.MemoryPack.Beyond_Gameplay_Actions_PureGetterForMemoryPack"
PUREGETTER_BASE_MEMBERS = 7


class GetterDerivationError(RuntimeError):
    pass


def derive_getter_rows(getter_names: Iterable[str], *, with_get_result: Iterable[str] = ()) -> dict[str, Any]:
    """Current-build fields for each managed getter type, keyed by its name."""
    from scripts.game_data.il2cpp.method_resolver import MethodSpec, open_resolver
    from scripts.game_data.il2cpp.native_image import NativeImage
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    from scripts.game_data.memorypack.wrapper_members import derive_from_image

    native = check_installed_native_inputs()
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        raise GetterDerivationError(f"installed native inputs: {native.status}: {native.detail}")
    image = NativeImage(native.gameassembly, native.metadata, label="pureGetterRows")
    wrappers = derive_from_image(image)
    by_wrapped = {wrapper.wrapped_type: wrapper for wrapper in wrappers.values() if wrapper.wrapped_type}
    switch = read_union_switch(image, UNION_BASE, wrappers=wrappers)
    tags = {entry["wrapperName"]: entry for entry in switch["entries"]}
    resolver, receipt = open_resolver()
    wanted_bodies = set(with_get_result)

    rows: dict[str, Any] = {}
    refused: list[str] = []
    for name in getter_names:
        wrapper = by_wrapped.get(name)
        if wrapper is None or wrapper.name not in tags:
            refused.append(f"{name}: no PureGetter wrapper in the current build")
            continue
        entry = tags[wrapper.name]
        row = {
            "wrapperName": wrapper.name,
            "unionTag": entry["tag"],
            "serializedMemberCount": len(wrapper.members),
            "fields": [
                {"name": member.name, "ordinal": ordinal, "managedType": member.declared_type}
                for ordinal, member in enumerate(wrapper.members) if ordinal >= PUREGETTER_BASE_MEMBERS
            ],
            "switchEntry": {key: entry[key] for key in ("targetVa", "bodyVa", "usageCellVa",
                                                        "registeredTypeIndex", "typeDefinition")},
        }
        if name in wanted_bodies:
            resolved = resolver.resolve(MethodSpec(type_name=name, method_name="GetResult"))
            matches = resolved.get("matches") or []
            if resolved.get("status") != "exact" or len(matches) != 1:
                refused.append(f"{name}.GetResult: {resolved.get('status')}")
                continue
            match = matches[0]
            row["getResult"] = {
                "token": match["token"], "va": match["methodPointerVa"],
                "fileOffset": int(match["fileOffset"], 16), "bodySize": match["bodyExtent"],
                "bodySha256": match["bodySha256"].upper(),
            }
        rows[name] = row
    return {
        "nativeInputs": {
            "gameAssemblySha256": receipt["gameAssembly"]["sha256"].upper(),
            "metadataSha256": receipt["globalMetadata"]["sha256"].upper(),
        },
        "union": {key: switch[key] for key in ("base", "dispatcherVa", "tableVa", "entryCount")},
        "rows": rows,
        "refused": refused,
    }
