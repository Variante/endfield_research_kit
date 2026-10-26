"""Selected-build BuffData values with complete-record and identifier gates.

The derived plan names stored fields; it does not establish runtime effects or
promote a record into the independently reviewed whole-schema receipt lane.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.derived_plans import BUFFDATA_TYPE, load_registry
from scripts.game_data.memorypack.derived_values import decode_file, find_identifier
from scripts.game_data.memorypack.target_settings_corpus import selected_enum_fields
from scripts.game_data.string_pool import StringPool


def _child(registry, definition: int, name: str, *, listed: bool = False) -> int:
    member = next((m for m in registry.plans[definition] if m.name == name), None)
    if listed:
        member = member.element if member is not None and member.kind == 'list' else None
    if member is None or member.kind != 'object' or member.ref not in registry.plans:
        raise ValueError(f'BuffData selected object plan unavailable: {name}')
    return member.ref


def load_context(*, registry=None, gameassembly: Path | None = None,
                 metadata: Path | None = None) -> dict[str, Any]:
    gate = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
    evidence = {"status": gate.status, "detail": gate.detail}
    if not gate.validated:
        return {"evidence": evidence}
    try:
        if registry is None:
            registry, audit = load_registry(gameassembly=gate.gameassembly, metadata=gate.metadata)
            if audit.get("status") != "validated":
                return {"evidence": {"status": audit.get("status", "unavailable"),
                                     "detail": str(audit.get("failures") or audit)}}
        definition = registry.named_roots[BUFFDATA_TYPE]
        image = open_native_image(gate.gameassembly, gate.metadata)
        enums, _ = selected_enum_fields(image, registry, definition, owner_type=BUFFDATA_TYPE,
                                        enum_fields=("lifeType",))
        stacking = _child(registry, definition, 'stackingSettings')
        stacking_enums, _ = selected_enum_fields(
            image, registry, stacking, owner_type=registry.wrapped_names[stacking],
            enum_fields=("identifierType", "stackingType"),
        )
        modifier = _child(registry, _child(registry, definition, 'attributeModifier'),
                          'attributeModifiers', listed=True)
        modifier_enums, _ = selected_enum_fields(image, registry, modifier,
            owner_type=registry.wrapped_names[modifier],
            enum_fields=('attributeType', 'formulaItem', 'modifyAttributeType'))
        events = _child(registry, definition, 'abilityEventAction', listed=True)
        event_enums, _ = selected_enum_fields(image, registry, events,
            owner_type=registry.wrapped_names[events], enum_fields=('abilityEvent',))
        return {"evidence": {"status": "validated", "detail": "",
                             "boundary": "Whole-record derived framing and selected field enum types; stored values only."},
                "registry": registry, "root": definition,
                "enums": {**enums, **stacking_enums, **modifier_enums, **event_enums}}
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, TypeError) as exc:
        return {"evidence": {"status": "unavailable", "detail": f"{type(exc).__name__}: {exc}"}}


def read_record(path: Path, context: dict[str, Any], *, strings: StringPool | None = None) -> dict[str, Any]:
    evidence = context.get("evidence") or {}
    if evidence.get("status") != "validated":
        raise ValueError(f"BuffData selected plan {evidence.get('status', 'missing')}: {evidence.get('detail', '')}")
    data = path.read_bytes()
    value, reached = decode_file(data, context["root"], context["registry"], source=path.name,
                                strings=strings, retain_union_framing=True)
    identifier = find_identifier(value)
    if reached != len(data) or identifier != path.stem:
        raise ValueError(f"BuffData whole-record-or-identifier mismatch: {reached}/{len(data)} id={identifier!r} expected={path.stem!r}")
    return value
