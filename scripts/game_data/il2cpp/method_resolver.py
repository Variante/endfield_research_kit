"""Resolve managed method identities to the selected build's native bodies.

Every native claim in this repository is written
down as a *name* plus a per-build address: a type, a method, a method pointer
VA, a file offset, and a body hash. Only the name survives a client update.
This module owns the one direction that can be replayed after an update:
managed name -> current installed build.

It deliberately pins nothing. ``Il2CppCodeRegistration`` is re-derived from the
selected ``GameAssembly.dll`` against the complete image-name set of the
selected ``global-metadata.dat``, so the resolver runs unchanged on a future
build instead of failing the way a recorded registration address does.

Two resolution routes exist because two kinds of managed name behave
differently across builds:

``exact``
    An authored method name (``ClothManager.OnEarlyClothUpdate``) is stable.
    Resolve it by type plus method name.

``lambda``
    A C# compiler-generated closure body is named
    ``<Owner>b__<ordinal>_<index>``, where ``ordinal`` is the declaring
    method's position inside its type. Adding a method anywhere above the
    owner renumbers every lambda under it without any source change, so an
    exact-name lookup of a recorded lambda silently reports "missing" on the
    next build. Resolve those by owner plus lambda index instead, and let the
    module report the ordinal it actually found.

A resolved body extent is the gap to the next distinct method pointer in the
image. That is an exact bound on the region the body occupies and an upper
bound on its instruction bytes, because trailing alignment padding is included;
it is not a proven function length. Callers that need a proven length must
disassemble to a return.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.protocol import load_metadata_helper, load_native_mapper
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.il2cpp-method-resolution.v1"

METADATA_HELPER = (
    REPO_ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
)
NATIVE_MAPPER = (
    REPO_ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
)

# ``<Owner>b__<ordinal>_<index>``: the ordinal is the declaring method's slot
# inside its type and is not build-stable; the index is the lambda's position
# inside that method and is.
LAMBDA_NAME = re.compile(r"^<(?P<owner>[^>]+)>b__(?P<ordinal>\d+)_(?P<index>\d+)$")

# ``<Job>Kernels+<Kernel>_<token>$BurstDirectCall``: Burst names each generated
# wrapper after the wrapped job's metadata token, which renumbers on any client
# update. The name is stable once that token is wildcarded.
BURST_DIRECT_CALL_TOKEN = re.compile(r"_[0-9A-Fa-f]{6,}\$BurstDirectCall")

# A recorded method name may carry a display decoration IL2CPP metadata does
# not store: a parameter list (``Execute(int)``) or generic arguments
# (``SetCustomPerDrawData<T>``). Both are stripped before a second lookup.
METHOD_DECORATION = re.compile(r"\s*(?:<[^<>]*>)?\s*(?:\([^()]*\))?\s*\Z")
RECORDED_PARAMETERS = re.compile(r"\(([^()]*)\)\s*\Z")

# C# keyword spellings of the framework types a recorded display signature is
# most likely to use. Matching is by suffix otherwise, so a recorded
# ``Vector3`` still matches ``UnityEngine.Vector3``.
PRIMITIVE_TYPE_ALIASES = {
    "bool": "System.Boolean",
    "byte": "System.Byte",
    "sbyte": "System.SByte",
    "char": "System.Char",
    "short": "System.Int16",
    "ushort": "System.UInt16",
    "int": "System.Int32",
    "uint": "System.UInt32",
    "long": "System.Int64",
    "ulong": "System.UInt64",
    "float": "System.Single",
    "double": "System.Double",
    "decimal": "System.Decimal",
    "string": "System.String",
    "object": "System.Object",
    "void": "System.Void",
}


def undecorated_method_name(method_name: str) -> str:
    """Strip a recorded display signature or generic suffix from a name."""

    if method_name.startswith("<"):
        # Compiler-generated names begin with '<' and are handled by the lambda
        # route; stripping them here would destroy the owner.
        return method_name
    return METHOD_DECORATION.sub("", method_name, count=1) or method_name


def recorded_parameter_types(method_name: str) -> list[str] | None:
    """Return the parameter type names a recorded display signature carries.

    ``None`` means the name carried no parameter list at all, which is
    different from ``[]`` for a recorded no-argument overload.
    """

    if method_name.startswith("<"):
        return None
    found = RECORDED_PARAMETERS.search(method_name)
    if found is None:
        return None
    body = found.group(1).strip()
    if not body:
        return []
    return [part.strip() for part in body.split(",") if part.strip()]


def parameter_type_matches(recorded: str, declared: str) -> bool:
    """Compare one recorded parameter type against the metadata type name."""

    recorded = recorded.strip()
    # A recorded signature usually omits the parameter name; keep the last
    # token when it does not (``int index``).
    if " " in recorded:
        recorded = recorded.rsplit(" ", 1)[0].strip()
    expanded = PRIMITIVE_TYPE_ALIASES.get(recorded, recorded)
    if expanded == declared:
        return True
    return declared.endswith("." + expanded.rsplit(".", 1)[-1]) and (
        expanded.rsplit(".", 1)[-1] == declared.rsplit(".", 1)[-1]
    )


class ResolverError(RuntimeError):
    """The resolver could not be opened against the selected build."""


@dataclass(frozen=True)
class MethodSpec:
    """One managed method to look for, plus where the request came from."""

    type_name: str
    method_name: str
    origin: str = ""

    @property
    def lambda_parts(self) -> tuple[str, int, int] | None:
        match = LAMBDA_NAME.match(self.method_name)
        if match is None:
            return None
        return (
            match.group("owner"),
            int(match.group("ordinal")),
            int(match.group("index")),
        )


@dataclass
class Resolver:
    """Managed-name lookup against one selected installed build."""

    metadata: Any
    pe: Any
    code_registration_va: int
    module_method_starts: dict[str, int] = field(default_factory=dict)
    module_pointers: dict[str, int] = field(default_factory=dict)
    module_pointer_counts: dict[str, int] = field(default_factory=dict)
    _type_index: dict[str, int] = field(default_factory=dict)
    _method_image: dict[int, str] = field(default_factory=dict)
    _sorted_pointers: list[int] = field(default_factory=list)

    # -- lookup -----------------------------------------------------------

    def type_index(self, type_full_name: str) -> int | None:
        return self._type_index.get(type_full_name)

    def method_names(self, type_full_name: str) -> list[tuple[int, str]]:
        """Every (metadata method index, name) declared by one type."""

        index = self.type_index(type_full_name)
        if index is None:
            return []
        type_def = self.metadata.types[index]
        if type_def.method_count <= 0 or type_def.method_start < 0:
            return []
        return [
            (position, self.metadata.string(self.metadata.methods[position].name_index))
            for position in range(
                type_def.method_start, type_def.method_start + type_def.method_count
            )
        ]

    def resolve(self, spec: MethodSpec) -> dict[str, Any]:
        """Resolve one spec, reporting how the match was reached."""

        row: dict[str, Any] = {
            "requestedType": spec.type_name,
            "requestedMethod": spec.method_name,
        }
        if spec.origin:
            row["origin"] = spec.origin

        type_name = spec.type_name
        type_drift: dict[str, Any] = {}
        if self.type_index(type_name) is None:
            burst = self._resolve_burst_type(type_name)
            if burst is None:
                row["status"] = "type_missing"
                if BURST_DIRECT_CALL_TOKEN.search(type_name):
                    # The wildcard route was tried and did not select a unique
                    # survivor; say so rather than claiming the route resolved.
                    row["typeRouteAttempted"] = "burstDirectCall"
                return row
            type_name = burst
            type_drift = {
                "typeRoute": "burstDirectCall",
                "resolvedType": burst,
            }
            row.update(type_drift)

        declared = self.method_names(type_name)
        exact = [index for index, name in declared if name == spec.method_name]
        if exact:
            row["status"] = "renamed" if type_drift else "exact"
            row["route"] = "name"
            row["matches"] = [self.describe(index) for index in exact]
            return row

        parts = spec.lambda_parts
        if parts is None:
            bare = undecorated_method_name(spec.method_name)
            if bare != spec.method_name:
                overloads = [index for index, name in declared if name == bare]
                if len(overloads) > 1:
                    narrowed = self._narrow_by_parameters(
                        overloads, recorded_parameter_types(spec.method_name)
                    )
                    if narrowed:
                        row["parameterMatch"] = "recorded display signature"
                        overloads = narrowed
                if overloads:
                    # The recorded name carries a display signature or generic
                    # decoration that IL2CPP metadata does not store. One match
                    # is the method; several mean the decoration was the only
                    # thing separating overloads, and this module does not
                    # compare parameter types.
                    row["route"] = "undecoratedName"
                    row["resolvedMethod"] = bare
                    row["status"] = (
                        "ambiguous_overload"
                        if len(overloads) > 1
                        else ("renamed" if type_drift else "exact")
                    )
                    row["matches"] = [self.describe(index) for index in overloads]
                    return row
            row["status"] = "method_missing"
            row["declaredMethodCount"] = len(declared)
            return row

        owner, recorded_ordinal, lambda_index = parts
        renamed = [
            (index, name)
            for index, name in declared
            if (match := LAMBDA_NAME.match(name)) is not None
            and match.group("owner") == owner
            and int(match.group("index")) == lambda_index
        ]
        if not renamed:
            row["status"] = "method_missing"
            row["lambdaOwner"] = owner
            row["lambdaIndex"] = lambda_index
            row["declaredMethodCount"] = len(declared)
            return row
        if len(renamed) > 1:
            # Two ordinals claiming one owner/index pair means the owner name is
            # ambiguous inside this type; do not guess which body was recorded.
            row["status"] = "lambda_ambiguous"
            row["lambdaOwner"] = owner
            row["lambdaIndex"] = lambda_index
            row["candidates"] = [name for _index, name in renamed]
            return row

        index, name = renamed[0]
        found_ordinal = int(LAMBDA_NAME.match(name).group("ordinal"))
        row["status"] = (
            "exact"
            if found_ordinal == recorded_ordinal and not type_drift
            else "renamed"
        )
        row["route"] = "lambda"
        row["lambdaOwner"] = owner
        row["lambdaIndex"] = lambda_index
        row["recordedOwnerOrdinal"] = recorded_ordinal
        row["installedOwnerOrdinal"] = found_ordinal
        row["resolvedMethod"] = name
        row["matches"] = [self.describe(index)]
        return row

    def resolve_all(self, specs: Iterable[MethodSpec]) -> list[dict[str, Any]]:
        return [self.resolve(spec) for spec in specs]

    def _narrow_by_parameters(
        self, candidates: list[int], recorded: list[str] | None
    ) -> list[int]:
        """Keep the overloads whose parameters match a recorded signature.

        Returns the narrowed list only when it selects exactly one method, so
        a partial or unrecognised type spelling leaves the ambiguity visible
        instead of picking an overload the recorded name did not establish.
        """

        if recorded is None:
            return []
        narrowed: list[int] = []
        for index in candidates:
            method = self.metadata.methods[index]
            if method.parameter_count != len(recorded):
                continue
            declared = [
                self.metadata.metadata_type_name(param.type_index)
                for param in self.metadata.parameters_for(method)
            ]
            if all(
                parameter_type_matches(want, have)
                for want, have in zip(recorded, declared)
            ):
                narrowed.append(index)
        return narrowed if len(narrowed) == 1 else []

    def _resolve_burst_type(self, type_name: str) -> str | None:
        """Re-find a Burst direct-call wrapper whose embedded token renumbered.

        Burst names each generated wrapper after the metadata token of the job
        it wraps. A client update renumbers those tokens, so the recorded type
        name stops existing even though nothing about the job changed. Match on
        the name with the token wildcarded, and accept only a unique hit.
        """

        found = BURST_DIRECT_CALL_TOKEN.search(type_name)
        if found is None:
            return None
        pattern = re.compile(
            re.escape(type_name[: found.start()])
            + r"_[0-9A-Fa-f]+\$BurstDirectCall"
            + re.escape(type_name[found.end() :])
            + r"\Z"
        )
        matches = [name for name in self._type_index if pattern.match(name)]
        return matches[0] if len(matches) == 1 else None

    # -- native body ------------------------------------------------------

    def describe(self, method_index: int) -> dict[str, Any]:
        """Join one metadata method index to its native body in this build."""

        method = self.metadata.methods[method_index]
        row: dict[str, Any] = {
            "methodIndex": method_index,
            "method": self.metadata.string(method.name_index),
            "token": f"0x{method.token:08x}",
            "declaringType": self.metadata.type_full_name(
                self.metadata.types[method.declaring_type]
            ),
        }
        image = self._method_image.get(method_index)
        if image is None:
            row["bodyStatus"] = "image_unmapped"
            return row
        row["image"] = image
        slot = method_index - self.module_method_starts[image]
        if not 0 <= slot < self.module_pointer_counts[image]:
            row["bodyStatus"] = "slot_out_of_range"
            return row
        pointer = self.pe.u64_at_va(self.module_pointers[image] + slot * 8)
        row["methodSlot"] = slot
        if not pointer:
            # A null slot is a real IL2CPP state (shared generic, stripped
            # body); it is not a resolver failure and must not be hidden.
            row["bodyStatus"] = "no_native_body"
            return row
        row["methodPointerVa"] = f"0x{pointer:x}"
        file_offset, section, rva = self.pe.file_offset_for_va(pointer)
        if file_offset is None:
            row["bodyStatus"] = "unbacked_va"
            row["rva"] = f"0x{rva:x}"
            return row
        position = bisect_right(self._sorted_pointers, pointer)
        end = (
            self._sorted_pointers[position]
            if position < len(self._sorted_pointers)
            else None
        )
        row["fileOffset"] = f"0x{file_offset:x}"
        row["section"] = section
        row["rva"] = f"0x{rva:x}"
        if end is None:
            row["bodyStatus"] = "no_following_pointer"
            return row
        size = end - pointer
        body = self.pe.buf[file_offset : file_offset + size]
        if len(body) != size:
            row["bodyStatus"] = "truncated_image"
            return row
        row["bodyStatus"] = "resolved"
        row["bodyExtent"] = size
        row["bodyExtentBoundary"] = "pointer-gap upper bound, includes alignment padding"
        row["bodySha256"] = hashlib.sha256(body).hexdigest()
        return row


def open_resolver(
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> tuple[Resolver, dict[str, Any]]:
    """Open the resolver against the selected installed build.

    Returns the resolver and the native-input receipt that every report built
    from it must carry. Raises :class:`ResolverError` when the gate is not
    validated or the registration cannot be derived uniquely.
    """

    native = check_installed_native_inputs(
        gameassembly=gameassembly, metadata=metadata
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        raise ResolverError(f"{native.status}: {native.detail}")

    helper = load_metadata_helper(METADATA_HELPER)
    mapper = load_native_mapper(NATIVE_MAPPER)
    image = helper.Metadata(native.metadata)
    pe = mapper.PeImage(native.gameassembly)

    image_names = {image.string(row.name_index) for row in image.images}
    candidates = mapper.find_code_registration_candidates(pe, image_names)
    if len(candidates) != 1:
        raise ResolverError(
            "expected exactly one Il2CppCodeRegistration matching the "
            f"{len(image_names)} metadata image names; actual "
            f"{[hex(value) for value in candidates]}"
        )
    code_registration_va = candidates[0]
    modules = mapper.parse_codegen_modules(pe, code_registration_va)
    ranges = mapper.image_method_ranges(image)

    resolver = Resolver(
        metadata=image, pe=pe, code_registration_va=code_registration_va
    )
    for index, type_def in enumerate(image.types):
        resolver._type_index.setdefault(image.type_full_name(type_def), index)

    pointers: set[int] = set()
    for name, module in modules.items():
        image_range = ranges.get(name)
        if image_range is None or image_range["methodStart"] < 0:
            continue
        count = min(module["methodPointerCount"], image_range["methodCount"])
        start = image_range["methodStart"]
        resolver.module_method_starts[name] = start
        resolver.module_pointers[name] = module["methodPointersVa"]
        resolver.module_pointer_counts[name] = count
        for slot in range(count):
            pointer = pe.u64_at_va(module["methodPointersVa"] + slot * 8)
            if pointer:
                pointers.add(pointer)
            resolver._method_image[start + slot] = name
    resolver._sorted_pointers = sorted(pointers)

    receipt = {
        "gameAssembly": {
            "path": str(native.gameassembly),
            "sha256": native.gameassembly_sha256,
        },
        "globalMetadata": {
            "path": str(native.metadata),
            "sha256": native.metadata_sha256,
        },
        "codeRegistrationVa": f"0x{code_registration_va:x}",
        "codeRegistrationSource": "derived from the complete metadata image-name set",
        "imageCount": len(image_names),
        "distinctMethodPointers": len(resolver._sorted_pointers),
    }
    return resolver, receipt


# -- request harvesting ---------------------------------------------------


def harvest_method_specs(value: Any, *, origin: str = "") -> Iterator[MethodSpec]:
    """Yield every ``{"type": ..., "method": ...}`` object in a JSON tree.

    Recorded native contracts nest their method identities at arbitrary depth,
    so migration reads the shape rather than one schema's key path.
    """

    if isinstance(value, dict):
        type_name = value.get("type")
        method_name = value.get("method")
        if isinstance(type_name, str) and isinstance(method_name, str):
            yield MethodSpec(type_name, method_name, origin)
        for key, child in value.items():
            yield from harvest_method_specs(
                child, origin=f"{origin}.{key}" if origin else str(key)
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from harvest_method_specs(child, origin=f"{origin}[{index}]")


def unique_specs(specs: Iterable[MethodSpec]) -> list[MethodSpec]:
    """Drop duplicate identities, keeping the first origin that named each."""

    seen: dict[tuple[str, str], MethodSpec] = {}
    for spec in specs:
        seen.setdefault((spec.type_name, spec.method_name), spec)
    return list(seen.values())


def resolve_contract_files(
    paths: Iterable[Path],
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Re-resolve every method identity recorded by the given contract files."""

    sources: list[dict[str, Any]] = []
    specs: list[MethodSpec] = []
    for path in paths:
        try:
            raw = Path(path).read_bytes()
            value = json.loads(raw.decode("utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            sources.append({"path": str(path), "status": f"unreadable: {exc}"[:400]})
            continue
        harvested = unique_specs(
            harvest_method_specs(value, origin=Path(path).name)
        )
        sources.append(
            {
                "path": str(path),
                "sha256": hashlib.sha256(raw).hexdigest().upper(),
                "status": "read",
                "methodIdentities": len(harvested),
            }
        )
        specs.extend(harvested)

    specs = unique_specs(specs)
    resolver, receipt = open_resolver(gameassembly=gameassembly, metadata=metadata)
    rows = resolver.resolve_all(specs)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {
        "schema": SCHEMA,
        "nativeInputs": receipt,
        "sources": sources,
        "summary": {"requested": len(rows), "byStatus": dict(sorted(counts.items()))},
        "resolutions": rows,
    }


# -- CLI ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve managed method identities against the selected installed "
            "build, deriving Il2CppCodeRegistration rather than pinning it."
        )
    )
    parser.add_argument(
        "--from-contract",
        type=Path,
        action="append",
        default=[],
        metavar="PATH",
        help="JSON contract whose recorded {type, method} identities to re-resolve",
    )
    parser.add_argument(
        "--type", dest="type_name", help="one managed type full name to resolve"
    )
    parser.add_argument("--method", help="one method name inside --type")
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument(
        "--report", type=Path, help="write the resolution report to this JSON path"
    )
    args = parser.parse_args(argv)

    if args.from_contract and (args.type_name or args.method):
        parser.error("--from-contract and --type/--method are separate requests")
    if bool(args.type_name) != bool(args.method):
        parser.error("--type and --method must be given together")
    if not args.from_contract and not args.type_name:
        parser.error("pass --from-contract or --type/--method")

    try:
        if args.from_contract:
            report = resolve_contract_files(
                args.from_contract,
                gameassembly=args.gameassembly,
                metadata=args.metadata,
            )
        else:
            resolver, receipt = open_resolver(
                gameassembly=args.gameassembly, metadata=args.metadata
            )
            rows = [resolver.resolve(MethodSpec(args.type_name, args.method))]
            report = {
                "schema": SCHEMA,
                "nativeInputs": receipt,
                "summary": {"requested": 1, "byStatus": {rows[0]["status"]: 1}},
                "resolutions": rows,
            }
    except ResolverError as exc:
        print(f"il2cpp method resolver unavailable: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
        summary = report["summary"]
        print(
            f"resolved {summary['requested']} method identities "
            f"({summary['byStatus']}) -> {args.report}"
        )
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover - documented entry point
    if not __package__:
        raise SystemExit(
            "run as: python -m scripts.game_data.il2cpp.method_resolver"
        )
    raise SystemExit(main())
