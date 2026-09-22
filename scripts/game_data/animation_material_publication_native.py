"""Authenticate the separate UI and gameplay animation/material consumer routes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.animation_curve_native import _pe_file_offset

CONTRACT_PATH = CONTRACTS_DIR / "animation_material_publication.json"
CONTRACT_SHA256 = '86E02CA931B13A54956972F3FBAB75757300B6EC2339783C0498B3EE77BD12CE'
SCHEMA = 'endfield.animation-material-publication-native.v1'


def load_animation_material_publication(*, game_root: Path | None = None,
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
        audit.update(status='validated', renderInputsAdmitted=True,
                     evidenceBoundary=contract['evidenceBoundary'],
                     validatedCodeWindows=len(contract['codeWindows']))
        return contract, audit
    except (OSError, ValueError, KeyError, TypeError) as error:
        failures.append(dict(gate='contract_validation', detail=str(error)))
        return None, audit
