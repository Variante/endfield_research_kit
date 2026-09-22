"""Derive the current-build LevelScript union layout table from the DummyDll.

`codecs/levelscript/action_map_layouts.json` is the reviewed contract: 277
rows recovered one at a time from the native dispatcher switch, each carrying
its own `nativeIdentity` provenance.  It is exact, and it is small.  The
serialized corpus uses far more unions than that, so `action_map.py` fails
closed on the rest and the family's named-byte coverage stalls.

This module closes the gap mechanically.  Two facts make it possible, and both
are proved against the reviewed contract rather than assumed:

* **Tag.**  A union's compact tag is its case-insensitive ordinal rank among
  the wrapper types of its family, ranked on the wrapped type's full name.
  The wrapper name flattens that name's `.`, `<`, `,` and `>` to `_`, so the
  key restores `.` and a generic's closing `>`: ranking the flattened name
  itself puts `IFixAction1.Data` before `IFixAction.Data` and
  `ClientOnce<bool>` before `ClientOnce<bool, Vector2Int>`, the reverse of
  the generator.  All 277 reviewed rows agree with that rank, and so does
  every entry of every family whose formatter switch was read natively.
* **Layout.**  A wrapper's members are its `set____name__` setters in
  declaration order, with the base chain's setters first, root first.  The
  declared type of each member is that setter's parameter type.  All 277
  reviewed field lists reproduce exactly.

So the derivation is a cross-check, not a guess: `derive()` recomputes every
reviewed row and refuses to return anything if one disagrees.  A build whose
DummyDll no longer reproduces the reviewed table has changed something this
module does not model, and the caller gets nothing instead of a plausible
wrong layout.

What this does *not* establish is the native identity of a derived row.  The
reviewed contract's `evidenceBoundary` is `exact` because each row was read
out of the dispatcher.  A derived row's boundary is `direct`: it is an
observed declaration in the build's own managed image, corroborated on 277
rows, but nothing here reads the dispatcher that assigns the tag.  Keep the
two tiers apart in anything a consumer gates on.

Run as: python -m scripts.game_data.levelscript_union_layouts
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any, Iterable

from scripts.common import check_installed_native_inputs, write_canonical_json
from scripts.game_data.dummydll_metadata import (
    DEFAULT_DUMMYDLL_ROOT,
    CliMetadata,
    DummyDllMetadataError,
    iter_assemblies,
    load,
)
from scripts.repo_paths import REPO_ROOT

SCHEMA = "endfield.levelscript-union-layouts-derived.v1"
EVIDENCE_BOUNDARY = "direct"

REVIEWED_CONTRACT = (
    REPO_ROOT / "scripts/game_data/codecs/levelscript/action_map_layouts.json"
)
GENERATION_MANIFEST = DEFAULT_DUMMYDLL_ROOT / "generation.json"
DEFAULT_REPORT = REPO_ROOT / "reports/game_data/levelscript_union_layouts.json"

WRAPPER_SUFFIX = "ForMemoryPack"
INSTANCE_MEMBER = "instance"

#: family name -> the wrapper base type every member of that family extends.
FAMILY_ROOTS = {
    "ActionBase": "Beyond_Gameplay_Actions_ActionBaseForMemoryPack",
    "GetterBase": "Beyond_Gameplay_Actions_PureGetterForMemoryPack",
    "ActionHeader": "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack",
    "GameCondition": "Beyond_Gameplay_GameConditionForMemoryPack",
}

#: Serialized roots whose declarations the closure also needs. These are not
#: union members, so nothing reaches them from the family walk, yet they are
#: what a whole-file framing decodes.
ROOT_TYPES = (
    "LevelScriptData", "LevelScriptTemplateData",
    "SkillData", "LevelData", "BuffData", "LevelConfig",
    "InteractiveTable", "InteractiveTemplateData",
    "ModelViewStateController.MVSCModelViewStateControllerData",
    # Animation-lane roots: these are what the character reconstruction work
    # reads, so they are seeded even though no union family reaches them.
    "AnimationConfigJson", "CharInteractPerformRuntimeCfg",
    "NpcAtmosphericDataTable", "SpawnerConfigData",
    "ExtendedPrefabGroupSerializeData", "PrefabGroupSerializeData",
    # Config tables, each its own root and named after its file.
    "AetherEnergyLockConfigDataTable", "DialogIdTable", "BambooRaftTaskTable",
    "NavMeshStateContainer", "LunaNavMeshAreaContainer",
    "MatrixShockWaveBeatConfigTable", "TeleportValidationDataTable",
)

#: The reviewed contract spells generic arguments with C# keywords and
#: top-level members with ECMA names.  Reproduce that rather than inventing a
#: third spelling, so a derived row and a reviewed row compare directly.
GENERIC_ARGUMENT_NAMES = {
    "int32": "int", "uint32": "uint", "int64": "long", "uint64": "ulong",
    "int16": "short", "uint16": "ushort", "int8": "sbyte", "uint8": "byte",
}

#: A declared enum is stored as its underlying integer, and the reviewed rows
#: record that width rather than the enum's name. The width is read from each
#: enum's own `value__` field: most are int32, but the reviewed wrappers
#: include byte-backed ones, so defaulting would mis-size them by three bytes.
ENUM_BASE_NAMES = frozenset({"Enum"})

#: A type extending one of these is a struct; anything else is a class, and a
#: class member is always a reference.
VALUE_TYPE_BASE_NAMES = frozenset({"ValueType"})

#: Unity's math types are unmanaged structs that the DummyDll set does not
#: declare, so the reference walk would otherwise default them to
#: reference-bearing and object-frame every struct holding one.
UNITY_VALUE_TYPES = {
    "Vector2": 8, "Vector3": 12, "Vector4": 16, "Quaternion": 16,
    "Vector2Int": 8, "Vector3Int": 12, "Color": 16, "Color32": 4,
}

#: Unity types a member declares by their Unity name but that MemoryPack
#: serializes through a Beyond-side stand-in. The wrapper is the shape on the
#: wire; the Unity type never is, and in `AnimationCurve`'s case cannot be --
#: its only instance field is an unmanaged engine pointer.
UNITY_FORMATTER_ALIASES = {
    "AnimationCurve": "FAnimationCurve",
    "Keyframe": "FKeyframe",
}

#: Types the build gives a *hand-written* `MemoryPackFormatter<T>` rather than
#: a generated `<T>ForMemoryPack` wrapper. Their wire form comes from the
#: formatter, so their field list may not describe it, and every framing bug
#: this lane has hit so far has been one of them.
#:
#: Enumerate them from the managed image rather than guessing: find every type
#: extending `MemoryPackFormatter<T>` whose name does not end
#: `ForMemoryPackFormatter`, and read off `T`. The non-stdlib answers on this
#: build are `AnimationCurve`, `AudioId`, `BezierKnot`, `Gradient`,
#: `RectOffset`, `SendLuaEvent1`, `SendLuaEvent2`, `StringPathHash`, `string`,
#: and the `SerializeFieldDictionary` / `SerializeReferenceDictionary` family.
#:
#: Three are settled. `StringPathHash`'s formatter matches its one int64 field,
#: corroborated by SpawnerConfig and LevelConfig closing every file.
#: `AudioId`'s matches its one int32 field: its `Deserialize` body is a
#: class-init guard, one reader call and one 32-bit store, with no null-marker
#: test, no member-count byte and no second call, and it is the same body shape
#: as `StringPathHash`'s differing only in the store width, so the settled case
#: fixes what the shape means. `AnimationCurve`'s does not match -- see the
#: order override below. The rest are read from their field lists on the
#: strength of nothing, so check this list first when a family stalls.
FORMATTER_BACKED_TYPES = frozenset({
    "AnimationCurve", "AudioId", "BezierKnot", "Gradient", "RectOffset",
    "SendLuaEvent1", "SendLuaEvent2", "StringPathHash",
})

#: Types whose members are readable but whose *serialized order* the wire
#: contradicts, with the order corroborated by corpus closure instead.
#:
#: `AnimationCurve` is the one case. MemoryPack serializes it through
#: `FAnimationCurve`, whose members read `keys, postWrapMode, preWrapMode` in
#: both setter order and real field order. The wire disagrees: a curve body
#: reads 8, 8, 3 before its float data, and 8 is `WrapMode.ClampForever`, so
#: the two wrap modes precede a three-element key array. Taking that order
#: raised whole-file closure on SkillData from 826 to 964 and on BuffData from
#: 2,659 to 2,729 with no family regressing -- the same sequential-closure
#: corroboration the reviewed layout contract records for its own rows.
#:
#: This is weaker evidence than a declaration. Anything added here needs the
#: same corpus measurement, stated, and a type whose order is merely
#: *suspected* belongs nowhere near this table.
#: Where an override's evidence runs out. Corpus closure proves the shapes the
#: corpus actually closes on and nothing else, so the part it never exercised
#: has to fail closed rather than ride along on the part it did.
#:
#: Every `AnimationCurve` in a file that closes has zero keys -- 783 of them
#: across SkillData and BuffData -- and every positive-key curve sits in a file
#: that does not. So the empty shape is established and the populated one is
#: not, which is the same boundary the reviewed layout contract already records
#: for `AnimationCurve` keys.
PROVEN_BOUNDARIES: dict[str, dict[str, Any]] = {}

SERIALIZED_ORDER_OVERRIDES: dict[str, list[list[str]]] = {
    # `MemoryPack.AnimationCurveFormatter` carries its own `SerializeKeyFrame`
    # and `DeserializeKeyFrame`, so a keyframe is not the declared struct: the
    # wire writes seven of its eight fields, dropping Unity's legacy
    # `tangentMode`, for a 28-byte stride with no per-element header.
    #
    # Stride is from corpus closure -- sweeping element size gives a single
    # sharp peak at 28, taking SkillData and BuffData together from 3,695
    # closed files to 5,494, with every other width flat. Field identity is
    # from the values themselves across 16,827 keyframes: slot 4 is small
    # integers in every single one (0, 1, 2 -- a `WeightedMode`), slots 5 and 6
    # carry Unity's default 0.3333 weights, and `time` in slot 0 increases
    # monotonically in 96.8% of multi-key curves.
    "FKeyframe": [
        ["time", "float"], ["value", "float"],
        # Unity writes a stepped tangent as +/-Infinity, so these two are
        # real values a finiteness check must not reject.
        ["inTangent", "floatAllowInfinite"], ["outTangent", "floatAllowInfinite"],
        ["weightedMode", "int32"],
        ["inWeight", "float"], ["outWeight", "float"],
    ],
    "AnimationCurve": [
        ["postWrapMode", "int32"],
        ["preWrapMode", "int32"],
        ["keys", "FKeyframe[]"],
    ],
}

#: Byte width of each unmanaged primitive. Natural alignment equals the width
#: for every one of these, which is what a sequential struct is padded to.
PRIMITIVE_SIZES = {
    "floatAllowInfinite": 4,
    "bool": 1, "int8": 1, "uint8": 1, "sbyte": 1, "byte": 1,
    "char": 2, "int16": 2, "uint16": 2, "short": 2, "ushort": 2,
    "int32": 4, "uint32": 4, "int": 4, "uint": 4, "float": 4, "float32": 4,
    "int64": 8, "uint64": 8, "long": 8, "ulong": 8, "double": 8,
}

#: Names that hold no reference by definition.
UNMANAGED_PRIMITIVES = frozenset({
    "floatAllowInfinite",
    "bool", "char", "float", "double", "int8", "uint8", "int16", "uint16",
    "int32", "uint32", "int64", "uint64", "sbyte", "byte", "short", "ushort",
    "int", "uint", "long", "ulong", "float32", "IntPtr", "UIntPtr",
})


class UnionLayoutError(RuntimeError):
    """The derivation could not be trusted, so it produced nothing."""


def _wrapper_sort_key(name: str, *, generic: bool) -> str:
    """The generator's ordinal key, rebuilt from a flattened wrapper name.

    Every flattened separator reads back as `.`: namespace and nesting dots
    are what they were, and the rare `<`/`,` it also stands for sit below
    every letter and digit either way. A generic's trailing `_` is its `>`,
    which must sort after `,` so a longer argument list ranks first.
    """

    base = name[: -len(WRAPPER_SUFFIX)] if name.endswith(WRAPPER_SUFFIX) else name
    base = base.lower()
    if generic and base.endswith("_"):
        base = base[:-1] + ">"
    return base.replace("_", ".")


class _TypeUniverse:
    """Type facts pooled across a DummyDll set, for cross-assembly resolution.

    A wrapper in `MemoryPack.Beyond.dll` names enums and nested types that are
    declared in other assemblies, so the enum and nesting questions cannot be
    answered from the wrapper's own image alone.
    """

    def __init__(self, root: Path) -> None:
        self.enums: dict[str, str] = {}
        #: real type name -> (isValueType, isSequentialLayout, declared fields)
        self.declared_types: dict[
            str, tuple[bool, bool, list[tuple[str, str]]]
        ] = {}
        for path in iter_assemblies(root):
            try:
                image = load(path)
                self._absorb(image)
            except (DummyDllMetadataError, IndexError, struct.error):
                # One unreadable auxiliary assembly must not decide the run;
                # a name it alone declared simply stays unresolved, which
                # shows up as an unnormalized type rather than a wrong one.
                continue

    def _absorb(self, image: CliMetadata) -> None:
        for entry in image.type_defs():
            base = image.type_def_or_ref_name(entry["extendsCode"])
            name = image.type_def_full_name(entry["row"])
            if base in ENUM_BASE_NAMES:
                underlying = image.enum_underlying_type(entry["row"])
                if underlying:
                    self.enums.setdefault(name, underlying)
                continue
            if name not in self.declared_types:
                # The *real* type's complete field list, not the wrapper's
                # serialized members: a compiler-generated backing field still
                # decides whether the struct holds a reference.
                self.declared_types[name] = (
                    base in VALUE_TYPE_BASE_NAMES,
                    image.type_layout(entry["row"]) == "sequential",
                    image.fields(entry["row"]),
                )

    def contains_references(self, name: str, depth: int = 0) -> bool:
        """Whether a declared type holds a reference anywhere inside it.

        This is the question MemoryPack asks before choosing a framing, and it
        is asked of the real type. `EntityPtr` and `AirWallPtr` declare the
        same three serialized members, but `EntityPtr` also carries a
        generated `ObjectPtr<Entity>` backing field, so only it is framed as an
        object. An unresolvable name is treated as reference-bearing, which is
        the fail-closed direction: it keeps a raw read from consuming bytes
        that were never there.
        """

        if depth > 8:
            return True
        if name in self.enums:
            return False
        if name in UNMANAGED_PRIMITIVES or name in UNITY_VALUE_TYPES:
            return False
        if name.endswith("[]") or "<" in name:
            return True
        declared = self.real_type(name)
        if declared is None:
            return True
        is_value_type, _sequential, fields = declared
        if not is_value_type:
            return True
        return any(
            self.contains_references(kind, depth + 1) for _field, kind in fields
        )

    def real_type(
        self, name: str
    ) -> tuple[bool, bool, list[tuple[str, str]]] | None:
        """The declaring-qualified real type, falling back to a simple name."""

        found = self.declared_types.get(name)
        if found is not None:
            return found
        leaf = name.rsplit(".", 1)[-1]
        matches = [
            key for key in self.declared_types if key.rsplit(".", 1)[-1] == leaf
        ]
        if len(matches) != 1:
            return None
        return self.declared_types[matches[0]]

    def raw_layout(self, name: str, depth: int = 0) -> dict[str, Any] | None:
        """Byte offsets for a struct written as raw memory, or None.

        An unmanaged struct is written as its in-memory image, so the bytes
        follow the *real* field order with natural alignment -- not the
        serialized member order. `AirWallPtr` is the case that makes the
        difference visible: its members serialize as logicId, slotId,
        useSlotId, while its memory is useSlotId, seven bytes of padding,
        logicId, slotId, for twenty-four bytes in all.

        Returns None whenever the layout is not established: a non-sequential
        type, an unresolvable field, or a nesting depth that suggests a cycle.
        Callers must fail closed on that rather than fall back to member order.
        """

        if depth > 6:
            return None
        if "<" in name and name.endswith(">"):
            # The open type declares its payload as `!0`; substitute the
            # instantiation's own arguments and lay the concrete type out.
            base, _, rest = name.partition("<")
            arguments = _split_generic_arguments(rest[:-1])
            declared = self.real_type(base)
            if declared is None:
                return None
            is_value_type, sequential, open_fields = declared
            fields = []
            for field, kind in open_fields:
                if kind.startswith("!"):
                    index = int(kind[1:]) if kind[1:].isdigit() else -1
                    if not 0 <= index < len(arguments):
                        return None
                    kind = arguments[index]
                fields.append((field, kind))
            declared = (is_value_type, sequential, fields)
        else:
            declared = self.real_type(name)
        if declared is None:
            return None
        is_value_type, sequential, fields = declared
        if not is_value_type:
            return None
        # A single-field struct has no ordering to get wrong, so auto layout
        # is as determined as sequential. With two or more, only a declared
        # sequential layout fixes the order.
        if not sequential and len(fields) != 1:
            return None
        offset = 0
        alignment = 1
        placed: list[list[Any]] = []
        for field, kind in fields:
            # Real field types keep enum names; the wire carries the storage
            # width, exactly as the wrapper member list records it.
            kind = self.enums.get(kind, kind)
            sized = self.sizeof(kind, depth + 1)
            if sized is None:
                return None
            size, align = sized
            offset = (offset + align - 1) // align * align
            placed.append([field, kind, offset, size])
            offset += size
            alignment = max(alignment, align)
        size = (offset + alignment - 1) // alignment * alignment
        return {"size": size, "alignment": alignment, "fields": placed}

    def sizeof(self, name: str, depth: int = 0) -> tuple[int, int] | None:
        """``(size, alignment)`` of an unmanaged type, or None if unknown."""

        if depth > 6:
            return None
        if name in self.enums:
            name = self.enums[name]
        fixed = PRIMITIVE_SIZES.get(name)
        if fixed is not None:
            return fixed, fixed
        unity = UNITY_VALUE_TYPES.get(name)
        if unity is not None:
            # Every one of these is a vector of 4-byte components, so its
            # alignment is 4 and its size is already a multiple of it.
            return unity, 4
        nested = self.raw_layout(name, depth + 1)
        if nested is None:
            return None
        return nested["size"], nested["alignment"]

    def qualify(self, name: str) -> str:
        """Names already arrive declaring-type qualified, so pass them through.

        Nesting is resolved on the metadata tables, not by short-name lookup:
        short names collide across a 169-assembly set, and guessing a parent
        from a name would invent a declaration.
        """

        return name

    def normalize(self, declared: str, *, generic_argument: bool = False) -> str:
        """Spell one declared type the way the reviewed contract spells it."""

        if declared.endswith("[]"):
            return self.normalize(declared[:-2], generic_argument=generic_argument) + "[]"
        if "<" in declared and declared.endswith(">"):
            base, _, rest = declared.partition("<")
            inner = [
                self.normalize(part, generic_argument=True)
                for part in _split_generic_arguments(rest[:-1])
            ]
            return f"{self.normalize(base)}<{','.join(inner)}>"
        if declared in self.enums and not generic_argument:
            # A directly serialized enum is its underlying integer on the wire
            # and the reviewed rows record that width. Inside a generic
            # argument the enum name is kept: it is what identifies the
            # instantiation, and the consumer still needs to resolve it.
            declared = self.enums[declared]
        if generic_argument:
            return GENERIC_ARGUMENT_NAMES.get(declared, self.qualify(declared))
        return declared if declared in GENERIC_ARGUMENT_NAMES or declared in (
            "bool", "string", "float", "double", "char", "object", "void",
        ) else self.qualify(declared)


def _split_generic_arguments(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current = ""
    for char in text:
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
            continue
        current += char
    if current:
        parts.append(current)
    return parts


def _member_name(setter: str) -> str:
    return setter[len("set_") :].strip("_")


class _WrapperImage:
    """The MemoryPack wrapper image, indexed by type name."""

    def __init__(self, path: Path) -> None:
        self.image = load(path)
        self.by_name: dict[str, dict[str, Any]] = {}
        for entry in self.image.type_defs():
            self.by_name.setdefault(entry["name"], entry)

    def base_chain(self, name: str) -> list[str]:
        """Base type names from the immediate base outward, cycle-guarded."""

        chain: list[str] = []
        seen = {name}
        current = self.by_name.get(name)
        while current is not None:
            base = self.image.type_def_or_ref_name(current["extendsCode"])
            if not base or base in seen:
                break
            seen.add(base)
            chain.append(base)
            current = self.by_name.get(base)
        return chain

    def members(self, name: str, universe: _TypeUniverse) -> list[list[str]]:
        """Declared members in wire order: base chain first, root first."""

        chain = [n for n in [name, *self.base_chain(name)] if n in self.by_name]
        members: list[list[str]] = []
        seen: set[str] = set()
        for type_name in reversed(chain):
            row = self.by_name[type_name]["row"]
            for method_row, setter in self.image.setters(row):
                member = _member_name(setter)
                if member == INSTANCE_MEMBER or member in seen:
                    continue
                declared = self.image.setter_parameter_type(method_row)
                if declared is None:
                    raise UnionLayoutError(
                        f"{type_name}.{setter} has no parameter to type"
                    )
                seen.add(member)
                members.append([member, universe.normalize(declared)])
        return members

    def resolve_wrapper(self, name: str, context: str | None = None) -> str | None:
        """Find the wrapper type a field's declared type name refers to.

        A wrapper is named `<Namespace_And_Declaring_Types>_<Type>ForMemoryPack`
        with every separator flattened to an underscore, while a field names
        its type as `Declaring.Nested`. Matching the dotted path as an
        underscore-joined suffix keeps two same-leaf types apart --
        `NpcOverrideEnvTalk.EnvTalkStruct` and
        `NpcAtmosphericOverrideEnvTalk.EnvTalkStruct` both exist, and resolving
        either by its leaf alone would silently pick the wrong layout. A name
        that still matches more than one wrapper resolves to none.
        """

        if "<" in name and name.endswith(">"):
            return self._resolve_generic_wrapper(name)
        index = getattr(self, "_wrapper_index", None)
        if index is None:
            index = [
                (name_, name_[: -len(WRAPPER_SUFFIX)])
                for name_ in self.by_name
                if name_.endswith(WRAPPER_SUFFIX)
            ]
            self._wrapper_index = index
        suffix = "_" + name.replace(".", "_")
        matches = {
            wrapper for wrapper, stem in index
            if stem == name.replace(".", "_") or stem.endswith(suffix)
        }
        if len(matches) == 1:
            return next(iter(matches))
        if not matches or context is None:
            return None
        # Two namespaces can contribute the same nested name --
        # `CameraImpulseAction.ImpulseDefinitionData` and
        # `ModelViewStateController.ImpulseDefinitionData` both exist. The
        # referring wrapper decides: prefer the candidate sharing the longest
        # leading path with it, and only when that winner is unique.
        def shared(candidate: str) -> int:
            a, b = candidate.split("_"), context.split("_")
            count = 0
            for left, right in zip(a, b):
                if left != right:
                    break
                count += 1
            return count
        ranked = sorted(matches, key=shared, reverse=True)
        best = shared(ranked[0])
        if best == 0 or (len(ranked) > 1 and shared(ranked[1]) == best):
            return None
        return ranked[0]

    def _resolve_generic_wrapper(self, name: str) -> str | None:
        """Find the wrapper for one generic instantiation, e.g. `Optional<T>`.

        A generic MemoryPack type gets one wrapper per instantiation, named by
        flattening the open type and its arguments into the same underscore
        path: `Optional<UnityEngine.Vector3>` becomes
        `Beyond_Optional_UnityEngine_Vector3_ForMemoryPack`. Matching on that
        flattened tail keeps `Optional<Vector3>` and `Optional<GameplayTag>`
        apart, which a match on the open type alone would not.
        """

        base, _, rest = name.partition("<")
        arguments = _split_generic_arguments(rest[:-1])
        # A declared type name carries no namespace, while the wrapper path
        # does, so the argument may appear as `UnityEngine_Vector3`. Anchor on
        # the open type and the argument's own segments and let whatever
        # namespace sits between them match.
        parts = [re.escape(base.replace(".", "_"))]
        # An array argument flattens its brackets to a trailing underscore,
        # so `Optional<GameplayTag[]>` is `..._Optional_..._GameplayTag__`.
        parts += [
            r"(?:[A-Za-z0-9]+_)*"
            + re.escape(argument.replace("[]", "_").replace(".", "_"))
            for argument in arguments
        ]
        # Exactly one trailing underscore closes the instantiation. Allowing
        # more would make `Optional<string>` also match `Optional<string[]>`,
        # whose argument contributes an underscore of its own.
        pattern = re.compile(r"(?:^|_)" + "_".join(parts) + r"_$")
        matches = {
            wrapper for wrapper in self.by_name
            if wrapper.endswith(WRAPPER_SUFFIX)
            and pattern.search(wrapper[: -len(WRAPPER_SUFFIX)])
        }
        if len(matches) != 1:
            return None
        return next(iter(matches))

    def has_subtypes(self, wrapper: str) -> bool:
        """Whether this wrapper is an abstract base with derived wrappers.

        MemoryPack frames such a type as a union -- a tag, then a member
        count -- so a member declared as the base is not simply its members
        inline. Both halves matter: `BlackboardInt` has subtypes yet is
        concrete, and is written as itself with no tag, while every genuine
        union base in this corpus is abstract.
        """

        entry = self.by_name.get(wrapper)
        if entry is None or not self.image.is_abstract(entry["row"]):
            return False

        index = getattr(self, "_subtype_bases", None)
        if index is None:
            index = set()
            for name in self.by_name:
                chain = self.base_chain(name)
                if chain:
                    index.add(chain[0])
            self._subtype_bases = index
        return wrapper in index

    def family_members(self, root: str) -> list[str]:
        """Every wrapper type whose base chain reaches ``root``."""

        found = []
        for name in self.by_name:
            if not name.endswith(WRAPPER_SUFFIX):
                continue
            if root in self.base_chain(name):
                found.append(name)
        return sorted(
            set(found),
            key=lambda name: _wrapper_sort_key(name, generic=self.wraps_generic(name)),
        )

    def wraps_generic(self, name: str) -> bool:
        """Whether the wrapper's `__instance` setter takes a generic type."""

        row = self.by_name[name]["row"]
        for method_row, setter in self.image.setters(row):
            if _member_name(setter) == INSTANCE_MEMBER:
                declared = self.image.setter_parameter_type(method_row) or ""
                return "<" in declared
        return False


#: Generic heads the codec frames itself. Everything else generic is an
#: ordinary type that happens to be parameterised, and has one wrapper per
#: instantiation, so the whole name has to survive the walk.
CONTAINER_GENERICS = frozenset({
    "List", "Dictionary", "SerializeFieldDictionary", "Nullable",
    "Param", "ParamOutput",
})


def _leaf_names(declared: str, into: set[str]) -> None:
    """Collect every type name a declared type mentions.

    A container's arguments are collected and the container itself dropped.
    Any other generic is kept whole as well as split, because
    `Optional<Vector3>` is a distinct declared type with its own wrapper --
    reducing it to `Optional` would lose the instantiation that names it.
    """

    if declared.endswith("[]"):
        return _leaf_names(declared[:-2], into)
    if "<" in declared and declared.endswith(">"):
        base, _, rest = declared.partition("<")
        if base not in CONTAINER_GENERICS:
            into.add(declared)
        _leaf_names(base, into)
        for argument in _split_generic_arguments(rest[:-1]):
            _leaf_names(argument, into)
        return
    into.add(declared)


def _referenced_declarations(
    families: dict[str, list[dict[str, Any]]],
    wrappers: _WrapperImage,
    universe: _TypeUniverse,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Close the set of struct and enum declarations the layouts refer to.

    A layout that names `Param<AirWallPtr>` is only usable if `AirWallPtr` is
    declared too, and that struct may itself name another. The closure runs to
    a fixed point so a consumer never has to resolve a name this report left
    dangling. Names with no wrapper type -- primitives, the generic heads
    `Param`, `List`, `ObjectPtr` -- are simply absent, which is how a consumer
    tells "not a struct" from "a struct I failed to record".
    """

    pending: set[str] = set(ROOT_TYPES)
    #: name -> a wrapper that referred to it, used only to break ties between
    #: same-named nested types in different namespaces.
    referrer: dict[str, str] = {}
    for rows in families.values():
        for row in rows:
            names: set[str] = set()
            for _member, declared in row["fields"]:
                _leaf_names(declared, names)
            for found in names:
                referrer.setdefault(found, row["wrapperName"].split(".")[-1])
            pending |= names

    structs: dict[str, Any] = {}
    enums: dict[str, str] = {}
    seen: set[str] = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        if name in universe.enums:
            enums[name] = universe.enums[name]
            continue
        if name.startswith("ValueTuple<") and name.endswith(">"):
            # A tuple has no wrapper; its members are Item1..ItemN in order.
            arguments = _split_generic_arguments(name[len("ValueTuple<") : -1])
            fields = [[f"Item{i + 1}", kind] for i, kind in enumerate(arguments)]
            holds = any(universe.contains_references(kind) for kind in arguments)
            raw = None
            if not holds:
                offset = 0
                alignment = 1
                placed = []
                for member, kind in fields:
                    sized = universe.sizeof(kind)
                    if sized is None:
                        placed = None
                        break
                    size, align = sized
                    offset = (offset + align - 1) // align * align
                    placed.append([member, kind, offset, size])
                    offset += size
                    alignment = max(alignment, align)
                if placed is not None:
                    raw = {
                        "size": (offset + alignment - 1) // alignment * alignment,
                        "alignment": alignment,
                        "fields": placed,
                    }
            structs[name] = {
                "wrapperName": None,
                "memberCount": len(fields),
                "fields": fields,
                "containsReferences": holds,
                "isUnionBase": False,
                **({"rawLayout": raw} if raw else {}),
            }
            for _member, kind in fields:
                _leaf_names(kind, pending)
            continue
        override = SERIALIZED_ORDER_OVERRIDES.get(name)
        if override is not None:
            holds_reference = any(
                universe.contains_references(kind) for _member, kind in override
            )
            raw = None
            if not holds_reference:
                offset = 0
                placed = []
                for member, kind in override:
                    size, align = universe.sizeof(kind) or (0, 1)
                    offset = (offset + align - 1) // align * align
                    placed.append([member, kind, offset, size])
                    offset += size
                raw = {"size": offset, "alignment": 4, "fields": placed}
            structs[name] = {
                "wrapperName": f"Beyond.MemoryPack.{wrappers.resolve_wrapper(UNITY_FORMATTER_ALIASES.get(name, name))}",
                "memberCount": len(override),
                "fields": [list(row) for row in override],
                "containsReferences": holds_reference,
                "isUnionBase": False,
                "orderEvidence": "corpus-closure",
                **({"rawLayout": raw} if raw else {}),
                **PROVEN_BOUNDARIES.get(name, {}),
            }
            for _member, kind in override:
                _leaf_names(kind, pending)
            continue
        wrapper = wrappers.resolve_wrapper(
            UNITY_FORMATTER_ALIASES.get(name, name), referrer.get(name)
        )
        if wrapper is None:
            # No MemoryPack wrapper means no generated formatter, so an
            # unmanaged struct here is written by the unmanaged formatter --
            # its real fields, as raw memory. `StringPathHash` is one bare
            # int64. Anything else stays unrecorded and fails closed.
            raw = universe.raw_layout(name)
            if raw is None or universe.contains_references(name):
                continue
            structs[name] = {
                "wrapperName": None,
                "memberCount": len(raw["fields"]),
                "fields": [[member, kind] for member, kind, _o, _s in raw["fields"]],
                "containsReferences": False,
                "isUnionBase": False,
                "rawLayout": raw,
            }
            for member, kind, _offset, _size in raw["fields"]:
                _leaf_names(kind, pending)
            continue
        fields = wrappers.members(wrapper, universe)
        structs[name] = {
            "wrapperName": f"Beyond.MemoryPack.{wrapper}",
            "memberCount": len(fields),
            "fields": fields,
            # How the value is framed on the wire, which the member list alone
            # does not say. See `_TypeUniverse.contains_references`.
            # A generic instantiation's open type declares its payload as a
            # type variable, which no reference walk can resolve. The
            # instantiation's own wrapper members are concrete, so ask them:
            # `Optional<Vector3>` holds no reference and is written raw.
            "containsReferences": (
                any(universe.contains_references(kind) for _member, kind in fields)
                if "<" in name
                else universe.contains_references(name)
            ),
            # A type other wrappers derive from is a MemoryPack union: its
            # value carries a tag and a member count before the members.
            "isUnionBase": wrappers.has_subtypes(wrapper),
        }
        if not structs[name]["containsReferences"]:
            # Raw framing needs the memory image, which the serialized member
            # list does not give. Absent means "not established", and the
            # codec must refuse rather than read members in order.
            raw = universe.raw_layout(name)
            if raw is not None:
                structs[name]["rawLayout"] = raw
        for _member, declared in fields:
            _leaf_names(declared, pending)
    return structs, enums


def _check_declarations(
    contract: dict[str, Any],
    structs: dict[str, Any],
    enums: dict[str, str],
) -> list[dict[str, Any]]:
    """Hold the derived declarations to what the reviewed contract states.

    `primitiveEvidence` records two things the derivation must agree with: the
    structs that carry exactly one string key, and the enums whose underlying
    type is int32. Both were established from the native side, so a
    disagreement means the declaration walk is reading something else.
    """

    evidence = contract.get("primitiveEvidence") or {}
    failures: list[dict[str, Any]] = []
    for name in evidence.get("stringKeyStructs") or {}:
        got = structs.get(name)
        if got is None:
            continue  # not referenced by any derived layout; nothing to check
        fields = got["fields"]
        if len(fields) != 1 or fields[0][1] != "string":
            failures.append({
                "gate": "stringKeyStruct", "name": name,
                "expected": "exactly one string member", "actual": fields,
            })
    for dotted in evidence.get("int32Enums") or []:
        leaf = dotted.rsplit(".", 1)[-1]
        matches = {
            name: underlying for name, underlying in enums.items()
            if name.rsplit(".", 1)[-1] == leaf
        }
        for name, underlying in matches.items():
            if underlying != "int32":
                failures.append({
                    "gate": "int32Enum", "name": name,
                    "expected": "int32", "actual": underlying,
                })
    return failures


def _reviewed_contract() -> dict[str, Any]:
    return json.loads(REVIEWED_CONTRACT.read_bytes().decode("utf-8-sig"))


def _reviewed_rows() -> list[dict[str, Any]]:
    return list(_reviewed_contract().get("layouts") or [])


def _native_gate(
    manifest_path: Path = GENERATION_MANIFEST,
) -> tuple[Any, dict[str, str]]:
    """Authenticate the DummyDll set against the selected installed build."""

    try:
        manifest = json.loads(Path(manifest_path).read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise UnionLayoutError(
            f"DummyDll generation manifest unreadable: {manifest_path}: {error}"
        ) from error
    game = manifest.get("game") or {}
    gameassembly = str(game.get("gameAssemblySha256") or "")
    metadata = str(game.get("metadataSha256") or "")
    if not gameassembly or not metadata:
        raise UnionLayoutError(
            "DummyDll generation manifest does not record both input hashes"
        )
    return check_installed_native_inputs(gameassembly, metadata), {
        "gameAssemblySha256": gameassembly.upper(),
        "metadataSha256": metadata.upper(),
        "generatedAtUtc": str(manifest.get("generatedAtUtc") or ""),
    }


def derive(
    dummydll_root: Path = DEFAULT_DUMMYDLL_ROOT,
    *,
    require_native: bool = True,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Derive every family's layout table, or fail closed.

    The reviewed rows are recomputed first.  A single disagreement raises,
    because a derivation that cannot reproduce what is already proved has no
    standing to state what is not.
    """

    native, manifest = _native_gate(
        manifest_path if manifest_path is not None
        else Path(dummydll_root) / GENERATION_MANIFEST.name
    )
    if require_native and native.status != "validated":
        raise UnionLayoutError(
            "levelscriptUnionLayouts.installed_native_inputs: "
            f"expected=validated actual={native.status} detail={native.detail}"
        )

    wrapper_path = Path(dummydll_root) / "MemoryPack.Beyond.dll"
    if not wrapper_path.is_file():
        raise UnionLayoutError(f"wrapper assembly not found: {wrapper_path}")
    wrappers = _WrapperImage(wrapper_path)
    universe = _TypeUniverse(Path(dummydll_root))

    families: dict[str, Any] = {}
    derived: dict[tuple[str, str], dict[str, Any]] = {}
    for family, root in FAMILY_ROOTS.items():
        if root not in wrappers.by_name:
            raise UnionLayoutError(f"family root type absent: {root}")
        rows = []
        for tag, name in enumerate(wrappers.family_members(root)):
            row = {
                "family": family,
                "tag": tag,
                "memberCount": 0,
                "wrapperName": f"Beyond.MemoryPack.{name}",
                "fields": wrappers.members(name, universe),
            }
            row["memberCount"] = len(row["fields"])
            rows.append(row)
            derived[(family, row["wrapperName"])] = row
        families[family] = rows

    # Closing the declarations discovers union bases, and each new family
    # brings declarations of its own, so the two steps run to a fixed point.
    # Stopping after one pass leaves a member of a discovered family naming a
    # type that was never recorded.
    for _pass in range(8):
        structs, enums = _referenced_declarations(families, wrappers, universe)
        added = False
        for name, declared in sorted(structs.items()):
            if not declared.get("isUnionBase") or name in families:
                continue
            root = wrappers.resolve_wrapper(name)
            if root is None:
                continue
            rows = [{
                "family": name, "tag": tag, "memberCount": len(fields),
                "wrapperName": f"Beyond.MemoryPack.{member}", "fields": fields,
            } for tag, member, fields in (
                (tag, member, wrappers.members(member, universe))
                for tag, member in enumerate(wrappers.family_members(root))
            )]
            if rows:
                families[name] = rows
                added = True
        if not added:
            break
    else:
        raise UnionLayoutError("declaration closure did not settle in eight passes")

    contract = _reviewed_contract()
    # The reviewed contract states two tables: `layouts` for the action/getter
    # /header families and `conditionLayouts` for GameCondition. Both must
    # reproduce, or the derivation has no standing on either.
    reviewed = [
        *(contract.get("layouts") or []),
        *({"family": "GameCondition", **row}
          for row in contract.get("conditionLayouts") or []),
    ]
    disagreements, divergences = _cross_check(reviewed, derived, universe.enums)
    if disagreements:
        raise UnionLayoutError(
            "derived layouts contradict the reviewed contract on "
            f"{len(disagreements)} row(s); first={disagreements[0]}"
        )

    declaration_failures = _check_declarations(contract, structs, enums)
    if declaration_failures:
        raise UnionLayoutError(
            "derived declarations contradict the reviewed primitive evidence on "
            f"{len(declaration_failures)} name(s); first={declaration_failures[0]}"
        )

    return {
        "schema": SCHEMA,
        "evidenceBoundary": EVIDENCE_BOUNDARY,
        "interpretation": (
            "Tag is the case-insensitive ordinal rank of the wrapped type's "
            "full name within the family, read back from the flattened wrapper "
            "name with `.` separators and a generic's closing `>`. Members "
            "are the base chain's setters, root first, then the type's own, in "
            "declaration order, typed by each setter's parameter. Enums are "
            "recorded as their int32 storage."
        ),
        "dummyDll": {"root": str(Path(dummydll_root)), **manifest},
        "installedNativeInputs": {
            "status": native.status,
            "detail": native.detail,
        },
        "reviewedContract": {
            "path": str(REVIEWED_CONTRACT.relative_to(REPO_ROOT)).replace("\\", "/"),
            "rows": len(reviewed),
            "reproduced": len(reviewed),
            "spellingDivergences": divergences,
        },
        "families": families,
        "structs": structs,
        "enums": enums,
    }


def _wire_form(declared: str, enums: dict[str, str]) -> str:
    """Collapse a declared type to what it actually costs on the wire.

    An enum is its int32 storage wherever it appears. The reviewed rows are
    not consistent about this inside a generic argument -- most keep the enum
    name, one records `Param<int>` -- and both spellings describe the same
    bytes. Comparing wire forms keeps that cosmetic split from masquerading as
    a layout disagreement, while `spellingDivergences` still reports it.
    """

    if declared.endswith("[]"):
        return _wire_form(declared[:-2], enums) + "[]"
    if "<" in declared and declared.endswith(">"):
        base, _, rest = declared.partition("<")
        inner = [_wire_form(part, enums) for part in _split_generic_arguments(rest[:-1])]
        return f"{_wire_form(base, enums)}<{','.join(inner)}>"
    if declared in enums:
        return _wire_form(enums[declared], enums)
    return {"int": "int32", "uint": "uint32", "long": "int64",
            "ulong": "uint64", "short": "int16", "ushort": "uint16",
            "sbyte": "int8", "byte": "uint8"}.get(declared, declared)


def _cross_check(
    reviewed: Iterable[dict[str, Any]],
    derived: dict[tuple[str, str], dict[str, Any]],
    enums: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Reviewed rows the derivation contradicts, and ones it only respells."""

    failures: list[dict[str, Any]] = []
    divergences: list[dict[str, Any]] = []
    for row in reviewed:
        key = (str(row.get("family")), str(row.get("wrapperName")))
        got = derived.get(key)
        if got is None:
            failures.append({"row": key, "gate": "present", "actual": None})
            continue
        if got["tag"] != row.get("tag"):
            failures.append({
                "row": key, "gate": "tag",
                "expected": row.get("tag"), "actual": got["tag"],
            })
            continue
        want = [list(field) for field in row.get("fields") or []]
        if got["fields"] == want:
            continue
        wire_want = [[name, _wire_form(kind, enums)] for name, kind in want]
        wire_got = [[name, _wire_form(kind, enums)] for name, kind in got["fields"]]
        first = next(
            (i for i, (a, b) in enumerate(zip(want, got["fields"])) if a != b),
            min(len(want), len(got["fields"])),
        )
        record = {
            "row": key, "memberIndex": first,
            "expected": want[first : first + 1],
            "actual": got["fields"][first : first + 1],
        }
        if wire_want == wire_got:
            divergences.append(record)
        else:
            failures.append({**record, "gate": "fields"})
    return failures, divergences


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dummydll-root", type=Path, default=DEFAULT_DUMMYDLL_ROOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--allow-build-drift",
        action="store_true",
        help="derive even when the DummyDll set is not the selected build",
    )
    args = parser.parse_args(argv)

    try:
        report = derive(
            args.dummydll_root, require_native=not args.allow_build_drift
        )
    except (UnionLayoutError, DummyDllMetadataError) as error:
        print(f"LevelScript union layouts unavailable: {error}", file=sys.stderr)
        return 2

    write_canonical_json(args.report, report)
    for family, rows in report["families"].items():
        closed = sum(1 for row in rows if row["fields"])
        print(f"{family}: {len(rows)} unions, {closed} with declared members")
    print(
        f"{len(report['structs'])} referenced structs, "
        f"{len(report['enums'])} referenced enums"
    )
    print(
        f"reviewed rows reproduced: {report['reviewedContract']['reproduced']}"
        f"/{report['reviewedContract']['rows']}"
    )
    print(f"-> {args.report}")
    return 0


if __name__ == "__main__":  # pragma: no cover - documented entry point
    if not __package__:
        raise SystemExit("run as: python -m scripts.game_data.levelscript_union_layouts")
    raise SystemExit(main())
