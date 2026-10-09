"""Fail-closed registration joins for named generic entry observations.

The caller authenticates the selected NativeImage. A registered instantiation
and a unique physical entry do not identify the runtime receiver's closed type,
its MethodInfo, or any instantiated field layout.
"""
from __future__ import annotations

import struct
from typing import Any

from .context import generic_method_candidates, method_spec_record
from .protocol import runtime_type_name


class GenericEntries:
    def __init__(self, image: Any):
        self.image = image
        self.source = str(image.gameassembly)
        self.meta = image.registration
        self.code = image.mapper.code_registration_summary(image.pe, image.code_registration)
        for owner, names in ((self.meta, ("methodSpecsCount", "genericInstsCount", "genericMethodTableCount")),
                             (self.code, ("genericMethodPointersCount", "invokerPointersCount"))):
            for name in names:
                if type(owner[name]) is not int or not 0 <= owner[name] <= 1_000_000:
                    raise ValueError(f"generic entry: unbounded {name}")
        spec_base = int(self.meta["methodSpecs"], 16)
        raw = image.pe.bytes_at_va(spec_base, self.meta["methodSpecsCount"] * 12)
        self.specs = [method_spec_record(raw[i:i + 12], len(image.metadata.methods),
                                       self.meta["genericInstsCount"], source=self.source, offset=spec_base + i)
                      for i in range(0, len(raw), 12)]
        self.table_base = int(self.meta["genericMethodTable"], 16)
        self.table = image.pe.bytes_at_va(self.table_base, self.meta["genericMethodTableCount"] * 16)
        self.pointers = image.pe.bytes_at_va(int(self.code["genericMethodPointers"], 16),
                                            self.code["genericMethodPointersCount"] * 8)
        # Validate every key/slot before selecting or checking folded aliases.
        for spec, slot, _invoker, _adjustor in struct.iter_unpack("<iiii", self.table):
            if not 0 <= spec < len(self.specs) or not 0 <= slot < len(self.pointers) // 8:
                raise ValueError(f"generic entry: invalid table key/slot {(spec, slot)!r}")

    def arguments(self, index: int) -> tuple[list[str], dict[str, Any]]:
        inst = self.image.instantiations.resolve(index)
        names = [runtime_type_name(self.image.pe, self.image.metadata, arg.type_pointer_va)
                 for arg in inst.arguments]
        return names, inst.as_dict()

    def resolve(self, method_index: int, class_arguments: list[str], method_arguments: list[str]) -> dict[str, Any]:
        selected = {i for i, row in enumerate(self.specs) if row[0] == method_index}
        rows = generic_method_candidates(
            self.table, self.meta["genericMethodTableCount"], len(self.specs), selected,
            self.code["genericMethodPointersCount"], self.code["invokerPointersCount"],
            source=self.source, offset=self.table_base)
        matches = []
        for row in rows:
            _definition, ci, mi = self.specs[row["methodSpecIndex"]]
            cn, cp = self.arguments(ci)
            mn, mp = self.arguments(mi)
            if cn == class_arguments and mn == method_arguments:
                slot = row["indices"][0]
                pointer = struct.unpack_from("<Q", self.pointers, slot * 8)[0]
                matches.append({"pointer": pointer, "methodSpecIndex": row["methodSpecIndex"],
                                "registration": row, "classInstantiation": cp, "methodInstantiation": mp})
        if len(matches) != 1 or not matches[0]["pointer"]:
            raise ValueError(f"generic entry: expected one non-null registered instantiation, matched {len(matches)}")
        result = matches[0]
        aliases = [self.specs[spec][0] for spec, slot, _invoker, _adjustor
                   in struct.iter_unpack("<iiii", self.table)
                   if struct.unpack_from("<Q", self.pointers, slot * 8)[0] == result["pointer"]]
        if set(aliases) != {method_index}:
            raise ValueError(f"generic entry: folded method definitions {sorted(set(aliases))!r}")
        result["methodDefinitionIndices"] = sorted(set(aliases))
        result["boundary"] = "Selected registration and physical entry only; runtime closed type, MethodInfo selection and instantiated fields unproved."
        return result
