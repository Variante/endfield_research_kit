"""Regenerate the buff residual and frontier native contracts against the selected build.

Covers ``buff_residual_actions_native.json`` (validated by
``memorypack/buff_residual_actions.py``) and the ``buff_frontiers_native``
family (``buff_residual_frontier.json``, ``buff_frontier6..9.json``).

What it re-derives from the installed build: union tag, switch table
identity, switch target and route window, usage cell, registered type index,
wrapper/actual type definitions, Deserialize method rows, setter rows
(``<type-index:N>`` placeholders renumbered), whole-function code windows
(pdata extent with trailing INT3 padding trimmed, ending in RET or JMP),
nested method-spec contexts, and ``nativeInputs``.

What it never changes: reviewed names, ``readOrder``, ``generatedOwnFields``,
reached file/offset evidence, boundaries.  It refuses (writing nothing for
that contract) when a reviewed claim does not re-prove: member count or own
field list differs (an inserted member is named as such; even an append needs
review), setter names/types differ, a nested context's type sequence
differs, or a window is a reviewed sub-range fragment whose boundary cannot
be re-derived mechanically.

Run: ``python -m scripts.game_data.buff_frontiers_regenerate --regenerate [--write]``.
"""
from __future__ import annotations

import copy
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any, Callable

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import generic_type_carrier, method_spec_usage_index
from scripts.game_data.levelscript_two_routes_native import (
    RouteRefused,
    _sha256_upper,
    _window,
    open_selected_build,
)

UNION = "Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
CONTRACT_FILES = {
    "residual_actions": "buff_residual_actions_native.json",
    "residual_frontier": "buff_residual_frontier.json",
    "frontier6": "buff_frontier6.json",
    "frontier7": "buff_frontier7.json",
    "frontier8": "buff_frontier8.json",
    "frontier9": "buff_frontier9.json",
}
_PLACEHOLDER = re.compile(r"<type-index:\d+>")
_FUNCTION_BOUNDARIES = ("complete ", )


def _norm(value: Any) -> Any:
    return _PLACEHOLDER.sub("<type-index:*>", value) if isinstance(value, str) else value


def check_fields(wrapper: str, reviewed: list[str], installed: list[str]) -> None:
    """Refuse unless the installed own-field list equals the reviewed one."""
    if installed == reviewed:
        return
    if installed[:len(reviewed)] == reviewed:
        raise RouteRefused(f"appended-fields={wrapper}:{installed[len(reviewed):]}:review-required")
    first = next(i for i in range(max(len(installed), len(reviewed)))
                 if i >= len(installed) or i >= len(reviewed) or installed[i] != reviewed[i])
    kind = "inserted" if len(installed) > len(reviewed) else "changed"
    raise RouteRefused(
        f"{kind}-field={wrapper}:member={first}"
        f":reviewed={reviewed[first] if first < len(reviewed) else None}"
        f":installed={installed[first] if first < len(installed) else None}")


def _type_definition(image: Any, name: str) -> int:
    found = [i for i in range(len(image.metadata.types)) if image.type_name(i) == name]
    if len(found) != 1:
        raise RouteRefused(f"type={name}:found={len(found)}")
    return found[0]


def _own_fields(image: Any, definition: int) -> list[str]:
    md = image.metadata
    return [md.string(f.name_index) for f in md.fields_for(md.types[definition])]


def _method_row(image: Any, old: list[Any]) -> list[Any]:
    md = image.metadata
    definition = _type_definition(image, old[1])
    owner = md.types[definition]
    rows = [i for i in range(owner.method_start, owner.method_start + owner.method_count)
            if md.string(md.methods[i].name_index) == old[2]]
    if len(rows) != 1:
        raise RouteRefused(f"method={old[1]}.{old[2]}:found={len(rows)}")
    index = rows[0]
    if len(old) == 4 and isinstance(old[3], int):
        return [index, old[1], old[2], image.method_pointer_va(md.methods[index]) - image.pe.image_base]
    return [index, old[1], old[2], _setter_param(image, md.methods[index])]


def _setter_param(image: Any, method: Any) -> str:
    md = image.metadata
    if method.parameter_count != 1:
        raise RouteRefused("setter-parameter-count")
    parameter = md.parameters[method.parameter_start]
    return md.metadata_type_name(parameter.type_index)


def _function_window(image: Any, extents: dict[int, int], start_rva: int, boundary: str,
                     limit: int = 4096) -> dict[str, Any]:
    """Linear decode from the method entry through its first RET (or first tail JMP
    when the reviewed boundary names one); an undecodable byte refuses."""
    if not boundary.startswith(_FUNCTION_BOUNDARIES):
        raise RouteRefused(f"fragment-window:{boundary}:review-required")
    base = image.pe.image_base
    start = base + start_rva
    if start not in extents:
        raise RouteRefused(f"no-pdata-entry={start_rva:#x}")
    stop = "jmp" if "JMP" in boundary else "ret"
    data = image.pe.bytes_at_va(start, limit)
    for row in image.mapper.decode_x64_subset(data, start, stop_offset=limit):
        text = row["text"]
        if text.startswith("db "):
            raise RouteRefused(f"undecodable={start_rva:#x}+{row['offset']:#x}")
        if text.split()[0] == stop:
            raw = row["bytes"]
            size = len(bytes.fromhex(raw.replace(" ", ""))) if isinstance(raw, str) else len(raw)
            return _window(image, start, start + row["offset"] + size, boundary)
    raise RouteRefused(f"no-{stop}={start_rva:#x}")


def _nested_contexts(image: Any, window: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive every rip-relative ``mov rdx`` method-spec load in a reader window."""
    base, pe = image.pe.image_base, image.pe
    start, end = base + window["startRva"], base + window["endRva"]
    rows = image.mapper.decode_x64_subset(pe.bytes_at_va(start, end - start), start, stop_offset=end - start)
    out = []
    for position, row in enumerate(rows):
        raw = bytes.fromhex(row["bytes"].replace(" ", "")) if isinstance(row["bytes"], str) else bytes(row["bytes"])
        row = dict(row, va=int(row["va"], 16) if isinstance(row["va"], str) else row["va"])
        if len(raw) != 7 or raw[:3] != b"\x48\x8B\x15":
            continue
        cell = row["va"] + 7 + struct.unpack_from("<i", raw, 3)[0]
        usage = pe.bytes_at_va(cell, 8)
        try:
            index = method_spec_usage_index(usage, image.registration["methodSpecsCount"],
                                            source=str(image.gameassembly), offset=cell)
        except ValueError:
            continue
        spec = list(struct.unpack("<iii", pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + index * 12, 12)))
        call = next((r for r in rows[position + 1:] if r["text"].startswith("call 0x")), None)
        instantiation = image.instantiations.resolve(spec[2])
        if len(instantiation.arguments) != 1:
            raise RouteRefused(f"nested-argument-count={row['va'] - base:#x}")
        argument = bytes.fromhex(instantiation.arguments[0].raw_type_record_hex)
        generic = None
        if argument[10] == 0x15:
            carrier_raw = pe.bytes_at_va(struct.unpack_from("<Q", argument)[0], 32)
            base_raw = pe.bytes_at_va(struct.unpack_from("<Q", carrier_raw)[0], 16)
            carrier = generic_type_carrier(argument, carrier_raw, base_raw,
                                           type_pointer=instantiation.arguments[0].type_pointer_va,
                                           type_count=len(image.metadata.types), source=str(image.gameassembly))
            definition = carrier["baseDefinitionIndex"]
            nested = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
            generic = {"carrierRawHex": carrier_raw.hex().upper(), "baseRawHex": base_raw.hex().upper(),
                       "elementInstantiationIndex": nested.index,
                       "elementArguments": [a.raw_type_record_hex for a in nested.arguments]}
        else:
            definition = struct.unpack_from("<Q", argument)[0]
        out.append({
            "instructionRva": row["va"] - base, "instructionHex": raw.hex().upper(),
            "consumerCallRva": (int(call["va"], 16) - base) if call else None,
            "consumerTargetRva": (int(call["text"].split()[1], 16) - base) if call else None,
            "cellVa": cell, "usageRawHex": usage.hex().upper(),
            "methodSpecIndex": index, "methodSpec": spec,
            "argumentRawHex": argument.hex().upper(), "typeDefinition": definition,
            "typeName": image.type_name(definition), "generic": generic, "typeKind": argument[10],
        })
    return out


def regenerate_action(image: Any, action: dict[str, Any], switch: dict[str, Any],
                      catalog: dict[str, dict[str, Any]], extents: dict[int, int]) -> dict[str, Any]:
    base = image.pe.image_base
    wrapper = action["wrapperName"]
    entries = [e for e in switch["entries"] if e.get("wrapperName") == wrapper]
    if len(entries) != 1:
        raise RouteRefused(f"switch-entry={wrapper}:found={len(entries)}")
    entry = entries[0]
    row = catalog.get(wrapper)
    if row is None or row["tag"] != entry["tag"]:
        raise RouteRefused(f"catalog-tag={wrapper}")
    new = copy.deepcopy(action)
    table_va = int(switch["tableVa"], 16) if isinstance(switch["tableVa"], str) else switch["tableVa"]
    target = int(entry["targetVa"], 16) if isinstance(entry["targetVa"], str) else entry["targetVa"]
    route_len = action["routeWindow"]["endRva"] - action["routeWindow"]["startRva"]
    route = image.pe.bytes_at_va(target, route_len)
    new.update(
        unionTag=entry["tag"], switchTableRva=table_va - base, switchEntryCount=switch["entryCount"],
        switchTableSha256=_sha256_upper(image.pe.bytes_at_va(table_va, switch["entryCount"] * 4)),
        switchTargetRva=target - base, registeredTypeIndex=entry["registeredTypeIndex"],
        wrapperTypeDefinition=entry["typeDefinition"],
        routeWindow={"startRva": target - base, "endRva": target - base + route_len,
                     "sha256": _sha256_upper(route)},
    )
    if "usageCellRva" in action:
        cell = entry["usageCellVa"]
        cell = int(cell, 16) if isinstance(cell, str) else cell
        new["usageCellRva"] = cell - base
        new["usageRawHex"] = image.pe.bytes_at_va(cell, 8).hex().upper()
    if "actualTypeName" in action:
        new["actualTypeDefinition"] = _type_definition(image, action["actualTypeName"])
        check_fields(wrapper, action["generatedOwnFields"], _own_fields(image, new["actualTypeDefinition"]))
    if row["memberCount"] != action["serializedMemberCount"]:
        raise RouteRefused(f"member-count={wrapper}:reviewed={action['serializedMemberCount']}"
                           f":installed={row['memberCount']}")
    old_method_rvas = {m[3]: i for i, m in enumerate(action["methods"])}
    new["methods"] = [_method_row(image, m) for m in action["methods"]]
    if "setterMethods" in action:
        new["setterMethods"] = [_method_row(image, m) for m in action["setterMethods"]]
        if [[_norm(x) for x in m[1:]] for m in new["setterMethods"]] != \
                [[_norm(x) for x in m[1:]] for m in action["setterMethods"]]:
            raise RouteRefused(f"setters={wrapper}")
    windows = []
    for window in action["codeWindows"]:
        index = old_method_rvas.get(window["startRva"])
        if index is None:
            raise RouteRefused(f"fragment-window={wrapper}:{window['boundary']}:review-required")
        windows.append(_function_window(image, extents, new["methods"][index][3], window["boundary"]))
    new["codeWindows"] = windows
    if action.get("nestedContextUsage"):
        if any("methodSpecIndex" not in c for c in action["nestedContextUsage"]):
            raise RouteRefused(f"nested-profile-context={wrapper}:review-required")
        # Reviewed contexts are the reference-type formatter lookups; value-type
        # (enum/struct, kind 0x11) loads are unmanaged reads the review excluded.
        derived = [c for w in windows for c in _nested_contexts(image, w) if c["typeKind"] != 0x11]
        if [c["typeName"] for c in derived] != [c["typeName"] for c in action["nestedContextUsage"]]:
            raise RouteRefused(f"nested-contexts={wrapper}:reviewed="
                               f"{[c['typeName'] for c in action['nestedContextUsage']]}"
                               f":installed={[c['typeName'] for c in derived]}")
        keys = list(action["nestedContextUsage"][0])
        new["nestedContextUsage"] = [{k: c[k] for k in keys} for c in derived]
    for extra in ("nestedProfileEvidence",):
        if extra in action:
            raise RouteRefused(f"{extra}={wrapper}:review-required")
    return new


def _read_switch(image: Any) -> dict[str, Any]:
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    return read_union_switch(image, UNION)


def _extents(image: Any) -> dict[int, int]:
    return dict(image.mapper.pdata_function_extents(image.pe))


def regenerate(contract: dict[str, Any], *, opener: Callable[[], tuple[Any, dict[str, str]]] = open_selected_build,
               catalog_doc: dict[str, Any] | None = None, switch_reader: Callable[[Any], dict[str, Any]] = _read_switch,
               extents_reader: Callable[[Any], dict[int, int]] = _extents) -> tuple[dict[str, Any], list[str]]:
    """Return ``(regenerated, refused)``; on any refusal the reviewed contract is returned unchanged."""
    image, inputs = opener()
    if catalog_doc is None:
        catalog_doc = json.loads((CONTRACTS_DIR / "levelscript_union_tags.json").read_bytes())
    ni = catalog_doc.get("nativeInputs", {})
    if (str(ni.get("gameAssemblySha256", "")).upper(), str(ni.get("metadataSha256", "")).upper()) != (
            inputs["GameAssembly.dll"].upper(), inputs["global-metadata.dat"].upper()):
        return contract, ["catalog-inputs:levelscript_union_tags.json is not regenerated for the selected build"]
    catalog = {r["wrapperName"]: r for r in catalog_doc["families"]["AbilityActionData"]}
    switch = switch_reader(image)
    extents = extents_reader(image)
    refused, actions = [], []
    for action in contract["actions"]:
        try:
            actions.append(regenerate_action(image, action, switch, catalog, extents))
        except (RouteRefused, ValueError, KeyError) as error:
            refused.append(f"{action['wrapperName'].split('Gameplay_')[-1]}:{error}")
    if refused:
        return contract, refused
    out = copy.deepcopy(contract)
    out["actions"] = actions
    out["nativeInputs"] = {k: inputs[k] for k in contract["nativeInputs"]}
    return out, []


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regenerate", action="store_true", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--only", choices=sorted(CONTRACT_FILES), action="append")
    args = parser.parse_args(argv)
    image_inputs = open_selected_build()
    status = 0
    for name in args.only or CONTRACT_FILES:
        path = CONTRACTS_DIR / CONTRACT_FILES[name]
        contract = json.loads(path.read_bytes())
        result, refused = regenerate(contract, opener=lambda: image_inputs)
        print(json.dumps({"contract": path.name, "refused": refused,
                          "written": bool(args.write and not refused)}, indent=1))
        if refused:
            status = 1
        elif args.write:
            text = json.dumps(result, indent=2, ensure_ascii=False).replace("\n", "\r\n") + "\r\n"
            path.write_bytes(text.encode("utf-8"))
    return status


if __name__ == "__main__":
    sys.exit(main())
