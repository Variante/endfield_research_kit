"""Validate reviewed LevelScript union Deserialize call order on a selected build.

The contract records a bounded native body and each read/setter call pair. A
validated row proves the generated reader consumes the named fields in order;
the shared ActionSerializedMap codec still owns the wire cursor and corpus gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, write_canonical_json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.repo_paths import REPO_ROOT


CONTRACT_PATH = CONTRACTS_DIR / "levelscript_route_deserialize_native.json"
LAYOUT_PATH = REPO_ROOT / "scripts/game_data/codecs/levelscript/action_map_layouts.json"
DEFAULT_REPORT = REPO_ROOT / "reports/game_data/levelscript_route_deserialize_native.json"
SCHEMA = "endfield.levelscript-route-deserialize-native.v1"
UNION_BASES = {
    "ActionBase": "Beyond_Gameplay_Actions_ActionBaseForMemoryPack",
    "GetterBase": "Beyond_Gameplay_Actions_PureGetterForMemoryPack",
    "ActionHeader": "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack",
}


def _relative_call_target(image: NativeImage, rva: int) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8:
        raise ValueError(f"levelscriptRouteDeserialize.native:not-relative-call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _runtime_parameter_name(image: NativeImage, type_index: int) -> str:
    types = int(image.registration["types"], 16)
    type_va = image.pe.u64_at_va(types + type_index * 8)
    return runtime_type_name(image.pe, image.metadata, type_va)


def validate(
    *, contract_path: Path = CONTRACT_PATH, layout_path: Path = LAYOUT_PATH,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_bytes())
    if contract.get("schema") != SCHEMA:
        raise ValueError("levelscriptRouteDeserialize.contract:unsupported-schema")
    native_inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        native_inputs["gameAssembly"]["sha256"],
        native_inputs["metadata"]["sha256"],
    )
    audit: dict[str, Any] = {
        "schema": "endfield.levelscript-route-deserialize-native-audit.v1",
        "status": gate.status,
        "nativeGate": gate.detail,
        "validatedRows": [],
    }
    if gate.status != "validated":
        return audit

    image = NativeImage(gate.gameassembly, gate.metadata, label="levelscriptRouteDeserialize")
    for enum in contract.get("enumUnderlying", []):
        definition = enum["typeDefinition"]
        if image.type_name(definition) != enum["typeName"]:
            raise ValueError(f"levelscriptRouteDeserialize.native:enum-type={definition}")
        fields = image.metadata.fields_for(image.metadata.types[definition])
        value_fields = [field for field in fields if image.metadata.string(field.name_index) == "value__"]
        if len(value_fields) != 1 or _runtime_parameter_name(image, value_fields[0].type_index) != enum["underlyingType"]:
            raise ValueError(f"levelscriptRouteDeserialize.native:enum-underlying={definition}")
    layouts = json.loads(layout_path.read_bytes())
    if layouts.get("schema") != "endfield.action-map-layouts.v3":
        raise ValueError("levelscriptRouteDeserialize.layout:unsupported-schema")
    selected = {(row["family"], row["tag"]): row for row in layouts["layouts"]}
    wrappers = derive_from_image(image) if any("nativeIdentity" in row for row in contract["routes"]) else None
    switches: dict[str, dict[str, Any]] = {}
    for row in contract["routes"]:
        key = row["family"], row["tag"]
        layout = selected.get(key)
        if layout is None or layout["wrapperName"] != row["wrapperName"]:
            raise ValueError(f"levelscriptRouteDeserialize.layout:missing-route={key}")
        order = row["readOrder"]
        if layout["memberCount"] != row["memberCount"] or [field[0] for field in layout["fields"]] != [item["name"] for item in order]:
            raise ValueError(f"levelscriptRouteDeserialize.layout:field-order={key}")
        if "fields" in row and layout["fields"] != row["fields"]:
            raise ValueError(f"levelscriptRouteDeserialize.layout:field-kinds={key}")
        if "nativeIdentity" in row:
            identity = row["nativeIdentity"]
            if row["family"] not in switches:
                switches[row["family"]] = read_union_switch(
                    image, UNION_BASES[row["family"]], wrappers=wrappers,
                )
            switch = switches[row["family"]]
            entry = switch["entries"][row["tag"]]
            expected = (
                identity["dispatcherVa"], identity["switchTableVa"],
                identity["switchTargetVa"], identity["branchBodyVa"],
                identity["usageCellVa"], identity["registeredTypeIndex"],
                identity["typeDefinition"], row["wrapperName"],
            )
            actual = (
                switch["dispatcherVa"], switch["tableVa"],
                entry["targetVa"], entry["bodyVa"],
                entry["usageCellVa"], entry["registeredTypeIndex"],
                entry["typeDefinition"], entry["wrapperName"],
            )
            if tuple(str(value).lower() for value in actual) != tuple(str(value).lower() for value in expected):
                raise ValueError(f"levelscriptRouteDeserialize.native:union-identity={key}")
            if image.pe.bytes_at_va(int(identity["branchBodyVa"], 16), len(identity["branchCodeHex"]) // 2).hex() != identity["branchCodeHex"].lower():
                raise ValueError(f"levelscriptRouteDeserialize.native:branch-code={key}")
            if image.pe.bytes_at_va(int(identity["usageCellVa"], 16), len(identity["usageRawHex"]) // 2).hex() != identity["usageRawHex"].lower():
                raise ValueError(f"levelscriptRouteDeserialize.native:usage-cell={key}")
        start = row["deserializeRva"]
        image.validate_method_row([
            row["deserializeMethodIndex"], row["wrapperName"], "Deserialize", start,
        ])
        body = image.pe.bytes_at_va(image.pe.image_base + start, row["normalBodyLength"])
        if hashlib.sha256(body).hexdigest().upper() != row["normalBodySha256"].upper():
            raise ValueError(f"levelscriptRouteDeserialize.native:body-sha256={key}")
        previous_setter = -1
        for item in order:
            read_call = item["readCallRva"]
            setter_call = item["setterCallRva"]
            if not (start <= read_call < setter_call < start + len(body)) or read_call <= previous_setter:
                raise ValueError(f"levelscriptRouteDeserialize.native:read-order={key}/{item['name']}")
            if _relative_call_target(image, read_call) != item["readTargetRva"]:
                raise ValueError(f"levelscriptRouteDeserialize.native:read-call={key}/{item['name']}")
            setter = image.metadata.methods[item["setterMethodIndex"]]
            if image.metadata.string(setter.name_index) != item["setterName"] or image.method_pointer_va(setter) != image.pe.image_base + item["setterTargetRva"]:
                raise ValueError(f"levelscriptRouteDeserialize.native:setter={key}/{item['name']}")
            if _relative_call_target(image, setter_call) != item["setterTargetRva"]:
                raise ValueError(f"levelscriptRouteDeserialize.native:setter-call={key}/{item['name']}")
            parameters = image.metadata.parameters_for(setter)
            if len(parameters) != 1 or _runtime_parameter_name(image, parameters[0].type_index) != item["declaredType"]:
                raise ValueError(f"levelscriptRouteDeserialize.native:setter-parameter={key}/{item['name']}")
            previous_setter = setter_call
        audit["validatedRows"].append({
            "family": row["family"], "tag": row["tag"],
            "memberCount": row["memberCount"],
            "deserializeRva": start,
        })
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    audit = validate()
    write_canonical_json(args.report, audit)
    print(audit["status"], "routes", len(audit["validatedRows"]), "report", args.report)


if __name__ == "__main__":
    main()
