"""Authenticate the native NPC animation-template resource path."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.animation_curve_native import _pe_file_offset

CONTRACT_PATH = Path(__file__).with_suffix('.json')
CONTRACT_SHA256 = '01E338948621CB5EE3F7A428FB02074C1B41402B4B859FE5FAFB163F2AEAB6F8'
SCHEMA = 'endfield.npc-animation-template-native.v1'


def load_npc_animation_template(*, game_root: Path | None = None,
                                        contract_path: Path = CONTRACT_PATH):
    """Return no consumer facts when any selected-build or byte gate fails."""
    failures = []
    audit = dict(status='validation_failed', validationFailures=failures,
                 renderInputsAdmitted=False)
    try:
        raw = contract_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest().upper()
        if digest != CONTRACT_SHA256:
            raise ValueError('contract_sha256: expected ' + CONTRACT_SHA256 + ', actual ' + digest)
        contract = json.loads(raw)
        if contract.get('schema') != SCHEMA or contract.get('status') != 'validated':
            raise ValueError('contract_schema_or_status: unsupported contract')
        inputs = contract['nativeInputs']
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            inputs['GameAssembly.dll'], inputs['global-metadata.dat'],
            gameassembly=root.parent / 'GameAssembly.dll' if root else None,
            metadata=root / 'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        audit.update(nativeGate=dict(status=gate.status, detail=gate.detail),
                     contractSha256=digest)
        if gate.status != 'validated':
            audit['status'] = gate.status
            failures.append(dict(gate='installed_native_inputs', expected='validated',
                                 actual=gate.status, detail=gate.detail))
            return None, audit
        image = gate.gameassembly.read_bytes()
        for row in contract['codeWindows']:
            size = row['length']
            offset = _pe_file_offset(image, int(row['rva'], 0), size)
            actual = hashlib.sha256(image[offset:offset + size]).hexdigest()
            if actual != row['sha256']:
                failures.append(dict(gate='code_window_sha256', owner=row['name'],
                                     expected=row['sha256'], actual=actual))
        if failures:
            return None, audit
        audit.update(status='validated', evidenceBoundary=contract['evidenceBoundary'],
                     validatedCodeWindows=len(contract['codeWindows']))
        return contract, audit
    except (OSError, ValueError, KeyError, TypeError) as error:
        failures.append(dict(gate='contract_validation', detail=str(error)))
        return None, audit


def cpu_template_asset_path(template: str, contract: dict) -> str:
    """Evaluate the reviewed base path branch, restricted to safe NPC tags.

    The caller must authenticate the contract and independently prove tag
    admission. This function does not simulate mutable caches or IFix patches.
    """
    if not isinstance(template, str) or not template.isascii():
        raise ValueError("template must be an ASCII NPC animation tag")
    parts = template.split("/")
    if parts[:2] != ["NPC", "AnimationConfig"] or len(parts) < 4 or any(
            not part or part in (".", "..") or any(c not in
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in part)
            for part in parts):
        raise ValueError("unsupported NPC animation tag hierarchy")
    rule = contract["pathRule"]
    prefix = rule["humanoidPrefix"] if parts[-3] == rule["humanoidSelector"] else ""
    return (rule["root"] + prefix + parts[-2] + rule["leafPrefix"]
            + parts[-1] + rule["suffix"])
