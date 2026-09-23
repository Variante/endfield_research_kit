"""One opened installed build, shared by every contract validator.

A reviewed native contract proves its rows against the selected
``GameAssembly.dll`` and ``global-metadata.dat``.  Every validator used to
open those files itself: load the two ``tools/endfield-il2cpp`` helpers by
path, locate the code registration, read the module pointer table, and then
re-implement the same method-identity, code-window, dispatcher-route, and
setter-order checks with a different error prefix.  This module owns that
scaffold once.  Each check still fails closed with the caller's label, so a
contract's diagnostics keep naming the contract that failed.

Nothing here selects a build.  Callers gate on their own contract's
``nativeInputs`` through ``scripts.common.check_installed_native_inputs`` and
hand the validated paths in.  The code registration is located, not pinned:
the pinned file hash already fixes it, and a build that yields zero or two
candidates is a failed gate, not a fallback.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Sequence

from scripts.game_data.il2cpp.context import (
    GenericInstantiationTable,
    match_image_modules,
    method_token_pointer,
    type_image_owners,
    unresolved_usage_index,
)
from scripts.game_data.il2cpp.protocol import load_metadata_helper, load_native_mapper
from scripts.repo_paths import REPO_ROOT


NATIVE_MAPPER_PATH = REPO_ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py"
METADATA_HELPER_PATH = REPO_ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py"
# The x64 ``mov r64, [rip+disp32]`` encodings a nested-context usage cell is
# loaded with: REX.W 8B 15 (rdx) and REX.WR 8B 05 (r8).
RIP_RELATIVE_LOAD_PREFIXES = (b"\x48\x8b\x15", b"\x4c\x8b\x05")


def read_reviewed_contract(
    path: Path,
    *,
    schema: str,
    label: str,
    status: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Return ``(contract, digest)`` for a reviewed contract.

    The contract is tracked, so git owns its integrity; this checks only the
    identity a reader depends on.  The uppercase digest is returned as report
    provenance, not compared against a pin.
    """
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise ValueError(f"{label}.contract:unsupported-schema")
    if status is not None and value.get("status") != status:
        raise ValueError(f"{label}.contract:unsupported-status")
    return value, digest


class NativeImage:
    """The selected build's PE image and metadata plus the tables checks need."""

    def __init__(self, gameassembly: Path, metadata_path: Path, *, label: str = "native") -> None:
        self.label = label
        self.gameassembly = Path(gameassembly)
        self.metadata_path = Path(metadata_path)
        mapper = load_native_mapper(NATIVE_MAPPER_PATH)
        catalog = load_metadata_helper(METADATA_HELPER_PATH)
        self.mapper = mapper
        self.pe = mapper.PeImage(self.gameassembly)
        self.metadata = catalog.Metadata(self.metadata_path)
        image_names = {self.metadata.string(row.name_index) for row in self.metadata.images}
        registrations = mapper.find_code_registration_candidates(self.pe, image_names)
        if len(registrations) != 1:
            raise ValueError(f"{label}.native:code-registration={registrations!r}")
        self.code_registration = registrations[0]
        self.metadata_registration = mapper.find_metadata_registration(self.pe, self.code_registration)
        self.registration = mapper.metadata_registration_summary(self.pe, self.metadata_registration)

    # ---- lazily built tables -------------------------------------------

    @cached_property
    def owners(self) -> Any:
        return type_image_owners(self.metadata.buf, len(self.metadata.types), source=str(self.metadata_path))

    @cached_property
    def modules(self) -> dict[str, int]:
        pe, metadata = self.pe, self.metadata
        module_pointers = pe.bytes_at_va(
            pe.u64_at_va(self.code_registration + 0x70), len(metadata.images) * 8
        )
        module_rows = [
            (pe.c_string_at_va(pe.u64_at_va(pointer)), pointer)
            for (pointer,) in struct.iter_unpack("<Q", module_pointers)
        ]
        return match_image_modules(
            [metadata.string(row.name_index) for row in metadata.images],
            module_rows,
            source=str(self.gameassembly),
        )

    @cached_property
    def instantiations(self) -> GenericInstantiationTable:
        return GenericInstantiationTable(
            self.pe.bytes_at_va,
            int(self.registration["genericInsts"], 16),
            self.registration["genericInstsCount"],
            source=str(self.gameassembly),
        )

    # ---- primitive reads -------------------------------------------------

    def window_bytes(self, window: dict[str, Any]) -> bytes:
        return self.pe.bytes_at_va(
            self.pe.image_base + window["startRva"], window["endRva"] - window["startRva"]
        )

    def type_name(self, definition: int) -> str:
        return self.metadata.type_full_name(self.metadata.types[definition])

    # ---- checks shared by contracts -------------------------------------

    def check_windows(self, windows: Sequence[dict[str, Any]], *, gate: str = "code-window", label: str | None = None) -> None:
        """Every window's bytes must hash to its recorded SHA256."""
        label = label or self.label
        for window in windows:
            if hashlib.sha256(self.window_bytes(window)).hexdigest().upper() != window["sha256"].upper():
                raise ValueError(f"{label}.native:{gate}={window['startRva']:#x}")

    def check_instruction_windows(self, rows: Sequence[Sequence[Any]], *, label: str | None = None) -> None:
        """``[rva, hex, role]`` rows must match the image byte for byte."""
        label = label or self.label
        for rva, raw_hex, *_ in rows:
            expected = bytes.fromhex(raw_hex)
            if self.pe.bytes_at_va(self.pe.image_base + rva, len(expected)) != expected:
                raise ValueError(f"{label}.native:instruction-window={rva:#x}")

    def method_pointer_va(self, method: Any) -> int:
        """The registered native pointer for a metadata method."""
        image = self.metadata.string(self.metadata.images[self.owners[method.declaring_type]].name_index)
        module = self.modules[image]
        count = self.pe.u32_at_va(module + 8)
        pointers = self.pe.bytes_at_va(self.pe.u64_at_va(module + 16), count * 8)
        row = method_token_pointer(method.token, pointers, source=str(self.gameassembly), offset=module + 16)
        return row["pointerVa"]

    def validate_method_row(self, row: Sequence[Any], *, label: str | None = None) -> int:
        """Check one ``[index, type, name]`` row, plus its pointer RVA or setter parameter.

        A fourth ``int`` element is the expected method pointer RVA; a fourth
        ``str`` element is the expected single parameter type name.
        """
        label = label or self.label
        method_index, type_name, method_name = row[:3]
        method = self.metadata.methods[method_index]
        if (
            self.type_name(method.declaring_type) != type_name
            or self.metadata.string(method.name_index) != method_name
        ):
            raise ValueError(f"{label}.native:method-identity={method_index}")
        if len(row) > 3 and isinstance(row[3], int):
            if self.method_pointer_va(method) != self.pe.image_base + row[3]:
                raise ValueError(f"{label}.native:method-pointer={method_index}")
        elif len(row) > 3:
            parameters = self.metadata.parameters_for(method)
            if len(parameters) != 1 or self.metadata.metadata_type_name(parameters[0].type_index) != row[3]:
                raise ValueError(f"{label}.native:setter-parameter={method_index}")
        return method_index

    def validate_dispatcher(self, block: dict[str, Any], *, label: str | None = None) -> dict[str, Any]:
        """Prove a union tag's switch route, usage cell, and wrapper type.

        The usage cell is the recorded ``usageCellRva`` when the block carries
        one, otherwise the rip-relative cell the route's first instruction
        loads.  Returns the resolved switch target, type index, and definition.
        """
        label = label or self.label
        pe, metadata = self.pe, self.metadata
        table = pe.bytes_at_va(pe.image_base + block["switchTableRva"], block["switchEntryCount"] * 4)
        if hashlib.sha256(table).hexdigest().upper() != block["switchTableSha256"].upper():
            raise ValueError(f"{label}.native:switch-table-sha256")
        target = struct.unpack_from("<I", table, block["unionTag"] * 4)[0]
        if target != block["switchTargetRva"]:
            raise ValueError(f"{label}.native:switch-target={target:#x}")
        route = block["routeWindow"]
        route_bytes = self.window_bytes(route)
        if hashlib.sha256(route_bytes).hexdigest().upper() != route["sha256"].upper():
            raise ValueError(f"{label}.native:route-window-sha256")
        if "usageCellRva" in block:
            cell = pe.image_base + block["usageCellRva"]
        else:
            cell = pe.image_base + target + 7 + struct.unpack_from("<i", route_bytes, 3)[0]
        usage = pe.bytes_at_va(cell, 8)
        if "usageRawHex" in block and usage.hex().upper() != block["usageRawHex"].upper():
            raise ValueError(f"{label}.native:usage-cell")
        type_index = unresolved_usage_index(
            usage, self.registration["typesCount"], tag=1, source=str(self.gameassembly), offset=cell
        )
        if type_index != block["registeredTypeIndex"]:
            raise ValueError(f"{label}.native:type-index={type_index}")
        type_pointer = pe.u64_at_va(int(self.registration["types"], 16) + type_index * 8)
        definition = struct.unpack_from("<Q", pe.bytes_at_va(type_pointer, 16))[0]
        if definition != block["wrapperTypeDefinition"]:
            raise ValueError(f"{label}.native:type-definition={definition}")
        if self.type_name(definition) != block["wrapperName"]:
            raise ValueError(f"{label}.native:wrapper-name")
        return {"target": target, "typeIndex": type_index, "definition": definition, "usageCell": cell}

    def nested_usage_cell(self, context: dict[str, Any], *, label: str | None = None) -> tuple[int, bytes]:
        """Resolve a nested-context usage cell from its recorded load instruction.

        The instruction is a 7-byte rip-relative load.  When the context records
        ``instructionHex`` the bytes must match exactly; otherwise only the
        encoding prefix is checked.  ``cellVa``/``cellRva`` and ``usageRawHex``
        are compared when present.
        """
        label = label or self.label
        pe = self.pe
        va = pe.image_base + context["instructionRva"]
        if "instructionHex" in context:
            expected = bytes.fromhex(context["instructionHex"])
            instruction = pe.bytes_at_va(va, len(expected))
            if instruction != expected:
                raise ValueError(f"{label}.native:nested-instruction={context['instructionRva']:#x}")
        else:
            instruction = pe.bytes_at_va(va, 7)
        if len(instruction) != 7 or instruction[:3] not in RIP_RELATIVE_LOAD_PREFIXES:
            raise ValueError(f"{label}.native:nested-instruction-shape={context['instructionRva']:#x}")
        cell = va + 7 + struct.unpack_from("<i", instruction, 3)[0]
        if "cellVa" in context and cell != context["cellVa"]:
            raise ValueError(f"{label}.native:nested-cell={context['instructionRva']:#x}")
        if "cellRva" in context and cell - pe.image_base != context["cellRva"]:
            raise ValueError(f"{label}.native:nested-cell={context['instructionRva']:#x}")
        usage = pe.bytes_at_va(cell, 8)
        if "usageRawHex" in context and usage.hex().upper() != context["usageRawHex"].upper():
            raise ValueError(f"{label}.native:nested-usage={context['instructionRva']:#x}")
        return cell, usage

    def setter_methods(self, owner: Any, *, parameter: str | None = None, label: str | None = None) -> list[list[Any]]:
        """The generated ``set_*`` methods of a type, in metadata order.

        ``parameter`` selects the third element: ``None`` for ``[index, name]``,
        ``"typeName"`` for the parameter's metadata type name, ``"typeIndex"``
        for its raw type index.  A setter with any arity but one fails.
        """
        label = label or self.label
        rows: list[list[Any]] = []
        for method_index in range(owner.method_start, owner.method_start + owner.method_count):
            method = self.metadata.methods[method_index]
            name = self.metadata.string(method.name_index)
            if not name.startswith("set_") or "instance" in name:
                continue
            if parameter is None:
                rows.append([method_index, name])
                continue
            if method.parameter_count != 1:
                raise ValueError(f"{label}.native:setter-arity={method_index}")
            parameter_row = self.metadata.parameters[method.parameter_start]
            if parameter == "typeName":
                rows.append([method_index, name, self.metadata.metadata_type_name(parameter_row.type_index)])
            elif parameter == "typeIndex":
                rows.append([method_index, name, parameter_row.type_index])
            else:
                raise ValueError(f"{label}.native:unsupported-setter-parameter={parameter}")
        return rows

    def check_wrapper_inheritance(self, wrapper: dict[str, Any], *, label: str | None = None) -> Any:
        """A generated wrapper must carry its recorded name and direct parent."""
        label = label or self.label
        owner = self.metadata.types[wrapper["typeDefinition"]]
        parent = self.metadata.types[wrapper["parentTypeDefinition"]]
        if (
            self.metadata.type_full_name(owner) != wrapper["typeName"]
            or self.metadata.type_full_name(parent) != wrapper["parentTypeName"]
            or owner.parent_index != parent.byval_type_index
        ):
            raise ValueError(f"{label}.native:wrapper-inheritance")
        return owner


@lru_cache(maxsize=2)
def open_native_image(gameassembly: Path, metadata_path: Path) -> NativeImage:
    """Open the selected build once per process for the given file pair.

    Checks take their own ``label`` so one opened image serves every contract.
    """
    return NativeImage(Path(gameassembly).resolve(), Path(metadata_path).resolve())
