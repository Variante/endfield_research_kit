"""Authenticate the current-build BuffData residual action route contracts.

Five reviewed contracts prove, frontier by frontier, which BuffData union
tags route to a generated MemoryPack wrapper in the selected build.  They
share one shape -- a switch-table route, a usage cell, a wrapper type, the
methods and setters the route calls, and hashed code windows -- and differ
only in which optional blocks a frontier proved: the base-only residual rows
carry no setter or nested-context evidence, the later frontiers add the
actual type's field list and nested generic contexts.  One validator walks
the union of those blocks and checks each block only where the contract
records it, so a frontier never inherits a claim it did not make.

Every loader fails closed: a missing or different installed build returns no
rows and an audit naming the gate that stopped it.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp_context import generic_type_carrier, method_spec_usage_index
from scripts.game_data.il2cpp_native_image import NativeImage, read_pinned_contract


CONTRACT_STATUS = "exact-current-build"


@dataclass(frozen=True)
class Frontier:
    name: str
    file: str
    sha256: str
    schema: str

    @property
    def path(self) -> Path:
        return CONTRACTS_DIR / self.file

    @property
    def label(self) -> str:
        return f"buffFrontier.{self.name}"


FRONTIERS: dict[str, Frontier] = {
    frontier.name: frontier
    for frontier in (
        Frontier(
            "residual",
            "buff_residual_frontier.json",
            "debabbbd6ea0465e4cf5bacffd489f0ca9b6c0838a7aa59088197c2dda6038f3",
            "endfield.buff-residual-frontier-native-contract.v1",
        ),
        Frontier(
            "frontier6",
            "buff_frontier6.json",
            "fabf42c86746d668e099ed640aa9c1dd44570f6dc591425710d66ca7a36133c4",
            "endfield.buff-frontier6-native-contract.v1",
        ),
        Frontier(
            "frontier7",
            "buff_frontier7.json",
            "100709c977caeb671d86a304f9a786b1df506edeed51d6506be09abf1136d0b3",
            "endfield.buff-frontier7-native-contract.v1",
        ),
        Frontier(
            "frontier8",
            "buff_frontier8.json",
            "196820a6fd2bcd811ccabacc5e17565289193e05c19e906ea2e29f0d0e91ddab",
            "endfield.buff-frontier8-native-contract.v1",
        ),
        Frontier(
            "frontier9",
            "buff_frontier9.json",
            "52b0a641d077383f54eb692d18178f2dbe97cd22ce4de9148e596c1011b79810",
            "endfield.buff-frontier9-native-contract.v1",
        ),
    )
}


def frontier(name: str) -> Frontier:
    try:
        return FRONTIERS[name]
    except KeyError:
        raise ValueError(f"unknown buff frontier {name!r}; known: {sorted(FRONTIERS)}") from None


def contract_path(name: str) -> Path:
    return frontier(name).path


def _read_contract(name: str, contract_path: Path | None = None) -> tuple[dict[str, Any], str]:
    spec = frontier(name)
    return read_pinned_contract(
        contract_path or spec.path,
        sha256=spec.sha256,
        schema=spec.schema,
        status=CONTRACT_STATUS,
        label=spec.label,
    )


@lru_cache(maxsize=len(FRONTIERS))
def reviewed_contract(name: str) -> dict[str, Any]:
    """Return the byte-pinned contract without selecting installed inputs."""
    return _read_contract(name)[0]


def _validate_nested_context(image: NativeImage, context: dict[str, Any], *, label: str) -> None:
    cell, usage = image.nested_usage_cell(context, label=label)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=str(image.gameassembly), offset=cell
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{label}.native:nested-method-spec-index")
    spec = struct.unpack(
        "<iii", image.pe.bytes_at_va(int(image.registration["methodSpecs"], 16) + index * 12, 12)
    )
    if list(spec) != context["methodSpec"]:
        raise ValueError(f"{label}.native:nested-method-spec")
    instantiation = image.instantiations.resolve(spec[2])
    if len(instantiation.arguments) != 1:
        raise ValueError(f"{label}.native:nested-argument-count")
    argument = bytes.fromhex(instantiation.arguments[0].raw_type_record_hex)
    if argument.hex().upper() != context["argumentRawHex"]:
        raise ValueError(f"{label}.native:nested-argument")
    if argument[10] == 0x15:
        carrier_pointer = struct.unpack_from("<Q", argument)[0]
        carrier_raw = image.pe.bytes_at_va(carrier_pointer, 32)
        base_pointer = struct.unpack_from("<Q", carrier_raw)[0]
        base_raw = image.pe.bytes_at_va(base_pointer, 16)
        carrier = generic_type_carrier(
            argument,
            carrier_raw,
            base_raw,
            type_pointer=instantiation.arguments[0].type_pointer_va,
            type_count=len(image.metadata.types),
            source=str(image.gameassembly),
        )
        definition = carrier["baseDefinitionIndex"]
        nested = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
        generic = context["generic"]
        if (
            generic is None
            or carrier_raw.hex().upper() != generic["carrierRawHex"]
            or base_raw.hex().upper() != generic["baseRawHex"]
            or nested.index != generic["elementInstantiationIndex"]
            or [a.raw_type_record_hex for a in nested.arguments] != generic["elementArguments"]
        ):
            raise ValueError(f"{label}.native:nested-generic-carrier")
    else:
        definition = struct.unpack_from("<Q", argument)[0]
        if context["generic"] is not None:
            raise ValueError(f"{label}.native:nested-unexpected-generic")
    if (
        definition != context["typeDefinition"]
        or image.type_name(definition) != context["typeName"]
        or argument[10] != context["typeKind"]
    ):
        raise ValueError(f"{label}.native:nested-type-identity")


def _validate_exact(contract: dict[str, Any], gameassembly: Path, metadata_path: Path) -> list[int]:
    """Prove every action route of one contract; return its union tags in order."""
    label = f"buffFrontier.{contract['schema']}"
    image = NativeImage(gameassembly, metadata_path, label=label)
    validated: list[int] = []
    for action in contract["actions"]:
        image.validate_dispatcher(action, label=label)
        if "actualTypeDefinition" in action:
            actual = image.metadata.types[action["actualTypeDefinition"]]
            if image.metadata.type_full_name(actual) != action["actualTypeName"]:
                raise ValueError(f"{label}.native:actual-type-name")
            field_names = [
                image.metadata.string(field.name_index) for field in image.metadata.fields_for(actual)
            ]
            if field_names != action["generatedOwnFields"]:
                raise ValueError(f"{label}.native:actual-fields={field_names!r}")
        for row in action["methods"]:
            image.validate_method_row(row, label=label)
        for row in action.get("setterMethods", []):
            image.validate_method_row(row, label=label)
        for context in action.get("nestedContextUsage", []):
            _validate_nested_context(image, context, label=label)
        image.check_windows(action["codeWindows"], label=label)
        validated.append(action["unionTag"])
    return validated


@lru_cache(maxsize=2 * len(FRONTIERS))
def load_rows(
    name: str, *, game_root: Path | None = None, contract_path: Path | None = None
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Return one frontier's authenticated union rows, or no rows with a fail-closed audit."""
    failures: list[dict[str, Any]] = []
    audit: dict[str, Any] = {
        "frontier": name,
        "status": "validation_failed",
        "validationFailures": failures,
    }
    try:
        contract, digest = _read_contract(name, contract_path)
        inputs = contract["nativeInputs"]
        selected = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            inputs["GameAssembly.dll"],
            inputs["global-metadata.dat"],
            gameassembly=selected.parent / "GameAssembly.dll" if selected else None,
            metadata=selected / "il2cpp_data/Metadata/global-metadata.dat" if selected else None,
        )
        audit.update(
            nativeGate={"status": gate.status, "detail": gate.detail},
            contractSha256=digest,
            inputSetSha256=contract["inputSetSha256"],
        )
        if gate.status != "validated":
            failures.append({
                "gate": "installed_native_inputs",
                "expected": "validated",
                "actual": gate.status,
                "detail": gate.detail,
            })
            audit["status"] = gate.status
            return {}, audit
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        unity_digest = hashlib.sha256(unity.read_bytes()).hexdigest().upper()
        if unity_digest != inputs["UnityPlayer.dll"]:
            failures.append({
                "gate": "UnityPlayer.dll_sha256",
                "expected": inputs["UnityPlayer.dll"],
                "actual": unity_digest,
            })
            return {}, audit
        validated = _validate_exact(contract, gate.gameassembly, gate.metadata)
        rows = {int(row["unionTag"]): row for row in contract["actions"]}
        if list(rows) != validated:
            raise ValueError("validated-row-set")
        audit.update(
            status="validated",
            evidenceBoundary=contract["evidenceBoundary"],
            validatedRows=len(rows),
        )
        return rows, audit
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        failures.append({"gate": "contract_validation", "detail": str(error)})
        return {}, audit
