"""Compose reviewed formatter semantics before authenticating projected bytes.

Plain window contracts retain their byte-only boundary and caller-owned build
gate. A projection declaring a required role contract must pass its explicitly
allowlisted semantic owner on the same selected image, with installed-input
bookends, before any annotation is removed for the raw byte-hash checker.
Unknown, mixed, missing or refused role declarations stay fail-closed. These
checks prove stored source flow only, never live formatter selection.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.il2cpp.native_image import read_reviewed_contract


def _role_owner(name: str):
    if name == "buff_ec_profiles_native.json":
        from scripts.game_data.memorypack import buff_ec_profiles_native
        return buff_ec_profiles_native
    if name == "buff_98_roles_native.json":
        from scripts.game_data.memorypack import buff_98_roles_native
        return buff_98_roles_native
    if name == "buff_23_roles_native.json":
        from scripts.game_data.memorypack import buff_23_roles_native
        return buff_23_roles_native
    raise ValueError(f"formatterNative.native:unsupported-role-contract={str(name)[:200]}")


def is_role_projection(contract: dict[str, Any]) -> bool:
    """Recognize a supported declaration shape; this never validates a claim."""
    return (contract.get('schemaVersion') == 2 and contract.get('roleContract') in (
                'buff_ec_profiles_native.json', 'buff_98_roles_native.json',
                'buff_23_roles_native.json')
            and bool(contract.get('codeWindows'))
            and all(row.get('requiredRoleContract') == contract['roleContract'] for row in contract['codeWindows']))


def check_formatter_windows(image: Any, contract: dict[str, Any], *, label: str) -> dict[str, Any]:
    """Validate declared semantics and the exact projected code-window bytes."""
    windows = contract.get("codeWindows", [])
    role = contract.get("roleContract")
    annotated = [row for row in windows if "requiredRoleContract" in row]
    if role is None and not annotated:
        if contract.get("schemaVersion", 1) != 1:
            raise ValueError(f"{label}.native:incomplete-role-contract-declaration")
        image.check_windows(windows, label=label)
        return {"status": "validated", "boundary": "byte-windows-only"}
    if (not isinstance(role, str) or not role or contract.get("schemaVersion") != 2
            or not windows or len(annotated) != len(windows)
            or any(row["requiredRoleContract"] != role for row in windows)):
        raise ValueError(f"{label}.native:incomplete-role-contract-declaration")
    owner = _role_owner(role)
    fact, _ = read_reviewed_contract(owner.CONTRACT_PATH, schema=owner.SCHEMA,
                                    status="exact-current-build", label=label + ".role")
    inputs = fact["nativeInputs"]
    _publication_gate(image, inputs)
    proof = owner.validate_on_image(image, inputs, projection=contract)
    if proof.get("status") != "validated":
        raise ValueError(f"{label}.native:role-contract-refused={str(proof)[:500]}")
    _publication_gate(image, inputs)
    image.check_windows([{key: value for key, value in row.items() if key != "requiredRoleContract"}
                         for row in windows], label=label)
    return proof
