"""Validate frozen Audio trace manifests and recorded module addresses offline."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.webui.story_recovery import runtime_trace_core as core


MANIFEST_SCHEMA = "audioRuntimeTrace.hooks.v2"
MAX_ABI_ARGUMENT_INDEX = 63
ABI_ARGUMENT_KINDS = frozenset({"pointer", "string", "u32", "i32", "u64", "bool", "utf16"})
ABI_RETURN_KINDS = ABI_ARGUMENT_KINDS | {"void"}


def _validate_abi_contract(hook: dict[str, Any], label: str) -> None:
    args = hook.get("args")
    if args is not None and not isinstance(args, dict):
        raise core.CaptureConfigurationError(f"{label} args must be an object")
    for name, spec in (args or {}).items():
        if not isinstance(name, str) or not name.strip() or not isinstance(spec, dict):
            raise core.CaptureConfigurationError(f"{label} args[{name!r}] must be an object")
        index = spec.get("index")
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or index < 0
            or index > MAX_ABI_ARGUMENT_INDEX
        ):
            raise core.CaptureConfigurationError(
                f"{label} args[{name!r}] index must be in 0..{MAX_ABI_ARGUMENT_INDEX}"
            )
        kind = spec.get("kind", "pointer")
        if not isinstance(kind, str) or kind not in ABI_ARGUMENT_KINDS:
            raise core.CaptureConfigurationError(f"{label} args[{name!r}] has unsupported kind")
        if "allowNull" in spec and (kind != "pointer" or type(spec["allowNull"]) is not bool):
            raise core.CaptureConfigurationError(f"{label} args[{name!r}] allowNull requires a pointer and boolean")
    string_args = hook.get("stringArgs")
    if string_args is not None and not isinstance(string_args, dict):
        raise core.CaptureConfigurationError(f"{label} stringArgs must be an object")
    for raw_index, name in (string_args or {}).items():
        try:
            index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise core.CaptureConfigurationError(
                f"{label} stringArgs index must be an integer"
            ) from exc
        if (
            isinstance(raw_index, bool)
            or index < 0
            or index > MAX_ABI_ARGUMENT_INDEX
            or str(index) != str(raw_index)
            or not isinstance(name, str)
            or not name.strip()
        ):
            raise core.CaptureConfigurationError(
                f"{label} stringArgs index must be in 0..{MAX_ABI_ARGUMENT_INDEX} "
                "and name a field"
            )
    return_kind = hook.get("returnKind", "void")
    if not isinstance(return_kind, str) or return_kind not in ABI_RETURN_KINDS:
        raise core.CaptureConfigurationError(f"{label} has unsupported returnKind")


def load_manifest(path: Path) -> dict[str, Any]:
    value = core.load_manifest_object(path, MANIFEST_SCHEMA, "audio hook")
    for key in ("gameBuild", "processName", "moduleName"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise core.CaptureConfigurationError(f"manifest {key} must be a non-empty string")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise core.CaptureConfigurationError("audio manifest must contain a non-empty files object")
    for required in ("executable", "gameAssembly", "metadata"):
        if required not in files:
            raise core.CaptureConfigurationError(f"audio manifest is missing files.{required}")
    native_module_name = value.get("nativeModuleName")
    native_hooks = value.get("nativeHooks", [])
    if native_module_name is not None and (
        not isinstance(native_module_name, str) or not native_module_name.strip()
    ):
        raise core.CaptureConfigurationError("manifest nativeModuleName must be a non-empty string")
    if not isinstance(native_hooks, list):
        raise core.CaptureConfigurationError("audio manifest nativeHooks must be a list")
    if native_hooks and "akSoundEngine" not in files:
        raise core.CaptureConfigurationError(
            "audio manifest nativeHooks require files.akSoundEngine"
        )
    hooks = value.get("hooks")
    if not isinstance(hooks, list) or not hooks:
        raise core.CaptureConfigurationError("audio manifest hooks must be a non-empty list")
    names: set[str] = set()
    for index, hook in enumerate(hooks):
        if not isinstance(hook, dict):
            raise core.CaptureConfigurationError(f"hooks[{index}] must be an object")
        name = hook.get("name")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise core.CaptureConfigurationError(f"hooks[{index}] has a duplicate/invalid name")
        names.add(name)
        rva = hook.get("rva")
        if not isinstance(rva, str) or not rva.lower().startswith("0x"):
            raise core.CaptureConfigurationError(f"hooks[{index}] has an invalid RVA")
        try:
            if int(rva, 16) < 0:
                raise ValueError
        except ValueError as exc:
            raise core.CaptureConfigurationError(
                f"hooks[{index}] has an invalid RVA: {rva!r}"
            ) from exc
        if hook.get("mode") not in {"carrier", "request", "control"}:
            raise core.CaptureConfigurationError(
                f"hooks[{index}] mode must be carrier, request, or control"
            )
        if not isinstance(hook.get("sourceKind"), str) or not hook["sourceKind"].strip():
            raise core.CaptureConfigurationError(f"hooks[{index}] sourceKind is required")
        if "required" in hook and not isinstance(hook["required"], bool):
            raise core.CaptureConfigurationError(f"hooks[{index}] required must be boolean")
        _validate_abi_contract(hook, f"hooks[{index}]")
        stack_arguments = hook.get("stackArguments")
        if stack_arguments is not None and not isinstance(stack_arguments, list):
            raise core.CaptureConfigurationError(
                f"hooks[{index}] stackArguments must be a list"
            )
        for stack_index, spec in enumerate(stack_arguments or []):
            if (
                not isinstance(spec, dict)
                or not isinstance(spec.get("name"), str)
                or not spec["name"].strip()
            ):
                raise core.CaptureConfigurationError(
                    f"hooks[{index}].stackArguments[{stack_index}] must name a field"
                )
            offset = spec.get("offset")
            if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
                raise core.CaptureConfigurationError(
                    f"hooks[{index}].stackArguments[{stack_index}] offset must be non-negative"
                )
            if not isinstance(spec.get("kind", "pointer"), str) or spec.get("kind", "pointer") not in {
                "pointer", "u32", "i32", "u64", "utf16",
            }:
                raise core.CaptureConfigurationError(
                    f"hooks[{index}].stackArguments[{stack_index}] has unsupported kind"
                )
    native_names: set[str] = set()
    for index, hook in enumerate(native_hooks):
        if not isinstance(hook, dict):
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] must be an object")
        name = hook.get("name")
        if not isinstance(name, str) or not name.strip() or name in native_names:
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] has a duplicate/invalid name")
        native_names.add(name)
        rva = hook.get("rva")
        if not isinstance(rva, str) or not rva.lower().startswith("0x"):
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] has an invalid RVA")
        try:
            if int(rva, 16) < 0:
                raise ValueError
        except ValueError as exc:
            raise core.CaptureConfigurationError(
                f"nativeHooks[{index}] has an invalid RVA: {rva!r}"
            ) from exc
        if not isinstance(hook.get("sourceKind"), str) or not hook["sourceKind"].strip():
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] sourceKind is required")
        if "required" in hook and not isinstance(hook["required"], bool):
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] required must be boolean")
        _validate_abi_contract(hook, f"nativeHooks[{index}]")
        memory = hook.get("memory")
        if memory is not None and not isinstance(memory, list):
            raise core.CaptureConfigurationError(f"nativeHooks[{index}] memory must be a list")
        previous_memory_kinds: dict[str, str] = {}
        for mem_index, spec in enumerate(memory or []):
            if (
                not isinstance(spec, dict)
                or not isinstance(spec.get("name"), str)
                or not spec["name"].strip()
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] must name a field"
                )
            if "argIndex" in spec and (
                isinstance(spec["argIndex"], bool)
                or not isinstance(spec["argIndex"], int)
                or not 0 <= spec["argIndex"] <= MAX_ABI_ARGUMENT_INDEX
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] argIndex must be in "
                    f"0..{MAX_ABI_ARGUMENT_INDEX}"
                )
            has_arg_index = (
                isinstance(spec.get("argIndex"), int)
                and not isinstance(spec["argIndex"], bool)
                and spec["argIndex"] <= MAX_ABI_ARGUMENT_INDEX
                and spec["argIndex"] >= 0
            )
            has_stack_offset = (
                isinstance(spec.get("stackOffset"), int)
                and not isinstance(spec["stackOffset"], bool)
                and spec["stackOffset"] >= 0
            )
            has_base_field = isinstance(spec.get("baseField"), str) and bool(
                spec["baseField"].strip()
            )
            if sum((has_arg_index, has_stack_offset, has_base_field)) != 1:
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] needs exactly one non-negative "
                    "argIndex, stackOffset, or baseField"
                )
            if "savePointer" in spec and not isinstance(spec["savePointer"], bool):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] savePointer must be boolean"
                )
            pointer_offsets = spec.get("pointerOffsets")
            if pointer_offsets is not None and (
                not isinstance(pointer_offsets, list)
                or any(
                    not isinstance(item, int)
                    or isinstance(item, bool)
                    or item < 0
                    for item in pointer_offsets
                )
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] pointerOffsets must be "
                    "a list of non-negative integers"
                )
            if "pointerOffset" in spec and "pointerOffsets" in spec:
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] cannot set both "
                    "pointerOffset and pointerOffsets"
                )
            if "pointerOffset" in spec and (
                not isinstance(spec["pointerOffset"], int)
                or isinstance(spec["pointerOffset"], bool)
                or spec["pointerOffset"] < 0
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] pointerOffset must be non-negative"
                )
            if (
                not isinstance(spec.get("offset", 0), int)
                or isinstance(spec.get("offset", 0), bool)
                or spec.get("offset", 0) < 0
            ):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] offset must be non-negative"
                )
            if not isinstance(spec.get("kind", "pointer"), str) or spec.get("kind", "pointer") not in {
                "pointer",
                "u32",
                "i32",
                "u64",
                "utf16",
                "utf16Direct",
            }:
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] has unsupported kind"
                )
            condition = spec.get("requireMemory")
            if condition is not None:
                valid = isinstance(condition, dict)
                name = condition.get("name") if valid else None
                kind = previous_memory_kinds.get(name) if isinstance(name, str) else None
                valid = valid and (
                    (set(condition) == {"name", "equals"} and kind == "u32"
                     and type(condition["equals"]) is int and 0 <= condition["equals"] <= 0xffffffff)
                    or (set(condition) == {"name", "nonzero"} and kind == "pointer"
                        and condition["nonzero"] is True)
                )
                if not valid:
                    raise core.CaptureConfigurationError(
                        f"nativeHooks[{index}].memory[{mem_index}] requireMemory must test an earlier "
                        "u32 field for equality or an earlier pointer for nonzero"
                    )
            if "samplePhase" in spec and spec["samplePhase"] not in ("entry", "result"):
                raise core.CaptureConfigurationError(
                    f"nativeHooks[{index}].memory[{mem_index}] samplePhase must be entry or result"
                )
            condition = spec.get("requireArgument")
            if condition is not None:
                valid = isinstance(condition, dict) and set(condition) == {"name", "nonzero"}
                name = condition.get("name") if valid else None
                argument = (hook.get("args") or {}).get(name) if isinstance(name, str) else None
                if not valid or condition["nonzero"] is not True or not argument or argument.get("kind") != "pointer":
                    raise core.CaptureConfigurationError(
                        f"nativeHooks[{index}].memory[{mem_index}] requireArgument must test a declared pointer for nonzero"
                    )
            previous_memory_kinds[spec["name"]] = spec.get("kind", "pointer")
    if native_hooks and not native_module_name:
        raise core.CaptureConfigurationError("nativeHooks require nativeModuleName")
    if not isinstance(value.get("evidenceBoundary"), dict):
        raise core.CaptureConfigurationError("audio manifest evidenceBoundary must be an object")
    return value


def validate_hook_ranges(
    manifest: dict[str, Any],
    game_assembly: Path,
    native_module: Path | None = None,
) -> None:
    """Reject frozen manifest RVAs outside the selected native files."""
    try:
        module_size = game_assembly.stat().st_size
    except OSError as exc:
        raise core.CaptureConfigurationError(
            f"cannot stat GameAssembly for audio hook range validation: {game_assembly}"
        ) from exc
    invalid = []
    for hook in manifest["hooks"]:
        rva = int(hook["rva"], 16)
        if rva <= 0 or rva >= module_size:
            invalid.append(f"{hook['name']}={hook['rva']}")
    if invalid:
        raise core.CaptureConfigurationError(
            "audio hook RVA is outside the verified GameAssembly range "
            f"(0x0..0x{module_size - 1:x}): {', '.join(invalid)}"
        )

    native_hooks = manifest.get("nativeHooks", [])
    if not native_hooks:
        return
    if native_module is None:
        raise core.CaptureConfigurationError(
            "native hook range validation requires the verified AkSoundEngine module"
        )
    try:
        native_size = native_module.stat().st_size
    except OSError as exc:
        raise core.CaptureConfigurationError(
            f"cannot stat AkSoundEngine for audio hook range validation: {native_module}"
        ) from exc
    invalid_native = []
    for hook in native_hooks:
        rva = int(hook["rva"], 16)
        if rva <= 0 or rva >= native_size:
            invalid_native.append(f"{hook['name']}={hook['rva']}")
    if invalid_native:
        raise core.CaptureConfigurationError(
            "audio native hook RVA is outside the verified AkSoundEngine range "
            f"(0x0..0x{native_size - 1:x}): {', '.join(invalid_native)}"
        )


def validated_module_base(value: Any, image_size: int, label: str) -> str:
    """Bound an ASLR image extent without reading process memory."""
    if (not isinstance(value, str) or not value.startswith("0x") or not 3 <= len(value) <= 18
            or any(character not in "0123456789abcdefABCDEF" for character in value[2:])):
        raise RuntimeError(f"{label}: expected hexadecimal module base")
    try:
        base = int(value, 16)
    except ValueError as exc:
        raise RuntimeError(f"{label}: invalid module base") from exc
    if base <= 0 or base % 4096 or not 0 < image_size < 0x800000000000 - base:
        raise RuntimeError(f"{label}: module extent is outside bounded Win64 user space")
    return hex(base)
