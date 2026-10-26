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
from scripts.game_data.il2cpp.native_image import NativeImage


class GenericEntries:
    def __new__(cls, image: Any):
        # Only reuse the parsed index of one opened image, never claim results.
        if type(image) is NativeImage and (cached := getattr(image, '_generic_entries_index', None)) is not None:
            return cached
        return super().__new__(cls)

    def __init__(self, image: Any):
        if getattr(self, '_initialized', False):
            return
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
        self.specs = tuple(method_spec_record(raw[i:i + 12], len(image.metadata.methods),
                                       self.meta["genericInstsCount"], source=self.source, offset=spec_base + i)
                      for i in range(0, len(raw), 12))
        self.table_base = int(self.meta["genericMethodTable"], 16)
        self.table = image.pe.bytes_at_va(self.table_base, self.meta["genericMethodTableCount"] * 16)
        self.pointers = image.pe.bytes_at_va(int(self.code["genericMethodPointers"], 16),
                                            self.code["genericMethodPointersCount"] * 8)
        # Frame every key and the full extent once before indexing any row.
        generic_method_candidates(self.table, self.meta["genericMethodTableCount"], len(self.specs), set(),
            self.code["genericMethodPointersCount"], self.code["invokerPointersCount"],
            source=self.source, offset=self.table_base)
        # Index immutable table bytes, never selected context/proof results.
        by_method, aliases = {}, {}
        for index, (spec, slot, _invoker, _adjustor) in enumerate(struct.iter_unpack("<iiii", self.table)):
            if not 0 <= spec < len(self.specs) or not 0 <= slot < len(self.pointers) // 8:
                raise ValueError(f"generic entry: invalid table key/slot {(spec, slot)!r}")
            method = self.specs[spec][0]
            by_method.setdefault(method, []).append((index, spec))
            pointer = struct.unpack_from("<Q", self.pointers, slot * 8)[0]
            aliases.setdefault(pointer, set()).add(method)
        from types import MappingProxyType
        self._rows_by_method = MappingProxyType({key: tuple(value) for key, value in by_method.items()})
        self._pointer_aliases = MappingProxyType({key: tuple(sorted(value)) for key, value in aliases.items()})

        if type(image) is NativeImage:
            self._initialized = True
            image._generic_entries_index = self

    def arguments(self, index: int) -> tuple[list[str], dict[str, Any]]:
        inst = self.image.instantiations.resolve(index)
        names = [runtime_type_name(self.image.pe, self.image.metadata, arg.type_pointer_va)
                 for arg in inst.arguments]
        return names, inst.as_dict()

    def _matching_registrations(self, method_index: int, class_arguments: list[str], method_arguments: list[str]) -> list[dict[str, Any]]:
        matches = []
        for index, spec in self._rows_by_method.get(method_index, ()):
            # Recheck each selected raw triple, including invoker/adjustor bounds.
            row, = generic_method_candidates(
                self.table[index * 16:(index + 1) * 16], 1, len(self.specs), {spec},
                self.code["genericMethodPointersCount"], self.code["invokerPointersCount"],
                source=self.source, offset=self.table_base + index * 16)
            row["tableIndex"] = index
            _definition, ci, mi = self.specs[row["methodSpecIndex"]]
            cn, cp = self.arguments(ci)
            mn, mp = self.arguments(mi)
            if cn == class_arguments and mn == method_arguments:
                slot = row["indices"][0]
                pointer = struct.unpack_from("<Q", self.pointers, slot * 8)[0]
                matches.append({"pointer": pointer, "methodSpecIndex": row["methodSpecIndex"],
                                "registration": row, "classInstantiation": cp, "methodInstantiation": mp})
        return matches

    def observe(self, method_index: int, class_arguments: list[str], method_arguments: list[str]) -> list[dict[str, Any]]:
        """Observe matching rows, preserving aliases without granting admission.

        Null pointers and multiple rows remain observations. Consumers needing
        a unique method-definition entry must continue to use ``resolve``.
        """
        result = []
        for row in self._matching_registrations(method_index, class_arguments, method_arguments):
            pointer = row['pointer']
            aliases = list(self._pointer_aliases.get(pointer, ())) if pointer else []
            result.append({**row, 'methodDefinitionIndices': aliases,
                'uniqueMethodDefinitionForPointer': bool(pointer) and aliases == [method_index],
                'runtimeSelectionObserved': False,
                'boundary': 'Matching registration rows and physical pointers only; folded aliases, null pointers and duplicate rows remain explicit. No unique body identity, runtime context selection or callee effects follow.'})
        return result

    def resolve(self, method_index: int, class_arguments: list[str], method_arguments: list[str]) -> dict[str, Any]:
        matches = self._matching_registrations(method_index, class_arguments, method_arguments)
        if len(matches) != 1 or not matches[0]["pointer"]:
            raise ValueError(f"generic entry: expected one non-null registered instantiation, matched {len(matches)}")
        result = matches[0]
        aliases = self._pointer_aliases[result["pointer"]]
        if set(aliases) != {method_index}:
            raise ValueError(f"generic entry: folded method definitions {sorted(set(aliases))!r}")
        result["methodDefinitionIndices"] = sorted(set(aliases))
        result["boundary"] = "Selected registration and physical entry only; runtime closed type, MethodInfo selection and instantiated fields unproved."
        return result
